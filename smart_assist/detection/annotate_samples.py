"""Run YOLO on selected video frames and save visual and JSON results."""

import argparse
from dataclasses import asdict
import json
from pathlib import Path
import time

import cv2

from .yolo_detector import Detection, YoloDetector
from ..input import VideoFileSource


def _draw_detection(image, detection: Detection) -> None:
    """Draw one detection and its confidence on an image in place."""

    top_left = (round(detection.x1), round(detection.y1))
    bottom_right = (round(detection.x2), round(detection.y2))
    cv2.rectangle(image, top_left, bottom_right, (0, 255, 0), 2)
    label = f"{detection.label} {detection.confidence:.2f}"
    cv2.putText(
        image,
        label,
        (top_left[0], max(top_left[1] - 8, 20)),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.7,
        (0, 255, 0),
        2,
        cv2.LINE_AA,
    )


def annotate_sample_frames(
    video_path: str | Path,
    output_dir: str | Path,
    frame_indices: list[int],
    detector: YoloDetector | None = None,
) -> list[dict]:
    """Save annotated frames and a JSON detection log for selected indices."""

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    detector = detector or YoloDetector()
    records: list[dict] = []

    with VideoFileSource(video_path) as source:
        for index in frame_indices:
            source.seek(index)
            frame = source.read()
            if frame is None or frame.index != index:
                raise ValueError(f"Could not read requested frame {index}")

            start = time.perf_counter()
            detections = detector.detect(frame.image)
            inference_ms = (time.perf_counter() - start) * 1000
            annotated = frame.image.copy()
            for detection in detections:
                _draw_detection(annotated, detection)

            image_path = output_path / f"annotated_{index:06d}.jpg"
            if not cv2.imwrite(str(image_path), annotated):
                raise OSError(f"Could not write annotated frame: {image_path}")
            records.append(
                {
                    "frame_index": frame.index,
                    "timestamp_ms": frame.timestamp_ms,
                    "inference_ms": inference_ms,
                    "image_path": str(image_path),
                    "detections": [asdict(detection) for detection in detections],
                }
            )

    log_path = output_path / "detections.json"
    log_path.write_text(json.dumps(records, indent=2) + "\n", encoding="utf-8")
    return records


def main() -> None:
    """Run YOLO annotation from the command line."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("video_path", type=Path)
    parser.add_argument("output_dir", type=Path)
    parser.add_argument(
        "--frame-index",
        type=int,
        action="append",
        dest="frame_indices",
        required=True,
    )
    args = parser.parse_args()
    records = annotate_sample_frames(
        args.video_path,
        args.output_dir,
        args.frame_indices,
    )
    print(json.dumps(records, indent=2))


if __name__ == "__main__":
    main()
