"""Small always-on-top bubble shown above the pet for click reactions, jokes, reminders and alerts.

The bubble is its own top-level window. While visible it re-centres itself over the pet's head on
every frame, so it travels along when the pet walks, floats, jumps or is dragged.
"""
from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import QPoint, Qt, QTimer
from PySide6.QtWidgets import QLabel

FOLLOW_INTERVAL_MS = 16  # ~60 fps, same rate as the pet


class SpeechBubble(QLabel):
    """Word-wrapped label that follows a moving anchor point (the top of the pet's head).

    ``anchor_fn`` returns the global screen point the bubble should sit above.
    """

    def __init__(self, anchor_fn: Callable[[], QPoint]) -> None:
        """Create the hidden bubble window; nothing shows until ``show_text``."""
        super().__init__(
            None,
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
            | Qt.WindowType.WindowDoesNotAcceptFocus,
        )
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setStyleSheet(
            "background-color: rgba(255,250,230,235); border: 1px solid #d08a2e; "
            "border-radius: 8px; padding: 6px 10px; color: #3a2410; font-size: 12px;"
        )
        self.setWordWrap(True)
        self.setMaximumWidth(240)
        self.hide()
        self._anchor_fn = anchor_fn

        self._auto_hide_timer = QTimer(self)
        self._auto_hide_timer.setSingleShot(True)
        self._auto_hide_timer.timeout.connect(self.hide)

        self._follow_timer = QTimer(self)
        self._follow_timer.setInterval(FOLLOW_INTERVAL_MS)
        self._follow_timer.timeout.connect(self._follow)

    def show_text(self, text: str, auto_hide_ms: int | None = 4000) -> None:
        """Show ``text`` above the pet.

        ``auto_hide_ms=None`` keeps the bubble visible until ``hide()`` is called (alerts).
        """
        self.setText(text)
        self.adjustSize()
        self._follow()
        self.show()
        self.raise_()
        self._follow_timer.start()
        self._auto_hide_timer.stop()
        if auto_hide_ms is not None:
            self._auto_hide_timer.start(auto_hide_ms)

    def is_sticky(self) -> bool:
        """True while a bubble without auto-hide (an alert) is on screen."""
        return self.isVisible() and not self._auto_hide_timer.isActive()

    def _follow(self) -> None:
        """Centre the bubble over the anchor, kept inside the screen's available area."""
        anchor = self._anchor_fn()
        screen = self.screen().availableGeometry()
        x = anchor.x() - self.width() // 2
        x = max(screen.left(), min(x, screen.right() - self.width()))
        y = max(screen.top(), anchor.y() - self.height() - 4)
        if (x, y) != (self.x(), self.y()):
            self.move(x, y)

    def hideEvent(self, event) -> None:  # noqa: N802 - Qt override
        """Stop following (and any pending auto-hide) once hidden."""
        super().hideEvent(event)
        self._follow_timer.stop()
        self._auto_hide_timer.stop()
