from smart_assist.detection.tracker import IoUTracker
from smart_assist.detection.yolo_detector import Detection


def person(x1: float, y1: float, x2: float, y2: float) -> Detection:
    return Detection(0, "person", 0.9, x1, y1, x2, y2)


def test_overlapping_person_keeps_track_id() -> None:
    tracker = IoUTracker(min_iou=0.2)
    first = tracker.update([person(0, 0, 100, 200)], 0)
    second = tracker.update([person(5, 5, 105, 205)], 500)

    assert first[0].track_id == second[0].track_id


def test_new_non_overlapping_person_gets_new_track_id() -> None:
    tracker = IoUTracker(min_iou=0.2)
    first = tracker.update([person(0, 0, 100, 200)], 0)
    second = tracker.update([person(500, 0, 600, 200)], 500)

    assert first[0].track_id != second[0].track_id
