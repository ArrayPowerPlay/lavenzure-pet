"""Reminder tool: "remind me in 30 minutes to ..." or "remind me at 11:00 to ...".

The model only passes what the user said (``minutes`` from now, or a clock time ``at``); this code
works out the actual due time, because language models are unreliable at clock arithmetic
(decision of round 21). A clock time that has already passed today means tomorrow.

The tool runs on the agent's worker thread. The registered scheduler (``BackgroundMonitor.
schedule_reminder``) only emits a Qt signal, which Qt delivers to the monitor on the UI thread,
so no shared state is touched across threads. The monitor saves reminders to a file, so they
survive the chat history being wiped and the app being restarted.
"""
from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timedelta

from langchain_core.tools import tool

MAX_DAYS = 7  # how far ahead a reminder may be set

_scheduler: Callable[[float, str], None] | None = None


def register_reminder_scheduler(fn: Callable[[float, str], None]) -> None:
    """Install the function that actually schedules reminders (set by the BackgroundMonitor).
    It is called as ``fn(due_timestamp, message)``."""
    global _scheduler
    _scheduler = fn


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
    the pet. Pass the reminder text in the user's language as ``message``, and EITHER ``minutes``
    (from now; convert hours/seconds to minutes, e.g. 'in 2 hours' -> 120) OR ``at`` (a clock
    time, 24-hour 'HH:MM' such as '23:00'; add the date as 'YYYY-MM-DD HH:MM' for another day,
    e.g. tomorrow afternoon). Never work out the time yourself from minutes: pass what the user
    said. Reminders can be up to 7 days ahead."""
    if _scheduler is None:
        return "Reminders aren't available right now."
    if not message.strip():
        return "Error: the reminder needs a message. Ask the user what to remind them about."
    now = datetime.now()
    try:
        due = resolve_due(minutes, at, now)
    except ValueError as exc:
        return f"Error: {exc}."
    _scheduler(due.timestamp(), message.strip())
    return (f'Okay! Reminder set for {describe_due(due, now)}: "{message.strip()}". '
            "Tell the user the time in their language.")
