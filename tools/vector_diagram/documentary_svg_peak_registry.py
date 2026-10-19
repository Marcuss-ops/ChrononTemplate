"""Registry resolver and RenderPlan builder for documentary SVG graph scenes."""
from __future__ import annotations

import json
import math
import re
import xml.etree.ElementTree as ET
from pathlib import Path

TEMPLATE = Path(__file__).resolve().parents[2]
CATALOG = TEMPLATE / "catalog" / "documentary_svg_peak_v1.json"
_PATH_TOKENS = re.compile(r"[ML]|[-+]?(?:\d*\.\d+|\d+\.?)(?:[eE][-+]?\d+)?")


def load_preset(preset_id: str = "documentary_svg_peak_v1") -> dict:
    catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
    if catalog.get("schema") != "chronontemplate.svg_scene_catalog.v1":
        raise ValueError("unsupported SVG scene catalog schema")
    if catalog.get("id") != preset_id:
        raise KeyError(f"unknown documentary SVG preset: {preset_id}")
    return catalog


def _svg_points(svg_path: Path) -> tuple[list[tuple[float, float]], tuple[float, float]]:
    root = ET.parse(svg_path).getroot()
    view_box = [float(v) for v in root.attrib.get("viewBox", "").replace(",", " ").split()]
    if len(view_box) != 4 or view_box[2] <= 0 or view_box[3] <= 0:
        raise ValueError("documentary SVG needs a positive four-value viewBox")
    paths = [node for node in root.iter()
             if node.tag.rsplit("}", 1)[-1] == "path"
             and node.attrib.get("id") == "peak_line"]
    if len(paths) != 1:
        raise ValueError("documentary SVG must contain exactly one #peak_line path")
    path_data = paths[0].attrib.get("d", "")
    tokens = _PATH_TOKENS.findall(path_data)
    if _PATH_TOKENS.sub("", path_data).strip(" ,\t\r\n"):
        raise ValueError("#peak_line uses unsupported SVG path syntax; only M/L is accepted")
    points: list[tuple[float, float]] = []
    index = 0
    command = None
    x = y = 0.0
    while index < len(tokens):
        if tokens[index] in {"M", "L"}:
            command = tokens[index]
            index += 1
        if command not in {"M", "L"} or index + 1 >= len(tokens):
            raise ValueError("#peak_line supports only explicit M/L coordinates")
        x, y = float(tokens[index]), float(tokens[index + 1])
        points.append((x, y))
        index += 2
        command = "L"  # SVG allows repeated coordinate pairs after M.
    if len(points) < 2:
        raise ValueError("#peak_line needs at least two points")
    points = [(x - view_box[0], y - view_box[1]) for x, y in points]
    return points, (view_box[2], view_box[3])


def build_plan(preset: dict | None = None) -> dict:
    preset = preset or load_preset()
    canvas = preset["canvas"]
    width, height = int(canvas["width"]), int(canvas["height"])
    fps, frames = int(canvas["fps"]), int(canvas["duration_frames"])
    if min(width, height, fps, frames) <= 0:
        raise ValueError("canvas dimensions, fps, and duration must be positive")
    asset = (TEMPLATE / preset["asset"]).resolve()
    if not asset.is_relative_to(TEMPLATE.resolve()) or not asset.is_file():
        raise ValueError("SVG asset must resolve to an existing ChrononTemplate file")
    source_points, viewbox = _svg_points(asset)
    framing = preset["framing"]
    scale = float(framing["scale"])
    offset_x, offset_y = map(float, framing["offset"])
    if (not math.isfinite(scale) or not 0.01 <= scale <= 100 or
            not all(map(math.isfinite, (offset_x, offset_y))) or
            max(abs(offset_x), abs(offset_y)) > 100000):
        raise ValueError("framing scale/offset is outside supported bounds")
    sx, sy = width / viewbox[0], height / viewbox[1]
    points = []
    for x, y in source_points:
        screen_x = x * sx
        screen_y = y * sy
        points.append([
            width / 2 + (screen_x - width / 2) * scale + offset_x,
            height / 2 + (screen_y - height / 2) * scale + offset_y,
        ])
    commands = ([{"type": "move_to", "point": points[0]}] +
                [{"type": "line_to", "point": point} for point in points[1:]])

    trim = preset["trim"]
    trim_start, trim_end = int(trim["start_frame"]), int(trim["end_frame"])
    marker = preset["marker"]
    marker_start, marker_end = int(marker["start_frame"]), int(marker["end_frame"])
    if not (0 <= trim_start < trim_end < frames and
            0 <= marker_start < marker_end < frames):
        raise ValueError("trim and marker keyframes must fit within the canvas duration")
    marker_progress = float(marker["progress_end"])
    if not 0.0 <= marker_progress <= 1.0:
        raise ValueError("marker progress_end must be within [0,1]")
    marker_size = float(marker["size"])
    if not math.isfinite(marker_size) or not 0.5 <= marker_size <= 512:
        raise ValueError("marker size must be within [0.5,512]")
    marker_fill = list(map(float, marker["fill"]))
    if len(marker_fill) != 4 or not all(
            math.isfinite(value) and 0.0 <= value <= 1.0 for value in marker_fill):
        raise ValueError("marker fill must be four normalized RGBA values")

    # The imported SVG viewBox is already mapped into the canvas-centered
    # local coordinate system. Keep the layer at the origin and express
    # framing offsets in screen coordinates while layer Y points upward.
    svg = {"id": "peak_svg", "type": "shape", "position": [offset_x, -offset_y],
           "size": [width * scale, height * scale],
           "start_frame": 0, "duration_frames": frames,
           "shape": {"type": "path", "asset": Path(preset["asset"]).name,
                     "operators": [{"kind": "trim", "target": "peak_line", "params": {
                         "start": 0, "end": 0,
                         "animation": {"easing": "linear", "keyframes": [
                             {"frame": trim_start, "value": [0, 0]},
                             {"frame": trim_end, "value": [0, 1]}]}}}]}}
    marker_layer = {
        "id": marker["id"], "type": "shape", "position": [0, 0],
        "size": [marker_size, marker_size],
        "start_frame": marker_start, "duration_frames": frames - marker_start,
        "shape": {"type": "ellipse", "fill": marker_fill},
        "follow_path": {"path_commands": commands,
            "progress": {"easing": "linear", "keyframes": [
                {"frame": marker_start, "value": 0.0},
                {"frame": marker_end, "value": marker_progress}]},
            "auto_orient": False, "clamp_end": True},
    }
    glow = marker.get("glow", {})
    if glow.get("enabled"):
        radius, intensity = float(glow["radius"]), float(glow["intensity"])
        if not 0 <= radius <= 256 or not 0 <= intensity <= 4:
            raise ValueError("marker glow is outside supported bounds")
        marker_layer["effects"] = [{"type": "glow", "radius": radius,
            "intensity": intensity, "color": glow["color"]}]

    bg = {"id": "background", "type": "color", "color": canvas["background"],
          "size": [width, height], "position": [0, 0], "start_frame": 0,
          "duration_frames": frames}
    return {"schema": "chronon.render-plan.v3", "version": 3,
            "job_id": preset["id"],
            "canvas": {"width": width, "height": height, "fps_num": fps,
                       "fps_den": 1, "duration_frames": frames},
            "layers": [bg, svg, marker_layer],
            "output": {"path": f"{preset['id']}.mp4", "format": "mp4"}}
