#!/usr/bin/env python3
"""Chronon3D — Documentary Background Quality 2.0 shared library.

Fixes D01..D10 from DOCBG_V2_AUDIT.md with shared primitives (no new deps,
only numpy+PIL). Architecture: base / texture-grain / imperfections /
illumination / animation separated. Vignette, scratches, dust usable as
overlays. The 15 historic preset IDs are kept as parametric variants of
7 bases to eliminate duplication while staying backward compatible.

Bases (7): dark_graphite, deep_navy, warm_umber, editorial_ivory, newsprint,
muted_olive, photo_bokeh.
"""

from __future__ import annotations

import math
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

W, H = 1920, 1080

# ---------------------------------------------------------------- primitives

def smoothstep(e0: float, e1: float, x: np.ndarray) -> np.ndarray:
    t = np.clip((x - e0) / max(1e-6, (e1 - e0)), 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def elliptical_dist(w: int, h: int, cx: float, cy: float, rx: float, ry: float,
                    asym: float = 0.0) -> np.ndarray:
    """Continuous elliptical distance field, asymmetry clamped <= 0.02."""
    asym = float(np.clip(asym, -0.02, 0.02))
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    xx = xx + asym * (yy - cy)  # tiny shear only
    return np.sqrt(((xx - cx) / rx) ** 2 + ((yy - cy) / ry) ** 2)


def soft_vignette_overlay(w: int, h: int, strength: float = 0.14,
                          seed: int = 0) -> Image.Image:
    """Elliptical, continuous, wide-feather vignette. No rings/geometry."""
    rng = np.random.default_rng(seed)
    cx = w / 2 + float(rng.uniform(-w * 0.01, w * 0.01))
    cy = h / 2 + float(rng.uniform(-h * 0.01, h * 0.01))
    rx, ry = w * 0.72, h * 0.78
    d = elliptical_dist(w, h, cx, cy, rx, ry)
    # wide feather: fully clear until 0.55, full strength at 1.15
    m = smoothstep(0.55, 1.15, d) * strength
    dark = (m * 255).astype(np.uint8)
    zero = np.zeros_like(dark)
    return Image.fromarray(np.dstack([zero, zero, zero, dark]), mode="RGBA")


def value_noise_fbm(w: int, h: int, seed: int, octaves: int = 4,
                    base: int = 8) -> np.ndarray:
    """Natural low-frequency tonal variation: random grids, bilinear
    upsampling, non-aligned octaves (no symmetry, no tiling)."""
    rng = np.random.default_rng(seed)
    acc = np.zeros((h, w), np.float32)
    amp, tot = 1.0, 0.0
    gw, gh = base, max(2, int(base * h / w))
    for o in range(octaves):
        jx, jy = int(rng.integers(0, 64)), int(rng.integers(0, 64))
        g = rng.random((gh + 2, gw + 2)).astype(np.float32)
        im = Image.fromarray((g * 255).astype(np.uint8)).resize(
            (w, h), Image.BILINEAR)
        # non-periodic crop offset breaks symmetry
        arr = np.asarray(im, dtype=np.float32) / 255.0
        arr = np.roll(arr, shift=(jy, jx), axis=(0, 1))
        acc += arr * amp
        tot += amp
        amp *= 0.5
        gw, gh = gw * 2 + 1, gh * 2 + 1
    acc /= tot
    return (acc - acc.mean()).astype(np.float32)  # zero-mean


def multiscale_grain(w: int, h: int, seed: int,
                     micro: float = 5.0, fine: float = 4.0,
                     lowfreq_amp: float = 3.0) -> np.ndarray:
    """Signed luminance grain: micro (full-res) + fine (half-res) + fBm
    low-freq. Bounded so no macro blotches: lowfreq <= 3.5."""
    rng = np.random.default_rng(seed)
    g_micro = rng.normal(0, micro, (h, w)).astype(np.float32)
    g_half = rng.normal(0, fine, (h // 2, w // 2)).astype(np.float32)
    g_fine = np.asarray(Image.fromarray(g_half).resize(
        (w, h), Image.BILINEAR), dtype=np.float32)
    g_low = value_noise_fbm(w, h, seed + 999, octaves=4,
                            base=6) * min(3.5, lowfreq_amp)
    return g_micro + g_fine + g_low


def apply_grain(base: Image.Image, grain: np.ndarray,
                warm_tint: tuple = (210, 205, 195)) -> Image.Image:
    """Add signed grain as luminance overlay with dithering to kill banding."""
    arr = np.asarray(base.convert("RGB"), dtype=np.float32)
    arr += grain[:, :, None]
    # ±1.2 LSB dither before quantize (banding fix D05)
    d = np.random.default_rng(777).normal(0, 1.2, grain.shape).astype(np.float32)
    arr += d[:, :, None]
    arr = np.clip(arr, 0, 255).astype(np.uint8)
    return Image.fromarray(arr, mode="RGB").convert("RGBA")


def paper_fibers(w: int, h: int, seed: int, n: int,
                 color: tuple, alpha_lo: int, alpha_hi: int,
                 blur: float = 0.6) -> Image.Image:
    rng = np.random.default_rng(seed)
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im, "RGBA")
    for _ in range(n):
        x0, y0 = rng.uniform(0, w), rng.uniform(0, h)
        ln = rng.uniform(10, 55)
        ang = rng.uniform(-0.5, 0.5) if rng.random() > 0.25 else rng.uniform(0, math.pi)
        x1, y1 = x0 + ln * math.cos(ang), y0 + ln * math.sin(ang)
        a = int(rng.uniform(alpha_lo, alpha_hi))
        d.line([(x0, y0), (x1, y1)], fill=(*color, a), width=1)
    return im.filter(ImageFilter.GaussianBlur(blur))


def scratches_overlay(w: int, h: int, seed: int, xs: list,
                      alpha_lo: int = 10, alpha_hi: int = 26) -> Image.Image:
    """Only broken faint segments, never full-height lines (D02 fix)."""
    rng = np.random.default_rng(seed)
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im, "RGBA")
    for sx in xs:
        y = float(rng.uniform(0, 120))
        while y < h:
            seg = float(rng.uniform(30, 160))
            gap = float(rng.uniform(60, 260))
            a = int(rng.uniform(alpha_lo, alpha_hi))
            d.line([(sx, y), (sx, min(h, y + seg))],
                   fill=(215, 205, 185, a), width=1)
            y += seg + gap
    return im


def dust_overlay(w: int, h: int, seed: int, n: int = 45) -> Image.Image:
    """Atmospheric dust: 3 size classes, low alpha, per-mote blur (depth)."""
    rng = np.random.default_rng(seed)
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im, "RGBA")
    for i in range(n):
        px, py = rng.uniform(60, w - 60), rng.uniform(60, h - 60)
        cls = rng.random()
        if cls < 0.55:  # far: tiny, faint
            r, a, bl = rng.uniform(0.8, 1.8), rng.uniform(10, 26), 0.4
        elif cls < 0.85:  # mid
            r, a, bl = rng.uniform(1.8, 3.4), rng.uniform(14, 34), 1.2
        else:  # near: soft bokeh
            r, a, bl = rng.uniform(3.4, 6.5), rng.uniform(12, 28), 2.6
        mote = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        md = ImageDraw.Draw(mote, "RGBA")
        md.ellipse([px - r, py - r, px + r, py + r],
                   fill=(235, 230, 220, int(a)))
        im.alpha_composite(mote.filter(ImageFilter.GaussianBlur(bl)))
    return im


