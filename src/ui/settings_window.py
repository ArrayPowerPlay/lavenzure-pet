"""The Settings window opened from the tray menu.

Which settings it will hold is not decided yet (see ``docs/DECISION_LOG.md``), so for now it is a
small, empty window in the pet's style that says so.
"""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QPushButton, QVBoxLayout, QWidget

STYLE = """
QWidget#settings { background: #fff8ea; }
QLabel { color: #6c0e16; font-family: "Segoe UI", "Arial"; }
QLabel#title { font-size: 15pt; font-weight: 600; }
QLabel#note { font-size: 10pt; color: #8a4a14; }
QPushButton {
    background: #f6a23a; color: white; border: none; border-radius: 12px;
    padding: 6px 22px; font-family: "Segoe UI", "Arial"; font-size: 10pt; font-weight: 600;
}
QPushButton:hover { background: #f08a1c; }
"""


class SettingsWindow(QWidget):
    """Small always-on-top window; placeholder until the settings are chosen."""

    def __init__(self) -> None:
        """Build the title, the "coming soon" note and a Close button."""
        super().__init__(None, Qt.WindowType.Window | Qt.WindowType.WindowStaysOnTopHint)
        self.setObjectName("settings")
        self.setWindowTitle("Calcifer - Settings")
        self.setFixedSize(340, 200)
        self.setStyleSheet(STYLE)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 18)
        title = QLabel("Settings")
        title.setObjectName("title")
        note = QLabel("Nothing to change here yet - settings are coming soon!")
        note.setObjectName("note")
        note.setWordWrap(True)
        close = QPushButton("Close")
        close.clicked.connect(self.close)
        layout.addWidget(title)
        layout.addWidget(note)
        layout.addStretch(1)
        layout.addWidget(close, alignment=Qt.AlignmentFlag.AlignRight)

    def open(self) -> None:
        """Show the window (or bring it to the front if it is already open)."""
        self.show()
        self.raise_()
        self.activateWindow()
