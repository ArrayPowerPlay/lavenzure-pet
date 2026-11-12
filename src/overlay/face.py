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
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen

from overlay.flame_common import (
    FACE_CY,
    FACE_RX,
    FACE_RY,
    approach,
    clamp,
    lerp,
    noise1,
    smoothstep,
)

INK = QColor(108, 14, 22)            # dark maroon used for every face line
EYE_WHITE = QColor(255, 253, 244)
PUPIL = QColor(96, 10, 20)
MOUTH = QColor(206, 30, 42)
THROAT = QColor(150, 16, 30)
TONGUE = QColor(244, 112, 112)


class Mood(Enum):
    """Facial expression / energy level the character is showing."""

    NORMAL = auto()
    HAPPY = auto()       # two looks, picked at random: sly side-glance grin / beaming upward
    SURPRISED = auto()
    SCARED = auto()      # fire bursts big and boxy, tiny pupils, huge open mouth
    ANGRY = auto()       # brows down, narrowed eyes, shouting, fire flares out at the sides
    CHILL = auto()       # flattened and relaxed under a frying pan (the pan is a prop)
    ALERT = auto()
    THINKING = auto()
    TALKING = auto()
    SLEEP = auto()       # closed smiling eyes, low wide flame, slow breathing
    YAWN = auto()        # on the way to sleep
    WAKE = auto()        # just woke up: eyes pop open, a little stretch
    FLY = auto()         # riding the log through the air (calm, content)
    TAKEOFF = auto()     # the moment the log is summoned (excited)
    YUCK = auto()        # fig. 8: wonky, mismatched eyes, a wide grimace with the tongue out


@dataclass
class Expression:
    """Continuous face (and flame) parameters; every mood is one target set."""

    eye_open: float = 1.0      # upper lid: 1 = fully open, 0 = closed
    lower_lid: float = 0.0     # 1 = cheeks push the lower lid up (smiling / squinting eyes)
    eye_scale: float = 1.0     # overall eye size
    eye_wide: float = 1.0      # horizontal stretch of the eyes (sly / sleepy looks are wide)
    eye_y: float = 0.0         # moves the eyes down (+) or up (-), in R
    gaze_x: float = 0.0        # forced look direction (-1..1, x right, y down) ...
    gaze_y: float = 0.0
    gaze_lock: float = 0.0     # ... and how strongly it overrides cursor tracking (0..1)
    brow: float = 0.0          # 1 = angry brows slanting down to the nose, -1 = worried brows
    pupil: float = 1.0         # pupil size relative to the eye
    pupil_in: float = 0.0      # pulls both pupils toward the nose (a fierce, focused glare)
    happy_eyes: float = 0.0    # 1 = closed "^ ^" smiling eyes
    slant: float = 0.0         # +1 = lids slope down toward the nose (cross), -1 = up (worried)
    almond: float = 0.0        # 1 = almond / lens-shaped eye: low arched top, pointed corners
    eye_wonk: float = 0.0      # 1 = mismatched, lopsided eyes: one squints, one bulges (fig. 8)
    mouth_open: float = 0.0    # 0 = closed line, 1 = wide open
    smile: float = 0.5         # -1 = frown, 1 = big smile
    mouth_round: float = 0.0   # 1 = round "o" mouth
    mouth_width: float = 1.0   # width multiplier
    mouth_wave: float = 0.0    # 1 = wobbly, worried mouth line
    mouth_top: float = 0.3     # open mouth: upper lip arch (0 = flat "D", 1 = oval, >1 = scream)
    mouth_bottom: float = 1.0  # open mouth: how deep the lower lip hangs
    mouth_dip: float = 0.0     # pushes the middle of the upper lip down (a soft "m" top)
    mouth_cat: float = 0.0     # lifts the middle of a closed mouth: a relaxed "w" line
    smirk: float = 0.0         # -1..1: lifts the left / right mouth corner
    mouth_curl: float = 0.0    # closed smile: both ends curl up into small dimples (fig. 7)
    mouth_tilt: float = 0.0    # extra rotation of the mouth alone (radians, lopsided grimace)
    tongue_out: float = 0.0    # 1 = the tongue sticks out over one corner of the lower lip
    tilt: float = 0.0          # head tilt in radians (positive = clockwise)
    flame: float = 1.0         # flame height multiplier
    flicker: float = 1.0       # flicker speed multiplier
    wild: float = 1.0          # flicker strength and how often the flame flares up
    alert: float = 0.0         # 0 = calm palette, 1 = alert palette
    shake: float = 0.0         # nervous horizontal jitter
    body_w: float = 1.0        # body shape: width / height multipliers (feet stay put) ...
    body_h: float = 1.0
    boxy: float = 0.0          # ... round (0) to almost rectangular (1) ...
    jag: float = 0.0           # ... smooth (0) to ragged, bursting edges all round (1) ...
    snooze: float = 0.0        # 1 = slow sleepy breathing (and floating "z"s)


