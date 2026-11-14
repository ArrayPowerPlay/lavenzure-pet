"""Holiday outfits the flame character can wear (task P4 / T6 in ``docs/TASKS.md``).

An outfit is a prop like the ones in ``overlay.props`` - a small model + painter that never moves
the window - but it is worn for days, across every mood, instead of belonging to one mood.
So it must follow the face of *any* expression: it is anchored to the eyes
(``Face.eye_boxes()``), the one landmark every expression has, never to the flame's tip
(the GPU flame moves all the time and the painter cannot know where its tip is).

- ``SantaHatProp`` - a big Santa hat (decision 2026-11-15, option a): it covers the top of the
  flame so the fire only licks out on both sides of the fur brim. The brim floats a clear gap
  above the eyes. The soft tip flops to one side and swings with the pet's own movement
  (walking sweeps it back, hops make it bounce), and the pompom jiggles a moment behind it.

All lengths are in units of R (the character's base radius); painting happens in the
character's body coordinates (pixels, origin at the feet, y down).
"""
from __future__ import annotations

import math

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import (
    QColor,
    QImage,
    QPainter,
    QPainterPath,
    QPainterPathStroker,
    QPen,
    QPolygonF,
)

from overlay.flame_common import Spring, clamp, noise1
from overlay.props import INK, approach_linear

HAT_RED = QColor(214, 34, 48)
HAT_RED_DARK = QColor(158, 18, 38)       # underside of the flopped tip
HAT_RED_LIGHT = QColor(246, 96, 96)      # thin shine along the upper edge
FUR = QColor(255, 250, 240)
FUR_SHADE = QColor(232, 216, 204)

HAT_GAP = 0.24           # clear space between the top of the eyes and the brim's lower edge (R)
BRIM_HALF_W = 0.92       # half width of the fur brim (R); the fire licks out beyond it
BRIM_HALF_H = 0.2        # half height of the brim (R)
BRIM_SAG = 0.08          # the brim wraps round the head, so its middle sits a little lower (R)
CONE_HALF_W = 0.76       # half width of the red cone where it meets the brim (R)
CROWN = (0.06, -1.3)     # where the cone's rounded crown turns into the flopped tube (R)
TUBE_HALF_W = 0.3        # half width of the flopped tube where it leaves the crown (R)
TIP_LEN = 1.16           # crown to pompom, straight line (R)
TIP_REST = math.radians(142)   # resting flop angle: 0 = straight up, 90 = sideways, 180 = down
POM_RADIUS = 0.21        # pompom radius (R)
GAZE_FOLLOW = 0.5        # the hat sits on top of the head, so it slides less than the eyes
BRIM_BUMPS = 7           # fluffy scallops along each edge of the brim
SPRITE_SUPERSAMPLE = 2.0 # still parts are pre-drawn at this many pixels per screen pixel
SPINE_STEPS = 18         # samples along the tube's centre line (smooth enough at any scale)


