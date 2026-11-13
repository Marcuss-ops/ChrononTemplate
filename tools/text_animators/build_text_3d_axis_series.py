#!/usr/bin/env python3
"""Text 3D axis series for ChrononTemplate.

Builds four six-second clips from the `text_3d_v1` scene:

* combined: the existing demo with all three rows staggered;
* yaw: the YAW / Y row swings around Y while the other rows stay still;
* pitch: the PITCH / X row swings around X while the other rows stay still;
* roll: the ROLL / Z row swings around Z while the other rows stay still.

Every clip uses the same head-on perspective camera and the same layout.
The camera conversion keeps the 3D anchors aligned with the screen labels.

Usage:
    python3 tools/text_animators/build_text_3d_axis_series.py --render
    python3 tools/text_animators/build_text_3d_axis_series.py --verify
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path

import build_text_3d_rotations as base

ROOT = base.ROOT
REPO = base.REPO
ASSETS = base.ASSETS
CLI = base.CLI
OUT = ROOT / "out" / "text_3d_axis_series_20261112"
VIDEOS = OUT / "videos"
PLANS = OUT / "plans"
LOGS = OUT / "logs"
STILLS = OUT / "stills"

STILL_SECONDS = (1.8, 3.9, 4.6)

# Keyframes are [X, Y, Z] degrees. The first and last beats are static, so
# each clip opens and closes on the same readable composition.
AXES = (
    {
        "id": "yaw",
        "title": "YAW / Y",
        "layer": "word_yaw",
        "axis": "yaw_y",
        "keys": (
            (0, (0.0, 0.0, 0.0)),
            (18, (0.0, 0.0, 0.0)),
            (62, (0.0, -52.0, 0.0)),
            (116, (0.0, 52.0, 0.0)),
            (170, (0.0, 0.0, 0.0)),
            (179, (0.0, 0.0, 0.0)),
        ),
    },
    {
        "id": "pitch",
        "title": "PITCH / X",
        "layer": "word_pitch",
        "axis": "pitch_x",
        "keys": (
            (0, (0.0, 0.0, 0.0)),
            (18, (0.0, 0.0, 0.0)),
            (62, (-44.0, 0.0, 0.0)),
            (116, (44.0, 0.0, 0.0)),
            (170, (0.0, 0.0, 0.0)),
            (179, (0.0, 0.0, 0.0)),
        ),
    },
    {
        "id": "roll",
        "title": "ROLL / Z",
        "layer": "word_roll",
        "axis": "roll_z",
        "keys": (
            (0, (0.0, 0.0, 0.0)),
            (18, (0.0, 0.0, 0.0)),
            (62, (0.0, 0.0, -20.0)),
            (116, (0.0, 0.0, 20.0)),
            (170, (0.0, 0.0, 0.0)),
            (179, (0.0, 0.0, 0.0)),
        ),
    },
)


def axis_track(spec: dict) -> dict:
    return base.rotation_track(
        [base.kf(frame, list(value)) for frame, value in spec["keys"]]
    )


def build_variant(spec: dict) -> dict:
    plan = base.build_plan()
    job_id = f"text_3d_{spec['id']}_v1"
    plan["job_id"] = job_id
    plan["output"]["path"] = f"text_3d_{spec['id']}_1920x1080_6s.mp4"
    track = axis_track(spec)

    for layer in plan["layers"]:
        if layer.get("id") not in {"word_yaw", "word_pitch", "word_roll"}:
            continue
        opacity = [
            item
            for item in layer["animation"]["tracks"]
            if item["property"] == "opacity"
        ]
        layer["animation"]["tracks"] = (
            [*opacity, track] if layer["id"] == spec["layer"] else opacity
        )
    return plan


def ensure_dirs() -> None:
    for path in (VIDEOS, PLANS, LOGS, STILLS):
        path.mkdir(parents=True, exist_ok=True)


def validate(plan_path: Path) -> None:
    result = subprocess.run(
        [str(CLI), "validate", "--plan", str(plan_path), "--assets-root", str(ASSETS)],
        cwd=REPO,
        text=True,
        capture_output=True,
    )
    if result.returncode != 0:
        tail = (result.stdout + result.stderr).strip().splitlines()[-12:]
        raise SystemExit(f"validation failed for {plan_path.name}: {' | '.join(tail)}")


def stills_for(video: Path, prefix: str) -> dict[str, dict]:
    rows: dict[str, dict] = {}
    for label, second in zip(("early", "mid", "late"), STILL_SECONDS):
        still = STILLS / f"{prefix}_{label}.png"
        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-v",
                "error",
                "-ss",
                f"{second:.3f}",
                "-i",
                str(video),
                "-frames:v",
                "1",
                str(still),
            ],
            check=True,
        )
        rows[label] = {
            "path": str(still.relative_to(REPO)),
            "sha256": base.sha256(still),
        }
    return rows


def verify_video(video: Path, log_path: Path) -> tuple[dict, int]:
    info = base.probe(video)
    if (info["width"], info["height"], info["frames"]) != (base.W, base.H, base.FRAMES):
        raise SystemExit(f"unexpected probe for {video.name}: {info}")
    if info["fps"] != f"{base.FPS}/1":
        raise SystemExit(f"unexpected fps for {video.name}: {info['fps']}")
    log_text = log_path.read_text(encoding="utf-8", errors="replace")
    routes = log_text.count("route=mtsdf")
    if routes == 0:
        raise SystemExit(f"no native MTSDF route in {log_path.name}")
    for marker in ("route=software", "UnsupportedCapability", "render failed"):
        if marker in log_text:
            raise SystemExit(f"{marker!r} found in {log_path.name}")
    return info, routes


def render_variant(spec: dict) -> dict:
    plan_path = PLANS / f"text_3d_{spec['id']}.plan.json"
    plan_path.write_text(
        json.dumps(build_variant(spec), indent=2) + "\n", encoding="utf-8"
    )
    validate(plan_path)

    video = VIDEOS / f"text_3d_{spec['id']}_1920x1080_6s.mp4"
    log_path = LOGS / f"text_3d_{spec['id']}.log"
    command = [
        str(CLI),
        "render",
        "--plan",
        str(plan_path),
        "--assets-root",
        str(ASSETS),
        "--backend",
        "vulkan",
        "--gpu-hot-path-mode",
        "require_gpu_native",
        "--tone-map",
        "aces",
        "--exposure",
        "1.0",
        "-o",
        str(video),
    ]
    started = time.time()
    with log_path.open("w", encoding="utf-8") as handle:
        handle.write(" ".join(command) + "\n\n")
        handle.flush()
        result = subprocess.run(
            command, cwd=REPO, stdout=handle, stderr=subprocess.STDOUT
        )
    if result.returncode != 0:
        tail = log_path.read_text(encoding="utf-8", errors="replace").strip().splitlines()[-12:]
        raise SystemExit(f"render failed for {spec['id']}: {' | '.join(tail)}")

    info, routes = verify_video(video, log_path)
    prefix = f"text_3d_{spec['id']}"
    return {
        "id": spec["id"],
        "title": spec["title"],
        "axis": spec["axis"],
        "layer": spec["layer"],
        "video": str(video.relative_to(REPO)),
        "video_name": video.name,
        "plan": str(plan_path.relative_to(REPO)),
        "log": str(log_path.relative_to(REPO)),
        "probe": info,
        "sha256": base.sha256(video),
        "render_seconds": round(time.time() - started, 1),
        "mtsdf_routes": routes,
        "stills": stills_for(video, prefix),
    }


def copy_combined() -> dict:
    source_video = base.OUT / "text_3d_rotations_v1.mp4"
    if not source_video.is_file():
        subprocess.run(
            [sys.executable, str(Path(base.__file__)), "--render"], cwd=REPO, check=True
        )
    video = VIDEOS / "text_3d_combined_1920x1080_6s.mp4"
    plan_path = PLANS / "text_3d_combined.plan.json"
    log_path = LOGS / "text_3d_combined.log"
    shutil.copy2(source_video, video)
    shutil.copy2(base.OUT / "text_3d_rotations_v1.plan.json", plan_path)
    shutil.copy2(base.OUT / "render.log", log_path)
    timing = source_video.with_suffix(".mp4.timing.json")
    if timing.is_file():
        shutil.copy2(timing, video.with_suffix(".mp4.timing.json"))

    info, routes = verify_video(video, log_path)
    return {
        "id": "combined",
        "title": "COMBINED / XYZ",
        "axis": "xyz",
        "layer": "word_yaw + word_pitch + word_roll",
        "video": str(video.relative_to(REPO)),
        "video_name": video.name,
        "plan": str(plan_path.relative_to(REPO)),
        "log": str(log_path.relative_to(REPO)),
        "probe": info,
        "sha256": base.sha256(video),
        "render_seconds": None,
        "mtsdf_routes": routes,
        "stills": stills_for(video, "text_3d_combined"),
    }


def build_manifest(variants: list[dict]) -> dict:
    return {
        "schema": "chronon.text-3d-axis-series.v1",
        "date": "2026-11-12",
        "section": "text_3d_v1",
        "contract": {
            "width": base.W,
            "height": base.H,
            "fps": f"{base.FPS}/1",
            "frames": base.FRAMES,
            "duration_s": 6.0,
            "stills_seconds": list(STILL_SECONDS),
        },
        "camera": base.camera(),
        "variants": variants,
        "notes": (
            "Text 3D axis series: combined plus one focused clip per axis. "
            "Layer-level perspective rotation on the native MTSDF route; "
            "no After Effects pixel-parity claim."
        ),
    }


def write_readme(manifest: dict) -> None:
    lines = [
        "# Text 3D axis series",
        "",
        "Four six-second ChrononTemplate clips for the `text_3d_v1` section.",
        "Same scene and camera; each focused clip isolates one rotation axis.",
        "",
        "| Clip | Axis | Video |",
        "|---|---|---|",
    ]
    for row in manifest["variants"]:
        lines.append(
            f"| {row['title']} | `{row['axis']}` | `{row['video']}` |"
        )
    lines += [
        "",
        "Contract: 1920x1080, 30/1 fps, 180 frames, 6.0 s, native `route=mtsdf`.",
        "",
        "Regenerate and render:",
        "",
        "```bash",
        "python3 ChrononTemplate/tools/text_animators/build_text_3d_axis_series.py --render",
        "```",
        "",
        "The camera projects the canvas plane with mirrored Y and a 1.30375 scale;",
        "the generator converts each intended screen anchor through that projection.",
        "The motion is layer-level perspective, not a claim of pixel parity with",
        "After Effects.",
        "",
    ]
    (OUT / "README.md").write_text("\n".join(lines), encoding="utf-8")


def verify_manifest() -> dict:
    manifest_path = OUT / "MANIFEST.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    for row in manifest["variants"]:
        video = REPO / row["video"]
        log = REPO / row["log"]
        if not video.is_file() or not log.is_file():
            raise SystemExit(f"missing artifact for {row['id']}")
        info, routes = verify_video(video, log)
        if base.sha256(video) != row["sha256"]:
            raise SystemExit(f"sha mismatch for {video.name}")
        if info != row["probe"] or routes != row["mtsdf_routes"]:
            raise SystemExit(f"probe/route mismatch for {video.name}")
    print(f"VERIFY {len(manifest['variants'])} clips OK")
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--render", action="store_true")
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()

    if args.verify:
        verify_manifest()
        return 0
    if not args.render:
        parser.print_help()
        return 0

    ensure_dirs()
    variants = [copy_combined()]
    for spec in AXES:
        print(f"RENDER {spec['id']}", flush=True)
        variants.append(render_variant(spec))
    manifest = build_manifest(variants)
    (OUT / "MANIFEST.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    write_readme(manifest)
    for row in variants:
        print(f"VIDEO {row['video']} {row['sha256']}")
    print(f"OUT {OUT.relative_to(REPO)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
