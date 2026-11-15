---
name: pet-animation
description: How to design, add, change or debug animations of the Lavenzure flame desktop pet - moods and facial expressions, props (log, frying pan, sunglasses, alarm clock), left-click reactions, body motion and the flame's look. Use this whenever the user talks about an animation, expression / biểu cảm, mood, face, mặt, reaction, prop, accessory, pose, the fire / flame / lửa, "copy y hệt" a figure from the reference sheet, or wants the pet to look or move in a new way - even when they never say "animation".
---

# Pet animation

Lavenzure is drawn entirely in code (QPainter vectors + a GLSL flame, no image assets). Almost
every animation task is "add or change a mood, a prop, a reaction, or how the fire moves". This
skill holds the mental model, the art direction the user has already approved or rejected, and a
workflow that ends with the user *seeing* the result. Read it fully once, then jump to the
reference file for the kind of change you are making.

## How the pet is drawn

Four layers, each owning one thing. Keep changes in the layer that owns them:

| Layer | File | Owns |
|---|---|---|
| Behavior | `src/overlay/behavior.py`, `animation.py` | Moving the whole **window** (walk, float, jump, drag), picking a mood for the state, the left-click **reaction pool** |
| Character | `src/overlay/character.py` | Body physics, mood layering, glow, embers, props, painting order |
| Face | `src/overlay/face.py`, `face_refs.py` | Eyes, lids, brows, mouth, gaze, blinking, micro-expressions; **expressions are data** |
| Flame body | `flame_common.py`, `flame_shader.py` (+ `fire_field.py`, `flame_baked.py`) | The fire silhouette and its three colour bands |

Rules that follow from the design (breaking them is the most common source of bad results):

- **Body language is derived from the window's movement.** Lean, stretch, hop and landing squash
  come from `FlameCharacter.update(dt, window_pos, cursor)` watching the window move. Movement
  code never animates the body directly - to get a jump that squashes on landing, move the window.
- **A mood is one `Expression` target.** Add a `Mood` and an entry in `MOOD_TARGETS`; the face
  blends toward it with springs, an anticipation kick and a delayed mouth. Never set face fields
  frame by frame from outside.
- **Mood layering** (highest wins): transient `play(mood, seconds)` > alert > reminding >
  sleeping > thinking > riding the log > normal. `set_*` flags are the persistent base, `play()`
  overrides them for a while.
- **Everything on the face stays inside the face safe area** (an ellipse on the yellow body,
  `FACE_*` in `flame_common.py`), so even the biggest grin never spills onto the orange rim.
- Only the **`shader` renderer** draws the full body shape (`body_w`, `body_h`, `boxy`, `jag`,
  paws); `metaball` and `baked` only scale. `shader` is the user's choice, so design for it.
- Click-through relies on per-pixel alpha: never add `setMask()`, and keep the glow fading to 0.

## Art direction (decided with the user - do not relitigate)

The target is the user's fan-art sticker sheet: `docs/references/calcipher.jpg`, and their
numbered picks in `docs/references/calcipher_picked.jpg`. These are third-party art kept **local
only** (git-ignored): never commit them, never copy original film assets.

- Flat sticker look: red rim / orange band / big yellow body, **one continuous thick dark maroon
  outline** (`INK`), big white eyes with dark pupils, wide red mouth with a pink tongue.
- Teardrop flame with one main tip and smaller tongues that **move** (not fixed slots), flickering
  like real fire - unpredictable, never a loop you can see repeat.
- Keep the soft glow. **No white sticker border** (it would flicker on the changing outline).
- Face lines are lighter than the body outline (`EYE_INK_W`, `CLOSED_EYE_INK_W`, `MOUTH_INK_W`
  in `face.py`, round 42) and the mouth outline keeps one on-screen width at any mouth size.
- The body shape is not fixed: an expression may puff up, go boxy and ragged, flatten or stretch
  to suit the emotion.
- Priority is beautiful, natural, smooth, lively motion; quality matters more than CPU cost,
  within the budget below.

What the user has rejected (so you do not propose it again): five tall pointy tongues at fixed
positions ("gượng, gai nhọn cố định"), tongues built from separate pieces ("đứt gãy"), faces that
only *approximate* a reference ("không giống", "đơ, cứng"), a mouth that spills out of the face,
a face that spreads wide to the sides.

## Pick the kind of change

