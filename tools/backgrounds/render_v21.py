#!/usr/bin/env python3
"""Render V2.1 animated editorial compositions + stroke matrix (light CRF23).

Usage: render_v21.py [JOB...]  (default: all)
Jobs: A_black B_black C_black A_01 B_01 C_01 A_03 B_03 C_03 A_06 B_06 C_06 stroke
Out: out/docbg_v21/<job>.mp4 (1920x1080, 30fps, 8s, CRF23 veryfast).
"""
import subprocess
import sys
from pathlib import Path
from PIL import Image

sys.path.insert(0, str(Path(__file__).parent))
from editorial_compositions_v21 import comp_A, comp_B, comp_C, framed_photo, stroke_matrix_plate
from documentary_background_v2 import build_v2

ROOT = Path("/home/pierone/src/go-master/projects/Pyt/VeloxEditing")
import os
OUT = ROOT / "out" / os.environ.get("V21_OUT", "docbg_v21")
OUT.mkdir(parents=True, exist_ok=True)
FONTS = ROOT / "ChrononTemplate" / "assets" / "fonts"
FB = str(FONTS / "Play-Bold.ttf")
FR = str(FONTS / "Play-Regular.ttf")

DRIFT = ("scale=2000:1125,"
         "crop=1920:1080:x='40-80*n/240':y='22-45*n/240',setsar=1")


# Fluid motion: ease-out cubic for entrances (fast start, soft landing),
# smootherstep for traces/pushes (soft both ends). Linear ramps read as mechanical.
def ease_out(x: str) -> str:
    return f"1-pow(1-({x}),3)"


def smooth(x: str) -> str:
    return f"({x})*({x})*(3-2*({x}))"


def dttang(font, text, color, size, x, y, delay, dur, rise):
    x0 = f"min(1,max(0,(t-{delay})/{dur}))"
    k = ease_out(x0)
    return (f"drawtext=fontfile={font}:text='{text}':fontcolor={color}:fontsize={size}:"
            f"x={x}:y='{y}+{rise}*(1-{k})':alpha='{k}'")


def amber_bar(w: int, h: int) -> Image.Image:
    return Image.new("RGBA", (w, h), (240, 200, 120, 255))


def run(job, plate: Image.Image, comp: dict, photo_xy=None):
    # NOTE: drawbox w/h and crop w/h are config-time only in ffmpeg 4.4, so
    # progressive width reveal uses a geq alpha mask (per-frame) on a bar overlay.
    plate_path = OUT / f"_{job}_plate.png"
    plate.save(plate_path)
    inputs = ["-loop", "1", "-i", str(plate_path)]
    a = comp["anim"]
    idx, nxt = 1, "bg"
    cur = f"[0:v]{DRIFT}[bg]"
    if comp.get("photo") is not None and photo_xy:
        ph_path = OUT / f"_{job}_photo.png"
        comp["photo"].save(ph_path)
        inputs += ["-loop", "1", "-i", str(ph_path)]
        px, py = photo_xy
        pp = "min(1,t/8)"
        cur = f"[0:v]{DRIFT}[bg0];[bg0][{idx}:v]overlay=x='{px}-8+16*{smooth(pp)}':y={py}[bg]"
        idx += 1
    if "underline" in a:
        u = a["underline"]
        bar_path = OUT / f"_{job}_bar.png"
        amber_bar(u["w"], u["h"]).save(bar_path)
        inputs += ["-loop", "1", "-i", str(bar_path)]
        p = f"min(1,max(0,(T-{u['delay']})/{u['dur']}))"
        k = f"{u['w']}*{smooth(p)}"
        cur += (f";[{idx}:v]format=rgba,geq=r='r(X,Y)':g='g(X,Y)':b='b(X,Y)':a='if(lt(X,{k}),255,0)'[bar];"
                f"[{nxt}][bar]overlay=x={u['x']}:y={u['y']}[bg2]")
        nxt = "bg2"
        idx += 1
    post = []
    if "title" in a:
        t = a["title"]
        post.append(dttang(FB, t["text"], a["ink"], t["size"], t["x"], t["y"],
                           t.get("delay", 0), t["fade_dur"], t["rise_px"]))
        if "title2" in a:
            t2 = a["title2"]
            post.append(dttang(FR, t2["text"], a["ink"], t2["size"], t2["x"], t2["y"],
                               t2.get("delay", 0), t2["fade_dur"], t2["rise_px"]))
    if "lines" in a:
        for ln in a["lines"]:
            f = FB if not ln.get("attr") else FR
            post.append(dttang(f, ln["text"], a["ink"], ln["size"],
                               "'(w-text_w)/2'", ln["y"], ln["delay"], a["fade_dur"], 12))
    full = cur + (f";[{nxt}]" + ",".join(post) + ",format=yuv420p" if post
                  else f";[{nxt}]format=yuv420p")
    dst = OUT / f"{job}.mp4"
    cmd = ["ffmpeg", "-y", "-v", "error"] + inputs + ["-filter_complex", full,
           "-c:v", "libx264", "-crf", "23", "-preset", "veryfast", "-r", "30", "-t", "8", str(dst)]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print(f"FAIL {job}:\n{r.stderr[-2000:]}")
        return False
    print(f"ok {dst.name} ({dst.stat().st_size//1024} KB)")
    return True


