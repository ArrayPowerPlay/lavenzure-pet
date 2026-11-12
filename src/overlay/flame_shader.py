"""GPU flame renderer (``character.flame_renderer: shader``): rising noise fire in a GLSL shader.

How it works:

- A fragment shader computes, for every pixel of the flame area, a "heat" value: the body
  ellipse plus a teardrop cone above it (leaning with ``sway`` and the wind), eaten away by
  domain-warped fractal noise that scrolls upward. Because the noise is 3D (x, height, time) and
  moves up through the shape, tongues are born on the body, rise, stretch, split, pinch off into
  little pieces and die - and the pattern never repeats.
- The noise is weak on the lower body (the face area stays calm and round) and grows with height.
- The heat is cut into the flat sticker bands - red rim, orange band, yellow body - plus a dark
  outline of constant width (the shader divides by the heat gradient so the outline does not get
  thicker where the heat changes slowly). Edges are anti-aliased.
- Rendering happens offscreen (``QOffscreenSurface`` + framebuffer object) and the result is read
  back into a ``QImage`` that the normal QPainter code draws. The overlay window therefore stays an
  ordinary per-pixel-alpha window, so transparency and click-through behave exactly as before.

If OpenGL 3.3 is not available (old driver, some remote-desktop sessions) the constructor raises
and ``make_flame_renderer`` falls back to the metaball renderer.
"""
from __future__ import annotations

import math
import random
import struct

import numpy as np
from PySide6.QtGui import QOffscreenSurface, QOpenGLContext, QSurfaceFormat
from PySide6.QtOpenGL import (
    QOpenGLBuffer,
    QOpenGLFramebufferObject,
    QOpenGLShader,
    QOpenGLShaderProgram,
    QOpenGLVertexArrayObject,
)

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

_GL_FLOAT = 0x1406
_GL_TRIANGLE_STRIP = 0x0005
_GL_COLOR_BUFFER_BIT = 0x4000

_VERTEX_SHADER = """
#version 330 core
in vec2 pos;
void main() { gl_Position = vec4(pos, 0.0, 1.0); }
"""

