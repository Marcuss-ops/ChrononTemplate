#!/usr/bin/env python3
"""Apollo style reel: 20 clips (4 groups x 5), 1920x1080 30fps, hero card
centered, real Armstrong/Glenn portraits. OOM-safe (one clip, one frame
at a time; heavy plates precomputed once per clip).
Groups: grid (pixel-grid + blur backdrop), stroke (orange sides),
glow (halo plates), rgb (anaglyph channel splits).
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
                   "..", "..", "out", "apollo_style_v1")
PNGDIR = os.path.join(OUT, "png")
MP4DIR = os.path.join(OUT, "mp4")
W, H = 1920, 1080
FPS = 30
NF = 120
ARMSTRONG = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                         "..", "..", "assets", "famous_people_trio_v1",
                         "sources", "neil_armstrong.jpg")
GLENN = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                     "..", "..", "assets", "famous_people_trio_v1",
                     "sources", "john_glenn.jpg")
SANS = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
CW, CH = 640, 800  # hero card
CX, CY = 960, 540
X0, Y0 = CX - CW // 2, CY - CH // 2


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


def smooth(p):
    p = min(max(p, 0.0), 1.0)
    return p * p * (3 - 2 * p)


def ease_out(p):
    p = min(max(p, 0.0), 1.0)
    return 1 - (1 - p) * (1 - p)


def grain(frame, seed, sigma):
    frame += np.random.default_rng(seed).normal(0, sigma, (H, W, 1)).astype(np.float32)
    return frame


def vignette(frame, strength):
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    dist = np.sqrt((xx / W - 0.5) ** 2 + (yy / H - 0.5) ** 2)
    frame *= (1 - strength * np.clip((dist - 0.32) / 0.45, 0, 1))[..., None]
    del yy, xx, dist
    return frame


def dark_bg():
    bg = np.full((H, W, 3), hexrgb("#08080A"), dtype=np.float32)
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    dx = (xx - W * 0.5) / (W * 0.62)
    dy = (yy - H * 0.5) / (H * 0.62)
    fall = np.clip(1 - np.sqrt(dx ** 2 + dy ** 2), 0, 1) ** 2
    bg = bg * (1 - fall[..., None] * 0.15) + np.array([74, 13, 18], dtype=np.float32) * fall[..., None] * 0.15
    del yy, xx, dx, dy, fall
    return bg


def paste(frame, img_f, cx, cy, op=1.0):
    """Paste float32 (h,w,3) image centered at (cx,cy) with opacity."""
    h, w = img_f.shape[:2]
    x1, y1 = int(cx - w / 2), int(cy - h / 2)
    x0c, y0c = max(x1, 0), max(y1, 0)
    x1c, y1c = min(x1 + w, W), min(y1 + h, H)
    if x1c <= x0c or y1c <= y0c:
        return frame
    src = img_f[y0c - y1:y1c - y1, x0c - x1:x1c - x1]
    frame[y0c:y1c, x0c:x1c] = frame[y0c:y1c, x0c:x1c] * (1 - op) + src * op
    return frame


def zoomed(card_big, zoom, cx=0.5, cy=0.5):
    bw, bh = card_big.size
    inv = 1.0 / zoom
    return card_big.transform(
        (CW, CH), Image.AFFINE,
        (inv, 0.0, bw * cx - CW * 0.5 * inv, 0.0, inv, bh * cy - CH * 0.5 * inv),
        resample=Image.BILINEAR)


def caption(frame, text, op=1.0):
    txt = Image.new("L", (700, 60), 0)
    ImageDraw.Draw(txt).text((350, 30), text,
                             font=ImageFont.truetype(SANS, 40), fill=255, anchor="mm")
    ta = np.asarray(txt, dtype=np.float32) / 255.0 * op
    region = frame[H - 110:H - 50, W // 2 - 350:W // 2 + 350]
    region[:] = region * (1 - ta[..., None]) + \
        np.array([200, 200, 205], dtype=np.float32) * ta[..., None]


def encode(frames_iter, nframes, mp4):
    cmd = ["ffmpeg", "-y", "-loglevel", "error",
           "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
           "-r", str(FPS), "-i", "-",
           "-c:v", "libx264", "-preset", "medium", "-crf", "18",
           "-pix_fmt", "yuv420p", "-an", mp4]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    preview = None
    for f in range(nframes):
        out8 = next(frames_iter)
        if f == nframes // 2:
            preview = out8.copy()
        proc.stdin.write(out8.tobytes())
        del out8
    proc.stdin.close()
    proc.wait()
    if proc.returncode != 0:
        raise SystemExit("ffmpeg failed for " + mp4)
    return preview


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def grid_backdrop(src):
    """Full-bleed dimmed blurred copy + lattice, precomputed once."""
    big = cover(src, W, H).filter(ImageFilter.GaussianBlur(18))
    a = np.asarray(big, dtype=np.float32) * 0.55
    img = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))
    dr = ImageDraw.Draw(img)
    for x in range(0, W + 1, 96):
        dr.line([(x, 0), (x, H)], fill=(138, 143, 152), width=2)
    for y in range(0, H + 1, 96):
        dr.line([(0, y), (W, y)], fill=(138, 143, 152), width=2)
    out = np.asarray(img, dtype=np.float32)
    del big, img
    return out


def grid_frames(variant, src, tag):
    back = grid_backdrop(src)
    card_big = cover(src, int(CW * 1.25), int(CH * 1.25))
    f = 0
    while True:
        fade = min(f / 16, 1.0)
        if f > NF - 16:
            fade = min(fade, (NF - f) / 16)
        frame = dark_bg() * (1 - fade) + back * fade
        if variant == "reveal":
            z = 0.90 + 0.12 * ease_out(f / 88)
            card = np.asarray(zoomed(card_big, z), dtype=np.float32)
            cop = min(f / 20, 1.0)
        elif variant == "step":
            sched = [(0, 48), (12, 24), (24, 12), (36, 6), (48, 1)]
            b = 1
            for onset, bb in sched:
                if f >= onset:
                    b = bb
            small = card_big.resize((max(CW // b, 4), max(CH // b, 4)), Image.BILINEAR)
            card = np.asarray(small.resize((CW, CH), Image.NEAREST), dtype=np.float32)
            cop = min(f / 16, 1.0)
        elif variant == "zoomout":
            z = 1.12 - 0.12 * ease_out(f / 96)
            card = np.asarray(zoomed(card_big, z), dtype=np.float32)
            cop = min(f / 20, 1.0)
        elif variant == "tiles":
            p = ease_out(f / 72)
            card = np.asarray(card_big.resize((CW, CH), Image.LANCZOS), dtype=np.float32)
            cop = min(f / 18, 1.0)
            frame = paste(frame, card, CX - 260 * (1 - p), CY, cop * fade)
            card = None
        elif variant == "breathe":
            import math
            z = 1.0 + 0.03 * math.sin(min(f / 96, 1.0) * math.pi)
            card = np.asarray(zoomed(card_big, z), dtype=np.float32)
            cop = min(f / 24, 1.0)
        if variant != "tiles":
            frame = paste(frame, card, CX, CY, cop * fade)
            del card
        caption(frame, tag, fade)
        frame = vignette(frame, 0.25)
        frame = grain(frame, 9000 + f, 1.0)
        f += 1
        yield np.clip(frame, 0, 255).astype(np.uint8)
        del frame
        if f >= NF:
            return


ORANGE = np.array([255, 122, 26], dtype=np.float32)


def stroke_frames(variant, src, tag):
    card_big = cover(src, int(CW * 1.25), int(CH * 1.25))
    f = 0
    while True:
        fade = min(f / 16, 1.0)
        if f > NF - 16:
            fade = min(fade, (NF - f) / 16)
        frame = dark_bg()
        p = ease_out(f / 88)
        z = 0.92 + 0.08 * p
        cf = np.asarray(zoomed(card_big, z), dtype=np.float32)
        cop = min(f / 20, 1.0) * fade
        frame = paste(frame, cf, CX, CY, cop)
        del cf
        sop = smooth((f - 6) / 24) * fade
        yy, xx = np.mgrid[Y0:Y0 + CH, X0:X0 + CW].astype(np.float32)
        lx, rx, ty, by = xx - X0, xx - X0, yy - Y0, yy - Y0
        if variant == "left":
            m = np.abs(lx - 18) < 5
            frame[Y0:Y0 + CH, X0:X0 + CW][m] = \
                frame[Y0:Y0 + CH, X0:X0 + CW][m] * (1 - sop) + ORANGE * sop
        elif variant == "right":
            m = np.abs(rx - (CW - 18)) < 5
            frame[Y0:Y0 + CH, X0:X0 + CW][m] = \
                frame[Y0:Y0 + CH, X0:X0 + CW][m] * (1 - sop) + ORANGE * sop
        elif variant == "duo":
            m = (np.abs(lx - 18) < 5) | (np.abs(rx - (CW - 18)) < 5)
            frame[Y0:Y0 + CH, X0:X0 + CW][m] = \
                frame[Y0:Y0 + CH, X0:X0 + CW][m] * (1 - sop) + ORANGE * sop
        elif variant == "topbottom":
            m = (np.abs(ty - 18) < 5) | (np.abs(by - (CH - 18)) < 5)
            frame[Y0:Y0 + CH, X0:X0 + CW][m] = \
                frame[Y0:Y0 + CH, X0:X0 + CW][m] * (1 - sop) + ORANGE * sop
        elif variant == "sweep":
            sx = 18 + (CW - 36) * smooth((f - 10) / 50)
            m = np.abs(lx - sx) < 5
            frame[Y0:Y0 + CH, X0:X0 + CW][m] = \
                frame[Y0:Y0 + CH, X0:X0 + CW][m] * (1 - sop) + ORANGE * sop
        del yy, xx, lx, rx, ty, by
        caption(frame, tag, fade)
        frame = vignette(frame, 0.25)
        frame = grain(frame, 9100 + f, 1.0)
        f += 1
        yield np.clip(frame, 0, 255).astype(np.uint8)
        del frame
        if f >= NF:
            return


def glow_plate(src, color):
    """Blurred tinted silhouette, precomputed once per clip."""
    card = cover(src, CW, CH)
    lum = np.asarray(card.convert("L"), dtype=np.float32) / 255.0
    soft = cover(src, CW, CH).filter(ImageFilter.GaussianBlur(36))
    a = np.asarray(soft, dtype=np.float32)
    tint = np.asarray(color, dtype=np.float32)
    plate = a * 0.35 + tint[None, None, :] * (lum[..., None] * 0.65)
    big = Image.fromarray(np.clip(plate, 0, 255).astype(np.uint8))
    big = big.resize((CW + 160, CH + 160), Image.BILINEAR)
    out = np.asarray(big, dtype=np.float32)
    del card, soft, big
    return out


def glow_frames(color, pulse, src, tag):
    plate = glow_plate(src, np.array(color, dtype=np.float32))
    card_big = cover(src, int(CW * 1.25), int(CH * 1.25))
    f = 0
    while True:
        fade = min(f / 16, 1.0)
        if f > NF - 16:
            fade = min(fade, (NF - f) / 16)
        frame = dark_bg()
        if pulse:
            inten = 0.5 - 0.22 * smooth(((f - 48) % 72) / 72 * 2 % 1.0) if f >= 48 else 0.5 * min(f / 30, 1.0)
        else:
            inten = 0.5 * min(f / 30, 1.0)
        frame = paste(frame, plate, CX, CY, inten * fade)
        z = 0.90 + 0.14 * ease_out(f / 88) if pulse else 0.92 + 0.08 * ease_out(f / 88)
        card = np.asarray(zoomed(card_big, min(z, 1.04)), dtype=np.float32)
        frame = paste(frame, card, CX, CY, min(f / 20, 1.0) * fade)
        del card
        caption(frame, tag, fade)
        frame = vignette(frame, 0.25)
        frame = grain(frame, 9200 + f, 1.0)
        f += 1
        yield np.clip(frame, 0, 255).astype(np.uint8)
        del frame
        if f >= NF:
            return


def shift_ch(a, d):
    """Shift a 2D channel horizontally by d px (zero-fill)."""
    d = int(round(d))
    out = np.zeros_like(a)
    if d > 0:
        out[:, d:] = a[:, :-d]
    elif d < 0:
        out[:, :d] = a[:, -d:]
    else:
        out[:] = a
    return out


def rgb_frames(variant, src, tag):
    base = np.asarray(cover(src, CW, CH), dtype=np.float32)
    f = 0
    while True:
        fade = min(f / 16, 1.0)
        if f > NF - 16:
            fade = min(fade, (NF - f) / 16)
        frame = dark_bg()
        if variant == "static":
            d = 10.0
        elif variant == "converge":
            d = 40 - 32 * ease_out(f / 48)
        elif variant == "pulse":
            import math
            d = 8 + 6 * math.sin(f / 12.0) if f >= 48 else 8.0
        elif variant == "glitch":
            rng = np.random.default_rng(9300 + f)
            d = float(rng.integers(4, 22)) if 30 <= f <= 90 else 8.0
        elif variant == "exit":
            d = 8 + 32 * smooth((f - 100) / 32) if f >= 100 else 8.0
        card = np.zeros((CH, CW, 3), dtype=np.float32)
        card[..., 0] = shift_ch(base[..., 0], -d)
        card[..., 1] = base[..., 1]
        card[..., 2] = shift_ch(base[..., 2], d)
        if variant == "glitch" and 30 <= f <= 90:
            rng = np.random.default_rng(9400 + f)
            for _ in range(3):
                y = int(rng.integers(0, CH - 40))
                card[y:y + 40] = np.roll(card[y:y + 40], int(rng.integers(-24, 25)), axis=1)
        # thin channel edge bars
        yy, xx = np.mgrid[0:CH, 0:CW]
        card[(np.abs(xx - 10) < 7)] *= 0.4
        card[(np.abs(xx - 10) < 7), 0] += 200 * 0.6
        card[(np.abs(xx - (CW - 10)) < 7)] *= 0.4
        card[(np.abs(xx - (CW - 10)) < 7), 2] += 200 * 0.6
        del yy, xx
        cop = min(f / 20, 1.0) * fade
        frame = paste(frame, card, CX, CY, cop)
        del card
        caption(frame, tag, fade)
        frame = vignette(frame, 0.25)
        frame = grain(frame, 9300 + f * 2, 1.0)
        f += 1
        yield np.clip(frame, 0, 255).astype(np.uint8)
        del frame
        if f >= NF:
            return


CLIPS = [
    ("grid_reveal", "reveal", ARMSTRONG, "APOLLO 11  \u2022  PIXEL GRID"),
    ("grid_step", "step", GLENN, "FRIENDSHIP 7  \u2022  PIXEL STEP"),
    ("grid_zoomout", "zoomout", ARMSTRONG, "APOLLO 11  \u2022  GRID ZOOM"),
    ("grid_tiles", "tiles", GLENN, "FRIENDSHIP 7  \u2022  GRID TILES"),
    ("grid_breathe", "breathe", ARMSTRONG, "APOLLO 11  \u2022  GRID BREATHE"),
    ("stroke_left", "left", ARMSTRONG, "APOLLO 11  \u2022  EDGE LEFT"),
    ("stroke_right", "right", GLENN, "FRIENDSHIP 7  \u2022  EDGE RIGHT"),
    ("stroke_duo", "duo", ARMSTRONG, "APOLLO 11  \u2022  EDGE DUO"),
    ("stroke_topbottom", "topbottom", GLENN, "FRIENDSHIP 7  \u2022  EDGE TOP+BOTTOM"),
    ("stroke_sweep", "sweep", ARMSTRONG, "APOLLO 11  \u2022  EDGE SWEEP"),
    ("glow_warm", (255, 138, 61), ARMSTRONG, "APOLLO 11  \u2022  WARM GLOW"),
    ("glow_cool", (56, 189, 248), GLENN, "FRIENDSHIP 7  \u2022  COOL GLOW"),
    ("glow_gold", (232, 184, 74), ARMSTRONG, "APOLLO 11  \u2022  GOLD GLOW"),
    ("glow_rose", (244, 114, 182), GLENN, "FRIENDSHIP 7  \u2022  ROSE GLOW"),
    ("glow_pulse", (167, 139, 250), ARMSTRONG, "APOLLO 11  \u2022  PULSE GLOW"),
    ("rgb_static", "static", ARMSTRONG, "APOLLO 11  \u2022  RGB STATIC"),
    ("rgb_converge", "converge", GLENN, "FRIENDSHIP 7  \u2022  RGB CONVERGE"),
    ("rgb_pulse", "pulse", ARMSTRONG, "APOLLO 11  \u2022  RGB PULSE"),
    ("rgb_glitch", "glitch", GLENN, "FRIENDSHIP 7  \u2022  RGB GLITCH"),
    ("rgb_exit", "exit", ARMSTRONG, "APOLLO 11  \u2022  RGB EXIT"),
]


def main():
    only = sys.argv[1] if len(sys.argv) > 1 else None
    os.makedirs(PNGDIR, exist_ok=True)
    os.makedirs(MP4DIR, exist_ok=True)
    manifest_path = os.path.join(OUT, "manifest.json")
    try:
        manifest = json.load(open(manifest_path))
    except (OSError, ValueError):
        manifest = {"version": 1, "kind": "apollo-style-v1",
                    "canvas": {"width": W, "height": H, "fps": FPS}, "assets": []}
    have = {a["id"] for a in manifest["assets"]}
    for name, variant, src, tag in CLIPS:
        if only and only != name and only != "all":
            continue
        mp4 = os.path.join(MP4DIR, f"apollo_{name}_v1.mp4")
        png = os.path.join(PNGDIR, f"apollo_{name}_v1.png")
        print(f"[{name}] {NF}f ...", flush=True)
        if name.startswith("grid_"):
            gen = grid_frames(variant, src, tag)
        elif name.startswith("stroke_"):
            gen = stroke_frames(variant, src, tag)
        elif name.startswith("glow_"):
            gen = glow_frames(variant, variant == (167, 139, 250), src, tag)
        else:
            gen = rgb_frames(variant, src, tag)
        preview = encode(gen, NF, mp4)
        Image.fromarray(preview).save(png)
        info = {"id": f"apollo-{name}-v1", "mp4": os.path.relpath(mp4, OUT),
                "png": os.path.relpath(png, OUT),
                "mp4_sha256": sha256(mp4), "frames": NF}
        manifest["assets"] = [a for a in manifest["assets"] if a["id"] != info["id"]]
        manifest["assets"].append(info)
        print(f"  ok {info['mp4_sha256'][:12]}", flush=True)
        gc.collect()
    with open(manifest_path, "w") as fh:
        json.dump(manifest, fh, indent=2)
    print("OK: " + OUT)


if __name__ == "__main__":
    sys.exit(main())
