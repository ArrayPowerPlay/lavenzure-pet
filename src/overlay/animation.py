"""Window-movement animation helpers used by the behavior state machine.

These only move the pet *window* around the screen. Everything the character does with its own
body while moving (lean, stretch, hop, squash on landing) is derived automatically from that
movement inside ``overlay.character.FlameCharacter``.

They drive the window's sub-pixel ``exactPos`` (see ``OverlaySprite``) rather than its whole-pixel
``pos``, so slow moves glide instead of stepping.
"""
from __future__ import annotations

import math

from PySide6.QtCore import QEasingCurve, QPoint, QPointF, QPropertyAnimation, QVariantAnimation


def travel_duration_ms(start: QPoint, target: QPoint, speed_px_s: float,
                       min_ms: int = 600, max_ms: int = 12000) -> int:
    """Duration that moves at roughly ``speed_px_s`` between two points, clamped to a range."""
    distance = math.hypot(target.x() - start.x(), target.y() - start.y())
    return int(max(min_ms, min(max_ms, distance / speed_px_s * 1000)))


def move_to_animation(
    widget,
    target: QPoint,
    duration_ms: int,
    easing: QEasingCurve.Type = QEasingCurve.Type.InOutSine,
) -> QPropertyAnimation:
    """One-shot straight move of ``widget`` to ``target`` (used for walk and float)."""
    anim = QPropertyAnimation(widget, b"exactPos")
    anim.setDuration(duration_ms)
    anim.setStartValue(widget.exact_pos())
    anim.setEndValue(QPointF(target))
    anim.setEasingCurve(easing)
    return anim


def jump_animation(widget, target: QPoint, height_px: int = 110,
                   duration_ms: int = 720) -> QVariantAnimation:
    """Physically shaped jump: constant horizontal speed and a true parabolic vertical arc.

    The arc peaks ``height_px`` above the higher of the start/target points.
    """
    start = widget.exact_pos()
    sx, sy = start.x(), start.y()
    tx, ty = target.x(), target.y()
    peak_rise = (sy - min(sy, ty)) + height_px  # rise above the start point

    anim = QVariantAnimation(widget)
    anim.setStartValue(0.0)
    anim.setEndValue(1.0)
    anim.setDuration(duration_ms)
    anim.setEasingCurve(QEasingCurve.Type.Linear)

    def apply(progress: float) -> None:
        """Place the window on the parabola for the given progress (0..1)."""
        x = sx + (tx - sx) * progress
        base_y = sy + (ty - sy) * progress
        y = base_y - 4.0 * peak_rise * progress * (1.0 - progress)
        widget.set_exact_pos(QPointF(x, y))

    anim.valueChanged.connect(apply)
    return anim
