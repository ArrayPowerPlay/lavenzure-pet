"""Code-drawn flame-spirit character: all shapes, motion and expressions are generated every frame.

No image assets are needed. ``FlameCharacter`` is a plain model + renderer (not a widget), so the
same character can be drawn by the always-on-top overlay window, by the preview tool, or into an
offscreen QImage for snapshots.

Look (flat "sticker" fan-art style): a squat flame with a round bottom and pointed tongues on top,
drawn as three nested layers - red rim, orange band, big yellow body - with one dark maroon outline
around the whole silhouette. The face (white eyes with small dark pupils, red mouth) sits on the
yellow body, plus a couple of pale highlight dabs.

What makes it feel like a real fire:
- Every layer is ONE continuous outline (body + tongues share their valley points), so the shape
  never shows seams or broken edges however the tongues move.
- Tongue length and sway come from smooth Perlin noise sampled along the flame's width, so tongues
  next to each other move together while the whole flame never repeats a pattern. All three layers
  read the same noise field, so the inner colors lick upward together with the outer edge.
- Random "flare-ups": a spot of the flame suddenly shoots up and falls back, often tearing off a
  small flame wisp that floats away. Their rate grows with the mood (calm < talking < happy/alert).
- Spring physics driven by the window's own movement: it leans/trails against the direction of
  travel, stretches when moving fast vertically, squashes and wobbles on landings, hops while
  walking.
- Eyes that blink at random and follow the mouse cursor (or wander when it is idle), plus smooth
  cross-faded expressions (normal, happy, surprised, alert, thinking, talking).
- Sparks and wisps that drift upward in *screen* space, so they trail behind the pet as it moves.
"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass, fields
from enum import Enum, auto

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import (
    QBrush,
    QColor,
    QImage,
    QPainter,
    QPainterPath,
    QPen,
    QPolygonF,
    QRadialGradient,
)


class Mood(Enum):
    """Facial expression / energy level the character is showing."""

    NORMAL = auto()
    HAPPY = auto()
    SURPRISED = auto()
    ALERT = auto()
    THINKING = auto()
    TALKING = auto()


@dataclass(frozen=True)
class Palette:
    """RGB fill colors of the three flame layers plus the soft glow behind the body."""

    outer: tuple[int, int, int]  # red rim (outermost layer)
    mid: tuple[int, int, int]    # orange band
    inner: tuple[int, int, int]  # yellow body the face is drawn on
    glow: tuple[int, int, int]


CALM_PALETTE = Palette(outer=(234, 54, 48), mid=(248, 132, 38), inner=(255, 210, 30),
                       glow=(255, 150, 40))
ALERT_PALETTE = Palette(outer=(186, 20, 28), mid=(234, 60, 38), inner=(255, 150, 36),
                        glow=(255, 60, 36))

INK = QColor(104, 16, 16)            # dark maroon used for the outline and every face line
HIGHLIGHT = QColor(255, 248, 204)    # pale dabs of shine on the yellow body
EYE_WHITE = QColor(255, 253, 244)
PUPIL = QColor(72, 14, 12)
MOUTH = QColor(212, 38, 44)
TONGUE = QColor(246, 122, 106)


@dataclass
class Expression:
    """Continuous face/flame parameters; every mood is one target set, values blend smoothly."""

    eye_open: float = 1.0      # 0 = closed, 1 = fully open
    eye_scale: float = 1.0     # overall eye size
    pupil: float = 1.0         # pupil size relative to the eye
    happy_eyes: float = 0.0    # 1 = closed "^ ^" smiling eyes
    mouth_open: float = 0.0    # 0 = line, 1 = wide open
    smile: float = 0.55        # -1 = frown, 1 = big smile
    mouth_round: float = 0.0   # 1 = round "O" mouth
    angry: float = 0.0         # 1 = eyelids slanted down toward the nose (alarmed / cross look)
    flame: float = 1.0         # flame height multiplier
    flicker: float = 1.0       # flicker speed multiplier
    wild: float = 1.0          # flicker strength and how often the flame flares up
    alert: float = 0.0         # 0 = calm palette, 1 = alert palette
    shake: float = 0.0         # nervous horizontal jitter


_MOOD_TARGETS: dict[Mood, Expression] = {
    Mood.NORMAL: Expression(),
    Mood.HAPPY: Expression(happy_eyes=1.0, mouth_open=0.75, smile=1.0, flame=1.15, flicker=1.4,
                           wild=1.5),
    Mood.SURPRISED: Expression(eye_scale=1.22, pupil=0.62, mouth_open=0.5, smile=0.0,
                               mouth_round=1.0, flame=1.12, flicker=1.7, wild=1.6),
    Mood.ALERT: Expression(eye_scale=1.04, pupil=0.8, mouth_open=0.4, smile=-0.7, angry=1.0,
                           flame=1.12, flicker=2.0, wild=1.9, alert=1.0, shake=1.0),
    Mood.THINKING: Expression(eye_open=0.78, smile=0.1, flame=0.9, flicker=0.6, wild=0.55),
    Mood.TALKING: Expression(smile=0.6, flame=1.05, flicker=1.25, wild=1.15),
}


# ---------------------------------------------------------------------- small math helpers

def _lerp(a: float, b: float, t: float) -> float:
    """Linear interpolation between ``a`` and ``b``."""
    return a + (b - a) * t


def _mix(c1: tuple[int, int, int], c2: tuple[int, int, int], t: float, alpha: int = 255) -> QColor:
    """Blend two RGB tuples into a QColor."""
    return QColor(*(int(_lerp(a, b, t)) for a, b in zip(c1, c2)), alpha)


def _approach(current: float, target: float, rate: float, dt: float) -> float:
    """Frame-rate independent exponential smoothing of ``current`` toward ``target``."""
    return current + (target - current) * (1.0 - math.exp(-rate * dt))


def _clamp(value: float, low: float, high: float) -> float:
    """Clamp ``value`` into ``[low, high]``."""
    return max(low, min(high, value))


def _hash(i: int, seed: int) -> float:
    """Deterministic pseudo-random value in ``[-1, 1]`` for lattice point ``i`` of noise ``seed``."""
    h = (i * 0x27D4EB2D ^ seed * 0x165667B1) & 0xFFFFFFFF
    h = ((h ^ (h >> 15)) * 0x85EBCA6B) & 0xFFFFFFFF
    h = ((h ^ (h >> 13)) * 0xC2B2AE35) & 0xFFFFFFFF
    h ^= h >> 16
    return h / 0x7FFFFFFF - 1.0


def _noise(x: float, seed: int) -> float:
    """1D gradient (Perlin) noise: smooth, never repeating, roughly within ``[-1, 1]``."""
    i = math.floor(x)
    f = x - i
    u = f * f * f * (f * (f * 6.0 - 15.0) + 10.0)
    return 2.0 * _lerp(_hash(i, seed) * f, _hash(i + 1, seed) * (f - 1.0), u)


def _fbm(x: float, seed: int) -> float:
    """Two octaves of noise: a slow swell plus a faster, smaller flutter on top."""
    return (_noise(x, seed) + 0.5 * _noise(x * 2.13 + 7.7, seed + 911)) / 1.5


# ---------------------------------------------------------------------- data records

class _Spring:
    """Damped spring (semi-implicit Euler). Under-damped settings give a jelly-like wobble."""

    def __init__(self, value: float, stiffness: float, damping: float) -> None:
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


@dataclass
class _Ember:
    """One spark (``wisp=False``) or torn-off little flame (``wisp=True``), in widget coordinates."""

    x: float
    y: float
    vx: float
    vy: float
    life: float
    max_life: float
    size: float
    phase: float
    wisp: bool = False


@dataclass(frozen=True)
class _Layer:
    """Shape recipe for one flame layer. Lengths are in units of ``R``, heights measured up from
    the feet. Inner layers are smaller copies sitting slightly higher, with shorter tongues whose
    roots line up with the outer ones (so each color nests inside the tongue around it)."""

    color: str                  # Palette attribute name
    half_width: float           # widest half-width of the round, onion-shaped body
    bottom: float               # height of the lowest point
    side: float                 # height where the body side turns into the first tongue
    dome: float                 # how far the head arch rises above the sides
    roots: tuple[float, ...]    # tongue root x positions (units of R), left to right
    length: float               # length of the tallest tongue


_OUTER = _Layer("outer", 1.14, 0.00, 0.98, 0.50, (-0.80, -0.42, 0.02, 0.44, 0.82), 0.92)
_MID = _Layer("mid", 1.05, 0.065, 0.98, 0.42, (-0.72, -0.38, 0.02, 0.40, 0.74), 0.66)
_INNER = _Layer("inner", 0.95, 0.13, 0.94, 0.30, (-0.58, -0.19, 0.21, 0.60), 0.34)
_LAYERS = (_OUTER, _MID, _INNER)

_COLUMNS = 7                 # noise samples across the flame width (shared by all layers)
_FLARE_RISE = 0.08           # seconds for a flare-up to reach full height
_FLARE_FALL = 0.22           # decay time constant of a flare-up
_FLARE_RATE = 0.11           # flare-ups per second per column at wild = 1


class FlameCharacter:
    """Stateful flame spirit. Call ``update()`` once per frame, then ``paint()``.

    Coordinates are widget-local: the canvas is ``width`` x ``height`` pixels and the bottom of the
    body ("feet") sits at ``feet``. Mood is layered: persistent flags (alert, thinking) form the
    base, and short-lived moods from ``play()`` (happy, surprised, talking) override them.
    """

    BASE_RADIUS = 46.0
    MAX_EMBERS = 40

    def __init__(self, scale: float = 1.0, seed: int | None = None) -> None:
        self.scale = scale
        self.R = self.BASE_RADIUS * scale
        self.width = int(round(200 * scale))
        self.height = int(round(236 * scale))
        self.feet = QPointF(self.width / 2, self.height - 22 * scale)

        self._rng = random.Random(seed)
        self._seed = self._rng.randrange(1 << 20)  # different pets flicker differently
        self._t = 0.0

        # Mood layering
        self._alert = False
        self._thinking = False
        self._transient: Mood | None = None
        self._transient_until: float | None = None  # None = until stop_transient()
        self._expr = Expression()

        # Motion physics
        self._prev_window_pos: QPointF | None = None
        self._vx = 0.0
        self._vy = 0.0
        self._still_frames = 0
        self._squash = _Spring(1.0, stiffness=320.0, damping=13.0)
        self._lean = _Spring(0.0, stiffness=110.0, damping=10.0)
        self._hop_y = 0.0          # <= 0, pixels above the ground line
        self._hop_v = 0.0
        self._sx = self._sy = 1.0  # body squash/stretch for this frame
        self._shake_px = 0.0

        # Fire simulation: a noise "clock" that runs faster when the flame flickers faster (so a
        # speed change never makes the shapes jump), per-column noise samples and flare-ups.
        self._clock = self._rng.uniform(0.0, 1000.0)
        self._len_n = [0.0] * _COLUMNS
        self._sway_n = [0.0] * _COLUMNS
        self._root_n = [0.0] * _COLUMNS
        self._flare_age = [10.0] * _COLUMNS
        self._flare = [0.0] * _COLUMNS
        self._height_n = 0.0
        self._breath_n = 0.0
        self._paths: list[QPainterPath] = []
        self._tips: list[tuple[float, float]] = []  # outer-layer tongue tips (body coordinates)

        # Eyes
        self._next_blink = self._rng.uniform(1.5, 4.0)
        self._blink_start = -10.0
        self._look_x = 0.0
        self._look_y = 0.0
        self._last_cursor: QPointF | None = None
        self._cursor_still_since = 0.0
        self._wander_target = (0.0, 0.0)
        self._next_wander = 0.0

        # Talking mouth
        self._talk_amount = 0.0

        self._embers: list[_Ember] = []
        self._glow_cache: dict[bool, QImage] = {}
        self._ember_debt = 0.0

        self._update_fire(0.0)  # so paint() works even before the first update()

    # ------------------------------------------------------------------ public control API

    def set_alert(self, active: bool) -> None:
        """Turn the persistent alert look (red-hot, cross eyes, shaking) on or off."""
        self._alert = active

    def set_thinking(self, active: bool) -> None:
        """Turn the persistent thinking look (calm, eyes up, small flame) on or off."""
        self._thinking = active

    def play(self, mood: Mood, seconds: float | None) -> None:
        """Show a temporary ``mood`` for ``seconds`` (``None`` = until ``stop_transient()``)."""
        self._transient = mood
        self._transient_until = None if seconds is None else self._t + seconds
        if mood == Mood.HAPPY:
            self.bounce(1.0)
            self.burst(12)
        elif mood == Mood.SURPRISED:
            self._squash.velocity += 3.5
            self._flare_column(self._COLUMNS_CENTER)

    def stop_transient(self) -> None:
        """End any temporary mood and fall back to the base mood."""
        self._transient = None
        self._transient_until = None

    def anticipate(self) -> None:
        """Crouch (squash down) right before a jump, the classic animation anticipation pose."""
        self._squash.velocity -= 4.5

    def bounce(self, strength: float = 1.0) -> None:
        """Make the character hop up in place; landing produces a squash automatically."""
        if self._hop_y >= -0.5:
            self._hop_v = -260.0 * self.scale * strength

    def burst(self, count: int) -> None:
        """Throw out a handful of sparks and a few wisps at once (used for happy reactions)."""
        for _ in range(count):
            self._spawn_ember(speed_boost=1.8)
        for _ in range(max(1, count // 5)):
            self._spawn_ember(speed_boost=1.3, wisp=True)
        for k in (1, _COLUMNS - 2):
            self._flare_column(k)

    @property
    def mood(self) -> Mood:
        """The mood currently being shown (transient mood wins over base flags)."""
        if self._transient is not None:
            return self._transient
        if self._alert:
            return Mood.ALERT
        if self._thinking:
            return Mood.THINKING
        return Mood.NORMAL

    def head_top(self) -> QPointF:
        """Widget-local point just above the flame tips; used to anchor speech bubbles."""
        return QPointF(self.feet.x(), self.feet.y() - 3.2 * self.R)

    # ------------------------------------------------------------------ simulation

    _COLUMNS_CENTER = _COLUMNS // 2

    def update(self, dt: float, window_pos: QPointF | None, cursor: QPointF | None) -> None:
        """Advance the simulation by ``dt`` seconds.

        ``window_pos`` is the global top-left of the hosting window (used to derive velocity and
        to keep embers in screen space); ``cursor`` is the mouse position in widget-local
        coordinates, or ``None`` if unknown.
        """
        dt = _clamp(dt, 0.0, 0.05)
        if dt == 0.0:
            return
        self._t += dt

        if self._transient_until is not None and self._t >= self._transient_until:
            self.stop_transient()

        moved_x, moved_y = self._update_velocity(dt, window_pos)
        self._update_expression(dt)
        self._update_body(dt)
        self._update_eyes(dt, cursor)
        self._update_fire(dt)
        self._update_embers(dt, moved_x, moved_y)

    def _update_velocity(self, dt: float, window_pos: QPointF | None) -> tuple[float, float]:
        """Estimate window velocity (smoothed) and return this frame's raw window displacement."""
        moved_x = moved_y = 0.0
        if window_pos is not None:
            if self._prev_window_pos is not None:
                moved_x = window_pos.x() - self._prev_window_pos.x()
                moved_y = window_pos.y() - self._prev_window_pos.y()
            self._prev_window_pos = QPointF(window_pos)
        smoothing = 1.0 - math.exp(-14.0 * dt)
        self._vx += (moved_x / dt - self._vx) * smoothing
        self._vy += (moved_y / dt - self._vy) * smoothing
        # Landing: was falling fast and the window has now stopped for two frames in a row
        # (two, because a single frame without movement can happen mid-flight).
        self._still_frames = self._still_frames + 1 if abs(moved_y) < 1.0 else 0
        if self._still_frames == 2 and self._vy > 200.0:
            self._squash.velocity -= _clamp(self._vy / 90.0, 2.5, 7.0)
            self._vy = 0.0
        return moved_x, moved_y

    def _update_expression(self, dt: float) -> None:
        """Blend every expression parameter toward the current mood's target values."""
        target = _MOOD_TARGETS[self.mood]
        for f in fields(Expression):
            current = getattr(self._expr, f.name)
            setattr(self._expr, f.name, _approach(current, getattr(target, f.name), 9.0, dt))

        talking = self.mood == Mood.TALKING
        if talking:
            # Irregular "syllables": fast open/close modulated by a slower phrase rhythm.
            syllable = abs(math.sin(self._t * 11.0)) * (0.55 + 0.45 * math.sin(self._t * 3.3))
            want = 0.12 + 0.7 * max(0.0, syllable)
        else:
            want = 0.0
        self._talk_amount = _approach(self._talk_amount, want, 25.0, dt)

    def _update_body(self, dt: float) -> None:
        """Springs for squash/stretch and lean, plus the hop (small jump) physics."""
        speed_x = abs(self._vx)
        stretch = _clamp(abs(self._vy) / 1100.0, 0.0, 0.2)
        self._squash.step(1.0 + stretch, dt)
        self._lean.step(_clamp(-self._vx / 520.0, -0.5, 0.5), dt)

        # Walking along the ground (horizontal motion, little vertical) -> keep hopping.
        walking = speed_x > 30.0 and abs(self._vy) < 40.0
        if walking and self._hop_y >= -0.5 and self._hop_v >= 0.0:
            self._hop_v = -_clamp(speed_x * 1.6, 110.0, 170.0) * self.scale

        gravity = 1500.0 * self.scale
        if self._hop_y < 0.0 or self._hop_v < 0.0:
            self._hop_v += gravity * dt
            self._hop_y += self._hop_v * dt
            if self._hop_y >= 0.0:
                self._hop_y = 0.0
                self._squash.velocity -= _clamp(self._hop_v / (90.0 * self.scale), 0.5, 4.0)
                self._hop_v = 0.0

        # Overall squash/stretch: spring + slow uneven "breathing" from the fire noise.
        ex = self._expr
        breathe = 0.02 * self._breath_n
        self._sy = max(0.6, self._squash.value + breathe)
        self._sx = 1.0 + (1.0 - self._sy) * 0.85  # keep the volume roughly constant
        self._shake_px = ex.shake * _noise(self._t * 40.0, self._seed + 77) * 2.2 * self.scale

    def _update_eyes(self, dt: float, cursor: QPointF | None) -> None:
        """Blink timing and gaze direction (cursor tracking, idle wandering, thinking glance)."""
        if self._t >= self._next_blink:
            self._blink_start = self._t
            double = self._rng.random() < 0.18
            self._next_blink = self._t + (0.3 if double else self._rng.uniform(2.2, 5.5))

        eye_center = QPointF(self.feet.x(), self.feet.y() - 1.0 * self.R)
        target_x, target_y = 0.0, 0.0
        if self.mood == Mood.THINKING:
            target_x, target_y = 0.6, -0.8
        elif cursor is not None:
            if self._last_cursor is None or (cursor - self._last_cursor).manhattanLength() > 2:
                self._cursor_still_since = self._t
                self._last_cursor = QPointF(cursor)
            if self._t - self._cursor_still_since < 4.0:
                dx = cursor.x() - eye_center.x()
                dy = cursor.y() - eye_center.y()
                dist = math.hypot(dx, dy) or 1.0
                reach = min(1.0, dist / (220.0 * self.scale))
                target_x, target_y = dx / dist * reach, dy / dist * reach
            else:
                if self._t >= self._next_wander:
                    angle = self._rng.uniform(0, math.tau)
                    radius = self._rng.choice((0.0, 0.0, self._rng.uniform(0.3, 0.8)))
                    self._wander_target = (math.cos(angle) * radius, math.sin(angle) * radius * 0.6)
                    self._next_wander = self._t + self._rng.uniform(1.5, 3.5)
                target_x, target_y = self._wander_target
        self._look_x = _approach(self._look_x, target_x, 10.0, dt)
        self._look_y = _approach(self._look_y, target_y, 10.0, dt)

    def _flare_column(self, k: int) -> None:
        """Start a flare-up (the flame shoots up there and falls back) at noise column ``k``."""
        if self._flare_age[k] > _FLARE_RISE:
            self._flare_age[k] = 0.0

    def _update_fire(self, dt: float) -> None:
        """Advance the fire noise and flare-ups, then rebuild the three layer outlines."""
        ex = self._expr
        self._clock += dt * ex.flicker
        c = self._clock
        s = self._seed

        wisp_columns = []
        for k in range(_COLUMNS):
            self._len_n[k] = _fbm(c * 1.7 + k * 3.7, s + 100 + k)
            self._sway_n[k] = _fbm(c * 0.9 + k * 5.1, s + 200 + k)
            self._root_n[k] = _noise(c * 0.35 + k * 7.3, s + 400 + k)
            age = self._flare_age[k]
            if age > 0.7 and self._rng.random() < _FLARE_RATE * ex.wild * ex.wild * dt:
                age = 0.0
            new_age = age + dt
            if age < _FLARE_RISE <= new_age and self._rng.random() < 0.6:
                wisp_columns.append(k)  # the tip tears off at the peak of the flare
            self._flare_age[k] = new_age
            if new_age < _FLARE_RISE:
                self._flare[k] = new_age / _FLARE_RISE
            else:
                self._flare[k] = math.exp(-(new_age - _FLARE_RISE) / _FLARE_FALL)
        self._height_n = _fbm(c * 0.55, s + 300)
        self._breath_n = _fbm(c * 0.4, s + 301)

        self._paths = []
        for layer in _LAYERS:
            path, tips = self._layer_path(layer)
            self._paths.append(path)
            if layer is _OUTER:
                self._tips = tips

        for k in wisp_columns:
            self._spawn_wisp_from_column(k)

    def _field(self, values: list[float], x: float) -> float:
        """Smoothly interpolate per-column samples at body x-coordinate ``x``."""
        pos = _clamp((x / (_OUTER.half_width * self.R) + 1.0) * 0.5, 0.0, 1.0) * (_COLUMNS - 1)
        i = min(int(pos), _COLUMNS - 2)
        f = pos - i
        f = f * f * (3.0 - 2.0 * f)
        return _lerp(values[i], values[i + 1], f)

    def _layer_path(self, layer: _Layer) -> tuple[QPainterPath, list[tuple[float, float]]]:
        """Build one layer as a single closed outline: tongues left to right, then the round bottom.

        Neighbouring tongues share their valley point, and the outermost tongues grow out of the
        body sides along the tangent the bottom curve ends with, so the outline is smooth and
        unbroken everywhere. Returns the path (body coordinates: origin at the feet, y up is
        negative) and the tongue tip positions.
        """
        r = self.R
        ex = self._expr
        a = layer.half_width * r * (1.0 + 0.025 * self._breath_n)
        y_bottom = -layer.bottom * r
        y_side = -layer.side * r
        xs = 0.88 * a                      # side point: where the body side meets the first tongue
        bulge = (1.07 * a, y_side + 0.55 * (y_bottom - y_side))  # widest, low part of the body
        dome = layer.dome * r
        lean = self._lean.value
        height = ex.flame * (1.0 + 0.09 * ex.wild * self._height_n)

        def arch_y(x: float) -> float:
            """Height of the head arch (where tongues are rooted) at ``x``."""
            return y_side - dome * math.sqrt(max(0.0, 1.0 - (x / xs) ** 2))

        n = len(layer.roots)
        roots = [_clamp(u * r + 0.08 * r * self._field(self._root_n, u * r), -0.95 * xs, 0.95 * xs)
                 for u in layer.roots]
        valley_x = [-xs] + [(roots[i] + roots[i + 1]) / 2 for i in range(n - 1)] + [xs]
        valleys = []
        for j, x in enumerate(valley_x):
            sink = 0.0 if j in (0, n) else 0.05 * r  # V-notches dip a little below the arch
            valleys.append((x, arch_y(x) + sink))


        path = QPainterPath()
        path.setFillRule(Qt.FillRule.WindingFill)
        path.moveTo(*valleys[0])
        tips = []
        for i, bx in enumerate(roots):
            u = bx / xs
            by = arch_y(bx)
            length = layer.length * r * (1.0 - 0.5 * abs(u) ** 1.5) * height
            length *= max(0.25, 1.0 + 0.32 * ex.wild * self._field(self._len_n, bx)
                          + 0.6 * self._field(self._flare, bx))
            sway = r * 0.17 * math.sqrt(ex.wild) * self._field(self._sway_n, bx)
            tip_x = bx + u * 0.2 * length + sway + lean * length * 0.85
            tip_y = by - length
            curl = sway * 0.9 + lean * length * 0.25  # tips hook the way they sway
            tips.append((tip_x, tip_y))

            (xl, yl), (xr, yr) = valleys[i], valleys[i + 1]
            wl, wr = bx - xl, xr - bx
            rise = length * 0.3
            # Outermost edges continue the bottom curve's tangent (up and inward, so the body
            # narrows like a teardrop); inner edges fan up out of their notch.
            q = rise / (bulge[1] - y_side)
            c1 = QPointF(xl + (bulge[0] - xs) * q if i == 0 else xl + wl * 0.15, yl - rise)
            c2 = QPointF(xr - (bulge[0] - xs) * q if i == n - 1 else xr - wr * 0.15, yr - rise)
            # Side tongues are lopsided like real licks of flame: the edge facing away from the
            # centre bulges out, the edge facing the centre is drawn in.
            left_bulge = 0.95 - 0.45 * u
            right_bulge = 0.95 + 0.45 * u
            path.cubicTo(c1, QPointF(tip_x - wl * left_bulge + curl, tip_y + length * 0.6),
                         QPointF(tip_x, tip_y))
            path.cubicTo(QPointF(tip_x + wr * right_bulge + curl, tip_y + length * 0.6), c2,
                         QPointF(xr, yr))

        # Round, onion-like bottom: right side -> bottom centre -> left side.
        path.cubicTo(QPointF(*bulge), QPointF(0.72 * a, y_bottom), QPointF(0.0, y_bottom))
        path.cubicTo(QPointF(-0.72 * a, y_bottom), QPointF(-bulge[0], bulge[1]),
                     QPointF(-xs, y_side))
        path.closeSubpath()
        return path, tips

    def _to_widget(self, x: float, y: float) -> tuple[float, float]:
        """Map a body-coordinate point to widget coordinates (same transform as ``paint``)."""
        shear = -self._lean.value * 0.22
        return (self.feet.x() + self._shake_px + self._sx * (x + shear * y),
                self.feet.y() + self._hop_y + self._sy * y)

    def _update_embers(self, dt: float, moved_x: float, moved_y: float) -> None:
        """Spawn, move and retire sparks and wisps (kept in screen space)."""
        mood = self.mood
        rate = {Mood.ALERT: 8.0, Mood.HAPPY: 7.0, Mood.SURPRISED: 5.0, Mood.THINKING: 1.2}.get(
            mood, 2.5
        )
        self._ember_debt += rate * dt
        while self._ember_debt >= 1.0:
            self._ember_debt -= 1.0
            self._spawn_ember()

        alive: list[_Ember] = []
        for e in self._embers:
            e.life -= dt
            if e.life <= 0.0:
                continue
            wobble = 14.0 if not e.wisp else 22.0
            e.x += (e.vx + math.sin(self._t * 3.0 + e.phase) * wobble * self.scale) * dt - moved_x
            e.y += e.vy * dt - moved_y
            e.vy *= 1.0 - (0.6 if not e.wisp else 0.9) * dt
            if -10 < e.x < self.width + 10 and -10 < e.y < self.height + 10:
                alive.append(e)
        self._embers = alive

    def _spawn_ember(self, speed_boost: float = 1.0, wisp: bool = False) -> None:
        """Create one spark (or wisp) at a random tongue tip of the outer layer."""
        if len(self._embers) >= self.MAX_EMBERS or not self._tips:
            return
        rng = self._rng
        tx, ty = rng.choice(self._tips)
        x, y = self._to_widget(tx + rng.uniform(-0.12, 0.12) * self.R, ty + 0.15 * self.R)
        self._add_ember(x, y, speed_boost, wisp)

    def _spawn_wisp_from_column(self, k: int) -> None:
        """Tear a small flame off the tongue tip closest to noise column ``k``."""
        if not self._tips:
            return
        cx = (k / (_COLUMNS - 1) * 2.0 - 1.0) * _OUTER.half_width * self.R
        tx, ty = min(self._tips, key=lambda tip: abs(tip[0] - cx))
        x, y = self._to_widget(tx, ty)
        self._add_ember(x, y, 1.0, wisp=True)

    def _add_ember(self, x: float, y: float, speed_boost: float, wisp: bool) -> None:
        """Append one particle at widget position (``x``, ``y``) with randomized motion."""
        if len(self._embers) >= self.MAX_EMBERS:
            return
        rng = self._rng
        life = rng.uniform(0.55, 0.95) if wisp else rng.uniform(0.7, 1.5)
        size = (rng.uniform(0.09, 0.14) * self.R) if wisp else rng.uniform(1.3, 2.6) * self.scale
        self._embers.append(
            _Ember(
                x=x, y=y,
                vx=rng.uniform(-14, 14) * self.scale * speed_boost - self._vx * 0.12,
                vy=-rng.uniform(55, 95) * self.scale * speed_boost,
                life=life, max_life=life, size=size, phase=rng.uniform(0, math.tau), wisp=wisp,
            )
        )

    # ------------------------------------------------------------------ rendering

    def paint(self, painter: QPainter) -> None:
        """Draw the whole character (glow, flame layers, face, sparks and wisps) with ``painter``."""
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        painter.save()
        painter.translate(self.feet.x() + self._shake_px, self.feet.y() + self._hop_y)
        painter.scale(self._sx, self._sy)
        painter.shear(-self._lean.value * 0.22, 0.0)  # top of the body leans, feet stay put
        self._paint_glow(painter)
        self._paint_flame(painter)
        self._paint_face(painter)
        painter.restore()

        self._paint_embers(painter)

    def _palette_color(self, layer: str, alpha: int = 255) -> QColor:
        """Current color of a flame layer, blended between the calm and alert palettes."""
        return _mix(getattr(CALM_PALETTE, layer), getattr(ALERT_PALETTE, layer), self._expr.alert,
                    alpha)

    def _glow_image(self, alert: bool) -> QImage:
        """Pre-rendered soft halo (one per palette). Drawing a cached image is far cheaper than
        filling a big radial gradient every frame."""
        cache = self._glow_cache
        if alert not in cache:
            size = int(math.ceil(3.6 * self.R)) + 2
            image = QImage(size, size, QImage.Format.Format_ARGB32_Premultiplied)
            image.fill(Qt.GlobalColor.transparent)
            grad = QRadialGradient(QPointF(size / 2, size / 2), size / 2 - 1)
            rgb = (ALERT_PALETTE if alert else CALM_PALETTE).glow
            for stop, alpha in ((0.0, 80), (0.45, 36), (0.75, 10), (1.0, 0)):
                grad.setColorAt(stop, QColor(*rgb, alpha))
            p = QPainter(image)
            p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QBrush(grad))
            p.drawEllipse(QRectF(0, 0, size, size))
            p.end()
            cache[alert] = image
        return cache[alert]

    def _paint_glow(self, painter: QPainter) -> None:
        """Soft warm halo behind the body that pulses with the fire; it fades to fully transparent
        at its edge (so clicks there still pass through to the desktop)."""
        r = self.R
        ex = self._expr
        pulse = 0.8 + 0.2 * self._height_n
        radius = 1.7 * r * ex.flame
        target = QRectF(-radius, -1.1 * r - radius, radius * 2, radius * 2)
        painter.save()
        for alert, weight in ((False, 1.0 - ex.alert), (True, ex.alert)):
            if weight > 0.01:
                painter.setOpacity(pulse * weight)
                painter.drawImage(target, self._glow_image(alert))
        painter.restore()

    def _paint_flame(self, painter: QPainter) -> None:
        """Red rim with the dark outline, then the orange band and the yellow body, then shine."""
        r = self.R
        outer, mid, inner = self._paths
        painter.setPen(QPen(INK, 0.065 * r, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap,
                            Qt.PenJoinStyle.RoundJoin))
        painter.setBrush(self._palette_color("outer"))
        painter.drawPath(outer)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(self._palette_color("mid"))
        painter.drawPath(mid)
        painter.setBrush(self._palette_color("inner"))
        painter.drawPath(inner)

        # Pale shine dabs on the left of the yellow body (flat sticker style).
        painter.setBrush(HIGHLIGHT)
        painter.save()
        painter.translate(-0.74 * r, -0.5 * r)
        painter.rotate(14.0)
        painter.drawEllipse(QPointF(0.0, 0.0), 0.045 * r, 0.1 * r)
        painter.restore()
        painter.drawEllipse(QPointF(-0.72 * r, -0.74 * r), 0.032 * r, 0.032 * r)

    def _paint_face(self, painter: QPainter) -> None:
        """Eyes and mouth; the face shifts slightly toward the gaze for depth."""
        r = self.R
        painter.save()
        painter.translate(self._look_x * 0.07 * r, -1.02 * r + self._look_y * 0.05 * r)
        for side in (-1, 1):
            self._paint_eye(painter, QPointF(side * 0.44 * r, 0.0), side)
        self._paint_mouth(painter, QPointF(0.0, 0.42 * r))
        painter.restore()

    def _blink_factor(self) -> float:
        """1 when the eyes are open, dips to 0 during a blink."""
        phase = (self._t - self._blink_start) / 0.15
        if 0.0 <= phase <= 1.0:
            return 1.0 - math.sin(math.pi * phase)
        return 1.0

    def _paint_eye(self, painter: QPainter, center: QPointF, side: int) -> None:
        """One eye: outlined white with a small tracking pupil (cut by slanted lids when angry),
        or a happy "^" arc, or a closed line while blinking."""
        r = self.R
        ex = self._expr
        rx = 0.23 * r * ex.eye_scale
        ry_full = 0.22 * r * ex.eye_scale
        openness = _clamp(ex.eye_open * self._blink_factor(), 0.0, 1.0)
        line_pen = QPen(INK, 0.07 * r, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)

        normal_alpha = 1.0 - ex.happy_eyes
        if normal_alpha > 0.01:
            painter.save()
            painter.setOpacity(normal_alpha)
            if openness > 0.12:
                ry = ry_full * openness
                cx, cy = center.x(), center.y() + ry_full * (1.0 - openness) * 0.5
                eye = QPainterPath()
                eye.addEllipse(QPointF(cx, cy), rx, ry)
                lid = None
                if ex.angry > 0.01:
                    # Cut the top of the eye with a line that drops toward the nose.
                    inner_x, outer_x = cx - side * rx * 1.3, cx + side * rx * 1.3
                    inner_y = cy - ry + ry * 1.0 * ex.angry
                    outer_y = cy - ry + ry * 0.1 * ex.angry
                    lid = (QPointF(inner_x, inner_y), QPointF(outer_x, outer_y))
                    cut = QPainterPath()
                    cut.addPolygon(QPolygonF([lid[0], lid[1], QPointF(outer_x, cy - 3 * ry),
                                              QPointF(inner_x, cy - 3 * ry)]))
                    cut.closeSubpath()
                    eye = eye.subtracted(cut)
                painter.setPen(QPen(INK, 0.05 * r, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap,
                                    Qt.PenJoinStyle.RoundJoin))
                painter.setBrush(EYE_WHITE)
                painter.drawPath(eye)

                painter.save()
                painter.setClipPath(eye)
                painter.setPen(Qt.PenStyle.NoPen)
                px = cx + self._look_x * rx * 0.45
                py = cy + self._look_y * ry * 0.4 + (ry * 0.25 * ex.angry)
                pr = rx * 0.4 * ex.pupil
                painter.setBrush(PUPIL)
                painter.drawEllipse(QPointF(px, py), pr, pr * max(0.6, openness))
                painter.setBrush(QColor(255, 255, 255, 235))
                painter.drawEllipse(QPointF(px - pr * 0.35, py - pr * 0.38), pr * 0.32, pr * 0.32)
                painter.restore()

                if lid is not None:
                    painter.setOpacity(normal_alpha * ex.angry)
                    painter.setPen(QPen(INK, 0.075 * r, Qt.PenStyle.SolidLine,
                                        Qt.PenCapStyle.RoundCap))
                    a, b = lid
                    painter.drawLine(QPointF(_lerp(a.x(), b.x(), 0.12), _lerp(a.y(), b.y(), 0.12)),
                                     QPointF(_lerp(a.x(), b.x(), 0.95), _lerp(a.y(), b.y(), 0.95)))
            else:
                closed = QPainterPath(QPointF(center.x() - rx, center.y()))
                closed.quadTo(QPointF(center.x(), center.y() + ry_full * 0.45),
                              QPointF(center.x() + rx, center.y()))
                painter.setPen(line_pen)
                painter.setBrush(Qt.BrushStyle.NoBrush)
                painter.drawPath(closed)
            painter.restore()

        if ex.happy_eyes > 0.01:
            painter.save()
            painter.setOpacity(ex.happy_eyes)
            arc = QPainterPath(QPointF(center.x() - rx, center.y() + ry_full * 0.3))
            arc.quadTo(QPointF(center.x(), center.y() - ry_full * 0.9),
                       QPointF(center.x() + rx, center.y() + ry_full * 0.3))
            painter.setPen(line_pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawPath(arc)
            painter.restore()

    def _paint_mouth(self, painter: QPainter, center: QPointF) -> None:
        """Mouth: a curved line / open smile-or-frown shape, cross-faded with a round 'O' mouth."""
        r = self.R
        ex = self._expr
        open_amount = _clamp(ex.mouth_open + self._talk_amount, 0.0, 1.2)
        smile = ex.smile
        w = 0.24 * r * (1.0 + 0.25 * max(smile, 0.0))
        mx, my = center.x(), center.y()
        corner_y = my - smile * 0.3 * w
        ink_pen = QPen(INK, 0.05 * r, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap,
                       Qt.PenJoinStyle.RoundJoin)

        curve_alpha = 1.0 - ex.mouth_round
        if curve_alpha > 0.01:
            painter.save()
            painter.setOpacity(curve_alpha)
            if open_amount < 0.06:
                line = QPainterPath(QPointF(mx - w, corner_y))
                line.quadTo(QPointF(mx, my + smile * 0.55 * w), QPointF(mx + w, corner_y))
                painter.setPen(QPen(INK, 0.06 * r, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
                painter.setBrush(Qt.BrushStyle.NoBrush)
                painter.drawPath(line)
            else:
                top_ctrl = my + smile * 0.2 * w - 0.08 * w
                bottom_ctrl = top_ctrl + open_amount * 1.6 * w + max(smile, 0.0) * 0.35 * w
                mouth = QPainterPath(QPointF(mx - w, corner_y))
                mouth.quadTo(QPointF(mx, top_ctrl), QPointF(mx + w, corner_y))
                mouth.cubicTo(QPointF(mx + w * 0.9, bottom_ctrl), QPointF(mx - w * 0.9, bottom_ctrl),
                              QPointF(mx - w, corner_y))
                mouth.closeSubpath()
                painter.setPen(ink_pen)
                painter.setBrush(MOUTH)
                painter.drawPath(mouth)
                if open_amount > 0.25:
                    tongue_y = bottom_ctrl - open_amount * 0.2 * w
                    tongue = QPainterPath()
                    tongue.addEllipse(QPointF(mx, tongue_y), w * 0.62, w * 0.42)
                    painter.save()
                    painter.setClipPath(mouth)
                    painter.setPen(Qt.PenStyle.NoPen)
                    painter.setBrush(TONGUE)
                    painter.drawPath(tongue)
                    painter.restore()
                    painter.setPen(ink_pen)
                    painter.setBrush(Qt.BrushStyle.NoBrush)
                    painter.drawPath(mouth)
            painter.restore()

        if ex.mouth_round > 0.01:
            painter.save()
            painter.setOpacity(ex.mouth_round)
            size = 0.7 + 0.6 * open_amount
            painter.setPen(ink_pen)
            painter.setBrush(MOUTH)
            painter.drawEllipse(QPointF(mx, my + 0.06 * r), 0.13 * r * size, 0.16 * r * size)
            painter.restore()

    def _paint_embers(self, painter: QPainter) -> None:
        """Sparks are glowing dots; wisps are little teardrop flames that shrink as they rise."""
        painter.setPen(Qt.PenStyle.NoPen)
        alert = self._expr.alert
        for e in self._embers:
            k = e.life / e.max_life  # 1 = newborn, 0 = dying
            if not e.wisp:
                color = _mix((255, 120, 40), (255, 230, 140), k, int(230 * min(1.0, k * 2.0)))
                painter.setBrush(color)
                size = e.size * (0.5 + 0.5 * k)
                painter.drawEllipse(QRectF(e.x - size, e.y - size, size * 2, size * 2))
                continue

            s = e.size * (0.35 + 0.65 * k)
            painter.save()
            painter.translate(e.x, e.y)
            painter.rotate(math.degrees(math.atan2(e.vx, -e.vy)) * 0.6
                           + 12.0 * math.sin(self._t * 9.0 + e.phase))
            painter.setOpacity(min(1.0, k * 2.5))
            drop = self._teardrop(s)
            painter.setPen(QPen(INK, max(0.8, 0.05 * self.R * k), Qt.PenStyle.SolidLine,
                                Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
            painter.setBrush(self._palette_color("outer"))
            painter.drawPath(drop)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(_mix(CALM_PALETTE.mid, ALERT_PALETTE.mid, alert))
            painter.translate(0.0, s * 0.3)
            painter.drawPath(self._teardrop(s * 0.55))
            painter.restore()
        painter.setOpacity(1.0)

    @staticmethod
    def _teardrop(s: float) -> QPainterPath:
        """Upward-pointing teardrop: round bottom of radius ``s`` centred on the origin."""
        path = QPainterPath(QPointF(0.0, -2.3 * s))
        path.cubicTo(QPointF(0.25 * s, -1.4 * s), QPointF(s, -0.8 * s), QPointF(s, 0.0))
        path.arcTo(QRectF(-s, -s, 2 * s, 2 * s), 0.0, -180.0)
        path.cubicTo(QPointF(-s, -0.8 * s), QPointF(-0.25 * s, -1.4 * s), QPointF(0.0, -2.3 * s))
        path.closeSubpath()
        return path
