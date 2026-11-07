"""Web Motion Lab — six new 1920x1080 animation grammars.

These shots are deliberately outside the existing families (34-shot pod, 24
marker variants, 10 Claude-Code shots, 12 motion classics). Each one introduces
a different motion idea and is authored with the shared ``web_shot_kit``:

  lab_aperture_scan      a bright 220 px aperture sweeps the page and reveals
                         the headline inside the slit
  lab_split_flap         four mechanical character cells settle on 2026
  lab_halftone_dissolve  a 16x9 dot veil dissolves in a diagonal wave
  lab_ink_bloom          four translucent marker strokes bloom with a wet edge
  lab_parallax_depth     three cards on different planes drift at different
                         speeds over a giant ghost word
  lab_slice_glitch       horizontal slices and RGB fringe reacquire the signal

Every clip is 6.0 s at 30 fps (180 frames), H.264, 1920x1080 — inside the
10-second ceiling requested for the delivery. The C++ counterpart lives in
``include/chronontemplate/web/WebMotionLabPack.hpp``; this module is the
delivery renderer, exactly like ``shots_next.py`` for WebShotsNextPack.
"""

from __future__ import annotations

import math
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from web_shot_kit import Canvas, Shot

W, H = 1920, 1080
FPS = 30
SECONDS = 6.0

INK = "#F4EFE7"
MUTED = "#8E8A82"
ACCENT = "#E4572E"
AMBER = "#E8871E"
ACID = "#E6E300"
CYAN = "#67B9D4"


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


def _ease(t: float) -> float:
    t = _clamp(t)
    return t * t * (3.0 - 2.0 * t)


def _sweep(t: float, t0: float = 0.08, t1: float = 0.60) -> float:
    if t <= t0:
        return 0.0
    if t >= t1:
        return 1.0
    return _ease((t - t0) / (t1 - t0))


def _burst(t: float, center: float, half_width: float) -> float:
    return _clamp(1.0 - abs(t - center) / half_width)


def _alpha(value: float, at: float = 1.0) -> float:
    return _clamp(value) * at


# --------------------------------------------------------------------------- #
# 1. Aperture scan
# --------------------------------------------------------------------------- #

def shot_lab_aperture_scan() -> Shot:
    head = "The frame remembers what the eye forgets"
    highlight = "remembers"

    def back(c: Canvas) -> None:
        c.rect(0, 0, W, H, "#0B0D10")
        for i in range(9):
            c.rect(90, 150 + i * 96, 1740, 1, INK, 0.035)
        c.text(120, 92, "MOTION LAB / APERTURE", 22, "oswald-bold", ACCENT)
        c.text(1800, 96, "SCAN 06  ·  1920 x 1080", 18, "sans", MUTED, anchor="ra")
        # The dim copy is the page before the slit arrives.
        c.text(150, 380, head, 76, "helv-bold", INK, alpha=0.13)
        c.text(150, 560, "APERTURE / SIX-SECOND SCAN", 28, "sans", MUTED)
        c.rect(150, 984, 1620, 2, INK, 0.18)
        c.text(150, 1006, "CHRONON / MOTION LAB · EXPERIMENT 01", 16, "oswald", MUTED)
        c.noise(0.010, seed=4101)
        c.vignette(0.28, 0.66)

    cache: dict[str, Image.Image] = {}

    def bright() -> Image.Image:
        if "img" not in cache:
            layer = Canvas()
            prefix = head[: head.index(highlight)]
            hx = 150 + layer.measure(prefix, 76, "helv-bold")
            hw = layer.measure(highlight, 76, "helv-bold")
            layer.marker(hx - 12, 468, hw + 26, 88, ACCENT, alpha=0.55, seed=12)
            layer.text(150, 380, head, 76, "helv-bold", INK)
            cache["img"] = layer.img
        return cache["img"]

    def anim(c: Canvas, t: float) -> None:
        scan = _ease(_clamp((t - 0.03) / 0.90))
        band_top = -240.0 + scan * (H + 500.0)
        band_h = 250.0
        y0, y1 = max(-320.0, band_top), min(H + 320.0, band_top + band_h)
        if y1 <= 0 or y0 >= H:
            return
        c.rect(0, y0, W, y1 - y0, INK, 0.035)
        s = c.ss
        bx0, bx1 = 0, int(W * s)
        by0, by1 = int(max(0.0, y0) * s), int(min(H, y1) * s)
        if by1 > by0:
            crop = bright().crop((bx0, by0, bx1, by1))
            c.img.alpha_composite(crop, (bx0, by0))
        c.rect(0, y1, W, 2, ACCENT, 0.92)
        c.rect(0, y0, W, 1, INK, 0.35)
        c.text(120, max(8.0, y0 - 26), "APERTURE 220 px", 17, "oswald", ACCENT)

    shot = Shot(
        name="lab_aperture_scan",
        source="native recipe (WebMotionLabPack::ApertureScan)",
        seconds=SECONDS,
        still_t=0.42,
        description="A bright aperture sweeps the page and reveals the headline",
        cam_from=(1.0, 0.5, 0.5), cam_to=(1.03, 0.5, 0.5),
        grain=0.010, vig=0.26,
        build_static=back, draw_anim=anim,
    )
    return shot


