#!/usr/bin/env python3
"""Render every generated plan in the date animation catalog.

Defaults to two concurrent Vulkan renders (the 16 GB GPU safely handles two
of these text plans). The approved Rolling Year preset is already rendered and
is skipped. Status, bytes and SHA-256 are written back to catalog.json.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]  # VeloxEditing
CHRONON = ROOT / "ChrononTemplate"
CATALOG = CHRONON / "golden_plans" / "date_animation_catalog" / "catalog.json"
CLI = ROOT / "Chronon3d" / "build" / "chronon" / "linux-video-release" / "apps" / "chronon3d_cli" / "chronon3d_cli"


def probe(path: Path) -> dict:
    return json.loads(subprocess.check_output([
        "ffprobe", "-v", "error", "-select_streams", "v:0",
        "-show_entries", "stream=width,height,r_frame_rate,nb_frames",
        "-show_entries", "format=duration",
        "-of", "json", str(path),
    ], text=True))


def finish(entry: dict, path: Path) -> None:
    info = probe(path)
    st = info["streams"][0]
    frames = int(st.get("nb_frames") or 0)
    expected = (1920, 1080, f"{entry['fps']}/1", int(entry["frames"]))
    actual = (int(st["width"]), int(st["height"]), st["r_frame_rate"], frames)
    if actual != expected:
        raise RuntimeError(f"unexpected stream: {st}; expected {expected}")
    entry["status"] = "rendered"
    entry["bytes"] = path.stat().st_size
    entry["sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
    entry["rendered_at"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--jobs", type=int, default=2)
    ap.add_argument("--only", default="", help="comma-separated slug prefixes")
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()
    jobs = max(1, min(2, args.jobs))
    only = [s.strip() for s in args.only.split(",") if s.strip()]

    catalog = json.loads(CATALOG.read_text())
    planned = []
    for entry in catalog["presets"]:
        if entry["status"] == "existing":
            continue
        if only and not any(entry["slug"].startswith(p) for p in only):
            continue
        if entry["status"] == "rendered" and not args.force:
            continue
        planned.append(entry)

    print(f"rendering {len(planned)} plans with {jobs} workers", flush=True)
    running = []
    failed = []
    while planned or running:
        while planned and len(running) < jobs:
            entry = planned.pop(0)
            out = CHRONON / entry["video"]
            out.parent.mkdir(parents=True, exist_ok=True)
            log_path = CHRONON / "renders" / "date_animation_catalog" / "logs" / f"{entry['slug']}.log"
            log_path.parent.mkdir(parents=True, exist_ok=True)
            log = log_path.open("w")
            cmd = [
                str(CLI), "render-plan",
                "--input", str(CHRONON / entry["plan"]),
                "--output", str(out),
                "--assets-root", str(CHRONON),
                "--backend", "vulkan",
                "--rate-control", "crf", "--crf", "14",
                "--encode-preset", "slow",
            ]
            p = subprocess.Popen(cmd, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT)
            running.append((entry, p, log, out, log_path))
            print(f"START {entry['slug']} -> {out}", flush=True)
        time.sleep(1)
        for item in running[:]:
            entry, p, log, out, log_path = item
            if p.poll() is None:
                continue
            log.close()
            running.remove(item)
            if p.returncode == 0:
                try:
                    finish(entry, out)
                    print(f"DONE  {entry['slug']} {entry['bytes']} bytes", flush=True)
                except Exception as exc:
                    entry["status"] = "failed"
                    entry["error"] = str(exc)
                    failed.append(entry["slug"])
                    print(f"FAIL  {entry['slug']}: {exc}", flush=True)
            else:
                entry["status"] = "failed"
                entry["error"] = f"render exit {p.returncode}"
                failed.append(entry["slug"])
                print(f"FAIL  {entry['slug']} log={log_path}", flush=True)
                print(log_path.read_text(errors="replace")[-1200:], flush=True)
            CATALOG.write_text(json.dumps(catalog, indent=2, ensure_ascii=False) + "\n")

    CATALOG.write_text(json.dumps(catalog, indent=2, ensure_ascii=False) + "\n")
    print(f"finished failures={failed}", flush=True)
    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main())
