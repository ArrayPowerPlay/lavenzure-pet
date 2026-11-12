"""Tests for the face expression springs: each mood settles on (one of) its target expressions."""
import random

import pytest

from overlay.face import MOOD_TARGETS, Face, Mood

SETTLED_FIELDS = ("eye_scale", "pupil", "mouth_open", "smile", "mouth_round", "happy_eyes",
                  "brow", "body_w", "body_h")


def _matches(expr, target) -> bool:
    """True when every settled field of ``expr`` is within 0.05 of ``target``."""
    return all(getattr(expr, n) == pytest.approx(getattr(target, n), abs=0.05)
               for n in SETTLED_FIELDS)


@pytest.mark.parametrize("mood", [Mood.HAPPY, Mood.SURPRISED, Mood.ALERT, Mood.SCARED,
                                  Mood.ANGRY, Mood.CHILL, Mood.SLEEP])
def test_mood_settles_on_target(qapp, mood):
    """After a few seconds the springs reach one of the mood's target variants."""
    face = Face(60.0, random.Random(1), seed=1)
    face.set_mood(mood)
    for _ in range(300):  # 5 s at 60 fps
        face.update(1 / 60, None, 0.0)
    assert any(_matches(face.expr, target) for target in MOOD_TARGETS[mood]), mood


def test_every_mood_has_a_target():
    """Each mood has at least one target expression (the AI and the click pool rely on it)."""
    for mood in Mood:
        assert MOOD_TARGETS[mood], mood


def test_happy_has_two_variants():
    """Happy picks between the sly grin (fig. 1) and the beaming smile (fig. 2)."""
    assert len(MOOD_TARGETS[Mood.HAPPY]) == 2
