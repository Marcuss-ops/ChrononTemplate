#!/usr/bin/env python3
"""Compare full-frame map rendering in Git HEAD with the working-tree ROI path.

Run from any directory with the project Python dependencies installed:
  PYTHONPATH=/usr/lib/python3/dist-packages python3 ChrononTemplate/tools/map/benchmark_map_roi.py

The benchmark renders identical deterministic 1080p inputs, reports per-style
median latency and pixel differences, and writes a JSON report. Baseline source
is loaded from the map repository's current HEAD; no network or tile requests.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import statistics
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
RENDERER = HERE / "render_geo_camera_small_places.py"
WIDTH, HEIGHT = 1920, 1080
POINT = (WIDTH // 2, HEIGHT // 2)
LABEL = "Garlasco"
PROGRESS = 0.95
CAPTION_STYLE = {
    "font_family": "inter", "font_size_px": 92, "stroke_size": 2,
    "shadow_blur_px": 14, "shadow_opacity": 0.7, "glow_size": 10,
    "glow_intensity": 0.4, "fill": "#F8F5EA", "shadow_color": "#000000",
    "glow_color": "#FFFFFF",
}


def load_baseline(baseline_ref: str):
    root = Path(subprocess.check_output(
        ["git", "-C", str(HERE), "rev-parse", "--show-toplevel"], text=True).strip())
    relative = RENDERER.relative_to(root)
    resolved_ref = subprocess.check_output(
        ["git", "-C", str(root), "rev-parse", baseline_ref], text=True).strip()
    source = subprocess.check_output(
        ["git", "-C", str(root), "show",
         f"{resolved_ref}:{relative.as_posix()}"], text=True)
    temporary = tempfile.NamedTemporaryFile(
        mode="w", suffix="_before_roi.py", prefix="chronon_map_roi_", delete=False)
    try:
        temporary.write(source)
        temporary.close()
        spec = importlib.util.spec_from_file_location("renderer_before_roi", temporary.name)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module, Path(temporary.name)
    except Exception:
        Path(temporary.name).unlink(missing_ok=True)
        raise


def render_caption(module, frame):
    return module.draw_editorial_map_caption(
        frame, LABEL, PROGRESS, CAPTION_STYLE, "slow_fade")


def diff_metrics(before: np.ndarray, after: np.ndarray) -> dict:
    difference = np.abs(before.astype(np.int16) - after.astype(np.int16))
    return {
        "max_abs_channel": int(difference.max(initial=0)),
        "mean_abs_channel": float(difference.mean()),
        "changed_pixels_gt_1": int(np.count_nonzero(np.any(difference > 1, axis=2))),
        "pixel_count": int(before.shape[0] * before.shape[1]),
        "before_sha256": hashlib.sha256(before.tobytes()).hexdigest(),
        "after_sha256": hashlib.sha256(after.tobytes()).hexdigest(),
    }


def median_ms(render, module, base, repeats):
    samples = []
    for _ in range(repeats):
        frame = base.copy()
        start = time.perf_counter()
        render(module, frame)
        samples.append((time.perf_counter() - start) * 1000.0)
    return statistics.median(samples)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repeats", type=int, default=7)
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--baseline-ref", default="HEAD^",
                        help="Git revision before the ROI changes (default: HEAD^)")
    parser.add_argument("--output", type=Path,
                        default=Path("/tmp/map_roi_benchmark.json"))
    args = parser.parse_args()
    if args.repeats < 1:
        parser.error("--repeats must be >= 1")

    os.environ.setdefault("OPENCV_NUM_THREADS", "1")
    sys.path.insert(0, str(HERE))
    import cv2
    import render_geo_camera_small_places as current
    cv2.setNumThreads(1)
    baseline, temporary = load_baseline(args.baseline_ref)
    try:
        rng = np.random.default_rng(args.seed)
        base = (rng.random((HEIGHT, WIDTH, 3)) * 255).astype(np.uint8)
        cases = [
            (f"marker:{style}",
             lambda module, frame, style=style:
             module.draw_map_location_marker(frame, POINT, LABEL, PROGRESS, style))
            for style in current.MAP_LABEL_ANIMATIONS
        ]
        cases.append(("caption:slow_fade", render_caption))
        results = []
        for name, render in cases:
            before = base.copy()
            after = base.copy()
            render(baseline, before)
            render(current, after)
            before_ms = median_ms(render, baseline, base, args.repeats)
            after_ms = median_ms(render, current, base, args.repeats)
            metrics = diff_metrics(before, after)
            results.append({
                "case": name,
                "baseline_median_ms": before_ms,
                "working_tree_median_ms": after_ms,
                "speedup": before_ms / after_ms if after_ms else None,
                **metrics,
            })
            print(f"{name:32} before={before_ms:8.2f} ms "
                  f"after={after_ms:8.2f} ms speedup={before_ms / after_ms:6.2f}x "
                  f"maxdiff={metrics['max_abs_channel']} "
                  f"mean={metrics['mean_abs_channel']:.5f} "
                  f"pixels>1={metrics['changed_pixels_gt_1']}", flush=True)

        report = {
            "frame": {"width": WIDTH, "height": HEIGHT, "seed": args.seed,
                      "label": LABEL, "point": POINT, "progress": PROGRESS},
            "baseline_git_ref": subprocess.check_output(
                ["git", "-C", str(HERE), "rev-parse", args.baseline_ref],
                text=True).strip(),
            "repeats": args.repeats,
            "acceptance": "all compared channels differ by at most 1 LSB",
            "pass": all(row["max_abs_channel"] <= 1 for row in results),
            "results": results,
        }
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        print(f"report: {args.output}")
        return 0 if report["pass"] else 1
    finally:
        temporary.unlink(missing_ok=True)


if __name__ == "__main__":
    raise SystemExit(main())
