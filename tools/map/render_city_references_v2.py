#!/usr/bin/env python3
"""Render four 5-second city map clips matching the supplied reference cards."""
from __future__ import annotations

import math
import subprocess
import sys
import argparse
from pathlib import Path

import cv2
import numpy as np
import torch

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import render_destructive_dark_maps as maps  # noqa: E402

OUT = HERE.parents[1] / "out" / "city_map_v2"
OUT.mkdir(parents=True, exist_ok=True)
FPS = 30
FRAMES = 150

CITIES = [
    # city, country, lon, lat, start pose, end pose, style
    ("Brasilia", "Brazil", -47.8825, -15.7942, (-64, -18, 7), (-52, -10, 24), "brazil_card"),
    ("Manaus", "Brazil", -60.0217, -3.1190, (-61.2, -1.7, 100), (-60.02, -3.12, 700), "manaus_satellite"),
    ("Tijuana", "Mexico", -117.0382, 32.5149, (-116.4, 32.9, 140), (-116.83, 32.17, 560), "baja_redbox"),
    ("Ensenada", "Mexico", -116.6063, 31.8667, (-116.2, 32.4, 140), (-116.83, 32.17, 560), "baja_redbox"),
]

RED = (30, 35, 238)
CORAL = (34, 85, 218)


def darken_grade(frame, style):
    if style == "brazil_card":
        # Warm relief paper and blue ocean, as in the Brasilia reference.
        b, g, r = cv2.split(frame)
        warm = cv2.merge((cv2.addWeighted(b, .38, g, .10, 82),
                          cv2.addWeighted(g, .55, r, .08, 103),
                          cv2.addWeighted(r, .55, g, .12, 112)))
        return cv2.addWeighted(frame, .18, warm, .82, 0)
    if style == "manaus_satellite":
        b, g, r = cv2.split(frame)
        forest = cv2.merge((cv2.convertScaleAbs(b, alpha=.55),
                            cv2.convertScaleAbs(g, alpha=.78, beta=6),
                            cv2.convertScaleAbs(r, alpha=.48)))
        return cv2.addWeighted(frame, .18, forest, .82, 0)
    # Near monochrome high contrast relief, dark sea / pale land like Baja references.
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    mono = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)
    mono = cv2.convertScaleAbs(mono, alpha=1.45, beta=-72)
    return cv2.addWeighted(frame, .12, mono, .88, 0)


def draw_grid(frame, color, alpha):
    grid = np.zeros_like(frame)
    for x in range(0, maps.WIDTH, 80):
        cv2.line(grid, (x, 0), (x, maps.HEIGHT), color, 1, cv2.LINE_AA)
    for y in range(0, maps.HEIGHT, 80):
        cv2.line(grid, (0, y), (maps.WIDTH, y), color, 1, cv2.LINE_AA)
    return cv2.addWeighted(frame, 1.0, grid, alpha, 0)


