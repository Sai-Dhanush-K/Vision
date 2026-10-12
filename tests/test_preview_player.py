import numpy as np

from smart_assist.detection.preview_player import draw_preview_overlay, monitor_video
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
