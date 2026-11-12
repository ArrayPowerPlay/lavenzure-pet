"""Desktop check (roadmap A7): look at the running pet's real window and test what can be tested
automatically on the Windows desktop.

Read-only: it never moves, clicks or closes anything. For the running pet it checks that

- the pet window is always-on-top (``WS_EX_TOPMOST``), a tool window (no taskbar button) and a
  per-pixel-alpha layered window (``WS_EX_LAYERED``), which is what makes click-through work;
- the mouse "falls through" the transparent corners of the window: Windows reports the window
  *underneath* at those points;
- the visible flame itself does catch the mouse (Windows reports the pet window there);
- the pet sits inside the usable screen area (not under the taskbar).

Everything else on the A7 list needs a human (see ``docs/TEST_CHECKLIST.md``).

Usage (Windows venv, with the pet running)::

    .venv-win/Scripts/python.exe src/desktop_check.py
"""
from __future__ import annotations

import ctypes
import sys
import time
from ctypes import wintypes

import psutil

GWL_EXSTYLE = -20
WS_EX_TOPMOST = 0x00000008
WS_EX_TOOLWINDOW = 0x00000080
WS_EX_LAYERED = 0x00080000
GA_ROOT = 2
SPI_GETWORKAREA = 0x0030


def pet_pids() -> set[int]:
    """Process ids of running pets (``python*`` processes started with ``main.py``)."""
    pids = set()
    for proc in psutil.process_iter(["name", "cmdline"]):
        name = (proc.info["name"] or "").lower()
        if name.startswith("python") and "main.py" in " ".join(proc.info["cmdline"] or []):
            pids.add(proc.pid)
    return pids


def visible_windows_of(pids: set[int]) -> list[tuple[int, wintypes.RECT]]:
    """Visible top-level windows owned by ``pids`` with their screen rectangles."""
    user32 = ctypes.windll.user32
    found: list[tuple[int, wintypes.RECT]] = []

    @ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    def callback(hwnd, _lparam):
        """Collect ``hwnd`` if a pet process owns it and it is visible."""
        pid = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        if pid.value in pids and user32.IsWindowVisible(hwnd):
            rect = wintypes.RECT()
            user32.GetWindowRect(hwnd, ctypes.byref(rect))
            found.append((hwnd, rect))
        return True

    user32.EnumWindows(callback, 0)
    return found


def root_window_at(x: int, y: int) -> int:
    """Top-level window that would receive a mouse click at screen point (x, y)."""
    user32 = ctypes.windll.user32
    user32.WindowFromPoint.argtypes = [wintypes.POINT]
    user32.WindowFromPoint.restype = wintypes.HWND
    user32.GetAncestor.restype = wintypes.HWND
    hwnd = user32.WindowFromPoint(wintypes.POINT(x, y))
    return user32.GetAncestor(hwnd, GA_ROOT) if hwnd else 0


def work_area() -> wintypes.RECT:
    """The primary screen without the taskbar."""
    rect = wintypes.RECT()
    ctypes.windll.user32.SystemParametersInfoW(SPI_GETWORKAREA, 0, ctypes.byref(rect), 0)
    return rect


def find_pet_window(pids: set[int]) -> tuple[int, wintypes.RECT] | None:
    """The pet sprite: the pet process' visible, layered, always-on-top window."""
    user32 = ctypes.windll.user32
    for hwnd, rect in visible_windows_of(pids):
        ex = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
        if ex & WS_EX_LAYERED and ex & WS_EX_TOPMOST:
            return hwnd, rect
    return None


def check() -> list[tuple[bool, str]]:
    """Run every check; returns (passed, description) pairs."""
    pids = pet_pids()
    if not pids:
        return [(False, "No running pet found - start it with src/main.py first")]
    found = find_pet_window(pids)
    if found is None:
        return [(False, "The pet runs but no visible always-on-top layered window was found "
                        "(hidden from the tray?)")]
    hwnd, rect = found
    ex = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
    results = [
        (bool(ex & WS_EX_TOPMOST), "Window is always-on-top"),
        (bool(ex & WS_EX_TOOLWINDOW), "Window is a tool window (no taskbar button)"),
        (bool(ex & WS_EX_LAYERED), "Window is a per-pixel-alpha layered window"),
    ]

    # The pet keeps moving, so sample a few times and take the best evidence.
    corners_through = flame_hit = False
    for _ in range(10):
        found = find_pet_window(pids)
        if found is None:
            break
        hwnd, rect = found
        corners = [(rect.left + 2, rect.top + 2), (rect.right - 3, rect.top + 2)]
        corners_through = corners_through or all(root_window_at(x, y) != hwnd
                                                 for x, y in corners)
        # The face sits around the middle of the lower body.
        cx, cy = (rect.left + rect.right) // 2, rect.top + (rect.bottom - rect.top) * 70 // 100
        flame_hit = flame_hit or root_window_at(cx, cy) == hwnd
        if corners_through and flame_hit:
            break
        time.sleep(0.3)
    results.append((corners_through, "Clicks fall through the transparent corners"))
    results.append((flame_hit, "The visible flame catches clicks"))

    area = work_area()
    inside = (rect.left >= area.left - 5 and rect.right <= area.right + 5
              and rect.bottom <= area.bottom + 40)
    results.append((inside, f"Pet window {rect.left},{rect.top}-{rect.right},{rect.bottom} is "
                            f"inside the screen above the taskbar (work area bottom "
                            f"{area.bottom})"))
    return results


def main() -> int:
    """Print a PASS/FAIL line per check; exit code 1 if anything failed."""
    if sys.platform != "win32":
        print("desktop_check.py inspects the real Windows desktop; run it with .venv-win.")
        return 2
    results = check()
    for ok, text in results:
        print(f"[{'PASS' if ok else 'FAIL'}] {text}")
    return 0 if all(ok for ok, _ in results) else 1


if __name__ == "__main__":
    sys.exit(main())
