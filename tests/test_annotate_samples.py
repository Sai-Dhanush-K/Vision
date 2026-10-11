import json
from pathlib import Path

import cv2
import pytest

from smart_assist.detection.annotate_samples import annotate_sample_frames


VIDEO_PATH = Path(__file__).parents[1] / "video.mp4"


@pytest.mark.skipif(not VIDEO_PATH.exists(), reason="Phase 1 video is not available")
def test_annotate_sample_frames_writes_images_and_detection_log(
    tmp_path: Path,
) -> None:
    records = annotate_sample_frames(VIDEO_PATH, tmp_path, [26_450])

    assert len(records) == 1
    record = records[0]
    assert record["frame_index"] == 26_450
    assert record["timestamp_ms"] > 0
    assert record["inference_ms"] > 0
    assert record["detections"]

    image = cv2.imread(record["image_path"])
    assert image is not None
    assert image.shape == (1080, 1920, 3)

    log = json.loads((tmp_path / "detections.json").read_text(encoding="utf-8"))
    assert log[0]["detections"][0]["label"]
