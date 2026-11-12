"""Tests for the face expression springs: each mood settles on (one of) its target expressions."""
import random

import pytest
from PySide6.QtCore import QPointF

from overlay.face import MOOD_TARGETS, Face, Mood
from overlay.face_refs import MOUTH_SAMPLES, REF_FACES, mouth_s

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


@pytest.mark.parametrize("mood", [Mood.SLEEP, Mood.YAWN])
def test_sleeping_eyes_ignore_the_cursor(qapp, mood):
    """Dozing off / asleep, the face does not follow the mouse (round 12)."""
    face = Face(60.0, random.Random(1), seed=1)
    face.set_mood(mood)
    for i in range(240):
        cursor = QPointF(400.0, 200.0) if i % 120 < 60 else QPointF(-400.0, -50.0)
        face.update(1 / 60, cursor, 0.0)
    assert abs(face._look_x) < 0.02 and abs(face._look_y) < 0.02


@pytest.mark.parametrize(("mood", "name"), [(Mood.CHILL, "fig7")])
def test_copied_faces_settle_fully(qapp, mood, name):
    """Chill becomes the traced fig. 7 face (weight 1) and is never mirrored."""
    face = Face(60.0, random.Random(3), seed=3)
    face.set_mood(mood)
    for _ in range(240):
        face.update(1 / 60, None, 0.0)
    assert getattr(face.expr, name) == pytest.approx(1.0, abs=0.01)
    assert face._mirror == 1.0


def test_happy_fig1_variant_is_copied():
    """The sly happy variant is the traced fig. 1 face; the other one (fig. 2) is not."""
    weights = sorted(v.fig1 for v in MOOD_TARGETS[Mood.HAPPY])
    assert weights == [0.0, 1.0]


def test_reference_data_is_sane():
    """Traced eyes have a closed radial profile near 1 and the mouths match the lip sampling."""
    assert mouth_s(0) == pytest.approx(-1.0) and mouth_s(MOUTH_SAMPLES - 1) == pytest.approx(1.0)
    for ref in REF_FACES.values():
        for eye in ref.eyes:
            assert all(0.3 < r < 1.6 for r in eye.radii)
        m = ref.mouth
        assert len(m.top) == len(m.bottom) == MOUTH_SAMPLES
        assert all(b >= t for t, b in zip(m.top, m.bottom, strict=True))
    assert REF_FACES["fig7"].mouth.closed and not REF_FACES["fig1"].mouth.closed
