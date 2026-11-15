"""Outfits the flame character can wear for days, across every mood (task T6 / H5 in the docs).

An outfit is a prop like the ones in ``overlay.props`` - a small model + painter that never moves
the window - but it is not tied to one mood: it must fit the body of *any* expression.

- ``ScarfProp`` - the Christmas outfit's chunky knitted scarf (decision 2026-11-15, round 39):
  red with white stripes, tied round the lower body. The lower body is the calm, predictable
  part of the fire, and ``flame_common.body_half_width`` gives its exact width at any height in
  every frame, so the band hugs the silhouette whatever the face does (puffed up, flat, boxy)
  while the flame tongues stay free. A soft knot sits on the pet's right (screen left) and two
  short tails stick out sideways from it; they swing with the pet's own movement (walking
  sweeps them back and every hop makes them bounce) and flutter a little while it moves.

All lengths are in units of R (the character's base radius); painting happens in the
character's body coordinates (pixels, origin at the feet, y *up is negative*), inside the body
transform, so the scarf squashes and leans with the body.
"""
from __future__ import annotations

import math
from collections.abc import Callable

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QImage, QPainter, QPainterPath, QPen, QPolygonF

from overlay.flame_common import FlameDrive, Spring, body_half_width, clamp, noise1, smoothstep
from overlay.props import INK, approach_linear

SCARF_RED = QColor(212, 34, 48)           # colours of the approved study (round 39)
SCARF_STRIPE = QColor(255, 246, 232)
SCARF_SHADE = QColor(120, 8, 30, 80)      # translucent: darkens red and stripes alike

SCARF_H = 0.5          # band centre height above the feet on a normal body (R)
SCARF_T = 0.14         # half thickness of the band (R)
SCARF_RIDE_RAISE = 0.14   # on the log the body's bottom is cut flat: the scarf sits higher (R)
SCARF_PINCH = 0.06     # how much the soft body is squeezed under the scarf (fraction of width)
SCARF_FACE_LIFT = 0.2  # the face moves up this much while the scarf is worn (R)
SCARF_MOUTH_ROOM = 0.03   # gap kept between a big mouth and the scarf's top edge (R)
SCARF_MAX_TALLER = 0.45   # most the body may grow taller to make room for the mouth (body_h)
BAND_MARGIN = 0.05     # the band stands this far out of the body outline (knitted thickness, R)
BAND_SAG = 0.06        # the front of the wrap curves down below its ends (R)
BAND_CAP = 0.1         # how far the rounded ends bulge past the body's sides (R)
BAND_STEPS = 24        # samples along each edge of the band
STRIPE_STEP = 0.62     # angle between stripes round the body (radians)
STRIPE_WIDTH = 0.4     # stripe width as a fraction of ``STRIPE_STEP``
SIDE = -1              # the knot is on the pet's right = screen left
KNOT_AT = 0.8          # knot position across the band (fraction of the half width)
FADE_SECONDS = 0.35    # putting the scarf on / taking it off
SPRITE_SUPERSAMPLE = 2.0  # band / knot images are pre-drawn at this many px per screen px
BAND_CACHE_SIZE = 24   # band images kept (the band's size only wanders a little)

Point = tuple[float, float]   # (x, y) in R, y up


class _Tail:
    """One short tail hanging out of the knot: a strip whose angle is a spring.

    The angle is measured from straight down (0) toward the knot's side; ``rest`` keeps the tail
    pointing out sideways (a long tail hanging straight down reads as a leg).
    """

    def __init__(self, rest: float, length: float, width: float, stiffness: float,
                 damping: float, curl: float) -> None:
        """``rest`` = resting angle (rad), ``length`` / ``width`` in R, spring settings, and
        ``curl`` = extra angle the tip bends further out than the root (rad)."""
        self.rest = rest
        self.length = length
        self.width = width
        self.curl = curl
        self.swing = Spring(0.0, stiffness=stiffness, damping=damping)

    def outline(self, root: Point, flutter: float,
                steps: int = 10) -> tuple[list[Point], list[Point], float]:
        """Left and right edge points (R, y up) from ``root`` to the tip, and the tip's
        direction angle. The tip swings more than the root, like cloth."""
        x, y = root
        left: list[Point] = []
        right: list[Point] = []
        a = 0.0
        seg = self.length / steps
        for j in range(steps + 1):
            t = j / steps
            a = SIDE * (self.rest + self.curl * t) + self.swing.value * (0.35 + 0.65 * t)
            a += flutter * t * t
            a = clamp(a, -2.0, 2.0)               # never curls up over the band
            hw = 0.5 * self.width * (1.0 - 0.12 * t)
            nx, ny = math.cos(a), math.sin(a)     # normal of the direction (sin a, -cos a)
            left.append((x - nx * hw, y - ny * hw))
            right.append((x + nx * hw, y + ny * hw))
            x += math.sin(a) * seg
            y -= math.cos(a) * seg
        return left, right, a


