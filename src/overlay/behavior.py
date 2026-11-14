"""Behavior state machine: drives autonomous movement and reacts to interaction events.

The pet wanders on its own (IDLE/WALK/FLOAT/JUMP picked at random, weights from ``config.yaml``)
unless something more important is going on. Priorities, highest first:

1. **DRAGGED** - the user is holding the pet.
2. **ALERT** - a system alert is waiting to be acknowledged (left-click clears it).
3. **REMIND** - a reminder is due: the pet stops where it is, the alarm clock rings beside it
   and it looks at the user until the pet is clicked (then a smiling "okay!" blink).
4. **REACT** - a short reaction to a left-click is playing (random pick from the reaction pool).
5. **CHAT** - the chat bubble is open: stand still beside it.
6. **SLEEP** - the user chose ``Idle`` in the right-click menu, or nobody has touched the
   computer for a while ("dozing"). The pet glides down to the ground and sleeps there.
7. Wandering.

Whenever one of these ends, ``_resume()`` picks the next thing from the same list, so e.g. a
sleeping pet woken up by a chat goes back to sleep once the chat closes.

The controller moves the window and tells the character which mood to show; the character
handles its own body language (lean, hop, squash) from the movement. Being in the air means
sitting on the flying log: it is summoned (with sparks) before a flight takes off from the
ground and crumbles into embers on landing.

**Reaction pool** - every reaction is a method decorated with ``@reaction("name")``; the
decorator registers it, so a new animation joins the left-click pool just by being defined here.
"""
from __future__ import annotations

import random
from collections.abc import Callable
from enum import Enum, auto

from PySide6.QtCore import QObject, QPoint, QTimer, Signal
from PySide6.QtGui import QGuiApplication

import config
from overlay.animation import jump_animation, move_to_animation, travel_duration_ms
from overlay.character import Mood
from overlay.overlay_window import OverlaySprite

WALK_SPEED_PX_S = 85.0
FLOAT_SPEED_PX_S = 120.0
SETTLE_SPEED_PX_S = 150.0     # gliding down to the ground to sleep...
SETTLE_MAX_MS = 3200          # ...but never longer than this, even from the top of the screen
TAKEOFF_DELAY_MS = 480        # the log appears and the pet gets excited before lifting off
NIGHT_SPEED = 0.7             # movement speed multiplier at night
NIGHT_IDLE = 1.5              # idle pauses get this much longer at night
OK_SECONDS = 1.0              # the smiling "okay!" blink after a reminder is acknowledged

# name -> unbound method returning the reaction length in seconds (None = it ends by itself).
REACTIONS: dict[str, Callable[[BehaviorController], float | None]] = {}


def reaction(name: str):
    """Decorator: register a ``BehaviorController`` method in the left-click reaction pool."""
    def register(method):
        """Store ``method`` under ``name`` and return it unchanged."""
        REACTIONS[name] = method
        return method
    return register


class PetState(Enum):
    """What the pet is currently doing."""

    IDLE = auto()
    WALK = auto()
    FLOAT = auto()
    JUMP = auto()
    DRAGGED = auto()
    REACT = auto()
    ALERT = auto()
    REMIND = auto()   # a reminder is due: standing still, the alarm clock ringing
    CHAT = auto()
    SETTLE = auto()   # gliding down to the ground before falling asleep
    SLEEP = auto()


def _state_weights() -> dict[PetState, float]:
    """Relative chance of each autonomous state, read from config (with sensible defaults)."""
    defaults = {"idle": 0.4, "walk": 0.25, "float": 0.25, "jump": 0.1}
    configured = config.get("behavior.state_weights", {}) or {}
    return {PetState[name.upper()]: float(configured.get(name, w)) for name, w in defaults.items()}


