from pathlib import Path

import numpy as np

from smart_assist.detection import (
    Detection,
    ThreatPipeline,
    ThreatRuleConfig,
    write_alert_log,
)
from smart_assist.detection.spatial_rules import NormalizedRegion


class SequenceDetector:
    def __init__(self, frames: list[list[Detection]]) -> None:
        self.frames = iter(frames)

    def detect(self, image: np.ndarray) -> list[Detection]:
        return next(self.frames)


def person_box(x1: float, y1: float, x2: float, y2: float) -> Detection:
    return Detection(0, "person", 0.9, x1, y1, x2, y2)


def test_pipeline_requires_middle_and_cooldown() -> None:
    detector = SequenceDetector(
        [
            [person_box(10, 200, 100, 900)],  # outside center
            [person_box(700, 200, 1200, 1000)],  # central and large
            [person_box(700, 200, 1200, 1000)],  # still central, cooldown
            [person_box(700, 200, 1200, 1000)],  # cooldown elapsed
        ]
    )
    pipeline = ThreatPipeline(detector=detector, cooldown_ms=5_000)
    image = np.zeros((1080, 1920, 3), dtype=np.uint8)

    assert pipeline.process_frame(image, 0) == []
    assert len(pipeline.process_frame(image, 1_000)) == 1
    assert pipeline.process_frame(image, 4_000) == []
    assert len(pipeline.process_frame(image, 6_000)) == 1


def test_small_center_detection_does_not_alert() -> None:
    detector = SequenceDetector([[person_box(920, 450, 1000, 530)]])
    pipeline = ThreatPipeline(detector=detector)
    image = np.zeros((1080, 1920, 3), dtype=np.uint8)

    assert pipeline.process_frame(image, 1_000) == []


def test_duplicate_candidates_same_class_emit_one_alert() -> None:
    detector = SequenceDetector(
        [[
            person_box(700, 200, 1200, 1000),
            person_box(750, 250, 1100, 950),
        ]]
    )
    pipeline = ThreatPipeline(detector=detector)
    image = np.zeros((1080, 1920, 3), dtype=np.uint8)

    assert len(pipeline.process_frame(image, 1_000)) == 1


def test_two_distinct_people_emit_two_alerts() -> None:
    detector = SequenceDetector(
        [[
            person_box(700, 200, 950, 1000),
            person_box(1000, 200, 1250, 1000),
        ]]
    )
    pipeline = ThreatPipeline(detector=detector)
    image = np.zeros((1080, 1920, 3), dtype=np.uint8)

    alerts = pipeline.process_frame(image, 1_000)

    assert len(alerts) == 2
    assert {alert.candidate.detection.track_id for alert in alerts} == {1, 2}


def test_custom_middle_region_is_used_and_alert_log_is_serializable(
    tmp_path: Path,
) -> None:
    detector = SequenceDetector([[person_box(100, 200, 500, 900)]])
    rules = ThreatRuleConfig(
        region=NormalizedRegion(left=0.0, top=0.0, right=0.4, bottom=1.0),
        min_height_ratio=0.1,
        min_area_ratio=0.01,
    )
    pipeline = ThreatPipeline(detector=detector, rules=rules)
    image = np.zeros((1000, 1000, 3), dtype=np.uint8)

    alerts = pipeline.process_frame(image, 1_000)
    log_path = tmp_path / "alerts.json"
    write_alert_log(alerts, log_path)

    assert len(alerts) == 1
    assert "Person ahead." in log_path.read_text(encoding="utf-8")
