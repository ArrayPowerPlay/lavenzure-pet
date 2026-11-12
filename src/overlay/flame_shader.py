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

- Reading the picture back is the expensive part: waiting for the GPU and converting the pixels
  took ~6 ms of the ~10 ms frame. On Windows the read therefore goes through two pixel-pack
  buffers (``_AsyncReadback``): each frame asks the GPU to copy the new picture into one buffer
  without waiting, and takes the *previous* frame's picture out of the other one, already in
  ``QImage``'s byte order. The flame is shown one frame (~16 ms) late, which is invisible, and
  the frame costs ~1 ms instead. Elsewhere (or if setting it up fails) the simple synchronous
  ``toImage()`` read is used.

If OpenGL 3.3 is not available (old driver, some remote-desktop sessions) the constructor raises
and ``make_flame_renderer`` falls back to the metaball renderer.
"""
from __future__ import annotations

import ctypes
import logging
import math
import random
import struct
import sys

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
_GL_BGRA = 0x80E1           # byte order B, G, R, A = QImage ARGB32 on little-endian machines
_GL_UNSIGNED_BYTE = 0x1401

log = logging.getLogger(__name__)

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
uniform vec4 uPaws;        // on the log: amount 0..1, kneading phase, seat height (R), -

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

// Distance to one paw (reference fig. 4): a short, soft, round-bottomed blob hanging from the
// seated body down over the front of the log. ``side`` is -1 (left) or 1 (right); the paws
// knead slowly, each pressing in turn (a pressed paw is a little wider and shorter).
float paw(vec2 p, float side, float rx, float seat, float grow, float phase) {
    float press = 0.5 + 0.5 * sin(phase + (side > 0.0 ? 2.1 : 0.0));
    float halfW = (0.2 + 0.015 * press) * grow;
    float depth = (0.34 - 0.025 * press) * grow;
    vec2 a = vec2(side * 0.55 * rx, seat + 0.2);              // starts inside the body
    vec2 b = vec2(a.x, seat - depth + halfW);                 // round bottom over the log
    vec2 q = p - a;
    vec2 ab = b - a;
    float t = clamp(dot(q, ab) / max(dot(ab, ab), 1e-6), 0.0, 1.0);
    vec2 r = q - ab * t;
    // A touch wider toward the bottom, like a mitten resting on the log.
    float w = halfW * (1.0 + 0.08 * t);
    return length(vec2(r.x * 0.95, r.y)) - w;
}

void main() {
    vec2 uv = gl_FragCoord.xy / uSize;
    float x = mix(uRange.x, uRange.y, uv.x);
    float h = mix(uRange.z, uRange.w, uv.y);       // height above the feet (R)
    // The feet stay on the ground: a taller / flatter body moves its centre up / down.
    float cy = uBody.x * uShape.y, rx = uBody.y * uShape.x, ry = uBody.z * uShape.y;
    float boxy = uShape.z, jag = uShape.w;
    float above = max(h - cy, 0.0);                 // height above the body centre
    float x0 = x;                                   // unbent x (for the paws)

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
    // Sitting on the log, the body's weight spreads its lower half a little (fig. 4: a wide
    // bottom resting on the log, not a narrow point).
    bx *= 1.0 + 0.12 * clamp(uPaws.x, 0.0, 1.0) * (1.0 - smoothstep(cy - ry, cy, h));
    vec2 q = vec2(x / bx, (h - cy) / by);
    float pw = 2.0 + 2.6 * boxy;
    vec2 aq = abs(q) + 1e-5;
    float lq = pow(pow(aq.x, pw) + pow(aq.y, pw), 1.0 / pw);
    vec2 gq = pow(aq, vec2(pw - 1.0)) / pow(max(lq, 1e-4), pw - 1.0);
    float gradLen = length(vec2(gq.x / bx, gq.y / by));
    float dBody = (lq - 1.0) / max(gradLen, 1e-4);
    // Deep inside, a boxy superellipse's distance estimate breaks down at the very centre (one
    // pixel in the middle of the face got a stray outline speck); there a plain ellipse
    // estimate is used instead - only the rim needs the exact shape.
    float dEll = (length(q) - 1.0) * min(bx, by);
    dBody = mix(dEll, dBody, smoothstep(0.25, 0.55, lq));
    float tipH = (2.1 + 0.5 * uFlare) * uFlame;   // cone height above the body centre
    float k = clamp(above / tipH, 0.0, 1.0);
    float halfW = rx * pow(1.0 - k, 0.7);
    float dCone = max((abs(x) - halfW) * 0.9 + max(above - tipH, 0.0), cy - h);
    float d = smin(dBody, dCone, 0.35);
    // Sitting on the log (reference fig. 4): the body settles over the log (the log is drawn
    // behind the fire) - its bottom edge sags a little over the log's front, and two round paws
    // hang from it lower down. Body, sag and paws are one shape joined with wide, soft fillets,
    // and down there the fire is all yellow core right to the outline (the red / orange bands
    // fade out toward the log, see ``drape`` below), so the paws read as the body itself
    // flowing over the log, not as separate drips.
    float pawMask = 0.0;
    float drape = 0.0;          // 1 where the body rests on / hangs over the log
    float dCut = 0.0;           // how much the cut along the log moved the outline inward
    if (uPaws.x > 0.01) {
        vec2 p = vec2(x0, h);
        float seat = uPaws.z;
        float dWhole = d;       // the body as if it were not cut along the log
        float across = clamp(x0 / max(rx, 0.1), -1.0, 1.0);
        float sag = 0.05 * (1.0 - across * across) * smoothstep(0.55, 1.0, uPaws.x);
        d = mix(d, -smin(-d, -(seat - sag - h), 0.1), uPaws.x);
        float grow = smoothstep(0.55, 1.0, uPaws.x);
        float dPaw = min(paw(p, -1.0, rx, seat, grow, uPaws.y),
                         paw(p, 1.0, rx, seat, grow, uPaws.y));
        pawMask = smoothstep(0.4, -0.05, dPaw) * grow;
        d = smin(d, dPaw, 0.11);
        dCut = max(d - smin(dWhole, dPaw, 0.11), 0.0);
        // The side bands run down to the log; below its top the fire is all yellow core.
        drape = uPaws.x * (1.0 - smoothstep(seat - 0.04, seat + 0.14, h));
    }

    // Heat: inside positive. Noise is gentle on the body and strong high up.
    float lift = smoothstep(cy - 0.1, cy + 1.0, h);
    float rim = smoothstep(0.32, 0.04, -d);         // only the outer skin of the body
    float amp = (0.04 + (0.55 + 0.15 * uWild) * lift * (1.0 - 0.6 * jag)
              + 0.03 * jag * rim * (1.0 - lift)) * (1.0 - pawMask);
    // Ridged noise stretched upward: tall, pointed tongues separated by gaps.
    float rx2 = (x + 0.22 * n) * 1.75;             // wiggle the tongues with the other noise
    float rn = gnoise(vec3(rx2, h * 0.7 - t * 1.25, t * 0.27 + uSeed * 1.3));
    float ridge = 1.0 - pow(abs(rn) * 1.15, 1.4);  // broad tongues, narrower gaps between them
    ridge = pow(max(ridge, 0.0), 1.0 + 0.8 * k);   // tongues get thinner higher up -> pointed tips
    float edge = smoothstep(0.75, 0.2, -d);        // carve near the silhouette, not deep inside
    float crown = smoothstep(cy + 0.15, cy + 0.9, h);
    // The bursting fringe below replaces these carved tongues (both together cut the fringe
    // off into floating bits).
    float carve = crown * edge * (1.0 - 0.8 * jag);
    float wobble = amp * n * 1.5 + carve * (ridge - 0.62) * (0.85 + 0.2 * uWild) - 0.05 * lift;
    // Bursting fire (``jag``: the scared look, and the fire under the pan): soft tongues of fire
    // that are born low on the sides, lick up along the silhouette and grow into the tall
    // tongues of the top corners. Nothing grows at the feet.
    if (jag > 0.01) {
        float sgn = x0 < 0.0 ? -1.0 : 1.0;
        float ang = acos(clamp(-q.y / max(length(q), 1e-4), -1.0, 1.0));   // 0 = feet, pi = top
        // Which way the body surface faces here (-1 = down, 0 = sideways, 1 = up): the upright
        // tongues of the top only grow where the surface faces up (beside the body they would
        // be loose vertical slivers), the sheared side tongues where it faces sideways.
        float nUp = normalize(vec2(gq.x * sign(q.x) / bx, gq.y * sign(q.y) / by)).y;
        float upF = smoothstep(0.35, 0.8, nUp);
        float topW = smoothstep(1.95, 2.55, ang) * upF;
        float shoulder = exp(-pow((ang - 2.15) / 0.34, 2.0)) * upF;
        float sideW = smoothstep(1.2, 1.75, ang) * (1.0 - smoothstep(0.1, 0.45, nUp));
        // Sides. Fire rises, it never sticks out sideways: the side wall is wrapped in a row of
        // tongues that scroll upward, and each tongue is sheared so that the further it reaches
        // out of the body the higher it goes - its tip always points up and out, like a flame
        // bending upward. Along every sheared line the tongue is one interval starting at the
        // body, so no loose bits ever break off. Every tongue has its own size, which breathes,
        // and the spacing is warped by noise, so the row never looks like a regular saw.
        float outside = max(d, 0.0);
        float lean = 1.6;
        float hs = h - lean * outside;
        float u = hs * 2.3 - t * 1.5 + sgn * 7.31
                + 0.45 * gnoise(vec3(hs * 1.2, t * 0.5, uSeed + sgn * 3.0));
        float cell = floor(u);
        float c = fract(u);
        float rnd = fract(sin(cell * 91.7 + sgn * 37.3 + uSeed * 0.37) * 43758.5453);
        float size = (0.5 + 0.5 * rnd) * (0.72 + 0.28 * sin(t * (1.6 + 1.8 * rnd) + rnd * 6.28));
        // One soft lobe per cell: zero (and flat) at both ends so neighbours join smoothly, a
        // rounded - not needle-sharp - tip.
        float lobe = pow(sin(3.14159 * pow(c, 0.8)), 1.4);
        float sideFire = 0.26 * size * lobe - 0.015;
        // Top: a row of taller tongues pointing straight up, each rising and falling on its own.
        // They depend on x only (not height), so a tongue is one solid spike: no loops or holes.
        float ft = gnoise(vec3(x * 2.0 + 0.25 * sin(t * 0.8), t * 1.1, uSeed + 3.7));
        float tongueTop = pow(max(1.0 - abs(ft) * 1.4, 0.0), 1.3);
        float flick = 0.7 + 0.3 * gnoise(vec3(x * 1.3, t * 1.7, uSeed + 9.0));
        // The top corners send up the tallest tongues (fig. 3 scream, fig. 7 fire licking up
        // beside the pan).
        tongueTop *= 1.0 + 1.1 * shoulder;
        topW = max(topW, shoulder);
        wobble += jag * (1.0 - pawMask)
                * (sideW * sideFire * smoothstep(0.35, 0.05, -d)
                   + topW * rim * (0.5 * tongueTop * flick - 0.1));
    }
    // No holes in the body: deep inside, the noise may thin the fire but never punch through
    // (sticker art has one clean silhouette). Up in the crown, gaps between tongues are allowed.
    // (The bursting look keeps one solid mass: no loose islands.)
    float gaps = smoothstep(cy + 0.9, cy + 1.8, h) * (1.0 - jag);
    // A blend (not a clamp that fades out), so the heat never flattens onto zero, which would
    // draw stray outline threads.
    float heat = -d + wobble;
    // The floor is continuous and never flat: a quarter of the depth inside, steeply negative
    // outside (so it never props up empty space around the body).
    float floorHeat = d < 0.0 ? -0.25 * d : -4.0 * d;
    // A *smooth* max: a hard max leaves a kink just outside the outline where the two fields
    // cross, the outline's width estimate jumps there and a thin stray arc appeared inside the
    // outline.
    heat = mix(-smin(-heat, -floorHeat, 0.06), heat, gaps);
    // Taper off before the edges of the drawing area, so a tall flame never ends in a cut line.
    heat -= 2.5 * (smoothstep(uRange.w - 0.4, uRange.w - 0.05, h)
                   + smoothstep(uRange.y - 0.35, uRange.y - 0.05, abs(x0)));

    // Bands: on the body they match the shared insets; higher up the inner bands need more heat,
    // so tongues get red tips, an orange middle and a yellow base.
    float top = smoothstep(cy + 0.35, cy + 1.6, h);
    float lvMid = uInsets.x + 0.06 * top;
    float lvInner = uInsets.y + 0.15 * top;
    // Over the log the bands thin out to nothing: yellow right up to the outline (fig. 4). The
    // bands are measured as if the body were not cut along the log (``dCut``), so no orange
    // stripe runs along the cut; only the sides keep their bands down to the log.
    lvMid = mix(lvMid, -0.02, drape);
    lvInner = mix(lvInner, -0.01, drape);
    float bandHeat = heat + dCut;

    // Pixel-space distances (divide by the gradient so the outline keeps a constant width).
    float g = max(length(vec2(dFdx(heat), dFdy(heat))), 1e-5);
    float dOuter = heat / g;
    float cov = clamp(dOuter + uOutlinePx * 0.5 + 0.5, 0.0, 1.0);       // outline outer edge
    float fill = clamp(dOuter - uOutlinePx * 0.5 + 0.5, 0.0, 1.0);      // outline inner edge
    vec3 col = uOuter;
    col = mix(col, uMid, clamp((bandHeat - lvMid) / g + 0.5, 0.0, 1.0));
    col = mix(col, uInner, clamp((bandHeat - lvInner) / g + 0.5, 0.0, 1.0));
    col = mix(uInk, col, fill);
    fragColor = vec4(col * cov, cov);
}
"""