# --------------------------------------------------------------------------- #
# 2. Split flap
# --------------------------------------------------------------------------- #

def shot_lab_split_flap() -> Shot:
    digits = ("2", "0", "2", "6")
    ghosts = ("9", "4", "8", "3")
    labels = ("REV", "SIG", "NOW", "06")

    def draw_full(c: Canvas, t: float) -> None:
        c.rect(0, 0, W, H, "#0A0908")
        c.noise(0.012, seed=4202)
        c.vignette(0.30, 0.62)
        c.text(120, 92, "CHRONON / DEPARTURES", 22, "oswald-bold", AMBER)
        c.text(1800, 96, "SIGNAL BOARD 06", 18, "sans", MUTED, anchor="ra")

        for i, (digit, ghost, label) in enumerate(zip(digits, ghosts, labels)):
            x = 355 + i * 310
            cx = x + 140
            c.rect(x, 240, 280, 430, "#15130F")
            c.rect(x, 240, 280, 2, INK, 0.14)
            c.rect(x, 452, 280, 2, INK, 0.16)
            p = _clamp((t - (0.06 + i * 0.09)) / 0.24)
            settled = _ease(p)
            c.text(cx, 452, ghost, 210, "anton", INK, alpha=0.08 * (1.0 - p), anchor="mm")
            if 0.0 < p < 1.0:
                c.rect(x, 242, 280, 3, AMBER, 0.85)
            size = 230 * (0.38 + 0.62 * settled)
            c.text(cx, 452 + 72 * (1.0 - settled), digit, size, "anton", INK,
                   alpha=min(1.0, p * 2.0), anchor="mm")
            c.text(cx, 700, label, 18, "oswald", MUTED, anchor="ma")

        rule = _sweep(t, 0.56, 0.78)
        if rule > 0:
            c.rect(355, 724, 1210 * rule, 4, AMBER, 0.9)
        c.text(150, 780, "FIELD NOTES LAND AT 20:26", 40, "oswald-bold", INK)
        c.text(150, 840, "DEPARTURES / SIGNAL BOARD 06", 24, "sans", MUTED)
        c.text(150, 1006, "FLAP / LOCKED  ·  CHRONON MOTION LAB", 16, "oswald", MUTED)

    return Shot(
        name="lab_split_flap",
        source="native recipe (WebMotionLabPack::SplitFlap)",
        seconds=SECONDS,
        still_t=0.86,
        description="Four mechanical character cells settle on 2026",
        cam_from=(1.0, 0.5, 0.5), cam_to=(1.02, 0.5, 0.5),
        grain=0.012, vig=0.28,
        draw_full=draw_full,
    )


# --------------------------------------------------------------------------- #
# 3. Halftone dissolve
# --------------------------------------------------------------------------- #

