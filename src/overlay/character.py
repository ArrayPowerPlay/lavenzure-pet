"""Code-drawn flame-spirit character: all shapes, motion and expressions are generated every frame.

No image assets are needed. ``FlameCharacter`` is a plain model + renderer (not a widget), so the
same character can be drawn by the always-on-top overlay window, by the preview tool, or into an
offscreen QImage for snapshots (the tray icon is made that way).

Look (flat "sticker" fan-art style): a round flame body with rising tongues on top, drawn as three
nested layers - red rim, orange band, big yellow body - with one dark maroon outline around the
whole silhouette. The face (``overlay.face.Face``) sits on the calm yellow part of the body.

Pieces:
- **Flame body** - one of several interchangeable renderers (``overlay.flame_common``:
  ``metaball``, ``shader`` or ``baked``), chosen with ``renderer=``. The body is not a fixed
  shape: every expression may reshape it (puff up, go boxy and ragged, flatten, shoot flame
  paws hanging over the log). Shape values are springs, so the fire wobbles like jelly when it
  changes shape.
- **Fire weather** - slow random calm / gust / crackle / lull phases and a drifting main tip, so
  the fire never falls into one rhythm. Mood sets the base flicker; moving the window blows the
  fire backwards like wind. At night (``set_night``) the fire burns lower, slower and deeper red.
- **Body physics** driven by the window's own movement: it leans/trails against the direction of
  travel, stretches when moving fast vertically, squashes and wobbles on landings, hops while
  walking. Sleeping adds slow breathing.
- **Face** - expressions, blinking, gaze, head turn, idle micro-expressions (see ``face.py``).
- **Props** (``overlay.props``) - the log it rides while flying (the face moves up while
  sitting on it, so the paws and the log never cover the mouth), the frying pan resting on the
  head in the ``chill`` mood, and the "z"s of a sleeping pet.
- **Sparks** that drift upward in *screen* space, so they trail behind the pet as it moves, plus
  little "poof" rings when a prop appears or vanishes.

Mood layering (highest wins): a transient mood from ``play()`` > alert > sleeping > thinking >
riding the log > normal.

Saving work: ``update()`` splits a long frame into short steps so the physics behave the same at
any frame rate (the pet draws 30 fps by default). ``set_lite_flame()`` lowers the flame's
internal resolution.
"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QBrush, QColor, QImage, QPainter, QPen, QRadialGradient

from overlay.face import Face, Mood
from overlay.flame_common import (
    BODY_CY,
    BODY_RX,
    FireWeather,
    FlameColors,
    FlameDrive,
    Spring,
    approach,
    clamp,
    fbm1,
    lerp,
    make_flame_renderer,
    noise1,
    smoothstep,
)
from overlay.props import LOG_CY, LOG_RADIUS, LogProp, PanProp, Snores

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
# Night: embers rather than a bright blaze - deeper reds, a warm amber body, less glow.
NIGHT_PALETTE = Palette(outer=(206, 48, 64), mid=(238, 112, 56), inner=(250, 192, 66),
                        glow=(255, 100, 40))

INK = QColor(108, 14, 22)            # dark maroon outline
HIGHLIGHT = QColor(255, 234, 168)    # pale dabs of shine on the right flank
POOF = QColor(255, 244, 214)


def _mix(c1: tuple[int, int, int], c2: tuple[int, int, int], t: float) -> tuple[int, int, int]:
    """Blend two RGB tuples."""
    return tuple(int(lerp(a, b, t)) for a, b in zip(c1, c2, strict=True))


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


@dataclass
class _Poof:
    """A quick expanding ring + twinkles where something appears or vanishes (widget px)."""

    x: float
    y: float
    age: float
    life: float
    radius: float


_FLARE_RATE = 0.4                  # spontaneous flare-ups per second at wild = 1
EMBER_RATES = {Mood.ALERT: 8.0, Mood.HAPPY: 7.0, Mood.SURPRISED: 5.0, Mood.THINKING: 1.2,
               Mood.SCARED: 11.0, Mood.ANGRY: 10.0, Mood.CHILL: 1.5, Mood.SLEEP: 0.5,
               Mood.YAWN: 1.0, Mood.TAKEOFF: 9.0, Mood.FLY: 3.0, Mood.WAKE: 4.0,
               Mood.YUCK: 4.0}
MAX_FRAME_DT = 0.1                 # a longer gap (a hitch) is treated as this long
MAX_STEP_DT = 1 / 30               # longer frames are simulated in steps of at most this
SEAT_SINK = 0.05                   # R: the body's flat bottom sits this far into the log
FACE_LIFT_ON_LOG = 0.24            # R: the face moves up while sitting on the log ...
MOUTH_FLOOR_ON_LOG = -0.56         # ... and the mouth stays above this height (R, feet = 0)
BREATH_PERIOD = 3.6                # seconds per breath while asleep


class FlameCharacter:
    """Stateful flame spirit. Call ``update()`` once per frame, then ``paint()``.

    Coordinates are widget-local: the canvas is ``width`` x ``height`` pixels and the bottom of the
    body ("feet") sits at ``feet``. Mood is layered: persistent flags (alert, sleeping, thinking,
    riding) form the base, and short-lived moods from ``play()`` override them.
    """

    BASE_RADIUS = 46.0
    MAX_EMBERS = 70

    def __init__(self, scale: float = 1.0, seed: int | None = None,
                 renderer: str = "metaball") -> None:
        """``scale`` = size multiplier; ``renderer`` = flame body renderer name (see module doc)."""
        self.scale = scale
        self.R = self.BASE_RADIUS * scale
        # Wide canvas: room for a puffed-up body, the frying pan's handle and the log.
        self.width = int(round(280 * scale))
        self.height = int(round(236 * scale))
        self.feet = QPointF(self.width / 2, self.height - 22 * scale)

        self._rng = random.Random(seed)
        self._seed = self._rng.randrange(1 << 20)  # different pets flicker differently
        self._t = 0.0

        # Mood layering
        self._alert = False
        self._thinking = False
        self._sleeping = False
        self._riding = False
        self._transient: Mood | None = None
        self._transient_until: float | None = None  # None = until stop_transient()
        self.face = Face(self.R, self._rng, self._seed)
        self._night = 0.0
        self._night_target = 0.0

        # Motion physics
        self._prev_window_pos: QPointF | None = None
        self._vx = 0.0
        self._vy = 0.0
        self._still_frames = 0
        self._squash = Spring(1.0, stiffness=320.0, damping=13.0)
        self._lean = Spring(0.0, stiffness=110.0, damping=10.0)
        self._hop_y = 0.0          # <= 0, pixels above the ground line
        self._hop_v = 0.0
        self._sx = self._sy = 1.0  # body squash/stretch for this frame
        self._shake_px = 0.0
        self._breath_phase = 0.0   # sleepy breathing
        self._breath_wave = 0.0
        self._float_y = 0.0        # bobbing while riding the log (pixels, body + log together)

        # Fire. ``_clock`` runs faster when the flame flickers faster (so a speed change never
        # makes the shapes jump).
        self._clock = self._rng.uniform(0.0, 1000.0)
        self._height_n = 0.0
        self._breath_n = 0.0
        self.weather = FireWeather(self._rng, self._seed)
        self.flame = make_flame_renderer(renderer, self.R, self._rng)

        # Props
        self.log = LogProp(self.R, self._rng, self._seed)
        self.pan = PanProp(self.R, self._rng, self._seed)
        self.snores = Snores(self.R, self._rng)

        self._embers: list[_Ember] = []
        self._poofs: list[_Poof] = []
        self._glow_cache: dict[str, QImage] = {}
        self._ember_debt = 0.0
        self._crumble_debt = 0.0
        self._moved = (0.0, 0.0)

        self._update_fire(0.0)  # so paint() works even before the first update()

    # ------------------------------------------------------------------ public control API

    @property
    def renderer_name(self) -> str:
        """Name of the flame renderer actually in use (after any fallback)."""
        return self.flame.name

    def set_lite_flame(self, lite: bool) -> None:
        """Turn the "lite flame" mode on or off (lower internal flame resolution; only the
        shader renderer has it)."""
        self.flame.set_lite(lite)

    def set_alert(self, active: bool) -> None:
        """Turn the persistent alert look (red-hot, cross eyes, shaking) on or off."""
        self._alert = active

    def set_thinking(self, active: bool) -> None:
        """Turn the persistent thinking look (calm, eyes up, small flame) on or off."""
        self._thinking = active

    def set_sleeping(self, active: bool) -> None:
        """Fall asleep (yawn, then settle low and wide with slow breathing and "z"s) or wake up
        (eyes pop open with a little stretch)."""
        if active == self._sleeping:
            return
        self._sleeping = active
        if active:
            if self._transient is None:
                self.play(Mood.YAWN, 1.6)
        elif self.mood in (Mood.SLEEP, Mood.YAWN):
            self.play(Mood.WAKE, 0.9)

    @property
    def sleeping(self) -> bool:
        """True while the sleeping base look is on."""
        return self._sleeping

    def set_riding(self, active: bool, takeoff: bool = False) -> None:
        """Summon the log and sit on it (``takeoff`` = excited face for a moment), or let the log
        crumble into embers."""
        if active == self._riding:
            if active and takeoff:
                self.play(Mood.TAKEOFF, 0.9)
            return
        self._riding = active
        if active:
            self.log.show()
            self._poof_at_log()
            if takeoff:
                self.play(Mood.TAKEOFF, 0.9)
        else:
            self.log.hide()

    @property
    def riding(self) -> bool:
        """True while the pet sits on its flying log."""
        return self._riding

    def set_night(self, amount: float) -> None:
        """Night look (0 = day, 1 = full night): lower, slower, deeper-red fire. Eases over
        several seconds, so switching at 20:00 is a gentle dusk rather than a jump."""
        self._night_target = clamp(amount, 0.0, 1.0)

    def play(self, mood: Mood, seconds: float | None) -> None:
        """Show a temporary ``mood`` for ``seconds`` (``None`` = until ``stop_transient()``).

        Playing the mood that is already showing restarts it (new variant, new kick). ``chill``
        needs the pan on the head, which does not go with riding the log (the log would hide
        the face), so while riding it is shown as ``happy`` instead."""
        if mood == Mood.CHILL and self._riding:
            mood = Mood.HAPPY
        restart = self._transient == mood or (self._transient is None and self.mood == mood)
        self._transient = mood
        self._transient_until = None if seconds is None else self._t + seconds
        if restart:
            self.face.restart_mood(mood)
        if mood == Mood.HAPPY:
            self.burst(12)                 # sparks and a flare, but no jump
        elif mood == Mood.SURPRISED:
            self._squash.velocity += 3.5   # jolt upward
            self.flame.flare(1.0)
        elif mood == Mood.SCARED:
            self.bounce(0.55)
            self.flame.flare(1.3)
            for _ in range(16):
                self._spawn_ember(speed_boost=2.4)
        elif mood == Mood.ANGRY:
            self._squash.velocity -= 3.5   # stomp down, then the fire flares up
            self.flame.flare(1.2)
            for _ in range(10):
                self._spawn_ember(speed_boost=2.0)
        elif mood == Mood.WAKE:
            self._squash.velocity += 3.0   # stretch
        elif mood == Mood.CHILL:
            self.pan.show()

    def talk(self, seconds: float) -> None:
        """Move the mouth like speaking for ``seconds`` without changing the expression."""
        self.face.talk(seconds)

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
        if self._sleeping:
            return Mood.SLEEP
        if self._thinking:
            return Mood.THINKING
        if self._riding:
            return Mood.FLY
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
        coordinates, or ``None`` if unknown. A frame longer than ``MAX_STEP_DT`` (low frame
        rates) is simulated as several short steps, the window gliding between its old and new
        position, so springs and physics behave exactly as at 60 fps.
        """
        dt = clamp(dt, 0.0, MAX_FRAME_DT)
        if dt == 0.0:
            return
        steps = max(1, math.ceil(dt / MAX_STEP_DT - 1e-9))
        start = self._prev_window_pos
        for i in range(1, steps + 1):
            pos = window_pos
            if window_pos is not None and start is not None and i < steps:
                pos = start + (window_pos - start) * (i / steps)
            self._step(dt / steps, pos, cursor)

    def _step(self, dt: float, window_pos: QPointF | None, cursor: QPointF | None) -> None:
        """One simulation step of ``dt`` seconds (see ``update``)."""
        self._t += dt

        if self._transient_until is not None and self._t >= self._transient_until:
            self.stop_transient()
        self._night = approach(self._night, self._night_target, 0.35, dt)

        moved_x, moved_y = self._update_velocity(dt, window_pos)
        self._moved = (moved_x, moved_y)
        mood = self.mood
        self.face.set_mood(mood)
        if mood != Mood.CHILL:
            self.pan.hide()
        ride = clamp(self.log.amount, 0.0, 1.0) if self.log.visible else 0.0
        self.face.lift = FACE_LIFT_ON_LOG * ride
        self.face.floor_y = MOUTH_FLOOR_ON_LOG * self.R if ride > 0.05 else None
        face_cursor = None
        if cursor is not None:
            face_cursor = QPointF(cursor.x() - self.feet.x(),
                                  cursor.y() - (self.feet.y() - BODY_CY * self.R))
        self.face.update(dt, face_cursor, (self._hop_v + self._vy * 0.3) / self.R)
        self._update_body(dt)
        self.weather.update(dt)
        self._update_fire(dt)
        self._update_props(dt)
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
        """Springs for squash/stretch and lean, the hop physics, sleepy breathing and the gentle
        bob while riding the log."""
        speed_x = abs(self._vx)
        stretch = clamp(abs(self._vy) / 1100.0, 0.0, 0.2)
        self._squash.step(1.0 + stretch, dt)
        self._lean.step(clamp(-self._vx / 520.0, -0.5, 0.5), dt)

        # Walking along the ground (horizontal motion, little vertical) -> keep hopping. Not while
        # sitting on the log: then it glides.
        on_log = self.log.visible
        walking = speed_x > 30.0 and abs(self._vy) < 40.0 and not on_log
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

        # Sleepy breathing: slow in-breath, a slightly quicker sigh out.
        snooze = clamp(self.face.expr.snooze, 0.0, 1.0)
        self._breath_phase += dt * math.tau / BREATH_PERIOD
        p = self._breath_phase
        self._breath_wave = (math.sin(p) + 0.22 * math.sin(2.0 * p - 0.6)) * snooze

        # Floating on the log: the body + log bob together, a bit above the ground line.
        ride = clamp(self.log.amount, 0.0, 1.0)
        self._float_y = (-0.1 * self.R - 0.07 * self.R * math.sin(self._t * 2.1)) * ride

        # Overall squash/stretch: spring + slow uneven "breathing" from the fire noise.
        breathe = 0.02 * self._breath_n + 0.045 * self._breath_wave
        self._sy = max(0.6, self._squash.value + breathe)
        self._sx = 1.0 + (1.0 - self._sy) * 0.85  # keep the volume roughly constant
        self._shake_px = (self.face.expr.shake * noise1(self._t * 40.0, self._seed + 77)
                          * 2.2 * self.scale)

    def _update_fire(self, dt: float) -> None:
        """Advance weather-scaled fire clock, flare-ups and the flame renderer."""
        ex = self.face.expr
        w = self.weather
        night = self._night
        speed = ex.flicker * w.speed * (1.0 - 0.28 * night)
        wild = ex.wild * w.turbulence * (1.0 - 0.25 * night)
        self._clock += dt * speed
        c = self._clock
        s = self._seed
        if self._rng.random() < _FLARE_RATE * ex.wild * ex.wild * w.flare_boost * dt:
            self.flame.flare(self._rng.uniform(0.7, 1.1) * (1.0 - 0.4 * night))
        self._height_n = fbm1(c * 0.55, s + 300)
        self._breath_n = fbm1(c * 0.4, s + 301)
        sway = (0.2 * math.sqrt(wild) * fbm1(c * 0.75, s + 303) + w.drift
                + 0.9 * self._lean.value)
        # Sitting on the log: the shader draws the paws as part of the fire (see ``paint``).
        ride = clamp(self.log.amount, 0.0, 1.2) if self.log.visible else 0.0
        height = ex.flame * w.height * (1.0 - 0.14 * night) * (1.0 + 0.1 * self._breath_wave)
        # Apparent wind from the pet's own movement (in R per second): the fire trails behind.
        self.flame.step(FlameDrive(
            dt=dt * speed, clock=c, seed=s, wild=wild, flame=height,
            wind_x=-0.45 * self._vx / self.R, wind_y=-0.3 * self._vy / self.R,
            sway=sway, breath=self._breath_n,
            body_w=ex.body_w, body_h=ex.body_h, boxy=clamp(ex.boxy, 0.0, 1.0),
            jag=clamp(ex.jag, 0.0, 1.2),
            paws=clamp(ride, 0.0, 1.0) * (1.0 - smoothstep(0.0, 0.3, self.log.crumble)),
            paw_phase=self.log.knead_phase, seat=-(LOG_CY - LOG_RADIUS) - SEAT_SINK,
        ))

    def _update_props(self, dt: float) -> None:
        """Log (and its crumbling embers), frying pan, snoring "z"s and poof rings."""
        self.log.update(dt)
        self.pan.update(dt)
        if self.pan.landing_impact():
            self._squash.velocity -= 1.2      # the pan lands on the head: squish
        if self.log.crumbling:
            self._crumble_debt += dt * 70.0
            n = int(self._crumble_debt)
            self._crumble_debt -= n
            for x, y in self.log.ember_points(n):
                wx, wy = self.feet.x() + x, self.feet.y() + self._float_y + y
                self._add_ember(wx, wy, self._rng.uniform(-30, 30) * self.scale,
                                -self._rng.uniform(40, 110) * self.scale, size_boost=1.2)
        ex = self.face.expr
        head = QPointF(self.feet.x() + 0.55 * self.R,
                       self.feet.y() + self._float_y - (1.75 * ex.body_h + 0.25) * self.R)
        self.snores.update(dt, ex.snooze > 0.7 and self.mood == Mood.SLEEP, head, self._moved)
        alive = []
        for poof in self._poofs:
            poof.age += dt
            poof.x -= self._moved[0]
            poof.y -= self._moved[1]
            if poof.age < poof.life:
                alive.append(poof)
        self._poofs = alive

    def _poof_at_log(self) -> None:
        """Puff + spark ring where the log pops into existence."""
        R = self.R
        cx, cy = self.feet.x(), self.feet.y() - 0.15 * R
        self._poofs.append(_Poof(cx, cy, 0.0, 0.4, 1.6 * R))
        for i in range(18):
            a = i / 18 * math.tau
            speed = self._rng.uniform(70, 130) * self.scale
            self._add_ember(cx + math.cos(a) * 1.2 * R, cy + math.sin(a) * 0.3 * R,
                            math.cos(a) * speed, math.sin(a) * speed * 0.5 - 40 * self.scale,
                            size_boost=1.3)

    def _to_widget(self, x: float, y: float) -> tuple[float, float]:
        """Map a body-coordinate point to widget coordinates (same transform as ``paint``)."""
        shear = -self._lean.value * 0.22
        return (self.feet.x() + self._shake_px + self._sx * (x + shear * y),
                self.feet.y() + self._hop_y + self._float_y + self._sy * y)

    def _update_embers(self, dt: float, moved_x: float, moved_y: float) -> None:
        """Spawn, move and retire sparks (kept in screen space)."""
        rate = EMBER_RATES.get(self.mood, 2.5) * (1.0 - 0.5 * self._night)
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
            e.vx *= 1.0 - 1.2 * dt
            if -10 < e.x < self.width + 10 and -10 < e.y < self.height + 10:
                alive.append(e)
        self._embers = alive

    def _spawn_ember(self, speed_boost: float = 1.0) -> None:
        """Create one spark somewhere along the top of the outer flame."""
        points = self.flame.top_points
        if not points:
            return
        tx, ty = self._rng.choice(points)
        x, y = self._to_widget(tx, ty - 0.04 * self.R)  # just outside the outline
        rng = self._rng
        self._add_ember(x, y, rng.uniform(-14, 14) * self.scale * speed_boost - self._vx * 0.12,
                        -rng.uniform(55, 95) * self.scale * speed_boost)

    def _add_ember(self, x: float, y: float, vx: float, vy: float,
                   size_boost: float = 1.0) -> None:
        """Add one spark at widget point (``x``, ``y``) with the given velocity."""
        if len(self._embers) >= self.MAX_EMBERS:
            return
        rng = self._rng
        life = rng.uniform(0.7, 1.5)
        self._embers.append(_Ember(x=x, y=y, vx=vx, vy=vy, life=life, max_life=life,
                                   size=rng.uniform(1.3, 2.6) * self.scale * size_boost,
                                   phase=rng.uniform(0, math.tau)))

    # ------------------------------------------------------------------ rendering

    def paint(self, painter: QPainter) -> None:
        """Draw the whole character (glow, props, flame layers, face and sparks)."""
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        # Sparks go behind the body: they appear to fly out from behind the flame tips.
        self._paint_embers(painter)
        ex = self.face.expr
        # With the shader the paws are part of the fire, so the log goes *behind* it: the body
        # sits on the log and the paws hang over its front, one mass with the flame.
        log_behind = self.flame.name == "shader"
        if log_behind:
            self._paint_log(painter, paws=False)

        painter.save()
        painter.translate(self.feet.x() + self._shake_px,
                          self.feet.y() + self._hop_y + self._float_y)
        painter.scale(self._sx, self._sy)
        painter.shear(-self._lean.value * 0.22, 0.0)  # top of the body leans, feet stay put
        self._paint_glow(painter)
        if self.flame.name == "shader":
            self.flame.paint(painter, self._colors())
        else:
            painter.save()                      # other renderers only know the round body
            painter.scale(ex.body_w, ex.body_h)
            self.flame.paint(painter, self._colors())
            painter.restore()
        self._paint_shine(painter)
        self.face.paint(painter)
        # The pan rests *on* the head, in front of the fire (reference fig. 7): its bottom sits
        # just above the eyes and the flame shows around and behind it.
        self.pan.paint(painter, self.face.eye_top() - 0.07 * self.R)
        painter.restore()

        if not log_behind:
            self._paint_log(painter, paws=True)
        self._paint_poofs(painter)
        self.snores.paint(painter)

    def _paint_log(self, painter: QPainter, paws: bool) -> None:
        """Draw the log under the pet (if it is out). ``paws`` = also draw the two paws over it
        as separate shapes (renderers that cannot draw them as part of the fire)."""
        if not self.log.visible:
            return
        painter.save()
        painter.translate(self.feet.x() + self._shake_px * 0.3,
                          self.feet.y() + self._hop_y + self._float_y)
        colors = (self._palette_color("inner"), self._palette_color("mid")) if paws else None
        self.log.paint(painter, colors)
        painter.restore()

    def _palette_rgb(self, layer: str) -> tuple[int, int, int]:
        """Current RGB of a flame layer: calm -> night by the night amount, then -> alert."""
        base = _mix(getattr(CALM_PALETTE, layer), getattr(NIGHT_PALETTE, layer), self._night)
        return _mix(base, getattr(ALERT_PALETTE, layer), clamp(self.face.expr.alert, 0.0, 1.0))

    def _palette_color(self, layer: str, alpha: int = 255) -> QColor:
        """Current colour of a flame layer as a QColor."""
        return QColor(*self._palette_rgb(layer), alpha)

    def _colors(self) -> FlameColors:
        """Colours handed to the flame renderer this frame."""
        return FlameColors(outer=self._palette_color("outer"), mid=self._palette_color("mid"),
                           inner=self._palette_color("inner"), ink=INK, outline_px=0.06 * self.R)

    def _glow_image(self, name: str) -> QImage:
        """Pre-rendered soft halo (one per palette). Drawing a cached image is far cheaper than
        filling a big radial gradient every frame."""
        cache = self._glow_cache
        if name not in cache:
            size = int(math.ceil(3.6 * self.R)) + 2
            image = QImage(size, size, QImage.Format.Format_ARGB32_Premultiplied)
            image.fill(Qt.GlobalColor.transparent)
            grad = QRadialGradient(QPointF(size / 2, size / 2), size / 2 - 1)
            rgb = {"calm": CALM_PALETTE, "alert": ALERT_PALETTE, "night": NIGHT_PALETTE}[name].glow
            for stop, alpha in ((0.0, 80), (0.45, 36), (0.75, 10), (1.0, 0)):
                grad.setColorAt(stop, QColor(*rgb, alpha))
            p = QPainter(image)
            p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QBrush(grad))
            p.drawEllipse(QRectF(0, 0, size, size))
            p.end()
            cache[name] = image
        return cache[name]

    def _paint_glow(self, painter: QPainter) -> None:
        """Soft warm halo behind the body that pulses with the fire; it fades to fully transparent
        at its edge (so clicks there still pass through to the desktop)."""
        r = self.R
        ex = self.face.expr
        pulse = (0.8 + 0.2 * self._height_n) * (1.0 - 0.35 * self._night)
        radius = 1.7 * r * clamp(ex.flame, 0.5, 1.6) * (0.5 + 0.5 * ex.body_w)
        target = QRectF(-radius, -1.2 * r * ex.body_h - radius, radius * 2, radius * 2)
        alert = clamp(ex.alert, 0.0, 1.0)
        painter.save()
        for name, weight in (("calm", (1.0 - alert) * (1.0 - self._night)),
                             ("night", (1.0 - alert) * self._night), ("alert", alert)):
            if weight > 0.01:
                painter.setOpacity(pulse * weight)
                painter.drawImage(target, self._glow_image(name))
        painter.restore()

    def _paint_shine(self, painter: QPainter) -> None:
        """Pale shine dabs on the right flank, between the yellow body and the red rim."""
        r = self.R
        ex = self.face.expr
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(HIGHLIGHT)
        x = BODY_RX * 0.78 * r * ex.body_w
        y = -(BODY_CY * ex.body_h + 0.12) * r
        painter.save()
        painter.setOpacity(painter.opacity() * (1.0 - 0.5 * self._night))
        painter.translate(x, y)
        painter.rotate(-18.0)
        painter.drawEllipse(QPointF(0.0, 0.0), 0.05 * r, 0.085 * r)
        painter.restore()
        painter.save()
        painter.setOpacity(painter.opacity() * (1.0 - 0.5 * self._night))
        painter.drawEllipse(QPointF(x - 0.06 * r, y - 0.22 * r), 0.035 * r, 0.035 * r)
        painter.restore()

    def _paint_embers(self, painter: QPainter) -> None:
        """Sparks: glowing dots that cool from pale yellow to orange and shrink as they rise."""
        painter.setPen(Qt.PenStyle.NoPen)
        for e in self._embers:
            k = e.life / e.max_life  # 1 = newborn, 0 = dying
            twinkle = 0.75 + 0.25 * math.sin(self._t * 17.0 + e.phase * 3.0)
            rgb = _mix((255, 120, 40), (255, 230, 140), k)
            painter.setBrush(QColor(*rgb, int(230 * min(1.0, k * 2.0) * twinkle)))
            size = e.size * (0.5 + 0.5 * k)
            painter.drawEllipse(QRectF(e.x - size, e.y - size, size * 2, size * 2))

    def _paint_poofs(self, painter: QPainter) -> None:
        """Expanding pale rings with four twinkling star points (props appearing / vanishing)."""
        for poof in self._poofs:
            k = poof.age / poof.life
            alpha = int(220 * (1.0 - smoothstep(0.3, 1.0, k)))
            radius = poof.radius * (0.35 + 0.65 * smoothstep(0.0, 1.0, k))
            color = QColor(POOF.red(), POOF.green(), POOF.blue(), alpha)
            painter.save()
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.setPen(QPen(color, max(1.0, 0.07 * self.R * (1.0 - k))))
            painter.drawEllipse(QPointF(poof.x, poof.y), radius, radius * 0.45)
            painter.setPen(QPen(color, max(1.0, 0.05 * self.R), Qt.PenStyle.SolidLine,
                                Qt.PenCapStyle.RoundCap))
            for i in range(4):
                a = i * math.tau / 4 + 0.4
                px = poof.x + math.cos(a) * radius * 1.1
                py = poof.y + math.sin(a) * radius * 0.6
                arm = 0.12 * self.R * (1.0 - k)
                painter.drawLine(QPointF(px - arm, py), QPointF(px + arm, py))
                painter.drawLine(QPointF(px, py - arm), QPointF(px, py + arm))
            painter.restore()
