"""CPU-friendly YOLO inference for individual video frames."""

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
from ultralytics import YOLO


@dataclass(frozen=True)
class Detection:
    """One object detected in a frame."""

    class_id: int
    label: str
    confidence: float
    x1: float
    y1: float
    x2: float
    y2: float
    track_id: int | None = None


class YoloDetector:
    """Run a lightweight pretrained YOLO model on CPU."""

    def __init__(
        self,
        model_path: str | Path = "yolov8n.pt",
        confidence: float = 0.25,
    ) -> None:
        if not 0.0 <= confidence <= 1.0:
            raise ValueError("confidence must be between 0 and 1")

        self.model = YOLO(str(model_path))
        self.confidence = confidence

    def detect(self, image: np.ndarray) -> list[Detection]:
        """Return detections for one BGR or RGB image."""

        if image.ndim != 3 or image.shape[2] != 3:
            raise ValueError("image must have shape (height, width, 3)")

        results = self.model.predict(
            source=image,
            conf=self.confidence,
            device="cpu",
            verbose=False,
        )
        if not results:
            return []
        return self._convert_result(results[0])

    def _convert_result(self, result: Any) -> list[Detection]:
        boxes = result.boxes
        names = result.names
        detections: list[Detection] = []

        for box, class_id, confidence in zip(
            boxes.xyxy.cpu().tolist(),
            boxes.cls.cpu().tolist(),
            boxes.conf.cpu().tolist(),
        ):
            numeric_class_id = int(class_id)
            label = names[numeric_class_id]
            detections.append(
                Detection(
                    class_id=numeric_class_id,
                    label=str(label),
                    confidence=float(confidence),
                    x1=float(box[0]),
                    y1=float(box[1]),
                    x2=float(box[2]),
                    y2=float(box[3]),
                )
            )
        return detections
