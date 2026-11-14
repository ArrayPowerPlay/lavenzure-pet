"""Chat bubble: a compact speech-bubble chat that sticks to the pet (replaces the chat window).

What it looks like / how it behaves:

- A rounded cream bubble with the pet's dark maroon outline and a tail that points at the pet's
  face. It opens beside the pet (right side, or left when there is no room) and follows the pet
  every frame, so it stays attached when the pet is dragged.
- Inside: a scrollable history (scroll up to re-read older messages; Lavenzure's replies are
  rendered from Markdown, user text is shown exactly as typed), a "Lavenzure is thinking..." line
  and an input row. Every message sits in its own rounded box (``MessageView``): the user's on the
  right in warm orange, Lavenzure's on the left in white with a maroon outline, so it is easy to
  see who said what.
- It closes itself after ``AUTO_CLOSE_MS`` without chat activity. The countdown restarts on every
  keystroke, scroll or click inside the bubble and after each reply, is paused while Lavenzure is
  answering, and is postponed while the mouse pointer rests on the bubble (someone is reading).
  Esc or the x button closes it at once. Closing never clears the history; ``clear_history()``
  does (the app calls it when the chat memory expires).
- Replies can stream in: ``stream_message(text)`` shows Lavenzure's answer so far and redraws it as
  it grows; ``finish_stream(text)`` puts the final text in place.
- Two tabs at the top (round 25): **Chat** and **Reminders**. The Reminders tab lists the
  reminders still waiting (soonest first, each with its time, text and an x button to remove it);
  the tab title shows how many there are. The app feeds the list with ``set_reminders`` whenever
  it changes, and the bubble only asks for removals (``reminder_cancel_requested(id)``), so it
  never owns reminder state. Opening the bubble always starts on the Chat tab.
"""
from __future__ import annotations

from collections.abc import Callable, Sequence
from datetime import datetime
from typing import Protocol

