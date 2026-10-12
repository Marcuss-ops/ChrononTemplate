#!/usr/bin/env python3
"""Render the six distinct-geometry label styles, one fixed camera.

Every clip uses the SAME camera animation (steady_hold, satellite basemap)
and a DIFFERENT real place of Rome with a DIFFERENT distinct-geometry label
style (size/position/typeface), so the six treatments compare one-to-one.
Each `label_animation` id is the exact runtime payload value.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
TEMPLATE = HERE.parents[1]
OUT = TEMPLATE / "out" / "map_label_styles_v1"
RENDERER = HERE / "render_dynamic_map_overlay.py"

CAMERA_ANIMATION = "steady_hold"
BASEMAP = "esri_sat"

# (slug, label text, latitude, longitude, label_animation, description)
PLACES = [
    ("01_piazza_popolo_title", "Piazza del Popolo", 41.9109, 12.4764,
     "title_top", "Large top title, Inter Bold 84px."),
    ("02_campo_fiori_badge", "Campo de' Fiori", 41.8956, 12.4846,
     "badge_side", "Pill badge right of the beacon, 34px."),
    ("03_aventino_huge", "Aventino", 41.8883, 12.4804,
     "huge_center", "Display face high on frame, Abril 150px."),
    ("04_gianicolo_small", "Gianicolo", 41.8911, 12.4602,
     "small_above", "Small caption over the beacon, 30px + accent bar."),
    ("05_piazza_venezia_card", "Piazza Venezia", 41.8960, 12.4828,
     "caption_card", "Top-left card, 46px + cyan accent bar."),
    ("06_termini_serif", "Stazione Termini", 41.9010, 12.5007,
     "editorial_serif", "Large roman serif below beacon, 76px."),
]


def render_place(slug: str, label: str, lat: float, lon: float,
                 label_animation: str) -> Path:
    source = OUT / f"{slug}.json"
    target = OUT / f"{slug}.mp4"
    payload = {
        "width": 1920, "height": 1080,
        "fps_num": 24, "fps_den": 1, "duration_us": 5_000_000,
        "pins": [{"id": slug, "label": label,
                  "latitude": lat, "longitude": lon,
                  "scope": "city"}],
        "area_glow_radius_km": 3.5,
        "camera_animation": CAMERA_ANIMATION,
        "label_animation": label_animation,
        "basemap": BASEMAP,
    }
    source.write_text(json.dumps(payload, separators=(",", ":")), encoding="utf-8")
    subprocess.run([sys.executable, str(RENDERER), "--input", str(source),
                    "--output", str(target)], check=True)
    return target


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    manifest = {
        "title": "Chronon Map Label Styles Pack v1",
        "city": "Roma, Italia",
        "camera_animation": CAMERA_ANIMATION,
        "basemap": BASEMAP,
        "canvas": "1920x1080, 24 fps, 5 seconds",
        "note": "One fixed camera for every clip; only the label style "
                "(size/position/typeface) changes, so styles compare one-to-one.",
        "clips": [],
    }
    files: list[Path] = []
    for slug, label, lat, lon, label_animation, description in PLACES:
        print(f"[label-styles] rendering {label} [{label_animation}]", flush=True)
        path = render_place(slug, label, lat, lon, label_animation)
        files.append(path)
        manifest["clips"].append({"id": slug, "text": label,
                                  "latitude": lat, "longitude": lon,
                                  "label_animation": label_animation,
                                  "description": description,
                                  "file": path.name})
    for path in files:
        still = OUT / f"{path.stem}.jpg"
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-ss", "4.4",
                        "-i", str(path), "-frames:v", "1", "-q:v", "3",
                        str(still)], check=True)
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2),
                                       encoding="utf-8")
    readme = ["# Chronon Map Label Styles Pack v1", "",
              "Roma, Italia — one fixed camera (`steady_hold`, satellite) for every clip.",
              "Only the label style (size/position/typeface) changes.",
              "Each `map_label_animation` id below is the exact runtime payload value.",
              "", "## Clips", ""]
    readme.extend(f"- **{x['text']}** — `{x['label_animation']}` ({x['description']}) `{x['file']}`"
                  for x in manifest["clips"])
    (OUT / "README.md").write_text("\n".join(readme) + "\n", encoding="utf-8")
    print(f"[label-styles] complete: {OUT}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
