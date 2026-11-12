"""Entry point: wires the overlay sprite, chat bubble, agent, and background monitors together.

Components never reference each other directly; ``CalciferApp._wire_signals`` connects their Qt
signals. Startup order: logging -> single-instance check -> build components -> show the pet.
"""
from __future__ import annotations

import os

# numpy's OpenBLAS starts one worker thread per CPU core and reserves ~30 MB for each of them
# (~500 MB on a 16-thread CPU) as soon as numpy is imported. The pet only does tiny array maths,
# so one thread is plenty. This must run before anything imports numpy.
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")

import json
import logging
import random
import sys
from pathlib import Path

from PySide6.QtCore import QObject, QThread, QTimer, Signal
from PySide6.QtGui import QCursor
from PySide6.QtWidgets import QApplication, QSystemTrayIcon

import app_logging
import config
from agent.emotion import split_emotion
from agent.errors import friendly_error
from agent.graph import run_agent
from agent.memory import SessionMemory
from chat.chat_bubble import ChatBubble
from monitor.background_monitor import BackgroundMonitor
from monitor.user_activity import UserActivityWatcher
from overlay.behavior import BehaviorController, PetState
from overlay.character import Mood
from overlay.overlay_window import OverlaySprite
from overlay.speech_bubble import SpeechBubble
from single_instance import SingleInstance
from ui.menus import PetMenu, themed_menu
from ui.settings_window import SettingsWindow
from ui.tray_icon import make_tray_icon

log = logging.getLogger(__name__)

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

# Emotion tag of an AI reply -> face the pet shows while the reply appears (decision E1).
EMOTION_MOODS = {"happy": Mood.HAPPY, "scared": Mood.SCARED, "angry": Mood.ANGRY,
                 "chill": Mood.CHILL, "surprised": Mood.SURPRISED, "thinking": Mood.THINKING,
                 "yuck": Mood.YUCK}
EMOTION_SECONDS = 5.0


