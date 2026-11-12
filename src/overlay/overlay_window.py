"""Always-on-top, transparent window that hosts and animates the code-drawn flame character.

Smooth motion:
- The frame loop is driven by Qt's animation clock (``_FrameClock``), the same clock that runs the
  window-movement animations, so the window moves and the character redraws in the same step
  instead of drifting against each other (which shows up as stutter).
- The window position is kept as floating point (``exactPos``). The real window can only sit on
  whole pixels, so the leftover fraction is applied as a drawing offset; a slow walk then glides
  instead of stepping 1 px / 2 px / 1 px.

Click-through is handled by Windows itself: for per-pixel-alpha (layered) windows, fully
transparent pixels let mouse events fall through to the app underneath, so only the visible flame
catches clicks. (No ``setMask()`` — a mask would also clip the soft glow and the embers.)
"""
from __future__ import annotations

import math

import config
from PySide6.QtCore import (QAbstractAnimation, QElapsedTimer, QPoint, QPointF, Property, Qt,
                            Signal)
from PySide6.QtGui import QCursor, QMouseEvent, QPainter
from PySide6.QtWidgets import QWidget

from overlay.character import FlameCharacter


class _FrameClock(QAbstractAnimation):
    """Endless animation used only as a frame clock.

    Qt advances every running animation in one pass of its shared timer, so ticking the pet from
    here keeps redraws in lock-step with the window-movement animations.
    """

    def __init__(self, parent, on_frame) -> None:
        """Call ``on_frame()`` on every pass of Qt's animation timer while running."""
        super().__init__(parent)
        self._on_frame = on_frame

    def duration(self) -> int:
        """-1 = runs until stopped."""
        return -1

    def updateCurrentTime(self, current_time: int) -> None:  # noqa: N802 - Qt override
        """Forward each animation-timer pass to the window."""
        self._on_frame()


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

        self.character = FlameCharacter(
            scale=float(config.get("character.scale", 1.0)),
            renderer=str(config.get("character.flame_renderer", "shader")),
        )
        self.resize(self.character.width, self.character.height)

        fps = max(10, int(config.get("character.fps", 60)))
        # Skip animation-timer passes that come sooner than this (allows fps below ~60).
        self._min_frame_ns = int(1e9 / fps) - 3_000_000
        self._frame_clock = _FrameClock(self, self._tick)
        self._clock = QElapsedTimer()

        self._exact = QPointF(self.pos())  # true (sub-pixel) top-left on screen
        self._frac = QPointF()             # exact - actual window position, drawn as an offset

        self._pressed = False
        self._dragging = False
        self._press_global = QPoint()
        self._drag_offset = QPointF()

    # ------------------------------------------------------------------ position

    def exact_pos(self) -> QPointF:
        """Sub-pixel top-left of the pet on screen (what movement animations should drive)."""
        return QPointF(self._exact)

    def set_exact_pos(self, pos: QPointF, immediate: bool = False) -> None:
        """Move the pet to a sub-pixel position.

        While the frame loop runs, the window follows on the next frame (in step with the redraw);
        ``immediate`` (or a hidden window) moves it right away.
        """
        self._exact = QPointF(pos)
        if immediate or self._frame_clock.state() != QAbstractAnimation.State.Running:
            self._apply_position()
            self.update()

    exactPos = Property(QPointF, exact_pos, set_exact_pos)  # animatable by QPropertyAnimation

    def _apply_position(self) -> None:
        """Snap the real window to the whole pixel at/below ``_exact``; keep the rest as offset."""
        whole = QPoint(math.floor(self._exact.x()), math.floor(self._exact.y()))
        if whole != self.pos():
            self.move(whole)
        self._frac = self._exact - QPointF(whole)

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
        self._exact = QPointF(self.pos())  # the system may have placed the window itself
        self._frac = QPointF()
        self._clock.restart()
        self._frame_clock.start()

    def hideEvent(self, event) -> None:  # noqa: N802 - Qt override
        """Stop redrawing while hidden (e.g. "Hide Pet" in the tray) to save CPU."""
        super().hideEvent(event)
        self._frame_clock.stop()

    def _tick(self) -> None:
        """Advance the character by the real elapsed time, move the window, and repaint."""
        if self._clock.nsecsElapsed() < self._min_frame_ns:
            return
        dt = self._clock.nsecsElapsed() / 1e9
        self._clock.restart()
        self._apply_position()
        cursor = QPointF(self.mapFromGlobal(QCursor.pos())) - self._frac
        self.character.update(dt, self.exact_pos(), cursor)
        # Paint right away (not just schedule it) so the new position and the matching drawing
        # offset reach the screen as close together as possible.
        self.repaint()

    def paintEvent(self, event) -> None:  # noqa: N802 - Qt override
        """Clear to fully transparent, then let the character draw itself (sub-pixel shifted)."""
        painter = QPainter(self)
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Source)
        painter.fillRect(self.rect(), Qt.GlobalColor.transparent)
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)
        painter.translate(self._frac)
        self.character.paint(painter)
        painter.end()

    # ------------------------------------------------------------------ mouse interaction

    def mousePressEvent(self, event: QMouseEvent) -> None:  # noqa: N802 - Qt override
        """Left press arms click/drag detection; right press opens the chat."""
        if event.button() == Qt.MouseButton.LeftButton:
            self._pressed = True
            self._dragging = False
            self._press_global = event.globalPosition().toPoint()
            self._drag_offset = event.globalPosition() - self._exact
        elif event.button() == Qt.MouseButton.RightButton:
            self.right_clicked.emit()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:  # noqa: N802 - Qt override
        """Turn a press into a drag once the cursor moves far enough, then follow the cursor."""
        if not self._pressed:
            return
        if not self._dragging:
            moved = event.globalPosition().toPoint() - self._press_global
            if moved.manhattanLength() < self.DRAG_THRESHOLD_PX:
                return
            self._dragging = True
            self.drag_started.emit()
        # Follow the cursor at once (no frame of lag) so the pet feels attached to the mouse.
        self.set_exact_pos(event.globalPosition() - self._drag_offset, immediate=True)

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
