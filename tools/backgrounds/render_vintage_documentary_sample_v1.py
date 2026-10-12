#!/usr/bin/env python3
"""Vintage documentary sample: 1920x1080 5s MP4, 30fps, fully static camera.

Faithful to ChrononTemplate/catalog/vintage_documentary.v1.json:
- black ground #050505 + diffuse dark-red radial light #52090D (0.22)
- sparse deterministic film dust (36 dots, seed 42) + vignette + grain
- aged photo card 760x480 at (960,430): torn edge (~7px), faded grade,
  pink wash #D9A7A0 @0.14, scanlines inside, soft halo behind
- white divider 420x3 + "TORINO 1978" 64px #F3CA43 double glow
- closing slice glitch (frames 130-139): 8 bands, +/-80px, RGB split 5px,
  mosaic 12px blocks

OOM-safe: static layers baked once (float32), one frame at a time piped
to ffmpeg via stdin. Peak ~150MB.
"""
import gc
import hashlib
import json
import os
import subprocess
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                   "..", "..", "out", "vintage_documentary_v1")
PNGDIR = os.path.join(OUT, "png")
MP4DIR = os.path.join(OUT, "mp4")
W, H = 1920, 1080
FPS, SECONDS = 30, 5
FRAMES = FPS * SECONDS

# Recipe values (mirror catalog/vintage_documentary.v1.json)
PHOTO_W, PHOTO_H = 760, 480
PHOTO_CX, PHOTO_CY = 960, 430
TITLE_Y = 790
TITLE_TEXT = "TORINO 1978"
GLITCH_START, GLITCH_DUR = 130, 10


def hexrgb(s):
    s = s.lstrip("#")
    return np.array([int(s[0:2], 16), int(s[2:4], 16), int(s[4:6], 16)],
                    dtype=np.float32)


def smooth_walk(rng, n, step):
    w = np.cumsum(rng.normal(0, step, n).astype(np.float64))
    w -= w.mean()
    return w.astype(np.float32)


def torn_mask(w, h, amount, seed, radius):
    """Jagged torn-paper alpha for a w*h card + rounded corners."""
    rng = np.random.default_rng(seed)
    mask = np.ones((h, w), dtype=np.float32)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    # Displace each edge with smoothed noise (~amount px peak).
    top = smooth_walk(rng, w, amount * 0.45)
    bot = smooth_walk(rng, w, amount * 0.45)
    lft = smooth_walk(rng, h, amount * 0.45)
    rgt = smooth_walk(rng, h, amount * 0.45)
    top = (top - top.min()) / (max(top.max() - top.min(), 1e-6)) * amount * 2
    bot = (bot - bot.min()) / (max(bot.max() - bot.min(), 1e-6)) * amount * 2
    lft = (lft - lft.min()) / (max(lft.max() - lft.min(), 1e-6)) * amount * 2
    rgt = (rgt - rgt.min()) / (max(rgt.max() - rgt.min(), 1e-6)) * amount * 2
    # A few deeper tears.
    for _ in range(6):
        x = rng.integers(0, w)
        top[max(0, x - 3):x + 3] += rng.uniform(amount, amount * 2.2)
    for _ in range(6):
        x = rng.integers(0, w)
        bot[max(0, x - 3):x + 3] += rng.uniform(amount, amount * 2.2)
    mask[yy < top[None, :]] = 0
    mask[yy > (h - 1 - bot[None, :])] = 0
    mask[xx < lft[:, None]] = 0
    mask[xx > (w - 1 - rgt[:, None])] = 0
    # Rounded corners (q = distance in from the two corner edges).
    if radius > 0:
        cy, cx = np.mgrid[0:h, 0:w].astype(np.float32)
        for (oy, ox) in ((0, 0), (0, w - 1), (h - 1, 0), (h - 1, w - 1)):
            qy = cy if oy == 0 else oy - cy
            qx = cx if ox == 0 else ox - cx
            corner = (qx < radius) & (qy < radius)
            outside = corner & ((qx - radius + 1) ** 2 +
                                (qy - radius + 1) ** 2 > radius ** 2)
            mask[outside] = 0
    # 1px feather.
    soft = Image.fromarray((mask * 255).astype(np.uint8)).filter(
        ImageFilter.GaussianBlur(0.8))
    return np.asarray(soft, dtype=np.float32) / 255.0


