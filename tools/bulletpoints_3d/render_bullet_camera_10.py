#!/usr/bin/env python3
"""Emit and render ten centered bullet-point camera moves at 1080p."""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
TEMPLATE = ROOT / "ChrononTemplate"
BUILD = TEMPLATE / "build" / "table-orbit"
EMITTER = BUILD / "chronontemplate_emit_bullet_camera_10"
SOURCE = TEMPLATE / "tools" / "bulletpoints_3d" / "emit_bullet_camera_10.cpp"
MOTION_INCLUDE = ROOT / "ChrononMotion3d" / "include"
MOTION_LIBRARY = ROOT / "ChrononMotion3d" / "build" / "table-visual" / "libchrononmotion.a"
CLI = ROOT / "Chronon3d" / "build/chronon/linux-video-fast-dev/apps/chronon3d_cli/chronon3d_cli"
OUT = TEMPLATE / "out" / "bullet_camera_10"
DEST = Path("/mnt/c/Users/pater/OneDrive/Documenti/Chronomotion/MP4/MP4/BulletPoints")
ASSETS = ROOT / "Chronon3d"
NAMES = [
    "01_push_in", "02_pull_out", "03_orbit_left", "04_orbit_right",
    "05_lateral_track", "06_crane_down", "07_crane_up", "08_dolly_arc",
    "09_roll_reveal", "10_slow_drift",
]


def run(args: list[str]) -> None:
    subprocess.run([str(x) for x in args], cwd=ROOT, check=True)


def main() -> None:
    if not EMITTER.is_file():
        if not MOTION_LIBRARY.is_file():
            raise SystemExit(f"ChrononMotion3D library missing; build target chrononmotion first: {MOTION_LIBRARY}")
        OUT.mkdir(parents=True, exist_ok=True)
        run(["g++", "-std=c++20", "-O2", "-I", MOTION_INCLUDE, SOURCE, MOTION_LIBRARY,
             "-o", OUT / "chronontemplate_emit_bullet_camera_10"])
        emitter = OUT / "chronontemplate_emit_bullet_camera_10"
    else:
        emitter = EMITTER
    if not CLI.is_file():
        raise SystemExit(f"Chronon3D renderer missing: {CLI}")
    OUT.mkdir(parents=True, exist_ok=True)
    DEST.mkdir(parents=True, exist_ok=True)
    run([emitter, OUT / "plans"])
    videos: list[Path] = []
    for name in NAMES:
        plan = OUT / "plans" / f"{name}.plan.json"
        target = DEST / f"BulletPoints_{name}_1920x1080.mp4"
        raw = OUT / f"{name}.rgba"
        run([CLI, "render", "--plan", plan, "--assets-root", ASSETS,
             "--backend", "vulkan", "--frames", "0-149", "--fps", "30",
             "--video-sink", "raw", "-o", raw])
        run(["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pixel_format", "rgba",
             "-video_size", "1920x1080", "-framerate", "30", "-i", raw,
             "-an", "-c:v", "libx264", "-preset", "fast", "-crf", "20",
             "-pix_fmt", "yuv420p", "-movflags", "+faststart", target])
        probe = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0",
                                "-show_entries", "stream=width,height,r_frame_rate,nb_frames",
                                "-of", "json", target], check=True, capture_output=True, text=True)
        stream = json.loads(probe.stdout)["streams"][0]
        if (stream.get("width"), stream.get("height"), stream.get("r_frame_rate"),
                int(stream.get("nb_frames", 0))) != (1920, 1080, "30/1", 150):
            raise RuntimeError(f"unexpected output format for {target.name}: {stream}")
        raw.unlink(missing_ok=True)
        Path(str(raw) + ".timing.json").unlink(missing_ok=True)
        videos.append(target)

    # Opening, midpoint, and ending frames document each animation's framing.
    tiles: list[Path] = []
    for name, video in zip(NAMES, videos):
        for label, sec in (("start", "0"), ("middle", "2.5"), ("end", "4.9")):
            frame = OUT / f"{name}_{label}.jpg"
            run(["ffmpeg", "-y", "-v", "error", "-ss", sec, "-i", video,
                 "-frames:v", "1", "-vf", "scale=480:270", "-q:v", "3", frame])
            tiles.append(frame)
    # Contact sheet arranged by shot (three frames per row).
    from PIL import Image, ImageDraw
    sheet = Image.new("RGB", (3 * 500, 10 * 310), (18, 23, 29))
    draw = ImageDraw.Draw(sheet)
    for i, name in enumerate(NAMES):
        y = i * 310
        draw.text((10, y + 4), name.replace("_", " ").upper(), fill=(230, 226, 215))
        for j, label in enumerate(("start", "middle", "end")):
            image = Image.open(OUT / f"{name}_{label}.jpg")
            sheet.paste(image, (10 + j * 500, y + 28))
            draw.text((15 + j * 500, y + 291), label, fill=(190, 198, 205))
    sheet_path = DEST / "BulletPoints_camera_10_contact_sheet.jpg"
    sheet.save(sheet_path, quality=92)
    clip_manifest = []
    for name, video in zip(NAMES, videos):
        plan_data = json.loads((OUT / "plans" / f"{name}.plan.json").read_text(encoding="utf-8"))
        layer_text = {layer["id"]: layer.get("text", "") for layer in plan_data["layers"]}
        clip_manifest.append({"file": video.name, "camera_move": name[3:].replace("_", " "),
                              "headline": layer_text["bullet_text"],
                              "supporting_text": layer_text["supporting_text"]})
    (DEST / "BulletPoints_camera_10_manifest.json").write_text(json.dumps({
        "resolution": "1920x1080", "fps": 30, "duration_seconds": 5,
        "backend": "Chronon3D Vulkan", "camera_authoring": "ChrononMotion3D CameraRig in C++",
        "clips": clip_manifest, "contact_sheet": sheet_path.name,
    }, indent=2) + "\n", encoding="utf-8")
    print(f"Rendered {len(videos)} clips to {DEST}")
    print(f"Contact sheet: {sheet_path}")


if __name__ == "__main__":
    main()
