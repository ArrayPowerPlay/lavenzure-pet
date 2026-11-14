"""Ask the Gemini / OpenAI / Tavily servers whether an API key works, before it is saved.

Each check makes the smallest request that needs a valid key (Gemini and OpenAI: list the
models; Tavily: one search with a single result) and turns the answer into a ``CheckResult``. The
key is sent in a header, never in the URL, so it cannot end up in an error message or the log.
This runs a network request: call it from a worker thread, never from the UI thread.
"""
from __future__ import annotations

import enum
from dataclasses import dataclass

import requests

GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models"
OPENAI_URL = "https://api.openai.com/v1/models"
TAVILY_URL = "https://api.tavily.com/search"
TIMEOUT_SECONDS = 15


class KeyStatus(enum.Enum):
    """What the server said about the key."""

    VALID = "valid"
    INVALID = "invalid"      # the server does not know this key
    QUOTA = "quota"          # the key is known, but its free allowance is used up
    NETWORK = "network"      # could not reach the server (nothing is known about the key)
    ERROR = "error"          # any other answer


@dataclass(frozen=True)
class CheckResult:
    """The outcome of a key check, with a short sentence the Settings window can show."""

    status: KeyStatus
    message: str

    @property
    def ok(self) -> bool:
        """True only when the key is valid (the only case in which it gets saved)."""
        return self.status is KeyStatus.VALID


def _classify(code: int, body: str, service: str) -> CheckResult:
    """Turn an HTTP status (and body text) from ``service`` into a ``CheckResult``."""
    text = body.lower()
    if 200 <= code < 300:
        return CheckResult(KeyStatus.VALID, "Key works.")
    if code in (401, 403) or "api key not valid" in text or "api_key_invalid" in text:
        return CheckResult(KeyStatus.INVALID, f"{service} doesn't accept this key. "
                                              "Check that you copied all of it.")
    if code in (429, 432, 433) or "resource_exhausted" in text or "quota" in text:
        return CheckResult(KeyStatus.QUOTA, f"{service} says this key is out of quota for now. "
                                            "Try again later.")
    return CheckResult(KeyStatus.ERROR, f"{service} answered with an unexpected error ({code}).")


def _request(method: str, url: str, service: str, **kwargs) -> CheckResult:
    """Send one request and classify the answer; connection problems become ``NETWORK``."""
    try:
        response = requests.request(method, url, timeout=TIMEOUT_SECONDS, **kwargs)
    except (requests.ConnectionError, requests.Timeout):
        return CheckResult(KeyStatus.NETWORK, "Couldn't reach the internet to check the key. "
                                              "Try again in a moment.")
    except requests.RequestException:
        return CheckResult(KeyStatus.ERROR, f"Couldn't check the key with {service}.")
    return _classify(response.status_code, response.text, service)


def check_gemini_key(key: str) -> CheckResult:
    """Check a Gemini key by listing the models it can use."""
    return _request("GET", GEMINI_URL, "Gemini", headers={"x-goog-api-key": key},
                    params={"pageSize": 1})


def check_openai_key(key: str) -> CheckResult:
    """Check an OpenAI key by listing the models it can use."""
    return _request("GET", OPENAI_URL, "OpenAI", headers={"Authorization": f"Bearer {key}"})


def check_tavily_key(key: str) -> CheckResult:
    """Check a Tavily key with the smallest possible search (one result)."""
    return _request("POST", TAVILY_URL, "Tavily", headers={"Authorization": f"Bearer {key}"},
                    json={"query": "test", "max_results": 1})
