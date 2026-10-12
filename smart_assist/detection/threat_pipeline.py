"""Compose YOLO detection, central-region rules, and cooldown events."""

from dataclasses import asdict
import json
from pathlib import Path
from typing import Any

import numpy as np

from ..input import VideoFileSource
from .spatial_rules import ThreatRuleConfig, find_threats
from .threat_events import ThreatAlert, ThreatEventState
from .yolo_detector import YoloDetector


class ThreatPipeline:
    """Turn sequential frames into central, proximity-filtered alert events."""

    def __init__(
        self,
        detector: Any | None = None,
        rules: ThreatRuleConfig | None = None,
        cooldown_ms: float = 5_000.0,
    ) -> None:
        self.detector = detector or YoloDetector()
        self.rules = rules or ThreatRuleConfig()
        self.event_state = ThreatEventState(cooldown_ms=cooldown_ms)

    def process_frame(
        self,
        image: np.ndarray,
        timestamp_ms: float,
    ) -> list[ThreatAlert]:
        """Process one frame using its source timestamp."""

        detections = self.detector.detect(image)
        candidates = find_threats(
            detections,
            image_width=image.shape[1],
            image_height=image.shape[0],
            config=self.rules,
        )
        return self.event_state.update(candidates, timestamp_ms)

    def process_video(
        self,
        video_path: str | Path,
        max_frames: int,
    ) -> list[ThreatAlert]:
        """Process at most ``max_frames`` sequential frames from a video."""

        if max_frames <= 0:
            raise ValueError("max_frames must be positive")

        alerts: list[ThreatAlert] = []
        with VideoFileSource(video_path) as source:
            for _ in range(max_frames):
                frame = source.read()
                if frame is None:
                    break
                alerts.extend(self.process_frame(frame.image, frame.timestamp_ms))
        return alerts


def write_alert_log(alerts: list[ThreatAlert], path: str | Path) -> None:
    """Write structured alert events without serializing model objects."""

    records = []
    for alert in alerts:
        record = {
            "label": alert.label,
            "message": alert.message,
            "timestamp_ms": alert.timestamp_ms,
            "candidate": asdict(alert.candidate),
        }
        records.append(record)
    Path(path).write_text(json.dumps(records, indent=2) + "\n", encoding="utf-8")
