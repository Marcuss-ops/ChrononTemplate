#!/usr/bin/env python3
"""Build responsive Chronon social-motion previews for landscape, square and vertical video."""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
from fractions import Fraction
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WORKSPACE = ROOT.parent
CHRONON = WORKSPACE / "Chronon3d"
DEFAULT_OUT = ROOT / "out/social_motion_pack_v1"
DRIVE_FOLDER = "1ATL0bnJXijNqFlKkgWye3PEAdAuQa1HI"
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
    "assets/images/dual_entity_left.png",
    "assets/images/dual_entity_right.png",
    "assets/images/card_trio_1.png",
    "assets/images/card_trio_2.png",
    "assets/images/card_penta_5.png",
]
SLOGANS = {
    "landscape": ["MAKE EVERY FRAME COUNT", "BUILT FOR THE SCROLL", "STORIES THAT MOVE YOU"],
    "square": ["IDEAS IN MOTION", "MADE TO MAKE YOU LOOK", "TURN VIEWS INTO MOMENTS"],
    "vertical": ["SCROLL-STOPPING BY DESIGN", "YOUR NEXT BIG MOMENT", "CREATE. CAPTURE. REPEAT."],
}


def image_layout(fmt: str, count: int) -> tuple[list[tuple[float, float]], tuple[int, int]]:
    """Return responsive center-relative slots and card size for one to five images."""
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


