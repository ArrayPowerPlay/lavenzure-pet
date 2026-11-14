"""Render the flame character in one or more moods into a single contact-sheet PNG.

This is the quickest way to *see* an animation change without starting the app: it builds a
``FlameCharacter``, puts it in each requested mood, lets it settle for a number of frames and
paints the results side by side. Optionally the first panel is a crop of a reference image, so
the render can be compared with the picture it is meant to match (the usual acceptance test
for a face the user asked to copy).

Usage (from the repo root, with the Windows venv so the GPU flame renderer works):

    .venv-win/Scripts/python.exe .claude/skills/pet-animation/scripts/render_sheet.py OUT.png \\
        [--moods normal,happy,cool] [--frames 90 [--frames 150 ...]] [--scale 1.6] \\
        [--renderer shader] [--seed 3] [--light] \\
        [--ref docs/references/calcipher_picked.jpg --crop X,Y,W,H]

Mood names are the lower-case ``Mood`` enum names (``happy``, ``chill``, ``remind`` ...). Passing
``--frames`` several times adds one row per value, which shows how a mood *develops* (the first
row catches the anticipation kick, later rows the settled face).
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path


def find_src() -> Path:
    """Walk up from this file to the repo's ``src`` folder (the import root of the project)."""
    for parent in Path(__file__).resolve().parents:
        if (parent / "src" / "overlay" / "character.py").exists():
            return parent / "src"
    sys.exit("could not find src/overlay/character.py above this script")


sys.path.insert(0, str(find_src()))

from PySide6.QtCore import QPointF, QRectF, Qt  # noqa: E402
from PySide6.QtGui import QColor, QGuiApplication, QImage, QPainter  # noqa: E402

from overlay.character import FlameCharacter, Mood  # noqa: E402

DT = 1 / 60


def apply_mood(ch: FlameCharacter, name: str) -> None:
    """Put ``ch`` into the mood called ``name``.

    Moods that are persistent flags in the character (alert, thinking, sleep, fly, remind) are
    switched on the way the app does it; every other mood is played until stopped.
    """
    mood = Mood[name.upper()]
    if mood == Mood.ALERT:
        ch.set_alert(True)
    elif mood == Mood.THINKING:
        ch.set_thinking(True)
    elif mood == Mood.SLEEP:
        ch.set_sleeping(True)
    elif mood == Mood.FLY:
        ch.set_riding(True)
    elif mood == Mood.REMIND:
        ch.set_reminding(True)
    elif mood == Mood.TALKING:
        ch.talk(60.0)
    elif mood != Mood.NORMAL:
        ch.play(mood, None)


def render_panel(name: str, frames: int, scale: float, renderer: str, seed: int,
                 bg: QColor) -> QImage:
    """Render one character in mood ``name`` after ``frames`` simulated frames (60 fps)."""
    ch = FlameCharacter(scale=scale, seed=seed, renderer=renderer)
    apply_mood(ch, name)
    for _ in range(frames):
        ch.update(DT, QPointF(0, 0), None)
    img = QImage(ch.width, ch.height + 28, QImage.Format.Format_ARGB32_Premultiplied)
    img.fill(bg)
    p = QPainter(img)
    ch.paint(p)
    p.setPen(QColor(235, 235, 240) if bg.lightness() < 128 else QColor(40, 40, 48))
    p.drawText(QRectF(0, ch.height, ch.width, 28), Qt.AlignmentFlag.AlignCenter,
               f"{name} @ {frames}f [{ch.renderer_name}]")
    p.end()
    return img


def reference_panel(path: str, crop: str | None, height: int, bg: QColor) -> QImage:
    """Load the reference image (optionally cropped to ``X,Y,W,H``) scaled to ``height``."""
    ref = QImage(path)
    if ref.isNull():
        sys.exit(f"cannot read reference image {path}")
    if crop:
        x, y, w, h = (int(v) for v in crop.split(","))
        ref = ref.copy(x, y, w, h)
    ref = ref.scaledToHeight(height, Qt.TransformationMode.SmoothTransformation)
    out = QImage(ref.width(), height, QImage.Format.Format_ARGB32_Premultiplied)
    out.fill(bg)
    p = QPainter(out)
    p.drawImage(0, 0, ref)
    p.end()
    return out


def main() -> int:
    """Parse arguments, render every panel and save the sheet."""
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("out", help="PNG file to write")
    ap.add_argument("--moods", default="normal,happy,surprised,scared,angry,chill,cool,sleep",
                    help="comma separated Mood names")
    ap.add_argument("--frames", type=int, action="append",
                    help="frames to simulate before the snapshot; repeat for more rows")
    ap.add_argument("--scale", type=float, default=1.6)
    ap.add_argument("--renderer", default="shader", choices=("shader", "metaball", "baked"))
    ap.add_argument("--seed", type=int, default=3)
    ap.add_argument("--light", action="store_true", help="light backdrop instead of dark")
    ap.add_argument("--ref", help="reference image shown as the first panel of every row")
    ap.add_argument("--crop", help="X,Y,W,H crop of the reference image")
    args = ap.parse_args()

    app = QGuiApplication(sys.argv[:1])  # noqa: F841 - must stay alive while painting
    bg = QColor(236, 239, 243) if args.light else QColor(38, 42, 50)
    names = [m.strip() for m in args.moods.split(",") if m.strip()]
    rows = args.frames or [150]
    panels = [[render_panel(n, f, args.scale, args.renderer, args.seed, bg) for n in names]
              for f in rows]
    ph = panels[0][0].height()
    if args.ref:
        refs = reference_panel(args.ref, args.crop, ph, bg)
        panels = [[refs] + row for row in panels]
    width = sum(img.width() for img in panels[0])
    sheet = QImage(width, ph * len(panels), QImage.Format.Format_ARGB32_Premultiplied)
    sheet.fill(bg)
    p = QPainter(sheet)
    for r, row in enumerate(panels):
        x = 0
        for img in row:
            p.drawImage(x, r * ph, img)
            x += img.width()
    p.end()
    sheet.save(args.out)
    print(f"wrote {args.out} ({sheet.width()}x{sheet.height()})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
