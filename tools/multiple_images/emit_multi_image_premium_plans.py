#!/usr/bin/env python3
"""Emit the eight premium multi-image choreographies as 2D render plans."""
from __future__ import annotations

import json
from pathlib import Path

FRAMES = 180
FPS = 30
W, H = 1920, 1080

GLENN = "assets/famous_people_trio_v1/john_glenn.png"
ARMSTRONG = "assets/famous_people_trio_v1/neil_armstrong.png"
RIDE = "assets/famous_people_trio_v1/sally_ride.png"
WOMAN = "assets/drive_trio_replica_v1/online/portrait_woman.jpg"
MAN = "assets/drive_trio_replica_v1/online/portrait_man1.jpg"

LAYOUTS = {
    "duo": (600, 900, [(-332, 0), (332, 0)]),
    "trio": (500, 740, [(-528, 0), (0, 0), (528, 0)]),
    "quad": (420, 570, [(-420, -300), (420, -300), (-420, 300), (420, 300)]),
    "penta": (300, 430, [(-384, -238), (384, -238), (-653, 238), (0, 238), (653, 238)]),
}


def track(prop: str, easing: str, keys: list[tuple[int, float]]) -> dict:
    # A focus beat may start on the same frame where the entrance settles; keep
    # the focus value instead of emitting two keys for one frame.
    unique = dict(keys)
    return {
        "property": prop,
        "easing": easing,
        "keyframes": [{"frame": frame, "value": value}
                      for frame, value in sorted(unique.items())],
    }


def image_layer(name: str, idx: int, asset: str, pos: tuple[float, float], size: tuple[float, float],
                start: int, dx: float, dy: float, focus: tuple[int, int, float, float, float] | None,
                pop: bool = False) -> dict:
    x, y = pos
    tracks = [
        track("opacity", "out_cubic", [(0, 0.0), (start + 18, 1.0), (172, 1.0), (179, 0.0)]),
        track("scale", "in_out_cubic", [
            (0, 0.86 if pop else 0.93),
            (start + 42, 1.0),
            *(([(focus[0], focus[2]), (focus[1], 1.0)]) if focus else []),
            (172, 1.0),
        ]),
    ]
    # Animation position tracks are offsets from the layer's base position.
    if dx or focus:
        keys = [(0, dx), (start + 55, 0.0)]
        if focus:
            keys += [(focus[0], focus[3]), (focus[1], 0.0)]
        tracks.append(track("position_x", "in_out_cubic", keys))
    if dy or focus:
        keys = [(0, dy), (start + 55, 0.0)]
        if focus:
            keys += [(focus[0], focus[4]), (focus[1], 0.0)]
        tracks.append(track("position_y", "in_out_cubic", keys))
    return {
        "id": f"{name}_image_{idx}",
        "type": "image",
        "asset": asset,
        "size": [size[0], size[1]],
        "position": [x, y],
        "radius": 0.0,
        "fit": "cover",
        "enable_3d": True,
        "start_frame": 0,
        "duration_frames": FRAMES,
        "animation": {"tracks": tracks},
    }


def title_layer(title: str) -> dict:
    return {
        "id": "title",
        "type": "text",
        "text": title,
        "position": [0, -472],
        "size": [1200, 40],
        "enable_3d": True,
        "start_frame": 0,
        "duration_frames": FRAMES,
        "style": {
            "font": "assets/fonts/Inter-Bold.ttf",
            "font_size": 28,
            "fill": "#EDE9FF",
        },
        "animation": {"tracks": [track("opacity", "out_cubic", [(0, 0.0), (20, 0.9), (170, 0.9), (179, 0.0)])]},
    }


