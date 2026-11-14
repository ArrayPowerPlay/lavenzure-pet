"""Turn agent failures into short, friendly (English) chat replies.

The Gemini / OpenAI / LangChain / HTTP libraries raise many different exception types, and
their class hierarchy changes between versions. Instead of importing them, ``classify_error`` looks at the
whole exception chain (``__cause__`` / ``__context__``): class names in each MRO, an HTTP ``code``
attribute when present, and well-known phrases in the message.
"""
from __future__ import annotations

import enum


class MissingApiKeyError(RuntimeError):
    """Raised when the chat is used but no API key is configured for the chosen AI provider."""


class ErrorKind(enum.Enum):
    """Broad failure categories, each with its own friendly reply."""

    MISSING_KEY = "missing_key"
    BAD_KEY = "bad_key"
    QUOTA = "quota"
    MODEL_GONE = "model_gone"
    NETWORK = "network"
    SERVER = "server"
    UNKNOWN = "unknown"


FRIENDLY_MESSAGES: dict[ErrorKind, str] = {
    ErrorKind.MISSING_KEY: (
        "I can't think without an API key! Right-click my tray icon, open Settings and "
        "paste your Gemini or OpenAI key in."
    ),
    ErrorKind.BAD_KEY: (
        "My AI service didn't accept my API key. Could you check it in Settings (tray icon)?"
    ),
    ErrorKind.QUOTA: (
        "Phew, I've used up my AI quota for now. Give me a little while and try again!"
    ),
    ErrorKind.MODEL_GONE: (
        "The AI model I'm set to use isn't available anymore. "
        "A newer version of me should fix that."
    ),
    ErrorKind.NETWORK: (
        "I can't reach the internet right now. Check your connection and try again?"
    ),
    ErrorKind.SERVER: (
        "The AI servers are having a rough moment. Try again in a minute?"
    ),
    ErrorKind.UNKNOWN: "Oops, my flame flickered out for a second. Try again?",
}

_NETWORK_NAME_HINTS = ("ConnectError", "ConnectionError", "Timeout", "NetworkError", "ProxyError")


def _chain(exc: BaseException):
    """Yield ``exc`` and every exception it was raised from / during (cycle-safe)."""
    seen: set[int] = set()
    while exc is not None and id(exc) not in seen:
        seen.add(id(exc))
        yield exc
        exc = exc.__cause__ or exc.__context__


def _http_code(exc: BaseException) -> int | None:
    """Return an HTTP status code stored on the exception (``code`` / ``status_code``), if any."""
    for attr in ("code", "status_code"):
        value = getattr(exc, attr, None)
        if isinstance(value, int) and 100 <= value < 600:
            return value
    return None


def classify_error(exc: BaseException) -> ErrorKind:
    """Map any exception raised while running the agent to an ``ErrorKind``."""
    for err in _chain(exc):
        if isinstance(err, MissingApiKeyError):
            return ErrorKind.MISSING_KEY

        names = " ".join(cls.__name__ for cls in type(err).__mro__)
        text = str(err).lower()
        code = _http_code(err)

        if "Authentication" in names or "PermissionDenied" in names or code in (401, 403) \
                or "api key not valid" in text or "api_key_invalid" in text:
            return ErrorKind.BAD_KEY
        if "RateLimit" in names or code == 429 or "resource_exhausted" in text \
                or "quota" in text:
            return ErrorKind.QUOTA
        if "NotFound" in names or code == 404:
            return ErrorKind.MODEL_GONE
        if any(hint in names for hint in _NETWORK_NAME_HINTS) \
                or isinstance(err, (ConnectionError, TimeoutError)) \
                or "getaddrinfo failed" in text or "name resolution" in text:
            return ErrorKind.NETWORK
        if code is not None and code >= 500:
            return ErrorKind.SERVER
    return ErrorKind.UNKNOWN


def friendly_error(exc: BaseException) -> str:
    """Return the in-character chat reply for ``exc``."""
    return FRIENDLY_MESSAGES[classify_error(exc)]
