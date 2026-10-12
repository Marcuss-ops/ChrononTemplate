#!/usr/bin/env python3
"""Elements reel: 30 clips (one per graphics object), 1920x1080 30fps,
120f each, motion on. Layouts mirror the C++ specs, root centered.
OOM-safe: one clip, one frame at a time.
"""
import gc
import hashlib
import json
import math
import os
import subprocess
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                   "..", "..", "out", "elements_v1")
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
SERIF = "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf"
GOLD = np.array([232, 184, 74], dtype=np.float32)
PAPER = np.array([244, 240, 231], dtype=np.float32)
INK_D = np.array([242, 239, 230], dtype=np.float32)
MUT = np.array([138, 143, 152], dtype=np.float32)
RED = np.array([224, 59, 47], dtype=np.float32)
GREEN = np.array([63, 185, 80], dtype=np.float32)


def hx(s):
    s = s.lstrip("#")
    return np.array([int(s[0:2], 16), int(s[2:4], 16), int(s[4:6], 16)], dtype=np.float32)


def smooth(p):
    p = min(max(p, 0.0), 1.0)
    return p * p * (3 - 2 * p)


def ease_out(p):
    p = min(max(p, 0.0), 1.0)
    return 1 - (1 - p) * (1 - p)


def dark_bg():
    bg = np.full((H, W, 3), hx("#08080A"), dtype=np.float32)
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    dx = (xx - W * 0.5) / (W * 0.62)
    dy = (yy - H * 0.5) / (H * 0.62)
    fall = np.clip(1 - np.sqrt(dx ** 2 + dy ** 2), 0, 1) ** 2
    bg = bg * (1 - fall[..., None] * 0.15) + np.array([74, 13, 18], dtype=np.float32) * fall[..., None] * 0.15
    del yy, xx, dx, dy, fall
    return bg


def paper_bg():
    bg = np.full((H, W, 3), hx("#E9E2D2"), dtype=np.float32)
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    dist = np.sqrt((xx / W - 0.5) ** 2 + (yy / H - 0.5) ** 2)
    bg *= (1 - 0.12 * np.clip((dist - 0.3) / 0.5, 0, 1))[..., None]
    del yy, xx, dist
    return bg


def cover(path, w, h):
    img = Image.open(path).convert("RGB")
    sw, sh = img.size
    s = max(w / sw, h / sh)
    img = img.resize((int(sw * s + 0.5), int(sh * s + 0.5)), Image.LANCZOS)
    l = (img.size[0] - w) // 2
    t = (img.size[1] - h) // 2
    return img.crop((l, t, l + w, t + h))


def textmask(text, size, font=SANS):
    f = ImageFont.truetype(font, size)
    bb = f.getbbox(text)
    img = Image.new("L", (bb[2] - bb[0] + 24, bb[3] - bb[1] + 24), 0)
    ImageDraw.Draw(img).text((12 - bb[0], 12 - bb[1]), text, font=f, fill=255)
    return np.asarray(img, dtype=np.float32) / 255.0


def stamp(frame, mask, cx, cy, color, op):
    if op <= 0:
        return frame
    h, w = mask.shape
    x1, y1 = int(cx - w / 2), int(cy - h / 2)
    x0c, y0c = max(x1, 0), max(y1, 0)
    x1c, y1c = min(x1 + w, W), min(y1 + h, H)
    if x1c <= x0c or y1c <= y0c:
        return frame
    a = mask[y0c - y1:y1c - y1, x0c - x1:x1c - x1] * min(op, 1.0)
    frame[y0c:y1c, x0c:x1c] = frame[y0c:y1c, x0c:x1c] * (1 - a[..., None]) + color * a[..., None]
    return frame


def bar(frame, cx, cy, w, h, color, op=1.0):
    if op <= 0 or w <= 0 or h <= 0:
        return frame
    x1, y1 = int(cx - w / 2), int(cy - h / 2)
    x0c, y0c = max(x1, 0), max(y1, 0)
    x1c, y1c = min(x1 + int(w), W), min(y1 + int(h), H)
    if x1c <= x0c or y1c <= y0c:
        return frame
    frame[y0c:y1c, x0c:x1c] = frame[y0c:y1c, x0c:x1c] * (1 - op) + color * op
    return frame


def dot(frame, cx, cy, r, color, op=1.0):
    if op <= 0:
        return frame
    yy, xx = np.mgrid[max(int(cy - r - 2), 0):min(int(cy + r + 2), H),
                      max(int(cx - r - 2), 0):min(int(cx + r + 2), W)].astype(np.float32)
    m = (xx - cx) ** 2 + (yy - cy) ** 2 < r ** 2
    reg = frame[yy.min().astype(int):yy.max().astype(int) + 1,
                xx.min().astype(int):xx.max().astype(int) + 1] if False else None
    ys = slice(max(int(cy - r - 2), 0), min(int(cy + r + 2), H))
    xs = slice(max(int(cx - r - 2), 0), min(int(cx + r + 2), W))
    sub = frame[ys, xs]
    mm = m[:sub.shape[0], :sub.shape[1]]
    sub[mm] = sub[mm] * (1 - op) + color * op
    del yy, xx, m
    return frame