# Each mood is one target expression, or several variants of which one is picked at random every
# time the mood starts (``happy``: the reference sheet's sly side-glance grin and upward beam).
MOOD_TARGETS: dict[Mood, tuple[Expression, ...]] = {
    Mood.NORMAL: (Expression(),),
    Mood.HAPPY: (
        # fig. 1 - sly: wide almond eyes (a low arched top, a round bottom, pointed corners),
        # big pupils tucked under the top edge glancing sideways; a soft, round open grin
        Expression(almond=1.0, eye_wide=1.3, eye_scale=1.1, pupil=1.0, eye_y=-0.05,
                   gaze_x=0.55, gaze_y=-0.55, gaze_lock=1.0, mouth_open=1.1, smile=0.3,
                   mouth_width=1.6, mouth_top=0.8, mouth_bottom=1.0, mouth_dip=0.0,
                   flame=0.95, flicker=1.35, wild=1.3, body_w=1.1, body_h=0.98),
        # fig. 2 - beaming: round eyes rolled up to one side, a wide rounded "D" smile
        Expression(eye_scale=1.08, pupil=0.72, gaze_x=-0.6, gaze_y=-0.8, gaze_lock=1.0,
                   mouth_open=0.95, smile=0.5, mouth_width=1.75, mouth_top=0.18,
                   mouth_bottom=1.0, mouth_dip=0.2, flame=1.0, flicker=1.4, wild=1.4,
                   body_w=1.04, body_h=1.03),
    ),
    Mood.SURPRISED: (Expression(eye_scale=1.2, pupil=0.6, mouth_open=0.55, smile=0.0,
                                mouth_round=1.0, flame=1.12, flicker=1.7, wild=1.6,
                                body_h=1.08, body_w=0.97),),
    # fig. 3 - eyes wide apart with tiny pupils, a huge scream: the upper lip arches high, the
    # lower one hangs shallow
    Mood.SCARED: (Expression(eye_scale=1.2, pupil=0.4, gaze_lock=1.0, eye_y=-0.16,
                             mouth_open=1.15, smile=-0.45, mouth_width=2.5, mouth_top=1.1,
                             mouth_bottom=1.0, flame=0.85,
                             flicker=1.7, wild=1.5, shake=0.45, body_w=1.22, body_h=1.1,
                             boxy=0.7, jag=1.0),),
    # fig. 6 body + a fierce face: lids cut down toward the nose, pupils staring straight
    # ahead, a big shouting mouth - wide open, a flat, gently rounded upper lip, a deep round
    # jaw (no pointed peak anywhere)
    Mood.ANGRY: (Expression(eye_open=1.0, eye_scale=1.05, eye_wide=1.1, pupil=0.55, slant=0.85,
                            eye_y=-0.1,
                            gaze_x=0.0, gaze_y=0.0, gaze_lock=1.0, mouth_open=1.55,
                            smile=-0.15, mouth_width=2.4, mouth_top=0.3, mouth_bottom=1.6,
                            mouth_dip=0.0,
                            flame=1.1, flicker=1.9, wild=1.3, alert=0.45, shake=0.35,
                            body_w=1.1, body_h=1.02),),
    # fig. 7 - lazy, content: wide almond eyes, big pupils glancing to the side right under
    # their top edge, head tipped a little; one long, gentle closed smile whose ends curl up
    # into small dimples
    Mood.CHILL: (Expression(almond=1.0, eye_scale=1.0, eye_wide=1.3,
                            slant=0.0, pupil=1.15, gaze_x=0.85, gaze_y=-0.55, gaze_lock=1.0,
                            eye_y=0.0, tilt=-0.05, smile=0.6, mouth_curl=1.0,
                            mouth_width=2.2, flame=0.45, flicker=0.65, wild=0.6,
                            body_w=1.32, body_h=0.72, boxy=0.35, jag=0.7),),
    Mood.ALERT: (Expression(eye_scale=1.05, pupil=0.78, slant=1.0, mouth_open=0.9, smile=-0.8,
                            mouth_width=1.1, flame=1.12, flicker=2.0, wild=1.9, alert=1.0,
                            shake=1.0),),
    Mood.THINKING: (Expression(eye_open=0.72, smile=0.15, smirk=0.55, mouth_width=0.75,
                               tilt=0.08, flame=0.9, flicker=0.6, wild=0.55),),
    Mood.TALKING: (Expression(smile=0.6, flame=1.05, flicker=1.25, wild=1.15),),
    Mood.SLEEP: (Expression(happy_eyes=1.0, eye_y=0.07, eye_wide=1.05, smile=0.55,
                            mouth_width=0.85, flame=0.5, flicker=0.42, wild=0.4, body_w=1.14,
                            body_h=0.85, snooze=1.0),),
    # Yawning: the eyes squeeze shut once, slowly, into the same closed arcs the sleeping face
    # keeps - so they never open again on the way to sleep.
    Mood.YAWN: (Expression(mouth_round=1.0, mouth_open=1.15, happy_eyes=1.0, eye_y=0.04,
                           flame=0.85, flicker=0.6, wild=0.55, body_w=0.96, body_h=1.08,
                           tilt=-0.06),),
    Mood.WAKE: (Expression(eye_scale=1.14, pupil=0.72, mouth_round=0.7, mouth_open=0.3,
                           smile=0.2, flame=1.15, flicker=1.4, wild=1.3, body_w=0.95,
                           body_h=1.1),),
    Mood.FLY: (Expression(pupil=0.9, mouth_open=0.62, smile=0.4, mouth_width=1.25,
                          mouth_top=0.55, mouth_dip=0.6, flame=1.05,
                          flicker=1.1, wild=1.05),),
    Mood.TAKEOFF: (Expression(eye_scale=1.14, pupil=0.72, gaze_lock=0.6, mouth_open=0.85,
                              smile=0.3, mouth_width=1.5, mouth_top=0.5, mouth_dip=0.25,
                              flame=1.1, flicker=1.6, wild=1.3,
                              body_h=1.04),),
    # fig. 8 - "yuck": lopsided eyes (one squints under a low lid, the other bulges, tilted and
    # egg-shaped, pupils crossing toward the nose), a wide wobbly grimace tipped to one side
    # with the tongue hanging out of the lower corner
    Mood.YUCK: (Expression(eye_wonk=1.0, eye_scale=1.0, eye_wide=1.3, pupil=0.62, eye_y=-0.07,
                           gaze_lock=1.0, mouth_open=1.05, smile=-0.25, mouth_width=2.3,
                           mouth_top=0.6, mouth_bottom=1.0, mouth_wave=0.35, mouth_tilt=0.1,
                           tongue_out=1.0,
                           flame=1.0, flicker=1.3, wild=1.2, shake=0.15, body_w=1.06,
                           body_h=0.98),),
}

