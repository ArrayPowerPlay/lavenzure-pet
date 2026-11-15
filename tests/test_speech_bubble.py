"""Tests for the speech bubble's sizing: it must fit the line it shows, not the previous one."""
from PySide6.QtCore import QPoint

from overlay.speech_bubble import GREETING_MAX_W, SpeechBubble

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


def test_greeting_is_a_bigger_self_hiding_bubble(qapp):
    """Round 46: the festive greeting gets the big decorated look, fits its text (not the
    markup) and hides by itself (it is not sticky)."""
    bubble = make_bubble(qapp)
    bubble.show_text(SHORT, 4000)
    plain = (bubble.width(), bubble.height())
    bubble.show_greeting("🎄", "Merry Christmas!", "Wishing you a warm and cozy holiday!", 5000)
    assert bubble.isVisible() and not bubble.is_sticky()
    assert bubble.height() > plain[1] and bubble.width() <= GREETING_MAX_W
    assert "Merry Christmas!" in bubble.text()
    bubble.show_text(SHORT, 4000)                  # back to a plain line: plain size again
    assert (bubble.width(), bubble.height()) == plain
    bubble.hide()


def test_greeting_is_centred_over_the_pet_and_lifted(qapp):
    """Round 47: the greeting card sits centred over the anchor (the middle of the pet) and
    ``lift`` pixels higher than a plain bubble; a later plain line drops back down."""
    bubble = make_bubble(qapp)
    bubble.show_greeting("🎄", "Merry Christmas!", "Wishing you a warm and cozy holiday!", 5000)
    assert abs(bubble.x() + bubble.width() / 2 - 400) <= 1
    resting = bubble.y() + bubble.height()
    bubble.show_greeting("🎄", "Merry Christmas!", "Wishing you a warm and cozy holiday!", 5000,
                         lift=24)
    assert bubble.y() + bubble.height() == resting - 24
    bubble.show_text(SHORT, 4000)
    assert bubble.y() + bubble.height() == resting
    bubble.hide()


def test_rounded_corners_are_see_through(qapp):
    """Round 47: only the rounded card is painted, so the very corner pixel stays transparent
    while the middle of the card is opaque."""
    bubble = make_bubble(qapp)
    bubble.show_greeting("🎄", "Merry Christmas!", "Wishing you a warm and cozy holiday!", 5000)
    image = bubble.grab().toImage()
    assert image.pixelColor(0, 0).alpha() == 0
    assert image.pixelColor(image.width() // 2, image.height() - 8).alpha() == 255
    bubble.hide()