def ring(frame, cx, cy, r, t, color, op=1.0, a0=0.0, a1=6.2832):
    if op <= 0:
        return frame
    R = int(r + t + 3)
    ys = slice(max(int(cy - R), 0), min(int(cy + R), H))
    xs = slice(max(int(cx - R), 0), min(int(cx + R), W))
    yy, xx = np.mgrid[ys, xs].astype(np.float32)
    d = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2)
    ang = np.arctan2(yy - cy, xx - cx)
    ang = np.where(ang < 0, ang + 6.2832, ang)
    m = (np.abs(d - r) < t) & (ang >= a0) & (ang <= a1)
    sub = frame[ys, xs]
    sub[m] = sub[m] * (1 - op) + color * op
    del yy, xx, d, ang, m
    return frame


def grain(frame, seed, sigma=1.0):
    frame += np.random.default_rng(seed).normal(0, sigma, (H, W, 1)).astype(np.float32)
    return frame


def vignette(frame, strength=0.25):
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    dist = np.sqrt((xx / W - 0.5) ** 2 + (yy / H - 0.5) ** 2)
    frame *= (1 - strength * np.clip((dist - 0.32) / 0.45, 0, 1))[..., None]
    del yy, xx, dist
    return frame


def fade_env(f):
    e = min(f / 14, 1.0)
    if f > NF - 14:
        e = min(e, (NF - f) / 14)
    return e


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


# ── 01-06 timeline ──

def el01_timeline():
    dates = [textmask("2007", 40), textmask("2010", 40), textmask("2017", 40)]
    labels = [textmask("iPHONE", 28), textmask("iPAD", 28), textmask("X", 28)]
    f = 0
    while True:
        e = fade_env(f)
        frame = dark_bg()
        p = ease_out(f / 60)
        total = 440
        bar(frame, 960, 540, total * p, 4, hx("#3A3A40"), e)
        for i, dx in enumerate((-220, 0, 220)):
            q = smooth((f - 8 - i * 10) / 16)
            x = 960 + dx
            dot(frame, x, 540, 13 if i == 1 else 8, GOLD if i == 1 else MUT, q * e)
            stamp(frame, dates[i], x, 476, INK_D if i == 1 else MUT, q * e)
            stamp(frame, labels[i], x, 604, MUT, q * e)
        frame = vignette(frame)
        frame = grain(frame, 1000 + f)
        f += 1
        yield np.clip(frame, 0, 255).astype(np.uint8)
        del frame
        if f >= NF:
            return


def el02_milestone():
    year = textmask("2007", 170, SERIF)
    head = textmask("THE FIRST iPHONE", 44)
    f = 0
    while True:
        e = fade_env(f)
        frame = dark_bg()
        rise = 90 * (1 - ease_out(f / 30))
        bar(frame, 700, 420 - rise * 0.3, 120 * smooth(f / 20), 10, GOLD, e)
        stamp(frame, year, 960, 500 - rise, INK_D, min(f / 20, 1.0) * e)
        stamp(frame, head, 960, 650 - rise * 0.5, MUT, smooth((f - 14) / 18) * e)
        frame = vignette(frame)
        frame = grain(frame, 1100 + f)
        f += 1
        yield np.clip(frame, 0, 255).astype(np.uint8)
        del frame
        if f >= NF:
            return


def el03_bracket():
    d0 = textmask("1998", 40)
    d1 = textmask("2010", 40)
    sp = textmask("12 YEARS", 32)
    f = 0
    while True:
        e = fade_env(f)
        frame = dark_bg()
        p = ease_out(f / 48)
        bar(frame, 960, 540, 560 * p, 4, hx("#3A3A40"), e)
        for sx in (-280, 280):
            bar(frame, 960 + sx * p, 540, 4, 44 * smooth((f - 20) / 14), GOLD, e)
        stamp(frame, d0, 960 - 280 * p, 470, INK_D, smooth((f - 30) / 14) * e)
        stamp(frame, d1, 960 + 280 * p, 470, INK_D, smooth((f - 30) / 14) * e)
        stamp(frame, sp, 960, 600, GOLD, smooth((f - 44) / 14) * e)
        frame = vignette(frame)
        frame = grain(frame, 1200 + f)
        f += 1
        yield np.clip(frame, 0, 255).astype(np.uint8)
        del frame
        if f >= NF:
            return


