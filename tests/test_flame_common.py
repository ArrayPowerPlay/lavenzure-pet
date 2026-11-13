"""Tests for the shared flame helpers: finding the flame's top edge for spawning sparks."""
import random

import numpy as np

from overlay.flame_common import TOP_POINT_STEP, ImageFlame


def _flame_alpha(width: int, height: int) -> np.ndarray:
    """A synthetic alpha mask: a solid dome whose top is highest in the middle."""
    alpha = np.zeros((height, width), dtype=np.uint8)
    for col in range(width):
        top = int(10 + 30 * abs(col - width / 2) / (width / 2))
        alpha[top:, col] = 255
    return alpha


def test_top_points_from_subsampled_columns_match(qapp):
    """Reading only every third column gives the same tip and top points as the full bitmap."""
    flame = ImageFlame(30.0, random.Random(1))
    alpha = _flame_alpha(flame.img_w, flame.img_h)
    flame._update_top_points(alpha)
    full_tip, full_points = flame.tip, flame.top_points
    flame._update_top_points(alpha[:, ::TOP_POINT_STEP], TOP_POINT_STEP)
    assert flame.tip == full_tip
    assert flame.top_points == full_points
    assert flame.top_points        # the dome reaches above the cut line


def test_empty_bitmap_has_no_top_points(qapp):
    """A fully transparent bitmap yields no spark points (and does not crash)."""
    flame = ImageFlame(30.0, random.Random(1))
    flame._update_top_points(np.zeros((flame.img_h, flame.img_w), dtype=np.uint8), 3)
    assert flame.top_points == []
