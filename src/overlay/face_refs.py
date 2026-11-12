"""Faces copied from the reference sticker sheet (``docs/references/calcipher_picked.jpg``).

The user asked for some expressions to be copied exactly from their picked figures instead of
being approximated with the parametric face in ``overlay.face``: fig. 1 (``happy``: half-dome
eyes with the pupils hanging from the top edge, an open mouth with a soft notch in the upper lip
and a pink tongue) and fig. 7 (``chill``: tilted half-dome eyes with big pupils, a long wavy
closed smile with a small stroke crossing each corner).

The outlines below were traced from the reference image (coordinates are the image's own pixels,
y down) and are turned into data the face can morph toward:

- every eye becomes a centre, half sizes and a *radial profile* (its outline's distance from the
  centre at evenly spaced angles, in units of the half sizes; 1 everywhere = an ellipse), so it
  blends point-for-point with the parametric (elliptic) eye;
- every mouth becomes upper / lower lip curves sampled at the same positions as the parametric
  mouth (``mouth_s``), so it blends with it the same way;
- ``RefFace.scale`` converts image pixels to the character's units (R).

Nothing here draws; ``overlay.face.Face`` does, blending these shapes in by the expression's
``fig1`` / ``fig7`` weights.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

RADIAL_SAMPLES = 72     # angles in an eye's radial profile
MOUTH_SAMPLES = 41      # points along each lip (shared with the parametric mouth)


def mouth_s(i: int) -> float:
    """Position (-1 = left corner .. 1 = right corner) of lip sample ``i``. Spaced like a cosine
    so the round corners of a mouth get more points than its flat middle."""
    return -math.cos(math.pi * i / (MOUTH_SAMPLES - 1))


def _catmull(points: list[tuple[float, float]], steps: int,
             closed: bool) -> list[tuple[float, float]]:
    """Smooth a traced polyline with a Catmull-Rom spline (``steps`` points per segment)."""
    n = len(points)
    out = []
    for i in range(n if closed else n - 1):
        p0 = points[(i - 1) % n] if closed else points[max(i - 1, 0)]
        p1, p2 = points[i], points[(i + 1) % n]
        p3 = points[(i + 2) % n] if closed else points[min(i + 2, n - 1)]
        for j in range(steps):
            t = j / steps
            out.append(tuple(
                0.5 * (2 * p1[c] + (p2[c] - p0[c]) * t
                       + (2 * p0[c] - 5 * p1[c] + 4 * p2[c] - p3[c]) * t * t
                       + (3 * p1[c] - p0[c] - 3 * p2[c] + p3[c]) * t * t * t)
                for c in (0, 1)))
    if not closed:
        out.append(points[-1])
    return out


def _ray_hit(poly: list[tuple[float, float]], angle: float) -> float:
    """Distance from the origin along ``angle`` to the farthest crossing with ``poly``."""
    dx, dy = math.cos(angle), math.sin(angle)
    best = 0.0
    for i in range(len(poly)):
        (x1, y1), (x2, y2) = poly[i], poly[(i + 1) % len(poly)]
        ex, ey = x2 - x1, y2 - y1
        den = dx * ey - dy * ex
        if abs(den) < 1e-12:
            continue
        t = (x1 * ey - y1 * ex) / den
        u = (x1 * dy - y1 * dx) / den
        if t > 0.0 and 0.0 <= u <= 1.0:
            best = max(best, t)
    return best


def _vertical_hits(poly: list[tuple[float, float]], x: float) -> list[float]:
    """Heights where the vertical line at ``x`` crosses the closed polygon ``poly``."""
    hits = []
    for i in range(len(poly)):
        (x1, y1), (x2, y2) = poly[i], poly[(i + 1) % len(poly)]
        if x1 != x2 and (x1 - x) * (x2 - x) <= 0.0:
            hits.append(y1 + (y2 - y1) * (x - x1) / (x2 - x1))
    return hits


def _interp(xs: list[float], ys: list[float], x: float) -> float:
    """Piecewise-linear interpolation of ``ys`` over increasing ``xs`` (clamped at the ends)."""
    if x <= xs[0]:
        return ys[0]
    for i in range(1, len(xs)):
        if x <= xs[i]:
            t = (x - xs[i - 1]) / ((xs[i] - xs[i - 1]) or 1.0)
            return ys[i - 1] + (ys[i] - ys[i - 1]) * t
    return ys[-1]


@dataclass(frozen=True)
class RefEye:
    """One traced eye: centre and half sizes (image pixels), the radial profile of its outline
    (``RADIAL_SAMPLES`` values, 1 = on the ellipse with those half sizes, angle 0 = right, y
    down) and its pupil as (x, y, rx, ry) in units of the half sizes, relative to the centre (the
    eye outline clips it)."""

    centre: tuple[float, float]
    half: tuple[float, float]
    radii: tuple[float, ...]
    pupil: tuple[float, float, float, float]

    @classmethod
    def trace(cls, outline: list[tuple[float, float]], pupil: tuple[float, float, float, float],
              smooth: int = 4) -> RefEye:
        """Build from a traced outline (image pixels) and pupil ellipse (centre + radii, pixels)."""
        pts = _catmull(outline, smooth, closed=True)
        xs, ys = [p[0] for p in pts], [p[1] for p in pts]
        cx, cy = (min(xs) + max(xs)) / 2.0, (min(ys) + max(ys)) / 2.0
        hx, hy = (max(xs) - min(xs)) / 2.0, (max(ys) - min(ys)) / 2.0
        norm = [((x - cx) / hx, (y - cy) / hy) for x, y in pts]
        radii = tuple(_ray_hit(norm, i * math.tau / RADIAL_SAMPLES)
                      for i in range(RADIAL_SAMPLES))
        px, py, prx, pry = pupil
        return cls((cx, cy), (hx, hy), radii, ((px - cx) / hx, (py - cy) / hy, prx / hx, pry / hy))

    def radius(self, angle: float) -> float:
        """Radial profile at ``angle`` (linear between samples)."""
        f = (angle / math.tau % 1.0) * RADIAL_SAMPLES
        i = int(f)
        t = f - i
        return self.radii[i % RADIAL_SAMPLES] * (1.0 - t) + self.radii[(i + 1) % RADIAL_SAMPLES] * t


@dataclass(frozen=True)
class RefMouth:
    """One traced mouth (image pixels, relative to ``centre``): upper and lower lip heights at the
    ``mouth_s`` positions across ``half_w`` (equal for a closed line), an optional tongue line
    (points; the tongue fills everything below it inside the mouth) and optional strokes crossing
    the corners, as (side, points): -1 = left / 1 = right corner; the points are relative to that
    corner, so the strokes follow the lip ends."""

    centre: tuple[float, float]
    half_w: float
    top: tuple[float, ...]
    bottom: tuple[float, ...]
    tongue: tuple[tuple[float, float], ...] = ()
    corner_strokes: tuple[tuple[int, tuple[tuple[float, float], ...]], ...] = ()

    @property
    def closed(self) -> bool:
        """True for a closed mouth (a single line)."""
        return self.top == self.bottom

    @classmethod
    def trace_open(cls, outline: list[tuple[float, float]],
                   tongue: list[tuple[float, float]]) -> RefMouth:
        """Build an open mouth from its traced outline and tongue line (image pixels)."""
        pts = _catmull(outline, 3, closed=True)
        xs = [p[0] for p in pts]
        x0, x1 = min(xs), max(xs)
        cx, half_w = (x0 + x1) / 2.0, (x1 - x0) / 2.0
        top, bottom = [], []
        for i in range(MOUTH_SAMPLES):
            x = cx + mouth_s(i) * half_w * 0.999
            hits = _vertical_hits(pts, x)
            top.append(min(hits))
            bottom.append(max(hits))
        cy = (min(top) + max(bottom)) / 2.0
        return cls((cx, cy), half_w, tuple(y - cy for y in top), tuple(y - cy for y in bottom),
                   tuple((x - cx, y - cy) for x, y in _catmull(tongue, 4, closed=False)))

    @classmethod
    def trace_line(cls, line: list[tuple[float, float]],
                   strokes: list[list[tuple[float, float]]]) -> RefMouth:
        """Build a closed mouth from its traced centre line and corner strokes (image pixels;
        each stroke's first point is where it meets the line)."""
        pts = _catmull(line, 6, closed=False)
        xs, ys = [p[0] for p in pts], [p[1] for p in pts]
        cx, half_w = (xs[0] + xs[-1]) / 2.0, (xs[-1] - xs[0]) / 2.0
        heights = [_interp(xs, ys, cx + mouth_s(i) * half_w) for i in range(MOUTH_SAMPLES)]
        cy = (min(heights) + max(heights)) / 2.0
        lip = tuple(y - cy for y in heights)
        return cls((cx, cy), half_w, lip, lip, (), tuple(
            (-1 if s[0][0] < cx else 1,
             tuple((x - s[0][0], y - s[0][1]) for x, y in _catmull(s, 4, closed=False)))
            for s in strokes))


@dataclass(frozen=True)
class RefFace:
    """A whole traced face: eyes (left, right as seen), mouth, line widths (image pixels), the
    image point that maps to the parametric eye line (centre between the eyes) and the pixels -> R
    scale."""

    scale: float
    origin: tuple[float, float]
    eyes: tuple[RefEye, RefEye]
    mouth: RefMouth
    eye_ink: float
    mouth_ink: float


# --------------------------------------------------------------------------- fig. 1 (happy)
# Half-dome eyes: a high round top, a flat bottom; the tall pupils hang from the top edge,
# glancing a little right. Open mouth: two round upper lobes with a soft notch between them, a
# deep round lower lip, a pink tongue in its lower half.
_FIG1_LEFT_EYE = [
    (264.8, 604.1), (266.2, 607.8), (265.4, 611.4), (261.4, 613.1), (256.7, 613.0), (253.4, 612.7),
    (251.1, 612.5), (249.2, 612.5), (247.5, 612.5), (245.7, 612.7), (243.7, 613.0), (241.0, 613.5),
    (237.3, 614.0), (233.1, 613.5), (230.5, 611.1), (230.1, 607.5), (230.6, 604.0), (232.4, 601.2),
    (235.7, 599.2), (238.2, 597.8), (240.4, 597.0), (242.4, 596.4), (244.2, 596.0), (245.9, 595.9),
    (247.5, 595.9), (249.1, 595.9), (250.8, 596.0), (252.5, 596.5), (254.6, 597.0), (256.9, 597.8),
    (259.5, 599.1), (262.2, 601.2),
]
_FIG1_RIGHT_EYE = [
    (311.9, 603.6), (313.2, 607.4), (312.1, 611.0), (308.0, 612.6), (303.1, 612.3), (299.7, 611.9),
    (297.4, 611.7), (295.6, 611.7), (294.0, 611.7), (292.3, 611.9), (290.3, 612.3), (287.7, 612.7),
    (284.3, 613.0), (280.3, 612.5), (277.5, 610.3), (277.0, 606.9), (278.2, 603.6), (280.2, 600.8),
    (282.5, 598.8), (284.7, 597.4), (286.9, 596.5), (288.9, 595.9), (290.6, 595.4), (292.3, 595.1),
    (294.0, 595.0), (295.7, 595.1), (297.4, 595.3), (299.3, 595.6), (301.5, 596.1), (303.9, 597.0),
    (306.6, 598.4), (309.4, 600.5),
]
_FIG1_MOUTH = [
    (296.0, 631.0), (294.4, 635.1), (290.8, 638.2), (286.8, 640.1), (283.3, 641.3), (280.2, 641.9),
    (277.5, 642.2), (275.2, 642.4), (273.0, 642.4), (271.0, 642.4), (269.0, 642.5), (266.8, 642.4),
    (264.4, 642.4), (261.6, 642.1), (258.5, 641.4), (254.9, 640.3), (251.0, 638.3), (247.6, 635.1),
    (245.7, 631.0), (245.7, 626.5), (248.2, 622.7), (252.9, 620.6), (258.4, 620.4), (262.7, 621.1),
    (265.9, 622.2), (268.2, 623.4), (269.8, 624.2), (271.0, 624.8), (272.2, 624.3), (273.8, 623.4),
    (276.2, 622.0), (279.7, 620.6), (283.8, 620.3), (288.5, 621.0), (292.5, 623.2), (295.1, 626.8),
]
# The tongue's upper edge, from where it leaves the lower lip on the left to the right.
_FIG1_TONGUE = [
    (253.0, 641.0), (255.0, 635.5), (258.0, 633.6), (262.0, 632.8), (266.0, 632.4),
    (270.0, 632.3), (274.0, 632.4), (278.0, 632.8), (282.0, 633.5), (286.0, 634.6),
    (289.5, 636.5), (291.5, 640.0),
]

# --------------------------------------------------------------------------- fig. 7 (chill)
# Seen a little from the side and tipped (the right side higher): half-dome eyes with slanted
# flat bottoms and big round pupils glancing right; a long, wavy closed smile, each corner crossed
# by a short stroke (a cheek dimple).
_FIG7_LEFT_EYE = [
    (138.6, 1219.9), (141.1, 1213.0), (146.75, 1208.6), (154.25, 1206.75), (161.75, 1206.5),
    (169.25, 1208.0), (174.25, 1210.5), (176.1, 1213.6), (175.5, 1216.75), (170.5, 1219.0),
    (160.5, 1219.5), (151.75, 1220.75), (144.9, 1223.6), (139.9, 1224.25), (138.0, 1221.75),
]
_FIG7_RIGHT_EYE = [
    (186.1, 1212.4), (188.0, 1206.75), (193.0, 1201.5), (200.5, 1199.25), (210.5, 1198.6),
    (218.0, 1199.9), (223.0, 1203.6), (223.6, 1208.0), (221.75, 1211.1), (213.0, 1211.75),
    (203.0, 1212.0), (194.25, 1213.6), (189.9, 1216.1), (187.4, 1215.5),
]
_FIG7_LINE = [
    (131.5, 1233.0), (133.0, 1234.9), (136.75, 1236.75), (143.0, 1238.0), (151.1, 1238.6),
    (158.0, 1236.1), (168.0, 1232.4), (176.75, 1231.1), (185.5, 1232.4), (193.0, 1232.4),
    (200.5, 1229.9), (205.5, 1228.0), (215.5, 1225.5), (225.5, 1223.0), (230.5, 1220.75),
    (234.5, 1219.0),
]
# Each stroke crosses a corner: one end above the line, the other just past it.
_FIG7_STROKES = [
    [(131.5, 1233.0), (131.2, 1228.0), (130.5, 1223.0)],      # left corner, upper part
    [(131.5, 1233.0), (129.0, 1236.5), (126.75, 1239.25)],    # left corner, tail
    [(234.5, 1219.0), (231.75, 1214.25), (229.25, 1208.0)],   # right corner, upper part
    [(234.5, 1219.0), (237.5, 1219.6), (239.9, 1219.3)],      # right corner, tail
]

REF_FACES: dict[str, RefFace] = {
    "fig1": RefFace(
        scale=0.021, origin=(271.6, 604.5),
        eyes=(RefEye.trace(_FIG1_LEFT_EYE, (250.1, 602.2, 3.8, 5.9), smooth=3),
              RefEye.trace(_FIG1_RIGHT_EYE, (297.3, 601.6, 3.8, 6.0), smooth=3)),
        mouth=RefMouth.trace_open(_FIG1_MOUTH, _FIG1_TONGUE),
        eye_ink=2.7, mouth_ink=2.3),
    "fig7": RefFace(
        scale=0.022, origin=(181.0, 1211.4),
        eyes=(RefEye.trace(_FIG7_LEFT_EYE, (158.0, 1212.5, 6.8, 6.8)),
              RefEye.trace(_FIG7_RIGHT_EYE, (205.5, 1205.5, 6.8, 6.8))),
        mouth=RefMouth.trace_line(_FIG7_LINE, _FIG7_STROKES),
        eye_ink=2.5, mouth_ink=2.5),
}
