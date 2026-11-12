"""Entry point: wires the overlay sprite, chat window, agent, and background monitor together.

Components never reference each other directly; ``CalciferApp._wire_signals`` connects their Qt
signals. Startup order: logging -> single-instance check -> build components -> show the pet.
"""
from __future__ import annotations

import json
import logging
import random
import sys
from pathlib import Path

import config
from PySide6.QtCore import QObject, QThread, Signal
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication, QMenu, QSystemTrayIcon

import app_logging
from agent.errors import friendly_error
from agent.graph import run_agent
from agent.memory import SessionMemory
from chat.chat_window import ChatWindow, markdown_to_plain
from monitor.background_monitor import BackgroundMonitor
from overlay.behavior import BehaviorController, PetState
from overlay.character import Mood
from overlay.overlay_window import OverlaySprite
from overlay.speech_bubble import SpeechBubble
from single_instance import SingleInstance

log = logging.getLogger(__name__)

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


class AgentWorker(QObject):
    """Runs the (potentially slow) LangGraph agent call off the Qt UI thread."""

    finished = Signal(str)  # the reply text
    failed = Signal(str)    # a friendly, in-character explanation of what went wrong

    def __init__(self, history: list[dict], message: str) -> None:
        """Store the conversation so far and the new user message for ``run``."""
        super().__init__()
        self._history = history
        self._message = message

    def run(self) -> None:
        """Call the agent (in the worker thread) and emit ``finished`` or ``failed``."""
        try:
            reply = run_agent(self._history, self._message)
            self.finished.emit(reply)
        except Exception as exc:  # noqa: BLE001 - surface any failure to the chat UI
            log.exception("Agent call failed")
            self.failed.emit(friendly_error(exc))


class CalciferApp:
    """Builds every component, connects them with signals and runs the Qt event loop."""

    def __init__(self, app: QApplication, instance: SingleInstance) -> None:
        """Create the pet, bubble, chat, monitor and tray; show the pet."""
        self.app = app
        self.instance = instance

        self.sprite = OverlaySprite()
        self.bubble = SpeechBubble(self.sprite.bubble_anchor)
        self.behavior = BehaviorController(self.sprite)
        self.chat_window = ChatWindow()
        self.monitor = BackgroundMonitor()
        self.memory = SessionMemory(
            ttl_seconds=config.get("memory.idle_timeout_minutes", 10) * 60
        )
        # Replies up to this many characters are also shown in the bubble (0 = never).
        self._reply_bubble_chars = int(config.get("chat.reply_bubble_max_chars", 140))

        click_reactions_path = DATA_DIR / "click_reactions.json"
        self._click_lines = json.loads(click_reactions_path.read_text(encoding="utf-8"))["lines"]

        self._alert_message = ""
        self._agent_thread: QThread | None = None
        self._agent_worker: AgentWorker | None = None

        self._wire_signals()
        self._build_tray_icon()

        self.sprite.show()

    def _wire_signals(self) -> None:
        """Connect component signals to the app's handlers (the only place components meet)."""
        self.instance.activated.connect(self._open_chat)
        self.sprite.clicked.connect(self._on_pet_clicked)
        self.sprite.right_clicked.connect(self._open_chat)
        self.chat_window.message_sent.connect(self._on_chat_message)

        self.monitor.alert_triggered.connect(self._on_alert)
        self.monitor.joke_triggered.connect(self._on_joke)
        self.monitor.reminder_triggered.connect(self._on_reminder)

    def _build_tray_icon(self) -> None:
        """Create the system-tray icon and its menu (Show/Hide Pet, Open Chat, Quit)."""
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

    # ------------------------------------------------------------------ bubble / pet reactions

    def _say(self, text: str, auto_hide_ms: int | None) -> None:
        """Show ``text`` in the speech bubble, or as a tray notification while the pet is hidden."""
        if self.sprite.isVisible():
            self.bubble.show_text(text, auto_hide_ms)
        else:
            self.tray.showMessage("Calcifer", text, QSystemTrayIcon.MessageIcon.NoIcon,
                                  auto_hide_ms or 10_000)

    def _on_pet_clicked(self) -> None:
        """A click clears an active alert; otherwise the pet hops and says a random line."""
        self.monitor.notify_activity()
        if self.behavior.state == PetState.ALERT:
            self.behavior.clear_alert()
            self.monitor.clear_alert()
            self._alert_message = ""
            self.bubble.hide()
            return
        self.behavior.trigger_reaction()
        self._say(random.choice(self._click_lines), auto_hide_ms=3000)

    def _on_alert(self, message: str) -> None:
        """System-status alert: alert face + a bubble that stays until the pet is clicked."""
        self._alert_message = message
        self.behavior.trigger_alert()
        self._say(message, auto_hide_ms=None)

    def _on_joke(self, text: str) -> None:
        """Ambient fact/joke after idle time (never covers an alert, skipped while hidden)."""
        if self.sprite.isVisible() and not self.bubble.is_sticky():
            self.bubble.show_text(text, auto_hide_ms=5000)

    def _on_reminder(self, message: str) -> None:
        """A reminder is due: surprised hop + bubble. During an alert, both stay on screen."""
        text = f"Reminder: {message}"
        if self.behavior.state == PetState.ALERT and self._alert_message:
            self._say(f"{text}\n\n{self._alert_message}", auto_hide_ms=None)
            return
        self.behavior.trigger_notice()
        self._say(text, auto_hide_ms=8000)

    def _toggle_visibility(self) -> None:
        """Hide or show the pet (the agent and the monitor keep running)."""
        if self.sprite.isVisible():
            self.sprite.hide()
            self.bubble.hide()
            self.toggle_action.setText("Show Pet")
        else:
            self.sprite.show()
            self.toggle_action.setText("Hide Pet")

    # ------------------------------------------------------------------ chat

    def _open_chat(self) -> None:
        """Open the chat window beside the pet (or where it was, if already open)."""
        self.chat_window.show_near(self.sprite.frameGeometry())

    def _on_chat_message(self, message: str) -> None:
        """Run the agent for ``message`` on a fresh worker thread (never on the UI thread)."""
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
        """Show the reply in the chat (and in the bubble if short) and animate the mouth."""
        self.memory.add("assistant", reply)
        self.chat_window.append_message("Calcifer", reply)
        self.chat_window.set_thinking(False)
        self.sprite.character.set_thinking(False)
        # Move the mouth for roughly as long as it would take to say the reply.
        self.sprite.character.play(Mood.TALKING, min(5.0, max(1.2, len(reply) * 0.045)))
        plain = markdown_to_plain(reply)
        if (0 < len(plain) <= self._reply_bubble_chars and self.sprite.isVisible()
                and not self.bubble.is_sticky()):
            self.bubble.show_text(plain, auto_hide_ms=max(3000, len(plain) * 60))

    def _on_agent_error(self, message: str) -> None:
        """Show the friendly error message (details are already in the log file)."""
        self.chat_window.append_message("Calcifer", message)
        self.chat_window.set_thinking(False)
        self.sprite.character.set_thinking(False)

    def run(self) -> int:
        """Run the Qt event loop until the user quits; returns the exit code."""
        return self.app.exec()


def main() -> int:
    """Start logging, make sure only one pet runs, then run the app."""
    log_file = app_logging.setup_logging()
    log.info("Calcifer starting (log file: %s)", log_file)
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    instance = SingleInstance()
    if not instance.acquire():
        return 0  # the running pet was asked to open its chat window instead
    code = CalciferApp(app, instance).run()
    log.info("Calcifer exiting (code %s)", code)
    return code


if __name__ == "__main__":
    sys.exit(main())
