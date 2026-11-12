"""Always-on-top text chat window; history is in-memory for the current session only.

- User text is HTML-escaped (so ``<``, ``>``, ``&`` show as typed); Calcifer's replies are rendered
  from Markdown (bold, lists, links), which is what Gemini writes.
- Warm, flame-coloured theme; opens beside the pet; Esc closes it; shows an animated
  "Calcifer is thinking..." line while the agent works.
"""
from __future__ import annotations

import html

from PySide6.QtCore import QPoint, QRect, Qt, QTimer, Signal
from PySide6.QtGui import QKeyEvent, QTextCursor, QTextDocument, QTextDocumentFragment
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

STYLE = """
QWidget#chat { background: #2b1712; }
QTextBrowser {
    background: #fff8ec; color: #3a2410; border: 1px solid #d08a2e; border-radius: 10px;
    padding: 6px; font-size: 13px; selection-background-color: #ffb347;
}
QLineEdit {
    background: #fff8ec; color: #3a2410; border: 1px solid #d08a2e; border-radius: 8px;
    padding: 6px 8px; font-size: 13px;
}
QLineEdit:disabled { background: #e9dccb; color: #8a7360; }
QPushButton {
    background: #f28a1e; color: white; border: none; border-radius: 8px;
    padding: 6px 14px; font-weight: bold;
}
QPushButton:hover { background: #ff9d33; }
QPushButton:disabled { background: #a9745a; }
QLabel#thinking { color: #ffcf8a; font-style: italic; }
"""

SENDER_COLORS = {"You": "#8a4a14", "Calcifer": "#c8321e"}
GAP_PX = 12  # space between the pet and the chat window


def markdown_to_plain(text: str) -> str:
    """Strip Markdown formatting (``**bold**``, list markers, links) for plain-text displays."""
    doc = QTextDocument()
    doc.setMarkdown(text)
    return doc.toPlainText().strip()


class ChatWindow(QWidget):
    """Chat UI: message history, input line and Send button. Emits ``message_sent(text)``."""

    message_sent = Signal(str)

    def __init__(self) -> None:
        """Build the widgets and the thinking-dots timer (window starts hidden)."""
        super().__init__(None, Qt.WindowType.WindowStaysOnTopHint)
        self.setObjectName("chat")
        self.setWindowTitle("Calcifer")
        self.setStyleSheet(STYLE)
        self.resize(380, 460)

        self._history = QTextBrowser(self)
        self._history.setOpenExternalLinks(True)

        self._thinking = QLabel("", self)
        self._thinking.setObjectName("thinking")
        self._dots = 0
        self._dots_timer = QTimer(self)
        self._dots_timer.setInterval(400)
        self._dots_timer.timeout.connect(self._animate_thinking)

        self._input = QLineEdit(self)
        self._input.setPlaceholderText("Ask Calcifer something...")
        self._input.returnPressed.connect(self._on_send)

        self._send_button = QPushButton("Send", self)
        self._send_button.clicked.connect(self._on_send)

        layout = QVBoxLayout(self)
        layout.addWidget(self._history)
        layout.addWidget(self._thinking)
        row = QHBoxLayout()
        row.addWidget(self._input)
        row.addWidget(self._send_button)
        layout.addLayout(row)

    # ------------------------------------------------------------------ public API

    def show_near(self, pet_rect: QRect) -> None:
        """Show, raise and focus the window beside ``pet_rect`` (right side, else left),
        kept inside the screen."""
        screen = self.screen().availableGeometry()
        frame = self.frameGeometry()
        x = pet_rect.right() + GAP_PX
        if x + frame.width() > screen.right():
            x = pet_rect.left() - GAP_PX - frame.width()
        y = pet_rect.bottom() - frame.height()
        x = max(screen.left(), min(x, screen.right() - frame.width()))
        y = max(screen.top(), min(y, screen.bottom() - frame.height()))
        if not self.isVisible():
            self.move(QPoint(x, y))
        self.show()
        self.raise_()
        self.activateWindow()
        self._input.setFocus()

    def append_message(self, sender: str, text: str) -> None:
        """Add one message; Calcifer's replies are rendered as Markdown, everything else as plain
        (escaped) text. Scrolls to the newest message."""
        color = SENDER_COLORS.get(sender, "#3a2410")
        cursor = self._history.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        if not self._history.document().isEmpty():
            cursor.insertBlock()
        cursor.insertHtml(f'<b style="color:{color}">{html.escape(sender)}:</b> ')
        if sender == "Calcifer":
            cursor.insertFragment(QTextDocumentFragment.fromMarkdown(text))
        else:
            cursor.insertText(text)
        self._history.setTextCursor(cursor)
        self._history.ensureCursorVisible()

    def set_thinking(self, thinking: bool) -> None:
        """Disable input and show animated dots while the agent is working."""
        self._input.setEnabled(not thinking)
        self._send_button.setEnabled(not thinking)
        if thinking:
            self._dots = 0
            self._animate_thinking()
            self._dots_timer.start()
        else:
            self._dots_timer.stop()
            self._thinking.setText("")
            self._input.setFocus()

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

    def keyPressEvent(self, event: QKeyEvent) -> None:  # noqa: N802 - Qt override
        """Esc closes (hides) the chat; the conversation is kept in memory."""
        if event.key() == Qt.Key.Key_Escape:
            self.hide()
            return
        super().keyPressEvent(event)
