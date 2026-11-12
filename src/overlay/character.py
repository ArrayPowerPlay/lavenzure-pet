"""Code-drawn flame-spirit character: all shapes, motion and expressions are generated every frame.

No image assets are needed. ``FlameCharacter`` is a plain model + renderer (not a widget), so the
same character can be drawn by the always-on-top overlay window, by the preview tool, or into an
offscreen QImage for snapshots.

Look (flat "sticker" fan-art style): a round flame body with rising tongues on top, drawn as three
nested layers - red rim, orange band, big yellow body - with one dark maroon outline around the
whole silhouette. The face (``overlay.face.Face``) sits on the calm yellow part of the body.

Pieces:
- **Flame body** - one of several interchangeable renderers (``overlay.flame_common``:
  ``metaball``, ``shader`` or ``baked``), chosen with ``renderer=``. They all share the same body
  geometry so the face always fits.
- **Fire weather** - slow random calm / gust / crackle / lull phases and a drifting main tip, so
  the fire never falls into one rhythm. Mood sets the base flicker; moving the window blows the
  fire backwards like wind.
- **Body physics** driven by the window's own movement: it leans/trails against the direction of
  travel, stretches when moving fast vertically, squashes and wobbles on landings, hops while
  walking.
- **Face** - expressions, blinking, gaze, head turn, idle micro-expressions (see ``face.py``).
- **Sparks** that drift upward in *screen* space, so they trail behind the pet as it moves.
"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QBrush, QColor, QImage, QPainter, QRadialGradient

from overlay.face import Face, Mood
from overlay.flame_common import (
    BODY_CY,
    BODY_RX,
    FireWeather,
    FlameColors,
    FlameDrive,
    clamp,
    fbm1,
    lerp,
    make_flame_renderer,
    noise1,
)

__all__ = ["FlameCharacter", "Mood"]


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

INK = QColor(108, 14, 22)            # dark maroon outline
HIGHLIGHT = QColor(255, 234, 168)    # pale dabs of shine on the right flank


def _mix(c1: tuple[int, int, int], c2: tuple[int, int, int], t: float, alpha: int = 255) -> QColor:
    """Blend two RGB tuples into a QColor."""
    return QColor(*(int(lerp(a, b, t)) for a, b in zip(c1, c2, strict=True)), alpha)


class _Spring:
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


_FLARE_RATE = 0.4                  # spontaneous flare-ups per second at wild = 1


class FlameCharacter:
    """Stateful flame spirit. Call ``update()`` once per frame, then ``paint()``.

    Coordinates are widget-local: the canvas is ``width`` x ``height`` pixels and the bottom of the
    body ("feet") sits at ``feet``. Mood is layered: persistent flags (alert, thinking) form the
    base, and short-lived moods from ``play()`` (happy, surprised, talking) override them.
    """

    BASE_RADIUS = 46.0
    MAX_EMBERS = 40

    def __init__(self, scale: float = 1.0, seed: int | None = None,
                 renderer: str = "metaball") -> None:
        """``scale`` = size multiplier; ``renderer`` = flame body renderer name (see module doc)."""
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
        self.face = Face(self.R, self._rng, self._seed)

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

        # Fire. ``_clock`` runs faster when the flame flickers faster (so a speed change never
        # makes the shapes jump).
        self._clock = self._rng.uniform(0.0, 1000.0)
        self._height_n = 0.0
        self._breath_n = 0.0
        self.weather = FireWeather(self._rng, self._seed)
        self.flame = make_flame_renderer(renderer, self.R, self._rng)

        self._embers: list[_Ember] = []
        self._glow_cache: dict[bool, QImage] = {}
        self._ember_debt = 0.0

        self._update_fire(0.0)  # so paint() works even before the first update()

    # ------------------------------------------------------------------ public control API

    @property
    def renderer_name(self) -> str:
        """Name of the flame renderer actually in use (after any fallback)."""
        return self.flame.name

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
            self._squash.velocity -= 2.0   # tiny crouch first...
            self._squash.velocity += 5.5   # ...then the jolt upward
            self.flame.flare(1.0)

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
        self.flame.flare(1.0)

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

    def body_rect(self) -> QRectF:
        """Widget-local rectangle around the round lower body (where the face is)."""
        r = self.R
        return QRectF(self.feet.x() - 1.2 * r, self.feet.y() - 2.1 * r, 2.4 * r, 2.1 * r)

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
        dt = clamp(dt, 0.0, 0.05)
        if dt == 0.0:
            return
        self._t += dt

        if self._transient_until is not None and self._t >= self._transient_until:
            self.stop_transient()

        moved_x, moved_y = self._update_velocity(dt, window_pos)
        self.face.set_mood(self.mood)
        face_cursor = None
        if cursor is not None:
            face_cursor = QPointF(cursor.x() - self.feet.x(),
                                  cursor.y() - (self.feet.y() - BODY_CY * self.R))
        self.face.update(dt, face_cursor, (self._hop_v + self._vy * 0.3) / self.R)
        self._update_body(dt)
        self.weather.update(dt)
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
            self._squash.velocity -= clamp(self._vy / 90.0, 2.5, 7.0)
            self._vy = 0.0
        return moved_x, moved_y

    def _update_body(self, dt: float) -> None:
        """Springs for squash/stretch and lean, plus the hop (small jump) physics."""
        speed_x = abs(self._vx)
        stretch = clamp(abs(self._vy) / 1100.0, 0.0, 0.2)
        self._squash.step(1.0 + stretch, dt)
        self._lean.step(clamp(-self._vx / 520.0, -0.5, 0.5), dt)

        # Walking along the ground (horizontal motion, little vertical) -> keep hopping.
        walking = speed_x > 30.0 and abs(self._vy) < 40.0
        if walking and self._hop_y >= -0.5 and self._hop_v >= 0.0:
            self._hop_v = -clamp(speed_x * 1.6, 110.0, 170.0) * self.scale

        gravity = 1500.0 * self.scale
        if self._hop_y < 0.0 or self._hop_v < 0.0:
            self._hop_v += gravity * dt
            self._hop_y += self._hop_v * dt
            if self._hop_y >= 0.0:
                self._hop_y = 0.0
                self._squash.velocity -= clamp(self._hop_v / (90.0 * self.scale), 0.5, 4.0)
                self._hop_v = 0.0

        # Overall squash/stretch: spring + slow uneven "breathing" from the fire noise.
        breathe = 0.02 * self._breath_n
        self._sy = max(0.6, self._squash.value + breathe)
        self._sx = 1.0 + (1.0 - self._sy) * 0.85  # keep the volume roughly constant
        self._shake_px = (self.face.expr.shake * noise1(self._t * 40.0, self._seed + 77)
                          * 2.2 * self.scale)

    def _update_fire(self, dt: float) -> None:
        """Advance weather-scaled fire clock, flare-ups and the flame renderer."""
        ex = self.face.expr
        w = self.weather
        speed = ex.flicker * w.speed
        wild = ex.wild * w.turbulence
        self._clock += dt * speed
        c = self._clock
        s = self._seed
        if self._rng.random() < _FLARE_RATE * ex.wild * ex.wild * w.flare_boost * dt:
            self.flame.flare(self._rng.uniform(0.7, 1.1))
        self._height_n = fbm1(c * 0.55, s + 300)
        self._breath_n = fbm1(c * 0.4, s + 301)
        sway = (0.2 * math.sqrt(wild) * fbm1(c * 0.75, s + 303) + w.drift
                + 0.9 * self._lean.value)
        # Apparent wind from the pet's own movement (in R per second): the fire trails behind.
        self.flame.step(FlameDrive(
            dt=dt * speed, clock=c, seed=s, wild=wild, flame=ex.flame * w.height,
            wind_x=-0.45 * self._vx / self.R, wind_y=-0.3 * self._vy / self.R,
            sway=sway, breath=self._breath_n,
        ))

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
        points = self.flame.top_points
        if len(self._embers) >= self.MAX_EMBERS or not points:
            return
        tx, ty = self._rng.choice(points)
        x, y = self._to_widget(tx, ty - 0.04 * self.R)  # just outside the outline
        rng = self._rng
        life = rng.uniform(0.7, 1.5)
        self._embers.append(_Ember(
            x=x, y=y,
            vx=rng.uniform(-14, 14) * self.scale * speed_boost - self._vx * 0.12,
            vy=-rng.uniform(55, 95) * self.scale * speed_boost,
            life=life, max_life=life, size=rng.uniform(1.3, 2.6) * self.scale,
            phase=rng.uniform(0, math.tau),
        ))

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
        self.flame.paint(painter, self._colors())
        self._paint_shine(painter)
        self.face.paint(painter)
        painter.restore()

    def _palette_color(self, layer: str, alpha: int = 255) -> QColor:
        """Current color of a flame layer, blended between the calm and alert palettes."""
        return _mix(getattr(CALM_PALETTE, layer), getattr(ALERT_PALETTE, layer),
                    self.face.expr.alert, alpha)

    def _colors(self) -> FlameColors:
        """Colours handed to the flame renderer this frame."""
        return FlameColors(outer=self._palette_color("outer"), mid=self._palette_color("mid"),
                           inner=self._palette_color("inner"), ink=INK, outline_px=0.06 * self.R)

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
        ex = self.face.expr
        pulse = 0.8 + 0.2 * self._height_n
        radius = 1.7 * r * ex.flame
        target = QRectF(-radius, -1.2 * r - radius, radius * 2, radius * 2)
        painter.save()
        for alert, weight in ((False, 1.0 - ex.alert), (True, ex.alert)):
            if weight > 0.01:
                painter.setOpacity(pulse * weight)
                painter.drawImage(target, self._glow_image(alert))
        painter.restore()

    def _paint_shine(self, painter: QPainter) -> None:
        """Pale shine dabs on the right flank, between the yellow body and the red rim."""
        r = self.R
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(HIGHLIGHT)
        x = BODY_RX * 0.78 * r
        painter.save()
        painter.translate(x, -(BODY_CY + 0.12) * r)
        painter.rotate(-18.0)
        painter.drawEllipse(QPointF(0.0, 0.0), 0.05 * r, 0.085 * r)
        painter.restore()
        painter.drawEllipse(QPointF(x - 0.06 * r, -(BODY_CY + 0.34) * r), 0.035 * r, 0.035 * r)

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
