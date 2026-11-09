#!/usr/bin/env python3
"""Emit Chronon RenderPlan V3 documents for the Pillow-composed pages.

Each scene is a single screen-space image layer plus live shape overlays.  The
image-layer convention in this CLI is the same as shapes: `position` is an
offset from the canvas centre, so a full-frame page sits at [0, 0].  Overlay
rectangles are stored in page coordinates by make_newspaper_pages.py and are
converted here.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PAGES_DIR = ROOT / "assets" / "newspaper" / "pages"
W, H = 1920, 1080
FPS = 30


def track(prop: str, keys: list[tuple[int, float]],
          easing: str = "out_cubic") -> dict:
    return {
        "property": prop,
        "easing": easing,
        "keyframes": [{"frame": int(frame), "value": float(value)}
                      for frame, value in keys],
    }


def rect_layer(
    layer_id: str,
    rect: list[int],
    fill: list[float],
    duration: int,
    z: float,
    animation: dict | None = None,
) -> dict:
    x, y, w, h = rect
    layer = {
        "id": layer_id,
        "type": "shape",
        "enable_3d": True,
        "size": [float(w), float(h)],
        "position": [float(x + w / 2 - W / 2), float(y + h / 2 - H / 2), z],
        "screen_space": True,
        "start_frame": 0,
        "duration_frames": duration,
        "shape": {"type": "rect", "fill": fill},
    }
    if animation:
        layer["animation"] = animation
    return layer


def marker_layer(spec: dict, duration: int) -> dict:
    x, y, w, h = spec["rect"]
    px = x + w / 2 - W / 2
    py = y + h / 2 - H / 2
    delay = int(spec["delay"])
    span = int(spec["span"])
    end = delay + span
    animation = {"tracks": [
        track("opacity", [(0, 0.0), (delay, 0.0), (end, spec["peak"])],
              "in_out_cubic"),
        track("scale_x", [(0, 0.0), (delay, 0.0), (end, 1.0)],
              "in_out_cubic"),
        # position_x is an additive offset from the layer position, not an
        # absolute coordinate: end at zero so the band lands on its rect.
        track("position_x", [(0, -w / 2), (delay, -w / 2), (end, 0.0)],
              "in_out_cubic"),
    ]}
    return rect_layer(spec["id"], spec["rect"], [1.0, 0.886, 0.165, 1.0],
                      duration, 20.0, animation)


def redaction_layer(spec: dict, duration: int) -> dict:
    x, y, w, h = spec["rect"]
    px = x + w / 2 - W / 2
    py = y + h / 2 - H / 2
    delay = int(spec["delay"])
    end = delay + int(spec["span"])
    animation = {"tracks": [
        track("opacity", [(0, 0.0), (delay, 0.0), (end, 1.0)]),
        # Same additive convention: the bar slides up 14 px into place.
        track("position_y", [(0, 14.0), (delay, 14.0), (end, 0.0)],
              "out_cubic"),
    ]}
    return rect_layer(spec["id"], spec["rect"], [0.055, 0.052, 0.045, 0.97],
                      duration, 20.0, animation)


def make_plan(name: str, meta: dict) -> dict:
    duration = int(meta["duration"])
    layers: list[dict] = [{
        "id": "backdrop",
        "type": "color",
        "color": [0.055, 0.052, 0.045, 1.0],
        "size": [float(W), float(H)],
        "position": [0.0, 0.0],
        "screen_space": True,
        "start_frame": 0,
        "duration_frames": duration,
    }]

    image = {
        "id": "page",
        "type": "image",
        "asset": meta["asset"],
        "fit": "cover",
        "size": [float(W), float(H)],
        "position": [0.0, 0.0, 0.0],
        "enable_3d": True,
        "screen_space": True,
        "start_frame": 0,
        "duration_frames": duration,
        "animation": {"tracks": [
            track("opacity", [(0, 0.0), (10, 1.0)]),
            track("scale_x", [(0, 1.03), (36, 1.0)]),
            track("scale_y", [(0, 1.03), (36, 1.0)]),
            track("position_y", [(0, 8.0), (36, 0.0)]),
        ]},
    }
    layers.append(image)

    for spec in meta.get("markers", []):
        layers.append(marker_layer(spec, duration))
    for spec in meta.get("redactions", []):
        layers.append(redaction_layer(spec, duration))

    return {
        "schema": "chronon.render-plan.v3",
        "version": 3,
        "job_id": name,
        "canvas": {
            "width": W,
            "height": H,
            "fps_num": FPS,
            "fps_den": 1,
            "duration_frames": duration,
        },
        "layers": layers,
        "output": {
            "path": name + ".mp4",
            "format": "mp4",
            "codec": "h264",
        },
    }


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("usage: emit_newspaper_plans.py <out-dir>")
    out_dir = Path(sys.argv[1]).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    meta = json.loads((PAGES_DIR / "meta.json").read_text())
    for key, scene_meta in meta.items():
        plan = make_plan("newspaper_" + key, scene_meta)
        path = out_dir / f"newspaper_{key}.plan.json"
        path.write_text(json.dumps(plan, indent=2) + "\n")
        print(f"wrote {path}")


if __name__ == "__main__":
    main()
