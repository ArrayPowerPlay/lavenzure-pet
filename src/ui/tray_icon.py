"""The system-tray icon: a small portrait of the pet, drawn by ``FlameCharacter`` itself.

The character is rendered once, large, into an offscreen image (calm face, a settled flame) and
scaled down to the usual tray sizes, so the icon always matches the pet on screen.
"""
from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QIcon, QImage, QPainter, QPixmap

from overlay.character import FlameCharacter

ICON_SIZES = (16, 20, 24, 32, 40, 48, 64, 128, 256)
_RENDER_SCALE = 2.4      # draw big, then scale down (sharper edges than drawing small)


def render_portrait(seed: int = 11) -> QImage:
    """A square, transparent picture of the pet's flame (body + tongues), about 400 px wide."""
    ch = FlameCharacter(scale=_RENDER_SCALE, seed=seed, renderer="metaball")
    for _ in range(90):                       # let the fire and the face settle
        ch.update(1 / 60, QPointF(0.0, 0.0), None)
    canvas = QImage(ch.width, ch.height, QImage.Format.Format_ARGB32_Premultiplied)
    canvas.fill(Qt.GlobalColor.transparent)
    painter = QPainter(canvas)
    ch.paint(painter)
    painter.end()
    r = ch.R
    side = 3.3 * r
    crop = QRectF(ch.feet.x() - side / 2, ch.feet.y() - side + 0.12 * r, side, side)
    return canvas.copy(crop.toAlignedRect())


def make_tray_icon() -> QIcon:
    """``QIcon`` with the portrait at every common tray size."""
    portrait = render_portrait()
    icon = QIcon()
    for size in ICON_SIZES:
        scaled = portrait.scaled(size, size, Qt.AspectRatioMode.KeepAspectRatio,
                                 Qt.TransformationMode.SmoothTransformation)
        icon.addPixmap(QPixmap.fromImage(scaled))
    return icon
