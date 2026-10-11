"""Save representative frames from a video for Phase 1 verification."""

import argparse
from dataclasses import asdict, dataclass
import json
from pathlib import Path
from typing import Iterable

import cv2

from .video_source import VideoFileSource


@dataclass(frozen=True)
class SavedSample:
    """Details about one saved sample frame."""

    index: int
    timestamp_ms: float
    path: str


def save_sample_frames(
    video_path: str | Path,
    output_dir: str | Path,
    frame_indices: Iterable[int],
    max_width: int = 640,
) -> list[SavedSample]:
    """Save selected frames and a JSON manifest containing source timestamps."""

    if max_width <= 0:
        raise ValueError("max_width must be positive")

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    saved: list[SavedSample] = []

    with VideoFileSource(video_path) as source:
        for index in frame_indices:
            if index < 0:
                raise ValueError("frame indices must not be negative")

            source.seek(index)
            frame = source.read()
            if frame is None or frame.index != index:
                raise ValueError(f"Could not read requested frame {index}")

            image = frame.image
            if image.shape[1] > max_width:
                scale = max_width / image.shape[1]
                image = cv2.resize(
                    image,
                    (max_width, round(image.shape[0] * scale)),
                    interpolation=cv2.INTER_AREA,
                )

            image_path = output_path / f"frame_{index:06d}.jpg"
            if not cv2.imwrite(str(image_path), image):
                raise OSError(f"Could not write sample frame: {image_path}")
            saved.append(
                SavedSample(
                    index=index,
                    timestamp_ms=frame.timestamp_ms,
                    path=str(image_path),
                )
            )

    manifest_path = output_path / "manifest.json"
    manifest_path.write_text(
        json.dumps([asdict(sample) for sample in saved], indent=2) + "\n",
        encoding="utf-8",
    )
    return saved


def main() -> None:
    """Run sample extraction from the command line."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("video_path", type=Path)
    parser.add_argument("output_dir", type=Path)
    parser.add_argument(
        "--frame-index",
        type=int,
        action="append",
        dest="frame_indices",
        required=True,
        help="Frame index to save; repeat this option for multiple frames.",
    )
    args = parser.parse_args()
    saved = save_sample_frames(
        args.video_path,
        args.output_dir,
        args.frame_indices,
    )
    print(json.dumps([asdict(sample) for sample in saved], indent=2))


if __name__ == "__main__":
    main()
