"""Crop a region of a reference image, zoom it and overlay a labelled coordinate grid.

Tracing a face from the reference sheet (``references/tracing-references.md``) means reading
outline points off the picture in the *image's own pixel coordinates*. A zoomed crop with grid
lines labelled in those coordinates makes that readable: look at the PNG this writes, note where
the outline crosses the grid, and type the points into ``src/overlay/face_refs.py``.

Usage (any Python with PySide6, e.g. the Windows venv):

    .venv-win/Scripts/python.exe .claude/skills/pet-animation/scripts/crop_grid.py \\
        docs/references/calcipher_picked.jpg OUT.png X Y W H [--zoom 8] [--step 5]
        [--points "x1,y1 x2,y2 ..."]

``X Y W H`` is the crop in image pixels. ``--step`` is the grid spacing in image pixels (labels
every second line). ``--points`` draws a polyline you traced (image pixels) on top, so you can
check a trace against the picture before committing it.
"""
from __future__ import annotations

import argparse
import sys

from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QColor, QGuiApplication, QImage, QPainter, QPen, QPolygonF


def main() -> int:
    """Parse arguments, draw the zoomed crop with grid (and optional trace) and save it."""
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("image")
    ap.add_argument("out")
    ap.add_argument("x", type=int)
    ap.add_argument("y", type=int)
    ap.add_argument("w", type=int)
    ap.add_argument("h", type=int)
    ap.add_argument("--zoom", type=int, default=8)
    ap.add_argument("--step", type=int, default=5)
    ap.add_argument("--points", default="", help='traced polyline, e.g. "10,12 14,15 20,18"')
    args = ap.parse_args()

    app = QGuiApplication(sys.argv[:1])  # noqa: F841 - must stay alive while painting
    src = QImage(args.image)
    if src.isNull():
        sys.exit(f"cannot read {args.image}")
    z = args.zoom
    crop = src.copy(args.x, args.y, args.w, args.h).scaled(
        args.w * z, args.h * z, Qt.AspectRatioMode.IgnoreAspectRatio,
        Qt.TransformationMode.SmoothTransformation).convertToFormat(
        QImage.Format.Format_ARGB32_Premultiplied)

    def to_px(x: float, y: float) -> QPointF:
        """Image coordinates -> pixel in the zoomed crop."""
        return QPointF((x - args.x) * z, (y - args.y) * z)

    p = QPainter(crop)
    p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    first = args.x - args.x % args.step
    for gx in range(first, args.x + args.w + 1, args.step):
        major = (gx // args.step) % 2 == 0
        p.setPen(QPen(QColor(0, 120, 255, 150 if major else 70), 1))
        p.drawLine(to_px(gx, args.y), to_px(gx, args.y + args.h))
        if major:
            p.setPen(QColor(0, 70, 200))
            p.drawText(to_px(gx, args.y) + QPointF(2, 11), str(gx))
    first = args.y - args.y % args.step
    for gy in range(first, args.y + args.h + 1, args.step):
        major = (gy // args.step) % 2 == 0
        p.setPen(QPen(QColor(0, 120, 255, 150 if major else 70), 1))
        p.drawLine(to_px(args.x, gy), to_px(args.x + args.w, gy))
        if major:
            p.setPen(QColor(0, 70, 200))
            p.drawText(to_px(args.x, gy) + QPointF(2, -2), str(gy))
    if args.points.strip():
        pts = [to_px(*(float(v) for v in pair.split(","))) for pair in args.points.split()]
        p.setPen(QPen(QColor(255, 0, 140), 2))
        p.drawPolyline(QPolygonF(pts))
        p.setBrush(QColor(255, 0, 140))
        for pt in pts:
            p.drawEllipse(pt, 3, 3)
    p.end()
    crop.save(args.out)
    print(f"wrote {args.out} ({crop.width()}x{crop.height()})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
