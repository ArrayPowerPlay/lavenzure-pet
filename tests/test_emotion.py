"""Tests for agent.emotion.split_emotion (the leading emotion tag of a reply)."""
import pytest

from agent.emotion import split_emotion


@pytest.mark.parametrize(("reply", "emotion", "text"), [
    ("[happy] Hello there!", "happy", "Hello there!"),
    ("[Scared]\nOh no, 98% CPU!", "scared", "Oh no, 98% CPU!"),
    ("**[angry]** Hmph.", "angry", "Hmph."),
    ("  [ thinking ]  Let me see...", "thinking", "Let me see..."),
    ("[yuck] Eww, raw broccoli.", "yuck", "Eww, raw broccoli."),
    ("[other] Just a fact.", None, "Just a fact."),
    ("No tag at all.", None, "No tag at all."),
    ("[sleepy] Unknown tag stays.", None, "[sleepy] Unknown tag stays."),
    ("Text with [happy] in the middle", None, "Text with [happy] in the middle"),
])
def test_split_emotion(reply, emotion, text):
    """The tag is recognised only at the start and removed from the shown text."""
    assert split_emotion(reply) == (emotion, text)


def test_markdown_link_is_not_a_tag():
    """A reply that starts with a markdown link keeps it (``[text](url)`` is not a tag)."""
    emotion, text = split_emotion("[docs](https://example.com) say hi")
    assert emotion is None and text.startswith("[docs](")


def test_yuck_is_offered_to_the_model():
    """The AI may pick the ``yuck`` face (round 12), and main maps it to the yuck mood."""
    from agent.emotion import EMOTION_INSTRUCTIONS, EMOTIONS

    assert "yuck" in EMOTIONS and "[yuck]" in EMOTION_INSTRUCTIONS


def test_cool_is_offered_to_the_model():
    """The AI may pick the ``cool`` face (sunglasses + smirk, round 21)."""
    from agent.emotion import EMOTION_INSTRUCTIONS, EMOTIONS
    from main import EMOTION_MOODS
    from overlay.face import Mood

    assert "cool" in EMOTIONS and "[cool]" in EMOTION_INSTRUCTIONS
    assert EMOTION_MOODS["cool"] == Mood.COOL


@pytest.mark.parametrize(("partial", "expected"), [
    ("", (None, "", False)),
    ("[", (None, "", False)),
    ("**[hap", (None, "", False)),
    ("[happy", (None, "", False)),
    ("[happy] Hel", ("happy", "Hel", True)),
    ("[other] Hi", (None, "Hi", True)),
    ("Hello", (None, "Hello", True)),
    ("[docs](", (None, "[docs](", True)),
])
def test_split_emotion_partial(partial, expected):
    """A half-received tag is held back; anything else is shown as soon as it arrives."""
    from agent.emotion import split_emotion_partial

    assert split_emotion_partial(partial) == expected
