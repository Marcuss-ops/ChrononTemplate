"""Render the six Web Motion Lab clips to 1920x1080 and upload them.

Per shot: still.png (hero frame), <name>.mp4 (6.0 s @ 30 fps, H.264) and one
contact sheet + manifest for the batch. Every clip is verified with ffprobe
before Drive is touched. Upload uses the operator credentials in
``RenderingGen/UploadDrive`` and the requested Drive folder.

Usage (from ChrononTemplate/):
  python tools/web_shots/render_motion_lab.py --stills-only
  python tools/web_shots/render_motion_lab.py --jobs 6
  python tools/web_shots/render_motion_lab.py --jobs 6 --upload
  python tools/web_shots/render_motion_lab.py --only lab_ink_bloom --upload
  python tools/web_shots/render_motion_lab.py --center --jobs 6 --upload
"""

from __future__ import annotations

import sys as _velox_sys
from pathlib import Path as _VeloxPath
_velox_sys.path.insert(0, str(_VeloxPath(__file__).resolve().parents[3] / "tools"))
from stack_config import overlay_root as _overlay_root  # noqa: E402

import os
import argparse
import hashlib
import json
import shutil
import subprocess
import sys
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from shots_motion_lab import SECONDS, all_motion_lab_shots, motion_lab_names  # noqa: E402
from shots_motion_lab_center import (  # noqa: E402
    all_centered_motion_lab_shots,
    centered_motion_lab_names,
)
from web_shot_kit import contact_sheet  # noqa: E402

TEMPLATE_ROOT = HERE.parents[1]
WORKSPACE = HERE.parents[2]
DEFAULT_OUT = TEMPLATE_ROOT / "out" / "web_motion_lab_v1"
DEFAULT_CENTER_OUT = TEMPLATE_ROOT / "out" / "web_motion_lab_center_v2"
DEFAULT_DRIVE_FOLDER = _overlay_root()
DRIVE_CREDENTIALS = WORKSPACE / "RenderingGen" / "UploadDrive" / "credentials.json"
DRIVE_TOKEN = WORKSPACE / "RenderingGen" / "UploadDrive" / "token.json"
WIDTH, HEIGHT, FPS = 1920, 1080, 30
FRAMES = int(round(SECONDS * FPS))


def _shot(name: str, center: bool = False):
    shots = all_centered_motion_lab_shots() if center else all_motion_lab_shots()
    for shot in shots:
        if shot.name == name:
            return shot
    raise KeyError(name)


def _probe(path: Path) -> dict:
    proc = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0",
         "-show_entries", "stream=codec_name,width,height,nb_frames",
         "-show_entries", "format=duration", "-of", "json", str(path)],
        check=True, capture_output=True, text=True,
    )
    data = json.loads(proc.stdout)
    stream = data["streams"][0]
    return {
        "codec": stream.get("codec_name"),
        "width": int(stream.get("width", 0)),
        "height": int(stream.get("height", 0)),
        "frames": int(stream.get("nb_frames", 0)),
        "seconds": float(data.get("format", {}).get("duration", 0.0)),
    }


def _verify(path: Path) -> list[str]:
    if not path.exists() or path.stat().st_size == 0:
        return [f"{path.name}: missing or empty"]
    info = _probe(path)
    problems = []
    if info["codec"] != "h264":
        problems.append(f"{path.name}: codec {info['codec']} != h264")
    if (info["width"], info["height"]) != (WIDTH, HEIGHT):
        problems.append(f"{path.name}: {info['width']}x{info['height']}")
    if info["frames"] != FRAMES:
        problems.append(f"{path.name}: {info['frames']} frames != {FRAMES}")
    if abs(info["seconds"] - SECONDS) > 0.20:
        problems.append(f"{path.name}: {info['seconds']:.2f}s != {SECONDS:.2f}s")
    return problems


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _render_one(name: str, out_dir: Path, stills_only: bool, force: bool,
                center: bool = False) -> dict:
    shot = _shot(name, center)
    shot_dir = out_dir / name
    still = shot_dir / "still.png"
    mp4 = shot_dir / f"{name}.mp4"
    if not force and still.exists() and (stills_only or mp4.exists()):
        return {"name": name, "skipped": True, "ok": True, "problems": []}
    shot_dir.mkdir(parents=True, exist_ok=True)
    if stills_only:
        shot.render_still().save(still)
        return {"name": name, "ok": True, "problems": []}
    entry = shot.render_all(out_dir, write_frames=True)
    shutil.rmtree(shot_dir / "frames", ignore_errors=True)
    problems = _verify(mp4)
    return {"name": name, "ok": not problems, "problems": problems,
            "clip": str(mp4), "frames": entry.get("frames"),
            "sha256": _sha256(mp4) if mp4.exists() else None}


