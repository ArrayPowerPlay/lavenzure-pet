"""Tests for the face expression springs: each mood settles on its target values."""
import random

import pytest

from overlay.face import MOOD_TARGETS, Face, Mood

SETTLED_FIELDS = ("eye_scale", "pupil", "mouth_open", "smile", "mouth_round", "happy_eyes")


@pytest.mark.parametrize("mood", [Mood.HAPPY, Mood.SURPRISED, Mood.ALERT])
def test_mood_settles_on_target(qapp, mood):
    """After a few seconds the springs reach the mood's target expression."""
    face = Face(60.0, random.Random(1), seed=1)
    face.set_mood(mood)
    for _ in range(240):  # 4 s at 60 fps
        face.update(1 / 60, None, 0.0)
    target = MOOD_TARGETS[mood]
    for name in SETTLED_FIELDS:
        assert getattr(face.expr, name) == pytest.approx(getattr(target, name), abs=0.05), name
