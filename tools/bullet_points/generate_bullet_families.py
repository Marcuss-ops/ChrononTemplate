#!/usr/bin/env python3
"""Four bullet-list variants, one per RenderingGen phrase-motion family.

Same editorial list and canvas as the ten-variant bullet showcase, but each
clip follows one of the planner's four default families:

  classic_apple              slow fade + rise, warm paper accent
  modern_apple               short slide + scale, cool blue, sans
  text_3d_v1                 perspective yaw entrance, violet
  documentary_highlighting_v1 marker band sweep, ochre

The motion ids in showcase.json are the real planner ids; the tracks below are
the render-plan translation of their visible grammar. Output:
`out/bullet_points_families_v1/plans/*.plan.json` + `showcase.json`.
"""
from __future__ import annotations

import copy
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "out" / "bullet_points_families_v1" / "plans"

W, H, FPS, FRAMES = 1920, 1080, 30, 180
BG = [0.043, 0.051, 0.063, 1.0]
INK = "#F6F2E9"
BODY = "#DAD5CA"
MUTED = "#8C8880"
FOOTER = "#5F5C57"

KICKER = "P U N T I   C H I A V E"
TITLE = "Cosa resta agli atti"
POINTS = [
    "Il luogo e la data fissano la scena",
    "Le prove tecniche guidano l'indagine",
    "Ogni ipotesi va verificata alle fonti",
]

VARIANTS = [
    dict(
        slug="01_classic_apple",
        label="CLASSIC APPLE",
        family="classic_apple",
        motion_id="apple_phrase_v2",
        description="Fade lento e rise breve, serif caldo, titolo nitido",
        title_font="PlayfairDisplay-Bold.ttf",
        body_font="Inter-Regular.ttf",
        accent="#E7D7BE",
        glow=dict(enabled=False, opacity=0.0, blur=0),
        title_rise=16,
        title_duration=34,
        body_rise=26,
        body_duration=30,
        stagger=24,
    ),
    dict(
        slug="02_modern_apple",
        label="MODERN APPLE",
        family="modern_apple",
        motion_id="apple_line_cascade",
        description="Slide-up corto con scale settle, sans, accento freddo",
        title_font="Inter-Black.ttf",
        body_font="Inter-Medium.ttf",
        accent="#8AB4FF",
        glow=dict(enabled=False, opacity=0.0, blur=0),
        title_rise=22,
        title_duration=24,
        body_rise=44,
        body_duration=18,
        stagger=10,
    ),
    dict(
        slug="03_text_3d",
        label="TEXT 3D",
        family="text_3d_v1",
        motion_id="text_3d_camera_push",
        description="Push 2.5D con scala e rise, viola, profondità leggera",
        title_font="PlayfairDisplay-Black.ttf",
        body_font="Inter-Light.ttf",
        accent="#B9A7FF",
        glow=dict(enabled=False, opacity=0.0, blur=0),
        title_rise=18,
        title_duration=32,
        body_rise=16,
        body_duration=22,
        stagger=18,
    ),
    dict(
        slug="04_documentary_highlight",
        label="DOCUMENTARY HIGHLIGHT",
        family="documentary_highlighting_v1",
        motion_id="doc_01_yellow_marker_sweep",
        description="Banda marker che spazza da sinistra, ocra documentario",
        title_font="PlayfairDisplay.ttf",
        body_font="Inter-Medium.ttf",
        accent="#FFD98A",
        glow=dict(enabled=False, opacity=0.0, blur=0),
        title_rise=8,
        title_duration=24,
        body_rise=0,
        body_duration=14,
        stagger=20,
    ),
]


def kf(pairs):
    return [{"frame": int(f), "value": v} for f, v in pairs]


def fade(start, end):
    return {"property": "opacity", "easing": "out_cubic",
            "keyframes": kf([(start, 0.0), (end, 1.0), (FRAMES - 1, 1.0)])}


def hex_rgba(value: str, alpha: float = 1.0) -> list[float]:
    v = value.lstrip("#")
    return [round(int(v[i:i + 2], 16) / 255.0, 4) for i in (0, 2, 4)] + [alpha]


