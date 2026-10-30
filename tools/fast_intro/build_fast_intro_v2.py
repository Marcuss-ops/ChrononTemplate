#!/usr/bin/env python3
"""Fast Intro v2 — single-source unified builder.

Owns all four v2 recipes (opening_plate, punch_stat, whip_match, chapter_card)
and emits canonical chronon.render-plan.v3 JSON in the exact dialect the
Chronon3d CLI validates (see golden_plans/entity_presentation_v1 for the
reference shapes):

- text:  {text, size, position, style:{font, font_size, fill, fit_mode,
           shadow?, glow?}}, transform tracks are OFFSETS (position_x/y) or
           absolute scalars (scale) / absolute (opacity)
- shape solid: shape:{type, fill:[r,g,b,a]} / rounded_rect + radius /
               ellipse + transparent fill + stroke (no `enabled` wrappers)
- gradient: shape:{type, fill:{type, spread, center, radius,
               color_stops:[{position, color:[r,g,b,a]}]}}
- easing: linear | out_cubic | in_out_cubic | smoothstep (NOT ease_out_cubic)

    python build_fast_intro_v2.py --out out/fast_intro_v2 [--vertical]
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
TEMPLATE = HERE.parents[1]
DEFAULT_OUT = TEMPLATE / "out" / "fast_intro_v2"

W, H, FPS = 1920, 1080, 30
FONT = "ChrononTemplate/assets/fonts/Inter-Black.ttf"
COLLAGE = "ChrononTemplate/assets/images/retro_collage.png"

MIN_SCALE = 0.02


def key(frame: int, value):
    return {"frame": frame, "value": value}


def track(prop: str, kfs, easing="out_cubic"):
    return {"property": prop, "easing": easing, "keyframes": kfs}


def rgba(hex_color: str, alpha: float = 1.0):
    h = hex_color.lstrip("#")
    return [int(h[0:2], 16) / 255.0, int(h[2:4], 16) / 255.0,
            int(h[4:6], 16) / 255.0, alpha]


def text_layer(lid, text, font_size, fill, pos, start, dur,
               box=None, shadow=None, glow=None, tracks=None):
    style = {"font": FONT, "font_size": font_size, "fill": fill,
             "fit_mode": "shrink_only", "min_font_size": font_size,
             "max_font_size": font_size}
    if shadow is not None:
        style["shadow"] = shadow
    if glow is not None:
        style["glow"] = glow
    layer = {"id": lid, "type": "text", "text": text,
             "size": box or [min(1700, len(text) * font_size * 0.62 + 80),
                             font_size * 2.0],
             "position": list(pos), "start_frame": start,
             "duration_frames": dur, "style": style}
    if tracks:
        layer["animation"] = {"tracks": tracks}
    return layer


def shape_layer(lid, shape, pos, size, start, dur, tracks=None):
    layer = {"id": lid, "type": "shape", "shape": shape,
             "position": list(pos), "size": list(size),
             "start_frame": start, "duration_frames": dur}
    if tracks:
        layer["animation"] = {"tracks": tracks}
    return layer


def base_plan(job_id: str, duration: int, width=W, height=H):
    return {
        "schema": "chronon.render-plan.v3",
        "version": 3,
        "job_id": job_id,
        "canvas": {"width": width, "height": height, "fps_num": FPS,
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


def radial_fill(stops, center=(0.5, 0.5), radius=0.5):
    return {"type": "radial", "spread": "pad", "center": list(center),
            "radius": radius,
            "color_stops": [{"position": p, "color": rgba(c, a)}
                            for p, c, a in stops]}


SHADOW_SOFT = {"color": "#000000", "offset": [0, 6], "opacity": 0.6,
               "blur": 10.0}


def build_opening(duration=120, width=W, height=H):
    cx, cy = width / 2, height / 2
    unit = width / 1920.0
    plan = base_plan("fast_intro_v2_opening", duration, width, height)
    add_camera_push(plan, 160.0, duration)
    L = plan["layers"]
    L.append({"id": "opening_ground", "type": "color",
              "color": rgba("#0B0B0E"), "position": [0, 0],
              "size": [width, height], "start_frame": 0,
              "duration_frames": duration})
    L.append(shape_layer(
        "opening_aura",
        {"type": "ellipse", "fill": radial_fill(
            [(0.0, "#FF4D2E", 0.28), (1.0, "#0B0B0E", 0.0)])},
        [cx, cy], [width * 1.1, height * 1.1], 0, duration,
        [track("opacity", [key(0, 0.0), key(20, 1.0)])]))
    L.append(text_layer(
        "opening_kicker", "CHRONON TEMPLATE", 30, "#FF4D2E",
        [cx, cy - 230 * unit], 0, duration, box=[900, 60],
        tracks=[track("opacity", [key(0, 0.0), key(8, 1.0)]),
                track("position_y", [key(0, 14), key(10, 0)])]))
    L.append(text_layer(
        "opening_title", "THE STORY SO FAR", 104 if width >= height else 76,
        "#F5F2EA", [cx, cy - 70 * unit], 0, duration, box=[1700, 160],
        shadow=SHADOW_SOFT,
        tracks=[track("opacity", [key(0, 0.0), key(10, 1.0)]),
                track("scale", [key(0, 0.92), key(12, 1.0)])]))
    L.append(text_layer(
        "opening_subtitle", "A short line that sets up the story.", 34,
        "#B9B4A8", [cx, cy + 80 * unit], 10, duration - 10, box=[1400, 60],
        tracks=[track("opacity", [key(10, 0.0), key(22, 1.0)])]))
    L.append(shape_layer(
        "opening_rail", {"type": "rect", "fill": rgba("#FF4D2E")},
        [cx, cy + 220 * unit], [width * 0.62, 4], 6, duration - 6,
        [track("scale_x", [key(6, MIN_SCALE), key(20, 1.0)], "linear")]))
    L.append(shape_layer(
        "opening_marker", {"type": "ellipse", "fill": rgba("#FF4D2E")},
        [cx - width * 0.31, cy + 220 * unit], [16, 16], 6, duration - 6,
        [track("opacity", [key(6, 0.0), key(14, 1.0)]),
         track("position_x", [key(6, width * 0.62), key(44, 0.0)],
               "in_out_cubic")]))
    topics = ["CONTEXT", "EVIDENCE", "WHAT CHANGED"]
    spacing = width * 0.20
    for i, topic in enumerate(topics):
        inn = 28 + i * 6
        x = cx + (i - 1.0) * spacing
        pill_w = len(topic) * 13 + 52
        L.append(shape_layer(
            f"opening_pill_{i}",
            {"type": "rounded_rect", "radius": 22,
             "fill": [0.10, 0.10, 0.12, 0.95],
             "stroke": {"color": "#FF4D2E", "width": 1.5}},
            [x, cy + 150 * unit], [pill_w, 44], inn, duration - inn,
            [track("opacity", [key(inn, 0.0), key(inn + 10, 0.95)])]))
        L.append(text_layer(
            f"opening_topic_{i}", topic, 22, "#E8E2D4", [x, cy + 150 * unit],
            inn, duration - inn, box=[pill_w, 40],
            tracks=[track("opacity", [key(inn, 0.0), key(inn + 10, 1.0)]),
                    track("position_y", [key(inn, 18), key(inn + 10, 0)])]))
    return plan


def build_punch(duration=150, width=W, height=H):
    cx, cy = width / 2, height / 2
    plan = base_plan("fast_intro_v2_punch", duration, width, height)
    add_camera_push(plan, 160.0, duration)
    L = plan["layers"]
    L.append({"id": "punch_ground", "type": "color",
              "color": rgba("#0E0202"), "position": [0, 0],
              "size": [width, height], "start_frame": 0,
              "duration_frames": duration})
    glow_size = max(width, height) * 1.2
    L.append(shape_layer(
        "punch_radial_glow",
        {"type": "ellipse", "fill": radial_fill([
            (0.00, "#FFD24A", 1.0), (0.26, "#EE7A10", 1.0),
            (0.52, "#C24A08", 1.0), (0.85, "#5E0D04", 1.0),
            (1.00, "#0E0202", 1.0)])},
        [cx, cy - 20], [glow_size, glow_size], 0, duration))
    for r in range(5):
        frac = 0.30 + r * 0.20
        L.append(shape_layer(
            f"punch_ring_{r}",
            {"type": "ellipse", "fill": [0, 0, 0, 0],
             "stroke": {"color": "#EE941F", "width": 10 - r * 1.2}},
            [cx, cy - 20], [glow_size * frac, glow_size * frac], 0, duration,
            [track("opacity", [key(0, 0.0), key(20, 0.20 - r * 0.02)]),
             track("scale", [key(0, 1.0), key(duration - 1, 1.12)],
                   "linear")]))
    era_end = min(46, duration - 1)
    L.append(text_layer(
        "punch_era", "1990s", 320, "#F5F1EA", [cx, cy], 0, era_end,
        box=[1200, 420],
        shadow={"color": "#1C0404", "offset": [8, 14], "opacity": 0.88,
                "blur": 12.0},
        tracks=[track("scale", [key(0, 1.0), key(min(38, era_end), 1.14),
                                key(era_end, 1.32)], "linear"),
                track("opacity", [key(0, 1.0), key(min(38, era_end), 1.0),
                                  key(era_end, 0.0)], "linear")]))
    stat_out = min(121, duration - 1)
    L.append(text_layer(
        "punch_stat", "37.7 M", 340, "#F5F1EA", [cx, cy], 38,
        max(1, stat_out - 38), box=[1300, 440],
        shadow={"color": "#1C0404", "offset": [12, 16], "opacity": 0.90,
                "blur": 14.0},
        tracks=[track("scale", [key(38, 3.4), key(48, 2.75), key(60, 2.2),
                                key(72, 1.5), key(82, 1.0),
                                key(stat_out, 0.94)]),
                track("position_x", [key(38, 320), key(82, 0)]),
                track("position_y", [key(38, 140), key(82, 0)]),
                track("opacity", [key(38, 0.0), key(39, 1.0),
                                  key(stat_out, 0.0)], "linear")]))
    L.append({"id": "punch_collage", "type": "image", "asset": COLLAGE,
              "fit": "contain", "position": [0, -15],
              "size": [width * 0.88, height * 0.96],
              "start_frame": 88, "duration_frames": max(1, duration - 88),
              "animation": {"tracks": [
                  track("scale", [key(88, 3.2), key(99, 2.4), key(120, 1.42),
                                 key(min(140, duration - 1), 1.04),
                                 key(duration - 1, 1.0)]),
                  track("opacity", [key(88, 0.0), key(90, 1.0)])]}})
    return plan


def build_whip(duration=180, width=W, height=H, n_plates=8):
    from build_match_cut_plan import NEWS, WEB
    cx, cy = width / 2, height / 2
    plan = base_plan("fast_intro_v2_whip", duration, width, height)
    add_camera_push(plan, 120.0, duration)
    L = plan["layers"]
    L.append({"id": "whip_ground", "type": "color", "color": [0, 0, 0, 1],
              "position": [0, 0], "size": [width, height],
              "start_frame": 0, "duration_frames": duration})
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
            "id": f"whip_shot_{i}", "type": "image",
            "asset": f"ChrononTemplate/assets/fast_intro_match_cut/{plate}.png",
            "fit": "cover", "position": [0, 0], "size": [width, height],
            "start_frame": s, "duration_frames": max(1, e - s),
            "animation": {"tracks": [
                track("position_x", [
                    key(s, direction * 1200),
                    key(min(s + 6, e - 1), 0)]),
                track("opacity", [
                    key(s, 0.0), key(min(s + 3, e - 1), 1.0)], "linear")]}})
        cursor += length
        if cursor >= duration:
            break
    L.append(shape_layer(
        "whip_vignette",
        {"type": "ellipse", "fill": radial_fill(
            [(0.0, "#000000", 0.0), (0.7, "#000000", 0.0),
             (1.0, "#000000", 0.55)])},
        [cx, cy], [width * 1.2, height * 1.2], 0, duration))
    return plan


def build_chapter(duration=150, width=W, height=H):
    cx, cy = width / 2, height / 2
    plan = base_plan("fast_intro_v2_chapter", duration, width, height)
    add_camera_push(plan, 200.0, duration)
    L = plan["layers"]
    L.append({"id": "chapter_ground", "type": "color",
              "color": rgba("#060608"), "position": [0, 0],
              "size": [width, height], "start_frame": 0,
              "duration_frames": duration})
    L.append(shape_layer(
        "chapter_band", {"type": "rect", "fill": rgba("#C40A1F")},
        [cx, cy - 20], [width, 110], 0, duration,
        [track("scale_x", [key(0, MIN_SCALE), key(18, 1.0)], "linear")]))
    L.append(text_layer(
        "chapter_label", "CHAPTER 1", 44, "#FF8A94", [cx, cy - 220], 4,
        duration - 4, box=[600, 70],
        tracks=[track("opacity", [key(4, 0.0), key(14, 1.0)])]))
    L.append(text_layer(
        "chapter_title", "THE HITMAN HIDDEN IN A FAMILY PHOTO",
        64 if width >= height else 52, "#FFF8F5", [cx, cy - 20], 8,
        duration - 8, box=[1700, 120],
        glow={"color": "#FF2638", "radius": 18.0, "intensity": 0.5},
        tracks=[track("opacity", [key(8, 0.0), key(20, 1.0)]),
                track("scale", [key(8, 0.94), key(26, 1.0)], "linear")]))
    L.append(text_layer(
        "chapter_subtitle", "A parametric chapter card, no hard-coded copy.",
        30, "#C9C2B4", [cx, cy + 180], 16, duration - 16, box=[1400, 60],
        tracks=[track("opacity", [key(16, 0.0), key(28, 1.0)])]))
    for p in range(12):
        px = cx - width * 0.45 + ((p * 173) % 100) / 100.0 * width * 0.9
        py = cy + ((p * 97) % 100) / 100.0 * 300.0 - 150.0
        size = 4 + (p % 3) * 3
        L.append(shape_layer(
            f"chapter_dust_{p}",
            {"type": "ellipse", "fill": [0.91, 0.725, 0.541, 0.5]},
            [px, py], [size, size], 0, duration,
            [track("opacity", [key(0, 0.0), key(20, 0.5)], "linear"),
             track("position_x", [key(0, 0), key(duration - 1, 30)], "linear"),
             track("position_y", [key(0, 0), key(duration - 1, -60)],
                   "linear")]))
    return plan


RECIPES = {
    "opening": (build_opening, 120),
    "punch": (build_punch, 150),
    "whip": (build_whip, 180),
    "chapter": (build_chapter, 150),
}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--vertical", action="store_true",
                    help="also emit 1080x1920 variants")
    ap.add_argument("--recipes", nargs="*", default=sorted(RECIPES),
                    choices=sorted(RECIPES))
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    catalog = {"schema": "fast-intro-motion.v1", "version": 1,
               "fps": FPS, "font_default": FONT, "recipes": []}
    for name in args.recipes:
        build, duration = RECIPES[name]
        plan = build(duration)
        path = args.out / f"fast_intro_v2_{name}.plan.json"
        path.write_text(json.dumps(plan, indent=1), encoding="utf8")
        print(f"wrote {path} ({len(plan['layers'])} layers)")
        catalog["recipes"].append({
            "id": f"fast_intro_v2_{name}", "recipe": name,
            "duration_frames": duration, "width": W, "height": H,
            "font": FONT, "camera_push": True,
            "hook_by_frame": 12, "max_scale": 3.4,
        })
        if args.vertical:
            vplan = build(duration, width=1080, height=1920)
            vplan["job_id"] = f"fast_intro_v2_{name}_vertical"
            vpath = args.out / f"fast_intro_v2_{name}_vertical.plan.json"
            vpath.write_text(json.dumps(vplan, indent=1), encoding="utf8")
            print(f"wrote {vpath}")
    (args.out / "fast_intro_motion.v1.json").write_text(
        json.dumps(catalog, indent=1), encoding="utf8")
    print("catalog:", args.out / "fast_intro_motion.v1.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
