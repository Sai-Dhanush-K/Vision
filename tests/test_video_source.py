from pathlib import Path

import pytest

from smart_assist.input import VideoFileSource


VIDEO_PATH = Path(__file__).parents[1] / "video.mp4"


@pytest.mark.skipif(not VIDEO_PATH.exists(), reason="Phase 1 video is not available")
def test_video_source_reads_frame_with_source_timestamp() -> None:
    with VideoFileSource(VIDEO_PATH) as source:
        assert source.metadata.width == 1920
        assert source.metadata.height == 1080
        assert source.metadata.fps > 0
        assert source.metadata.frame_count > 0

        frame = source.read()

    assert frame is not None
    assert frame.index == 0
    assert frame.timestamp_ms == 0
    assert frame.image.shape == (1080, 1920, 3)


def test_video_source_rejects_unreadable_file(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="Could not open video file"):
        VideoFileSource(tmp_path / "missing.mp4")
