"""Run PyInstaller, but wait patiently when Windows Defender is scanning the new ``.exe``.

PyInstaller edits the freshly written ``Lavenzure.exe`` several times (icon, manifest, checksum).
Windows Defender often holds the file for a few seconds right after it appears, and PyInstaller's
own retry (20 tries in about 4 seconds) then gives up with ``PermissionError``
(https://github.com/pyinstaller/pyinstaller/issues/8138). This wrapper repeats that retry for up
to a minute per step. Arguments are passed straight to PyInstaller.
"""
from __future__ import annotations

import sys
import time

from PyInstaller.__main__ import run
from PyInstaller.building import api

_original = api.EXE._retry_operation


def _patient(func, *args, **kwargs):
    """PyInstaller's retry, repeated every 2 s (up to 30 times) while the file stays locked."""
    for attempt in range(30):
        try:
            return _original(func, *args, **kwargs)
        except RuntimeError as exc:
            if "no more attempts left" not in str(exc) or attempt == 29:
                raise
            print(f"File still locked (antivirus scan?), waiting... ({attempt + 1}/30)", flush=True)
            time.sleep(2)


api.EXE._retry_operation = staticmethod(_patient)

if __name__ == "__main__":
    run(sys.argv[1:])