def shot_lab_halftone_dissolve() -> Shot:
    head = "Attention is a finite resource"
    cols, rows = 16, 9
    left, top = 90.0, 110.0
    cell_w, cell_h = 1740.0 / cols, 890.0 / rows

    def draw_full(c: Canvas, t: float) -> None:
        c.rect(0, 0, W, H, "#F2EFE8")
        c.noise(0.008, seed=4303)
        c.text(120, 92, "MOTION LAB / HALFTONE", 22, "oswald-bold", ACCENT)
        c.text(1800, 96, "DOT MATRIX 16 x 9", 18, "sans", "#6E6A62", anchor="ra")
        c.text(120, 330, head, 88, "serif-bold", "#121110")
        c.rect(120, 470, 440 * _sweep(t, 0.12, 0.48), 6, ACCENT, 0.95)
        c.text(120, 510, "A PAGE MADE OF DOTS", 27, "sans", "#55514A")

        for row in range(rows):
            for col in range(cols):
                start = 0.02 + (row + col) * 0.022
                p = _clamp((t - start) / 0.26)
                scale = 1.0 - _ease(p)
                if scale <= 0.012:
                    continue
                w, h = cell_w * 0.84 * scale, cell_h * 0.82 * scale
                x = left + col * cell_w + (cell_w - w) * 0.5
                y = top + row * cell_h + (cell_h - h) * 0.5
                c.ellipse(x, y, w, h, "#14110D")

        c.text(120, 930, "FINITE / 06", 24, "oswald", ACCENT)
        c.text(150, 1006, "CHRONON / MOTION LAB  ·  EXPERIMENT 03", 16, "oswald",
               "#6E6A62")

    return Shot(
        name="lab_halftone_dissolve",
        source="native recipe (WebMotionLabPack::HalftoneDissolve)",
        seconds=SECONDS,
        still_t=0.62,
        description="A 16x9 dot veil dissolves in a diagonal wave",
        cam_from=(1.0, 0.5, 0.5), cam_to=(1.02, 0.5, 0.5),
        grain=0.008, vig=0.14,
        draw_full=draw_full,
    )


# --------------------------------------------------------------------------- #
# 4. Ink bloom
# --------------------------------------------------------------------------- #

def shot_lab_ink_bloom() -> Shot:
    head = "The story bleeds through the page"
    highlight = "bleeds through"
    size = 86

    def back(c: Canvas) -> None:
        c.rect(0, 0, W, H, "#EFEAE1")
        c.noise(0.009, seed=4404)
        c.vignette(0.18, 0.70)
        c.text(120, 92, "MOTION LAB / INK BLOOM", 22, "oswald-bold", ACCENT)
        c.text(150, 1006, "WET EDGE / 06  ·  CHRONON MOTION LAB", 16, "oswald",
               "#6E6A62")

    def front(c: Canvas) -> None:
        c.text(180, 436, head, size, "serif-bold", "#151310")
        c.text(180, 610, "WET EDGE / MARKER STUDY", 28, "sans", "#5E594F")
        c.rect(180, 680, 820, 3, "#151310", 0.7)

    cache: dict[str, Image.Image] = {}

    def bloom() -> Image.Image:
        if "img" in cache:
            return cache["img"]
        layer = Canvas()
        prefix = head[: head.index(highlight)]
        hx = 180 + layer.measure(prefix, size, "serif-bold")
        hw = layer.measure(highlight, size, "serif-bold") + 30
        layer.marker(hx - 18, 430, hw + 24, 112, ACID, alpha=0.50, seed=44)
        layer.marker(hx + 6, 438, hw + 14, 94, "#E8DC4A", alpha=0.42, seed=71)
        layer.marker(hx - 6, 446, hw + 4, 100, "#F2C500", alpha=0.34, seed=97)
        for i in range(7):
            layer.ellipse(hx - 26 + (i * 173) % int(hw + 60),
                          424 + (i * 53) % 120,
                          10 + (i % 3) * 6, 8 + (i % 4) * 4, ACID, 0.35)
        cache["img"] = layer.img.filter(ImageFilter.GaussianBlur(9))
        return cache["img"]

    def anim(c: Canvas, t: float) -> None:
        reveal = _ease(_clamp(t / 0.68))
        if reveal <= 0.0:
            return
        s = c.ss
        tex = bloom()
        if tex.size != c.img.size:
            tex = tex.resize(c.img.size, Image.LANCZOS)
        arr = np.array(tex)
        alpha = arr[:, :, 3].astype(np.float32) / 255.0
        xs = np.arange(arr.shape[1], dtype=np.float32)
        front = (120.0 + reveal * 1460.0) * s
        ramp = np.clip((front - xs) / (90.0 * s), 0.0, 1.0)
        arr[:, :, 3] = (alpha * ramp * 255.0).astype(np.uint8)
        c.img.alpha_composite(Image.fromarray(arr, "RGBA"))
        c.draw = ImageDraw.Draw(c.img, "RGBA")

    return Shot(
        name="lab_ink_bloom",
        source="native recipe (WebMotionLabPack::InkBloom)",
        seconds=SECONDS,
        still_t=0.82,
        description="Four marker strokes bloom with a wet edge behind the headline",
        cam_from=(1.0, 0.5, 0.5), cam_to=(1.02, 0.5, 0.5),
        grain=0.009, vig=0.16,
        build_static=back, build_static_front=front, draw_anim=anim,
    )


