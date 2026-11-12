"""Tests for BackgroundMonitor: alert thresholds, reminders and idle lines (psutil faked)."""
import threading
from types import SimpleNamespace

import pytest

from conftest import pump
from monitor import background_monitor as bm


@pytest.fixture
def monitor(qapp, monkeypatch):
    """A monitor with calm fake system readings; tests change them as needed."""
    readings = SimpleNamespace(cpu=10.0, ram=40.0, battery=None)
    monkeypatch.setattr(bm.psutil, "cpu_percent", lambda interval=None: readings.cpu)
    monkeypatch.setattr(bm.psutil, "virtual_memory", lambda: SimpleNamespace(percent=readings.ram))
    monkeypatch.setattr(bm.psutil, "sensors_battery", lambda: readings.battery)
    mon = bm.BackgroundMonitor()
    mon.readings = readings
    mon.alerts, mon.reminders, mon.jokes = [], [], []
    mon.alert_triggered.connect(mon.alerts.append)
    mon.reminder_triggered.connect(mon.reminders.append)
    mon.joke_triggered.connect(mon.jokes.append)
    yield mon
    for timer in (mon._status_timer, mon._reminder_timer, mon._idle_timer):
        timer.stop()


def test_no_alert_when_calm(monitor):
    """Normal readings raise nothing."""
    monitor._check_system_status()
    assert monitor.alerts == []


def test_cpu_alert_fires_once_until_cleared(monitor):
    """An alert is not repeated until the user clears it by clicking the pet."""
    monitor.readings.cpu = 97
    monitor._check_system_status()
    monitor._check_system_status()
    assert len(monitor.alerts) == 1 and "97%" in monitor.alerts[0]
    monitor.clear_alert()
    monitor._check_system_status()
    assert len(monitor.alerts) == 2


def test_battery_alert_only_when_unplugged(monitor):
    """Low battery alerts only while running on battery."""
    monitor.readings.battery = SimpleNamespace(percent=20, power_plugged=True)
    monitor._check_system_status()
    assert monitor.alerts == []
    monitor.readings.battery = SimpleNamespace(percent=20, power_plugged=False)
    monitor._check_system_status()
    assert "Battery" in monitor.alerts[0]


def test_reminder_from_worker_thread_fires(qapp, monitor):
    """schedule_reminder may be called from another thread; it fires on the UI thread."""
    thread = threading.Thread(target=monitor.schedule_reminder, args=(0, "stretch"))
    thread.start()
    thread.join()
    pump(qapp, 0.05)  # deliver the queued signal
    monitor._check_reminders()
    assert monitor.reminders == ["stretch"]


def test_idle_line_after_idle_time(monitor):
    """A fact/joke is emitted only after the idle period, then the clock restarts."""
    monitor._check_idle()
    assert monitor.jokes == []
    monitor._last_activity -= monitor._idle_minutes * 60 + 1
    monitor._check_idle()
    assert len(monitor.jokes) == 1
    monitor._check_idle()
    assert len(monitor.jokes) == 1
