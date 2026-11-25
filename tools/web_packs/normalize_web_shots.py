#!/usr/bin/env python3
"""Center and fit the native web-shot plans inside the 1920x1080 canvas.

The C++ WebShotsRebuild pack keeps the authored screenshot coordinates but
drops the perspective camera. Several shots therefore keep text at negative
X or extend past the right edge. This pass measures the real 2D content bbox,
moves its center to the canvas center and, only when needed, scales the whole
composition down to preserve a small safe margin.

Full-bleed color plates and full-width bars are intentionally left untouched:
they are page chrome, not content. All other layers, their size/font/path
geometry and their position keyframes are transformed together.
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any

CANVAS_W = 1920.0
CANVAS_H = 1080.0
DEFAULT_MARGIN = 40.0


def _size(layer: dict[str, Any]) -> tuple[float, float]:
    size = layer.get("size")
    if not isinstance(size, list) or len(size) < 2:
        return 0.0, 0.0
    return float(size[0]), float(size[1])


def _screen_center(layer: dict[str, Any]) -> tuple[float, float] | None:
    """Return the layer center in top-down screen coordinates."""
    position = layer.get("position")
    if not isinstance(position, list) or len(position) < 2:
        return None
    x, y = float(position[0]), float(position[1])
    kind = layer.get("type")
    if kind == "shape":
        # flattenLayersTo2d: absolute top-down [center_x, center_y]
        return x, y
    if kind == "text":
        # flattenLayersTo2d: [center_x, top_down_center_y]
        return x, y
    if kind == "image":
        # wireImagePos: [center_x - 960, 540 - center_y]
        return x + CANVAS_W * 0.5, CANVAS_H * 0.5 - y
    return None


def _is_page_chrome(layer: dict[str, Any]) -> bool:
    """Full-bleed plates and full-width bars should not move or shrink."""
    if layer.get("type") == "color":
        return True
    if layer.get("type") != "shape":
        return False
    width, height = _size(layer)
    return width >= CANVAS_W - 20.0 or height >= CANVAS_H - 20.0


def content_bbox(layers: list[dict[str, Any]]) -> tuple[float, float, float, float] | None:
    left = top = math.inf
    right = bottom = -math.inf
    for layer in layers:
        if _is_page_chrome(layer):
            continue
        center = _screen_center(layer)
        width, height = _size(layer)
        if center is None or width <= 0.0 or height <= 0.0:
            continue
        cx, cy = center
        left = min(left, cx - width * 0.5)
        right = max(right, cx + width * 0.5)
        top = min(top, cy - height * 0.5)
        bottom = max(bottom, cy + height * 0.5)
    if not math.isfinite(left):
        return None
    return left, top, right, bottom


def _scale_value(value: Any, scale: float) -> Any:
    if isinstance(value, (int, float)):
        return float(value) * scale
    return value


def _scale_tracks(tracks: Any, scale: float) -> None:
    if not isinstance(tracks, list):
        return
    for track in tracks:
        if not isinstance(track, dict):
            continue
        prop = track.get("property")
        if prop not in {"position_x", "position_y", "tracking"}:
            continue
        for key in track.get("keyframes", []):
            if isinstance(key, dict) and "value" in key:
                key["value"] = _scale_value(key["value"], scale)


def _scale_text_animators(animators: Any, scale: float) -> None:
    if not isinstance(animators, list):
        return
    for animator in animators:
        if isinstance(animator, dict):
            _scale_tracks(animator.get("properties"), scale)


def _scale_path(shape: dict[str, Any], scale: float) -> None:
    path = shape.get("path")
    if not isinstance(path, list):
        return
    for command in path:
        if not isinstance(command, dict):
            continue
        point = command.get("point")
        if isinstance(point, list) and len(point) >= 2:
            point[0] = _scale_value(point[0], scale)
            point[1] = _scale_value(point[1], scale)


def _scale_layer(layer: dict[str, Any], scale: float, new_cx: float, new_cy: float) -> None:
    kind = layer.get("type")
    width, height = _size(layer)
    if width > 0.0:
        layer["size"][0] = width * scale
    if height > 0.0:
        layer["size"][1] = height * scale

    if kind == "shape":
        layer["position"][0] = new_cx
        layer["position"][1] = new_cy
        shape = layer.get("shape")
        if isinstance(shape, dict):
            _scale_path(shape, scale)
    elif kind == "text":
        layer["position"][0] = new_cx
        layer["position"][1] = new_cy
        style = layer.get("style")
        if isinstance(style, dict) and "font_size" in style:
            style["font_size"] = _scale_value(style["font_size"], scale)
        _scale_text_animators(layer.get("text_animators"), scale)
    elif kind == "image":
        layer["position"][0] = new_cx - CANVAS_W * 0.5
        layer["position"][1] = CANVAS_H * 0.5 - new_cy

    _scale_tracks(layer.get("animation", {}).get("tracks"), scale)


def normalize_plan(plan: dict[str, Any], margin: float = DEFAULT_MARGIN) -> dict[str, Any]:
    """Center and fit one plan in place; returns the same plan for convenience."""
    layers = plan.get("layers")
    if not isinstance(layers, list) or not layers:
        return plan
    bbox = content_bbox(layers)
    if bbox is None:
        return plan
    left, top, right, bottom = bbox
    width = max(1.0, right - left)
    height = max(1.0, bottom - top)
    target_w = max(1.0, CANVAS_W - 2.0 * margin)
    target_h = max(1.0, CANVAS_H - 2.0 * margin)
    scale = min(1.0, target_w / width, target_h / height)
    center_x = (left + right) * 0.5
    center_y = (top + bottom) * 0.5

    for layer in layers:
        if _is_page_chrome(layer):
            continue
        center = _screen_center(layer)
        if center is None:
            continue
        cx, cy = center
        new_cx = CANVAS_W * 0.5 + (cx - center_x) * scale
        new_cy = CANVAS_H * 0.5 + (cy - center_y) * scale
        _scale_layer(layer, scale, new_cx, new_cy)
    return plan


def normalize_file(path: Path, margin: float = DEFAULT_MARGIN) -> bool:
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("external"):
        return False
    before = json.dumps(data, sort_keys=True)
    normalize_plan(data, margin)
    after = json.dumps(data, sort_keys=True)
    if before == after:
        return False
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("plans", type=Path, help="directory containing *.plan.json")
    parser.add_argument("--margin", type=float, default=DEFAULT_MARGIN)
    args = parser.parse_args()
    changed = 0
    for path in sorted(args.plans.glob("*.plan.json")):
        if normalize_file(path, args.margin):
            changed += 1
            print(f"[center] {path.name}")
    print(f"[center] changed={changed}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
