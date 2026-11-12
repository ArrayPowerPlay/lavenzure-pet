"""Polls system health, fires scheduled reminders, and triggers ambient idle lines.

Everything here runs on the Qt UI thread (QTimers). Reminders requested by the agent's worker
thread arrive through the queued ``_reminder_requested`` signal.
"""
from __future__ import annotations

import json
import random
import time
from pathlib import Path

import psutil
from PySide6.QtCore import QObject, Qt, QTimer, Signal

import config
from agent.tools import set_timer_reminder as reminder_tool

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"


class BackgroundMonitor(QObject):
    """Emits ``alert_triggered`` (CPU/RAM/battery over threshold, once until cleared),
    ``reminder_triggered`` (a reminder is due) and ``joke_triggered`` (after idle time)."""

    alert_triggered = Signal(str)
    joke_triggered = Signal(str)
    reminder_triggered = Signal(str)
    _reminder_requested = Signal(float, str)  # internal: worker thread -> UI thread hand-off

    def __init__(self) -> None:
        """Read thresholds/intervals from config, load idle lines and start the poll timers."""
        super().__init__()
        self._cpu_threshold = config.get("system_status.cpu_threshold_percent", 90)
        self._ram_threshold = config.get("system_status.ram_threshold_percent", 90)
        self._battery_threshold = config.get("system_status.battery_threshold_percent", 30)
        self._poll_interval = config.get("system_status.poll_interval_seconds", 45)
        self._idle_minutes = config.get("ambient.random_fact_or_joke.idle_minutes", 15)

        facts_filename = Path(
            config.get("ambient.random_fact_or_joke.facts_file", "data/facts_jokes.json")
        ).name
        facts_path = DATA_DIR / facts_filename
        self._lines: list[str] = json.loads(facts_path.read_text(encoding="utf-8"))["lines"]

        self._alert_active = False
        self._last_activity = time.time()
        self._reminders: list[tuple[float, str]] = []

        self._reminder_requested.connect(self._add_reminder, Qt.ConnectionType.QueuedConnection)
        reminder_tool.register_reminder_scheduler(self.schedule_reminder)

        self._status_timer = QTimer(self)
        self._status_timer.timeout.connect(self._check_system_status)
        self._status_timer.start(int(self._poll_interval * 1000))

        self._reminder_timer = QTimer(self)
        self._reminder_timer.timeout.connect(self._check_reminders)
        self._reminder_timer.start(1000)

        self._idle_timer = QTimer(self)
        self._idle_timer.timeout.connect(self._check_idle)
        self._idle_timer.start(30_000)

    def notify_activity(self) -> None:
        """Call whenever the user chats or clicks the pet, to reset the idle joke clock."""
        self._last_activity = time.time()

    def clear_alert(self) -> None:
        """The user acknowledged the alert (clicked the pet); allow new alerts again."""
        self._alert_active = False

    def schedule_reminder(self, minutes: float, message: str) -> None:
        """Schedule a reminder ``minutes`` from now. Safe to call from any thread."""
        self._reminder_requested.emit(float(minutes), message)

    def _add_reminder(self, minutes: float, message: str) -> None:
        """Store a reminder (UI thread only)."""
        self._reminders.append((time.time() + minutes * 60, message))

    def _check_system_status(self) -> None:
        """Poll CPU/RAM/battery and raise at most one alert until the user clears it."""
        if self._alert_active:
            return  # don't stack alerts; wait for the user to click the pet first
        cpu = psutil.cpu_percent(interval=None)
        ram = psutil.virtual_memory().percent
        battery = psutil.sensors_battery()

        if cpu > self._cpu_threshold:
            self._fire_alert(f"CPU usage is at {cpu:.0f}%! Might want to check what's running.")
        elif ram > self._ram_threshold:
            self._fire_alert(f"RAM usage is at {ram:.0f}%! Things might slow down soon.")
        elif (
            battery is not None
            and not battery.power_plugged
            and battery.percent < self._battery_threshold
        ):
            self._fire_alert(f"Battery is down to {battery.percent:.0f}%. Better plug in!")

    def _fire_alert(self, message: str) -> None:
        """Mark an alert as active and announce it."""
        self._alert_active = True
        self.alert_triggered.emit(message)

    def _check_reminders(self) -> None:
        """Emit every reminder whose time has come and drop it from the list."""
        now = time.time()
        due = [r for r in self._reminders if r[0] <= now]
        if not due:
            return
        self._reminders = [r for r in self._reminders if r[0] > now]
        for _, message in due:
            self.reminder_triggered.emit(message)

    def _check_idle(self) -> None:
        """After enough time without chat/clicks, emit a random fact or joke."""
        if time.time() - self._last_activity >= self._idle_minutes * 60:
            self.joke_triggered.emit(random.choice(self._lines))
            self._last_activity = time.time()  # reschedule the next idle line
