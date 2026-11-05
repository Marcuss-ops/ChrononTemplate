#!/usr/bin/env python3
"""Ten bullet-point animation variants authored inside ChrononTemplate.

One editorial list (kicker, title, three points) is rendered ten times. Each
variant changes only the treatment under test: the reveal, the display and body
face, the soft accent glow and the accent colour. The copy stays identical so
two clips can be compared frame by frame.

The glow is a blurred accent copy of the text drawn behind the white text
(duplicate layer, same animation), so the glyph core stays warm white while the
halo carries the accent. Text `style.glow` is deliberately not used: on the
Vulkan lane a glowing text layer is dropped from the frame. Note that a shadow
on the top text layer is composited over the fill, tinting the glyphs; hence the
glow copy.

Outputs `out/bullet_points_showcase_v1/plans/*.plan.json` and `showcase.json`.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "out" / "bullet_points_showcase_v1" / "plans"

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
    dict(slug="01_cool_slide", label="SLIDE LEFT", reveal="slide_left",
         title_font="PlayfairDisplay-Bold.ttf", body_font="Inter-SemiBold.ttf",
         accent="#67E8F9", glow_opacity=0.85, glow_blur=26),
    dict(slug="02_amber_slide_right", label="SLIDE RIGHT", reveal="slide_right",
         title_font="PlayfairDisplay.ttf", body_font="Inter-Medium.ttf",
         accent="#F6B26B", glow_opacity=0.80, glow_blur=24),
    dict(slug="03_editorial_rise", label="RISE FADE", reveal="rise_fade",
         title_font="Oswald-Bold.ttf", body_font="Inter-Regular.ttf",
         accent="#E7D7BE", glow_opacity=0.55, glow_blur=18),
    dict(slug="04_signal_drop", label="DROP BOUNCE", reveal="drop_bounce",
         title_font="Anton-Regular.ttf", body_font="Oswald-Medium.ttf",
         accent="#FF6FB5", glow_opacity=0.90, glow_blur=30),
    dict(slug="05_lime_pop", label="SCALE POP", reveal="scale_pop",
         title_font="AbrilFatface-Regular.ttf", body_font="Inter-Bold.ttf",
         accent="#C8F26B", glow_opacity=0.85, glow_blur=26),
    dict(slug="06_teal_depth", label="DEPTH PUSH", reveal="depth_push",
         title_font="PlayfairDisplay-Black.ttf", body_font="Inter-Light.ttf",
         accent="#5EEAD4", glow_opacity=0.78, glow_blur=32),
    dict(slug="07_violet_fade", label="FADE IN", reveal="fade_in",
         title_font="PlayfairDisplay-Italic.ttf", body_font="Inter-Regular.ttf",
         accent="#B9A7FF", glow_opacity=0.70, glow_blur=20),
    dict(slug="08_gold_soft_rise", label="SOFT RISE", reveal="soft_rise",
         title_font="PlayfairDisplay-BoldItalic.ttf", body_font="Inter-Medium.ttf",
         accent="#FFD98A", glow_opacity=0.95, glow_blur=34),
    dict(slug="09_mixed_cascade", label="MIXED CASCADE", reveal="mixed",
         title_font="Inter-Black.ttf", body_font="Inter-SemiBold.ttf",
         accent="#8AB4FF", glow_opacity=0.75, glow_blur=22),
    dict(slug="10_mixed_cascade_warm", label="MIXED CASCADE WARM", reveal="mixed_warm",
         title_font="PlayfairDisplay-ExtraBold.ttf", body_font="Inter-Regular.ttf",
         accent="#FF8F6B", glow_opacity=0.88, glow_blur=28),
]


def kf(pairs):
    return [{"frame": int(f), "value": v} for f, v in pairs]


def text_layer(lid, text, x, y, w, h, font, size, fill, shadow=None,
               start=0, tracks=None):
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


def hex_rgba(value: str) -> list[float]:
    v = value.lstrip("#")
    return [round(int(v[i:i + 2], 16) / 255.0, 4) for i in (0, 2, 4)] + [1.0]


def fade(start, end):
    return {"property": "opacity", "easing": "out_cubic",
            "keyframes": kf([(start, 0.0), (end, 1.0), (FRAMES - 1, 1.0)])}


def reveal_tracks(kind, start, duration=24):
    end = start + duration
    tracks = [fade(start, end)]
    if kind == "slide_left":
        tracks.append({"property": "position_x", "easing": "out_cubic",
                       "keyframes": kf([(start, -160.0), (end, 0.0), (FRAMES - 1, 0.0)])})
    elif kind == "slide_right":
        tracks.append({"property": "position_x", "easing": "out_cubic",
                       "keyframes": kf([(start, 160.0), (end, 0.0), (FRAMES - 1, 0.0)])})
    elif kind == "rise_fade":
        tracks.append({"property": "position_y", "easing": "out_cubic",
                       "keyframes": kf([(start, 70.0), (end, 0.0), (FRAMES - 1, 0.0)])})
    elif kind == "drop_bounce":
        tracks = [
            {"property": "opacity", "easing": "out_cubic",
             "keyframes": kf([(start, 0.0), (start + 10, 1.0), (FRAMES - 1, 1.0)])},
            {"property": "position_y", "easing": "linear",
             "keyframes": kf([(start, -90.0), (start + 16, 0.0), (start + 21, 12.0),
                              (start + 28, 0.0), (FRAMES - 1, 0.0)])},
        ]
    elif kind == "scale_pop":
        tracks.append({"property": "scale", "easing": "out_cubic",
                       "keyframes": kf([(start, 0.6), (start + 18, 1.05),
                                        (start + 27, 1.0), (FRAMES - 1, 1.0)])})
    elif kind == "depth_push":
        tracks.append({"property": "scale", "easing": "out_cubic",
                       "keyframes": kf([(start, 1.35), (end, 1.0), (FRAMES - 1, 1.0)])})
    elif kind == "soft_rise":
        tracks = [fade(start, start + 32),
                  {"property": "position_y", "easing": "out_cubic",
                   "keyframes": kf([(start, 24.0), (start + 32, 0.0), (FRAMES - 1, 0.0)])}]
    elif kind == "pulse":
        tracks = [fade(start, start + 12),
                  {"property": "scale", "easing": "out_cubic",
                   "keyframes": kf([(start, 1.0), (start + 12, 1.04), (start + 24, 1.0),
                                    (FRAMES - 1, 1.0)])}]
    return tracks


def build(variant):
    accent = variant["accent"]
    accent_rgba = hex_rgba(accent)
    glow = {"color": accent, "opacity": variant["glow_opacity"],
            "blur": variant["glow_blur"], "offset": [0, 0]}
    body_glow = {"color": accent, "opacity": round(variant["glow_opacity"] * 0.38, 3),
                 "blur": max(10, variant["glow_blur"] // 2), "offset": [0, 0]}

    # `color` layers take centre-relative positions in the certified plans
    # (0,0 = canvas centre), while text layers take absolute canvas pixels.
    layers = [
        color_layer("bg", BG, W, H, 0, 0),
        color_layer("top_rule", accent_rgba, 1200, 1, 0, -360, 0, [
            {"property": "scale_x", "easing": "out_cubic",
             "keyframes": kf([(0, 0.001), (42, 1.0), (FRAMES - 1, 1.0)])},
            {"property": "opacity", "easing": "linear",
             "keyframes": kf([(0, 0.0), (8, 0.65), (FRAMES - 1, 0.65)])},
        ]),
        text_layer("kicker", KICKER, 960, 255, 900, 30, "Inter-SemiBold.ttf",
                   20, accent, None, 0, [fade(0, 20)]),
        text_layer("title_glow", TITLE, 960, 355, 1500, 150,
                   variant["title_font"], 96, accent, glow, 0, [
                       fade(0, 22),
                       {"property": "position_y", "easing": "out_cubic",
                        "keyframes": kf([(0, 16.0), (22, 0.0), (FRAMES - 1, 0.0)])},
                   ]),
        text_layer("title", TITLE, 960, 355, 1500, 150,
                   variant["title_font"], 96, INK, None, 0, [
                       fade(0, 22),
                       {"property": "position_y", "easing": "out_cubic",
                        "keyframes": kf([(0, 16.0), (22, 0.0), (FRAMES - 1, 0.0)])},
                   ]),
        color_layer("title_rule", accent_rgba, 190, 3, 0, -112, 0, [
            {"property": "scale_x", "easing": "out_cubic",
             "keyframes": kf([(12, 0.001), (48, 1.0), (FRAMES - 1, 1.0)])},
            {"property": "opacity", "easing": "linear",
             "keyframes": kf([(0, 0.0), (12, 1.0), (FRAMES - 1, 1.0)])},
        ]),
        color_layer("progress", accent_rgba, 1600, 3, 0, 445, 0, [
            {"property": "scale_x", "easing": "linear",
             "keyframes": kf([(0, 0.001), (170, 1.0), (FRAMES - 1, 1.0)])},
        ]),
        text_layer("badge", f"{int(variant['slug'][:2]):02d} / 10   ·   {variant['label']}",
                   1640, 255, 420, 24, "Inter-Medium.ttf", 13, MUTED, None, 6,
                   [fade(6, 24)]),
        text_layer("footer", "CHRONON TEMPLATE  ·  BULLET POINTS",
                   250, 1010, 520, 20, "Inter-Regular.ttf", 12, FOOTER),
    ]

    for i, point in enumerate(POINTS):
        start = 34 + i * 14
        kind = variant["reveal"]
        if kind == "mixed":
            kind = ["slide_right", "rise_fade", "scale_pop"][i]
        elif kind == "mixed_warm":
            kind = ["slide_left", "depth_push", "soft_rise"][i]
        elif kind == "focus_sweep":
            start = 22
            kind = "pulse"
        text = f"\u2014  {point}"
        tracks = reveal_tracks(kind, start)
        layers.append(text_layer(
            f"bullet_{i}_glow", text, 960, 500 + i * 150, 1400, 60,
            variant["body_font"], 40, accent, body_glow, start, tracks))
        layers.append(text_layer(
            f"bullet_{i}", text, 960, 500 + i * 150, 1400, 60,
            variant["body_font"], 40, BODY, None, start, tracks))

    return {
        "schema": "chronon.render-plan.v3",
        "version": 3,
        "job_id": f"bullet_points_{variant['slug']}",
        "canvas": {"width": W, "height": H, "fps_num": FPS, "fps_den": 1,
                   "duration_frames": FRAMES},
        "layers": layers,
        "output": {"path": f"{variant['slug']}.mp4", "format": "mp4", "codec": "h264"},
    }


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    catalog = {"schema": "chronontemplate.bullet-points-showcase.v1",
               "canvas": {"width": W, "height": H, "fps": FPS, "frames": FRAMES},
               "content": {"kicker": KICKER, "title": TITLE, "points": POINTS},
               "variants": []}
    for index, variant in enumerate(VARIANTS, start=1):
        plan = build(variant)
        path = OUT / f"{variant['slug']}.plan.json"
        path.write_text(json.dumps(plan, indent=2, ensure_ascii=False) + "\n")
        catalog["variants"].append({
            "index": index,
            "slug": variant["slug"],
            "label": variant["label"],
            "reveal": variant["reveal"],
            "title_font": variant["title_font"],
            "body_font": variant["body_font"],
            "accent": variant["accent"],
            "glow": {"shadow_color": variant["accent"],
                     "opacity": variant["glow_opacity"],
                     "blur": variant["glow_blur"]},
            "plan": f"plans/{variant['slug']}.plan.json",
            "mp4": f"{variant['slug']}.mp4",
        })
        print(f"{path}  layers={len(plan['layers'])}  reveal={variant['reveal']}")
    (OUT / "showcase.json").write_text(json.dumps(catalog, indent=2) + "\n")
    print(f"wrote {OUT / 'showcase.json'}")


if __name__ == "__main__":
    main()
