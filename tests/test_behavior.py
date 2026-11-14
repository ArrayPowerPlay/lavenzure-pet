"""Tests for overlay.behavior: the reaction pool and the priority rules between states."""
import pytest
from PySide6.QtCore import QPointF

from overlay.behavior import REACTIONS, BehaviorController, PetState
from overlay.character import Mood
from overlay.overlay_window import OverlaySprite


@pytest.fixture
def pet(qapp):
    """A behavior controller whose pet stands on the ground (no window shown)."""
    sprite = OverlaySprite()
    behavior = BehaviorController(sprite)
    sprite.set_exact_pos(QPointF(200, behavior._ground_y()), immediate=True)
    yield behavior
    behavior._stop_motion()
    sprite.deleteLater()


def test_pool_has_every_animation_but_not_alert_or_sleep():
    """Every reaction registers itself; alert and sleep are not click reactions."""
    assert {"happy", "surprised", "scared", "angry", "thinking", "chill", "speak", "fly"} <= set(
        REACTIONS)
    assert "alert" not in REACTIONS and "sleep" not in REACTIONS


def test_random_reaction_never_repeats_back_to_back(pet):
    """Two clicks in a row give two different reactions."""
    names = [pet.play_random_reaction() for _ in range(30)]
    assert all(a != b for a, b in zip(names, names[1:], strict=False))


def test_speak_reaction_asks_for_a_line(pet):
    """The "speak" reaction emits ``speak_requested`` (main shows a random line)."""
    seen = []
    pet.speak_requested.connect(lambda: seen.append(True))
    pet.play_reaction("speak")
    assert seen == [True] and pet.state == PetState.REACT


def test_idle_sleeps_and_wander_wakes(pet):
    """Menu Idle -> asleep on the ground; Wander -> back to roaming."""
    pet.set_resting(True)
    assert pet.state == PetState.SLEEP and pet.character.sleeping
    pet.set_resting(False)
    assert pet.state == PetState.IDLE and not pet.character.sleeping


def test_chat_wakes_a_resting_pet_then_it_sleeps_again(pet):
    """Idle + Chat: awake while chatting, asleep again after the chat closes."""
    pet.set_resting(True)
    pet.set_chatting(True)
    assert pet.state == PetState.CHAT and not pet.character.sleeping
    pet.set_chatting(False)
    assert pet.state == PetState.SLEEP and pet.character.sleeping


def test_alert_wakes_and_clearing_it_goes_back_to_sleep(pet):
    """Idle + alert: alert face; after the click that clears it, sleep again."""
    pet.set_resting(True)
    pet.trigger_alert()
    assert pet.state == PetState.ALERT and pet.character.mood == Mood.ALERT
    pet.play_random_reaction()          # a click during an alert plays nothing
    assert pet.state == PetState.ALERT
    pet.clear_alert()
    assert pet.state == PetState.SLEEP


def test_dozing_follows_user_activity(pet):
    """No input for a while -> doze; input again -> awake (unless Idle was chosen)."""
    pet.set_dozing(True)
    assert pet.sleeping
    pet.set_dozing(False)
    assert not pet.sleeping


def test_drag_wakes_and_drop_resumes_sleep(pet):
    """Dragging a sleeping pet wakes it; letting go of it on the ground puts it back to sleep."""
    pet.set_resting(True)
    pet.sprite.drag_started.emit()
    assert pet.state == PetState.DRAGGED and not pet.character.sleeping
    pet.sprite.drag_ended.emit()
    assert pet.state == PetState.SLEEP


def test_airborne_resting_pet_settles_to_the_ground_first(pet):
    """Choosing Idle in mid-air glides down (on the log) before sleeping."""
    pet.sprite.set_exact_pos(QPointF(200, pet._ground_y() - 300), immediate=True)
    pet.set_resting(True)
    assert pet.state == PetState.SETTLE
    pet._update_riding()
    assert pet.character.riding


def test_night_slows_movement(pet):
    """At night the pet moves slower and its fire switches to the night look."""
    day = pet._speed(100.0)
    pet.set_night(True)
    assert pet._speed(100.0) < day
    assert pet.character._night_target == 1.0


def test_reminder_rings_until_cleared_then_ok_blink(pet):
    """A due reminder stops the pet with the remind face and the ringing clock; clearing it
    puts the clock away and plays the short "okay!" blink, then the pet roams again."""
    pet.trigger_reminder()
    assert pet.state == PetState.REMIND and pet.reminding
    assert pet.character.mood == Mood.REMIND and pet.character.clock.ringing
    pet.clear_reminder()
    assert not pet.reminding and not pet.character.clock.ringing
    assert pet.state == PetState.REACT and pet.character.mood == Mood.OK
    pet._end_reaction()
    assert pet.state == PetState.IDLE


def test_reminder_wakes_a_sleeping_pet_and_it_sleeps_again(pet):
    """Idle + reminder: awake while the clock rings, back to sleep after the "okay!"."""
    pet.set_resting(True)
    pet.trigger_reminder()
    assert pet.state == PetState.REMIND and not pet.character.sleeping
    pet.clear_reminder()
    pet._end_reaction()
    assert pet.state == PetState.SLEEP


def test_alert_face_wins_over_a_reminder(pet):
    """Alert + reminder: the alert face shows, the clock still rings."""
    pet.trigger_reminder()
    pet.trigger_alert()
    assert pet.state == PetState.ALERT and pet.character.mood == Mood.ALERT
    assert pet.character.clock.ringing
    pet.clear_alert()
    assert pet.state == PetState.REMIND