# --------------------------------------------------------------------------- #
# 5. Parallax depth
# --------------------------------------------------------------------------- #

def shot_lab_parallax_depth() -> Shot:
    titles = ("FOREGROUND", "MIDGROUND", "BACKGROUND")
    numbers = ("01", "02", "03")
    bodies = ("the subject", "the context", "the field")
    panels = ("#2C3A46", "#222C36", "#1A222A")
    accents = (ACCENT, ACID, CYAN)
    base_x = (1100.0, 640.0, 180.0)  # front to back

    def draw_full(c: Canvas, t: float) -> None:
        c.rect(0, 0, W, H, "#0E1216")
        c.noise(0.011, seed=4505)
        c.vignette(0.34, 0.62)
        c.text(60, 70, "DEPTH", 300, "oswald-bold", INK, alpha=0.05)

        for i in range(12):
            c.ellipse(120 + (i * 317) % 1680, 180 + (i * 211) % 620, 3, 3, INK, 0.18)

        # Back to front: the deepest card moves least, the foreground most.
        for depth in (2, 1, 0):
            shift = (-1.0 + 2.0 * _ease(t)) * (58.0 + depth * 44.0)
            intro = (1.0 - _ease(_clamp(t / 0.45))) * 260.0 * (depth + 1)
            x = base_x[depth] + shift + intro
            y = 392.0 + depth * 22.0
            w, h = 470.0, 330.0
            c.rect(x + 18, y + 22, w, h, "#000000", 0.34, radius=18)
            c.rect(x + 36, y + 44, w, h, "#000000", 0.16, radius=18)
            c.rect(x, y, w, h, panels[depth], 1.0, radius=16)
            c.rect(x, y, w, 4, accents[depth], 0.95)
            c.text(x + 34, y + 36, numbers[depth], 46, "oswald-bold", accents[depth])
            c.text(x + 34, y + 100, titles[depth], 26, "oswald", INK)
            c.text(x + 34, y + 160, bodies[depth], 34, "serif-bold", "#C9C2B6")
            c.rect(x + 34, y + 250, 180, 3, accents[depth], 0.72)

        c.text(120, 92, "MOTION LAB / PARALLAX", 22, "oswald-bold", ACCENT)
        c.text(1800, 96, "THREE PLANES  ·  ONE FRAME", 18, "sans", MUTED, anchor="ra")
        c.text(120, 880, "Three planes, one frame", 42, "serif-bold", INK)
        c.text(120, 940, "DEPTH / MOTION STUDY", 22, "sans", MUTED)

    return Shot(
        name="lab_parallax_depth",
        source="native recipe (WebMotionLabPack::ParallaxDepth)",
        seconds=SECONDS,
        still_t=0.80,
        description="Three cards on different planes drift at different speeds",
        cam_from=(1.0, 0.5, 0.5), cam_to=(1.025, 0.5, 0.5),
        grain=0.011, vig=0.30,
        draw_full=draw_full,
    )


