"""CPU YOLO-World inference with configurable zero-shot class prompts."""

from pathlib import Path
from typing import Any, Iterable

import numpy as np
from ultralytics import YOLOWorld

from .yolo_detector import Detection


DEFAULT_WORLD_LABELS = (
    "person",
    "car",
    "bus",
    "truck",
    "motorcycle",
    "bicycle",
    "tree",
    "pole",
    "traffic light",
    "stairs",
    "curb",
    "construction barrier",
    "tree trunk",
    "electric pole",
    "streetlight pole",
)


class YoloWorldDetector:
    """Run YOLO-World on CPU using user-configured zero-shot labels."""

    def __init__(
        self,
        model_path: str | Path = "yolov8s-world.pt",
        labels: Iterable[str] = DEFAULT_WORLD_LABELS,
        confidence: float = 0.25,
    ) -> None:
        if not 0.0 <= confidence <= 1.0:
            raise ValueError("confidence must be between 0 and 1")
        normalized_labels = tuple(
            label.strip() for label in labels if label.strip()
        )
        if not normalized_labels:
            raise ValueError("labels must not be empty")

        self.model = YOLOWorld(str(model_path))
        self.model.set_classes(list(normalized_labels))
        self.labels = normalized_labels
        self.confidence = confidence

    def detect(self, image: np.ndarray) -> list[Detection]:
        """Return zero-shot detections for one BGR or RGB image."""

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
            detections.append(
                Detection(
                    class_id=numeric_class_id,
                    label=str(names[numeric_class_id]),
                    confidence=float(confidence),
                    x1=float(box[0]),
                    y1=float(box[1]),
                    x2=float(box[2]),
                    y2=float(box[3]),
                )
            )
        return detections
