#!/usr/bin/env python3
"""render_typewriter_dna_chapter.py — ricrea il frame DNA/CHAPTER 1 con testo typewriter.

Riferimento: visual_venture_channel_archive/classified_library/02_svg_vector_motion/
08_DNA_Tests_Exposed_Family_Secrets_frame_0042..0045.png
- sfondo quasi nero con alone rosso centrale + polvere
- kicker "CHAPTER 1" bianco con glow, sopra la banda
- banda rossa orizzontale con titolo bianco typewriter + caret

Contratto GPU gia' verificato in v1 (render_typewriter_modern.py):
- reveal typing con opacity=0 + window sulla coda (square)
- solo style.glow, mai effects: bloom sul sink Vulkan
- contact sheet con eq(n,X), non select con +

Uso:
  python tools/important_phrases/render_typewriter_dna_chapter.py
  python tools/important_phrases/render_typewriter_dna_chapter.py --render
"""
from __future__ import annotations
import argparse, json, os, shutil, subprocess, sys, time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WORKSPACE = ROOT.parent
OUT_ROOT = ROOT / "out" / "typewriter_dna_chapter_v1"

WIDTH, HEIGHT = 1920, 1080
FPS = 30
DUR = 180
FONT_REL = "ChrononTemplate/assets/fonts/Inter-ExtraBold.ttf"
KICKER, PHRASE = "CHAPTER 1", "THE CHILD WHO FOOLED AN ENTIRE FAMILY"
KICKER_Y, BANNER_Y = 452.0, 560.0
BANNER_W, BANNER_H = 1560.0, 120.0
RED = [0.78, 0.086, 0.10, 1.0]          # #C7161A
RED_HI = [0.91, 0.15, 0.17, 0.55]       # riflesso centrale
INK = "#FFFFFF"
TYPE_START = 18.0
CHUNK = 60


def hex_rgba(h): return [int(h.lstrip("#")[i:i+2], 16)/255.0 for i in (0, 2, 4)]+[1.0]
def track(prop, kfs, easing="linear"): return {"property": prop, "easing": easing, "keyframes": kfs}
def kfs(pairs): return [{"frame": f, "value": v} for f, v in pairs]

def measure(phrase, target, cap):
    from PIL import ImageFont
    fp = WORKSPACE / FONT_REL
    font = ImageFont.truetype(str(fp), 160)
    return min(cap, 160 * (target / font.getlength(phrase)))

def glyph_starts(phrase, size):
    from PIL import ImageFont
    font = ImageFont.truetype(str(WORKSPACE / FONT_REL), int(size))
    starts, x = [], 0.0
    for ch in phrase:
        starts.append(x); x += font.getlength(ch)
    return starts, x

def reveal_animator(ts, te):
    return {"selectors": [{"unit": "glyph", "shape": "square", "order": "forward",
        "start": {"keyframes": kfs([(0, 0.0), (int(ts), 0.0), (int(te)+1, 100.0), (DUR, 100.0)])},
        "end": {"keyframes": kfs([(0, 100.0), (DUR, 100.0)])}}],
        "properties": [track("opacity", kfs([(0, 0.0), (DUR, 0.0)]))]}

