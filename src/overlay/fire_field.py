"""Metaball fire renderer (``character.flame_renderer: metaball``).

Rising tongues melted into one shape.

How it works (all lengths in units of R in body coordinates: x right, y *up is negative*, origin
at the feet):

- The flame is a smooth "density field": a soft-edged body ellipse (where the face lives) plus a
  set of teardrop-shaped *tongues* - one persistent "spine" that forms the main tip and a stream
  of short-lived tongues.
- Tongues are born just inside the top and the flanks of the body, rise with buoyancy, bend,
  stretch, lean with the wind (the pet's own movement) and fade. Where they overlap they melt
  together smoothly; when one rises faster than its neighbours it pinches off into a small
  separate flame piece and dies away - the way a hand-drawn cartoon flame behaves.
- Each colour layer (red rim, orange band, yellow body) is an iso-contour of the same field at a
  different level. The levels change with height, so tongues have red tips, an orange middle and
  a yellow base, and the red rim stays thin around the bottom of the body.
- Contours are traced with marching squares on a coarse grid (numpy) and turned into smooth
  ``QPainterPath`` outlines (in pixels) that the character paints with QPainter.
"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass

import numpy as np
from PySide6.QtCore import Qt
from PySide6.QtGui import QPainter, QPainterPath, QPen

from overlay.flame_common import BODY_CY, BODY_RX, BODY_RY, FlameColors, FlameDrive, FlameRenderer
from overlay.flame_common import noise1 as _noise1
from overlay.flame_common import smoothstep as _smoothstep

# Base iso-levels of the three colour layers (outer red rim, orange band, yellow body).
_LEVELS = (0.16, 0.27, 0.38)
# Extra level added high up for the inner layers, so tongue tips are red and only their base
# is yellow (as in the reference art).
_TOP_GAIN = (0.0, 0.06, 0.14)

_TIP_SPREAD = 1.3     # angular half-width (radians) over which a tongue narrows into its tip
_BODY_FALLOFF = 0.12  # how quickly (in R) the body's field dies off outside its outline


@dataclass
class _Tongue:
    """One rising flame tongue (position/size in units of R, time in simulation seconds)."""

    x: float
    y: float
    vx: float
    vy: float
    size: float      # radius of the round base when fully grown
    stretch: float   # tip length relative to the round base, when born
    age: float
    life: float
    weight: float    # peak strength (bigger = more solid)
    curl: float      # how much the tongue bends sideways toward its tip


def _segment_table() -> np.ndarray:
    """Marching-squares lookup: for each cell case, up to two segments as (edge, edge) pairs.

    Cell corners: top-left=8, top-right=4, bottom-right=2, bottom-left=1. Edges: 0=top,
    1=right, 2=bottom, 3=left. Cases 5 and 10 are saddles; codes 16/17 are those saddles when
    the cell centre is inside (the two inside corners are joined).
    """
    segments = {
        1: ((3, 2),), 2: ((2, 1),), 3: ((3, 1),), 4: ((0, 1),), 5: ((0, 1), (3, 2)),
        6: ((0, 2),), 7: ((3, 0),), 8: ((3, 0),), 9: ((0, 2),), 10: ((3, 0), (2, 1)),
        11: ((0, 1),), 12: ((3, 1),), 13: ((2, 1),), 14: ((3, 2),),
        16: ((3, 0), (2, 1)), 17: ((0, 1), (3, 2)),
    }
    table = np.full((18, 2, 2), -1, dtype=np.int64)
    for case, segs in segments.items():
        for k, pair in enumerate(segs):
            table[case, k] = pair
    return table


_SEGMENT_TABLE = _segment_table()


class MetaballFlame(FlameRenderer):
    """Simulates the tongues and traces the three layer outlines every frame.

    ``R`` is the character's base radius in pixels. Call ``step()`` once per frame, then
    ``paint()``; ``paths`` holds the outer, middle and inner layer outlines (pixels, body
    coordinates).
    """

    name = "metaball"

    GRID_STEP_PX = 2.4       # spacing of the field samples in pixels (finer = smoother, slower)
    X_RANGE = (-2.2, 2.2)    # field area in units of R
    Y_RANGE = (-4.0, 0.3)

    def __init__(self, R: float, rng: random.Random) -> None:
        """Build the sample grid and the per-node colour levels for radius ``R`` (pixels)."""
        super().__init__(R, rng)
        self.tongues: list[_Tongue] = []
        self._spawn_debt = 0.0

        h = 1.0 / min(20.0, max(10.0, R / self.GRID_STEP_PX))
        self._h = h
        xs = np.arange(self.X_RANGE[0], self.X_RANGE[1] + h / 2, h, dtype=np.float32)
        ys = np.arange(self.Y_RANGE[0], self.Y_RANGE[1] + h / 2, h, dtype=np.float32)
        self._x0, self._y0 = float(xs[0]), float(ys[0])
        self._X, self._Y = np.meshgrid(xs, ys)

        # Per-node level of every layer: lower near the feet (thin rim around the bottom),
        # higher toward the top for the inner layers (red-tipped tongues).
        bottom = np.clip((self._Y + BODY_CY) / BODY_CY, 0.0, 1.0)
        top = np.clip((-self._Y - BODY_CY - 0.4) / 1.2, 0.0, 1.0)
        self._levels = [
            (lvl - (lvl - _LEVELS[0]) * 0.55 * bottom ** 2 + gain * top).astype(np.float32)
            for lvl, gain in zip(_LEVELS, _TOP_GAIN, strict=True)
        ]

        self.paths: list[QPainterPath] = [QPainterPath() for _ in _LEVELS]

    # ------------------------------------------------------------------ simulation

    def flare(self, strength: float = 1.0) -> None:
        """Sudden flare-up: one big tongue up the middle plus a couple of smaller ones across the
        top, so the crown jumps up ragged instead of as one smooth cone."""
        self._spawn("centre", boost=strength)
        for _ in range(2):
            self._spawn("top", boost=strength * self._rng.uniform(0.85, 1.1))

    def step(self, drive: FlameDrive) -> None:
        """Advance the tongues by one frame and rebuild the layer outlines."""
        dt, clock, seed = drive.dt, drive.clock, drive.seed
        wild, flame, wind_x, wind_y = drive.wild, drive.flame, drive.wind_x, drive.wind_y
        rng = self._rng
        # Irregular emission: a noisy rate, so tongues come in little clusters and lulls.
        rate = (7.0 + 4.0 * wild) * (0.7 + 0.6 * _noise1(clock * 0.9, seed + 11))
        self._spawn_debt += rate * dt
        while self._spawn_debt >= 1.0:
            self._spawn_debt -= 1.0
            roll = rng.random()
            self._spawn("centre" if roll < 0.15 else "flank" if roll < 0.45 else "top", 1.0)

        alive = []
        for t in self.tongues:
            t.age += dt
            if t.age >= t.life:
                continue
            # Buoyancy speeds tongues up as they rise; they drift toward the centre line (where
            # the main tip is) and are pushed around by a little turbulence and the wind.
            turbulence = 1.6 * wild * _noise1(clock * 2.3 + t.weight * 31.0, seed + 23)
            t.vy -= 2.2 * flame * dt
            t.vx += (-0.12 * t.x + turbulence + 2.5 * (wind_x - t.vx)) * dt
            t.vy += 0.8 * wind_y * dt
            t.x += t.vx * dt
            t.y += t.vy * dt
            alive.append(t)
        self.tongues = alive

        self._rebuild(clock, seed, wild, flame, drive.sway, drive.breath)

    def paint(self, painter: QPainter, colors: FlameColors) -> None:
        """Red rim with the dark outline, then the orange band and the yellow body."""
        outer, mid, inner = self.paths
        painter.setPen(QPen(colors.ink, colors.outline_px, Qt.PenStyle.SolidLine,
                            Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
        painter.setBrush(colors.outer)
        painter.drawPath(outer)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(colors.mid)
        painter.drawPath(mid)
        painter.setBrush(colors.inner)
        painter.drawPath(inner)

    def _spawn(self, where: str, boost: float) -> None:
        """Create one tongue just inside the body: up the middle, on top, or on a flank."""
        rng = self._rng
        if where == "flank":
            # Low on the shoulders: these become the small licks running up the sides.
            side = rng.choice((-1.0, 1.0))
            phi = rng.uniform(0.75, 1.2)  # angle from straight up
            x = side * (BODY_RX - 0.08) * math.sin(phi)
            y = -BODY_CY - (BODY_RY - 0.06) * math.cos(phi)
            size = rng.uniform(0.3, 0.42)
            vx = -side * rng.uniform(0.0, 0.3)
        else:
            if where == "centre":
                x = rng.gauss(0.0, 0.22)
                size = rng.uniform(0.4, 0.52) * boost
            else:
                x = rng.uniform(-0.8, 0.8) * BODY_RX
                size = rng.uniform(0.38, 0.52) * (1.0 - 0.15 * abs(x)) * boost
            y = -BODY_CY - (BODY_RY - 0.02) * math.sqrt(max(0.0, 1.0 - (x / BODY_RX) ** 2)) + 0.12
            vx = rng.uniform(-0.25, 0.25) + 0.1 * x
        self.tongues.append(_Tongue(
            x=x, y=y, vx=vx, vy=-rng.uniform(0.5, 1.0) * boost, size=size,
            stretch=rng.uniform(2.6, 3.6), age=0.0, life=rng.uniform(0.65, 1.05),
            weight=rng.uniform(0.45, 0.6), curl=rng.uniform(-0.06, 0.06),
        ))

    # ------------------------------------------------------------------ field + contours

    def _rebuild(self, clock: float, seed: int, wild: float, flame: float, sway: float,
                 breath: float) -> None:
        """Evaluate the density field and trace the outline of every colour layer."""
        X, Y = self._X, self._Y
        # Body: a soft-edged ellipse. Its field grows steadily inside (so the inner colour
        # layers are even bands) and dies off quickly outside (so tongues stay distinct).
        bx = BODY_RX * (1.0 + 0.02 * breath)
        by = BODY_RY * (1.0 - 0.02 * breath)
        u = X * (1.0 / bx)
        v = (Y + BODY_CY) * (1.0 / by)
        q = np.sqrt(u * u + v * v) + 1e-6
        gradient = np.sqrt((u * (1.0 / bx)) ** 2 + (v * (1.0 / by)) ** 2) / q
        d = (q - 1.0) / gradient  # approximate signed distance to the ellipse (in R)
        outer = _LEVELS[0]
        body = np.where(d > 0.0, outer * np.exp(-np.maximum(d, 0.0) * (1.0 / _BODY_FALLOFF)),
                        outer - d * 0.92)

        # Tongues: (x, y, half-width, half-height, tip length, tip angle, weight, bend).
        prims = [
            # Spine: the main tip. It sways and flutters on its own noise.
            (0.1 * _noise1(clock * 0.7, seed + 5), -BODY_CY - 0.55, 0.7, 0.7,
             flame * (3.7 + 0.6 * wild * _noise1(clock * 2.6, seed + 6)), sway, 0.62,
             0.07 * _noise1(clock * 1.1, seed + 7)),
        ]
        for t in self.tongues:
            k = t.age / t.life
            env = _smoothstep(0.0, 0.2, k) * (1.0 - k) ** 1.2
            size = t.size * (1.0 - 0.3 * k) / 0.54
            # Tongues away from the middle are shorter and lean in toward the main tip, so the
            # crown reads as one flame rather than separate "ears".
            stretch = flame * (t.stretch + 1.0 * k) * (1.0 - 0.32 * min(1.0, abs(t.x)))
            tilt = math.atan2(t.vx, -t.vy) * 0.6 - 0.3 * t.x
            prims.append((t.x, t.y, size, size, stretch, tilt, t.weight * env,
                          t.curl + 0.05 * t.vx))

        # Tongues combine with a soft maximum (4-norm) instead of a plain sum, so a cluster of
        # overlapping tongues stays a cluster of tongues instead of swelling into one fat blob.
        # Each tongue is only evaluated inside its own bounding box.
        acc = np.zeros_like(X)
        h, x0, y0 = self._h, self._x0, self._y0
        ny, nx = X.shape
        for cx, cy, ax, ay, tip, ang, w, bend in prims:
            if w < 0.02:
                continue
            reach = tip * max(ax, ay) * (1.0 + abs(bend)) + h
            j0, j1 = max(0, int((cx - reach - x0) / h)), min(nx, int((cx + reach - x0) / h) + 2)
            i0, i1 = max(0, int((cy - reach - y0) / h)), min(ny, int((cy + reach - y0) / h) + 2)
            if j0 >= j1 or i0 >= i1:
                continue
            du = X[i0:i1, j0:j1] - cx
            dv = Y[i0:i1, j0:j1] - cy
            sin_a, cos_a = math.sin(ang), math.cos(ang)
            along = (du * sin_a - dv * cos_a) * (1.0 / ay)  # toward the tip
            # Bend: shift sideways more and more toward the tip, so tongues curl like licks.
            across = (du * cos_a + dv * sin_a) * (1.0 / ax)
            if bend:
                across -= bend * np.square(np.maximum(along, 0.0))
            # Concave flanks running into a sharp point (a high power keeps the tip
            # needle-sharp while the base stays round), like a hand-drawn flame tongue.
            ramp = np.maximum(1.0 - np.arctan2(np.abs(across), along) * (1.0 / _TIP_SPREAD), 0.0)
            reach_n = 1.0 + (tip - 1.0) * (ramp * ramp * ramp)
            kern = np.maximum(1.0 - (along * along + across * across) / (reach_n * reach_n), 0.0)
            value = w * kern * kern * kern
            value *= value
            acc[i0:i1, j0:j1] += value * value
        field = body + np.sqrt(np.sqrt(acc))

        R = self.R
        self.paths = []
        for i, level in enumerate(self._levels):
            g = field - level
            loops = _solid_loops(_trace(g, x0, y0, h))
            path = QPainterPath()
            for loop in loops:
                _add_smooth_loop(path, loop, R)
            self.paths.append(path)
            if i == 0:
                pts = [(x * R, y * R) for loop in loops for (x, y) in loop]
                if pts:
                    self.tip = min(pts, key=lambda p: p[1])
                cut = -(BODY_CY + 0.5) * R
                self.top_points = [p for p in pts if p[1] < cut]

# ---------------------------------------------------------------------- contour helpers

def _trace(g: np.ndarray, x0: float, y0: float, h: float) -> list[list[tuple[float, float]]]:
    """Marching squares: closed loops (in units of R) where ``g`` crosses 0.

    Segments are generated with numpy; only the final walk around each loop is Python.
    """
    g[0, :] = g[-1, :] = -1.0  # force closed loops at the border
    g[:, 0] = g[:, -1] = -1.0
    inside = g > 0.0
    ny, nx = g.shape
    n_h = ny * (nx - 1)            # horizontal edges come first, then vertical edges
    n_edges = n_h + (ny - 1) * nx

    # Crossing point on every grid edge whose two ends disagree (linear interpolation).
    px = np.zeros(n_edges)
    py = np.zeros(n_edges)
    hi, hj = np.nonzero(inside[:, :-1] != inside[:, 1:])
    ga, gb = g[hi, hj], g[hi, hj + 1]
    ids = hi * (nx - 1) + hj
    px[ids] = x0 + h * (hj + ga / (ga - gb))
    py[ids] = y0 + h * hi
    vi, vj = np.nonzero(inside[:-1, :] != inside[1:, :])
    ga, gb = g[vi, vj], g[vi + 1, vj]
    ids = n_h + vi * nx + vj
    px[ids] = x0 + h * vj
    py[ids] = y0 + h * (vi + ga / (ga - gb))

    cases = ((inside[:-1, :-1] * 8) | (inside[:-1, 1:] * 4) | (inside[1:, 1:] * 2)
             | inside[1:, :-1])
    ci, cj = np.nonzero((cases > 0) & (cases < 15))
    if len(ci) == 0:
        return []
    case = cases[ci, cj].astype(np.int64)
    centre = (g[ci, cj] + g[ci, cj + 1] + g[ci + 1, cj] + g[ci + 1, cj + 1]) > 0.0
    case = np.where(centre & (case == 5), 16, np.where(centre & (case == 10), 17, case))
    edges = np.stack([ci * (nx - 1) + cj,            # top
                      n_h + ci * nx + cj + 1,        # right
                      (ci + 1) * (nx - 1) + cj,      # bottom
                      n_h + ci * nx + cj], axis=1)   # left
    seg = _SEGMENT_TABLE[case]                       # (cells, 2 segments, 2 edges)
    cell, k = np.nonzero(seg[:, :, 0] >= 0)
    a = edges[cell, seg[cell, k, 0]]
    b = edges[cell, seg[cell, k, 1]]

    # Every crossing edge is shared by exactly two segments: pair them up by sorting.
    ends = np.concatenate([a, b])
    other = np.concatenate([b, a])
    order = np.argsort(ends, kind="stable")
    ends, other = ends[order], other[order]
    # Renumber the crossing edges 0..n-1 so the Python walk only touches small lists.
    crossing = ends[0::2]
    first_l = np.searchsorted(crossing, other[0::2]).tolist()
    second_l = np.searchsorted(crossing, other[1::2]).tolist()
    xs, ys = px[crossing].tolist(), py[crossing].tolist()
    visited = bytearray(len(crossing))
    loops = []
    for start in range(len(crossing)):
        if visited[start]:
            continue
        loop = []
        prev, cur = -1, start
        while not visited[cur]:
            visited[cur] = 1
            loop.append((xs[cur], ys[cur]))
            nxt = first_l[cur]
            if nxt == prev:
                nxt = second_l[cur]
            prev, cur = cur, nxt
        if len(loop) >= 4:
            loops.append(loop)
    return loops


def _solid_loops(loops: list[list[tuple[float, float]]]) -> list[list[tuple[float, float]]]:
    """Keep only the outer boundaries of a layer, dropping dust-sized islands.

    A loop lying inside another loop is a hole (where two tongues barely fail to meet) or an
    island inside such a hole. Real flames have no holes, so they are filled in: each layer
    becomes a set of solid shapes. (The tracer's loop direction is not reliable, so nesting is
    decided geometrically.)
    """
    loops = [lp for lp in loops if abs(_signed_area(lp)) >= 0.004]
    if len(loops) < 2:
        return loops
    arrays = [np.asarray(lp) for lp in loops]
    boxes = [(a[:, 0].min(), a[:, 0].max(), a[:, 1].min(), a[:, 1].max()) for a in arrays]
    kept = []
    for i, lp in enumerate(loops):
        x, y = lp[0]
        nested = any(
            j != i and b[0] <= x <= b[1] and b[2] <= y <= b[3] and _point_in(arrays[j], x, y)
            for j, b in enumerate(boxes)
        )
        if not nested:
            kept.append(lp)
    return kept


def _point_in(poly: np.ndarray, x: float, y: float) -> bool:
    """Even-odd ray-casting test: is (``x``, ``y``) inside the closed polygon ``poly``?"""
    xs, ys = poly[:, 0], poly[:, 1]
    xn, yn = np.roll(xs, -1), np.roll(ys, -1)
    crosses = (ys > y) != (yn > y)
    with np.errstate(divide="ignore", invalid="ignore"):
        x_at = xs + (y - ys) * (xn - xs) / (yn - ys)
    return bool(np.count_nonzero(crosses & (x < x_at)) % 2)


def _signed_area(loop: list[tuple[float, float]]) -> float:
    """Shoelace area of a closed polygon (sign depends on the direction it was traced)."""
    total = 0.0
    px, py = loop[-1]
    for x, y in loop:
        total += px * y - x * py
        px, py = x, y
    return total * 0.5


def _add_smooth_loop(path: QPainterPath, loop: list[tuple[float, float]], scale: float) -> None:
    """Append one closed loop as a smooth curve (quadratic segments through the midpoints)."""
    pts = [(x * scale, y * scale) for x, y in loop]
    lx, ly = pts[-1]
    fx, fy = pts[0]
    path.moveTo((lx + fx) * 0.5, (ly + fy) * 0.5)
    quad = path.quadTo
    for i in range(len(pts) - 1):
        x, y = pts[i]
        nx_, ny_ = pts[i + 1]
        quad(x, y, (x + nx_) * 0.5, (y + ny_) * 0.5)
    quad(lx, ly, (lx + fx) * 0.5, (ly + fy) * 0.5)
    path.closeSubpath()
