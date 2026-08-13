"""Create a Windows Startup-folder shortcut so Calcifer launches automatically at logon (dev mode)."""
from __future__ import annotations

import os
import sys
from pathlib import Path

import win32com.client

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
MAIN_SCRIPT = PROJECT_ROOT / "src" / "main.py"


def install() -> Path:
    startup_dir = (
        Path(os.environ["APPDATA"]) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"
    )
    shortcut_path = startup_dir / "Calcifer.lnk"
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