class ScarfProp:
    """Red-and-white knitted scarf tied round the lower body (see the module docstring).

    ``show()`` / ``hide()`` fade it in / out; ``amount`` (0..1) also drives the face lift and
    the body squeeze, so everything eases together. ``update()`` takes the pet's velocity in R
    per second (y down positive) to swing the tails; ``paint()`` takes the frame's
    ``FlameDrive`` so the band follows the body shape the flame was drawn with.
    """

    def __init__(self, R: float, seed: int) -> None:
        """``R`` = character radius in pixels; ``seed`` varies the idle flutter between pets."""
        self.R = R
        self._seed = seed
        self._t = 0.0
        self._amount = 0.0
        self._target = 0.0
        self._prev_vy: float | None = None
        self._speed = 0.0
        self.front = _Tail(rest=1.0, length=0.42, width=0.2, stiffness=55.0, damping=4.8,
                           curl=-0.25)
        self.back = _Tail(rest=1.6, length=0.36, width=0.18, stiffness=42.0, damping=4.2,
                          curl=-0.35)
        self._pen = QPen(INK, 0.05 * R, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap,
                         Qt.PenJoinStyle.RoundJoin)
        self._fringe_pen = QPen(INK, 0.035 * R, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
        self._band_cache: dict[tuple[float, float, float], tuple[QImage, QRectF]] = {}
        self._knot: tuple[QImage, QRectF] | None = None

    # ------------------------------------------------------------------ state

    def show(self) -> None:
        """Start putting the scarf on."""
        self._target = 1.0

    def hide(self) -> None:
        """Start taking the scarf off."""
        self._target = 0.0

    @property
    def worn(self) -> bool:
        """True while the scarf is on or going on."""
        return self._target > 0.5

    @property
    def visible(self) -> bool:
        """True while any of the scarf shows."""
        return self._amount > 0.0

    @property
    def amount(self) -> float:
        """0 = not worn, 1 = fully on (eased, for the face lift and the body squeeze)."""
        return smoothstep(0.0, 1.0, self._amount)

    def band_height(self, body_h: float, ride: float) -> float:
        """Height (R above the feet) of the band's centre for a body ``body_h`` tall; ``ride``
        (0..1) = sitting on the log, whose cut-flat bottom pushes the scarf up."""
        return (SCARF_H + SCARF_RIDE_RAISE * ride) * (0.4 + 0.6 * body_h)

    def update(self, dt: float, vx: float, vy: float) -> None:
        """Fade, and swing the tails: ``vx`` / ``vy`` = the pet's velocity (R/s, y down)."""
        self._t += dt
        self._amount = approach_linear(self._amount, self._target, dt / FADE_SECONDS)
        if not self.visible:
            self._prev_vy = None
            return
        self._speed += (min(abs(vx) / 3.0, 1.0) - self._speed) * (1.0 - math.exp(-4.0 * dt))
        # Moving sideways sweeps both tails back (they trail behind the movement).
        trail = clamp(-vx * 0.3, -1.0, 1.0)
        if self._prev_vy is not None and dt > 0.0:
            # A change of vertical speed (hop, landing) flicks the tails: going up they droop
            # (toward straight down), falling they lift.
            dv = clamp(vy - self._prev_vy, -6.0, 6.0)
            self.front.swing.velocity += SIDE * dv * 0.55
            self.back.swing.velocity += SIDE * dv * 0.6
        self._prev_vy = vy
        sway = 0.07 * noise1(self._t * 0.6, self._seed + 17)
        self.front.swing.step(trail + sway, dt)
        self.back.swing.step(trail * 1.15 + sway, dt)

    # ------------------------------------------------------------------ painting

    def paint(self, painter: QPainter, drive: FlameDrive, band_h: float) -> None:
        """Draw the scarf on the body described by ``drive``, its band centred ``band_h`` R
        above the feet (see ``band_height``).

        The band and the knot only change with the body's size, so they are pre-drawn into
        small cached images (sizes rounded to 1/100 R, far below a pixel); only the swinging
        tails are drawn fresh every frame."""
        if not self.visible:
            return
        R = self.R
        hs = round(band_h, 2)
        wt = round(body_half_width(hs + SCARF_T - 0.03, drive) + BAND_MARGIN, 2)
        wb = round(body_half_width(hs - SCARF_T + 0.03, drive) + BAND_MARGIN, 2)
        kx, ky = SIDE * KNOT_AT * 0.5 * (wt + wb), hs - 0.02
        flutter = 0.12 * self._speed * noise1(self._t * 5.0, self._seed + 23)

        painter.save()
        painter.setOpacity(painter.opacity() * self.amount)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
        band_img, band_rect = self._band_sprite(wt, wb, hs)
        painter.drawImage(band_rect, band_img)
        # Both tails come out from under the knot in a V: the back one first, so the front one
        # overlaps it.
        self._paint_tail(painter, self.back, (kx, ky - 0.03), -flutter)
        self._paint_tail(painter, self.front, (kx + SIDE * 0.01, ky - 0.09), flutter)
        if self._knot is None:
            self._knot = self._sprite(self._paint_knot, QRectF(-0.3 * R, -0.3 * R,
                                                               0.6 * R, 0.6 * R))
        knot_img, knot_rect = self._knot
        painter.drawImage(knot_rect.translated(kx * R, -ky * R), knot_img)
        painter.restore()

    def _sprite(self, draw: Callable[[QPainter], None],
                bounds: QRectF) -> tuple[QImage, QRectF]:
        """Pre-draw ``draw(painter)`` (body px) into an image covering ``bounds``, at
        ``SPRITE_SUPERSAMPLE`` pixels per pixel so it stays crisp when the body stretches."""
        k = SPRITE_SUPERSAMPLE
        img = QImage(max(1, math.ceil(bounds.width() * k)), max(1, math.ceil(bounds.height() * k)),
                     QImage.Format.Format_ARGB32_Premultiplied)
        img.fill(Qt.GlobalColor.transparent)
        p = QPainter(img)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        p.scale(k, k)
        p.translate(-bounds.left(), -bounds.top())
        draw(p)
        p.end()
        return img, QRectF(bounds.left(), bounds.top(), img.width() / k, img.height() / k)

    def _band_sprite(self, wt: float, wb: float, hs: float) -> tuple[QImage, QRectF]:
        """Cached image of the band for half widths ``wt`` / ``wb`` (top / bottom edge) and
        centre height ``hs`` (all R). A short cache: the size only wanders a little (breathing,
        an expression changing the body)."""
        key = (wt, wb, hs)
        cached = self._band_cache.get(key)
        if cached is not None:
            return cached
        R = self.R
        y_top, y_bot = hs + SCARF_T, hs - SCARF_T

        def edge(u: float, top: bool) -> QPointF:
            """Point on the top / bottom edge at ``u`` (-1 left end .. 1 right end), in px."""
            w = wt if top else wb
            lump = 0.022 * math.sin(math.asin(clamp(u, -1.0, 1.0)) * 5.0 + (0.6 if top else 2.1))
            y = (y_top + lump if top else y_bot - lump) - BAND_SAG * (1.0 - u * u)
            return QPointF(u * w * R, -y * R)

        us = [-1.0 + 2.0 * i / BAND_STEPS for i in range(BAND_STEPS + 1)]
        top = [edge(u, True) for u in us]
        bot = [edge(u, False) for u in us]
        cap = BAND_CAP * R
        band = QPainterPath(top[0])
        for pt in top[1:]:
            band.lineTo(pt)
        band.cubicTo(QPointF(top[-1].x() + cap, top[-1].y()),
                     QPointF(bot[-1].x() + cap, bot[-1].y()), bot[-1])
        for pt in reversed(bot[:-1]):
            band.lineTo(pt)
        band.cubicTo(QPointF(bot[0].x() - cap, bot[0].y()),
                     QPointF(top[0].x() - cap, top[0].y()), top[0])
        band.closeSubpath()

        def draw(p: QPainter) -> None:
            """Fill, stripes (wrapping round a cylinder, so they crowd toward the ends), a
            shaded lower edge, then the outline on top so it stays crisp over the stripes."""
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(SCARF_RED)
            p.drawPath(band)
            p.setBrush(SCARF_STRIPE)
            for k in range(-3, 4):
                th0 = (k - 0.5 * STRIPE_WIDTH + 0.5) * STRIPE_STEP
                th1 = (k + 0.5 * STRIPE_WIDTH + 0.5) * STRIPE_STEP
                if abs(th0) > 1.5 or abs(th1) > 1.5:
                    continue
                u0, u1 = math.sin(th0), math.sin(th1)
                p.drawPolygon(QPolygonF([edge(u0, True), edge(u1, True),
                                         edge(u1, False), edge(u0, False)]))
            p.save()
            p.setClipPath(band)          # the shade runs round the rounded ends too
            p.setBrush(SCARF_SHADE)
            low = [QPointF(bot[0].x() - cap, bot[0].y()), *bot,
                   QPointF(bot[-1].x() + cap, bot[-1].y())]
            p.drawPolygon(QPolygonF([QPointF(q.x(), q.y() + 0.1 * R) for q in low]
                                    + [QPointF(q.x(), q.y() - 0.07 * R) for q in reversed(low)]))
            p.restore()
            p.setPen(self._pen)
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawPath(band)

        pad = self._pen.widthF()
        sprite = self._sprite(draw, band.boundingRect().adjusted(-pad, -pad, pad, pad))
        if len(self._band_cache) >= BAND_CACHE_SIZE:
            self._band_cache.pop(next(iter(self._band_cache)))   # drop the oldest
        self._band_cache[key] = sprite
        return sprite

    def _paint_knot(self, painter: QPainter) -> None:
        """A soft bunched knot (not a box) centred on the origin: rounder and wider on top,
        gathered narrow at the bottom where the tails come out, tilted a little, with one
        stripe running round it like the band's stripes."""
        R = self.R
        tilt = -SIDE * 0.2
        cos_t, sin_t = math.cos(tilt), math.sin(tilt)

        def pt(x: float, y: float) -> QPointF:
            """Knot-local point (R, y up) -> px, tilted about the knot centre."""
            return QPointF((x * cos_t - y * sin_t) * R, -(x * sin_t + y * cos_t) * R)

        path = QPainterPath(pt(-0.07, -0.11))
        path.cubicTo(pt(-0.14, -0.07), pt(-0.19, 0.01), pt(-0.155, 0.08))
        path.cubicTo(pt(-0.12, 0.16), pt(0.12, 0.16), pt(0.155, 0.08))
        path.cubicTo(pt(0.19, 0.01), pt(0.14, -0.07), pt(0.07, -0.11))
        path.cubicTo(pt(0.03, -0.14), pt(-0.03, -0.14), pt(-0.07, -0.11))
        path.closeSubpath()
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(SCARF_RED)
        painter.drawPath(path)
        painter.save()
        painter.setClipPath(path)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.setPen(QPen(SCARF_STRIPE, 0.07 * R, Qt.PenStyle.SolidLine, Qt.PenCapStyle.FlatCap))
        stripe = QPainterPath(pt(0.0, 0.2))
        stripe.quadTo(pt(0.05, 0.0), pt(0.0, -0.2))
        painter.drawPath(stripe)
        painter.restore()
        painter.setPen(self._pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawPath(path)

    def _paint_tail(self, painter: QPainter, tail: _Tail, root: Point, flutter: float) -> None:
        """One tail: red strip, two stripes near the end, a fringe of short strands."""
        R = self.R
        left_r, right_r, tip_angle = tail.outline(root, flutter)
        left = [QPointF(x * R, -y * R) for x, y in left_r]
        right = [QPointF(x * R, -y * R) for x, y in right_r]
        poly = QPolygonF(left + right[::-1])
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(SCARF_RED)
        painter.drawPolygon(poly)
        painter.setBrush(SCARF_STRIPE)
        for k in (4, 7):
            painter.drawPolygon(QPolygonF([left[k], left[k + 1], right[k + 1], right[k]]))
        painter.setPen(self._pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawPolygon(poly)
        painter.setPen(self._fringe_pen)
        dx, dy = math.sin(tip_angle) * 0.08 * R, math.cos(tip_angle) * 0.08 * R
        for f in range(4):
            u = (f + 0.5) / 4
            px = left[-1].x() + (right[-1].x() - left[-1].x()) * u
            py = left[-1].y() + (right[-1].y() - left[-1].y()) * u
            painter.drawLine(QPointF(px, py), QPointF(px + dx, py + dy))