def text_layer(lid, text, x, y, w, h, font, size, fill, start=0,
               tracks=None, shadow=None):
    layer = {
        "id": lid,
        "type": "text",
        "text": text,
        "size": [w, h],
        "position": [x, y],
        "start_frame": start,
        "duration_frames": FRAMES - start,
        "style": {
            "font": f"assets/fonts/{font}",
            "font_size": size,
            "min_font_size": size,
            "max_font_size": size,
            "fit_mode": "shrink_only",
            "fill": fill,
        },
    }
    if shadow:
        layer["style"]["shadow"] = shadow
    if tracks:
        layer["animation"] = {"tracks": tracks}
    return layer


def color_layer(lid, color, w, h, x, y, start=0, tracks=None):
    layer = {
        "id": lid,
        "type": "color",
        "color": color,
        "size": [w, h],
        "position": [x, y],
        "start_frame": start,
        "duration_frames": FRAMES - start,
    }
    if tracks:
        layer["animation"] = {"tracks": tracks}
    return layer


def title_tracks(v):
    tracks = [fade(0, v["title_duration"])]
    if v["title_rise"]:
        tracks.append({
            "property": "position_y", "easing": "out_cubic",
            "keyframes": kf([(0, float(v["title_rise"])), (v["title_duration"], 0.0), (FRAMES - 1, 0.0)]),
        })
    if v["family"] == "modern_apple":
        tracks.append({
            "property": "scale", "easing": "out_cubic",
            "keyframes": kf([(0, 0.97), (v["title_duration"], 1.0), (FRAMES - 1, 1.0)]),
        })
    if v["family"] == "text_3d_v1":
        tracks.append({
            "property": "scale", "easing": "out_cubic",
            "keyframes": kf([(0, 1.12), (v["title_duration"], 1.0), (FRAMES - 1, 1.0)]),
        })
    return tracks


def body_tracks(v, start):
    end = start + v["body_duration"]
    tracks = [fade(start, end)]
    if v["body_rise"]:
        tracks.append({
            "property": "position_y", "easing": "out_cubic",
            "keyframes": kf([(start, float(v["body_rise"])), (end, 0.0), (FRAMES - 1, 0.0)]),
        })
    if v["family"] == "modern_apple":
        tracks.append({
            "property": "scale", "easing": "out_cubic",
            "keyframes": kf([(start, 0.96), (end, 1.0), (FRAMES - 1, 1.0)]),
        })
    if v["family"] == "text_3d_v1":
        tracks.append({
            "property": "scale", "easing": "out_cubic",
            "keyframes": kf([(start, 1.08), (end, 1.0), (FRAMES - 1, 1.0)]),
        })
    return tracks


