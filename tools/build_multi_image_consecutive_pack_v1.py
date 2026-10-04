#!/usr/bin/env python3
"""Build, render and optionally upload the multi-image consecutive motion pack v1.

Four NEW composed animation styles for the x2/x3/x4/x5 multi-image layouts,
authored as flat keyframe tracks (ChrononMotion "zona franca" style: every
style is data, not a C++ plugin):

  fan_rollout_v1   — cards fan out from the centre: slide from the stack slot
                     to their layout slot with rotation and a spring settle.
  depth_wave_v1    — cards rise out of Z (enable_3d): depth_cascade-style
                     perspective roll with per-card phase offsets.
  carousel_swing_v1— cards swing in from alternating top corners with
                     out_back overshoot on rotation_z, then settle straight.
  photo_boom_v1    — pop-z entrance: scale from 0.55 with position_z punch and
                     out_back scale overshoot, alternating every other card.

Every plan keeps the social contract proven by build_social_motion_pack_v1.py:
flat cards (no runtime radius), cover fit, full-duration presence, focus scale
<= 1.05 that never clips the canvas, and responsive per-format slots.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
from fractions import Fraction
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKSPACE = ROOT.parent
CHRONON = WORKSPACE / "Chronon3d"
DEFAULT_OUT = ROOT / "out/multi_image_consecutive_pack_v1"
# Target operator folder for this pack (requested 2026-10-04).
DRIVE_FOLDER = "1J_xUGo_bchzXDIGqSX04CU44c_Dm3SxS"
UPLOADER = WORKSPACE / "RenderingGen/bin/drive-upload"
CREDENTIALS = Path.home() / ".config/velox/credentials.json"
TOKEN = Path.home() / ".config/velox/token.json"
FPS, FRAMES = 30, 150

FORMATS = {
    "landscape": (1920, 1080),
    "square": (1080, 1080),
    "vertical": (1080, 1920),
}
ASSETS = [
    "assets/images/card_trio_1.png",
    "assets/images/card_trio_2.png",
    "assets/images/card_penta_1.png",
    "assets/images/card_penta_2.png",
    "assets/images/card_penta_3.png",
]
STYLES = ("fan_rollout_v1", "depth_wave_v1", "carousel_swing_v1", "photo_boom_v1")

# Responsive slots, shared with the social pack contract.
def image_layout(fmt: str, count: int) -> tuple[list[tuple[float, float]], tuple[int, int]]:
    if count == 1:
        w, h = FORMATS[fmt]
        return [(0, 0)], (round(w * (0.48 if fmt == "landscape" else 0.72)),
                         round(h * (0.68 if fmt == "landscape" else 0.48)))
    if fmt == "landscape":
        if count == 2:
            return [(-330, 0), (330, 0)], (560, 700)
        if count == 3:
            return [(-610, 0), (0, 0), (610, 0)], (430, 570)
        if count == 4:
            return [(-295, -205), (295, -205), (-295, 205), (295, 205)], (520, 365)
        return [(0, -25), (-555, -270), (555, -270), (-555, 270), (555, 270)], (500, 430)
    if fmt == "square":
        if count == 2:
            return [(0, -185), (0, 185)], (550, 350)
        if count == 3:
            return [(0, -335), (0, 0), (0, 335)], (560, 290)
        if count == 4:
            return [(-210, -175), (210, -175), (-210, 175), (210, 175)], (390, 310)
        return [(0, 0), (-290, -300), (290, -300), (-290, 300), (290, 300)], (390, 300)
    if count == 2:
        return [(0, -440), (0, 440)], (680, 430)
    if count == 3:
        return [(0, -570), (0, 0), (0, 570)], (640, 390)
    if count == 4:
        return [(-245, -245), (245, -245), (-245, 245), (245, 245)], (455, 430)
    return [(0, 0), (-245, -635), (245, -635), (-245, 635), (245, 635)], (490, 420)


def _track(prop: str, keys: list[tuple[int, float]], easing: str = "in_out_cubic") -> dict:
    return {"property": prop, "easing": easing,
            "keyframes": [{"frame": frame, "value": value} for frame, value in keys]}


def _delayed(prop: str, delay: int, value: float, keys: list[tuple[int, float]],
             easing: str = "in_out_cubic") -> dict:
    """A track holding `value` until `delay` then moving through `keys`."""
    full = [(0, value)]
    if delay > 0:
        full.append((delay, value))
    full.extend(keys)
    return _track(prop, full, easing)


def _stack_slot(index: int, count: int, fmt: str) -> tuple[float, float]:
    """Where card `index` starts inside the centre stack before fanning out."""
    if fmt == "vertical":
        return (0, 0) if index == 0 else (0, -60 - index * 30)
    return (0, 0) if index == 0 else (index * 26, -34 - index * 26)


def _tracks_fan_rollout(index: int, count: int, fmt: str, slot: tuple[float, float],
                        card_w: int, card_h: int) -> list[dict]:
    x, y = slot
    sx, sy = _stack_slot(index, count, fmt)
    delay = index * 6
    # Slide from the stack slot to the layout slot with a quarter-turn settle.
    return [
        _delayed("position_x", delay, sx, [(delay + 30, x), (FRAMES - 1, x)], "in_out_cubic"),
        _delayed("position_y", delay, sy, [(delay + 30, y), (FRAMES - 1, y)], "in_out_cubic"),
        _delayed("rotation_z", delay, -14 if index % 2 else 14,
                 [(delay + 26, 0), (FRAMES - 1, 0)], "out_cubic"),
        _delayed("opacity", delay, 0, [(delay + 12, 1), (FRAMES - 1, 1)], "out_cubic"),
        _track("scale", [(0, 0.82), (delay + 30, 1.0), (delay + 44, 1.02), (FRAMES - 1, 1.0)]),
    ]


def _tracks_depth_wave(index: int, count: int, fmt: str, slot: tuple[float, float],
                       card_w: int, card_h: int) -> list[dict]:
    x, y = slot
    phase = index * 5
    rise = 520
    # Renderer contract: component tracks of the same axis group (position_x/y/z)
    # must share keyframes and easing whenever one of them is non-linear.
    return [
        _delayed("position_y", phase, y - 40, [(phase + 30, y), (FRAMES - 1, y)], "out_cubic"),
        _delayed("position_z", phase, rise, [(phase + 30, 0), (FRAMES - 1, 0)], "out_cubic"),
        _delayed("rotation_x", phase, -26, [(phase + 30, 0), (FRAMES - 1, 0)], "out_cubic"),
        _delayed("opacity", phase, 0, [(phase + 10, 1), (FRAMES - 1, 1)], "out_cubic"),
        _track("scale", [(0, 0.9), (phase + 30, 1.0), (phase + 46, 1.03), (FRAMES - 1, 1.0)]),
    ]


def _tracks_carousel_swing(index: int, count: int, fmt: str, slot: tuple[float, float],
                           card_w: int, card_h: int) -> list[dict]:
    x, y = slot
    delay = index * 7
    swing = 30 if index % 2 == 0 else -30
    # Renderer contract: rotation_x/y/z share keyframes and easing; position
    # tracks stay linear so the swing carries all the personality.
    return [
        _delayed("position_x", delay, x, [(FRAMES - 1, x)], "linear"),
        _delayed("position_y", delay, y, [(FRAMES - 1, y)], "linear"),
        _delayed("rotation_z", delay, swing,
                 [(delay + 34, 0), (FRAMES - 1, 0)], "out_back"),
        _delayed("rotation_y", delay, swing,
                 [(delay + 34, 0), (FRAMES - 1, 0)], "out_back"),
        _delayed("opacity", delay, 0, [(delay + 12, 1), (FRAMES - 1, 1)], "out_cubic"),
        _track("scale", [(0, 0.9), (delay + 34, 1.0), (delay + 50, 1.02), (FRAMES - 1, 1.0)]),
    ]


def _tracks_photo_boom(index: int, count: int, fmt: str, slot: tuple[float, float],
                       card_w: int, card_h: int) -> list[dict]:
    x, y = slot
    delay = index * 5
    even = index % 2 == 0
    # Renderer contract: position_x/y/z share keyframes and easing; the constant
    # x/y tracks ride the same out_expo timeline as the z punch.
    return [
        _delayed("position_x", delay, x, [(delay + 22, x), (FRAMES - 1, x)], "out_expo"),
        _delayed("position_y", delay, y, [(delay + 22, y), (FRAMES - 1, y)], "out_expo"),
        _delayed("position_z", delay, 260 if even else 180,
                 [(delay + 22, 0), (FRAMES - 1, 0)], "out_expo"),
        _delayed("rotation_z", delay, -6 if even else 6,
                 [(delay + 22, 0), (FRAMES - 1, 0)], "out_cubic"),
        _delayed("opacity", delay, 0, [(delay + 8, 1), (FRAMES - 1, 1)], "out_expo"),
        _track("scale", [(0, 0.55), (delay + 24, 1.04), (delay + 36, 0.99), (FRAMES - 1, 1.0)],
               "out_back"),
    ]


TRACK_BUILDERS = {
    "fan_rollout_v1": _tracks_fan_rollout,
    "depth_wave_v1": _tracks_depth_wave,
    "carousel_swing_v1": _tracks_carousel_swing,
    "photo_boom_v1": _tracks_photo_boom,
}

# Styles that animate camera-backed Z properties; those layers must enable 3D.
Z3D_STYLES = {
    "depth_wave_v1": {"position_z", "rotation_x"},
    "photo_boom_v1": {"position_z"},
    "carousel_swing_v1": {"rotation_y"},
}


def image_plan(fmt: str, count: int, style: str) -> dict:
    width, height = FORMATS[fmt]
    centers, (card_w, card_h) = image_layout(fmt, count)
    layers = [{"id": "background", "type": "color", "color": [0.025, 0.035, 0.065, 1.0],
               "start_frame": 0, "duration_frames": FRAMES}]
    for index, ((x, y), asset) in enumerate(zip(centers, ASSETS[:count])):
        tracks = TRACK_BUILDERS[style](index, count, fmt, (x, y), card_w, card_h)
        props3d = {t["property"] for t in tracks} & Z3D_STYLES.get(style, set())
        layers.append({"id": f"image_{index + 1}", "type": "image", "asset": asset,
                       "size": [card_w, card_h], "position": [x, y], "fit": "cover",
                       # Source cards already carry an anti-aliased rounded alpha mask;
                       # a second runtime mask causes dark edge halos in export.
                       "radius": 0, "enable_3d": bool(props3d), "start_frame": 0,
                       "duration_frames": FRAMES, "animation": {"tracks": tracks}})
    plan_id = f"multiconsec_{style}_{fmt}_x{count}"
    return {"schema": "chronon.render-plan.v3", "version": 3, "job_id": plan_id,
            "canvas": {"width": width, "height": height, "fps_num": FPS, "fps_den": 1,
                       "duration_frames": FRAMES},
            "output": {"path": f"{plan_id}.mp4", "format": "mp4", "codec": "h264"},
            "layers": layers}


def all_plans() -> list[dict]:
    # x2..x5 are the multi-image consecutive matrix; x1 is the anchor probe.
    return [image_plan(fmt, count, style)
            for style in STYLES
            for fmt in FORMATS
            for count in range(1, 6)]


def validate_contract(plan: dict) -> None:
    job_id = plan["job_id"]
    # job_id shape: multiconsec_<style>_<fmt>_x<count>; style itself has underscores.
    parts = job_id.split("_")
    count = int(parts[-1][1:])
    fmt = parts[-2]
    style = "_".join(parts[1:-2])
    if style not in STYLES or fmt not in FORMATS or not 1 <= count <= 5:
        raise ValueError(f"{job_id}: malformed plan id")
    width, height = FORMATS[fmt]
    if plan["canvas"] != {"width": width, "height": height, "fps_num": FPS,
                          "fps_den": 1, "duration_frames": FRAMES}:
        raise ValueError(f"{job_id}: wrong canvas")
    layers = plan["layers"]
    images = [layer for layer in layers if layer["type"] == "image"]
    if len(images) != count:
        raise ValueError(f"{job_id}: expected {count} simultaneous images")
    centers, size = image_layout(fmt, count)
    for layer, center in zip(images, centers):
        if layer["position"] != list(center) or layer["size"] != list(size):
            raise ValueError(f"{job_id}: image does not use its responsive slot")
        if layer["duration_frames"] != FRAMES or layer["fit"] != "cover":
            raise ValueError(f"{job_id}: image does not cover the full scene")
        if layer.get("radius", 0) != 0:
            raise ValueError(f"{job_id}: preserve the pre-masked corner alpha")
        x, y = center
        w, h = size
        if max(key["value"] for track in layer["animation"]["tracks"]
               if track["property"] == "scale"
               for key in track["keyframes"]) > 1.05:
            raise ValueError(f"{job_id}: focus scale exceeds 1.05x")
        if abs(x) + w * 1.05 / 2 > width / 2 or abs(y) + h * 1.05 / 2 > height / 2:
            raise ValueError(f"{job_id}: focus scale clips an image outside the canvas")
        # Entrance delay must leave room for the settle before the last frame.
        delays = [key["frame"] for track in layer["animation"]["tracks"]
                  for key in track["keyframes"] if key["frame"] > 0]
        if delays and min(delays) + 40 > FRAMES - 1:
            raise ValueError(f"{job_id}: entrance starts too late to settle")


def verify_video(path: Path, fmt: str) -> None:
    expected = FORMATS[fmt]
    probe = subprocess.run(["ffprobe", "-v", "error", "-show_streams", "-show_format",
                            "-of", "json", str(path)], capture_output=True, text=True,
                           check=True)
    metadata = json.loads(probe.stdout)
    stream = next((item for item in metadata["streams"] if item.get("codec_type") == "video"),
                  None)
    if not stream or (stream.get("width"), stream.get("height")) != expected:
        raise RuntimeError(f"{path.name}: encoded resolution does not match {expected}")
    if Fraction(stream.get("avg_frame_rate", "0/1")) != FPS:
        raise RuntimeError(f"{path.name}: expected {FPS} fps")
    if abs(float(metadata["format"].get("duration", 0)) - FRAMES / FPS) > 0.15:
        raise RuntimeError(f"{path.name}: expected a five-second video")
    if path.stat().st_size < 2_000:
        raise RuntimeError(f"{path.name}: encoded MP4 is unexpectedly small")


def upload_videos(paths: list[Path], args) -> list[dict]:
    if not args.drive_uploader.is_file():
        raise FileNotFoundError(f"Drive uploader not found: {args.drive_uploader}")
    if not args.drive_credentials.is_file() or not args.drive_token.is_file():
        raise FileNotFoundError("Google Drive OAuth files are missing; "
                                "pass --drive-credentials and --drive-token")
    manifest = []
    for path in paths:
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        result = subprocess.run([
            str(args.drive_uploader), "-credentials", str(args.drive_credentials),
            "-token", str(args.drive_token), "-folder", args.drive_folder,
            "-subfolder", args.drive_subfolder,
            "-file", str(path), "-name", path.name, "-sha256", digest,
        ], capture_output=True, text=True, check=True)
        output = result.stdout.strip()
        if ("DRIVE_UPLOAD_PASS " not in output or f"sha256={digest}" not in output
                or f"bytes={path.stat().st_size}" not in output):
            raise RuntimeError(f"Drive upload verification failed for {path.name}: "
                               f"{output or result.stderr.strip()}")
        manifest.append({"file": path.name, "sha256": digest,
                         "bytes": path.stat().st_size, "verification": output})
        print(output, flush=True)
    return manifest


def cli_arguments(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cli", type=Path,
                        default=CHRONON / "build/chronon/linux-video-fast-dev/apps/chronon3d_cli/chronon3d_cli")
    parser.add_argument("--assets-root", type=Path, default=CHRONON)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--validate-only", action="store_true",
                        help="write and validate plans without rendering")
    parser.add_argument("--render", action="store_true",
                        help="render the complete pack locally")
    parser.add_argument("--force-render", action="store_true",
                        help="render even when a current MP4 already exists")
    parser.add_argument("--style", dest="styles", action="append", choices=STYLES,
                        help="limit the selection to one or more styles")
    parser.add_argument("--format", dest="formats", action="append", choices=tuple(FORMATS),
                        help="limit the selection to one or more social formats")
    parser.add_argument("--count", dest="counts", type=int, action="append", choices=(1, 2, 3, 4, 5),
                        help="limit the selection to one or more image counts")
    parser.add_argument("--upload", action="store_true",
                        help="upload the rendered MP4s to Google Drive")
    parser.add_argument("--drive-uploader", type=Path, default=UPLOADER)
    parser.add_argument("--drive-credentials", type=Path, default=CREDENTIALS)
    parser.add_argument("--drive-token", type=Path, default=TOKEN)
    parser.add_argument("--drive-folder", default=DRIVE_FOLDER)
    parser.add_argument("--drive-subfolder", default="multi_image_consecutive_pack_v1")
    return parser.parse_args(argv)


def main(argv=None) -> int:
    args = cli_arguments(argv)
    out_dir, assets_root, cli = args.output_dir.resolve(), args.assets_root.resolve(), args.cli.resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    plans = all_plans()
    if args.styles:
        plans = [p for p in plans if any(p["job_id"].startswith(f"multiconsec_{s}_") for s in args.styles)]
    if args.formats:
        plans = [p for p in plans if any(f"_{fmt}_x" in p["job_id"] for fmt in args.formats)]
    if args.counts:
        plans = [p for p in plans if int(p["job_id"].rsplit("_x", 1)[1]) in args.counts]
    expected_ids = {plan["job_id"] for plan in plans}
    if not plans or len(expected_ids) != len(plans):
        raise RuntimeError("selection must contain at least one uniquely named plan")
    written = []
    for plan in plans:
        validate_contract(plan)
        for layer in plan["layers"]:
            if layer["type"] == "image" and not (assets_root / layer["asset"]).is_file():
                raise FileNotFoundError(f"Missing image asset: {assets_root / layer['asset']}")
        path = out_dir / f"{plan['job_id']}.plan.json"
        content = json.dumps(plan, indent=2) + "\n"
        if not path.exists() or path.read_text() != content:
            path.write_text(content)
        if not args.validate_only:
            if not cli.is_file():
                raise FileNotFoundError(f"Chronon3D CLI not found: {cli}")
            subprocess.run([str(cli), "validate", "--plan", str(path),
                            "--assets-root", str(assets_root)], check=True)
        written.append((plan, path))
    print(f"Validated {len(written)} multi-image consecutive plans.")
    if args.validate_only:
        return 0

    videos = []
    for plan, plan_path in written:
        parts = plan["job_id"].split("_")
        fmt = parts[-2]
        video = out_dir / f"{plan['job_id']}.mp4"
        if args.render and (args.force_render or not video.is_file()
                            or video.stat().st_mtime < plan_path.stat().st_mtime):
            subprocess.run([str(cli), "render", "--backend", "software", "--plan", str(plan_path),
                            "--assets-root", str(assets_root), "-o", str(video),
                            "--ffmpeg-mode", "pipe", "--codec", "h264",
                            "--encode-preset", "fast"], check=True)
        if args.render or args.upload:
            if not video.is_file():
                raise FileNotFoundError(f"Missing rendered MP4: {video}; run with --render first")
            verify_video(video, fmt)
            videos.append(video)
    if args.upload:
        manifest = upload_videos(videos, args)
        (out_dir / "multi_image_consecutive_pack_v1_upload_manifest.json").write_text(
            json.dumps({"destination_folder": args.drive_folder,
                        "subfolder": args.drive_subfolder, "videos": manifest},
                       indent=2) + "\n")
        print(f"Uploaded {len(manifest)} verified videos to folder {args.drive_folder}.")
    elif args.render:
        print("Rendered and verified locally. No Google Drive request was made.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
