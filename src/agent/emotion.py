"""Emotion tags: the model starts each reply with one tag saying how Calcifer feels about it.

The system prompt asks for a leading ``[happy]``, ``[scared]``, ``[angry]``, ``[chill]``,
``[surprised]``, ``[thinking]`` or ``[other]``. ``split_emotion`` takes the tag off so the chat
only shows the clean text, and the pet plays the matching face for a few seconds (``other`` or a
missing / unknown tag = keep the current face).
"""
from __future__ import annotations

import re

EMOTIONS = ("happy", "scared", "angry", "chill", "surprised", "thinking", "other")

# A tag at the very start, optionally wrapped in markdown emphasis, e.g. "[happy] Hi!" or
# "**[Happy]**\nHi!". Case and spaces inside the brackets are ignored.
_TAG = re.compile(r"^\s*[*_]{0,2}\[\s*([A-Za-z]+)\s*\][*_]{0,2}[ \t]*\n?\s*")

EMOTION_INSTRUCTIONS = (
    "Begin every reply with exactly one emotion tag showing how you feel about it: "
    + ", ".join(f"[{e}]" for e in EMOTIONS)
    + ". Use [other] when no particular feeling fits. Put nothing before the tag."
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
