"""Emotion tags: the model starts each reply with one tag saying how Lavenzure feels about it.

The system prompt asks for a leading ``[happy]``, ``[scared]``, ``[angry]``, ``[chill]``,
``[surprised]``, ``[thinking]``, ``[yuck]``, ``[cool]`` or ``[other]``. ``split_emotion`` takes
the tag off so the chat only shows the clean text, and the pet plays the matching face for a few seconds
(``other`` or a missing / unknown tag = keep the current face).

While a reply is still streaming in, ``split_emotion_partial`` tells whether the start of the text
can still turn into a tag (e.g. ``"[hap"``), so a half-received tag never flashes in the chat.
"""
from __future__ import annotations

import re

EMOTIONS = ("happy", "scared", "angry", "chill", "surprised", "thinking", "yuck",
            "cool", "other")

# A tag at the very start, optionally wrapped in markdown emphasis, e.g. "[happy] Hi!" or
# "**[Happy]**\nHi!". Case and spaces inside the brackets are ignored.
_TAG = re.compile(r"^\s*[*_]{0,2}\[\s*([A-Za-z]+)\s*\][*_]{0,2}[ \t]*\n?\s*")
# What the start of a reply looks like while a tag is still arriving: "", "*", "[", "**[hap", ...
_TAG_PREFIX = re.compile(r"^\s*[*_]{0,2}(\[\s*[A-Za-z]*\s*)?$")

EMOTION_INSTRUCTIONS = (
    "Begin every reply with exactly one emotion tag showing how you feel about it: "
    + ", ".join(f"[{e}]" for e in EMOTIONS)
    + ". Use [yuck] for disgust (something gross, bad taste, awful code). Use [cool] when you"
    " feel smug or proud (praised, showing off, a slick answer). Use [other] when no"
    " particular feeling fits. Put nothing before the tag."
)


def split_emotion(reply: str) -> tuple[str | None, str]:
    """Return ``(emotion, text)``: the leading tag's emotion (lower case, ``None`` when there is
    no known tag or it is ``other``) and the reply without the tag."""
    match = _TAG.match(reply)
    if not match:
        return None, reply.strip()
    name = match.group(1).lower()
    if name not in EMOTIONS:
        return None, reply.strip()
    text = reply[match.end():].strip()
    return (None if name == "other" else name), text


def split_emotion_partial(partial: str) -> tuple[str | None, str, bool]:
    """Like ``split_emotion`` for a reply that is still arriving.

    Returns ``(emotion, text, settled)``. ``settled`` is False while the text so far could still
    be the beginning of a tag; then nothing should be shown yet. Once settled, ``emotion`` and
    ``text`` are what ``split_emotion`` would give for the text so far.
    """
    if _TAG_PREFIX.match(partial):
        return None, "", False
    emotion, text = split_emotion(partial)
    return emotion, text, True
