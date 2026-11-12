"""Offline baker for the ``baked`` flame renderer: runs a real 2D fire simulation and saves it.

Usage (from the repo root, takes a minute or two):

    .venv-win/Scripts/python.exe src/bake_flame.py [--seconds 24] [--seed 7] [--preview out.png]

What it simulates - a small "stable fluids" solver (Jos Stam's method) in numpy:

- The flame body (the same ellipse every renderer uses, see ``overlay.flame_common``) is a
  burner: it keeps injecting heat and a gentle upward push, with the strength varying in space
  and time so the fire pulses unevenly.
- Hot gas rises (buoyancy), swirls (vorticity confinement keeps small eddies alive), is carried
  along by its own velocity (semi-Lagrangian advection), stays incompressible (pressure
  projection) and cools down as it rises, so it breaks into tongues that curl, split and fade.
- Every other simulation step is recorded as an 8-bit temperature frame (30 frames per second
  of fire time) into ``assets/flame/baked_flame.npz``.

The runtime (``overlay.flame_baked``) plays random stretches of this recording and morphs between
them, then turns temperature into the flat sticker colour bands.
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import numpy as np

from overlay.flame_common import BODY_CY, BODY_RX, BODY_RY

ROOT = Path(__file__).resolve().parent.parent
OUT_PATH = ROOT / "assets" / "flame" / "baked_flame.npz"

X_RANGE = (-2.2, 2.2)      # simulated area in units of R (x)
H_RANGE = (-0.25, 4.1)     # height above the feet (R)
CELLS_PER_R = 28
SIM_DT = 1.0 / 60.0        # seconds of fire time per simulation step
RECORD_EVERY = 2           # -> 30 recorded frames per second

BUOYANCY = 6.0             # upward acceleration per unit temperature (R/s^2)
COOLING = 1.2              # temperature lost per second (grows with height)
VORTICITY = 4.0            # strength of the swirl-preserving force
TURBULENCE = 9.0           # strength of the random sideways force (R/s^2)
JACOBI_ITERS = 40


class FireSim:
    """2D smoke/fire solver on a regular grid (row 0 = bottom, x to the right)."""

    def __init__(self, seed: int) -> None:
        """Allocate fields and the burner mask for the shared body ellipse."""
        self.rng = np.random.default_rng(seed)
        self.h = 1.0 / CELLS_PER_R
        self.nx = int(round((X_RANGE[1] - X_RANGE[0]) * CELLS_PER_R))
        self.ny = int(round((H_RANGE[1] - H_RANGE[0]) * CELLS_PER_R))
        xs = X_RANGE[0] + (np.arange(self.nx) + 0.5) * self.h
        hs = H_RANGE[0] + (np.arange(self.ny) + 0.5) * self.h
        self.X, self.H = np.meshgrid(xs, hs)
        self.u = np.zeros((self.ny, self.nx))
        self.v = np.zeros((self.ny, self.nx))
        self.T = np.zeros((self.ny, self.nx))
        self.t = 0.0
        q = np.sqrt((self.X / BODY_RX) ** 2 + ((self.H - BODY_CY) / BODY_RY) ** 2)
        self.burner = np.clip((1.0 - q) / 0.12, 0.0, 1.0)     # soft-edged body
        self.upper = np.clip((self.H - BODY_CY + 0.2) / 0.6, 0.0, 1.0) * self.burner
        jj, ii = np.meshgrid(np.arange(self.nx, dtype=float), np.arange(self.ny, dtype=float))
        self.ii, self.jj = ii, jj
        # Smooth random "noise" fields for the burner pulses, re-drawn now and then and blended.
        self._noise_a = self._smooth_noise()
        self._noise_b = self._smooth_noise()
        self._noise_t = 0.0
        self._turb_a = self._smooth_noise((16, 22))
        self._turb_b = self._smooth_noise((16, 22))
        self._turb_t = 0.0

    def _smooth_noise(self, shape: tuple[int, int] = (8, 12)) -> np.ndarray:
        """A blobby random field in [-1, 1] (coarse random grid of ``shape``, upsampled)."""
        coarse = self.rng.uniform(-1.0, 1.0, shape)
        ci = np.linspace(0, coarse.shape[0] - 1.001, self.ny)
        cj = np.linspace(0, coarse.shape[1] - 1.001, self.nx)
        i0, j0 = ci.astype(int), cj.astype(int)
        fi, fj = (ci - i0)[:, None], (cj - j0)[None, :]
        fi, fj = fi * fi * (3 - 2 * fi), fj * fj * (3 - 2 * fj)
        a = coarse[i0][:, j0]
        b = coarse[i0][:, j0 + 1]
        c = coarse[i0 + 1][:, j0]
        d = coarse[i0 + 1][:, j0 + 1]
        return (a * (1 - fj) + b * fj) * (1 - fi) + (c * (1 - fj) + d * fj) * fi

    def _sample(self, q: np.ndarray, pi: np.ndarray, pj: np.ndarray) -> np.ndarray:
        """Bilinear sample of field ``q`` at fractional cell positions (row ``pi``, col ``pj``)."""
        pi = np.clip(pi, 0.0, self.ny - 1.001)
        pj = np.clip(pj, 0.0, self.nx - 1.001)
        i0 = pi.astype(int)
        j0 = pj.astype(int)
        fi = pi - i0
        fj = pj - j0
        return ((q[i0, j0] * (1 - fj) + q[i0, j0 + 1] * fj) * (1 - fi)
                + (q[i0 + 1, j0] * (1 - fj) + q[i0 + 1, j0 + 1] * fj) * fi)

    def _project(self) -> None:
        """Make the velocity field divergence-free (Jacobi pressure solve)."""
        u, v, h = self.u, self.v, self.h
        div = np.zeros_like(u)
        div[1:-1, 1:-1] = ((u[1:-1, 2:] - u[1:-1, :-2]) + (v[2:, 1:-1] - v[:-2, 1:-1])) / (2 * h)
        p = np.zeros_like(u)
        for _ in range(JACOBI_ITERS):
            p[1:-1, 1:-1] = (p[1:-1, 2:] + p[1:-1, :-2] + p[2:, 1:-1] + p[:-2, 1:-1]
                             - div[1:-1, 1:-1] * h * h) * 0.25
            p[0, :], p[-1, :], p[:, 0], p[:, -1] = p[1, :], 0.0, p[:, 1], p[:, -2]
        u[1:-1, 1:-1] -= (p[1:-1, 2:] - p[1:-1, :-2]) / (2 * h)
        v[1:-1, 1:-1] -= (p[2:, 1:-1] - p[:-2, 1:-1]) / (2 * h)
        u[:, 0] = u[:, -1] = 0.0
        v[0, :] = 0.0

    def _vorticity_force(self) -> tuple[np.ndarray, np.ndarray]:
        """Force that re-spins existing eddies (keeps the fire lively and curly)."""
        u, v, h = self.u, self.v, self.h
        w = np.zeros_like(u)
        w[1:-1, 1:-1] = ((v[1:-1, 2:] - v[1:-1, :-2]) - (u[2:, 1:-1] - u[:-2, 1:-1])) / (2 * h)
        aw = np.abs(w)
        gx = np.zeros_like(u)
        gy = np.zeros_like(u)
        gx[1:-1, 1:-1] = (aw[1:-1, 2:] - aw[1:-1, :-2]) / (2 * h)
        gy[1:-1, 1:-1] = (aw[2:, 1:-1] - aw[:-2, 1:-1]) / (2 * h)
        mag = np.sqrt(gx * gx + gy * gy) + 1e-6
        nx, ny = gx / mag, gy / mag
        return VORTICITY * h * ny * w, -VORTICITY * h * nx * w

    def step(self, dt: float) -> None:
        """Advance the fire by ``dt`` seconds."""
        self.t += dt
        self._noise_t += dt * 0.9
        if self._noise_t >= 1.0:
            self._noise_t -= 1.0
            self._noise_a, self._noise_b = self._noise_b, self._smooth_noise()
        k = self._noise_t * self._noise_t * (3 - 2 * self._noise_t)
        pulse = self._noise_a * (1 - k) + self._noise_b * k

        # Burner: heat and an uneven upward push inside the body, strongest near its top.
        strength = np.clip(0.8 + 0.6 * pulse, 0.25, 1.4)
        self.T = np.maximum(self.T, self.burner * strength)
        self.v += dt * self.upper * (2.5 + 2.0 * pulse)
        self.u += dt * self.upper * 1.8 * self._noise_b

        # Turbulence: a finer random force field that keeps changing, strongest above the body,
        # which breaks the rising heat into separate tongues.
        self._turb_t += dt * 2.5
        if self._turb_t >= 1.0:
            self._turb_t -= 1.0
            self._turb_a, self._turb_b = self._turb_b, self._smooth_noise((16, 22))
        kt = self._turb_t * self._turb_t * (3 - 2 * self._turb_t)
        turb = self._turb_a * (1 - kt) + self._turb_b * kt
        lift = np.clip((self.H - BODY_CY + 0.3) / 1.0, 0.0, 1.0)

        # Buoyancy, swirl, a little random breeze.
        fx, fy = self._vorticity_force()
        self.u += dt * (fx + TURBULENCE * lift * turb)
        self.v += dt * (fy + BUOYANCY * self.T)
        self._project()

        # Carry everything along the flow (trace back where each cell's content came from).
        back_i = self.ii - dt * self.v / self.h
        back_j = self.jj - dt * self.u / self.h
        self.u = self._sample(self.u, back_i, back_j)
        self.v = self._sample(self.v, back_i, back_j)
        self.T = self._sample(self.T, back_i, back_j)

        # Cooling: hardly any inside the body, more and more above it.
        above = np.clip((self.H - BODY_CY) / 1.5, 0.0, 1.0)
        self.T = np.maximum(self.T - dt * COOLING * (0.2 + 2.2 * above * above), 0.0)
        self.u *= 1.0 - 0.6 * dt
        self.v *= 1.0 - 0.6 * dt
        self.T[-2:, :] = 0.0


def bake(seconds: float, seed: int) -> np.ndarray:
    """Simulate ``seconds`` of recorded fire (after a warm-up); returns uint8 frames (row 0 = top)."""
    sim = FireSim(seed)
    for _ in range(int(2.5 / SIM_DT)):
        sim.step(SIM_DT)
    frames = []
    total = int(seconds / SIM_DT)
    start = time.perf_counter()
    for n in range(total):
        sim.step(SIM_DT)
        if n % RECORD_EVERY == 0:
            frames.append(np.clip(sim.T[::-1] * 255.0, 0, 255).astype(np.uint8))
        if n % 300 == 0:
            print(f"  {n * SIM_DT:5.1f}s / {seconds:.0f}s  ({time.perf_counter() - start:.0f}s)",
                  flush=True)
    return np.stack(frames)


def main() -> int:
    """Parse arguments, bake, save, optionally write a preview strip."""
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--seconds", type=float, default=24.0)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--preview", help="also save a strip of raw temperature frames as PNG")
    args = ap.parse_args()
    frames = bake(args.seconds, args.seed)
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(OUT_PATH, frames=frames, fps=np.float32(SIM_DT * RECORD_EVERY) ** -1,
                        x_range=np.float32(X_RANGE), h_range=np.float32(H_RANGE))
    print(f"saved {frames.shape} -> {OUT_PATH} ({OUT_PATH.stat().st_size / 1e6:.1f} MB)")
    if args.preview:
        from PySide6.QtGui import QImage
        pick = frames[:: max(1, len(frames) // 12)][:12]
        strip = np.ascontiguousarray(np.concatenate(list(pick), axis=1))
        img = QImage(strip.data, strip.shape[1], strip.shape[0], strip.shape[1],
                     QImage.Format.Format_Grayscale8)
        img.save(args.preview)
    return 0


if __name__ == "__main__":
    sys.exit(main())
