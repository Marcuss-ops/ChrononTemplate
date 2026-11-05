#!/usr/bin/env python3
"""Four-date focus timeline (chronon.render-plan.v3).

One active date at a time is huge in the centre. A long rail slides under a
fixed pin; at every step the old date leaves to the left, the new date enters
from the right, and the pin keeps pointing at the active node. The same motion
is repeated for all four dates.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]  # ChrononTemplate
OUT = ROOT / "golden_plans" / "date_focus_4dates"
TOTAL = 320  # 10.67 s at 30 fps
STEP = 80
SPACING = 380.0

INK = "#262521"
MUTED = "#77746E"
FAINT = "#A39F97"
ACCENT = "#C8553D"
BG = [0.96, 0.95, 0.93, 1.0]
RAIL = [0.72, 0.70, 0.66, 1.0]
ACCENT_RGBA = [0.784, 0.333, 0.239, 1.0]
# Four milestones selected from date_timeline::technologyDateSample()
# (ChrononTemplate/include/chronontemplate/date_timeline/DateTimelinePack.hpp).
DATES = [("1948", "BIRTH"), ("1969", "CHANGE"),
         ("1998", "LAUNCH"), ("2026", "NOW")]


def kf(pairs):
    return [{"frame": f, "value": v} for f, v in pairs]


def text_layer(lid, text, x, y, w, h, font, size, fill, start=0, tracks=None,
               min_size=None, max_size=None):
    layer = {
        "id": lid,
        "type": "text",
        "text": text,
        "size": [w, h],
        "position": [x, y],
        "start_frame": start,
        "duration_frames": TOTAL - start,
        "style": {
            "font": font,
            "font_size": size,
            "min_font_size": min_size if min_size is not None else size,
            "max_font_size": max_size if max_size is not None else size,
            "fit_mode": "shrink_only",
            "fill": fill,
        },
    }
    if tracks:
        layer["animation"] = {"tracks": tracks}
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
    """The rail, its nodes, ticks and small labels move together, one step left
    for every new central date. The pin never moves."""
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
    """Every date sweeps in from off-screen right and out to off-screen left.
    No opacity and no visibility windows: the motion itself guarantees that
    only the active date sits in the centre."""
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
    return text_layer(f"big_date_{i}", date_text, 960, 470, 1200, 300,
                      "assets/fonts/PlayfairDisplay.ttf", 230, INK,
                      0, tracks, 160, 230)


def big_label(i, label):
    tracks = [
        {"property": "position_x", "keyframes": kf(sweep_pos(i)), "easing": "out_cubic"},
    ]
    return text_layer(f"big_label_{i}", label, 960, 635, 900, 70,
                      "assets/fonts/Inter-Regular.ttf", 38, MUTED,
                      0, tracks, 30, 38)


def count_label():
    return [
        text_layer("count", "04", 1700, 142, 200, 40,
                   "assets/fonts/PlayfairDisplay.ttf", 30, ACCENT),
        text_layer("count_caption", "DATES", 1700, 176, 200, 20,
                   "assets/fonts/Inter-Regular.ttf", 11, FAINT),
    ]


def reticle():
    """Thin fixed focus box around the active date, in the style of a camera
    focus reticle. The date sweeps through it; the box itself never moves."""
    c = [0.784, 0.333, 0.239, 0.35]
    return [
        color_layer("reticle_top", c, 720, 3, 0, -220),
        color_layer("reticle_bottom", c, 720, 3, 0, 60),
        color_layer("reticle_left", c, 3, 280, -360, -80),
        color_layer("reticle_right", c, 3, 280, 360, -80),
    ]


def build():
    shift = rail_shift()
    layers = [
        color_layer("bg", BG, 1920, 1080, 0, 0),
        color_layer("rail", RAIL, 4400, 3, 0, 280, 0, [shift]),
        color_layer("active_halo", [ACCENT_RGBA[0], ACCENT_RGBA[1], ACCENT_RGBA[2], 0.14],
                    54, 54, 0, 280),
    ]
    # Ticks, nodes and small axis labels all ride the rail.
    for i, (date_text, _) in enumerate(DATES):
        ox = i * SPACING
        layers.append(color_layer(f"tick_{i}", RAIL, 1, 24, ox, 304, 0, [shift]))
        layers.append(color_layer(f"node_{i}", [0.15, 0.15, 0.14, 1.0],
                                  16, 16, ox, 280, 0, [shift]))
        layers.append(text_layer(f"axis_{i}", date_text, 960 + ox, 885, 240, 40,
                                 "assets/fonts/PlayfairDisplay.ttf", 26, MUTED,
                                 0, [shift]))
    # Fixed pin marking the active node.
    layers.extend([
        color_layer("pin_stem", ACCENT_RGBA, 4, 100, 0, 230),
        color_layer("pin_head", ACCENT_RGBA, 26, 26, 0, 160),
        color_layer("pin_centre", BG, 8, 8, 0, 160),
    ])
    layers.extend(reticle())
    for i, (date_text, label) in enumerate(DATES):
        layers.append(big_date(i, date_text))
        layers.append(big_label(i, label))
    layers.extend(count_label())
    layers.extend([
        text_layer("heading", "A CHRONOLOGY", 960, 140, 1200, 80,
                   "assets/fonts/PlayfairDisplay.ttf", 44, INK, 0,
                   [fade(0, 18), {"property": "position_y",
                                  "keyframes": kf([(0, 10.0), (18, 0.0), (TOTAL - 1, 0.0)]),
                                  "easing": "out_cubic"}]),
        text_layer("subtitle", "FOUR DATES  ·  1948—2026", 960, 197, 1200, 30,
                   "assets/fonts/Inter-Regular.ttf", 18, MUTED, 0, [fade(0, 22)]),
        text_layer("footer", "CHRONON TEMPLATE  ·  DATE TIMELINE", 250, 1010, 420, 24,
                   "assets/fonts/Inter-Regular.ttf", 12, FAINT),
    ])
    return {
        "schema": "chronon.render-plan.v3",
        "version": 3,
        "job_id": "date_timeline_focus_4dates",
        "canvas": {"width": 1920, "height": 1080, "fps_num": 30, "fps_den": 1,
                   "duration_frames": TOTAL},
        "layers": layers,
        "output": {"path": "focus_4dates.mp4", "format": "mp4", "codec": "h264"},
    }


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    plan = build()
    path = OUT / "focus_4dates.plan.json"
    path.write_text(json.dumps(plan, indent=2, ensure_ascii=False) + "\n")
    print(f"{path}  layers={len(plan['layers'])}  frames={TOTAL}")


if __name__ == "__main__":
    main()