def el04_metric():
    unit = textmask("$ BILLION", 56)
    lab = textmask("REVENUE", 32)
    dlt = textmask("▲ 12%", 36)
    f = 0
    while True:
        e = fade_env(f)
        frame = dark_bg()
        v = int(45 * ease_out(f / 70))
        val = textmask(str(v), 150, SERIF)
        stamp(frame, val, 960, 440, INK_D, e)
        del val
        stamp(frame, unit, 960, 560, GOLD, smooth((f - 16) / 14) * e)
        stamp(frame, lab, 960, 630, MUT, smooth((f - 28) / 14) * e)
        stamp(frame, dlt, 960, 690, GREEN, smooth((f - 44) / 14) * e)
        frame = vignette(frame)
        frame = grain(frame, 1300 + f)
        f += 1
        yield np.clip(frame, 0, 255).astype(np.uint8)
        del frame
        if f >= NF:
            return


def el05_delta():
    l = textmask("2.1", 110, SERIF)
    r = textmask("4.8", 110, SERIF)
    ll = textmask("BEFORE", 30)
    rl = textmask("AFTER", 30)
    dd = textmask("▲ 128%", 44)
    f = 0
    while True:
        e = fade_env(f)
        frame = dark_bg()
        stamp(frame, l, 700, 460, INK_D, smooth(f / 18) * e)
        stamp(frame, r, 1220, 460, INK_D, smooth((f - 12) / 18) * e)
        stamp(frame, ll, 700, 570, MUT, smooth((f - 24) / 14) * e)
        stamp(frame, rl, 1220, 570, MUT, smooth((f - 24) / 14) * e)
        bar(frame, 960, 500, 4, 170 * smooth((f - 16) / 16), hx("#3A3A40"), e)
        stamp(frame, dd, 960, 670, GREEN, smooth((f - 44) / 14) * e)
        frame = vignette(frame)
        frame = grain(frame, 1400 + f)
        f += 1
        yield np.clip(frame, 0, 255).astype(np.uint8)
        del frame
        if f >= NF:
            return


def el06_rail():
    dates = [textmask("2001", 34), textmask("2005", 34), textmask("2008", 34)]
    labels = [textmask("CAUSE", 28), textmask("EFFECT", 28), textmask("AFTERMATH", 28)]
    f = 0
    while True:
        e = fade_env(f)
        frame = dark_bg()
        bar(frame, 770, 540, 4, 300 * ease_out(f / 50), hx("#3A3A40"), e)
        for i, dy in enumerate((-150, 0, 150)):
            q = smooth((f - 10 - i * 14) / 16)
            dot(frame, 770, 540 + dy, 9, GOLD, q * e)
            stamp(frame, dates[i], 900, 532 + dy, INK_D, q * e)
            stamp(frame, labels[i], 900, 576 + dy, MUT, q * e)
        frame = vignette(frame)
        frame = grain(frame, 1500 + f)
        f += 1
        yield np.clip(frame, 0, 255).astype(np.uint8)
        del frame
        if f >= NF:
            return


# ── 07-12 annotation ──

def el07_brush():
    f = 0
    while True:
        e = fade_env(f)
        frame = dark_bg()
        p = ease_out(f / 60)
        L, x0 = 420, 960 - 210
        # halo, core, head, trail
        bar(frame, x0 + L * p / 2, 540, L * p, 24, hx("#FFB82E"), 0.35 * e)
        bar(frame, x0 + L * p / 2, 540, L * p, 6, hx("#FFFFFF"), e)
        dot(frame, x0 + L * p, 540, 9, hx("#FFFFFF"), e)
        bar(frame, x0 + L * p - 75, 540, 147 * p, 12, hx("#FFB82E"), 0.4 * e)
        frame = vignette(frame)
        frame = grain(frame, 1600 + f)
        f += 1
        yield np.clip(frame, 0, 255).astype(np.uint8)
        del frame
        if f >= NF:
            return


def el08_underline():
    word = textmask("STEVE JOBS", 64)
    f = 0
    while True:
        e = fade_env(f)
        frame = dark_bg()
        stamp(frame, word, 960, 470, INK_D, min(f / 16, 1.0) * e)
        p = smooth((f - 18) / 30)
        w = 340 * p
        bar(frame, 960 - 170 * p + w / 2 - 170 * 0, 560, w, 18, GOLD, e)
        bar(frame, 960 + 40, 566, 180 * p, 10, GOLD, e)
        frame = vignette(frame)
        frame = grain(frame, 1700 + f)
        f += 1
        yield np.clip(frame, 0, 255).astype(np.uint8)
        del frame
        if f >= NF:
            return


def el09_marker():
    phrase = textmask("THE FIRST iPHONE", 56)
    f = 0
    while True:
        e = fade_env(f)
        frame = dark_bg()
        p = smooth((f - 8) / 26)
        h, w = phrase.shape
        # yellow stripe wipes behind the phrase
        bar(frame, 960 - w / 2 + (w + 36) * p / 2, 540, (w + 36) * p, h + 20,
            hx("#FFE45E"), e)
        stamp(frame, phrase, 960, 540, hx("#101014"), smooth((f - 20) / 12) * e)
        frame = vignette(frame)
        frame = grain(frame, 1800 + f)
        f += 1
        yield np.clip(frame, 0, 255).astype(np.uint8)
        del frame
        if f >= NF:
            return


