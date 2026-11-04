#!/usr/bin/env python3
"""Build the cyan, bevel-lit title treatment from the Drive reference."""
from __future__ import annotations
import argparse
import json
from pathlib import Path

W, H = 1920, 320
FRAMES = 1
PHRASE = "calories or ingredients"
FONT = "ChrononTemplate/assets/fonts/LiberationMono-Bold.ttf"


def rgb(hex_color: str) -> list[float]:
    value = hex_color.lstrip("#")
    return [int(value[i:i+2], 16) / 255 for i in (0, 2, 4)] + [1.0]


def color_spans(text: str) -> list[dict]:
    stops = [(70, 221, 245), (194, 255, 255), (70, 221, 245)]
    result, count = [], len(text)
    for index, char in enumerate(text):
        t = index / max(1, count - 1) * 2
        segment = min(1, int(t))
        local_t = t - segment
        color = tuple(round(stops[segment][k] * (1 - local_t) +
                            stops[segment + 1][k] * local_t) for k in range(3))
        result.append({
            "start": index, "end": index + len(char.encode("utf-8")),
            "style": {"color": "#" + "".join(f"{channel:02X}" for channel in color)},
        })
    return result


def make_plan() -> dict:
    layers = [{"id": "reference_blurred_background", "type": "image",
               "asset": "ChrononTemplate/assets/backgrounds/calories_ingredients_blur.png",
               "size": [W, H], "position": [0, 0], "opacity": 0.36,
               "start_frame": 0, "duration_frames": FRAMES},
        {"id": "bevel_lower_rim", "type": "text", "text": PHRASE,
         "size": [1840, 250], "position": [W / 2, H / 2 + 2], "screen_space": True,
         "start_frame": 0, "duration_frames": FRAMES, "opacity": 0.42,
         "style": {"font": FONT, "font_size": 126, "font_weight": 700,
                   "fill": "#003366"}},
        {"id": "reference_text", "type": "text", "text": PHRASE,
         "size": [1840, 250], "position": [W / 2, H / 2], "screen_space": True,
         "start_frame": 0, "duration_frames": FRAMES,
         "style": {
             "font": FONT, "font_size": 126, "font_weight": 700,
             "fill": "#A2FAFF",
             "stroke": {"color": "#57DFFF", "width": 1.2, "opacity": 0.42},
             "glow": {"radius": 16, "intensity": 0.22, "color": "#00DFFF"},
             "shadows": [{"color": "#F0FFFF", "offset": [0, -2],
                          "opacity": 0.86, "blur": 0}],
         }},
    ]
    layers[-1]["spans"] = color_spans(PHRASE)
    return {
        "schema": "chronon.render-plan.v3", "version": 3,
        "job_id": "reference_neon_bevel", "canvas": {
            "width": W, "height": H, "fps_num": 30, "fps_den": 1,
            "duration_frames": FRAMES},
        "layers": layers,
        "output": {"path": "reference_neon_bevel.png", "format": "png"},
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=Path("out/text_25d_depth"))
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    plan_path = args.out / "reference_neon_bevel.plan.json"
    plan_path.write_text(json.dumps(make_plan(), ensure_ascii=False, indent=2) + "\n",
                         encoding="utf-8")
    print(plan_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
