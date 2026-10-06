#!/usr/bin/env python3
"""Build and render a compact, GPU-native modern map animation mini-series."""
from __future__ import annotations

import argparse
import json
import math
import hashlib
import subprocess
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[2]
WORKSPACE = ROOT.parent
OUT = ROOT / "out" / "modern_gpu_map_series_v1"
CLI = WORKSPACE / "Chronon3d/build/chronon/linux-video-fast-dev/apps/chronon3d_cli/chronon3d_cli"
W, H, FPS, FRAMES = 1920, 1080, 30, 240
BOLD = "Chronon3d/assets/fonts/Poppins-Bold.ttf"
REGULAR = "Chronon3d/assets/fonts/Poppins-Regular.ttf"
WHITE = "#F5F4EE"
MINT = "#59E1C8"
GOLD = "#F2C36A"
BLUE = "#73C9F5"


def rgba(color: str, alpha: float = 1.0) -> list[float]:
    raw = color.lstrip("#")
    return [int(raw[i:i + 2], 16) / 255.0 for i in (0, 2, 4)] + [alpha]


def tr(prop: str, keys: list[tuple[int, float]], easing: str = "out_cubic") -> dict:
    return {"property": prop, "easing": easing,
            "keyframes": [{"frame": f, "value": v} for f, v in keys]}


def text(id_: str, value: str, xy: tuple[float, float], size: int, color: str,
         *, font: str = REGULAR, start: int = 0, duration: int | None = None,
         anim: list[dict] | None = None, box: tuple[int, int] = (1400, 90)) -> dict:
    duration = FRAMES - start if duration is None else duration
    return {"id": id_, "type": "text", "text": value, "size": list(box),
            "position": list(xy), "start_frame": start, "duration_frames": duration,
            "style": {"font": font, "font_size": size, "fill": color,
                      "stroke": {"color": "#071522", "width": 1.5}}}


def shape(id_: str, xy: tuple[float, float], diameter: float, color: str,
          start: int, anim: list[dict]) -> dict:
    duration = FRAMES - start
    return {"id": id_, "type": "shape", "shape": {"type": "ellipse", "fill": rgba(color),
            "stroke": {"color": WHITE, "width": 2}}, "size": [diameter, diameter],
            "position": list(xy), "start_frame": start, "duration_frames": duration}


def project(lon: float, lat: float) -> tuple[float, float]:
    return ((lon + 180) / 360 * W, 120 + (82 - lat) / 142 * 800)


def layers_for(job: str, asset: str, kicker: str, title: str, accent: str,
               camera: list[tuple[int, float]], pins: list[tuple[str, float, float, str, int]],
               subline: str) -> list[dict]:
    result = [
        {"id": f"{job}-map", "type": "image", "asset": asset,
         "size": [W, 820], "fit": "cover", "position": [960, 540],
         "start_frame": 0, "duration_frames": FRAMES,
         "animation": {"tracks": [tr("scale", camera, "in_out_sine")]}},
        {"id": f"{job}-veil", "type": "color", "color": [0.01, 0.025, 0.04, 0.22],
         "size": [W, H], "position": [960, 540], "screen_space": True,
         "start_frame": 0, "duration_frames": FRAMES},
        text(f"{job}-kicker", kicker.upper(), (960, 76), 20, accent,
             start=0, box=(1450, 44)),
        text(f"{job}-title", title.upper(), (960, 158), 68, WHITE, font=BOLD,
             start=0, box=(1650, 110)),
        text(f"{job}-footer", subline.upper(), (960, 1012), 18, "#C2D0D5",
             start=0, box=(1600, 46)),
    ]
    plate_path = OUT / "plans" / f"{job}-labels.png"
    plate = Image.open(WORKSPACE / asset).convert("RGB").resize((W, 820), Image.LANCZOS)
    draw = ImageDraw.Draw(plate)
    for name, lon, lat, color, _enter in pins:
        x, y = project(lon, lat)
        mx, my = int((x / W) * W), int(((y - 130) / 800) * 820)
        r = 9
        draw.ellipse((mx-r, my-r, mx+r, my+r), fill=color, outline=WHITE, width=2)
        lx, ly = min(W-300, mx+24), max(24, my-19)
        draw.rounded_rectangle((lx-9, ly-5, lx+210, ly+31), radius=8,
                               fill=(7, 21, 34), outline=color, width=2)
        draw.text((lx, ly), name.upper(), fill=color)
    plate.save(plate_path)

    result.append({"id": f"{job}-geo-label-plate", "type": "image",
                   "asset": str(plate_path.relative_to(WORKSPACE)),
                   "size": [W, 820], "fit": "stretch", "position": [960, 540],
                   "start_frame": 0, "duration_frames": FRAMES,
                   "animation": {"tracks": [tr("scale", camera, "in_out_sine")]}})
    return result


