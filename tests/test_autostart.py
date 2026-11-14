"""Tests for autostart.startup against throw-away registry keys (never the real Run key)."""
import sys

import pytest

pytestmark = pytest.mark.skipif(sys.platform != "win32", reason="needs the Windows registry")

TEST_ROOT = r"Software\LavenzureTest"


@pytest.fixture
def startup(monkeypatch):
    """The startup module pointed at test keys, cleaned up afterwards."""
    import winreg

    from autostart import startup as module

    monkeypatch.setattr(module, "RUN_KEY", TEST_ROOT + r"\Run")
    monkeypatch.setattr(module, "APPROVED_KEY", TEST_ROOT + r"\Approved")
    yield module
    for sub in ("Run", "Approved"):
        try:
            winreg.DeleteKey(winreg.HKEY_CURRENT_USER, TEST_ROOT + "\\" + sub)
        except FileNotFoundError:
            pass
    try:
        winreg.DeleteKey(winreg.HKEY_CURRENT_USER, TEST_ROOT)
    except (FileNotFoundError, OSError):
        pass


def test_off_by_default(startup):
    """Nothing is registered until the user turns the switch on."""
    assert not startup.is_enabled()


def test_enable_then_disable(startup):
    """The switch writes and removes the Run value."""
    startup.enable()
    assert startup.is_enabled()
    startup.disable()
    assert not startup.is_enabled()
    startup.disable()   # already off: not an error


def test_command_is_quoted_and_runs_main_from_source(startup):
    """From source the command is ``pythonw.exe main.py`` (both paths quoted)."""
    command = startup.command()
    assert command.startswith('"') and command.endswith('main.py"')
    assert "pythonw.exe" in command


def test_switched_off_in_task_manager_counts_as_off(startup):
    """Task Manager keeps the Run value but flags it disabled; the Settings switch must show off,
    and turning it on again clears the flag."""
    import winreg

    startup.enable()
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, startup.APPROVED_KEY) as key:
        winreg.SetValueEx(key, startup.VALUE_NAME, 0, winreg.REG_BINARY,
                          bytes([3]) + bytes(11))
    assert not startup.is_enabled()
    startup.enable()
    assert startup.is_enabled()


def test_frozen_command_is_the_exe(startup, monkeypatch):
    """The packaged build registers Lavenzure.exe itself."""
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "executable", r"C:\Apps\Lavenzure\Lavenzure.exe")
    assert startup.command() == r'"C:\Apps\Lavenzure\Lavenzure.exe"'
