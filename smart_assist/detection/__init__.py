"""Local object detection components."""

from .yolo_detector import Detection, YoloDetector
from .spatial_rules import NormalizedRegion, ThreatCandidate, ThreatRuleConfig, find_threats

__all__ = [
    "Detection",
    "NormalizedRegion",
    "ThreatCandidate",
    "ThreatRuleConfig",
    "YoloDetector",
    "find_threats",
]
