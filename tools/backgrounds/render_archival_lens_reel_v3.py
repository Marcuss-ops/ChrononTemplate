#!/usr/bin/env python3
"""Archival lens reel: 1920x1080 9s MP4, 30fps — three lens looks.

Segments (3s each), lens static, content drifting behind it:
- A WSJ/Reddit article (k=0.07, s=1.07, rgb=1.5, blur=0.8, vig=0.18):
  slow zoom 1.06->1.12 + 25px lateral pan across the page.
- B Vintage CRT Q&A (k=0.17, s=1.10, rgb=2.0, blur=1.5, vig=0.35):
  uncovered warp edges fall to black = curved bezel, content near still.
- C Documentary photo (k=0.035, s=1.04, rgb=0.7, blur=0.4, vig=0.10):
  gentle 1.00->1.05 push on the archive portrait.

Mirrors ArchivalLensLook presets 1:1. OOM-safe: warp index maps baked
once per preset, one frame at a time piped to ffmpeg.
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
FPS = 30
SEG = 90  # 3s per look
FRAMES = SEG * 3
BIG = (2208, 1242)  # 1.15x content overscan for zoom/pan headroom
ARMSTRONG = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                         "..", "..", "assets", "famous_people_trio_v1",
                         "sources", "neil_armstrong.jpg")
GLENN = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                     "..", "..", "assets", "famous_people_trio_v1",
                     "sources", "john_glenn.jpg")
SERIF = "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf"
SANS = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"


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


def article_card():
    w, h = BIG
    img = Image.new("RGB", (w, h), "#F2EDE3")
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, w, 150], fill="#111111")
    d.text((60, 75), "THE DAILY CHRONICLE", font=ImageFont.truetype(SERIF, 64),
           fill="#F5F2EA", anchor="lm")
    d.rectangle([0, 150, w, 162], fill="#8E1B1B")
    d.text((60, 250), "MARKETS RALLY", font=ImageFont.truetype(SERIF, 120),
           fill="#141414")
    d.text((60, 400), "Wall Street posts its strongest week since 2011",
           font=ImageFont.truetype(SERIF, 44), fill="#4A4A4A")
    d.rectangle([60, 470, w - 60, 478], fill="#8E1B1B")
    y = 530
    for _ in range(9):
        d.rounded_rectangle([60, y, w // 2 - 40, y + 22], radius=11, fill="#B9B2A4")
        d.rounded_rectangle([w // 2 + 40, y, w - 60, y + 22], radius=11, fill="#B9B2A4")
        y += 52
    # Photo block with caption.
    ph = cover(ARMSTRONG, 620, 420)
    img.paste(ph, (w - 700, h - 520))
    d.rectangle([w - 700, h - 520, w - 80, h - 100], outline="#141414", width=4)
    d.text((w - 700, h - 84), "Archive photo, 1969",
           font=ImageFont.truetype(SERIF, 30), fill="#4A4A4A")
    return img


def qa_card():
    # Real portrait at the center: two-column broadcast card, Glenn left,
    # Q&A text right. No fully-procedural people.
    w, h = BIG
    img = Image.new("RGB", (w, h), "#0E1420")
    portrait = cover(GLENN, 760, 960)
    img.paste(portrait, (90, 140))
    d = ImageDraw.Draw(img)
    d.rectangle([90, 140, 850, 1100], outline="#C9A227", width=5)
    d.rounded_rectangle([950, 140, 1220, 250], radius=18, fill="#C9A227")
    d.text((1085, 195), "Q&A", font=ImageFont.truetype(SANS, 72),
           fill="#0E1420", anchor="mm")
    d.text((950, 330), "Who flew first?",
           font=ImageFont.truetype(SANS, 76), fill="#F2F4F8")
    y = 500
    for line, ln in (("Friendship 7, three orbits", 0),
                     ("of the Earth, 1962.", 1),
                     ("The portrait that opened", 2),
                     ("the Space Age.", 3)):
        shade = 168 - ln * 10
        col = "#%02X%02X%02X" % (shade, shade + 6, shade + 12)
        d.text((950, y), line, font=ImageFont.truetype(SANS, 52), fill=col)
        y += 92
    d.ellipse([950, h - 160, 990, h - 120], fill="#C22A2A")
    d.text((1015, h - 140), "ARCHIVE FOOTAGE",
           font=ImageFont.truetype(SANS, 36), fill="#8B93A3", anchor="lm")
    d.text((90, h - 90), "John Glenn  -  NASA portrait, 1962",
           font=ImageFont.truetype(SERIF, 32), fill="#8B93A3")
    return img


def build_warp(k, scale):
    """Bilinear sample maps for barrel warp; uncovered pixels -> black."""
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    aspect = W / H
    nx = (xx / W - 0.5) * aspect
    ny = yy / H - 0.5
    r2 = nx * nx + ny * ny
    factor = (1.0 + k * r2) / scale
    sx = (nx * factor / aspect + 0.5) * W
    sy = (ny * factor + 0.5) * H
    inside = (sx >= 0) & (sx <= W - 1.001) & (sy >= 0) & (sy <= H - 1.001)
    sx = np.clip(sx, 0, W - 1.001)
    sy = np.clip(sy, 0, H - 1.001)
    x0 = sx.astype(np.int32)
    y0 = sy.astype(np.int32)
    x1 = np.minimum(x0 + 1, W - 1)
    y1 = np.minimum(y0 + 1, H - 1)
    wx = (sx - x0).astype(np.float32)
    wy = (sy - y0).astype(np.float32)
    return y0, x0, y1, x1, wx, wy, inside.astype(np.float32)


def apply_warp(content, maps):
    y0, x0, y1, x1, wx, wy, inside = maps
    c00 = content[y0, x0]
    c10 = content[y0, x1]
    c01 = content[y1, x0]
    c11 = content[y1, x1]
    top = c00 * (1 - wx[..., None]) + c10 * wx[..., None]
    bot = c01 * (1 - wx[..., None]) + c11 * wx[..., None]
    out = top * (1 - wy[..., None]) + bot * wy[..., None]
    return out * inside[..., None]


def rgb_split(img, px):
    out = img.copy()
    out[..., 0] = np.roll(img[..., 0], px, axis=1)
    out[..., 2] = np.roll(img[..., 2], -px, axis=1)
    return out


def viewport(baked, zoom, panx, pany=0.0):
    # Single affine resample with FLOAT pan/zoom: output pixel (ox,oy)
    # samples the baked card at center + ((o - out_center + pan) / zoom).
    # No integer crop steps, so slow drifts stay stepless (no judder).
    bw, bh = baked.size
    cx, cy = bw * 0.5, bh * 0.5
    inv = 1.0 / zoom
    return baked.transform(
        (W, H), Image.AFFINE,
        (inv, 0.0, cx - (W * 0.5 - panx) * inv,
         0.0, inv, cy - (H * 0.5 - pany) * inv),
        resample=Image.BILINEAR)


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    os.makedirs(PNGDIR, exist_ok=True)
    os.makedirs(MP4DIR, exist_ok=True)
    print("baking content cards ...", flush=True)
    card_a = article_card()
    card_b = qa_card()
    card_c = cover(ARMSTRONG, *BIG)
    segs = [
        {"k": 0.07, "s": 1.07, "rgb": 2, "blur": 0.8,
         "grain": 0.8, "vig": 0.18, "card": card_a, "id": "wsj_reddit"},
        {"k": 0.17, "s": 1.10, "rgb": 2, "blur": 1.5,
         "grain": 1.0, "vig": 0.35, "card": card_b, "id": "vintage_crt"},
        {"k": 0.035, "s": 1.04, "rgb": 1, "blur": 0.4,
         "grain": 0.6, "vig": 0.10, "card": card_c, "id": "documentary"},
    ]
    print("baking warp maps ...", flush=True)
    for sg in segs:
        sg["maps"] = build_warp(sg["k"], sg["s"])
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
        dist = np.sqrt((xx / W - 0.5) ** 2 + (yy / H - 0.5) ** 2)
        sg["vigmap"] = (1 - sg["vig"] * np.clip((dist - 0.32) / 0.45, 0, 1))
        del yy, xx, dist
    gc.collect()
    mp4 = os.path.join(MP4DIR, "archival_lens_reel_v3.mp4")
    cmd = ["ffmpeg", "-y", "-loglevel", "error",
           "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
           "-r", str(FPS), "-i", "-",
           "-c:v", "libx264", "-preset", "medium", "-crf", "18",
           "-pix_fmt", "yuv420p", "-an", mp4]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    previews = {}
    for f in range(FRAMES):
        si, local = f // SEG, f % SEG
        sg = segs[si]
        p = local / (SEG - 1)
        if si == 0:
            zoom, panx, pany = 1.06 + 0.05 * p, 22 * p, 0.0
        elif si == 1:
            zoom, panx, pany = 1.0, 3 * np.sin(2 * np.pi * p), 2 * np.sin(4 * np.pi * p)
        else:
            zoom, panx, pany = 1.0 + 0.05 * p, 0.0, 0.0
        vp = viewport(sg["card"], zoom, panx, pany)
        frame = np.asarray(vp, dtype=np.float32)
        del vp
        frame = apply_warp(frame, sg["maps"])
        frame = rgb_split(frame, sg["rgb"])
        frame = np.asarray(Image.fromarray(np.clip(frame, 0, 255).astype(np.uint8))
                           .filter(ImageFilter.GaussianBlur(sg["blur"])), dtype=np.float32)
        frame *= sg["vigmap"][..., None]
        frame += np.random.default_rng(5000 + f).normal(0, sg["grain"], (H, W, 1)).astype(np.float32)
        out8 = np.clip(frame, 0, 255).astype(np.uint8)
        if f in (45, 135, 225):
            previews[f] = out8.copy()
        proc.stdin.write(out8.tobytes())
        del frame, out8
        if (f + 1) % 45 == 0:
            print(f"  frame {f + 1}/{FRAMES}", flush=True)
    proc.stdin.close()
    proc.wait()
    if proc.returncode != 0:
        raise SystemExit("ffmpeg failed")
    pngs = {}
    for f, img in previews.items():
        png = os.path.join(PNGDIR, f"archival_lens_v3_{f}.png")
        Image.fromarray(img).save(png)
        pngs[str(f)] = {"png": os.path.relpath(png, OUT), "png_sha256": sha256(png)}
    # Same folder manifest: keep the v1 reel entry, append v2 (real center
    # portrait, calmed grain/drift). Drive ids for v1 already recorded.
    manifest_path = os.path.join(OUT, "manifest.json")
    if os.path.exists(manifest_path):
        manifest = json.load(open(manifest_path))
    else:
        manifest = {"version": 1, "kind": "archival-lens-v1",
                    "canvas": {"width": W, "height": H, "fps": FPS},
                    "assets": []}
    manifest["version"] = 2
    manifest["duration_seconds"] = FRAMES / FPS
    manifest["presets"] = [{k: sg[k] for k in ("k", "s", "rgb", "blur", "grain", "vig", "id")} for sg in segs]
    manifest["rgb_note"] = "integer px (rounded from 1.5/2.0/0.7)"
    manifest["v3_note"] = "affine subpixel viewport (no crop judder); calmer moves; same lens/grain as v2"
    manifest["assets"] = [a for a in manifest.get("assets", [])
                            if a.get("id") != "archival-lens-reel-03"]
    manifest["assets"].append({"id": "archival-lens-reel-03",
                                "mp4": os.path.relpath(mp4, OUT),
                                "mp4_sha256": sha256(mp4), "previews": pngs})
    with open(manifest_path, "w") as fh:
        json.dump(manifest, fh, indent=2)
    print("OK: %s" % OUT)


if __name__ == "__main__":
    sys.exit(main())
