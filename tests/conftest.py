"""Shared pytest setup: run Qt without a display and provide one QApplication for all tests."""
from __future__ import annotations

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


@pytest.fixture(scope="session")
def qapp():
    """The single QApplication that Qt widgets/timers in the tests need."""
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance() or QApplication([])
    yield app


def pump(app, seconds: float) -> None:
    """Process Qt events for ``seconds`` (lets queued signals and timers run)."""
    import time

    end = time.monotonic() + seconds
    while time.monotonic() < end:
        app.processEvents()
        time.sleep(0.005)


class MemoryKeyring:
    """A tiny in-memory stand-in for the system key store (``keyring`` backend API)."""

    def __init__(self) -> None:
        """Start with nothing stored."""
        self.store: dict[tuple[str, str], str] = {}

    def get_password(self, service, name):
        """Return the stored value or ``None``."""
        return self.store.get((service, name))

    def set_password(self, service, name, value):
        """Store ``value``."""
        self.store[(service, name)] = value

    def delete_password(self, service, name):
        """Remove the value (``PasswordDeleteError`` when there is none, like the real store)."""
        from keyring.errors import PasswordDeleteError

        if (service, name) not in self.store:
            raise PasswordDeleteError("not found")
        del self.store[(service, name)]


@pytest.fixture(autouse=True)
def fake_key_store(monkeypatch):
    """Every test gets an empty in-memory key store and no key environment variables, so no test
    can touch the real Windows Credential Manager or pick up a developer's own ``.env`` keys."""
    import keyring

    store = MemoryKeyring()
    for attr in ("get_password", "set_password", "delete_password"):
        monkeypatch.setattr(keyring, attr, getattr(store, attr))
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("TAVILY_API_KEY", raising=False)
    return store
