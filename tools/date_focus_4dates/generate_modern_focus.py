#!/usr/bin/env python3
"""Modern four-date focus timeline (chronon.render-plan.v3).

Same four milestones and same spatial logic as the classic timeline, but a
younger visual language: near-black canvas, electric cyan/lime/magenta,
Anton display dates, Inter ExtraBold labels, a thin grid, neon pin and a real
per-text glow (style.glow). One big date sits in the centre; the rail slides
one step at a time and the old/new dates sweep out/in.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]  # ChrononTemplate
OUT = ROOT / "golden_plans" / "date_focus_4dates_modern"
TOTAL = 320  # 10.67 s at 30 fps
STEP = 80
SPACING = 380.0

ICE = "#F2FFFF"
MUTED = "#7891B5"
FAINT = "#40536E"
CYAN = "#3DF4FF"
LIME = "#D8FF3E"
MAGENTA = "#FF3DBB"
BG = [0.018, 0.024, 0.045, 1.0]
RAIL = [0.12, 0.18, 0.30, 1.0]
GRID = [0.10, 0.16, 0.28, 0.55]
CYAN_RGBA = [0.24, 0.96, 1.0, 1.0]
LIME_RGBA = [0.85, 1.0, 0.24, 1.0]
MAGENTA_RGBA = [1.0, 0.24, 0.73, 1.0]
# Four milestones selected from date_timeline::technologyDateSample()
# (ChrononTemplate/include/chronontemplate/date_timeline/DateTimelinePack.hpp).
DATES = [("1948", "BIRTH"), ("1969", "CHANGE"),
         ("1998", "LAUNCH"), ("2026", "NOW")]


def kf(pairs):
    return [{"frame": f, "value": v} for f, v in pairs]


def text_layer(lid, text, x, y, w, h, font, size, fill, start=0, tracks=None,
               min_size=None, max_size=None, glow=None, shadow=None,
               opacity=None):
    style = {
        "font": font,
        "font_size": size,
        "min_font_size": min_size if min_size is not None else size,
        "max_font_size": max_size if max_size is not None else size,
        "fit_mode": "shrink_only",
        "fill": fill,
    }
    if glow is not None:
        style["glow"] = glow
    if shadow is not None:
        style["shadow"] = shadow
    layer = {
        "id": lid,
        "type": "text",
        "text": text,
        "size": [w, h],
        "position": [x, y],
        "start_frame": start,
        "duration_frames": TOTAL - start,
        "style": style,
    }
    if tracks:
        layer["animation"] = {"tracks": tracks}
    if opacity is not None:
        layer["opacity"] = opacity
    return layer


def color_layer(lid, color, w, h, ox, oy, start=0, tracks=None):
    layer = {
        "id": lid,
        "type": "color",
        "color": color,
        "size": [w, h],
        "position": [ox, oy],
        "start_frame": start,
        "duration_frames": TOTAL - start,
    }
    if tracks:
        layer["animation"] = {"tracks": tracks}
    return layer


def fade(start, end, peak=1.0):
    return {"property": "opacity",
            "keyframes": kf([(start, 0.0), (end, float(peak)), (TOTAL - 1, float(peak))]),
            "easing": "out_cubic"}


def rail_shift():
    return {
        "property": "position_x",
        "keyframes": kf([
            (0, 0.0), (60, 0.0), (88, -SPACING), (140, -SPACING),
            (168, -2 * SPACING), (220, -2 * SPACING),
            (248, -3 * SPACING), (TOTAL - 1, -3 * SPACING),
        ]),
        "easing": "in_out_cubic",
    }


def sweep_pos(i):
    if i == 0:
        return [(0, 0.0), (60, 0.0), (100, -1300.0), (TOTAL - 1, -1300.0)]
    if i == 3:
        return [(0, 1300.0), (210, 1300.0), (250, 0.0), (TOTAL - 1, 0.0)]
    in_start, in_end = (50, 90) if i == 1 else (130, 170)
    out_start, out_end = (140, 180) if i == 1 else (220, 260)
    return [(0, 1300.0), (in_start, 1300.0), (in_end, 0.0),
            (out_start, 0.0), (out_end, -1300.0), (TOTAL - 1, -1300.0)]


def sweep_scale(i):
    if i == 0:
        return [(0, 1.0), (60, 1.0), (100, 0.95), (TOTAL - 1, 0.95)]
    if i == 3:
        return [(0, 0.9), (210, 0.9), (250, 1.0), (TOTAL - 1, 1.0)]
    in_start, in_end = (50, 90) if i == 1 else (130, 170)
    out_start, out_end = (140, 180) if i == 1 else (220, 260)
    return [(0, 0.9), (in_start, 0.9), (in_end, 1.0),
            (out_start, 1.0), (out_end, 0.95), (TOTAL - 1, 0.95)]


def big_date(i, date_text):
    tracks = [
        {"property": "position_x", "keyframes": kf(sweep_pos(i)), "easing": "out_cubic"},
        {"property": "scale", "keyframes": kf(sweep_scale(i)), "easing": "out_cubic"},
    ]
    # Magenta echo slightly offset: gives the date a chromatic/neon edge.
    echo = text_layer(
        f"big_date_echo_{i}", date_text, 966, 472, 1200, 340,
        "assets/fonts/Anton-Regular.ttf", 270, MAGENTA, 0, tracks,
        220, 270,
        opacity=0.22,
    )
    main = text_layer(
        f"big_date_{i}", date_text, 960, 470, 1200, 340,
        "assets/fonts/Anton-Regular.ttf", 270, ICE, 0, tracks,
        220, 270,
        shadow={"color": CYAN, "opacity": 0.85, "blur": 46, "offset": [0, 0]},
    )
    return [echo, main]


def big_label(i, label):
    return text_layer(
        f"big_label_{i}", label, 960, 680, 900, 60,
        "assets/fonts/Inter-ExtraBold.ttf", 30, LIME, 0,
        [{"property": "position_x", "keyframes": kf(sweep_pos(i)), "easing": "out_cubic"}],
        24, 30,
        shadow={"color": LIME, "opacity": 0.75, "blur": 18, "offset": [0, 0]},
    )


def reticle():
    """Four thin corner brackets, fixed around the active date."""
    c = [0.24, 0.96, 1.0, 0.55]
    arm = 80
    t = 2
    return [
        color_layer("reticle_tl_h", c, arm, t, -320, -240),
        color_layer("reticle_tl_v", c, t, arm, -360, -200),
        color_layer("reticle_tr_h", c, arm, t, 320, -240),
        color_layer("reticle_tr_v", c, t, arm, 360, -200),
        color_layer("reticle_bl_h", c, arm, t, -320, 100),
        color_layer("reticle_bl_v", c, t, arm, -360, 60),
        color_layer("reticle_br_h", c, arm, t, 320, 100),
        color_layer("reticle_br_v", c, t, arm, 360, 60),
    ]


def grid_lines():
    layers = []
    for x in (-720, -240, 240, 720):
        layers.append(color_layer(f"grid_v_{x}", GRID, 1, 1080, x, 0))
    for y in (-270, 0, 270):
        layers.append(color_layer(f"grid_h_{y}", GRID, 1920, 1, 0, y))
    return layers


def build():
    shift = rail_shift()
    layers = [color_layer("bg", BG, 1920, 1080, 0, 0)]
    layers.extend(grid_lines())
    # Rail: faint cyan underlay, dark core, moving nodes/ticks/labels.
    layers.append(color_layer("rail_glow", [0.24, 0.96, 1.0, 0.07],
                              4400, 10, 0, 280, 0, [shift]))
    layers.append(color_layer("rail", RAIL, 4400, 2, 0, 280, 0, [shift]))
    for i, (date_text, _) in enumerate(DATES):
        ox = i * SPACING
        layers.append(color_layer(f"tick_{i}", [0.18, 0.36, 0.52, 1.0],
                                  1, 26, ox, 302, 0, [shift]))
        layers.append(color_layer(f"node_{i}", [0.25, 0.42, 0.60, 1.0],
                                  14, 14, ox, 280, 0, [shift]))
        layers.append(text_layer(f"axis_{i}", date_text, 960 + ox, 900, 240, 40,
                                 "assets/fonts/Inter-SemiBold.ttf", 20, MUTED,
                                 0, [shift]))
    # Fixed active node and halo under the pin.
    layers.extend([
        color_layer("active_halo", [0.24, 0.96, 1.0, 0.08], 90, 90, 0, 280),
        color_layer("active_halo_inner", [0.24, 0.96, 1.0, 0.16], 40, 40, 0, 280),
        color_layer("active_node", CYAN_RGBA, 18, 18, 0, 280),
    ])
    # Neon pin: cyan stem, magenta head.
    layers.extend([
        color_layer("pin_stem_glow", [0.24, 0.96, 1.0, 0.12], 9, 70, 0, 245),
        color_layer("pin_stem", CYAN_RGBA, 3, 70, 0, 245),
        color_layer("pin_head_glow", [1.0, 0.24, 0.73, 0.18], 56, 56, 0, 200),
        color_layer("pin_head", MAGENTA_RGBA, 20, 20, 0, 200),
        color_layer("pin_centre", BG, 7, 7, 0, 200),
    ])
    layers.extend(reticle())
    for i, (date_text, label) in enumerate(DATES):
        layers.extend(big_date(i, date_text))
        layers.append(big_label(i, label))
    layers.extend([
        text_layer("eyebrow", "CHRONON / MODERN EDITION", 960, 96, 1200, 26,
                   "assets/fonts/Inter-SemiBold.ttf", 13, CYAN, 0, [fade(0, 18)],
                   13, 13,
                   shadow={"color": CYAN, "opacity": 0.60, "blur": 12, "offset": [0, 0]}),
        text_layer("heading", "FOUR MOMENTS", 960, 150, 1200, 76,
                   "assets/fonts/Inter-ExtraBold.ttf", 46, ICE, 0,
                   [fade(0, 18), {"property": "position_y",
                                  "keyframes": kf([(0, 10.0), (18, 0.0), (TOTAL - 1, 0.0)]),
                                  "easing": "out_cubic"}],
                   46, 46,
                   shadow={"color": CYAN, "opacity": 0.45, "blur": 22, "offset": [0, 0]}),
        text_layer("subtitle", "1948 — 2026  /  A NEW TIMELINE", 960, 202, 1200, 30,
                   "assets/fonts/Inter-Medium.ttf", 16, MUTED, 0, [fade(0, 22)]),
        text_layer("count", "04 / 04", 1740, 130, 260, 30,
                   "assets/fonts/Inter-Bold.ttf", 16, LIME, 0, None, 16, 16,
                   shadow={"color": LIME, "opacity": 0.55, "blur": 12, "offset": [0, 0]}),
        text_layer("count_caption", "MOMENTS", 1740, 160, 260, 20,
                   "assets/fonts/Inter-Medium.ttf", 10, MUTED),
        text_layer("footer", "CHRONON TEMPLATE  /  MODERN CHRONOLOGY", 300, 1015, 520, 24,
                   "assets/fonts/Inter-Medium.ttf", 11, MUTED),
    ])
    # Edge lights: cyan top, magenta bottom.
    layers.append(color_layer("top_line", [0.24, 0.96, 1.0, 0.75], 1920, 2, 0, -540))
    layers.append(color_layer("bottom_line", [1.0, 0.24, 0.73, 0.55], 1920, 2, 0, 538))
    return {
        "schema": "chronon.render-plan.v3",
        "version": 3,
        "job_id": "date_focus_4dates_modern",
        "canvas": {"width": 1920, "height": 1080, "fps_num": 30, "fps_den": 1,
                   "duration_frames": TOTAL},
        "layers": layers,
        "output": {"path": "focus_4dates_modern.mp4", "format": "mp4", "codec": "h264"},
    }


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    plan = build()
    path = OUT / "focus_4dates_modern.plan.json"
    path.write_text(json.dumps(plan, indent=2, ensure_ascii=False) + "\n")
    print(f"{path}  layers={len(plan['layers'])}  frames={TOTAL}")


if __name__ == "__main__":
    main()
