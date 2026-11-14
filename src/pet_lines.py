"""Everything the pet says on its own, in the language picked in Settings (English / Vietnamese).

Two pools per language live in ``data/`` (decisions of rounds 20-22):

- ``care_lines.json`` - 20 caring lines (have you eaten, drink some water, sleep early...). A
  line may carry ``"hours": [start, end)`` (local hours, wrapping past midnight when
  ``end < start``) and is only said at those hours, e.g. "Have you had breakfast?" in the
  morning.
- ``facts_jokes.json`` - 50 fire facts and jokes.

``PetLines`` hands out:

- ``next_ambient(now)`` - the line said on its own every few minutes: care line and fact/joke take
  turns. Each pool is drawn like a shuffled deck, so every fitting line is said once before any
  repeats, and never the same line twice in a row.
- ``random_line(now)`` - the line for the "speak" click reaction: any of the 70 lines (care lines
  only at their hours), never the one said just before.
- ``phrase(key, **values)`` - short fixed texts outside the pools (system alerts, the
  "Reminder:" prefix, used only for reminders saved without a pet line), from ``PHRASES``.

Chat replies are not covered here: the AI answers in whatever language the user writes in.
"""
from __future__ import annotations

import json
import random
from datetime import datetime
from pathlib import Path

# Language code -> name shown in Settings (each name in its own language).
LANGUAGES: dict[str, str] = {"en": "English", "vi": "Tiếng Việt"}
DEFAULT_LANGUAGE = "en"

# Fixed texts outside the line pools, per language (``str.format`` placeholders).
PHRASES: dict[str, dict[str, str]] = {
    "en": {
        "cpu_alert": "CPU usage is at {value:.0f}%! Might want to check what's running.",
        "ram_alert": "RAM usage is at {value:.0f}%! Things might slow down soon.",
        "battery_alert": "Battery is down to {value:.0f}%. Better plug in!",
        "reminder": "Reminder: {message}",
        "reminder_late": "Reminder ({minutes} min late): {message}",
        "reminder_line_late": "{line} ({minutes} min late)",
        "reminder_set_note": "⏰ Reminder set: {when} · {message}",
        "reminder_cancelled_note": "⏰ Reminder cancelled: {when} · {message}",
        "today": "Today {clock}",
        "tomorrow": "Tomorrow {clock}",
        "other_day": "{weekday} {day}/{month}, {clock}",
    },
    "vi": {
        "cpu_alert": "CPU đang chạy tới {value:.0f}%! Xem thử app nào đang ngốn máy nhé.",
        "ram_alert": "RAM đã dùng tới {value:.0f}%! Máy sắp chậm rồi đó.",
        "battery_alert": "Pin chỉ còn {value:.0f}%. Cắm sạc đi bạn ơi!",
        "reminder": "Nhắc nhở: {message}",
        "reminder_late": "Nhắc nhở (trễ {minutes} phút): {message}",
        "reminder_line_late": "{line} (trễ {minutes} phút)",
        "reminder_set_note": "⏰ Đã đặt nhắc: {when} · {message}",
        "reminder_cancelled_note": "⏰ Đã huỷ nhắc: {when} · {message}",
        "today": "{clock} hôm nay",
        "tomorrow": "{clock} ngày mai",
        "other_day": "{clock} {weekday} {day}/{month}",
    },
}

# Short weekday names (Monday first), for ``when()``.
WEEKDAYS: dict[str, list[str]] = {
    "en": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
    "vi": ["T2", "T3", "T4", "T5", "T6", "T7", "CN"],
}

CARE = "care"
FACTS = "facts"


def phrase(language: str, key: str, **values) -> str:
    """The fixed text ``key`` in ``language`` (English if the language is unknown), filled in."""
    table = PHRASES.get(language, PHRASES[DEFAULT_LANGUAGE])
    return table[key].format(**values)


