#!/usr/bin/env python3
"""scene_camera_sequencer_v1 — render the SceneCameraPack gallery.

Runs the native pose dumper (applySceneCameraSequence on real TemplateScene
rigs), lowers the per-frame camera channels into chronon.render-plan.v3
plans, and renders them through the Chronon3D software lane. The subjects
(phrase → image → text) never animate: only the camera moves, from stacco to
stacco, exactly as the pack authored it.

Usage:
  render_scene_camera_sequencer_v1.py                # plans + renders
  render_scene_camera_sequencer_v1.py --generate-only
"""

from __future__ import annotations

import argparse
import json
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WORKSPACE = ROOT.parent
POSE_DUMPER = ROOT / "build/dev/chronontemplate_dump_scene_camera_poses"
SEQUENCE_TOOL = ROOT / "build/dev/chronontemplate_sequence_from_json"
CLI = (WORKSPACE / "Chronon3d/build/chronon/linux-video-fast-dev/apps/chronon3d_cli/chronon3d_cli").resolve()
ASSETS = (WORKSPACE / "Chronon3d").resolve()
OUT = ROOT / "out/scene_camera_sequencer_v1"

WIDTH, HEIGHT, FPS = 1920, 1080, 30
PROPERTIES = ["camera_position_x", "camera_position_y", "camera_position_z",
              "camera_rotation_x", "camera_rotation_y", "camera_rotation_z", "camera_fov_deg"]


def sampled_poses() -> dict[str, list[list[float]]]:
    """Run the dumper and parse `seq_id total` + `frame px py pz rx ry rz fov focus` rows."""
    raw = subprocess.run([str(POSE_DUMPER)], check=True, capture_output=True, text=True).stdout
    sequences: dict[str, list[list[float]]] = {}
    current: str | None = None
    for line in raw.splitlines():
        parts = line.split()
        if len(parts) == 2 and parts[1].isdigit():
            current = parts[0]
            sequences[current] = []
            continue
        if current and len(parts) >= 8 and parts[0].isdigit():
            sequences[current].append([float(p) for p in parts[:8]])
    return sequences


def unwrap_degrees(values: list[float]) -> list[float]:
    result = [values[0]]
    for angle in values[1:]:
        prev = result[-1]
        while angle - prev > 180:
            angle -= 360
        while angle - prev < -180:
            angle += 360
        result.append(angle)
    return result


def track(prop: str, values: list[float]) -> dict:
    return {"property": prop, "easing": "linear",
            "keyframes": [{"frame": i, "value": round(v, 6)} for i, v in enumerate(values)]}


def caption_for(seq_id: str) -> str:
    return seq_id.replace("_", " ").upper()


