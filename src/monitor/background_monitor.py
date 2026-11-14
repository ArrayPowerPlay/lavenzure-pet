"""Polls system health, fires scheduled reminders, and says when it is time for an ambient line.

Everything here runs on the Qt UI thread (QTimers). Reminder requests from the agent's worker
thread (add, cancel, hide the bubble) arrive through queued internal signals, so the reminder
list is only ever changed on the UI thread; it is saved to a file
(``monitor.reminders.ReminderStore``), so it survives restarts. Other threads read it through
``pending_reminders``, an immutable snapshot replaced after every change. Alert texts are
written in the language chosen in Settings (``set_language``); which ambient line to say is up
to the app (``pet_lines.PetLines``), the monitor only keeps the clock.
"""
from __future__ import annotations

import itertools
import threading
import time
from pathlib import Path

import psutil
from PySide6.QtCore import QObject, Qt, QTimer, Signal

import config
import pet_lines
from agent.tools import set_timer_reminder as reminder_tool
from monitor.reminders import Reminder, ReminderStore

LATE_GRACE_SECONDS = 60   # a reminder going off later than this says how late it is


class BackgroundMonitor(QObject):
    """Emits ``alert_triggered`` (CPU/RAM/battery over threshold, once until cleared, then quiet
    for ``system_status.snooze_minutes`` after the user dismisses it), ``reminder_triggered``
    (message, line, minutes late - 0 when on time; late when the PC slept or the app was closed
    at the due time; ``line`` is what the pet says, "" for reminders saved before round 28) and
    ``ambient_due`` (``ambient.interval_minutes`` since the last line or interaction: time for
    the pet to say something on its own). For the reminders list it also
    emits ``reminders_changed(list[Reminder])`` after every add / cancel / reminder going off,
    ``reminder_added(Reminder)`` / ``reminder_cancelled(Reminder)`` when one is set or cancelled
    through the AI's tools (the chat shows a note written by the app, so a reply that only
    claims it is easy to spot), and ``reminders_dismissed`` when the AI asks to hide the
    reminders showing on the pet. ``remove_reminder`` (the Reminders tab's x) is silent.

    It is the ``ReminderService`` of the reminder tools (``agent.tools.set_timer_reminder``):
    ``schedule_reminder``, ``pending_reminders``, ``cancel_reminder`` and
    ``dismiss_shown_reminders`` are safe to call from any thread."""

    alert_triggered = Signal(str)
    ambient_due = Signal()
    reminder_triggered = Signal(str, str, int)
    reminders_changed = Signal(list)
    reminder_added = Signal(object)
    reminder_cancelled = Signal(object)
    reminders_dismissed = Signal()
    # Internal worker thread -> UI thread hand-offs.
    _reminder_requested = Signal(int, float, str, str)
    _cancel_requested = Signal(int)
    _dismiss_requested = Signal()

    def __init__(self, reminders_path: Path | None = None) -> None:
        """Read thresholds/intervals from config, load saved reminders and start the poll
        timers. ``reminders_path`` overrides the reminders file (tests)."""
        super().__init__()
        self._cpu_threshold = config.get("system_status.cpu_threshold_percent", 90)
        self._ram_threshold = config.get("system_status.ram_threshold_percent", 90)
        self._battery_threshold = config.get("system_status.battery_threshold_percent", 30)
        self._poll_interval = config.get("system_status.poll_interval_seconds", 45)
        self._snooze_seconds = float(config.get("system_status.snooze_minutes", 10)) * 60
        self._ambient_seconds = float(config.get("ambient.interval_minutes", 5)) * 60
        self._language = pet_lines.DEFAULT_LANGUAGE

        self._alert_active = False
        self._snoozed_until = 0.0   # no new alerts before this time (set when one is dismissed)
        self._last_activity = time.time()
        self._reminders = ReminderStore(reminders_path)
        self._snapshot: tuple[Reminder, ...] = self._reminders.items()
        self._ids = itertools.count(self._reminders.max_id() + 1)
        self._ids_lock = threading.Lock()

        queued = Qt.ConnectionType.QueuedConnection
        self._reminder_requested.connect(self._add_reminder, queued)
        self._cancel_requested.connect(self._cancel_from_tool, queued)
        self._dismiss_requested.connect(self.reminders_dismissed, queued)
        reminder_tool.register_reminder_service(self)

        self._status_timer = QTimer(self)
        self._status_timer.timeout.connect(self._check_system_status)
        self._status_timer.start(int(self._poll_interval * 1000))

        self._reminder_timer = QTimer(self)
        self._reminder_timer.timeout.connect(self._check_reminders)
        self._reminder_timer.start(1000)

        self._idle_timer = QTimer(self)
        self._idle_timer.timeout.connect(self._check_idle)
        self._idle_timer.start(15_000)

    def set_language(self, language: str) -> None:
        """Write future alerts in ``language`` (a ``pet_lines.LANGUAGES`` code)."""
        self._language = language

    def notify_activity(self) -> None:
        """Call whenever the user chats or clicks the pet, or the pet says a line: the next
        ambient line comes ``ambient.interval_minutes`` after this."""
        self._last_activity = time.time()

    def clear_alert(self) -> None:
        """The user dismissed the alert (clicked the pet or chose Idle): stay quiet for the snooze
        time, then alert again if the problem is still there."""
        self._alert_active = False
        self._snoozed_until = time.time() + self._snooze_seconds

    def schedule_reminder(self, due: float, message: str, line: str = "") -> int:
        """Schedule a reminder at unix time ``due`` (``message`` = the task, ``line`` = what the
        pet says when it goes off) and return its id. Safe to call from any thread (the list
        itself is updated on the UI thread a moment later)."""
        with self._ids_lock:
            reminder_id = next(self._ids)
        self._reminder_requested.emit(reminder_id, float(due), message, line)
        return reminder_id

    def pending_reminders(self) -> list[Reminder]:
        """The reminders still waiting, soonest first. Safe to call from any thread."""
        return list(self._snapshot)

    def cancel_reminder(self, reminder_id: int) -> Reminder | None:
        """Cancel the pending reminder ``reminder_id``; returns it, or ``None`` when no pending
        reminder has that id. Safe to call from any thread (removed on the UI thread)."""
        found = next((r for r in self._snapshot if r.id == reminder_id), None)
        if found is not None:
            self._cancel_requested.emit(reminder_id)
        return found

    def dismiss_shown_reminders(self) -> None:
        """Ask the app to hide the reminders showing on the pet (``reminders_dismissed`` is
        emitted on the UI thread). Safe to call from any thread."""
        self._dismiss_requested.emit()

    def remove_reminder(self, reminder_id: int) -> None:
        """Drop a reminder right away without announcing it (UI thread only; used by the
        Reminders tab, where the user sees the row go)."""
        if self._reminders.remove(reminder_id) is not None:
            self._publish()

    def _add_reminder(self, reminder_id: int, due: float, message: str, line: str) -> None:
        """Store (and save) a reminder set by the AI and announce it (UI thread only)."""
        reminder = Reminder(reminder_id, due, message, line)
        self._reminders.add(reminder)
        self._publish()
        self.reminder_added.emit(reminder)

    def _cancel_from_tool(self, reminder_id: int) -> None:
        """Drop a reminder the AI cancelled and announce it (UI thread only; already gone =
        nothing to do)."""
        reminder = self._reminders.remove(reminder_id)
        if reminder is not None:
            self._publish()
            self.reminder_cancelled.emit(reminder)

    def _publish(self) -> None:
        """Refresh the snapshot other threads read and announce the new list."""
        self._snapshot = self._reminders.items()
        self.reminders_changed.emit(list(self._snapshot))

    def _check_system_status(self) -> None:
        """Poll CPU/RAM/battery and raise at most one alert until the user clears it (and none
        during the snooze time after that)."""
        if self._alert_active:
            return  # don't stack alerts; wait for the user to click the pet first
        if time.time() < self._snoozed_until:
            return  # the user just dismissed an alert; don't nag again right away
        cpu = psutil.cpu_percent(interval=None)
        ram = psutil.virtual_memory().percent
        battery = psutil.sensors_battery()

        if cpu > self._cpu_threshold:
            self._fire_alert(pet_lines.phrase(self._language, "cpu_alert", value=cpu))
        elif ram > self._ram_threshold:
            self._fire_alert(pet_lines.phrase(self._language, "ram_alert", value=ram))
        elif (
            battery is not None
            and not battery.power_plugged
            and battery.percent < self._battery_threshold
        ):
            self._fire_alert(pet_lines.phrase(self._language, "battery_alert",
                                              value=battery.percent))

    def _fire_alert(self, message: str) -> None:
        """Mark an alert as active and announce it."""
        self._alert_active = True
        self.alert_triggered.emit(message)

    def _check_reminders(self) -> None:
        """Emit every reminder whose time has come (with how many minutes late it is) and drop
        it from the saved list. Runs every second, and right after startup for reminders that
        fell due while the app was closed."""
        now = time.time()
        due = self._reminders.pop_due(now)
        if due:
            self._publish()
        for reminder in due:
            late = now - reminder.due
            minutes_late = int(round(late / 60)) if late > LATE_GRACE_SECONDS else 0
            self.reminder_triggered.emit(reminder.message, reminder.line, minutes_late)

    def _check_idle(self) -> None:
        """Once ``ambient.interval_minutes`` have passed since the last line or interaction,
        emit ``ambient_due`` and start counting again (if the app has to skip the line, e.g. the
        pet is asleep, the next chance comes one interval later)."""
        if time.time() - self._last_activity >= self._ambient_seconds:
            self._last_activity = time.time()
            self.ambient_due.emit()