def el10_circle():
    lab = textmask("SUBJECT", 32)
    f = 0
    while True:
        e = fade_env(f)
        frame = dark_bg()
        # hand ring draws progressively + wobble ring
        a1 = 6.2832 * ease_out(f / 55)
        ring(frame, 960, 520, 110, 7, RED, e, 0.0, a1)
        ring(frame, 964, 517, 114, 4, RED, 0.6 * e, 0.0, a1)
        stamp(frame, lab, 960, 690, RED, smooth((f - 50) / 14) * e)
        frame = vignette(frame)
        frame = grain(frame, 1900 + f)
        f += 1
        yield np.clip(frame, 0, 255).astype(np.uint8)
        del frame
        if f >= NF:
            return


def el11_arrow():
    lab = textmask("SEE HERE", 32)
    f = 0
    while True:
        e = fade_env(f)
        frame = dark_bg()
        p = ease_out(f / 45)
        L = 260 * p
        bar(frame, 830 - 130 + L / 2, 540, L, 10, INK_D, e)
        # head chevrons at the tip
        tx = 830 - 130 + L
        q = smooth((f - 40) / 12) * e
        bar(frame, tx - 17, 527, 34, 10, INK_D, q)
        bar(frame, tx - 17, 553, 34, 10, INK_D, q)
        stamp(frame, lab, 660, 480, INK_D, smooth((f - 55) / 12) * e)
        frame = vignette(frame)
        frame = grain(frame, 2000 + f)
        f += 1
        yield np.clip(frame, 0, 255).astype(np.uint8)
        del frame
        if f >= NF:
            return


def el12_bracket():
    lab = textmask("EVIDENCE A", 30)
    f = 0
    while True:
        e = fade_env(f)
        frame = dark_bg()
        W2, H2, c, t = 420, 260, 56, 8
        for i, (sx, sy) in enumerate(((-1, -1), (1, -1), (-1, 1), (1, 1))):
            q = smooth((f - 6 - i * 8) / 14) * e
            cx = 960 + sx * W2 / 2
            cy = 540 + sy * H2 / 2
            bar(frame, cx + sx * c / 2, cy, c, t, INK_D, q)
            bar(frame, cx, cy + sy * c / 2, t, c, INK_D, q)
        stamp(frame, lab, 960, 540 - H2 / 2 - 44, INK_D, smooth((f - 50) / 12) * e)
        frame = vignette(frame)
        frame = grain(frame, 2100 + f)
        f += 1
        yield np.clip(frame, 0, 255).astype(np.uint8)
        del frame
        if f >= NF:
            return


# ── 13-18 web (paper cards) ──

def paper_card(frame, cx, cy, w, h, accent, op):
    x0, y0 = int(cx - w / 2), int(cy - h / 2)
    frame[y0:y0 + h, x0:x0 + w] = PAPER * op + frame[y0:y0 + h, x0:x0 + w] * (1 - op)
    bar(frame, cx, y0 + 3, w * op, 6, accent, op)
    return frame


def el13_news():
    m = [textmask(t, s) for t, s in (("ARCHIVE / 2012", 30), ("MAPS", 30),
        ("An Apple Exit Over Maps", 52), ("Software executive leaves the company", 30),
        ("Source, date, author", 28), ("leaves the company", 30))]
    f = 0
    while True:
        e = fade_env(f)
        frame = paper_bg()
        paper_card(frame, 960, 540, 860, 520, GOLD, e)
        ys = (330, 380, 460, 570, 740, 650)
        cols = (MUT, GOLD, hx("#242627"), MUT, MUT, hx("#101014"))
        for i in range(6):
            q = smooth((f - 6 - i * 9) / 14) * e
            if i == 5:
                h, w = m[i].shape
                # highlight stripe behind the highlight words
                bar(frame, 580, ys[i], (w + 24) * min(q * 3, 1.0), h + 12, hx("#FFE45E"), e)
            stamp(frame, m[i], 580, ys[i], cols[i], q)
        frame = grain(frame, 2200 + f)
        f += 1
        yield np.clip(frame, 0, 255).astype(np.uint8)
        del frame
        if f >= NF:
            return


def el14_reddit():
    m = [textmask(t, s) for t, s in (("r/space", 30), ("u/apollo_fan", 28),
        ("That launch footage never gets old", 32), ("12.4k", 30), ("never gets old", 30))]
    f = 0
    while True:
        e = fade_env(f)
        frame = paper_bg()
        paper_card(frame, 960, 540, 820, 420, hx("#FF4500"), e)
        dot(frame, 610, 400, 32, hx("#FF4500"), e)
        ys = (380, 422, 520, 690, 610)
        cols = (hx("#242627"), MUT, hx("#242627"), hx("#FF4500"), hx("#C08D4E"))
        for i in range(5):
            stamp(frame, m[i], 660, ys[i], cols[i], smooth((f - 8 - i * 10) / 14) * e)
        frame = grain(frame, 2300 + f)
        f += 1
        yield np.clip(frame, 0, 255).astype(np.uint8)
        del frame
        if f >= NF:
            return


