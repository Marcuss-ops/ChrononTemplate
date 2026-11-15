#!/usr/bin/env python3
"""Generate the P7 vertical tonal ramp with sub-LSB triangular dither.

A shape-layer gradient currently renders as the clear colour in this build;
the image path is stable. The ramp spans the same four stops authored by the
old shape fill.
"""
from pathlib import Path

import numpy as np
from PIL import Image

W, H = 1920, 1080
stops = [
    (0.00, (5, 7, 10)),
    (0.32, (22, 30, 40)),
    (0.64, (113, 128, 141)),
    (1.00, (237, 241, 244)),
]
y = np.linspace(0.0, 1.0, H)
rgb = np.empty((H, 3), dtype=float)
for i in range(len(stops) - 1):
    p0, c0 = stops[i]
    p1, c1 = stops[i + 1]
    mask = (y >= p0) & (y <= p1)
    t = (y[mask] - p0) / (p1 - p0)
    for channel in range(3):
        rgb[mask, channel] = c0[channel] + (c1[channel] - c0[channel]) * t

# Deterministic per-pixel noise dither, +/-6 LSB. An ordered Bayer cell is
# annihilated by the camera's sub-pixel bilinear resampling (a 2x2 box filter
# averages the cell back to its mean); a hash-noise field keeps its variance
# through the resample, so 8-bit quantization plateaus stay broken.
yy, xx = np.mgrid[0:H, 0:W]
hash = (xx.astype(np.uint32) * 374761393 +
        yy.astype(np.uint32) * 668265263 + 1442695041)
hash ^= hash >> 13
hash *= 1274126177
hash ^= hash >> 16
pattern = ((hash & 1023).astype(float) / 1023.0 - 0.5) * 12.0
pixels = np.clip(np.rint(rgb[:, None, :] + pattern[:, :, None]), 0, 255).astype(np.uint8)
out = Path("ChrononTemplate/assets/documentary_parity/p7_gradient.png")
out.parent.mkdir(parents=True, exist_ok=True)
Image.fromarray(pixels, "RGB").save(out)
print(out, pixels.shape)
