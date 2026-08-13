"""Small always-on-top label shown above the pet for click reactions, jokes, and alerts."""
from __future__ import annotations

from PySide6.QtCore import QTimer, Qt


from PySide6.QtWidgets import QLabel


class SpeechBubble(QLabel):
    def __init__(self) -> None:
        super().__init__(None, Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setStyleSheet(
            "background-color: rgba(255,250,230,235); border: 1px solid #d08a2e; "
            "border-radius: 8px; padding: 6px 10px; color: #3a2410; font-size: 12px;"
        )
        self.setWordWrap(True)
        self.setMaximumWidth(220)
        self.hide()
        self._auto_hide_timer = QTimer(self)
        self._auto_hide_timer.setSingleShot(True)
        self._auto_hide_timer.timeout.connect(self.hide)

    def show_above(self, anchor_pos, text: str, auto_hide_ms: int | None = 4000) -> None:
        """auto_hide_ms=None keeps the bubble visible until hide() is called explicitly (alerts)."""
        self.setText(text)
        self.adjustSize()
        self.move(anchor_pos.x(), anchor_pos.y() - self.height() - 10)
        self.show()
        self.raise_()
        self._auto_hide_timer.stop()
        if auto_hide_ms is not None:
            self._auto_hide_timer.start(auto_hide_ms)