class _AsyncReadback:
    """Copies framebuffer pictures to the CPU through two pixel-pack buffers, without stalling.

    ``read_into(image)`` starts copying the framebuffer that is bound right now into one buffer
    (returns at once) and fills ``image`` from the other buffer, which holds the picture started
    on the previous call. The very first call waits for its own picture so nothing is blank.
    Must be called with the GL context current. Windows only: PySide's ``glReadPixels`` does not
    accept a buffer offset, so the plain GL 1.1 entry point is called from ``opengl32.dll``.
    """

    def __init__(self, width: int, height: int) -> None:
        """Create both buffers (the GL context must be current); raises if anything is missing."""
        self.width, self.height = width, height
        self.size = width * height * 4
        read_pixels = ctypes.windll.opengl32.glReadPixels
        read_pixels.argtypes = [ctypes.c_int] * 4 + [ctypes.c_uint] * 2 + [ctypes.c_void_p]
        read_pixels.restype = None
        self._read_pixels = read_pixels
        self._buffers = []
        for _ in range(2):
            buffer = QOpenGLBuffer(QOpenGLBuffer.Type.PixelPackBuffer)
            if not buffer.create():
                raise RuntimeError("cannot create a pixel-pack buffer")
            buffer.setUsagePattern(QOpenGLBuffer.UsagePattern.StreamRead)
            buffer.bind()
            buffer.allocate(self.size)
            buffer.release()
            self._buffers.append(buffer)
        self._frame = 0

    def read_into(self, image) -> None:
        """Queue the current framebuffer and copy the previous one into ``image`` (same size,
        ``Format_ARGB32_Premultiplied``), flipped so row 0 is the top."""
        current = self._buffers[self._frame % 2]
        current.bind()
        self._read_pixels(0, 0, self.width, self.height, _GL_BGRA, _GL_UNSIGNED_BYTE, None)
        current.release()
        ready = current if self._frame == 0 else self._buffers[(self._frame + 1) % 2]
        self._frame += 1
        ready.bind()
        try:
            pointer = ready.mapRange(0, self.size, QOpenGLBuffer.RangeAccessFlag.RangeRead)
            if pointer is None or int(pointer) == 0:
                raise RuntimeError("cannot map the pixel-pack buffer")
            raw = (ctypes.c_uint8 * self.size).from_address(int(pointer))
            src = np.frombuffer(raw, dtype=np.uint8).reshape(self.height, self.width * 4)
            stride = image.bytesPerLine()
            dst = np.frombuffer(image.bits(), dtype=np.uint8).reshape(self.height, stride)
            dst[:, : self.width * 4] = src[::-1]   # GL rows run bottom-up
        finally:
            ready.unmap()
            ready.release()


