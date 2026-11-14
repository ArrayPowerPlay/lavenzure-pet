"""Tests for the chat bubble: text handling (escaping, Markdown) and the auto-close countdown."""
from datetime import datetime
from types import SimpleNamespace

from PySide6.QtCore import QRect

from chat.chat_bubble import ChatBubble, format_due, markdown_to_plain


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


def test_every_message_gets_its_own_box(qapp):
    """Each message is remembered (start + sender) so a box is drawn around it; redrawing a
    streamed reply replaces its box instead of adding another one."""
    bubble = make_bubble()
    bubble.open()   # shown, so the text gets laid out
    bubble.append_message("You", "hi")
    bubble.stream_message("Hel")
    bubble.stream_message("Hello there")
    bubble.finish_stream("Hello there, friend!")
    view = bubble._history
    assert [kind for _, kind in view._messages] == ["user", "pet"]
    qapp.processEvents()
    start, _ = view._messages[1]
    end = view.document().characterCount()
    assert view._message_rect(start, end) is not None
    bubble.clear_history()
    assert view._messages == []


def test_format_due():
    """Reminder times read Today / Tomorrow / weekday + date."""
    now = datetime(2026, 11, 14, 15, 20)
    assert format_due(datetime(2026, 11, 14, 20, 0), now) == "Today 20:00"
    assert format_due(datetime(2026, 11, 15, 8, 0), now) == "Tomorrow 08:00"
    assert format_due(datetime(2026, 11, 17, 9, 5), now) == "Tue 17 Nov, 09:05"


def test_reminders_tab_lists_and_cancels(qapp):
    """The Reminders tab shows each reminder with its count in the title; its x asks for a
    cancel (by id) and the list only changes when the app sends a new one."""
    bubble = make_bubble()
    assert bubble._reminders_tab.text() == "Reminders"
    due = datetime.now().timestamp() + 3600
    bubble.set_reminders([SimpleNamespace(id=4, due=due, message="call <b>mom</b>"),
                          SimpleNamespace(id=7, due=due + 60, message="tea")])
    assert bubble._reminders_tab.text() == "Reminders (2)"
    from PySide6.QtWidgets import QLabel, QPushButton
    texts = [label.text() for label in bubble._reminder_list.findChildren(QLabel)
             if label.objectName() == "reminderText"]
    assert texts == ["call <b>mom</b>", "tea"]
    asked = []
    bubble.reminder_cancel_requested.connect(asked.append)
    buttons = [b for b in bubble._reminder_list.findChildren(QPushButton)
               if b.objectName() == "removeReminder"]
    buttons[1].click()
    assert asked == [7]
    bubble.set_reminders([])
    assert bubble._reminders_tab.text() == "Reminders"


def test_open_always_starts_on_chat_tab(qapp):
    """Clicking the Reminders tab switches pages; opening the bubble again shows Chat."""
    bubble = make_bubble()
    bubble.open()
    bubble._reminders_tab.click()
    assert bubble.current_tab() == 1
    bubble.open()
    assert bubble.current_tab() == 0
    bubble.hide()


def test_note_waits_for_streamed_reply(qapp):
    """A note never lands inside a reply that is still streaming: it follows the reply, and
    it ends the reply's box without getting one itself."""
    bubble = make_bubble()
    bubble.append_message("You", "remind me at 9")
    bubble.stream_message("Sure")
    bubble.append_note("Reminder set: Today 21:00")
    bubble.stream_message("Sure, done!")
    bubble.finish_stream("Sure, done!")
    text = bubble._history.toPlainText()
    assert text.index("Sure, done!") < text.index("Reminder set")
    assert [kind for _, kind in bubble._history._messages] == ["user", "pet", "note"]
    bubble.append_note("Another")      # no stream running: added at once
    assert bubble._history.toPlainText().endswith("Another")
