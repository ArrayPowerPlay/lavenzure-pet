"""Entry point: wires the overlay sprite, chat window, agent, and background monitor together."""
from __future__ import annotations

import json
import random
import sys
from pathlib import Path

import config
from PySide6.QtCore import QObject, QThread, Signal
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication, QMenu, QSystemTrayIcon

from agent.graph import run_agent
from agent.memory import SessionMemory
from chat.chat_window import ChatWindow
from monitor.background_monitor import BackgroundMonitor
from overlay.behavior import BehaviorController, PetState
from overlay.character import Mood
from overlay.overlay_window import OverlaySprite
from overlay.speech_bubble import SpeechBubble

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


class AgentWorker(QObject):
    """Runs the (potentially slow) LangGraph agent call off the Qt UI thread."""

    finished = Signal(str)
    failed = Signal(str)

    def __init__(self, history: list[dict], message: str) -> None:
        super().__init__()
        self._history = history
        self._message = message

    def run(self) -> None:
        try:
            reply = run_agent(self._history, self._message)
            self.finished.emit(reply)
        except Exception as exc:  # noqa: BLE001 - surface any failure to the chat UI
            self.failed.emit(str(exc))


class CalciferApp:
    def __init__(self) -> None:
        self.app = QApplication(sys.argv)
        self.app.setQuitOnLastWindowClosed(False)

        self.sprite = OverlaySprite()
        self.bubble = SpeechBubble()
        self.behavior = BehaviorController(self.sprite)
        self.chat_window = ChatWindow()
        self.monitor = BackgroundMonitor()
        self.memory = SessionMemory(
            ttl_seconds=config.get("memory.idle_timeout_minutes", 10) * 60
        )

        click_reactions_path = DATA_DIR / "click_reactions.json"
        self._click_lines = json.loads(click_reactions_path.read_text(encoding="utf-8"))["lines"]

        self._agent_thread: QThread | None = None
        self._agent_worker: AgentWorker | None = None

        self._wire_signals()
        self._build_tray_icon()

        self.sprite.show()

    def _wire_signals(self) -> None:
        self.sprite.clicked.connect(self._on_pet_clicked)
        self.sprite.right_clicked.connect(self._open_chat)
        self.chat_window.message_sent.connect(self._on_chat_message)

        self.monitor.alert_triggered.connect(self._on_alert)
        self.monitor.joke_triggered.connect(self._on_joke)
        self.monitor.reminder_triggered.connect(self._on_reminder)

    def _build_tray_icon(self) -> None:
        # Windows has no icon theme, so fall back to a snapshot of the drawn character.
        icon = QIcon.fromTheme("weather-clear")
        if icon.isNull():
            icon = QIcon(self.sprite.grab())
        self.tray = QSystemTrayIcon(icon, self.app)
        self.tray.setToolTip("Calcifer")

        menu = QMenu()
        self.toggle_action = menu.addAction("Hide Pet")
        self.toggle_action.triggered.connect(self._toggle_visibility)
        menu.addAction("Open Chat", self._open_chat)
        menu.addSeparator()
        menu.addAction("Quit", self.app.quit)

        self.tray.setContextMenu(menu)
        self.tray.show()

    def _on_pet_clicked(self) -> None:
        self.monitor.notify_activity()
        if self.behavior.state == PetState.ALERT:
            self.behavior.clear_alert()
            self.monitor.clear_alert()
            self.bubble.hide()
            return
        self.behavior.trigger_reaction()
        line = random.choice(self._click_lines)
        self.bubble.show_above(self.sprite.bubble_anchor(), line, auto_hide_ms=3000)

    def _on_alert(self, message: str) -> None:
        self.behavior.trigger_alert()
        self.bubble.show_above(self.sprite.bubble_anchor(), message, auto_hide_ms=None)

    def _on_joke(self, text: str) -> None:
        self.bubble.show_above(self.sprite.bubble_anchor(), text, auto_hide_ms=5000)

    def _on_reminder(self, message: str) -> None:
        self.bubble.show_above(self.sprite.bubble_anchor(), f"Reminder: {message}", auto_hide_ms=6000)

    def _toggle_visibility(self) -> None:
        if self.sprite.isVisible():
            self.sprite.hide()
            self.bubble.hide()
            self.toggle_action.setText("Show Pet")
        else:
            self.sprite.show()
            self.toggle_action.setText("Hide Pet")

    def _open_chat(self) -> None:
        self.chat_window.show()
        self.chat_window.raise_()
        self.chat_window.activateWindow()

    def _on_chat_message(self, message: str) -> None:
        self.monitor.notify_activity()
        history = self.memory.get_history()
        self.memory.add("user", message)
        self.chat_window.set_thinking(True)
        self.sprite.character.set_thinking(True)

        self._agent_thread = QThread()
        self._agent_worker = AgentWorker(history, message)
        self._agent_worker.moveToThread(self._agent_thread)
        self._agent_thread.started.connect(self._agent_worker.run)
        self._agent_worker.finished.connect(self._on_agent_reply)
        self._agent_worker.failed.connect(self._on_agent_error)
        self._agent_worker.finished.connect(self._agent_thread.quit)
        self._agent_worker.failed.connect(self._agent_thread.quit)
        self._agent_thread.start()

    def _on_agent_reply(self, reply: str) -> None:
        self.memory.add("assistant", reply)
        self.chat_window.append_message("Calcifer", reply)
        self.chat_window.set_thinking(False)
        self.sprite.character.set_thinking(False)
        # Move the mouth for roughly as long as it would take to say the reply.
        self.sprite.character.play(Mood.TALKING, min(5.0, max(1.2, len(reply) * 0.045)))

    def _on_agent_error(self, error: str) -> None:
        self.chat_window.append_message(
            "Calcifer", "Oops, my flame flickered out for a second. Try again?"
        )
        self.chat_window.set_thinking(False)
        self.sprite.character.set_thinking(False)

    def run(self) -> int:
        return self.app.exec()


if __name__ == "__main__":
    sys.exit(CalciferApp().run())
