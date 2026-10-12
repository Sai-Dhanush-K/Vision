"""Monitor central threat detection from sampled video frames."""

import argparse
from pathlib import Path
import time

import cv2
import numpy as np

from ..input import VideoFileSource
from .annotate_samples import _draw_detection
from .spatial_rules import ThreatRuleConfig, find_threats
from .threat_events import ThreatEventState
from .tracker import IoUTracker
from .yolo_detector import YoloDetector


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
    detector = detector or YoloDetector()
    rules = rules or ThreatRuleConfig()
    state = ThreatEventState(cooldown_ms=cooldown_ms)
    tracker = IoUTracker()
    processed = 0

    with VideoFileSource(video_path) as source:
        frame_step = source.metadata.fps / sample_fps
        next_index = 0.0
        last_detections = []
        last_messages: list[str] = []
        decoded = 0
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
                processed += 1
                elapsed_ms = (time.perf_counter() - started) * 1000
                current = ", ".join(
                    f"{candidate.detection.label}#{candidate.detection.track_id}"
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
                    f"{candidate.detection.label.title()} ahead."
                    for candidate in candidates
                ]
                next_index += frame_step
            if display:
                preview = draw_preview_overlay(
                    frame.image, rules, last_detections, last_messages
                )
                cv2.imshow("Smart Assistive Glasses - Threat Monitor", preview)
                key = cv2.waitKey(1) & 0xFF
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
    parser.add_argument("--max-frames", type=int, default=20)
    args = parser.parse_args()

    started = time.perf_counter()
    processed = monitor_video(
        args.video_path,
        sample_fps=args.sample_fps,
        max_frames=None if args.full_video else args.max_frames,
        display=args.display,
    )
    elapsed = time.perf_counter() - started
    print(f"Processed {processed} frames in {elapsed:.1f} seconds.")


if __name__ == "__main__":
    main()
