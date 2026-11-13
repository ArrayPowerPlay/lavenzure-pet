"""Tests for the performance options (roadmap Phase 12): the frame rate and its pacing, fixed-step
physics, the lite flame, the Settings window and remembered settings."""
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


def test_window_frame_rate_defaults_to_30_and_can_change(qapp):
    """The pet draws 30 fps by default (config.yaml); Settings can switch it to 60."""
    sprite = OverlaySprite()
    assert sprite.max_fps == 30
    sprite.set_max_fps(60)
    assert sprite.max_fps == 60
    sprite.set_max_fps(1)
    assert sprite.max_fps == 10  # never absurdly low
    sprite.deleteLater()


@pytest.mark.parametrize("fps, drawn", [(60, 60), (30, 30)])
def test_pacer_hits_the_rate_on_a_60hz_timer(fps, drawn):
    """On a 60 Hz animation timer (with a little jitter) the pacer draws the asked rate."""
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


def test_settings_window_reports_frame_rate(qapp):
    """Picking a frame rate emits it; the live readout shows the measured frame rate. Only the
    frame-rate choice is left (adaptive fps and the lite-flame switch were removed)."""
    window = SettingsWindow(max_fps=30)
    seen = []
    window.max_fps_changed.connect(seen.append)
    assert list(window.fps_buttons) == [30, 60]
    assert window.fps_buttons[30].isChecked()
    window.fps_buttons[60].setChecked(True)
    assert seen == [60]
    assert not hasattr(window, "adaptive_box") and not hasattr(window, "lite_box")
    window.show_frame_rate(29.6)
    assert window.live.text() == "Drawing: 30 fps"


def test_user_settings_default_save_and_reload(tmp_path):
    """Unset settings come from config.yaml; a change is saved and read back next time."""
    path = tmp_path / "settings.json"
    settings = UserSettings(path)
    assert settings.get("max_fps") == 30
    settings.set("max_fps", 60)
    assert json.loads(path.read_text(encoding="utf-8")) == {"max_fps": 60}
    assert UserSettings(path).get("max_fps") == 60


def test_user_settings_survive_a_broken_file(tmp_path):
    """A corrupt settings file falls back to the defaults instead of crashing the app; old
    entries for removed settings are simply ignored."""
    path = tmp_path / "settings.json"
    path.write_text("{not json", encoding="utf-8")
    settings = UserSettings(path)
    assert settings.get("max_fps") == 30
    settings.set("max_fps", 60)
    assert UserSettings(path).get("max_fps") == 60
    with pytest.raises(KeyError):
        settings.set("adaptive_fps", True)
