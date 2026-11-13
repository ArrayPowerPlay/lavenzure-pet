"""Tests for BackgroundMonitor: alert thresholds, reminders and idle lines (psutil faked)."""
import threading
import time
from types import SimpleNamespace

import pytest

from conftest import pump
from monitor import background_monitor as bm
from monitor.reminders import ReminderStore


@pytest.fixture
def monitor(qapp, monkeypatch, tmp_path):
    """A monitor with calm fake system readings; tests change them as needed."""
    readings = SimpleNamespace(cpu=10.0, ram=40.0, battery=None)
    monkeypatch.setattr(bm.psutil, "cpu_percent", lambda interval=None: readings.cpu)
    monkeypatch.setattr(bm.psutil, "virtual_memory", lambda: SimpleNamespace(percent=readings.ram))
    monkeypatch.setattr(bm.psutil, "sensors_battery", lambda: readings.battery)
    mon = bm.BackgroundMonitor(reminders_path=tmp_path / "reminders.json")
    mon.readings = readings
    mon.alerts, mon.reminders, mon.ambient = [], [], []
    mon.alert_triggered.connect(mon.alerts.append)
    mon.reminder_triggered.connect(lambda msg, late: mon.reminders.append((msg, late)))
    mon.ambient_due.connect(lambda: mon.ambient.append(1))
    yield mon
    for timer in (mon._status_timer, mon._reminder_timer, mon._idle_timer):
        timer.stop()


def test_no_alert_when_calm(monitor):
    """Normal readings raise nothing."""
    monitor._check_system_status()
    assert monitor.alerts == []


def test_cpu_alert_fires_once_until_cleared(monitor):
    """An alert is not repeated until the user clears it, nor during the snooze after that."""
    monitor.readings.cpu = 97
    monitor._check_system_status()
    monitor._check_system_status()
    assert len(monitor.alerts) == 1 and "97%" in monitor.alerts[0]
    monitor.clear_alert()
    monitor._check_system_status()
    assert len(monitor.alerts) == 1          # snoozed: still quiet right after dismissing
    monitor._snoozed_until -= monitor._snooze_seconds + 1
    monitor._check_system_status()
    assert len(monitor.alerts) == 2          # snooze over and still high: alert again


def test_snooze_is_ten_minutes_by_default(monitor):
    """Dismissing an alert keeps the pet quiet for 10 minutes (config default)."""
    assert monitor._snooze_seconds == 600


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
    thread = threading.Thread(target=monitor.schedule_reminder, args=(time.time(), "stretch"))
    thread.start()
    thread.join()
    pump(qapp, 0.05)  # deliver the queued signal
    monitor._check_reminders()
    assert monitor.reminders == [("stretch", 0)]


def test_reminder_waits_for_its_time(qapp, monitor):
    """A reminder in the future stays saved and silent until it is due."""
    monitor._add_reminder(time.time() + 600, "call mom")
    monitor._check_reminders()
    assert monitor.reminders == [] and len(monitor._reminders) == 1


def test_reminders_survive_a_restart(qapp, monitor, tmp_path):
    """Reminders are saved to the file: a new monitor (app restarted) still has them, and one
    that fell due while the app was closed fires saying how late it is."""
    monitor._add_reminder(time.time() - 30 * 60, "drink water")
    again = bm.BackgroundMonitor(reminders_path=tmp_path / "reminders.json")
    fired = []
    again.reminder_triggered.connect(lambda msg, late: fired.append((msg, late)))
    again._check_reminders()
    assert fired == [("drink water", 30)]
    assert len(ReminderStore(tmp_path / "reminders.json")) == 0     # gone once it went off
    for timer in (again._status_timer, again._reminder_timer, again._idle_timer):
        timer.stop()


def test_ambient_line_every_interval(monitor):
    """``ambient_due`` fires once the interval (5 min by default) has passed since the last line
    or interaction, then the clock restarts."""
    assert monitor._ambient_seconds == 300
    monitor._check_idle()
    assert monitor.ambient == []
    monitor._last_activity -= monitor._ambient_seconds + 1
    monitor._check_idle()
    assert len(monitor.ambient) == 1
    monitor._check_idle()
    assert len(monitor.ambient) == 1


def test_alerts_follow_the_language(monitor):
    """Alert texts are written in the language chosen in Settings."""
    monitor.set_language("vi")
    monitor.readings.ram = 95
    monitor._check_system_status()
    assert monitor.alerts == ["RAM đã dùng tới 95%! Máy sắp chậm rồi đó."]
