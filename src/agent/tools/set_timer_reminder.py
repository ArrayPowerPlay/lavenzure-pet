"""Reminder tool; actual scheduling is delegated to the BackgroundMonitor at app startup."""
from __future__ import annotations

from typing import Callable, Optional

from langchain_core.tools import tool

_scheduler: Optional[Callable[[float, str], None]] = None


def register_reminder_scheduler(fn: Callable[[float, str], None]) -> None:
    global _scheduler
    _scheduler = fn


@tool
def set_timer_reminder(minutes: float, message: str) -> str:
    """Set a reminder that pops up after a number of minutes, e.g. 'remind me to drink water in 10 minutes'."""
    if _scheduler is None:
        return "Reminders aren't available right now."
    _scheduler(minutes, message)
    return f'Okay! I\'ll remind you in {minutes:g} minutes: "{message}".'
