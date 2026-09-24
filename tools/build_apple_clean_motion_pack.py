#!/usr/bin/env python3
"""Build and certify ChrononTemplate's clean image/text motion pack.

The pack is intentionally self-contained under ChrononTemplate/out. It renders
image planes with hard (zero-radius) corners and restrained black-on-white
Inter typography with a subtle blurred drop shadow; no glow is authored.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[2]
TEMPLATE = ROOT / "ChrononTemplate"
RENDERER = ROOT / "Chronon3d/build/chronon/linux-video-release/apps/chronon3d_cli/chronon3d_cli"
ASSETS_ROOT = ROOT / "Chronon3d"
OUT_DEFAULT = TEMPLATE / "out/apple_clean_motion_pack_v1"
DURATION = 120
WIDTH = 1920
HEIGHT = 1080
FPS = 24


def kf(points: list[tuple[int, float]], easing: str = "out_cubic") -> dict[str, Any]:
    return {
        "keyframes": [{"frame": frame, "value": value} for frame, value in points],
        "easing": easing,
    }


def enter_hold_exit(start: float, overshoot: float, settle: float, easing: str = "out_cubic") -> dict[str, Any]:
    return kf([(0, start), (34, overshoot), (48, settle), (104, settle), (119, start)], easing)


def opacity_track() -> dict[str, Any]:
    return kf([(0, 0.0), (26, 1.0), (104, 1.0), (119, 0.0)], "linear")


IMAGE_MOTIONS: list[dict[str, Any]] = [
    {"id": "image_01_parallax_dolly", "label": "Parallax dolly", "tracks": {
        "position_z": enter_hold_exit(180, 24, 0), "scale": enter_hold_exit(1.12, 1.025, 1.0),
    }},
    {"id": "image_02_left_orbit", "label": "Left orbit settle", "tracks": {
        "rotation_y": enter_hold_exit(-20, 2.0, 0), "position_x": enter_hold_exit(-42, 5, 0),
        "scale": enter_hold_exit(1.04, 1.01, 1.0),
    }},
    {"id": "image_03_right_orbit", "label": "Right orbit settle", "tracks": {
        "rotation_y": enter_hold_exit(20, -2.0, 0), "position_x": enter_hold_exit(42, -5, 0),
        "scale": enter_hold_exit(1.04, 1.01, 1.0),
    }},
    {"id": "image_04_top_tilt", "label": "Top tilt reveal", "tracks": {
        "rotation_x": enter_hold_exit(15, -1.5, 0), "position_y": enter_hold_exit(32, -3, 0),
    }},
    {"id": "image_05_card_pitch", "label": "Card pitch", "tracks": {
        "rotation_x": enter_hold_exit(-12, 1.2, 0),
        "scale": enter_hold_exit(0.94, 1.015, 1.0),
    }},
    {"id": "image_06_diagonal_float", "label": "Diagonal float", "tracks": {
        "position_x": enter_hold_exit(-110, 8, 0), "rotation_z": enter_hold_exit(-3.5, 0.4, 0),
    }},
    {"id": "image_07_depth_lift", "label": "Depth lift", "tracks": {
        "position_z": enter_hold_exit(130, 16, 0), "rotation_x": enter_hold_exit(8, -0.8, 0),
        "scale": enter_hold_exit(0.96, 1.01, 1.0),
    }},
    {"id": "image_08_yaw_sweep", "label": "Yaw sweep", "tracks": {
        "rotation_y": kf([(0, -18.0), (30, -6.0), (52, 0.0), (82, 6.0), (104, 0.0), (119, -18.0)], "in_out_sine"),
        "position_x": enter_hold_exit(-24, 8, 0),
    }},
    {"id": "image_09_soft_push", "label": "Soft push and settle", "tracks": {
        "position_z": enter_hold_exit(220, 35, 0), "rotation_y": enter_hold_exit(9, -0.8, 0),
        "scale": enter_hold_exit(1.14, 1.025, 1.0),
    }},
    {"id": "image_10_plane_roll", "label": "Plane roll settle", "tracks": {
        "rotation_z": enter_hold_exit(5, -0.5, 0), "scale": enter_hold_exit(0.95, 1.01, 1.0),
    }},
]

TEXT_MOTIONS: list[dict[str, Any]] = [
    {"id": "text_01_quiet_fade", "label": "Quiet fade", "phrase": "Less, but better.", "tracks": {
        "position_y": enter_hold_exit(16, -1.5, 0),
    }},
    {"id": "text_02_soft_lift", "label": "Soft lift", "phrase": "Make room for better.", "tracks": {
        "position_y": enter_hold_exit(40, -3, 0), "scale": enter_hold_exit(0.985, 1.008, 1.0),
    }},
    {"id": "text_03_gentle_scale", "label": "Gentle scale", "phrase": "Designed to feel effortless.", "tracks": {
        "scale": enter_hold_exit(0.94, 1.012, 1.0),
    }},
    {"id": "text_04_editorial_left", "label": "Editorial from left", "phrase": "Simplicity is the ultimate.", "tracks": {
        "position_x": enter_hold_exit(-52, 4, 0), "opacity": opacity_track(),
    }},
    {"id": "text_05_editorial_right", "label": "Editorial from right", "phrase": "A little more clarity.", "tracks": {
        "position_x": enter_hold_exit(52, -4, 0), "opacity": opacity_track(),
    }},
    {"id": "text_06_center_open", "label": "Centered open", "phrase": "Focus on what matters.", "tracks": {
        "scale_x": enter_hold_exit(0.92, 1.012, 1.0), "opacity": opacity_track(),
    }},
    {"id": "text_07_rise_and_settle", "label": "Rise and settle", "phrase": "Made for everyday life.", "tracks": {
        "position_y": enter_hold_exit(30, -4, 0), "scale": enter_hold_exit(0.99, 1.006, 1.0),
        "opacity": opacity_track(),
    }},
    {"id": "text_08_subtle_drift", "label": "Subtle drift", "phrase": "Move forward, naturally.", "tracks": {
        "position_x": kf([(0, -22.0), (30, 4.0), (72, 0.0), (104, 0.0), (119, -22.0)], "in_out_sine"),
        "opacity": opacity_track(),
    }},
    {"id": "text_09_perspective_hint", "label": "Perspective hint", "phrase": "Thoughtfully in every detail.", "tracks": {
        "position_y": enter_hold_exit(12, -1, 0),
        "opacity": opacity_track(),
    }},
    {"id": "text_10_minimal_focus", "label": "Minimal focus", "phrase": "The power of less.", "tracks": {
        "scale": enter_hold_exit(1.035, 0.995, 1.0), "position_y": enter_hold_exit(8, -1, 0),
        "opacity": opacity_track(),
    }},
]


def make_plan(item: dict[str, Any], kind: str) -> dict[str, Any]:
    image = kind == "image"
    bg = [0.965, 0.968, 0.962, 1.0] if image else [1.0, 1.0, 1.0, 1.0]
    if image:
        subject: dict[str, Any] = {
            "id": "image", "type": "image", "asset": "assets/images/minimalist_landscape.png",
            "size": [1512, 850], "position": [960, 540], "fit": "cover", "radius": 0,
            "enable_3d": True,
        }
    else:
        subject = {
            "id": "phrase", "type": "text", "text": item["phrase"],
            "size": [1640, 360], "position": [960, 540],
            "style": {
                "font": "assets/fonts/Inter-Regular.ttf", "font_size": 124,
                "fill": "#111111", "stroke": {"color": "#111111", "width": 0},
                "shadow": {"color": "#000000", "opacity": 0.12, "blur": 7.0, "offset": [0.0, 4.0]},
            },
        }
    tracks = [
        {"property": prop, **track}
        for prop, track in item["tracks"].items()
    ]
    if image:
        tracks.append({"property": "opacity", **opacity_track()})
    if any(track["property"] in {"position_z", "rotation_x", "rotation_y", "scale_z"} for track in tracks):
        subject["enable_3d"] = True
    subject.update({
        "start_frame": 0,
        "duration_frames": DURATION,
        "animation": {"tracks": tracks},
    })
    layers = [
        {"id": "background", "type": "color", "color": bg, "size": [WIDTH * 2, HEIGHT * 2],
         "position": [WIDTH / 2, HEIGHT / 2],
         "start_frame": 0, "duration_frames": DURATION},
        subject,
    ]
    return {
        "schema": "chronon.render-plan.v2", "version": 2,
        "job_id": f"chronontemplate_apple_clean_{item['id']}",
        "canvas": {"width": WIDTH, "height": HEIGHT, "fps_num": FPS, "fps_den": 1,
                   "duration_frames": DURATION},
        "layers": layers,
        "output": {"path": f"{item['id']}.mp4", "format": "mp4", "codec": "h264"},
    }


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def probe(path: Path) -> dict[str, Any]:
    raw = subprocess.check_output([
        "ffprobe", "-v", "error", "-select_streams", "v:0", "-count_frames",
        "-show_entries", "stream=codec_name,width,height,avg_frame_rate,nb_read_frames",
        "-of", "json", str(path),
    ], text=True)
    stream = json.loads(raw)["streams"][0]
    return {"codec": stream["codec_name"], "width": int(stream["width"]),
            "height": int(stream["height"]), "fps": stream["avg_frame_rate"],
            "frames": int(stream["nb_read_frames"])}


def check_video(path: Path, item: dict[str, Any], kind: str, work: Path) -> dict[str, Any]:
    info = probe(path)
    if info != {"codec": "h264", "width": WIDTH, "height": HEIGHT,
                "fps": "24/1", "frames": DURATION}:
        raise RuntimeError(f"invalid encode metadata for {path.name}: {info}")
    subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-f", "null", "-"], check=True)
    hashes: dict[int, str] = {}
    previews: list[tuple[int, Image.Image]] = []
    for frame in (24, 48, 84):
        png = work / f"{path.stem}-{frame:03d}.png"
        subprocess.run([
            "ffmpeg", "-y", "-v", "error", "-i", str(path), "-vf",
            f"select=eq(n\\,{frame})", "-frames:v", "1", str(png),
        ], check=True)
        with Image.open(png) as frame_image:
            rgb = frame_image.convert("RGB")
            hashes[frame] = hashlib.sha256(rgb.tobytes()).hexdigest()
            previews.append((frame, rgb.copy()))
            if kind == "text" and frame == 48:
                top_edge = [rgb.getpixel((x, 4)) for x in (4, WIDTH // 4, WIDTH // 2, 3 * WIDTH // 4, WIDTH - 5)]
                bottom_edge = [rgb.getpixel((x, HEIGHT - 5)) for x in (4, WIDTH // 4, WIDTH // 2, 3 * WIDTH // 4, WIDTH - 5)]
                edge_samples = top_edge + bottom_edge
                if min(sum(pixel) / 3 for pixel in edge_samples) < 235:
                    raise RuntimeError(f"{path.name}: expected white canvas edges, got {edge_samples}")
                crop = rgb.crop((100, 250, WIDTH - 100, 830)).convert("L")
                dark = sum(1 for pixel in crop.getdata() if pixel < 75)
                if dark < 300:
                    raise RuntimeError(f"{path.name}: no visible black text at frame 48")
    if len(set(hashes.values())) < 2:
        raise RuntimeError(f"{path.name}: sampled frames show no animation")
    sheet = Image.new("RGB", (480 * 3, 270 + 28), "#f3f4f6")
    draw = ImageDraw.Draw(sheet)
    for index, (frame, image) in enumerate(previews):
        image.thumbnail((480, 270))
        sheet.paste(image, (index * 480, 28))
        draw.text((index * 480 + 10, 7), f"{path.stem} · frame {frame}", fill="#111111")
    return {"name": path.name, "sha256": sha256(path), "bytes": path.stat().st_size,
            "metadata": info, "sample_frames": [24, 48, 84], "visible_text_pixels": dark if kind == "text" else None,
            "sample_hashes": {str(k): v for k, v in hashes.items()}, "contact_sheet": sheet}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=OUT_DEFAULT)
    parser.add_argument("--emit-only", action="store_true", help="write plans without rendering")
    args = parser.parse_args()
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    if not args.emit_only and (not RENDERER.is_file() or shutil.which("ffmpeg") is None or shutil.which("ffprobe") is None):
        raise SystemExit("rendering requires the Chronon3D CLI build, ffmpeg and ffprobe")

    items = [("image", item) for item in IMAGE_MOTIONS] + [("text", item) for item in TEXT_MOTIONS]
    manifest: dict[str, Any] = {
        "schema": "chronontemplate.apple-clean-motion-pack.v1",
        "pipeline": "ChrononTemplate -> Chronon3D render-plan v2 -> H.264",
        "canvas": {"width": WIDTH, "height": HEIGHT, "fps": FPS, "frames": DURATION},
        "image_style": {"source": "assets/images/minimalist_landscape.png", "enable_3d": True, "corner_radius": 0},
        "text_style": {"font": "assets/fonts/Inter-Regular.ttf", "fill": "#111111",
                       "background": "#FFFFFF", "glow": None,
                       "shadow": {"color": "#000000", "opacity": 0.12, "blur": 7.0, "offset": [0, 4]}},
        "clips": [],
    }
    work = out / ".frames"
    if not args.emit_only:
        work.mkdir(exist_ok=True)
    contact_tiles: dict[str, list[Image.Image]] = {"images": [], "text": []}
    for kind, item in items:
        plan = make_plan(item, kind)
        plan_path = out / f"{item['id']}.plan.json"
        video_path = out / f"{item['id']}.mp4"
        plan_content = json.dumps(plan, indent=2) + "\n"
        if not plan_path.is_file() or plan_path.read_text() != plan_content:
            plan_path.write_text(plan_content)
        entry: dict[str, Any] = {"id": item["id"], "label": item["label"],
                                 "kind": kind, "plan": plan_path.name}
        if kind == "text":
            entry["phrase"] = item["phrase"]
        if not args.emit_only:
            if (not video_path.is_file() or video_path.stat().st_size == 0
                    or plan_path.stat().st_mtime_ns > video_path.stat().st_mtime_ns):
                log_path = out / f"{item['id']}.render.log"
                with log_path.open("w") as log:
                    try:
                        subprocess.run([
                            str(RENDERER), "render", "--plan", str(plan_path),
                            "--assets-root", str(ASSETS_ROOT), "--backend", "software",
                            "--profile", "production", "--codec", "h264", "--fps", "24",
                            "--crf", "18", "-o", str(video_path),
                        ], cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, check=True)
                    except subprocess.CalledProcessError as error:
                        tail = log_path.read_text(errors="replace").splitlines()[-30:]
                        raise RuntimeError(f"render failed for {item['id']} (see {log_path}):\\n" + "\\n".join(tail)) from error
            checked = check_video(video_path, item, kind, work)
            log_path = out / f"{item['id']}.render.log"
            if log_path.exists():
                log_path.unlink()
            contact_tiles["images" if kind == "image" else "text"].append(checked.pop("contact_sheet"))
            entry.update(checked)
            print(f"PASS {video_path.name} ({entry['bytes']} bytes)", flush=True)
        manifest["clips"].append(entry)

    (out / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    if not args.emit_only:
        for group, tiles in contact_tiles.items():
            sheet = Image.new("RGB", (480 * 3, 298 * 4), "#f3f4f6")
            draw = ImageDraw.Draw(sheet)
            for index, tile in enumerate(tiles):
                x, y = (index % 3) * 480, (index // 3) * 298
                sheet.paste(tile, (x, y))
            sheet.save(out / f"{group}_contact_sheet.jpg", quality=90)
        shutil.rmtree(work)
        manifest["contact_sheets"] = ["images_contact_sheet.jpg", "text_contact_sheet.jpg"]
        (out / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
        print(f"PASS built and verified {len(manifest['clips'])} clips in {out}")
    else:
        print(f"emitted {len(manifest['clips'])} render plans in {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
