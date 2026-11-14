"""Where the app's read-only files live (``config.yaml``, ``data/``, ``assets/``).

Running from source they sit in the project folder (the parent of ``src/``). In a packaged build
(PyInstaller) they are unpacked next to the program, in the folder PyInstaller exposes as
``sys._MEIPASS``. Code asks ``resource(...)`` instead of building paths from ``__file__``, so both
cases work. The user's own files (settings, reminders, logs) are NOT here: they live in
``%LOCALAPPDATA%\\Lavenzure`` (see ``user_settings.app_data_dir``).
"""
from __future__ import annotations

import sys
from pathlib import Path


def is_frozen() -> bool:
    """True when running from a packaged build (PyInstaller), False when running from source."""
    return bool(getattr(sys, "frozen", False))


def resource_root() -> Path:
    """The folder that holds ``config.yaml``, ``data/`` and ``assets/``."""
    if is_frozen():
        return Path(getattr(sys, "_MEIPASS", Path(sys.executable).resolve().parent))
    return Path(__file__).resolve().parent.parent


def resource(*parts: str) -> Path:
    """Path of a bundled read-only file, e.g. ``resource("data", "care_lines.json")``."""
    return resource_root().joinpath(*parts)