def el15_social():
    m = [textmask(t, s) for t, s in (("NASA", 34), ("@nasa", 28),
        ("One small step", 34), ("2.1M likes", 28))]
    f = 0
    while True:
        e = fade_env(f)
        frame = paper_bg()
        paper_card(frame, 960, 540, 820, 440, hx("#1D9BF0"), e)
        dot(frame, 620, 400, 36, hx("#1D9BF0"), e)
        ys = (380, 425, 530, 690)
        cols = (hx("#242627"), MUT, hx("#242627"), MUT)
        for i in range(4):
            stamp(frame, m[i], 675, ys[i], cols[i], smooth((f - 8 - i * 10) / 14) * e)
        frame = grain(frame, 2400 + f)
        f += 1
        yield np.clip(frame, 0, 255).astype(np.uint8)
        del frame
        if f >= NF:
            return


def el16_search():
    m = [textmask(t, s) for t, s in (("nasa.gov/apollo", 28),
        ("Apollo 11 Mission Overview", 46), ("The first crewed Moon landing", 30))]
    f = 0
    while True:
        e = fade_env(f)
        frame = paper_bg()
        dot(frame, 560, 480, 20, GOLD, e)
        ys = (470, 530, 600)
        cols = (MUT, hx("#1A56DB"), MUT)
        for i in range(3):
            stamp(frame, m[i], 610, ys[i], cols[i], smooth((f - 8 - i * 10) / 14) * e)
        frame = grain(frame, 2500 + f)
        f += 1
        yield np.clip(frame, 0, 255).astype(np.uint8)
        del frame
        if f >= NF:
            return


def el17_browser():
    url = textmask("nasa.gov/apollo", 26)
    tab = textmask("Apollo 11", 28)
    f = 0
    while True:
        e = fade_env(f)
        frame = paper_bg()
        x0, y0, w, h = 510, 260, 900, 560
        frame[y0:y0 + h, x0:x0 + w] = PAPER * e + frame[y0:y0 + h, x0:x0 + w] * (1 - e)
        for i, c in enumerate((RED, GOLD, GREEN)):
            dot(frame, x0 + 40 + i * 36, y0 + 34, 11, c, e)
        bar(frame, x0 + 360, y0 + 34, 560 * smooth(f / 20), 44, hx("#D5DAE2"), e)
        stamp(frame, url, x0 + 140, y0 + 26, MUT, smooth((f - 16) / 12) * e)
        stamp(frame, tab, x0 + 220, y0 + 80, hx("#242627"), smooth((f - 28) / 12) * e)
        bar(frame, 960, y0 + 150 + (h - 150) / 2, (w - 40) * smooth((f - 30) / 20), h - 150,
            hx("#D5DAE2"), e)
        frame = grain(frame, 2600 + f)
        f += 1
        yield np.clip(frame, 0, 255).astype(np.uint8)
        del frame
        if f >= NF:
            return


def el18_shotfocus():
    lab = textmask("FIGURE 1", 30)
    f = 0
    while True:
        e = fade_env(f)
        frame = dark_bg()
        x0, y0, w, h = 510, 260, 900, 560
        bar(frame, 960, 540, w, h, hx("#1A1A20"), e)
        pulse = 0.75 + 0.25 * math.sin(f / 14.0)
        bar(frame, 960, 540, 320, 200, hx("#2E2E38"), e)
        for sx, sy in ((-1, -1), (1, -1), (-1, 1), (1, 1)):
            bar(frame, 960 + sx * 160, 540 + sy * 100, 44, 6, GOLD, pulse * e)
        stamp(frame, lab, 960, 690, GOLD, smooth((f - 40) / 12) * e)
        frame = vignette(frame)
        frame = grain(frame, 2700 + f)
        f += 1
        yield np.clip(frame, 0, 255).astype(np.uint8)
        del frame
        if f >= NF:
            return


# ── 19-24 documentary ──

def el19_archive():
    tag = textmask("ARCHIVE NO. 018", 34)
    dat = textmask("CALIFORNIA, 1980s", 30)
    src = textmask("AppleInsider", 26)
    f = 0
    while True:
        e = fade_env(f)
        frame = dark_bg()
        p = 0.9 + 0.1 * ease_out(f / 60)
        ph = np.asarray(cover(ARMSTRONG, int(620 * p), int(760 * p)), dtype=np.float32)
        hh, ww = ph.shape[:2]
        bar(frame, 960, 560, ww + 48, hh + 150, PAPER, e)
        ys = slice(int(560 - 35 - hh / 2), int(560 - 35 + hh / 2))
        xs = slice(int(960 - ww / 2), int(960 + ww / 2))
        frame[ys, xs] = frame[ys, xs] * (1 - e) + ph[:ys.stop - ys.start, :xs.stop - xs.start] * e
        del ph
        stamp(frame, tag, 650, 1050 - 140, hx("#242627"), smooth((f - 20) / 12) * e)
        stamp(frame, dat, 650, 1050 - 88, MUT, smooth((f - 30) / 12) * e)
        stamp(frame, src, 650, 1050 - 44, MUT, smooth((f - 40) / 12) * e)
        frame = vignette(frame)
        frame = grain(frame, 2800 + f)
        f += 1
        yield np.clip(frame, 0, 255).astype(np.uint8)
        del frame
        if f >= NF:
            return


