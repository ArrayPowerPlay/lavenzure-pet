"""Always-on-top, transparent sprite window with alpha-based click-through."""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QPoint, Qt, Signal
from PySide6.QtGui import QMouseEvent, QPixmap
from PySide6.QtWidgets import QLabel, QWidget

ASSETS_DIR = Path(__file__).resolve().parent.parent.parent / "assets" / "calcifer"


class OverlaySprite(QWidget):
    """Renders Calcifer; only the non-transparent pixels of the sprite catch mouse events."""

    clicked = Signal()
    right_clicked = Signal()
    drag_started = Signal()
    drag_ended = Signal()

    SIZE = 160

    def __init__(self) -> None:
        super().__init__(
            None,
            Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool | Qt.NoDropShadowWindowHint,
        )
        self.setAttribute(Qt.WA_TranslucentBackground)

        self._label = QLabel(self)
        self._dragging = False
        self._drag_offset = QPoint()

        self.set_layer("body_base.png")

    def set_layer(self, filename: str) -> None:
        """Swap the currently displayed sprite frame and refresh the click-through mask."""
        path = ASSETS_DIR / filename
        pixmap = QPixmap(str(path)) if path.exists() else _placeholder_pixmap(self.SIZE)
        if pixmap.width() != self.SIZE or pixmap.height() != self.SIZE:
            pixmap = pixmap.scaled(
                self.SIZE, self.SIZE, Qt.KeepAspectRatio, Qt.SmoothTransformation
            )
        self._label.setPixmap(pixmap)
        self._label.resize(pixmap.size())
        self.resize(pixmap.size())
        self.setMask(pixmap.mask())

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.LeftButton:
            self._dragging = True
            self._drag_offset = event.globalPosition().toPoint() - self.pos()
            self.drag_started.emit()
        elif event.button() == Qt.RightButton:
            self.right_clicked.emit()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self._dragging:
            self.move(event.globalPosition().toPoint() - self._drag_offset)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.LeftButton and self._dragging:
            self._dragging = False
            self.drag_ended.emit()
            self.clicked.emit()


def _placeholder_pixmap(size: int) -> QPixmap:
    """Draw a simple flame shape until real cutout PNG layers are added (see ANIMATION_TUTORIAL.md)."""
    from PySide6.QtGui import QBrush, QColor, QPainter, QPainterPath

    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)
    path = QPainterPath()
    path.moveTo(size * 0.5, size * 0.05)
    path.cubicTo(size * 0.9, size * 0.35, size * 0.75, size * 0.6, size * 0.5, size * 0.95)
    path.cubicTo(size * 0.25, size * 0.6, size * 0.1, size * 0.35, size * 0.5, size * 0.05)
    painter.setBrush(QBrush(QColor(255, 140, 0)))
    painter.setPen(Qt.NoPen)
    painter.drawPath(path)
    painter.end()
    return pixmap
