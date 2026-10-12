#!/usr/bin/env python3
"""Centerpiece stretched shot: 1920x1080 5s MP4, 30fps.

A medium portrait card (720x900, Sally Ride) at canvas center — never
fullscreen — under a strong edge-stretching lens (k=0.20, scale=1.14,
extra outward magnification +0.18 toward the edges), RGB split, soft
blur, calm grain, vignette. One slow push 1.00->1.02, affine subpixel.
Mirrors CenterpieceStretched 1:1.
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
                   "..", "..", "out", "archival_lens_v1")
PNGDIR = os.path.join(OUT, "png")
MP4DIR = os.path.join(OUT, "mp4")
W, H = 1920, 1080
FPS, SECONDS = 30, 5
FRAMES = FPS * SECONDS
CARD_W, CARD_H = 720, 900
RIDE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                    "..", "..", "assets", "famous_people_trio_v1",
                    "sources", "sally_ride.jpg")
SERIF = "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf"
SANS = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
K, SCALE, STRETCH = 0.20, 1.14, 0.18


def hexrgb(s):
    s = s.lstrip("#")
    return np.array([int(s[0:2], 16), int(s[2:4], 16), int(s[4:6], 16)],
                    dtype=np.float32)


def cover(path, w, h):
    img = Image.open(path).convert("RGB")
    sw, sh = img.size
    s = max(w / sw, h / sh)
    img = img.resize((int(sw * s + 0.5), int(sh * s + 0.5)), Image.LANCZOS)
    l = (img.size[0] - w) // 2
    t = (img.size[1] - h) // 2
    return img.crop((l, t, l + w, t + h))


def smoothstep(a, b, x):
    t = np.clip((x - a) / (b - a), 0, 1).astype(np.float32)
    return t * t * (3 - 2 * t)


def build_warp():
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    aspect = W / H
    nx = (xx / W - 0.5) * aspect
    ny = yy / H - 0.5
    r = np.sqrt(nx * nx + ny * ny)
    factor = (1.0 + K * r * r) / SCALE * (1.0 + STRETCH * smoothstep(0.3, 0.75, r))
    sx = (nx * factor / aspect + 0.5) * W
    sy = (ny * factor + 0.5) * H
    inside = (sx >= 0) & (sx <= W - 1.001) & (sy >= 0) & (sy <= H - 1.001)
    sx = np.clip(sx, 0, W - 1.001)
    sy = np.clip(sy, 0, H - 1.001)
    x0 = sx.astype(np.int32)
    y0 = sy.astype(np.int32)
    x1 = np.minimum(x0 + 1, W - 1)
    y1 = np.minimum(y0 + 1, H - 1)
    return y0, x0, y1, x1, (sx - x0).astype(np.float32), \
        (sy - y0).astype(np.float32), inside.astype(np.float32)


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    os.makedirs(PNGDIR, exist_ok=True)
    os.makedirs(MP4DIR, exist_ok=True)
    print("baking ...", flush=True)
    bg = np.full((H, W, 3), hexrgb("#08080A"), dtype=np.float32)
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    dx = (xx - W * 0.5) / (W * 0.62)
    dy = (yy - H * 0.5) / (H * 0.62)
    fall = np.clip(1 - np.sqrt(dx ** 2 + dy ** 2), 0, 1) ** 2
    bg = bg * (1 - fall[..., None] * 0.15) + hexrgb("#4A0D12") * fall[..., None] * 0.15
    del dx, dy, fall
    vig = np.clip((np.sqrt(((xx / W - 0.5) ** 2 + (yy / H - 0.5) ** 2)) - 0.32) / 0.45, 0, 1)
    vigmap = 1 - 0.30 * vig
    del xx, yy, vig
    photo_big = cover(RIDE, int(CARD_W * 1.15), int(CARD_H * 1.15))
    # Caption strip below the centered card (no plate, bg shows through).
    cap = Image.new("RGB", (840, 54), "#08080A")
    d = ImageDraw.Draw(cap)
    d.text((20, 5), "SALLY RIDE  -  1983", font=ImageFont.truetype(SANS, 36),
           fill="#C9A227")
    maps = build_warp()
    y0, x0, y1, x1, wx, wy, inside = maps
    mp4 = os.path.join(MP4DIR, "centerpiece_stretched_v1.mp4")
    cmd = ["ffmpeg", "-y", "-loglevel", "error",
           "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
           "-r", str(FPS), "-i", "-",
           "-c:v", "libx264", "-preset", "medium", "-crf", "18",
           "-pix_fmt", "yuv420p", "-an", mp4]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    preview = None
    bw, bh = photo_big.size
    for f in range(FRAMES):
        p = f / (FRAMES - 1)
        p = p * p * (3 - 2 * p)
        zoom = 1.0 + 0.02 * p
        card = photo_big.transform(
            (CARD_W, CARD_H), Image.AFFINE,
            (1 / zoom, 0.0, bw * 0.5 - (CARD_W * 0.5) / zoom,
             0.0, 1 / zoom, bh * 0.5 - (CARD_H * 0.5) / zoom),
            resample=Image.BILINEAR)
        frame = bg.copy()
        cx0, cy0 = (W - CARD_W) // 2, (H - CARD_H) // 2
        frame[cy0:cy0 + CARD_H, cx0:cx0 + CARD_W] = np.asarray(card, dtype=np.float32)
        capx0 = (W - 840) // 2
        frame[1000:1054, capx0:capx0 + 840] = np.asarray(cap, dtype=np.float32)
        del card
        c00 = frame[y0, x0]
        c10 = frame[y0, x1]
        c01 = frame[y1, x0]
        c11 = frame[y1, x1]
        top = c00 * (1 - wx[..., None]) + c10 * wx[..., None]
        bot = c01 * (1 - wx[..., None]) + c11 * wx[..., None]
        frame = (top * (1 - wy[..., None]) + bot * wy[..., None]) * inside[..., None]
        del c00, c10, c01, c11, top, bot
        out = frame.copy()
        out[..., 0] = np.roll(frame[..., 0], 2, axis=1)
        out[..., 2] = np.roll(frame[..., 2], -2, axis=1)
        frame = np.asarray(Image.fromarray(np.clip(out, 0, 255).astype(np.uint8))
                           .filter(ImageFilter.GaussianBlur(1.0)), dtype=np.float32)
        del out
        frame *= vigmap[..., None]
        frame += np.random.default_rng(7000 + f).normal(0, 1.5, (H, W, 1)).astype(np.float32)
        out8 = np.clip(frame, 0, 255).astype(np.uint8)
        if f == 75:
            preview = out8.copy()
        proc.stdin.write(out8.tobytes())
        del frame, out8
        if (f + 1) % 50 == 0:
            print(f"  frame {f + 1}/{FRAMES}", flush=True)
    proc.stdin.close()
    proc.wait()
    if proc.returncode != 0:
        raise SystemExit("ffmpeg failed")
    png = os.path.join(PNGDIR, "centerpiece_stretched_v1.png")
    Image.fromarray(preview).save(png)
    manifest_path = os.path.join(OUT, "manifest.json")
    manifest = json.load(open(manifest_path))
    manifest["assets"] = [a for a in manifest.get("assets", [])
                          if a.get("id") != "centerpiece-stretched-01"]
    manifest["assets"].append({"id": "centerpiece-stretched-01",
                              "mp4": "mp4/centerpiece_stretched_v1.mp4",
                              "mp4_sha256": sha256(mp4),
                              "png": os.path.relpath(png, OUT),
                              "png_sha256": sha256(png),
                              "note": "Ride 720x900 centerpiece, edge stretch 0.18, push 1.00-1.02"})
    json.dump(manifest, open(manifest_path, "w"), indent=2)
    print("OK: %s" % OUT)


if __name__ == "__main__":
    sys.exit(main())
