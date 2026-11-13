#!/usr/bin/env python3
"""Centered classic bevel text for the `text_3d_v1` section.

One six-second clip: a single serif word centred on a dark plate, a slow
push-in, a deliberately strong `light.sdf_bevel` treatment on the glyph edges,
and a native `camera_ring` defocus that blurs the left and right ends of the
word while the optical centre stays sharp. Both effects are C++ kernels; this
file only authors the RenderPlan and renders it through the strict Vulkan path.

Usage:
    python3 tools/text_animators/build_text_3d_bevel_classic.py --render
    python3 tools/text_animators/build_text_3d_bevel_classic.py --verify
"""
from __future__ import annotations

import argparse
import json
import subprocess
import time
from pathlib import Path

import build_text_3d_rotations as base

ROOT = base.ROOT
REPO = base.REPO
ASSETS = base.ASSETS
CLI = base.CLI
OUT = ROOT / "out" / "text_3d_bevel_camera_ring_20261112"
VIDEO = OUT / "text_3d_bevel_camera_ring_1920x1080_6s.mp4"
PLAN = OUT / "text_3d_bevel_camera_ring.plan.json"
LOG = OUT / "text_3d_bevel_camera_ring.log"
MANIFEST = OUT / "MANIFEST.json"
STILLS = OUT / "stills"

FONT = "assets/fonts/PlayfairDisplay-Bold.ttf"
WORD = "CHRONON"
BEVEL = [
    {"param": "bevel_width", "value": 20.0},
    {"param": "bevel_height", "value": 34.0},
    {"param": "rim_width", "value": 5.0},
    {"param": "rim_intensity", "value": 1.0},
    {"param": "highlight", "value": 1.9},
    {"param": "shade", "value": 0.9},
    {"param": "light_angle", "value": -135.0},
    {"param": "light_elevation", "value": 48.0},
    {"param": "shadow_distance", "value": 28.0},
    {"param": "shadow_softness", "value": 16.0},
    {"param": "shadow_opacity", "value": 0.85},
]
CAMERA_RING = {
    "center": [0.5, 0.5],
    "axis_scale": [1.15, 0.72],
    "inner_radius": 0.08,
    "outer_radius": 0.46,
    "max_blur_radius": 0.055,
    "chroma_dispersion": 0.012,
    "anamorphic_stretch": 1.65,
    "samples": 64,
}


def build_plan() -> dict:
    return {
        "schema": "chronon.render-plan.v3",
        "version": 3,
        "job_id": "text_3d_bevel_camera_ring_v1",
        "canvas": {
            "width": base.W,
            "height": base.H,
            "fps_num": base.FPS,
            "fps_den": 1,
            "duration_frames": base.FRAMES,
        },
        "layers": [
            {
                "id": "backdrop",
                "type": "color",
                "color": [0.0045, 0.0055, 0.0085, 1.0],
                "size": [float(base.W), float(base.H)],
                "position": [0.0, 0.0],
                "start_frame": 0,
                "duration_frames": base.FRAMES,
                "effects": [
                    {
                        "type": "vignette",
                        "radius": 0.68,
                        "softness": 0.7,
                        "amount": 0.32,
                        "color": [0.0, 0.0, 0.0, 1.0],
                    }
                ],
            },
            {
                "id": "bevel_word",
                "type": "text",
                "text": WORD,
                "size": [float(base.W), float(base.H)],
                "position": [base.W * 0.5, base.H * 0.5],
                "start_frame": 0,
                "duration_frames": base.FRAMES,
                "style": {
                    "font": FONT,
                    "font_size": 238.0,
                    "font_weight": 700,
                    "fill": "#D8B26A",
                    "text_align": "center",
                },
                "effects": [
                    {
                        "type": "catalog",
                        "effect_id": "light.sdf_bevel",
                        "params": BEVEL,
                    },
                    {"type": "camera_ring", **CAMERA_RING},
                ],
                "animation": {
                    "tracks": [
                        {
                            "property": "opacity",
                            "easing": "out_cubic",
                            "keyframes": [
                                {"frame": 0, "value": 0.0},
                                {"frame": 16, "value": 1.0},
                                {"frame": 179, "value": 1.0},
                            ],
                        },
                        {
                            "property": "scale",
                            "easing": "in_out_sine",
                            "keyframes": [
                                {"frame": 0, "value": 0.975},
                                {"frame": 179, "value": 1.035},
                            ],
                        },
                    ]
                },
            },
        ],
        "output": {
            "path": VIDEO.name,
            "format": "mp4",
            "codec": "h264",
        },
    }


