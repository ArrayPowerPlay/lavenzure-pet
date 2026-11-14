"""Tests for ``pet_lines``: both languages, 25 care + 50 fact/joke lines, hours, no repeats."""
import random
from datetime import datetime
from pathlib import Path

import pytest

from pet_lines import CARE, FACTS, LANGUAGES, PHRASES, PetLines, fits_hour, phrase

DATA = Path(__file__).resolve().parent.parent / "data"


@pytest.fixture
def lines():
    """Line pools with a fixed random seed."""
    return PetLines(DATA, rng=random.Random(4))


def at(hour: int) -> datetime:
    """A moment at ``hour`` o'clock."""
    return datetime(2026, 11, 14, hour, 30)


@pytest.mark.parametrize("language", list(LANGUAGES))
def test_pool_sizes(lines, language):
    """Each language has 25 care lines and 50 facts/jokes (decision of round 22)."""
    lines.set_language(language)
    assert len(lines.pool(CARE)) == 25
    assert len(lines.pool(FACTS)) == 50


def test_every_phrase_exists_in_every_language():
    """Alerts and reminder texts are translated for each language."""
    for language in LANGUAGES:
        assert PHRASES[language].keys() == PHRASES["en"].keys()


@pytest.mark.parametrize(("hours", "hour", "expected"), [
    ([5, 11], 7, True), ([5, 11], 11, False), ([22, 5], 23, True), ([22, 5], 3, True),
    ([22, 5], 12, False), (None, 12, True),
])
def test_fits_hour(hours, hour, expected):
    """``hours`` is a [start, end) window that may wrap past midnight."""
    entry = {"text": "x", "hours": hours} if hours else {"text": "x"}
    assert fits_hour(entry, hour) is expected


def test_ambient_alternates_care_and_facts(lines):
    """Care lines and facts/jokes take turns."""
    care = {e["text"] for e in lines.pool(CARE)}
    facts = {e["text"] for e in lines.pool(FACTS)}
    said = [lines.next_ambient(at(15)) for _ in range(6)]
    assert [s in care for s in said] == [True, False] * 3
    assert all(s in facts for s in said[1::2])


def test_ambient_says_every_fitting_line_before_repeating(lines):
    """A whole deck of facts is used up before any fact repeats."""
    facts = [lines.next_ambient(at(15)) for _ in range(100)][1::2]
    assert len(set(facts)) == 50


def test_care_lines_respect_their_hours(lines):
    """At noon the pet never asks about breakfast or tells you to go to sleep."""
    noon_only = {e["text"] for e in lines.pool(CARE) if fits_hour(e, 12)}
    said = [lines.next_ambient(at(12)) for _ in range(80)][0::2]
    assert set(said) <= noon_only
    assert "Have you had breakfast yet? Don't skip it!" not in said


def test_random_line_never_repeats_back_to_back(lines):
    """The click line is never the line said just before."""
    said = [lines.random_line(at(9)) for _ in range(200)]
    assert all(a != b for a, b in zip(said, said[1:], strict=False))


def test_language_switch_changes_lines(lines):
    """After switching to Vietnamese, lines come from the Vietnamese pools."""
    lines.set_language("vi")
    vi = {e["text"] for kind in (CARE, FACTS) for e in lines.pool(kind)}
    assert lines.next_ambient(at(9)) in vi
    assert lines.phrase("reminder", message="uống nước") == "Nhắc nhở: uống nước"


def test_unknown_language_falls_back_to_english(lines):
    """A bad value in the settings file never breaks the pet."""
    lines.set_language("fr")
    assert lines.language == "en"
    assert phrase("fr", "reminder", message="x") == "Reminder: x"


def test_when_in_both_languages():
    """Reminder times for the chat notes follow the language."""
    from datetime import datetime

    import pet_lines
    now = datetime(2026, 11, 14, 15, 20)
    assert pet_lines.when("en", datetime(2026, 11, 14, 21, 0), now) == "Today 21:00"
    assert pet_lines.when("vi", datetime(2026, 11, 15, 8, 0), now) == "08:00 ngày mai"
    assert pet_lines.when("en", datetime(2026, 11, 17, 9, 5), now) == "Tue 17/11, 09:05"
    assert pet_lines.when("vi", datetime(2026, 11, 17, 9, 5), now) == "09:05 T3 17/11"
