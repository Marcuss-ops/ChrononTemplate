"""Web Motion Lab — center-only cuts of the six grammars.

The first Motion Lab delivery carried editorial chrome: a kicker at the top,
a caption at the bottom, subtitles and corner labels. This variant keeps the
motion and palette of every recipe but removes all of that: one statement,
optically centered, with nothing above, below or in the corners.

Everything is still 1920x1080, 30 fps, 6.0 s. The delivery renderer is
``render_motion_lab.py --center``.
"""

from __future__ import annotations

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from shots_motion_lab import (
    ACCENT,
    ACID,
    AMBER,
    CYAN,
    H,
    INK,
    SECONDS,
    W,
    _burst,
    _clamp,
    _ease,
)
from web_shot_kit import Canvas, Shot, get_font

HALFTONE_PAPER = "#F2EFE8"


# --------------------------------------------------------------------------- #
# centering helpers
# --------------------------------------------------------------------------- #

def _metrics(c: Canvas, text: str, size: float, font: str):
    """Ink box of a text run in plate coordinates, anchored at the glyph ink."""
    f = get_font(font, size, c.ss)
    left, top, right, bottom = c.draw.textbbox((0, 0), text, font=f)
    return left / c.ss, top / c.ss, (right - left) / c.ss, (bottom - top) / c.ss


def _place(c: Canvas, text: str, size: float, font: str, top: float):
    """Return the draw position that puts the ink box at `top`, centered in x."""
    left, ink_top, w, h = _metrics(c, text, size, font)
    return (W - w) / 2 - left, top - ink_top, w, h


def _center(c: Canvas, text: str, size: float, font: str, fill,
            alpha: float = 1.0, dy: float = 0.0):
    """Draw one text run with its ink box centered on the canvas."""
    left, ink_top, w, h = _metrics(c, text, size, font)
    top = (H - h) / 2 + dy
    x = (W - w) / 2 - left
    y = top - ink_top
    c.text(x, y, text, size, font, fill, alpha)
    return x, y, w, h


# --------------------------------------------------------------------------- #
# 1. Aperture scan
# --------------------------------------------------------------------------- #

def shot_center_aperture_scan() -> Shot:
    head = "The frame remembers what the eye forgets"
    highlight = "remembers"
    size = 92

    def back(c: Canvas) -> None:
        c.rect(0, 0, W, H, "#0B0D10")
        for i in range(9):
            c.rect(90, 150 + i * 96, 1740, 1, INK, 0.035)
        _center(c, head, size, "helv-bold", INK, alpha=0.10)
        c.noise(0.010, seed=5101)
        c.vignette(0.28, 0.66)

    cache: dict[str, Image.Image] = {}

    def bright() -> Image.Image:
        if "img" not in cache:
            layer = Canvas()
            left, ink_top, w, h = _metrics(layer, head, size, "helv-bold")
            x = (W - w) / 2 - left
            y = (H - h) / 2 - ink_top
            prefix = head[: head.index(highlight)]
            hx = x + layer.measure(prefix, size, "helv-bold")
            hw = layer.measure(highlight, size, "helv-bold")
            layer.marker(hx - 14, y - h * 0.04, hw + 28, h * 1.10,
                         ACCENT, alpha=0.55, seed=12)
            layer.text(x, y, head, size, "helv-bold", INK)
            cache["img"] = layer.img
        return cache["img"]

    def anim(c: Canvas, t: float) -> None:
        scan = _ease(_clamp((t - 0.04) / 0.55))
        band_h = 300.0
        start = -band_h
        end = (H - band_h) / 2
        band_top = start + (end - start) * scan
        y0, y1 = max(-40.0, band_top), min(H + 40.0, band_top + band_h)
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

    return Shot(
        name="lab_aperture_scan_center",
        source="center cut (WebMotionLabPack::ApertureScan)",
        seconds=SECONDS,
        still_t=0.82,
        description="Centered aperture scan; no chrome, only the revealed line",
        cam_from=(1.0, 0.5, 0.5), cam_to=(1.015, 0.5, 0.5),
        grain=0.010, vig=0.26,
        build_static=back, draw_anim=anim,
    )


