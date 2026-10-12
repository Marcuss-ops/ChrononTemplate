#!/usr/bin/env python3
"""DocFX preview reel set: seven 4-5s MP4s, 30fps, one per documentary
effect pack. Real assets (Armstrong/Glenn portraits), static camera,
calm motion, OOM-safe (one clip, one frame at a time).
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
                   "..", "..", "out", "documentary_effects_v1")
PNGDIR = os.path.join(OUT, "png")
MP4DIR = os.path.join(OUT, "mp4")
W, H = 1920, 1080
FPS = 30
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


def smooth(p):
    p = min(max(p, 0.0), 1.0)
    return p * p * (3 - 2 * p)


def ease_out(p):
    p = min(max(p, 0.0), 1.0)
    return 1 - (1 - p) * (1 - p)


def affine(baked, out_w, out_h, zoom, cx, cy):
    bw, bh = baked.size
    inv = 1.0 / zoom
    return baked.transform(
        (out_w, out_h), Image.AFFINE,
        (inv, 0.0, cx - out_w * 0.5 * inv, 0.0, inv, cy - out_h * 0.5 * inv),
        resample=Image.BILINEAR)


def grain(frame, seed, sigma):
    frame += np.random.default_rng(seed).normal(0, sigma, (H, W, 1)).astype(np.float32)
    return frame


def vignette(frame, strength):
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    dist = np.sqrt((xx / W - 0.5) ** 2 + (yy / H - 0.5) ** 2)
    frame *= (1 - strength * np.clip((dist - 0.32) / 0.45, 0, 1))[..., None]
    del yy, xx, dist
    return frame


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


def dark_bg(red=(74, 13, 18), amt=0.15):
    bg = np.full((H, W, 3), hexrgb("#08080A"), dtype=np.float32)
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    dx = (xx - W * 0.5) / (W * 0.62)
    dy = (yy - H * 0.5) / (H * 0.62)
    fall = np.clip(1 - np.sqrt(dx ** 2 + dy ** 2), 0, 1) ** 2
    bg = bg * (1 - fall[..., None] * amt) + np.array(red, dtype=np.float32) * fall[..., None] * amt
    del yy, xx, dx, dy, fall
    return bg


def loupe_frames():
    """Ring travels 700->1220 over f10-90, card pushes 1.0->1.04,
    content magnified 1.8x inside the ring."""
    cw, ch, cx, cy = 760, 480, 960, 430
    card_big = cover(ARMSTRONG, int(cw * 1.2), int(ch * 1.2))
    bw, bh = card_big.size
    x0, y0 = cx - cw // 2, cy - ch // 2
    yy, xx = np.mgrid[0:ch, 0:cw].astype(np.float32)
    f = 0
    while True:
        frame = dark_bg()
        p = smooth((f - 10) / 80)
        rcx = 700 + (1220 - 700) * p - x0
        rcy = 430 - y0
        zoom = 1.0 + 0.04 * ease_out((f - 10) / 80) if f >= 10 else 1.0
        card = np.asarray(affine(card_big, cw, ch, zoom, bw * 0.5, bh * 0.5),
                          dtype=np.float32)
        # Magnified patch inside the ring.
        R = 110
        mag = np.asarray(affine(card_big, cw, ch, zoom * 1.8,
                                bw * 0.5 + (rcx - cw * 0.5) / zoom,
                                bh * 0.5 + (rcy - ch * 0.5) / zoom),
                         dtype=np.float32)
        dist = np.sqrt((xx - rcx) ** 2 + (yy - rcy) ** 2)
        inner = np.clip((R - dist) / 12, 0, 1)
        card = card * (1 - inner[..., None]) + mag * inner[..., None]
        # Halo + ring.
        halo = np.clip((R * 2.2 - dist) / (R * 2.2), 0, 1)[..., None] * 0.18
        card = card * (1 - halo) + np.array([255, 246, 216], dtype=np.float32) * halo
        ring = (np.abs(dist - R) < 4).astype(np.float32)[..., None]
        card = card * (1 - ring) + 245 * ring
        card_op = min(f / 16, 1.0)
        a = np.zeros((H, W, 1), dtype=np.float32)
        a[y0:y0 + ch, x0:x0 + cw, 0] = card_op
        base = np.zeros((H, W, 3), dtype=np.float32)
        base[y0:y0 + ch, x0:x0 + cw] = card
        frame = frame * (1 - a) + base * a
        frame = vignette(frame, 0.30)
        frame = grain(frame, 8000 + f, 1.0)
        del card, mag, base, a
        f += 1
        yield np.clip(frame, 0, 255).astype(np.uint8)
        del frame
        if f >= 120:
            return


def redacted_frames():
    cw, ch, cx, cy = 860, 1000, 960, 540
    x0, y0 = cx - cw // 2, cy - ch // 2
    bars = [(0.1, 0.15, 0.8, 0.06, 0), (0.1, 0.35, 0.6, 0.06, 10),
            (0.1, 0.55, 0.75, 0.06, 20), (0.1, 0.75, 0.5, 0.06, 30)]
    f = 0
    total = 150
    while True:
        frame = dark_bg()
        fade = min(f / 16, 1.0)
        if f > total - 16:
            fade = min(fade, (total - f) / 16)
        paper = np.full((ch, cw, 3), hexrgb("#EDE6D6"), dtype=np.float32)
        py, px = np.mgrid[0:ch, 0:cw].astype(np.float32)
        for i, (bx, by, bw, bh, delay) in enumerate(bars):
            # Faint text line under each bar.
            paper[int((by + bh * 0.4) * ch) - 4:int((by + bh * 0.4) * ch) + 4,
                  int(bx * cw):int((bx + bw * 0.96) * cw)] = np.array([138, 132, 116], dtype=np.float32)
            onset = 10 + i * 14 + delay
            p = smooth((f - onset) / 18)
            shift = bw * cw * 1.2 * p
            cover_m = (px >= (bx * cw + shift)) & (px < ((bx + bw) * cw + shift)) & \
                      (py >= by * ch) & (py < (by + bh) * ch)
            paper[cover_m] = np.array([11, 11, 12], dtype=np.float32)
        base = np.zeros((H, W, 3), dtype=np.float32)
        base[y0:y0 + ch, x0:x0 + cw] = paper * fade
        frame = frame * (1 - fade * (np.abs(base).sum(-1, keepdims=True) > 0)) + base
        # Stamp slams at f90.
        if f >= 90:
            sp = min((f - 90) / 14, 1.0)
            sc = 2.2 - 1.2 * (sp * sp * (3 - 2 * sp))
            txt = Image.new("L", (700, 160), 0)
            ImageDraw.Draw(txt).text((350, 80), "DECLASSIFIED",
                                     font=ImageFont.truetype(SANS, 92), fill=255, anchor="mm")
            tw, th = int(700 / sc), int(160 / sc)
            txt = txt.resize((max(tw, 8), max(th, 8)), Image.BILINEAR)
            ta = np.asarray(txt, dtype=np.float32) / 255.0
            th2, tw2 = ta.shape
            sy, sx = cy - th2 // 2, cx - tw2 // 2
            op = min((f - 90) / 6, 1.0)
            region = frame[sy:sy + th2, sx:sx + tw2]
            region[:] = region * (1 - ta[..., None] * op) + \
                np.array([179, 40, 45], dtype=np.float32) * ta[..., None] * op
        frame = vignette(frame, 0.25)
        frame = grain(frame, 8100 + f, 1.0)
        del paper, base
        f += 1
        yield np.clip(frame, 0, 255).astype(np.uint8)
        del frame
        if f >= total:
            return


def leader_frames():
    beats, per = 5, 18
    total = beats * per + 30
    f = 0
    while True:
        frame = np.full((H, W, 3), hexrgb("#3A3A3C"), dtype=np.float32)
        frame = grain(frame, 8200 + f * 3, 4.0)
        # Crosshairs + ring.
        frame[H // 2 - 3:H // 2 + 3, :] = frame[H // 2 - 3:H // 2 + 3, :] * 0.5 + \
            np.array([201, 162, 39], dtype=np.float32) * 0.25
        frame[:, W // 2 - 3:W // 2 + 3] = frame[:, W // 2 - 3:W // 2 + 3] * 0.5 + \
            np.array([201, 162, 39], dtype=np.float32) * 0.25
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
        ring = (np.abs(np.sqrt((xx - W / 2) ** 2 + (yy - H / 2) ** 2) - 400) < 5)
        frame[ring] = frame[ring] * 0.4 + np.array([242, 239, 230], dtype=np.float32) * 0.6
        del yy, xx, ring
        if f < beats * per:
            n = beats - f // per
            lf = f % per
            sc = 1.6 - 0.6 * min(lf / 8, 1.0)
            txt = Image.new("L", (500, 500), 0)
            ImageDraw.Draw(txt).text((250, 250), str(n),
                                     font=ImageFont.truetype(SANS, 420), fill=255, anchor="mm")
            tw = (int(500 / sc), int(500 / sc))
            txt = txt.resize(tw, Image.BILINEAR)
            ta = np.asarray(txt, dtype=np.float32) / 255.0
            th2, tw2 = ta.shape
            sy, sx = H // 2 - th2 // 2, W // 2 - tw2 // 2
            op = min(lf / 4, 1.0)
            region = frame[sy:sy + th2, sx:sx + tw2]
            region[:] = region * (1 - ta[..., None] * op) + \
                np.array([242, 239, 230], dtype=np.float32) * ta[..., None] * op
        else:
            txt = Image.new("L", (1200, 160), 0)
            ImageDraw.Draw(txt).text((600, 80), "PICTURE START",
                                     font=ImageFont.truetype(SANS, 118), fill=255, anchor="mm")
            ta = np.asarray(txt, dtype=np.float32) / 255.0
            op = min((f - beats * per) / 10, 1.0)
            region = frame[H // 2 - 80:H // 2 + 80, W // 2 - 600:W // 2 + 600]
            region[:] = region * (1 - ta[..., None] * op) + \
                np.array([242, 239, 230], dtype=np.float32) * ta[..., None] * op
        frame = vignette(frame, 0.20)
        f += 1
        yield np.clip(frame, 0, 255).astype(np.uint8)
        del frame
        if f >= total:
            return


def parallax_frames():
    bg_big = cover(GLENN, 2304, 1296)
    fg_big = cover(ARMSTRONG, 900, 1100)
    fbbw, fbbh = fg_big.size
    bbw, bbh = bg_big.size
    total = 130
    f = 0
    while True:
        p = ease_out(f / (total - 1))
        frame = np.asarray(affine(bg_big, W, H, 1.0 + 0.06 * p,
                                  bbw * 0.5 - 40 * p, bbh * 0.5), dtype=np.float32)
        frame = frame * 0.55  # darken bg
        fw, fh = 620, int(620 * 1100 / 900)
        fgx = int(W * 0.58 + 60 * p - fw / 2)
        fgy = int(H * 0.5 - fh / 2 + 20 * (1 - p))
        fg = np.asarray(fg_big.resize((fw, fh), Image.LANCZOS), dtype=np.float32)
        # cream frame border
        pad = 18
        canvas = np.full((fh + pad * 2, fw + pad * 2, 3), hexrgb("#F2EEE5"), dtype=np.float32)
        canvas[pad:pad + fh, pad:pad + fw] = fg
        # paste with fade
        op = min(f / 14, 1.0)
        y1, x1 = max(fgy - pad, 0), max(fgx - pad, 0)
        y2, x2 = min(y1 + canvas.shape[0], H), min(x1 + canvas.shape[1], W)
        cy1, cx1 = y1 - (fgy - pad), x1 - (fgx - pad)
        frame[y1:y2, x1:x2] = frame[y1:y2, x1:x2] * (1 - op) + \
            canvas[cy1:cy1 + (y2 - y1), cx1:cx1 + (x2 - x1)] * op
        # title
        if f > 20:
            txt = Image.new("L", (900, 90), 0)
            ImageDraw.Draw(txt).text((450, 45), "APOLLO 11  \u2022  1969",
                                     font=ImageFont.truetype(SANS, 56), fill=255, anchor="mm")
            ta = np.asarray(txt, dtype=np.float32) / 255.0 * min((f - 20) / 12, 1.0)
            th2, tw2 = ta.shape
            sx, sy = 120, H - 160
            region = frame[sy:sy + th2, sx:sx + tw2]
            region[:] = region * (1 - ta[..., None]) + np.array([242, 239, 230], dtype=np.float32) * ta[..., None]
        frame = vignette(frame, 0.28)
        frame = grain(frame, 8300 + f, 1.2)
        del canvas, fg
        f += 1
        yield np.clip(frame, 0, 255).astype(np.uint8)
        del frame
        if f >= total:
            return


def route_frames():
    pts = [(300, 800), (600, 640), (900, 680), (1150, 500),
           (1400, 540), (1620, 320)]
    # dense polyline
    dense = []
    for i in range(len(pts) - 1):
        for t in np.linspace(0, 1, 120, endpoint=False):
            dense.append((pts[i][0] * (1 - t) + pts[i + 1][0] * t,
                          pts[i][1] * (1 - t) + pts[i + 1][1] * t))
    dense.append(pts[-1])
    labels = [(300, 800, "EARTH"), (1150, 500, "ORBIT"), (1620, 320, "MOON")]
    total = 150
    f = 0
    while True:
        frame = dark_bg(red=(20, 30, 46), amt=0.22)
        frame[::90, :] = frame[::90, :] * 0.8 + 8
        frame[:, ::90] = frame[:, ::90] * 0.8 + 8
        p = smooth((f - 8) / 110)
        nshow = int(len(dense) * p)
        img = Image.fromarray(np.clip(frame, 0, 255).astype(np.uint8))
        dr = ImageDraw.Draw(img)
        if nshow > 2:
            seg = dense[:nshow]
            # dashed gold route
            for k in range(0, len(seg) - 1, 2):
                if (k // 2) % 2 == 0:
                    dr.line([seg[k], seg[min(k + 1, len(seg) - 1)]],
                            fill=(201, 162, 39), width=7)
        cum = 0
        bounds = []
        step = len(dense) / 6
        for wi, (lx, ly) in enumerate(pts):
            on = nshow > (wi * step)
            r = 12 if on else 7
            col = (242, 239, 230) if on else (110, 110, 116)
            dr.ellipse([lx - r, ly - r, lx + r, ly + r], fill=col)
        if nshow > 2:
            tx, ty = dense[nshow - 1]
            dr.ellipse([tx - 34, ty - 34, tx + 34, ty + 34],
                       outline=(179, 40, 45), width=3)
            dr.ellipse([tx - 16, ty - 16, tx + 16, ty + 16],
                       fill=(179, 40, 45))
        for i, (lx, ly, name) in enumerate(labels):
            lp = smooth((f - (8 + i * 34)) / 12)
            if lp <= 0:
                continue
            dr.text((lx, max(ly - 110, 30)), name,
                    font=ImageFont.truetype(SANS, 52), fill=(242, 239, 230),
                    anchor="mm")
        frame = np.asarray(img, dtype=np.float32)
        frame = vignette(frame, 0.25)
        frame = grain(frame, 8400 + f, 1.0)
        f += 1
        yield np.clip(frame, 0, 255).astype(np.uint8)
        del frame, img
        if f >= total:
            return


def beforeafter_frames():
    left = np.asarray(cover(ARMSTRONG, W, H), dtype=np.float32)
    right = np.asarray(cover(GLENN, W, H), dtype=np.float32)
    # sepia-tone the whole left plate once
    sep = np.stack([left[..., 0] * 0.393 + left[..., 1] * 0.769 + left[..., 2] * 0.189,
                    left[..., 0] * 0.349 + left[..., 1] * 0.686 + left[..., 2] * 0.168,
                    left[..., 0] * 0.272 + left[..., 1] * 0.534 + left[..., 2] * 0.131], -1)
    left = np.clip(sep, 0, 255)
    del sep
    total = 140
    f = 0
    while True:
        p = smooth((f - 12) / 70)
        split = int(200 + (1720 - 200) * p)
        frame = np.zeros((H, W, 3), dtype=np.float32)
        frame[:, :split] = left[:, :split]
        frame[:, split:] = right[:, split:]
        # divider
        frame[:, max(split - 4, 0):min(split + 4, W)] = np.array([242, 239, 230], dtype=np.float32)
        # tags
        for txt_s, on, txc in [("1969", f > 18, 200), ("NOW", f > 60, W - 320)]:
            if not on:
                continue
            txt = Image.new("L", (300, 80), 0)
            ImageDraw.Draw(txt).text((150, 40), txt_s,
                                     font=ImageFont.truetype(SANS, 56), fill=255, anchor="mm")
            ta = np.asarray(txt, dtype=np.float32) / 255.0
            region = frame[80:160, txc:txc + 300]
            region[:] = region * (1 - ta[..., None] * 0.95) + \
                np.array([242, 239, 230], dtype=np.float32) * ta[..., None] * 0.95
        frame = vignette(frame, 0.22)
        frame = grain(frame, 8500 + f, 1.1)
        f += 1
        yield np.clip(frame, 0, 255).astype(np.uint8)
        del frame
        if f >= total:
            return


def counters_frames():
    total = 130
    f = 0
    while True:
        frame = dark_bg()
        p = ease_out(f / (total - 1))
        val = int(384400 * p)
        txt = Image.new("L", (1400, 300), 0)
        ImageDraw.Draw(txt).text((700, 150), f"{val:,}".replace(",", " "),
                                 font=ImageFont.truetype(SANS, 200), fill=255, anchor="mm")
        ta = np.asarray(txt, dtype=np.float32) / 255.0
        th2, tw2 = ta.shape
        sx, sy = W // 2 - tw2 // 2, 300
        region = frame[sy:sy + th2, sx:sx + tw2]
        region[:] = region * (1 - ta[..., None]) + \
            np.array([242, 239, 230], dtype=np.float32) * ta[..., None]
        # ruler 1961-1969
        y0 = 760
        frame[y0 - 3:y0 + 3, 260:1660] = np.array([120, 120, 126], dtype=np.float32)
        for i, yr in enumerate(range(1961, 1970)):
            x = 260 + int(i * (1400 / 8))
            frame[y0 - 22:y0 + 22, x - 2:x + 2] = np.array([242, 239, 230], dtype=np.float32)
            t2 = Image.new("L", (160, 60), 0)
            ImageDraw.Draw(t2).text((80, 30), str(yr),
                                    font=ImageFont.truetype(SANS, 40), fill=255, anchor="mm")
            a2 = np.asarray(t2, dtype=np.float32) / 255.0 * 0.9
            region2 = frame[y0 + 26:y0 + 86, x - 80:x + 80]
            region2[:] = region2 * (1 - a2[..., None]) + \
                np.array([200, 200, 205], dtype=np.float32) * a2[..., None]
        cxr = int(260 + p * 1400)
        frame[y0 - 60:y0 + 60, cxr - 4:cxr + 4] = np.array([179, 40, 45], dtype=np.float32)
        # unit
        t3 = Image.new("L", (700, 80), 0)
        ImageDraw.Draw(t3).text((350, 40), "KM  TO  THE  MOON",
                                font=ImageFont.truetype(SANS, 52), fill=255, anchor="mm")
        a3 = np.asarray(t3, dtype=np.float32) / 255.0 * min(f / 14, 1.0)
        region3 = frame[150:230, W // 2 - 350:W // 2 + 350]
        region3[:] = region3 * (1 - a3[..., None]) + \
            np.array([201, 162, 39], dtype=np.float32) * a3[..., None]
        frame = vignette(frame, 0.25)
        frame = grain(frame, 8600 + f, 1.0)
        f += 1
        yield np.clip(frame, 0, 255).astype(np.uint8)
        del frame
        if f >= total:
            return


CLIPS = [
    ("loupe", loupe_frames, 120),
    ("redacted", redacted_frames, 150),
    ("leader", leader_frames, 120),
    ("parallax", parallax_frames, 130),
    ("route", route_frames, 150),
    ("beforeafter", beforeafter_frames, 140),
    ("counters", counters_frames, 130),
]


def main():
    only = sys.argv[1] if len(sys.argv) > 1 else None
    os.makedirs(PNGDIR, exist_ok=True)
    os.makedirs(MP4DIR, exist_ok=True)
    manifest = {"version": 1, "kind": "documentary-effects-v1",
                "canvas": {"width": W, "height": H, "fps": FPS}, "assets": []}
    for name, fn, n in CLIPS:
        if only and only != name and only != "all":
            continue
        mp4 = os.path.join(MP4DIR, f"docfx_{name}_v1.mp4")
        png = os.path.join(PNGDIR, f"docfx_{name}_v1.png")
        print(f"[{name}] {n}f ...", flush=True)
        preview = encode(fn(), n, mp4)
        Image.fromarray(preview).save(png)
        info = {"id": f"docfx-{name}-v1", "mp4": os.path.relpath(mp4, OUT),
                "png": os.path.relpath(png, OUT),
                "mp4_sha256": sha256(mp4), "frames": n}
        manifest["assets"].append(info)
        print(f"  ok {info['mp4_sha256'][:12]}", flush=True)
        gc.collect()
    with open(os.path.join(OUT, "manifest.json"), "w") as fh:
        json.dump(manifest, fh, indent=2)
    print("OK: " + OUT)


if __name__ == "__main__":
    sys.exit(main())
