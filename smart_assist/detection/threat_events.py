"""Cooldown and state handling for central threat candidates."""

from dataclasses import dataclass

from .spatial_rules import ThreatCandidate


@dataclass(frozen=True)
class ThreatAlert:
    """A new alert-worthy threat event."""

    label: str
    message: str
    candidate: ThreatCandidate
    timestamp_ms: float


class ThreatEventState:
    """Suppress repeated alerts while a threat remains continuously present."""

    def __init__(self, cooldown_ms: float = 5_000.0) -> None:
        if cooldown_ms < 0:
            raise ValueError("cooldown_ms must not be negative")
        self.cooldown_ms = cooldown_ms
        self._last_alert_ms: dict[str, float] = {}
        self._active_labels: set[str] = set()

    def update(
        self,
        candidates: list[ThreatCandidate],
        timestamp_ms: float,
    ) -> list[ThreatAlert]:
        """Return only newly eligible alerts for the current source timestamp."""

        if timestamp_ms < 0:
            raise ValueError("timestamp_ms must not be negative")

        current_labels = {candidate.detection.label for candidate in candidates}
        self._active_labels.intersection_update(current_labels)
        alerts: list[ThreatAlert] = []
        emitted_labels: set[str] = set()

        for candidate in candidates:
            label = candidate.detection.label
            if label in emitted_labels:
                continue
            last_alert_ms = self._last_alert_ms.get(label)
            is_new = label not in self._active_labels
            cooldown_elapsed = (
                last_alert_ms is None
                or timestamp_ms - last_alert_ms >= self.cooldown_ms
            )
            if is_new or cooldown_elapsed:
                alerts.append(
                    ThreatAlert(
                        label=label,
                        message=f"{label.title()} ahead.",
                        candidate=candidate,
                        timestamp_ms=timestamp_ms,
                    )
                )
                self._last_alert_ms[label] = timestamp_ms
                emitted_labels.add(label)

        self._active_labels.update(current_labels)
        return alerts
