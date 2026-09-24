#!/usr/bin/env python3
"""Build and render the eight-motion by three-corner image motion matrix."""
from __future__ import annotations

import json
import subprocess
import time
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
MATRIX = ROOT / "out/image_25d_clean_v1/verify_matrix_v2"
MOTIONS = [
    "image_25d_depth_float_in", "image_25d_yaw_flip_in",
    "image_25d_pitch_lift", "image_25d_pop_z_bounce",
    "image_25d_swipe_3d", "image_25d_card_swing",
    "image_25d_blur_focus_in", "image_25d_blur_scale_in",
]
SHAPES = [("square", 760, 0), ("rounded_40", 830, 40), ("rounded_96", 900, 96)]
CLI = ROOT.parent / "Chronon3d/build/chronon/linux-video-release/apps/chronon3d_cli/chronon3d_cli"


def make_rounded_source(radius: int, output: Path) -> None:
    source = Image.open(ROOT / "assets/test/square_bottle_clean_source.png").convert("RGBA")
    width, height = source.size
    source_radius = round(radius * width / (760 + (radius == 40) * 70 + (radius == 96) * 140))
    scale = 4
    mask = Image.new("L", (width * scale, height * scale), 0)
    ImageDraw.Draw(mask).rounded_rectangle(
        (0, 0, width * scale - 1, height * scale - 1),
        radius=source_radius * scale,
        fill=255,
    )
    source.putalpha(mask.resize((width, height), Image.Resampling.LANCZOS))
    source.save(output)


def main() -> None:
    MATRIX.mkdir(parents=True, exist_ok=True)
    plan_dir = MATRIX / "plans"
    asset_dir = MATRIX / "assets"
    plan_dir.mkdir(exist_ok=True)
    asset_dir.mkdir(exist_ok=True)
    catalog = json.loads((ROOT / "catalog/motion_catalog.v1.json").read_text())
    definitions = {motion["id"]: motion for motion in catalog["motions"]}
    for motion in MOTIONS:
        if motion not in definitions:
            raise RuntimeError(f"missing canonical catalog motion: {motion}")

    template = json.loads((ROOT / "out/image_25d_clean_v1/plans/image_25d_depth_float_in.plan.json").read_text())
    assets = ["assets/test/square_bottle_clean_source.png"]
    for name, _, radius in SHAPES[1:]:
        asset = asset_dir / f"square_bottle_{name}.png"
        make_rounded_source(radius, asset)
        assets.append(str(asset.relative_to(ROOT)))

    for motion in MOTIONS:
        for index, (shape, size, _) in enumerate(SHAPES):
            plan = json.loads(json.dumps(template))
            plan["job_id"] = f"verify_{motion}_{shape}"
            layer = next(item for item in plan["layers"] if item.get("type") == "image")
            layer["asset"] = assets[index]
            layer["size"] = [size, size]
            layer["radius"] = 0  # rounded alpha is baked once to avoid the Vulkan/software edge halo
            layer["animation"] = {"tracks": definitions[motion]["tracks"]}
            (plan_dir / f"{motion}_{shape}.plan.json").write_text(json.dumps(plan, indent=2) + "\n")

    timings = []
    log_dir = MATRIX / "render_logs"
    log_dir.mkdir(exist_ok=True)
    started = time.perf_counter()
    for plan_path in sorted(plan_dir.glob("*.plan.json")):
        clip_name = plan_path.name.removesuffix(".plan.json")
        output = MATRIX / f"{clip_name}.mp4"
        t0 = time.perf_counter()
        result = subprocess.run([
            str(CLI), "render", "--plan", str(plan_path), "--assets-root", str(ROOT),
            "--output", str(output), "--backend", "software", "--gpu-hot-path-mode", "auto",
            "--hardware", "none", "--encoder-backend", "pipe", "--encode-preset", "ultrafast",
            "--fps", "30", "--crf", "18", "--log-level", "error",
        ], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        (log_dir / f"{clip_name}.log").write_text(result.stdout)
        if result.returncode:
            raise RuntimeError(f"Chronon render failed for {clip_name}; see {log_dir / f'{clip_name}.log'}")
        elapsed = time.perf_counter() - t0
        record = {"file": output.name, "render_seconds": round(elapsed, 3), "size_bytes": output.stat().st_size,
                  "frames": 150, "fps": 30, "render_fps": round(150 / elapsed, 2)}
        timing_path = Path(str(output) + ".timing.json")
        if timing_path.exists():
            timing = json.loads(timing_path.read_text())
            summary = timing.get("summary", {})
            exclusive = timing.get("exclusive_wall_timeline", {})
            record.update({
                "render_loop_ms": exclusive.get("render_loop_ms"),
                "prepare_ms": exclusive.get("prepare_ms"),
                "encoder_drain_finalize_ms": exclusive.get("encoder_drain_finalize_ms"),
                "mean_frame_ms": summary.get("mean_frame_ms"),
                "p95_frame_ms": summary.get("p95_frame_ms"),
                "measured_fps": summary.get("measured_fps"),
                "realtime_factor": summary.get("realtime_factor"),
                "dirty_area_ratio": timing.get("frame_times_ms", [{}])[0].get("dirty_area_ratio"),
            })
        timings.append(record)
        print(f"rendered {output.name}: {elapsed:.2f}s, {150 / elapsed:.1f} render-fps")
    total = time.perf_counter() - started
    (MATRIX / "render_metrics.json").write_text(json.dumps({
        "backend": "software", "clips": len(timings), "frames_per_clip": 150, "fps": 30,
        "total_seconds": round(total, 3), "average_seconds_per_clip": round(total / len(timings), 3),
        "average_render_fps": round(sum(item["render_fps"] for item in timings) / len(timings), 2),
        "average_render_loop_ms": round(sum(item.get("render_loop_ms", 0) or 0 for item in timings) / len(timings), 2),
        "average_mean_frame_ms": round(sum(item.get("mean_frame_ms", 0) or 0 for item in timings) / len(timings), 2),
        "average_p95_frame_ms": round(sum(item.get("p95_frame_ms", 0) or 0 for item in timings) / len(timings), 2),
        "clips": timings,
    }, indent=2) + "\n")
    print(f"PASS: {len(timings)} clips in {total:.2f}s; metrics written to {MATRIX / 'render_metrics.json'}")


if __name__ == "__main__":
    main()