def image_plan(fmt: str, count: int) -> dict:
    width, height = FORMATS[fmt]
    centers, (card_w, card_h) = image_layout(fmt, count)
    layers = [{"id": "background", "type": "color", "color": [0.025, 0.035, 0.065, 1.0],
               "start_frame": 0, "duration_frames": FRAMES}]
    for index, ((x, y), asset) in enumerate(zip(centers, ASSETS[:count])):
        delay = index * (5 if count > 1 else 0)
        axis = "position_y" if fmt == "vertical" or (fmt == "square" and count in (2, 3)) else "position_x"
        sign = -1 if (y if axis == "position_y" else x) < 0 else 1
        if x == 0 and y == 0:
            sign = -1 if index % 2 == 0 else 1
        shift = 72 * sign
        focus_frame = 28 + index * max(1, 90 // count)
        settle_frame = min(140, focus_frame + 18)
        tracks = [
            _track(axis, [(delay, shift), (delay + 24, 0), (FRAMES - 1, 0)], "out_cubic"),
            _track("opacity", [(delay, 0), (delay + 16, 1), (FRAMES - 1, 1)], "out_cubic"),
            _track("scale", [(0, 0.88), (delay + 24, 1.0), (focus_frame, 1.04),
                             (settle_frame, 0.97), (FRAMES - 1, 1.0)]),
        ]
        layers.append({"id": f"image_{index + 1}", "type": "image", "asset": asset,
                       "size": [card_w, card_h], "position": [x, y], "fit": "cover",
                       # Source cards already carry an anti-aliased rounded alpha mask.
                       # Applying a second runtime mask caused dark edge halos in export.
                       "radius": 0, "enable_3d": False, "start_frame": 0,
                       "duration_frames": FRAMES, "animation": {"tracks": tracks}})
    plan_id = f"social_{fmt}_image_{count}"
    return {"schema": "chronon.render-plan.v3", "version": 3, "job_id": plan_id,
            "canvas": {"width": width, "height": height, "fps_num": FPS, "fps_den": 1,
                       "duration_frames": FRAMES},
            "output": {"path": f"{plan_id}.mp4", "format": "mp4", "codec": "h264"},
            "layers": layers}


def phrase_plan(fmt: str) -> dict:
    width, height = FORMATS[fmt]
    size = 104 if fmt == "landscape" else (74 if fmt == "square" else 82)
    box = [round(width * 0.88), round(height * 0.25)]
    layers = [{"id": "background", "type": "color", "color": [0.025, 0.035, 0.065, 1.0],
               "start_frame": 0, "duration_frames": FRAMES}]
    for index, phrase in enumerate(SLOGANS[fmt]):
        start = index * 48
        end = 149 if index == len(SLOGANS[fmt]) - 1 else start + 48
        opacity_keys = [(0, 0)]
        if start > 0:
            opacity_keys.append((start, 0))
        opacity_keys.extend([(start + 10, 1), (end - 9 if index == len(SLOGANS[fmt]) - 1 else end - 9, 1)])
        if end < FRAMES - 1:
            opacity_keys.append((end, 0))
        position_keys = [(0, 22)]
        if start > 0:
            position_keys.append((start, 22))
        position_keys.append((start + 16, 0))
        if end < FRAMES - 1:
            position_keys.append((end, -14))
        else:
            position_keys.append((end, 0))
        layers.append({
            "id": f"phrase_{index + 1}", "type": "text", "text": phrase,
            "position": [width / 2, height / 2], "size": box,
                        "style": {"font": "assets/fonts/Inter-Bold.ttf", "font_size": size,
                      "min_font_size": max(28, size - 22), "max_font_size": size,
                      "fit_mode": "shrink_only", "fill": "#F5F3F7"},
            "start_frame": 0, "duration_frames": FRAMES,
            "animation": {"tracks": [
                _track("position_y", position_keys, "out_cubic"),
                _track("opacity", opacity_keys, "out_cubic"),
                _track("scale", [(0, 0.96), (start + 14, 1.0), (149, 1.0)]),
            ]},
        })
    plan_id = f"social_{fmt}_phrases"
    return {"schema": "chronon.render-plan.v3", "version": 3, "job_id": plan_id,
            "canvas": {"width": width, "height": height, "fps_num": FPS, "fps_den": 1,
                       "duration_frames": FRAMES},
            "output": {"path": f"{plan_id}.mp4", "format": "mp4", "codec": "h264"},
            "layers": layers}


def all_plans() -> list[dict]:
    plans = [image_plan(fmt, count) for fmt in FORMATS for count in range(1, 6)]
    plans.extend(phrase_plan(fmt) for fmt in FORMATS)
    return plans


def validate_contract(plan: dict) -> None:
    fmt = next((key for key in FORMATS if plan["job_id"].startswith(f"social_{key}_")), None)
    if fmt is None:
        raise ValueError("unknown social format")
    width, height = FORMATS[fmt]
    if plan["canvas"] != {"width": width, "height": height, "fps_num": FPS,
                          "fps_den": 1, "duration_frames": FRAMES}:
        raise ValueError(f"{plan['job_id']}: wrong canvas")
    layers = plan["layers"]
    images = [layer for layer in layers if layer["type"] == "image"]
    if images:
        count = int(plan["job_id"].rsplit("_", 1)[1])
        if len(images) != count:
            raise ValueError(f"{plan['job_id']}: expected {count} simultaneous images")
        centers, size = image_layout(fmt, count)
        if len(centers) != count:
            raise ValueError("image layout count mismatch")
        for layer, center in zip(images, centers):
            if layer["position"] != list(center) or layer["size"] != list(size):
                raise ValueError(f"{plan['job_id']}: image does not use its responsive slot")
            if layer["duration_frames"] != FRAMES or layer["fit"] != "cover":
                raise ValueError(f"{plan['job_id']}: image does not cover the full scene")
            if layer.get("radius", 0) != 0:
                raise ValueError(f"{plan['job_id']}: preserve the pre-masked corner alpha; runtime radius causes edge halos")
            if layer.get("enable_3d", False):
                raise ValueError(f"{plan['job_id']}: flat image cards must not receive 3D depth grading")
            if max(key["value"] for track in layer["animation"]["tracks"] if track["property"] == "scale"
                   for key in track["keyframes"]) > 1.05:
                raise ValueError(f"{plan['job_id']}: focus scale exceeds 1.05x")
            x, y = center
            w, h = size
            if abs(x) + w * 1.05 / 2 > width / 2 or abs(y) + h * 1.05 / 2 > height / 2:
                raise ValueError(f"{plan['job_id']}: focus scale clips an image outside the canvas")
        return
    phrases = [layer for layer in layers if layer["type"] == "text"]
    if len(phrases) != 3 or [layer["text"] for layer in phrases] != SLOGANS[fmt]:
        raise ValueError(f"{plan['job_id']}: expected three English web phrases")
    if any(layer["style"].get("fit_mode") != "shrink_only" for layer in phrases):
        raise ValueError(f"{plan['job_id']}: phrase must fit within the responsive safe box")


def cli_arguments(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cli", type=Path, default=CHRONON / "build/chronon/linux-video-fast-dev/apps/chronon3d_cli/chronon3d_cli")
    parser.add_argument("--assets-root", type=Path, default=CHRONON)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--validate-only", action="store_true", help="write and validate plans without rendering")
    parser.add_argument("--render", action="store_true", help="render the complete 18-video pack locally")
    parser.add_argument("--force-render", action="store_true", help="render even when a current MP4 already exists")
    parser.add_argument("--images-only", action="store_true", help="validate/render only the 15 image compositions")
    parser.add_argument("--format", dest="formats", action="append", choices=tuple(FORMATS), help="limit the selection to one or more social formats")
    parser.add_argument("--mirror-output-dir", type=Path, help="also copy generated plans, MP4s and timing sidecars to this delivery directory")
    parser.add_argument("--upload", action="store_true", help="upload the complete verified MP4 set to Google Drive")
    parser.add_argument("--drive-uploader", type=Path, default=UPLOADER)
    parser.add_argument("--drive-credentials", type=Path, default=CREDENTIALS)
    parser.add_argument("--drive-token", type=Path, default=TOKEN)
    parser.add_argument("--drive-folder", default=DRIVE_FOLDER)
    return parser.parse_args(argv)


def verify_video(path: Path, fmt: str) -> None:
    expected = FORMATS[fmt]
    probe = subprocess.run(["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", str(path)],
                           capture_output=True, text=True, check=True)
    metadata = json.loads(probe.stdout)
    stream = next((item for item in metadata["streams"] if item.get("codec_type") == "video"), None)
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
        raise FileNotFoundError("Google Drive OAuth files are missing; pass --drive-credentials and --drive-token")
    help_result = subprocess.run([str(args.drive_uploader), "-h"], capture_output=True, text=True)
    if "-sha256" not in help_result.stderr + help_result.stdout:
        raise RuntimeError("Drive uploader lacks SHA-256 verification support")
    manifest = []
    for path in paths:
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        result = subprocess.run([
            str(args.drive_uploader), "-credentials", str(args.drive_credentials),
            "-token", str(args.drive_token), "-folder", args.drive_folder,
            "-file", str(path), "-name", path.name, "-sha256", digest,
        ], capture_output=True, text=True, check=True)
        output = result.stdout.strip()
        if ("DRIVE_UPLOAD_PASS " not in output or f"parent={args.drive_folder}" not in output
                or f"sha256={digest}" not in output or f"bytes={path.stat().st_size}" not in output):
            raise RuntimeError(f"Drive upload verification failed for {path.name}: {output or result.stderr.strip()}")
        manifest.append({"file": path.name, "sha256": digest, "bytes": path.stat().st_size,
                         "verification": output})
        print(output, flush=True)
    return manifest


def main(argv=None) -> int:
    args = cli_arguments(argv)
    out_dir, assets_root, cli = args.output_dir.resolve(), args.assets_root.resolve(), args.cli.resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    plans = all_plans()
    if args.images_only and args.upload:
        raise SystemExit("--images-only cannot upload an incomplete 18-video pack")
    if args.images_only:
        plans = [plan for plan in plans if "_image_" in plan["job_id"]]
    if args.formats:
        selected_formats = set(args.formats)
        plans = [plan for plan in plans if any(plan["job_id"].startswith(f"social_{fmt}_") for fmt in selected_formats)]
    expected_count = len(plans)
    expected_ids = {plan["job_id"] for plan in plans}
    if not expected_count or len(expected_ids) != expected_count:
        raise RuntimeError("social motion selection must contain at least one uniquely named plan")
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
            subprocess.run([str(cli), "validate", "--plan", str(path), "--assets-root", str(assets_root)], check=True)
        written.append((plan, path))
    print(f"Validated {len(written)} responsive plans" + (" (image layouts only)." if args.images_only else " (image layouts and phrase reels)."))
    mirror_dir = args.mirror_output_dir.resolve() if args.mirror_output_dir else None
    if mirror_dir:
        mirror_dir.mkdir(parents=True, exist_ok=True)
        for _, plan_path in written:
            shutil.copy2(plan_path, mirror_dir / plan_path.name)
    if args.validate_only:
        return 0

    videos = []
    for plan, plan_path in written:
        fmt = next(key for key in FORMATS if plan["job_id"].startswith(f"social_{key}_"))
        video = out_dir / f"{plan['job_id']}.mp4"
        if args.render and (args.force_render or not video.is_file() or video.stat().st_mtime < plan_path.stat().st_mtime):
            subprocess.run([str(cli), "render", "--backend", "software", "--plan", str(plan_path),
                            "--assets-root", str(assets_root), "-o", str(video), "--ffmpeg-mode", "pipe",
                            "--codec", "h264", "--encode-preset", "fast"], check=True)
        if args.render or args.upload:
            if not video.is_file():
                raise FileNotFoundError(f"Missing rendered MP4: {video}; run with --render first")
            verify_video(video, fmt)
            videos.append(video)
            if mirror_dir:
                shutil.copy2(video, mirror_dir / video.name)
                timing = Path(f"{video}.timing.json")
                if timing.is_file():
                    shutil.copy2(timing, mirror_dir / timing.name)
    if args.upload:
        manifest = upload_videos(videos, args)
        (out_dir / "social_motion_pack_v1_upload_manifest.json").write_text(json.dumps({
            "destination_folder": args.drive_folder, "videos": manifest,
        }, indent=2) + "\n")
    elif args.render:
        print("Rendered and verified locally. No Google Drive request was made.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
