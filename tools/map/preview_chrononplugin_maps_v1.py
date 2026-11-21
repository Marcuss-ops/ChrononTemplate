#!/usr/bin/env python3
"""Render a ChrononTemplate runtime preview for a ChrononPlugin map preset.

The map effect remains authored and rendered by ChrononPlugin. This bridge
places its original, finished clip as a native ChrononTemplate video layer so
the preset can be inspected through the Template renderer and its output path.
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parents[3]
TEMPLATE = WORKSPACE / "ChrononTemplate"
CATALOG = TEMPLATE / "catalog/chrononplugin_map_previews.v1.json"
OUT = TEMPLATE / "out/chrononplugin_map_previews_v1"
CLI_CANDIDATES = (
    WORKSPACE / "Chronon3d/build/chronon/linux-video-release/apps/chronon3d_cli/chronon3d_cli",
    WORKSPACE / "Chronon3d/build/chronon/linux-fast-dev/apps/chronon3d_cli/chronon3d_cli",
)


def probe(source: Path) -> tuple[int, int, int, float]:
    raw = subprocess.check_output([
        "ffprobe", "-v", "error", "-select_streams", "v:0",
        "-show_entries", "stream=width,height,r_frame_rate",
        "-show_entries", "format=duration", "-of", "json", str(source),
    ], text=True)
    value = json.loads(raw)
    stream = value["streams"][0]
    num, den = (int(part) for part in stream["r_frame_rate"].split("/"))
    return int(stream["width"]), int(stream["height"]), round(num / den), float(value["format"]["duration"])


def make_plan(sample: dict) -> dict:
    source = WORKSPACE / sample["source"]
    if not source.is_file():
        raise FileNotFoundError(
            f"missing preview {source}; render the ChrononPlugin map showcase first"
        )
    width, height, fps, duration = probe(source)
    if (width, height) != (1920, 1080):
        raise ValueError(f"{sample['id']}: source is {width}x{height}, expected 1920x1080")
    if duration <= 0 or duration > 10.0:
        raise ValueError(f"{sample['id']}: source duration {duration:.3f}s exceeds 10s")
    frames = round(duration * fps)
    job_id = f"chrononplugin_map_preview_{sample['id']}"
    return {
        "schema": "chronon.render-plan.v3",
        "version": 3,
        "job_id": job_id,
        "canvas": {"width": width, "height": height, "fps_num": fps,
                   "fps_den": 1, "duration_frames": frames},
        "layers": [{
            "id": "chrononplugin-map-preview",
            "type": "video",
            "source": sample["source"],
            "size": [width, height],
            "fit": "stretch",
            "screen_space": True,
            "start_frame": 0,
            "duration_frames": frames,
        }],
        "output": {"path": f"{job_id}.mp4", "format": "mp4", "codec": "h264"},
    }


def load_samples() -> list[dict]:
    value = json.loads(CATALOG.read_text())
    if value.get("schema") != "chronontemplate.chrononplugin-map-previews.v1":
        raise ValueError("unsupported ChrononPlugin map preview catalog")
    samples = value.get("samples", [])
    ids = [sample.get("id") for sample in samples]
    if not ids or len(ids) != len(set(ids)):
        raise ValueError("preview catalog has no samples or duplicate IDs")
    return samples


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--list", action="store_true", help="list available previews")
    mode.add_argument("--preset", help="write one preview plan by ID")
    mode.add_argument("--all-plans", action="store_true", help="write every preview plan")
    parser.add_argument("--render", action="store_true", help="render the selected plan(s) in Chronon3d")
    parser.add_argument("--cli", type=Path, help="chronon3d_cli path")
    args = parser.parse_args()
    samples = load_samples()
    if args.list:
        for sample in samples:
            print(f"{sample['id']}\t{sample.get('map_animation', 'basemap')}\t{sample['title']}")
        return 0
    if args.preset:
        selected = [sample for sample in samples if sample["id"] == args.preset]
        if not selected:
            parser.error(f"unknown preview preset: {args.preset}")
    else:
        selected = samples
    cli = args.cli or next((path for path in CLI_CANDIDATES if path.is_file()), None)
    if args.render and cli is None:
        parser.error("chronon3d_cli not found; pass --cli")
    OUT.mkdir(parents=True, exist_ok=True)
    for sample in selected:
        plan = make_plan(sample)
        plan_path = OUT / f"{sample['id']}.plan.json"
        plan_path.write_text(json.dumps(plan, indent=2) + "\n")
        print(f"wrote {plan_path}")
        if args.render:
            output = OUT / f"{sample['id']}.mp4"
            subprocess.run([str(cli), "render", "--plan", str(plan_path),
                            "--assets-root", str(WORKSPACE), "--output", str(output),
                            "--backend", "software"], check=True)
            print(f"rendered {output}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
