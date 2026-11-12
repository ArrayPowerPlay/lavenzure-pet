"""Pre-simulated flame renderer (``character.flame_renderer: baked``).

The fire motion comes from a real 2D fluid simulation that ``src/bake_flame.py`` ran offline and
saved as temperature frames in ``assets/flame/baked_flame.npz``. At runtime (numpy only, no GPU):

1. **Playback without visible loops** - two "play heads" read the recording. Each plays a random
   stretch of 1.5-4.5 s, then the other head jumps to a random new spot and the image morphs
   across over ~0.6 s. Because the *temperature* fields are blended (not the coloured images),
   the shape flows from one fire into the other instead of showing a ghostly double. Playback
   speed follows the character's flicker speed.
2. **Shaping** - temperature is turned into the same "heat" scale the other renderers use and
   merged with the shared body ellipse (so the face area is always calm and identical). The
   flame height multiplier and flare-ups lower the burn threshold (taller fire); sway and wind
   bend the upper part sideways.
3. **Sticker colours** - heat is upsampled to the bitmap and cut into the flat red / orange /
   yellow bands with a constant-width dark outline (the band edges are divided by the heat
   gradient, exactly like the shader version), anti-aliased.

If the clip file is missing the constructor raises and the metaball renderer is used instead.
"""
from __future__ import annotations

import math
import random
from pathlib import Path

import numpy as np
from PySide6.QtGui import QImage

from overlay.flame_common import (
    BODY_CY,
    BODY_RX,
    BODY_RY,
    INNER_INSET,
    MID_INSET,
    FlameColors,
    FlameDrive,
    ImageFlame,
)

CLIP_PATH = Path(__file__).resolve().parents[2] / "assets" / "flame" / "baked_flame.npz"

_BURN = 0.2           # temperature where the outer outline sits (at flame height 1)
_GAIN = 0.62          # heat per unit of temperature above the burn level
_FADE_S = 0.6         # morph time between two stretches of the recording
_SEGMENT_S = (1.5, 4.5)
_STRETCH = 1.15       # sideways stretch applied to the simulated fire


