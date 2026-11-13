"""The Settings window opened from the tray menu.

For now it holds the performance options of roadmap Phase 12, so they can be tried out live and
compared (any combination works):

- **Frame rate** - 60 / 45 / 30 fps for every animation (the most frames drawn per second).
- **Adaptive frame rate** - full frame rate only while the pet moves or reacts, fewer frames when
  it stands still or sleeps.

(The lite flame is no longer a switch here: the user chose it, so it is always on - see
``performance.lite_flame`` in config.yaml.)

A small live readout shows how many frames per second the pet is drawing right now and why
(moving / standing still / asleep), so the effect of each mode is visible at once.

The window only *reports* changes (``max_fps_changed`` / ``adaptive_fps_toggled``); the app
applies them to the pet and remembers them (``user_settings``).
"""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QRadioButton,
    QVBoxLayout,
    QWidget,
)

import config

STYLE = """
QWidget#settings { background: #fff8ea; }
QLabel { color: #6c0e16; font-family: "Segoe UI", "Arial"; }
QLabel#title { font-size: 15pt; font-weight: 600; }
QLabel#section { font-size: 11pt; font-weight: 600; margin-top: 4px; }
QLabel#note { font-size: 9pt; color: #8a4a14; margin-left: 26px; }
QLabel#live { font-size: 9pt; color: #8a4a14; background: #fdecc8; border-radius: 8px;
              padding: 6px 10px; }
QCheckBox, QRadioButton { color: #6c0e16; font-family: "Segoe UI", "Arial"; font-size: 10pt;
                          spacing: 8px; }
QPushButton {
    background: #f6a23a; color: white; border: none; border-radius: 12px;
    padding: 6px 22px; font-family: "Segoe UI", "Arial"; font-size: 10pt; font-weight: 600;
}
QPushButton:hover { background: #f08a1c; }
"""

# Frame-rate caps offered in the window.
FPS_CHOICES = (60, 45, 30)

# Activity level reported by the pet window -> words for the live readout.
LEVEL_TEXT = {"active": "moving or reacting", "calm": "standing still", "asleep": "asleep"}


class SettingsWindow(QWidget):
    """Small always-on-top window with the performance switches and a live frame-rate readout."""

    max_fps_changed = Signal(int)
    adaptive_fps_toggled = Signal(bool)

    def __init__(self, adaptive_fps: bool = False, max_fps: int = 60) -> None:
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

        fps_label = QLabel("Frame rate")
        fps_row = QHBoxLayout()
        fps_row.setContentsMargins(0, 0, 0, 0)
        self.fps_group = QButtonGroup(self)
        self.fps_buttons: dict[int, QRadioButton] = {}
        for fps in FPS_CHOICES:
            button = QRadioButton(f"{fps} fps")
            button.setChecked(fps == max_fps)
            self.fps_group.addButton(button, fps)
            self.fps_buttons[fps] = button
            fps_row.addWidget(button)
        fps_row.addStretch(1)
        self.fps_group.idToggled.connect(self._on_fps_toggled)
        fps_note = self._note("The most frames drawn per second, for every animation. Lower = "
                              "less CPU and GPU, less smooth motion. 45 fps on a 60 Hz screen "
                              "draws 3 refreshes out of 4, so motion can look a bit uneven.")

        self.adaptive_box = QCheckBox("Adaptive frame rate")
        self.adaptive_box.setChecked(adaptive_fps)
        self.adaptive_box.toggled.connect(self.adaptive_fps_toggled)
        adaptive_note = self._note(
            "Full frame rate only while Lavenzure moves or reacts; "
            f"{config.get('performance.calm_fps', 30)} fps when standing still, "
            f"{config.get('performance.sleep_fps', 15)} fps asleep. Saves CPU and GPU.")

        self.live = QLabel("Drawing: -")
        self.live.setObjectName("live")

        close = QPushButton("Close")
        close.clicked.connect(self.close)

        for widget in (title, section, fps_label):
            layout.addWidget(widget)
        layout.addLayout(fps_row)
        for widget in (fps_note, self.adaptive_box, adaptive_note):
            layout.addWidget(widget)
        layout.addSpacing(6)
        layout.addWidget(self.live)
        layout.addSpacing(8)
        layout.addWidget(close, alignment=Qt.AlignmentFlag.AlignRight)

    def _on_fps_toggled(self, fps: int, checked: bool) -> None:
        """A frame-rate button was picked: report the new cap (ignore the one switched off)."""
        if checked:
            self.max_fps_changed.emit(fps)

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
