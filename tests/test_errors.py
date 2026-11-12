"""Tests for agent.errors: mapping library exceptions to friendly chat replies."""
import pytest

from agent.errors import ErrorKind, MissingApiKeyError, classify_error, friendly_error


class FakeHttpError(Exception):
    """Mimics google-genai errors, which carry an HTTP ``code`` attribute."""

    def __init__(self, code, message=""):
        super().__init__(message)
        self.code = code


class GoogleRateLimitError(Exception):
    """Same class name as the langchain-google-genai rate-limit error."""


class ConnectError(Exception):
    """Same class name as httpx.ConnectError."""


@pytest.mark.parametrize(
    ("exc", "kind"),
    [
        (MissingApiKeyError("no key"), ErrorKind.MISSING_KEY),
        (FakeHttpError(400, "API key not valid. Please pass a valid API key."), ErrorKind.BAD_KEY),
        (FakeHttpError(403), ErrorKind.BAD_KEY),
        (FakeHttpError(429), ErrorKind.QUOTA),
        (GoogleRateLimitError("slow down"), ErrorKind.QUOTA),
        (FakeHttpError(400, "RESOURCE_EXHAUSTED: quota exceeded"), ErrorKind.QUOTA),
        (FakeHttpError(404, "model not found"), ErrorKind.MODEL_GONE),
        (ConnectError("boom"), ErrorKind.NETWORK),
        (TimeoutError(), ErrorKind.NETWORK),
        (OSError("[Errno 11001] getaddrinfo failed"), ErrorKind.NETWORK),
        (FakeHttpError(503), ErrorKind.SERVER),
        (ValueError("something else"), ErrorKind.UNKNOWN),
    ],
)
def test_classify(exc, kind):
    """Each failure family maps to its category."""
    assert classify_error(exc) is kind


def test_classify_looks_through_exception_chain():
    """A wrapper exception is classified by what caused it."""
    try:
        try:
            raise ConnectError("dns")
        except ConnectError as inner:
            raise RuntimeError("agent failed") from inner
    except RuntimeError as outer:
        assert classify_error(outer) is ErrorKind.NETWORK


def test_friendly_error_is_english_text():
    """The reply shown in the chat mentions what the user should fix."""
    assert "GEMINI_API_KEY" in friendly_error(MissingApiKeyError())
