"""Chat bubble: a compact speech-bubble chat that sticks to the pet (replaces the chat window).

What it looks like / how it behaves:

- A rounded cream bubble with the pet's dark maroon outline and a tail that points at the pet's
  face. It opens beside the pet (right side, or left when there is no room) and follows the pet
  every frame, so it stays attached when the pet is dragged.
- Inside: a scrollable history (scroll up to re-read older messages; Calcifer's replies are
  rendered from Markdown, user text is shown exactly as typed), a "Calcifer is thinking..." line
  and an input row.
- It closes itself after ``AUTO_CLOSE_MS`` without chat activity. The countdown restarts on every
  keystroke, scroll or click inside the bubble and after each reply, is paused while Calcifer is
  answering, and is postponed while the mouse pointer rests on the bubble (someone is reading).
  Esc or the x button closes it at once. Closing never clears the history; ``clear_history()``
  does (the app calls it when the chat memory expires).
"""
from __future__ import annotations

from collections.abc import Callable

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
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
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
USER_COLOR = "#8a4a14"   # the user's lines; Calcifer's use the browser's text colour

STYLE = """
* { font-family: "Segoe UI", "Arial"; }
QLabel#title { color: #6c0e16; font-weight: bold; font-size: 13px; }
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
"""


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
        self.setWindowTitle("Calcifer")
        self.setStyleSheet(STYLE)
        self.resize(BUBBLE_W, BUBBLE_H)
        self._anchor_fn = anchor_fn
        self._tail_left = True       # bubble on the pet's right, tail pointing left
        self._tail_y = BUBBLE_H * 0.7
        self._thinking_now = False
        self._closing = False

        title = QLabel("Calcifer", self)
        title.setObjectName("title")
        close_button = QPushButton("×", self)
        close_button.setObjectName("close")
        close_button.setCursor(Qt.CursorShape.PointingHandCursor)
        close_button.setToolTip("Close (Esc)")
        close_button.clicked.connect(self.close_bubble)

        self._history = QTextBrowser(self)
        self._history.setOpenExternalLinks(True)
        self._history.setFrameShape(QTextBrowser.Shape.NoFrame)
        self._history.document().setDocumentMargin(2)

        self._thinking = QLabel("", self)
        self._thinking.setObjectName("thinking")
        self._dots = 0
        self._dots_timer = QTimer(self)
        self._dots_timer.setInterval(380)
        self._dots_timer.timeout.connect(self._animate_thinking)

        self._input = QLineEdit(self)
        self._input.setPlaceholderText("Say something to Calcifer...")
        self._input.returnPressed.connect(self._on_send)
        self._input.textEdited.connect(self._kick)

        self._send_button = QPushButton("➤", self)
        self._send_button.setObjectName("send")
        self._send_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self._send_button.clicked.connect(self._on_send)

        self._layout = QVBoxLayout(self)
        self._layout.setSpacing(4)
        header = QHBoxLayout()
        header.addWidget(title)
        header.addStretch(1)
        header.addWidget(close_button)
        self._layout.addLayout(header)
        self._layout.addWidget(self._history, 1)
        self._layout.addWidget(self._thinking)
        row = QHBoxLayout()
        row.setSpacing(6)
        row.addWidget(self._input, 1)
        row.addWidget(self._send_button)
        self._layout.addLayout(row)
        self._apply_margins()

        # Any typing, scrolling or clicking inside counts as chat activity.
        for widget in (self._input, self._history, self._history.viewport()):
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
        """Show the bubble beside the pet (fading in), focus the input and start the countdown."""
        self._closing = False
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
        """Add one message and scroll to it. ``sender`` is "You" or "Calcifer": the user's lines
        are right-aligned plain text, Calcifer's are left-aligned Markdown."""
        mine = sender != "Calcifer"
        cursor = self._history.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        block = QTextBlockFormat()
        block.setAlignment(Qt.AlignmentFlag.AlignRight if mine else Qt.AlignmentFlag.AlignLeft)
        block.setTopMargin(0 if self._history.document().isEmpty() else 8)
        block.setLeftMargin(28 if mine else 0)
        block.setRightMargin(0 if mine else 18)
        if self._history.document().isEmpty():
            cursor.setBlockFormat(block)
        else:
            cursor.insertBlock(block, QTextCharFormat())
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
        self._history.setTextCursor(cursor)
        self._history.ensureCursorVisible()
        bar = self._history.verticalScrollBar()
        bar.setValue(bar.maximum())

    def clear_history(self) -> None:
        """Forget every message on screen (used when the chat memory expires)."""
        self._history.clear()

    def set_thinking(self, thinking: bool) -> None:
        """While Calcifer answers: disable the input, animate the status line and pause the
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
            if self.is_open():
                self._input.setFocus()
            self._kick()

    # ------------------------------------------------------------------ countdown

    def _kick(self) -> None:
        """Restart the auto-close countdown (never while Calcifer is answering)."""
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
        self._thinking.setText("Calcifer is thinking" + "." * self._dots)

