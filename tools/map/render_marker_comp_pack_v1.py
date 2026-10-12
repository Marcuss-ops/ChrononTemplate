#!/usr/bin/env python3
"""Render the six full marker compositions, one fixed camera.

Every clip uses the SAME camera animation (steady_hold, satellite basemap)
and a DIFFERENT real place of Rome with a DIFFERENT marker composition
(own marker + own text shape, no bottom rail), so the six treatments
compare one-to-one. Each `label_animation` id is the exact runtime
payload value.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
TEMPLATE = HERE.parents[1]
OUT = TEMPLATE / "out" / "map_marker_comp_v1"
RENDERER = HERE / "render_dynamic_map_overlay.py"

CAMERA_ANIMATION = "steady_hold"
BASEMAP = "esri_sat"

# (slug, label text, latitude, longitude, label_animation, description)
PLACES = [
    ("01_castello_pin", "Castel Sant'Angelo", 41.9031, 12.4663,
     "gpin_bubble", "Google red pin dropping + white bubble, dark text."),
    ("02_pietro_card", "San Pietro", 41.9022, 12.4539,
     "card_glass", "Frosted glass card left-center, cyan border."),
    ("03_circo_bare", "Circo Massimo", 41.8859, 12.4855,
     "bare_big", "Naked display type, no rectangle, no stroke."),
    ("04_patria_ribbon", "Altare della Patria", 41.8957, 12.4848,
     "ribbon", "Full-width band wiping from the left."),
    ("05_borghese_dot", "Villa Borghese", 41.9142, 12.4921,
     "dot_ring", "Ultra-minimal dot + pulsing ring + tiny text."),
    ("06_pincio_outline", "Pincio", 41.9100, 12.4770,
     "outline_box", "Empty wireframe box with white corner ticks."),
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
        "title": "Chronon Map Marker Compositions Pack v1",
        "city": "Roma, Italia",
        "camera_animation": CAMERA_ANIMATION,
        "basemap": BASEMAP,
        "canvas": "1920x1080, 24 fps, 5 seconds",
        "note": "One fixed camera for every clip; each composition draws "
                "its own marker and hides the bottom rail, so treatments "
                "compare one-to-one.",
        "clips": [],
    }
    files: list[Path] = []
    for slug, label, lat, lon, label_animation, description in PLACES:
        print(f"[marker-comp] rendering {label} [{label_animation}]", flush=True)
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
    readme = ["# Chronon Map Marker Compositions Pack v1", "",
              "Roma, Italia — one fixed camera (`steady_hold`, satellite) for every clip.",
              "Each composition draws its own marker and hides the bottom rail.",
              "Each `map_label_animation` id below is the exact runtime payload value.",
              "", "## Clips", ""]
    readme.extend(f"- **{x['text']}** — `{x['label_animation']}` ({x['description']}) `{x['file']}`"
                  for x in manifest["clips"])
    (OUT / "README.md").write_text("\n".join(readme) + "\n", encoding="utf-8")
    print(f"[marker-comp] complete: {OUT}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