def plan_for(seq_id: str, rows: list[list[float]], master: bool) -> dict:
    total = len(rows)
    channels = list(zip(*[r[1:] for r in rows]))
    channels = [list(channels[0]), list(channels[1]), list(channels[2]),
                *[unwrap_degrees(list(c)) for c in channels[3:6]], list(channels[6])]
    # ChrononTemplate authors camera poses in canvas coordinates (centre at
    # 960,540, z forward); render-plan 3D layers are centre-relative and use
    # the renderer's -Z camera convention.
    channels[0] = [x - WIDTH / 2 for x in channels[0]]
    channels[1] = [y - HEIGHT / 2 for y in channels[1]]
    channels[2] = [-z for z in channels[2]]

    background = {"id": "background", "type": "color", "color": [0.018, 0.028, 0.033, 1],
                  "size": [WIDTH, HEIGHT], "screen_space": True, "start_frame": 0,
                  "duration_frames": total}
    if master:
        subjects = [
            {"id": "hero-phrase", "type": "text", "text": "TUTTO COMINCIA DA UN LUOGO",
             "size": [1420, 170], "position": [960, 540, 0], "start_frame": 0,
             "duration_frames": total, "enable_3d": True,
             "style": {"font": "assets/fonts/Inter-Bold.ttf", "font_size": 84,
                       "fill": "#F2F0E8", "fit_mode": "shrink_only", "min_font_size": 40,
                       "max_font_size": 84}},
            {"id": "hero-image", "type": "image",
             "asset": "assets/images/camera_reference.jpg", "size": [920, 520],
             "position": [960, 540, 0], "fit": "contain", "start_frame": 0,
             "duration_frames": total, "enable_3d": True},
            {"id": "hero-quote", "type": "text", "text": "IL CORAGGIO DI CAMBIARE",
             "size": [1240, 150], "position": [960, 540, 0], "start_frame": 0,
             "duration_frames": total, "enable_3d": True,
             "style": {"font": "assets/fonts/Inter-Bold.ttf", "font_size": 72,
                       "fill": "#92B4A6", "fit_mode": "shrink_only", "min_font_size": 36,
                       "max_font_size": 72}},
            {"id": "hero-card", "type": "shape", "size": [920, 520],
             "position": [960, 540, 0], "start_frame": 0, "duration_frames": total,
             "enable_3d": True,
             "shape": {"type": "rounded_rect", "radius": 18,
                       "fill": [0.063, 0.094, 0.125, 1.0],
                       "stroke": {"color": "#4AB5FA", "width": 2}}},
            {"id": "hero-title", "type": "text", "text": "E FINISCE COME UNA DOMANDA",
             "size": [1500, 190], "position": [960, 540, 0], "start_frame": 0,
             "duration_frames": total, "enable_3d": True,
             "style": {"font": "assets/fonts/Inter-Bold.ttf", "font_size": 108,
                       "fill": "#F2F0E8", "fit_mode": "shrink_only", "min_font_size": 44,
                       "max_font_size": 108}},
        ]
    else:
        subjects = [
            {"id": "hero-phrase", "type": "text", "text": "LA STORIA COMINCIA QUI",
             "size": [1420, 170], "position": [960, 540, 0], "start_frame": 0,
             "duration_frames": total, "enable_3d": True,
             "style": {"font": "assets/fonts/Inter-Bold.ttf", "font_size": 96,
                       "fill": "#F2F0E8", "fit_mode": "shrink_only", "min_font_size": 44,
                       "max_font_size": 96}},
            {"id": "hero-image", "type": "image",
             "asset": "assets/images/camera_reference.jpg", "size": [920, 520],
             "position": [960, 540, 0], "fit": "contain", "start_frame": 0,
             "duration_frames": total, "enable_3d": True},
            {"id": "hero-title", "type": "text", "text": "IL SECONDO ATTO",
             "size": [1240, 200], "position": [960, 540, 0], "start_frame": 0,
             "duration_frames": total, "enable_3d": True,
             "style": {"font": "assets/fonts/Inter-Bold.ttf", "font_size": 120,
                       "fill": "#F2F0E8", "fit_mode": "shrink_only", "min_font_size": 54,
                       "max_font_size": 120}},
        ]
    caption = {"id": "move-caption", "type": "text", "text": caption_for(seq_id),
               "size": [1100, 54], "position": [960, 880, 0], "start_frame": 0,
               "duration_frames": total, "enable_3d": True,
               "style": {"font": "assets/fonts/Inter-Bold.ttf", "font_size": 26,
                         "fill": "#92B4A6", "fit_mode": "shrink_only", "min_font_size": 20,
                         "max_font_size": 26}}
    return {"schema": "chronon.render-plan.v3", "version": 3,
            "job_id": f"scene_camera_sequencer_v1_{seq_id}",
            "canvas": {"width": WIDTH, "height": HEIGHT, "fps_num": FPS, "fps_den": 1,
                       "duration_frames": total},
            "camera": {"type": "perspective",
                       "position": [round(channels[i][0], 6) for i in range(3)],
                       "rotation_deg": [round(x, 6) for x in rows[0][4:7]],
                       "fov_deg": round(rows[0][7], 6), "near": 1, "far": 10000, "zoom": 1},
            "camera_animation": {"tracks": [track(p, c) for p, c in zip(PROPERTIES, channels)]},
            "layers": [background, *subjects, caption],
            "output": {"path": f"{seq_id}.mp4", "format": "mp4", "codec": "h264"}}


