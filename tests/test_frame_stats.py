"""Tests for ``overlay.overlay_window.FrameStats``: the periodic fps / time-per-frame log line."""
from __future__ import annotations

from overlay.overlay_window import FrameStats


def test_summary_only_after_interval():
    """No line until the interval has passed; then fps, average and max are reported."""
    stats = FrameStats(10.0)
    start = stats._start
    for i in range(59):
        assert stats.record(4.0 if i else 12.0, now=start + i * 0.1) is None
    line = stats.record(4.0, now=start + 10.0)
    assert line is not None
    assert "6.0 fps over 10s" in line
    assert "work avg 4.13 ms" in line
    assert "max 12.0 ms" in line
    assert stats.frames == 0  # a new window starts after each line


def test_zero_interval_disables_logging():
    """An interval of 0 never logs (and doesn't even count)."""
    stats = FrameStats(0)
    assert stats.record(5.0, now=stats._start + 1000) is None
    assert stats.frames == 0
