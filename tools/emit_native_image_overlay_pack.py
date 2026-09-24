#!/usr/bin/env python3
"""Emit the Overlay V3 image motion pack directly for Chronon3D.

This is the pre-RenderingGen canary path: the catalog is read from
ChrononTemplate and lowered straight to chronon.render-plan.v2, so image
motion support is proven at the renderer boundary before any Go integration.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def keyframes(track: dict[str, Any], duration: int) -> list[dict[str, Any]]:
    source = track.get("keyframes", [])
    values = [{"frame": int(k["frame"]), "value": k["value"]} for k in source]
    if not values:
        return []
    hold = max(values[-1]["frame"], duration - 9)
    end = duration - 1
    out = [k for k in values if k["frame"] < hold]
    if not out or out[-1]["frame"] != hold:
        out.append({"frame": hold, "value": values[-1]["value"]})
    if end > hold:
        out.append({"frame": end, "value": values[0]["value"]})
    return out


def make_plan(motion: dict[str, Any], duration: int) -> dict[str, Any]:
    tracks = [
        {"property": t["property"], "keyframes": keyframes(t, duration), "easing": t.get("easing", "linear")}
        for t in motion.get("tracks", [])
    ]
    return {
        "schema": "chronon.render-plan.v2",
        "version": 2,
        "job_id": f"chronontemplate_native_{motion['id']}",
        "canvas": {"width": 1920, "height": 1080, "fps_num": 24, "fps_den": 1, "duration_frames": duration},
        "layers": [
            {"id": "background", "type": "color", "color": [0.04, 0.05, 0.08, 1.0], "size": [1920, 1080], "start_frame": 0, "duration_frames": duration},
            {"id": "image", "type": "image", "asset": "assets/test_image.png", "size": [720, 720], "position": [960, 540], "fit": "contain", "start_frame": 0, "duration_frames": duration, "animation": {"tracks": tracks}},
        ],
        "output": {"path": f"{motion['id']}.mp4", "format": "mp4", "codec": "h264"},
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--catalog", type=Path, default=Path("ChrononTemplate/catalog/motion_catalog.v1.json"))
    parser.add_argument("--out", type=Path, default=Path("ChrononTemplate/out/overlay_v3_image_pack_v1"))
    parser.add_argument("--duration", type=int, default=120)
    args = parser.parse_args()
    catalog = json.loads(args.catalog.read_text())
    motions = [m for m in catalog["motions"] if m.get("category") == "overlay_v3_image"]
    if len(motions) != 10:
        raise SystemExit(f"expected 10 Overlay V3 image motions, got {len(motions)}")
    args.out.mkdir(parents=True, exist_ok=True)
    manifest = {"source": str(args.catalog), "pipeline": "ChrononTemplate -> Chronon3D native image render-plan", "motions": []}
    for motion in motions:
        destination = args.out / f"{motion['id']}.plan.json"
        destination.write_text(json.dumps(make_plan(motion, args.duration), indent=2) + "\n")
        manifest["motions"].append({"id": motion["id"], "plan": destination.name})
    (args.out / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"emitted {len(motions)} native image plans in {args.out}")


if __name__ == "__main__":
    main()
