import pytest

from smart_assist.detection.spatial_rules import ThreatCandidate
from smart_assist.detection.threat_events import ThreatEventState
from smart_assist.detection.yolo_detector import Detection


def candidate(label: str = "person") -> ThreatCandidate:
    return ThreatCandidate(
        detection=Detection(0, label, 0.9, 700, 400, 1200, 1000),
        center_x_ratio=0.5,
        center_y_ratio=0.65,
        height_ratio=0.55,
        area_ratio=0.14,
    )


def test_first_threat_emits_one_alert() -> None:
    state = ThreatEventState(cooldown_ms=5_000)

    alerts = state.update([candidate()], timestamp_ms=1_000)

    assert len(alerts) == 1
    assert alerts[0].message == "Person ahead."


def test_continuous_threat_is_suppressed_until_cooldown() -> None:
    state = ThreatEventState(cooldown_ms=5_000)
    state.update([candidate()], timestamp_ms=1_000)

    assert state.update([candidate()], timestamp_ms=4_000) == []
    assert len(state.update([candidate()], timestamp_ms=6_000)) == 1


def test_threat_alerts_again_after_disappearing() -> None:
    state = ThreatEventState(cooldown_ms=5_000)
    state.update([candidate()], timestamp_ms=1_000)
    assert state.update([], timestamp_ms=2_000) == []

    alerts = state.update([candidate()], timestamp_ms=2_100)

    assert len(alerts) == 1


def test_different_labels_have_independent_state() -> None:
    state = ThreatEventState(cooldown_ms=5_000)
    state.update([candidate("person")], timestamp_ms=1_000)

    alerts = state.update([candidate("car")], timestamp_ms=2_000)

    assert [alert.label for alert in alerts] == ["car"]


def test_negative_timestamp_and_cooldown_are_rejected() -> None:
    with pytest.raises(ValueError, match="cooldown"):
        ThreatEventState(cooldown_ms=-1)

    state = ThreatEventState()
    with pytest.raises(ValueError, match="timestamp"):
        state.update([], timestamp_ms=-1)
