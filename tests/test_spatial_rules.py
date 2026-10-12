import pytest

from smart_assist.detection.spatial_rules import (
    NormalizedRegion,
    ThreatRuleConfig,
    find_threats,
)
from smart_assist.detection.yolo_detector import Detection


def detection(label: str, x1: float, y1: float, x2: float, y2: float) -> Detection:
    return Detection(0, label, 0.9, x1, y1, x2, y2)


def test_large_central_person_is_a_threat() -> None:
    threats = find_threats(
        [detection("person", 700, 400, 1200, 1000)],
        image_width=1920,
        image_height=1080,
    )

    assert len(threats) == 1
    assert threats[0].detection.label == "person"
    assert threats[0].height_ratio > 0.5


def test_small_far_person_in_center_is_not_a_threat() -> None:
    threats = find_threats(
        [detection("person", 920, 450, 1000, 530)],
        image_width=1920,
        image_height=1080,
    )

    assert threats == []


def test_default_rule_requires_person_to_fill_half_center_strip_and_bottom_half() -> None:
    assert find_threats(
        [detection("person", 900, 550, 1100, 900)],
        image_width=1920,
        image_height=1080,
    )
    assert find_threats(
        [detection("person", 900, 100, 1100, 500)],
        image_width=1920,
        image_height=1080,
    ) == []


def test_large_detection_outside_center_is_not_a_threat() -> None:
    threats = find_threats(
        [detection("car", 50, 400, 700, 1000)],
        image_width=1920,
        image_height=1080,
    )

    assert threats == []


def test_irrelevant_label_is_ignored() -> None:
    threats = find_threats(
        [detection("handbag", 700, 400, 1200, 1000)],
        image_width=1920,
        image_height=1080,
    )

    assert threats == []


def test_geometry_and_thresholds_are_customizable() -> None:
    config = ThreatRuleConfig(
        region=NormalizedRegion(left=0.0, top=0.0, right=0.5, bottom=1.0),
        relevant_labels=frozenset({"person"}),
        min_height_ratio=0.05,
        min_area_ratio=0.005,
    )
    threats = find_threats(
        [detection("person", 100, 100, 300, 250)],
        image_width=1000,
        image_height=1000,
        config=config,
    )

    assert len(threats) == 1


def test_invalid_image_dimensions_are_rejected() -> None:
    with pytest.raises(ValueError, match="dimensions"):
        find_threats([], image_width=0, image_height=1080)