def stroke_job():
    from PIL import ImageDraw, ImageFont
    W, H = 1920, 1080
    # base: weights + labels only
    S = 2
    base = Image.new("RGBA", (W * S, H * S), (13, 14, 17, 255))
    d = ImageDraw.Draw(base, "RGBA")
    fk = ImageFont.truetype(FB, 24 * S)
    fr = ImageFont.truetype(FR, 30 * S)
    fb = ImageFont.truetype(FB, 44 * S)
    d.text((120 * S, 60 * S), "STROKE QUALITY MATRIX - weights / curve / underline / taper / reveal", font=fk, fill=(200, 200, 205, 255))
    y = 120 * S
    for label, px in [("0.75 px", 1.5), ("1.5 px", 3), ("3 px", 6), ("6 px", 12)]:
        d.text((120 * S, y), label, font=fr, fill=(220, 220, 225, 255))
        d.line([(420 * S, y + 20 * S), (1800 * S, y + 20 * S)], fill=(240, 240, 245, 255), width=max(1, int(px)))
        y += 110 * S
    import math
    d.text((120 * S, y), "curva 3 px", font=fr, fill=(220, 220, 225, 255))
    pts = []
    for i in range(101):
        t = i / 100
        x = 420 + t * 1380
        yy = 40 * math.sin(t * math.pi * 2) - t * 30
        pts.append((x * S, (y / S + 20 + yy) * S))
    curve = Image.new("RGBA", (W * S, H * S), (0, 0, 0, 0))
    ImageDraw.Draw(curve, "RGBA").line(pts, fill=(120, 200, 255, 255), width=6, joint="curve")
    y += 130 * S
    d.text((120 * S, y), "underline 4 px", font=fr, fill=(220, 220, 225, 255))
    s = "La carta ricorda"
    d.text((420 * S, y - 10 * S), s, font=fb, fill=(245, 243, 238, 255))
    b = d.textbbox((420 * S, y - 10 * S), s, font=fb)
    ux, uw = b[0] // S, (b[2] - b[0]) // S
    uy = (b[3] + 8 * S) // S
    y += 130 * S
    d.text((120 * S, y), "taper 8>1 px", font=fr, fill=(220, 220, 225, 255))
    taper = Image.new("RGBA", (W * S, H * S), (0, 0, 0, 0))
    ImageDraw.Draw(taper, "RGBA").polygon(
        [(420 * S, y + 12 * S), (1800 * S, y + 19 * S), (1800 * S, y + 21 * S), (420 * S, y + 28 * S)],
        fill=(150, 230, 170, 255))
    base = base.resize((W, H), Image.LANCZOS)
    curve = curve.resize((W, H), Image.LANCZOS)
    taper = taper.resize((W, H), Image.LANCZOS)
    bp, cp, tp = OUT / "_stroke_base.png", OUT / "_stroke_curve.png", OUT / "_stroke_taper.png"
    base.save(bp)
    # animated reveals via cropped overlay inputs
    cw_anim = f"1380*min(1,max(0,(t-1.2)/1.5))"
    tw_anim = f"1380*min(1,max(0,(t-4.0)/1.0))"
    uw_anim = f"{uw}*min(1,max(0,(t-3.0)/0.6))"
    # crop w/h is config-time only, so curve/taper reveal via staggered alpha
    # fade; straight-line reveal stays progressive via per-frame drawbox w.
    ubar = OUT / "_stroke_ubar.png"
    tbar = OUT / "_stroke_tbar.png"
    amber_bar(uw, 8).save(ubar)
    amber_bar(1380, 6).save(tbar)
    upp = "min(1,max(0,(T-3.0)/0.6))"
    tpp = "min(1,max(0,(T-0.6)/0.8))"
    uk = f"{uw}*{smooth(upp)}"
    tk = f"1380*{smooth(tpp)}"
    filt = (f"[1:v]format=rgba,fade=t=in:st=1.2:d=1.5:alpha=1[cv];"
            f"[2:v]format=rgba,fade=t=in:st=4.0:d=1.0:alpha=1[tp];"
            f"[3:v]format=rgba,geq=r='r(X,Y)':g='g(X,Y)':b='b(X,Y)':a='if(lt(X,{uk}),255,0)'[ub];"
            f"[4:v]format=rgba,geq=r='r(X,Y)':g='g(X,Y)':b='b(X,Y)':a='if(lt(X,{tk}),255,0)'[tb];"
            f"[0:v]{DRIFT},format=rgb24[bg];"
            f"[bg][cv]overlay=x=0:y=0:format=rgb[o1];"
            f"[o1][tp]overlay=x=0:y=0:format=rgb[o2];"
            f"[o2][ub]overlay=x={ux}:y={uy}:format=rgb[o3];"
            f"[o3][tb]overlay=x=420:y=360:format=rgb,format=yuv420p")
    # overlays must be cropped to content origin: shift curve/taper into crop origin
    curve_c = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    curve_c.alpha_composite(curve, (0, 0))
    # crop from x=0 reveals from left edge of frame; shift art left so x=420 aligns:
    curve_shift = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    curve_shift.alpha_composite(curve.crop((420, 540, W, 660)), (0, 0))
    taper_shift = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    taper_shift.alpha_composite(taper.crop((420, 800, W, 860)), (0, 0))
    curve_shift.save(cp)
    taper_shift.save(tp)
    dst = OUT / "stroke_quality_matrix.mp4"
    cmd = ["ffmpeg", "-y", "-v", "error", "-loop", "1", "-i", str(bp),
           "-loop", "1", "-i", str(cp), "-loop", "1", "-i", str(tp),
           "-loop", "1", "-i", str(ubar), "-loop", "1", "-i", str(tbar),
           "-filter_complex", filt, "-c:v", "libx264", "-crf", "23",
           "-preset", "veryfast", "-r", "30", "-t", "8", str(dst)]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print(f"FAIL stroke:\n{r.stderr[-2000:]}")
        return False
    print(f"ok {dst.name} ({dst.stat().st_size//1024} KB)")
    return True


BGS = {
    "black": (Image.new("RGBA", (1920, 1080), (0, 0, 0, 255)), True),
    "01": (build_v2("01_dark_film_grain"), True),
    "03": (build_v2("03_archival_film"), True),
    "06": (build_v2("06_editorial_ivory"), False),
}
BUILDERS = {"A": comp_A, "B": comp_B, "C": comp_C}
PHOTO = framed_photo()


def job(name: str) -> bool:
    if name == "stroke":
        return stroke_job()
    c, bgid = name.split("_", 1)
    bg, dark = BGS[bgid]
    comp = BUILDERS[c](bg, dark, PHOTO) if c == "A" else BUILDERS[c](bg, dark)
    px = {"x": 1290, "y": 300} if c == "A" else None
    return run(f"{c}_{bgid}", comp["plate"], comp, (px["x"], px["y"]) if px else None)


if __name__ == "__main__":
    jobs = sys.argv[1:] or ["A_black", "B_black", "C_black", "A_01", "B_01", "C_01",
                             "A_03", "B_03", "C_03", "A_06", "B_06", "C_06", "stroke"]
    bad = [j for j in jobs if not job(j)]
    sys.exit(1 if bad else 0)
