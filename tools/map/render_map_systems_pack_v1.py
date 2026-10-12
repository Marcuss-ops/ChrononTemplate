#!/usr/bin/env python3
"""Render the 15 cartographic motion-graphic systems, one fixed camera.

Every clip uses the SAME camera animation (steady_hold, satellite basemap);
each clip shows a DIFFERENT real place with a DIFFERENT `map_animation`
system (the exact runtime payload value). Multi-pin systems (multi_locations,
route_line) use 2-3 real pins through the tour path. The standard rail is
suppressed for every system (label_animation=none proves the composition
owns all text).

Honest pack limits: photo_callout/info_card render compact (no photo asset
staged, never generated); info_card omits the counter row (no trusted
numeric source in this pack); region systems use the circular highlight.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
TEMPLATE = HERE.parents[1]
OUT = TEMPLATE / "out" / "map_systems_v1"
RENDERER = HERE / "render_dynamic_map_overlay.py"

CAMERA_ANIMATION = "steady_hold"
BASEMAP = "esri_sat"
STD_US = 5_000_000
# Multi-pin tours need a longer camera budget: the strict velocity gate
# reserves a 1.5 s terminal hold and each leg needs >= 1.8 s.

CLIPS = [
    ("01_simple_label",
     [{"id": "popolo", "label": "Piazza del Popolo", "latitude": 41.9109,
       "longitude": 12.4764, "scope": "city", "subtitle": "PIAZZA"}],
     "simple_label", "Pop point, trim line, dark panel + text."),
    ("02_region_zoom",
     [{"id": "aventino", "label": "Aventino", "latitude": 41.8885,
       "longitude": 12.4767, "scope": "city", "subtitle": "RIONE"}],
     "region_zoom", "Circular region highlight + outline sweep + name."),
    ("03_bracket_label",
     [{"id": "gazometro", "label": "Gazometro", "latitude": 41.8676,
       "longitude": 12.4754, "scope": "city", "subtitle": "INDUSTRIAL SITE"}],
     "bracket_label", "Corner brackets, text straight on the map."),
    ("04_photo_callout",
     [{"id": "maxxi", "label": "MAXXI", "latitude": 41.9287,
       "longitude": 12.4669, "scope": "city", "subtitle": "MUSEUM"}],
     "photo_callout", "Connector + card (compact: no photo asset staged)."),
    ("05_pulse_marker",
     [{"id": "termini", "label": "Stazione Termini", "latitude": 41.9010,
       "longitude": 12.5008, "scope": "city", "subtitle": "RAILWAY STATION"}],
     "pulse_marker", "Looping concentric rings + label."),
    ("06_multi_locations",
     [{"id": "ostia", "label": "Ostia", "latitude": 41.7596,
       "longitude": 12.2819, "scope": "city", "subtitle": "WIND",
       "category": "wind"},
      {"id": "tivoli", "label": "Tivoli", "latitude": 41.9634,
       "longitude": 12.8100, "scope": "city", "subtitle": "SOLAR",
       "category": "solar"},
      {"id": "fiumicino", "label": "Fiumicino", "latitude": 41.7714,
       "longitude": 12.2360, "scope": "city", "subtitle": "FOCUS",
       "category": "focus"}],
     "multi_locations", "Staggered pins, category colours, screen labels.",
     8_000_000),
    ("07_focus_title",
     [{"id": "colosseo", "label": "Colosseo", "latitude": 41.8902,
       "longitude": 12.4922, "scope": "city", "subtitle": "ANFITEATRO FLAVIO"}],
     "focus_title", "Region wash + giant screen-space title + accent line."),
    ("08_route_line",
     [{"id": "sanpietro", "label": "San Pietro", "latitude": 41.9022,
       "longitude": 12.4539, "scope": "city"},
      {"id": "colosseo2", "label": "Colosseo", "latitude": 41.8902,
       "longitude": 12.4922, "scope": "city"}],
     "route_line", "Dashed editorial curve + traveller + end labels.",
     6_500_000),
    ("09_spotlight",
     [{"id": "gianicolo", "label": "Gianicolo", "latitude": 41.8919,
       "longitude": 12.4444, "scope": "city", "subtitle": "BELVEDERE"}],
     "spotlight", "Darkened exterior, focus circle + label."),
    ("10_region_fill",
     [{"id": "acquedotti", "label": "Parco degli Acquedotti",
       "latitude": 41.8500, "longitude": 12.5050, "scope": "city",
       "subtitle": "PARCO REGIONALE"}],
     "region_fill", "Outline draw + progressive fill + marker + label."),
    ("11_info_card",
     [{"id": "eur", "label": "EUR", "latitude": 41.8337,
       "longitude": 12.4703, "scope": "city", "subtitle": "QUARTIERE",
       "location": "ROMA, IT"}],
     "info_card", "Stacked card (compact: no photo, no counter data)."),
    ("12_vertical_callout",
     [{"id": "venezia", "label": "Piazza Venezia", "latitude": 41.8963,
       "longitude": 12.4821, "scope": "city", "subtitle": "PIAZZA"}],
     "vertical_callout", "Vertical line + black panel above."),
    ("13_icon_label",
     [{"id": "soratte", "label": "Monte Soratte", "latitude": 41.7486,
       "longitude": 12.7098, "scope": "city", "subtitle": "WIND",
       "category": "wind"}],
     "icon_label", "Category circle + turbine glyph + panel."),
    ("14_label_reveal",
     [{"id": "navona", "label": "Piazza Navona", "latitude": 41.8989,
       "longitude": 12.4731, "scope": "city", "subtitle": "PIAZZA"}],
     "label_reveal", "Colour bar opens the dark panel rightward."),
    ("15_global_context",
     [{"id": "eur2", "label": "EUR", "latitude": 41.8337,
       "longitude": 12.4703, "scope": "city", "subtitle": "ROMA"}],
     "global_context", "Main map + stylized inset viewport schematic."),
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
        "title": "Chronon Map Systems Pack v1",
        "city": "Roma e Lazio, Italia",
        "camera_animation": CAMERA_ANIMATION,
        "label_animation": "none (every system owns its text)",
        "basemap": BASEMAP,
        "canvas": "1920x1080, 24 fps, 5 seconds",
        "limits": "photo_callout/info_card compact (no photo asset staged, "
                  "never generated); info_card omits the counter (no trusted "
                  "numeric source in this pack); region systems use the "
                  "circular highlight (no polygon dataset); the inset is a "
                  "stylized schematic, not a second real map.",
        "clips": [],
    }
    files = []
    for entry in CLIPS:
        slug, pins, map_animation, description = entry[:4]
        duration_us = entry[4] if len(entry) > 4 else STD_US
        print("[map-systems] rendering " + slug + " [" + map_animation + "]",
              flush=True)
        path = render_clip(slug, pins, map_animation, duration_us)
        files.append(path)
        manifest["clips"].append({"id": slug, "map_animation": map_animation,
                                  "pins": pins, "description": description,
                                  "duration_us": duration_us,
                                  "file": path.name})
    for path in files:
        still = OUT / (path.stem + ".jpg")
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-ss", "4.4",
                        "-i", str(path), "-frames:v", "1", "-q:v", "3",
                        str(still)], check=True)
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2),
                                       encoding="utf-8")
    lines = ["# Chronon Map Systems Pack v1", "",
             "Roma e Lazio - one fixed camera (steady_hold, satellite) for every clip.",
             "Each map_animation id below is the exact runtime payload value.",
             "", "## Clips", ""]
    for x in manifest["clips"]:
        lines.append("- **" + x["id"] + "** - `" + x["map_animation"] + "` (" +
                     x["description"] + ") `" + x["file"] + "`")
    (OUT / "README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("[map-systems] complete: " + str(OUT), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
