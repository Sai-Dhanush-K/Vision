import json
from pathlib import Path

import cv2
import pytest

from smart_assist.input.sample_frames import save_sample_frames


VIDEO_PATH = Path(__file__).parents[1] / "video.mp4"


@pytest.mark.skipif(not VIDEO_PATH.exists(), reason="Phase 1 video is not available")
def test_save_sample_frames_writes_images_and_manifest(tmp_path: Path) -> None:
    samples = save_sample_frames(VIDEO_PATH, tmp_path, [0, 26_450], max_width=320)

    assert [sample.index for sample in samples] == [0, 26_450]
    assert samples[0].timestamp_ms == 0
    assert all(Path(sample.path).exists() for sample in samples)

    image = cv2.imread(samples[0].path)
    assert image is not None
    assert image.shape == (180, 320, 3)

    manifest = json.loads((tmp_path / "manifest.json").read_text(encoding="utf-8"))
    assert manifest[1]["index"] == 26_450
