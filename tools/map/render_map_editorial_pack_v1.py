#!/usr/bin/env python3
"""Render all six certified documentary map scenes from the shared visual brief.

Each clip's `map_animation` id is an exact runtime payload value. Outputs are
MP4-only in the pack directory; uploads never include stills or payloads.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
TEMPLATE = HERE.parents[1]
OUT = TEMPLATE / "out" / "map_editorial_v1"
RENDERER = HERE / "render_dynamic_map_overlay.py"

CAMERA_ANIMATION = "slow_approach"
BASEMAP = "esri_sat"
STD_US = 5_000_000

CLIPS = [
    ("01_ed_saudi_base",
     [{"id": "saudi", "label": "Saudi Arabia", "latitude": 24.7136,
       "longitude": 46.6753, "scope": "country"}],
     "ed_saudi_base", "Saudi Arabia real border, restrained grid, title."),
    ("02_ed_iran_glow",
     [{"id": "iran", "label": "Iran", "latitude": 32.0,
       "longitude": 53.0, "scope": "country"}],
     "ed_iran_glow", "Iran real border with GPU glow and editorial title."),
    ("03_ed_yemen_fill",
     [{"id": "yemen", "label": "Yemen", "latitude": 15.3,
       "longitude": 47.0, "scope": "country"}],
     "ed_yemen_fill", "Yemen full country fill; not conflict-control data."),
    ("04_ed_yemen_markers",      [{"id": "sanaa", "label": "Sanaa", "latitude": 15.3694,
       "longitude": 44.1910, "scope": "country"},
      {"id": "hodeidah", "label": "Hodeidah", "latitude": 14.7979,
       "longitude": 42.9545, "scope": "country"},
      {"id": "abha", "label": "Abha Intl Airport", "latitude": 18.2164,
       "longitude": 42.5053, "scope": "country"}],
     "ed_yemen_markers", "Yemen fill with grounded city/airport markers.",
     5_000_000),
    ("06_ed_mocha_tactical",
     [{"id": "mocha", "label": "Mocha", "latitude": 13.3167,
       "longitude": 43.2500, "scope": "region"}],
     "ed_mocha_tactical", "Mocha schematic tactical overlays, not sourced control."),
    ("05_ed_hormuz_routes",
     [{"id": "hormuz", "label": "Strait of Hormuz", "latitude": 26.55,
       "longitude": 56.27, "scope": "country"}],
     "ed_hormuz_routes", "Editorial route corridors through Hormuz, Bab el-Mandeb, Asia and Europe."),
]


def render_clip(slug, pins, map_animation, duration_us=STD_US):
    source = OUT / (slug + ".json")
    target = OUT / (slug + ".mp4")
    payload = {
        "width": 1920, "height": 1080,
        "fps_num": 24, "fps_den": 1, "duration_us": duration_us,
        "pins": pins,
        "area_glow_radius_km": 0.0,
        "camera_animation": CAMERA_ANIMATION,
        "label_animation": "none",
        "map_animation": map_animation,
        "basemap": BASEMAP,
    }
    source.write_text(json.dumps(payload, separators=(",", ":")),
                      encoding="utf-8")
    subprocess.run([sys.executable, str(RENDERER), "--input", str(source),
                    "--output", str(target)], check=True)
    return target


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    manifest = {
        "title": "Chronon Map Editorial Pack v1",
        "region": "Middle East",
        "camera_animation": CAMERA_ANIMATION,
        "label_animation": "none (every scene owns its text)",
        "basemap": BASEMAP,
        "canvas": "1920x1080, 24 fps, 5s per scene",
        "honesty": "Country borders: Natural Earth 50m. Yemen fill is the national boundary only; no sourced control-area dataset was present. Hormuz routes and Mocha tactical overlays are schematic.",
        "clips": [],
        "files": "MP4 only; telemetry, JSON payloads, and stills stay local.",
    }
    filter_ids = set(sys.argv[1:]) if len(sys.argv) > 1 else None
    for entry in CLIPS:
        slug, pins, anim, desc = entry[:4]
        if filter_ids and slug not in filter_ids and anim not in filter_ids:
            continue
        dur = entry[4] if len(entry) > 4 else STD_US
        print("[map-editorial] rendering " + slug + " [" + anim + "]",
              flush=True)
        path = render_clip(slug, pins, anim, dur)
        manifest["clips"].append({"id": slug, "map_animation": anim,
                                  "pins": pins, "description": desc,
                                  "duration_us": dur, "file": path.name})
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2),
                                       encoding="utf-8")
    print("[map-editorial] complete: " + str(OUT), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
