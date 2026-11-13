"""Tests for the performance modes (roadmap Phase 12): the frame-rate cap and its pacing, the
adaptive frame rate, the character's activity levels and fixed-step physics, the Settings window
switches and remembered settings."""
from __future__ import annotations

import json

import pytest
from PySide6.QtCore import QPointF

from overlay.character import FlameCharacter, Mood
from overlay.overlay_window import FramePacer, OverlaySprite
from ui.settings_window import SettingsWindow
from user_settings import UserSettings


def _settle(ch: FlameCharacter, seconds: float, pos: QPointF | None = None) -> None:
    """Run the character for ``seconds`` at 60 fps with the window parked at ``pos``."""
    pos = pos or QPointF(300.0, 300.0)
    for _ in range(int(seconds * 60)):
        ch.update(1 / 60, pos, None)


def test_standing_pet_is_calm_and_moving_pet_is_active(qapp):
    """A pet standing still is "calm"; moving the window makes it "active"."""
    ch = FlameCharacter(scale=0.75, seed=5)
    _settle(ch, 3.0)
    assert ch.activity() == "calm"
    pos = QPointF(300.0, 300.0)
    for _ in range(10):
        pos = QPointF(pos.x() + 4.0, pos.y())
        ch.update(1 / 60, pos, None)
    assert ch.activity() == "active"


def test_reactions_and_talking_are_active(qapp):
    """A transient mood (click reaction / AI emotion) and talking need the full frame rate."""
    ch = FlameCharacter(scale=0.75, seed=5)
    _settle(ch, 3.0)
    ch.play(Mood.HAPPY, 1.0)
    ch.update(1 / 60, QPointF(300.0, 300.0), None)
    assert ch.activity() == "active"
    _settle(ch, 3.0)
    ch.talk(1.0)
    ch.update(1 / 60, QPointF(300.0, 300.0), None)
    assert ch.activity() == "active"


def test_sleeping_pet_is_asleep_after_the_yawn(qapp):
    """Once the yawn has finished and the body has sunk, a sleeping pet reports "asleep"."""
    ch = FlameCharacter(scale=0.75, seed=5)
    ch.set_sleeping(True)
    _settle(ch, 6.0)
    assert ch.activity() == "asleep"


def test_long_frames_are_simulated_in_short_steps(qapp):
    """One 1/15 s frame gives (almost) the same result as four 1/60 s frames: the springs and
    the face do not run slow or jump at a low frame rate."""
    a = FlameCharacter(scale=0.75, seed=9)
    b = FlameCharacter(scale=0.75, seed=9)
    for ch in (a, b):
        _settle(ch, 1.0)
        ch.play(Mood.SURPRISED, 2.0)
    for _ in range(15):
        a.update(1 / 15, QPointF(300.0, 300.0), None)
        for _ in range(4):
            b.update(1 / 60, QPointF(300.0, 300.0), None)
    assert a._t == pytest.approx(b._t)
    assert a.face.expr.eye_scale == pytest.approx(b.face.expr.eye_scale, abs=0.02)
    assert a._sy == pytest.approx(b._sy, abs=0.02)


def test_window_frame_level_follows_mode_and_movement(qapp):
    """Adaptive off: always full speed. Adaptive on: the character's level, but any pending
    window movement means full speed right away."""
    sprite = OverlaySprite()
    _settle(sprite.character, 3.0, sprite.exact_pos())
    sprite._drawn_exact = sprite.exact_pos()
    assert sprite._frame_level() == "active"           # mode off
    sprite.set_adaptive_fps(True)
    assert sprite._frame_level() == "calm"
    sprite._exact = sprite._exact + QPointF(2.0, 0.0)  # a movement animation moved the pet
    assert sprite._frame_level() == "active"
    assert sprite._level_fps == {"active": 60, "calm": 30, "asleep": 15}
    sprite.deleteLater()