def aged_photo(w, h, seed):
    """Procedural sun-faded landscape, heavily softened like old print."""
    rng = np.random.default_rng(seed)
    yy = np.linspace(0, 1, h, dtype=np.float32)[:, None].repeat(w, axis=1)
    sky = np.stack([205 - 55 * yy, 188 - 58 * yy,
                    178 - 53 * yy], axis=-1)
    horizon = 0.58 + 0.03 * np.sin(
        np.linspace(0, 6.28, w, dtype=np.float32))[None, :].repeat(h, 0)
    hill = np.clip((yy - horizon) * 6, 0, 1)
    hill_col = np.array([96, 82, 78], dtype=np.float32)
    img = sky * (1 - hill[..., None]) + hill_col * hill[..., None]
    fg = np.clip((yy - 0.78) * 8, 0, 1)
    img = img * (1 - fg[..., None]) + np.array([64, 55, 53]) * fg[..., None]
    # Sun-fade blob upper third.
    sy, sx = np.mgrid[0:h, 0:w].astype(np.float32)
    sun = np.exp(-(((sx - w * 0.62) ** 2) / (2 * (w * 0.16) ** 2) +
                   ((sy - h * 0.30) ** 2) / (2 * (h * 0.20) ** 2)))
    img = img * (1 - sun[..., None] * 0.35) + 235 * sun[..., None] * 0.35
    # Dark soft masses (trees / rooftop), then heavy blur = old lens.
    blobs = np.zeros((h, w), dtype=np.float32)
    for _ in range(9):
        bx, by = rng.uniform(0, w), rng.uniform(h * 0.45, h * 0.95)
        br = rng.uniform(w * 0.03, w * 0.09)
        blobs += np.exp(-(((sx - bx) ** 2) + ((sy - by) ** 2)) / (2 * br ** 2))
    blobs = np.clip(blobs, 0, 1)
    blobs = np.clip(blobs, 0, 1)
    dark = np.array([52, 46, 44], dtype=np.float32)
    img = img * (1 - blobs[..., None] * 0.45) + dark * blobs[..., None] * 0.45
    del blobs, sx, sy
    soft = Image.fromarray(np.clip(img, 0, 255).astype(np.uint8))
    soft = soft.filter(ImageFilter.GaussianBlur(3.0))
    img = np.asarray(soft, dtype=np.float32)
    # Faded grade: pull saturation toward warm gray, soften contrast.
    gray = img.mean(axis=-1, keepdims=True)
    img = gray + (img - gray) * 0.72
    img = 128 + (img - 128) * 0.95
    return np.clip(img, 0, 255)


