"""Tests for monitor.user_activity: dozing after idle time and the night window."""
from datetime import datetime

import pytest

from monitor.user_activity import UserActivityWatcher, is_night


@pytest.mark.parametrize(("hour", "night"), [(19, False), (20, True), (23, True), (0, True),
                                             (4, True), (5, False), (12, False)])
def test_night_window_wraps_midnight(hour, night):
    """20:00-05:00 counts as night."""
    assert is_night(hour, 20, 5) is night


def test_same_day_window_and_empty_window():
    """A window inside one day works too; start == end means never night."""
    assert is_night(14, 13, 15) and not is_night(16, 13, 15)
    assert not is_night(3, 4, 4)


def test_dozes_after_idle_and_wakes_on_input(qapp):
    """Idle past 10 minutes -> dozing; any input -> awake again (one signal per change)."""
    idle = {"s": 0.0}
    watcher = UserActivityWatcher(idle_source=lambda: idle["s"],
                                  clock=lambda: datetime(2026, 1, 1, 12))
    seen = []
    watcher.dozing_changed.connect(seen.append)
    watcher.check()
    idle["s"] = 601.0
    watcher.check()
    watcher.check()
    idle["s"] = 0.5
    watcher.check()
    assert seen == [True, False]


def test_night_signal(qapp):
    """Crossing 20:00 reports night once."""
    now = {"t": datetime(2026, 1, 1, 19, 59)}
    watcher = UserActivityWatcher(idle_source=lambda: 0.0, clock=lambda: now["t"])
    seen = []
    watcher.night_changed.connect(seen.append)
    watcher.check()
    now["t"] = datetime(2026, 1, 1, 20, 0)
    watcher.check()
    watcher.check()
    assert seen == [True]


def test_coming_back_reports_time_away(qapp):
    """Waking from a doze reports how long the user was away (the last idle time seen)."""
    idle = {"s": 0.0}
    watcher = UserActivityWatcher(idle_source=lambda: idle["s"],
                                  clock=lambda: datetime(2026, 1, 1, 12))
    away = []
    watcher.user_returned.connect(away.append)
    watcher.check()
    idle["s"] = 1499.0
    watcher.check()
    idle["s"] = 0.3
    watcher.check()
    watcher.check()
    assert away == [1499.0]