def validate() -> None:
    result = subprocess.run(
        [str(CLI), "validate", "--plan", str(PLAN), "--assets-root", str(ASSETS)],
        cwd=REPO,
        text=True,
        capture_output=True,
    )
    if result.returncode != 0:
        tail = (result.stdout + result.stderr).strip().splitlines()[-14:]
        raise SystemExit(f"validation failed: {' | '.join(tail)}")


def verify_video() -> tuple[dict, int]:
    info = base.probe(VIDEO)
    if (info["width"], info["height"], info["frames"]) != (base.W, base.H, base.FRAMES):
        raise SystemExit(f"unexpected probe: {info}")
    if info["fps"] != f"{base.FPS}/1":
        raise SystemExit(f"unexpected fps: {info['fps']}")
    log_text = LOG.read_text(encoding="utf-8", errors="replace")
    routes = log_text.count("route=mtsdf")
    if routes == 0:
        raise SystemExit("render log has no native MTSDF route")
    for marker in ("route=software", "UnsupportedCapability", "render failed"):
        if marker in log_text:
            raise SystemExit(f"{marker!r} found in render log")
    return info, routes


def stills() -> dict[str, dict]:
    rows: dict[str, dict] = {}
    STILLS.mkdir(parents=True, exist_ok=True)
    for label, second in (("early", 0.6), ("mid", 3.0), ("late", 5.6)):
        path = STILLS / f"text_3d_bevel_camera_ring_{label}.png"
        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-v",
                "error",
                "-ss",
                f"{second:.3f}",
                "-i",
                str(VIDEO),
                "-frames:v",
                "1",
                str(path),
            ],
            check=True,
        )
        rows[label] = {"path": str(path.relative_to(REPO)), "sha256": base.sha256(path)}
    return rows


def write_manifest(info: dict, routes: int) -> dict:
    manifest = {
        "schema": "chronontemplate.text-3d-bevel-camera-ring.v1",
        "date": "2026-11-12",
        "section": "text_3d_v1",
        "job_id": "text_3d_bevel_camera_ring_v1",
        "word": WORD,
        "font": FONT,
        "contract": {
            "width": base.W,
            "height": base.H,
            "fps": f"{base.FPS}/1",
            "frames": base.FRAMES,
            "duration_s": 6.0,
        },
        "look": {
            "bevel_effect": "light.sdf_bevel",
            "bevel_params": {row["param"]: row["value"] for row in BEVEL},
            "camera_ring": CAMERA_RING,
            "push_in": {"from_scale": 0.975, "to_scale": 1.035, "easing": "in_out_sine"},
        },
        "video": str(VIDEO.relative_to(REPO)),
        "plan": str(PLAN.relative_to(REPO)),
        "log": str(LOG.relative_to(REPO)),
        "probe": info,
        "sha256": base.sha256(VIDEO),
        "mtsdf_routes": routes,
        "stills": stills(),
        "notes": (
            "Single centered serif word with a strong native SDF bevel, a "
            "native Petzval camera-ring defocus at the left/right ends, and a "
            "slow scale push-in. Not an After Effects pixel-parity claim."
        ),
    }
    MANIFEST.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


def render() -> dict:
    OUT.mkdir(parents=True, exist_ok=True)
    PLAN.write_text(json.dumps(build_plan(), indent=2) + "\n", encoding="utf-8")
    validate()

    command = [
        str(CLI),
        "render",
        "--plan",
        str(PLAN),
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
        str(VIDEO),
    ]
    started = time.time()
    with LOG.open("w", encoding="utf-8") as handle:
        handle.write(" ".join(command) + "\n\n")
        handle.flush()
        result = subprocess.run(command, cwd=REPO, stdout=handle, stderr=subprocess.STDOUT)
    if result.returncode != 0:
        tail = LOG.read_text(encoding="utf-8", errors="replace").strip().splitlines()[-14:]
        raise SystemExit(f"render failed: {' | '.join(tail)}")

    info, routes = verify_video()
    manifest = write_manifest(info, routes)
    print(f"VIDEO {manifest['video']} {manifest['sha256']}")
    print(f"RENDER {round(time.time() - started, 1)}s")
    return manifest


def verify() -> dict:
    if not MANIFEST.is_file():
        raise SystemExit(f"missing manifest: {MANIFEST}")
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    info, routes = verify_video()
    if info != manifest["probe"] or routes != manifest["mtsdf_routes"]:
        raise SystemExit("probe/route mismatch")
    if base.sha256(VIDEO) != manifest["sha256"]:
        raise SystemExit("sha mismatch")
    print(f"VERIFY {VIDEO.name} OK")
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--render", action="store_true")
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    if args.render:
        render()
    elif args.verify:
        verify()
    else:
        parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
