"""Priority speech scheduling for local alerts and future scene messages."""

from dataclasses import dataclass
from enum import IntEnum
import heapq
import threading
from typing import Protocol


class Speaker(Protocol):
    """Minimal speech-engine contract used by the manager."""

    def speak(self, text: str) -> None:
        """Speak one complete message, blocking until it finishes."""

    def stop(self) -> None:
        """Interrupt the current message if one is speaking."""


class AlertPriority(IntEnum):
    """Lower numeric values are more urgent."""

    CRITICAL = 0
    HIGH = 1
    NORMAL = 2
    LOW = 3


@dataclass(frozen=True)
class SpeechRequest:
    """One message submitted to the central speech manager."""

    text: str
    priority: AlertPriority
    deduplication_key: str


class Pyttsx3Speaker:
    """Local pyttsx3 adapter, created only when speech is first used."""

    def __init__(self) -> None:
        import pyttsx3

        self._engine = pyttsx3.init()

    def speak(self, text: str) -> None:
        self._engine.say(text)
        self._engine.runAndWait()

    def stop(self) -> None:
        self._engine.stop()


class SpeechManager:
    """Serialize speech and let critical messages interrupt lower priorities."""

    def __init__(self, speaker: Speaker) -> None:
        self._speaker = speaker
        self._condition = threading.Condition()
        self._queue: list[tuple[int, int, SpeechRequest]] = []
        self._sequence = 0
        self._pending_keys: set[str] = set()
        self._active_key: str | None = None
        self._closed = False
        self._worker = threading.Thread(
            target=self._run,
            name="speech-manager",
            daemon=True,
        )
        self._worker.start()

    def submit(self, request: SpeechRequest) -> bool:
        """Queue a non-duplicate request and return whether it was accepted."""

        if not request.text.strip():
            raise ValueError("speech text must not be empty")
        with self._condition:
            if self._closed:
                raise RuntimeError("speech manager is closed")
            if (
                request.deduplication_key in self._pending_keys
                or request.deduplication_key == self._active_key
            ):
                return False
            if request.priority == AlertPriority.CRITICAL:
                self._speaker.stop()
            self._sequence += 1
            heapq.heappush(
                self._queue,
                (int(request.priority), self._sequence, request),
            )
            self._pending_keys.add(request.deduplication_key)
            self._condition.notify()
            return True

    def close(self) -> None:
        """Stop accepting requests and wait for the worker to finish."""

        with self._condition:
            if self._closed:
                return
            self._closed = True
            self._speaker.stop()
            self._condition.notify_all()
        self._worker.join(timeout=5)

    def _run(self) -> None:
        while True:
            with self._condition:
                while not self._queue and not self._closed:
                    self._condition.wait()
                if self._closed and not self._queue:
                    return
                _, _, request = heapq.heappop(self._queue)
                self._pending_keys.discard(request.deduplication_key)
                self._active_key = request.deduplication_key
            try:
                self._speaker.speak(request.text)
            finally:
                with self._condition:
                    if self._active_key == request.deduplication_key:
                        self._active_key = None
