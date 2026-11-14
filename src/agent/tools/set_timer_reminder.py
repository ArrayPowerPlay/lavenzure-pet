"""Reminder tools: set ("remind me in 30 minutes to ..." / "at 11:00"), list and cancel reminders,
and hide reminders that already went off.

The model only passes what the user said (``minutes`` from now, or a clock time ``at``); this code
works out the actual due time, because language models are unreliable at clock arithmetic
(decision of round 21). A clock time that has already passed today means tomorrow.

When the user gives no time or only a vague one ("tonight", "later"), the system prompt makes the
model ask first, suggesting a time from ``config.yaml`` ``reminders.suggested_times`` (decision
of round 25), so these tools always receive a real time.

The tools run on the agent's worker thread. The registered service (``BackgroundMonitor``) only
emits queued Qt signals for changes, which Qt delivers on the UI thread, and answers
``pending_reminders`` from an immutable snapshot, so no shared state is changed across threads.
The monitor saves reminders to a file, so they survive the chat history being wiped and the app
being restarted.
"""
from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime, timedelta
from typing import Protocol

from langchain_core.tools import tool

MAX_DAYS = 7  # how far ahead a reminder may be set
UNAVAILABLE = "Reminders aren't available right now."


class PendingReminder(Protocol):
    """What the tools read from a pending reminder (``monitor.reminders.Reminder``)."""

    id: int
    due: float
    message: str


class ReminderService(Protocol):
    """What the tools need from whoever keeps the reminders (the ``BackgroundMonitor``). Every
    method must be safe to call from the agent's worker thread."""

    def schedule_reminder(self, due: float, message: str) -> int:
        """Schedule a reminder at unix time ``due``; returns its id."""

    def pending_reminders(self) -> Sequence[PendingReminder]:
        """The reminders still waiting, soonest first."""

    def cancel_reminder(self, reminder_id: int) -> PendingReminder | None:
        """Cancel a pending reminder; returns it, or ``None`` if no such reminder is pending."""

    def dismiss_shown_reminders(self) -> None:
        """Hide the reminders that already went off and are showing on the pet."""


_service: ReminderService | None = None


def register_reminder_service(service: ReminderService | None) -> None:
    """Install the object that actually keeps the reminders (done by the BackgroundMonitor)."""
    global _service
    _service = service


def _parse_at(at: str, now: datetime) -> datetime:
    """Turn ``"HH:MM"`` (today, or tomorrow if already past) or ``"YYYY-MM-DD HH:MM"`` into a
    datetime. Raises ``ValueError`` for anything else."""
    text = at.strip().upper().replace(".", ":")
    for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%dT%H:%M"):
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            pass
    for fmt in ("%H:%M", "%H", "%I:%M %p", "%I %p", "%I:%M%p", "%I%p"):
        try:
            clock = datetime.strptime(text, fmt)
        except ValueError:
            continue
        due = now.replace(hour=clock.hour, minute=clock.minute, second=0, microsecond=0)
        return due if due > now else due + timedelta(days=1)
    raise ValueError(f"unrecognised time {at!r}")


def resolve_due(minutes: float | None, at: str | None, now: datetime) -> datetime:
    """The moment a reminder is due, from ``minutes`` after ``now`` or a clock time ``at``.

    Raises ``ValueError`` with a message meant for the model when the request makes no sense
    (both or neither given, in the past, more than ``MAX_DAYS`` ahead, unreadable time).
    """
    has_at = at is not None and bool(at.strip())
    if (minutes is None) == (not has_at):
        raise ValueError("give exactly one of 'minutes' (from now) or 'at' (a clock time)")
    if minutes is not None:
        if minutes <= 0:
            raise ValueError("minutes must be greater than 0")
        due = now + timedelta(minutes=minutes)
    else:
        try:
            due = _parse_at(at, now)
        except ValueError:
            raise ValueError("'at' must look like '11:00' or '2026-11-15 07:30' "
                             "(24-hour clock)") from None
        if due <= now:
            raise ValueError("that time has already passed")
    if due - now > timedelta(days=MAX_DAYS):
        raise ValueError(f"reminders can be at most {MAX_DAYS} days ahead")
    return due


def describe_due(due: datetime, now: datetime) -> str:
    """Human wording of the due time for the confirmation, e.g. ``"11:00 today"``."""
    days = (due.date() - now.date()).days
    clock = due.strftime("%H:%M")
    if days == 0:
        return f"{clock} today"
    if days == 1:
        return f"{clock} tomorrow ({due:%A})"
    return f"{clock} on {due:%A %Y-%m-%d}"


@tool
def set_timer_reminder(message: str, minutes: float | None = None,
                       at: str | None = None) -> str:
    """Set a reminder that pops up on the pet at the right time and stays until the user clicks
    the pet. Only call it once the time is clear (if the user gave no time or a vague one, ask
    first). Pass the reminder text in the user's language as ``message``, and EITHER ``minutes``
    (from now; convert hours/seconds to minutes, e.g. 'in 2 hours' -> 120) OR ``at`` (a clock
    time, 24-hour 'HH:MM' such as '23:00'; add the date as 'YYYY-MM-DD HH:MM' for another day,
    e.g. tomorrow afternoon). Never work out the time yourself from minutes: pass what the user
    said. Reminders can be up to 7 days ahead."""
    if _service is None:
        return UNAVAILABLE
    if not message.strip():
        return "Error: the reminder needs a message. Ask the user what to remind them about."
    now = datetime.now()
    try:
        due = resolve_due(minutes, at, now)
    except ValueError as exc:
        return f"Error: {exc}."
    reminder_id = _service.schedule_reminder(due.timestamp(), message.strip())
    return (f'Okay! Reminder #{reminder_id} set for {describe_due(due, now)}: '
            f'"{message.strip()}". Tell the user the time in their language.')


def describe_reminder(reminder: PendingReminder, now: datetime) -> str:
    """One line naming a pending reminder for the model, e.g. ``#3 at 20:00 today: "call mom"``."""
    due = datetime.fromtimestamp(reminder.due)
    return f'#{reminder.id} at {describe_due(due, now)}: "{reminder.message}"'


@tool
def list_reminders() -> str:
    """List the reminders that are still waiting to go off (number, time, text). Call it before
    cancel_reminder, and when the user asks what reminders they have."""
    if _service is None:
        return UNAVAILABLE
    pending = _service.pending_reminders()
    if not pending:
        return "There are no pending reminders."
    now = datetime.now()
    return "Pending reminders:\n" + "\n".join(describe_reminder(r, now) for r in pending)


@tool
def cancel_reminder(reminder_id: int) -> str:
    """Cancel a pending reminder by its number (from list_reminders or from setting it), when the
    user no longer needs it. To change a reminder's time or text, cancel it and set a new one."""
    if _service is None:
        return UNAVAILABLE
    reminder = _service.cancel_reminder(int(reminder_id))
    if reminder is None:
        return (f"Error: there is no pending reminder #{reminder_id} (it may have gone off "
                "already). Call list_reminders to see the current ones.")
    return (f"Cancelled reminder {describe_reminder(reminder, datetime.now())}. "
            "Tell the user in their language.")


@tool
def dismiss_reminder_bubble() -> str:
    """Hide reminders that have ALREADY gone off and are still showing in the bubble on the pet
    (the same as the user clicking the pet). Use it when the user says to turn off / stop the
    reminder that is showing now; pending reminders are not affected."""
    if _service is None:
        return UNAVAILABLE
    _service.dismiss_shown_reminders()
    return "Done: the reminder bubble on the pet is hidden."
