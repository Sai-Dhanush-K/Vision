import threading
import time

import pytest

from smart_assist.alerts import AlertPriority, SpeechManager, SpeechRequest


class FakeSpeaker:
    def __init__(self) -> None:
        self.started: list[str] = []
        self.finished: list[str] = []
        self.stop_event = threading.Event()
        self.release_event = threading.Event()

    def speak(self, text: str) -> None:
        self.started.append(text)
        if text == "scene":
            self.release_event.wait(timeout=2)
        if not self.stop_event.is_set():
            self.finished.append(text)
        self.stop_event.clear()

    def stop(self) -> None:
        self.stop_event.set()
        self.release_event.set()


def request(text: str, priority: AlertPriority, key: str | None = None) -> SpeechRequest:
    return SpeechRequest(text, priority, key or text)


def wait_for(predicate) -> None:
    deadline = time.time() + 2
    while time.time() < deadline:
        if predicate():
            return
        time.sleep(0.01)
    raise AssertionError("condition was not reached")


def test_critical_request_interrupts_scene_and_speaks_next() -> None:
    speaker = FakeSpeaker()
    manager = SpeechManager(speaker)
    try:
        assert manager.submit(request("scene", AlertPriority.NORMAL))
        wait_for(lambda: speaker.started == ["scene"])
        assert manager.submit(request("Person ahead.", AlertPriority.CRITICAL, "person-1"))
        wait_for(lambda: "Person ahead." in speaker.started)
    finally:
        manager.close()

    assert speaker.started[:2] == ["scene", "Person ahead."]


def test_duplicate_keys_are_suppressed() -> None:
    speaker = FakeSpeaker()
    manager = SpeechManager(speaker)
    try:
        assert manager.submit(request("Car ahead.", AlertPriority.HIGH, "car-1"))
        assert not manager.submit(request("Car ahead.", AlertPriority.HIGH, "car-1"))
    finally:
        manager.close()


def test_empty_text_and_closed_manager_are_rejected() -> None:
    speaker = FakeSpeaker()
    manager = SpeechManager(speaker)
    with pytest.raises(ValueError, match="empty"):
        manager.submit(request("  ", AlertPriority.NORMAL))
    manager.close()
    with pytest.raises(RuntimeError, match="closed"):
        manager.submit(request("hello", AlertPriority.NORMAL))
