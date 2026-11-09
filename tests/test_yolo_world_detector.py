from types import SimpleNamespace

import pytest

from smart_assist.detection.yolo_world_detector import YoloWorldDetector


def test_yolo_world_detector_rejects_invalid_configuration() -> None:
    with pytest.raises(ValueError, match="confidence"):
        YoloWorldDetector(confidence=1.1)


def test_yolo_world_conversion_preserves_zero_shot_labels() -> None:
    detector = YoloWorldDetector.__new__(YoloWorldDetector)
    result = SimpleNamespace(
        boxes=SimpleNamespace(
            xyxy=SimpleNamespace(cpu=lambda: SimpleNamespace(
                tolist=lambda: [[10, 20, 100, 200]]
            )),
            cls=SimpleNamespace(cpu=lambda: SimpleNamespace(
                tolist=lambda: [1]
            )),
            conf=SimpleNamespace(cpu=lambda: SimpleNamespace(
                tolist=lambda: [0.8]
            )),
        ),
        names={1: "tree"},
    )

    detections = detector._convert_result(result)

    assert detections[0].label == "tree"
    assert detections[0].confidence == 0.8
    assert detections[0].x2 == 100
