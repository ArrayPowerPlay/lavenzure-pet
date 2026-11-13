"""Shared building blocks for the flame body renderers.

The flame character can draw its fire body in more than one way (see ``config.yaml`` ->
``character.flame_renderer``):

- ``metaball`` - particle "tongues" melted into a density field, traced into vector outlines
  (``overlay.fire_field``).
- ``shader``   - a GLSL fragment shader of rising, domain-warped noise, rendered offscreen on the
  GPU (``overlay.flame_shader``).
- ``baked``    - clips of a real 2D fluid simulation computed offline and played back with
  morphing between clips (``overlay.flame_baked``).

All of them share what lives in this module:

- the body geometry (``BODY_*``), so the face always sits on the same calm yellow area no matter
  which renderer is active;
- ``FlameDrive`` (per-frame inputs from the character) and ``FlameColors``;
- ``FireWeather``: slow random "moods" of the fire (calm, gust, crackle, lull) plus a drifting
  lean of the main tip, so the flame never settles into one predictable rhythm;
- ``FlameRenderer`` (the interface) and ``ImageFlame`` (helper for renderers that produce a
  bitmap instead of vector paths);
- small noise / math helpers.

Coordinates: "body coordinates" are pixels relative to the character's feet, x to the right and
y *up is negative* (Qt's convention). Lengths in the constants below are in units of R, the
character's base radius.
"""
from __future__ import annotations

import logging
import math
import random
from dataclasses import dataclass

import numpy as np
from PySide6.QtCore import QRectF
from PySide6.QtGui import QColor, QImage, QPainter

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------- body geometry (units of R)

BODY_CY = 1.0    # height of the body ellipse's centre above the feet
BODY_RX = 1.16   # half-width of the body (outer outline)
BODY_RY = 1.0    # half-height of the body (outer outline)

# Inset (in R, measured inward from the outer outline) of the orange band and the yellow body on
# the calm lower part of the flame. Renderers make their bands follow these so the face area is
# identical everywhere.
MID_INSET = 0.12
INNER_INSET = 0.24

# Sparks are spawned on the flame's top edge, sampled at every this-many-th bitmap column.
TOP_POINT_STEP = 3

# Face "safe area": an ellipse inside the yellow body that every face feature must stay within.
FACE_CY = 0.98   # centre height above the feet
FACE_RX = BODY_RX - INNER_INSET - 0.1
FACE_RY = BODY_RY - INNER_INSET - 0.08


# ---------------------------------------------------------------------- small math / noise helpers

def lerp(a: float, b: float, t: float) -> float:
    """Linear interpolation between ``a`` and ``b``."""
    return a + (b - a) * t


def clamp(value: float, low: float, high: float) -> float:
    """Clamp ``value`` into ``[low, high]``."""
    return max(low, min(high, value))


def approach(current: float, target: float, rate: float, dt: float) -> float:
    """Frame-rate independent exponential smoothing of ``current`` toward ``target``."""
    return current + (target - current) * (1.0 - math.exp(-rate * dt))