def draw_reference_pin(mask, x, y, radius=24):
    # Red map pin silhouette with a bright center hole, matching both Brazil cards.
    cv2.circle(mask, (x, y - radius), radius, 255, -1, cv2.LINE_AA)
    tip = np.array([[x - radius + 3, y - radius // 2],
                    [x + radius - 3, y - radius // 2], [x, y + radius + 15]], np.int32)
    cv2.fillConvexPoly(mask, tip, 255, cv2.LINE_AA)


def render(city_data):
    name, country, lon, lat, start_pose, end_pose, style = city_data
    maps.RENDERER_MODE = "opencv"
    cam = maps.DynamicCamera(start_pose, end_pose, FRAMES)
    brazil_rings = maps.GEO.get_country_rings("Brazil") if style == "brazil_card" else []
    frames = []
    for f in range(FRAMES):
        cx, cy, scale = cam.get_pose(f)
        frame = cam.render_base(cx, cy, scale)
        frame = darken_grade(frame, style)
        if style == "brazil_card":
            frame = draw_grid(frame, (120, 174, 197), .33)
        elif style == "manaus_satellite":
            frame = draw_grid(frame, (50, 96, 28), .34)
        else:
            frame = draw_grid(frame, (198, 198, 198), .48)

        city_progress = maps.smooth_swoop((f - 28) / 48.0)
        gpu = maps.GPUMapFrame(frame)

        px, py = cam.project_point(lon, lat, cx, cy, scale)
        if style in ("brazil_card", "manaus_satellite"):
            # Reference cards use a large italic serif label and a red location pin.
            if style == "brazil_card":
                label = "Brasilia"
                label_x, label_y = max(40, px - 150), max(120, py - 160)
                # Composite the title after the country fill so the white serif type stays legible.
                title_shadow = np.zeros((maps.HEIGHT, maps.WIDTH), dtype=np.uint8)
                title = np.zeros_like(title_shadow)
                face = cv2.FONT_HERSHEY_TRIPLEX | cv2.FONT_ITALIC
                cv2.putText(title_shadow, label, (label_x + 2, label_y + 3), face, 2.0, 255, 7, cv2.LINE_AA)
                cv2.putText(title, label, (label_x, label_y), face, 2.0, 255, 5, cv2.LINE_AA)
            else:
                cv2.putText(frame, "Manaus", (max(50, px - 200), max(130, py - 175)),
                            cv2.FONT_HERSHEY_TRIPLEX | cv2.FONT_ITALIC, 2.25,
                            (250, 248, 240), 4, cv2.LINE_AA)
            gpu = maps.GPUMapFrame(frame)
            if style == "brazil_card":
                # Highlight the whole country in warm orange-red, not just the city.
                brazil_polys = cam.project_rings(brazil_rings, cx, cy, scale)
                country_mask = np.zeros((maps.HEIGHT, maps.WIDTH), dtype=np.uint8)
                cv2.fillPoly(country_mask, brazil_polys, 255, shift=maps.SUBPIXEL_SHIFT)
                gpu.blend_mask(country_mask, CORAL, .86 * city_progress)
                maps.DynamicEffects.draw_outline_glow(gpu, brazil_polys, CORAL,
                                                      progress=city_progress, thickness=2, halo_strength=.5)
                gpu.blend_mask(title_shadow, (25, 26, 31), .62)
                gpu.blend_mask(title, (250, 248, 244), .98)
            if city_progress > 0:
                halo = np.zeros((maps.HEIGHT, maps.WIDTH), dtype=np.uint8)
                cv2.circle(halo, (px, py - 12), 52, 255, 3, cv2.LINE_AA)
                gpu.blend_mask(gpu.gaussian(halo, 15), RED, .5 * city_progress)
                gpu.blend_mask(halo, RED, .7 * city_progress)
                pin = np.zeros((maps.HEIGHT, maps.WIDTH), dtype=np.uint8)
                draw_reference_pin(pin, px, py, 27 if style == "brazil_card" else 24)
                gpu.blend_mask(gpu.gaussian(pin, 13), RED, .62 * city_progress)
                gpu.blend_mask(pin, RED, .95 * city_progress)
                center = np.zeros_like(pin)
                cv2.circle(center, (px, py - (27 if style == "brazil_card" else 24)), 10, 255, -1, cv2.LINE_AA)
                gpu.blend_mask(center, (42, 154, 236), .86 * city_progress)
        else:
            # Baja: black rectangular white type boxes over pale monochrome map and red borders.
            box_y = 56 if name == "Tijuana" else 124
            box_w, box_h = 370, 112
            cv2.rectangle(frame, (72, box_y), (72 + box_w, box_y + box_h), (18, 18, 18), -1)
            cv2.putText(frame, "Tijuana", (92, box_y + 43), cv2.FONT_HERSHEY_SIMPLEX,
                        .86, (244, 244, 244), 2, cv2.LINE_AA)
            cv2.putText(frame, "Ensenada", (92, box_y + 87), cv2.FONT_HERSHEY_SIMPLEX,
                        .86, (244, 244, 244), 2, cv2.LINE_AA)
            cv2.rectangle(frame, (72, box_y), (78, box_y + box_h), RED, -1)
            gpu = maps.GPUMapFrame(frame)
            # The red trace follows Mexico's coast/land outline in the reference style.
            mx = maps.GEO.get_country_rings("Mexico")
            mx_polys = cam.project_rings(mx, cx, cy, scale)
            maps.DynamicEffects.draw_outline_glow(gpu, mx_polys, RED,
                                                  progress=city_progress, thickness=4, halo_strength=.34)
            if city_progress > 0:
                selected = (px, py)
                pulse = np.zeros((maps.HEIGHT, maps.WIDTH), dtype=np.uint8)
                cv2.circle(pulse, selected, 22, 255, 3, cv2.LINE_AA)
                gpu.blend_mask(gpu.gaussian(pulse, 10), RED, .52 * city_progress)
                gpu.blend_mask(pulse, RED, .95 * city_progress)
                dot = np.zeros_like(pulse)
                cv2.circle(dot, selected, 5, 255, -1, cv2.LINE_AA)
                gpu.blend_mask(dot, (20, 20, 20), .9 * city_progress)
        frames.append(gpu.to_numpy())
    out = OUT / f"{name.lower()}_city_map_5s.mp4"
    maps.write_video_h264(frames, out)
    print(f"Rendered {name}: {out}", flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--city", choices=[item[0] for item in CITIES],
                        help="render one city; omit to render all four")
    args = parser.parse_args()
    if not torch.cuda.is_available():
        raise RuntimeError("CUDA required; CPU rendering is disabled")
    encoders = subprocess.run(["ffmpeg", "-hide_banner", "-encoders"], capture_output=True,
                              text=True, check=True).stdout
    if "h264_nvenc" not in encoders:
        raise RuntimeError("h264_nvenc required; software encoding is disabled")
    print(f"GPU renderer active: {torch.cuda.get_device_name(0)}; encoder=h264_nvenc", flush=True)
    for city_data in CITIES:
        if args.city and city_data[0] != args.city:
            continue
        render(city_data)


if __name__ == "__main__":
    main()
