"""Tests for agent.key_check with the HTTP layer faked out (no network)."""
import pytest
import requests

from agent import key_check
from agent.key_check import KeyStatus


class FakeResponse:
    """The bits of ``requests.Response`` the checker looks at."""

    def __init__(self, status_code, text=""):
        self.status_code, self.text = status_code, text


def fake_request(monkeypatch, response=None, error=None):
    """Make ``requests.request`` return ``response`` or raise ``error``; record the call."""
    calls = []

    def request(method, url, **kwargs):
        calls.append((method, url, kwargs))
        if error:
            raise error
        return response

    monkeypatch.setattr(key_check.requests, "request", request)
    return calls


@pytest.mark.parametrize(
    ("code", "body", "status"),
    [
        (200, "{}", KeyStatus.VALID),
        (400, "API key not valid. Please pass a valid API key.", KeyStatus.INVALID),
        (403, "", KeyStatus.INVALID),
        (401, "", KeyStatus.INVALID),
        (429, "RESOURCE_EXHAUSTED", KeyStatus.QUOTA),
        (432, "", KeyStatus.QUOTA),
        (500, "", KeyStatus.ERROR),
    ],
)
def test_gemini_answers(monkeypatch, code, body, status):
    """Each kind of Gemini answer maps to its status."""
    fake_request(monkeypatch, FakeResponse(code, body))
    assert key_check.check_gemini_key("k").status is status


def test_openai_key_travels_as_bearer_token(monkeypatch):
    """OpenAI is checked by listing models; a rejected key is INVALID."""
    calls = fake_request(monkeypatch, FakeResponse(401, "Incorrect API key provided"))
    result = key_check.check_openai_key("sk-SECRET")
    assert result.status is KeyStatus.INVALID
    assert calls[0][2]["headers"]["Authorization"] == "Bearer sk-SECRET"
    assert "sk-SECRET" not in calls[0][1]


def test_only_valid_counts_as_ok(monkeypatch):
    """``ok`` (= may be saved) is true only for a valid key."""
    fake_request(monkeypatch, FakeResponse(200))
    assert key_check.check_tavily_key("k").ok
    fake_request(monkeypatch, FakeResponse(401))
    assert not key_check.check_tavily_key("k").ok


@pytest.mark.parametrize("error", [requests.ConnectionError("x"), requests.Timeout("x")])
def test_network_problems_are_not_a_verdict_on_the_key(monkeypatch, error):
    """Connection trouble is reported as NETWORK, not INVALID."""
    fake_request(monkeypatch, error=error)
    assert key_check.check_gemini_key("k").status is KeyStatus.NETWORK


def test_key_travels_in_a_header_not_the_url(monkeypatch):
    """The key must never be part of the URL (it could leak into logs / error text)."""
    calls = fake_request(monkeypatch, FakeResponse(200))
    key_check.check_gemini_key("SECRET")
    _method, url, kwargs = calls[0]
    assert "SECRET" not in url
    assert "SECRET" not in str(kwargs.get("params", ""))
    assert kwargs["headers"]["x-goog-api-key"] == "SECRET"


def test_tavily_uses_the_smallest_search(monkeypatch):
    """The Tavily check asks for one result only."""
    calls = fake_request(monkeypatch, FakeResponse(200))
    key_check.check_tavily_key("SECRET")
    assert calls[0][2]["json"]["max_results"] == 1
    assert calls[0][2]["headers"]["Authorization"] == "Bearer SECRET"
