"""Simple always-on-top text chat window; history is in-memory for the current session only."""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QLineEdit,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QHBoxLayout,
    QWidget,
)


class ChatWindow(QWidget):
    message_sent = Signal(str)

    def __init__(self) -> None:
        super().__init__(None, Qt.WindowStaysOnTopHint)
        self.setWindowTitle("Calcifer")
        self.resize(360, 420)

        self._history = QTextEdit(self)
        self._history.setReadOnly(True)

        self._input = QLineEdit(self)
        self._input.setPlaceholderText("Ask Calcifer something...")
        self._input.returnPressed.connect(self._on_send)

        send_button = QPushButton("Send", self)
        send_button.clicked.connect(self._on_send)

        layout = QVBoxLayout(self)
        layout.addWidget(self._history)
        row = QHBoxLayout()
        row.addWidget(self._input)
        row.addWidget(send_button)
        layout.addLayout(row)

    def _on_send(self) -> None:
        text = self._input.text().strip()
        if not text:
            return
        self.append_message("You", text)
        self._input.clear()
        self.message_sent.emit(text)

    def append_message(self, sender: str, text: str) -> None:
        self._history.append(f"<b>{sender}:</b> {text}")

    def set_thinking(self, thinking: bool) -> None:
        self._input.setEnabled(not thinking)
