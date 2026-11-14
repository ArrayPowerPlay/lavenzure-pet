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
    monitor.schedule_reminder(time.time() + 600, "call mom")
    pump(qapp, 0.05)
    monitor._check_reminders()
    assert monitor.reminders == [] and len(monitor._reminders) == 1


def test_reminders_survive_a_restart(qapp, monitor, tmp_path):
    """Reminders are saved to the file: a new monitor (app restarted) still has them, and one
    that fell due while the app was closed fires saying how late it is."""
    monitor.schedule_reminder(time.time() - 30 * 60, "drink water")
    pump(qapp, 0.05)
    again = bm.BackgroundMonitor(reminders_path=tmp_path / "reminders.json")
    fired = []
    again.reminder_triggered.connect(lambda msg, late: fired.append((msg, late)))
    again._check_reminders()
    assert fired == [("drink water", 30)]
    assert len(ReminderStore(tmp_path / "reminders.json")) == 0     # gone once it went off
    for timer in (again._status_timer, again._reminder_timer, again._idle_timer):
        timer.stop()


def test_reminder_list_and_cancel_from_worker_thread(qapp, monitor, tmp_path):
    """The tools' calls (any thread): ids come back at once, the list is readable, a cancel
    removes the reminder from the list and the file, and every change is announced."""
    lists = []
    monitor.reminders_changed.connect(lists.append)
    ids = []
    worker = threading.Thread(target=lambda: ids.extend([
        monitor.schedule_reminder(time.time() + 900, "tea"),
        monitor.schedule_reminder(time.time() + 600, "stretch")]))
    worker.start()
    worker.join()
    pump(qapp, 0.05)
    assert ids == [1, 2]
    assert [r.message for r in monitor.pending_reminders()] == ["stretch", "tea"]   # soonest first
    result = []
    worker = threading.Thread(target=lambda: result.append(monitor.cancel_reminder(1)))
    worker.start()
    worker.join()
    pump(qapp, 0.05)
    assert result[0].message == "tea"
    assert [r.id for r in monitor.pending_reminders()] == [2]
    assert [r.id for r in ReminderStore(tmp_path / "reminders.json").items()] == [2]
    assert monitor.cancel_reminder(1) is None          # already gone
    assert len(lists) == 3 and [r.id for r in lists[-1]] == [2]


def test_reminder_ids_continue_after_restart(qapp, monitor, tmp_path):
    """A restarted monitor never hands out an id that a saved reminder already has."""
    monitor.schedule_reminder(time.time() + 600, "a")
    monitor.schedule_reminder(time.time() + 700, "b")
    pump(qapp, 0.05)
    again = bm.BackgroundMonitor(reminders_path=tmp_path / "reminders.json")
    assert again.schedule_reminder(time.time() + 800, "c") == 3
    for timer in (again._status_timer, again._reminder_timer, again._idle_timer):
        timer.stop()


def test_dismiss_from_worker_thread_reaches_ui_thread(qapp, monitor):
    """dismiss_shown_reminders (called by the tool) emits reminders_dismissed on the UI thread."""
    seen = []
    monitor.reminders_dismissed.connect(lambda: seen.append(threading.current_thread()))
    worker = threading.Thread(target=monitor.dismiss_shown_reminders)
    worker.start()
    worker.join()
    pump(qapp, 0.05)
    assert seen == [threading.main_thread()]


def test_store_numbers_reminders_from_older_files(tmp_path):
    """A file written before ids existed (or with clashing ids) gets unique numbers."""
    path = tmp_path / "reminders.json"
    path.write_text('[{"due": 200, "message": "b"}, {"due": 100, "message": "a"},'
                    ' {"id": 5, "due": 300, "message": "c"},'
                    ' {"id": 5, "due": 400, "message": "d"}]', encoding="utf-8")
    items = ReminderStore(path).items()
    assert [r.message for r in items] == ["a", "b", "c", "d"]
    assert sorted(r.id for r in items) == [5, 6, 7, 8]


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
