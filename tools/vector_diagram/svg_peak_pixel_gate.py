#!/usr/bin/env python3
"""Raw-pixel gate for an imported SVG path and a marker following its geometry.

This renders an SVG asset through Chronon3D's software raw sink, checks its
pixels and marker centroids at f0/f15/f30/f44/f45, and repeats for deterministic
equality. Trim progression is covered by the encoded showcase gate.
"""
from __future__ import annotations

import argparse
import copy
import json
import math
import os
import subprocess
import tempfile
from pathlib import Path

WIDTH, HEIGHT = 320, 180
SAMPLE_FRAMES = (0, 15, 30, 45, 60)
POINTS = ((32.0, 146.0), (96.0, 88.0), (128.0, 76.0),
          (166.0, 40.0), (210.0, 22.0), (278.0, 140.0))
FRAME_BYTES = WIDTH * HEIGHT * 4


def path_commands():
    half = (WIDTH / 2.0, HEIGHT / 2.0)
    relative = [(x - half[0], half[1] - y) for x, y in POINTS]
    return ([{"type": "move_to", "point": list(POINTS[0])}] +
            [{"type": "line_to", "point": list(point)} for point in POINTS[1:]])


def svg_text():
    path = "M " + " L ".join(f"{x:g} {y:g}" for x, y in POINTS)
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" '
            f'height="{HEIGHT}" viewBox="0 0 {WIDTH} {HEIGHT}">'
            f'<path id="peak_line" d="{path}" fill="none" stroke="#E8EBF0" '
            'stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/>'
            '</svg>')


def plan(layers):
    return {
        "schema": "chronon.render-plan.v3", "version": 3,
        "job_id": "svg_peak_pixel_gate",
        "canvas": {"width": WIDTH, "height": HEIGHT, "fps_num": 30,
                   "fps_den": 1, "duration_frames": 90},
        "layers": layers,
        "output": {"path": "svg_peak_pixel_gate.mp4", "format": "mp4"},
    }


def scene_layers():
    return [
            {"id": "peak_svg", "type": "shape", "position": [WIDTH / 2, HEIGHT / 2],
             "size": [WIDTH, HEIGHT], "shape": {
                 "type": "path", "asset": "peak.svg"}},
            {"id": "yellow_marker", "type": "shape", "position": [0.0, 0.0],
             "size": [12.0, 12.0], "shape": {"type": "ellipse",
                 "fill": [1.0, 0.86, 0.08, 1.0]},
             "follow_path": {"path_commands": path_commands(),
                 "progress": {"easing": "linear", "keyframes": [
                     {"frame": 0, "value": 0.0},
                     {"frame": 60, "value": 1.0}]},
                 "auto_orient": False, "clamp_end": True}},
        ]


def expected_marker(frame: int) -> tuple[float, float]:
    segments = [math.dist(a, b) for a, b in zip(POINTS, POINTS[1:])]
    remaining = sum(segments) * frame / 60.0
    for (a, b), length in zip(zip(POINTS, POINTS[1:]), segments):
        if remaining <= length:
            fraction = remaining / length
            return (a[0] + (b[0] - a[0]) * fraction,
                    a[1] + (b[1] - a[1]) * fraction)
        remaining -= length
    return POINTS[-1]


def analyse_frame(frame: bytes) -> tuple[int, tuple[float, float] | None]:
    svg_pixels = 0
    yellow = 0
    sum_x = 0
    sum_y = 0
    for offset in range(0, len(frame), 4):
        red, green, blue, alpha = frame[offset:offset + 4]
        pixel = offset // 4
        x, y = pixel % WIDTH, pixel // WIDTH
        svg_pixels += red > 200 and green > 200 and blue > 205 and alpha > 128
        if red > 225 and green > 160 and 0 <= blue < 100 and alpha > 160:
            yellow += 1
            sum_x += x
            sum_y += y
    centroid = (sum_x / yellow, sum_y / yellow) if yellow else None
    return svg_pixels, centroid