# Small expressions the idle face drifts through: name -> (weight, (min, max) seconds, values).
MICRO_EXPRESSIONS: dict[str, tuple[float, tuple[float, float], dict[str, float]]] = {
    "content": (3.0, (1.8, 3.4), {"lower_lid": 0.5, "smile": 0.9}),
    "smirk": (2.0, (1.0, 2.0), {"smirk": 0.8, "eye_open": 0.82, "smile": 0.45}),
    "pout": (1.2, (0.8, 1.5), {"mouth_round": 0.95, "mouth_open": 0.1, "mouth_width": 0.7,
                               "smile": 0.0}),
    "sleepy": (1.2, (2.0, 3.6), {"eye_open": 0.5, "smile": 0.3}),
    "worried": (1.0, (1.2, 2.0), {"slant": -0.7, "mouth_wave": 1.0, "smile": -0.15}),
    "yawn": (0.45, (1.9, 2.6), {"mouth_round": 1.0, "mouth_open": 1.0, "eye_open": 0.12,
                                "slant": -0.3}),
}

MOUTH_FIELDS = frozenset({"mouth_open", "smile", "mouth_round", "mouth_width", "mouth_wave",
                          "smirk", "mouth_top", "mouth_bottom", "mouth_dip", "mouth_cat",
                          "mouth_curl", "mouth_tilt", "tongue_out"})
# Parameters that blend with an under-damped spring (a little overshoot = "pop"), as
# (stiffness, damping). The body is softer and wobblier than the face: it puffs up like jelly.
SPRUNG_FIELDS: dict[str, tuple[float, float]] = {
    "eye_scale": (240.0, 21.0), "pupil": (240.0, 21.0), "mouth_open": (240.0, 21.0),
    "mouth_round": (170.0, 22.0),
    "smile": (240.0, 21.0), "mouth_width": (240.0, 21.0), "lower_lid": (240.0, 21.0),
    "eye_wide": (240.0, 21.0), "brow": (260.0, 20.0),
    "body_w": (150.0, 12.5), "body_h": (150.0, 12.5),
}
# Parameters that switch between two different drawings are cross-faded quickly, so the two
# shapes are never seen as a ghostly double for long.
FAST_FIELDS = frozenset({"happy_eyes"})

