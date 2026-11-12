"""Design playground for the flame character: try every mood and motion in a normal window.

Usage (from the repo root):  .venv-win/Scripts/python.exe src/character_preview.py [renderer ...]

By default it shows the three flame body renderers side by side (``metaball``, ``shader``,
``baked``) so they can be compared; pass renderer names to show only those. Each panel says which
renderer is really running (it may have fallen back to ``metaball``), the current fire "weather"
and the update cost per frame. Move the mouse to see the eyes follow it, press the buttons to
switch moods (they apply to every panel), and use the motion buttons to see lean / hop / squash.
No API keys or tray icon needed.
"""
from __future__ import annotations

import math
import sys

from PySide6.QtCore import QElapsedTimer, QPointF, Qt, QTimer
from PySide6.QtGui import QColor, QCursor, QPainter
from PySide6.QtWidgets import (
    QApplication,
    QGridLayout,
    QHBoxLayout,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from overlay.character import FlameCharacter, Mood

RENDERERS = ("metaball", "shader", "baked")


class Stage(QWidget):
    """Canvas that runs one character and can fake window movement to show body physics."""

    def __init__(self, renderer: str, scale: float = 1.4) -> None:
        """Create a character using flame ``renderer`` at ``scale``."""
        super().__init__()
        self.character = FlameCharacter(scale=scale, renderer=renderer)
        self.requested = renderer
        self.setFixedSize(int(self.character.width * 1.6), self.character.height + 24)
        self.dark = True
        self._fake_pos = QPointF(0, 0)  # pretend "window position" fed to the physics
        self._motion: str | None = None
        self._motion_t = 0.0
        self._clock = QElapsedTimer()
        self._clock.start()
        self._cost_ms = 0.0
        timer = QTimer(self)
        timer.setTimerType(Qt.TimerType.PreciseTimer)
        timer.timeout.connect(self._tick)
        timer.start(16)

    def _offset(self) -> QPointF:
        """Where the character's canvas sits inside this panel."""
        return QPointF((self.width() - self.character.width) / 2, 24)

    def start_motion(self, kind: str | None) -> None:
        """Simulate 'walk' (back and forth), 'float' (circles) or 'jump' (one arc); None = stop."""
        self._motion = kind
        self._motion_t = 0.0
        if kind == "jump":
            self.character.anticipate()

    def _tick(self) -> None:
        """Advance fake motion + character, then repaint."""
        dt = self._clock.restart() / 1000.0
        self._motion_t += dt
        t = self._motion_t
        if self._motion == "walk":
            self._fake_pos = QPointF(math.sin(t * 0.6) * 260, 0)
        elif self._motion == "float":
            self._fake_pos = QPointF(math.cos(t * 1.2) * 120, math.sin(t * 2.4) * 60)
        elif self._motion == "jump":
            p = min(1.0, max(0.0, (t - 0.17) / 0.72))
            self._fake_pos = QPointF(p * 160, -4 * 110 * p * (1 - p))
            if t > 1.6:
                self._motion, self._fake_pos = None, QPointF(0, 0)
        cursor = QPointF(self.mapFromGlobal(QCursor.pos())) - self._offset()
        timer = QElapsedTimer()
        timer.start()
        self.character.update(dt, self._fake_pos, cursor)
        self._cost_ms += (timer.nsecsElapsed() / 1e6 - self._cost_ms) * 0.05
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802 - Qt override
        """Draw a dark or light backdrop (to check both desktop themes), a label and the pet."""
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(38, 42, 50) if self.dark else QColor(236, 239, 243))
        painter.setPen(QColor(200, 205, 215) if self.dark else QColor(60, 64, 72))
        ch = self.character
        label = ch.renderer_name
        if label != self.requested:
            label = f"{self.requested} -> {label} (fallback)"
        painter.drawText(8, 16, f"{label}   [{ch.weather.state}]   {self._cost_ms:.1f} ms")
        painter.translate(self._offset())
        ch.paint(painter)
        painter.end()


def main() -> int:
    """Build the preview window with one panel per renderer and shared mood/motion buttons."""
    app = QApplication(sys.argv)
    names = [a for a in sys.argv[1:] if not a.startswith("-")] or list(RENDERERS)
    root = QWidget()
    root.setWindowTitle("Flame character preview")
    stages = [Stage(name) for name in names]
    chars = [s.character for s in stages]
    layout = QVBoxLayout(root)
    row = QHBoxLayout()
    for stage in stages:
        row.addWidget(stage)
    layout.addLayout(row)
    grid = QGridLayout()
    layout.addLayout(grid)

    def button(label: str, r: int, c: int, action) -> None:
        """Add one control button to the grid."""
        b = QPushButton(label)
        b.clicked.connect(action)
        grid.addWidget(b, r, c)

    def each(fn):
        """Wrap ``fn(character)`` so a button applies it to every panel."""
        return lambda: [fn(ch) for ch in chars]

    def reset(ch: FlameCharacter) -> None:
        """Back to the calm base mood."""
        ch.stop_transient()
        ch.set_alert(False)
        ch.set_thinking(False)

    button("Normal", 0, 0, each(reset))
    button("Happy (click)", 0, 1, each(lambda ch: ch.play(Mood.HAPPY, 1.4)))
    button("Surprised (drag)", 0, 2, each(lambda ch: ch.play(Mood.SURPRISED, 2.0)))
    button("Talking", 0, 3, each(lambda ch: ch.play(Mood.TALKING, 4.0)))
    button("Thinking", 1, 0, each(lambda ch: (reset(ch), ch.set_thinking(True))))
    button("Alert", 1, 1, each(lambda ch: (reset(ch), ch.set_alert(True))))
    button("Walk", 1, 2, lambda: [s.start_motion("walk") for s in stages])
    button("Float", 1, 3, lambda: [s.start_motion("float") for s in stages])
    button("Jump", 2, 0, lambda: [s.start_motion("jump") for s in stages])
    button("Stop moving", 2, 1, lambda: [s.start_motion(None) for s in stages])
    button("Hop", 2, 2, each(lambda ch: ch.bounce(1.0)))

    def toggle_bg() -> None:
        """Switch the backdrop between dark and light."""
        for s in stages:
            s.dark = not s.dark

    button("Dark/Light bg", 2, 3, toggle_bg)
    root.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