from PySide6.QtCore import (
    QEasingCurve,
    QEvent,
    QObject,
    QPointF,
    QPropertyAnimation,
    QRect,
    QRectF,
    Qt,
    QTimer,
    Signal,
)
from PySide6.QtGui import (
    QColor,
    QKeyEvent,
    QPainter,
    QPainterPath,
    QPen,
    QTextBlockFormat,
    QTextCharFormat,
    QTextCursor,
    QTextDocument,
    QTextDocumentFragment,
)
from PySide6.QtWidgets import (
    QButtonGroup,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QStackedWidget,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

import config

AUTO_CLOSE_MS = 30_000     # default; ``chat.auto_close_seconds`` in config.yaml overrides it
FOLLOW_INTERVAL_MS = 16    # re-attach to the pet ~60 times per second
BUBBLE_W, BUBBLE_H = 320, 360   # window size, tail included
TAIL = 20                  # how far the tail sticks out of the bubble body (px)
RADIUS = 18                # corner radius of the bubble body
PAD = 5                    # room for the outline and the soft shadow around the body
GAP_PX = 2                 # space between the tail tip and the pet's body

FILL = QColor(255, 248, 234)
INK = QColor(108, 14, 22)            # same dark maroon as the pet's outline
SHADOW = QColor(40, 10, 0, 45)
USER_COLOR = "#8a4a14"   # the user's lines; Lavenzure's use the browser's text colour

# Rounded box drawn around every message (fill, outline) and the room it needs.
USER_BOX = (QColor(255, 226, 184), QColor(232, 160, 90))
PET_BOX = (QColor(255, 253, 247), QColor(176, 92, 70))
BOX_PAD_X, BOX_PAD_Y = 9, 5   # box padding around the text (px)
BOX_RADIUS = 11
MESSAGE_GAP = 2 * BOX_PAD_Y + 7   # space between two messages (the boxes leave ~7 px free)
PARAGRAPH_GAP = 4                 # space between paragraphs inside one reply
SIDE_ROOM = 34                    # free room on the far side, so the two speakers look apart
LIST_MARKER_W = 16                # room for a bullet / number left of a list item's text

STYLE = """
* { font-family: "Segoe UI", "Arial"; }
QPushButton#close {
    background: transparent; color: #a0522d; border: none; font-size: 16px; font-weight: bold;
    padding: 0px 4px;
}
QPushButton#close:hover { color: #d2381e; }
QTextBrowser {
    background: transparent; color: #3a2410; border: none; font-size: 13px;
    selection-background-color: #ffb347;
}
QScrollBar:vertical { background: transparent; width: 7px; margin: 2px 0px; }
QScrollBar::handle:vertical { background: #f0b878; border-radius: 3px; min-height: 24px; }
QScrollBar::handle:vertical:hover { background: #e8913a; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; }
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: transparent; }
QLineEdit {
    background: #fffdf7; color: #3a2410; border: 2px solid #f0b878; border-radius: 14px;
    padding: 5px 10px; font-size: 13px;
}
QLineEdit:focus { border-color: #ef8a2e; }
QLineEdit:disabled { background: #f3e8d8; color: #9a8470; }
QPushButton#send {
    background: #f28a1e; color: white; border: 2px solid #6c0e16; border-radius: 15px;
    font-size: 14px; font-weight: bold; min-width: 26px; min-height: 26px;
    max-width: 26px; max-height: 26px;
}
QPushButton#send:hover { background: #ff9d33; }
QPushButton#send:disabled { background: #d9b38f; border-color: #a07060; }
QLabel#thinking { color: #c8641e; font-style: italic; font-size: 12px; }
QPushButton#tab {
    background: transparent; color: #a0522d; border: none; border-bottom: 2px solid transparent;
    font-size: 13px; font-weight: bold; padding: 1px 6px 2px 6px;
}
QPushButton#tab:hover { color: #d2381e; }
QPushButton#tab:checked { color: #6c0e16; border-bottom-color: #ef8a2e; }
QScrollArea, QWidget#reminderList { background: transparent; border: none; }
QFrame#reminderRow { background: #fffdf7; border: 1px solid #b05c46; border-radius: 11px; }
QLabel#reminderTime { color: #c8641e; font-weight: bold; font-size: 12px; }
QLabel#reminderText { color: #3a2410; font-size: 13px; }
QLabel#reminderEmpty { color: #9a8470; font-style: italic; font-size: 12px; }
QPushButton#removeReminder {
    background: transparent; color: #a0522d; border: none; font-size: 15px; font-weight: bold;
    padding: 0px 2px;
}
QPushButton#removeReminder:hover { color: #d2381e; }
"""

EMPTY_REMINDERS = ("No reminders yet.\nAsk me in the Chat tab, e.g.\n"
                   "\"remind me at 9 pm to call mom\".")


class ReminderLike(Protocol):
    """What the Reminders tab shows of a reminder (``monitor.reminders.Reminder``)."""

    id: int
    due: float
    message: str


def format_due(due: datetime, now: datetime) -> str:
    """Short label for a reminder's time: ``Today 20:00``, ``Tomorrow 08:00`` or
    ``Mon 17 Nov, 09:00``."""
    days = (due.date() - now.date()).days
    clock = due.strftime("%H:%M")
    if days == 0:
        return f"Today {clock}"
    if days == 1:
        return f"Tomorrow {clock}"
    return f"{due:%a} {due.day} {due:%b}, {clock}"


class MessageView(QTextBrowser):
    """The chat history: a ``QTextBrowser`` that paints a rounded box behind every message.

    The text itself stays ordinary rich text (selectable, links clickable, Markdown rendered);
    each message only remembers where it starts in the document and who sent it. Messages are
    only ever added at the end or removed from the end (a streamed reply being redrawn), so the
    start positions stay valid. Each box is fitted around the text that was really laid out,
    so a short message gets a small box and a long one wraps inside a wide box.
    """

    def __init__(self, parent: QWidget) -> None:
        """An empty history with room around the text for the boxes."""
        super().__init__(parent)
        self._messages: list[tuple[int, bool]] = []   # (start position, sent by the user)
        self.document().setDocumentMargin(BOX_PAD_Y + 2)

    def add_message_start(self, position: int, mine: bool) -> None:
        """Remember that a message starts at document ``position`` (``mine`` = the user's)."""
        self._messages.append((position, mine))
        self.viewport().update()

    def drop_messages_from(self, position: int) -> None:
        """Forget every message that starts at or after ``position`` (its text was removed)."""
        self._messages = [m for m in self._messages if m[0] < position]

    def clear(self) -> None:
        """Remove all text and every box."""
        self._messages = []
        super().clear()

    def _message_rect(self, start: int, end: int) -> QRectF | None:
        """Tight rectangle (document coordinates) around the laid-out text from ``start`` up to
        ``end``, or ``None`` when that text has nothing visible."""
        doc = self.document()
        layout_of = doc.documentLayout()
        rect: QRectF | None = None
        block = doc.findBlock(start)
        while block.isValid() and block.position() < end:
            origin = layout_of.blockBoundingRect(block).topLeft()
            layout = block.layout()
            for i in range(layout.lineCount()):
                line = layout.lineAt(i)
                if line.naturalTextWidth() <= 0:
                    continue
                line_rect = line.naturalTextRect().translated(origin)
                if block.textList() is not None and i == 0:
                    line_rect.setLeft(line_rect.left() - LIST_MARKER_W)
                rect = line_rect if rect is None else rect.united(line_rect)
            block = block.next()
        return rect

    def paintEvent(self, event) -> None:  # noqa: N802 - Qt override
        """Draw the message boxes first, then let ``QTextBrowser`` draw the text on top."""
        if self._messages:
            painter = QPainter(self.viewport())
            painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
            painter.translate(-self.horizontalScrollBar().value(),
                              -self.verticalScrollBar().value())
            visible = QRectF(self.viewport().rect()).translated(
                self.horizontalScrollBar().value(), self.verticalScrollBar().value())
            doc_end = self.document().characterCount()
            for index, (start, mine) in enumerate(self._messages):
                end = self._messages[index + 1][0] if index + 1 < len(self._messages) else doc_end
                rect = self._message_rect(start, end)
                if rect is None:
                    continue
                box = rect.adjusted(-BOX_PAD_X, -BOX_PAD_Y, BOX_PAD_X, BOX_PAD_Y)
                if not box.intersects(visible):
                    continue
                fill, outline = USER_BOX if mine else PET_BOX
                painter.setBrush(fill)
                painter.setPen(QPen(outline, 1.4))
                painter.drawRoundedRect(box, BOX_RADIUS, BOX_RADIUS)
            painter.end()
        super().paintEvent(event)


def markdown_to_plain(text: str) -> str:
    """Strip Markdown formatting (``**bold**``, list markers, links) for plain-text displays."""
    doc = QTextDocument()
    doc.setMarkdown(text)
    return doc.toPlainText().strip()


class ChatBubble(QWidget):
    """The chat UI. Emits ``message_sent(text)`` when the user sends something and ``closed`` when
    the bubble goes away (auto-close, Esc or the x button).

    ``anchor_fn`` returns the pet's body rectangle in global screen coordinates; the bubble sits
    beside it and aims its tail at the rectangle's centre.
    """

    message_sent = Signal(str)
    closed = Signal()
    reminder_cancel_requested = Signal(int)

    def __init__(self, anchor_fn: Callable[[], QRect]) -> None:
        """Build the (hidden) bubble window and its timers."""
        super().__init__(
            None,
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
            | Qt.WindowType.NoDropShadowWindowHint,
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setWindowTitle("Lavenzure")
        self.setStyleSheet(STYLE)
        self.resize(BUBBLE_W, BUBBLE_H)
        self._anchor_fn = anchor_fn
        self._tail_left = True       # bubble on the pet's right, tail pointing left
        self._tail_y = BUBBLE_H * 0.7
        self._thinking_now = False
        self._closing = False
        self._stream_start: int | None = None   # where the reply that is still arriving begins

        self._chat_tab = self._make_tab("Chat")
        self._reminders_tab = self._make_tab("Reminders")
        self._tabs = QButtonGroup(self)
        self._tabs.setExclusive(True)
        self._tabs.addButton(self._chat_tab, 0)
        self._tabs.addButton(self._reminders_tab, 1)
        self._chat_tab.setChecked(True)
        self._tabs.idClicked.connect(self._on_tab_clicked)
        close_button = QPushButton("×", self)
        close_button.setObjectName("close")
        close_button.setCursor(Qt.CursorShape.PointingHandCursor)
        close_button.setToolTip("Close (Esc)")
        close_button.clicked.connect(self.close_bubble)

        self._history = MessageView(self)
        self._history.setOpenExternalLinks(True)
        self._history.setFrameShape(QTextBrowser.Shape.NoFrame)

        self._thinking = QLabel("", self)
        self._thinking.setObjectName("thinking")
        self._dots = 0
        self._dots_timer = QTimer(self)
        self._dots_timer.setInterval(380)
        self._dots_timer.timeout.connect(self._animate_thinking)

        self._input = QLineEdit(self)
        self._input.setPlaceholderText("Say something to Lavenzure...")
        self._input.returnPressed.connect(self._on_send)
        self._input.textEdited.connect(self._kick)

        self._send_button = QPushButton("➤", self)
        self._send_button.setObjectName("send")
        self._send_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self._send_button.clicked.connect(self._on_send)

        self._layout = QVBoxLayout(self)
        self._layout.setSpacing(4)
        header = QHBoxLayout()
        header.setSpacing(2)
        header.addWidget(self._chat_tab)
        header.addWidget(self._reminders_tab)
        header.addStretch(1)
        header.addWidget(close_button)
        self._layout.addLayout(header)

        chat_page = QWidget(self)
        chat_layout = QVBoxLayout(chat_page)
        chat_layout.setContentsMargins(0, 0, 0, 0)
        chat_layout.setSpacing(4)
        chat_layout.addWidget(self._history, 1)
        chat_layout.addWidget(self._thinking)
        row = QHBoxLayout()
        row.setSpacing(6)
        row.addWidget(self._input, 1)
        row.addWidget(self._send_button)
        chat_layout.addLayout(row)

        self._reminder_scroll = QScrollArea(self)
        self._reminder_scroll.setWidgetResizable(True)
        self._reminder_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._reminder_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._reminder_scroll.viewport().setAutoFillBackground(False)
        self._reminder_list = QWidget()
        self._reminder_list.setObjectName("reminderList")
        self._reminder_rows = QVBoxLayout(self._reminder_list)
        self._reminder_rows.setContentsMargins(0, 4, 4, 4)
        self._reminder_rows.setSpacing(6)
        self._reminder_scroll.setWidget(self._reminder_list)

        self._pages = QStackedWidget(self)
        self._pages.addWidget(chat_page)
        self._pages.addWidget(self._reminder_scroll)
        self._layout.addWidget(self._pages, 1)
        self._apply_margins()
        self.set_reminders([])

        # Any typing, scrolling or clicking inside counts as chat activity.
        for widget in (self._input, self._history, self._history.viewport(),
                       self._reminder_scroll.viewport()):
            widget.installEventFilter(self)

        self._auto_close = QTimer(self)
        self._auto_close.setSingleShot(True)
        self._auto_close.setInterval(
            int(float(config.get("chat.auto_close_seconds", AUTO_CLOSE_MS / 1000)) * 1000))
        self._auto_close.timeout.connect(self._on_auto_close)

        self._follow_timer = QTimer(self)
        self._follow_timer.setInterval(FOLLOW_INTERVAL_MS)
        self._follow_timer.timeout.connect(self._follow)

        self._fade = QPropertyAnimation(self, b"windowOpacity", self)
        self._fade.setDuration(160)
        self._fade.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._fade.finished.connect(self._on_fade_finished)

    # ------------------------------------------------------------------ public API

    def open(self) -> None:
        """Show the bubble beside the pet (fading in) on the Chat tab, focus the input and start
        the countdown."""
        self._closing = False
        self.show_tab(0)
        self._choose_side(force=not self.isVisible())
        self._follow()
        if not self.isVisible():
            self.setWindowOpacity(0.0)
            self.show()
            self._fade.stop()
            self._fade.setStartValue(0.0)
            self._fade.setEndValue(1.0)
            self._fade.start()
        self.raise_()
        self.activateWindow()
        self._input.setFocus()
        self._follow_timer.start()
        self._history.verticalScrollBar().setValue(self._history.verticalScrollBar().maximum())
        self._kick()

    def close_bubble(self) -> None:
        """Fade out and hide; the history stays (``closed`` is emitted once hidden)."""
        if not self.isVisible() or self._closing:
            return
        self._closing = True
        self._auto_close.stop()
        self._fade.stop()
        self._fade.setStartValue(self.windowOpacity())
        self._fade.setEndValue(0.0)
        self._fade.start()

    def is_open(self) -> bool:
        """True while the bubble is on screen (and not on its way out)."""
        return self.isVisible() and not self._closing

    def append_message(self, sender: str, text: str) -> None:
        """Add one message and scroll to it. ``sender`` is "You" or "Lavenzure": the user's lines
        are right-aligned plain text, Lavenzure's are left-aligned Markdown."""
        self._insert_message(sender, text)

    def stream_message(self, text: str) -> None:
        """Show Lavenzure's reply as far as it has arrived, replacing the previous partial text.
        The "thinking" line goes away as soon as the first words appear."""
        if self._stream_start is None:
            self._dots_timer.stop()
            self._thinking.setText("")
        else:
            self._remove_from(self._stream_start)
        self._stream_start = self._insert_message("Lavenzure", text)

    def finish_stream(self, text: str | None) -> None:
        """End the streamed reply: show ``text`` as its final version (``None`` keeps whatever
        arrived). Without a stream in progress, ``text`` is simply appended."""
        if text is not None:
            if self._stream_start is None:
                self._insert_message("Lavenzure", text)
            else:
                self.stream_message(text)
        self._stream_start = None

    def _remove_from(self, position: int) -> None:
        """Delete everything in the history from ``position`` to the end (text and boxes)."""
        self._history.drop_messages_from(position)
        cursor = self._history.textCursor()
        cursor.setPosition(position)
        cursor.movePosition(QTextCursor.MoveOperation.End, QTextCursor.MoveMode.KeepAnchor)
        cursor.removeSelectedText()

    def _insert_message(self, sender: str, text: str) -> int:
        """Append one message (see ``append_message``) in its own box; returns the position where
        it starts, so ``_remove_from`` can take it off again."""
        mine = sender != "Lavenzure"
        first = self._history.document().isEmpty()
        cursor = self._history.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        message_start = cursor.position()
        # Every block of the message: its side, room for the box, small gaps between paragraphs.
        block = QTextBlockFormat()
        block.setAlignment(Qt.AlignmentFlag.AlignRight if mine else Qt.AlignmentFlag.AlignLeft)
        block.setTopMargin(PARAGRAPH_GAP)
        block.setBottomMargin(0)
        block.setLeftMargin(SIDE_ROOM + BOX_PAD_X if mine else BOX_PAD_X)
        block.setRightMargin(BOX_PAD_X if mine else SIDE_ROOM + BOX_PAD_X)
        if first:
            cursor.setBlockFormat(block)
        else:
            cursor.insertBlock(block, QTextCharFormat())
        text_start = cursor.position()
        if mine:
            fmt = QTextCharFormat()
            fmt.setForeground(QColor(USER_COLOR))
            cursor.insertText(text, fmt)
        else:
            fragment = QTextDocumentFragment.fromMarkdown(text)
            start = cursor.position()
            cursor.insertFragment(fragment)
            # Keep the alignment of every block the fragment brought in.
            end = cursor.position()
            cursor.setPosition(start)
            cursor.setPosition(end, QTextCursor.MoveMode.KeepAnchor)
            cursor.mergeBlockFormat(block)
            cursor.clearSelection()
            cursor.movePosition(QTextCursor.MoveOperation.End)
        # The message's first block keeps it apart from the message above.
        cursor.setPosition(text_start)
        head = QTextBlockFormat()
        head.setTopMargin(0 if first else MESSAGE_GAP)
        cursor.mergeBlockFormat(head)
        cursor.movePosition(QTextCursor.MoveOperation.End)
        self._history.add_message_start(text_start, mine)
        self._history.setTextCursor(cursor)
        self._history.ensureCursorVisible()
        bar = self._history.verticalScrollBar()
        bar.setValue(bar.maximum())
        return message_start

    def show_tab(self, index: int) -> None:
        """Switch to the Chat (0) or Reminders (1) tab."""
        self._tabs.button(index).setChecked(True)
        self._pages.setCurrentIndex(index)
        if index == 0:
            if self.is_open() and self._input.isEnabled():
                self._input.setFocus()
        else:
            self.setFocus()   # keep Esc working while no input field is shown

    def current_tab(self) -> int:
        """The tab on show: 0 = Chat, 1 = Reminders."""
        return self._pages.currentIndex()

    def set_reminders(self, reminders: Sequence[ReminderLike]) -> None:
        """Show ``reminders`` (soonest first) in the Reminders tab and their number in its
        title. Called by the app whenever the list changes."""
        while self._reminder_rows.count():
            item = self._reminder_rows.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.hide()           # gone from the screen now, freed by Qt a bit later
                widget.setParent(None)
                widget.deleteLater()
        now = datetime.now()
        for reminder in reminders:
            self._reminder_rows.addWidget(self._make_reminder_row(reminder, now))
        if not reminders:
            empty = QLabel(EMPTY_REMINDERS, self._reminder_list)
            empty.setObjectName("reminderEmpty")
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty.setWordWrap(True)
            self._reminder_rows.addSpacing(40)
            self._reminder_rows.addWidget(empty)
        self._reminder_rows.addStretch(1)
        count = len(reminders)
        self._reminders_tab.setText(f"Reminders ({count})" if count else "Reminders")

    def clear_history(self) -> None:
        """Forget every message on screen (used when the chat memory expires)."""
        self._history.clear()
        self._stream_start = None

    def set_thinking(self, thinking: bool) -> None:
        """While Lavenzure answers: disable the input, animate the status line and pause the
        auto-close countdown (it restarts when the answer arrives)."""
        self._thinking_now = thinking
        self._input.setEnabled(not thinking)
        self._send_button.setEnabled(not thinking)
        if thinking:
            self._auto_close.stop()
            self._dots = 0
            self._animate_thinking()
            self._dots_timer.start()
        else:
            self._dots_timer.stop()
            self._thinking.setText("")
            if self.is_open() and self.current_tab() == 0:
                self._input.setFocus()
            self._kick()

    # ------------------------------------------------------------------ countdown

    def _kick(self) -> None:
        """Restart the auto-close countdown (never while Lavenzure is answering)."""
        if self._thinking_now or not self.is_open():
            return
        self._auto_close.start()

    def _on_auto_close(self) -> None:
        """Countdown over: close, unless the pointer rests on the bubble (someone is reading)."""
        if self._thinking_now:
            return
        if self.underMouse():
            self._auto_close.start(5_000)
            return
        self.close_bubble()

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:  # noqa: N802 - Qt override
        """Treat key presses, wheel scrolls and clicks inside the bubble as activity."""
        if event.type() in (QEvent.Type.KeyPress, QEvent.Type.Wheel,
                            QEvent.Type.MouseButtonPress):
            self._kick()
        return super().eventFilter(watched, event)

    # ------------------------------------------------------------------ placement

    def _choose_side(self, force: bool = False) -> None:
        """Put the bubble on the pet's right if it fits there, otherwise on its left.

        Only flips when the current side stops fitting, so dragging the pet does not make the
        bubble jump back and forth."""
        pet = self._anchor_fn()
        screen = self.screen().availableGeometry()
        fits_right = pet.right() + GAP_PX + self.width() <= screen.right()
        fits_left = pet.left() - GAP_PX - self.width() >= screen.left()
        if force:
            want_left_tail = fits_right or not fits_left
        elif self._tail_left and not fits_right and fits_left:
            want_left_tail = False
        elif not self._tail_left and not fits_left and fits_right:
            want_left_tail = True
        else:
            want_left_tail = self._tail_left
        if want_left_tail != self._tail_left:
            self._tail_left = want_left_tail
            self._apply_margins()

    def _apply_margins(self) -> None:
        """Keep the widgets inside the bubble body (the tail side gets extra room)."""
        inner = 14
        left = PAD + inner + (TAIL if self._tail_left else 0)
        right = PAD + inner + (0 if self._tail_left else TAIL)
        self._layout.setContentsMargins(left, PAD + 8, right, PAD + 12)
        self.update()

    def _follow(self) -> None:
        """Stay beside the pet and aim the tail at its middle; kept inside the screen."""
        pet = self._anchor_fn()
        self._choose_side()
        screen = self.screen().availableGeometry()
        if self._tail_left:
            x = pet.right() + GAP_PX
        else:
            x = pet.left() - GAP_PX - self.width()
        target_y = pet.center().y()
        # Sit so the tail is in the lower part of the bubble, like a speech bubble.
        y = target_y - int(self.height() * 0.72)
        x = max(screen.left(), min(x, screen.right() - self.width()))
        y = max(screen.top(), min(y, screen.bottom() - self.height()))
        tail_y = min(max(target_y - y, RADIUS + 18), self.height() - RADIUS - 18 - PAD)
        if abs(tail_y - self._tail_y) > 0.5:
            self._tail_y = tail_y
            self.update()
        if (x, y) != (self.x(), self.y()):
            self.move(x, y)

    # ------------------------------------------------------------------ painting / events

    def _body_rect(self) -> QRectF:
        """The rounded body of the bubble (without the tail), in widget coordinates."""
        left = PAD + (TAIL if self._tail_left else 0)
        right = self.width() - PAD - (0 if self._tail_left else TAIL)
        return QRectF(left, PAD, right - left, self.height() - 2 * PAD - 3)

    def _bubble_path(self) -> QPainterPath:
        """Rounded body united with a curved tail pointing toward the pet."""
        body = self._body_rect()
        path = QPainterPath()
        path.addRoundedRect(body, RADIUS, RADIUS)
        ty = self._tail_y
        tail = QPainterPath()
        if self._tail_left:
            edge, tip = body.left() + 2, PAD + 1
        else:
            edge, tip = body.right() - 2, self.width() - PAD - 1
        tail.moveTo(QPointF(edge, ty - 13))
        tail.quadTo(QPointF((edge + tip) / 2, ty - 2), QPointF(tip, ty + 6))
        tail.quadTo(QPointF((edge + tip) / 2 + (2 if self._tail_left else -2), ty + 8),
                    QPointF(edge, ty + 10))
        tail.closeSubpath()
        return path.united(tail).simplified()

    def paintEvent(self, event) -> None:  # noqa: N802 - Qt override
        """Soft shadow, cream fill and the thick maroon outline (sticker style, like the pet)."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        path = self._bubble_path()
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(SHADOW)
        painter.drawPath(path.translated(0, 3))
        painter.setBrush(FILL)
        painter.setPen(QPen(INK, 2.6, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap,
                            Qt.PenJoinStyle.RoundJoin))
        painter.drawPath(path)
        painter.end()

    def keyPressEvent(self, event: QKeyEvent) -> None:  # noqa: N802 - Qt override
        """Esc closes the bubble (the conversation is kept)."""
        if event.key() == Qt.Key.Key_Escape:
            self.close_bubble()
            return
        super().keyPressEvent(event)

    def _on_fade_finished(self) -> None:
        """After fading out: really hide and report it."""
        if self._closing:
            self.hide()

    def hideEvent(self, event) -> None:  # noqa: N802 - Qt override
        """Stop following and counting once hidden, then tell the app."""
        super().hideEvent(event)
        self._closing = False
        self._follow_timer.stop()
        self._auto_close.stop()
        self.closed.emit()

    # ------------------------------------------------------------------ internals

    def _make_tab(self, text: str) -> QPushButton:
        """A flat, checkable tab button for the header."""
        button = QPushButton(text, self)
        button.setObjectName("tab")
        button.setCheckable(True)
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        return button

    def _on_tab_clicked(self, index: int) -> None:
        """A tab was clicked: show its page and count it as activity."""
        self.show_tab(index)
        self._kick()

    def _make_reminder_row(self, reminder: ReminderLike, now: datetime) -> QFrame:
        """One row of the Reminders tab: time on top, text below, x button on the right."""
        row = QFrame(self._reminder_list)
        row.setObjectName("reminderRow")
        layout = QHBoxLayout(row)
        layout.setContentsMargins(10, 5, 4, 6)
        layout.setSpacing(4)
        texts = QVBoxLayout()
        texts.setSpacing(1)
        when = QLabel(format_due(datetime.fromtimestamp(reminder.due), now), row)
        when.setObjectName("reminderTime")
        what = QLabel(reminder.message, row)
        what.setObjectName("reminderText")
        what.setTextFormat(Qt.TextFormat.PlainText)
        what.setWordWrap(True)
        texts.addWidget(when)
        texts.addWidget(what)
        layout.addLayout(texts, 1)
        remove = QPushButton("×", row)
        remove.setObjectName("removeReminder")
        remove.setCursor(Qt.CursorShape.PointingHandCursor)
        remove.setToolTip("Remove this reminder")
        remove.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        reminder_id = reminder.id
        remove.clicked.connect(lambda: self._on_remove_clicked(reminder_id))
        layout.addWidget(remove, 0, Qt.AlignmentFlag.AlignTop)
        return row

    def _on_remove_clicked(self, reminder_id: int) -> None:
        """The x of a reminder row: ask the app to cancel it (the list refreshes when it has)."""
        self._kick()
        self.reminder_cancel_requested.emit(reminder_id)

    def _on_send(self) -> None:
        """Echo the typed message into the history and emit it."""
        text = self._input.text().strip()
        if not text or not self._input.isEnabled():
            return
        self.append_message("You", text)
        self._input.clear()
        self.message_sent.emit(text)

    def _animate_thinking(self) -> None:
        """Cycle "thinking." / ".." / "..." on the status line."""
        self._dots = self._dots % 3 + 1
        self._thinking.setText("Lavenzure is thinking" + "." * self._dots)

