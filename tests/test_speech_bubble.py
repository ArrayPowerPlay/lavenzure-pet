"""Tests for the speech bubble's sizing: it must fit the line it shows, not the previous one."""
from PySide6.QtCore import QPoint

from overlay.speech_bubble import SpeechBubble

LONG = ("Firefighters sometimes fight fire with fire: they burn a strip of land ahead of time "
        "so the big fire has nothing left to eat.")
SHORT = "Good morning! Hope you slept well and have a gentle start to your day:>"


def make_bubble(qapp):
    """A bubble anchored somewhere on screen."""
    return SpeechBubble(lambda: QPoint(400, 400))


def test_short_line_after_long_line_is_not_oversized(qapp):
    """A reused bubble shrinks back: the short line gets the same size as in a fresh bubble."""
    used = make_bubble(qapp)
    used.show_text(LONG, 4000)
    used.show_text(SHORT, 4000)
    fresh = make_bubble(qapp)
    fresh.show_text(SHORT, 4000)
    assert (used.width(), used.height()) == (fresh.width(), fresh.height())
    used.hide()
    fresh.hide()


def test_long_line_wraps_into_more_height(qapp):
    """The longer line needs a taller bubble than the shorter one."""
    bubble = make_bubble(qapp)
    bubble.show_text(SHORT, 4000)
    short_height = bubble.height()
    bubble.show_text(LONG, 4000)
    assert bubble.height() > short_height
    bubble.hide()


def test_one_word_is_a_small_bubble(qapp):
    """A tiny line after a big one gets a small bubble (not the width/height of the big one)."""
    bubble = make_bubble(qapp)
    bubble.show_text(LONG, 4000)
    big = (bubble.width(), bubble.height())
    bubble.show_text("Hi!", 4000)
    assert bubble.width() < big[0] and bubble.height() < big[1]
    bubble.hide()
