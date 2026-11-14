"""Props the flame character can use: the flying log, the frying pan, sunglasses, the alarm clock
and the sleepy "z"s.

Every prop is a small model + painter, like the character itself: ``update(dt, ...)`` once per
frame, then ``paint(painter, ...)``. Props never move the window; the character decides when they
show and where they are drawn. All lengths are in units of R (the character's base radius) and
painting happens in the character's body coordinates (pixels, origin at the feet, y down).

- ``LogProp`` - the log Lavenzure rides through the air (reference figures 4 and 5). It pops into
  existence with a springy overshoot when summoned, wobbles gently while flying, and crumbles
  into embers when dismissed (the character spawns the embers from ``ember_points()``). Two small
  round flame "paws" drape over its top edge, out toward the sides (clear of the mouth).
- ``PanProp`` - the frying pan (bacon and two fried eggs) resting on the flattened flame's head
  for the ``chill`` mood (reference figure 7): drawn in front of the fire, its bottom just
  above the eyes, tipped a little with the handle hanging down to one side. It drops in from
  above, settles, sizzles (steam wisps and popping grease) and lifts off again.
- ``SunglassesProp`` - black sunglasses for the ``cool`` mood (no reference figure; designed
  freely): they drop from above onto the eyes, a glint sweeps across the lenses once they land,
  and they slide back up and fade when the mood ends.
- ``AlarmClockProp`` - the ⏰ alarm clock for a due reminder (``remind`` mood, round 31): pops
  in beside the pet, rings until the user clicks the pet, then is put away.
- ``Snores`` - "z" letters that float up from a sleeping pet, sway, grow and fade.
"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QLinearGradient, QPainter, QPainterPath, QPen

from overlay.flame_common import Spring, clamp, lerp, noise1, smoothstep

INK = QColor(108, 14, 22)

# ---------------------------------------------------------------------- log

BARK = QColor(204, 78, 62)
BARK_LIGHT = QColor(232, 118, 92)
BARK_DARK = QColor(160, 48, 46)
BARK_LINE = QColor(140, 36, 40)
END_GRAIN = QColor(244, 152, 112)
RING = QColor(196, 86, 66)

LOG_HALF_LEN = 1.38     # half length of the log (R)
LOG_RADIUS = 0.29       # half thickness (R)
LOG_CY = -0.12          # centre height relative to the feet (R, negative = up)
END_RX = 0.16           # width of the visible cut end (R)


class LogProp:
    """The flying log. ``show()`` summons it (pop-in), ``hide()`` crumbles it into embers."""

    def __init__(self, R: float, rng: random.Random, seed: int) -> None:
        """``R`` = character radius in pixels; ``seed`` decorrelates its wobble."""
        self.R = R
        self._rng = rng
        self._seed = seed
        self._t = 0.0
        self._size = Spring(0.0, stiffness=230.0, damping=13.0)   # pop-in with overshoot
        self._target = 0.0
        self.crumble = 0.0          # 0 = solid, 1 = fully turned to embers
        self._crumbling = False
        self.visible = False

    @property
    def amount(self) -> float:
        """How present the log is (0 = gone, 1 = fully there); overshoots a little on pop-in."""
        if not self.visible:
            return 0.0
        return max(0.0, self._size.value) * (1.0 - self.crumble)

    def show(self) -> None:
        """Summon the log (restarts the pop-in if it was crumbling)."""
        if self.visible and not self._crumbling:
            return
        if not self.visible or self._crumbling:
            self._size.value = 0.0
            self._size.velocity = 0.0
        self.visible = True
        self._crumbling = False
        self.crumble = 0.0
        self._target = 1.0

    def hide(self) -> None:
        """Start crumbling into embers (no-op if already gone)."""
        if self.visible and not self._crumbling:
            self._crumbling = True

    @property
    def crumbling(self) -> bool:
        """True while the log is falling apart into embers."""
        return self.visible and self._crumbling

    def update(self, dt: float) -> None:
        """Advance the pop-in spring, the crumbling and the idle wobble."""
        if not self.visible:
            return
        self._t += dt
        self._size.step(self._target, dt)
        if self._crumbling:
            self.crumble = min(1.0, self.crumble + dt / 0.42)
            if self.crumble >= 1.0:
                self.visible = False
                self._crumbling = False
                self.crumble = 0.0

    def tilt(self) -> float:
        """Gentle rocking of the log while flying (radians)."""
        return 0.035 * noise1(self._t * 0.7, self._seed + 61)

    def ember_points(self, count: int) -> list[tuple[float, float]]:
        """Random points on the log (body pixels) for the crumbling embers."""
        R = self.R
        pts = []
        for _ in range(count):
            x = self._rng.uniform(-LOG_HALF_LEN, LOG_HALF_LEN) * R
            y = (LOG_CY + self._rng.uniform(-LOG_RADIUS, LOG_RADIUS)) * R
            pts.append((x, y))
        return pts

    @property
    def knead_phase(self) -> float:
        """Phase of the paws' slow kneading (radians); the shader's paws use it too."""
        return self._t * 2.6

    def paint(self, painter: QPainter, paw_colors: tuple[QColor, QColor] | None) -> None:
        """Draw the log (bark, cut end with rings, outline) and, if ``paw_colors`` is given, the
        two flame paws on top.

        The painter is in body pixels with the origin at the feet. ``paw_colors`` = (yellow fill,
        orange underside) of the flame, so the paws match the body. The shader renderer draws the
        paws as part of the fire instead (one seamless shape) and passes ``None``."""
        amount = self.amount
        if amount <= 0.01:
            return
        R = self.R
        crumble = self.crumble
        painter.save()
        painter.translate(0.0, LOG_CY * R)
        painter.rotate(math.degrees(self.tilt()))
        # Pop-in: the log grows out from the middle, a little wider than tall.
        painter.scale(lerp(0.2, 1.0, min(amount, 1.2)), lerp(0.4, 1.0, min(amount, 1.2)))
        painter.setOpacity(painter.opacity() * (1.0 - smoothstep(0.35, 1.0, crumble)))
        L, r, er = LOG_HALF_LEN * R, LOG_RADIUS * R, END_RX * R
        ink = QPen(INK, 0.06 * R, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap,
                   Qt.PenJoinStyle.RoundJoin)

        body = QPainterPath()
        body.moveTo(-L + er, -r)
        body.lineTo(L, -r)
        body.lineTo(L, r)
        body.lineTo(-L + er, r)
        body.arcTo(QRectF(-L, -r, 2 * er, 2 * r), 270.0, -180.0)
        body.closeSubpath()
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(BARK)
        painter.drawPath(body)
        painter.save()
        painter.setClipPath(body)
        painter.setBrush(BARK_DARK)
        painter.drawRect(QRectF(-L, r * 0.35, 2 * L, r))           # shaded underside
        painter.setBrush(BARK_LIGHT)
        painter.drawRoundedRect(QRectF(-L * 0.78, -r * 0.72, L * 1.4, r * 0.32), r * 0.16,
                                r * 0.16)                         # light catching the top
        # A few bark grooves (as fractions of the log's radius, so they stay on the bark).
        painter.setPen(QPen(BARK_LINE, 0.045 * R, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        for x0, x1, y in ((-0.95, -0.35, 0.55), (0.05, 0.75, 0.1), (-0.55, 0.1, -0.15)):
            groove = QPainterPath(QPointF(x0 * R, y * r))
            groove.quadTo(QPointF((x0 + x1) / 2 * R, y * r - 0.05 * R), QPointF(x1 * R, y * r))
            painter.drawPath(groove)
        painter.restore()
        painter.setPen(ink)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawPath(body)

        # The cut end with growth rings.
        painter.setBrush(END_GRAIN)
        painter.drawEllipse(QPointF(L, 0.0), er, r)
        painter.setPen(QPen(RING, 0.04 * R, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        spiral = QPainterPath()
        for i in range(40):
            a = i / 39 * math.tau * 1.6
            k = 0.12 + 0.62 * i / 39
            p = QPointF(L + math.cos(a) * er * k, math.sin(a) * r * k)
            if i == 0:
                spiral.moveTo(p)
            else:
                spiral.lineTo(p)
        painter.drawPath(spiral)
        painter.restore()

        if crumble < 0.3 and paw_colors is not None:
            self._paint_paws(painter, amount, paw_colors)

    def _paint_paws(self, painter: QPainter, amount: float,
                    paw_colors: tuple[QColor, QColor]) -> None:
        """Two round flame paws draped over the front of the log (reference fig. 4): each is a
        single soft blob, like a mitten - no fingers or toe lines. It grows out of the body
        (no outline across its top, so it reads as part of the flame) and hangs over the log
        with a round bottom. The paws knead slowly, each squashing a little in turn."""
        R = self.R
        fill, under = paw_colors
        grow = smoothstep(0.55, 1.0, amount)
        if grow <= 0.01:
            return
        top = (LOG_CY - LOG_RADIUS) * R
        for side in (-1, 1):
            phase = self.knead_phase + (0.0 if side < 0 else 2.1)
            press = 0.5 + 0.5 * math.sin(phase)             # 1 = pressed into the log
            half_w = (0.17 + 0.015 * press) * R * grow       # pressing makes it a bit wider ...
            depth = (0.27 - 0.025 * press) * R * grow        # ... and a bit shorter
            cx = side * 0.64 * R                             # out by the sides, clear of the mouth
            y0 = top - 0.1 * R                               # starts inside the body
            y1 = top + depth                                 # round bottom over the log front
            # Outline of the visible part: down one side, around the round bottom, up the other.
            rim = QPainterPath(QPointF(cx - half_w, y0))
            rim.cubicTo(QPointF(cx - half_w * 1.08, y0 + (y1 - y0) * 0.45),
                        QPointF(cx - half_w * 1.02, y1),
                        QPointF(cx, y1))
            rim.cubicTo(QPointF(cx + half_w * 1.02, y1),
                        QPointF(cx + half_w * 1.08, y0 + (y1 - y0) * 0.45),
                        QPointF(cx + half_w, y0))
            blob = QPainterPath(rim)
            blob.closeSubpath()
            painter.save()
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(fill)
            painter.drawPath(blob)
            # A warm shade along the bottom and a small shine dot give it a soft, round volume.
            painter.setClipPath(blob)
            painter.setBrush(under)
            painter.drawEllipse(QPointF(cx + side * 0.03 * R, y1 + 0.02 * R),
                                half_w * 1.15, depth * 0.38)
            painter.setClipping(False)
            painter.setBrush(QColor(255, 255, 255, 150))
            painter.drawEllipse(QPointF(cx - side * half_w * 0.38, y0 + (y1 - y0) * 0.5),
                                0.035 * R * grow, 0.05 * R * grow)
            # Ink only where the paw hangs over the log; above it the paw melts into the body.
            painter.setClipRect(QRectF(cx - R, top - 0.03 * R, 2 * R, 2 * R))
            painter.setPen(QPen(INK, 0.055 * R, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap,
                                Qt.PenJoinStyle.RoundJoin))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawPath(rim)
            painter.restore()


# ---------------------------------------------------------------------- frying pan

PAN_DARK = QColor(62, 62, 72)
PAN_MID = QColor(92, 92, 104)
PAN_INNER = QColor(124, 124, 136)
PAN_SHINE = QColor(170, 170, 184)
EGG_WHITE = QColor(255, 252, 244)
YOLK = QColor(255, 196, 40)
YOLK_SHINE = QColor(255, 236, 160)
BACON = QColor(226, 92, 86)
BACON_FAT = QColor(250, 196, 176)
STEAM = QColor(255, 255, 255)
PAN_RX = 1.28           # rim half-width (R)
PAN_RY = 0.52           # rim half-height as seen from a little above (R)
PAN_DEPTH = 0.21        # height of the side wall (R)
PAN_BOTTOM = PAN_DEPTH + 0.9 * PAN_RY   # from the rim centre down to the bottom of the wall


@dataclass
class _Wisp:
    """One puff of steam or a pop of grease above the pan (body pixels)."""

    x: float
    y: float
    vx: float
    vy: float
    life: float
    max_life: float
    size: float
    grease: bool


class PanProp:
    """Frying pan with bacon and eggs, balanced on top of the flame (``chill`` mood)."""

    def __init__(self, R: float, rng: random.Random, seed: int) -> None:
        """``R`` = character radius in pixels."""
        self.R = R
        self._rng = rng
        self._seed = seed
        self._t = 0.0
        self.visible = False
        # 0 = far above, 1 = resting. Nearly critically damped: it settles with one soft dip
        # instead of bouncing down over the eyes.
        self._drop = Spring(0.0, stiffness=150.0, damping=20.0)
        self._target = 0.0
        self._alpha = 0.0
        self._wisps: list[_Wisp] = []
        self._wisp_debt = 0.0

    def show(self) -> None:
        """Drop the pan onto the flame's head."""
        if not self.visible:
            self._drop.value = 0.0
            self._drop.velocity = 0.0
            self._alpha = 0.0
        self.visible = True
        self._target = 1.0

    def hide(self) -> None:
        """Lift the pan away (it fades as it rises)."""
        self._target = 0.0

    def update(self, dt: float) -> None:
        """Drop / lift spring, sizzling steam and grease."""
        if not self.visible:
            return
        self._t += dt
        self._drop.step(self._target, dt)
        self._alpha = approach_linear(self._alpha, 1.0 if self._target > 0.5 else 0.0, dt / 0.25)
        if self._target < 0.5 and self._alpha <= 0.01:
            self.visible = False
            self._wisps.clear()
            return
        R = self.R
        rng = self._rng
        self._wisp_debt += dt * 7.0 * self._alpha
        while self._wisp_debt >= 1.0:
            self._wisp_debt -= 1.0
            grease = rng.random() < 0.4
            life = rng.uniform(0.25, 0.45) if grease else rng.uniform(0.9, 1.6)
            self._wisps.append(_Wisp(
                x=rng.uniform(-0.75, 0.75) * R, y=rng.uniform(-0.12, 0.08) * R,
                vx=rng.uniform(-0.5, 0.5) * R * (2.0 if grease else 0.3),
                vy=-rng.uniform(1.6, 2.6) * R if grease else -rng.uniform(0.5, 0.9) * R,
                life=life, max_life=life, size=rng.uniform(0.04, 0.07) * R if grease
                else rng.uniform(0.1, 0.17) * R, grease=grease))
        alive = []
        for w in self._wisps:
            w.life -= dt
            if w.life <= 0.0:
                continue
            w.x += w.vx * dt
            w.y += w.vy * dt
            if w.grease:
                w.vy += 9.0 * R * dt     # grease drops fall back down
            else:
                w.vx += math.sin(self._t * 3.0 + w.size) * R * 0.4 * dt
            alive.append(w)
        self._wisps = alive

    def landing_impact(self) -> bool:
        """True on the frame the pan first slams down (the character squashes the body)."""
        return self._drop.value > 0.96 and self._drop.velocity > 1.0

    def _place(self, painter: QPainter, seat_y: float) -> None:
        """Move / rotate ``painter`` to the pan's centre: its bottom rests at ``seat_y``; it is
        tipped (right side up, handle down to the left, as in fig. 7), rocks slightly in the
        heat and drops in from above."""
        R = self.R
        y_off = (1.0 - self._drop.value) * -2.2 * R
        sizzle = 0.01 * R * math.sin(self._t * 31.0) * self._alpha
        painter.setOpacity(painter.opacity() * self._alpha)
        painter.translate(0.1 * R + sizzle, seat_y - PAN_BOTTOM * R + y_off)
        painter.rotate(-9.0 + 1.5 * noise1(self._t * 0.8, self._seed + 99))

    def paint(self, painter: QPainter, seat_y: float) -> None:
        """Draw the pan (handle, pan, food) resting on the head with its bottom at ``seat_y``
        (body pixels), in front of the flame, then the steam and grease above it."""
        if not self.visible or self._alpha <= 0.01:
            return
        painter.save()
        self._place(painter, seat_y)
        self._paint_pan(painter)
        self._paint_wisps(painter)
        painter.restore()

    def _paint_pan(self, painter: QPainter) -> None:
        """The pan itself in its own coordinates (centre of the rim at the origin)."""
        R = self.R
        ink = QPen(INK, 0.06 * R, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap,
                   Qt.PenJoinStyle.RoundJoin)
        # About as wide as the flattened flame (reference fig. 7): the fire shows at the sides.
        rx, ry, depth = PAN_RX * R, PAN_RY * R, PAN_DEPTH * R

        # Handle, sticking out to the left and slightly down.
        handle = QPainterPath()
        handle.moveTo(-rx * 0.86, -0.06 * R)
        handle.lineTo(-rx - 0.88 * R, 0.24 * R)
        handle.quadTo(-rx - 1.03 * R, 0.35 * R, -rx - 0.89 * R, 0.42 * R)
        handle.lineTo(-rx * 0.8, 0.16 * R)
        handle.closeSubpath()
        painter.setPen(ink)
        painter.setBrush(PAN_DARK)
        painter.drawPath(handle)
        painter.setPen(QPen(PAN_SHINE, 0.035 * R, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        painter.drawLine(QPointF(-rx - 0.1 * R, 0.08 * R), QPointF(-rx - 0.7 * R, 0.24 * R))

        # Pan body: the side wall (seen a little from above) and the rim on top of it.
        wall = QPainterPath()
        wall.moveTo(-rx, 0.0)
        wall.arcTo(QRectF(-rx, -ry, 2 * rx, 2 * ry), 180.0, 180.0)
        wall.lineTo(rx * 0.93, depth)
        wall.arcTo(QRectF(-rx * 0.93, depth - ry * 0.9, 2 * rx * 0.93, 2 * ry * 0.9), 0.0, -180.0)
        wall.closeSubpath()
        painter.setPen(ink)
        painter.setBrush(PAN_DARK)
        painter.drawPath(wall)
        # The fire heats the pan: a hot orange glow creeps up its wall from below, pulsing.
        heat = QLinearGradient(0.0, depth + ry * 0.9, 0.0, 0.0)
        pulse = 0.8 + 0.2 * math.sin(self._t * 4.3) * math.sin(self._t * 2.9 + 1.0)
        heat.setColorAt(0.0, QColor(255, 120, 40, int(230 * pulse)))
        heat.setColorAt(0.55, QColor(230, 70, 40, int(120 * pulse)))
        heat.setColorAt(1.0, QColor(200, 50, 40, 0))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(heat)
        painter.drawPath(wall)
        painter.setPen(ink)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawPath(wall)
        painter.setBrush(PAN_MID)
        painter.drawEllipse(QPointF(0.0, 0.0), rx, ry)
        inner = QPainterPath()
        inner.addEllipse(QPointF(0.0, 0.02 * R), rx * 0.86, ry * 0.78)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(PAN_INNER)
        painter.drawPath(inner)

        painter.save()
        painter.setClipPath(inner)
        self._paint_food(painter)
        painter.restore()
        painter.setPen(QPen(PAN_SHINE, 0.03 * R, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawArc(QRectF(-rx * 0.92, -ry * 0.92, 2 * rx * 0.92, 2 * ry * 0.92),
                        int(110 * 16), int(50 * 16))

    def _paint_food(self, painter: QPainter) -> None:
        """Two strips of bacon and two sunny-side-up eggs that jiggle in the heat."""
        R = self.R
        t = self._t
        painter.scale(1.18, 1.18)
        ink = QPen(INK, 0.04 * R, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap,
                   Qt.PenJoinStyle.RoundJoin)
        for k, (x0, y0) in enumerate(((-0.78, -0.12), (-0.62, 0.08))):
            strip = QPainterPath()
            pts = [QPointF((x0 + i * 0.13) * R,
                           (y0 + 0.05 * math.sin(i * 1.7 + t * 5.0 + k)) * R) for i in range(7)]
            strip.moveTo(pts[0])
            for p in pts[1:]:
                strip.lineTo(p)
            painter.setPen(QPen(INK, 0.17 * R, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap,
                                Qt.PenJoinStyle.RoundJoin))
            painter.drawPath(strip)
            painter.setPen(QPen(BACON, 0.12 * R, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap,
                                Qt.PenJoinStyle.RoundJoin))
            painter.drawPath(strip)
            painter.setPen(QPen(BACON_FAT, 0.03 * R, Qt.PenStyle.SolidLine,
                                Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
            painter.drawPath(strip)
        for i, (ex, ey) in enumerate(((0.12, -0.04), (0.6, 0.04))):
            wob = 1.0 + 0.04 * math.sin(t * 7.0 + i * 2.0)
            white = QPainterPath()
            pts = []
            for j in range(9):
                a = j / 9 * math.tau
                rr = (0.27 + 0.05 * math.sin(a * 3.0 + i * 1.3)) * wob
                pts.append(QPointF((ex + math.cos(a) * rr) * R, (ey + math.sin(a) * rr * 0.55) * R))
            white.moveTo(pts[0])
            for j in range(9):
                p1, p2 = pts[j], pts[(j + 1) % 9]
                white.quadTo(p1, QPointF((p1.x() + p2.x()) / 2, (p1.y() + p2.y()) / 2))
            white.closeSubpath()
            painter.setPen(ink)
            painter.setBrush(EGG_WHITE)
            painter.drawPath(white)
            painter.setBrush(YOLK)
            painter.drawEllipse(QPointF((ex + 0.02) * R, (ey - 0.02) * R), 0.11 * R * wob,
                                0.085 * R * wob)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(YOLK_SHINE)
            painter.drawEllipse(QPointF((ex - 0.02) * R, (ey - 0.05) * R), 0.035 * R, 0.022 * R)

    def _paint_wisps(self, painter: QPainter) -> None:
        """Steam puffs (soft white) and grease pops (tiny bright dots)."""
        painter.setPen(Qt.PenStyle.NoPen)
        for w in self._wisps:
            k = w.life / w.max_life
            if w.grease:
                painter.setBrush(QColor(255, 236, 180, int(230 * k)))
                painter.drawEllipse(QPointF(w.x, w.y), w.size, w.size)
            else:
                alpha = int(120 * smoothstep(0.0, 0.3, k) * smoothstep(1.0, 0.7, k))
                painter.setBrush(QColor(STEAM.red(), STEAM.green(), STEAM.blue(), alpha))
                size = w.size * (1.6 - 0.6 * k)
                painter.drawEllipse(QPointF(w.x, w.y), size, size * 0.8)


# ---------------------------------------------------------------------- sunglasses

SHADES_FRAME = QColor(24, 18, 28)
SHADES_LENS_TOP = QColor(58, 50, 78)
SHADES_LENS_BOTTOM = QColor(20, 16, 30)
SHADES_SHINE = QColor(255, 255, 255)
SHADES_MIN_HALF_W = 0.29    # smallest lens half width (R); the lenses grow with bigger eyes
SHADES_MIN_HALF_H = 0.23    # smallest lens half height (R)
SHADES_ARM_X = 0.78         # where the arms disappear behind the flame's sides (R from centre)
GLINT_SECONDS = 0.5         # one sweep of the glint across both lenses


class SunglassesProp:
    """Black wayfarer-style sunglasses over the eyes (``cool`` mood).

    ``show()`` drops them from above (a springy landing with a small dip), then a bright glint
    sweeps across the lenses; ``hide()`` pushes them back up while they fade. They follow the eyes
    every frame (``paint`` gets the eye boxes), so they move, tilt and squash with the face.
    """

    def __init__(self, R: float) -> None:
        """``R`` = character radius in pixels."""
        self.R = R
        self.visible = False
        # 0 = above the head, 1 = on the eyes; slightly under-damped so it lands with a dip.
        self._drop = Spring(0.0, stiffness=190.0, damping=17.0)
        self._target = 0.0
        self._alpha = 0.0
        self._glint = -1.0          # < 0 = no glint; 0..1 = sweep progress
        self._landed = False

    def show(self) -> None:
        """Drop the glasses onto the eyes (again from above if they were gone)."""
        if not self.visible:
            self._drop.value = 0.0
            self._drop.velocity = 0.0
            self._alpha = 0.0
            self._landed = False
            self._glint = -1.0
        self.visible = True
        self._target = 1.0

    def hide(self) -> None:
        """Push the glasses back up; they fade out on the way."""
        self._target = 0.0

    def update(self, dt: float) -> None:
        """Drop / lift spring, fade and the glint sweep."""
        if not self.visible:
            return
        self._drop.step(self._target, dt)
        rising = self._target < 0.5
        self._alpha = approach_linear(self._alpha, 0.0 if rising else 1.0,
                                      dt / (0.3 if rising else 0.12))
        if rising and self._alpha <= 0.01:
            self.visible = False
            return
        if not rising and not self._landed and self._drop.value > 0.97:
            self._landed = True
            self._glint = 0.0
        if self._glint >= 0.0:
            self._glint += dt / GLINT_SECONDS
            if self._glint > 1.0:
                self._glint = -1.0

    def landing_impact(self) -> bool:
        """True on the frame the glasses land on the nose (the character gives a little nod)."""
        return self._target > 0.5 and self._drop.value > 0.97 and self._drop.velocity > 1.2

    def paint(self, painter: QPainter, eyes: tuple[tuple[float, float, float, float], ...],
              tilt: float) -> None:
        """Draw the glasses over ``eyes`` (left and right ``(cx, cy, rx, ry)`` in body pixels),
        rotated by the head ``tilt`` (radians)."""
        if not self.visible or self._alpha <= 0.01:
            return
        R = self.R
        (lx, ly, lrx, lry), (rx_, ry_, rrx, rry) = eyes
        half_w = max(SHADES_MIN_HALF_W * R, 1.2 * max(lrx, rrx))
        half_h = max(SHADES_MIN_HALF_H * R, 0.9 * max(lry, rry))
        mx, my = (lx + rx_) / 2.0, (ly + ry_) / 2.0
        gap = (rx_ - lx) / 2.0               # lens centres sit on the eye centres
        painter.save()
        painter.setOpacity(painter.opacity() * self._alpha)
        painter.translate(mx, my + (1.0 - self._drop.value) * -1.5 * R)
        painter.rotate(math.degrees(tilt))
        lenses = [self._lens_path(side * gap, half_w, half_h) for side in (-1, 1)]
        self._paint_frame(painter, gap, half_w, half_h)
        for lens in lenses:
            self._paint_lens(painter, lens, half_h)
        if self._glint >= 0.0:
            self._paint_glint(painter, lenses, gap, half_w, half_h)
        painter.restore()

    @staticmethod
    def _lens_path(cx: float, half_w: float, half_h: float) -> QPainterPath:
        """One wayfarer lens centred at (``cx``, 0): a nearly straight top edge rising a little
        toward the outer side, and a full rounded bottom."""
        out = 1.0 if cx > 0 else -1.0
        inner_x, outer_x = cx - out * half_w, cx + out * half_w
        top_inner, top_outer = -0.72 * half_h, -0.9 * half_h
        path = QPainterPath(QPointF(inner_x, top_inner))
        path.lineTo(outer_x, top_outer)
        path.cubicTo(QPointF(outer_x + out * 0.08 * half_w, 0.2 * half_h),
                     QPointF(cx + out * 0.55 * half_w, 1.05 * half_h),
                     QPointF(cx, 1.0 * half_h))
        path.cubicTo(QPointF(cx - out * 0.6 * half_w, 0.95 * half_h),
                     QPointF(inner_x - out * 0.02 * half_w, 0.35 * half_h),
                     QPointF(inner_x, top_inner))
        path.closeSubpath()
        return path

    def _paint_frame(self, painter: QPainter, gap: float, half_w: float, half_h: float) -> None:
        """The arms going back to the flame's sides, and the thick top bar with the bridge."""
        R = self.R
        pen = QPen(SHADES_FRAME, 0.07 * R, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap,
                   Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        for side in (-1, 1):
            start = QPointF(side * (gap + half_w), -0.82 * half_h)
            end = QPointF(side * max(SHADES_ARM_X * R, gap + half_w + 0.12 * R), -0.62 * half_h)
            painter.drawLine(start, end)
        bar = QPainterPath(QPointF(-(gap + half_w), -0.9 * half_h))
        bar.lineTo(-(gap - half_w), -0.72 * half_h)
        bar.quadTo(QPointF(0.0, -0.95 * half_h), QPointF(gap - half_w, -0.72 * half_h))
        bar.lineTo(gap + half_w, -0.9 * half_h)
        painter.setPen(QPen(SHADES_FRAME, 0.11 * R, Qt.PenStyle.SolidLine,
                            Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
        painter.drawPath(bar)

    def _paint_lens(self, painter: QPainter, lens: QPainterPath, half_h: float) -> None:
        """A dark lens with a soft top-to-bottom sheen and a small fixed highlight."""
        R = self.R
        fill = QLinearGradient(0.0, -half_h, 0.0, half_h)
        fill.setColorAt(0.0, SHADES_LENS_TOP)
        fill.setColorAt(1.0, SHADES_LENS_BOTTOM)
        painter.setPen(QPen(SHADES_FRAME, 0.05 * R, Qt.PenStyle.SolidLine,
                            Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
        painter.setBrush(fill)
        painter.drawPath(lens)
        box = lens.boundingRect()
        shine = QColor(SHADES_SHINE)
        shine.setAlpha(110)
        painter.setPen(QPen(shine, 0.035 * R, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        x0 = box.left() + box.width() * 0.22
        painter.drawLine(QPointF(x0, box.top() + box.height() * 0.32),
                         QPointF(x0 + box.width() * 0.16, box.top() + box.height() * 0.18))

    def _paint_glint(self, painter: QPainter, lenses: list[QPainterPath], gap: float,
                     half_w: float, half_h: float) -> None:
        """A slanted bright band sliding left to right across both lenses (clipped to them)."""
        R = self.R
        clip = QPainterPath()
        for lens in lenses:
            clip = clip.united(lens)
        span = 2.0 * (gap + half_w) + 0.6 * R
        x = -span / 2.0 + span * smoothstep(0.0, 1.0, self._glint)
        band = QPainterPath(QPointF(x - 0.06 * R, -1.3 * half_h))
        band.lineTo(x + 0.1 * R, -1.3 * half_h)
        band.lineTo(x - 0.12 * R, 1.3 * half_h)
        band.lineTo(x - 0.28 * R, 1.3 * half_h)
        band.closeSubpath()
        painter.save()
        painter.setClipPath(clip)
        glow = QColor(SHADES_SHINE)
        glow.setAlpha(int(200 * math.sin(math.pi * clamp(self._glint, 0.0, 1.0))))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(glow)
        painter.drawPath(band)
        painter.restore()


# ---------------------------------------------------------------------- alarm clock

CLOCK_FACE = QColor(255, 247, 226)      # cream dial
CLOCK_CASE = QColor(176, 44, 46)        # deep red-brown case ring (sticker style)
CLOCK_CASE_LIGHT = QColor(214, 84, 76)
CLOCK_METAL = QColor(52, 186, 172)      # teal bells and feet: they stand out on the orange fire
CLOCK_METAL_LIGHT = QColor(150, 230, 218)
CLOCK_SECOND = QColor(226, 60, 52)
KRING_FILL = QColor(255, 246, 226)
CLOCK_X = 1.58          # clock centre: beside the upper body, to the pet's right (R from feet)
CLOCK_Y = -1.72
CLOCK_RADIUS = 0.4      # outer radius of the case (R)
RING_HZ = 6.0           # rattles per second (at 30 fps each rattle still gets ~5 frames)
RING_DEG_START = 11.0   # rattle angle while it starts ringing ...
RING_DEG_STEADY = 6.0   # ... easing down to this after a few seconds, gentle enough to run long
RING_SETTLE_S = 4.0


class AlarmClockProp:
    """A little alarm clock (⏰) that rings beside the pet while a reminder is due.

    ``show()`` pops it in with a springy overshoot; it then rattles without stopping (the bells
    rock, the hammer hits left and right, "kring" strokes flash on both sides, the second hand
    ticks once a second) until ``hide()``, when it shrinks away and fades ("put away"). The first
    few seconds ring harder; then it calms to a smaller rattle that is fine to leave on screen.
    Painted in body pixels (origin at the feet) but not squashed with the body.
    """

    def __init__(self, R: float) -> None:
        """``R`` = character radius in pixels."""
        self.R = R
        self.visible = False
        self._pop = Spring(0.0, stiffness=230.0, damping=12.0)   # 0 = gone, 1 = there
        self._target = 0.0
        self._alpha = 0.0
        self._t = 0.0           # seconds since it started ringing

    def show(self) -> None:
        """Pop the clock in and start ringing (from the beginning if it was gone)."""
        if not self.visible or self._target < 0.5:
            self._t = 0.0
        if not self.visible:
            self._pop.value = 0.0
            self._pop.velocity = 0.0
            self._alpha = 0.0
        self.visible = True
        self._target = 1.0

    def hide(self) -> None:
        """Put the clock away: it shrinks and fades out."""
        self._target = 0.0

    @property
    def ringing(self) -> bool:
        """True while the clock is out (not on its way away)."""
        return self.visible and self._target > 0.5

    def anchor(self) -> QPointF:
        """Centre of the clock in body pixels (e.g. for the poof when it is put away)."""
        return QPointF(CLOCK_X * self.R, CLOCK_Y * self.R)

    def update(self, dt: float) -> None:
        """Pop / put-away spring, fade and the ringing clock."""
        if not self.visible:
            return
        self._t += dt
        self._pop.step(self._target, dt)
        leaving = self._target < 0.5
        self._alpha = approach_linear(self._alpha, 0.0 if leaving else 1.0,
                                      dt / (0.22 if leaving else 0.1))
        if leaving and self._alpha <= 0.01:
            self.visible = False

    def _rattle(self) -> float:
        """Current rattle (-1..1) times its amplitude in degrees; zero while being put away."""
        if self._target < 0.5:
            return 0.0
        amp = lerp(RING_DEG_START, RING_DEG_STEADY, smoothstep(0.0, RING_SETTLE_S, self._t))
        return amp * math.sin(self._t * math.tau * RING_HZ)

    def paint(self, painter: QPainter) -> None:
        """Draw the clock (bells, hammer, feet, case, dial, hands) and the "kring" strokes."""
        if not self.visible or self._alpha <= 0.01:
            return
        R = self.R
        size = max(0.0, self._pop.value)
        painter.save()
        painter.setOpacity(painter.opacity() * self._alpha)
        painter.translate(CLOCK_X * R, CLOCK_Y * R)
        if self._target > 0.5:
            self._paint_kring(painter)
        # Rocks about a point near its feet, like a real clock dancing on a table.
        angle = self._rattle()
        pivot = 0.4 * R
        painter.translate(0.0, pivot)
        painter.rotate(angle)
        painter.scale(size, size)
        painter.translate(0.0, -pivot)
        self._paint_clock(painter, angle)
        painter.restore()

    def _ink(self, width: float) -> QPen:
        """Round-capped dark outline pen ``width`` R wide."""
        return QPen(INK, width * self.R, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap,
                    Qt.PenJoinStyle.RoundJoin)

    def _paint_clock(self, painter: QPainter, angle: float) -> None:
        """The clock itself, centred on its dial (``angle`` = current rattle, for the hammer)."""
        R = self.R
        r = CLOCK_RADIUS * R
        # Feet: two stubby teal legs splayed out under the case (outline first, then fill).
        for side in (-1, 1):
            a = math.radians(90 + side * 38)
            start = QPointF(math.cos(a) * r * 0.8, math.sin(a) * r * 0.8)
            end = QPointF(math.cos(a) * r * 1.28, math.sin(a) * r * 1.22)
            painter.setPen(self._ink(0.17))
            painter.drawLine(start, end)
            painter.setPen(QPen(CLOCK_METAL, 0.09 * R, Qt.PenStyle.SolidLine,
                                Qt.PenCapStyle.RoundCap))
            painter.drawLine(start, end)
        # Hammer: a short stem on top with a ball that swings with the rattle, hitting the bells.
        swing = clamp(angle / RING_DEG_START, -1.0, 1.0)
        base = QPointF(0.0, -r * 0.98)
        tip = QPointF(-swing * 0.2 * R, -r * 1.42)
        painter.setPen(self._ink(0.06))
        painter.drawLine(base, tip)
        painter.setBrush(CLOCK_METAL)
        painter.drawEllipse(tip, 0.07 * R, 0.07 * R)
        # Bells: two domes on top, tipped outward, each with a little knob.
        for side in (-1, 1):
            painter.save()
            a = math.radians(-90 + side * 42)
            painter.translate(math.cos(a) * r * 1.02, math.sin(a) * r * 1.02)
            painter.rotate(side * 42)
            bw, bh = 0.27 * R, 0.21 * R
            dome = QPainterPath(QPointF(-bw, 0.0))
            dome.cubicTo(QPointF(-bw, -bh * 1.35), QPointF(bw, -bh * 1.35), QPointF(bw, 0.0))
            dome.quadTo(QPointF(0.0, bh * 0.28), QPointF(-bw, 0.0))
            dome.closeSubpath()
            painter.setPen(self._ink(0.055))
            painter.setBrush(CLOCK_METAL)
            painter.drawPath(dome)
            painter.drawEllipse(QPointF(0.0, -bh * 1.05), 0.05 * R, 0.05 * R)
            painter.setPen(QPen(CLOCK_METAL_LIGHT, 0.035 * R, Qt.PenStyle.SolidLine,
                                Qt.PenCapStyle.RoundCap))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            shine = QPainterPath(QPointF(-bw * 0.55, -bh * 0.25))
            shine.quadTo(QPointF(-bw * 0.45, -bh * 0.8), QPointF(-bw * 0.05, -bh * 0.92))
            painter.drawPath(shine)
            painter.restore()
        # Case and dial.
        painter.setPen(self._ink(0.06))
        painter.setBrush(CLOCK_CASE)
        painter.drawEllipse(QPointF(0.0, 0.0), r, r)
        painter.setPen(QPen(CLOCK_CASE_LIGHT, 0.04 * R, Qt.PenStyle.SolidLine,
                            Qt.PenCapStyle.RoundCap))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawArc(QRectF(-r * 0.86, -r * 0.86, r * 1.72, r * 1.72), 100 * 16, 60 * 16)
        dial = r * 0.74
        painter.setPen(self._ink(0.04))
        painter.setBrush(CLOCK_FACE)
        painter.drawEllipse(QPointF(0.0, 0.0), dial, dial)
        # Four hour marks, then the hands (short hour hand, long minute hand, ticking seconds).
        painter.setPen(self._ink(0.04))
        for i in range(4):
            a = i * math.pi / 2
            painter.drawLine(QPointF(math.cos(a) * dial * 0.7, math.sin(a) * dial * 0.7),
                             QPointF(math.cos(a) * dial * 0.86, math.sin(a) * dial * 0.86))
        painter.setPen(self._ink(0.055))
        painter.drawLine(QPointF(0.0, 0.0), QPointF(dial * 0.36, -dial * 0.2))
        painter.drawLine(QPointF(0.0, 0.0), QPointF(-dial * 0.08, -dial * 0.66))
        tick = math.floor(self._t) * math.tau / 60.0 + math.radians(20)
        painter.setPen(QPen(CLOCK_SECOND, 0.025 * R, Qt.PenStyle.SolidLine,
                            Qt.PenCapStyle.RoundCap))
        painter.drawLine(QPointF(0.0, 0.0),
                         QPointF(math.sin(tick) * dial * 0.72, -math.cos(tick) * dial * 0.72))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(INK)
        painter.drawEllipse(QPointF(0.0, 0.0), 0.045 * R, 0.045 * R)

    def _paint_kring(self, painter: QPainter) -> None:
        """Three short "kring" strokes fanning out on each side of the clock; the two sides
        flash in turn with the rattle (cream with the dark outline, readable on any wallpaper)."""
        R = self.R
        r = CLOCK_RADIUS * R
        phase = self._t * math.tau * RING_HZ
        for side in (-1, 1):
            flash = 0.5 + 0.5 * math.sin(phase + (0.0 if side > 0 else math.pi))
            alpha = smoothstep(0.15, 0.85, flash)
            if alpha <= 0.02:
                continue
            painter.save()
            painter.setOpacity(painter.opacity() * alpha)
            reach = 0.02 * R * flash
            for k, deg in enumerate((-32.0, 0.0, 32.0)):
                a = math.radians(deg - 18.0)
                inner = r * 1.45 + reach
                outer = inner + (0.2 if k == 1 else 0.15) * R
                p0 = QPointF(side * math.cos(a) * inner, math.sin(a) * inner)
                p1 = QPointF(side * math.cos(a) * outer, math.sin(a) * outer)
                painter.setPen(self._ink(0.1))
                painter.drawLine(p0, p1)
                painter.setPen(QPen(KRING_FILL, 0.05 * R, Qt.PenStyle.SolidLine,
                                    Qt.PenCapStyle.RoundCap))
                painter.drawLine(p0, p1)
            painter.restore()


def approach_linear(current: float, target: float, step: float) -> float:
    """Move ``current`` toward ``target`` by at most ``step``."""
    if current < target:
        return min(target, current + step)
    return max(target, current - step)


# ---------------------------------------------------------------------- snoring "z"s

ZZZ_FILL = QColor(255, 246, 226)


@dataclass
class _Zee:
    """One floating "z" (widget pixels)."""

    x: float
    y: float
    age: float
    life: float
    size: float
    phase: float


class Snores:
    """Sleepy "z" letters drifting up from the pet's head while it sleeps."""

    def __init__(self, R: float, rng: random.Random) -> None:
        """``R`` = character radius in pixels."""
        self.R = R
        self._rng = rng
        self._zees: list[_Zee] = []
        self._next = 1.2

    def update(self, dt: float, active: bool, origin: QPointF, moved: tuple[float, float]) -> None:
        """Spawn a new "z" every couple of seconds at ``origin`` (widget px) while ``active``;
        ``moved`` = how far the window moved this frame (the letters stay in screen space)."""
        self._next -= dt
        if active and self._next <= 0.0:
            self._next = self._rng.uniform(1.4, 2.2)
            self._zees.append(_Zee(origin.x(), origin.y(), 0.0, self._rng.uniform(2.4, 3.0),
                                   self._rng.uniform(0.85, 1.15), self._rng.uniform(0, math.tau)))
        elif not active:
            self._next = min(self._next, 0.6)
        R = self.R
        alive = []
        for z in self._zees:
            z.age += dt
            if z.age >= z.life:
                continue
            z.x += (0.28 * R + 0.35 * R * math.cos(z.age * 2.4 + z.phase)) * dt - moved[0]
            z.y += -0.62 * R * dt - moved[1]
            alive.append(z)
        self._zees = alive

    def paint(self, painter: QPainter) -> None:
        """Draw each "z": a cream letter with the dark outline, growing and fading out."""
        R = self.R
        for z in self._zees:
            k = z.age / z.life
            alpha = smoothstep(0.0, 0.12, k) * (1.0 - smoothstep(0.6, 1.0, k))
            size = 0.26 * R * z.size * (0.45 + 0.75 * smoothstep(0.0, 0.5, k))
            tilt = 12.0 * math.sin(z.age * 2.0 + z.phase)
            painter.save()
            painter.setOpacity(painter.opacity() * alpha)
            painter.translate(z.x, z.y)
            painter.rotate(tilt)
            path = QPainterPath(QPointF(-size, -size))
            path.lineTo(size, -size)
            path.lineTo(-size, size)
            path.lineTo(size, size)
            width = clamp(size * 0.34, 1.2, 0.2 * R)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.setPen(QPen(INK, width + 0.07 * R, Qt.PenStyle.SolidLine,
                                Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
            painter.drawPath(path)
            painter.setPen(QPen(ZZZ_FILL, width, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap,
                                Qt.PenJoinStyle.RoundJoin))
            painter.drawPath(path)
            painter.restore()
