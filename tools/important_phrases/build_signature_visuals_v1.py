#!/usr/bin/env python3
"""Build the first two Chronon signature visual RenderPlan V3 canaries."""
from __future__ import annotations

import argparse
import json
import math
import shutil
import subprocess
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
WORKSPACE = ROOT.parent
CHRONON = WORKSPACE / "Chronon3d"
PLANS_DIR = ROOT / "golden_plans/signature_visuals_v1"
DEFAULT_OUT = ROOT / "out/signature_visuals_v1"
CLI = CHRONON / ".tmp/chronon-builds/linux-video-fast-dev/apps/chronon3d_cli/chronon3d_cli"
WIDTH, HEIGHT, FPS = 1920, 1080, 30
ANAMORPHIC_FRAMES = 240
SCALE_FRAMES = 300
FONT = "Chronon3d/assets/fonts/Inter-Bold.ttf"
WORD = "CHRONON"
BG = [0.012, 0.018, 0.032, 1.0]
WHITE = "#F5F3F7"
CYAN = "#66E3D0"


def track(prop: str, values: list[tuple[int, Any]], easing: str = "in_out_cubic") -> dict[str, Any]:
    return {"property": prop, "easing": easing,
            "keyframes": [{"frame": f, "value": v} for f, v in values]}


def base_plan(job_id: str, frames: int, layers: list[dict[str, Any]], camera: dict[str, Any],
              camera_tracks: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "schema": "chronon.render-plan.v3", "version": 3, "job_id": job_id,
        "canvas": {"width": WIDTH, "height": HEIGHT, "fps_num": FPS,
                   "fps_den": 1, "duration_frames": frames},
        "camera": camera, "camera_animation": {"tracks": camera_tracks},
        "layers": layers,
        "output": {"path": f"{job_id}.mp4", "format": "mp4", "codec": "h264"},
    }


def anamorphic_plan() -> tuple[dict[str, Any], dict[str, Any]]:
    from PIL import ImageFont

    frames, fov = ANAMORPHIC_FRAMES, 45.0
    font_path = CHRONON / "assets/fonts/Inter-Bold.ttf"
    font = ImageFont.truetype(str(font_path), 1000)
    advances = [font.getlength(WORD[:i]) for i in range(len(WORD) + 1)]
    total = advances[-1]
    target_word_width_px = 760.0
    target_glyph_height_px = 170.0
    focal_px = HEIGHT / (2 * math.tan(math.radians(fov) / 2))
    depths = [260.0, 410.0, 590.0, 790.0, 1010.0, 1260.0, 1510.0]
    colors = [WHITE, WHITE, CYAN, WHITE, WHITE, CYAN, WHITE]
    layers: list[dict[str, Any]] = [{
        "id": "background", "type": "color", "color": BG, "size": [WIDTH, HEIGHT],
        "screen_space": True, "start_frame": 0, "duration_frames": frames,
    }]
    placements = []
    for i, letter in enumerate(WORD):
        depth = depths[i]
        advance_center = (advances[i] + advances[i + 1]) / 2 - total / 2
        desired_x_px = advance_center * target_word_width_px / total
        world_x = WIDTH / 2 + desired_x_px * depth / focal_px
        world_z = -1000.0 + depth
        projected_font = target_glyph_height_px * depth / focal_px
        projected_width = (advances[i + 1] - advances[i]) / total * target_word_width_px * depth / focal_px
        # The renderer anchors text layers at their center; generous frame height avoids shrink-to-fit.
        layers.append({
            "id": f"glyph-{i}-{letter.lower()}", "type": "text", "text": letter,
            "size": [max(90.0, projected_width * 1.7), projected_font * 1.8],
            "position": [world_x, HEIGHT / 2, world_z], "enable_3d": True,
            "style": {"font": FONT, "font_size": projected_font, "min_font_size": projected_font,
                      "max_font_size": projected_font, "fit_mode": "shrink_only", "fill": colors[i]},
            "start_frame": 0, "duration_frames": frames,
        })
        placements.append({"glyph": letter, "world_position": [round(world_x, 4), 0.0, round(world_z, 4)],
                           "camera_depth": depth, "target_screen_x_px": round(desired_x_px, 3)})
    camera = {"type": "perspective", "position": [0.0, 10.0, -1000.0],
              "rotation_deg": [0.0, 8.0, 0.0], "fov_deg": fov,
              "near": 1.0, "far": 10000.0, "zoom": 1.0}
    tracks = [
        track("camera_position_x", [(0, 0.0), (80, 0.0), (145, 0.0), (239, 0.0)]),
        track("camera_position_y", [(0, 10.0), (80, 0.0), (239, 0.0)]),
        track("camera_rotation_y", [(0, 8.0), (80, 0.0), (145, 0.0), (239, 0.0)]),
        track("camera_position_z", [(0, -1000.0), (80, -1000.0), (145, -1000.0), (239, -925.0)]),
    ]
    plan = base_plan("signature_anamorphic_typography_v1", frames, layers, camera, tracks)
    meta = {"anchor_frame": 110, "anchor_camera": {"position": [0, 0, -1000], "rotation_deg": [0, 0, 0],
            "fov_deg": fov}, "word": WORD, "projection": "perspective camera; glyphs solved along individual view rays",
            "glyphs": placements, "breakup": "camera passes forward after frame 145"}
    return plan, meta


SCALE_STAGES = [
    ("ATOMIC SPACING", "10⁻¹⁰ m", "distance between atoms"),
    ("TRANSISTOR", "10⁻⁷ m", "feature scale in modern silicon"),
    ("SAND GRAIN", "10⁻³ m", "a millimetre across"),
    ("HAND", "10⁻¹ m", "a familiar human measure"),
    ("HUMAN", "10⁰ m", "one metre"),
    ("ROOM", "10¹ m", "interior architecture"),
    ("BUILDING", "10² m", "urban structure"),
    ("CITY", "10⁴ m", "district to district"),
    ("EARTH", "10⁷ m", "planetary diameter scale"),
    ("SOLAR SYSTEM", "10¹³ m", "outer planetary distances"),
]


