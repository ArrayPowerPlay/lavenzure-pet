"""The Settings window opened from the tray menu.

It holds these options; a choice made here is remembered (``user_settings``):

- **Language** - English / Tiếng Việt: the language of everything the pet says on screen (click
  lines, care lines, facts/jokes, alerts, reminders). Chat replies follow the language the user
  writes in.
- **Chat AI** - which service answers the chat (Gemini / OpenAI) and the API keys: one box for the
  chosen service plus an optional Tavily box for web search (``ApiKeyPanel``; keys go to the
  Windows Credential Manager, never to the settings file).
- **Frame rate** - 30 / 60 fps for every animation (roadmap Phase 12). 30 is the default the user
  chose (``character.fps`` in config.yaml).

A small live readout shows how many frames per second the pet is really drawing, so the effect of
the choice is visible at once. (The lite flame is not a switch here: the user chose it, so it is
always on - see ``performance.lite_flame`` in config.yaml.)

The window only *reports* changes (``language_changed``, ``max_fps_changed``,
``provider_changed``, ``api_keys_changed``); the app applies them and remembers them.
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

import api_keys
import version
from agent.key_check import check_gemini_key, check_openai_key, check_tavily_key
from pet_lines import LANGUAGES
from ui.api_key_panel import ApiKeyPanel

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
QPushButton:disabled { background: #e7cfa8; }
QPushButton#small { padding: 3px 14px; font-size: 9pt; border-radius: 9px; }
QLineEdit { background: white; color: #6c0e16; border: 1px solid #e4b979; border-radius: 8px;
            padding: 4px 8px; font-family: "Segoe UI", "Arial"; font-size: 10pt; }
QLabel#note a { color: #c0561a; }
"""

# Frame rates offered in the window (30 = the default the user chose).
FPS_CHOICES = (30, 60)

# AI services offered for the chat: setting value -> name shown in the window.
PROVIDER_CHOICES = {"gemini": "Gemini", "openai": "OpenAI"}


class SettingsWindow(QWidget):
    """Small always-on-top window with the language, chat-AI and frame-rate choices and a live
    frame-rate readout."""

    language_changed = Signal(str)
    max_fps_changed = Signal(int)
    provider_changed = Signal(str)
    api_keys_changed = Signal()

    def __init__(self, max_fps: int = 30, language: str = "en", provider: str = "gemini") -> None:
        """Build the window; the buttons matching the current language, chat AI and frame rate
        start selected."""
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

        language_section = QLabel("Language")
        language_section.setObjectName("section")
        language_row = QHBoxLayout()
        language_row.setContentsMargins(0, 0, 0, 0)
        self.language_group = QButtonGroup(self)
        self.language_buttons: dict[str, QRadioButton] = {}
        for code, name in LANGUAGES.items():
            button = QRadioButton(name)
            button.setChecked(code == language)
            button.toggled.connect(lambda checked, c=code: self._on_language_toggled(c, checked))
            self.language_group.addButton(button)
            self.language_buttons[code] = button
            language_row.addWidget(button)
        language_row.addStretch(1)
        language_note = self._note("What the pet says on screen. Chat replies follow the "
                                   "language you write in.")

        ai_section = QLabel("Chat AI")
        ai_section.setObjectName("section")
        ai_row = QHBoxLayout()
        ai_row.setContentsMargins(0, 0, 0, 0)
        self.provider_group = QButtonGroup(self)
        self.provider_buttons: dict[str, QRadioButton] = {}
        for code, name in PROVIDER_CHOICES.items():
            button = QRadioButton(name)
            button.setChecked(code == provider)
            button.toggled.connect(lambda checked, c=code: self._on_provider_toggled(c, checked))
            self.provider_group.addButton(button)
            self.provider_buttons[code] = button
            ai_row.addWidget(button)
        ai_row.addStretch(1)
        ai_note = self._note("The service that answers when you chat with the pet. Each one "
                             "needs its own API key.")
        self.key_panels: dict[str, ApiKeyPanel] = {
            "gemini": ApiKeyPanel(
                api_keys.GEMINI, "Gemini API key", check_gemini_key,
                '<a href="https://aistudio.google.com/apikey">Get a free key</a> '
                "from Google AI Studio."),
            "openai": ApiKeyPanel(
                api_keys.OPENAI, "OpenAI API key", check_openai_key,
                '<a href="https://platform.openai.com/api-keys">Get a key</a> '
                "from the OpenAI platform."),
        }
        self.tavily_panel = ApiKeyPanel(
            api_keys.TAVILY, "Tavily API key", check_tavily_key,
            '<a href="https://app.tavily.com">Get a free key</a> to let the pet search the web.',
            optional=True)
        for panel in (*self.key_panels.values(), self.tavily_panel):
            panel.changed.connect(self.api_keys_changed)
        self._show_provider_panel(provider)

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
        version_label = QLabel(version.display_name())
        version_label.setObjectName("note")
        version_label.setStyleSheet("margin-left: 0;")

        layout.addWidget(title)
        layout.addWidget(language_section)
        layout.addLayout(language_row)
        layout.addWidget(language_note)
        layout.addWidget(ai_section)
        layout.addLayout(ai_row)
        layout.addWidget(ai_note)
        for panel in (*self.key_panels.values(), self.tavily_panel):
            layout.addWidget(panel)
        for widget in (section, fps_label):
            layout.addWidget(widget)
        layout.addLayout(fps_row)
        layout.addWidget(fps_note)
        layout.addSpacing(6)
        layout.addWidget(self.live)
        layout.addSpacing(8)
        footer = QHBoxLayout()
        footer.setContentsMargins(0, 0, 0, 0)
        footer.addWidget(version_label)
        footer.addStretch(1)
        footer.addWidget(close)
        layout.addLayout(footer)

    def _on_language_toggled(self, code: str, checked: bool) -> None:
        """A language button was picked: report it (ignore the one switched off)."""
        if checked:
            self.language_changed.emit(code)

    def _on_provider_toggled(self, code: str, checked: bool) -> None:
        """A chat-AI button was picked: show its key box and report it (ignore the one switched
        off)."""
        if checked:
            self._show_provider_panel(code)
            self.provider_changed.emit(code)

    def _show_provider_panel(self, provider: str) -> None:
        """Show only the key box of the chosen chat AI."""
        for code, panel in self.key_panels.items():
            panel.setVisible(code == provider)
        self.adjustSize()

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
        for panel in (*self.key_panels.values(), self.tavily_panel):
            panel.refresh()
        self.show()
        self.raise_()
        self.activateWindow()