def build_plan() -> Path:
    from PIL import ImageFont
    ksize = measure(KICKER, 420.0, 72.0)
    psize = measure(PHRASE, 1440.0, 68.0)
    font = ImageFont.truetype(str(WORKSPACE / FONT_REL), int(psize))
    total = font.getlength(PHRASE)
    starts, _ = glyph_starts(PHRASE, psize)
    te = TYPE_START + len(PHRASE) * 2.2

    layers = [
        {"id": "bg", "type": "shape", "size": [WIDTH, HEIGHT],
         "position": [WIDTH/2.0, HEIGHT/2.0], "start_frame": 0, "duration_frames": DUR,
         "shape": {"type": "rect", "fill": [0.012, 0.014, 0.02, 1.0]}},
        {"id": "red_glow_wide", "type": "shape", "size": [1650.0, 850.0],
         "position": [960.0, 620.0], "start_frame": 0, "duration_frames": DUR,
         "shape": {"type": "ellipse", "fill": [0.38, 0.07, 0.05, 0.6]},
         "style": {"glow": {"radius": 140.0, "intensity": 0.65, "color": "#FF2A1A"}},
         "animation": {"tracks": [track("opacity", kfs([(0, 0.85), (90, 1.0), (DUR, 0.9)]))] }},
        {"id": "red_glow_core", "type": "shape", "size": [950.0, 420.0],
         "position": [960.0, 600.0], "start_frame": 0, "duration_frames": DUR,
         "shape": {"type": "ellipse", "fill": [0.55, 0.12, 0.07, 0.7]},
         "style": {"glow": {"radius": 90.0, "intensity": 0.7, "color": "#FF3A22"}},
         "animation": {"tracks": [track("opacity", kfs([(0, 0.9), (90, 1.0), (DUR, 0.92)]))] }},
    ]
    # grain cinematografico: 48 granelli con flicker + deriva (twinkle diseguale)
    import random
    rng = random.Random(7)
    for i in range(48):
        x = rng.uniform(80, 1840); y = rng.uniform(80, 1000)
        s = rng.choice([2.0, 2.0, 3.0]); dy = rng.uniform(-30, 30)
        a0 = round(rng.uniform(0.12, 0.5), 3); a1 = round(rng.uniform(0.12, 0.5), 3)
        f1 = rng.randint(40, 90); f2 = rng.randint(100, 160)
        layers.append({"id": f"grain_{i:02d}", "type": "shape", "size": [s, s],
            "position": [x, y], "start_frame": 0, "duration_frames": DUR,
            "shape": {"type": "rect", "fill": [1.0, 0.95, 0.9, 0.5]},
            "animation": {"tracks": [
                track("position_y", kfs([(0, 0.0), (DUR, dy)])),
                track("opacity", kfs([(0, a0), (f1, a1), (f2, a0), (DUR, a1)]))]}})
    # perline: scanline sottili su tutto il frame + vignetta cinema sopra/sotto
    for j in range(36):
        y = 15.0 + j*30.0
        if 490.0 <= y <= 630.0: continue  # la banda resta rosso pieno, non sporcata
        layers.append({"id": f"scan_{j:02d}", "type": "shape", "size": [1920.0, 2.0],
            "position": [960.0, y], "start_frame": 0, "duration_frames": DUR,
            "shape": {"type": "rect", "fill": [0.0, 0.0, 0.0, 0.07]}})
    for bid, by, bh, ba in [("vig_top", 45.0, 90.0, 0.42), ("vig_bot", 1035.0, 90.0, 0.42)]:
        layers.append({"id": bid, "type": "shape", "size": [1920.0, bh],
            "position": [960.0, by], "start_frame": 0, "duration_frames": DUR,
            "shape": {"type": "rect", "fill": [0.0, 0.0, 0.0, ba]}})
    layers += [
        {"id": "kicker", "type": "text", "text": KICKER, "size": [800, 130],
         "position": [960.0, KICKER_Y], "start_frame": 0, "duration_frames": DUR,
         "style": {"font": FONT_REL, "font_size": ksize, "fill": INK,
                   "glow": {"radius": 30.0, "intensity": 0.9, "color": "#FFFFFF"}},
         "spans": [{"start": 0, "end": len(KICKER.encode()), "style": {"tracking": 6.0}}],
         "animation": {"tracks": [track("opacity", kfs([(0, 0.0), (20, 1.0), (DUR, 1.0)]))]}},
        {"id": "banner", "type": "shape", "size": [BANNER_W, BANNER_H],
         "position": [960.0, BANNER_Y], "start_frame": 0, "duration_frames": DUR,
         "shape": {"type": "rect", "fill": RED}},
        {"id": "banner_hi", "type": "shape", "size": [BANNER_W, 36.0],
         "position": [960.0, BANNER_Y - BANNER_H/2 + 22.0], "start_frame": 0, "duration_frames": DUR,
         "shape": {"type": "rect", "fill": RED_HI}},
        {"id": "banner_lo", "type": "shape", "size": [BANNER_W, 30.0],
         "position": [960.0, BANNER_Y + BANNER_H/2 - 15.0], "start_frame": 0, "duration_frames": DUR,
         "shape": {"type": "rect", "fill": [0.0, 0.0, 0.0, 0.38]}},
        {"id": "banner_edge", "type": "shape", "size": [BANNER_W, 3.0],
         "position": [960.0, BANNER_Y - BANNER_H/2 + 1.5], "start_frame": 0, "duration_frames": DUR,
         "shape": {"type": "rect", "fill": [1.0, 0.45, 0.4, 0.8]}},
        {"id": "title_base", "type": "text", "text": PHRASE, "size": [1500, 150],
         "position": [960.0, BANNER_Y], "start_frame": 0, "duration_frames": DUR,
         "style": {"font": FONT_REL, "font_size": psize, "fill": INK},
         "spans": [{"start": 0, "end": len(PHRASE.encode()), "style": {"tracking": 0.0}}],
         "animation": {"tracks": [track("opacity", kfs([(0, 0.0), (DUR, 0.0)]))]}},
        {"id": "title_typed", "type": "text", "text": PHRASE, "size": [1500, 150],
         "position": [960.0, BANNER_Y], "start_frame": 0, "duration_frames": DUR,
         "style": {"font": FONT_REL, "font_size": psize, "fill": INK,
                   "glow": {"radius": 6.0, "intensity": 0.18, "color": "#FFFFFF"}},
         "spans": [{"start": 0, "end": len(PHRASE.encode()), "style": {"tracking": 0.0}}],
         "text_animators": [reveal_animator(TYPE_START, te)]},
    ]
    # caret bianco sulla banda, insegue la frontiera
    left = 960.0 - total/2.0; xk = []
    for f in range(0, DUR, 2):
        d = max(0.0, min(float(len(PHRASE)), (f-TYPE_START)/(te-TYPE_START)*len(PHRASE)))
        k = min(len(PHRASE), int(d))
        xk.append((f, (left + (starts[k] if k < len(PHRASE) else total)) - 960.0))
    layers.append({"id": "caret", "type": "shape", "size": [8.0, psize*0.8],
        "position": [960.0, BANNER_Y], "start_frame": 0, "duration_frames": DUR,
        "shape": {"type": "rect", "fill": hex_rgba("#FFFFFF")},
        "style": {"glow": {"radius": 10.0, "intensity": 0.3, "color": "#FFFFFF"}},
        "animation": {"tracks": [track("position_x", kfs(xk)),
            track("opacity", kfs([(0,0.0),(int(TYPE_START),0.0),(int(TYPE_START+10),1.0),(DUR,1.0)]))]}})

    samples = []
    for f in range(DUR):
        t = f / max(1, DUR - 1); e = t * t * (3.0 - 2.0 * t)
        cam = {"type": "perspective", "position": [0.0, 0.0, -1000.0 + 70.0 * e],
            "rotation_deg": [0.0, 0.0, 0.0], "fov_deg": 45, "near": 1, "far": 10000,
            "zoom": 1, "sensor_width_mm": 36, "lens_shift": [0, 0]}
        samples.append({"frame": f, "camera": cam})
    plan = {"schema": "chronon.render-plan.v3", "version": 3, "job_id": "dna_chapter_typewriter",
        "canvas": {"width": WIDTH, "height": HEIGHT, "fps_num": FPS, "fps_den": 1, "duration_frames": DUR},
        "camera": samples[0]["camera"], "camera_samples": samples,
        "layers": layers, "output": {"path": "dna_chapter_typewriter.mp4", "format": "mp4", "codec": "h264"}}
    OUT_ROOT.mkdir(parents=True, exist_ok=True)
    p = OUT_ROOT / "dna_chapter_typewriter.plan.json"
    p.write_text(json.dumps(plan, indent=2)+"\n", encoding="utf-8")
    return p