def scale_plan() -> tuple[dict[str, Any], dict[str, Any]]:
    frames, spacing, depth = SCALE_FRAMES, 1400.0, 1000.0
    layers: list[dict[str, Any]] = [{
        "id": "background", "type": "color", "color": BG, "size": [WIDTH, HEIGHT],
        "screen_space": True, "start_frame": 0, "duration_frames": frames,
    }]
    stages = []
    for index, (title, magnitude, detail) in enumerate(SCALE_STAGES):
        start = index * 30
        z = index * spacing
        stages.append({"index": index, "title": title, "magnitude": magnitude, "detail": detail,
                       "frame_start": start, "frame_end": min(frames - 1, start + 29),
                       "coordinate_band_z": z})
        duration = min(30, frames - start)
        for suffix, text, y, size, color in [
            ("title", title, 700.0, 88, CYAN if index % 3 == 1 else WHITE),
            ("magnitude", magnitude, 520.0, 66, CYAN),
            ("detail", detail, 340.0, 34, "#AAB5C5"),
        ]:
            layers.append({
                "id": f"scale-band-{index:02d}-{suffix}", "type": "text", "text": text,
                "size": [1500, size * 2.2], "position": [WIDTH / 2, y, z], "enable_3d": True,
                "style": {"font": FONT, "font_size": size, "min_font_size": size,
                          "max_font_size": size, "fit_mode": "shrink_only", "fill": color},
                "start_frame": start, "duration_frames": duration,
            })
    camera = {"type": "perspective", "position": [0.0, 0.0, -depth], "rotation_deg": [0.0, 0.0, 0.0],
              "fov_deg": 45.0, "near": 1.0, "far": 20000.0, "zoom": 1.0}
    points: list[tuple[int, float]] = []
    for stage in stages:
        here = stage["coordinate_band_z"] - depth
        points.extend([(stage["frame_start"], here),
                       (min(frames - 1, stage["frame_start"] + 20), here)])
    points.append((frames - 1, (len(stages) - 1) * spacing - depth))
    camera_track = track("camera_position_z", points)
    plan = base_plan("signature_powers_of_ten_v1", frames, layers, camera, [camera_track])
    meta = {"method": "camera-relative coordinate bands with content handoff",
            "coordinate_spacing": spacing, "camera_depth_to_band": depth,
            "physical_scale_is_metadata": True,
            "stages": stages}
    return plan, meta


def write_plans(directory: Path) -> list[Path]:
    directory.mkdir(parents=True, exist_ok=True)
    generated = [anamorphic_plan(), scale_plan()]
    paths = []
    for plan, meta in generated:
        plan_id = plan["job_id"]
        path = directory / f"{plan_id}.plan.json"
        path.write_text(json.dumps(plan, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        (directory / f"{plan_id}.scene.json").write_text(
            json.dumps(meta, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        paths.append(path)
    manifest = {"schema": "chronontemplate.signature-visuals.v1", "family": "signature_visuals_v1",
                "renderer_contract": "Chronon RenderPlan V3; 3D text layers and deterministic camera tracks",
                "canvas": {"width": WIDTH, "height": HEIGHT, "fps": FPS},
                "scenes": [{"id": p.stem.removesuffix(".plan"), "plan": p.name,
                            "duration_frames": json.loads(p.read_text()) ["canvas"]["duration_frames"]}
                           for p in paths]}
    (directory / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return paths


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plans-dir", type=Path, default=PLANS_DIR)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--cli", type=Path, default=CLI)
    parser.add_argument("--render", action="store_true", help="validate and render both scenes serially")
    parser.add_argument("--scene", choices=("signature_anamorphic_typography_v1",
                        "signature_powers_of_ten_v1"), action="append",
                        help="render only selected scene(s); repeat as needed")
    parser.add_argument("--render-backend", choices=("vulkan", "software"), default="vulkan")
    args = parser.parse_args(argv)
    plans_dir, out_dir = args.plans_dir.resolve(), args.out.resolve()
    paths = write_plans(plans_dir)
    print(f"Wrote {len(paths)} plans to {plans_dir}", flush=True)
    if not args.render:
        return 0
    if not args.cli.is_file():
        raise SystemExit(f"Chronon3D CLI not found: {args.cli}")
    out_dir.mkdir(parents=True, exist_ok=True)
    selected = [p for p in paths if args.scene is None or
                p.name.removesuffix(".plan.json") in set(args.scene)]
    for plan_path in selected:
        subprocess.run([str(args.cli), "validate", "--plan", str(plan_path), "--assets-root",
                        str(WORKSPACE), "--profile", "preview"], check=True)
        video = out_dir / f"{plan_path.name.removesuffix('.plan.json')}.mp4"
        subprocess.run([str(args.cli), "render", "--backend", args.render_backend, "--plan",
                        str(plan_path), "--assets-root", str(WORKSPACE), "-o", str(video),
                        "--ffmpeg-mode", "pipe", "--codec", "h264", "--encode-preset", "fast"], check=True)
        subprocess.run(["ffprobe", "-v", "error", "-count_frames", "-select_streams", "v:0",
                        "-show_entries", "stream=width,height,avg_frame_rate,nb_read_frames", "-of", "json",
                        str(video)], check=True, stdout=subprocess.PIPE, text=True)
        print(f"Rendered {video}", flush=True)
    shutil.copy2(plans_dir / "manifest.json", out_dir / "manifest.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
