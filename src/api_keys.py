"""Where the API keys (Gemini, OpenAI, Tavily) come from, and how they are kept safe.

The keys the user types into Settings (Gemini or OpenAI for the chat, Tavily for web search) are
stored with ``keyring`` (on Windows that is the Credential Manager) under the service name
``Lavenzure``: one entry per key. There is deliberately no plain-text fallback - if the key store
fails, the error is reported instead.

Reading order for a key (``get_key``):

1. An environment variable (``GEMINI_API_KEY`` / ``OPENAI_API_KEY`` / ``TAVILY_API_KEY``, or the
   same name in a ``.env`` file in the project folder). This is for development only and wins over
   the saved key; the Settings window says so when it happens.
2. The key saved in ``keyring``.

Every read happens at the moment the key is needed (never at import time), so a key saved in
Settings works at once, without restarting the pet. Keys are never written to the log.
"""
from __future__ import annotations

import logging
import os

import keyring
from keyring.errors import KeyringError, PasswordDeleteError

import config  # noqa: F401 - importing it loads the optional .env file into os.environ

log = logging.getLogger(__name__)

SERVICE = "Lavenzure"

GEMINI = "gemini_api_key"
OPENAI = "openai_api_key"
TAVILY = "tavily_api_key"

# key name -> environment variable that overrides it (development only)
ENV_VARS: dict[str, str] = {
    GEMINI: "GEMINI_API_KEY",
    OPENAI: "OPENAI_API_KEY",
    TAVILY: "TAVILY_API_KEY",
}


class KeyStoreError(RuntimeError):
    """The system key store (Credential Manager) could not be written to."""


def _check_name(name: str) -> None:
    """Reject anything that is not one of the known key names."""
    if name not in ENV_VARS:
        raise KeyError(f"unknown API key {name!r}")


def env_key(name: str) -> str:
    """The key set through the environment / ``.env`` (empty when there is none)."""
    _check_name(name)
    return os.environ.get(ENV_VARS[name], "").strip()


def saved_key(name: str) -> str:
    """The key saved in the key store (empty when there is none or the store cannot be read)."""
    _check_name(name)
    try:
        return (keyring.get_password(SERVICE, name) or "").strip()
    except KeyringError as exc:
        log.warning("Could not read %s from the key store (%s)", name, type(exc).__name__)
        return ""


def get_key(name: str) -> str:
    """The key to use right now: the environment's if set, otherwise the saved one, else ``""``."""
    return env_key(name) or saved_key(name)


def key_source(name: str) -> str:
    """Where ``get_key`` finds the key: ``"env"``, ``"saved"`` or ``"none"``."""
    if env_key(name):
        return "env"
    if saved_key(name):
        return "saved"
    return "none"


def save_key(name: str, value: str) -> None:
    """Store ``value`` in the key store (raises ``KeyStoreError`` if that fails)."""
    _check_name(name)
    value = value.strip()
    if not value:
        raise ValueError("an empty key cannot be saved")
    try:
        keyring.set_password(SERVICE, name, value)
    except KeyringError as exc:
        log.warning("Could not save %s to the key store (%s)", name, type(exc).__name__)
        raise KeyStoreError("Windows would not let me store the key.") from exc


def delete_key(name: str) -> None:
    """Remove the saved key (nothing happens if there is none)."""
    _check_name(name)
    try:
        keyring.delete_password(SERVICE, name)
    except PasswordDeleteError:
        pass  # nothing was saved
    except KeyringError as exc:
        log.warning("Could not delete %s from the key store (%s)", name, type(exc).__name__)
        raise KeyStoreError("Windows would not let me remove the key.") from exc


def gemini_api_key() -> str:
    """The Gemini key to use right now (``""`` when none is set)."""
    return get_key(GEMINI)


def openai_api_key() -> str:
    """The OpenAI key to use right now (``""`` when none is set)."""
    return get_key(OPENAI)


def tavily_api_key() -> str:
    """The Tavily key to use right now (``""`` when none is set)."""
    return get_key(TAVILY)
