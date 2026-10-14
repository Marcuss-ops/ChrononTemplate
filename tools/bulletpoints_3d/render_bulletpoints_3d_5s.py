#!/usr/bin/env python3
"""Bulletpoints 3D — 5 animazioni documentaristiche, Play font, 5s 1920x1080 30fps.

Sezione 3D = multi-plane parallax reale: stesso camera path, ampiezze diverse
per bg (0.3x) / dust-mid (0.6x) / fg-testo (1.0x) => profondita' documentaristica.
Camera: push / track / crane / micro-orbit / handheld-settle, easing fluide.
Out: out/bullets_3d_5s/<id>_5s.mp4
"""
import math, subprocess, sys
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from ChrononTemplate.tools.backgrounds.documentary_background_v2 import (
    base_dark_graphite, dust_overlay, soft_vignette_overlay, diffuse_light_pool)

W, H, FPS, DUR, N = 1920, 1080, 30, 5, 150
OUT = ROOT / "out" / "bullets_3d_5s"
OUT.mkdir(parents=True, exist_ok=True)
FONTS = ROOT / "ChrononTemplate" / "assets" / "fonts"
FB = str(FONTS / "Play-Bold.ttf")
FR = str(FONTS / "Play-Regular.ttf")

INK = (245, 243, 238)
MUT = (200, 200, 205)
AMB = (240, 200, 120)
SHD = (0, 0, 0)

KICKER, TITLE = "PUNTI CHIAVE", "Cosa resta agli atti"
BULLETS = ["Il luogo e la data fissano la scena",
           "Le prove tecniche guidano l'indagine",
           "Ogni ipotesi va verificata alle fonti"]

# oversized plates for parallax crop (2200x1240)
OW, OH = 2200, 1240

def build_plates(seed=11):
    bg_big = base_dark_graphite(seed).convert("RGBA").resize((OW, OH), Image.BILINEAR)
    bg_big.alpha_composite(diffuse_light_pool(OW, OH, (88, 58, 34), 0.08, cxr=0.5, cyr=0.45, spread=1.3).resize((OW, OH)))
    bg_big.alpha_composite(soft_vignette_overlay(OW, OH, 0.16, seed + 5))
    dust_big = dust_overlay(OW, OH, seed + 7, n=70)
    return bg_big.convert("RGB"), dust_big

BG_BIG, DUST_BIG = build_plates()

F_TITLE = ImageFont.truetype(FB, 84)
F_BUL = ImageFont.truetype(FR, 44)
F_KICK = ImageFont.truetype(FB, 28)
F_NUM = ImageFont.truetype(FB, 40)

def ease_out(x): return 1 - (1 - x) ** 3
def smoother(x):
    x = min(1.0, max(0.0, x))
    return x * x * x * (x * (x * 6 - 15) + 10)
def clamp01(x): return min(1.0, max(0.0, x))

def cam_path(rid, f):
    t = f / (N - 1)
    if rid == "bullet_3d_doc_push_in":
        s = 1.08 - 0.08 * smoother(t)
        cx, cy = 8 * t, 5 * t
    elif rid == "bullet_3d_doc_lateral_track":
        s = 1.06 - 0.01 * smoother(t)
        cx, cy = -45 + 90 * smoother(t), 4 * math.sin(t * math.pi)
    elif rid == "bullet_3d_doc_crane_rise":
        s = 1.05 - 0.02 * smoother(t)
        cx, cy = 5 * math.sin(t * math.pi * 2), 35 - 70 * smoother(t)
    elif rid == "bullet_3d_doc_micro_orbit":
        s = 1.0 + 0.015 * math.sin(t * math.pi)
        cx, cy = 18 * math.sin(t * math.pi * 2), 8 * math.sin(t * math.pi * 2 + 1.0)
    elif rid == "bullet_3d_doc_handheld_settle":
        decay = math.exp(-f / 38.0)
        hx = 14 * decay * math.sin(2 * math.pi * f / 23.0) + 5 * decay * math.sin(2 * math.pi * f / 7.3 + 1.2)
        hy = 10 * decay * math.sin(2 * math.pi * f / 29.0 + 0.5) + 4 * decay * math.sin(2 * math.pi * f / 9.1)
        s = 1.04 - 0.04 * smoother(t)
        cx, cy = hx, hy
    else:
        s, cx, cy = 1.0, 0.0, 0.0
    return s, cx, cy