# --------------------------------------------------------------------------- #
# 2. Split flap
# --------------------------------------------------------------------------- #

def shot_center_split_flap() -> Shot:
    digits = ("2", "0", "2", "6")
    ghosts = ("9", "4", "8", "3")

    def draw_full(c: Canvas, t: float) -> None:
        c.rect(0, 0, W, H, "#0A0908")
        c.noise(0.012, seed=5202)
        c.vignette(0.30, 0.62)

        total = 4 * 280 + 3 * 30
        x0 = (W - total) / 2
        y0 = (H - 430) / 2
        cy = y0 + 215

        for i, (digit, ghost) in enumerate(zip(digits, ghosts)):
            x = x0 + i * 310
            cx = x + 140
            c.rect(x, y0, 280, 430, "#15130F")
            c.rect(x, y0, 280, 2, INK, 0.14)
            c.rect(x, y0 + 212, 280, 2, INK, 0.16)
            p = _clamp((t - (0.06 + i * 0.09)) / 0.24)
            settled = _ease(p)
            c.text(cx, cy, ghost, 210, "anton", INK,
                   alpha=0.08 * (1.0 - p), anchor="mm")
            if 0.0 < p < 1.0:
                c.rect(x, y0 + 2, 280, 3, AMBER, 0.85)
            size = 230 * (0.38 + 0.62 * settled)
            c.text(cx, cy + 72 * (1.0 - settled), digit, size, "anton", INK,
                   alpha=min(1.0, p * 2.0), anchor="mm")

    return Shot(
        name="lab_split_flap_center",
        source="center cut (WebMotionLabPack::SplitFlap)",
        seconds=SECONDS,
        still_t=0.86,
        description="Centered four-cell split flap; digits only",
        cam_from=(1.0, 0.5, 0.5), cam_to=(1.02, 0.5, 0.5),
        grain=0.012, vig=0.28,
        draw_full=draw_full,
    )


# --------------------------------------------------------------------------- #
# 3. Halftone dissolve
# --------------------------------------------------------------------------- #

def shot_center_halftone_dissolve() -> Shot:
    head = "Attention is a finite resource"
    cols, rows = 16, 9

    def draw_full(c: Canvas, t: float) -> None:
        c.rect(0, 0, W, H, HALFTONE_PAPER)
        cell_w, cell_h = W / cols, H / rows
        for row in range(rows):
            for col in range(cols):
                start = 0.02 + (row + col) * 0.022
                p = _clamp((t - start) / 0.26)
                scale = 1.0 - _ease(p)
                if scale <= 0.012:
                    continue
                w, h = cell_w * 0.84 * scale, cell_h * 0.82 * scale
                x = col * cell_w + (cell_w - w) * 0.5
                y = row * cell_h + (cell_h - h) * 0.5
                c.ellipse(x, y, w, h, "#14110D")

        left, ink_top, w, h = _metrics(c, head, 96, "serif-bold")
        x = (W - w) / 2 - left
        y = (H - h) / 2 - ink_top
        # A paper-colored knockout keeps the centered line legible over dots.
        for dx, dy in ((-5, 0), (5, 0), (0, -5), (0, 5),
                       (-4, -4), (4, -4), (-4, 4), (4, 4)):
            c.text(x + dx, y + dy, head, 96, "serif-bold",
                   HALFTONE_PAPER, alpha=0.92)
        c.text(x, y, head, 96, "serif-bold", "#121110")
        c.noise(0.008, seed=5303)
        c.vignette(0.14, 0.70)

    return Shot(
        name="lab_halftone_dissolve_center",
        source="center cut (WebMotionLabPack::HalftoneDissolve)",
        seconds=SECONDS,
        still_t=0.60,
        description="Centered headline over a full-bleed halftone dissolve",
        cam_from=(1.0, 0.5, 0.5), cam_to=(1.015, 0.5, 0.5),
        grain=0.008, vig=0.14,
        draw_full=draw_full,
    )


# --------------------------------------------------------------------------- #
# 4. Ink bloom
# --------------------------------------------------------------------------- #

