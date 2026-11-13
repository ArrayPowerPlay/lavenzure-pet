"""The Settings window opened from the tray menu.

For now it holds the two performance modes of roadmap Phase 12, so they can be tried out live
and compared (any combination works):

- **Adaptive frame rate** - 60 fps only while the pet moves or reacts, fewer frames when it stands
  still or sleeps.
- **Lite flame** - the flame is rendered at a lower internal resolution (less GPU work).

A small live readout shows how many frames per second the pet is drawing right now and why
(moving / standing still / asleep), so the effect of each mode is visible at once.

The window only *reports* changes (``adaptive_fps_toggled`` / ``lite_flame_toggled``); the app
applies them to the pet and remembers them (``user_settings``).
"""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QCheckBox, QLabel, QPushButton, QVBoxLayout, QWidget

import config

STYLE = """
QWidget#settings { background: #fff8ea; }
QLabel { color: #6c0e16; font-family: "Segoe UI", "Arial"; }
QLabel#title { font-size: 15pt; font-weight: 600; }
QLabel#section { font-size: 11pt; font-weight: 600; margin-top: 4px; }
QLabel#note { font-size: 9pt; color: #8a4a14; margin-left: 26px; }
QLabel#live { font-size: 9pt; color: #8a4a14; background: #fdecc8; border-radius: 8px;
              padding: 6px 10px; }
QCheckBox { color: #6c0e16; font-family: "Segoe UI", "Arial"; font-size: 10pt; spacing: 8px; }
QPushButton {
    background: #f6a23a; color: white; border: none; border-radius: 12px;
    padding: 6px 22px; font-family: "Segoe UI", "Arial"; font-size: 10pt; font-weight: 600;
}
QPushButton:hover { background: #f08a1c; }
"""

# Activity level reported by the pet window -> words for the live readout.
LEVEL_TEXT = {"active": "moving or reacting", "calm": "standing still", "asleep": "asleep"}


class SettingsWindow(QWidget):
    """Small always-on-top window with the performance switches and a live frame-rate readout."""

    adaptive_fps_toggled = Signal(bool)
    lite_flame_toggled = Signal(bool)

    def __init__(self, adaptive_fps: bool = False, lite_flame: bool = False) -> None:
        """Build the window; the check boxes start at the given current values."""
        super().__init__(None, Qt.WindowType.Window | Qt.WindowType.WindowStaysOnTopHint)
        self.setObjectName("settings")
        self.setWindowTitle("Lavenzure - Settings")
        self.setFixedWidth(380)
        self.setStyleSheet(STYLE)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 18)
        layout.setSpacing(6)

        title = QLabel("Settings")
        title.setObjectName("title")
        section = QLabel("Performance")
        section.setObjectName("section")

        self.adaptive_box = QCheckBox("Adaptive frame rate")
        self.adaptive_box.setChecked(adaptive_fps)
        self.adaptive_box.toggled.connect(self.adaptive_fps_toggled)
        adaptive_note = self._note(
            f"{config.get('character.fps', 60)} fps only while Lavenzure moves or reacts; "
            f"{config.get('performance.calm_fps', 30)} fps when standing still, "
            f"{config.get('performance.sleep_fps', 15)} fps asleep. Saves CPU and GPU.")

        self.lite_box = QCheckBox("Lite flame")
        self.lite_box.setChecked(lite_flame)
        self.lite_box.toggled.connect(self.lite_flame_toggled)
        lite_note = self._note("Draws the fire at a lower resolution: much less GPU work, "
                               "slightly softer flame edges.")

        self.live = QLabel("Drawing: -")
        self.live.setObjectName("live")

        close = QPushButton("Close")
        close.clicked.connect(self.close)

        for widget in (title, section, self.adaptive_box, adaptive_note, self.lite_box,
                       lite_note):
            layout.addWidget(widget)
        layout.addSpacing(6)
        layout.addWidget(self.live)
        layout.addSpacing(8)
        layout.addWidget(close, alignment=Qt.AlignmentFlag.AlignRight)

    @staticmethod
    def _note(text: str) -> QLabel:
        """A small explanatory line under a check box."""
        note = QLabel(text)
        note.setObjectName("note")
        note.setWordWrap(True)
        return note

    def show_frame_rate(self, fps: float, level: str) -> None:
        """Update the live readout (connected to the pet window's ``frame_rate_changed``)."""
        self.live.setText(f"Drawing: {fps:.0f} fps ({LEVEL_TEXT.get(level, level)})")

    def open(self) -> None:
        """Show the window (or bring it to the front if it is already open)."""
        self.show()
        self.raise_()
        self.activateWindow()
