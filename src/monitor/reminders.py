"""Reminders waiting to go off, kept in a small file so they survive restarts.

The file is ``%LOCALAPPDATA%\\Lavenzure\\reminders.json``, next to ``settings.json`` (decision of
round 24: saved to a file rather than kept in RAM only). It holds a list of
``{"id": <number>, "due": <unix time>, "message": "..."}``; a reminder is removed from it as soon
as it goes off or is cancelled (round 25: from the chat or the bubble's Reminders tab), so the
file is empty most of the time. Reminders are independent of the chat history: wiping the chat
after 15 idle minutes does not touch them.

The ``id`` is a small number that names a reminder while it is pending, so the AI and the
Reminders tab can say which one to cancel. Files written before ids existed get numbers when
they are loaded.

Only the UI thread uses a ``ReminderStore`` (the agent's tools hand requests over through queued
Qt signals, see ``BackgroundMonitor``).
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path

from user_settings import app_data_dir

log = logging.getLogger(__name__)


def default_path() -> Path:
    """Where the reminders file lives (see the module doc)."""
    return app_data_dir() / "reminders.json"


@dataclass(frozen=True)
class Reminder:
    """One reminder: its number, when it is due (unix time) and what to say."""

    id: int
    due: float
    message: str


class ReminderStore:
    """The pending reminders, sorted by due time and saved to disk after every change."""

    def __init__(self, path: Path | None = None) -> None:
        """Load ``path`` (default: ``default_path()``). A missing file means no reminders; a
        broken one is logged and replaced on the next change."""
        self.path = path or default_path()
        self._items: list[Reminder] = []
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
            used: set[int] = set()
            for entry in raw:
                rid = entry.get("id")
                if not isinstance(rid, int) or rid <= 0 or rid in used:
                    rid = 0     # numbered below, after every valid id is known
                used.add(rid)
                self._items.append(Reminder(rid, float(entry["due"]), str(entry["message"])))
            next_id = max(used, default=0) + 1
            for index, item in enumerate(self._items):
                if item.id == 0:
                    self._items[index] = Reminder(next_id, item.due, item.message)
                    next_id += 1
            self._items.sort(key=lambda r: r.due)
        except FileNotFoundError:
            pass
        except (OSError, ValueError, TypeError, KeyError, AttributeError) as exc:
            log.warning("Ignoring unreadable reminders file %s (%s)", self.path, exc)
            self._items = []

    def __len__(self) -> int:
        """Number of reminders still waiting."""
        return len(self._items)

    def items(self) -> tuple[Reminder, ...]:
        """Every pending reminder, soonest first (an immutable snapshot)."""
        return tuple(self._items)

    def max_id(self) -> int:
        """The highest id in use (0 when empty); new ids must be larger."""
        return max((r.id for r in self._items), default=0)

    def add(self, reminder: Reminder) -> None:
        """Add ``reminder`` (its id must not be in use yet) and save."""
        self._items.append(reminder)
        self._items.sort(key=lambda r: r.due)
        self._save()

    def remove(self, reminder_id: int) -> Reminder | None:
        """Remove the reminder with ``reminder_id`` and save; returns it, or ``None`` when no
        pending reminder has that id (it already went off or was cancelled)."""
        for reminder in self._items:
            if reminder.id == reminder_id:
                self._items.remove(reminder)
                self._save()
                return reminder
        return None

    def pop_due(self, now: float) -> list[Reminder]:
        """Remove and return every reminder due at or before ``now`` (oldest first); saves only
        when something was removed."""
        due = [r for r in self._items if r.due <= now]
        if due:
            self._items = [r for r in self._items if r.due > now]
            self._save()
        return due

    def _save(self) -> None:
        """Write the list to disk (a failure is logged; the reminders still work this run)."""
        data = [{"id": r.id, "due": r.due, "message": r.message} for r in self._items]
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.write_text(json.dumps(data, ensure_ascii=False, indent=2),
                                 encoding="utf-8")
        except OSError as exc:
            log.warning("Could not save reminders to %s (%s)", self.path, exc)
