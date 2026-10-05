#!/usr/bin/env python3
"""Add the map-image motion family to the canonical ChrononTemplate catalog."""
from __future__ import annotations
import argparse, json
from pathlib import Path

CATALOG = Path(__file__).resolve().parents[1] / "catalog/motion_catalog.v1.json"

def t(prop, keys, easing="in_out_sine"):
    return {"property": prop, "easing": easing,
            "keyframes": [{"frame": f, "value": v} for f, v in keys]}

def motion(name, enter, scale, opacity, extra=()):
    tracks = [t("scale", scale), t("opacity", opacity, "linear"), *extra]
    return {"id": f"map_image_{name}", "category": "map_image_v1", "targets": ["image"],
            "unit": "layer", "enter": enter, "exit": 14, "tracks": tracks,
            "duration_bounds": {"minimum_frames": 48, "maximum_frames": 240}, "render_safe": True}

MOTIONS = [
    motion("brazil_glow_reveal", 54, [(0,1.24),(40,1.015),(54,1)], [(0,0),(18,1),(54,1)]),
    motion("usa_sweep_in", 48, [(0,1.34),(18,1.15),(36,1.025),(48,1)], [(0,0),(15,1),(48,1)]),
    motion("iran_gold_focus", 56, [(0,1.18),(38,1.025),(56,1)], [(0,0),(22,1),(56,1)]),
    motion("india_contour_draw", 52, [(0,1.22),(34,1.02),(52,1)], [(0,0),(17,1),(52,1)]),
    motion("gujarat_detail_push", 46, [(0,1.15),(28,1.025),(46,1)], [(0,0),(13,1),(46,1)]),
    motion("italy_beacon_arrival", 58, [(0,1.26),(42,1.02),(58,1)], [(0,0),(20,1),(58,1)]),
    motion("nigeria_neon_bloom", 50, [(0,1.20),(34,1.015),(50,1)], [(0,0),(12,1),(50,1)]),
    motion("china_slow_reveal", 64, [(0,1.16),(42,1.035),(64,1)], [(0,0),(24,1),(64,1)]),
    motion("korea_pin_focus", 44, [(0,1.28),(30,1.02),(44,1)], [(0,0),(12,1),(44,1)]),
    motion("australia_sunset_drift", 60, [(0,1.19),(42,1.025),(60,1)], [(0,0),(21,1),(60,1)]),
]

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--check",action="store_true"); args=ap.parse_args()
    data=json.loads(CATALOG.read_text())
    existing={x["id"]:x for x in data["motions"] if x.get("category")=="map_image_v1"}
    missing=[m for m in MOTIONS if existing.get(m["id"])!=m]
    if args.check:
        if missing: raise SystemExit("missing map motions: "+", ".join(m["id"] for m in missing))
        print("map_image_v1 catalog: 10/10 present")
        return
    data["motions"]=[m for m in data["motions"] if m.get("category")!="map_image_v1"]
    data["motions"].extend(MOTIONS)
    CATALOG.write_text(json.dumps(data,ensure_ascii=False,indent=2)+"\n")
    print(f"added {len(missing)} map_image_v1 motions")
if __name__=="__main__": main()