def make_plans() -> list[dict]:
    scenes = [
        ("modern_map_atlantic_route", "ChrononTemplate/catalog/maps/nasa_blue_marble_august.jpg",
         "01 / TRANSATLANTIC ROUTE", "Across the Atlantic", GOLD,
         [(0, 1.0), (FRAMES - 1, 1.16)],
         [("New York", -74.006, 40.713, GOLD, 52), ("London", -0.128, 51.507, MINT, 112)],
         "North Atlantic · staggered beacon arrival"),
        ("modern_map_europe_arrivals", "ChrononTemplate/catalog/maps/natural_earth_hypso_relief_water.jpg",
         "02 / EUROPEAN CITY NETWORK", "Four cities, one frame", BLUE,
         [(0, 1.0), (92, 1.14), (FRAMES - 1, 1.18)],
         [("London", -0.128, 51.507, BLUE, 42), ("Paris", 2.352, 48.857, GOLD, 92),
          ("Rome", 12.496, 41.903, MINT, 142)],
         "Europe · sequential pins and labels"),
        ("modern_map_global_hubs", "ChrononTemplate/catalog/maps/natural_earth_landcover_relief_water.jpg",
         "03 / GLOBAL CONNECTIONS", "A world of hubs", MINT,
         [(0, 1.17), (105, 1.06), (FRAMES - 1, 1.0)],
         [("New York", -74.006, 40.713, GOLD, 48), ("London", -0.128, 51.507, BLUE, 94),
          ("Singapore", 103.8198, 1.3521, MINT, 140)],
         "Illustrative hub locations · not traffic data"),
    ]
    plans = []
    for job, asset, kicker, title, accent, camera, pins, subline in scenes:
        plans.append({"schema": "chronon.render-plan.v3", "version": 3, "job_id": job,
            "canvas": {"width": W, "height": H, "fps_num": FPS, "fps_den": 1,
                       "duration_frames": FRAMES},
            "layers": layers_for(job, asset, kicker, title, accent, camera, pins, subline),
            "output": {"path": f"{job}.mp4", "format": "mp4", "codec": "h264"}})
    return plans


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--plans-only", action="store_true")
    ap.add_argument("--qp", type=int, default=14, help="NVENC constant QP, lower is higher quality")
    ap.add_argument("--only", choices=("atlantic", "europe", "global"), action="append")
    ap.add_argument("--cli", type=Path, default=CLI)
    ap.add_argument("--chunk-frames", type=int, default=240,
                    help="Maximum frames per independent Vulkan/NVENC render segment")
    ap.add_argument("--chunks", type=int, default=8,
                    help="Legacy native render chunk count; not used by segmented rendering")
    args = ap.parse_args()
    if not 0 <= args.qp <= 63:
        ap.error("--qp must be between 0 and 63")
    if not 1 <= args.chunk_frames <= FRAMES:
        ap.error(f"--chunk-frames must be between 1 and {FRAMES}")
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "plans").mkdir(exist_ok=True)
    (OUT / "renders").mkdir(exist_ok=True)
    filters = {"atlantic": "modern_map_atlantic_route", "europe": "modern_map_europe_arrivals",
               "global": "modern_map_global_hubs"}
    chosen = set(args.only or filters)
    manifest = []
    for plan in make_plans():
        job = plan["job_id"]
        if job not in {filters[k] for k in chosen}:
            continue
        path = OUT / "plans" / f"{job}.plan.json"
        path.write_text(json.dumps(plan, indent=2) + "\n")
        video = OUT / "renders" / f"{job}.mp4"
        subprocess.run([str(args.cli), "validate", "--plan", str(path),
                        "--assets-root", str(WORKSPACE)], check=True)
        segment_count = math.ceil(FRAMES / args.chunk_frames)
        if not args.plans_only:
            with tempfile.TemporaryDirectory(prefix=f"{job}-segments-", dir=OUT / "renders") as temp_dir:
                segments = []
                for chunk_index, first in enumerate(range(0, FRAMES, args.chunk_frames)):
                    last = min(FRAMES - 1, first + args.chunk_frames - 1)
                    segment = Path(temp_dir) / f"segment_{chunk_index:03d}.mp4"
                    subprocess.run([str(args.cli), "render", "--plan", str(path),
                        "--assets-root", str(WORKSPACE), "--output", str(segment),
                        "--backend", "vulkan", "--gpu-hot-path-mode", "require_gpu_native",
                        "--hardware", "nvenc", "--encoder-backend", "native", "--fps", str(FPS),
                        "--rate-control", "qp", "--qp", str(args.qp), "--encode-preset", "p5",
                        "--start-frame", str(first), "--end-frame", str(last),
                        "--log-level", "error"], check=True)
                    probe = json.loads(subprocess.check_output([
                        "ffprobe", "-v", "error", "-show_streams", "-of", "json", str(segment)],
                        text=True))
                    streams = [s for s in probe["streams"] if s.get("codec_type") == "video"]
                    if len(streams) != 1:
                        raise RuntimeError(f"{segment} must contain exactly one video stream")
                    stream = streams[0]
                    if (stream.get("codec_name") != "h264" or
                            stream.get("width") != W or stream.get("height") != H or
                            stream.get("r_frame_rate") != f"{FPS}/1" or
                            int(stream.get("nb_frames", -1)) != last - first + 1):
                        raise RuntimeError(f"segment metadata mismatch in {segment}: {stream}")
                    sidecar = json.loads(Path(f"{segment}.timing.json").read_text())
                    stats = sidecar.get("job", {}).get("gpu", {})
                    if (stats.get("effective_backend") != "vulkan" or
                            stats.get("encoder_backend") != "nvenc" or
                            stats.get("gpu_native_encode_frames") != last - first + 1):
                        raise RuntimeError(f"segment GPU route check failed in {segment}")
                    segments.append(segment)
                    print(f"Rendered {job} segment {chunk_index + 1}/{segment_count} "
                          f"(frames {first}-{last})", flush=True)
                concat_file = Path(temp_dir) / "segments.ffconcat"
                concat_file.write_text("ffconcat version 1.0\n" + "".join(
                    f"file '{segment.as_posix()}'\n" for segment in segments))
                subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
                    "-f", "concat", "-safe", "0", "-i", str(concat_file),
                    "-c", "copy", "-movflags", "+faststart", str(video)], check=True)
                sidecar_data = json.loads(Path(f"{segments[0]}.timing.json").read_text())
                sidecar_data["video"] = str(video.resolve())
                sidecar_data["joined_from_gpu_segments"] = len(segments)
                Path(f"{video}.timing.json").write_text(json.dumps(sidecar_data, indent=2) + "\n")
        if not args.plans_only:
            sidecar = json.loads(Path(f"{video}.timing.json").read_text())
            gpu_stats = sidecar.get("job", {}).get("gpu", {})
            if (sidecar.get("frames_total") != FRAMES or
                    gpu_stats.get("effective_backend") != "vulkan" or
                    gpu_stats.get("encoder_backend") != "nvenc" or
                    gpu_stats.get("gpu_native_encode_frames") != FRAMES):
                raise RuntimeError(f"final GPU render verification failed for {video}")
            probe = json.loads(subprocess.check_output([
                "ffprobe", "-v", "error", "-count_frames", "-select_streams", "v:0",
                "-show_entries", "stream=codec_name,width,height,r_frame_rate,nb_read_frames,duration",
                "-of", "json", str(video)], text=True))
            final_streams = probe.get("streams", [])
            if len(final_streams) != 1:
                raise RuntimeError(f"{video} must contain exactly one video stream")
            final_stream = final_streams[0]
            if (final_stream.get("codec_name") != "h264" or
                    final_stream.get("width") != W or final_stream.get("height") != H or
                    final_stream.get("r_frame_rate") != f"{FPS}/1" or
                    int(final_stream.get("nb_read_frames", -1)) != FRAMES):
                raise RuntimeError(f"final video metadata mismatch in {video}: {final_stream}")
            subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-i", str(video),
                            "-f", "null", "-"], check=True)
        manifest.append({"id": job, "plan": str(path.relative_to(OUT)),
                         "video": str(video.relative_to(OUT)), "renderer": "Vulkan + NVENC",
                         "sha256": hashlib.sha256(video.read_bytes()).hexdigest(),
                         "qp": args.qp, "segment_frames": args.chunk_frames,
                         "segments": segment_count, "size": f"{W}x{H}", "fps": FPS,
                         "duration_seconds": FRAMES / FPS})
        print(f"Prepared/rendered {job}", flush=True)
    (OUT / "manifest.json").write_text(json.dumps({"family": "modern_gpu_map_series_v1",
        "renderer": "Vulkan required_gpu_native + native NVENC", "clips": manifest}, indent=2) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
