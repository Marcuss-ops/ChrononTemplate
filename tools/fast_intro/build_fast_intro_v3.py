#!/usr/bin/env python3
"""Fast Intro v3 — rebuilt from zero with a modern documentary language.

Deliberately NOT an evolution of v2. New rules:

- Display face Anton (condensed, monumental), labels Inter-Black. No Regular.
- Near-black canvas #0A0A0B, off-white ink, ONE signal-red accent #FF3B30.
- Film grain overlay (deterministic PNG, flickering opacity) on every recipe.
- Letterbox bars where cinema helps (cutline), negative space where not.
- Left-aligned monumental type with staggered word reveals (monolith/folio),
  split-screen number+image (statline), full-bleed directional whips (cutline).
- No radial orange gradients, no pills, no bouncing dots, no ivory.

Renderer dialect (proven against chronon3d_cli, see FAST_INTRO_V2_CONTRACT.md):
text/shape positions are canvas pixels (layer center); image/color positions
are center-relative (canvas center = [0,0]); text locks min/max to font_size;
easing in {linear, out_cubic, in_out_cubic, smoothstep}.

    python build_fast_intro_v3.py --out out/fast_intro_v3
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
TEMPLATE = HERE.parents[1]
DEFAULT_OUT = TEMPLATE / "out" / "fast_intro_v3"

W, H, FPS = 1920, 1080, 30
DISPLAY = "ChrononTemplate/assets/fonts/Anton-Regular.ttf"
LABEL = "ChrononTemplate/assets/fonts/Inter-Black.ttf"
GRAIN = "ChrononTemplate/assets/fast_intro_v3_grain.png"
COLLAGE = "ChrononTemplate/assets/images/retro_collage.png"

INK = "#F4F1EA"
MUTE = "#A8A29A"
ACCENT = "#FF3B30"
GROUND = "#0A0A0B"


def key(frame: int, value):
    return {"frame": frame, "value": value}


def track(prop: str, kfs, easing="out_cubic"):
    return {"property": prop, "easing": easing, "keyframes": kfs}


def rgba(hex_color: str, alpha: float = 1.0):
    h = hex_color.lstrip("#")
    return [int(h[0:2], 16) / 255.0, int(h[2:4], 16) / 255.0,
            int(h[4:6], 16) / 255.0, alpha]


def text_layer(lid, text, font, font_size, fill, pos, start, dur,
               box=None, tracks=None):
    w = box[0] if box else min(1720, int(len(text) * font_size * 0.52 + 120))
    h = box[1] if box else int(font_size * 2.0)
    style = {"font": font, "font_size": font_size, "fill": fill,
             "fit_mode": "shrink_only", "min_font_size": font_size,
             "max_font_size": font_size}
    layer = {"id": lid, "type": "text", "text": text, "size": [w, h],
             "position": list(pos), "start_frame": start,
             "duration_frames": dur, "style": style}
    if tracks:
        layer["animation"] = {"tracks": tracks}
    return layer


try:
    from PIL import ImageFont as _ImageFont
    _FONT_CACHE = {}

    def _measure(text, font_path, font_size):
        key = (font_path, font_size)
        if key not in _FONT_CACHE:
            _FONT_CACHE[key] = _ImageFont.truetype(
                str(TEMPLATE.parent / font_path), font_size)
        left, _, right, _ = _FONT_CACHE[key].getbbox(text)
        return right - left

    _HAS_PIL = True
except Exception:
    _HAS_PIL = False

    def _measure(text, font_path, font_size):
        return int(len(text) * 0.55 * font_size)


def left_text(lid, text, font, font_size, fill, left_x, y, start, dur,
            tracks=None):
    """Left-aligned text: the box is sized to the measured copy so its
    left edge lands exactly at left_x (layer position is the box center)."""
    w = int(_measure(text, font, font_size) + 80)
    return text_layer(lid, text, font, font_size, fill,
                        [left_x + w / 2, y], start, dur, box=[w, int(font_size * 2.0)],
                        tracks=tracks)


def shape_layer(lid, shape, pos, size, start, dur, tracks=None):
    layer = {"id": lid, "type": "shape", "shape": shape,
             "position": list(pos), "size": list(size),
             "start_frame": start, "duration_frames": dur}
    if tracks:
        layer["animation"] = {"tracks": tracks}
    return layer


def base_plan(job_id: str, duration: int):
    return {
        "schema": "chronon.render-plan.v3",
        "version": 3,
        "job_id": job_id,
        "canvas": {"width": W, "height": H, "fps_num": FPS,
                   "fps_den": 1, "duration_frames": duration},
        "camera": {"type": "perspective", "position": [0, 0, -1350],
                   "rotation_deg": [0, 0, 0], "fov_deg": 48.0,
                   "near": 1, "far": 10000, "zoom": 1.0},
        "camera_samples": [],
        "layers": [],
        "output": {"path": job_id + ".mp4", "format": "mp4", "codec": "h264"},
    }


def add_camera_push(plan: dict, push: float, duration: int):
    plan["camera_samples"] = [
        {"frame": f, "camera": {
            "type": "perspective",
            "position": [0, 0, -1350 + push * f / max(1, duration - 1)],
            "rotation_deg": [0, 0, 0], "fov_deg": 48.0,
            "near": 1, "far": 10000, "zoom": 1.0}}
        for f in range(duration)]


def ground_and_grain(plan, duration, grain_opacity=0.08):
    plan["layers"].append(
        {"id": "ground", "type": "color", "color": rgba(GROUND),
         "position": [0, 0], "size": [W, H], "start_frame": 0,
         "duration_frames": duration})
    flicker = []
    f = 0
    up = True
    while f < duration:
        flicker.append(key(f, round(grain_opacity + (0.02 if up else -0.02), 3)))
        up = not up
        f += 6
    flicker.append(key(duration - 1, grain_opacity))
    plan["layers"].append(
        {"id": "grain", "type": "image", "asset": GRAIN, "fit": "cover",
         "position": [0, 0], "size": [W, H], "start_frame": 0,
         "duration_frames": duration,
         "animation": {"tracks": [track("opacity", flicker, "linear")]}})


def build_monolith(duration=150):
    plan = base_plan("fast_intro_v3_monolith", duration)
    add_camera_push(plan, 120.0, duration)
    ground_and_grain(plan, duration)
    L = plan["layers"]
    L.append(left_text(
        "kicker", "CHRONON ORIGINAL", LABEL, 26, ACCENT, 240, 300, 0,
        duration,
        tracks=[track("opacity", [key(0, 0.0), key(8, 1.0)]),
                track("position_y", [key(0, 14), key(10, 0)])]))
    lines = [("THE", 470), ("STORY", 650), ("SO FAR", 830)]
    for i, (word, y) in enumerate(lines):
        inn = 8 + i * 6
        L.append(left_text(
            f"title_{i}", word, DISPLAY, 170, INK, 240, y, inn,
            duration - inn,
            tracks=[track("opacity", [key(inn, 0.0), key(inn + 10, 1.0)]),
                    track("position_y", [key(inn, 46), key(inn + 14, 0)])]))
    L.append(shape_layer(
        "accent_bar", {"type": "rect", "fill": rgba(ACCENT)},
        [240 + 60, 985], [120, 10], 26, duration - 26,
        [track("scale_x", [key(26, 0.02), key(40, 1.0)], "linear")]))
    L.append(left_text(
        "subtitle", "A short line that sets up the story.", LABEL, 30,
        MUTE, 240, 1050 - 60, 40, duration - 40,
        tracks=[track("opacity", [key(40, 0.0), key(52, 1.0)])]))
    return plan


def build_statline(duration=150):
    plan = base_plan("fast_intro_v3_statline", duration)
    add_camera_push(plan, 100.0, duration)
    ground_and_grain(plan, duration)
    L = plan["layers"]
    L.append(left_text(
        "kicker", "BY THE NUMBERS", LABEL, 26, ACCENT, 240, 330, 0,
        duration,
        tracks=[track("opacity", [key(0, 0.0), key(8, 1.0)])]))
    L.append(left_text(
        "number", "37.7M", DISPLAY, 300, INK, 240, 620, 0,
        duration,
        tracks=[track("opacity", [key(0, 0.0), key(8, 1.0)]),
                track("scale", [key(0, 1.6), key(24, 1.0)])]))
    L.append(left_text(
        "caption", "REACH ACROSS ONE SEASON", LABEL, 28, MUTE,
        240, 900, 18, duration - 18,
        tracks=[track("opacity", [key(18, 0.0), key(30, 1.0)]),
                track("position_y", [key(18, 20), key(30, 0)])]))
    L.append(shape_layer(
        "divider", {"type": "rect", "fill": rgba(ACCENT)},
        [960, 540], [3, 640], 10, duration - 10,
        [track("scale_y", [key(10, 0.02), key(26, 1.0)], "linear")]))
    # Right-half image: canvas center of the half is (1440, 540) -> [480, 0].
    L.append({"id": "photo", "type": "image", "asset": COLLAGE,
              "fit": "cover", "position": [480, 0], "size": [960, 1080],
              "start_frame": 60, "duration_frames": duration - 60,
              "animation": {"tracks": [
                  track("position_x", [key(60, 500), key(96, 0)]),
                  track("opacity", [key(60, 0.0), key(66, 1.0)],
                        "linear")]}})
    return plan


def build_cutline(duration=180, n_plates=10):
    from build_match_cut_plan import NEWS, WEB
    plan = base_plan("fast_intro_v3_cutline", duration)
    add_camera_push(plan, 90.0, duration)
    ground_and_grain(plan, duration, grain_opacity=0.06)
    L = plan["layers"]
    # Letterbox bars slide in from the edges (scale about their centers).
    L.append(shape_layer(
        "bar_top", {"type": "rect", "fill": [0, 0, 0, 1]},
        [960, 55], [W, 110], 0, duration,
        [track("scale_y", [key(0, 0.02), key(14, 1.0)], "linear")]))
    L.append(shape_layer(
        "bar_bottom", {"type": "rect", "fill": [0, 0, 0, 1]},
        [960, 1025], [W, 110], 0, duration,
        [track("scale_y", [key(0, 0.02), key(14, 1.0)], "linear")]))
    all_shots = (NEWS + WEB)[:n_plates]
    quick, hold = 8, 15
    cursor = 0
    for i, (plate, _kind) in enumerate(all_shots):
        length = hold if i % 3 == 1 else quick
        if i == len(all_shots) - 1:
            length = max(length, duration - cursor)
        s = cursor
        e = min(s + length, duration)
        if s >= duration:
            break
        direction = 1 if i % 2 == 0 else -1
        L.append({
            "id": f"shot_{i}", "type": "image",
            "asset": f"ChrononTemplate/assets/fast_intro_match_cut/{plate}.png",
            "fit": "cover", "position": [0, 0], "size": [W, H],
            "start_frame": s, "duration_frames": max(1, e - s),
            "animation": {"tracks": [
                track("position_x", [
                    key(s, direction * 1400),
                    key(min(s + 6, e - 1), 0)]),
                track("opacity", [
                    key(s, 0.0), key(min(s + 3, e - 1), 1.0)], "linear")]}})
        cursor += length
        if cursor >= duration:
            break
    L.append(left_text(
        "caption", "MATCH CUT — SEAMLESS STORIES", DISPLAY, 30, INK,
        240, 985, 14, duration - 14,
        tracks=[track("opacity", [key(14, 0.0), key(24, 1.0)])]))
    # Grain must sit above the plates: move it last.
    grain = next(l for l in L if l["id"] == "grain")
    L.remove(grain)
    L.append(grain)
    return plan


def build_folio(duration=150):
    plan = base_plan("fast_intro_v3_folio", duration)
    add_camera_push(plan, 80.0, duration)
    ground_and_grain(plan, duration, grain_opacity=0.05)
    L = plan["layers"]
    L.append(text_layer(
        "ghost", "01", DISPLAY, 500, INK, [1450, 540], 0, duration,
        box=[700, 700],
        tracks=[track("opacity", [key(0, 0.0), key(30, 0.14)], "linear")]))
    L.append(left_text(
        "tag", "CHAPTER 01", LABEL, 28, ACCENT, 240, 400, 4,
        duration - 4,
        tracks=[track("opacity", [key(4, 0.0), key(14, 1.0)]),
                track("position_y", [key(4, 16), key(14, 0)])]))
    for i, (word, y) in enumerate([("THE HITMAN", 600), ("HIDDEN IN A", 730),
                                   ("FAMILY PHOTO", 860)]):
        inn = 10 + i * 7
        L.append(left_text(
            f"title_{i}", word, DISPLAY, 110, INK, 240, y, inn,
            duration - inn,
            tracks=[track("opacity", [key(inn, 0.0), key(inn + 10, 1.0)]),
                    track("position_y", [key(inn, 36), key(inn + 14, 0)])]))
    L.append(shape_layer(
        "rule", {"type": "rect", "fill": [0.35, 0.34, 0.33, 1.0]},
        [240 + 600, 985], [1200, 2], 30, duration - 30,
        [track("scale_x", [key(30, 0.02), key(52, 1.0)], "linear")]))
    L.append(left_text(
        "meta", "A PARAMETRIC CHAPTER CARD", LABEL, 24, MUTE,
        240, 1025, 44, duration - 44,
        tracks=[track("opacity", [key(44, 0.0), key(56, 1.0)])]))
    return plan


RECIPES = {
    "monolith": (build_monolith, 150),
    "statline": (build_statline, 150),
    "cutline": (build_cutline, 180),
    "folio": (build_folio, 150),
}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--recipes", nargs="*", default=sorted(RECIPES),
                    choices=sorted(RECIPES))
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    catalog = {"schema": "fast-intro-motion.v1", "version": 3,
               "fps": FPS, "display_font": DISPLAY, "label_font": LABEL,
               "recipes": []}
    for name in args.recipes:
        build, duration = RECIPES[name]
        plan = build(duration)
        path = args.out / f"fast_intro_v3_{name}.plan.json"
        path.write_text(json.dumps(plan, indent=1), encoding="utf8")
        print(f"wrote {path} ({len(plan['layers'])} layers)")
        catalog["recipes"].append({
            "id": f"fast_intro_v3_{name}", "recipe": name,
            "duration_frames": duration, "width": W, "height": H,
            "display_font": DISPLAY, "label_font": LABEL,
            "camera_push": True, "hook_by_frame": 12,
        })
    (args.out / "fast_intro_motion.v1.json").write_text(
        json.dumps(catalog, indent=1), encoding="utf8")
    print("catalog:", args.out / "fast_intro_motion.v1.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
