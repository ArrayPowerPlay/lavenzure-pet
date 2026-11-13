"""The Settings window opened from the tray menu.

For now it holds one performance option (roadmap Phase 12):

- **Frame rate** - 30 / 60 fps for every animation. 30 is the default the user chose
  (``character.fps`` in config.yaml); a choice made here is remembered (``user_settings``).

A small live readout shows how many frames per second the pet is really drawing, so the effect of
the choice is visible at once. (The lite flame is not a switch here: the user chose it, so it is
always on - see ``performance.lite_flame`` in config.yaml.)

The window only *reports* changes (``max_fps_changed``); the app applies them to the pet and
remembers them.
"""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QButtonGroup,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QRadioButton,
    QVBoxLayout,
    QWidget,
)

STYLE = """
QWidget#settings { background: #fff8ea; }
QLabel { color: #6c0e16; font-family: "Segoe UI", "Arial"; }
QLabel#title { font-size: 15pt; font-weight: 600; }
QLabel#section { font-size: 11pt; font-weight: 600; margin-top: 4px; }
QLabel#note { font-size: 9pt; color: #8a4a14; margin-left: 26px; }
QLabel#live { font-size: 9pt; color: #8a4a14; background: #fdecc8; border-radius: 8px;
              padding: 6px 10px; }
QRadioButton { color: #6c0e16; font-family: "Segoe UI", "Arial"; font-size: 10pt; spacing: 8px; }
QPushButton {
    background: #f6a23a; color: white; border: none; border-radius: 12px;
    padding: 6px 22px; font-family: "Segoe UI", "Arial"; font-size: 10pt; font-weight: 600;
}
QPushButton:hover { background: #f08a1c; }
"""

# Frame rates offered in the window (30 = the default the user chose).
FPS_CHOICES = (30, 60)


class SettingsWindow(QWidget):
    """Small always-on-top window with the frame-rate choice and a live frame-rate readout."""

    max_fps_changed = Signal(int)

    def __init__(self, max_fps: int = 30) -> None:
        """Build the window; the button matching the current frame rate starts selected."""
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
        fps_note = self._note("Frames drawn per second, for every animation. Higher = smoother "
                              "motion, more CPU and GPU.")

        self.live = QLabel("Drawing: -")
        self.live.setObjectName("live")

        close = QPushButton("Close")
        close.clicked.connect(self.close)

        for widget in (title, section, fps_label):
            layout.addWidget(widget)
        layout.addLayout(fps_row)
        layout.addWidget(fps_note)
        layout.addSpacing(6)
        layout.addWidget(self.live)
        layout.addSpacing(8)
        layout.addWidget(close, alignment=Qt.AlignmentFlag.AlignRight)

    def _on_fps_toggled(self, fps: int, checked: bool) -> None:
        """A frame-rate button was picked: report the new rate (ignore the one switched off)."""
        if checked:
            self.max_fps_changed.emit(fps)

    @staticmethod
    def _note(text: str) -> QLabel:
        """A small explanatory line under an option."""
        note = QLabel(text)
        note.setObjectName("note")
        note.setWordWrap(True)
        return note

    def show_frame_rate(self, fps: float) -> None:
        """Update the live readout (connected to the pet window's ``frame_rate_changed``)."""
        self.live.setText(f"Drawing: {fps:.0f} fps")

    def open(self) -> None:
        """Show the window (or bring it to the front if it is already open)."""
        self.show()
        self.raise_()
        self.activateWindow()
