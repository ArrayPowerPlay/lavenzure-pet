# Adding a mood (a new face / emotion)

A mood is a named face the pet can show. It can come from three places - a left-click reaction,
the AI's emotion tag, or a program event (alert, reminder, sleep) - and every place needs a
tiny hook. Use `cool` (sunglasses + smirk) and `yuck` as worked examples: grep for `Mood.COOL`.

## 1. The face (`src/overlay/face.py`)

1. Add the member to `Mood` with a one-line comment saying what it looks like.
2. Add `Mood.X: (Expression(...),)` to `MOOD_TARGETS`. Give a tuple of several `Expression`s
   when the mood has variants (one is picked at random each time it starts). Only set fields
   that differ from the defaults. Fields worth knowing:
   - eyes: `eye_open`, `eye_scale`, `eye_wide`, `eye_y`, `almond`, `slant`, `lower_lid`,
     `happy_eyes` (closed "^ ^"), `eye_wonk`, `pupil`, `gaze_x/y` + `gaze_lock`, `brow`
   - mouth: `mouth_open`, `smile` (-1..1), `mouth_round`, `mouth_width`, `mouth_top/bottom`,
     `mouth_dip`, `mouth_cat`, `mouth_curl`, `smirk`, `mouth_tilt`, `tongue_out`
   - head / body: `tilt`, `shake`, `body_w`, `body_h`, `boxy`, `jag`, `snooze`
   - fire: `flame` (height), `flicker` (speed), `wild` (strength + flare-ups), `alert` (palette)
   - `fig1` / `fig7`: blend weights of faces traced from the sheet (see `tracing-references.md`)
   The dataclass in `face.py` documents every field; read it rather than guessing ranges.
3. Add an **anticipation kick** for it in `Face._start_mood` (`vel["body_h"] -= 1.2` and the
   like: a small squeeze the "wrong" way before the spring pops past the target). It is what
   makes a change of mood read as a reaction instead of a state swap.
4. Mood-specific tuning, only if needed: `SLOW_FIELDS`, `DROWSY_MOODS` (sleepy transitions),
   `FAST_FIELDS` (shapes that cross-fade between two drawings).
5. Keep every feature inside the face safe area; check wide mouths and big eyes.

## 2. The character (`src/overlay/character.py`)

- `EMBER_RATES[Mood.X]`: spark rate while the mood shows (default 2.5; calm 1-1.5, wild 8-11).
- `FlameCharacter.play()`: add an `elif mood == Mood.X:` branch for side effects - a hop
  (`bounce`), a squash jolt (`_squash.velocity`), `flame.flare()`, `burst()`, showing a prop.
- A mood that is a **persistent state** instead of a timed `play()` (like alert, reminding,
  sleeping): add a `_x` flag + `set_x()`, put it in the `mood` property at the right priority,
  and mention it in the layering line of the module docstring.
- A prop that belongs to the mood must be hidden when the mood ends: see `_step`
  (`if mood != Mood.COOL: self.shades.hide()`). See `props.md`.
- If it clashes with riding the log (the log hides the face, as with the pan), map it to another
  mood inside `play()` and skip it in `BehaviorController.play_random_reaction`.

## 3. The click reaction (`src/overlay/behavior.py`)

```python
@reaction("x")
def _react_x(self) -> float:
    """One-line description of what the pet does."""
    return self._play(Mood.X, 2.4)          # mood, seconds (+ hop=0.7 for a jump)
```

The decorator registers it: it joins the left-click pool automatically (never twice in a row).
Return the length in seconds (`None` if the reaction ends itself, like `fly`). Add the name to
the set asserted in `tests/test_behavior.py::test_pool_has_every_animation_but_not_alert_or_sleep`.
Program-driven moods (alert, reminder, sleep) are *not* reactions: `trigger_*` / `set_*` methods
in the controller drive them, following the priority list in the module docstring.

## 4. The AI's emotion tag (only if the AI should be able to pick it)

- `src/agent/emotion.py`: add the word to `EMOTIONS` and, when it needs a hint on when to use
  it, one sentence to `EMOTION_INSTRUCTIONS` (see `[yuck]`, `[cool]`).
- `src/main.py`: add it to `EMOTION_MOODS` (tag -> `Mood`).
- `tests/test_emotion.py`: copy `test_cool_is_offered_to_the_model`.
- After changing the prompt text, run the real-model check mentioned in `CLAUDE.md` if the
  change touches reminders; otherwise a unit test is enough.

## 5. Preview, tests, docs

- `src/character_preview.py`: add a button (`each(lambda ch: ch.play(Mood.X, 2.4))`; persistent
  flags also need resetting in `reset()`).
- `tests/test_face.py`: add the mood to `test_mood_settles_on_target` (it settles on one of its
  targets); `test_every_mood_has_a_target` already covers the table.
- README (`README.md`, `README_vi.md`) lists the expressions and shows
  `docs/images/expressions.png`; refresh the picture and the alt text only when the user wants
  the README updated (render each mood with `scripts/render_sheet.py`, crop to the drawn pixels).
- `docs/DECISION_LOG.md` (new round entry) and the `docs/implementation_plan.md` checkbox.
- Any line the pet says with it: English + Vietnamese in `PetLines` / `data/`.

## Quick checklist

`Mood` enum -> `MOOD_TARGETS` -> `_start_mood` kick -> `EMBER_RATES` -> `play()` branch ->
`@reaction` -> (`EMOTIONS` + `EMOTION_MOODS`) -> preview button -> tests -> render the sheet and
look at it -> ruff + pytest -> report with the image.
