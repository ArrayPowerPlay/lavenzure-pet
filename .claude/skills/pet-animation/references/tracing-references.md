# Copying a figure from the reference sheet ("copy y hệt")

When the user says to copy a face exactly ("copy y hệt", "đừng tạo mới", "không giống"), do **not**
tune parametric values until it looks similar: earlier rounds did that (almond eyes, hand-set
mouths) and were rejected again and again. Trace the figure from the image, store the outline as
data and blend it in with an `Expression` weight. Already traced: **fig. 1** (`happy`, sly grin)
and **fig. 7** (`chill`, under the pan); the sheet's other figures map to fig. 2 `happy` (beaming,
parametric), fig. 3 `scared`, figs. 4-5 the log, fig. 6 `angry`, fig. 8 `yuck`.

Source image: `docs/references/calcipher_picked.jpg` (the user's numbered picks, 736 x 1279 px,
local only). Everything below uses the image's own pixel coordinates, y down.

## 1. Find and read the figure

Open the image with `Read`, locate the figure by its number, then zoom with the grid helper:

```bash
.venv-win/Scripts/python.exe .claude/skills/pet-animation/scripts/crop_grid.py \
    docs/references/calcipher_picked.jpg .scratch/fig.png X Y W H --zoom 10 --step 5
```

`X Y W H` is a crop around the eyes + mouth (about 80 x 60 px for a face at the sheet's scale).
Open `.scratch/fig.png`: grid lines are labelled with image coordinates, so you can read where an
outline passes. Zoom in further on the eyes and the mouth separately if needed.

## 2. Trace

Write polylines of about 25-35 points going round each shape, evenly spaced, with extra points on
sharp corners:

- **each eye**: closed outline (the dark rim's *outer* edge), plus the pupil as an ellipse
  `(cx, cy, rx, ry)`; the eye outline clips the pupil, so a pupil hanging off the top edge is
  fine;
- **open mouth** (`RefMouth.trace_open`): closed outline of the mouth + the tongue's *upper edge*
  as an open polyline from the left lip to the right lip;
- **closed mouth** (`RefMouth.trace_line`): the centre line left to right + short corner strokes,
  each starting on the line (dimples, tails).

Check a trace before using it: pass it to `crop_grid.py --points "x,y x,y ..."` and look at the
overlay. The points must sit on the drawn outline, not inside the shape.

## 3. Store it (`src/overlay/face_refs.py`)

Add the lists (`_FIG3_LEFT_EYE = [...]`, `_FIG3_MOUTH`, ...) with a comment describing the figure,
then a `REF_FACES["fig3"] = RefFace(scale, origin, eyes, mouth, eye_ink, mouth_ink)` entry:

- `scale`: image pixels -> R (fig. 1 uses 0.021, fig. 7 0.022; choose it so the eyes come out the
  size of the figure's eyes relative to the body);
- `origin`: the image point that maps to the middle between the eyes;
- `eye_ink` / `mouth_ink`: line widths in image pixels (measure the dark rim, about 2.3-2.7).

`RefEye.trace` turns an outline into a radial profile and `RefMouth.trace_*` into lip curves
sampled like the parametric mouth, so they blend point for point - nothing else to write.

## 4. Hook it up (`src/overlay/face.py`)

The weight names are spelled out in a few places; add the new one to each (grep `fig7`):
- `Expression`: a `figN: float = 0.0` field;
- `Face._start_mood`: the `copied = goal.fig1 > 0.0 or goal.fig7 > 0.0` test (copied faces are
  never mirrored);
- `Face._refs`: the `(("fig1", ...), ("fig7", ...))` tuple;
- the eye-geometry cache key in `_eye_geom` (it lists `ex.fig1, ex.fig7`) - forgetting this
  gives stale eyes (`test_eye_geometry_cache_follows_every_change` guards it).

Then the mood's `Expression` sets `figN=1.0` and parametric values that are *close to the copy*
(sizes, widths, gaze), so the blend does not pass through a different face on the way in. Add
the new figure to the parametrization of `test_copied_faces_settle_fully` in `tests/test_face.py`
and to `test_reference_data_is_sane`.

## 5. Prove it matches

```bash
.venv-win/Scripts/python.exe .claude/skills/pet-animation/scripts/render_sheet.py \
    .scratch/cmp.png --moods <mood> --frames 150 --scale 2.5 \
    --ref docs/references/calcipher_picked.jpg --crop X,Y,W,H
```

Look at the reference and the render side by side: eye shape, pupil position and size, lip
curves, tongue, strokes. Fix the trace (not the weights) when they differ. Only report "matches"
after this comparison, and say which details you checked.
