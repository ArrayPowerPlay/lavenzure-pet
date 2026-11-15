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
                                  Mood.ANGRY, Mood.CHILL, Mood.SLEEP, Mood.COOL])
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


def test_settled_values_land_exactly_on_the_goal(qapp):
    """Once the springs have settled, the values sit exactly on the goal and stop being blended
    (the speed-up must not leave them hovering just off it)."""
    face = Face(60.0, random.Random(2), seed=2)
    face.set_mood(Mood.SURPRISED)
    for _ in range(600):  # 10 s at 60 fps
        face.update(1 / 60, None, 0.0)
    goal = face._target()
    for name in SETTLED_FIELDS:
        assert getattr(face.expr, name) == getattr(goal, name), name


def test_eye_geometry_cache_follows_every_change(qapp):
    """The cached eye geometry always equals a fresh computation, also right after a change."""
    face = Face(60.0, random.Random(3), seed=3)
    for step in range(120):
        face.update(1 / 60, QPointF(40.0 * (step % 7 - 3), -20.0), 0.0)
        if step == 60:
            face.expr.eye_scale = 1.4      # a direct change between two frames
            face.lift = 0.2
        for side in (-1, 1):
            assert face._eye_geom(side) == face._compute_eye_geom(side)


def test_cool_mood_wears_sunglasses_and_takes_them_off(qapp):
    """``cool`` drops the sunglasses on (round 21); when the mood ends they lift away."""
    from overlay.character import FlameCharacter

    ch = FlameCharacter(seed=2)
    ch.play(Mood.COOL, 1.0)
    for _ in range(30):                      # 1 s at 30 fps: landed
        ch.update(1 / 30, QPointF(0, 0), None)
    assert ch.shades.visible
    for _ in range(45):                      # mood over, glasses rise and fade out
        ch.update(1 / 30, QPointF(0, 0), None)
    assert not ch.shades.visible


def test_xmas_outfit_puts_the_scarf_on_and_takes_it_off(qapp):
    """The Christmas outfit (round 39) fades a knitted scarf on, lifts the face a little, keeps
    the mouth above the band and squeezes the body under it, and snows on the log (round 43);
    ``normal`` takes it all off."""
    from overlay.character import FlameCharacter
    from overlay.outfits import SCARF_FACE_LIFT

    ch = FlameCharacter(seed=2, renderer="shader")
    ch.set_outfit("xmas")
    for _ in range(30):                      # 1 s at 30 fps: fully on
        ch.update(1 / 30, QPointF(0, 0), None)
    assert ch.outfit == "xmas" and ch.scarf.worn and ch.scarf.amount > 0.99
    assert ch.face.lift >= SCARF_FACE_LIFT - 1e-6
    assert ch.face.floor_y is not None and ch._drive.scarf_pinch > 0.0
    assert ch.log.snow > 0.99
    ch.play(Mood.CHILL, 1.0)                 # the scarf stays on in every mood
    for _ in range(10):
        ch.update(1 / 30, QPointF(0, 0), None)
    assert ch.scarf.worn
    ch.set_outfit("normal")
    for _ in range(30):
        ch.update(1 / 30, QPointF(0, 0), None)
    assert not ch.scarf.visible and ch.face.lift == 0.0 and ch.face.floor_y is None
    assert ch._drive.scarf_pinch == 0.0 and ch.log.snow == 0.0
    with pytest.raises(ValueError):
        ch.set_outfit("party")


def test_scarf_makes_the_body_taller_instead_of_shrinking_a_big_mouth(qapp):
    """Round 42: with the scarf on, a big mouth (scared) is not squeezed above the band for
    long - the body grows taller until it fits, and settles back when the mood ends."""
    from PySide6.QtGui import QImage, QPainter

    from overlay.character import FlameCharacter

    ch = FlameCharacter(seed=2, renderer="shader")
    ch.set_outfit("xmas")
    img = QImage(ch.width, ch.height, QImage.Format.Format_ARGB32_Premultiplied)

    def run(frames: int) -> None:
        """Update and paint (the mouth's room is measured while painting)."""
        for _ in range(frames):
            ch.update(1 / 30, QPointF(0, 0), None)
            painter = QPainter(img)
            ch.paint(painter)
            painter.end()

    run(30)
    assert ch.face.taller == 0.0             # the calm face fits as it is
    ch.play(Mood.SCARED, 1.5)
    run(30)
    assert ch.face.taller > 0.1 and ch.face.mouth_overflow < 0.01
    run(45)
    assert ch.face.taller < 0.02


def test_tongue_is_drawn_over_the_scarf(qapp):
    """Yuck (tongue out) with the Xmas scarf on: the tongue is held back while the face is
    drawn and painted after the scarf, so the scarf never hides it."""
    from PySide6.QtGui import QImage, QPainter

    from overlay.character import FlameCharacter

    ch = FlameCharacter(seed=2, renderer="shader")
    ch.set_outfit("xmas")
    img = QImage(ch.width, ch.height, QImage.Format.Format_ARGB32_Premultiplied)
    ch.play(Mood.YUCK, None)
    for _ in range(60):
        ch.update(1 / 30, QPointF(0, 0), None)
        painter = QPainter(img)
        ch.paint(painter)
        painter.end()
    assert ch.face.tongue_in_front
    assert ch.face._front_tongue is None     # drawn and cleared by the end of the frame
    ch.set_outfit("normal")
    for _ in range(60):
        ch.update(1 / 30, QPointF(0, 0), None)
    assert not ch.face.tongue_in_front
