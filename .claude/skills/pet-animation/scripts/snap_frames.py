"""Dump (and compare) a fixed, scripted sequence of character frames to catch unwanted changes.

The character is deterministic for a fixed seed and fixed frame time, so two versions of the
code that are *supposed* to draw the same thing must produce identical PNGs. Use it before and
after a refactor or a speed optimisation of the per-frame hot paths (``face.py``, the flame
renderers, ``character.py``): any differing frame means the picture changed.

Usage (from the repo root, Windows venv):

    SNAP=.claude/skills/pet-animation/scripts/snap_frames.py
    .venv-win/Scripts/python.exe $SNAP dump OUT_DIR [renderer]
    .venv-win/Scripts/python.exe $SNAP compare DIR_A DIR_B

``dump`` plays a script that walks through every mood, the log ride and sleep, and saves a frame
every 25 ticks. ``compare`` reports which frames differ (exit code 1 when any do).
"""
from __future__ import annotations

import sys
from pathlib import Path


def find_src() -> Path:
    """Walk up from this file to the repo's ``src`` folder (the import root of the project)."""
    for parent in Path(__file__).resolve().parents:
        if (parent / "src" / "overlay" / "character.py").exists():
            return parent / "src"
    sys.exit("could not find src/overlay/character.py above this script")


sys.path.insert(0, str(find_src()))

from PySide6.QtCore import QPointF, Qt  # noqa: E402
from PySide6.QtGui import QGuiApplication, QImage, QPainter  # noqa: E402

from overlay.character import FlameCharacter, Mood  # noqa: E402


def dump(out: Path, renderer: str) -> None:
    """Play the fixed script and save every 25th frame as ``fNNNN.png`` into ``out``."""
    out.mkdir(parents=True, exist_ok=True)
    ch = FlameCharacter(scale=0.75, seed=7, renderer=renderer)
    print("renderer", ch.renderer_name)
    script = {
        30: lambda: ch.play(Mood.HAPPY, 2.0), 200: lambda: ch.play(Mood.SURPRISED, 1.5),
        320: lambda: ch.talk(2.0), 420: lambda: ch.play(Mood.CHILL, 3.0),
        640: lambda: ch.set_riding(True, takeoff=True), 820: lambda: ch.set_riding(False),
        900: lambda: ch.set_sleeping(True), 1150: lambda: ch.play(Mood.ANGRY, 1.5),
        1300: lambda: ch.play(Mood.YUCK, 1.5), 1450: lambda: ch.play(Mood.COOL, 2.0),
    }
    pos = QPointF(500, 500)
    for i in range(1600):
        if i in script:
            script[i]()
        if 100 <= i < 160:
            pos = QPointF(pos.x() + 3.0, pos.y())          # walk
        if 700 <= i < 760:
            pos = QPointF(pos.x() - 2.0, pos.y() - 2.5)    # fly up
        cursor = QPointF(40 + (i % 300), 60 + (i % 170) * 0.5)
        ch.update(1 / 60, pos, cursor)
        if i % 25 == 0:
            img = QImage(ch.width, ch.height, QImage.Format.Format_ARGB32_Premultiplied)
            img.fill(Qt.GlobalColor.transparent)
            p = QPainter(img)
            ch.paint(p)
            p.end()
            img.save(str(out / f"f{i:04d}.png"))


def compare(a: Path, b: Path) -> int:
    """Compare the PNG frames of two dumps; print the differing ones. Returns the exit code."""
    names = sorted(p.name for p in a.glob("f*.png"))
    if not names or names != sorted(p.name for p in b.glob("f*.png")):
        print("the two folders do not hold the same frames")
        return 2
    diff = [n for n in names if QImage(str(a / n)) != QImage(str(b / n))]
    print(f"{len(names) - len(diff)}/{len(names)} frames identical")
    for n in diff:
        print("  differs:", n)
    return 1 if diff else 0


def main() -> int:
    """Dispatch ``dump`` / ``compare``."""
    args = sys.argv[1:]
    app = QGuiApplication(sys.argv[:1])  # noqa: F841 - must stay alive while painting
    if len(args) >= 2 and args[0] == "dump":
        dump(Path(args[1]), args[2] if len(args) > 2 else "shader")
        return 0
    if len(args) == 3 and args[0] == "compare":
        return compare(Path(args[1]), Path(args[2]))
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main())
