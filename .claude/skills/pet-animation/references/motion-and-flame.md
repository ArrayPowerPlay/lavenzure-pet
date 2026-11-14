# Motion and the flame itself

## Moving the pet (behavior)

`BehaviorController` (`src/overlay/behavior.py`) moves the whole **window**; helpers in
`animation.py` (`move_to_animation`, `jump_animation`) animate the sub-pixel `exactPos`. Speeds
are constants at the top of `behavior.py`, state weights come from `config.yaml`
(`behavior.state_weights`). Use restartable single-shot `QTimer`s (not `QTimer.singleShot`) so a
stale timeout cannot advance the loop twice.

What the *character* then does by itself, in `FlameCharacter` (`_update_velocity`,
`_update_body`): lean against the direction of travel, stretch when fast vertically, squash on
landing (a window that was falling and stopped for two frames), hop while walking, bob on the
log, fire trailing behind as "wind". So:

- A new movement style = new window movement in `behavior.py` (a new `PetState` or a new
  motion inside an existing one) and the body follows. Tune feel with the spring constants
  (`_squash`, `_lean`) and the thresholds in `_update_body` - not by animating the body in the
  behavior code.
- Priorities (drag > alert > remind > react > chat > sleep > wander) are resolved in `_resume()`.
  A new state must say where it sits in that list and what happens when it ends.
- `character_preview.py` fakes window movement (`start_motion`: walk / float / jump) to show the
  body physics without the app; add a fake motion there to preview a new one.

## The fire

`FlameCharacter._update_fire` builds a `FlameDrive` each frame (clock, wild, height, wind, sway,
breath, body shape, log paws) and the renderer draws from it:

- `flame_common.py`: body geometry (`BODY_*`, `FACE_*`), `FireWeather` (slow calm / gust /
  crackle / lull phases + a drifting tip, so the fire never repeats), the `FlameRenderer`
  interface, `FlameDrive`, `FlameColors`.
- `flame_shader.py` (default): GLSL on an offscreen QOpenGL 3.3 context, read back into a
  QImage (this keeps the layered window's per-pixel click-through). Body shape arrives as
  uniforms (`uShape`: `body_w`, `body_h`, `boxy`, `jag`). A new body-shape parameter means:
  a field on `Expression`, a field on `FlameDrive`, passing it in `_update_fire`, a uniform
  in the shader, and a `SPRUNG_FIELDS` / `SLOW_FIELDS` entry so it eases instead of snapping.
- `fire_field.py` (`metaball`) and `flame_baked.py` (`baked`, clips from `src/bake_flame.py`) are
  fallbacks / comparisons that only scale the body. Keep them working, but do not design new
  looks around them. The shader falls back to `metaball` if OpenGL 3.3 is missing.
- Colours: `CALM_PALETTE`, `ALERT_PALETTE`, `NIGHT_PALETTE` in `character.py`; `INK` is the
  outline colour everywhere. Three flat bands (red / orange / yellow) + one outline - no
  gradients inside the body.

When the fire's *look* changes (shape, tongues, bands), judge it moving, not in one frame:
run `character_preview.py` and also render a short sequence, because "looks like real fire" is a
property of the motion. The user's bar: unpredictable, no visible loop, no fixed tongue slots,
no broken outline.

## Performance

~2.5-5 ms/frame at scale 0.75 is the measured cost; the user chose 30 fps and the "lite flame"
(lower internal resolution, `performance.lite_flame_supersample`). Frames longer than 1/30 s
are sub-stepped in `FlameCharacter.update`, so physics must not depend on the frame rate.
Hot-path code (`face.py`, renderers) relies on caches and settled-value skipping; when you
change it, `scripts/snap_frames.py dump` before and after and `compare` - the pictures must be
identical unless the change is meant to alter them. For real-app load use
`src/perf_check.py` (quit the running pet first).