class BakedFlame(ImageFlame):
    """Plays back the baked fire simulation and colours it in numpy."""

    name = "baked"
    SUPERSAMPLE = 1.25     # numpy does the pixel work, so use fewer pixels; Qt smooths the blit

    def __init__(self, R: float, rng: random.Random) -> None:
        """Load the clip and precompute the sampling grids for radius ``R``."""
        super().__init__(R, rng)
        data = np.load(CLIP_PATH)
        self._frames = data["frames"]                  # (n, ny, nx) uint8, row 0 = top
        self._fps = float(data["fps"])
        x0, x1 = (float(v) for v in data["x_range"])
        h0, h1 = (float(v) for v in data["h_range"])
        n, ny, nx = self._frames.shape
        self._n = n
        cell = (x1 - x0) / nx

        # Body heat at simulation resolution (approximate signed distance, inside positive).
        xs = x0 + (np.arange(nx) + 0.5) * cell
        hs = h1 - (np.arange(ny) + 0.5) * cell        # row 0 = top
        X, Hh = np.meshgrid(xs, hs)
        # The lower body belongs to the shared ellipse only: push the simulated heat down there,
        # so the face area and the rim around it look the same as with every other renderer.
        # Also cut heat that spills sideways out of the body near face height.
        outside = np.clip(-self._ellipse_heat(X, Hh), 0.0, 0.3)
        low = np.clip((BODY_CY + 0.7 - Hh) / 0.6, 0.0, 1.0)
        side = np.clip((BODY_CY + 1.0 - Hh) / 0.5, 0.0, 1.0)
        self._low_penalty = (0.9 * low + 6.0 * outside * side).astype(np.float32)

        # Bitmap pixel -> body coordinates -> fractional simulation cell.
        w, h = self.img_w, self.img_h
        px_x = self.X_RANGE[0] + (np.arange(w) + 0.5) / (R * self.SUPERSAMPLE)
        px_h = -(self.Y_RANGE[0] + (np.arange(h) + 0.5) / (R * self.SUPERSAMPLE))
        rows = np.clip((h1 - px_h) / cell - 0.5, 0.0, ny - 1.001)
        self._i0 = rows.astype(np.int32)
        self._fi = (rows - self._i0).astype(np.float32)[:, None]
        # The simulated fire is sampled a little stretched sideways (fuller crown).
        self._base_j = ((px_x / _STRETCH - x0) / cell - 0.5).astype(np.float32)[None, :]
        PX, PH = np.meshgrid(px_x, px_h)
        self._body_heat = self._ellipse_heat(PX, PH).astype(np.float32)
        self._above = np.maximum(px_h - BODY_CY, 0.0).astype(np.float32)   # per bitmap row (R)
        self._cell = cell
        self._nx = nx
        top = np.clip((px_h - BODY_CY - 0.35) / 1.25, 0.0, 1.0)
        top = top * top * (3 - 2 * top)
        self._lv_mid = (MID_INSET + 0.06 * top).astype(np.float32)[:, None]
        self._lv_inner = (INNER_INSET + 0.15 * top).astype(np.float32)[:, None]
        self._buffer = np.zeros((h, w, 4), dtype=np.uint8)

        # Play heads: (position in frames, frames left in this stretch).
        self._heads = [self._new_head(), self._new_head()]
        self._active = 0
        self._fade = 1.0          # 1 = only the active head is visible
        self._flare = 0.0

    # ------------------------------------------------------------------ helpers

    @staticmethod
    def _ellipse_heat(x: np.ndarray, h: np.ndarray) -> np.ndarray:
        """Approximate signed distance to the body ellipse in R (positive inside)."""
        u = x / BODY_RX
        v = (h - BODY_CY) / BODY_RY
        q = np.sqrt(u * u + v * v) + 1e-6
        grad = np.sqrt((u / BODY_RX) ** 2 + (v / BODY_RY) ** 2) / q
        return -(q - 1.0) / grad

    def _new_head(self) -> list[float]:
        """A play head at a random spot with a random stretch length (both in frames)."""
        length = self._rng.uniform(*_SEGMENT_S) * self._fps
        start = self._rng.uniform(0.0, max(1.0, self._n - length - 2))
        return [start, length]

    def _frame_at(self, pos: float) -> np.ndarray:
        """Temperature at fractional frame ``pos`` (linear blend of the two nearest frames)."""
        pos = min(max(pos, 0.0), self._n - 1.001)
        k = int(pos)
        f = pos - k
        a = self._frames[k].astype(np.float32)
        b = self._frames[k + 1].astype(np.float32)
        return (a + (b - a) * f) * (1.0 / 255.0)

    # ------------------------------------------------------------------ FlameRenderer API

    def flare(self, strength: float = 1.0) -> None:
        """Make the fire burn taller for a moment."""
        self._flare = min(1.4, self._flare + strength)

    def step(self, drive: FlameDrive) -> None:
        """Advance playback and remember the inputs; the bitmap is built in ``paint()``."""
        dt = drive.dt
        self._flare *= math.exp(-2.6 * dt)
        frames = dt * self._fps
        for head in self._heads:
            head[0] += frames
            head[1] -= frames
        active = self._heads[self._active]
        if self._fade >= 1.0 and active[1] <= 0.0:
            # Start morphing into a fresh stretch on the other head.
            self._active = 1 - self._active
            self._heads[self._active] = self._new_head()
            self._fade = 0.0
        if self._fade < 1.0:
            self._fade = min(1.0, self._fade + dt / _FADE_S)
        self._drive = drive
        self._dirty = True

    def paint(self, painter, colors: FlameColors) -> None:
        """Build the bitmap for this frame if needed, then blit it."""
        if getattr(self, "_dirty", False):
            self._dirty = False
            self._render(colors)
        super().paint(painter, colors)

    # ------------------------------------------------------------------ rendering

    def _render(self, colors: FlameColors) -> None:
        """Temperature -> heat -> upsampled, bent bitmap with sticker colours."""
        drive = self._drive
        temp = self._frame_at(self._heads[self._active][0])
        if self._fade < 1.0:
            k = self._fade * self._fade * (3 - 2 * self._fade)
            old = self._frame_at(self._heads[1 - self._active][0])
            temp = old + (temp - old) * k

        # Taller flame / flare-ups lower the burn threshold high up (the body stays the same).
        height = max(0.5, drive.flame * (1.0 + 0.3 * self._flare))
        burn = _BURN / height
        heat = (temp - burn) * _GAIN - self._low_penalty

        # Bend: shift each bitmap row sideways by the lean / wind (none below the body centre).
        above = self._above
        wind = max(-0.9, min(0.9, -drive.wind_x * 0.18))
        shift = (drive.sway * above * 0.55 + above * above * 0.32 * wind) / self._cell
        j = self._base_j - shift.astype(np.float32)[:, None]
        np.clip(j, 0.0, self._nx - 1.001, out=j)
        j0 = j.astype(np.int32)
        fj = j - j0
        # Separable bilinear sampling: rows first (fixed per bitmap row), then the bent columns.
        i0 = self._i0
        upper = heat[i0]
        rows = upper + (heat[i0 + 1] - upper) * self._fi
        left = np.take_along_axis(rows, j0, axis=1)
        right = np.take_along_axis(rows, j0 + 1, axis=1)
        sim = left + (right - left) * fj
        # Soft maximum so the simulated fire melts smoothly into the body outline.
        body = self._body_heat
        kk = 0.08
        hd = np.clip(0.5 + 0.5 * (sim - body) / kk, 0.0, 1.0)
        H = body + (sim - body) * hd + kk * hd * (1.0 - hd)

        self._colorize(H, colors)
        self._update_top_points(self._buffer[:, :, 3])

    def _colorize(self, H: np.ndarray, colors: FlameColors) -> None:
        """Cut heat into bands + outline (anti-aliased) and write premultiplied BGRA pixels."""
        gy, gx = np.gradient(H)
        g = np.sqrt(gx * gx + gy * gy)
        np.maximum(g, 1e-5, out=g)
        inv = 1.0 / g
        half = colors.outline_px * self.SUPERSAMPLE * 0.5
        d0 = H * inv
        cov = np.clip(d0 + (half + 0.5), 0.0, 1.0)
        fill = np.clip(d0 - (half - 0.5), 0.0, 1.0)
        m = np.clip((H - self._lv_mid) * inv + 0.5, 0.0, 1.0)
        i = np.clip((H - self._lv_inner) * inv + 0.5, 0.0, 1.0)
        buf = self._buffer
        for ch, attr in ((0, "blue"), (1, "green"), (2, "red")):
            o = getattr(colors.outer, attr)()
            md = getattr(colors.mid, attr)()
            inn = getattr(colors.inner, attr)()
            ink = getattr(colors.ink, attr)()
            col = o + (md - o) * m
            col += (inn - col) * i
            col = ink + (col - ink) * fill
            buf[:, :, ch] = col * cov
        buf[:, :, 3] = cov * 255.0
        self.image = QImage(buf.data, self.img_w, self.img_h, self.img_w * 4,
                            QImage.Format.Format_ARGB32_Premultiplied)
