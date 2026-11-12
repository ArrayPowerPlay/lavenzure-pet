"""Code-drawn flame-spirit character: all shapes, motion and expressions are generated every frame.

No image assets are needed. ``FlameCharacter`` is a plain model + renderer (not a widget), so the
same character can be drawn by the always-on-top overlay window, by the preview tool, or into an
offscreen QImage for snapshots.

Look (flat "sticker" fan-art style): a squat flame with a round bottom and pointed tongues on top,
drawn as three nested layers - red rim, orange band, big yellow body - with one dark maroon outline
around the whole silhouette. The face (white eyes with small dark pupils, red mouth) sits on the
yellow body, plus a couple of pale highlight dabs.

What makes it feel like a real fire:
- The flame shape comes from ``overlay.fire_field.FireField``: a little particle simulation of
  flame "tongues" that are born on the body, rise, bend in the wind, merge with each other, pinch
  off and fade. The three colored layers are contour lines of that one soft field, so they are
  always smooth closed outlines (no seams), nest inside each other, and nothing is pinned in place.
- Flicker speed/strength and the flare-up rate follow the mood; moving the window blows the
  tongues backwards like wind.
- Spring physics driven by the window's own movement: it leans/trails against the direction of
  travel, stretches when moving fast vertically, squashes and wobbles on landings, hops while
  walking.
- Eyes that blink at random (fast close, slower open), dart to new spots like real eyes (saccades)
  and follow the mouse cursor. Expressions blend with a little springy overshoot so faces "pop"
  (normal, happy, surprised, alert, thinking, talking); talking uses an irregular, noise-driven
  mouth with pauses between phrases.
- Sparks that drift upward in *screen* space, so they trail behind the pet as it moves. (Torn-off
  bits of flame come from the fire simulation itself.)
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

from overlay.fire_field import FireField


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


CALM_PALETTE = Palette(outer=(236, 56, 58), mid=(247, 138, 52), inner=(252, 212, 34),
                       glow=(255, 150, 40))
ALERT_PALETTE = Palette(outer=(190, 22, 34), mid=(236, 70, 44), inner=(255, 160, 40),
                        glow=(255, 60, 36))

INK = QColor(108, 14, 22)            # dark maroon used for the outline and every face line
HIGHLIGHT = QColor(255, 234, 168)    # pale dabs of shine on the right flank
EYE_WHITE = QColor(255, 253, 244)
PUPIL = QColor(118, 12, 24)
MOUTH = QColor(206, 30, 42)
TONGUE = QColor(244, 112, 112)


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


def _smoothstep(edge0: float, edge1: float, x: float) -> float:
    """0 below ``edge0``, 1 above ``edge1``, smooth S-curve in between."""
    t = _clamp((x - edge0) / (edge1 - edge0), 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


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
    """One spark, in widget coordinates."""

    x: float
    y: float
    vx: float
    vy: float
    life: float
    max_life: float
    size: float
    phase: float


_FLARE_RATE = 0.45                  # spontaneous flare-ups per second at wild = 1
# Face parameters that blend with a slightly under-damped spring (a little overshoot = "pop");
# every other Expression field eases in smoothly.
_SPRUNG_FIELDS = frozenset({"eye_scale", "pupil", "mouth_open", "smile"})
_FACE_STIFFNESS = 260.0
_FACE_DAMPING = 22.0
# Fields that switch between two different drawings (curved/round mouth, open/"^" eyes) are
# cross-faded quickly so the two shapes are never seen as a ghostly double for long.
_FAST_FIELDS = frozenset({"mouth_round", "happy_eyes"})


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
        self._expr_vel: dict[str, float] = {name: 0.0 for name in _SPRUNG_FIELDS}

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

        # Fire simulation. ``_clock`` runs faster when the flame flickers faster (so a speed
        # change never makes the shapes jump). The shape itself comes from ``FireField``.
        self._clock = self._rng.uniform(0.0, 1000.0)
        self._height_n = 0.0
        self._breath_n = 0.0
        self._fire = FireField(self.R, self._rng)
        self._paths: list[QPainterPath] = []
        self._tip_point = (0.0, -2.6 * self.R)             # outer main tip (body coordinates)
        self._top_points: list[tuple[float, float]] = []  # outer outline near the top

        # Eyes
        self._next_blink = self._rng.uniform(1.5, 4.0)
        self._blink_start = -10.0
        self._look_x = 0.0
        self._look_y = 0.0
        self._last_cursor: QPointF | None = None
        self._cursor_still_since = 0.0
        self._wander_target = (0.0, 0.0)
        self._next_wander = 0.0
        self._micro = (0.0, 0.0)       # tiny fixation jitter added to the gaze
        self._next_micro = 0.0
        self._saccade = False          # True while the eyes are darting to a far target

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
            self._expr_vel["eye_scale"] += 9.0  # eyes pop open past their size, then settle
            self._start_flare()

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
        """Throw out a handful of sparks and flare up (used for happy reactions)."""
        for _ in range(count):
            self._spawn_ember(speed_boost=1.8)
        self._start_flare()

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
            name = f.name
            current = getattr(self._expr, name)
            goal = getattr(target, name)
            if name in _SPRUNG_FIELDS:
                vel = self._expr_vel[name]
                vel += (_FACE_STIFFNESS * (goal - current) - _FACE_DAMPING * vel) * dt
                self._expr_vel[name] = vel
                setattr(self._expr, name, current + vel * dt)
            else:
                rate = 22.0 if name in _FAST_FIELDS else 9.0
                setattr(self._expr, name, _approach(current, goal, rate, dt))

        if self.mood == Mood.TALKING:
            # Irregular "syllables" from noise, gated by a slower noise so phrases have pauses.
            syllable = _clamp(0.5 + 1.2 * _noise(self._t * 7.0, self._seed + 501), 0.0, 1.0)
            phrase = _smoothstep(-0.3, 0.05, _noise(self._t * 0.9, self._seed + 502))
            want = (0.1 + 0.7 * syllable) * phrase
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

        if self._t >= self._next_micro:
            # Real eyes never hold perfectly still: tiny jumps around the fixation point.
            self._micro = (self._rng.uniform(-0.07, 0.07), self._rng.uniform(-0.05, 0.05))
            self._next_micro = self._t + self._rng.uniform(0.35, 1.1)

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
                    radius = self._rng.choice((0.0, 0.0, self._rng.uniform(0.3, 0.9)))
                    self._wander_target = (math.cos(angle) * radius, math.sin(angle) * radius * 0.6)
                    self._next_wander = self._t + self._rng.uniform(1.2, 3.5)
                    recently_blinked = self._t - self._blink_start < 1.0
                    if radius > 0.5 and not recently_blinked and self._rng.random() < 0.3:
                        self._blink_start = self._t  # people often blink with a big glance
                target_x, target_y = self._wander_target
        target_x += self._micro[0]
        target_y += self._micro[1]
        # Saccade: a far target is reached with one quick dart; near ones are followed smoothly.
        gap = math.hypot(target_x - self._look_x, target_y - self._look_y)
        if gap > 0.25:
            self._saccade = True
        elif gap < 0.03:
            self._saccade = False
        rate = 32.0 if self._saccade else 12.0
        self._look_x = _approach(self._look_x, target_x, rate, dt)
        self._look_y = _approach(self._look_y, target_y, rate, dt)

    def _start_flare(self) -> None:
        """Make the fire flare up: a couple of big tongues shoot up through the main tip."""
        self._fire.flare(1.0)

    def _update_fire(self, dt: float) -> None:
        """Advance the fire noise, flare-ups and tongues, then pick up the new layer outlines."""
        ex = self._expr
        self._clock += dt * ex.flicker
        c = self._clock
        s = self._seed
        if self._rng.random() < _FLARE_RATE * ex.wild * ex.wild * dt:
            self._start_flare()
        self._height_n = _fbm(c * 0.55, s + 300)
        self._breath_n = _fbm(c * 0.4, s + 301)
        sway = 0.22 * math.sqrt(ex.wild) * _fbm(c * 0.75, s + 303) + 0.9 * self._lean.value
        # Apparent wind from the pet's own movement (in R per second): tongues trail behind.
        self._fire.step(dt * ex.flicker, clock=c, seed=s, wild=ex.wild, flame=ex.flame,
                        wind_x=-0.45 * self._vx / self.R, wind_y=-0.3 * self._vy / self.R,
                        sway=sway, body_breath=self._breath_n)
        self._paths = self._fire.paths
        self._tip_point = self._fire.tip
        top = -1.5 * self.R
        self._top_points = [q for q in self._fire.outer_points if q[1] < top]

    def _to_widget(self, x: float, y: float) -> tuple[float, float]:
        """Map a body-coordinate point to widget coordinates (same transform as ``paint``)."""
        shear = -self._lean.value * 0.22
        return (self.feet.x() + self._shake_px + self._sx * (x + shear * y),
                self.feet.y() + self._hop_y + self._sy * y)

    def _update_embers(self, dt: float, moved_x: float, moved_y: float) -> None:
        """Spawn, move and retire sparks (kept in screen space)."""
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
            e.x += (e.vx + math.sin(self._t * 3.0 + e.phase) * 14.0 * self.scale) * dt - moved_x
            e.y += e.vy * dt - moved_y
            e.vy *= 1.0 - 0.6 * dt
            if -10 < e.x < self.width + 10 and -10 < e.y < self.height + 10:
                alive.append(e)
        self._embers = alive

    def _spawn_ember(self, speed_boost: float = 1.0) -> None:
        """Create one spark somewhere along the top of the outer flame."""
        if len(self._embers) >= self.MAX_EMBERS or not self._top_points:
            return
        tx, ty = self._rng.choice(self._top_points)
        x, y = self._to_widget(tx, ty - 0.04 * self.R)  # just outside the outline
        self._add_ember(x, y, speed_boost)

    def _add_ember(self, x: float, y: float, speed_boost: float) -> None:
        """Append one particle at widget position (``x``, ``y``) with randomized motion."""
        if len(self._embers) >= self.MAX_EMBERS:
            return
        rng = self._rng
        life = rng.uniform(0.7, 1.5)
        size = rng.uniform(1.3, 2.6) * self.scale
        self._embers.append(
            _Ember(
                x=x, y=y,
                vx=rng.uniform(-14, 14) * self.scale * speed_boost - self._vx * 0.12,
                vy=-rng.uniform(55, 95) * self.scale * speed_boost,
                life=life, max_life=life, size=size, phase=rng.uniform(0, math.tau),
            )
        )

    # ------------------------------------------------------------------ rendering

    def paint(self, painter: QPainter) -> None:
        """Draw the whole character (glow, flame layers, face and sparks) with ``painter``."""
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        # Sparks go behind the body: they appear to fly out from behind the flame tips.
        self._paint_embers(painter)

        painter.save()
        painter.translate(self.feet.x() + self._shake_px, self.feet.y() + self._hop_y)
        painter.scale(self._sx, self._sy)
        painter.shear(-self._lean.value * 0.22, 0.0)  # top of the body leans, feet stay put
        self._paint_glow(painter)
        self._paint_flame(painter)
        self._paint_face(painter)
        painter.restore()

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
        painter.setPen(QPen(INK, 0.06 * r, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap,
                            Qt.PenJoinStyle.RoundJoin))
        painter.setBrush(self._palette_color("outer"))
        painter.drawPath(outer)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(self._palette_color("mid"))
        painter.drawPath(mid)
        painter.setBrush(self._palette_color("inner"))
        painter.drawPath(inner)

        # Pale shine dabs on the right flank, between the yellow body and the red rim.
        painter.setBrush(HIGHLIGHT)
        painter.save()
        painter.translate(1.0 * r, -1.1 * r)
        painter.rotate(-18.0)
        painter.drawEllipse(QPointF(0.0, 0.0), 0.05 * r, 0.085 * r)
        painter.restore()
        painter.drawEllipse(QPointF(0.93 * r, -1.32 * r), 0.035 * r, 0.035 * r)

    def _paint_face(self, painter: QPainter) -> None:
        """Eyes and mouth; the face shifts slightly toward the gaze for depth."""
        r = self.R
        painter.save()
        painter.translate(self._look_x * 0.07 * r, -0.98 * r + self._look_y * 0.05 * r)
        for side in (-1, 1):
            self._paint_eye(painter, QPointF(side * 0.52 * r, 0.0), side)
        self._paint_mouth(painter, QPointF(0.0, 0.42 * r))
        painter.restore()

    def _blink_factor(self) -> float:
        """1 when the eyes are open, dips to 0 during a blink."""
        since = self._t - self._blink_start
        if since < 0.0 or since > 0.2:
            return 1.0
        if since < 0.055:  # lids drop fast...
            return 1.0 - _smoothstep(0.0, 0.055, since)
        return _smoothstep(0.075, 0.2, since)  # ...and lift a bit slower

    def _paint_eye(self, painter: QPainter, center: QPointF, side: int) -> None:
        """One eye: outlined white with a small tracking pupil (cut by slanted lids when angry),
        or a happy "^" arc, or a closed line while blinking."""
        r = self.R
        ex = self._expr
        rx = 0.24 * r * ex.eye_scale
        ry_full = 0.23 * r * ex.eye_scale
        # Going "^ ^": the open eye squeezes shut first, then the arc takes over (no ghosting).
        squint = 1.0 - _smoothstep(0.0, 0.6, ex.happy_eyes)
        openness = _clamp(ex.eye_open * self._blink_factor() * squint, 0.0, 1.0)
        line_pen = QPen(INK, 0.07 * r, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)

        normal_alpha = 1.0 - _smoothstep(0.45, 0.75, ex.happy_eyes)
        arc_alpha = _smoothstep(0.45, 0.75, ex.happy_eyes)
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
                painter.setPen(QPen(INK, 0.075 * r, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap,
                                    Qt.PenJoinStyle.RoundJoin))
                painter.setBrush(EYE_WHITE)
                painter.drawPath(eye)

                painter.save()
                painter.setClipPath(eye)
                painter.setPen(Qt.PenStyle.NoPen)
                px = cx + self._look_x * rx * 0.45
                py = cy + self._look_y * ry * 0.4 + (ry * 0.25 * ex.angry)
                pr = rx * 0.5 * ex.pupil
                painter.setBrush(PUPIL)
                painter.drawEllipse(QPointF(px, py), pr, pr * max(0.6, openness))
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

        if arc_alpha > 0.01:
            painter.save()
            painter.setOpacity(arc_alpha)
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
        w = 0.4 * r * (1.0 + 0.2 * max(smile, 0.0))
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
                painter.setPen(QPen(INK, 0.07 * r, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
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
                    # Both bottom controls sit at bottom_ctrl, so the lip's lowest point is 3/4 down.
                    lip_y = corner_y + 0.75 * (bottom_ctrl - corner_y)
                    tongue_y = lip_y - 0.12 * w
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
            painter.drawEllipse(QPointF(mx, my + 0.08 * r), 0.16 * r * size, 0.19 * r * size)
            painter.restore()

    def _paint_embers(self, painter: QPainter) -> None:
        """Sparks: glowing dots that cool from pale yellow to orange and shrink as they rise."""
        painter.setPen(Qt.PenStyle.NoPen)
        for e in self._embers:
            k = e.life / e.max_life  # 1 = newborn, 0 = dying
            twinkle = 0.75 + 0.25 * math.sin(self._t * 17.0 + e.phase * 3.0)
            color = _mix((255, 120, 40), (255, 230, 140), k, int(230 * min(1.0, k * 2.0) * twinkle))
            painter.setBrush(color)
            size = e.size * (0.5 + 0.5 * k)
            painter.drawEllipse(QRectF(e.x - size, e.y - size, size * 2, size * 2))
