"""Lightweight IoU tracker for distinguishing nearby people between samples."""

from dataclasses import replace

from .yolo_detector import Detection


def _iou(first: Detection, second: Detection) -> float:
    left = max(first.x1, second.x1)
    top = max(first.y1, second.y1)
    right = min(first.x2, second.x2)
    bottom = min(first.y2, second.y2)
    intersection = max(0.0, right - left) * max(0.0, bottom - top)
    first_area = max(0.0, first.x2 - first.x1) * max(0.0, first.y2 - first.y1)
    second_area = max(0.0, second.x2 - second.x1) * max(0.0, second.y2 - second.y1)
    union = first_area + second_area - intersection
    return intersection / union if union else 0.0


class IoUTracker:
    """Assign stable IDs to same-class detections with sufficient box overlap."""

    def __init__(self, min_iou: float = 0.3, max_gap_ms: float = 2_000.0) -> None:
        if not 0.0 <= min_iou <= 1.0:
            raise ValueError("min_iou must be between 0 and 1")
        if max_gap_ms < 0:
            raise ValueError("max_gap_ms must not be negative")
        self.min_iou = min_iou
        self.max_gap_ms = max_gap_ms
        self._tracks: dict[int, tuple[Detection, float]] = {}
        self._next_id = 1

    def update(self, detections: list[Detection], timestamp_ms: float) -> list[Detection]:
        """Return detections annotated with stable track IDs."""

        if timestamp_ms < 0:
            raise ValueError("timestamp_ms must not be negative")
        active_tracks = {
            track_id: (detection, last_seen)
            for track_id, (detection, last_seen) in self._tracks.items()
            if timestamp_ms - last_seen <= self.max_gap_ms
        }
        used_tracks: set[int] = set()
        tracked: list[Detection] = []

        for detection in detections:
            duplicate_matches = [
                tracked_detection
                for tracked_detection in tracked
                if tracked_detection.label == detection.label
                and _iou(tracked_detection, detection) >= self.min_iou
            ]
            if duplicate_matches:
                tracked.append(replace(detection, track_id=duplicate_matches[0].track_id))
                continue
            matches = [
                (track_id, previous)
                for track_id, (previous, _) in active_tracks.items()
                if track_id not in used_tracks
                and previous.label == detection.label
                and _iou(previous, detection) >= self.min_iou
            ]
            if matches:
                track_id, _ = max(matches, key=lambda match: _iou(match[1], detection))
            else:
                track_id = self._next_id
                self._next_id += 1
            used_tracks.add(track_id)
            tracked_detection = replace(detection, track_id=track_id)
            tracked.append(tracked_detection)
            active_tracks[track_id] = (tracked_detection, timestamp_ms)

        self._tracks = active_tracks
        return tracked