def ledger_lines_overlay(w: int, h: int, seed: int, n: int = 6) -> Image.Image:
    """Occasional irregular editorial rules, never a permanent grid (D07)."""
    rng = np.random.default_rng(seed)
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im, "RGBA")
    ys = sorted(rng.uniform(80, h - 80, n))
    for y in ys:
        x0 = rng.uniform(0, w * 0.3)
        x1 = rng.uniform(w * 0.7, w)
        a = int(rng.uniform(8, 16))
        d.line([(x0, y), (x1, y)], fill=(150, 165, 185, a), width=1)
    return im


def diffuse_light_pool(w: int, h: int, color: tuple, strength: float,
                       cxr: float = 0.5, cyr: float = 0.42,
                       spread: float = 1.1) -> Image.Image:
    """Very wide low-alpha ambient pool (D09/P1 fix): no readable beam."""
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    rx, ry = w * 0.85 * spread, h * 0.9 * spread
    d = np.sqrt(((xx - w * cxr) / rx) ** 2 + ((yy - h * cyr) / ry) ** 2)
    m = (1.0 - smoothstep(0.0, 1.0, d)) * strength
    rgb = np.zeros((h, w, 3), np.uint8)
    rgb[:, :] = color
    return Image.fromarray(
        np.dstack([rgb, (m * 255).astype(np.uint8)]), mode="RGBA")

# ---------------------------------------------------------------- 7 bases

def base_dark_graphite(seed: int = 11) -> Image.Image:
    yy = np.linspace(0, 1, H, dtype=np.float32)[:, None]
    base = np.zeros((H, W, 3), np.float32)
    base[:, :] = (15, 17, 21)
    base += (1 - yy[:, :, None] if yy.ndim == 2 else 1) * 0  # keep flat-ish
    base += np.linspace(4, 0, H, dtype=np.float32)[:, None, None] * np.array(
        [1, 1, 1.2], np.float32)
    base += value_noise_fbm(W, H, seed, 4, 6)[:, :, None] * np.array(
        [2.2, 2.2, 2.6], np.float32)
    im = Image.fromarray(np.clip(base, 0, 255).astype(np.uint8)).convert("RGBA")
    g = multiscale_grain(W, H, seed + 1, 5.0, 4.0, 2.6)
    return apply_grain(im, g)


