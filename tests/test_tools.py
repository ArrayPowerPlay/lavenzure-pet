"""Tests for the agent tools with the network faked out."""
from datetime import datetime
from types import SimpleNamespace

import pytest
import requests

from agent.tools import set_timer_reminder as reminder_module
from agent.tools import weather, web_search


class FakeResponse:
    """Minimal stand-in for requests.Response."""

    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        """Never fails (the payload decides the outcome)."""

    def json(self):
        """Return the canned payload."""
        return self._payload


def test_weather_success(monkeypatch):
    """Geocode, then forecast, then a one-line summary."""
    def fake_get(url, params, timeout):
        if url == weather.GEOCODE_URL:
            return FakeResponse({"results": [{"latitude": 21.0, "longitude": 105.8,
                                              "name": "Hanoi", "country": "Vietnam"}]})
        return FakeResponse({"current_weather": {"temperature": 25.5, "windspeed": 7}})

    monkeypatch.setattr(weather.requests, "get", fake_get)
    text = weather.get_weather.invoke({"location": "Hanoi"})
    assert "Hanoi" in text and "25.5" in text


def test_weather_unknown_place(monkeypatch):
    """No geocoding results -> a clear message instead of a crash."""
    monkeypatch.setattr(weather.requests, "get", lambda *a, **k: FakeResponse({}))
    assert "couldn't find" in weather.get_weather.invoke({"location": "Nowhere"})


def test_weather_network_error_is_reported(monkeypatch):
    """A connection error becomes text for the model, not an exception."""
    def boom(*a, **k):
        raise requests.ConnectionError("offline")

    monkeypatch.setattr(weather.requests, "get", boom)
    assert "couldn't be reached" in weather.get_weather.invoke({"location": "Hanoi"})


class FakeTavily:
    """Stand-in Tavily client returning canned results or raising."""

    def __init__(self, result=None, error=None):
        self._result, self._error = result, error

    def search(self, query, max_results):
        """Return the canned result or raise the canned error."""
        if self._error:
            raise self._error
        return self._result


def test_web_search_formats_results(monkeypatch):
    """Results become a short bullet list."""
    monkeypatch.setattr(web_search, "_client", FakeTavily(
        {"results": [{"title": "PySide6", "content": "Qt for Python"}]}))
    assert web_search.web_search.invoke({"query": "pyside6"}) == "- PySide6: Qt for Python"


def test_web_search_error_is_reported(monkeypatch):
    """An API error is returned as text so the model can rephrase."""
    monkeypatch.setattr(web_search, "_client", FakeTavily(error=RuntimeError("bad query")))
    assert "Web search failed" in web_search.web_search.invoke({"query": "site:x"})


def test_web_search_without_key(monkeypatch):
    """No key configured -> explain instead of failing."""
    monkeypatch.setattr(web_search, "_client", None)
    assert "TAVILY_API_KEY" in web_search.web_search.invoke({"query": "x"})


@pytest.mark.parametrize(
    ("args", "accepted"),
    [({"minutes": 10, "message": "drink water"}, True),
     ({"at": "23:59", "message": "sleep"}, True),
     ({"minutes": 0, "message": "x"}, False),
     ({"minutes": -5, "message": "x"}, False),
     ({"minutes": 7 * 24 * 60 + 1, "message": "x"}, False),
     ({"minutes": 5, "message": "   "}, False),
     ({"message": "x"}, False),
     ({"minutes": 5, "at": "11:00", "message": "x"}, False),
     ({"at": "half past ten", "message": "x"}, False)],
)
def test_reminder_validation(monkeypatch, args, accepted):
    """Only sensible reminders reach the service (as a due timestamp + message)."""
    service = FakeReminderService()
    monkeypatch.setattr(reminder_module, "_service", service)
    reply = reminder_module.set_timer_reminder.invoke(args)
    assert bool(service.items) is accepted
    assert reply.startswith("Okay") is accepted
    if accepted:
        assert "#1" in reply


class FakeReminderService:
    """Stands in for the BackgroundMonitor in the reminder tool tests."""

    def __init__(self) -> None:
        """No reminders yet."""
        self.items: list[SimpleNamespace] = []
        self.dismissed = 0

    def schedule_reminder(self, due: float, message: str) -> int:
        """Keep the reminder; ids count from 1."""
        self.items.append(SimpleNamespace(id=len(self.items) + 1, due=due, message=message))
        return self.items[-1].id

    def pending_reminders(self) -> list:
        """The kept reminders, soonest first."""
        return sorted(self.items, key=lambda r: r.due)

    def cancel_reminder(self, reminder_id: int):
        """Remove and return a reminder, or None."""
        for item in self.items:
            if item.id == reminder_id:
                self.items.remove(item)
                return item
        return None

    def dismiss_shown_reminders(self) -> None:
        """Count the requests."""
        self.dismissed += 1


def test_list_and_cancel_reminders(monkeypatch):
    """list_reminders names each pending reminder by number; cancel_reminder removes one and
    explains when the number is unknown."""
    service = FakeReminderService()
    monkeypatch.setattr(reminder_module, "_service", service)
    assert "no pending" in reminder_module.list_reminders.invoke({})
    reminder_module.set_timer_reminder.invoke({"minutes": 30, "message": "call mom"})
    reminder_module.set_timer_reminder.invoke({"minutes": 10, "message": "tea"})
    listing = reminder_module.list_reminders.invoke({})
    assert listing.index('#2') < listing.index('#1')            # soonest first
    assert '"call mom"' in listing and ("today" in listing or "tomorrow" in listing)
    reply = reminder_module.cancel_reminder.invoke({"reminder_id": 1})
    assert reply.startswith("Cancelled") and "call mom" in reply
    assert [r.id for r in service.items] == [2]
    assert reminder_module.cancel_reminder.invoke({"reminder_id": 1}).startswith("Error")
    assert reminder_module.dismiss_reminder_bubble.invoke({}).startswith("Done")
    assert service.dismissed == 1


def test_reminder_tools_without_service(monkeypatch):
    """Before the monitor exists the tools say so instead of failing."""
    monkeypatch.setattr(reminder_module, "_service", None)
    for tool_, args in ((reminder_module.list_reminders, {}),
                        (reminder_module.cancel_reminder, {"reminder_id": 1}),
                        (reminder_module.dismiss_reminder_bubble, {})):
        assert tool_.invoke(args) == reminder_module.UNAVAILABLE


NOW = datetime(2026, 11, 14, 15, 20)


@pytest.mark.parametrize(("minutes", "at", "expected"), [
    (30, None, datetime(2026, 11, 14, 15, 50)),
    (None, "11:00", datetime(2026, 11, 15, 11, 0)),       # already past today -> tomorrow
    (None, "23:00", datetime(2026, 11, 14, 23, 0)),
    (None, "9 PM", datetime(2026, 11, 14, 21, 0)),
    (None, "2026-11-16 07:30", datetime(2026, 11, 16, 7, 30)),
])
def test_resolve_due(minutes, at, expected):
    """The code, not the model, works out the due time."""
    assert reminder_module.resolve_due(minutes, at, NOW) == expected


def test_resolve_due_rejects_past_dates():
    """An explicit date in the past is refused."""
    with pytest.raises(ValueError):
        reminder_module.resolve_due(None, "2026-11-13 08:00", NOW)


def test_describe_due():
    """The confirmation says today / tomorrow."""
    assert reminder_module.describe_due(datetime(2026, 11, 14, 23, 0), NOW) == "23:00 today"
    assert reminder_module.describe_due(datetime(2026, 11, 15, 11, 0), NOW).startswith(
        "11:00 tomorrow")