def hex_to_rgba(value: str) -> list[float]:
    value = value.lstrip("#")
    return [int(value[i:i + 2], 16) / 255.0 for i in (0, 2, 4)] + [1.0]


def content_layer(index: int, beat: dict, start: int, window: int) -> dict | None:
    """The render side of a beat: its `content` block becomes a static 3D layer
    whose lifetime is exactly the beat's window. Camera-only here too: the
    layer never animates."""
    content = beat.get("content")
    if not content:
        return None
    cx, cy, cz = beat["center"]
    base = {"id": f"beat-{index}", "position": [cx, cy, cz], "start_frame": start,
            "duration_frames": window, "enable_3d": True}
    kind = content["type"]
    if kind == "text":
        size = content["font_size"]
        base.update({"type": "text", "text": content["text"], "size": content["size"],
                     "style": {"font": content["font"], "font_size": size,
                               "fill": content["fill"], "fit_mode": "shrink_only",
                               "min_font_size": max(20, int(size * 0.4)),
                               "max_font_size": size}})
    elif kind == "image":
        base.update({"type": "image", "asset": content["asset"], "size": content["size"],
                     "fit": "contain"})
    elif kind == "shape":
        shape = {"type": "rounded_rect", "radius": content.get("radius", 0),
                 "fill": hex_to_rgba(content["fill"])}
        if "stroke" in content:
            shape["stroke"] = content["stroke"]
        base.update({"type": "shape", "size": content["size"], "shape": shape})
    return base


def plan_from_sequence_json(seq_path: Path, seq_id: str, rows: list[list[float]]) -> dict:
    """One pre-configured map JSON -> one render plan: camera tracks from the
    tool rows, layers from the beats' content blocks."""
    doc = json.loads(seq_path.read_text())
    travel = int(doc.get("travel_frames", 24))
    in_frame = int(doc.get("in_frame", 0))
    total = len(rows)

    background = {"id": "background", "type": "color", "color": [0.018, 0.028, 0.033, 1],
                  "size": [WIDTH, HEIGHT], "screen_space": True, "start_frame": 0,
                  "duration_frames": total}
    layers = [background]
    start = in_frame
    for index, beat in enumerate(doc["beats"]):
        is_last = index == len(doc["beats"]) - 1
        window = int(beat["hold"]) + (0 if is_last else travel)
        layer = content_layer(index, beat, start, window)
        if layer:
            layers.append(layer)
        start += window
    caption = {"id": "move-caption", "type": "text", "text": caption_for(seq_id),
               "size": [1100, 54], "position": [960, 880, 0], "start_frame": 0,
               "duration_frames": total, "enable_3d": True,
               "style": {"font": "assets/fonts/Inter-Bold.ttf", "font_size": 26,
                         "fill": "#92B4A6", "fit_mode": "shrink_only", "min_font_size": 20,
                         "max_font_size": 26}}

    channels = list(zip(*[r[1:] for r in rows]))
    channels = [list(channels[0]), list(channels[1]), list(channels[2]),
                *[unwrap_degrees(list(c)) for c in channels[3:6]], list(channels[6])]
    channels[0] = [x - WIDTH / 2 for x in channels[0]]
    channels[1] = [y - HEIGHT / 2 for y in channels[1]]
    channels[2] = [-z for z in channels[2]]
    return {"schema": "chronon.render-plan.v3", "version": 3,
            "job_id": f"scene_camera_sequencer_v1_{seq_id}",
            "canvas": {"width": WIDTH, "height": HEIGHT, "fps_num": FPS, "fps_den": 1,
                       "duration_frames": total},
            "camera": {"type": "perspective",
                       "position": [round(channels[i][0], 6) for i in range(3)],
                       "rotation_deg": [round(x, 6) for x in rows[0][4:7]],
                       "fov_deg": round(rows[0][7], 6), "near": 1, "far": 10000, "zoom": 1},
            "camera_animation": {"tracks": [track(p, c) for p, c in zip(PROPERTIES, channels)]},
            "layers": [*layers, caption],
            "output": {"path": f"{seq_id}.mp4", "format": "mp4", "codec": "h264"}}


