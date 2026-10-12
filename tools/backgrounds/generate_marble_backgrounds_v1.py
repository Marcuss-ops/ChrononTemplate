#!/usr/bin/env python3
"""10 marble backgrounds 2048x1152 (master) + 1920x1080 5s MP4 via ffmpeg zoompan.

OOM-safe by design:
- one background at a time, float32, del+gc between variants;
- video motion comes from ffmpeg zoompan (single PNG in, no frame buffering
  in Python);
- MP4s encoded sequentially, veryfast preset.
"""
import gc
import hashlib
import json
import os
import subprocess
import sys

import numpy as np
from PIL import Image

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                   "..", "..", "out", "marble_backgrounds_v1")
PNGDIR = os.path.join(OUT, "png")
MP4DIR = os.path.join(OUT, "mp4")
W, H = 2048, 1152
FPS, SECONDS = 30, 5
FRAMES = FPS * SECONDS

PALETTES = [
    ("carrara_white",   (236, 234, 228), (120, 118, 114), 42, 0.85),
    ("marquina_black",  (24, 24, 28),    (148, 146, 138), 43, 0.38, True),
    ("beige_emperador", (176, 152, 124), (88, 66, 48),    44, 0.85),
    ("grey_bardiglio",  (148, 152, 158), (70, 74, 82),    45, 0.85),
    ("verde_alpi",      (38, 74, 66),    (180, 190, 178), 46, 0.55),
    ("rosa_norvegia",   (214, 178, 168), (120, 80, 76),   47, 0.85),
    ("blu_macuba",      (52, 72, 96),    (168, 178, 192), 48, 0.55),
    ("gold_calacatta",  (232, 224, 206), (150, 118, 70),  49, 0.85),
    ("nero_portoro",    (18, 18, 20),    (152, 128, 80),  50, 0.38, True),
    ("onyx_chiaro",     (226, 214, 192), (140, 120, 100), 51, 0.85),
]


def value_noise(h, w, cells_y, cells_x, rng):
    grid = rng.random((cells_y + 1, cells_x + 1)).astype(np.float32)
    img = Image.fromarray((grid * 255).astype(np.uint8), mode="L")
    img = img.resize((w, h), Image.BILINEAR)
    return np.asarray(img, dtype=np.float32) / 255.0


def fbm(h, w, base_cells, octaves, rng):
    acc = np.zeros((h, w), dtype=np.float32)
    amp, total = 1.0, 0.0
    cy, cx = base_cells
    for _ in range(octaves):
        acc += amp * value_noise(h, w, cy, cx, rng)
        total += amp
        amp *= 0.5
        cy *= 2
        cx *= 2
    return acc / total


def marble(seed, base, vein, gain=0.85, crisp=False):
    r1 = np.random.default_rng(seed * 100 + 1)
    r2 = np.random.default_rng(seed * 100 + 2)
    r3 = np.random.default_rng(seed * 100 + 3)
    r4 = np.random.default_rng(seed * 100 + 4)
    warp = fbm(H, W, (5, 6), 5, r1) * 5.0
    tone = fbm(H, W, (3, 4), 4, r2)
    # Ridged multifractal: thin chaotic web veins (isotropic, no banding).
    n = fbm(H, W, (9, 11), 5, r3)
    n = n + 0.35 * (warp / 5.0 - 0.5)
    ridged = 1.0 - np.abs(2.0 * n - 1.0)
    del n
    if crisp:
        # Dark stone: hard thin mineral lines instead of soft glowing falloff.
        veins = np.clip((ridged - 0.80) * 10.0, 0, 1).astype(np.float32)
    else:
        veins = np.power(np.clip(ridged, 0, 1), 34.0).astype(np.float32)
    del ridged
    gc.collect()
    # A few bold mineral veins on an independent field.
    n2 = fbm(H, W, (4, 5), 4, r4)
    ridged2 = 1.0 - np.abs(2.0 * n2 - 1.0)
    del n2
    if crisp:
        bold = (np.clip((ridged2 - 0.85) * 10.0, 0, 1) * 0.9).astype(np.float32)
    else:
        bold = (np.power(np.clip(ridged2, 0, 1), 60.0) * 0.9).astype(np.float32)
    del ridged2
    mix = np.clip((veins * 0.85 + bold) * gain, 0, 1)
    del veins, bold
    shade = (0.96 + 0.08 * tone) if crisp else (0.92 + 0.16 * tone)
    del tone
    base_a = np.array(base, dtype=np.float32)[None, None, :]
    vein_a = np.array(vein, dtype=np.float32)[None, None, :]
    img = base_a * (1 - mix[..., None]) + vein_a * mix[..., None]
    img *= shade[..., None]
    del mix, shade
    gc.collect()
    grain = r4.normal(0, 1.6, (H, W)).astype(np.float32)
    img += grain[..., None]
    del grain
    vx = (np.linspace(-1, 1, W, dtype=np.float32) ** 2)[None, :, None]
    vy = (np.linspace(-1, 1, H, dtype=np.float32) ** 2)[:, None, None]
    img *= (1.0 - 0.10 * np.clip(vx + vy, 0, 1))
    del vx, vy
    return np.clip(img, 0, 255).astype(np.uint8)


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def encode(png, mp4):
    # NO camera motion: the frame is perfectly still, only animated grain
    # (temporal film grain) lives over the marble. Single PNG in, ffmpeg
    # synthesizes the grain per frame — no Python frame buffering.
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-loop", "1", "-i", png,
           "-vf", "scale=1920:1080,noise=alls=3:allf=t",
           "-t", str(SECONDS), "-r", str(FPS),
           "-c:v", "libx264", "-preset", "medium",
           "-crf", "18", "-pix_fmt", "yuv420p", "-an", mp4]
    subprocess.run(cmd, check=True)


def main():
    os.makedirs(PNGDIR, exist_ok=True)
    os.makedirs(MP4DIR, exist_ok=True)
    manifest = {"version": 1, "kind": "marble-backgrounds-v1",
                "canvas": {"width": 1920, "height": 1080, "fps": FPS},
                "duration_seconds": SECONDS, "assets": []}
    for i, pal in enumerate(PALETTES):
        name, base, vein, seed, gain = pal[:5]
        crisp = pal[5] if len(pal) > 5 else False
        png = os.path.join(PNGDIR, "marble_bg_%02d_%s.png" % (i + 1, name))
        mp4 = os.path.join(MP4DIR, "marble_bg_%02d_%s.mp4" % (i + 1, name))
        print("[%d/10] %s ..." % (i + 1, name), flush=True)
        if not os.path.exists(png):
            Image.fromarray(marble(seed, base, vein, gain, crisp)).save(png)
            gc.collect()
        encode(png, mp4)
        info = {"id": "marble-bg-%02d" % (i + 1), "name": name,
                "png": os.path.relpath(png, OUT),
                "mp4": os.path.relpath(mp4, OUT),
                "png_sha256": sha256(png), "mp4_sha256": sha256(mp4)}
        manifest["assets"].append(info)
        print("  png=%s mp4=%s" % (info["png_sha256"][:12], info["mp4_sha256"][:12]),
              flush=True)
        gc.collect()
    with open(os.path.join(OUT, "manifest.json"), "w") as f:
        json.dump(manifest, f, indent=2)
    print("OK: %s" % OUT)


if __name__ == "__main__":
    sys.exit(main())
