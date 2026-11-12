"""Behavior state machine: drives autonomous movement and reacts to interaction events.

States IDLE/WALK/FLOAT/JUMP are picked at random (weights from ``config.yaml``); DRAGGED, REACT
and ALERT are triggered by the mouse or the background monitor and lock out the random loop.
The controller moves the window and tells the character which mood to show; the character
handles its own body language (lean, hop, squash) from the movement.
"""
from __future__ import annotations

import random
from enum import Enum, auto

from PySide6.QtCore import QObject, QPoint, QTimer
from PySide6.QtGui import QGuiApplication

import config
from overlay.animation import jump_animation, move_to_animation, travel_duration_ms
from overlay.character import Mood
from overlay.overlay_window import OverlaySprite

WALK_SPEED_PX_S = 85.0
FLOAT_SPEED_PX_S = 120.0
REACT_SECONDS = 1.4


class PetState(Enum):
    """What the pet is currently doing."""

    IDLE = auto()
    WALK = auto()
    FLOAT = auto()
    JUMP = auto()
    DRAGGED = auto()
    REACT = auto()
    ALERT = auto()
    CHAT = auto()


def _state_weights() -> dict[PetState, float]:
    """Relative chance of each autonomous state, read from config (with sensible defaults)."""
    defaults = {"idle": 0.4, "walk": 0.25, "float": 0.25, "jump": 0.1}
    configured = config.get("behavior.state_weights", {}) or {}
    return {PetState[name.upper()]: float(configured.get(name, w)) for name, w in defaults.items()}


class BehaviorController(QObject):
    """Owns the current PetState and the window-movement animation currently playing."""

    def __init__(self, sprite: OverlaySprite) -> None:
        """Attach to ``sprite``, create the state timers and start the random idle loop."""
        super().__init__()
        self.sprite = sprite
        self.character = sprite.character
        self.state = PetState.IDLE
        self._weights = _state_weights()
        self._active_anim = None
        self._locked = False  # True while DRAGGED/REACT/ALERT override the random loop
        self._alert_active = False  # survives a drag so the alert comes back afterwards
        self._chatting = False  # the chat bubble is open: stand still

        # Dedicated single-shot timers (restartable, so a stale timeout can never fire twice).
        self._idle_timer = self._make_timer(self._advance)
        self._jump_delay = self._make_timer(self._launch_jump)
        self._react_timer = self._make_timer(self._release_lock)
        self._pending_jump: tuple[QPoint, int] | None = None

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

    # ------------------------------------------------------------------ random loop

    def _stop_motion(self) -> None:
        """Stop any movement and pending timers of the autonomous loop."""
        self._idle_timer.stop()
        self._jump_delay.stop()
        self._pending_jump = None
        if self._active_anim is not None:
            self._active_anim.stop()
            self._active_anim = None

    def _pick_next_state(self) -> PetState:
        """Weighted random choice of the next autonomous state."""
        states = list(self._weights)
        return random.choices(states, weights=[self._weights[s] for s in states])[0]

    def _advance(self) -> None:
        """Finish the current autonomous state and start a new random one."""
        if self._locked:
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
        if self._locked:
            return
        self.state = PetState.IDLE
        self._idle_timer.start(random.randint(4000, 9000))

    def _start_move(self, target: QPoint, speed: float) -> None:
        """Animate the window to ``target`` at ``speed`` px/s, then pick the next state."""
        duration = travel_duration_ms(self.sprite.pos(), target, speed)
        self._active_anim = move_to_animation(self.sprite, target, duration)
        self._active_anim.finished.connect(self._advance)
        self._active_anim.start()

    def _enter_walk(self) -> None:
        """Hop along the bottom edge to a spot a few hundred pixels away.

        Drifts down diagonally if the pet is airborne."""
        self.state = PetState.WALK
        direction = random.choice((-1, 1))
        x = self._clamp_x(self.sprite.x() + direction * random.randint(150, 500))
        self._start_move(QPoint(x, self._ground_y()), WALK_SPEED_PX_S)

    def _enter_float(self) -> None:
        """Drift smoothly to a random point anywhere on screen."""
        self.state = PetState.FLOAT
        rect = self.screen_rect()
        x = self._clamp_x(random.randint(rect.left(), rect.right()))
        y = random.randint(rect.top() + 40, self._ground_y())
        self._start_move(QPoint(x, y), FLOAT_SPEED_PX_S)

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
        if self._locked or self._pending_jump is None:
            return
        target, height = self._pending_jump
        self._pending_jump = None
        self._active_anim = jump_animation(self.sprite, target, height_px=height)
        self._active_anim.finished.connect(self._advance)
        self._active_anim.start()

    # ------------------------------------------------------------------ interaction overrides

    def trigger_reaction(self) -> None:
        """Called when the user clicks the sprite: happy face + hop, then resume wandering."""
        if self.state == PetState.ALERT:
            self.clear_alert()
            return
        self._locked = True
        self.state = PetState.REACT
        self._stop_motion()
        self.character.play(Mood.HAPPY, REACT_SECONDS)
        self._react_timer.start(int(REACT_SECONDS * 1000))

    def trigger_notice(self) -> None:
        """Called when a reminder fires: a surprised hop to catch the user's eye.

        Unlike ``trigger_reaction`` it never clears an alert and leaves a drag alone."""
        if self.state in (PetState.ALERT, PetState.DRAGGED):
            return
        self._locked = True
        self.state = PetState.REACT
        self._stop_motion()
        self.character.play(Mood.SURPRISED, REACT_SECONDS)
        self.character.bounce(1.0)
        self._react_timer.start(int(REACT_SECONDS * 1000))

    def trigger_alert(self) -> None:
        """Called by the background monitor when a system_status threshold is crossed."""
        self._locked = True
        self._alert_active = True
        self.state = PetState.ALERT
        self._react_timer.stop()
        self._stop_motion()
        self.character.stop_transient()  # the alert face wins over e.g. a happy reaction
        self.character.set_alert(True)

    def clear_alert(self) -> None:
        """Called when the user acknowledges an alert by clicking the pet."""
        self._alert_active = False
        self.character.set_alert(False)
        if self.state == PetState.ALERT:
            self._release_lock()

    def set_chatting(self, active: bool) -> None:
        """The chat bubble opened (stand still beside it) or closed (wander again)."""
        self._chatting = active
        if self.state in (PetState.DRAGGED, PetState.ALERT, PetState.REACT):
            return  # those finish first and then look at ``_chatting``
        if active:
            self._locked = True
            self.state = PetState.CHAT
            self._stop_motion()
        else:
            self._release_lock()

    def _release_lock(self) -> None:
        """Return control to the random loop (or keep standing still while chatting)."""
        if self._chatting:
            self._locked = True
            self.state = PetState.CHAT
            self._stop_motion()
            return
        self._locked = False
        self._enter_idle()

    def _on_drag_started(self) -> None:
        """User grabbed the pet: stop moving and look surprised while dangling."""
        self._locked = True
        self.state = PetState.DRAGGED
        self._react_timer.stop()
        self._stop_motion()
        self.character.play(Mood.SURPRISED, None)

    def _on_drag_ended(self) -> None:
        """User let go: plop, then resume (or go back to the alert if one is still active)."""
        self.character.stop_transient()
        self.character.bounce(0.6)
        if self._alert_active:
            self.state = PetState.ALERT
            return
        self._release_lock()