class AgentWorker(QObject):
    """Runs the (potentially slow) LangGraph agent call off the Qt UI thread."""

    finished = Signal(str)  # the reply text (still starting with its emotion tag)
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
        self.chat = ChatBubble(self.sprite.body_rect)
        self.monitor = BackgroundMonitor()
        self.activity = UserActivityWatcher()
        self.pet_menu = PetMenu()
        self.settings: SettingsWindow | None = None
        self.memory = SessionMemory(
            ttl_seconds=config.get("memory.idle_timeout_minutes", 15) * 60
        )
        # Wipe the whole conversation (screen + memory) once it has been idle past the TTL.
        self._memory_timer = QTimer()
        self._memory_timer.timeout.connect(self._expire_chat_history)
        self._memory_timer.start(20_000)

        click_reactions_path = DATA_DIR / "click_reactions.json"
        self._click_lines = json.loads(click_reactions_path.read_text(encoding="utf-8"))["lines"]

        self._alert_message = ""
        self._agent_thread: QThread | None = None
        self._agent_worker: AgentWorker | None = None

        self._wire_signals()
        self._build_tray_icon()
        self.activity.check()   # apply night / dozing right away instead of after a second

        self.sprite.show()

    def _wire_signals(self) -> None:
        """Connect component signals to the app's handlers (the only place components meet)."""
        self.instance.activated.connect(self._open_chat)
        self.sprite.clicked.connect(self._on_pet_clicked)
        self.sprite.right_clicked.connect(self._show_pet_menu)
        self.pet_menu.chat_requested.connect(self._open_chat)
        self.pet_menu.rest_requested.connect(self.behavior.set_resting)
        self.behavior.speak_requested.connect(self._say_random_line)
        self.chat.message_sent.connect(self._on_chat_message)
        self.chat.closed.connect(lambda: self.behavior.set_chatting(False))

        self.activity.dozing_changed.connect(self.behavior.set_dozing)
        self.activity.night_changed.connect(self.behavior.set_night)

        self.monitor.alert_triggered.connect(self._on_alert)
        self.monitor.joke_triggered.connect(self._on_joke)
        self.monitor.reminder_triggered.connect(self._on_reminder)

    def _build_tray_icon(self) -> None:
        """Create the system-tray icon (a portrait drawn by the character itself) and its menu:
        Hide/Show Pet, Settings, Quit App."""
        self.tray = QSystemTrayIcon(make_tray_icon(), self.app)
        self.tray.setToolTip("Lavenzure")

        self._tray_menu = themed_menu()
        self.toggle_action = self._tray_menu.addAction("Hide Pet")
        self.toggle_action.triggered.connect(self._toggle_visibility)
        self._tray_menu.addAction("Settings", self._open_settings)
        self._tray_menu.addSeparator()
        self._tray_menu.addAction("Quit App", self.app.quit)

        self.tray.setContextMenu(self._tray_menu)
        self.tray.show()

    def _open_settings(self) -> None:
        """Open the (for now empty) Settings window."""
        if self.settings is None:
            self.settings = SettingsWindow()
        self.settings.open()

    # ------------------------------------------------------------------ bubble / pet reactions

    def _say(self, text: str, auto_hide_ms: int | None) -> None:
        """Show ``text`` in the speech bubble, or as a tray notification while the pet is hidden."""
        if self.sprite.isVisible():
            self.bubble.show_text(text, auto_hide_ms)
        else:
            self.tray.showMessage("Lavenzure", text, QSystemTrayIcon.MessageIcon.NoIcon,
                                  auto_hide_ms or 10_000)

    def _on_pet_clicked(self) -> None:
        """A click only clears an active alert; otherwise the pet plays a random reaction."""
        self.monitor.notify_activity()
        if self.behavior.state == PetState.ALERT:
            self.behavior.clear_alert()
            self.monitor.clear_alert()
            self._alert_message = ""
            self.bubble.hide()
            return
        self.behavior.play_random_reaction()

    def _say_random_line(self) -> None:
        """The "speak" reaction: one random line from ``data/click_reactions.json``."""
        if not self.bubble.is_sticky():
            self._say(random.choice(self._click_lines), auto_hide_ms=3000)

    def _show_pet_menu(self) -> None:
        """Right-click on the pet: the small Chat / Idle (Wander) menu at the cursor."""
        self.monitor.notify_activity()
        self.pet_menu.popup(QCursor.pos(), self.behavior.resting)

    def _on_alert(self, message: str) -> None:
        """System-status alert: alert face + a bubble that stays until the pet is clicked."""
        self._alert_message = message
        self.behavior.trigger_alert()
        self._say(message, auto_hide_ms=None)

    def _on_joke(self, text: str) -> None:
        """Ambient fact/joke after idle time (never covers an alert; skipped while hidden or
        asleep)."""
        if self.sprite.isVisible() and not self.bubble.is_sticky() and not self.behavior.sleeping:
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
            self.chat.hide()
            self.toggle_action.setText("Show Pet")
        else:
            self.sprite.show()
            self.toggle_action.setText("Hide Pet")

    # ------------------------------------------------------------------ chat

    def _open_chat(self) -> None:
        """Open the chat bubble beside the pet; the pet stands still while it is open."""
        if not self.sprite.isVisible():
            self._toggle_visibility()
        self.behavior.set_chatting(True)
        self.chat.open()

    def _expire_chat_history(self) -> None:
        """After the idle TTL the conversation is gone for good, on screen and in memory."""
        if self.memory.check_and_clear_if_idle():
            self.chat.clear_history()

    def _on_chat_message(self, message: str) -> None:
        """Run the agent for ``message`` on a fresh worker thread (never on the UI thread)."""
        self.monitor.notify_activity()
        history = self.memory.get_history()
        self.memory.add("user", message)
        self.chat.set_thinking(True)
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
        """Show the reply (without its emotion tag) in the chat bubble, show the emotion on the
        pet's face for a few seconds and move its mouth."""
        emotion, text = split_emotion(reply)
        self.memory.add("assistant", reply)   # keep the tag: the model sees its own format
        self.chat.append_message("Lavenzure", text)
        self.chat.set_thinking(False)
        character = self.sprite.character
        character.set_thinking(False)
        mood = EMOTION_MOODS.get(emotion or "")
        if mood is not None:
            character.play(mood, EMOTION_SECONDS)
        # Move the mouth for roughly as long as it would take to say the reply.
        character.talk(min(5.0, max(1.2, len(text) * 0.045)))

    def _on_agent_error(self, message: str) -> None:
        """Show the friendly error message (details are already in the log file)."""
        self.chat.append_message("Lavenzure", message)
        self.chat.set_thinking(False)
        self.sprite.character.set_thinking(False)

    def run(self) -> int:
        """Run the Qt event loop until the user quits; returns the exit code."""
        return self.app.exec()


def main() -> int:
    """Start logging, make sure only one pet runs, then run the app."""
    log_file = app_logging.setup_logging()
    log.info("Lavenzure starting (log file: %s)", log_file)
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    instance = SingleInstance()
    if not instance.acquire():
        return 0  # the running pet was asked to open its chat window instead
    code = CalciferApp(app, instance).run()
    log.info("Lavenzure exiting (code %s)", code)
    return code


if __name__ == "__main__":
    sys.exit(main())
