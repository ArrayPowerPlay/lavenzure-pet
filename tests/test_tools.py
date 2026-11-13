"""Tests for the agent tools with the network faked out."""
from datetime import datetime

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
    """Only sensible reminders reach the scheduler (as a due timestamp + message)."""
    calls = []
    monkeypatch.setattr(reminder_module, "_scheduler", lambda due, msg: calls.append((due, msg)))
    reply = reminder_module.set_timer_reminder.invoke(args)
    assert bool(calls) is accepted
    assert reply.startswith("Okay") is accepted


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