def crop_layer(plate, s, cx, cy, parallax):
    ww, hh = OW / s, OH / s
    x0 = (OW - ww) / 2 + cx * parallax
    y0 = (OH - wh) / 2 + cy * parallax if (wh := hh) else 0
    x0 = min(max(0, x0), OW - ww); y0 = min(max(0, y0), OH - hh)
    crop = plate.crop((int(x0), int(y0), int(x0 + ww), int(y0 + hh)))
    return crop.resize((W, H), Image.BILINEAR)

def text_rgba(rid, f):
    """Foreground text layer with per-bullet entrance + fg camera shift."""
    _, fcx, fcy = cam_path(rid, f)
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    # kicker
    kp = ease_out(clamp01(f / 20.0))
    d.text((140, 120 + int(14 * (1 - kp))), f"{KICKER}  •  DOCUMENTARIO",
           font=F_KICK, fill=MUT + (int(255 * kp),))
    # title
    tp = ease_out(clamp01((f - 6) / 24.0))
    ty = 190 + int(26 * (1 - tp))
    # shadow + main
    d.text((142, ty + 2), TITLE, font=F_TITLE, fill=SHD + (int(160 * tp),))
    d.text((140, ty), TITLE, font=F_TITLE, fill=INK + (int(255 * tp),))
    # amber underline sweep
    up = smoother((f - 22) / 18.0)
    if up > 0:
        uw = int(560 * up)
        bar = Image.new("RGBA", (uw, 8), AMB + (255,))
        layer.alpha_composite(bar, (140, ty + 108))
    # bullets
    y = 420
    for i, b in enumerate(BULLETS):
        dl = 34 + i * 13
        if rid == "bullet_3d_doc_lateral_track":
            p = ease_out(clamp01((f - dl) / 22.0))
            xo = int(70 * (1 - p)); yo = 0
        elif rid == "bullet_3d_doc_handheld_settle":
            p = ease_out(clamp01((f - dl) / 16.0))
            sc = 1.06 - 0.06 * p
            xo, yo = 0, int(16 * (1 - p))
        else:
            p = ease_out(clamp01((f - dl) / 22.0))
            xo, yo = 0, int(30 * (1 - p))
        a = int(255 * p)
        if a <= 0:
            y += 130; continue
        # marker dot + number
        d.ellipse([140 + xo - 2, y + yo + 18, 140 + xo + 14, y + yo + 34], fill=AMB + (a,))
        d.text((170 + xo, y + yo), f"0{i+1}", font=F_NUM, fill=AMB + (a,))
        d.text((262 + xo, y + yo + 4), b, font=F_BUL, fill=INK + (a,))
        # thin rule grows
        rw = int(900 * ease_out(clamp01((f - dl - 8) / 26.0)))
        if rw > 4:
            rule = Image.new("RGBA", (rw, 2), (120, 130, 150, int(90 * p)))
            layer.alpha_composite(rule, (140, y + yo + 96))
        y += 130
    # fg parallax shift (camera * 1.0, small: text rides camera)
    sx, sy = int(round(fcx)), int(round(fcy))
    if sx or sy:
        layer = layer.transform((W, H), Image.AFFINE, (1, 0, -sx, 0, 1, -sy),
                                resample=Image.BILINEAR)
    # micro-orbit focus pull: slight blur early
    if rid == "bullet_3d_doc_micro_orbit" and f < 40:
        layer = layer.filter(ImageFilter.GaussianBlur(8 * (1 - f / 40.0)))
    return layer

def render_one(rid):
    dst = OUT / f"{rid}_5s.mp4"
    cmd = ["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
           "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
           "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "20",
           "-preset", "veryfast", "-movflags", "+faststart", str(dst)]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for f in range(N):
        s, cx, cy = cam_path(rid, f)
        bg = crop_layer(BG_BIG, s, cx, cy, 0.3)
        dust = crop_layer(DUST_BIG, s, cx, cy, 0.6).convert("RGBA")
        frame = bg.convert("RGBA")
        frame.alpha_composite(dust)
        frame.alpha_composite(text_rgba(rid, f))
        # grain shimmer cheap: per-frame luminance jitter +-2
        proc.stdin.write(frame.convert("RGB").tobytes())
    proc.stdin.close(); proc.wait()
    if proc.returncode != 0:
        print(f"FAIL {rid}"); return None
    print(f"ok {dst.name} ({dst.stat().st_size//1024} KB)")
    return dst

if __name__ == "__main__":
    ids = sys.argv[1:] or ["bullet_3d_doc_push_in", "bullet_3d_doc_lateral_track",
        "bullet_3d_doc_crane_rise", "bullet_3d_doc_micro_orbit",
        "bullet_3d_doc_handheld_settle"]
    bad = [r for r in ids if render_one(r) is None]
    sys.exit(1 if bad else 0)
