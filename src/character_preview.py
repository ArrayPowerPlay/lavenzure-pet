"""Design playground for the flame character: run it to try every mood and motion in a normal window.

Usage (from the repo root):  .venv/Scripts/python.exe src/character_preview.py

Move the mouse to see the eyes follow it, press the buttons to switch moods, and use the motion
buttons to see lean / hop / squash. No API keys or tray icon needed.
"""
from __future__ import annotations

import math
import sys

from PySide6.QtCore import QElapsedTimer, QPointF, Qt, QTimer
from PySide6.QtGui import QColor, QCursor, QPainter
from PySide6.QtWidgets import QApplication, QGridLayout, QPushButton, QVBoxLayout, QWidget

from overlay.character import FlameCharacter, Mood


class Stage(QWidget):
    """Canvas that runs the character and can fake window movement to show body physics."""

    def __init__(self, scale: float = 1.6) -> None:
        super().__init__()
        self.character = FlameCharacter(scale=scale)
        self.setFixedSize(self.character.width * 2, self.character.height)
        self.dark = True
        self._fake_pos = QPointF(0, 0)  # pretend "window position" fed to the physics
        self._motion: str | None = None
        self._motion_t = 0.0
        self._clock = QElapsedTimer()
        self._clock.start()
        timer = QTimer(self)
        timer.setTimerType(Qt.TimerType.PreciseTimer)
        timer.timeout.connect(self._tick)
        timer.start(16)

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
        offset = QPointF(self.character.width / 2, 0)
        cursor = QPointF(self.mapFromGlobal(QCursor.pos())) - offset
        self.character.update(dt, self._fake_pos, cursor)
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802 - Qt override
        """Draw a dark or light backdrop (to check both desktop themes) and the character."""
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(38, 42, 50) if self.dark else QColor(236, 239, 243))
        painter.translate(self.character.width / 2, 0)
        self.character.paint(painter)
        painter.end()


def main() -> int:
    """Build the preview window with mood and motion buttons."""
    app = QApplication(sys.argv)
    root = QWidget()
    root.setWindowTitle("Flame character preview")
    stage = Stage()
    ch = stage.character
    layout = QVBoxLayout(root)
    layout.addWidget(stage)
    grid = QGridLayout()
    layout.addLayout(grid)

    def button(label: str, row: int, col: int, action) -> None:
        """Add one control button to the grid."""
        b = QPushButton(label)
        b.clicked.connect(action)
        grid.addWidget(b, row, col)

    def reset() -> None:
        """Back to the calm base mood."""
        ch.stop_transient()
        ch.set_alert(False)
        ch.set_thinking(False)

    button("Normal", 0, 0, reset)
    button("Happy (click)", 0, 1, lambda: ch.play(Mood.HAPPY, 1.4))
    button("Surprised (drag)", 0, 2, lambda: ch.play(Mood.SURPRISED, 2.0))
    button("Talking", 0, 3, lambda: ch.play(Mood.TALKING, 4.0))
    button("Thinking", 1, 0, lambda: (reset(), ch.set_thinking(True)))
    button("Alert", 1, 1, lambda: (reset(), ch.set_alert(True)))
    button("Walk", 1, 2, lambda: stage.start_motion("walk"))
    button("Float", 1, 3, lambda: stage.start_motion("float"))
    button("Jump", 2, 0, lambda: stage.start_motion("jump"))
    button("Stop moving", 2, 1, lambda: stage.start_motion(None))
    button("Hop", 2, 2, lambda: ch.bounce(1.0))

    def toggle_bg() -> None:
        """Switch the backdrop between dark and light."""
        stage.dark = not stage.dark

    button("Dark/Light bg", 2, 3, toggle_bg)
    root.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
