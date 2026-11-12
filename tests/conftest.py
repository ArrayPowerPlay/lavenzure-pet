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