class SantaHatProp:
    """A soft red Santa hat with a white fur brim and pompom, worn above the eyes.

    ``show()`` drops it onto the head from above (springy landing, a small squish of the body via
    ``landing_impact``); ``hide()`` lifts it off while it fades. Every frame ``update`` gets the
    pet's velocity, so the floppy tip swings like cloth: it trails behind when the pet walks,
    dips when it takes off and flicks up when it lands, then sways gently at rest.
    """

    def __init__(self, R: float, seed: int = 0) -> None:
        """``R`` = character radius in pixels; ``seed`` varies the idle sway between pets."""
        self.R = R
        self.visible = False
        self._seed = seed
        self._t = 0.0
        # 0 = above the head, 1 = worn; slightly under-damped so it lands with a dip.
        self._drop = Spring(0.0, stiffness=170.0, damping=16.0)
        self._target = 0.0
        self._alpha = 0.0
        # Floppy tip: a loose, lightly damped spring on the flop angle (radians) ...
        self._flop = Spring(TIP_REST, stiffness=38.0, damping=4.2)
        self._prev_vy: float | None = None
        # ... and the pompom lagging a moment behind the tip (offset in R).
        self._pom_x = Spring(0.0, stiffness=150.0, damping=9.0)
        self._pom_y = Spring(0.0, stiffness=150.0, damping=9.0)
        self._prev_tip: tuple[float, float] | None = None
        # Drawing tools and the shapes that never change, built once.
        self._pen = QPen(INK, 0.055 * R, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap,
                         Qt.PenJoinStyle.RoundJoin)
        self._shine_pen = QPen(HAT_RED_LIGHT, 0.065 * R, Qt.PenStyle.SolidLine,
                               Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
        self._sprites: dict[float, tuple[tuple[QImage, QRectF], tuple[QImage, QRectF]]] = {}
        self._pom_sprite: tuple[QImage, QRectF] | None = None

    def show(self) -> None:
        """Put the hat on (dropping it from above if it was off)."""
        if not self.visible:
            self._drop.value = 0.0
            self._drop.velocity = 0.0
            self._alpha = 0.0
            self._flop.value, self._flop.velocity = TIP_REST, 0.0
            self._prev_tip = None
        self.visible = True
        self._target = 1.0

    def hide(self) -> None:
        """Lift the hat off; it fades on the way up."""
        self._target = 0.0

    @property
    def amount(self) -> float:
        """How much the hat is on, 0 (off) to 1 (fully on); the character lowers the flame by it
        so the fire licks out at the sides instead of shooting out of the top of the hat."""
        return self._alpha if self.visible else 0.0

    @property
    def worn(self) -> bool:
        """True while the hat is on (or coming on), False once it is being taken off."""
        return self.visible and self._target > 0.5

    def update(self, dt: float, vx: float, vy: float) -> None:
        """Drop / lift, fade and the cloth swing of the tip.

        ``vx`` / ``vy`` = the body's velocity in R per second (screen axes, y down), i.e. the
        window's movement plus the walking hop.
        """
        if not self.visible:
            return
        self._t += dt
        self._drop.step(self._target, dt)
        lifting = self._target < 0.5
        self._alpha = approach_linear(self._alpha, 0.0 if lifting else 1.0,
                                      dt / (0.3 if lifting else 0.12))
        if lifting and self._alpha <= 0.01:
            self.visible = False
            return
        # Horizontal motion: the tip trails behind (moving right lets it hang down toward the
        # back, moving left streams it out to the right).
        # A slow wander keeps it from ever hanging perfectly still.
        sway = 0.07 * noise1(self._t * 0.45, self._seed + 911)
        target = TIP_REST + clamp(vx * 0.11, -0.8, 0.8) + sway
        # Vertical acceleration kicks it like a pendulum: taking off (velocity turning upward)
        # throws the tip down, landing flicks it up.
        if self._prev_vy is not None and dt > 0.0:
            dv = clamp(vy - self._prev_vy, -6.0, 6.0)
            self._flop.velocity -= dv * 0.9 * math.sin(self._flop.value)
        self._prev_vy = vy
        self._flop.step(target, dt)
        self._flop.value = clamp(self._flop.value, math.radians(25), math.radians(172))
        # Pompom: pushed opposite to how far the tip moved this frame, springs back.
        tip = self._tip_point(self._flop.value)
        if self._prev_tip is not None:
            self._pom_x.velocity -= (tip[0] - self._prev_tip[0]) * 9.0
            self._pom_y.velocity -= (tip[1] - self._prev_tip[1]) * 9.0
        self._prev_tip = tip
        self._pom_x.step(0.0, dt)
        self._pom_y.step(0.0, dt)

    def landing_impact(self) -> bool:
        """True on the frame the hat lands on the head (the body gives a small squish)."""
        return self._target > 0.5 and self._drop.value > 0.97 and self._drop.velocity > 1.0

    # ------------------------------------------------------------------ geometry (units of R)

    @staticmethod
    def _tip_point(flop: float) -> tuple[float, float]:
        """Pompom centre for flop angle ``flop`` (hat coordinates, R)."""
        return CROWN[0] + TIP_LEN * math.sin(flop), CROWN[1] - TIP_LEN * math.cos(flop)

    def _cone_path(self, width: float) -> QPainterPath:
        """The upright part of the hat (pixels, hat coordinates): from the brim up to a round
        crown, leaning a little toward the side the tip hangs. Its base hides under the brim."""
        R = self.R
        hw = CONE_HALF_W * width
        cx, cy = CROWN
        path = QPainterPath(QPointF(-hw * R, 0.0))
        path.cubicTo(QPointF(-0.9 * hw * R, -0.62 * R), QPointF((cx - 0.5) * R, (cy - 0.05) * R),
                     QPointF((cx - 0.12) * R, (cy - TUBE_HALF_W * 0.95) * R))
        path.quadTo(QPointF((cx + 0.22) * R, (cy - TUBE_HALF_W * 1.2) * R),
                    QPointF((cx + TUBE_HALF_W) * R, (cy - 0.02) * R))
        path.cubicTo(QPointF((cx + 0.42) * R, (cy + 0.5) * R), QPointF(0.92 * hw * R, -0.45 * R),
                     QPointF(hw * R, 0.0))
        path.closeSubpath()
        return path

    def _tube_spine(self, flop: float) -> list[tuple[float, float, float, float, float]]:
        """Samples ``(x, y, nx, ny, half)`` along the flopped tube, crown to tip (R units).

        The centre line is a quadratic curve that leaves the crown less bent than the straight
        line to the pompom, so the cloth arcs over before it hangs. ``(nx, ny)`` is the normal
        toward the outside of the arc ("upper" edge); the inside is the fold. ``half`` = half
        width, tapering from the crown to a thin tube.
        """
        sx, sy = CROWN
        tx, ty = self._tip_point(flop)
        lead = flop * 0.5
        qx, qy = sx + 0.55 * TIP_LEN * math.sin(lead), sy - 0.55 * TIP_LEN * math.cos(lead)
        side = 1.0 if math.sin(flop) >= 0.0 else -1.0
        out = []
        for i in range(SPINE_STEPS + 1):
            t = i / SPINE_STEPS
            u = 1.0 - t
            dx = 2 * u * (qx - sx) + 2 * t * (tx - qx)
            dy = 2 * u * (qy - sy) + 2 * t * (ty - qy)
            n = math.hypot(dx, dy) or 1.0
            out.append((u * u * sx + 2 * u * t * qx + t * t * tx,
                        u * u * sy + 2 * u * t * qy + t * t * ty,
                        dy / n * side, -dx / n * side,
                        TUBE_HALF_W * (1.0 - t) ** 1.15 + 0.07 * t))
        return out

    # ------------------------------------------------------------------ painting

    def _still_sprites(self, width: float) -> tuple[tuple[QImage, QRectF], tuple[QImage, QRectF]]:
        """The parts that never move relative to the brim, pre-drawn once per (rounded) body
        width: the cone with its shine (behind the floppy tube) and the fur brim (in front).
        Drawing two small images per frame is several times cheaper than stroking the paths
        under the body's squash and lean, and they are supersampled like the flame image."""
        key = round(width * 50.0) / 50.0
        sprites = self._sprites.get(key)
        if sprites is None:
            if len(self._sprites) > 24:
                self._sprites.clear()
            brim = self._brim_path(key)
            tufts = QPainterPath()
            hw, hh = BRIM_HALF_W * key, BRIM_HALF_H
            for i in range(BRIM_BUMPS):
                x = -hw + 2 * hw * (i + 0.5) / BRIM_BUMPS
                tufts.addEllipse(QPointF(x * self.R, (_brim_mid(x, hw) + hh * 0.72) * self.R),
                                 hw / BRIM_BUMPS * 0.62 * self.R, hh * 0.42 * self.R)
            cone = self._sprite([(self._cone_path(key), self._pen, HAT_RED),
                                 (self._shine_path(), self._shine_pen, None)])
            fur = self._sprite([(brim, self._pen, FUR),
                                (self._inset(brim).intersected(tufts), None, FUR_SHADE)])
            sprites = (cone, fur)
            self._sprites[key] = sprites
        return sprites

    def _sprite(self, layers: list[tuple[QPainterPath, QPen | None, QColor | None]]
                ) -> tuple[QImage, QRectF]:
        """Pre-draw ``layers`` (path, outline pen or None, fill or None) into a transparent image;
        returns it with the rectangle (hat coordinates, pixels) it must be drawn into."""
        margin = self._pen.widthF()
        rect = QRectF()
        for path, _pen, _fill in layers:
            rect = rect.united(path.boundingRect())
        rect = rect.adjusted(-margin, -margin, margin, margin)
        ss = SPRITE_SUPERSAMPLE
        img = QImage(max(1, math.ceil(rect.width() * ss)), max(1, math.ceil(rect.height() * ss)),
                     QImage.Format.Format_ARGB32_Premultiplied)
        img.fill(0)
        p = QPainter(img)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        p.scale(ss, ss)
        p.translate(-rect.left(), -rect.top())
        for path, pen, fill in layers:
            p.setPen(pen if pen is not None else Qt.PenStyle.NoPen)
            p.setBrush(fill if fill is not None else Qt.BrushStyle.NoBrush)
            p.drawPath(path)
        p.end()
        return img, QRectF(rect.left(), rect.top(), img.width() / ss, img.height() / ss)

    def paint(self, painter: QPainter, eyes: tuple[tuple[float, float, float, float], ...],
              tilt: float, width: float = 1.0) -> None:
        """Draw the hat above ``eyes`` (left and right ``(cx, cy, rx, ry)`` in body pixels),
        rotated by the head ``tilt`` (radians). ``width`` = the body's width factor, so a
        puffed-up body gets a bigger hat."""
        if not self.visible or self._alpha <= 0.01:
            return
        R = self.R
        (lx, ly, _lrx, lry), (rx_, ry_, _rrx, rry) = eyes
        top = min(ly - lry, ry_ - rry)
        mx = (lx + rx_) / 2.0 * GAZE_FOLLOW
        brim_y = top - (HAT_GAP + BRIM_HALF_H) * R
        (cone_img, cone_rect), (fur_img, fur_rect) = self._still_sprites(clamp(width, 0.8, 1.5))
        if self._pom_sprite is None:
            pom, shade = self._pompom_paths()
            self._pom_sprite = self._sprite([(pom, self._pen, FUR), (shade, None, FUR_SHADE)])
        pom_img, pom_rect = self._pom_sprite
        painter.save()
        painter.setOpacity(painter.opacity() * self._alpha)
        painter.translate(mx, brim_y + (1.0 - self._drop.value) * -1.8 * R)
        painter.rotate(math.degrees(tilt))
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
        flop = self._flop.value
        painter.drawImage(cone_rect, cone_img)                 # cone and its shine
        self._paint_tube(painter, flop)                        # the only part redrawn
        painter.drawImage(fur_rect, fur_img)                   # fur brim
        tx, ty = self._tip_point(flop)                         # pompom, lagging behind the tip
        painter.drawImage(pom_rect.translated((tx + self._pom_x.value) * R,
                                              (ty + self._pom_y.value) * R), pom_img)
        painter.restore()

    def _paint_tube(self, painter: QPainter, flop: float) -> None:
        """The flopped part over the cone, redrawn every frame because it swings.

        Drawn as filled polygons only (much cheaper than stroking a path): an ink band one pen
        width wider than the tube, the red tube inside it, then a darker underside. The band is
        open at the crown, so the tube melts into the cone, and its inner edge, where the tube
        lies over the cone, reads as the fold.
        """
        R = self.R
        pen = 0.5 * self._pen.widthF() / R
        spine = self._tube_spine(flop)
        ink_up, ink_lo, red_up, red_lo, mid = [], [], [], [], []
        for x, y, nx, ny, half in spine:
            ink_up.append(QPointF((x + nx * (half + pen)) * R, (y + ny * (half + pen)) * R))
            ink_lo.append(QPointF((x - nx * (half + pen)) * R, (y - ny * (half + pen)) * R))
            h = max(half - pen, 0.01)
            red_up.append(QPointF((x + nx * h) * R, (y + ny * h) * R))
            red_lo.append(QPointF((x - nx * h) * R, (y - ny * h) * R))
        # Underside: from the inner edge 45% of the way across, fading in from the crown.
        for i, (x, y, nx, ny, half) in enumerate(spine):
            h = max(half - pen, 0.01)
            k = 0.9 * min(1.0, max(0.0, (i - 2) / 5.0))
            mid.append(QPointF((x - nx * h * (1.0 - k)) * R, (y - ny * h * (1.0 - k)) * R))
        # The red starts a little back inside the crown, so no ink fringe shows where the band
        # is open.
        x, y, nx, ny, half = spine[0]
        side = 1.0 if math.sin(flop) >= 0.0 else -1.0
        bx, by = x + ny * side * 3.0 * pen, y - nx * side * 3.0 * pen
        h = max(half - pen, 0.01)
        red_up.insert(0, QPointF((bx + nx * h) * R, (by + ny * h) * R))
        red_lo.insert(0, QPointF((bx - nx * h) * R, (by - ny * h) * R))
        mid.insert(0, red_lo[0])
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(INK)
        painter.drawPolygon(QPolygonF(ink_up + ink_lo[::-1]), Qt.FillRule.WindingFill)
        painter.setBrush(HAT_RED)
        painter.drawPolygon(QPolygonF(red_up + red_lo[::-1]), Qt.FillRule.WindingFill)
        painter.setBrush(HAT_RED_DARK)
        painter.drawPolygon(QPolygonF(red_lo[3:] + mid[:2:-1]), Qt.FillRule.WindingFill)

    def _shine_path(self) -> QPainterPath:
        """A short light stroke inside the cone's left edge."""
        R = self.R
        hw = CONE_HALF_W
        shine = QPainterPath(QPointF(-0.6 * hw * R, -0.3 * R))
        shine.cubicTo(QPointF(-0.56 * hw * R, -0.62 * R), QPointF(-0.42 * R, -0.95 * R),
                      QPointF(-0.24 * R, -1.18 * R))
        return shine

    def _brim_path(self, width: float) -> QPainterPath:
        """Fluffy white fur band (pixels, hat coordinates): soft scallops along the top and
        bottom, round ends, sagging a little in the middle as it wraps round the head."""
        R = self.R
        hw = BRIM_HALF_W * width
        hh = BRIM_HALF_H
        bumps = BRIM_BUMPS

        def mid_y(x: float) -> float:
            """Centre line of the band at ``x`` (R)."""
            return _brim_mid(x, hw)

        path = QPainterPath()
        path.moveTo(-hw * R, (mid_y(-hw) - hh * 0.85) * R)
        for i in range(bumps):
            x1 = -hw + 2 * hw * (i + 1) / bumps
            xm = -hw + 2 * hw * (i + 0.5) / bumps
            path.quadTo(QPointF(xm * R, (mid_y(xm) - hh * 1.22) * R),
                        QPointF(x1 * R, (mid_y(x1) - hh * 0.95) * R))
        path.cubicTo(QPointF((hw + hh * 0.75) * R, (mid_y(hw) - hh) * R),
                     QPointF((hw + hh * 0.75) * R, (mid_y(hw) + hh) * R),
                     QPointF(hw * R, (mid_y(hw) + hh * 0.95) * R))
        for i in range(bumps, 0, -1):
            x1 = -hw + 2 * hw * (i - 1) / bumps
            xm = -hw + 2 * hw * (i - 0.5) / bumps
            path.quadTo(QPointF(xm * R, (mid_y(xm) + hh * 1.2) * R),
                        QPointF(x1 * R, (mid_y(x1) + hh * 0.95) * R))
        path.cubicTo(QPointF((-hw - hh * 0.75) * R, (mid_y(-hw) + hh) * R),
                     QPointF((-hw - hh * 0.75) * R, (mid_y(-hw) - hh) * R),
                     QPointF(-hw * R, (mid_y(-hw) - hh * 0.85) * R))
        path.closeSubpath()
        return path

    def _pompom_paths(self) -> tuple[QPainterPath, QPainterPath]:
        """Fluffy ball centred on the origin (a scalloped circle) and its shaded lower-right
        crescent."""
        r = POM_RADIUS * self.R
        bumps = 9
        pom = QPainterPath(QPointF(r, 0.0))
        for i in range(1, bumps + 1):
            a = math.tau * i / bumps
            am = math.tau * (i - 0.5) / bumps
            pom.quadTo(QPointF(1.22 * r * math.cos(am), 1.22 * r * math.sin(am)),
                       QPointF(r * math.cos(a), r * math.sin(a)))
        pom.closeSubpath()
        dark = QPainterPath()
        dark.addEllipse(QPointF(0.35 * r, 0.4 * r), 0.85 * r, 0.7 * r)
        light = QPainterPath()
        light.addEllipse(QPointF(-0.1 * r, -0.1 * r), 0.8 * r, 0.75 * r)
        return pom, self._inset(pom).intersected(dark).subtracted(light)

    def _inset(self, path: QPainterPath) -> QPainterPath:
        """``path`` minus the inner half of its outline, so shading drawn inside it never
        covers the ink line."""
        stroker = QPainterPathStroker()
        stroker.setWidth(self._pen.widthF())
        return path.subtracted(stroker.createStroke(path))


def _brim_mid(x: float, half_w: float) -> float:
    """Centre line of the fur brim at ``x`` (R): ``BRIM_SAG`` lower in the middle than at the
    ends, because the band wraps round the head."""
    return BRIM_SAG * (1.0 - (x / half_w) ** 2)