def el20_evidence():
    hdr = textmask("EXHIBIT A", 36)
    ref = textmask("CASE 2011-0847", 28)
    bod = textmask("The email thread confirms the meeting", 32)
    quo = textmask("Stay hungry, stay foolish", 32)
    stp = textmask("SEALED", 44)
    f = 0
    while True:
        e = fade_env(f)
        frame = paper_bg()
        x0, y0 = 550, 260
        frame[y0:y0 + 560, x0:x0 + 820] = PAPER * e + frame[y0:y0 + 560, x0:x0 + 820] * (1 - e)
        stamp(frame, hdr, 600, 320, hx("#242627"), smooth(f / 14) * e)
        stamp(frame, ref, 600, 368, MUT, smooth((f - 10) / 12) * e)
        bar(frame, 960, 410, 720 * smooth((f - 16) / 16), 3, hx("#D8D2C2"), e)
        stamp(frame, bod, 600, 500, hx("#242627"), smooth((f - 26) / 12) * e)
        bar(frame, 600, 630, 8, 90 * smooth((f - 36) / 12), GOLD, e)
        stamp(frame, quo, 600, 630, hx("#242627"), smooth((f - 40) / 12) * e)
        # stamp slam
        if f >= 70:
            sp = min((f - 70) / 12, 1.0)
            sc = 1.8 - 0.8 * (sp * sp * (3 - 2 * sp))
            big = np.asarray(Image.fromarray((stp * 255).astype(np.uint8)).resize(
                (int(stp.shape[1] / sc), int(stp.shape[0] / sc)), Image.BILINEAR),
                dtype=np.float32) / 255.0
            stamp(frame, big, 1140, 740, RED, min((f - 70) / 5, 1.0) * e)
            del big
        frame = grain(frame, 2900 + f)
        f += 1
        yield np.clip(frame, 0, 255).astype(np.uint8)
        del frame
        if f >= NF:
            return


def el21_quote():
    q = textmask("Design is how it works", 64, SERIF)
    a = textmask("Steve Jobs", 38)
    r = textmask("Co-founder, Apple", 30)
    f = 0
    while True:
        e = fade_env(f)
        frame = dark_bg()
        bar(frame, 580, 540, 10, 300 * smooth(f / 20), GOLD, e)
        stamp(frame, q, 620, 480, INK_D, smooth((f - 12) / 16) * e)
        stamp(frame, a, 620, 650, GOLD, smooth((f - 30) / 12) * e)
        stamp(frame, r, 620, 702, MUT, smooth((f - 40) / 12) * e)
        frame = vignette(frame)
        frame = grain(frame, 3000 + f)
        f += 1
        yield np.clip(frame, 0, 255).astype(np.uint8)
        del frame
        if f >= NF:
            return


def el22_lowerthird():
    n = textmask("Steve Jobs", 64)
    p = textmask("Co-founder", 34)
    c = textmask("Apple Inc.", 30)
    f = 0
    while True:
        e = fade_env(f)
        frame = dark_bg()
        sl = 260 * (1 - ease_out(f / 30))
        stamp(frame, n, 630 - sl, 830, INK_D, e)
        bar(frame, 630 - sl, 900, 90 * smooth((f - 12) / 12), 8, GOLD, e)
        stamp(frame, p, 740 - sl, 900, INK_D, smooth((f - 20) / 12) * e)
        stamp(frame, c, 630 - sl, 960, MUT, smooth((f - 30) / 12) * e)
        frame = vignette(frame)
        frame = grain(frame, 3100 + f)
        f += 1
        yield np.clip(frame, 0, 255).astype(np.uint8)
        del frame
        if f >= NF:
            return


def el23_chapter():
    ch = textmask("CHAPTER 03", 40)
    ti = textmask("THE TURNING POINT", 130, SERIF)
    f = 0
    while True:
        e = fade_env(f)
        frame = dark_bg()
        stamp(frame, ch, 960, 380, GOLD, smooth(f / 14) * e)
        stamp(frame, ti, 960, 520, INK_D, smooth((f - 12) / 16) * e)
        bar(frame, 960, 690, 560, 6, hx("#3A3A40"), e)
        bar(frame, 680 + 280 * ease_out(f / 80), 690, 560 * ease_out(f / 80), 6, GOLD, e)
        frame = vignette(frame)
        frame = grain(frame, 3200 + f)
        f += 1
        yield np.clip(frame, 0, 255).astype(np.uint8)
        del frame
        if f >= NF:
            return


