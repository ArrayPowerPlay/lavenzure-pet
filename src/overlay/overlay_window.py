"""Always-on-top, transparent window that hosts and animates the code-drawn flame character.

The window redraws ``FlameCharacter`` on a fixed-rate timer. Click-through is handled by Windows
itself: for per-pixel-alpha (layered) windows, fully transparent pixels let mouse events fall
through to the app underneath, so only the visible flame catches clicks. (No ``setMask()`` — a
mask would also clip the soft glow and the embers.)
"""
from __future__ import annotations

import config
from PySide6.QtCore import QElapsedTimer, QPoint, QPointF, Qt, QTimer, Signal
from PySide6.QtGui import QCursor, QMouseEvent, QPainter
from PySide6.QtWidgets import QWidget

from overlay.character import FlameCharacter


class OverlaySprite(QWidget):
    """Frameless pet window. Emits ``clicked`` for a press+release without movement, and
    ``drag_started``/``drag_ended`` once the mouse has moved more than a few pixels."""

    clicked = Signal()
    right_clicked = Signal()
    drag_started = Signal()
    drag_ended = Signal()

    DRAG_THRESHOLD_PX = 6

    def __init__(self) -> None:
        super().__init__(
            None,
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
            | Qt.WindowType.NoDropShadowWindowHint,
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        self.character = FlameCharacter(scale=float(config.get("character.scale", 1.0)))
        self.resize(self.character.width, self.character.height)

        fps = max(10, int(config.get("character.fps", 60)))
        self._frame_timer = QTimer(self)
        self._frame_timer.setTimerType(Qt.TimerType.PreciseTimer)
        self._frame_timer.setInterval(1000 // fps)
        self._frame_timer.timeout.connect(self._tick)
        self._clock = QElapsedTimer()

        self._pressed = False
        self._dragging = False
        self._press_global = QPoint()
        self._drag_offset = QPoint()

    # ------------------------------------------------------------------ geometry helpers

    def feet_margin(self) -> int:
        """Pixels between the character's feet and the bottom edge of the window."""
        return int(self.height() - self.character.feet.y())

    def bubble_anchor(self) -> QPoint:
        """Global screen point just above the flame tips, for positioning speech bubbles."""
        return self.mapToGlobal(self.character.head_top().toPoint())

    # ------------------------------------------------------------------ animation loop

    def showEvent(self, event) -> None:  # noqa: N802 - Qt override
        """Start the frame loop whenever the pet becomes visible."""
        super().showEvent(event)
        self._clock.restart()
        self._frame_timer.start()

    def hideEvent(self, event) -> None:  # noqa: N802 - Qt override
        """Stop redrawing while hidden (e.g. "Hide Pet" in the tray) to save CPU."""
        super().hideEvent(event)
        self._frame_timer.stop()

    def _tick(self) -> None:
        """Advance the character simulation by the real elapsed time and schedule a repaint."""
        dt = self._clock.restart() / 1000.0
        cursor = QPointF(self.mapFromGlobal(QCursor.pos()))
        self.character.update(dt, QPointF(self.pos()), cursor)
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802 - Qt override
        """Clear to fully transparent, then let the character draw itself."""
        painter = QPainter(self)
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Source)
        painter.fillRect(self.rect(), Qt.GlobalColor.transparent)
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)
        self.character.paint(painter)
        painter.end()

    # ------------------------------------------------------------------ mouse interaction

    def mousePressEvent(self, event: QMouseEvent) -> None:  # noqa: N802 - Qt override
        """Left press arms click/drag detection; right press opens the chat."""
        if event.button() == Qt.MouseButton.LeftButton:
            self._pressed = True
            self._dragging = False
            self._press_global = event.globalPosition().toPoint()
            self._drag_offset = self._press_global - self.pos()
        elif event.button() == Qt.MouseButton.RightButton:
            self.right_clicked.emit()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:  # noqa: N802 - Qt override
        """Turn a press into a drag once the cursor moves far enough, then follow the cursor."""
        if not self._pressed:
            return
        global_pos = event.globalPosition().toPoint()
        if not self._dragging:
            if (global_pos - self._press_global).manhattanLength() < self.DRAG_THRESHOLD_PX:
                return
            self._dragging = True
            self.drag_started.emit()
        self.move(global_pos - self._drag_offset)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:  # noqa: N802 - Qt override
        """Finish a drag, or report a plain click if the mouse never moved."""
        if event.button() != Qt.MouseButton.LeftButton or not self._pressed:
            return
        self._pressed = False
        if self._dragging:
            self._dragging = False
            self.drag_ended.emit()
        else:
            self.clicked.emit()
