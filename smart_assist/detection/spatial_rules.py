"""Configurable central-region and proximity rules for local detections."""

from dataclasses import dataclass, field
from typing import Iterable

from .yolo_detector import Detection


@dataclass(frozen=True)
class NormalizedRegion:
    """A rectangular region expressed as fractions of image width and height."""

    left: float = 0.40
    top: float = 0.50
    right: float = 0.60
    bottom: float = 1.0

    def __post_init__(self) -> None:
        if not 0.0 <= self.left < self.right <= 1.0:
            raise ValueError("region horizontal bounds must satisfy 0 <= left < right <= 1")
        if not 0.0 <= self.top < self.bottom <= 1.0:
            raise ValueError("region vertical bounds must satisfy 0 <= top < bottom <= 1")

    def contains(self, x: float, y: float) -> bool:
        """Return whether a normalized point lies inside the region."""

        return self.left <= x <= self.right and self.top <= y <= self.bottom


@dataclass(frozen=True)
class ThreatRuleConfig:
    """Thresholds controlling when a relevant detection becomes a threat."""

    region: NormalizedRegion = field(default_factory=NormalizedRegion)
    relevant_labels: frozenset[str] = frozenset(
        {"person", "car", "bus", "truck", "motorcycle", "bicycle"}
    )
    vehicle_labels: frozenset[str] = frozenset(
        {"car", "bus", "truck", "motorcycle", "bicycle"}
    )
    include_obstacles: bool = True
    min_width_ratio: float = 0.10
    min_height_ratio: float = 0.15
    min_area_ratio: float = 0.02

    def __post_init__(self) -> None:
        if not 0.0 < self.min_width_ratio <= 1.0:
            raise ValueError("min_width_ratio must be greater than 0 and at most 1")
        if not 0.0 < self.min_height_ratio <= 1.0:
            raise ValueError("min_height_ratio must be greater than 0 and at most 1")
        if not 0.0 < self.min_area_ratio <= 1.0:
            raise ValueError("min_area_ratio must be greater than 0 and at most 1")
        if not self.relevant_labels:
            raise ValueError("relevant_labels must not be empty")


@dataclass(frozen=True)
class ThreatCandidate:
    """A detection that passes the configured central-region threat rules."""

    detection: Detection
    alert_label: str
    center_x_ratio: float
    center_y_ratio: float
    height_ratio: float
    area_ratio: float


def find_threats(
    detections: Iterable[Detection],
    image_width: int,
    image_height: int,
    config: ThreatRuleConfig | None = None,
) -> list[ThreatCandidate]:
    """Return relevant, central, sufficiently large detections.

    A detection must satisfy all three conditions:
    1. Its class is configured as relevant or is treated as an obstacle.
    2. Its bounding-box center is inside the central region.
    3. Its normalized height and area both meet the proximity thresholds.

    The size checks intentionally reject small distant people or vehicles even
    when their center happens to fall in the central region.
    """

    if image_width <= 0 or image_height <= 0:
        raise ValueError("image dimensions must be positive")
    config = config or ThreatRuleConfig()
    threats: list[ThreatCandidate] = []

    for detection in detections:
        if detection.label in config.relevant_labels:
            alert_label = (
                "vehicle" if detection.label in config.vehicle_labels else "person"
            )
        elif config.include_obstacles:
            alert_label = "obstacle"
        else:
            continue

        width = max(0.0, detection.x2 - detection.x1)
        height = max(0.0, detection.y2 - detection.y1)
        center_x = (detection.x1 + detection.x2) / 2 / image_width
        center_y = (detection.y1 + detection.y2) / 2 / image_height
        height_ratio = height / image_height
        width_ratio = width / image_width
        area_ratio = width * height / (image_width * image_height)

        if not config.region.contains(center_x, center_y):
            continue
        if width_ratio < config.min_width_ratio:
            continue
        if height_ratio < config.min_height_ratio:
            continue
        if area_ratio < config.min_area_ratio:
            continue

        threats.append(
            ThreatCandidate(
                detection=detection,
                alert_label=alert_label,
                center_x_ratio=center_x,
                center_y_ratio=center_y,
                height_ratio=height_ratio,
                area_ratio=area_ratio,
            )
        )

    return threats