# Slow fields: the fire's shape settles calmly instead of snapping (e.g. going to sleep).
SLOW_FIELDS = frozenset({"boxy", "jag", "snooze"})
# Falling asleep: the body sinks slowly into its low, wide sleeping shape instead of popping.
BODY_FIELDS = frozenset({"body_w", "body_h"})
DROWSY_MOODS = frozenset({Mood.SLEEP, Mood.YAWN})
# While dozing off these follow slowly too: heavy lids, the head tipping, the mouth relaxing.
DROWSY_SLOW_FIELDS = frozenset({"eye_open", "slant", "eye_y", "tilt", "happy_eyes",
                                "mouth_wave", "smirk"})
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
        # Velocities: of the springy fields, and of the eased fields (``_ease_vel``).
        self._vel: dict[str, float] = {name: 0.0 for name in SPRUNG_FIELDS}
        self._ease_vel: dict[str, float] = {f.name: 0.0 for f in fields(Expression)}
        self._mood = Mood.NORMAL
        self._goal = MOOD_TARGETS[Mood.NORMAL][0]        # the variant picked for the mood
        self._mouth_goal = self._goal                    # ... which the mouth follows later
        self._mouth_switch_at: float | None = None
        self._talk_until = -1.0

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
        # Lopsided looks (side glance, tongue out, wonky eyes) are mirrored at random: +1 = as
        # authored, -1 = flipped left/right.
        self._mirror = 1.0

        # Set by the character every frame: how far the whole face is raised (R; e.g. sitting
        # on the log, so the paws never cover the mouth) and the lowest point the mouth may
        # reach (body pixels, ``None`` = no limit).
        self.lift = 0.0
        self.floor_y: float | None = None

    # ------------------------------------------------------------------ simulation

    @property
    def mood(self) -> Mood:
        """The mood the face is currently showing (or blending toward)."""
        return self._mood

    def set_mood(self, mood: Mood) -> None:
        """Switch the target mood (called every frame; only real changes do anything)."""
        if mood == self._mood:
            return
        self._start_mood(mood)

    def restart_mood(self, mood: Mood) -> None:
        """Start ``mood`` again even if it is already showing (picks a fresh variant and gives
        the anticipation kick again, e.g. when the pet is clicked twice)."""
        self._start_mood(mood)

    def talk(self, seconds: float) -> None:
        """Move the mouth like speaking for ``seconds``, on top of whatever expression is shown."""
        self._talk_until = max(self._talk_until, self._t + seconds)

    def _start_mood(self, mood: Mood) -> None:
        """Pick a variant of ``mood``, schedule the mouth to follow, and kick the springs."""
        self._mood = mood
        variants = MOOD_TARGETS[mood]
        goal = self._rng.choice(variants) if len(variants) > 1 else variants[0]
        # Mirror lopsided looks at random (glance left or right, tongue out of either corner).
        self._mirror = self._rng.choice((-1.0, 1.0))
        if self._mirror < 0.0:
            goal = replace(goal, gaze_x=-goal.gaze_x, tilt=-goal.tilt, smirk=-goal.smirk,
                           mouth_tilt=-goal.mouth_tilt)
        self._goal = goal
        self._mouth_switch_at = self._t + MOUTH_DELAY
        self._micro = None
        vel = self._vel
        # Anticipation: squeeze a little the "wrong" way first, then the spring pops past.
        if mood == Mood.SURPRISED:
            vel["eye_scale"] -= 2.5
            vel["mouth_open"] -= 2.0
            vel["body_h"] -= 1.2
        elif mood == Mood.HAPPY:
            vel["lower_lid"] += 4.0
            vel["body_w"] += 0.8
        elif mood == Mood.ALERT:
            vel["eye_scale"] += 4.0
        elif mood == Mood.SCARED:
            vel["eye_scale"] -= 3.0      # eyes squeeze, then pop wide
            vel["body_h"] -= 1.5         # a flinch down before the fire bursts up
            vel["body_w"] -= 1.0
        elif mood == Mood.ANGRY:
            vel["body_h"] -= 1.8         # crouch / wind up before flaring
            vel["brow"] += 3.0
        elif mood == Mood.WAKE:
            vel["eye_scale"] += 2.5
            vel["body_h"] += 1.2
        elif mood == Mood.TAKEOFF:
            vel["body_h"] -= 1.2
            vel["eye_scale"] += 2.0
        elif mood == Mood.CHILL:
            vel["body_h"] -= 1.0         # flops down under the pan
        elif mood == Mood.YUCK:
            vel["body_h"] -= 1.2         # recoils
            vel["eye_scale"] -= 1.5

    def update(self, dt: float, cursor: QPointF | None, body_vy: float) -> None:
        """Advance ``dt`` seconds. ``cursor`` is the mouse relative to the face centre (pixels,
        or ``None``); ``body_vy`` is the body's vertical speed in R/s (for the lagging face)."""
        self._t += dt
        if self._mouth_switch_at is not None and self._t >= self._mouth_switch_at:
            self._mouth_goal = self._goal
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
        mouth_goal = self._mouth_goal
        goal = replace(self._goal, **{name: getattr(mouth_goal, name) for name in MOUTH_FIELDS})
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
            spring = SPRUNG_FIELDS.get(name)
            if spring is not None:
                stiffness, damping = spring
                if name in BODY_FIELDS and self._mood in DROWSY_MOODS:
                    stiffness, damping = 22.0, 8.0     # melt down slowly when dozing off
                vel = self._vel[name]
                vel += (stiffness * (goal - current) - damping * vel) * dt
                self._vel[name] = vel
                setattr(self.expr, name, current + vel * dt)
            else:
                rate = 20.0 if name in FAST_FIELDS else 2.5 if name in SLOW_FIELDS else 9.0
                if self._mood in DROWSY_MOODS and name in DROWSY_SLOW_FIELDS:
                    rate = min(rate, 2.4)          # lids droop and the face relaxes slowly
                # Critically damped easing (no overshoot): unlike a plain exponential approach
                # it starts gently instead of jumping off at full speed, so a change of mood
                # eases in and out (this was the "not smooth" feel of falling asleep / waking).
                omega = 1.7 * rate
                vel = self._ease_vel[name]
                steps = max(1, math.ceil(omega * dt / 0.4))   # stays stable on a slow frame
                h = dt / steps
                for _ in range(steps):
                    vel += (omega * omega * (goal - current) - 2.0 * omega * vel) * h
                    current += vel * h
                self._ease_vel[name] = vel
                setattr(self.expr, name, current)

        if self._mood == Mood.TALKING or self._t < self._talk_until:
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
        if self._mood in DROWSY_MOODS or self.expr.happy_eyes > 0.3:
            # Dozing off / closed smiling eyes: no blinks, the eyes close once and stay shut.
            self._next_blink = max(self._next_blink, self._t + 0.8)
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
        drowsy = self._mood in DROWSY_MOODS
        if drowsy:
            # Dozing off / asleep: the closed eyes (and the head turn that follows them) settle
            # facing forward; the mouse and the small fixation jumps below are ignored.
            self._jitter = (0.0, 0.0)
        elif self._mood == Mood.THINKING:
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
        # Expressions with a set look (sly side-glance, beaming up) override the free gaze.
        lock = clamp(self.expr.gaze_lock, 0.0, 1.0)
        target_x = lerp(target_x, self.expr.gaze_x, lock) + self._jitter[0] * (1.0 - 0.6 * lock)
        target_y = lerp(target_y, self.expr.gaze_y, lock) + self._jitter[1] * (1.0 - 0.6 * lock)
        # Saccade: a far target is reached with one quick dart; near ones are followed smoothly.
        gap = math.hypot(target_x - self._look_x, target_y - self._look_y)
        if gap > 0.25:
            self._saccade = True
        elif gap < 0.03:
            self._saccade = False
        rate = 2.5 if drowsy else 30.0 if self._saccade else 11.0
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
        ex = self.expr
        lock = clamp(ex.gaze_lock, 0.0, 1.0)
        turn = self._look_x * 0.38 * (1.0 - 0.7 * lock)   # set looks are eyes-only, not the head
        nod = self._look_y * 0.08 * (1.0 - 0.7 * lock)
        theta0 = x / SPHERE_R
        theta = clamp(theta0 + turn, -1.3, 1.3)
        fx = SPHERE_R * math.sin(theta)
        squeeze = math.cos(theta) / max(0.2, math.cos(theta0))
        fy = y + nod
        tilt = ex.tilt
        ct, st = math.cos(tilt), math.sin(tilt)
        rx, ry = fx * ct - fy * st, fx * st + fy * ct
        return rx * R, (ry - self._face_cy() - self.lift + self._lag) * R, squeeze

    def _face_cy(self) -> float:
        """Height of the face centre above the feet (R); it rides up/down with the body height."""
        return FACE_CY * self.expr.body_h

    def _spread(self) -> float:
        """How far apart features sit: a wider (or boxier) body spreads the face a little."""
        return 1.0 + 0.45 * (self.expr.body_w - 1.0) + 0.3 * self.expr.boxy

    def _fit(self, cx: float, cy: float, pts: list[tuple[float, float]]) -> float:
        """Largest scale (<= 1) about (``cx``, ``cy``) that keeps ``pts`` (body pixels, relative to
        that centre) inside the face safe area."""
        R = self.R
        bw, bh = self.expr.body_w, self.expr.body_h
        ex, ey = 0.0, -(self._face_cy() + self.lift) * R
        ax, ay = FACE_RX * bw * R, FACE_RY * bh * R
        # A boxy body has more room in its corners, so the face may grow wider and taller.
        ax *= 1.0 + 0.6 * self.expr.boxy
        ay *= 1.0 + 0.35 * self.expr.boxy
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
        """Draw both eyes, the brows (if any) and the mouth (painter in body coordinates)."""
        for side in (-1, 1):
            self._paint_eye(painter, side)
        if abs(self.expr.brow) > 0.03:
            for side in (-1, 1):
                self._paint_brow(painter, side)
        self._paint_mouth(painter)

    def _eye_tweak(self, side: int) -> tuple[float, float, float, float, float, float, float]:
        """Per-eye changes for the lopsided ``eye_wonk`` look (fig. 8), all fading with it:
        (size, upper-lid limit, extra slant, rotation in radians, pupil x / y offsets as
        fractions of the eye radii, egg-shape amount). One eye squints under a low, slightly
        slanted lid with its pupil pushed up toward the nose; the other bulges, egg-shaped and
        tipped, its pupil also turned toward the nose (they cross)."""
        w = clamp(self.expr.eye_wonk, 0.0, 1.0)
        if w < 0.005:
            return 1.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0
        inward = -side                       # toward the nose
        if side == -int(self._mirror):       # the squinting eye
            return (1.0 - 0.04 * w, lerp(1.0, 0.86, w), 0.5 * w, 0.0,
                    inward * 0.1 * w, -0.3 * w, 0.3 * w)
        return (1.0 + 0.15 * w, 1.0, -0.1 * w, -side * 0.24 * w,
                inward * 0.38 * w, 0.08 * w, w)

    def _eye_geom(self, side: int) -> tuple[float, float, float, float]:
        """Centre (body pixels) and radii of one eye after the safe-area fit."""
        R = self.R
        ex = self.expr
        size = self._eye_tweak(side)[0]
        cx, cy, squeeze = self._place(side * EYE_X * self._spread(), EYE_Y + ex.eye_y)
        rx = EYE_RX * R * ex.eye_scale * ex.eye_wide * squeeze * size
        ry = EYE_RY * R * ex.eye_scale * size
        angles = (i * math.tau / 12 for i in range(12))
        k = self._fit(cx, cy, [(rx * math.cos(a), ry * math.sin(a)) for a in angles])
        return cx, cy, rx * k, ry * k

    def eye_top(self) -> float:
        """Highest point of the eyes (body pixels), e.g. so the frying pan sits above them."""
        return min(cy - ry for cx, cy, rx, ry in (self._eye_geom(-1), self._eye_geom(1)))

    def _paint_brow(self, painter: QPainter, side: int) -> None:
        """A thick, tapered brow (heavy at the nose end, thin at the outer end) floating a clear
        gap above the eye. ``brow`` > 0 follows the angry lid down toward the nose; < 0 lifts the
        inner end (worried)."""
        R = self.R
        ex = self.expr
        amount = clamp(ex.brow, -1.0, 1.2)
        cx, cy, rx, ry = self._eye_geom(side)
        lid_open = clamp(ex.eye_open, 0.0, 1.0)
        lid_y = -ry + 2.0 * ry * (1.0 - lid_open) * 0.85
        if amount >= 0.0:
            slant = max(ex.slant, 0.0)
            ix, iy = -side * rx * 1.35, lid_y + slant * ry * 0.95
            ox, oy = side * rx * 1.35, lid_y - slant * ry * 0.1
            extra = 0.18 * ry * amount            # brows press down a bit more than the lid
        else:
            ix, iy = -side * rx * 1.35, -ry - 0.4 * ry * -amount
            ox, oy = side * rx * 1.35, -ry + 0.05 * ry
            extra = 0.0
        gap = 0.1 * R + 0.12 * ry

        def line_y(x: float) -> float:
            """Height of the lid line at ``x`` (eye-local pixels)."""
            return iy + (oy - iy) * (x - ix) / (ox - ix)

        x_in, x_out = -side * rx * 1.02, side * rx * 0.98
        lower, upper = [], []
        n = 10
        for i in range(n + 1):
            t = i / n
            x = lerp(x_in, x_out, t)
            y = line_y(x) - gap + extra * (1.0 - t) - 0.05 * R * math.sin(math.pi * t)
            thick = lerp(0.15, 0.05, t ** 0.8) * R * min(1.0, 0.4 + 0.6 * abs(amount))
            lower.append(QPointF(x, y))
            upper.append(QPointF(x + side * 0.01 * R, y - thick))
        path = QPainterPath(lower[0])
        for pt in lower[1:]:
            path.lineTo(pt)
        for pt in reversed(upper):
            path.lineTo(pt)
        path.closeSubpath()
        painter.save()
        painter.translate(cx, cy)
        painter.rotate(math.degrees(ex.tilt))
        painter.setOpacity(painter.opacity() * smoothstep(0.03, 0.4, abs(amount)))
        painter.setPen(QPen(INK, 0.03 * R, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap,
                            Qt.PenJoinStyle.RoundJoin))
        painter.setBrush(INK)
        painter.drawPath(path)
        painter.restore()

    def _paint_eye(self, painter: QPainter, side: int) -> None:
        """One eye: outlined white with a tracking pupil, cut by the lids - or, once closed, a
        single line that bends from a relaxed closed lid into the smiling "^" arc (one shape
        morphing, never two drawings cross-fading, so closing reads as one smooth motion)."""
        R = self.R
        ex = self.expr
        cx, cy, rx, ry = self._eye_geom(side)
        tweak = self._eye_tweak(side)

        # Going "^ ^": the open eye squeezes shut first, then the closed line bends into the arc.
        squint = 1.0 - smoothstep(0.0, 0.6, ex.happy_eyes)
        blink = self._blink_factor()
        openness = clamp(blink * squint, 0.0, 1.0)
        lid_open = min(clamp(ex.eye_open, 0.0, 1.0), tweak[1])

        painter.save()
        painter.translate(cx, cy)
        painter.rotate(math.degrees(ex.tilt + tweak[3]))
        if openness * lid_open > 0.1:
            self._paint_open_eye(painter, side, rx, ry, openness, lid_open, tweak)
        else:
            arc = smoothstep(0.45, 0.8, ex.happy_eyes)
            end_y = lerp(0.0, ry * 0.3, arc)
            line = QPainterPath(QPointF(-rx, end_y))
            line.quadTo(QPointF(0.0, lerp(ry * 0.4, -ry * 0.85, arc)), QPointF(rx, end_y))
            painter.setPen(QPen(INK, 0.065 * R, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap,
                                Qt.PenJoinStyle.RoundJoin))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawPath(line)
        painter.restore()

    @staticmethod
    def _eye_outline(rx: float, ry: float, cy: float, egg: float,
                     almond: float = 0.0) -> QPainterPath:
        """The white of the eye: an ellipse; for ``almond`` > 0 it morphs into a lens shape
        (figs. 1 and 7: a low, gently arched top edge, a round bottom, pointed corners); for
        ``egg`` > 0 a lopsided egg (narrower on top, a slight dent). Always one smooth closed
        curve."""
        path = QPainterPath()
        if almond > 0.01:
            # Each edge is h * (1 - u^2)^p: p = 0.5 is the ellipse, p near 1 gives the corners
            # a point. Sampled densely toward the corners (u = -cos(theta)).
            top_h = ry * lerp(1.0, 0.42, almond)
            bot_h = ry * lerp(1.0, 0.88, almond)
            p_top, p_bot = lerp(0.5, 1.0, almond), lerp(0.5, 0.78, almond)
            shift = -0.3 * (bot_h - top_h)        # keep the eye roughly where it was
            n = 40
            pts = []
            for i in range(n + 1):
                u = -math.cos(math.pi * i / n)
                pts.append(QPointF(u * rx, cy + shift - top_h * (1.0 - u * u) ** p_top))
            for i in range(1, n):
                u = math.cos(math.pi * i / n)
                pts.append(QPointF(u * rx, cy + shift + bot_h * (1.0 - u * u) ** p_bot))
            path.moveTo(pts[0])
            for pt in pts[1:]:
                path.lineTo(pt)
            path.closeSubpath()
            return path
        if egg < 0.01:
            path.addEllipse(QPointF(0.0, cy), rx, ry)
            return path
        n = 24
        pts = []
        for i in range(n):
            a = i * math.tau / n
            wobble = 1.0 + 0.05 * egg * math.cos(3.0 * a + 1.1)
            x = rx * math.cos(a) * (1.0 + 0.12 * egg * math.sin(a)) * wobble
            y = ry * math.sin(a) * wobble
            pts.append(QPointF(x, cy + y))
        mid = [QPointF((pts[i].x() + pts[(i + 1) % n].x()) / 2,
                       (pts[i].y() + pts[(i + 1) % n].y()) / 2) for i in range(n)]
        path.moveTo(mid[-1])
        for i in range(n):
            path.quadTo(pts[i], mid[i])
        path.closeSubpath()
        return path

    def _paint_open_eye(self, painter: QPainter, side: int, rx: float, ry: float,
                        openness: float, lid_open: float,
                        tweak: tuple[float, float, float, float, float, float, float]) -> None:
        """White eye (squashed by the blink), clipped by the upper and lower lids, with pupil."""
        R = self.R
        ex = self.expr
        ry_b = ry * openness
        cy = ry * (1.0 - openness) * 0.5  # blinking eyes close toward their lower half
        eye = self._eye_outline(rx, ry_b, cy, tweak[6], clamp(ex.almond, 0.0, 1.0))

        # Upper lid: a straight edge that drops with ``eye_open`` and tilts with ``slant``.
        slant = ex.slant + tweak[2]
        lid_y = cy - ry_b + 2.0 * ry_b * (1.0 - lid_open) * 0.85
        if slant >= 0.0:
            inner_y, outer_y = lid_y + slant * ry_b * 0.95, lid_y - slant * ry_b * 0.1
        else:
            inner_y, outer_y = lid_y + slant * ry_b * 0.25, lid_y - slant * ry_b * 0.75
        inner_x, outer_x = -side * rx * 1.35, side * rx * 1.35
        lid_line = QPainterPath(QPointF(inner_x, inner_y))
        lid_line.lineTo(QPointF(outer_x, outer_y))
        lid_cut = lid_open < 0.97 or abs(slant) > 0.03
        if lid_cut:
            top = cy - 3 * ry
            cut = QPainterPath(lid_line)
            cut.lineTo(QPointF(outer_x, top))
            cut.lineTo(QPointF(inner_x, top))
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
        lock = clamp(ex.gaze_lock, 0.0, 1.0)
        pr = min(rx, EYE_RX * R * ex.eye_scale) * 0.56 * ex.pupil
        # Pupils travel further when an expression sets the look (they touch the eye's edge).
        px = (self._look_x * rx * (0.5 + 0.18 * lock) - side * ex.pupil_in * rx * 0.42
              + tweak[4] * rx)
        py = (cy + self._look_y * ry_b * (0.42 + 0.22 * lock) + ry_b * 0.2 * max(0.0, slant)
              + tweak[5] * ry_b)
        painter.setBrush(PUPIL)
        painter.drawEllipse(QPointF(px, py), pr, pr * max(0.65, openness))
        painter.restore()

        if not lid_cut:
            return
        cross = smoothstep(0.25, 0.6, abs(slant))
        if cross > 0.01:
            # A cross / worried lid is a firm line running a bit past the eye, like a brow
            # (fig. a2: the thick lid line *is* the brow).
            painter.save()
            painter.setOpacity(painter.opacity() * cross)
            lid_pen = 0.075 * R * (1.0 + 0.45 * smoothstep(0.3, 0.9, slant))
            painter.setPen(QPen(INK, lid_pen, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            a, b = QPointF(inner_x, inner_y), QPointF(outer_x, outer_y)
            painter.drawLine(QPointF(lerp(a.x(), b.x(), 0.14), lerp(a.y(), b.y(), 0.14)),
                             QPointF(lerp(a.x(), b.x(), 0.9), lerp(a.y(), b.y(), 0.9)))
            painter.restore()

    def _mouth_curves(self, w: float) -> tuple[list[tuple[float, float]],
                                               list[tuple[float, float]], float]:
        """Top and bottom lip polylines (local pixels, origin = mouth centre, y down) and the
        largest gap between them.

        One shape family covers every mouth, so changing expression *morphs* the outline instead
        of cross-fading two drawings (which looked blurry and doubled):

        - a centre line (smile / frown curve, wobble, smirk, cat-like "w" bump) that is the whole
          mouth when it is closed;
        - when open, a rounded superellipse grows around that line: ``mouth_top`` sets how high
          the upper lip arches (0 = flat "D" top, 1 = oval, more = scream arch), ``mouth_bottom``
          how deep the lower lip hangs, ``mouth_dip`` pushes the middle of the upper lip down;
        - ``mouth_round`` pulls all of that toward a small round "o".
        """
        R = self.R
        ex = self.expr
        open_amount = clamp(ex.mouth_open + self._talk_amount, 0.0, 1.2)
        rnd = clamp(ex.mouth_round, 0.0, 1.0)
        smile = clamp(ex.smile, -1.0, 1.2)
        # Round "o": its size grows with how open it is (a yawn is a big "O").
        o_size = 0.7 + 0.55 * open_amount + 0.9 * max(open_amount - 0.85, 0.0)
        o_half_w, o_half_h = 0.15 * R * o_size, 0.18 * R * o_size
        half_w = lerp(w, o_half_w, rnd)
        k_open = smoothstep(0.0, 0.35, open_amount)
        height = lerp(open_amount * 0.95 * w, 2.0 * o_half_h, rnd)   # full opening height
        top_k = lerp(ex.mouth_top, 1.0, rnd)
        bot_k = lerp(ex.mouth_bottom, 1.0, rnd)
        total = max(top_k + bot_k, 0.2)
        top_h, bot_h = height * top_k / total, height * bot_k / total
        dip = ex.mouth_dip * (1.0 - rnd)
        arch_e = lerp(lerp(2.4, 1.75, smoothstep(0.9, 1.3, top_k)), 2.0, rnd)
        prof_e = lerp(2.4, 2.0, rnd)          # a round "o" is a true ellipse
        # The centre line bends less once the mouth is open (big grins stay round, no horns).
        bend = (1.0 - 0.6 * k_open) * (1.0 - rnd)
        y_left = -max(-ex.smirk, 0.0) * 0.35 * w + max(ex.smirk, 0.0) * 0.08 * w
        y_right = -max(ex.smirk, 0.0) * 0.35 * w + max(-ex.smirk, 0.0) * 0.08 * w
        top, bottom = [], []
        n = 33
        for i in range(n):
            s = -1.0 + 2.0 * i / (n - 1)
            x = s * half_w
            bow = 1.0 - s * s
            centre = (bend * smile * w * (0.42 * bow - 0.3)
                      + lerp(y_left, y_right, (s + 1.0) * 0.5) * (1.0 - rnd)
                      + ex.mouth_wave * 0.09 * w * math.sin(3.0 * math.pi * s) * (1.0 - rnd)
                      - ex.mouth_cat * 0.13 * w * math.exp(-(s / 0.28) ** 2) * (1.0 - rnd))
            prof = (1.0 - abs(s) ** prof_e) ** (1.0 / prof_e)   # rounded, slightly square ends
            # A tall upper lip (scream) is a smooth arch rather than a box.
            prof_top = (1.0 - abs(s) ** arch_e) ** (1.0 / arch_e)
            upper = centre - top_h * prof_top + dip * top_h * 0.55 * math.exp(-(s / 0.3) ** 2)
            lower = centre + bot_h * prof
            top.append((x, upper))
            bottom.append((x, max(lower, upper)))
        gap = max(b[1] - t[1] for t, b in zip(top, bottom, strict=True))
        return top, bottom, gap

    def _eye_bottom(self) -> float:
        """Lowest point of the eyes (body pixels): the mouth must stay clear of it."""
        ex = self.expr
        _, cy, _ = self._place(EYE_X * self._spread(), EYE_Y + ex.eye_y)
        ry = EYE_RY * self.R * ex.eye_scale
        return cy + ry * lerp(1.0, 0.3, smoothstep(0.45, 0.75, ex.happy_eyes))

    def _paint_mouth(self, painter: QPainter) -> None:
        """One mouth outline that morphs between a closed line, an open smile / scream and a
        round "o": red inside, a darker throat at the top, a pink tongue, ink outline."""
        R = self.R
        ex = self.expr
        cx, cy, squeeze = self._place(0.0, MOUTH_Y * (0.85 + 0.15 * self.expr.body_h))
        w = MOUTH_W * R * ex.mouth_width * (1.0 + 0.15 * max(ex.smile, 0.0)) * squeeze
        top, bottom, gap = self._mouth_curves(w)
        angle = ex.tilt + ex.mouth_tilt
        ct, st = math.cos(angle), math.sin(angle)
        # (A closed line's curled corners count too, so they never touch the eyes.)
        outline = top + bottom if gap >= 0.02 * R else self._curled(top, w)
        pts = [(x * ct - y * st, x * st + y * ct) for x, y in outline]
        # The mouth hangs from its upper edge, a clear gap under the eyes (an open mouth grows
        # downward like in the reference art); the safe-area fit then scales it about that edge,
        # so it can never creep up onto the eyes. Only the part of the lip that is right below
        # an eye counts: between the eyes a screaming arch may rise higher (fig. 3).
        clearance = self._eye_bottom() + 0.14 * R
        right_cx, _, right_rx, _ = self._eye_geom(1)
        left_cx, _, left_rx, _ = self._eye_geom(-1)
        inner = 0.5 * (right_cx - left_cx) - 1.1 * max(right_rx, left_rx)
        under = [y for x, y in pts if abs(x) > inner]
        highest = min(under) if under else min(y for _, y in pts)
        k_open = smoothstep(0.02 * R, 0.25 * R, gap)
        top_y = max(clearance, lerp(cy + highest, clearance, k_open))
        pts = [(x, y - highest) for x, y in pts]
        k = self._fit(cx, top_y, pts)
        if self.floor_y is not None:
            # Never below the floor (sitting on the log: the paws and the log stay clear).
            depth = max(y for _, y in pts)
            if depth > 0.0 and top_y + depth * k > self.floor_y:
                k = clamp((self.floor_y - top_y) / depth, 0.35, k)
        cy = top_y - highest * k     # mouth centre after scaling about the upper edge

        pen_w = 0.062 * R
        ink_pen = QPen(INK, pen_w, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap,
                       Qt.PenJoinStyle.RoundJoin)
        painter.save()
        painter.translate(cx, cy)
        painter.rotate(math.degrees(angle))
        painter.scale(k, k)
        if gap < 0.02 * R:
            line = QPainterPath()
            for i, (x, y) in enumerate(self._curled(top, w)):
                if i == 0:
                    line.moveTo(x, y)
                else:
                    line.lineTo(x, y)
            painter.setPen(ink_pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawPath(line)
            painter.restore()
            return
        mouth = QPainterPath(QPointF(*top[0]))
        for x, y in top[1:]:
            mouth.lineTo(x, y)
        for x, y in reversed(bottom[1:-1]):
            mouth.lineTo(x, y)
        mouth.closeSubpath()
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(MOUTH)
        painter.drawPath(mouth)
        painter.save()
        painter.setClipPath(mouth)
        mid = len(top) // 2
        t_mid, b_mid = top[mid][1], bottom[mid][1]
        open_h = b_mid - t_mid
        # Darker throat along the upper lip gives the opening some depth.
        painter.setBrush(THROAT)
        throat = QPainterPath(QPointF(*top[0]))
        for x, y in top[1:]:
            throat.lineTo(x, y + 0.24 * open_h)
        for x, y in reversed(top):
            throat.lineTo(x, y - R)
        painter.drawPath(throat)
        # Tongue: a soft pink mound resting on the lower lip; it fades in as the mouth opens
        # and shrinks away for a small round "o".
        tongue_alpha = smoothstep(0.1 * R, 0.24 * R, open_h) * (1.0 - 0.6 * ex.mouth_round)
        if tongue_alpha > 0.01:
            painter.setOpacity(painter.opacity() * tongue_alpha)
            half = abs(top[-1][0])
            painter.setBrush(TONGUE)
            painter.drawEllipse(QPointF(0.0, b_mid + 0.05 * open_h), half * 0.62, open_h * 0.42)
        painter.restore()
        painter.setPen(ink_pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawPath(mouth)
        if ex.tongue_out > 0.02:
            self._paint_tongue_out(painter, mouth, top, bottom, ink_pen)
        painter.restore()

    def _curled(self, line: list[tuple[float, float]], w: float) -> list[tuple[float, float]]:
        """A closed mouth line with both ends continued into small hooks that curl up and back
        in (``mouth_curl``, the dimpled corners of fig. 7). The hooks keep turning gradually, so
        the stroke stays one smooth, unbroken line."""
        curl = clamp(self.expr.mouth_curl, 0.0, 1.0)
        if curl < 0.02 or len(line) < 2:
            return line
        steps = 14
        length = 0.17 * w * curl
        turn = 2.3 * curl

        def hook(end: tuple[float, float], before: tuple[float, float],
                 direction: float) -> list[tuple[float, float]]:
            """Points continuing from ``end`` (heading away from ``before``), turning upward."""
            heading = math.atan2(end[1] - before[1], end[0] - before[0])
            x, y = end
            out = []
            for _ in range(steps):
                heading += direction * turn / steps
                x += math.cos(heading) * length / steps
                y += math.sin(heading) * length / steps
                out.append((x, y))
            return out

        # The right end turns counter-clockwise on screen (up, then back in), the left end the
        # other way.
        right = hook(line[-1], line[-2], -1.0)
        left = hook(line[0], line[1], 1.0)
        return list(reversed(left)) + line + right

    def _paint_tongue_out(self, painter: QPainter, mouth: QPainterPath,
                          top: list[tuple[float, float]], bottom: list[tuple[float, float]],
                          ink_pen: QPen) -> None:
        """The tongue hanging out over the lower lip near one corner (fig. 8). It covers the
        lip line where it crosses it, and its own outline is only drawn outside the mouth, so it
        reads as coming out of the mouth rather than being stuck on top."""
        R = self.R
        amount = clamp(self.expr.tongue_out, 0.0, 1.0)
        side = self._mirror
        n = len(bottom)
        bx, by = bottom[int(round((0.5 + side * 0.32) * (n - 1)))]
        open_h = max(b[1] - t[1] for t, b in zip(top, bottom, strict=True))
        # A soft oval whose long axis points out of the corner and down.
        length = (0.17 * R + 0.15 * open_h) * amount
        width = 0.12 * R * amount
        tongue = QPainterPath()
        tongue.addEllipse(QPointF(0.0, 0.0), length, width)
        centre = QPointF(bx + side * 0.1 * R * amount, by + 0.01 * R * amount)
        angle = side * 32.0
        painter.save()
        painter.translate(centre)
        painter.rotate(angle)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(TONGUE)
        painter.drawPath(tongue)
        # The groove along the middle of the tongue.
        painter.setPen(QPen(THROAT, 0.03 * R, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        painter.drawLine(QPointF(-side * length * 0.2, 0.0), QPointF(side * length * 0.5, 0.0))
        painter.restore()
        # Its outline only outside the mouth opening.
        outside = QPainterPath()
        outside.addRect(mouth.boundingRect().adjusted(-R, -R, R, R))
        painter.save()
        painter.setClipPath(outside.subtracted(mouth))
        painter.translate(centre)
        painter.rotate(angle)
        painter.setPen(ink_pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawPath(tongue)
        painter.restore()
