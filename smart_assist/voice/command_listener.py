"""Voice commands for scene descriptions and optional AI assistance."""

from dataclasses import dataclass
import threading
from typing import Callable


@dataclass(frozen=True)
class VoiceCommand:
    """Normalized action produced from spoken text."""

    action: str


def parse_command(text: str) -> VoiceCommand | None:
    """Map common spoken phrases to a small, deterministic command set."""

    normalized = " ".join(text.lower().strip().split())
    if not normalized:
        return None
    if any(phrase in normalized for phrase in (
        "describe the scene",
        "describe scene",
        "what is in front of me",
        "what's in front of me",
        "what is ahead of me",
        "describe my surroundings",
    )):
        return VoiceCommand("describe_scene")
    if any(phrase in normalized for phrase in (
        "turn on advanced ai help",
        "turn on advanced ai",
        "enable advanced ai help",
        "enable ai help",
    )):
        return VoiceCommand("ai_help_on")
    if any(phrase in normalized for phrase in (
        "turn off advanced ai help",
        "turn off advanced ai",
        "disable advanced ai help",
        "disable ai help",
    )):
        return VoiceCommand("ai_help_off")
    if any(phrase in normalized for phrase in (
        "turn on voice commands",
        "enable voice commands",
        "start listening",
    )):
        return VoiceCommand("voice_on")
    if any(phrase in normalized for phrase in (
        "turn off voice commands",
        "disable voice commands",
        "stop listening",
    )):
        return VoiceCommand("voice_off")
    return None


class VoiceCommandListener:
    """Optional microphone listener that emits parsed commands in a worker."""

    def __init__(
        self,
        on_command: Callable[[VoiceCommand], None],
        on_error: Callable[[Exception], None] | None = None,
    ) -> None:
        self._on_command = on_command
        self._on_error = on_error
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        """Start microphone listening, importing audio dependencies lazily."""

        if self._thread is not None and self._thread.is_alive():
            return
        self._thread = threading.Thread(
            target=self._run,
            name="voice-command-listener",
            daemon=True,
        )
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=2)

    def _run(self) -> None:
        try:
            import speech_recognition as sr

            recognizer = sr.Recognizer()
            with sr.Microphone() as microphone:
                recognizer.adjust_for_ambient_noise(microphone, duration=0.5)
                while not self._stop_event.is_set():
                    try:
                        audio = recognizer.listen(
                            microphone, timeout=1, phrase_time_limit=4
                        )
                        text = recognizer.recognize_google(audio)
                    except (sr.WaitTimeoutError, sr.UnknownValueError):
                        continue
                    command = parse_command(text)
                    if command is not None:
                        self._on_command(command)
        except Exception as error:
            if self._on_error is not None:
                self._on_error(error)
