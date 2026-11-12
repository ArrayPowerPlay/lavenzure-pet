"""Tests for the chat bubble: text handling (escaping, Markdown) and the auto-close countdown."""
from PySide6.QtCore import QRect

from chat.chat_bubble import ChatBubble, markdown_to_plain


def make_bubble() -> ChatBubble:
    """A bubble attached to a fake pet in the middle of the screen."""
    return ChatBubble(lambda: QRect(300, 300, 100, 100))


def test_markdown_to_plain():
    """Markdown markers are removed for plain-text displays."""
    assert markdown_to_plain("**Hot** and *spicy*") == "Hot and spicy"


def test_user_text_is_not_interpreted_as_html(qapp):
    """What the user types appears exactly, even if it looks like HTML."""
    bubble = make_bubble()
    bubble.append_message("You", "is 3 < 5 && <b>x</b>?")
    assert "is 3 < 5 && <b>x</b>?" in bubble._history.toPlainText()


def test_lavenzure_reply_renders_markdown(qapp):
    """Lavenzure's Markdown is rendered, so no raw ``**`` shows up."""
    bubble = make_bubble()
    bubble.append_message("Lavenzure", "**Yes!**\n\n- one\n- two")
    text = bubble._history.toPlainText()
    assert "**" not in text and "one" in text and "two" in text


def test_thinking_disables_input_and_pauses_countdown(qapp):
    """While the agent works the input is disabled and the bubble cannot auto-close."""
    bubble = make_bubble()
    bubble.open()
    assert bubble._auto_close.isActive()
    bubble.set_thinking(True)
    assert not bubble._input.isEnabled() and "thinking" in bubble._thinking.text()
    assert not bubble._auto_close.isActive()
    bubble.set_thinking(False)
    assert bubble._input.isEnabled() and bubble._thinking.text() == ""
    assert bubble._auto_close.isActive()


def test_typing_restarts_countdown(qapp):
    """Each keystroke restarts the 30 s countdown."""
    bubble = make_bubble()
    bubble.open()
    bubble._auto_close.stop()
    bubble._input.textEdited.emit("h")
    assert bubble._auto_close.isActive()


def test_close_keeps_history_and_clear_wipes_it(qapp):
    """Closing only hides the bubble; clear_history (memory expired) empties it."""
    bubble = make_bubble()
    bubble.open()
    bubble.append_message("You", "hello")
    closed = []
    bubble.closed.connect(lambda: closed.append(True))
    bubble.hide()
    assert closed and "hello" in bubble._history.toPlainText()
    bubble.clear_history()
    assert bubble._history.toPlainText() == ""


def test_streamed_reply_is_replaced_in_place(qapp):
    """Each partial reply replaces the previous one; the final text stays once."""
    bubble = make_bubble()
    bubble.append_message("You", "hello")
    bubble.set_thinking(True)
    bubble.stream_message("Hi")
    bubble.stream_message("Hi the")
    assert bubble._thinking.text() == ""
    bubble.finish_stream("Hi there, **friend**!")
    text = bubble._history.toPlainText()
    assert text == "hello\nHi there, friend!"   # no blank lines left by the replaced parts
    bubble.append_message("You", "next")
    assert bubble._history.toPlainText().endswith("next")


def test_error_after_partial_keeps_partial(qapp):
    """If the answer breaks off, what arrived stays and the error is added below it."""
    bubble = make_bubble()
    bubble.stream_message("Half an ans")
    bubble.finish_stream(None)
    bubble.append_message("Lavenzure", "My flame flickered.")
    text = bubble._history.toPlainText()
    assert "Half an ans" in text and text.endswith("My flame flickered.")
