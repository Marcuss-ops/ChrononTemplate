#!/usr/bin/env python3
"""Render five Chronon map moves and ten premium marker-label animations."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import cv2

HERE = Path(__file__).resolve().parent
TEMPLATE = HERE.parents[1]
ROOT = TEMPLATE.parent
OUT = TEMPLATE / "out" / "map_premium_animations_v1_20261003"
RENDERER = HERE / "render_dynamic_map_overlay.py"
sys.path.insert(0, str(HERE))
from render_geo_camera_small_places import MAP_LABEL_ANIMATIONS, draw_map_marker_label

MAP_STYLES = [
    ("01_signature_dive", "signature_dive", "Signature Dive", "Confident, smooth satellite descent."),
    ("02_tilt_reveal", "tilt_reveal", "Tilt Reveal", "A subtle horizon tilt as the camera lands."),
    ("03_orbit_arrival", "orbit_arrival", "Orbit Arrival", "A restrained yaw that adds dimensionality."),
    ("04_slow_approach", "slow_approach", "Slow Approach", "Longer, calmer approach with a clean hold."),
    ("05_wide_context", "wide_context", "Wide Context", "A wider landing that preserves nearby geography."),
]


def encode_label_variant(source: Path, output: Path, animation: str, title: str) -> None:
    capture = cv2.VideoCapture(str(source))
    if not capture.isOpened():
        raise RuntimeError(f"cannot open map source {source}")
    width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = capture.get(cv2.CAP_PROP_FPS) or 24.0
    raw_path = output.with_suffix(".raw.mp4")
    writer = cv2.VideoWriter(str(raw_path), cv2.VideoWriter_fourcc(*"mp4v"), fps,
                             (width, height))
    if not writer.isOpened():
        raise RuntimeError("OpenCV could not open the temporary MP4 writer")
    frames = int(capture.get(cv2.CAP_PROP_FRAME_COUNT))
    index = 0
    while True:
        ok, frame = capture.read()
        if not ok:
            break
        progress = index / max(1, frames - 1)
        draw_map_marker_label(frame, (width // 2, height // 2), title,
                              progress, animation)
        writer.write(frame)
        index += 1
    capture.release()
    writer.release()
    if index != frames:
        raise RuntimeError(f"{output.name}: encoded {index} of {frames} frames")
    subprocess.run([
        "ffmpeg", "-y", "-loglevel", "error", "-i", str(raw_path),
        "-an", "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
        "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(output),
    ], check=True)
    raw_path.unlink(missing_ok=True)


def render_map_variant(style_id: str, camera_animation: str, title: str,
                       description: str, map_label: str) -> Path:
    source = OUT / f"{style_id}.json"
    target = OUT / f"{style_id}.mp4"
    payload = {
        "width": 1920, "height": 1080,
        "fps_num": 24, "fps_den": 1, "duration_us": 5_000_000,
        "pins": [{"id": "new-orleans", "label": "New Orleans",
                  "latitude": 29.9561422, "longitude": -90.0733934,
                  "scope": "city"}],
        "area_glow_radius_km": 3.5,
        "camera_animation": camera_animation,
        "label_animation": map_label,
    }
    source.write_text(json.dumps(payload, separators=(",", ":")), encoding="utf-8")
    subprocess.run([sys.executable, str(RENDERER), "--input", str(source),
                    "--output", str(target)], check=True)
    return target


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    manifest = {
        "title": "Chronon Map Premium Animation Pack",
        "place": {"name": "New Orleans", "latitude": 29.9561422,
                  "longitude": -90.0733934},
        "canvas": "1920x1080, 24 fps, 5 seconds",
        "label_treatment": "white face, black keyline, soft cyan outer glow; positioned below the map beacon",
        "map_animations": [], "label_animations": [],
    }

    # Five real map-camera passes, each rendered through the ChrononTemplate
    # dynamic tile camera and its normal map acceptance gate.
    map_files: dict[str, Path] = {}
    for style_id, camera_animation, title, description in MAP_STYLES:
        print(f"[map-pack] rendering {title}", flush=True)
        if camera_animation == "signature_dive":
            clean_source = render_map_variant("00_label_comparison_source",
                                              camera_animation, title, description, "none")
            path = OUT / f"{style_id}.mp4"
            encode_label_variant(clean_source, path, "gentle_fade", "New Orleans")
        else:
            path = render_map_variant(style_id, camera_animation, title, description,
                                      "gentle_fade")
        map_files[style_id] = path
        manifest["map_animations"].append({"id": style_id, "name": title,
                                           "description": description,
                                           "file": path.name})

    # The label set shares one already-rendered Chronon camera move so the
    # comparison isolates typography and entrance timing.
    print("[map-pack] reusing clean Chronon signature-dive plate for label comparison", flush=True)
    clean = OUT / "00_label_comparison_source.mp4"
    for index, animation in enumerate(MAP_LABEL_ANIMATIONS, start=1):
        slug = f"{index:02d}_{animation}"
        target = OUT / f"label_{slug}.mp4"
        print(f"[map-pack] encoding label {index}/{len(MAP_LABEL_ANIMATIONS)}: {animation}", flush=True)
        encode_label_variant(clean, target, animation, "New Orleans")
        manifest["label_animations"].append({"id": animation,
                                              "name": animation.replace("_", " ").title(),
                                              "file": target.name})

    # Representative stills make the collection browsable in Drive without
    # requiring every video to be opened first.
    for path in list(map_files.values()) + [OUT / f"label_{i:02d}_{name}.mp4"
                                             for i, name in enumerate(MAP_LABEL_ANIMATIONS, 1)]:
        still = OUT / f"{path.stem}.jpg"
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-ss", "4.4",
                        "-i", str(path), "-frames:v", "1", "-q:v", "3", str(still)], check=True)
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    readme = ["# Chronon Map Premium Animation Pack", "",
              "All clips were rendered from the ChrononTemplate dynamic satellite-map runtime.",
              "The map camera variants use real tile-pyramid camera motion. The label variants share a clean Chronon map render and isolate the text entrance.",
              "Every label has a white face, black stroke and soft cyan glow and sits below the point beacon.", "",
              "## Map camera animations", ""]
    readme.extend(f"- **{x['name']}** — {x['description']} `{x['file']}`" for x in manifest["map_animations"])
    readme.extend(["", "## Marker label animations", ""])
    readme.extend(f"- **{x['name']}** — `{x['file']}`" for x in manifest["label_animations"])
    (OUT / "README.md").write_text("\n".join(readme) + "\n", encoding="utf-8")
    print(f"[map-pack] complete: {OUT}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
