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
        self._last_alert_ms: dict[int | str, float] = {}
        self._active_keys: set[int | str] = set()

    def update(
        self,
        candidates: list[ThreatCandidate],
        timestamp_ms: float,
    ) -> list[ThreatAlert]:
        """Return only newly eligible alerts for the current source timestamp."""

        if timestamp_ms < 0:
            raise ValueError("timestamp_ms must not be negative")

        current_keys = {
            candidate.detection.track_id or candidate.detection.label
            for candidate in candidates
        }
        self._active_keys.intersection_update(current_keys)
        alerts: list[ThreatAlert] = []
        emitted_keys: set[int | str] = set()

        for candidate in candidates:
            label = candidate.alert_label
            key = candidate.detection.track_id or label
            if key in emitted_keys:
                continue
            last_alert_ms = self._last_alert_ms.get(key)
            is_new = key not in self._active_keys
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
                self._last_alert_ms[key] = timestamp_ms
                emitted_keys.add(key)

        self._active_keys.update(current_keys)
        return alerts
