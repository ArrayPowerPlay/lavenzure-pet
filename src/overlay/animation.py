"""QPropertyAnimation helpers used by the behavior state machine."""
from __future__ import annotations

from PySide6.QtCore import QEasingCurve, QPoint, QPropertyAnimation


def bob_animation(widget, amplitude: int = 8, duration_ms: int = 1200) -> QPropertyAnimation:
    """Gentle up-down idle breathing motion, loops forever."""
    start = widget.pos()
    anim = QPropertyAnimation(widget, b"pos")
    anim.setDuration(duration_ms)
    anim.setStartValue(start)
    anim.setKeyValueAt(0.5, start + QPoint(0, -amplitude))
    anim.setEndValue(start)
    anim.setEasingCurve(QEasingCurve.InOutSine)
    anim.setLoopCount(-1)
    return anim


def move_to_animation(
    widget,
    target: QPoint,
    duration_ms: int = 2500,
    easing: QEasingCurve.Type = QEasingCurve.InOutQuad,
) -> QPropertyAnimation:
    """One-shot move used for the walk/float transitions."""
    anim = QPropertyAnimation(widget, b"pos")
    anim.setDuration(duration_ms)
    anim.setStartValue(widget.pos())
    anim.setEndValue(target)
    anim.setEasingCurve(easing)
    return anim


def jump_animation(widget, target: QPoint, duration_ms: int = 700) -> QPropertyAnimation:
    """Parabolic jump arc from the current position to a nearby point."""
    start = widget.pos()
    peak = QPoint((start.x() + target.x()) // 2, min(start.y(), target.y()) - 60)
    anim = QPropertyAnimation(widget, b"pos")
    anim.setDuration(duration_ms)
    anim.setKeyValueAt(0.0, start)
    anim.setKeyValueAt(0.5, peak)
    anim.setKeyValueAt(1.0, target)
    anim.setEasingCurve(QEasingCurve.OutInQuad)
    return anim
