#!/usr/bin/env python3
"""Bulletpoints 3D SIMPLE — solo testo centrato tipo 'Capitolo 1 : Parte iniziale'.
5 camera doc + Play font, 5s 1920x1080 30fps. Out: out/bullets_3d_simple_5s/<id>_5s.mp4
"""
import math, subprocess, sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from ChrononTemplate.tools.backgrounds.documentary_background_v2 import (
    base_dark_graphite, dust_overlay, soft_vignette_overlay, diffuse_light_pool)

W, H, FPS, N = 1920, 1080, 30, 150
OUT = ROOT / "out" / "bullets_3d_simple_5s"
OUT.mkdir(parents=True, exist_ok=True)
FONTS = ROOT / "ChrononTemplate" / "assets" / "fonts"
FB, FR = str(FONTS / "Play-Bold.ttf"), str(FONTS / "Play-Regular.ttf")
INK, MUT, AMB, SHD = (245,243,238), (200,200,205), (240,200,120), (0,0,0)
OW, OH = 2200, 1240

def build_plates(seed=11):
    bg = base_dark_graphite(seed).convert("RGBA").resize((OW, OH), Image.BILINEAR)
    bg.alpha_composite(diffuse_light_pool(OW, OH, (88,58,34), 0.08, cxr=0.5, cyr=0.45, spread=1.3).resize((OW, OH)))
    bg.alpha_composite(soft_vignette_overlay(OW, OH, 0.16, seed+5))
    return bg.convert("RGB"), dust_overlay(OW, OH, seed+7, n=70)
BG_BIG, DUST_BIG = build_plates()

F_KICK = ImageFont.truetype(FB, 40)
F_TITLE = ImageFont.truetype(FB, 120)
F_SUB = ImageFont.truetype(FR, 54)

KICKER, TITLE, SUB = "CAPITOLO 1", "Parte iniziale", "l'inizio della storia"

def ease_out(x): return 1-(1-x)**3
def smoother(x):
    x = min(1.0, max(0.0, x)); return x*x*x*(x*(x*6-15)+10)
def c01(x): return min(1.0, max(0.0, x))

def cam(rid, f):
    t = f/(N-1)
    if rid == "cap1_push_in":
        return 1.08-0.08*smoother(t), 8*t, 5*t
    if rid == "cap1_lateral":
        return 1.06-0.01*smoother(t), -45+90*smoother(t), 4*math.sin(t*math.pi)
    if rid == "cap1_crane":
        return 1.05-0.02*smoother(t), 5*math.sin(t*math.pi*2), 35-70*smoother(t)
    if rid == "cap1_orbit":
        return 1.0+0.015*math.sin(t*math.pi), 18*math.sin(t*math.pi*2), 8*math.sin(t*math.pi*2+1.0)
    if rid == "cap1_handheld":
        dec = math.exp(-f/38.0)
        hx = 14*dec*math.sin(2*math.pi*f/23.0)+5*dec*math.sin(2*math.pi*f/7.3+1.2)
        hy = 10*dec*math.sin(2*math.pi*f/29.0+0.5)+4*dec*math.sin(2*math.pi*f/9.1)
        return 1.04-0.04*smoother(t), hx, hy
    return 1.0, 0.0, 0.0

def crop(plate, s, cx, cy, par):
    ww, hh = OW/s, OH/s
    x0 = min(max(0, (OW-ww)/2 + cx*par), OW-ww)
    y0 = min(max(0, (OH-hh)/2 + cy*par), OH-hh)
    return plate.crop((int(x0), int(y0), int(x0+ww), int(y0+hh))).resize((W, H), Image.BILINEAR)

def fg(rid, f):
    _, fcx, fcy = cam(rid, f)
    L = Image.new("RGBA", (W, H), (0,0,0,0))
    d = ImageDraw.Draw(L)
    kp = ease_out(c01(f/18.0))
    tp = ease_out(c01((f-8)/24.0))
    sp = ease_out(c01((f-26)/24.0))
    def ct(font, txt, y, yo, a, col=INK):
        bb = d.textbbox((0,0), txt, font=font)
        tw = bb[2]-bb[0]
        d.text(((W-tw)/2+2, y+yo+3), txt, font=font, fill=SHD+(int(150*a),))
        d.text(((W-tw)/2, y+yo), txt, font=font, fill=col+(int(255*a),))
    ct(F_KICK, KICKER, 360, int(16*(1-kp)), kp, AMB)
    # small amber rule under kicker
    rw = int(220*smoother((f-14)/16.0))
    if rw > 4:
        bar = Image.new("RGBA", (rw, 5), AMB+(255,))
        L.alpha_composite(bar, ((W-rw)//2, 440))
    ct(F_TITLE, TITLE, 480, int(30*(1-tp)), tp)
    ct(F_SUB, SUB, 660, int(22*(1-sp)), sp, MUT)
    sx, sy = int(round(fcx)), int(round(fcy))
    if sx or sy:
        L = L.transform((W,H), Image.AFFINE, (1,0,-sx,0,1,-sy), resample=Image.BILINEAR)
    if rid == "cap1_orbit" and f < 35:
        L = L.filter(ImageFilter.GaussianBlur(7*(1-f/35.0)))
    return L

def render_one(rid):
    dst = OUT / f"{rid}_5s.mp4"
    cmd = ["ffmpeg","-y","-v","error","-f","rawvideo","-pix_fmt","rgb24",
           "-s",f"{W}x{H}","-r",str(FPS),"-i","-","-c:v","libx264",
           "-pix_fmt","yuv420p","-crf","20","-preset","veryfast",
           "-movflags","+faststart",str(dst)]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for f in range(N):
        s, cx, cy = cam(rid, f)
        fr = crop(BG_BIG, s, cx, cy, 0.3).convert("RGBA")
        fr.alpha_composite(crop(DUST_BIG, s, cx, cy, 0.6).convert("RGBA"))
        fr.alpha_composite(fg(rid, f))
        p.stdin.write(fr.convert("RGB").tobytes())
    p.stdin.close(); p.wait()
    print(("FAIL " if p.returncode else "ok ")+dst.name, flush=True)
    return p.returncode == 0

if __name__ == "__main__":
    ids = sys.argv[1:] or ["cap1_push_in","cap1_lateral","cap1_crane","cap1_orbit","cap1_handheld"]
    sys.exit(0 if all(render_one(r) for r in ids) else 1)
