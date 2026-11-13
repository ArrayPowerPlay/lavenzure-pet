"""Reminders waiting to go off, kept in a small file so they survive restarts.

The file is ``%LOCALAPPDATA%\\Lavenzure\\reminders.json``, next to ``settings.json`` (decision of
round 24: saved to a file rather than kept in RAM only). It holds a list of
``{"due": <unix time>, "message": "..."}``; a reminder is removed from it as soon as it goes off,
so the file is empty most of the time. Reminders are independent of the chat history: wiping the
chat after 15 idle minutes does not touch them.

Only the UI thread uses a ``ReminderStore`` (the agent's tool hands reminders over through a
queued Qt signal, see ``BackgroundMonitor``).
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
    """One reminder: when it is due (unix time) and what to say."""

    due: float
    message: str


class ReminderStore:
    """The pending reminders, saved to disk after every change."""

    def __init__(self, path: Path | None = None) -> None:
        """Load ``path`` (default: ``default_path()``). A missing file means no reminders; a
        broken one is logged and replaced on the next change."""
        self.path = path or default_path()
        self._items: list[Reminder] = []
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
            self._items = [Reminder(float(r["due"]), str(r["message"])) for r in raw]
        except FileNotFoundError:
            pass
        except (OSError, ValueError, TypeError, KeyError) as exc:
            log.warning("Ignoring unreadable reminders file %s (%s)", self.path, exc)

    def __len__(self) -> int:
        """Number of reminders still waiting."""
        return len(self._items)

    def add(self, due: float, message: str) -> None:
        """Add a reminder due at unix time ``due`` and save."""
        self._items.append(Reminder(due, message))
        self._items.sort(key=lambda r: r.due)
        self._save()

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
        data = [{"due": r.due, "message": r.message} for r in self._items]
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.write_text(json.dumps(data, ensure_ascii=False, indent=2),
                                 encoding="utf-8")
        except OSError as exc:
            log.warning("Could not save reminders to %s (%s)", self.path, exc)