def el24_citation():
    s = textmask("NASA Archive", 28)
    d = textmask("1969", 28)
    m = textmask("16mm", 28)
    f = 0
    while True:
        e = fade_env(f)
        frame = dark_bg()
        sl = 200 * (1 - ease_out(f / 24))
        cx = 480 - sl
        bar(frame, cx, 1000, 520 * min(f / 16, 1.0), 64, hx("#101014"), e)
        dot(frame, cx - 230, 1000, 9, GOLD, e)
        stamp(frame, s, cx - 160, 992, INK_D, smooth((f - 14) / 10) * e)
        stamp(frame, d, cx + 60, 992, MUT, smooth((f - 22) / 10) * e)
        stamp(frame, m, cx + 190, 992, MUT, smooth((f - 30) / 10) * e)
        frame = vignette(frame)
        frame = grain(frame, 3300 + f)
        f += 1
        yield np.clip(frame, 0, 255).astype(np.uint8)
        del frame
        if f >= NF:
            return


# ── 25-30 diagram ──

def el25_geo():
    lab = textmask("CUPERTINO", 32)
    f = 0
    while True:
        e = fade_env(f)
        frame = dark_bg()
        pulse = 46 + 8 * math.sin(f / 12.0)
        ring(frame, 960, 520, pulse, 6, RED, 0.9 * e)
        dot(frame, 960, 520, 10, RED, e)
        stamp(frame, lab, 960, 640, INK_D, smooth((f - 20) / 12) * e)
        frame = vignette(frame)
        frame = grain(frame, 3400 + f)
        f += 1
        yield np.clip(frame, 0, 255).astype(np.uint8)
        del frame
        if f >= NF:
            return


def el26_region():
    lab = textmask("SECTOR 7", 34)
    f = 0
    while True:
        e = fade_env(f)
        frame = dark_bg()
        # hexagonal boundary draws progressively
        img = Image.new("L", (W, H), 0)
        dr = ImageDraw.Draw(img)
        cx, cy, R = 960, 520, 260
        pts = [(cx + R * math.cos(math.pi / 3 * k), cy + R * math.sin(math.pi / 3 * k))
               for k in range(7)]
        nshow = max(2, int(7 * ease_out(f / 55)))
        dr.line(pts[:nshow], fill=255, width=5)
        ma = np.asarray(img, dtype=np.float32) / 255.0
        frame = frame * (1 - ma[..., None] * e) + GOLD * ma[..., None] * e
        del img, dr, ma
        bar(frame, 960 - 274, 520, 8, 250 * smooth((f - 30) / 16), GOLD, e)
        stamp(frame, lab, 960, 830, GOLD, smooth((f - 45) / 12) * e)
        frame = vignette(frame)
        frame = grain(frame, 3500 + f)
        f += 1
        yield np.clip(frame, 0, 255).astype(np.uint8)
        del frame
        if f >= NF:
            return


def el27_route():
    nm = textmask("EARTH TO MOON", 36)
    f = 0
    while True:
        e = fade_env(f)
        frame = dark_bg()
        p = ease_out(f / 55)
        bar(frame, 880 - 150 + 150 * p, 500, 300 * p, 20, GOLD, 0.35 * e)
        bar(frame, 880 - 150 + 150 * p, 500, 300 * p, 6, hx("#FFFFFF"), e)
        bar(frame, 880 + 150 * p + 12, 491, 34, 6, GOLD, smooth((f - 50) / 10) * e)
        stamp(frame, nm, 880, 560, INK_D, smooth((f - 30) / 12) * e)
        bar(frame, 760, 620, 44 * smooth((f - 55) / 10), 16, GOLD, e)
        bar(frame, 820, 620, 44 * smooth((f - 60) / 10), 16, hx("#38BDF8"), e)
        frame = vignette(frame)
        frame = grain(frame, 3600 + f)
        f += 1
        yield np.clip(frame, 0, 255).astype(np.uint8)
        del frame
        if f >= NF:
            return


def el28_relation():
    l = textmask("APPLE", 34)
    r = textmask("NOKIA", 34)
    re = textmask("DISRUPTED", 30)
    f = 0
    while True:
        e = fade_env(f)
        frame = dark_bg()
        p = ease_out(f / 45)
        dot(frame, 680, 540, 15, GOLD, smooth(f / 14) * e)
        dot(frame, 1240, 540, 15, GOLD, smooth((f - 10) / 14) * e)
        bar(frame, 960, 540, 560 * p, 4, hx("#3A3A40"), e)
        stamp(frame, l, 680, 610, INK_D, smooth((f - 16) / 12) * e)
        stamp(frame, r, 1240, 610, INK_D, smooth((f - 26) / 12) * e)
        stamp(frame, re, 960, 488, GOLD, smooth((f - 50) / 12) * e)
        frame = vignette(frame)
        frame = grain(frame, 3700 + f)
        f += 1
        yield np.clip(frame, 0, 255).astype(np.uint8)
        del frame
        if f >= NF:
            return