def build(v):
    accent_rgba = hex_rgba(v["accent"])
    layers = [
        color_layer("bg", BG, W, H, 0, 0),
        color_layer("top_rule", accent_rgba, 1200, 1, 0, -360, 0, [
            {"property": "scale_x", "easing": "out_cubic",
             "keyframes": kf([(0, 0.001), (42, 1.0), (FRAMES - 1, 1.0)])},
            {"property": "opacity", "easing": "linear",
             "keyframes": kf([(0, 0.0), (8, 0.65), (FRAMES - 1, 0.65)])},
        ]),
        text_layer("kicker", KICKER, 960, 255, 900, 30,
                   "Inter-SemiBold.ttf", 20, v["accent"], 0, [fade(0, 20)]),
    ]

    title_tracks_value = title_tracks(v)
    if v["glow"]["enabled"]:
        glow = {"color": v["accent"], "opacity": v["glow"]["opacity"],
                "blur": v["glow"]["blur"], "offset": [0, 0]}
        layers.append(text_layer(
            "title_glow", TITLE, 960, 355, 1500, 150, v["title_font"], 96,
            v["accent"], 0, copy.deepcopy(title_tracks_value), shadow=glow))
    layers.append(text_layer(
        "title", TITLE, 960, 355, 1500, 150, v["title_font"], 96, INK, 0,
        title_tracks_value))

    layers += [
        color_layer("title_rule", accent_rgba, 190, 3, 0, -112, 0, [
            {"property": "scale_x", "easing": "out_cubic",
             "keyframes": kf([(8, 0.001), (40, 1.0), (FRAMES - 1, 1.0)])},
            {"property": "opacity", "easing": "linear",
             "keyframes": kf([(0, 0.0), (8, 1.0), (FRAMES - 1, 1.0)])},
        ]),
        color_layer("progress", accent_rgba, 1600, 3, 0, 445, 0, [
            {"property": "scale_x", "easing": "linear",
             "keyframes": kf([(0, 0.001), (170, 1.0), (FRAMES - 1, 1.0)])},
        ]),
        text_layer("badge", f"{int(v['slug'][:2]):02d} / 04   ·   {v['label']}",
                   1630, 255, 500, 24, "Inter-Medium.ttf", 13, MUTED, 6, [fade(6, 24)]),
        text_layer("footer", "CHRONON TEMPLATE  ·  BULLET FAMILIES",
                   250, 1010, 560, 20, "Inter-Regular.ttf", 12, FOOTER),
    ]

    for i, point in enumerate(POINTS):
        start = 34 + i * v["stagger"]
        y = 500 + i * 150
        if v["family"] == "documentary_highlighting_v1":
            band_w = min(1280, max(560, int(len(point) * 22.0 + 36)))
            band_start = start + 2
            layers.append(color_layer(
                f"bullet_{i}_marker", hex_rgba(v["accent"], 0.24), band_w, 50,
                0, y - 540 + 4, 0, [
                    {"property": "scale_x", "easing": "out_expo",
                     "keyframes": kf([(band_start, 0.001), (band_start + 20, 1.0), (FRAMES - 1, 1.0)])},
                    {"property": "position_x", "easing": "out_expo",
                     "keyframes": kf([(band_start, -band_w / 2), (band_start + 20, 0.0), (FRAMES - 1, 0.0)])},
                    {"property": "opacity", "easing": "linear",
                     "keyframes": kf([(band_start, 0.0), (band_start + 2, 1.0), (FRAMES - 1, 1.0)])},
                ]))
        text = f"—  {point}"
        tracks = body_tracks(v, start)
        layers.append(text_layer(
            f"bullet_{i}", text, 960, y, 1400, 60, v["body_font"], 40, BODY,
            0, tracks))

    return {
        "schema": "chronon.render-plan.v3",
        "version": 3,
        "job_id": f"bullet_families_{v['slug']}",
        "canvas": {"width": W, "height": H, "fps_num": FPS, "fps_den": 1,
                   "duration_frames": FRAMES},
        "layers": layers,
        "output": {"path": f"{v['slug']}.mp4", "format": "mp4", "codec": "h264"},
    }


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    catalog = {
        "schema": "chronontemplate.bullet-families.v1",
        "canvas": {"width": W, "height": H, "fps": FPS, "frames": FRAMES},
        "content": {"kicker": KICKER, "title": TITLE, "points": POINTS},
        "variants": [],
    }
    for index, v in enumerate(VARIANTS, start=1):
        plan = build(v)
        (OUT / f"{v['slug']}.plan.json").write_text(
            json.dumps(plan, indent=2, ensure_ascii=False) + "\n")
        catalog["variants"].append({
            "index": index,
            "slug": v["slug"],
            "label": v["label"],
            "family": v["family"],
            "motion_id": v["motion_id"],
            "description": v["description"],
            "reveal": v["family"],
            "title_font": v["title_font"],
            "body_font": v["body_font"],
            "accent": v["accent"],
            "glow": {"shadow_color": v["accent"], "enabled": v["glow"]["enabled"],
                     "opacity": v["glow"]["opacity"], "blur": v["glow"]["blur"]},
            "plan": f"plans/{v['slug']}.plan.json",
            "mp4": f"{v['slug']}.mp4",
        })
        print(f"{v['slug']}: {len(plan['layers'])} layers, {v['family']} / {v['motion_id']}")
    (OUT / "showcase.json").write_text(json.dumps(catalog, indent=2) + "\n")
    print(f"wrote {OUT / 'showcase.json'}")


if __name__ == "__main__":
    main()
