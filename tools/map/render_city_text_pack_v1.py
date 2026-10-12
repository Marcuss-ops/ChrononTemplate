#!/usr/bin/env python3
"""Render one fixed map camera with many city-referred label texts.

Every clip uses the SAME camera animation (steady_hold, satellite basemap)
and a DIFFERENT real place of Rome with a DIFFERENT certified label
animation, so the text treatments can be compared one-to-one.
Covers all 14 certified label animations (the 10 calm fades plus
diffuse_city_beacon, rise_up, pop_in and soft_tracking).
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
TEMPLATE = HERE.parents[1]
OUT = TEMPLATE / "out" / "map_city_texts_v1"
RENDERER = HERE / "render_dynamic_map_overlay.py"

CAMERA_ANIMATION = "steady_hold"
BASEMAP = "esri_sat"

# (slug, label text, latitude, longitude, label_animation)
PLACES = [
    ("01_colosseo", "Colosseo", 41.8902, 12.4922, "gentle_fade"),
    ("02_fori_imperiali", "Fori Imperiali", 41.8925, 12.4853, "soft_glow"),
    ("03_pantheon", "Pantheon", 41.8986, 12.4769, "clean_fade"),
    ("04_piazza_navona", "Piazza Navona", 41.8992, 12.4731, "word_soft_fade"),
    ("05_fontana_trevi", "Fontana di Trevi", 41.9009, 12.4833, "slow_fade"),
    ("06_piazza_spagna", "Piazza di Spagna", 41.9058, 12.4823, "quiet_bloom"),
    ("07_castel_santangelo", "Castel Sant'Angelo", 41.9031, 12.4663, "quick_fade"),
    ("08_san_pietro", "San Pietro", 41.9022, 12.4539, "silky_fade"),
    ("09_trastevere", "Trastevere", 41.8897, 12.4697, "subtle_halo"),
    ("10_circo_massimo", "Circo Massimo", 41.8859, 12.4855, "cinematic_fade"),
    ("11_altare_patria", "Altare della Patria", 41.8957, 12.4848, "diffuse_city_beacon"),
    ("12_villa_borghese", "Villa Borghese", 41.9142, 12.4921, "rise_up"),
    ("13_terme_caracalla", "Terme di Caracalla", 41.8791, 12.4933, "pop_in"),
    ("14_bocca_verita", "Bocca della Verita", 41.8881, 12.4817, "soft_tracking"),
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
        "title": "Chronon Map City Texts Pack v1",
        "city": "Roma, Italia",
        "camera_animation": CAMERA_ANIMATION,
        "basemap": BASEMAP,
        "canvas": "1920x1080, 24 fps, 5 seconds",
        "note": "One fixed camera for every clip; only the place text and "
                "its label animation change, so treatments compare one-to-one.",
        "clips": [],
    }
    files: list[Path] = []
    for slug, label, lat, lon, label_animation in PLACES:
        print(f"[city-texts] rendering {label} [{label_animation}]", flush=True)
        path = render_place(slug, label, lat, lon, label_animation)
        files.append(path)
        manifest["clips"].append({"id": slug, "text": label,
                                  "latitude": lat, "longitude": lon,
                                  "label_animation": label_animation,
                                  "file": path.name})
    for path in files:
        still = OUT / f"{path.stem}.jpg"
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-ss", "4.4",
                        "-i", str(path), "-frames:v", "1", "-q:v", "3",
                        str(still)], check=True)
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2),
                                       encoding="utf-8")
    readme = ["# Chronon Map City Texts Pack v1", "",
              "Roma, Italia — one fixed camera (`steady_hold`, satellite) for every clip.",
              "Only the place text and its certified label animation change.",
              "Each `map_label_animation` id below is the exact runtime payload value.",
              "", "## Clips", ""]
    readme.extend(f"- **{x['text']}** — `{x['label_animation']}` `{x['file']}`"
                  for x in manifest["clips"])
    (OUT / "README.md").write_text("\n".join(readme) + "\n", encoding="utf-8")
    print(f"[city-texts] complete: {OUT}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
