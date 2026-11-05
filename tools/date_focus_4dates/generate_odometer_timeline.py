#!/usr/bin/env python3
"""Playfair four-date odometer (chronon.render-plan.v3).

Light editorial variant. The century ("19", then "20") stays fixed while the
last two digits roll vertically inside a cream slot. Only the date and a
minimal rail remain; there is no reticle, pin, count, label or footer.
No glow, no shadows, no neon.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]  # ChrononTemplate
OUT = ROOT / "golden_plans" / "date_odometer_4dates"
TOTAL = 320
SPACING = 280.0
RAIL_X = [540.0, 820.0, 1100.0, 1380.0]

INK = "#262521"
MUTED = "#66625B"
ACCENT = "#C8553D"
BG = [0.96, 0.95, 0.93, 1.0]
RAIL = [0.72, 0.70, 0.66, 1.0]
ACCENT_RGBA = [0.784, 0.333, 0.239, 1.0]
DATES = [("1948", "BIRTH", "48"), ("1969", "CHANGE", "69"),
         ("1998", "LAUNCH", "98"), ("2026", "NOW", "26")]


def kf(pairs):
    return [{"frame": f, "value": v} for f, v in pairs]


def text_layer(lid, text, x, y, w, h, font, size, fill, tracks=None):
    layer = {
        "id": lid,
        "type": "text",
        "text": text,
        "size": [w, h],
        "position": [x, y],
        "start_frame": 0,
        "duration_frames": TOTAL,
        "style": {
            "font": font,
            "font_size": size,
            "min_font_size": size,
            "max_font_size": size,
            "fit_mode": "shrink_only",
            "fill": fill,
        },
    }
    if tracks:
        layer["animation"] = {"tracks": tracks}
    return layer


def color_layer(lid, color, w, h, ox, oy, tracks=None):
    layer = {
        "id": lid,
        "type": "color",
        "color": color,
        "size": [w, h],
        "position": [ox, oy],
        "start_frame": 0,
        "duration_frames": TOTAL,
    }
    if tracks:
        layer["animation"] = {"tracks": tracks}
    return layer


def wheel_track():
    """Roll the last-two-digit drum one step up for each date."""
    return {"property": "position_y",
            "keyframes": kf([
                (0, 0.0), (60, 0.0), (88, -380.0), (140, -380.0),
                (168, -760.0), (220, -760.0),
                (248, -1140.0), (TOTAL - 1, -1140.0),
            ]),
            "easing": "in_out_cubic"}


def prefix_track():
    """The century stays fixed for 1948/1969/1998, then rolls 19 -> 20."""
    return {"property": "position_y",
            "keyframes": kf([(0, 0.0), (220, 0.0), (248, -380.0),
                             (TOTAL - 1, -380.0)]),
            "easing": "in_out_cubic"}


def active_track():
    # Offsets from the layer's base x (RAIL_X[0] - 960), not screen x.
    return {"property": "position_x",
            "keyframes": kf([
                (0, 0.0), (60, 0.0), (88, 280.0),
                (140, 280.0), (168, 560.0), (220, 560.0),
                (248, 840.0), (TOTAL - 1, 840.0),
            ]),
            "easing": "in_out_cubic"}


def build():
    wheel = wheel_track()
    prefix = prefix_track()
    active_x = active_track()
    layers = [color_layer("bg", BG, 1920, 1080, 0, 0)]
    # Century wheel: 19 for the first three dates, 20 for 2026.
    layers.append(text_layer("prefix_19", "19", 850, 470, 600, 300,
                             "assets/fonts/PlayfairDisplay.ttf", 230, INK, [prefix]))
    layers.append(text_layer("prefix_20", "20", 850, 850, 600, 300,
                             "assets/fonts/PlayfairDisplay.ttf", 230, INK, [prefix]))
    # Last-two-digit drum.
    for i, (_, _, suffix) in enumerate(DATES):
        layers.append(text_layer(f"suffix_{i}", suffix, 1070, 470 + i * 380,
                                 600, 300, "assets/fonts/PlayfairDisplay.ttf",
                                 230, INK, [wheel]))
    # Opaque cream covers create the odometer slot. They must sit ABOVE the
    # wheels and BELOW the rail overlay to hide off-slot dates.
    layers.extend([
        color_layer("slot_cover_top", BG, 1920, 300, 0, -390),
        color_layer("slot_cover_bottom", BG, 1920, 380, 0, 350),
    ])
    # Minimal static rail: one line, four dates, no nodes, ticks or pin.
    layers.append(color_layer("rail", RAIL, 1000, 2, 0, 280))
    for i, (date_text, _, _) in enumerate(DATES):
        layers.append(text_layer(f"axis_{i}", date_text, RAIL_X[i], 886,
                                 240, 40, "assets/fonts/PlayfairDisplay.ttf",
                                 26, MUTED))
    # The only moving marker is a short terracotta underline under the
    # active date. No square head, halo or vertical stem.
    layers.append(color_layer("active_underline", ACCENT_RGBA, 160, 2,
                              RAIL_X[0] - 960.0, 375, [active_x]))
    return {
        "schema": "chronon.render-plan.v3",
        "version": 3,
        "job_id": "date_odometer_4dates",
        "canvas": {"width": 1920, "height": 1080, "fps_num": 30, "fps_den": 1,
                   "duration_frames": TOTAL},
        "layers": layers,
        "output": {"path": "odometer_4dates.mp4", "format": "mp4", "codec": "h264"},
    }


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    plan = build()
    path = OUT / "odometer_4dates.plan.json"
    path.write_text(json.dumps(plan, indent=2, ensure_ascii=False) + "\n")
    print(f"{path}  layers={len(plan['layers'])}  frames={TOTAL}")


if __name__ == "__main__":
    main()
