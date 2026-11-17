#!/usr/bin/env python3
"""10 modern phrase styles (new fonts, simple backgrounds), authored as Chronon render plans and
rendered with chronon3d_cli. Recreates the 'Kind of. But also, not really.' reference:
3 colour groups, coloured glow, soft reflection shadow, staggered rise-in.
Usage: build_phrase_styles_v2.py [out_dir] [style_idx ...]"""
import json, subprocess, sys
from pathlib import Path
import numpy as np
from PIL import Image, ImageFont
from fontTools.ttLib import TTFont
from fontTools.varLib import instancer

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
C3D = REPO / "Chronon3d"
FONTS = C3D / "assets/fonts"
SRC = REPO / "RenderingGen/Upload/style_presets_20261117/fonts"
OUT = Path(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1] else REPO / "RenderingGen/Upload/style_presets_20261117/chronon"
CLI = C3D / "build/chronon/linux-video-release/apps/chronon3d_cli/chronon3d_cli"
W, H, FPS, FR = 1920, 1080, 30, 120
Y, WH, R = "#FFD83A", "#FFFFFF", "#FF2A1F"
GROUPS = ["Kind of.", "But also,", "not really."]

# id, source font, static name, axes, size, bg1, bg2, colours, light-bg?
STY = [
 ("01_newsreader_graphite", "Newsreader[opsz,wght].ttf", "Newsreader-Medium.ttf", dict(wght=500, opsz=48), 128, "#4a4a4a", "#121212", (Y, WH, R), False),
 ("02_sourceserif_charcoal", "SourceSerif4[opsz,wght].ttf", "SourceSerif4-Semibold.ttf", dict(wght=600, opsz=48), 120, "#3c3c40", "#0e0e10", (WH, WH, WH), False),
 ("03_fraunces_cream", "Fraunces[SOFT,WONK,opsz,wght].ttf", "Fraunces-Semibold.ttf", dict(wght=600, opsz=72, SOFT=0, WONK=0), 124, "#f4eee2", "#d8cfba", ("#1a1a1a", "#1a1a1a", "#C2261B"), True),
 ("04_instrumentserif_navy", "InstrumentSerif-Regular.ttf", None, None, 150, "#223049", "#0a0f1a", ("#FFE08A", WH, "#FF7A6B"), False),
 ("05_youngserif_forest", "YoungSerif-Regular.ttf", None, None, 118, "#24402f", "#0a1510", ("#F6E7B0", WH, "#F28C5B"), False),
 ("06_gloock_wine", "Gloock-Regular.ttf", None, None, 118, "#4b1f2a", "#140509", ("#F5D9A8", WH, "#FF8F8F"), False),
 ("07_literata_slate", "Literata[opsz,wght].ttf", "Literata-Semibold.ttf", dict(wght=600, opsz=36), 118, "#e9edf1", "#c3ccd6", ("#0F2A47", "#0F2A47", "#D8322A"), True),
 ("08_geist_black", "Geist[wght].ttf", "Geist-Bold.ttf", dict(wght=700), 112, "#262626", "#000000", (WH, WH, "#4DA3FF"), False),
 ("09_figtree_sand", "Figtree[wght].ttf", "Figtree-ExtraBold.ttf", dict(wght=800), 118, "#efe3cf", "#cdb998", ("#2B2118", "#2B2118", "#E0541D"), True),
 ("10_onest_ink", "Onest[wght].ttf", "Onest-Bold.ttf", dict(wght=700), 114, "#1c2540", "#05070f", ("#7CF0C9", WH, "#FFB454"), False),
]

def hx(c): return np.array([int(c[i:i+2], 16) for i in (1, 3, 5)], np.float32)

def static_font(src, name, axes):
    if name is None:
        dst = FONTS / src
        if not dst.exists(): dst.write_bytes((SRC / src).read_bytes())
        return f"assets/fonts/{src}"
    dst = FONTS / name
    if not dst.exists():
        f = TTFont(SRC / src)
        instancer.instantiateVariableFont(f, axes, inplace=True)
        f.save(dst)
    return f"assets/fonts/{name}"