SPECS = {
    "duo_cinematic_parallax": {
        "layout": "duo", "title": "CINEMATIC PARALLAX",
        "cards": [
            (GLENN, 0, -180, 60, (85, 125, 1.045, -8, 0), False),
            (RIDE, 12, 180, 60, (130, 170, 1.045, 8, 0), False),
        ],
    },
    "duo_depth_handoff": {
        "layout": "duo", "title": "DEPTH HANDOFF",
        "cards": [
            (ARMSTRONG, 0, 0, 70, (65, 105, 1.05, 0, -6), True),
            (WOMAN, 10, 0, 70, (115, 155, 1.05, 0, -6), True),
        ],
    },
    "trio_orbit_focus": {
        "layout": "trio", "title": "ORBIT FOCUS",
        "cards": [
            (GLENN, 10, -200, 60, (65, 95, 1.05, -6, 0), False),
            (ARMSTRONG, 0, 0, 40, (100, 130, 1.06, 0, 0), True),
            (RIDE, 20, 200, 60, (135, 165, 1.05, 6, 0), False),
        ],
    },
    "trio_prism_cascade": {
        "layout": "trio", "title": "PRISM CASCADE",
        "cards": [
            (RIDE, 0, -220, 90, (55, 85, 1.05, 0, -6), False),
            (WOMAN, 8, 0, 110, (90, 120, 1.06, 0, 0), False),
            (MAN, 16, 220, 90, (125, 155, 1.05, 0, -6), False),
        ],
    },
    "quad_mosaic_wave": {
        "layout": "quad", "title": "MOSAIC WAVE",
        "cards": [
            (GLENN, 0, 0, 80, (60, 80, 1.04, 0, -4), False),
            (ARMSTRONG, 6, 0, 80, (85, 105, 1.04, 0, -4), False),
            (RIDE, 12, 0, 80, (110, 130, 1.04, 0, -4), False),
            (WOMAN, 18, 0, 80, (135, 155, 1.04, 0, -4), False),
        ],
    },
    "quad_parallax_grid": {
        "layout": "quad", "title": "PARALLAX GRID",
        "cards": [
            (MAN, 0, -190, 0, (60, 95, 1.05, 0, -5), False),
            (GLENN, 20, 190, 0, (75, 110, 1.05, 0, -5), False),
            (WOMAN, 10, -190, 0, (115, 150, 1.045, 0, -5), False),
            (ARMSTRONG, 30, 190, 0, (130, 165, 1.045, 0, -5), False),
        ],
    },
    "penta_carousel_orbit": {
        "layout": "penta", "title": "CAROUSEL ORBIT",
        "cards": [
            (GLENN, 0, 0, 60, (60, 80, 1.045, -4, 0), False),
            (ARMSTRONG, 4, 0, 60, (70, 90, 1.045, 4, 0), False),
            (RIDE, 8, 0, 60, (80, 100, 1.045, -4, 0), False),
            (WOMAN, 12, 0, 60, (90, 110, 1.045, 4, 0), False),
            (MAN, 16, 0, 60, (100, 120, 1.045, -4, 0), False),
        ],
    },
    "penta_hero_cascade": {
        "layout": "penta", "title": "HERO CASCADE",
        "cards": [
            (RIDE, 8, 0, 60, (120, 140, 1.035, -4, 0), False),
            (WOMAN, 12, 0, 60, (125, 145, 1.035, 4, 0), False),
            (GLENN, 4, 0, 60, (130, 150, 1.035, -4, 0), False),
            (MAN, 0, 0, 70, (75, 115, 1.07, 0, -5), True),
            (ARMSTRONG, 16, 0, 60, (135, 155, 1.035, 4, 0), False),
        ],
    },
}


def main() -> None:
    out = Path(__file__).resolve().parents[2] / "out" / "multi_image_premium_v1"
    out.mkdir(parents=True, exist_ok=True)
    for name, spec in SPECS.items():
        width, height, positions = LAYOUTS[spec["layout"]]
        layers = [{
            "id": "studio_dark_bg",
            "type": "color",
            "color": [0.025, 0.03, 0.075, 1.0],
            "size": [W, H],
            "position": [0, 0],
            "start_frame": 0,
            "duration_frames": FRAMES,
        }, title_layer(spec["title"])]
        for idx, (asset, start, dx, dy, focus, pop) in enumerate(spec["cards"]):
            layers.append(image_layer(name, idx, asset, positions[idx], (width, height),
                                      start, dx, dy, focus, pop))
        plan = {
            "schema": "chronon.render-plan.v3",
            "version": 3,
            "job_id": name,
            "canvas": {"width": W, "height": H, "fps_num": FPS, "fps_den": 1,
                       "duration_frames": FRAMES},
            "output": {"path": f"{name}.mp4", "format": "mp4", "codec": "h264"},
            "layers": layers,
        }
        path = out / f"{name}.plan.json"
        path.write_text(json.dumps(plan, indent=2) + "\n")
        print(f"{path} ({len(layers)} layers)")


if __name__ == "__main__":
    main()