# --------------------------------------------------------------------------- #
# 6. Slice glitch
# --------------------------------------------------------------------------- #

def shot_lab_slice_glitch() -> Shot:
    def draw_full(c: Canvas, t: float) -> None:
        c.rect(0, 0, W, H, "#07090B")
        c.noise(0.014, seed=4606)
        c.vignette(0.38, 0.58)
        for i in range(8):
            c.rect(90, 120 + i * 120, 1740, 1, INK, 0.045)

        c.text(110, 82, "TRANSMISSION / RECOVERY", 22, "oswald-bold", CYAN)
        c.ellipse(1772, 88, 12, 12, ACCENT)
        c.text(1798, 82, "LIVE", 18, "oswald", MUTED)

        glitch = max(_burst(t, 0.16, 0.075),
                     _burst(t, 0.40, 0.065) * 0.85,
                     _burst(t, 0.64, 0.055) * 0.70)
        amp = 30.0 * glitch

        # RGB fringe under the two headline runs.
        for dx, dy, color, alpha in ((-8, -4, "#FF3B30", 0.45),
                                     (8, 4, CYAN, 0.38)):
            c.text(110 + dx, 255 + dy, "SIGNAL", 200, "oswald-bold", color, alpha=alpha)
            c.text(115 + dx, 483 + dy, "RECOVERED", 118, "oswald-bold", color,
                   alpha=alpha)
        c.text(110, 255, "SIGNAL", 200, "oswald-bold", INK)
        c.text(115, 483, "RECOVERED", 118, "oswald-bold", INK)

        # Horizontal slices: the renderer can't clip a text run, so the delivery
        # renderer displaces whole scanline bands of the composed frame.
        if amp > 0.4:
            arr = np.array(c.img)
            rng = np.random.default_rng(int(t * 1000) + 7)
            s = c.ss
            top, bottom = int(220 * s), int(700 * s)
            for _ in range(9):
                y0 = int(rng.integers(top, bottom - int(30 * s)))
                height = int(rng.integers(int(8 * s), int(38 * s)))
                shift = int(rng.integers(-int(amp), int(amp) + 1) * s)
                if shift:
                    arr[y0:y0 + height, :, :] = np.roll(
                        arr[y0:y0 + height, :, :], shift, axis=1)
            c.img = Image.fromarray(arr, "RGBA")
            c.draw = ImageDraw.Draw(c.img, "RGBA")
            for i in range(4):
                y = 300 + i * 110 + (i * 37) % 80
                c.rect(110, y, 820, 8, INK, 0.10 * glitch)

        c.rect(115, 650, 920 * _sweep(t, 0.70, 0.94), 5, CYAN, 0.85)
        c.text(115, 690, "TRANSMISSION / RECOVERY", 28, "sans", MUTED)
        c.rect(0, 986, W, 44, "#101418", 1.0)
        c.text(36, 997, "SIGNAL LOCKED  /  SLICE 06  /  CHRONON MOTION LAB  /  ",
               17, "oswald", CYAN)

    return Shot(
        name="lab_slice_glitch",
        source="native recipe (WebMotionLabPack::SliceGlitch)",
        seconds=SECONDS,
        still_t=0.88,
        description="Horizontal slices and RGB fringe reacquire the signal",
        cam_from=(1.0, 0.5, 0.5), cam_to=(1.02, 0.5, 0.5),
        grain=0.014, vig=0.32,
        draw_full=draw_full,
    )


BUILDERS = (
    shot_lab_aperture_scan,
    shot_lab_split_flap,
    shot_lab_halftone_dissolve,
    shot_lab_ink_bloom,
    shot_lab_parallax_depth,
    shot_lab_slice_glitch,
)


def all_motion_lab_shots() -> list[Shot]:
    return [build() for build in BUILDERS]


def motion_lab_names() -> list[str]:
    return [shot.name for shot in all_motion_lab_shots()]


if __name__ == "__main__":
    for shot in all_motion_lab_shots():
        print(shot.name, "|", shot.description)
    print(len(BUILDERS), "shots")