class BehaviorController(QObject):
    """Owns the current PetState and the window-movement animation currently playing."""

    speak_requested = Signal()   # the "say a random line" reaction was picked

    def __init__(self, sprite: OverlaySprite) -> None:
        """Attach to ``sprite``, create the state timers and start the random idle loop."""
        super().__init__()
        self.sprite = sprite
        self.character = sprite.character
        self.state = PetState.IDLE
        self._weights = _state_weights()
        self._active_anim = None

        # What is going on (see the priority list in the module docstring).
        self._dragging = False
        self._alert_active = False
        self._reminding = False
        self._reacting = False
        self._chatting = False
        self._resting = False     # user picked "Idle"
        self._dozing = False      # computer unused for a while
        self._night = False
        self._last_reaction: str | None = None

        # Dedicated single-shot timers (restartable, so a stale timeout can never fire twice).
        self._idle_timer = self._make_timer(self._advance)
        self._jump_delay = self._make_timer(self._launch_jump)
        self._takeoff_delay = self._make_timer(self._launch_float)
        self._react_timer = self._make_timer(self._end_reaction)
        self._pending_jump: tuple[QPoint, int] | None = None
        self._pending_float: QPoint | None = None

        # Sitting on the log whenever the pet is up in the air (checked a few times a second).
        self._ride_timer = QTimer(self)
        self._ride_timer.timeout.connect(self._update_riding)
        self._ride_timer.start(80)

        self.sprite.drag_started.connect(self._on_drag_started)
        self.sprite.drag_ended.connect(self._on_drag_ended)

        self._enter_idle()

    def _make_timer(self, slot) -> QTimer:
        """Create a single-shot timer owned by this controller."""
        timer = QTimer(self)
        timer.setSingleShot(True)
        timer.timeout.connect(slot)
        return timer

    # ------------------------------------------------------------------ geometry

    def screen_rect(self):
        """Usable area of the primary screen (excludes the taskbar)."""
        return QGuiApplication.primaryScreen().availableGeometry()

    def _ground_y(self) -> int:
        """Window y at which the character's feet rest on the bottom of the usable area."""
        return self.screen_rect().bottom() - self.sprite.height() + self.sprite.feet_margin()

    def _clamp_x(self, x: int) -> int:
        """Keep the window horizontally on screen."""
        rect = self.screen_rect()
        return max(rect.left(), min(x, rect.right() - self.sprite.width()))

    def _on_ground(self) -> bool:
        """True when the pet is standing on the bottom edge."""
        return abs(self.sprite.y() - self._ground_y()) <= 2

    def _speed(self, base: float) -> float:
        """Movement speed, slower at night."""
        return base * (NIGHT_SPEED if self._night else 1.0)

    def _update_riding(self) -> None:
        """Sit on the log while airborne (or about to take off); let it crumble on landing."""
        airborne = not self._on_ground() and self.state not in (PetState.JUMP, PetState.DRAGGED)
        taking_off = self.state == PetState.FLOAT and self._pending_float is not None
        self.character.set_riding(airborne or taking_off)

    # ------------------------------------------------------------------ public API

    @property
    def sleeping(self) -> bool:
        """True while the pet is asleep (Idle or dozing) or settling down to sleep."""
        return self.state in (PetState.SLEEP, PetState.SETTLE)

    @property
    def resting(self) -> bool:
        """True while the user's ``Idle`` choice is on (the menu then offers ``Wander``)."""
        return self._resting

    def set_resting(self, active: bool) -> None:
        """Right-click menu ``Idle`` (lie down and sleep) / ``Wander`` (roam again)."""
        self._resting = active
        self._resume()

    def set_dozing(self, active: bool) -> None:
        """Doze off because the computer has been unused for a while / wake up on activity."""
        if active == self._dozing:
            return
        self._dozing = active
        self._resume()

    def set_night(self, active: bool) -> None:
        """Night look and pace: calmer fire, slower moves, longer pauses (never forces sleep)."""
        self._night = active
        self.character.set_night(1.0 if active else 0.0)

    def set_chatting(self, active: bool) -> None:
        """The chat bubble opened (stand still beside it) or closed (back to what came before)."""
        self._chatting = active
        self._resume()

    def trigger_alert(self) -> None:
        """Called by the background monitor when a system_status threshold is crossed."""
        self._alert_active = True
        self._react_timer.stop()
        self._reacting = False
        self.character.stop_transient()  # the alert face wins over e.g. a happy reaction
        self._resume()

    def clear_alert(self) -> None:
        """Called when the user acknowledges an alert by clicking the pet."""
        self._alert_active = False
        self.character.set_alert(False)
        self._resume()

    @property
    def reminding(self) -> bool:
        """True while a due reminder is waiting for the user to click the pet."""
        return self._reminding

    def trigger_reminder(self) -> None:
        """A reminder is due: stop (waking up if asleep), the ``remind`` face and the ringing
        alarm clock, until ``clear_reminder()``. During an alert the alert face stays on top,
        but the clock still rings."""
        self._reminding = True
        self._react_timer.stop()
        self._reacting = False
        if not self._dragging:
            self.character.stop_transient()   # the remind face wins over e.g. a reaction
        self.character.set_reminding(True)
        self._resume()

    def clear_reminder(self) -> None:
        """The user acknowledged the reminder(s): the clock is put away and the pet gives a
        smiling "okay!" blink for about a second before carrying on."""
        if not self._reminding:
            return
        self._reminding = False
        self.character.set_reminding(False)
        self._start_reaction_with(lambda: self._play(Mood.OK, OK_SECONDS))
        if self.state != PetState.REACT:
            self._resume()                 # no blink during an alert / drag: just carry on

    def play_random_reaction(self) -> str:
        """Left-click: play one reaction picked at random from the pool (not the same one twice
        in a row). Returns its name."""
        skip = {self._last_reaction}
        if self.character.riding:
            skip.add("chill")              # the pan does not go with sitting on the log
        names = [n for n in REACTIONS if n not in skip] or list(REACTIONS)
        name = random.choice(names)
        self._last_reaction = name
        self._start_reaction_with(lambda: REACTIONS[name](self))
        return name

    def play_reaction(self, name: str) -> None:
        """Play the reaction called ``name`` (used by the preview tool)."""
        self._start_reaction_with(lambda: REACTIONS[name](self))

    # ------------------------------------------------------------------ reaction pool

    def _play(self, mood: Mood, seconds: float, hop: float = 0.0) -> float:
        """Helper for reactions: show ``mood`` for ``seconds`` (+ optional hop)."""
        self.character.play(mood, seconds)
        if hop:
            self.character.bounce(hop)
        return seconds

    @reaction("happy")
    def _react_happy(self) -> float:
        """Big grin (one of two faces) and a shower of sparks - no jump."""
        return self._play(Mood.HAPPY, 2.2)

    @reaction("surprised")
    def _react_surprised(self) -> float:
        """Jolt with round eyes and an "o" mouth."""
        return self._play(Mood.SURPRISED, 1.6, hop=0.7)

    @reaction("scared")
    def _react_scared(self) -> float:
        """Fire bursts up big and ragged, eyes wide, mouth wide open, trembling."""
        return self._play(Mood.SCARED, 2.0)

    @reaction("angry")
    def _react_angry(self) -> float:
        """Frown, fierce slanted eyes and a wide-open shouting mouth (fig. 6, without arms)."""
        return self._play(Mood.ANGRY, 2.4)

    @reaction("thinking")
    def _react_thinking(self) -> float:
        """Looks up, mouth to one side, small calm flame."""
        return self._play(Mood.THINKING, 2.4)

    @reaction("chill")
    def _react_chill(self) -> float:
        """Flattens out and fries breakfast on its head (pan, bacon and eggs)."""
        return self._play(Mood.CHILL, 5.0)

    @reaction("yuck")
    def _react_yuck(self) -> float:
        """Pulls a lopsided, tongue-out "yuck" face, as if it bit on an eggshell (fig. 8)."""
        return self._play(Mood.YUCK, 2.4)

    @reaction("cool")
    def _react_cool(self) -> float:
        """Slides on a pair of sunglasses and smirks (the glasses drop in, a glint, then off)."""
        return self._play(Mood.COOL, 3.0)

    @reaction("speak")
    def _react_speak(self) -> float:
        """Says one random line (care line or fact/joke, see ``pet_lines``) with a moving
        mouth."""
        self.speak_requested.emit()
        self.character.play(Mood.TALKING, 2.0)
        return 2.6

    @reaction("fly")
    def _react_fly(self) -> None:
        """Summons the log and flies off somewhere (the flight ends the reaction)."""
        self._reacting = False
        self._react_timer.stop()
        self._enter_float()
        return None

    def _start_reaction_with(self, start: Callable[[], float | None]) -> None:
        """Stop wandering, wake up if asleep, run ``start`` and come back when it ends."""
        if self._alert_active or self._dragging:
            return
        self._stop_motion()
        self.character.set_sleeping(False)
        self._reacting = True
        self.state = PetState.REACT
        seconds = start()
        if seconds is not None and self._reacting:
            self._react_timer.start(int(seconds * 1000))

    def _end_reaction(self) -> None:
        """The reaction finished: go back to whatever has priority now."""
        self._reacting = False
        self._resume()

    # ------------------------------------------------------------------ priorities

    def _resume(self) -> None:
        """Do whatever has the highest priority right now (see the module docstring)."""
        if self._dragging:
            return                                   # the drag handlers take over
        if self._alert_active:
            self._stop_motion()
            self.state = PetState.ALERT
            self.character.set_sleeping(False)
            self.character.set_alert(True)
            return
        if self._reminding:
            self._stop_motion()
            self.state = PetState.REMIND
            self.character.set_sleeping(False)
            return
        if self._reacting:
            return                                   # ``_end_reaction`` calls back here
        if self._chatting:
            self._stop_motion()
            self.state = PetState.CHAT
            self.character.set_sleeping(False)
            return
        if self._resting or self._dozing:
            if self.state not in (PetState.SLEEP, PetState.SETTLE):
                self._go_to_sleep()
            return
        self.character.set_sleeping(False)
        if self.state in (PetState.ALERT, PetState.REMIND, PetState.CHAT, PetState.SLEEP,
                          PetState.SETTLE, PetState.REACT, PetState.DRAGGED):
            self._stop_motion()
            self._enter_idle()

    def _go_to_sleep(self) -> None:
        """Glide down to the ground if airborne, then fall asleep there."""
        self._stop_motion()
        if self._on_ground():
            self._fall_asleep()
            return
        self.state = PetState.SETTLE
        target = QPoint(self.sprite.x(), self._ground_y())
        duration = min(SETTLE_MAX_MS,
                       travel_duration_ms(self.sprite.pos(), target, SETTLE_SPEED_PX_S))
        self._active_anim = move_to_animation(self.sprite, target, duration)
        self._active_anim.finished.connect(self._fall_asleep)
        self._active_anim.start()

    def _fall_asleep(self) -> None:
        """Yawn and settle into the sleeping pose (unless something else came up meanwhile)."""
        self._active_anim = None
        if (self._dragging or self._alert_active or self._reminding or self._reacting
                or self._chatting):
            return
        if not (self._resting or self._dozing):
            self._resume()
            return
        self.state = PetState.SLEEP
        self.character.set_sleeping(True)

    # ------------------------------------------------------------------ random loop

    def _stop_motion(self) -> None:
        """Stop any movement and pending timers of the autonomous loop."""
        self._idle_timer.stop()
        self._jump_delay.stop()
        self._takeoff_delay.stop()
        self._pending_jump = None
        self._pending_float = None
        if self._active_anim is not None:
            self._active_anim.stop()
            self._active_anim = None

    def _wandering(self) -> bool:
        """True when nothing with a higher priority than wandering is going on."""
        return not (self._dragging or self._alert_active or self._reminding or self._reacting
                    or self._chatting or self._resting or self._dozing)

    def _pick_next_state(self) -> PetState:
        """Weighted random choice of the next autonomous state."""
        states = list(self._weights)
        return random.choices(states, weights=[self._weights[s] for s in states])[0]

    def _advance(self) -> None:
        """Finish the current autonomous state and start a new random one."""
        self._active_anim = None
        if not self._wandering():
            self._resume()
            return
        self._stop_motion()
        next_state = self._pick_next_state()
        if next_state == PetState.WALK:
            self._enter_walk()
        elif next_state == PetState.FLOAT:
            self._enter_float()
        elif next_state == PetState.JUMP:
            self._enter_jump()
        else:
            self._enter_idle()

    def _enter_idle(self) -> None:
        """Stay in place for a while; the character breathes and looks around by itself."""
        if not self._wandering():
            return
        self.state = PetState.IDLE
        pause = random.randint(4000, 9000)
        self._idle_timer.start(int(pause * (NIGHT_IDLE if self._night else 1.0)))

    def _start_move(self, target: QPoint, speed: float) -> None:
        """Animate the window to ``target`` at ``speed`` px/s, then pick the next state."""
        duration = travel_duration_ms(self.sprite.pos(), target, self._speed(speed))
        self._active_anim = move_to_animation(self.sprite, target, duration)
        self._active_anim.finished.connect(self._advance)
        self._active_anim.start()

    def _enter_walk(self) -> None:
        """Hop along the bottom edge to a spot a few hundred pixels away.

        Glides down diagonally on the log if the pet is airborne."""
        self.state = PetState.WALK
        direction = random.choice((-1, 1))
        x = self._clamp_x(self.sprite.x() + direction * random.randint(150, 500))
        self._start_move(QPoint(x, self._ground_y()), WALK_SPEED_PX_S)

    def _enter_float(self) -> None:
        """Fly on the log to a random point anywhere on screen.

        From the ground the log is summoned first and the pet takes off a moment later."""
        self.state = PetState.FLOAT
        rect = self.screen_rect()
        x = self._clamp_x(random.randint(rect.left(), rect.right()))
        y = random.randint(rect.top() + 40, self._ground_y())
        target = QPoint(x, y)
        if self._on_ground():
            self._pending_float = target
            self.character.set_riding(True, takeoff=True)
            self.character.anticipate()
            self._takeoff_delay.start(TAKEOFF_DELAY_MS)
        else:
            self._start_move(target, FLOAT_SPEED_PX_S)

    def _launch_float(self) -> None:
        """Lift off toward the target chosen by ``_enter_float``."""
        target, self._pending_float = self._pending_float, None
        if target is None or self.state != PetState.FLOAT:
            return
        self._start_move(target, FLOAT_SPEED_PX_S)

    def _enter_jump(self) -> None:
        """Crouch briefly (anticipation), then leap to a nearby spot on the ground."""
        self.state = PetState.JUMP
        direction = random.choice((-1, 1))
        x = self._clamp_x(self.sprite.x() + direction * random.randint(60, 260))
        self._pending_jump = (QPoint(x, self._ground_y()), random.randint(80, 150))
        self.character.anticipate()
        self._jump_delay.start(170)

    def _launch_jump(self) -> None:
        """Start the jump arc prepared by ``_enter_jump``."""
        if self._pending_jump is None or self.state != PetState.JUMP:
            return
        target, height = self._pending_jump
        self._pending_jump = None
        self._active_anim = jump_animation(self.sprite, target, height_px=height)
        self._active_anim.finished.connect(self._advance)
        self._active_anim.start()

    # ------------------------------------------------------------------ dragging

    def _on_drag_started(self) -> None:
        """User grabbed the pet: stop everything, wake up, look surprised while dangling."""
        self._dragging = True
        self._react_timer.stop()
        self._reacting = False
        self._stop_motion()
        self.state = PetState.DRAGGED
        self.character.set_sleeping(False)
        self.character.play(Mood.SURPRISED, None)

    def _on_drag_ended(self) -> None:
        """User let go: plop, then carry on with whatever has priority."""
        self._dragging = False
        self.character.stop_transient()
        self.character.bounce(0.6)
        self._resume()