def el29_split():
    left = np.asarray(cover(ARMSTRONG, W, H), dtype=np.float32)
    right = np.asarray(cover(GLENN, W, H), dtype=np.float32)
    btag = textmask("BEFORE", 30)
    atag = textmask("AFTER", 30)
    f = 0
    while True:
        e = fade_env(f)
        p = smooth((f - 10) / 60)
        split = int(200 + 1520 * p)
        frame = np.zeros((H, W, 3), dtype=np.float32)
        if split > 0:
            frame[:, :split] = left[:, :split] * e + frame[:, :split] * (1 - e)
        if split < W:
            frame[:, split:] = right[:, split:] * e + frame[:, split:] * (1 - e)
        bar(frame, split, 540, 6, 540, hx("#F2EFE6"), e)
        stamp(frame, btag, 290, 104, hx("#F2EFE6"), smooth((f - 30) / 12) * e)
        stamp(frame, atag, 1630, 104, hx("#F2EFE6"), smooth((f - 40) / 12) * e)
        frame = vignette(frame, 0.2)
        frame = grain(frame, 3800 + f)
        f += 1
        yield np.clip(frame, 0, 255).astype(np.uint8)
        del frame
        if f >= NF:
            return


def el30_flow():
    ti = textmask("LAUNCH", 44)
    su = textmask("Cause", 30)
    f = 0
    while True:
        e = fade_env(f)
        frame = dark_bg()
        pop = 0.85 + 0.15 * ease_out(f / 30)
        w, h = 420 * pop, 220 * pop
        bar(frame, 960, 540, w, h, hx("#17171D"), e)
        bar(frame, 960, 540 - h / 2 + 4, w * min(f / 20, 1.0), 8, GOLD, e)
        stamp(frame, ti, 790, 510, INK_D, smooth((f - 16) / 12) * e)
        stamp(frame, su, 790, 580, MUT, smooth((f - 28) / 12) * e)
        bar(frame, 960 - w / 2 - 20, 540, 40 * smooth((f - 40) / 10), 6, hx("#3A3A40"), e)
        bar(frame, 960 + w / 2 + 20, 540, 40 * smooth((f - 48) / 10), 6, hx("#3A3A40"), e)
        frame = vignette(frame)
        frame = grain(frame, 3900 + f)
        f += 1
        yield np.clip(frame, 0, 255).astype(np.uint8)
        del frame
        if f >= NF:
            return


CLIPS = [
    "timeline", "milestone", "bracket", "metric", "delta", "rail",
    "brush", "underline", "marker", "circle", "arrow", "bracket_focus",
    "news", "reddit", "social", "search", "browser", "shotfocus",
    "archive", "evidence", "quote", "lowerthird", "chapter", "citation",
    "geo", "region", "route", "relation", "split", "flow",
]

FNS = {
    "timeline": el01_timeline, "milestone": el02_milestone, "bracket": el03_bracket,
    "metric": el04_metric, "delta": el05_delta, "rail": el06_rail,
    "brush": el07_brush, "underline": el08_underline, "marker": el09_marker,
    "circle": el10_circle, "arrow": el11_arrow, "bracket_focus": el12_bracket,
    "news": el13_news, "reddit": el14_reddit, "social": el15_social,
    "search": el16_search, "browser": el17_browser, "shotfocus": el18_shotfocus,
    "archive": el19_archive, "evidence": el20_evidence, "quote": el21_quote,
    "lowerthird": el22_lowerthird, "chapter": el23_chapter, "citation": el24_citation,
    "geo": el25_geo, "region": el26_region, "route": el27_route,
    "relation": el28_relation, "split": el29_split, "flow": el30_flow,
}


def main():
    only = sys.argv[1] if len(sys.argv) > 1 else None
    os.makedirs(PNGDIR, exist_ok=True)
    os.makedirs(MP4DIR, exist_ok=True)
    manifest_path = os.path.join(OUT, "manifest.json")
    try:
        manifest = json.load(open(manifest_path))
    except (OSError, ValueError):
        manifest = {"version": 1, "kind": "elements-v1",
                    "canvas": {"width": W, "height": H, "fps": FPS}, "assets": []}
    for num, name in enumerate(CLIPS, 1):
        if only and only != name and only != "all":
            continue
        mp4 = os.path.join(MP4DIR, f"el_{num:02d}_{name}_v1.mp4")
        png = os.path.join(PNGDIR, f"el_{num:02d}_{name}_v1.png")
        print(f"[{num:02d}/{len(CLIPS)} {name}] {NF}f ...", flush=True)
        preview = encode(FNS[name](), NF, mp4)
        Image.fromarray(preview).save(png)
        info = {"id": f"el-{num:02d}-{name}-v1", "mp4": os.path.relpath(mp4, OUT),
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