def _upload(out_dir: Path, folder: str, names: list[str]) -> dict:
    sys.path.insert(0, str(TEMPLATE_ROOT / "tools"))
    from kit import drive  # noqa: PLC0415

    token = drive.refresh_token(DRIVE_TOKEN, DRIVE_CREDENTIALS)
    files = [out_dir / n / f"{n}.mp4" for n in names]
    files = [path for path in files if path.exists()]
    print(f"--- upload: {len(files)} MP4 -> Drive folder {folder} ---", flush=True)
    uploads = drive.upload_many(token, files, folder)
    links = {path.stem: drive.link_for(result) for path, result in uploads.items()}
    for name, link in sorted(links.items()):
        print(f"  [UP] {name} -> {link}", flush=True)
    return links


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=None)
    ap.add_argument("--jobs", type=int, default=6)
    ap.add_argument("--only", nargs="*", default=None)
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--stills-only", action="store_true")
    ap.add_argument("--upload", action="store_true")
    ap.add_argument("--center", action="store_true",
                    help="render the center-only cuts (no header/footer text)")
    ap.add_argument("--drive-folder", default=DEFAULT_DRIVE_FOLDER)
    args = ap.parse_args(argv)

    out_dir = Path(args.out) if args.out else (
        DEFAULT_CENTER_OUT if args.center else DEFAULT_OUT)
    out_dir.mkdir(parents=True, exist_ok=True)
    all_names = centered_motion_lab_names() if args.center else motion_lab_names()
    names = args.only or all_names
    unknown = [n for n in names if n not in all_names]
    if unknown:
        raise SystemExit(f"unknown shot(s): {', '.join(unknown)}")

    entries: dict[str, dict] = {}
    jobs = max(1, min(args.jobs, len(names)))
    if jobs == 1:
        for name in names:
            entries[name] = _render_one(name, out_dir, args.stills_only,
                                        args.force, args.center)
            print(f"  [{'OK' if entries[name]['ok'] else 'FAIL'}] {name}", flush=True)
    else:
        with ProcessPoolExecutor(max_workers=jobs) as pool:
            futures = {pool.submit(_render_one, n, out_dir, args.stills_only,
                                   args.force, args.center): n for n in names}
            for future in as_completed(futures):
                name = futures[future]
                entries[name] = future.result()
                print(f"  [{'OK' if entries[name]['ok'] else 'FAIL'}] {name}",
                      flush=True)

    problems = [p for e in entries.values() for p in e.get("problems", [])]
    for problem in problems:
        print(f"  [VERIFY-FAIL] {problem}", file=sys.stderr)

    stills = []
    for name in sorted(entries):
        still = out_dir / name / "still.png"
        if still.exists():
            stills.append((name, Image.open(still).convert("RGB")))
    if stills:
        contact_sheet(stills, out_dir / "contact_sheet.jpg", cols=3, cell_w=560)

    drive_links = None
    if args.upload and not problems and not args.stills_only:
        drive_links = _upload(out_dir, args.drive_folder, sorted(entries))

    manifest = {
        "schema": ("chronon.web-motion-lab.center.v1" if args.center
                   else "chronon.web-motion-lab.pod.v1"),
        "generated": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "canvas": {"width": WIDTH, "height": HEIGHT, "fps": FPS, "frames": FRAMES,
                   "seconds": SECONDS},
        "source": ("ChrononTemplate/tools/web_shots/shots_motion_lab_center.py"
                   if args.center else
                   "ChrononTemplate/tools/web_shots/shots_motion_lab.py"),
        "cpp_source": "chronontemplate/web/WebMotionLabPack.hpp",
        "variant": "center" if args.center else "chrome",
        "layout": ("single centered statement; no header, footer or corner text"
                   if args.center else "editorial chrome"),
        "count": len(entries),
        "items": entries,
    }
    if drive_links:
        manifest["drive"] = drive_links
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n",
                                           encoding="utf-8")

    ok = sum(1 for e in entries.values() if e.get("ok"))
    print(f"\nmotion lab: {ok}/{len(entries)} OK -> {out_dir}")
    return 0 if ok == len(entries) and not problems else 1


if __name__ == "__main__":
    raise SystemExit(main())