def shot_center_ink_bloom() -> Shot:
    head = "The story bleeds through the page"
    highlight = "bleeds through"
    size = 92

    def back(c: Canvas) -> None:
        c.rect(0, 0, W, H, "#EFEAE1")
        c.noise(0.009, seed=5404)
        c.vignette(0.18, 0.70)

    def front(c: Canvas) -> None:
        _center(c, head, size, "serif-bold", "#151310")

    cache: dict[str, Image.Image] = {}

    def bloom() -> Image.Image:
        if "img" in cache:
            return cache["img"]
        layer = Canvas()
        left, ink_top, w, h = _metrics(layer, head, size, "serif-bold")
        x = (W - w) / 2 - left
        y = (H - h) / 2 - ink_top
        prefix = head[: head.index(highlight)]
        hx = x + layer.measure(prefix, size, "serif-bold")
        hw = layer.measure(highlight, size, "serif-bold") + 30
        layer.marker(hx - 22, y - h * 0.10, hw + 28, h * 1.26,
                     ACID, alpha=0.50, seed=44)
        layer.marker(hx + 4, y - h * 0.05, hw + 16, h * 1.08,
                     "#E8DC4A", alpha=0.42, seed=71)
        layer.marker(hx - 8, y - h * 0.02, hw + 4, h * 1.14,
                     "#F2C500", alpha=0.34, seed=97)
        for i in range(7):
            layer.ellipse(hx - 26 + (i * 173) % int(hw + 60),
                          y + h * 0.10 + (i * 53) % int(h * 1.2),
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
        front_px = (100.0 + reveal * 1560.0) * s
        ramp = np.clip((front_px - xs) / (90.0 * s), 0.0, 1.0)
        arr[:, :, 3] = (alpha * ramp * 255.0).astype(np.uint8)
        c.img.alpha_composite(Image.fromarray(arr, "RGBA"))
        c.draw = ImageDraw.Draw(c.img, "RGBA")

    return Shot(
        name="lab_ink_bloom_center",
        source="center cut (WebMotionLabPack::InkBloom)",
        seconds=SECONDS,
        still_t=0.82,
        description="Centered ink bloom; one line on paper, no chrome",
        cam_from=(1.0, 0.5, 0.5), cam_to=(1.015, 0.5, 0.5),
        grain=0.009, vig=0.16,
        build_static=back, build_static_front=front, draw_anim=anim,
    )


# --------------------------------------------------------------------------- #
# 5. Parallax depth
# --------------------------------------------------------------------------- #

def shot_center_parallax_depth() -> Shot:
    titles = ("FOREGROUND", "MIDGROUND", "BACKGROUND")
    numbers = ("01", "02", "03")
    bodies = ("the subject", "the context", "the field")
    panels = ("#2C3A46", "#222C36", "#1A222A")
    accents = (ACCENT, ACID, CYAN)
    base_x = (1185.0, 725.0, 265.0)  # front to back
    base_y = 331.0

    def draw_full(c: Canvas, t: float) -> None:
        c.rect(0, 0, W, H, "#0E1216")
        c.noise(0.011, seed=5505)
        c.vignette(0.34, 0.62)
        for i in range(12):
            c.ellipse(120 + (i * 317) % 1680, 180 + (i * 211) % 620,
                      3, 3, INK, 0.18)

        # Spread the planes around the centered stack: the front card moves
        # right while the back card moves left, so the group stays centered.
        spread = (_ease(t) - 0.5) * 2.0
        offsets = (spread * 38.0, spread * 22.0, -spread * 38.0)
        for depth in (2, 1, 0):
            x = base_x[depth] + offsets[depth]
            y = base_y + depth * 22.0
            w, h = 470.0, 330.0
            c.rect(x + 18, y + 22, w, h, "#000000", 0.34, radius=18)
            c.rect(x + 36, y + 44, w, h, "#000000", 0.16, radius=18)
            c.rect(x, y, w, h, panels[depth], 1.0, radius=16)
            c.rect(x, y, w, 4, accents[depth], 0.95)
            c.text(x + 34, y + 36, numbers[depth], 46, "oswald-bold",
                   accents[depth])
            c.text(x + 34, y + 100, titles[depth], 26, "oswald", INK)
            c.text(x + 34, y + 160, bodies[depth], 34, "serif-bold", "#C9C2B6")
            c.rect(x + 34, y + 250, 180, 3, accents[depth], 0.72)

    return Shot(
        name="lab_parallax_depth_center",
        source="center cut (WebMotionLabPack::ParallaxDepth)",
        seconds=SECONDS,
        still_t=0.80,
        description="Centered three-plane parallax; no ghost word or captions",
        cam_from=(1.0, 0.5, 0.5), cam_to=(1.02, 0.5, 0.5),
        grain=0.011, vig=0.30,
        draw_full=draw_full,
    )


# --------------------------------------------------------------------------- #
# 6. Slice glitch
# --------------------------------------------------------------------------- #

def shot_center_slice_glitch() -> Shot:
    first, second = "SIGNAL", "RECOVERED"
    s1, s2, gap = 200, 118, 8

    def draw_full(c: Canvas, t: float) -> None:
        c.rect(0, 0, W, H, "#07090B")
        c.noise(0.014, seed=5606)
        c.vignette(0.38, 0.58)
        for i in range(8):
            c.rect(90, 120 + i * 120, 1740, 1, INK, 0.045)

        _, _, _, h1 = _metrics(c, first, s1, "oswald-bold")
        _, _, _, h2 = _metrics(c, second, s2, "oswald-bold")
        top = (H - (h1 + gap + h2)) / 2
        x1, y1, _, _ = _place(c, first, s1, "oswald-bold", top)
        x2, y2, _, _ = _place(c, second, s2, "oswald-bold", top + h1 + gap)

        glitch = max(_burst(t, 0.16, 0.075),
                     _burst(t, 0.40, 0.065) * 0.85,
                     _burst(t, 0.64, 0.055) * 0.70)
        amp = 30.0 * glitch

        for dx, dy, color, alpha in ((-8, -4, "#FF3B30", 0.45),
                                     (8, 4, CYAN, 0.38)):
            c.text(x1 + dx, y1 + dy, first, s1, "oswald-bold", color,
                   alpha=alpha)
            c.text(x2 + dx, y2 + dy, second, s2, "oswald-bold", color,
                   alpha=alpha)
        c.text(x1, y1, first, s1, "oswald-bold", INK)
        c.text(x2, y2, second, s2, "oswald-bold", INK)

        if amp > 0.4:
            arr = np.array(c.img)
            rng = np.random.default_rng(int(t * 1000) + 7)
            s = c.ss
            band_top, band_bottom = int((top - 80) * s), int((top + h1 + gap + h2 + 80) * s)
            for _ in range(9):
                y0 = int(rng.integers(band_top, max(band_top + 1, band_bottom - int(30 * s))))
                height = int(rng.integers(int(8 * s), int(38 * s)))
                shift = int(rng.integers(-int(amp), int(amp) + 1) * s)
                if shift:
                    arr[y0:y0 + height, :, :] = np.roll(
                        arr[y0:y0 + height, :, :], shift, axis=1)
            c.img = Image.fromarray(arr, "RGBA")
            c.draw = ImageDraw.Draw(c.img, "RGBA")
            for i in range(4):
                y = top - 40 + i * 80 + (i * 37) % 60
                c.rect((W - 820) / 2, y, 820, 8, INK, 0.10 * glitch)

    return Shot(
        name="lab_slice_glitch_center",
        source="center cut (WebMotionLabPack::SliceGlitch)",
        seconds=SECONDS,
        still_t=0.90,
        description="Centered signal recovery; only the two-line statement",
        cam_from=(1.0, 0.5, 0.5), cam_to=(1.02, 0.5, 0.5),
        grain=0.014, vig=0.32,
        draw_full=draw_full,
    )


BUILDERS = (
    shot_center_aperture_scan,
    shot_center_split_flap,
    shot_center_halftone_dissolve,
    shot_center_ink_bloom,
    shot_center_parallax_depth,
    shot_center_slice_glitch,
)


def all_centered_motion_lab_shots() -> list[Shot]:
    return [build() for build in BUILDERS]


def centered_motion_lab_names() -> list[str]:
    return [shot.name for shot in all_centered_motion_lab_shots()]


if __name__ == "__main__":
    for shot in all_centered_motion_lab_shots():
        print(shot.name, "|", shot.description)
    print(len(BUILDERS), "centered shots")