def build_static():
    """Bake bg, card (rgb+alpha), title (rgb+alpha), scan pattern, dust."""
    bg = np.full((H, W, 3), hexrgb("#050505"), dtype=np.float32)
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    dx = (xx - W * 0.5) / (W * 0.62)
    dy = (yy - H * 0.5) / (H * 0.62)
    dist = np.sqrt(dx ** 2 + dy ** 2)
    fall = np.clip(1 - dist, 0, 1) ** 2
    bg = bg * (1 - fall[..., None] * 0.22) + \
        hexrgb("#52090D") * fall[..., None] * 0.22
    del dx, dy, dist, fall
    vig = np.clip((np.sqrt(((xx / W - 0.5) ** 2 +
                            (yy / H - 0.5) ** 2)) - 0.32) / 0.45, 0, 1)
    bg *= (1 - 0.45 * vig[..., None])
    del xx, yy, vig
    gc.collect()

    # Photo card.
    photo = aged_photo(PHOTO_W, PHOTO_H, 7)
    tint = hexrgb("#D9A7A0")
    photo = photo * 0.86 + tint * 0.14
    halo = Image.new("L", (W, H), 0)
    hd = ImageDraw.Draw(halo)
    hx0, hy0 = PHOTO_CX - PHOTO_W * 0.72, PHOTO_CY - PHOTO_H * 0.75
    hx1, hy1 = PHOTO_CX + PHOTO_W * 0.72, PHOTO_CY + PHOTO_H * 0.75
    hd.ellipse([hx0, hy0, hx1, hy1], fill=26)
    halo = halo.filter(ImageFilter.GaussianBlur(18))
    halo_a = np.asarray(halo, dtype=np.float32) / 255.0
    glow_col = hexrgb("#FFF6D8")
    bg = bg * (1 - halo_a[..., None] * 0.10) + \
        glow_col * halo_a[..., None] * 0.10
    del halo, hd, halo_a
    gc.collect()

    mask = torn_mask(PHOTO_W, PHOTO_H, 7.0, 7, 14)
    card_rgb = np.zeros((H, W, 3), dtype=np.float32)
    card_a = np.zeros((H, W), dtype=np.float32)
    x0, y0 = PHOTO_CX - PHOTO_W // 2, PHOTO_CY - PHOTO_H // 2
    card_rgb[y0:y0 + PHOTO_H, x0:x0 + PHOTO_W] = photo
    card_a[y0:y0 + PHOTO_H, x0:x0 + PHOTO_W] = mask
    del photo, mask
    gc.collect()

    # Scanlines INSIDE the photo: precomputed multiplier on card region.
    scan = np.ones((PHOTO_H, PHOTO_W), dtype=np.float32)
    period = max(int(round(1 / 0.004)), 2)
    rows = np.arange(PHOTO_H) % period == 0
    scan[rows] = 1 - 0.06
    scan_full = np.ones((H, W), dtype=np.float32)
    scan_full[y0:y0 + PHOTO_H, x0:x0 + PHOTO_W] = scan
    del scan

    # Title + divider with double glow, baked with alpha.
    font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/"
                              "DejaVuSans-Bold.ttf", 64)
    pad = 90
    tw = 760 + pad * 2
    th = 200 + pad * 2
    txt = Image.new("L", (tw, th), 0)
    ImageDraw.Draw(txt).text((tw // 2, th // 2), TITLE_TEXT, font=font,
                             fill=255, anchor="mm")
    txt_a = np.asarray(txt, dtype=np.float32) / 255.0
    wide = np.asarray(txt.filter(ImageFilter.GaussianBlur(22)),
                      dtype=np.float32) / 255.0 * 0.18
    tight = np.asarray(txt.filter(ImageFilter.GaussianBlur(4)),
                       dtype=np.float32) / 255.0 * 0.45
    tx, ty = PHOTO_CX - tw // 2, TITLE_Y - th // 2
    title_rgb = np.zeros((H, W, 3), dtype=np.float32)
    title_a = np.zeros((H, W), dtype=np.float32)
    y1, y2 = max(ty, 0), min(ty + th, H)
    x1, x2 = max(tx, 0), min(tx + tw, W)
    sy1, sy2 = y1 - ty, y2 - ty
    sx1, sx2 = x1 - tx, x2 - tx
    core = txt_a[sy1:sy2, sx1:sx2]
    halo_mix = np.clip(wide[sy1:sy2, sx1:sx2] +
                       tight[sy1:sy2, sx1:sx2], 0, 1)
    gold, mint = hexrgb("#F3CA43"), hexrgb("#E4E6A0")
    halo_rgb = mint * 0.5 + gold * 0.5
    region = title_rgb[y1:y2, x1:x2]
    region[:] = (halo_rgb * halo_mix[..., None] * (1 - core[..., None]) +
                 gold * core[..., None])
    title_a[y1:y2, x1:x2] = np.clip(core + halo_mix, 0, 1)
    del txt, txt_a, wide, tight, core, halo_mix, region
    gc.collect()
    # Divider rule + halo sandwich.
    rule_y = int(round(TITLE_Y - 64 * 0.9))
    for hh, op in ((9, 0.22 * 0.9), (3, 0.9)):
        rx0 = PHOTO_CX - 420 // 2
        title_rgb[rule_y - hh // 2:rule_y + hh // 2 + 1, rx0:rx0 + 420] = \
            255.0 * op + title_rgb[rule_y - hh // 2:rule_y + hh // 2 + 1,
                                   rx0:rx0 + 420] * (1 - op)
        title_a[rule_y - hh // 2:rule_y + hh // 2 + 1, rx0:rx0 + 420] = \
            np.maximum(title_a[rule_y - hh // 2:rule_y + hh // 2 + 1,
                               rx0:rx0 + 420], op)

    # Deterministic dust (base pos + drift vector + size + phase).
    rng = np.random.default_rng(42)
    dust = np.stack([
        rng.uniform(0, W, 36), rng.uniform(0, H, 36),
        (rng.uniform(0, 1, 36) - 0.5) * 60,
        (rng.uniform(0, 1, 36) - 0.5) * 36,
        2 + rng.uniform(0, 1, 36) * 3,
        rng.uniform(0, 6.28, 36)]).T.astype(np.float32)
    return bg, card_rgb, card_a, title_rgb, title_a, scan_full, dust


def glitch_photo(region, frame_index):
    """Digital slice break on the photo region (H_px,W_px,3 float32)."""
    rng = np.random.default_rng(123 + frame_index * 17)
    h, w, _ = region.shape
    bands = 8
    edges = np.linspace(0, h, bands + 1).astype(int)
    out = region.copy()
    for b in range(bands):
        off = int(rng.integers(-80, 81))
        if off:
            out[edges[b]:edges[b + 1]] = np.roll(
                region[edges[b]:edges[b + 1]], off, axis=1)
        out[edges[b]:edges[b + 1]] += rng.uniform(-10, 10)
    # RGB split: R +5px, B -5px (wrap inside region).
    r = np.roll(out[..., 0], 5, axis=1)
    bl = np.roll(out[..., 2], -5, axis=1)
    out[..., 0], out[..., 2] = r, bl
    # Mosaic 12px blocks.
    bh = 12
    hh, ww = h // bh * bh, w // bh * bh
    crop = out[:hh, :ww].reshape(hh // bh, bh, ww // bh, bh, 3).mean(axis=(1, 3))
    out[:hh, :ww] = crop.repeat(bh, axis=0).repeat(bh, axis=1)
    # 2 black tear lines.
    for _ in range(2):
        y = rng.integers(0, h)
        out[y:y + 2] = 0
    return np.clip(out, 0, 255)


def draw_dust(frame, dust, t):
    for i in range(dust.shape[0]):
        x = dust[i, 0] + dust[i, 2] * t
        y = dust[i, 1] + dust[i, 3] * t
        if x < 0 or x >= W or y < 0 or y >= H:
            continue
        s = int(dust[i, 4])
        tw = 0.6 + 0.4 * np.sin(t * 2.2 + dust[i, 5])
        op = 0.25 * tw
        xi, yi = int(x), int(y)
        x1, x2 = max(xi - s // 2, 0), min(xi + s // 2 + 1, W)
        y1, y2 = max(yi - s // 2, 0), min(yi + s // 2 + 1, H)
        frame[y1:y2, x1:x2] = \
            frame[y1:y2, x1:x2] * (1 - op) + 255.0 * op


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    os.makedirs(PNGDIR, exist_ok=True)
    os.makedirs(MP4DIR, exist_ok=True)
    print("baking static layers ...", flush=True)
    bg, card_rgb, card_a, title_rgb, title_a, scan, dust = build_static()
    x0, y0 = PHOTO_CX - PHOTO_W // 2, PHOTO_CY - PHOTO_H // 2
    mp4 = os.path.join(MP4DIR, "vintage_documentary_sample_v1.mp4")
    cmd = ["ffmpeg", "-y", "-loglevel", "error",
           "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
           "-r", str(FPS), "-i", "-",
           "-c:v", "libx264", "-preset", "medium", "-crf", "18",
           "-pix_fmt", "yuv420p", "-an", mp4]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    preview = None
    for f in range(FRAMES):
        frame = bg.copy()
        card_op = min(f / 20.0, 1.0)
        title_op = min(max((f - 12) / 20.0, 0.0), 1.0)
        a = (card_a * card_op)[..., None]
        card = card_rgb * scan[..., None]
        frame = frame * (1 - a) + card * a
        a2 = (title_a * title_op)[..., None]
        frame = frame * (1 - a2) + title_rgb * a2
        if GLITCH_START <= f < GLITCH_START + GLITCH_DUR:
            region = frame[y0:y0 + PHOTO_H, x0:x0 + PHOTO_W].copy()
            frame[y0:y0 + PHOTO_H, x0:x0 + PHOTO_W] = \
                glitch_photo(region, f)
        t = f / FPS
        draw_dust(frame, dust, t)
        grain = np.random.default_rng(9000 + f).normal(
            0, 2.0, (H, W, 1)).astype(np.float32)
        frame += grain
        del grain
        out8 = np.clip(frame, 0, 255).astype(np.uint8)
        if f == 75:
            preview = out8.copy()
        proc.stdin.write(out8.tobytes())
        del frame, out8, a, a2, card
        if (f + 1) % 30 == 0:
            print(f"  frame {f + 1}/{FRAMES}", flush=True)
    proc.stdin.close()
    proc.wait()
    if proc.returncode != 0:
        raise SystemExit("ffmpeg failed")
    png = os.path.join(PNGDIR, "vintage_documentary_sample_v1.png")
    Image.fromarray(preview).save(png)
    manifest = {"version": 1, "kind": "vintage-documentary-v1",
                "canvas": {"width": W, "height": H, "fps": FPS},
                "duration_seconds": SECONDS,
                "recipe": "../../catalog/vintage_documentary.v1.json",
                "assets": [{"id": "vintage-doc-sample-01",
                            "mp4": os.path.relpath(mp4, OUT),
                            "png": os.path.relpath(png, OUT),
                            "mp4_sha256": sha256(mp4),
                            "png_sha256": sha256(png)}]}
    with open(os.path.join(OUT, "manifest.json"), "w") as fh:
        json.dump(manifest, fh, indent=2)
    print("OK: %s" % OUT)


if __name__ == "__main__":
    sys.exit(main())
