#!/usr/bin/env python3
"""Pixel certification harness for the ChrononTemplate SVG parity tools.

Runs the C++ emitter (`svg_peak_parity_emitter`) and the C++ Blend2D renderer
(`render_svg_parity_blend2d`) against the SVG asset + scene preset and
certifies the primitives on rendered pixels. All expected values are derived
by an INDEPENDENT Python implementation of the scene contract (SVG parse,
framing, easing, arc-length sampling, camera) — never by calling into the C++
tools — so shared bugs cannot self-certify (SVG-06).

Tests:
  SVG-01  both tools run and produce artifacts
  SVG-02  RenderPlan V3 structurally valid + parity with the Python registry
  SVG-03  single source of truth: no scene coordinates in C++; perturbed
          SVG/preset drive plan and pixels without recompilation
  SVG-04  Trim Path 0->100%
  SVG-05  trim continuity across vertices (no holes, no out-of-place pixels)
  SVG-06  Follow Path: sun centroid vs independent sampler, <= 2 px
  SVG-07  timing variants (duration + easing) keep the sun on the line
  FX-08   camera pan + dolly: sun, line and checkpoints stay aligned
  SVG-08  invalid inputs give explicit errors, no crash
  INT-03  encoded video is 1920x1080, 30 fps, 150 frames, continuous PTS

Usage (from anywhere):
  python3 tools/vector_diagram/svg_peak_parity_pixel_tests.py \
      [--emitter PATH] [--renderer PATH] [--out DIR] \
      [--ffmpeg CMD] [--ffprobe CMD]
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
import re
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import numpy as np
from PIL import Image

TEMPLATE = Path(__file__).resolve().parents[2]
SVG = TEMPLATE / "tools" / "vector_diagram" / "assets" / "documentary_svg_peak_v1.svg"
PRESET = TEMPLATE / "catalog" / "documentary_svg_peak_v1.json"

RESULTS: list[tuple[str, str, str]] = []


def record(test_id: str, ok: bool, message: str) -> None:
    RESULTS.append((test_id, "PASS" if ok else "FAIL", message))
    print(f"[{'PASS' if ok else 'FAIL'}] {test_id}: {message}")


# ─────────────────────────── independent reference math ──────────────────────
# This block re-implements the documented scene contract in Python. It is the
# "independent sampler" demanded by SVG-06 and must never import or execute
# C++ code.

PATH_TOKENS = re.compile(r"[MLA-Za-z]|[-+]?(?:\d*\.\d+|\d+\.?)(?:[eE][-+]?\d+)?")


def parse_svg(path: Path):
    root = ET.parse(path).getroot()
    view_box = [float(v) for v in root.attrib.get("viewBox", "").replace(",", " ").split()]
    if len(view_box) != 4 or view_box[2] <= 0 or view_box[3] <= 0:
        raise ValueError("bad viewBox")
    points = None
    stroke = (232 / 255, 235 / 255, 240 / 255)
    stroke_width = 3.0
    circles = {}
    for node in root.iter():
        tag = node.tag.rsplit("}", 1)[-1]
        if tag == "path" and node.attrib.get("id") == "peak_line":
            tokens = PATH_TOKENS.findall(node.attrib.get("d", ""))
            pts = []
            expect = "M"
            i = 0
            while i < len(tokens):
                if tokens[i] in ("M", "L"):
                    expect = tokens[i]
                    i += 1
                elif tokens[i].isalpha():
                    raise ValueError(f"unsupported path command {tokens[i]}")
                if expect not in ("M", "L") or i + 1 >= len(tokens):
                    raise ValueError("bad path data")
                pts.append((float(tokens[i]), float(tokens[i + 1])))
                i += 2
                expect = "L"
            points = pts
            color = node.attrib.get("stroke", "")
            if color.startswith("#") and len(color) == 7:
                stroke = tuple(int(color[1 + 2 * c:3 + 2 * c], 16) / 255 for c in range(3))
            stroke_width = float(node.attrib.get("stroke-width", "3"))
        elif tag == "circle":
            circles[node.attrib.get("id", "")] = (
                float(node.attrib["cx"]), float(node.attrib["cy"]), float(node.attrib["r"]))
    if not points or len(points) < 2:
        raise ValueError("no #peak_line")
    return (view_box[2], view_box[3]), points, circles, stroke, stroke_width


def load_preset(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def easing(name: str, t: float) -> float:
    t = min(max(t, 0.0), 1.0)
    if name == "linear":
        return t
    if name == "in_quad":
        return t * t
    if name == "out_quad":
        return t * (2.0 - t)
    if name == "in_out_quad":
        return 2.0 * t * t if t < 0.5 else -1.0 + (4.0 - 2.0 * t) * t
    if name == "in_cubic":
        return t ** 3
    if name == "out_cubic":
        return 1.0 - (1.0 - t) ** 3
    if name == "in_out_cubic":
        return 4.0 * t ** 3 if t < 0.5 else 1.0 - (-2.0 * t + 2.0) ** 3 / 2.0
    if name == "in_sine":
        return 1.0 - math.cos(t * math.pi / 2)
    if name == "out_sine":
        return math.sin(t * math.pi / 2)
    if name == "in_out_sine":
        return -(math.cos(math.pi * t) - 1.0) / 2.0
    if name == "smoothstep":
        return t * t * (3.0 - 2.0 * t)
    raise ValueError(f"unknown easing {name}")


def track_value(keyframes, ease: str, frame: float) -> float:
    if frame <= keyframes[0][0]:
        return keyframes[0][1]
    if frame >= keyframes[-1][0]:
        return keyframes[-1][1]
    for (f0, v0), (f1, v1) in zip(keyframes, keyframes[1:]):
        if f0 <= frame <= f1:
            t = (frame - f0) / (f1 - f0) if f1 > f0 else 0.0
            return v0 + (v1 - v0) * easing(ease, t)
    return keyframes[-1][1]


def scene_geometry(svg: Path, preset: dict):
    """Canvas-space polyline + checkpoint centres, as the shared contract maps them."""
    (vb_w, vb_h), points, circles, stroke, stroke_width = parse_svg(svg)
    canvas = preset["canvas"]
    width, height = int(canvas["width"]), int(canvas["height"])
    scale = float(preset["framing"]["scale"])
    offset_x, offset_y = (float(v) for v in preset["framing"]["offset"])
    sx, sy = width / vb_w, height / vb_h

    def to_canvas(p):
        return (width / 2 + (p[0] * sx - width / 2) * scale + offset_x,
                height / 2 + (p[1] * sy - height / 2) * scale + offset_y)

    canvas_points = [to_canvas(p) for p in points]
    checkpoints = []
    for entry in preset.get("checkpoints", []):
        cx, cy, r = circles[entry["id"]]
        checkpoints.append({
            "id": entry["id"],
            "center": to_canvas((cx, cy)),
            "radius": r * (sx + sy) * 0.5 * scale,
            "start_frame": int(entry["start_frame"]),
        })
    return {
        "width": width, "height": height,
        "points": canvas_points, "checkpoints": checkpoints,
        "stroke": stroke, "stroke_width": stroke_width * sx * scale,
        "circles": circles,
    }


def sample_polyline(points, progress: float):
    if progress <= 0.0:
        return points[0]
    if progress >= 1.0:
        return points[-1]
    seg = [math.dist(a, b) for a, b in zip(points, points[1:])]
    total = sum(seg)
    remaining = progress * total
    for length, a, b in zip(seg, points, points[1:]):
        if remaining <= length:
            t = remaining / length if length else 0.0
            return (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)
        remaining -= length
    return points[-1]


def trim_polyline(points, progress: float):
    if progress <= 0.0:
        return []
    out = [points[0]]
    if progress >= 1.0:
        return out + points[1:]
    seg = [math.dist(a, b) for a, b in zip(points, points[1:])]
    remaining = progress * sum(seg)
    for length, a, b in zip(seg, points, points[1:]):
        if remaining >= length:
            out.append(b)
            remaining -= length
        elif remaining > 0.0:
            t = remaining / length
            out.append((a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t))
            break
        else:
            break
    return out


def camera_state(preset: dict, frame: float):
    cam = preset.get("camera", {})
    tracks = {t["property"]: t for t in cam.get("tracks", [])}

    def value(prop, default=0.0):
        t = tracks.get(prop)
        if not t:
            return default
        return track_value([(k["frame"], k["value"]) for k in t["keyframes"]],
                           t.get("easing", "linear"), frame)

    zoom = max(0.01, 1.0 + value("camera.position.z") / 1000.0)
    return value("camera.position.x"), value("camera.position.y"), zoom


def apply_camera(state, point, center):
    pan_x, pan_y, zoom = state
    return (center[0] + (point[0] - center[0]) * zoom + pan_x,
            center[1] + (point[1] - center[1]) * zoom + pan_y)


def distance_to_polyline(point, points) -> float:
    best = math.inf
    for a, b in zip(points, points[1:]):
        ax, ay = a
        bx, by = b
        dx, dy = bx - ax, by - ay
        seg = dx * dx + dy * dy
        if seg <= 0.0:
            best = min(best, math.dist(point, a))
            continue
        t = max(0.0, min(1.0, ((point[0] - ax) * dx + (point[1] - ay) * dy) / seg))
        best = min(best, math.dist(point, (ax + dx * t, ay + dy * t)))
    return best


def track(preset: dict, block: str, start_default=0):
    b = preset[block]
    return [(int(b["start_frame"]), 0.0), (int(b["end_frame"]),
             1.0 if block == "trim" else float(b["progress_end"]))], b.get("easing", "linear")


# ─────────────────────────────── pixel analysis ──────────────────────────────

def load_rgba(path: Path) -> np.ndarray:
    return np.asarray(Image.open(path).convert("RGBA"), dtype=np.int16)


def mask_line(arr: np.ndarray) -> np.ndarray:
    rgb = arr[:, :, :3]
    return (rgb.min(axis=2) > 120) & (rgb.max(axis=2) - rgb.min(axis=2) < 70)


def mask_sun(arr: np.ndarray) -> np.ndarray:
    r, g, b = arr[:, :, 0], arr[:, :, 1], arr[:, :, 2]
    return (r > 180) & (g > 130) & (b < 130)


def mask_red(arr: np.ndarray) -> np.ndarray:
    r, g, b = arr[:, :, 0], arr[:, :, 1], arr[:, :, 2]
    return (r > 170) & (g < 110) & (b < 120)


def centroid(mask: np.ndarray):
    ys, xs = np.nonzero(mask)
    if len(xs) == 0:
        return None
    return (float(xs.mean()) + 0.5, float(ys.mean()) + 0.5)


def polyline_samples(points, step: float = 2.0):
    samples = []
    for a, b in zip(points, points[1:]):
        length = math.dist(a, b)
        n = max(1, int(length / step))
        for i in range(n):
            t = i / n
            samples.append((a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t))
    samples.append(points[-1])
    return samples


def coverage(mask: np.ndarray, points, radius: float = 5.0, occluders=()) -> float:
    """Fraction of polyline samples that have a masked pixel within radius.

    `occluders` are (center, radius) zones where other scene elements (the
    sun marker, checkpoints) are drawn ON TOP of the line, so the line's
    pixels are legitimately hidden there.
    """
    if len(points) < 2:
        return 1.0
    ys, xs = np.nonzero(mask)
    if len(xs) == 0:
        return 0.0
    px = np.stack([xs + 0.5, ys + 0.5], axis=1)
    samples = [s for s in polyline_samples(points)
               if not any(math.dist(s, c) <= r for c, r in occluders)]
    if not samples:
        return 1.0
    hit = 0
    for s in samples:
        d = np.hypot(px[:, 0] - s[0], px[:, 1] - s[1]).min()
        if d <= radius:
            hit += 1
    return hit / len(samples)


def occluders_at(preset, geom, frame):
    """Zones where markers cover the line at this frame."""
    zones = []
    mkeys, mease = track(preset, "marker")
    if frame >= mkeys[0][0]:
        center = (geom["width"] / 2, geom["height"] / 2)
        cam = camera_state(preset, frame)
        world = sample_polyline(geom["points"], track_value(mkeys, mease, frame))
        radius = float(preset["marker"]["size"]) * 0.5 * cam[2]
        zones.append((apply_camera(cam, world, center), radius * 2.2 + 3.0))
        for checkpoint in geom["checkpoints"]:
            if frame >= checkpoint["start_frame"]:
                zones.append((apply_camera(cam, checkpoint["center"], center),
                              checkpoint["radius"] * 2.4 * cam[2] + 3.0))
    return zones


# ───────────────────────────────── process running ───────────────────────────

def run(cmd, cwd=None):
    proc = subprocess.run([str(c) for c in cmd], cwd=cwd, capture_output=True, text=True)
    return proc.returncode, proc.stdout, proc.stderr


def render(renderer, svg, preset, frames_dir: Path, atmosphere: str, cwd):
    frames_dir.mkdir(parents=True, exist_ok=True)
    code, out, err = run([renderer, frames_dir, "--svg", svg, "--preset", preset,
                          "--atmosphere", atmosphere], cwd=cwd)
    return code == 0, err or out


def frame_path(frames_dir: Path, frame: int) -> Path:
    return frames_dir / f"frame_{frame:04d}.png"


# ─────────────────────────────────── the tests ───────────────────────────────

def expected_sun(preset, geom, frame):
    keys, ease = track(preset, "marker")
    progress = track_value(keys, ease, frame)
    world = sample_polyline(geom["points"], progress)
    center = (geom["width"] / 2, geom["height"] / 2)
    return apply_camera(camera_state(preset, frame), world, center)


def expected_visible(preset, geom, frame):
    keys, ease = track(preset, "trim")
    progress = track_value(keys, ease, frame)
    visible = trim_polyline(geom["points"], progress)
    center = (geom["width"] / 2, geom["height"] / 2)
    cam = camera_state(preset, frame)
    return [apply_camera(cam, p, center) for p in visible]


def test_svg01(emitter, renderer, out: Path, cwd) -> Path:
    code_e, msg_e, err_e = run([emitter, "--help"], cwd=cwd)
    code_r, msg_r, err_r = run([renderer, "--help"], cwd=cwd)
    ok = code_e == 0 and code_r == 0
    record("SVG-01", ok, "both CMake-built targets respond (--help exit 0)"
           if ok else f"emitter exit {code_e}, renderer exit {code_r}: {err_e}{msg_e}{err_r}{msg_r}")
    plan_dir = out / "plan"
    code, _, err = run([emitter, plan_dir, "--svg", SVG, "--preset", PRESET], cwd=cwd)
    ok = code == 0 and (plan_dir / "documentary_svg_peak_v1.plan.json").is_file()
    record("SVG-01/emit", ok, "emitter writes the RenderPlan"
           if ok else f"emitter failed: {err}")
    return plan_dir


def test_svg02(plan_dir: Path) -> dict:
    plan = json.loads((plan_dir / "documentary_svg_peak_v1.plan.json").read_text())
    preset = load_preset(PRESET)
    geom = scene_geometry(SVG, preset)
    problems = []
    if plan.get("schema") != "chronon.render-plan.v3" or plan.get("version") != 3:
        problems.append("schema/version mismatch")
    canvas = plan.get("canvas", {})
    want = {"width": geom["width"], "height": geom["height"], "fps_num": 30,
            "fps_den": 1, "duration_frames": 150}
    for key, value in want.items():
        if canvas.get(key) != value:
            problems.append(f"canvas.{key}={canvas.get(key)} expected {value}")
    layers = {layer.get("id"): layer for layer in plan.get("layers", [])}
    for needed in ("background", "peak_svg", "yellow_marker"):
        if needed not in layers:
            problems.append(f"missing layer {needed}")
    svg_layer = layers.get("peak_svg", {})
    if svg_layer.get("shape", {}).get("asset") != SVG.name:
        problems.append("peak_svg asset name mismatch")
    op = svg_layer.get("shape", {}).get("operators", [{}])[0]
    anim = op.get("params", {}).get("animation", {})
    kfs = anim.get("keyframes", [])
    if op.get("kind") != "trim" or op.get("target") != "peak_line":
        problems.append("trim operator missing or mis-targeted")
    want_frames = [preset["trim"]["start_frame"], preset["trim"]["end_frame"]]
    if [k.get("frame") for k in kfs] != want_frames:
        problems.append(f"trim keyframes {[k.get('frame') for k in kfs]} != {want_frames}")
    marker = layers.get("yellow_marker", {})
    follow = marker.get("follow_path", {})
    cmds = follow.get("path_commands", [])
    if len(cmds) != len(geom["points"]):
        problems.append("follow_path command count mismatch")
    else:
        for cmd, (x, y) in zip(cmds, geom["points"]):
            if abs(cmd["point"][0] - x) > 1e-6 or abs(cmd["point"][1] - y) > 1e-6:
                problems.append("follow_path geometry deviates from the SVG mapping")
                break
    progress = follow.get("progress", {}).get("keyframes", [])
    want_progress = [0.0, float(preset["marker"]["progress_end"])]
    if [k.get("value") for k in progress] != want_progress:
        problems.append(f"marker progress {progress} != {want_progress}")

    # Parity with the Python registry (the CLI-validated generator).
    sys.path.insert(0, str(TEMPLATE / "tools" / "vector_diagram"))
    import documentary_svg_peak_registry as registry
    ref = registry.build_plan(registry.load_preset())
    if ref["canvas"] != plan["canvas"]:
        problems.append("canvas differs from the Python registry plan")
    ref_layers = {layer["id"]: layer for layer in ref["layers"]}
    ref_marker = ref_layers["yellow_marker"]
    if any(abs(a - b) > 1e-9 for a, b in zip(ref_marker["size"], marker["size"])):
        problems.append("marker size differs from the registry plan")
    if ref_marker["start_frame"] != marker["start_frame"] or \
       ref_marker["duration_frames"] != marker["duration_frames"]:
        problems.append("marker timing differs from the registry plan")
    if abs(ref_marker["follow_path"]["progress"]["keyframes"][1]["value"] -
           follow["progress"]["keyframes"][1]["value"]) > 1e-9:
        problems.append("marker progress differs from the registry plan")
    ref_cmds = ref_marker["follow_path"]["path_commands"]
    for ref_cmd, cmd in zip(ref_cmds, cmds):
        if any(abs(a - b) > 1e-9 for a, b in zip(ref_cmd["point"], cmd["point"])):
            problems.append("path commands differ from the registry plan")
            break
    record("SVG-02", not problems,
           "plan structurally valid and identical (semantically) to the Python registry plan"
           if not problems else "; ".join(problems))
    return plan


def test_svg03(emitter, renderer, out: Path, cwd) -> None:
    # Static: the scene's coordinates must not live in the C++ sources.
    literals = ["106.0", "219.0", "262.0", "304.0", "383.0", "458.0", "594.0", "706.0"]
    sources = ["svg_peak_scene.hpp", "svg_peak_parity_emitter.cpp",
               "render_svg_parity_blend2d.cpp"]
    leaks = []
    for name in sources:
        text = (TEMPLATE / "tools" / "vector_diagram" / name).read_text()
        for lit in literals:
            if lit in text:
                leaks.append(f"{name} contains {lit}")
    record("SVG-03/static", not leaks,
           "no scene coordinates duplicated in C++ sources"
           if not leaks else "; ".join(leaks))

    # Behavioural: a perturbed SVG + preset must move geometry and timing
    # without recompilation. Perturb the summit vertex by a known delta.
    var_dir = out / "variants"
    var_dir.mkdir(parents=True, exist_ok=True)
    base_geom = scene_geometry(SVG, load_preset(PRESET))
    peak_idx = min(range(len(base_geom["points"])),
                   key=lambda i: base_geom["points"][i][1])
    peak_svg = parse_svg(SVG)[1][peak_idx]
    old_vertex = f"L {peak_svg[0]:g} {peak_svg[1]:g}"
    new_vertex = f"L {peak_svg[0] + 40:g} {peak_svg[1] + 30:g}"
    svg_text = SVG.read_text()
    if old_vertex not in svg_text:
        record("SVG-03/runtime", False, f"cannot locate vertex '{old_vertex}' in the SVG")
        return
    svg_text = svg_text.replace(old_vertex, new_vertex)
    pert_svg = var_dir / "perturbed.svg"
    pert_svg.write_text(svg_text)
    preset = load_preset(PRESET)
    preset = copy.deepcopy(preset)
    preset["trim"]["start_frame"], preset["trim"]["end_frame"] = 20, 70
    preset["marker"]["start_frame"], preset["marker"]["end_frame"] = 20, 80
    preset["canvas"]["duration_frames"] = 100
    pert_preset = var_dir / "perturbed.json"
    pert_preset.write_text(json.dumps(preset))

    plan_dir = var_dir / "plan"
    code, _, err = run([emitter, plan_dir, "--svg", pert_svg, "--preset", pert_preset], cwd=cwd)
    problems = []
    if code != 0:
        problems.append(f"emitter failed on perturbed inputs: {err}")
    else:
        plan = json.loads((plan_dir / "documentary_svg_peak_v1.plan.json").read_text())
        geom = scene_geometry(pert_svg, preset)
        cmds = plan["layers"][2]["follow_path"]["path_commands"]
        moved = cmds[peak_idx]["point"]
        if abs(moved[0] - geom["points"][peak_idx][0]) > 1e-6 or abs(moved[1] - geom["points"][peak_idx][1]) > 1e-6:
            problems.append("plan geometry did not follow the perturbed SVG")
        if abs(moved[0] - (peak_svg[0] + 40)) > 1e-6 or abs(moved[1] - (peak_svg[1] + 30)) > 1e-6:
            problems.append(f"plan kept the old vertex (got {moved})")
        anim = plan["layers"][1]["shape"]["operators"][0]["params"]["animation"]
        if [k["frame"] for k in anim["keyframes"]] != [20, 70]:
            problems.append("plan timing did not follow the perturbed preset")

    frames_dir = var_dir / "frames"
    ok, msg = render(renderer, pert_svg, pert_preset, frames_dir, "off", cwd)
    if not ok:
        problems.append(f"renderer failed on perturbed inputs: {msg}")
    else:
        geom = scene_geometry(pert_svg, preset)
        for frame in (30, 55, 85):
            arr = load_rgba(frame_path(frames_dir, frame))
            got = centroid(mask_sun(arr))
            want = expected_sun(preset, geom, frame)
            if got is None or math.dist(got, want) > 2.5:
                problems.append(f"sun off the perturbed path at frame {frame}: {got} vs {want}")
    record("SVG-03/runtime", not problems,
           "perturbed SVG + preset drive plan and pixels without recompilation"
           if not problems else "; ".join(problems))


def test_trim_and_follow(preset, geom, frames_dir: Path) -> None:
    # SVG-04: Trim Path 0 -> 100%.
    keys, ease = track(preset, "trim")
    problems = []
    arr0 = load_rgba(frame_path(frames_dir, 0))
    if mask_line(arr0).sum() != 0:
        problems.append("line pixels exist before the trim starts")
    full = geom["points"]
    cov = {}
    for frame in (23, 33, 48, 60, 149):
        arr = load_rgba(frame_path(frames_dir, frame))
        cov[frame] = coverage(mask_line(arr), full,
                              occluders=occluders_at(preset, geom, frame))
    expected = {f: track_value(keys, ease, f) for f in (23, 33, 48, 60, 149)}
    for frame in (23, 33, 48):
        if abs(cov[frame] - expected[frame]) > 0.15:
            problems.append(f"trim coverage {cov[frame]:.2f} != expected {expected[frame]:.2f} at frame {frame}")
    if cov[149] < 0.95:
        problems.append(f"final coverage {cov[149]:.2f} < 0.95")
    if not (cov[23] < cov[33] < cov[48] < cov[60]):
        problems.append("trim coverage is not monotonic")
    record("SVG-04", not problems,
           "trim grows 0->100% with the declared timing"
           if not problems else "; ".join(problems))

    # SVG-05: continuity — no holes, no out-of-place pixels (frame 33).
    problems = []
    frame = 33
    arr = load_rgba(frame_path(frames_dir, frame))
    mask = mask_line(arr)
    visible = expected_visible(preset, geom, frame)
    occluders = occluders_at(preset, geom, frame)
    if len(visible) >= 2:
        for s in polyline_samples(visible):
            if any(math.dist(s, c) <= r for c, r in occluders):
                continue  # hidden under a marker, not a hole
            ys, xs = np.nonzero(mask)
            if len(xs) == 0:
                problems.append("no visible line at frame 33")
                break
            d = np.hypot(xs + 0.5 - s[0], ys + 0.5 - s[1]).min()
            if d > 5.0:
                problems.append(f"hole in the trim near ({s[0]:.0f},{s[1]:.0f})")
                break
        ys, xs = np.nonzero(mask)
        for x, y in zip(xs[:2000], ys[:2000]):
            if distance_to_polyline((x + 0.5, y + 0.5), visible) > 10.0:
                problems.append("line pixels outside the visible trim")
                break
    else:
        problems.append("expected visible trim is empty at frame 33")
    record("SVG-05", not problems,
           "trim is continuous across vertices with no stray segments"
           if not problems else "; ".join(problems))

    # SVG-06: Follow Path vs the independent sampler (<= 2 px).
    problems = []
    worst = 0.0
    mkeys, mease = track(preset, "marker")
    for frame in range(10, 150, 10):
        arr = load_rgba(frame_path(frames_dir, frame))
        got = centroid(mask_sun(arr))
        want = expected_sun(preset, geom, frame)
        if got is None:
            problems.append(f"no sun pixels at frame {frame}")
            break
        err = math.dist(got, want)
        worst = max(worst, err)
        if err > 2.0:
            problems.append(f"sun off the path by {err:.2f}px at frame {frame}")
            break
    record("SVG-06", not problems,
           f"sun centroid tracks the path within 2px (worst {worst:.2f}px)"
           if not problems else "; ".join(problems))


def test_svg07(renderer, out: Path, cwd, base_preset) -> None:
    variants = []
    a = copy.deepcopy(base_preset)
    a["canvas"]["duration_frames"] = 90
    a["trim"].update(start_frame=5, end_frame=40, easing="out_cubic")
    a["marker"].update(start_frame=5, end_frame=45, easing="out_cubic", progress_end=0.8)
    variants.append(("A_90f_out_cubic", a))
    b = copy.deepcopy(base_preset)
    b["canvas"]["duration_frames"] = 240
    b["trim"].update(start_frame=20, end_frame=140, easing="in_out_cubic")
    b["marker"].update(start_frame=20, end_frame=160, easing="in_out_cubic", progress_end=1.0)
    variants.append(("B_240f_in_out_cubic", b))

    problems = []
    for name, preset in variants:
        var_dir = out / "variants" / name
        preset_path = var_dir / "preset.json"
        var_dir.mkdir(parents=True, exist_ok=True)
        preset_path.write_text(json.dumps(preset))
        frames_dir = var_dir / "frames"
        ok, msg = render(renderer, SVG, preset_path, frames_dir, "off", cwd)
        if not ok:
            problems.append(f"{name}: render failed: {msg}")
            continue
        geom = scene_geometry(SVG, preset)
        frames = int(preset["canvas"]["duration_frames"])
        first = int(preset["marker"]["start_frame"]) + 2
        for frame in range(first, frames, 8):
            arr = load_rgba(frame_path(frames_dir, frame))
            got = centroid(mask_sun(arr))
            want = expected_sun(preset, geom, frame)
            if got is None or math.dist(got, want) > 2.5:
                err = None if got is None else math.dist(got, want)
                problems.append(f"{name}: sun off the line at frame {frame} (err {err})")
                break
    record("SVG-07", not problems,
           "duration + easing variants keep the sun on the line"
           if not problems else "; ".join(problems))


def test_fx08(renderer, out: Path, cwd, base_preset) -> None:
    preset = copy.deepcopy(base_preset)
    preset["checkpoints"] = [
        {"id": "red_rising_marker", "start_frame": 35},
        {"id": "red_peak_marker", "start_frame": 68},
    ]
    preset["camera"] = {"tracks": [
        {"property": "camera.position.x", "easing": "in_out_cubic",
         "keyframes": [{"frame": 0, "value": 0.0}, {"frame": 150, "value": 60.0}]},
        {"property": "camera.position.y", "easing": "in_out_cubic",
         "keyframes": [{"frame": 0, "value": 0.0}, {"frame": 150, "value": -30.0}]},
        {"property": "camera.position.z", "easing": "in_out_cubic",
         "keyframes": [{"frame": 0, "value": 0.0}, {"frame": 150, "value": 260.0}]},
    ]}
    var_dir = out / "variants" / "C_camera"
    var_dir.mkdir(parents=True, exist_ok=True)
    preset_path = var_dir / "preset.json"
    preset_path.write_text(json.dumps(preset))
    frames_dir = var_dir / "frames"
    problems = []
    ok, msg = render(renderer, SVG, preset_path, frames_dir, "off", cwd)
    if not ok:
        problems.append(f"render failed: {msg}")
    else:
        geom = scene_geometry(SVG, preset)
        center = (geom["width"] / 2, geom["height"] / 2)
        for frame in (10, 30, 50, 70, 90, 110, 130, 148):
            arr = load_rgba(frame_path(frames_dir, frame))
            cam = camera_state(preset, frame)
            # sun vs the camera-transformed path
            got = centroid(mask_sun(arr))
            want = expected_sun(preset, geom, frame)
            if got is None or math.dist(got, want) > 2.5:
                err = None if got is None else math.dist(got, want)
                problems.append(f"sun misaligned at frame {frame} (err {err})")
                break
            # line vs the camera-transformed trim (markers legitimately
            # cover the line where they sit on it)
            visible = expected_visible(preset, geom, frame)
            if coverage(mask_line(arr), visible, occluders=occluders_at(preset, geom, frame)) < 0.85:
                problems.append(f"line misaligned at frame {frame}")
                break
            # checkpoints vs their camera-transformed SVG centres
            if frame >= 35:
                red = mask_red(arr)
                ys, xs = np.nonzero(red)
                for checkpoint in geom["checkpoints"]:
                    if frame < checkpoint["start_frame"]:
                        continue
                    want_c = apply_camera(cam, checkpoint["center"], center)
                    if len(xs) == 0:
                        problems.append(f"no checkpoint pixels at frame {frame}")
                        break
                    d = np.hypot(xs + 0.5 - want_c[0], ys + 0.5 - want_c[1])
                    near = d <= 3.5 * checkpoint["radius"]
                    if not near.any():
                        problems.append(f"checkpoint {checkpoint['id']} missing at frame {frame}")
                        break
                    got_c = centroid(red & (np.hypot(
                        np.arange(arr.shape[1])[None, :] + 0.5 - want_c[0],
                        np.arange(arr.shape[0])[:, None] + 0.5 - want_c[1])
                        <= 3.5 * checkpoint["radius"]))
                    if got_c is None or math.dist(got_c, want_c) > 2.5:
                        err = None if got_c is None else math.dist(got_c, want_c)
                        problems.append(
                            f"checkpoint {checkpoint['id']} misaligned at frame {frame} (err {err})")
                        break
                if problems:
                    break
    record("FX-08", not problems,
           "sun, line and checkpoints share one camera transform (pan + dolly)"
           if not problems else "; ".join(problems))


def test_svg08(emitter, renderer, out: Path, cwd) -> None:
    var_dir = out / "variants" / "errors"
    var_dir.mkdir(parents=True, exist_ok=True)
    cases = []

    bad_svg = var_dir / "malformed.svg"
    bad_svg.write_text("this is not an svg")
    cases.append(("malformed SVG", emitter, bad_svg, PRESET))

    no_peak = var_dir / "no_peak.svg"
    no_peak.write_text(SVG.read_text().replace('id="peak_line"', 'id="other_line"'))
    cases.append(("missing #peak_line", emitter, no_peak, PRESET))

    curves = var_dir / "curves.svg"
    curves.write_text(SVG.read_text().replace(" L ", " C 1 2 3 4 5 6 ", 1))
    cases.append(("unsupported path command", emitter, curves, PRESET))

    preset = copy.deepcopy(load_preset(PRESET))
    del preset["trim"]
    broken_preset = var_dir / "broken_preset.json"
    broken_preset.write_text(json.dumps(preset))
    cases.append(("missing preset field", emitter, SVG, broken_preset))

    wobble = copy.deepcopy(load_preset(PRESET))
    wobble["trim"]["easing"] = "wobble"
    wobble_preset = var_dir / "wobble_preset.json"
    wobble_preset.write_text(json.dumps(wobble))
    cases.append(("unknown easing", emitter, SVG, wobble_preset))

    problems = []
    for name, tool, svg, preset_path in cases:
        code, out_text, err_text = run([tool, var_dir / "case_out", "--svg", svg,
                                        "--preset", preset_path], cwd=cwd)
        message = err_text + out_text
        if code == 0:
            problems.append(f"{name}: expected failure, got exit 0")
        elif "[ERROR]" not in message:
            problems.append(f"{name}: no explicit [ERROR] message")
        elif "stack" in message.lower() or "segmentation" in message.lower():
            problems.append(f"{name}: crashed instead of failing cleanly")
    record("SVG-08", not problems,
           "malformed SVG, missing path, unsupported geometry and bad presets fail explicitly"
           if not problems else "; ".join(problems))


def test_int03(hd_frames: Path, out: Path, ffmpeg: str | None, ffprobe: str | None) -> None:
    frames = sorted(hd_frames.glob("frame_*.png"))
    if len(frames) != 150:
        record("INT-03", False, f"expected 150 HD frames, found {len(frames)}")
        return
    if not ffmpeg or not ffprobe:
        record("INT-03", False, "ffmpeg/ffprobe unavailable; encoded video not verified")
        return
    mp4 = out / "documentary_svg_peak_blend2d.mp4"

    def as_tool_path(path: Path) -> str:
        # Windows ffmpeg.exe (GPU/NVENC) needs Windows paths even when the
        # harness runs under WSL.
        if ffmpeg.endswith(".exe"):
            converted = subprocess.run(["wslpath", "-w", str(path)],
                                       capture_output=True, text=True)
            if converted.returncode == 0:
                return converted.stdout.strip()
        return str(path)

    in_pattern = as_tool_path(hd_frames / "frame_%04d.png")
    mp4_arg = as_tool_path(mp4)
    code, _, err = run([ffmpeg, "-y", "-framerate", "30", "-i", in_pattern,
                        "-c:v", "h264_nvenc", "-pix_fmt", "yuv420p", mp4_arg])
    if code != 0:
        code, _, err = run([ffmpeg, "-y", "-framerate", "30", "-i", in_pattern,
                            "-c:v", "libx264", "-pix_fmt", "yuv420p", mp4_arg])
    if code != 0:
        record("INT-03", False, f"encode failed: {err}")
        return
    code, out_text, _ = run([ffprobe, "-v", "error", "-count_frames", "-select_streams", "v:0",
                             "-show_entries",
                             "stream=width,height,r_frame_rate,nb_read_frames", "-of", "json", mp4_arg])
    probe = json.loads(out_text)
    stream = probe["streams"][0]
    code2, pts_text, _ = run([ffprobe, "-v", "error", "-select_streams", "v:0",
                              "-show_entries", "packet=pts_time", "-of", "csv=p=0", mp4_arg])
    pts = sorted(float(line) for line in pts_text.split() if line.strip())
    continuous = (len(pts) == 150 and all(b > a for a, b in zip(pts, pts[1:]))
                  and all(b - a < 0.05 for a, b in zip(pts, pts[1:])))
    ok = (int(stream["width"]) == 1920 and int(stream["height"]) == 1080
          and stream["r_frame_rate"] == "30/1" and int(stream["nb_read_frames"]) == 150
          and continuous)
    record("INT-03", ok,
           f"mp4 {stream['width']}x{stream['height']} {stream['r_frame_rate']} "
           f"{stream['nb_read_frames']} frames, PTS continuous: {continuous}"
           if ok else f"probe mismatch: {stream}, continuous={continuous}")


# ──────────────────────────────────── main ───────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--emitter", type=Path,
                        default=TEMPLATE / "build" / "svg-parity" / "chronontemplate_svg_peak_parity_emitter")
    parser.add_argument("--renderer", type=Path,
                        default=TEMPLATE / "build" / "svg-parity" / "chronontemplate_render_svg_parity_blend2d")
    parser.add_argument("--out", type=Path, default=TEMPLATE / "out" / "svg_parity" / "cert")
    parser.add_argument("--ffmpeg", default=None)
    parser.add_argument("--ffprobe", default=None)
    parser.add_argument("--skip-hd", action="store_true")
    args = parser.parse_args()

    out: Path = args.out
    out.mkdir(parents=True, exist_ok=True)
    cwd = TEMPLATE

    if not args.emitter.is_file() or not args.renderer.is_file():
        record("SVG-01", False, f"built tools missing: {args.emitter}, {args.renderer}")
    else:
        plan_dir = test_svg01(args.emitter, args.renderer, out, cwd)
        test_svg02(plan_dir)
        test_svg03(args.emitter, args.renderer, out, cwd)

        # Canonical SD run (clean plate) for the primitive tests.
        sd_frames = out / "frames_sd"
        ok, msg = render(args.renderer, SVG, PRESET, sd_frames, "off", cwd)
        if not ok:
            record("SVG-04", False, f"canonical render failed: {msg}")
            record("SVG-05", False, "skipped")
            record("SVG-06", False, "skipped")
        else:
            preset = load_preset(PRESET)
            geom = scene_geometry(SVG, preset)
            test_trim_and_follow(preset, geom, sd_frames)

        test_svg07(args.renderer, out, cwd, load_preset(PRESET))
        test_fx08(args.renderer, out, cwd, load_preset(PRESET))
        test_svg08(args.emitter, args.renderer, out, cwd)

        if not args.skip_hd:
            hd_preset = TEMPLATE / "catalog" / "documentary_svg_peak_v1_hd.json"
            hd_frames = out / "frames_hd"
            ok, msg = render(args.renderer, SVG, hd_preset, hd_frames, "on", cwd)
            if not ok:
                record("INT-03", False, f"HD render failed: {msg}")
            else:
                # frame hashes for the certification record
                hashes = {}
                for frame in (0, 58, 149):
                    data = Image.open(frame_path(hd_frames, frame)).convert("RGBA").tobytes()
                    hashes[f"frame_{frame:04d}"] = hashlib.sha256(data).hexdigest()
                (out / "frame_hashes.json").write_text(json.dumps(hashes, indent=2) + "\n")
                for frame in (58, 149):
                    shutil.copy(frame_path(hd_frames, frame),
                                out / f"checkpoint_frame_{frame:04d}.png")
                test_int03(hd_frames, out, args.ffmpeg, args.ffprobe)

    log_lines = [f"{test_id}\t{status}\t{message}" for test_id, status, message in RESULTS]
    (out / "svg_parity_certification.log").write_text("\n".join(log_lines) + "\n")
    failed = [r for r in RESULTS if r[1] != "PASS"]
    print(f"\n{len(RESULTS) - len(failed)}/{len(RESULTS)} checks passed. "
          f"Log: {out / 'svg_parity_certification.log'}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