def when(language: str, due: datetime, now: datetime) -> str:
    """A reminder's time in ``language``: today / tomorrow / weekday + date, e.g.
    ``"Today 21:00"`` or ``"21:00 hôm nay"``."""
    clock = due.strftime("%H:%M")
    days = (due.date() - now.date()).days
    if days == 0:
        return phrase(language, "today", clock=clock)
    if days == 1:
        return phrase(language, "tomorrow", clock=clock)
    weekdays = WEEKDAYS.get(language, WEEKDAYS[DEFAULT_LANGUAGE])
    return phrase(language, "other_day", clock=clock, weekday=weekdays[due.weekday()],
                  day=due.day, month=due.month)


def fits_hour(entry: dict, hour: int) -> bool:
    """True when a care line may be said at ``hour`` (lines without ``hours`` always fit)."""
    hours = entry.get("hours")
    if not hours:
        return True
    start, end = hours
    if start <= end:
        return start <= hour < end
    return hour >= start or hour < end      # wraps past midnight, e.g. [22, 5)


class PetLines:
    """The line pools of both languages and the "deck" state used to avoid repeats."""

    def __init__(self, data_dir: Path, language: str = DEFAULT_LANGUAGE,
                 rng: random.Random | None = None) -> None:
        """Load ``care_lines.json`` and ``facts_jokes.json`` from ``data_dir``."""
        self._rng = rng or random.Random()
        care = json.loads((data_dir / "care_lines.json").read_text(encoding="utf-8"))
        facts = json.loads((data_dir / "facts_jokes.json").read_text(encoding="utf-8"))
        # pools[language][kind] = list of {"text": ..., "hours": ... (care lines only)}
        self._pools: dict[str, dict[str, list[dict]]] = {
            code: {CARE: list(care[code]), FACTS: [{"text": t} for t in facts[code]]}
            for code in LANGUAGES
        }
        self._decks: dict[tuple[str, str], list[int]] = {}
        self._last_index: dict[tuple[str, str], int] = {}
        self._next_kind = CARE
        self._last_text = ""
        self.language = DEFAULT_LANGUAGE
        self.set_language(language)

    def set_language(self, language: str) -> None:
        """Switch every line to ``language`` (unknown codes fall back to English)."""
        self.language = language if language in LANGUAGES else DEFAULT_LANGUAGE

    def when(self, due: datetime, now: datetime) -> str:
        """A reminder's time in the current language (see the module function ``when``)."""
        return when(self.language, due, now)

    def phrase(self, key: str, **values) -> str:
        """A fixed text (alert, reminder prefix) in the current language."""
        return phrase(self.language, key, **values)

    def pool(self, kind: str) -> list[dict]:
        """All entries of one pool (``CARE`` or ``FACTS``) in the current language."""
        return self._pools[self.language][kind]

    def next_ambient(self, now: datetime) -> str:
        """The next line the pet says on its own: care lines and facts/jokes take turns."""
        kind = self._next_kind
        self._next_kind = FACTS if kind == CARE else CARE
        text = self._draw(kind, now.hour)
        self._last_text = text
        return text

    def random_line(self, now: datetime) -> str:
        """A random line for the "speak" click reaction: any line that fits the hour, but not
        the one said just before."""
        candidates = [e["text"] for kind in (CARE, FACTS) for e in self.pool(kind)
                      if fits_hour(e, now.hour) and e["text"] != self._last_text]
        text = self._rng.choice(candidates)
        self._last_text = text
        return text

    def _draw(self, kind: str, hour: int) -> str:
        """Take the next fitting line from the shuffled deck of ``kind`` (reshuffling once every
        fitting line has been said; the last line said is never first in the new deck)."""
        entries = self.pool(kind)
        key = (self.language, kind)
        fitting = {i for i, e in enumerate(entries) if fits_hour(e, hour)}
        deck = self._decks.setdefault(key, [])
        choices = [i for i in deck if i in fitting]
        if not choices:
            deck[:] = list(range(len(entries)))
            self._rng.shuffle(deck)
            last = self._last_index.get(key)
            choices = [i for i in deck if i in fitting and i != last] or sorted(fitting)
        index = choices[0]
        if index in deck:
            deck.remove(index)
        self._last_index[key] = index
        return entries[index]["text"]
