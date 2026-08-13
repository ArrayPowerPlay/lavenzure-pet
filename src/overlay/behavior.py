"""Behavior state machine: drives autonomous movement and reacts to interaction events."""
from __future__ import annotations

import random
from enum import Enum, auto

from PySide6.QtCore import QObject, QPoint, QTimer
from PySide6.QtGui import QGuiApplication

from overlay.animation import bob_animation, jump_animation, move_to_animation
from overlay.overlay_window import OverlaySprite


class PetState(Enum):
    IDLE = auto()
    WALK = auto()
    FLOAT = auto()
    JUMP = auto()
    DRAGGED = auto()
    REACT = auto()
    ALERT = auto()


_STATE_WEIGHTS = {
    PetState.IDLE: 0.4,
    PetState.WALK: 0.25,
    PetState.FLOAT: 0.25,
    PetState.JUMP: 0.1,
}


class BehaviorController(QObject):
    """Owns the current PetState and the animation currently playing on the sprite."""

    def __init__(self, sprite: OverlaySprite) -> None:
        super().__init__()
        self.sprite = sprite
        self.state = PetState.IDLE
        self._active_anim = None
        self._locked = False  # True while DRAGGED/REACT/ALERT override the random loop

        self.sprite.drag_started.connect(self._on_drag_started)
        self.sprite.drag_ended.connect(self._on_drag_ended)

        self._enter_idle()

    def screen_rect(self):
        return QGuiApplication.primaryScreen().availableGeometry()

    def _pick_next_state(self) -> PetState:
        states = list(_STATE_WEIGHTS.keys())
        weights = list(_STATE_WEIGHTS.values())
        return random.choices(states, weights=weights)[0]

    def _enter_idle(self) -> None:
        if self._locked:
            return
        self.state = PetState.IDLE
        self._active_anim = bob_animation(self.sprite)
        self._active_anim.start()
        QTimer.singleShot(random.randint(4000, 8000), self._advance)

    def _advance(self) -> None:
        if self._locked:
            return
        if self._active_anim:
            self._active_anim.stop()
        next_state = self._pick_next_state()
        if next_state == PetState.IDLE:
            self._enter_idle()
        elif next_state == PetState.WALK:
            self._enter_walk()
        elif next_state == PetState.FLOAT:
            self._enter_float()
        else:
            self._enter_jump()

    def _random_point(self, on_ground: bool) -> QPoint:
        rect = self.screen_rect()
        x = random.randint(rect.left(), max(rect.left(), rect.right() - self.sprite.width()))
        if on_ground:
            y = rect.bottom() - self.sprite.height()
        else:
            y = random.randint(rect.top(), max(rect.top(), rect.bottom() - self.sprite.height()))
        return QPoint(x, y)

    def _enter_walk(self) -> None:
        self.state = PetState.WALK
        target = self._random_point(on_ground=True)
        self._active_anim = move_to_animation(self.sprite, target, duration_ms=3000)
        self._active_anim.finished.connect(self._advance)
        self._active_anim.start()

    def _enter_float(self) -> None:
        self.state = PetState.FLOAT
        target = self._random_point(on_ground=False)
        self._active_anim = move_to_animation(self.sprite, target, duration_ms=3500)
        self._active_anim.finished.connect(self._advance)
        self._active_anim.start()

    def _enter_jump(self) -> None:
        self.state = PetState.JUMP
        target = self._random_point(on_ground=True)
        self._active_anim = jump_animation(self.sprite, target)
        self._active_anim.finished.connect(self._advance)
        self._active_anim.start()

    def trigger_reaction(self) -> None:
        """Called when the user clicks the sprite; briefly overrides the idle loop."""
        if self.state == PetState.ALERT:
            self.clear_alert()
            return
        self._locked = True
        self.state = PetState.REACT
        if self._active_anim:
            self._active_anim.stop()
        QTimer.singleShot(1200, self._release_lock)

    def trigger_alert(self) -> None:
        """Called by the background monitor when a system_status threshold is crossed."""
        self._locked = True
        self.state = PetState.ALERT
        if self._active_anim:
            self._active_anim.stop()

    def clear_alert(self) -> None:
        if self.state == PetState.ALERT:
            self._release_lock()

    def _release_lock(self) -> None:
        self._locked = False
        self._enter_idle()

    def _on_drag_started(self) -> None:
        self._locked = True
        self.state = PetState.DRAGGED
        if self._active_anim:
            self._active_anim.stop()

    def _on_drag_ended(self) -> None:
        self._release_lock()