def test_frame_cap_limits_every_level(qapp):
    """The cap applies to every animation; the calm / asleep rates never exceed it."""
    sprite = OverlaySprite()
    sprite.set_max_fps(45)
    assert sprite.max_fps == 45
    assert sprite._level_fps == {"active": 45, "calm": 30, "asleep": 15}
    sprite.set_max_fps(30)
    assert sprite._level_fps == {"active": 30, "calm": 30, "asleep": 15}
    sprite.deleteLater()


@pytest.mark.parametrize("fps, drawn", [(60, 60), (45, 45), (30, 30), (15, 15)])
def test_pacer_hits_the_rate_on_a_60hz_timer(fps, drawn):
    """On a 60 Hz animation timer (with a little jitter) the pacer draws the asked rate, also
    45 fps, which does not divide 60 (3 passes drawn out of 4)."""
    pacer = FramePacer()
    count = 0
    for i in range(600):  # 10 seconds
        now = int(i * 1e9 / 60) + (i % 3 - 1) * 500_000
        if pacer.due(now, fps):
            pacer.drawn(now, fps)
            count += 1
    assert count == pytest.approx(drawn * 10, abs=2)


def test_pacer_does_not_burst_after_a_stall():
    """After a long pause (e.g. a slow frame) drawing resumes at the normal pace, no burst."""
    pacer = FramePacer()
    pacer.drawn(0, 60)
    stalled = 500_000_000
    assert pacer.due(stalled, 60)
    pacer.drawn(stalled, 60)
    assert not pacer.due(stalled + 5_000_000, 60)
    assert pacer.due(stalled + int(1e9 / 60), 60)


def test_lite_flame_switch_is_safe_on_every_renderer(qapp):
    """Switching the lite flame on and off works (or is ignored) whatever renderer runs."""
    ch = FlameCharacter(scale=0.75, seed=5, renderer="metaball")
    ch.set_lite_flame(True)
    ch.set_lite_flame(False)
    _settle(ch, 0.2)


def test_settings_window_reports_switches(qapp):
    """Ticking the boxes emits the matching signals; the live readout shows the frame rate."""
    window = SettingsWindow(adaptive_fps=False, lite_flame=True, max_fps=60)
    seen = []
    window.max_fps_changed.connect(lambda fps: seen.append(("fps", fps)))
    assert window.fps_buttons[60].isChecked()
    window.adaptive_fps_toggled.connect(lambda on: seen.append(("adaptive", on)))
    window.lite_flame_toggled.connect(lambda on: seen.append(("lite", on)))
    assert window.lite_box.isChecked() and not window.adaptive_box.isChecked()
    window.adaptive_box.setChecked(True)
    window.lite_box.setChecked(False)
    assert seen == [("adaptive", True), ("lite", False)]
    window.fps_buttons[45].setChecked(True)
    assert seen[-1] == ("fps", 45)
    window.show_frame_rate(29.6, "calm")
    assert window.live.text() == "Drawing: 30 fps (standing still)"


def test_user_settings_default_save_and_reload(tmp_path):
    """Unset settings come from config.yaml; a change is saved and read back next time."""
    path = tmp_path / "settings.json"
    settings = UserSettings(path)
    assert settings.get("adaptive_fps") is False
    settings.set("adaptive_fps", True)
    assert json.loads(path.read_text(encoding="utf-8")) == {"adaptive_fps": True}
    assert UserSettings(path).get("adaptive_fps") is True
    assert UserSettings(path).get("lite_flame") is True     # chosen as the default
    assert UserSettings(path).get("max_fps") == 60


def test_user_settings_survive_a_broken_file(tmp_path):
    """A corrupt settings file falls back to the defaults instead of crashing the app."""
    path = tmp_path / "settings.json"
    path.write_text("{not json", encoding="utf-8")
    settings = UserSettings(path)
    assert settings.get("lite_flame") is True
    settings.set("lite_flame", False)
    assert UserSettings(path).get("lite_flame") is False
    with pytest.raises(KeyError):
        settings.set("no_such_setting", 1)