def smoothstep(edge0: float, edge1: float, x: float) -> float:
    """0 below ``edge0``, 1 above ``edge1``, smooth S-curve in between."""
    t = clamp((x - edge0) / (edge1 - edge0), 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


class Spring:
    """Damped spring (semi-implicit Euler). Under-damped settings give a jelly-like wobble."""

    def __init__(self, value: float, stiffness: float, damping: float) -> None:
        """Start at rest at ``value``."""
        self.value = value
        self.velocity = 0.0
        self.stiffness = stiffness
        self.damping = damping

    def step(self, target: float, dt: float) -> float:
        """Advance the spring toward ``target`` by ``dt`` seconds and return the new value."""
        accel = self.stiffness * (target - self.value) - self.damping * self.velocity
        self.velocity += accel * dt
        self.value += self.velocity * dt
        return self.value


def _hash(i: int, seed: int) -> float:
    """Deterministic pseudo-random value in ``[-1, 1]``.

    One value per lattice point ``i`` of noise ``seed``.
    """
    h = (i * 0x27D4EB2D ^ seed * 0x165667B1) & 0xFFFFFFFF
    h = ((h ^ (h >> 15)) * 0x85EBCA6B) & 0xFFFFFFFF
    h = ((h ^ (h >> 13)) * 0xC2B2AE35) & 0xFFFFFFFF
    h ^= h >> 16
    return h / 0x7FFFFFFF - 1.0


def noise1(x: float, seed: int) -> float:
    """1D gradient (Perlin) noise: smooth, never repeating, roughly within ``[-1, 1]``."""
    i = math.floor(x)
    f = x - i
    u = f * f * f * (f * (f * 6.0 - 15.0) + 10.0)
    return 2.0 * lerp(_hash(i, seed) * f, _hash(i + 1, seed) * (f - 1.0), u)


def fbm1(x: float, seed: int) -> float:
    """Two octaves of 1D noise: a slow swell plus a faster, smaller flutter on top."""
    return (noise1(x, seed) + 0.5 * noise1(x * 2.13 + 7.7, seed + 911)) / 1.5


# ---------------------------------------------------------------------- inputs / colours

@dataclass
class FlameDrive:
    """Everything the character tells the flame renderer each frame.

    ``dt`` and ``clock`` are in *simulation* seconds (they already run faster when the fire
    flickers faster). ``wild`` = flicker strength, ``flame`` = height multiplier, ``wind_x`` /
    ``wind_y`` = apparent wind in R per second caused by the pet's own movement (the fire trails
    behind), ``sway`` = lean of the main tip in radians, ``breath`` = slow -1..1 body breathing.
    """

    dt: float
    clock: float
    seed: int
    wild: float
    flame: float
    wind_x: float
    wind_y: float
    sway: float
    breath: float
    # Body shape (expressions reshape the flame freely; only the shader renderer draws all of it,
    # the others get a plain scale): width / height multipliers, boxiness 0..1, raggedness 0..1.
    body_w: float = 1.0
    body_h: float = 1.0
    boxy: float = 0.0
    jag: float = 0.0
    # Sitting on the log (shader only): how much 0..1, the paws' kneading phase and the height
    # of the log's top (R above the feet) where the body's bottom is cut flat.
    paws: float = 0.0
    paw_phase: float = 0.0
    seat: float = 0.0


@dataclass
class FlameColors:
    """Fill colours of the three layers, the outline colour, and the outline width in pixels."""

    outer: QColor
    mid: QColor
    inner: QColor
    ink: QColor
    outline_px: float


# ---------------------------------------------------------------------- fire weather

class FireWeather:
    """Slow random "weather" of the fire so it never falls into one rhythm.

    The fire wanders between a few states - a steady *calm* burn, a *gust* (taller, swaying), a
    short *crackle* (fast, jittery), a *lull* (low and lazy) - each lasting a random time, and the
    outputs glide between them. On top of that the main tip slowly drifts left and right
    (``drift``) instead of always standing in the middle.
    """

    # name: (pick weight, (min, max) seconds, height, turbulence, speed, flare chance multiplier)
    STATES = {
        "calm": (4.0, (2.5, 7.0), 1.0, 0.9, 0.95, 1.0),
        "gust": (2.0, (0.9, 2.4), 1.12, 1.3, 1.2, 1.6),
        "crackle": (1.4, (0.4, 1.3), 1.04, 1.55, 1.55, 2.2),
        "lull": (1.2, (1.6, 3.8), 0.88, 0.7, 0.75, 0.4),
    }

    def __init__(self, rng: random.Random, seed: int) -> None:
        """Start in a calm state; ``seed`` makes the drift noise differ between pets."""
        self._rng = rng
        self._seed = seed
        self._state = "calm"
        self._until = rng.uniform(1.0, 4.0)
        self._t = 0.0
        self.height = 1.0
        self.turbulence = 1.0
        self.speed = 1.0
        self.flare_boost = 1.0
        self.drift = 0.0

    @property
    def state(self) -> str:
        """Name of the current weather state (for debugging / the preview tool)."""
        return self._state

    def update(self, dt: float) -> None:
        """Advance real time ``dt`` seconds: maybe change state, ease the outputs toward it."""
        self._t += dt
        if self._t >= self._until:
            names = [n for n in self.STATES if n != self._state]
            weights = [self.STATES[n][0] for n in names]
            self._state = self._rng.choices(names, weights)[0]
            lo, hi = self.STATES[self._state][1]
            self._until = self._t + self._rng.uniform(lo, hi)
        _, _, height, turbulence, speed, flare = self.STATES[self._state]
        rate = 6.0 if self._state == "crackle" else 1.8
        self.height = approach(self.height, height, rate, dt)
        self.turbulence = approach(self.turbulence, turbulence, rate, dt)
        self.speed = approach(self.speed, speed, rate, dt)
        self.flare_boost = flare
        self.drift = 0.2 * fbm1(self._t * 0.13, self._seed + 4242)


# ---------------------------------------------------------------------- renderer interface

class FlameRenderer:
    """Interface of a flame body renderer.

    Call ``step()`` once per frame, then ``paint()`` with a painter already transformed into body
    coordinates. ``top_points`` (outer outline points high on the flame, body pixels) is used by
    the character to spawn sparks; ``tip`` is the highest outline point.
    """

    name = "base"

    def __init__(self, R: float, rng: random.Random) -> None:
        """``R`` = character base radius in pixels; ``rng`` = the character's random source."""
        self.R = R
        self._rng = rng
        self.top_points: list[tuple[float, float]] = []
        self.tip: tuple[float, float] = (0.0, -2.6 * R)

    def flare(self, strength: float = 1.0) -> None:
        """Sudden flare-up of the fire (used for happy / surprised reactions)."""

    def step(self, drive: FlameDrive) -> None:
        """Advance the fire by one frame."""
        raise NotImplementedError

    def paint(self, painter: QPainter, colors: FlameColors) -> None:
        """Draw the three layers and the dark outline in body coordinates."""
        raise NotImplementedError


class ImageFlame(FlameRenderer):
    """Base for renderers whose output is a premultiplied ARGB bitmap of the flame.

    The bitmap covers ``X_RANGE`` x ``Y_RANGE`` (units of R) of body space at ``SUPERSAMPLE``
    times the on-screen resolution (so it stays crisp under the character's squash/lean
    transform). Subclasses fill ``self.image`` in ``step()`` and call ``_update_top_points()``.
    """

    X_RANGE = (-2.2, 2.2)
    Y_RANGE = (-4.1, 0.25)
    SUPERSAMPLE = 2.0

    def __init__(self, R: float, rng: random.Random) -> None:
        """Work out the bitmap size from ``R``."""
        super().__init__(R, rng)
        px_per_r = R * self.SUPERSAMPLE
        self.img_w = int(math.ceil((self.X_RANGE[1] - self.X_RANGE[0]) * px_per_r))
        self.img_h = int(math.ceil((self.Y_RANGE[1] - self.Y_RANGE[0]) * px_per_r))
        self.image = QImage(self.img_w, self.img_h, QImage.Format.Format_ARGB32_Premultiplied)
        self.image.fill(0)
        self._rect = QRectF(self.X_RANGE[0] * R, self.Y_RANGE[0] * R,
                            (self.X_RANGE[1] - self.X_RANGE[0]) * R,
                            (self.Y_RANGE[1] - self.Y_RANGE[0]) * R)

    def paint(self, painter: QPainter, colors: FlameColors) -> None:
        """Blit the bitmap (colours were already baked in during ``step()``)."""
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
        painter.drawImage(self._rect, self.image)
        painter.restore()

    def _update_top_points(self, alpha: np.ndarray, step: int = 1) -> None:
        """Find the flame's top edge from an alpha array (rows top->bottom) for spark spawning.

        ``step`` = the array already holds only every ``step``-th pixel column (cheaper);
        otherwise every third solid column is used."""
        solid = alpha > 128
        has = solid.any(axis=0)
        cols = np.nonzero(has)[0]
        if step == 1:
            cols = cols[::TOP_POINT_STEP]
        if len(cols) == 0:
            self.top_points = []
            return
        rows = solid[:, cols].argmax(axis=0)
        scale = 1.0 / (self.R * self.SUPERSAMPLE)
        xs = (self.X_RANGE[0] + (cols * step + 0.5) * scale) * self.R
        ys = (self.Y_RANGE[0] + (rows + 0.5) * scale) * self.R
        top = int(np.argmin(ys))                 # first highest point, like min() would pick
        self.tip = (float(xs[top]), float(ys[top]))
        high = ys < -(BODY_CY + 0.4) * self.R
        self.top_points = list(zip(xs[high].tolist(), ys[high].tolist(), strict=True))


def make_flame_renderer(name: str, R: float, rng: random.Random) -> FlameRenderer:
    """Create the renderer called ``name``; falls back to ``metaball`` if it cannot start
    (for example no usable OpenGL driver for ``shader``, or missing clips for ``baked``)."""
    from overlay.fire_field import MetaballFlame

    if name == "shader":
        try:
            from overlay.flame_shader import ShaderFlame
            return ShaderFlame(R, rng)
        except Exception:  # noqa: BLE001 - any GL/driver failure means "use the fallback"
            log.exception("Shader flame unavailable, falling back to metaball")
    elif name == "baked":
        try:
            from overlay.flame_baked import BakedFlame
            return BakedFlame(R, rng)
        except Exception:  # noqa: BLE001 - missing/corrupt clips means "use the fallback"
            log.exception("Baked flame unavailable, falling back to metaball")
    elif name != "metaball":
        log.warning("Unknown flame renderer %r, using metaball", name)
    return MetaballFlame(R, rng)
