from pathlib import Path

import cv2

from smart_assist.detection.annotate_video import annotate_video
from smart_assist.detection.yolo_detector import Detection


class FakeDetector:
    def detect(self, image) -> list[Detection]:
        return [
            Detection(
                class_id=0,
                label="person",
                confidence=0.9,
                x1=10,
                y1=10,
                x2=100,
                y2=100,
            )
        ]


def test_annotate_video_writes_bounded_output(tmp_path: Path) -> None:
    video_path = tmp_path / "input.mp4"
    writer = cv2.VideoWriter(
        str(video_path),
        cv2.VideoWriter_fourcc(*"mp4v"),
        10,
        (64, 48),
    )
    for _ in range(3):
        writer.write(255 * (cv2.UMat(48, 64, cv2.CV_8UC3).get()))
    writer.release()

    output_video = tmp_path / "annotated.mp4"
    log_path = tmp_path / "detections.json"
    summary = annotate_video(
        video_path,
        output_video,
        log_path,
        max_frames=2,
        detector=FakeDetector(),
    )

    assert summary["frames_processed"] == 2
    assert summary["average_inference_ms"] >= 0
    assert output_video.exists()
    assert log_path.exists()

    capture = cv2.VideoCapture(str(output_video))
    assert int(capture.get(cv2.CAP_PROP_FRAME_COUNT)) == 2
    capture.release()