_FRAGMENT_SHADER = """
#version 330 core
out vec4 fragColor;

uniform vec2 uSize;        // framebuffer size in pixels
uniform vec4 uRange;       // x0, x1, h0, h1: body-space area covered (R; h = height above feet)
uniform float uTime;       // fire clock (already scaled by flicker speed)
uniform float uSeed;
uniform float uFlame;      // height multiplier
uniform float uWild;       // turbulence strength
uniform float uSway;       // lean of the main tip (radians)
uniform vec2 uWind;        // apparent wind (R/s), x right, y down
uniform float uBreath;     // -1..1 slow breathing of the body
uniform float uFlare;      // 0..1 decaying flare-up
uniform float uPxPerR;     // framebuffer pixels per R
uniform float uOutlinePx;  // outline width in framebuffer pixels
uniform vec3 uOuter, uMid, uInner, uInk;
uniform vec3 uBody;        // body centre height, half-width, half-height (R)
uniform vec2 uInsets;      // mid / inner band insets on the calm body (R)
uniform vec4 uShape;       // body width mult, body height mult, boxiness 0..1, raggedness 0..1
uniform vec4 uArms;        // side flares: amount 0..1, flap phase, flap strength, unused

// ---- 3D gradient noise (hash-based, no textures) ----
vec3 hash3(vec3 p) {
    p = vec3(dot(p, vec3(127.1, 311.7, 74.7)), dot(p, vec3(269.5, 183.3, 246.1)),
             dot(p, vec3(113.5, 271.9, 124.6)));
    return -1.0 + 2.0 * fract(sin(p) * 43758.5453123);
}

float gnoise(vec3 p) {
    vec3 i = floor(p);
    vec3 f = fract(p);
    vec3 u = f * f * f * (f * (f * 6.0 - 15.0) + 10.0);
    return mix(mix(mix(dot(hash3(i + vec3(0,0,0)), f - vec3(0,0,0)),
                       dot(hash3(i + vec3(1,0,0)), f - vec3(1,0,0)), u.x),
                   mix(dot(hash3(i + vec3(0,1,0)), f - vec3(0,1,0)),
                       dot(hash3(i + vec3(1,1,0)), f - vec3(1,1,0)), u.x), u.y),
               mix(mix(dot(hash3(i + vec3(0,0,1)), f - vec3(0,0,1)),
                       dot(hash3(i + vec3(1,0,1)), f - vec3(1,0,1)), u.x),
                   mix(dot(hash3(i + vec3(0,1,1)), f - vec3(0,1,1)),
                       dot(hash3(i + vec3(1,1,1)), f - vec3(1,1,1)), u.x), u.y), u.z);
}

float fbm(vec3 p) {
    float sum = 0.0;
    float amp = 0.55;
    for (int i = 0; i < 3; i++) {
        sum += amp * gnoise(p);
        p = p * 2.07 + vec3(17.1, -9.3, 4.7);
        amp *= 0.33;
    }
    return sum;
}

float smin(float a, float b, float k) {
    float h = clamp(0.5 + 0.5 * (b - a) / k, 0.0, 1.0);
    return mix(b, a, h) - k * h * (1.0 - h);
}

// Distance to one flame "arm" (reference sheet, fig. 6): a soft, thick tube that comes out of the
// lower side of the body, runs outward almost level, then curls up into a round fist.
// ``side`` is -1 (left) or 1 (right).
float sideFlare(vec2 p, float side, float cy, float rx, float amount, float phase, float flap) {
    vec2 base = vec2(side * rx * 0.7, cy - 0.32);
    float reach = 1.08 * amount, rise = 0.62 * amount;
    float ang = side * flap * (0.22 * sin(phase) + 0.08 * sin(phase * 2.3 + 1.0));
    float ca = cos(ang), sa = sin(ang);
    float best = 1e5;
    vec2 prev = base;
    float rPrev = 0.3 * (0.45 + 0.55 * amount);
    for (int i = 1; i <= 7; i++) {
        float s = float(i) / 7.0;
        // Out of the side with a little sag, then the forearm bends up at the end.
        float bend = smoothstep(0.5, 1.0, s);
        vec2 off = vec2(side * reach * (s - 0.18 * bend * bend),
                        -0.13 * amount * sin(3.14159 * min(s, 0.75)) + rise * bend * bend);
        off = vec2(off.x * ca - off.y * sa, off.x * sa + off.y * ca);
        vec2 cur = base + off;
        float rCur = mix(0.27, 0.16, s) * (0.45 + 0.55 * amount);
        vec2 ab = cur - prev;
        float t = clamp(dot(p - prev, ab) / max(dot(ab, ab), 1e-6), 0.0, 1.0);
        best = min(best, length(p - (prev + ab * t)) - mix(rPrev, rCur, t));
        prev = cur;
        rPrev = rCur;
    }
    // The fist: a round blob at the end of the arm.
    return min(best, length(p - prev - vec2(0.0, 0.03)) - 0.22 * amount);
}

void main() {
    vec2 uv = gl_FragCoord.xy / uSize;
    float x = mix(uRange.x, uRange.y, uv.x);
    float h = mix(uRange.z, uRange.w, uv.y);       // height above the feet (R)
    // The feet stay on the ground: a taller / flatter body moves its centre up / down.
    float cy = uBody.x * uShape.y, rx = uBody.y * uShape.x, ry = uBody.z * uShape.y;
    float boxy = uShape.z, jag = uShape.w;
    float above = max(h - cy, 0.0);                 // height above the body centre
    float x0 = x;                                   // unbent x (for the side flares)

    // Lean + wind bend the upper flame; the feet stay put.
    float bendAmt = above * above * 0.32;
    x -= uSway * above * 0.55 + bendAmt * clamp(-uWind.x * 0.18, -0.9, 0.9);

    // Rising, domain-warped noise. Coordinates are stretched vertically so features become
    // tall tongues; the time axis makes the pattern evolve instead of just scrolling.
    float t = uTime;
    vec3 p = vec3(x * 1.6, h * 0.75 - t * 1.45 + uWind.y * 0.1, t * 0.3 + uSeed);
    vec3 warp = vec3(gnoise(p * 0.7 + vec3(3.1, 0.0, 1.7)), gnoise(p * 0.7 + vec3(-5.2, 2.4, 0.3)),
                     0.0);
    float n = fbm(p + warp * (0.5 + 0.2 * uWild));

    // Base shape: body (a superellipse: round, or boxy when ``boxy`` grows; approximate signed
    // distance) + teardrop cone above it.
    float bx = rx * (1.0 + 0.02 * uBreath), by = ry * (1.0 - 0.02 * uBreath);
    vec2 q = vec2(x / bx, (h - cy) / by);
    float pw = 2.0 + 2.6 * boxy;
    vec2 aq = abs(q) + 1e-5;
    float lq = pow(pow(aq.x, pw) + pow(aq.y, pw), 1.0 / pw);
    vec2 gq = pow(aq, vec2(pw - 1.0)) / pow(max(lq, 1e-4), pw - 1.0);
    float gradLen = length(vec2(gq.x / bx, gq.y / by));
    float dBody = (lq - 1.0) / max(gradLen, 1e-4);
    float tipH = (2.1 + 0.5 * uFlare) * uFlame;   // cone height above the body centre
    float k = clamp(above / tipH, 0.0, 1.0);
    float halfW = rx * (1.02 + 0.08 * boxy) * pow(1.0 - k, 0.7 - 0.4 * boxy);
    float dCone = max((abs(x) - halfW) * 0.9 + max(above - tipH, 0.0), cy - h);
    float d = smin(dBody, dCone, 0.35);
    float armMask = 0.0;
    if (uArms.x > 0.01) {
        vec2 p = vec2(x0, h);
        float dArm = min(sideFlare(p, -1.0, cy, rx, uArms.x, uArms.y, uArms.z),
                         sideFlare(p, 1.0, cy, rx, uArms.x, uArms.y + 1.7, uArms.z));
        armMask = smoothstep(0.35, -0.1, dArm) * uArms.x;
        d = smin(d, dArm, 0.2);
    }

    // Heat: inside positive. Noise is gentle on the body and strong high up.
    float lift = smoothstep(cy - 0.1, cy + 1.0, h);
    float rim = smoothstep(0.32, 0.04, -d);         // only the outer skin of the body
    float amp = 0.04 + (0.55 + 0.15 * uWild + 0.15 * jag) * lift * (1.0 - 0.9 * armMask)
              + 0.3 * jag * rim * (1.0 - lift);
    // Ridged noise stretched upward: tall, pointed tongues separated by gaps.
    float rx2 = (x + 0.22 * n) * 1.75;             // wiggle the tongues with the other noise
    float rn = gnoise(vec3(rx2, h * 0.7 - t * 1.25, t * 0.27 + uSeed * 1.3));
    float ridge = 1.0 - pow(abs(rn) * 1.15, 1.4);  // broad tongues, narrower gaps between them
    ridge = pow(max(ridge, 0.0), 1.0 + 0.8 * k);   // tongues get thinner higher up -> pointed tips
    float edge = smoothstep(0.75, 0.2, -d);        // carve near the silhouette, not deep inside
    float crown = smoothstep(cy + 0.15, cy + 0.9, h);
    // Ragged (bursting) fire: tongues all around the sides too, not only on top.
    float carve = max(crown * edge, jag * smoothstep(0.15, 0.6, h) * 0.85 * rim)
                * (1.0 - armMask);   // arms stay smooth (no flame tongues on them)
    float wobble = amp * n * 1.5 + carve * (ridge - 0.62) * (0.85 + 0.2 * uWild) - 0.05 * lift;
    // No holes in the body: deep inside, the noise may thin the fire but never punch through
    // (sticker art has one clean silhouette). Up in the crown, gaps between tongues are allowed.
    float gaps = max(smoothstep(cy + 0.9, cy + 1.8, h), jag) * (1.0 - armMask);
    // A blend (not a clamp that fades out), so the heat never flattens onto zero, which would
    // draw stray outline threads.
    float heat = -d + wobble;
    // The floor is continuous and never flat: a quarter of the depth inside, steeply negative
    // outside (so it never props up empty space around the body).
    float floorHeat = d < 0.0 ? -0.25 * d : -4.0 * d;
    heat = mix(max(heat, floorHeat), heat, gaps);
    // Taper off before the edges of the drawing area, so a tall flame never ends in a cut line.
    heat -= 2.5 * (smoothstep(uRange.w - 0.4, uRange.w - 0.05, h)
                   + smoothstep(uRange.y - 0.35, uRange.y - 0.05, abs(x0)));

    // Bands: on the body they match the shared insets; higher up the inner bands need more heat,
    // so tongues get red tips, an orange middle and a yellow base.
    float top = smoothstep(cy + 0.35, cy + 1.6, h);
    float lvMid = uInsets.x + 0.06 * top;
    float lvInner = uInsets.y + 0.15 * top;

    // Pixel-space distances (divide by the gradient so the outline keeps a constant width).
    float g = max(length(vec2(dFdx(heat), dFdy(heat))), 1e-5);
    float dOuter = heat / g;
    float cov = clamp(dOuter + uOutlinePx * 0.5 + 0.5, 0.0, 1.0);       // outline outer edge
    float fill = clamp(dOuter - uOutlinePx * 0.5 + 0.5, 0.0, 1.0);      // outline inner edge
    vec3 col = uOuter;
    col = mix(col, uMid, clamp((heat - lvMid) / g + 0.5, 0.0, 1.0));
    col = mix(col, uInner, clamp((heat - lvInner) / g + 0.5, 0.0, 1.0));
    col = mix(uInk, col, fill);
    fragColor = vec4(col * cov, cov);
}
"""


