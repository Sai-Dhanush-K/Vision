"""Local object detection components."""

from .yolo_detector import Detection, YoloDetector
from .spatial_rules import NormalizedRegion, ThreatCandidate, ThreatRuleConfig, find_threats
from .threat_events import ThreatAlert, ThreatEventState

__all__ = [
    "Detection",
    "NormalizedRegion",
    "ThreatCandidate",
    "ThreatRuleConfig",
    "ThreatAlert",
    "ThreatEventState",
    "YoloDetector",
    "find_threats",
]
