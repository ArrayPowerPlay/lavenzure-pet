"""Reminder tool; actual scheduling is delegated to the BackgroundMonitor at app startup.

The tool runs on the agent's worker thread. The registered scheduler (``BackgroundMonitor.
schedule_reminder``) only emits a Qt signal, which Qt delivers to the monitor on the UI thread,
so no shared state is touched across threads.
"""
from __future__ import annotations

from collections.abc import Callable

from langchain_core.tools import tool

MAX_MINUTES = 24 * 60  # reminders live in RAM only, so keep them within a day

_scheduler: Callable[[float, str], None] | None = None


def register_reminder_scheduler(fn: Callable[[float, str], None]) -> None:
    """Install the function that actually schedules reminders (set by the BackgroundMonitor)."""
    global _scheduler
    _scheduler = fn


@tool
def set_timer_reminder(minutes: float, message: str) -> str:
    """Set a reminder that pops up after a number of minutes (at most 24 hours), e.g. 'remind me
    to drink water in 10 minutes'. Convert hours or seconds to minutes."""
    if _scheduler is None:
        return "Reminders aren't available right now."
    if not message.strip():
        return "Error: the reminder needs a message. Ask the user what to remind them about."
    if minutes <= 0:
        return "Error: minutes must be greater than 0."
    if minutes > MAX_MINUTES:
        return "Error: reminders can be at most 24 hours (1440 minutes) away."
    _scheduler(minutes, message.strip())
    return f'Okay! I\'ll remind you in {minutes:g} minutes: "{message.strip()}".'
