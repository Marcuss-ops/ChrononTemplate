#!/usr/bin/env python3
"""Generate the neutral off-white paper background used by the paper title card.

Stack (matching feedback from reference 'Why France Is Europe's Next Debt Crisis'):
  1. solid off-white neutral base   #ECECEC / #EAEAEA (not warm/yellowish)
  2. soft radial gradient           centre #F2F2F2 -> edges #DADADA
  3. cloud / uneven paper texture   large-scale fractal noise
  4. fine monochrome noise          ~1.5 %, blurred 0.5 px
  5. localized dust & specks        ~8-10 % cluster-biased, especially right side
  6. localized thin scratches       faint scratches & micro-streaks, right side
  7. stronger wide vignette         edge darkening 18-22%, wide smooth falloff

Usage: make_paper_background.py <out.png> [<out2.png> ...]
"""
import sys

import numpy as np
from PIL import Image, ImageFilter

W, H = 1920, 1080
SEED = 20261011


def hex_rgb(value):
    return np.array([int(value[i:i + 2], 16) for i in (1, 3, 5)], dtype=np.float32) / 255.0


def blur(arr, radius):
    img = Image.fromarray(np.clip(arr * 255.0, 0, 255).astype(np.uint8), "L")
    return np.asarray(img.filter(ImageFilter.GaussianBlur(radius)), dtype=np.float32) / 255.0


def fractal(rng, octaves=5):
    acc = np.zeros((H, W), np.float32)
    amp, total = 1.0, 0.0
    for o in range(octaves):
        cells = 3 * 2 ** o
        small = rng.random((max(2, cells * H // W), cells)).astype(np.float32)
        img = Image.fromarray((small * 255).astype(np.uint8), "L").resize((W, H), Image.BICUBIC)
        acc += amp * np.asarray(img, dtype=np.float32) / 255.0
        total += amp
        amp *= 0.5
    return acc / total


def main(outputs):
    rng = np.random.default_rng(SEED)
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)

    # Elliptical normalized distance from center
    rx = (xx - W / 2) / (W / 2)
    ry = (yy - H / 2) / (H / 2)
    r = np.sqrt(rx ** 2 + ry ** 2)
    r_norm = np.clip(r / 1.35, 0, 1)[..., None]

    # Neutral base tone (neutral grey/off-white, not warm/yellow)
    centre = hex_rgb("#F1F1F1")
    edge = hex_rgb("#D8D8D8")
    base = centre * (1.0 - r_norm) + edge * r_norm

    # Cloud / uneven texture: subtle organic paper variation
    cloud = fractal(rng)
    base += ((cloud - cloud.mean()) * 0.028)[..., None]

    # Fine monochrome noise ~1.5%
    noise = blur(rng.random((H, W)).astype(np.float32), 0.5)
    base += ((noise - 0.5) * 0.025)[..., None]

    # Localized dust & specks (biased toward right & edges)
    dust = np.zeros((H, W), np.float32)
    for _ in range(1200):
        # Biased distribution towards the right half & perimeter
        if rng.random() > 0.4:
            x = rng.integers(int(W * 0.45), W)
        else:
            x = rng.integers(0, W)
        y = rng.integers(0, H)
        rad = rng.integers(0, 3)
        dust[max(0, y - rad):y + rad + 1, max(0, x - rad):x + rad + 1] = rng.uniform(0.3, 1.0)
    dust = blur(dust, 0.6)
    base *= (1.0 - 0.09 * np.clip(dust * 2.2, 0, 1))[..., None]

    # Localized faint vertical scratches & micro marks (prominent on right)
    scratch = np.zeros((H, W), np.float32)
    for _ in range(40):
        if rng.random() > 0.35:
            x = rng.integers(int(W * 0.5), W)
        else:
            x = rng.integers(0, W)
        y0 = rng.integers(0, H)
        ln = rng.integers(40, 260)
        scratch[y0:min(H, y0 + ln), x] = rng.uniform(0.3, 0.85)
    scratch = blur(scratch, 0.5)
    base *= (1.0 - 0.05 * np.clip(scratch * 2.5, 0, 1))[..., None]

    # Stronger, elegant vignette: edge darkening ~18-20%, wide softness
    vignette = np.clip((r / 1.25) ** 1.8, 0, 1)
    base *= (1.0 - 0.19 * vignette)[..., None]

    out = Image.fromarray(np.clip(base * 255.0 + 0.5, 0, 255).astype(np.uint8), "RGB")
    for path in outputs:
        out.save(path, optimize=True)
        print("wrote", path)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    main(sys.argv[1:])
