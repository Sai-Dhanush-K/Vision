"""Monitor central threat detection from sampled video frames."""

import argparse
from pathlib import Path
import time
from typing import Protocol

import cv2
import numpy as np

from ..alerts import AlertPriority, Pyttsx3Speaker, SpeechManager, SpeechRequest
from ..input import VideoFileSource
from .annotate_samples import _draw_detection
from .spatial_rules import ThreatRuleConfig, find_threats
from .threat_events import ThreatEventState
from .tracker import IoUTracker
from .yolo_detector import YoloDetector


class SceneWorker(Protocol):
    """Minimal background scene worker used by the preview."""

    def submit(self, image: np.ndarray, detailed: bool = False) -> bool:
        """Submit one frame if no scene request is currently running."""


class PreviewControls:
    """Mouse and keyboard state for optional AI controls in the preview."""

    def __init__(self, scene_enabled: bool = False) -> None:
        self.scene_enabled = scene_enabled
        self.request_scene = False
        self._button_rects: dict[str, tuple[int, int, int, int]] = {}

    def draw(self, image: np.ndarray) -> np.ndarray:
        """Draw controls and return an annotated copy."""

        output = image.copy()
        height, width = output.shape[:2]
        button_width = min(300, max(220, width // 4))
        button_height = 46
        gap = 12
        y = height - button_height - 20
        self._button_rects = {
            "toggle": (20, y, 20 + button_width, y + button_height),
            "scene": (
                20 + button_width + gap,
                y,
                20 + 2 * button_width + gap,
                y + button_height,
            ),
        }
        labels = {
            "toggle": (
                "AI scan: ON (A)" if self.scene_enabled else "AI scan: OFF (A)"
            ),
            "scene": "Describe scene (S)",
        }
        for name, (left, top, right, bottom) in self._button_rects.items():
            color = (30, 140, 30) if name == "toggle" and self.scene_enabled else (
                80, 80, 80
            )
            cv2.rectangle(output, (left, top), (right, bottom), color, -1)
            cv2.putText(
                output,
                labels[name],
                (left + 12, top + 30),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (255, 255, 255),
                2,
                cv2.LINE_AA,
            )
        return output

    def handle_key(self, key: int) -> bool:
        """Handle keyboard controls and return whether the key was consumed."""

        if key in (ord("a"), ord("A")):
            self.scene_enabled = not self.scene_enabled
            return True
        if key in (ord("s"), ord("S")):
            self.request_scene = True
            return True
        return False

    def handle_click(self, x: int, y: int) -> bool:
        """Handle a mouse click against the most recently drawn controls."""

        for name, (left, top, right, bottom) in self._button_rects.items():
            if left <= x <= right and top <= y <= bottom:
                if name == "toggle":
                    self.scene_enabled = not self.scene_enabled
                else:
                    self.request_scene = True
                return True
        return False


def draw_preview_overlay(
    image: np.ndarray,
    config: ThreatRuleConfig,
    detections,
    messages: list[str],
) -> np.ndarray:
    """Return a frame with the central region, detections, and current alerts."""

    output = image.copy()
    height, width = output.shape[:2]
    region = config.region
    top_left = (round(region.left * width), round(region.top * height))
    bottom_right = (round(region.right * width), round(region.bottom * height))
    cv2.rectangle(output, top_left, bottom_right, (0, 220, 0), 3)

    for detection in detections:
        _draw_detection(output, detection)

    for index, message in enumerate(messages):
        cv2.putText(
            output,
            f"THREAT: {message}",
            (30, 50 + index * 40),
            cv2.FONT_HERSHEY_SIMPLEX,
            1.0,
            (0, 0, 255),
            3,
            cv2.LINE_AA,
        )
    return output


def monitor_video(
    video_path: str | Path,
    sample_fps: float = 2.0,
    max_frames: int | None = 20,
    detector: YoloDetector | None = None,
    rules: ThreatRuleConfig | None = None,
    cooldown_ms: float = 5_000.0,
    display: bool = False,
    speech_manager: SpeechManager | None = None,
    scene_worker: SceneWorker | None = None,
    scene_interval_seconds: float = 5.0,
    controls: PreviewControls | None = None,
) -> int:
    """Print threat status after sampled frames and return frames processed.

    ``sample_fps`` is based on source-video time, not processing time. A
    ``max_frames`` value bounds development runs; ``None`` processes the
    complete source video.
    """

    if sample_fps <= 0:
        raise ValueError("sample_fps must be positive")
    if max_frames is not None and max_frames <= 0:
        raise ValueError("max_frames must be positive when provided")
    if scene_interval_seconds <= 0:
        raise ValueError("scene_interval_seconds must be positive")
    detector = detector or YoloDetector()
    rules = rules or ThreatRuleConfig()
    state = ThreatEventState(cooldown_ms=cooldown_ms)
    tracker = IoUTracker()
    processed = 0

    with VideoFileSource(video_path) as source:
        controls = controls or PreviewControls(scene_worker is not None)
        if display:
            cv2.namedWindow(
                "Smart Assistive Glasses - Threat Monitor",
                cv2.WINDOW_NORMAL,
            )
            cv2.resizeWindow(
                "Smart Assistive Glasses - Threat Monitor",
                960,
                540,
            )
        frame_step = source.metadata.fps / sample_fps
        next_index = 0.0
        last_detections = []
        last_messages: list[str] = []
        decoded = 0
        next_scene_timestamp_ms = 0.0
        while max_frames is None or processed < max_frames:
            if not display:
                source.seek(round(next_index))
            frame = source.read()
            if frame is None:
                break
            decoded += 1
            should_sample = frame.timestamp_ms >= next_index / source.metadata.fps * 1000
            if should_sample:
                started = time.perf_counter()
                detections = tracker.update(
                    detector.detect(frame.image), frame.timestamp_ms
                )
                candidates = find_threats(
                    detections,
                    image_width=frame.image.shape[1],
                    image_height=frame.image.shape[0],
                    config=rules,
                )
                alerts = state.update(candidates, frame.timestamp_ms)
                if speech_manager is not None:
                    for alert in alerts:
                        track_id = alert.candidate.detection.track_id
                        speech_manager.submit(
                            SpeechRequest(
                                text=alert.message,
                                priority=AlertPriority.HIGH,
                                deduplication_key=(
                                    f"local:{alert.label}:"
                                    f"{track_id if track_id is not None else alert.label}"
                                ),
                            )
                        )
                processed += 1
                elapsed_ms = (time.perf_counter() - started) * 1000
                current = ", ".join(
                    f"{candidate.alert_label}#{candidate.detection.track_id}"
                    for candidate in candidates
                ) or "none"
                new_alerts = ", ".join(alert.message for alert in alerts) or "none"
                print(
                    f"frame={frame.index} "
                    f"source_time={frame.timestamp_ms / 1000:.2f}s "
                    f"threats={current} "
                    f"new_alerts={new_alerts} "
                    f"processing={elapsed_ms:.0f}ms",
                    flush=True,
                )
                last_detections = detections
                last_messages = [
                    f"{candidate.alert_label.title()} ahead."
                    for candidate in candidates
                ]
                next_index += frame_step
                if (
                    scene_worker is not None
                    and controls.scene_enabled
                    and frame.timestamp_ms >= next_scene_timestamp_ms
                ):
                    scene_worker.submit(frame.image, detailed=False)
                    next_scene_timestamp_ms += scene_interval_seconds * 1000
                if scene_worker is not None and controls.request_scene:
                    if scene_worker.submit(frame.image, detailed=True):
                        controls.request_scene = False
            if display:
                preview = draw_preview_overlay(
                    frame.image, rules, last_detections, last_messages
                )
                preview = controls.draw(preview)
                cv2.setMouseCallback(
                    "Smart Assistive Glasses - Threat Monitor",
                    lambda event, x, y, flags, param: (
                        controls.handle_click(x, y)
                        if event == cv2.EVENT_LBUTTONUP
                        else None
                    ),
                )
                cv2.imshow("Smart Assistive Glasses - Threat Monitor", preview)
                key = cv2.waitKey(1) & 0xFF
                controls.handle_key(key)
                if key in (ord("q"), 27):
                    break

    if display:
        cv2.destroyAllWindows()
    return processed


def main() -> None:
    """Run the terminal threat monitor."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("video_path", type=Path)
    parser.add_argument("--sample-fps", type=float, default=2.0)
    parser.add_argument(
        "--display",
        action="store_true",
        help="Also show sampled annotated frames in an OpenCV window.",
    )
    parser.add_argument(
        "--full-video",
        action="store_true",
        help="Process sampled frames until the video ends.",
    )
    parser.add_argument(
        "--speech",
        action="store_true",
        help="Speak newly eligible local threat alerts with pyttsx3.",
    )
    parser.add_argument(
        "--mistral-scene",
        action="store_true",
        help="Speak optional short Mistral scene guidance every five seconds.",
    )
    parser.add_argument(
        "--scene-interval",
        type=float,
        default=5.0,
        help="Source-video seconds between Mistral scene requests.",
    )
    parser.add_argument("--max-frames", type=int, default=20)
    args = parser.parse_args()

    started = time.perf_counter()
    speech_manager = (
        SpeechManager(Pyttsx3Speaker())
        if args.speech or args.mistral_scene
        else None
    )
    scene_worker = None
    if args.mistral_scene:
        from ..scene import MistralSceneAnalyzer, MistralSceneWorker

        def speak_scene(result) -> None:
            print(f"scene_summary={result.scene_summary}", flush=True)
            if result.detailed:
                speech_manager.submit(
                    SpeechRequest(
                        text=result.scene_summary,
                        priority=AlertPriority.NORMAL,
                        deduplication_key="scene:detailed-summary",
                    )
                )
                return
            for index, observation in enumerate(result.observations):
                speech_manager.submit(
                    SpeechRequest(
                        text=observation.speech_text,
                        priority={
                            "high": AlertPriority.HIGH,
                            "normal": AlertPriority.NORMAL,
                            "low": AlertPriority.LOW,
                        }[observation.priority],
                        deduplication_key=(
                            f"scene:{observation.category}:"
                            f"{observation.location}:{index}"
                        ),
                    )
                )
            if not result.observations:
                speech_manager.submit(
                    SpeechRequest(
                        text=result.scene_summary,
                        priority=AlertPriority.NORMAL,
                        deduplication_key="scene:summary",
                    )
                )

        def report_scene_error(error: Exception) -> None:
            print(f"scene_error={error}", flush=True)

        scene_worker = MistralSceneWorker(
            MistralSceneAnalyzer(),
            on_result=speak_scene,
            on_error=report_scene_error,
        )
    try:
        processed = monitor_video(
            args.video_path,
            sample_fps=args.sample_fps,
            max_frames=None if args.full_video else args.max_frames,
            display=args.display,
            speech_manager=speech_manager,
            scene_worker=scene_worker,
            scene_interval_seconds=args.scene_interval,
        )
    finally:
        if scene_worker is not None:
            scene_worker.close()
        if speech_manager is not None:
            speech_manager.close()
    elapsed = time.perf_counter() - started
    print(f"Processed {processed} frames in {elapsed:.1f} seconds.")


if __name__ == "__main__":
    main()