| The user wants... | Do this | Read |
|---|---|---|
| A new emotion / face the pet can show (also reachable from clicks and from the AI's reply tag) | New `Mood` + `Expression` + reaction + emotion tag | `references/new-mood.md` |
| An accessory or object (hat, pan, glasses, clock...) | New prop class wired into `FlameCharacter` | `references/props.md` |
| A face copied exactly from a figure of the sheet ("copy y hệt", "đừng tạo mới") | Trace it into `face_refs.py`, blend with an `Expression` weight | `references/tracing-references.md` |
| New movement, a different jump / walk feel, body squash, or a change of the fire itself | Window movement (behavior) or `FlameDrive` / shader | `references/motion-and-flame.md` |
| Just retune an existing look | Edit the numbers in that mood's `Expression`, then check with the sheet | (this file) |

## Workflow

1. **Know the target.** Is there a reference figure (a spec - match it) or is it a free design
   (decide, then say so)? If it is a real open design choice and the user gave no hint, state
   the look you plan in two or three lines and ask before building; for tiny tweaks just do it.
2. **Build the smallest slice** that can be seen - usually the `Expression` values alone - and
   render it before wiring the rest (reaction, AI tag, tests).
3. **Look at it.** Render a contact sheet and open the PNG (`Read` shows images):
   ```bash
   .venv-win/Scripts/python.exe .claude/skills/pet-animation/scripts/render_sheet.py \
       .scratch/sheet.png --moods normal,<mood> --frames 12 --frames 150
   ```
   Row one (`--frames 12`) catches the anticipation kick, row two the settled face. Add
   `--ref docs/references/calcipher_picked.jpg --crop X,Y,W,H` to put the reference next to your
   render, and `--light` to check a light desktop. Look for: features leaving the yellow area,
   a mouth overlapping the eyes, a doubled / ghosted shape during blends, a flat or lifeless
   pose, an outline that breaks.
4. **Compare with the reference** before reporting, side by side, whenever there is one.
   "Looks about right" is how earlier rounds went wrong.
5. **Try it alive** (blinking, gaze following the mouse, transitions into and out of the mood):
   `.venv-win/Scripts/python.exe src/character_preview.py` shows every mood and motion in a
   normal window. Do not produce GIF / MP4 exports - the user does not want them.
6. **Guard the rest.** `python -m pytest` and `python -m ruff check .` (see `CLAUDE.md` for the
   commands). If you touched a per-frame hot path (`face.py`, a flame renderer, `character.py`
   update / paint), also prove the picture did not change with `scripts/snap_frames.py`
   (`dump` before and after, then `compare`).
7. **Report in plain language** with the image, and say what you matched, what you designed
   freely and what is left for the user to judge. The user reviews in rounds and asks for
   changes; when they settle something, append it to `docs/DECISION_LOG.md` (decisions live
   there, not in new files) and tick the item in `docs/implementation_plan.md`.

## Making it feel alive (what `face.py` already does - extend it, don't bypass it)

- **Overlapping timing**: eyes react first, the mouth follows ~75 ms later (`MOUTH_DELAY`).
- **Springs with overshoot** (`SPRUNG_FIELDS`) so eyes "pop", plus an **anticipation kick** in
  `Face._start_mood` (a small squeeze the wrong way first). Every new mood needs one.
- **Lids** (upper lid slant, lower lid pushed up by cheeks) and asymmetric blinks.
- **Head turn**: features sit on a sphere, so gaze shifts slide the whole face.
- **Idle micro-expressions** (`MICRO_EXPRESSIONS`) so the neutral face is never frozen.
- Moods with variants (`happy` has two faces) pick one at random each time; lopsided looks are
  mirrored at random, except faces copied from the sheet, which are never mirrored.
- Embers and flare-ups sell the energy: `EMBER_RATES` and the `play()` side effects in
  `character.py` (hop, squash jolt, sparks).

## Budget and pitfalls

- Frame budget: about 2.5-5 ms per frame at scale 0.75 (`update` + `paint`), 30 fps by default,
  60 selectable. The code runs per frame: reuse caches, skip values that have settled, avoid
  allocating in loops. Measure with the cost shown in `character_preview.py`.
- Any on-screen **text** that comes with an animation needs English **and** Vietnamese
  (`src/pet_lines.py`, `data/*.json`); code and comments stay English.
- New files start with a module docstring; every class and function gets a docstring.
- Source line endings are mixed (many `src/overlay/*.py` are CRLF): keep each file's endings,
  and treat a whole-file diff with no real change as a line-ending flip.
- Run the app and scripts with `.venv-win` (Windows Python via WSL), not the Linux venv; the
  Linux venv is only for rough previews, never for judging overlay behavior.
- `docs/references/` and `.scratch/` are git-ignored: put throwaway scripts and renders in
  `.scratch/`, and do not reference the sheet's pixels from anything that ships.