def glow_delta_in_ring(glow_frame: bytes, plain_frame: bytes,
                       center: tuple[float, float], inner: float,
                       outer: float) -> int:
    cx, cy = center
    changed = 0
    for offset in range(0, len(glow_frame), 4):
        pixel = offset // 4
        x, y = pixel % WIDTH, pixel // WIDTH
        distance = math.hypot(x - cx, y - cy)
        if inner <= distance <= outer and glow_frame[offset:offset + 3] != plain_frame[offset:offset + 3]:
            changed += 1
    return changed


def changed_pixels_in_disk(frame_a: bytes, frame_b: bytes,
                           center: tuple[float, float], radius: float) -> int:
    cx, cy = center
    changed = 0
    for offset in range(0, len(frame_a), 4):
        pixel = offset // 4
        x, y = pixel % WIDTH, pixel // WIDTH
        if math.hypot(x - cx, y - cy) <= radius and frame_a[offset:offset + 4] != frame_b[offset:offset + 4]:
            changed += 1
    return changed


def render(cli: Path, root: Path, output: Path, layers) -> bytes:
    (root / "plan.json").write_text(json.dumps(plan(layers)))
    command = [str(cli), "render", "--plan", str(root / "plan.json"),
               "--assets-root", str(root), "--backend", "software",
               "--video-sink", "raw",
               "--output", str(output)]
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode:
        raise RuntimeError((result.stdout + "\n" + result.stderr)[-6000:])
    raw = output.read_bytes()
    if len(raw) != FRAME_BYTES * 90:
        raise RuntimeError(f"raw sink returned {len(raw)} bytes, expected "
                           f"{FRAME_BYTES * 90} for frames 0..89")
    return raw


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cli", type=Path,
                        default=Path(os.environ["CHRONON_CLI"]) if os.environ.get("CHRONON_CLI") else None)
    args = parser.parse_args()
    if args.cli is None or not args.cli.is_file():
        parser.error("pass --cli or set CHRONON_CLI to an SVG-enabled chronon3d_cli")

    with tempfile.TemporaryDirectory(prefix="svg_peak_pixel_gate_") as temporary:
        root = Path(temporary)
        (root / "peak.svg").write_text(svg_text())
        svg_layer, marker_layer = scene_layers()
        svg_first = render(args.cli.resolve(), root, root / "svg_first.rgba", [svg_layer])
        svg_second = render(args.cli.resolve(), root, root / "svg_second.rgba", [svg_layer])
        marker_first = render(args.cli.resolve(), root, root / "marker_first.rgba", [marker_layer])
        marker_second = render(args.cli.resolve(), root, root / "marker_second.rgba", [marker_layer])
        # The static SVG source and animated marker must compose correctly
        # through the whole sequence, without forcing the SVG layer to be
        # frame-dependent with a constant-opacity workaround.
        unguarded = render(args.cli.resolve(), root, root / "combined_unguarded.rgba",
                           [svg_layer, marker_layer])
        unguarded_repeat = render(args.cli.resolve(), root,
                                  root / "combined_unguarded_repeat.rgba",
                                  [svg_layer, marker_layer])
        unguarded_counts = [analyse_frame(
            unguarded[frame * FRAME_BYTES:(frame + 1) * FRAME_BYTES])[0]
            for frame in SAMPLE_FRAMES]
        if min(unguarded_counts) < 30:
            raise RuntimeError(f"static SVG path pixels were lost during marker composition: {unguarded_counts}")

        svg_layer["animation"] = {"tracks": [{"property": "opacity",
            "keyframes": [{"frame": 0, "value": 1.0}, {"frame": 89, "value": 1.0}]}]}
        combined_first = render(args.cli.resolve(), root, root / "combined_first.rgba",
                                [svg_layer, marker_layer])
        combined_second = render(args.cli.resolve(), root, root / "combined_second.rgba",
                                 [svg_layer, marker_layer])
        glow_layer = copy.deepcopy(marker_layer)
        glow_layer["effects"] = [{"type": "glow", "radius": 16,
            "intensity": 0.8, "color": [1.0, 0.72, 0.1, 1.0]}]
        combined_glow = render(args.cli.resolve(), root, root / "combined_glow.rgba",
                               [svg_layer, glow_layer])
        combined_glow_repeat = render(args.cli.resolve(), root, root / "combined_glow_repeat.rgba",
                                      [svg_layer, glow_layer])
        if (svg_first != svg_second or marker_first != marker_second or
                unguarded != unguarded_repeat or
                combined_first != combined_second or combined_glow != combined_glow_repeat):
            raise RuntimeError("repeated raw renders differ pixel-for-pixel")

    samples = []
    for frame_number in SAMPLE_FRAMES:
        start = frame_number * FRAME_BYTES
        samples.append(analyse_frame(svg_first[start:start + FRAME_BYTES]))
    marker_samples = [analyse_frame(marker_first[frame * FRAME_BYTES:(frame + 1) * FRAME_BYTES])
                      for frame in SAMPLE_FRAMES]
    svg_counts = [sample[0] for sample in samples]
    if min(svg_counts) < 30:
        raise RuntimeError(f"imported SVG path pixels are missing: {svg_counts}")

    errors = []
    combined_errors = []
    combined_line_counts = []
    for frame_number, (_, centroid) in zip(SAMPLE_FRAMES, marker_samples):
        if centroid is None:
            raise RuntimeError(f"yellow marker is missing from frame {frame_number}")
        expected = expected_marker(frame_number)
        errors.append(math.dist(centroid, expected))
        offset = frame_number * FRAME_BYTES
        combined_pixels, combined_centroid = analyse_frame(
            combined_first[offset:offset + FRAME_BYTES])
        combined_line_counts.append(combined_pixels)
        if combined_centroid is None:
            raise RuntimeError(f"combined yellow marker is missing from frame {frame_number}")
        combined_errors.append(math.dist(combined_centroid, expected))
    if max(errors) > 2.0:
        raise RuntimeError(f"rendered marker leaves the source path: errors={errors}")
    if min(combined_line_counts) < min(svg_counts) - 16:
        raise RuntimeError(f"SVG path pixels were lost under marker composition: {combined_line_counts}")
    if max(combined_errors) > 2.0:
        raise RuntimeError(f"combined marker leaves the source path: errors={combined_errors}")

    glow_frame_number = 60
    glow_offset = glow_frame_number * FRAME_BYTES
    glow_frame = combined_glow[glow_offset:glow_offset + FRAME_BYTES]
    plain_frame = combined_first[glow_offset:glow_offset + FRAME_BYTES]
    current_center = expected_marker(glow_frame_number)
    old_center = expected_marker(30)
    glow_pixels = glow_delta_in_ring(glow_frame, plain_frame, current_center, 8, 16)
    stale_pixels = changed_pixels_in_disk(glow_frame, plain_frame, old_center, 14)
    if glow_pixels < 10:
        raise RuntimeError(f"moving marker glow halo is missing: {glow_pixels} changed pixels")
    if stale_pixels:
        raise RuntimeError(f"moving marker glow left {stale_pixels} pixels near its prior position")

    print(f"SVG-01 imported SVG pixel truth: PASS (f0/15/30/45/60={svg_counts})")
    print(f"SVG-03 marker pixel alignment: PASS (max centroid error={max(errors):.3f}px)")
    print(f"SVG-03 combined SVG+marker: PASS (path coverage f0/15/30/45/60={unguarded_counts})")
    print("SVG-08 unguarded sequence repeat: PASS (all raw RGBA frames match exactly)")
    print(f"SVG-04 marker glow: PASS ({glow_pixels} halo pixels; {stale_pixels} prior-position pixels)")
    print(f"SVG-08 repeat determinism: PASS (raw SVG, marker, combined, and glow renders match exactly)")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, json.JSONDecodeError) as error:
        print(f"SVG peak pixel gate failed: {error}", file=__import__("sys").stderr)
        raise SystemExit(1)
