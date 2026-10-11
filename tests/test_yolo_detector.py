from pathlib import Path

import cv2
import pytest

from smart_assist.detection import YoloDetector
from smart_assist.input import VideoFileSource


VIDEO_PATH = Path(__file__).parents[1] / "video.mp4"


@pytest.mark.skipif(not VIDEO_PATH.exists(), reason="Phase 1 video is not available")
def test_yolo_detector_runs_cpu_inference_on_a_video_frame() -> None:
    with VideoFileSource(VIDEO_PATH) as source:
        source.seek(26_450)
        frame = source.read()

    assert frame is not None
    detector = YoloDetector()
    detections = detector.detect(frame.image)

    assert detections
    for detection in detections:
        assert detection.label
        assert 0.0 <= detection.confidence <= 1.0
        assert detection.x1 <= detection.x2
        assert detection.y1 <= detection.y2


def test_yolo_detector_rejects_invalid_confidence() -> None:
    with pytest.raises(ValueError, match="confidence"):
        YoloDetector(confidence=1.1)