def sequence_rows(seq_path: Path) -> tuple[str, list[list[float]]]:
    raw = subprocess.run([str(SEQUENCE_TOOL), str(seq_path)], check=True,
                         capture_output=True, text=True).stdout
    lines = raw.strip().splitlines()
    seq_id, _total = lines[0].split()
    rows = [[float(v) for v in line.split()] for line in lines[1:]]
    return seq_id, rows


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--generate-only", action="store_true", help="write plans without rendering")
    parser.add_argument("--sequence-json", type=Path, default=None,
                        help="render ONE pre-configured map JSON instead of the gallery")
    parser.add_argument("--id", default=None, help="override the sequence id for --sequence-json")
    args = parser.parse_args()
    if not POSE_DUMPER.is_file():
        raise SystemExit(f"missing {POSE_DUMPER}; build target "
                         "chronontemplate_dump_scene_camera_poses first")
    if args.sequence_json and not SEQUENCE_TOOL.is_file():
        raise SystemExit(f"missing {SEQUENCE_TOOL}; build target "
                         "chronontemplate_sequence_from_json first")
    if not args.generate_only and not CLI.is_file():
        raise SystemExit(f"missing Chronon3D CLI: {CLI}")

    def render(job: tuple[Path, Path]) -> Path:
        plan_path, output = job
        subprocess.run([str(CLI), "render-plan", "--input", str(plan_path),
                        "--assets-root", str(ASSETS), "--output", str(output),
                        "--backend", "software", "--encode-preset", "veryfast"],
                       check=True, cwd=WORKSPACE,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return output

    if args.sequence_json:
        seq_path = args.sequence_json.resolve()
        seq_id, rows = sequence_rows(seq_path)
        if args.id:
            seq_id = args.id
        plan_dir = OUT / "plans"
        render_dir = OUT / "renders"
        plan_dir.mkdir(parents=True, exist_ok=True)
        render_dir.mkdir(parents=True, exist_ok=True)
        plan = plan_from_sequence_json(seq_path, seq_id, rows)
        plan_path = plan_dir / f"{seq_id}.plan.json"
        plan_path.write_text(json.dumps(plan, indent=2) + "\n")
        if not args.generate_only:
            render((plan_path, render_dir / f"{seq_id}.mp4"))
        print(f"Generated 1 render plan under {OUT}")
        return

    poses = sampled_poses()
    render_jobs = []
    for seq_id, rows in poses.items():
        plan_dir = OUT / "plans"
        render_dir = OUT / "renders"
        plan_dir.mkdir(parents=True, exist_ok=True)
        render_dir.mkdir(parents=True, exist_ok=True)
        plan = plan_for(seq_id, rows, master=seq_id.startswith("master_"))
        plan_path = plan_dir / f"{seq_id}.plan.json"
        plan_path.write_text(json.dumps(plan, indent=2) + "\n")
        if not args.generate_only:
            render_jobs.append((plan_path, render_dir / f"{seq_id}.mp4"))

    if render_jobs:
        with ThreadPoolExecutor(max_workers=4) as pool:
            futures = [pool.submit(render, job) for job in render_jobs]
            for future in as_completed(futures):
                print(future.result(), flush=True)
    print(f"Generated {len(poses)} render plans under {OUT}")


if __name__ == "__main__":
    main()
