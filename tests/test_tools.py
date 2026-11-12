"""Tests for the agent tools with the network faked out."""
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
    ("minutes", "message", "accepted"),
    [(10, "drink water", True), (0, "x", False), (-5, "x", False), (1441, "x", False),
     (5, "   ", False)],
)
def test_reminder_validation(monkeypatch, minutes, message, accepted):
    """Only sensible reminders reach the scheduler."""
    calls = []
    monkeypatch.setattr(reminder_module, "_scheduler", lambda m, msg: calls.append((m, msg)))
    reply = reminder_module.set_timer_reminder.invoke({"minutes": minutes, "message": message})
    assert bool(calls) is accepted
    assert reply.startswith("Okay") is accepted
