"""Tests for the chat window's text handling (escaping and Markdown)."""
from chat.chat_window import ChatWindow, markdown_to_plain


def test_markdown_to_plain():
    """Markdown markers are removed for plain-text displays such as the bubble."""
    assert markdown_to_plain("**Hot** and *spicy*") == "Hot and spicy"


def test_user_text_is_not_interpreted_as_html(qapp):
    """What the user types appears exactly, even if it looks like HTML."""
    win = ChatWindow()
    win.append_message("You", "is 3 < 5 && <b>x</b>?")
    assert "is 3 < 5 && <b>x</b>?" in win._history.toPlainText()


def test_calcifer_reply_renders_markdown(qapp):
    """Calcifer's Markdown is rendered, so no raw ``**`` shows up."""
    win = ChatWindow()
    win.append_message("Calcifer", "**Yes!**\n\n- one\n- two")
    text = win._history.toPlainText()
    assert "**" not in text and "one" in text and "two" in text


def test_thinking_disables_input(qapp):
    """While the agent works the input is disabled and a status line is shown."""
    win = ChatWindow()
    win.set_thinking(True)
    assert not win._input.isEnabled() and "thinking" in win._thinking.text()
    win.set_thinking(False)
    assert win._input.isEnabled() and win._thinking.text() == ""