def base_deep_navy(seed: int = 22) -> Image.Image:
    yy = np.linspace(0, 1, H, dtype=np.float32)[:, None, None]
    top = np.array([10, 20, 38], np.float32)
    bot = np.array([3, 6, 14], np.float32)
    col = top[None, None, :] * (1 - yy) + bot[None, None, :] * yy
    base = np.broadcast_to(col, (H, W, 3)).copy()
    base += value_noise_fbm(W, H, seed, 4, 6)[:, :, None] * 2.4
    im = Image.fromarray(np.clip(base, 0, 255).astype(np.uint8)).convert("RGBA")
    im.alpha_composite(diffuse_light_pool(W, H, (24, 52, 92), 0.10,
                                          cxr=0.78, cyr=0.22, spread=1.2))
    return apply_grain(im, multiscale_grain(W, H, seed + 1, 4.5, 3.5, 2.4))


def base_warm_umber(seed: int = 33) -> Image.Image:
    yy = np.linspace(0, 1, H, dtype=np.float32)[:, None, None]
    top = np.array([30, 22, 15], np.float32)
    bot = np.array([16, 12, 8], np.float32)
    col = top[None, None, :] * (1 - yy) + bot[None, None, :] * yy
    base = np.broadcast_to(col, (H, W, 3)).copy()
    base += value_noise_fbm(W, H, seed, 4, 7)[:, :, None] * np.array(
        [2.6, 2.2, 1.8], np.float32)
    im = Image.fromarray(np.clip(base, 0, 255).astype(np.uint8)).convert("RGBA")
    # warm ambient pool, very diffuse (replaces hard center pool)
    im.alpha_composite(diffuse_light_pool(W, H, (88, 58, 34), 0.10,
                                          cxr=0.5, cyr=0.45, spread=1.25))
    im.alpha_composite(soft_vignette_overlay(W, H, 0.12, seed + 5))
    return apply_grain(im, multiscale_grain(W, H, seed + 1, 5.0, 4.0, 2.8))


def base_editorial_ivory(seed: int = 44) -> Image.Image:
    """Matte opaque paper: near-uniform, thin fiber, 4% edge tone (D08 fix)."""
    base = np.zeros((H, W, 3), np.float32)
    base[:, :] = (237, 232, 221)
    base += value_noise_fbm(W, H, seed, 3, 8)[:, :, None] * 1.6
    im = Image.fromarray(np.clip(base, 0, 255).astype(np.uint8)).convert("RGBA")
    im.alpha_composite(paper_fibers(W, H, seed + 1, 420, (120, 112, 98), 8, 20, 0.6))
    # gentle edge toning only (no central spotlight)
    im.alpha_composite(soft_vignette_overlay(W, H, 0.05, seed + 2))
    g = multiscale_grain(W, H, seed + 3, 2.6, 2.0, 1.2)
    return apply_grain(im, g)


def base_newsprint(seed: int = 55) -> Image.Image:
    base = np.zeros((H, W, 3), np.float32)
    base[:, :] = (219, 210, 190)
    yy = np.linspace(0, 1, H, dtype=np.float32)[:, None, None]
    base += (0.5 - np.abs(yy - 0.5)) * 10.0  # soft center lift, ±5 max
    base += value_noise_fbm(W, H, seed, 4, 8)[:, :, None] * 2.0
    im = Image.fromarray(np.clip(base, 0, 255).astype(np.uint8)).convert("RGBA")
    im.alpha_composite(paper_fibers(W, H, seed + 1, 600, (85, 75, 62), 10, 24, 0.5))
    return apply_grain(im, multiscale_grain(W, H, seed + 2, 3.2, 2.6, 1.8))


def base_muted_olive(seed: int = 66) -> Image.Image:
    yy = np.linspace(0, 1, H, dtype=np.float32)
    top = np.array([34, 42, 32], np.float32)  # lifted, cleaner (no muddy brown)
    bot = np.array([18, 24, 18], np.float32)
    yyw = np.linspace(0, 1, H, dtype=np.float32)[:, None, None]
    col = top[None, None, :] * (1 - yyw) + bot[None, None, :] * yyw
    base = np.broadcast_to(col, (H, W, 3)).copy()
    base += value_noise_fbm(W, H, seed, 4, 6)[:, :, None] * 2.2
    im = Image.fromarray(np.clip(base, 0, 255).astype(np.uint8)).convert("RGBA")
    im.alpha_composite(soft_vignette_overlay(W, H, 0.12, seed + 5))
    return apply_grain(im, multiscale_grain(W, H, seed + 1, 4.6, 3.6, 2.5))


