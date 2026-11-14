"""Start Lavenzure when the user logs in to Windows: the "Start with Windows" switch in Settings.

It is one value in the registry key ``HKEY_CURRENT_USER\\Software\\Microsoft\\Windows\\
CurrentVersion\\Run`` (no administrator rights needed). Windows lists it in Task Manager > Startup
and in Windows Settings > Apps > Startup, where the user can switch it off too; that switch lives
in a second key (``...\\Explorer\\StartupApproved\\Run``), so ``is_enabled`` looks at both. The
default is OFF: the value only exists after the user turned the switch on.

The command is the packaged ``Lavenzure.exe``; when running from source (development) it is
``pythonw.exe src/main.py`` so there is no console window either way.
"""
from __future__ import annotations

import sys
from pathlib import Path

from paths import is_frozen

try:
    import winreg
except ImportError:  # not Windows (e.g. the Linux preview venv)
    winreg = None  # type: ignore[assignment]

RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
APPROVED_KEY = r"Software\Microsoft\Windows\CurrentVersion\Explorer\StartupApproved\Run"
VALUE_NAME = "Lavenzure"


def available() -> bool:
    """True where the switch can work (Windows)."""
    return winreg is not None


def command() -> str:
    """The command Windows runs at login (quoted, so paths with spaces work)."""
    if is_frozen():
        return f'"{Path(sys.executable).resolve()}"'
    pythonw = Path(sys.executable).with_name("pythonw.exe")
    main_script = Path(__file__).resolve().parent.parent / "main.py"
    return f'"{pythonw}" "{main_script}"'


def _disabled_in_task_manager() -> bool:
    """True when the user switched the entry off in Task Manager / Windows Settings.

    Those tools keep the Run value and write a binary flag in ``StartupApproved``: the first byte
    is even (2, 6) when enabled and odd (3) when disabled.
    """
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, APPROVED_KEY) as key:
            data, _kind = winreg.QueryValueEx(key, VALUE_NAME)
    except FileNotFoundError:
        return False
    return bool(data) and data[0] % 2 == 1


def is_enabled() -> bool:
    """Whether Lavenzure will start at login right now (read fresh from the registry)."""
    if not available():
        return False
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as key:
            winreg.QueryValueEx(key, VALUE_NAME)
    except FileNotFoundError:
        return False
    return not _disabled_in_task_manager()


def enable() -> None:
    """Turn the switch on (also clears a "disabled" flag set in Task Manager). Raises
    ``OSError`` if the registry cannot be written."""
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as key:
        winreg.SetValueEx(key, VALUE_NAME, 0, winreg.REG_SZ, command())
    _forget_approval_flag()


def disable() -> None:
    """Turn the switch off (nothing happens if it was already off)."""
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE) as key:
            winreg.DeleteValue(key, VALUE_NAME)
    except FileNotFoundError:
        pass
    _forget_approval_flag()


def _forget_approval_flag() -> None:
    """Remove Task Manager's on/off flag for our entry so the Run value alone decides."""
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, APPROVED_KEY, 0,
                            winreg.KEY_SET_VALUE) as key:
            winreg.DeleteValue(key, VALUE_NAME)
    except FileNotFoundError:
        pass
