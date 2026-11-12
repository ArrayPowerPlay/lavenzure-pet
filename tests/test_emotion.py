"""Tests for agent.emotion.split_emotion (the leading emotion tag of a reply)."""
import pytest

from agent.emotion import split_emotion


@pytest.mark.parametrize(("reply", "emotion", "text"), [
    ("[happy] Hello there!", "happy", "Hello there!"),
    ("[Scared]\nOh no, 98% CPU!", "scared", "Oh no, 98% CPU!"),
    ("**[angry]** Hmph.", "angry", "Hmph."),
    ("  [ thinking ]  Let me see...", "thinking", "Let me see..."),
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
