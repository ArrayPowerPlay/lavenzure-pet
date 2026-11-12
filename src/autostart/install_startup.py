"""Create a Windows Startup-folder shortcut so Lavenzure launches automatically at logon.

Dev-mode autostart: the shortcut runs ``pythonw.exe src/main.py`` from the project's venv.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import win32com.client

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
MAIN_SCRIPT = PROJECT_ROOT / "src" / "main.py"


def install() -> Path:
    """Create (or overwrite) ``Lavenzure.lnk`` in the user's Startup folder; returns its path."""
    startup_dir = (
        Path(os.environ["APPDATA"])
        / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"
    )
    shortcut_path = startup_dir / "Lavenzure.lnk"
    pythonw = Path(sys.executable).with_name("pythonw.exe")

    shell = win32com.client.Dispatch("WScript.Shell")
    shortcut = shell.CreateShortCut(str(shortcut_path))
    shortcut.TargetPath = str(pythonw)
    shortcut.Arguments = f'"{MAIN_SCRIPT}"'
    shortcut.WorkingDirectory = str(PROJECT_ROOT)
    shortcut.IconLocation = str(pythonw)
    shortcut.Save()
    return shortcut_path


if __name__ == "__main__":
    created_path = install()
    print(f"Startup shortcut created at: {created_path}")
