"""Settings the user changes from the Settings window, remembered between runs.

They are stored as a small JSON file, ``%LOCALAPPDATA%\\Lavenzure\\settings.json`` (or
``settings.json`` in the project folder when ``LOCALAPPDATA`` is not set). A setting that was never
changed falls back to its default in ``config.yaml`` (``DEFAULTS`` maps each setting to that
config path and a last-resort value), so ``config.yaml`` keeps describing the out-of-the-box
behaviour and the file only holds the user's own choices. Delete the file to go back to the
defaults.

Current settings (roadmap Phase 12):

- ``max_fps`` - frame rate of every animation (30 / 60; default 30, chosen by the user).
- ``language`` - language of everything the pet says (``en`` / ``vi``; default ``language`` in
  config.yaml).
"""
from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any

import config

log = logging.getLogger(__name__)

# setting name -> (config.yaml path of its default, value if config.yaml has none)
DEFAULTS: dict[str, tuple[str, Any]] = {
    "max_fps": ("character.fps", 30),
    "language": ("language", "en"),
}


def default_path() -> Path:
    """Where the settings file lives (see the module doc)."""
    base = os.environ.get("LOCALAPPDATA")
    if base:
        return Path(base) / "Lavenzure" / "settings.json"
    return Path(__file__).resolve().parent.parent / "settings.json"


class UserSettings:
    """Read and change the user's settings; every change is written to disk at once."""

    def __init__(self, path: Path | None = None) -> None:
        """Load ``path`` (default: ``default_path()``). A missing or broken file means "no
        choices made yet" (a broken one is logged and replaced on the next change)."""
        self.path = path or default_path()
        self._values: dict[str, Any] = {}
        try:
            loaded = json.loads(self.path.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                self._values = loaded
        except FileNotFoundError:
            pass
        except (OSError, ValueError) as exc:
            log.warning("Ignoring unreadable settings file %s (%s)", self.path, exc)

    def get(self, name: str) -> Any:
        """The user's value for ``name``, or its default from ``config.yaml``."""
        if name in self._values:
            return self._values[name]
        config_path, fallback = DEFAULTS[name]
        return config.get(config_path, fallback)

    def set(self, name: str, value: Any) -> None:
        """Change ``name`` and save the file (a failed save is logged; the value still applies
        for this run)."""
        if name not in DEFAULTS:
            raise KeyError(f"unknown setting {name!r}")
        self._values[name] = value
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.write_text(json.dumps(self._values, indent=2), encoding="utf-8")
        except OSError as exc:
            log.warning("Could not save settings to %s (%s)", self.path, exc)
