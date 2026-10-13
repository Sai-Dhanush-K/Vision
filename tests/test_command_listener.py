import pytest

from smart_assist.voice.command_listener import VoiceCommand, parse_command


@pytest.mark.parametrize(
    ("spoken", "action"),
    [
        ("Describe the scene", "describe_scene"),
        ("what's in front of me", "describe_scene"),
        ("Turn on advanced AI help", "ai_help_on"),
        ("turn off advanced ai help please", "ai_help_off"),
        ("start listening", "voice_on"),
        ("stop listening", "voice_off"),
    ],
)
def test_parse_command_variants(spoken: str, action: str) -> None:
    assert parse_command(spoken) == VoiceCommand(action)


def test_parse_command_rejects_unrelated_speech() -> None:
    assert parse_command("tell me a joke") is None