class ShaderFlame(ImageFlame):
    """Flame body drawn by the GLSL shader above into an offscreen framebuffer."""

    name = "shader"
    X_RANGE = (-3.0, 3.0)   # wide enough for side flares and puffed-up bodies
    Y_RANGE = (-4.4, 0.25)

    def __init__(self, R: float, rng: random.Random) -> None:
        """Create the GL context, framebuffer and shader program; raises if GL 3.3 fails."""
        super().__init__(R, rng)
        fmt = QSurfaceFormat()
        fmt.setVersion(3, 3)
        fmt.setProfile(QSurfaceFormat.OpenGLContextProfile.CoreProfile)
        self._ctx = QOpenGLContext()
        self._ctx.setFormat(fmt)
        if not self._ctx.create() or self._ctx.format().version() < (3, 3):
            raise RuntimeError("OpenGL 3.3 context unavailable")
        self._surface = QOffscreenSurface()
        self._surface.setFormat(self._ctx.format())
        self._surface.create()
        if not self._ctx.makeCurrent(self._surface):
            raise RuntimeError("cannot make the OpenGL context current")
        try:
            self._gl = self._ctx.functions()
            self._fbo = QOpenGLFramebufferObject(self.img_w, self.img_h)
            prog = QOpenGLShaderProgram()
            if not prog.addShaderFromSourceCode(QOpenGLShader.ShaderTypeBit.Vertex, _VERTEX_SHADER):
                raise RuntimeError(prog.log())
            if not prog.addShaderFromSourceCode(QOpenGLShader.ShaderTypeBit.Fragment,
                                                _FRAGMENT_SHADER):
                raise RuntimeError(prog.log())
            prog.bindAttributeLocation("pos", 0)
            if not prog.link():
                raise RuntimeError(prog.log())
            self._prog = prog
            self._vao = QOpenGLVertexArrayObject()
            self._vao.create()
            self._vao.bind()
            self._vbo = QOpenGLBuffer()
            self._vbo.create()
            self._vbo.bind()
            quad = struct.pack("8f", -1, -1, 1, -1, -1, 1, 1, 1)
            self._vbo.allocate(quad, len(quad))
            prog.bind()
            prog.enableAttributeArray(0)
            prog.setAttributeBuffer(0, _GL_FLOAT, 0, 2)
            self._vao.release()
        finally:
            self._ctx.doneCurrent()
        self._seed_offset = rng.uniform(0.0, 500.0)
        self._flare = 0.0
        self._colors: FlameColors | None = None
        self._last_rgb: tuple | None = None

    def flare(self, strength: float = 1.0) -> None:
        """Push the cone taller for a moment; the noise turns it into a burst of tongues."""
        self._flare = min(1.4, self._flare + strength)

    def step(self, drive: FlameDrive) -> None:
        """Render one frame on the GPU and read it back into ``self.image``."""
        self._flare *= math.exp(-2.6 * drive.dt)
        self._drive = drive
        self._dirty = True

    def paint(self, painter, colors: FlameColors) -> None:
        """Render with this frame's colours (the shader bakes them in), then blit. Repaints
        without a new ``step()`` reuse the last frame."""
        if getattr(self, "_dirty", False):
            self._dirty = False
            self._render(colors)
        super().paint(painter, colors)

    def _render(self, colors: FlameColors) -> None:
        """Draw the shader quad into the framebuffer and copy the result to ``self.image``."""
        drive = getattr(self, "_drive", None)
        if drive is None:
            return
        if not self._ctx.makeCurrent(self._surface):
            return
        try:
            prog = self._prog
            self._fbo.bind()
            gl = self._gl
            gl.glViewport(0, 0, self.img_w, self.img_h)
            gl.glClearColor(0.0, 0.0, 0.0, 0.0)
            gl.glClear(_GL_COLOR_BUFFER_BIT)
            prog.bind()
            prog.setUniformValue("uSize", float(self.img_w), float(self.img_h))
            prog.setUniformValue("uRange", self.X_RANGE[0], self.X_RANGE[1],
                                 -self.Y_RANGE[1], -self.Y_RANGE[0])
            prog.setUniformValue1f("uTime", float(drive.clock % 10000.0))
            prog.setUniformValue1f("uSeed", float(self._seed_offset))
            prog.setUniformValue1f("uFlame", float(drive.flame))
            prog.setUniformValue1f("uWild", float(drive.wild))
            prog.setUniformValue1f("uSway", float(drive.sway))
            prog.setUniformValue("uWind", float(drive.wind_x), float(drive.wind_y))
            prog.setUniformValue1f("uBreath", float(drive.breath))
            prog.setUniformValue1f("uFlare", float(self._flare))
            prog.setUniformValue1f("uPxPerR", float(self.R * self.SUPERSAMPLE))
            prog.setUniformValue1f("uOutlinePx", float(colors.outline_px * self.SUPERSAMPLE))
            for name, c in (("uOuter", colors.outer), ("uMid", colors.mid),
                            ("uInner", colors.inner), ("uInk", colors.ink)):
                prog.setUniformValue(name, c.redF(), c.greenF(), c.blueF())
            prog.setUniformValue("uBody", BODY_CY, BODY_RX, BODY_RY)
            prog.setUniformValue("uInsets", MID_INSET, INNER_INSET)
            prog.setUniformValue("uShape", float(drive.body_w), float(drive.body_h),
                                 float(drive.boxy), float(drive.jag))
            prog.setUniformValue("uArms", float(drive.arms), float(drive.arms_phase),
                                 float(drive.arms_flap), 0.0)
            self._vao.bind()
            gl.glDrawArrays(_GL_TRIANGLE_STRIP, 0, 4)
            self._vao.release()
            self.image = self._fbo.toImage(True)
            self._fbo.release()
        finally:
            self._ctx.doneCurrent()
        bits = np.frombuffer(self.image.constBits(), dtype=np.uint8)
        stride = self.image.bytesPerLine()
        alpha = bits.reshape(self.img_h, stride)[:, 3:self.img_w * 4:4]
        self._update_top_points(alpha)