def base_photo_bokeh(seed: int = 77) -> Image.Image:
    rng = np.random.default_rng(seed)
    base = np.zeros((H, W, 3), np.float32)
    base[:, :] = (14, 16, 21)
    im = Image.fromarray(base.astype(np.uint8)).convert("RGBA")
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ld = ImageDraw.Draw(layer, "RGBA")
    blobs = [((0.22, 0.30, 300, (52, 38, 26, 30))),
             ((0.78, 0.68, 340, (26, 38, 34, 28))),
             ((0.51, 0.48, 260, (30, 32, 42, 26))),
             ((0.62, 0.25, 150, (40, 44, 60, 18)))]
    for (fx, fy, r, col) in blobs:
        jx, jy = int(rng.uniform(-20, 20)), int(rng.uniform(-14, 14))
        ld.ellipse([W * fx - r + jx, H * fy - r + jy,
                    W * fx + r + jx, H * fy + r + jy], fill=col)
    im.alpha_composite(layer.filter(ImageFilter.GaussianBlur(90)))
    im.alpha_composite(soft_vignette_overlay(W, H, 0.10, seed + 3))
    return apply_grain(im, multiscale_grain(W, H, seed + 4, 4.5, 3.5, 2.4))


def base_archival(seed: int = 88) -> Image.Image:
    base = np.zeros((H, W, 3), np.float32)
    base[:, :] = (20, 17, 13)
    base += value_noise_fbm(W, H, seed, 4, 7)[:, :, None] * np.array(
        [2.6, 2.2, 1.8], np.float32)
    im = Image.fromarray(np.clip(base, 0, 255).astype(np.uint8)).convert("RGBA")
    im.alpha_composite(diffuse_light_pool(W, H, (70, 50, 32), 0.08,
                                          cxr=0.5, cyr=0.5, spread=1.3))
    im.alpha_composite(soft_vignette_overlay(W, H, 0.14, seed + 5))
    im.alpha_composite(scratches_overlay(W, H, seed + 6, [612, 1188]))
    im.alpha_composite(dust_overlay(W, H, seed + 7, n=22))
    return apply_grain(im, multiscale_grain(W, H, seed + 8, 5.2, 4.2, 2.8))


# ------------------------------------------------- 15-ID compatible mapping
# 7 bases + overlays; each historic ID gets a distinct base/seed/overlay combo.

def build_v2(preset_id: str) -> Image.Image:
    m = {
        "01_dark_film_grain": lambda: base_dark_graphite(11),
        "02_dark_paper": lambda: _with(base_dark_graphite(21),
                                       paper_fibers(W, H, 2021, 550, (200, 200, 205), 10, 26)),
        "03_archival_film": lambda: base_archival(88),
        "04_deep_navy_gradient": lambda: base_deep_navy(22),
        "05_warm_documentary": lambda: base_warm_umber(33),
        "06_editorial_ivory": lambda: base_editorial_ivory(44),
        "07_soft_vignette": "OVERLAY",  # common vignette option over graphite
        "08_matte_charcoal": lambda: base_dark_graphite(81),
        "09_subtle_film_scratches": "OVERLAY",
        "10_blurred_backdrop": lambda: base_photo_bokeh(77),
        "11_newspaper_paper": lambda: base_newsprint(55),
        "12_faint_horizontal_lines": lambda: _with(
            base_dark_graphite(121), ledger_lines_overlay(W, H, 1212, n=6)),
        "13_floating_dust": lambda: _with(
            _tint(base_dark_graphite(131), (20, 22, 27)), dust_overlay(W, H, 1313, n=45)),
        "14_muted_olive": lambda: base_muted_olive(66),
        "15_soft_light_sweep": lambda: _with(
            base_dark_graphite(151),
            diffuse_light_pool(W, H, (235, 230, 220), 0.07, cxr=0.62,
                               cyr=0.40, spread=1.5)),
    }
    v = m[preset_id]
    if v == "OVERLAY":
        if preset_id == "07_soft_vignette":
            return _with(base_dark_graphite(71),
                         soft_vignette_overlay(W, H, 0.14, 707))
        return _with(base_dark_graphite(91),
                     scratches_overlay(W, H, 909, [560, 1080, 1540],
                                       10, 24))
    im = v()
    assert isinstance(im, Image.Image)
    return im


def _with(base: Image.Image, overlay: Image.Image) -> Image.Image:
    base.alpha_composite(overlay)
    return base


def _tint(base: Image.Image, color: tuple) -> Image.Image:
    arr = np.asarray(base.convert("RGB"), dtype=np.float32)
    lum = arr.mean(axis=2, keepdims=True)
    arr = lum * 0.25 + np.array(color, np.float32)[None, None, :] * 0.75
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8)).convert("RGBA")
