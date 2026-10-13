import numpy as np

from smart_assist.alerts import AlertPriority, SpeechRequest
from smart_assist.detection.preview_player import (
    PreviewControls,
    draw_preview_overlay,
    monitor_video,
)
from smart_assist.detection.spatial_rules import ThreatRuleConfig
from smart_assist.detection.yolo_detector import Detection


def test_draw_preview_overlay_marks_region_and_threat_text() -> None:
    image = np.zeros((100, 200, 3), dtype=np.uint8)
    detection = Detection(0, "person", 0.9, 50, 30, 150, 90)

    output = draw_preview_overlay(
        image,
        ThreatRuleConfig(),
        [detection],
        ["Person ahead."],
    )

    assert output.shape == image.shape
    assert not np.array_equal(output, image)
    assert output[:, :, 2].max() > 0


def test_monitor_rejects_invalid_sampling_rate() -> None:
    try:
        monitor_video("missing.mp4", sample_fps=0)
    except ValueError as error:
        assert "sample_fps" in str(error)
    else:
        raise AssertionError("invalid sampling rate was accepted")


def test_speech_manager_is_optional() -> None:
    class FakeSpeechManager:
        def __init__(self) -> None:
            self.requests: list[SpeechRequest] = []

        def submit(self, request: SpeechRequest) -> bool:
            self.requests.append(request)
            return True

    speech_manager = FakeSpeechManager()
    processed = monitor_video(
        "video.mp4",
        sample_fps=2,
        max_frames=1,
        detector=_ThreatDetector(),
        speech_manager=speech_manager,
    )

    assert processed == 1
    assert speech_manager.requests == [
        SpeechRequest(
            text="Person ahead.",
            priority=AlertPriority.HIGH,
            deduplication_key="local:person:1",
        )
    ]


class _ThreatDetector:
    def detect(self, image: np.ndarray) -> list[Detection]:
        return [Detection(0, "person", 0.99, 850, 550, 1070, 1080)]


def test_preview_controls_toggle_and_request_scene() -> None:
    controls = PreviewControls()
    image = np.zeros((200, 400, 3), dtype=np.uint8)
    controls.draw(image)

    assert not controls.scene_enabled
    assert controls.handle_key(ord("a"))
    assert controls.scene_enabled
    assert controls.handle_key(ord("s"))
    assert controls.request_scene

    assert controls.handle_click(30, 170)
    assert not controls.scene_enabled
