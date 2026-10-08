#!/usr/bin/env python3
"""Publish the paired Dark Map/OpenCV map-motion choices.

The same five map and animation IDs are available from either renderer. The
previous ten map-image choices remain in the catalog as deprecated IDs for
clear retirement diagnostics; they are no longer selectable or resolvable.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

CATALOG = Path(__file__).resolve().parents[2] / "catalog/motion_catalog.v1.json"
REMOVE_AFTER = "2026-10-08"
LEGACY_IDS = {
    "map_image_australia_sunset_drift", "map_image_brazil_glow_reveal",
    "map_image_china_slow_reveal", "map_image_gujarat_detail_push",
    "map_image_india_contour_draw", "map_image_iran_gold_focus",
    "map_image_italy_beacon_arrival", "map_image_korea_pin_focus",
    "map_image_nigeria_neon_bloom", "map_image_usa_sweep_in",
}

def track(prop, keys, easing="in_out_sine"):
    return {"property": prop, "easing": easing,
            "keyframes": [{"frame": frame, "value": value} for frame, value in keys]}

SCENES = [
    ("italy", "radar_lock", 58, [(0, 1.24), (30, 1.10), (58, 1.0)], [(0, 0), (16, 1), (58, 1)]),
    ("japan", "archipelago_chain", 54, [(0, 1.20), (30, 1.06), (54, 1.0)], [(0, 0), (14, 1), (54, 1)]),
    ("russia", "continental_laser", 60, [(0, 1.18), (34, 1.04), (60, 1.0)], [(0, 0), (18, 1), (60, 1)]),
    ("germany", "industrial_nodes", 52, [(0, 1.22), (28, 1.05), (52, 1.0)], [(0, 0), (15, 1), (52, 1)]),
    ("saudi_arabia", "desert_pipeline", 56, [(0, 1.20), (32, 1.04), (56, 1.0)], [(0, 0), (17, 1), (56, 1)]),
]
RENDERERS = ("dark_map", "opencv")

def motion(renderer, scene):
    map_id, animation_id, enter, scale, opacity = scene
    return {
        "id": f"map_image_{renderer}_{map_id}_{animation_id}",
        "category": "map_image_v1",
        "targets": ["map_view"],
        "unit": "layer",
        "enter": enter,
        "exit": 14,
        "tracks": [track("scale", scale), track("opacity", opacity, "linear")],
        "duration_bounds": {"minimum_frames": 150, "maximum_frames": 150},
        "render_safe": True,
        "map_renderer": renderer,
        "map_id": map_id,
        "map_animation": animation_id,
    }

def active_motions():
    return [motion(renderer, scene) for scene in SCENES for renderer in RENDERERS]

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()
    data = json.loads(CATALOG.read_text())
    old = [m for m in data["motions"] if m.get("id") in LEGACY_IDS]
    if len(old) != len(LEGACY_IDS):
        raise SystemExit(f"expected {len(LEGACY_IDS)} legacy map motions, found {len(old)}")
    for item in old:
        item["deprecated"] = True
        item["remove_after"] = REMOVE_AFTER
        item["deprecation_note"] = "Replaced by the paired Dark Map and OpenCV country-animation options."
    wanted = active_motions()
    existing = {m["id"]: m for m in data["motions"] if m.get("category") == "map_image_v1" and not m.get("deprecated")}
    missing = [m for m in wanted if existing.get(m["id"]) != m]
    if args.check:
        if missing or len(existing) != len(wanted):
            raise SystemExit(f"map_image_v1 active set differs; missing or changed: {', '.join(m['id'] for m in missing)}")
        print("map_image_v1 catalog: 5 maps × 2 renderers, all motion pairs aligned")
        return
    data["motions"] = [m for m in data["motions"] if m.get("category") != "map_image_v1"]
    data["motions"].extend(old)
    data["motions"].extend(wanted)
    CATALOG.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")
    print("map_image_v1 catalog: 5 maps × 2 renderers; legacy options retained as deprecated")

if __name__ == "__main__":
    main()