def default_cli():
    override = os.environ.get("CHRONON_CLI")
    if override: return Path(override)
    cands = sorted((WORKSPACE/"Chronon3d"/"build"/"chronon").glob("*/apps/chronon3d_cli/chronon3d_cli*"))
    cands = [c for c in cands if c.suffix in ("", ".exe")]
    if not cands: raise SystemExit("chronon3d CLI not found")
    return cands[-1]

def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--render", action="store_true"); ap.add_argument("--max-attempts", type=int, default=5)
    a = ap.parse_args()
    plan_path = build_plan(); print(f"Wrote {plan_path}", flush=True)
    if not a.render: return 0
    cli = default_cli().resolve()
    subprocess.run([str(cli), "validate", "--plan", str(plan_path),
        "--assets-root", str(WORKSPACE)], check=True, cwd=WORKSPACE)
    video = OUT_ROOT / "dna_chapter_typewriter.mp4"
    scratch = OUT_ROOT / "chunks"; scratch.mkdir(parents=True, exist_ok=True); parts = []
    for start in range(0, DUR, CHUNK):
        end = min(start+CHUNK-1, DUR-1); part = scratch / f"part_{start:05d}.mp4"; parts.append(part)
        for att in range(1, a.max_attempts+1):
            yuv = part.with_suffix(".yuv")
            cmd = [str(cli), "render", "--backend", "vulkan", "--plan", str(plan_path),
                   "--assets-root", str(WORKSPACE), "-o", str(yuv), "--video-sink", "raw",
                   "--pipe-pixfmt", "yuv420p", "--start-frame", str(start), "--end-frame", str(end)]
            print(f"[chunk] {start}-{end} att{att}", flush=True)
            with open(part.with_suffix(".log"), "w") as h:
                subprocess.run(cmd, check=True, cwd=WORKSPACE, stdout=h, stderr=subprocess.STDOUT)
            break
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "yuv420p",
            "-s", f"{WIDTH}x{HEIGHT}", "-r", str(FPS), "-i", str(yuv),
            "-c:v", "h264_nvenc", "-preset", "p7", "-cq", "19", str(part)], check=True, cwd=WORKSPACE)
        yuv.unlink(missing_ok=True)
    listing = scratch / "concat.txt"
    listing.write_text("\n".join(f"file '{p.as_posix()}'" for p in parts)+"\n", encoding="utf-8")
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0",
        "-i", str(listing), "-c", "copy", str(video)], check=True, cwd=WORKSPACE)
    shutil.rmtree(scratch, ignore_errors=True)
    sheet = OUT_ROOT / "dna_chapter_typewriter_contact_sheet.png"
    sel = "+".join(f"eq(n\\,{f})" for f in [30, 60, 100, 150, 178])
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(video), "-vf",
        f"select={sel},scale=640:360,tile=5x1", "-frames:v", "1", str(sheet)], check=True, cwd=WORKSPACE)
    print(f"Rendered {video}; {sheet}", flush=True)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
