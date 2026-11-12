"""The flame character's face: expressions, eyes, mouth and how they move.

``Face`` owns everything that happens on the face and is drawn on top of the flame body by
``overlay.character.FlameCharacter``. Expressions are data: every ``Mood`` is one target
``Expression`` (a set of continuous parameters such as how open the eyes are or how much the
mouth smiles) and the face blends toward it. Things that make it feel alive rather than
mechanical:

- **Overlapping timing** - the eyes react first and the mouth follows a beat later, instead of
  every feature switching in the same frame.
- **Springs with a little overshoot** on sizes (eyes "pop" when surprised) plus an *anticipation*
  kick (a tiny squeeze in the opposite direction) right when the mood changes.
- **Lids** - an upper lid that can droop or slant (cross / worried looks) and a lower lid that
  cheeks push up when smiling, on top of fast-close / slow-open blinks.
- **Head turn** - features sit on an imaginary sphere, so when the eyes look sideways the whole
  face slides that way and the far side gets narrower, as if the head turned.
- **Idle micro-expressions** - while nothing is going on the face drifts through small random
  expressions (a smug smirk, a content squint, a little "o", a yawn, sleepy lids, a worried
  wiggle) at irregular times.
- **Safe area** - eyes and mouth are always fitted inside ``FACE_*`` (an ellipse on the yellow
  body), so even the biggest grin never spills onto the orange/red rim.

All sizes are in units of R (the character's base radius); drawing happens in the character's
body coordinates (pixels, origin at the feet, y up is negative).
"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass, fields, replace
from enum import Enum, auto

from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen, QPolygonF

from overlay.flame_common import (FACE_CY, FACE_RX, FACE_RY, approach, clamp, lerp, noise1,
                                  smoothstep)

INK = QColor(108, 14, 22)            # dark maroon used for every face line
EYE_WHITE = QColor(255, 253, 244)
PUPIL = QColor(96, 10, 20)
MOUTH = QColor(206, 30, 42)
TONGUE = QColor(244, 112, 112)


class Mood(Enum):
    """Facial expression / energy level the character is showing."""

    NORMAL = auto()
    HAPPY = auto()
    SURPRISED = auto()
    ALERT = auto()
    THINKING = auto()
    TALKING = auto()


@dataclass
class Expression:
    """Continuous face (and flame) parameters; every mood is one target set."""

    eye_open: float = 1.0      # upper lid: 1 = fully open, 0 = closed
    lower_lid: float = 0.0     # 1 = cheeks push the lower lid up (smiling / squinting eyes)
    eye_scale: float = 1.0     # overall eye size
    pupil: float = 1.0         # pupil size relative to the eye
    happy_eyes: float = 0.0    # 1 = closed "^ ^" smiling eyes
    slant: float = 0.0         # +1 = lids slope down toward the nose (cross), -1 = up (worried)
    mouth_open: float = 0.0    # 0 = closed line, 1 = wide open
    smile: float = 0.5         # -1 = frown, 1 = big smile
    mouth_round: float = 0.0   # 1 = round "o" mouth
    mouth_width: float = 1.0   # width multiplier
    mouth_wave: float = 0.0    # 1 = wobbly, worried mouth line
    smirk: float = 0.0         # -1..1: lifts the left / right mouth corner
    tilt: float = 0.0          # head tilt in radians (positive = clockwise)
    flame: float = 1.0         # flame height multiplier
    flicker: float = 1.0       # flicker speed multiplier
    wild: float = 1.0          # flicker strength and how often the flame flares up
    alert: float = 0.0         # 0 = calm palette, 1 = alert palette
    shake: float = 0.0         # nervous horizontal jitter


MOOD_TARGETS: dict[Mood, Expression] = {
    Mood.NORMAL: Expression(),
    Mood.HAPPY: Expression(happy_eyes=1.0, mouth_open=0.8, smile=1.0, mouth_width=1.1,
                           flame=1.15, flicker=1.4, wild=1.5),
    Mood.SURPRISED: Expression(eye_scale=1.2, pupil=0.6, mouth_open=0.55, smile=0.0,
                               mouth_round=1.0, flame=1.12, flicker=1.7, wild=1.6),
    Mood.ALERT: Expression(eye_scale=1.05, pupil=0.78, slant=1.0, mouth_open=0.65, smile=-0.7,
                           mouth_width=0.95, flame=1.12, flicker=2.0, wild=1.9, alert=1.0,
                           shake=1.0),
    Mood.THINKING: Expression(eye_open=0.72, smile=0.15, smirk=0.55, mouth_width=0.75,
                              tilt=0.08, flame=0.9, flicker=0.6, wild=0.55),
    Mood.TALKING: Expression(smile=0.6, flame=1.05, flicker=1.25, wild=1.15),
}

# Small expressions the idle face drifts through: name -> (weight, (min, max) seconds, values).
MICRO_EXPRESSIONS: dict[str, tuple[float, tuple[float, float], dict[str, float]]] = {
    "content": (3.0, (1.8, 3.4), {"lower_lid": 0.5, "smile": 0.9}),
    "smirk": (2.0, (1.0, 2.0), {"smirk": 0.8, "eye_open": 0.82, "smile": 0.45}),
    "pout": (1.2, (0.8, 1.5), {"mouth_round": 0.75, "mouth_open": 0.12, "mouth_width": 0.7}),
    "sleepy": (1.2, (2.0, 3.6), {"eye_open": 0.5, "smile": 0.3}),
    "worried": (1.0, (1.2, 2.0), {"slant": -0.7, "mouth_wave": 1.0, "smile": -0.15}),
    "yawn": (0.45, (1.9, 2.6), {"mouth_round": 1.0, "mouth_open": 1.0, "eye_open": 0.12,
                                "slant": -0.3}),
}

EYE_FIELDS = frozenset({"eye_open", "lower_lid", "eye_scale", "pupil", "happy_eyes", "slant",
                        "tilt"})
MOUTH_FIELDS = frozenset({"mouth_open", "smile", "mouth_round", "mouth_width", "mouth_wave",
                          "smirk"})
# Parameters that blend with a slightly under-damped spring (a little overshoot = "pop").
SPRUNG_FIELDS = frozenset({"eye_scale", "pupil", "mouth_open", "smile", "mouth_width",
                           "lower_lid"})
# Parameters that switch between two different drawings are cross-faded quickly, so the two
# shapes are never seen as a ghostly double for long.
FAST_FIELDS = frozenset({"mouth_round", "happy_eyes"})

FACE_STIFFNESS = 240.0
FACE_DAMPING = 21.0
MOUTH_DELAY = 0.075     # seconds the mouth lags behind the eyes when the mood changes

EYE_X = 0.34            # eye centres, left/right of the face centre (R)
EYE_Y = -0.13           # eye centres relative to the face centre (R, negative = up)
EYE_RX = 0.19
EYE_RY = 0.225
MOUTH_Y = 0.27          # mouth centre relative to the face centre (R)
MOUTH_W = 0.26          # half-width of the neutral mouth (R)
SPHERE_R = 0.95         # radius of the imaginary head sphere used for the turn effect (R)


class Face:
    """Expression state + eyes + mouth. Call ``update()`` every frame, then ``paint()``."""

    def __init__(self, R: float, rng: random.Random, seed: int) -> None:
        """``R`` = base radius in pixels; ``seed`` decorrelates this face's noise."""
        self.R = R
        self._rng = rng
        self._seed = seed
        self._t = 0.0
        self.expr = Expression()
        self._vel: dict[str, float] = {name: 0.0 for name in SPRUNG_FIELDS}
        self._mood = Mood.NORMAL
        self._mouth_mood = Mood.NORMAL
        self._mouth_switch_at: float | None = None

        # Idle micro-expressions
        self._micro: str | None = None
        self._micro_start = 0.0
        self._micro_end = 0.0
        self._micro_sign = 1.0
        self._next_micro = rng.uniform(3.0, 7.0)

        # Eyes
        self._next_blink = rng.uniform(1.5, 4.0)
        self._blink_start = -10.0
        self._blink_len = 0.2
        self._look_x = 0.0
        self._look_y = 0.0
        self._last_cursor: QPointF | None = None
        self._cursor_still_since = 0.0
        self._wander_target = (0.0, 0.0)
        self._next_wander = 0.0
        self._jitter = (0.0, 0.0)       # tiny fixation jitter added to the gaze
        self._next_jitter = 0.0
        self._saccade = False

        self._talk_amount = 0.0
        self._lag = 0.0                 # face lags behind fast vertical body motion (R)
        self._lag_vel = 0.0

    # ------------------------------------------------------------------ simulation

    def set_mood(self, mood: Mood) -> None:
        """Switch the target mood (called every frame; only real changes do anything)."""
        if mood == self._mood:
            return
        self._mood = mood
        self._mouth_switch_at = self._t + MOUTH_DELAY
        self._micro = None
        # Anticipation: squeeze a little the "wrong" way first, then the spring pops past.
        if mood == Mood.SURPRISED:
            self._vel["eye_scale"] -= 2.5
            self._vel["mouth_open"] -= 2.0
        elif mood == Mood.HAPPY:
            self._vel["lower_lid"] += 4.0
        elif mood == Mood.ALERT:
            self._vel["eye_scale"] += 4.0

    def update(self, dt: float, cursor: QPointF | None, body_vy: float) -> None:
        """Advance ``dt`` seconds. ``cursor`` is the mouse relative to the face centre (pixels,
        or ``None``); ``body_vy`` is the body's vertical speed in R/s (for the lagging face)."""
        self._t += dt
        if self._mouth_switch_at is not None and self._t >= self._mouth_switch_at:
            self._mouth_mood = self._mood
            self._mouth_switch_at = None
        self._update_micro()
        self._update_expression(dt)
        self._update_eyes(dt, cursor)
        # The face is a little "loose" on the body: it trails fast vertical motion and settles.
        accel = 180.0 * (clamp(body_vy * 0.012, -0.07, 0.07) - self._lag) - 14.0 * self._lag_vel
        self._lag_vel += accel * dt
        self._lag += self._lag_vel * dt

    def _update_micro(self) -> None:
        """Start / end the idle micro-expressions (only while the mood is NORMAL)."""
        if self._mood != Mood.NORMAL:
            self._next_micro = max(self._next_micro, self._t + 2.0)
            return
        if self._micro is not None and self._t >= self._micro_end:
            self._micro = None
            self._next_micro = self._t + self._rng.uniform(3.5, 10.0)
        if self._micro is None and self._t >= self._next_micro:
            names = list(MICRO_EXPRESSIONS)
            weights = [MICRO_EXPRESSIONS[n][0] for n in names]
            self._micro = self._rng.choices(names, weights)[0]
            lo, hi = MICRO_EXPRESSIONS[self._micro][1]
            self._micro_start = self._t
            self._micro_end = self._t + self._rng.uniform(lo, hi)
            self._micro_sign = self._rng.choice((-1.0, 1.0))

    def _target(self) -> Expression:
        """Current goal: eyes follow the mood now, the mouth a beat later, plus micro-overlay."""
        eye_goal = MOOD_TARGETS[self._mood]
        mouth_goal = MOOD_TARGETS[self._mouth_mood]
        goal = replace(eye_goal, **{name: getattr(mouth_goal, name) for name in MOUTH_FIELDS})
        if self._micro is not None:
            _, _, values = MICRO_EXPRESSIONS[self._micro]
            env = (smoothstep(self._micro_start, self._micro_start + 0.3, self._t)
                   * (1.0 - smoothstep(self._micro_end - 0.4, self._micro_end, self._t)))
            for name, value in values.items():
                if name == "smirk":
                    value *= self._micro_sign
                setattr(goal, name, lerp(getattr(goal, name), value, env))
        return goal

    def _update_expression(self, dt: float) -> None:
        """Blend every parameter toward the target (springs for sizes, easing for the rest)."""
        target = self._target()
        for f in fields(Expression):
            name = f.name
            current = getattr(self.expr, name)
            goal = getattr(target, name)
            if name in SPRUNG_FIELDS:
                vel = self._vel[name]
                vel += (FACE_STIFFNESS * (goal - current) - FACE_DAMPING * vel) * dt
                self._vel[name] = vel
                setattr(self.expr, name, current + vel * dt)
            else:
                rate = 20.0 if name in FAST_FIELDS else 9.0
                setattr(self.expr, name, approach(current, goal, rate, dt))

        if self._mood == Mood.TALKING:
            # Irregular "syllables" from noise, gated by a slower noise so phrases have pauses.
            syllable = clamp(0.5 + 1.2 * noise1(self._t * 7.0, self._seed + 501), 0.0, 1.0)
            phrase = smoothstep(-0.3, 0.05, noise1(self._t * 0.9, self._seed + 502))
            want = (0.08 + 0.62 * syllable) * phrase
        else:
            want = 0.0
        self._talk_amount = approach(self._talk_amount, want, 25.0, dt)

    def _update_eyes(self, dt: float, cursor: QPointF | None) -> None:
        """Blink timing and gaze (cursor tracking, idle wandering, thinking glance)."""
        rng = self._rng
        if self._t >= self._next_blink:
            self._blink_start = self._t
            slow = self._micro == "sleepy" or self._mood == Mood.THINKING
            self._blink_len = rng.uniform(0.32, 0.45) if slow else rng.uniform(0.17, 0.23)
            double = rng.random() < 0.15
            self._next_blink = self._t + (0.35 if double else rng.uniform(2.0, 5.5))

        if self._t >= self._next_jitter:
            # Real eyes never hold perfectly still: tiny jumps around the fixation point.
            self._jitter = (rng.uniform(-0.07, 0.07), rng.uniform(-0.05, 0.05))
            self._next_jitter = self._t + rng.uniform(0.35, 1.1)

        target_x, target_y = 0.0, 0.0
        if self._mood == Mood.THINKING:
            target_x, target_y = 0.55, -0.75
        elif self._micro == "yawn":
            target_x, target_y = 0.0, -0.3
        elif cursor is not None:
            if self._last_cursor is None or (cursor - self._last_cursor).manhattanLength() > 2:
                self._cursor_still_since = self._t
                self._last_cursor = QPointF(cursor)
            if self._t - self._cursor_still_since < 4.0:
                dist = math.hypot(cursor.x(), cursor.y()) or 1.0
                reach = min(1.0, dist / (4.8 * self.R))
                target_x, target_y = cursor.x() / dist * reach, cursor.y() / dist * reach
            else:
                if self._t >= self._next_wander:
                    angle = rng.uniform(0, math.tau)
                    radius = rng.choice((0.0, 0.0, rng.uniform(0.3, 0.9)))
                    self._wander_target = (math.cos(angle) * radius, math.sin(angle) * radius * 0.6)
                    self._next_wander = self._t + rng.uniform(1.2, 3.5)
                    if radius > 0.5 and self._t - self._blink_start > 1.0 and rng.random() < 0.3:
                        self._blink_start = self._t  # people often blink with a big glance
                        self._blink_len = 0.2
                target_x, target_y = self._wander_target
        target_x += self._jitter[0]
        target_y += self._jitter[1]
        # Saccade: a far target is reached with one quick dart; near ones are followed smoothly.
        gap = math.hypot(target_x - self._look_x, target_y - self._look_y)
        if gap > 0.25:
            self._saccade = True
        elif gap < 0.03:
            self._saccade = False
        rate = 30.0 if self._saccade else 11.0
        self._look_x = approach(self._look_x, target_x, rate, dt)
        self._look_y = approach(self._look_y, target_y, rate, dt)

    def _blink_factor(self) -> float:
        """1 when the eyes are open, dips to 0 during a blink (fast close, slower open)."""
        since = self._t - self._blink_start
        length = self._blink_len
        if since < 0.0 or since > length:
            return 1.0
        close = length * 0.28
        if since < close:
            return 1.0 - smoothstep(0.0, close, since)
        return smoothstep(close + length * 0.08, length, since)

    # ------------------------------------------------------------------ geometry helpers

    def _place(self, x: float, y: float) -> tuple[float, float, float]:
        """Map a face-space point (R, relative to the face centre) through head turn, tilt and
        lag into body pixels. Returns (x, y, horizontal foreshortening factor)."""
        R = self.R
        turn = self._look_x * 0.38
        nod = self._look_y * 0.08
        theta0 = x / SPHERE_R
        theta = clamp(theta0 + turn, -1.3, 1.3)
        fx = SPHERE_R * math.sin(theta)
        squeeze = math.cos(theta) / max(0.2, math.cos(theta0))
        fy = y + nod
        tilt = self.expr.tilt
        ct, st = math.cos(tilt), math.sin(tilt)
        rx, ry = fx * ct - fy * st, fx * st + fy * ct
        return rx * R, (ry - FACE_CY + self._lag) * R, squeeze

    def _fit(self, cx: float, cy: float, pts: list[tuple[float, float]]) -> float:
        """Largest scale (<= 1) about (``cx``, ``cy``) that keeps ``pts`` (body pixels, relative to
        that centre) inside the face safe area."""
        R = self.R
        ex, ey, ax, ay = 0.0, -FACE_CY * R, FACE_RX * R, FACE_RY * R
        scale = 1.0
        for _ in range(3):
            worst = max(((cx + px * scale - ex) / ax) ** 2 + ((cy + py * scale - ey) / ay) ** 2
                        for px, py in pts)
            if worst <= 1.0:
                break
            scale *= 0.97 / math.sqrt(worst) if worst > 1.0 else 1.0
        return scale

    # ------------------------------------------------------------------ painting

    def paint(self, painter: QPainter) -> None:
        """Draw both eyes and the mouth (painter in body coordinates)."""
        for side in (-1, 1):
            self._paint_eye(painter, side)
        self._paint_mouth(painter)

    def _paint_eye(self, painter: QPainter, side: int) -> None:
        """One eye: outlined white with a tracking pupil, cut by the lids, or a "^" arc, or a
        closed line while blinking."""
        R = self.R
        ex = self.expr
        cx, cy, squeeze = self._place(side * EYE_X, EYE_Y)
        rx = EYE_RX * R * ex.eye_scale * squeeze
        ry = EYE_RY * R * ex.eye_scale
        ring = [(rx * math.cos(a), ry * math.sin(a)) for a in (i * math.tau / 12 for i in range(12))]
        k = self._fit(cx, cy, ring)
        rx, ry = rx * k, ry * k

        # Going "^ ^": the open eye squeezes shut first, then the arc takes over (no ghosting).
        squint = 1.0 - smoothstep(0.0, 0.6, ex.happy_eyes)
        blink = self._blink_factor()
        openness = clamp(blink * squint, 0.0, 1.0)
        lid_open = clamp(ex.eye_open, 0.0, 1.0)
        line_pen = QPen(INK, 0.065 * R, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap,
                        Qt.PenJoinStyle.RoundJoin)

        painter.save()
        painter.translate(cx, cy)
        painter.rotate(math.degrees(ex.tilt))
        normal_alpha = 1.0 - smoothstep(0.45, 0.75, ex.happy_eyes)
        arc_alpha = smoothstep(0.45, 0.75, ex.happy_eyes)
        if normal_alpha > 0.01:
            painter.setOpacity(normal_alpha)
            if openness * lid_open > 0.1:
                self._paint_open_eye(painter, side, rx, ry, openness, lid_open)
            else:
                closed = QPainterPath(QPointF(-rx, 0.0))
                closed.quadTo(QPointF(0.0, ry * 0.4), QPointF(rx, 0.0))
                painter.setPen(line_pen)
                painter.setBrush(Qt.BrushStyle.NoBrush)
                painter.drawPath(closed)
        if arc_alpha > 0.01:
            painter.setOpacity(arc_alpha)
            arc = QPainterPath(QPointF(-rx, ry * 0.3))
            arc.quadTo(QPointF(0.0, -ry * 0.85), QPointF(rx, ry * 0.3))
            painter.setPen(line_pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawPath(arc)
        painter.restore()

    def _paint_open_eye(self, painter: QPainter, side: int, rx: float, ry: float,
                        openness: float, lid_open: float) -> None:
        """White eye (squashed by the blink), clipped by the upper and lower lids, with pupil."""
        R = self.R
        ex = self.expr
        ry_b = ry * openness
        cy = ry * (1.0 - openness) * 0.5  # blinking eyes close toward their lower half
        eye = QPainterPath()
        eye.addEllipse(QPointF(0.0, cy), rx, ry_b)

        # Upper lid: a line that drops with ``eye_open`` and tilts with ``slant``.
        slant = ex.slant
        lid_y = cy - ry_b + 2.0 * ry_b * (1.0 - lid_open) * 0.85
        if slant >= 0.0:
            inner_y, outer_y = lid_y + slant * ry_b * 0.95, lid_y - slant * ry_b * 0.1
        else:
            inner_y, outer_y = lid_y + slant * ry_b * 0.25, lid_y - slant * ry_b * 0.75
        inner_x, outer_x = -side * rx * 1.35, side * rx * 1.35
        lid_cut = lid_open < 0.97 or abs(slant) > 0.03
        if lid_cut:
            cut = QPainterPath()
            cut.addPolygon(QPolygonF([QPointF(inner_x, inner_y), QPointF(outer_x, outer_y),
                                      QPointF(outer_x, cy - 3 * ry), QPointF(inner_x, cy - 3 * ry)]))
            cut.closeSubpath()
            eye = eye.subtracted(cut)
        # Lower lid: cheeks push up a soft curve from below.
        if ex.lower_lid > 0.02:
            low_y = cy + ry_b - 2.0 * ry_b * clamp(ex.lower_lid, 0.0, 1.0) * 0.55
            cheek = QPainterPath(QPointF(-rx * 1.4, low_y + ry_b * 0.3))
            cheek.quadTo(QPointF(0.0, low_y - ry_b * 0.35 * ex.lower_lid),
                         QPointF(rx * 1.4, low_y + ry_b * 0.3))
            cheek.lineTo(QPointF(rx * 1.4, cy + 3 * ry))
            cheek.lineTo(QPointF(-rx * 1.4, cy + 3 * ry))
            cheek.closeSubpath()
            eye = eye.subtracted(cheek)

        pen = QPen(INK, 0.07 * R, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap,
                   Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)
        painter.setBrush(EYE_WHITE)
        painter.drawPath(eye)

        painter.save()
        painter.setClipPath(eye)
        painter.setPen(Qt.PenStyle.NoPen)
        px = self._look_x * rx * 0.5
        py = cy + self._look_y * ry_b * 0.42 + ry_b * 0.2 * max(0.0, slant)
        pr = rx * 0.56 * ex.pupil
        painter.setBrush(PUPIL)
        painter.drawEllipse(QPointF(px, py), pr, pr * max(0.65, openness))
        painter.restore()

        if lid_cut and abs(slant) > 0.05:
            # A firm lid line that runs a bit past the eye, like a brow (cross / worried looks).
            painter.save()
            painter.setOpacity(painter.opacity() * min(1.0, abs(slant) * 1.5))
            painter.setPen(QPen(INK, 0.075 * R, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            a, b = QPointF(inner_x, inner_y), QPointF(outer_x, outer_y)
            painter.drawLine(QPointF(lerp(a.x(), b.x(), 0.14), lerp(a.y(), b.y(), 0.14)),
                             QPointF(lerp(a.x(), b.x(), 0.9), lerp(a.y(), b.y(), 0.9)))
            painter.restore()

    def _mouth_curves(self, w: float) -> tuple[list[tuple[float, float]], list[tuple[float, float]],
                                               float]:
        """Top and bottom lip polylines (local pixels, origin = mouth centre, y down) and the
        opening amount. When the mouth is closed both lips coincide."""
        ex = self.expr
        open_amount = clamp(ex.mouth_open + self._talk_amount, 0.0, 1.15)
        smile = clamp(ex.smile, -1.0, 1.2)
        pos, neg = max(smile, 0.0), max(-smile, 0.0)
        y_left = -smile * 0.3 * w - max(-ex.smirk, 0.0) * 0.35 * w + max(ex.smirk, 0.0) * 0.08 * w
        y_right = -smile * 0.3 * w - max(ex.smirk, 0.0) * 0.35 * w + max(-ex.smirk, 0.0) * 0.08 * w
        depth = 1.3 * w
        k_open = smoothstep(0.04, 0.3, open_amount)
        top, bottom = [], []
        n = 25
        for i in range(n):
            s = -1.0 + 2.0 * i / (n - 1)
            x = s * w
            base = lerp(y_left, y_right, (s + 1.0) * 0.5)
            bow = 1.0 - s * s
            round_bow = math.sqrt(max(bow, 0.0))
            wave = ex.mouth_wave * 0.09 * w * math.sin(3.0 * math.pi * s)
            closed_y = base + bow * smile * 0.42 * w + wave
            open_top = base + bow * 0.14 * w * pos - neg * open_amount * depth * 0.75 * round_bow + wave
            gap = open_amount * depth * round_bow * (0.78 + 0.22 * pos) * (1.0 - 0.55 * neg)
            if neg > 0.0:
                gap += neg * open_amount * depth * 0.75 * round_bow * 0.6
            t = lerp(closed_y, open_top, k_open)
            top.append((x, t))
            bottom.append((x, t + gap))
        return top, bottom, open_amount

    def _paint_mouth(self, painter: QPainter) -> None:
        """Mouth: closed curve / open "D" smile or scream, cross-faded with a round "o"."""
        R = self.R
        ex = self.expr
        cx, cy, squeeze = self._place(0.0, MOUTH_Y)
        w = MOUTH_W * R * ex.mouth_width * (1.0 + 0.15 * max(ex.smile, 0.0)) * squeeze
        top, bottom, open_amount = self._mouth_curves(w)
        # Round "o" mouth size, needed for the safe-area fit too.
        o_size = 0.7 + 0.55 * open_amount
        o_rx, o_ry = 0.15 * R * o_size * squeeze, 0.18 * R * o_size
        ct, st = math.cos(ex.tilt), math.sin(ex.tilt)
        pts = top + bottom + [(o_rx * math.cos(a), 0.06 * R + o_ry * math.sin(a))
                              for a in (i * math.tau / 10 for i in range(10))]
        k = self._fit(cx, cy, [(x * ct - y * st, x * st + y * ct) for x, y in pts])

        ink_pen = QPen(INK, 0.055 * R, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap,
                       Qt.PenJoinStyle.RoundJoin)
        painter.save()
        painter.translate(cx, cy)
        painter.rotate(math.degrees(ex.tilt))
        painter.scale(k, k)
        curve_alpha = 1.0 - ex.mouth_round
        if curve_alpha > 0.01:
            painter.setOpacity(curve_alpha)
            if open_amount < 0.06:
                line = QPainterPath(QPointF(*top[0]))
                for x, y in top[1:]:
                    line.lineTo(x, y)
                painter.setPen(QPen(INK, 0.068 * R, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap,
                                    Qt.PenJoinStyle.RoundJoin))
                painter.setBrush(Qt.BrushStyle.NoBrush)
                painter.drawPath(line)
            else:
                mouth = QPainterPath(QPointF(*top[0]))
                for x, y in top[1:]:
                    mouth.lineTo(x, y)
                for x, y in reversed(bottom[:-1]):
                    mouth.lineTo(x, y)
                mouth.closeSubpath()
                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(MOUTH)
                painter.drawPath(mouth)
                gap = bottom[len(bottom) // 2][1] - top[len(top) // 2][1]
                if gap > 0.12 * R:
                    painter.save()
                    painter.setClipPath(mouth)
                    painter.setBrush(TONGUE)
                    ty = bottom[len(bottom) // 2][1]
                    painter.drawEllipse(QPointF(0.0, ty), w * 0.6, gap * 0.42)
                    painter.restore()
                painter.setPen(ink_pen)
                painter.setBrush(Qt.BrushStyle.NoBrush)
                painter.drawPath(mouth)
        if ex.mouth_round > 0.01:
            painter.setOpacity(ex.mouth_round)
            painter.setPen(ink_pen)
            painter.setBrush(MOUTH)
            painter.drawEllipse(QPointF(0.0, 0.06 * R), o_rx, o_ry)
        painter.restore()