def plate(name, c1, c2):
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    d = np.clip(np.sqrt(((xx/W-.5)*1.1)**2 + (yy/H-.45)**2)/.8, 0, 1)[..., None]
    a = hx(c1)*(1-d) + hx(c2)*d + np.random.default_rng(3).normal(0, 1.2, (H, W, 1)).astype(np.float32)
    p = C3D / f"assets/images/{name}_plate.png"
    Image.fromarray(np.clip(a, 0, 255).astype(np.uint8)).save(p)
    return f"assets/images/{name}_plate.png"

def track(prop, keys, easing="out_cubic"):
    return {"property": prop, "keyframes": [{"frame": int(f), "value": v} for f, v in keys], "easing": easing}

def build(i):
    sid, src, sname, axes, size, b1, b2, cols, light = STY[i]
    font = static_font(src, sname, axes)
    pf = ImageFont.truetype(str(FONTS / font.split("/")[-1]), size)
    gap = int(size*.28); ws = [pf.getlength(g) for g in GROUPS]
    x = (W - (sum(ws)+gap*2))/2; layers = [{"id": "bg", "type": "image", "asset": plate(sid, b1, b2),
        "size": [W, H], "position": [0, 0], "start_frame": 0, "duration_frames": FR}]
    for k, (g, w, c) in enumerate(zip(GROUPS, ws, cols)):
        cx = x + w/2; x += w + gap
        s0 = 9 + k*14; s1 = s0 + 16
        def anim(dy, op, blur=0):
            return {"tracks": ([track("blur", [(0, blur), (FR, blur)], "linear")] if blur else []) + [track("position_y", [(0, 28), (s0, 28), (s1, 0)]),
                               track("opacity", [(0, 0), (s0, 0), (s1, op)], "linear")]}
        # reflection / soft shadow (flipped look approximated by blurred dark copy below)
        layers.append({"id": f"shadow{k}", "type": "text", "text": g, "size": [W, H], "position": [cx, 540+size*0.95],
            "style": {"font": font, "font_size": size, "fill": "#000000"},
            "start_frame": 0, "duration_frames": FR, "animation": anim(size*0.95, 0.18, 14)})
        layers.append({"id": f"word{k}", "type": "text", "text": g, "size": [W, H], "position": [cx, 540],
            "style": {"font": font, "font_size": size, "fill": c,
                      "glow": {"radius": 18 if not light else 10, "intensity": 0.55 if not light else 0.2, "color": c}},
            "start_frame": 0, "duration_frames": FR, "animation": anim(0, 1.0)})
    return sid, {"schema": "chronon.render-plan.v2", "version": 2, "job_id": sid,
        "canvas": {"width": W, "height": H, "fps_num": FPS, "fps_den": 1, "duration_frames": FR},
        "layers": layers, "output": {"path": sid+".mp4", "format": "mp4", "codec": "h264"}}

def main():
    OUT.mkdir(parents=True, exist_ok=True)
    idx = [int(a) for a in sys.argv[2:]] or range(len(STY))
    for i in idx:
        sid, plan = build(i); pp = OUT/f"{sid}.plan.json"; pp.write_text(json.dumps(plan, indent=1))
        r = subprocess.run([str(CLI), "render", "--plan", str(pp), "--assets-root", str(C3D), "--backend", "vulkan",
            "--hardware", "nvenc", "--encoder-backend", "native", "--gpu-hot-path-mode", "require_gpu_native",
            "--codec", "h264", "--fps", "30", "--rate-control", "qp", "--qp", "18", "-o", str(OUT/f"{sid}.mp4")],
            capture_output=True, text=True)
        (OUT/f"{sid}.log").write_text(r.stdout+r.stderr)
        print(sid, "OK" if r.returncode == 0 else "FAIL\n"+(r.stdout+r.stderr)[-600:], flush=True)
main()
