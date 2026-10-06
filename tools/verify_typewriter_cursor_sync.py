#!/usr/bin/env python3
"""Pixel audit for cursor-synchronized type-on previews.

Uses the exact cursor position tracks from each plan and sampled encoded MP4
frames. Neutral text ink must not pass the cursor on the cursor's current line.
Also checks cursor-track/render agreement, final text presence, and signature
colors for the four overlay effects plus the correction/highlighter treatments.
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "out/typewriter_modern_v1"
FPS = 30
TEXT_CURSOR_TOL = 45  # expected gap between cursor center and last glyph ink edge
TRACK_PIXEL_TOL = 55   # center estimate includes cursor glow/stroke
WINDOW = {
    "01": (0, 46), "02": (20, 58), "03": (0, 56), "04": (0, 56), "05": (44, 94),
    "06": (0, 56), "07": (0, 46), "08": (0, 56), "09": (0, 56), "10": (0, 56),
    "11": (0, 64), "12": (0, 56), "13": (0, 56), "14": (0, 56), "15": (0, 56),
}


def frames_for(key: str) -> list[int]:
    start, end = WINDOW[key]
    return sorted(set([*range(start, end + 1), 100, 149]))


def decode(mp4: Path, frames: list[int]) -> dict[int, np.ndarray]:
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        expr = "+".join(f"eq(n\\,{n})" for n in frames)
        subprocess.run(["ffmpeg", "-v", "error", "-i", str(mp4), "-vf",
                        f"select='{expr}'", "-vsync", "0", str(td / "f%03d.png")],
                       check=True, capture_output=True)
        files = sorted(td.glob("f*.png"))
        if len(files) != len(frames):
            raise RuntimeError(f"decoded {len(files)} frames; expected {len(frames)}")
        return {f: np.asarray(Image.open(img).convert("RGB"), dtype=np.uint8)
                for f, img in zip(frames, files)}


def neutral_ink(rgb: np.ndarray) -> np.ndarray:
    c = rgb.astype(np.int16)
    lo, hi = c.min(axis=2), c.max(axis=2)
    # Main white title only. Exclude pale gray cursor-blended pixels and
    # intentionally gray correction text so overlays cannot count as future ink.
    return (lo > 190) & ((hi - lo) < 62)


def red_cursor(rgb: np.ndarray) -> np.ndarray:
    r, g, b = (rgb[..., i].astype(np.int16) for i in range(3))
    return (r > 145) & (r > g * 1.45) & (r > b * 1.4) & (g < 135) & (b < 135)


def amber(rgb: np.ndarray) -> np.ndarray:
    r, g, b = (rgb[..., i].astype(np.int16) for i in range(3))
    return (r > 155) & (g > 100) & (r > g * 1.2) & (g > b * 1.5)


def track_map(plan: dict, prop: str) -> dict[int, float]:
    layer = next(l for l in plan["layers"] if l["id"] == "cursor")
    track = next(t for t in layer["animation"]["tracks"] if t["property"] == prop)
    return {int(k["frame"]): float(k["value"]) for k in track["keyframes"]}


def effect_pixel_count(key: str, imgs: dict[int, np.ndarray]) -> tuple[str, int] | None:
    if key == "02":
        rgb = imgs[24].astype(np.int16); m = (rgb[..., 1] > 145) & (rgb[..., 1] > rgb[..., 0] + 35) & (rgb[..., 1] > rgb[..., 2] + 15)
        return "scramble_teal", int(m.sum())
    if key == "06":
        rgb = imgs[30].astype(np.int16); m = (rgb[..., 0] > 145) & (rgb[..., 1] < 135) & (rgb[..., 2] < 135)
        return "beam_red", int(m.sum())
    if key == "09":
        return "highlighter_amber", int(amber(imgs[40]).sum())
    if key == "12":
        rgb = imgs[4].astype(np.int16)
        cyan = (rgb[..., 2] > 145) & (rgb[..., 2] > rgb[..., 0] + 35)
        red = (rgb[..., 0] > 145) & (rgb[..., 0] > rgb[..., 1] + 45) & (rgb[..., 1] < 140)
        return "rgb_glitch_colors", int(cyan.sum() + red.sum())
    return None


def audit(name: str, plan: dict, imgs: dict[int, np.ndarray]) -> tuple[list[str], dict]:
    key = name[:2]
    errors: list[str] = []
    xs, ys = track_map(plan, "position_x"), track_map(plan, "position_y")
    start, end = WINDOW[key]
    frame_deltas = []
    ahead = []
    cursor_misses = []
    for f in range(start, end + 1):
        rgb = imgs[f]
        x = 960.0 + xs[f]
        y = 540.0 + ys[f]
        red = red_cursor(rgb)
        # Check cursor only near its plan position; ignore blink-off frames.
        x0, x1 = max(0, int(x - 80)), min(rgb.shape[1], int(x + 80))
        y0, y1 = max(0, int(y - 100)), min(rgb.shape[0], int(y + 100))
        cm = red[y0:y1, x0:x1]
        cy, cx = np.nonzero(cm)
        if cx.size:
            actual_x = x0 + float(np.median(cx))
            frame_deltas.append(abs(actual_x - x))
        # Compare only neutral ink on the cursor's own line (wrap has two lines).
        ink = neutral_ink(rgb)
        row0, row1 = max(0, int(y - 65)), min(rgb.shape[0], int(y + 65))
        yy, xx = np.nonzero(ink[row0:row1, 160:1760])
        if xx.size:
            # Restrict to the run immediately left of the cursor. A whole-line
            # bbox incorrectly treats already-typed characters on a different
            # wrapped line as being ahead of the cursor.
            cols = np.unique(xx + 160)
            runs: list[tuple[int, int]] = []
            lo = hi = int(cols[0])
            for col in cols[1:]:
                col = int(col)
                if col - hi > 8:
                    runs.append((lo, hi))
                    lo = col
                hi = col
            runs.append((lo, hi))
            left_of_cursor = [run for run in runs if run[0] <= x + 35]
            right = max((run[1] for run in left_of_cursor), default=None)
            if right is not None and right > x + TEXT_CURSOR_TOL:
                ahead.append((f, right, round(x, 1)))
    if frame_deltas and max(frame_deltas) > TRACK_PIXEL_TOL:
        errors.append(f"rendered cursor differs from plan track by up to {max(frame_deltas):.1f}px")
    if ahead:
        errors.append("ink right edge ahead of cursor: " + ", ".join(
            f"f{f} edge={r} cursor={x}" for f, r, x in ahead[:8]))

    final_ink = int(neutral_ink(imgs[149]).sum())
    if final_ink < 800:
        errors.append(f"final text not visible enough: {final_ink} neutral pixels")

    effect = effect_pixel_count(key, imgs)
    if effect:
        threshold = 250 if key in ("02", "06", "12") else 700
        if effect[1] < threshold:
            errors.append(f"signature effect {effect[0]} weak/invisible: {effect[1]} pixels")

    # Correction copy is on at frame 20 and removed well before the corrected text.
    if key == "05":
        def gray_count(frame: int) -> int:
            a = imgs[frame].astype(np.int16)
            r, g, b = a[..., 0], a[..., 1], a[..., 2]
            return int(((r > 115) & (r < 215) & (g > 120) & (g < 225) &
                        (b > 130) & (b < 230) & (np.abs(r-g) < 30) &
                        (np.abs(g-b) < 30)).sum())
        if gray_count(20) < 500:
            errors.append("mistake text not visible at frame 20")
        if gray_count(44) > 300:
            errors.append(f"mistake text persists into corrected reveal: {gray_count(42)} pixels")

    return errors, {"frames_checked": end - start + 1,
                    "cursor_track_pixel_max_delta": round(max(frame_deltas), 2) if frame_deltas else None,
                    "max_text_ahead_px": max((r-x for _, r, x in ahead), default=0),
                    "final_neutral_ink_pixels": final_ink,
                    "signature_effect": effect[0] if effect else None,
                    "signature_effect_pixels": effect[1] if effect else None}


def main() -> int:
    failures, report = 0, {}
    plans = sorted(OUT.glob("*.plan.json"))
    if len(plans) != 15:
        print(f"expected 15 plans, found {len(plans)}")
        return 2
    for p in plans:
        name = p.name.removesuffix(".plan.json")
        key = name[:2]
        mp4 = OUT / f"{name}.mp4"
        try:
            plan = json.loads(p.read_text())
            requested = sorted(set([*range(WINDOW[key][0], WINDOW[key][1] + 1), 20, 24, 30, 40, 100, 149]))
            imgs = decode(mp4, requested)
            errors, stats = audit(name, plan, imgs)
        except Exception as exc:
            errors, stats = [f"audit error: {exc}"], {}
        status = "PASS" if not errors else "FAIL"
        failures += bool(errors)
        print(f"{status} {name}: {stats}")
        for error in errors:
            print("  -", error)
        report[name] = {"status": status, "errors": errors, **stats}
    (OUT / "logs/cursor_sync_report.json").write_text(json.dumps(report, indent=2) + "\n")
    print(f"\n{15-failures}/15 pass")
    return int(bool(failures))


if __name__ == "__main__":
    sys.exit(main())
