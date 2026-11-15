# Props (accessories and objects)

Existing props live in `src/overlay/props.py`: `LogProp` (ridden while flying), `PanProp`
(frying pan with bacon and eggs for `chill`), `SunglassesProp` (`cool`), `AlarmClockProp`
(ringing beside the pet while a reminder is due) and `Snores` (floating "z"s). Outfits worn
across every mood live in `src/overlay/outfits.py`: `ScarfProp` (Christmas, `set_outfit("xmas")`)
hugs the lower body with `flame_common.body_half_width` (the shader body's exact width at a
height) and pre-draws its still parts into cached images; copy it for anything that must fit
the body of every expression. An outfit can also dress other props: the Xmas outfit sets
`LogProp.snow` (snow patches on the log, faded with the scarf). Copy the closest
one; `SunglassesProp` is the smallest complete example.

## Shape of a prop

A prop is a small model + painter - **not** a widget and it never moves the window:

```python
class HatProp:
    """One-line purpose, how it enters / leaves, what it follows."""

    def __init__(self, R: float) -> None:      # R = character radius in pixels
        self.R = R
        self.visible = False
        self._drop = Spring(0.0, stiffness=190.0, damping=17.0)   # from flame_common
        self._target = 0.0

    def show(self) -> None: ...                # start entering (reset springs if it was gone)
    def hide(self) -> None: ...                # start leaving; set visible False when done
    def update(self, dt: float) -> None: ...   # springs, fades, small timers
    def landing_impact(self) -> bool: ...      # optional: True on the frame it lands
    def paint(self, painter, ...) -> None: ...
```

- Sizes in units of `R`; painting happens in the character's body coordinates (pixels, origin
  at the feet, y *up is negative*). Springs with slight under-damping give the landing dip and
  overshoot the user likes; fade in and out instead of popping.
- Style: flat fills, the same dark maroon outline (`INK`, round caps, about `0.04-0.06 R` thick), no gradients that
  fight the sticker look. When there is no reference, pick colours that separate from the orange
  fire (the alarm clock uses teal for its bells and feet). A small glint or highlight sells it.
- Follow the face, don't float over a fixed spot: the glasses take `face.eye_boxes()` every
  frame so they tilt and squash with the expression; the pan sits on `face.eye_top()`.

## Wiring it into `FlameCharacter`

1. Import and construct next to the others in `__init__` (`self.hat = HatProp(self.R)`).
2. `play()` (or a `set_*` flag): call `self.hat.show()` for its mood.
3. `_step`: hide it when the mood is not active (`if mood != Mood.X: self.hat.hide()`).
4. `_update_props`: `self.hat.update(dt)`; if it lands, nudge the body
   (`self._squash.velocity -= 0.6` - the pan squishes the head, the glasses nod).
5. `paint()` order decides what covers what:
   - things attached to the body (pan, glasses) are painted **inside** the translated / scaled /
     sheared body transform, after `face.paint`, so they squash and lean with the body;
   - things beside or under the body (alarm clock, log paws) are painted **outside** it so they
     do not squash with it; with the `shader` renderer the log goes *behind* the fire so the
     flame paws drape over it.
6. Tests: copy `test_cool_mood_wears_sunglasses_and_takes_them_off` in `tests/test_face.py`
   (show on mood start, gone after it ends).
7. Update the module docstring list at the top of `props.py` and the one in `character.py`.

## Checks

Render it with `scripts/render_sheet.py --frames 6 --frames 40 --frames 150` to catch the
entry, the landing and the settled pose; also check that it never hides the mouth or leaves the
canvas (`FlameCharacter.width` x `height`, sized for the pan handle and the log), and that
leaving the mood removes it cleanly (no leftover after `stop_transient`).
