"""The app's version number, taken from git tags (the single source of truth).

Releases are tagged ``vMAJOR.MINOR.PATCH`` on ``main`` (``v0.1.0``; trial builds ``v0.1.0-rc.1``).
Nothing in the code is edited by hand to change the number:

- A packaged build has ``src/_version.py`` (git-ignored), written by ``scripts/write_version.py``
  just before packaging from ``git describe``.
- Running from source, the number is asked from ``git describe`` directly; without git it is
  ``"dev"``.

``git describe`` says ``v0.1.0`` on a tagged commit and ``v0.1.0-3-gabc1234`` three commits later;
``from_describe`` turns the second form into the dev version ``0.1.1.dev3+gabc1234`` (the next patch
number, "3 commits in").
"""
from __future__ import annotations

import re
import subprocess
import sys
from functools import lru_cache

from paths import resource_root

_DESCRIBE = re.compile(
    r"^v(?P<major>\d+)\.(?P<minor>\d+)\.(?P<patch>\d+)(?P<pre>-[0-9A-Za-z.]+?)?"
    r"(?:-(?P<ahead>\d+)-g(?P<sha>[0-9a-f]+))?$"
)


def from_describe(described: str) -> str | None:
    """Convert ``git describe`` output to a version string (``None`` if it is not a ``v*`` tag).

    ``v0.1.0`` -> ``0.1.0``; ``v0.1.0-rc.1`` -> ``0.1.0-rc.1``; ``v0.1.0-3-gabc1234`` ->
    ``0.1.1.dev3+gabc1234``; ``v0.1.0-rc.1-3-gabc1234`` -> ``0.1.0-rc.1.dev3+gabc1234``.
    """
    match = _DESCRIBE.match(described.strip())
    if not match:
        return None
    major, minor, patch = (int(match[name]) for name in ("major", "minor", "patch"))
    pre = match["pre"] or ""
    if not match["ahead"]:
        return f"{major}.{minor}.{patch}{pre}"
    if pre:
        return f"{major}.{minor}.{patch}{pre}.dev{match['ahead']}+g{match['sha']}"
    return f"{major}.{minor}.{patch + 1}.dev{match['ahead']}+g{match['sha']}"


def git_version() -> str | None:
    """Ask git for the version of the project folder (``None`` when git or tags are missing)."""
    flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)   # no console flash when run from pythonw
    try:
        done = subprocess.run(
            ["git", "describe", "--tags", "--match", "v*"],
            cwd=resource_root(), capture_output=True, text=True, timeout=5,
            creationflags=flags, check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return from_describe(done.stdout) if done.returncode == 0 else None


@lru_cache(maxsize=1)
def get_version() -> str:
    """The running app's version: the build's ``_version.py``, else git, else ``"dev"``."""
    try:
        from _version import VERSION  # written at build time, not in git
        return str(VERSION)
    except ImportError:
        pass
    if getattr(sys, "frozen", False):
        return "dev"   # a packaged build without _version.py: never go looking for git
    return git_version() or "dev"


def display_name() -> str:
    """``Lavenzure v0.1.0`` (or ``Lavenzure (dev)``), for the Settings footer and the tray."""
    version = get_version()
    return "Lavenzure (dev)" if version == "dev" else f"Lavenzure v{version}"
