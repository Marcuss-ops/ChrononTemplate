#!/usr/bin/env python3
"""Render the editorial_motion_pack_v1 plans to verified 1080p MP4s.

Uses the same canonical `chronon3d_cli render-plan` route as the date-animation
catalog, two bounded workers, and ffprobe verification before a clip is marked
rendered. Every clip is 1920x1080, 30 fps and 180 frames (6 s), below the
requested 10-second limit.

    python3 ChrononTemplate/tools/editorial_motion/render_pack.py --jobs 2
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
TEMPLATE = ROOT / "ChrononTemplate"
PACK = TEMPLATE / "golden_plans" / "editorial_motion_pack_v1"
CATALOG = PACK / "catalog.json"
RENDERS = TEMPLATE / "renders" / "editorial_motion_pack_v1"
CLI_CANDIDATES = (
    ROOT / "Chronon3d/build/chronon/linux-video-release.root-bin/apps/chronon3d_cli/chronon3d_cli",
    ROOT / "Chronon3d/build/chronon/linux-video-release/apps/chronon3d_cli/chronon3d_cli",
)
CLI = max((path for path in CLI_CANDIDATES if path.is_file()),
          key=lambda path: path.stat().st_mtime, default=CLI_CANDIDATES[0])
WIDTH, HEIGHT, FPS, FRAMES = 1920, 1080, 30, 180


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def entries(catalog: dict):
    for family in catalog["families"]:
        for preset in family["presets"]:
            yield family, preset


def probe(path: Path) -> dict:
    data = json.loads(subprocess.check_output([
        "ffprobe", "-v", "error", "-select_streams", "v:0",
        "-show_entries", "stream=width,height,r_frame_rate,nb_frames",
        "-show_entries", "format=duration",
        "-of", "json", str(path),
    ], text=True))
    stream = data["streams"][0]
    duration = float(data["format"]["duration"])
    frames = int(stream.get("nb_frames") or 0)
    if frames <= 0:
        frames = round(duration * FPS)
    return {
        "width": int(stream["width"]),
        "height": int(stream["height"]),
        "fps": stream["r_frame_rate"],
        "frames": frames,
        "duration_s": duration,
    }


def verify(path: Path) -> dict:
    info = probe(path)
    expected = (WIDTH, HEIGHT, "30/1", FRAMES)
    actual = (info["width"], info["height"], info["fps"], info["frames"])
    if actual != expected:
        raise RuntimeError(f"unexpected stream {actual}; expected {expected}")
    if not 5.9 <= info["duration_s"] <= 6.1:
        raise RuntimeError(f"unexpected duration {info['duration_s']:.3f}s")
    return info


def write_catalog(catalog: dict) -> None:
    CATALOG.write_text(json.dumps(catalog, indent=2, ensure_ascii=False) + "\n")


def make_contact_sheet(catalog: dict) -> Path | None:
    from PIL import Image, ImageDraw, ImageFont

    rendered = [(family, preset) for family, preset in entries(catalog)
                if preset.get("status") == "rendered"]
    if not rendered:
        return None
    sheet_dir = RENDERS / "preview"
    sheet_dir.mkdir(parents=True, exist_ok=True)
    tiles = []
    for family, preset in rendered:
        video = TEMPLATE / preset["video"]
        still = sheet_dir / f"{preset['id']}.jpg"
        result = subprocess.run([
            "ffmpeg", "-y", "-loglevel", "error", "-ss", "3", "-i", str(video),
            "-frames:v", "1", "-vf", "scale=384:216", str(still),
        ], capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(f"still failed for {preset['id']}: {result.stderr[-800:]}")
        image = Image.open(still).convert("RGB")
        tile = Image.new("RGB", (384, 256), (12, 16, 22))
        tile.paste(image, (0, 0))
        draw = ImageDraw.Draw(tile)
        try:
            font = ImageFont.truetype(
                "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 14)
        except Exception:
            font = None
        draw.text((10, 224), preset["id"][:48], fill=(228, 236, 245), font=font)
        draw.text((10, 240), family["id"][:48], fill=(112, 210, 240), font=font)
        tiles.append(tile)
    columns = 5
    rows = (len(tiles) + columns - 1) // columns
    sheet = Image.new("RGB", (columns * 384, rows * 256), (12, 16, 22))
    for index, tile in enumerate(tiles):
        sheet.paste(tile, ((index % columns) * 384, (index // columns) * 256))
    out = RENDERS / "catalog_contact_sheet.jpg"
    sheet.save(out, quality=92)
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--jobs", type=int, default=2)
    parser.add_argument("--only", default="", help="comma-separated preset ids")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--no-sheet", action="store_true")
    args = parser.parse_args()
    jobs = max(1, min(2, args.jobs))
    only = [value.strip() for value in args.only.split(",") if value.strip()]

    if not CLI.is_file():
        raise SystemExit(f"missing render CLI: {CLI}")
    catalog = json.loads(CATALOG.read_text())
    RENDERS.mkdir(parents=True, exist_ok=True)
    (RENDERS / "logs").mkdir(parents=True, exist_ok=True)

    pending = []
    for family, preset in entries(catalog):
        if only and preset["id"] not in only:
            continue
        video = RENDERS / f"{preset['id']}.mp4"
        if video.is_file() and not args.force:
            try:
                info = verify(video)
                preset.update(status="rendered", video=str(video.relative_to(TEMPLATE)),
                              bytes=video.stat().st_size, sha256=sha256_file(video),
                              duration_s=round(info["duration_s"], 3))
                continue
            except Exception as exc:
                print(f"re-render {preset['id']}: {exc}", flush=True)
        pending.append((family, preset, video))

    print(f"rendering {len(pending)} clips with {jobs} workers", flush=True)
    running = []
    failed = []
    while pending or running:
        while pending and len(running) < jobs:
            family, preset, video = pending.pop(0)
            log_path = RENDERS / "logs" / f"{preset['id']}.log"
            log = log_path.open("w")
            command = [
                str(CLI), "render-plan",
                "--input", str(TEMPLATE / preset["plan"]),
                "--output", str(video),
                "--assets-root", str(TEMPLATE),
                "--backend", "vulkan",
                "--rate-control", "crf", "--crf", "16",
                "--encode-preset", "slow",
            ]
            log.write("$ " + " ".join(command) + "\n")
            log.flush()
            started = time.time()
            process = subprocess.Popen(command, cwd=ROOT, stdout=log,
                                       stderr=subprocess.STDOUT)
            running.append((family, preset, video, process, log, log_path, started))
            print(f"START {family['id']}/{preset['id']}", flush=True)

        time.sleep(1)
        for item in running[:]:
            family, preset, video, process, log, log_path, started = item
            if process.poll() is None:
                continue
            log.close()
            running.remove(item)
            elapsed = round(time.time() - started, 3)
            if process.returncode != 0:
                preset.update(status="failed", video=None,
                              error=f"render exit {process.returncode}")
                failed.append(preset["id"])
                print(f"FAIL  {preset['id']} ({elapsed}s) log={log_path}", flush=True)
                print(log_path.read_text(errors="replace")[-1400:], flush=True)
            else:
                try:
                    info = verify(video)
                    preset.update(
                        status="rendered",
                        video=str(video.relative_to(TEMPLATE)),
                        bytes=video.stat().st_size,
                        sha256=sha256_file(video),
                        duration_s=round(info["duration_s"], 3),
                        render_seconds=elapsed,
                        rendered_at=time.strftime("%Y-%m-%dT%H:%M:%S%z"),
                    )
                    preset.pop("error", None)
                    print(f"DONE  {preset['id']} {preset['bytes']} bytes "
                          f"{elapsed}s", flush=True)
                except Exception as exc:
                    preset.update(status="failed", video=None, error=str(exc))
                    failed.append(preset["id"])
                    print(f"FAIL  {preset['id']}: {exc}", flush=True)
            write_catalog(catalog)

    write_catalog(catalog)
    if not args.no_sheet:
        sheet = make_contact_sheet(catalog)
        if sheet:
            catalog["contact_sheet"] = str(sheet.relative_to(TEMPLATE))
            write_catalog(catalog)
            print(f"sheet {sheet}", flush=True)

    manifest = {
        "schema": "chronontemplate.editorial-motion-pack.render.v1",
        "family_id": catalog["family_id"],
        "canvas": catalog["canvas"],
        "duration_frames": catalog["duration_frames"],
        "cli": str(CLI.relative_to(ROOT)),
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "clips": [
            {
                "id": preset["id"],
                "family": family["id"],
                "status": preset.get("status"),
                "plan": preset["plan"],
                "video": preset.get("video"),
                "bytes": preset.get("bytes"),
                "sha256": preset.get("sha256"),
                "duration_s": preset.get("duration_s"),
                "frames": FRAMES,
            }
            for family, preset in entries(catalog)
        ],
    }
    (RENDERS / "render_manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n")
    print(f"finished failures={failed}", flush=True)
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
