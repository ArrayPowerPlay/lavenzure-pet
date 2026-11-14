"""Watches whether the user is at the computer and what time of day it is.

- **Dozing:** when nobody has touched the mouse or keyboard for ``behavior.doze_after_minutes``
  (default 10), ``dozing_changed(True)`` fires and the pet dozes off; the first input after that
  fires ``dozing_changed(False)`` and it wakes up. The idle time comes from the Windows
  ``GetLastInputInfo`` call, which covers input to *any* application.
- **Coming back:** together with that wake-up, ``user_returned(seconds)`` reports how long the
  user was away (idle time just before the first input), so the pet can say "Welcome back!"
  (task T1). It only fires after a doze, i.e. after at least ``doze_after_minutes`` away.
- **Night:** between ``behavior.night_start_hour`` (default 20) and ``behavior.night_end_hour``
  (default 5) ``night_changed(True)`` fires: the pet looks calmer and moves slower, but is never
  put to sleep by the clock.
"""
from __future__ import annotations

import ctypes
import sys
from datetime import datetime

from PySide6.QtCore import QObject, QTimer, Signal

import config

POLL_MS = 1000


class _LastInputInfo(ctypes.Structure):
    """The Win32 ``LASTINPUTINFO`` struct."""

    _fields_ = [("cbSize", ctypes.c_uint), ("dwTime", ctypes.c_uint)]


def seconds_since_input() -> float:
    """Seconds since the last mouse / keyboard input anywhere on the system (0 off Windows)."""
    if sys.platform != "win32":
        return 0.0
    info = _LastInputInfo()
    info.cbSize = ctypes.sizeof(info)
    if not ctypes.windll.user32.GetLastInputInfo(ctypes.byref(info)):
        return 0.0
    # Both counters are 32-bit milliseconds that wrap after ~49 days; the mask handles the wrap.
    now = ctypes.windll.kernel32.GetTickCount() & 0xFFFFFFFF
    return ((now - info.dwTime) & 0xFFFFFFFF) / 1000.0


def is_night(hour: int, start: int, end: int) -> bool:
    """True when ``hour`` (0-23) is inside the night window ``start``..``end`` (may wrap)."""
    if start == end:
        return False
    if start < end:
        return start <= hour < end
    return hour >= start or hour < end


class UserActivityWatcher(QObject):
    """Polls the idle time and the clock once a second and reports changes."""

    dozing_changed = Signal(bool)
    night_changed = Signal(bool)
    user_returned = Signal(float)   # seconds the user was away (emitted when a doze ends)

    def __init__(self, idle_source=seconds_since_input, clock=datetime.now) -> None:
        """``idle_source`` / ``clock`` can be replaced in tests."""
        super().__init__()
        self._idle_source = idle_source
        self._clock = clock
        self._doze_after = float(config.get("behavior.doze_after_minutes", 10)) * 60.0
        self._night_start = int(config.get("behavior.night_start_hour", 20))
        self._night_end = int(config.get("behavior.night_end_hour", 5))
        self.dozing = False
        self.night = False
        self._last_idle = 0.0      # idle seconds at the previous poll (= time away on return)
        self._timer = QTimer(self)
        self._timer.timeout.connect(self.check)
        self._timer.start(POLL_MS)

    def check(self) -> None:
        """Compare the current idle time and hour with the last state; emit on changes."""
        idle = self._idle_source()
        dozing = idle >= self._doze_after
        if dozing != self.dozing:
            self.dozing = dozing
            self.dozing_changed.emit(dozing)
            if not dozing:
                # Input arrived since the last poll: the user was away for about as long as the
                # idle time measured then (plus the part of a second until the input).
                self.user_returned.emit(max(self._last_idle, self._doze_after))
        self._last_idle = idle
        night = is_night(self._clock().hour, self._night_start, self._night_end)
        if night != self.night:
            self.night = night
            self.night_changed.emit(night)
