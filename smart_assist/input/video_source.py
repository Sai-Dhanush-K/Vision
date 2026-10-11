"""OpenCV input for prerecorded video files."""

from dataclasses import dataclass
from pathlib import Path
from types import TracebackType
from typing import Iterator, Optional, Type

import cv2
import numpy as np


@dataclass(frozen=True)
class Frame:
    """A decoded video frame and its source position."""

    index: int
    timestamp_ms: float
    image: np.ndarray


@dataclass(frozen=True)
class VideoMetadata:
    """Metadata reported by OpenCV for a video file."""

    fps: float
    frame_count: int
    width: int
    height: int

    @property
    def duration_seconds(self) -> Optional[float]:
        """Return the estimated duration when FPS is available."""

        if self.fps <= 0:
            return None
        return self.frame_count / self.fps


class VideoFileSource:
    """Read a prerecorded video sequentially while preserving source timestamps."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self._capture = cv2.VideoCapture(str(self.path))
        if not self._capture.isOpened():
            self._capture.release()
            raise ValueError(f"Could not open video file: {self.path}")

        self.metadata = VideoMetadata(
            fps=self._capture.get(cv2.CAP_PROP_FPS),
            frame_count=int(self._capture.get(cv2.CAP_PROP_FRAME_COUNT)),
            width=int(self._capture.get(cv2.CAP_PROP_FRAME_WIDTH)),
            height=int(self._capture.get(cv2.CAP_PROP_FRAME_HEIGHT)),
        )
        self._next_index = 0
        self._closed = False

    def __iter__(self) -> Iterator[Frame]:
        """Yield decoded frames until the source is exhausted."""

        while True:
            frame = self.read()
            if frame is None:
                return
            yield frame

    def read(self) -> Optional[Frame]:
        """Read the next frame, or return None at end of file."""

        if self._closed:
            raise RuntimeError("Cannot read from a closed video source")

        ok, image = self._capture.read()
        if not ok or image is None:
            return None

        frame = Frame(
            index=self._next_index,
            timestamp_ms=self._capture.get(cv2.CAP_PROP_POS_MSEC),
            image=image,
        )
        self._next_index += 1
        return frame

    def seek(self, index: int) -> None:
        """Position the next read at a zero-based frame index."""

        if self._closed:
            raise RuntimeError("Cannot seek a closed video source")
        if index < 0:
            raise ValueError("frame index must not be negative")
        if not self._capture.set(cv2.CAP_PROP_POS_FRAMES, index):
            raise ValueError(f"Could not seek to frame {index}")
        self._next_index = index

    def close(self) -> None:
        """Release the OpenCV capture resource."""

        if not self._closed:
            self._capture.release()
            self._closed = True

    def __enter__(self) -> "VideoFileSource":
        return self

    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_value: Optional[BaseException],
        traceback: Optional[TracebackType],
    ) -> None:
        self.close()
