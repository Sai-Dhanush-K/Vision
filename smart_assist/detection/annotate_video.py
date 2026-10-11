"""Create a bounded YOLO-annotated video and structured detection log."""

import argparse
from dataclasses import asdict
import json
from pathlib import Path
import time
from typing import Any

import cv2

from ..input import VideoFileSource
from .annotate_samples import _draw_detection
from .yolo_detector import Detection, YoloDetector


def annotate_video(
    video_path: str | Path,
    output_video: str | Path,
    log_path: str | Path,
    max_frames: int,
    detector: Any | None = None,
) -> dict[str, Any]:
    """Annotate at most ``max_frames`` sequential frames and write a log."""

    if max_frames <= 0:
        raise ValueError("max_frames must be positive")

    detector = detector or YoloDetector()
    timings: list[float] = []
    records: list[dict[str, Any]] = []

    with VideoFileSource(video_path) as source:
        metadata = source.metadata
        writer = cv2.VideoWriter(
            str(output_video),
            cv2.VideoWriter_fourcc(*"mp4v"),
            metadata.fps,
            (metadata.width, metadata.height),
        )
        if not writer.isOpened():
            raise OSError(f"Could not open output video: {output_video}")

        try:
            for _ in range(max_frames):
                frame = source.read()
                if frame is None:
                    break

                start = time.perf_counter()
                detections: list[Detection] = detector.detect(frame.image)
                inference_ms = (time.perf_counter() - start) * 1000
                timings.append(inference_ms)
                annotated = frame.image.copy()
                for detection in detections:
                    _draw_detection(annotated, detection)
                writer.write(annotated)
                records.append(
                    {
                        "frame_index": frame.index,
                        "timestamp_ms": frame.timestamp_ms,
                        "inference_ms": inference_ms,
                        "detections": [asdict(detection) for detection in detections],
                    }
                )
        finally:
            writer.release()

    summary = {
        "video_path": str(video_path),
        "output_video": str(output_video),
        "frames_processed": len(records),
        "source_fps": metadata.fps,
        "average_inference_ms": sum(timings) / len(timings) if timings else 0.0,
        "minimum_inference_ms": min(timings) if timings else 0.0,
        "maximum_inference_ms": max(timings) if timings else 0.0,
        "frames": records,
    }
    Path(log_path).write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    return summary


def main() -> None:
    """Run bounded YOLO video annotation from the command line."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("video_path", type=Path)
    parser.add_argument("output_video", type=Path)
    parser.add_argument("log_path", type=Path)
    parser.add_argument("--max-frames", type=int, default=30)
    args = parser.parse_args()
    summary = annotate_video(
        args.video_path,
        args.output_video,
        args.log_path,
        args.max_frames,
    )
    print(json.dumps({key: value for key, value in summary.items() if key != "frames"}, indent=2))


if __name__ == "__main__":
    main()