class ShaderFlame(ImageFlame):
    """Flame body drawn by the GLSL shader above into an offscreen framebuffer."""

    name = "shader"
    X_RANGE = (-3.0, 3.0)   # wide enough for puffed-up, wind-blown bodies
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
            self._readback = self._make_readback()
        finally:
            self._ctx.doneCurrent()
        self._seed_offset = rng.uniform(0.0, 500.0)
        self._flare = 0.0
        self._colors: FlameColors | None = None
        self._last_rgb: tuple | None = None

    def _make_readback(self) -> _AsyncReadback | None:
        """The fast, non-blocking read on Windows; ``None`` (= plain ``toImage()``) elsewhere or
        if the driver refuses."""
        if sys.platform != "win32":
            return None
        try:
            return _AsyncReadback(self.img_w, self.img_h)
        except Exception as exc:  # noqa: BLE001 - any driver problem: use the simple read
            log.warning("Async flame read-back unavailable (%s); using the slower one", exc)
            return None

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
            prog.setUniformValue("uPaws", float(drive.paws), float(drive.paw_phase),
                                 float(drive.seat), 0.0)
            self._vao.bind()
            gl.glDrawArrays(_GL_TRIANGLE_STRIP, 0, 4)
            self._vao.release()
            self._read_back()
            self._fbo.release()
        finally:
            self._ctx.doneCurrent()
        bits = np.frombuffer(self.image.constBits(), dtype=np.uint8)
        stride = self.image.bytesPerLine()
        alpha = bits.reshape(self.img_h, stride)[:, 3:self.img_w * 4:4]
        self._update_top_points(alpha)

    def _read_back(self) -> None:
        """Copy the framebuffer (bound, context current) into ``self.image``."""
        if self._readback is not None:
            try:
                self._readback.read_into(self.image)
                return
            except Exception as exc:  # noqa: BLE001 - fall back for good on any driver problem
                log.warning("Async flame read-back failed (%s); using the slower one", exc)
                self._readback = None
        self.image = self._fbo.toImage(True)
