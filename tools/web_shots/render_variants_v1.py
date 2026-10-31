"""Render the 24 web animation variants to 1920x1080 MP4 and upload them.

Per shot: still.png (hero frame), <name>.mp4 (3.0 s @ 30 fps, H.264) and one
contact sheet + manifest for the whole batch. Rendering runs in parallel
processes; every clip is verified with ffprobe before it is uploaded.

Usage (from ChrononTemplate/):
  python tools/web_shots/render_variants_v1.py --stills-only
  python tools/web_shots/render_variants_v1.py --jobs 4
  python tools/web_shots/render_variants_v1.py --jobs 4 --upload
  python tools/web_shots/render_variants_v1.py --only v01_marker_push --upload
"""

from __future__ import annotations

import argparse
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

from shots_variants import SECONDS, variant_names  # noqa: E402
from web_shot_kit import contact_sheet  # noqa: E402

TEMPLATE_ROOT = HERE.parents[1]
WORKSPACE = HERE.parents[2]
DEFAULT_OUT = TEMPLATE_ROOT / "out" / "web_anim_variants_v1"
DEFAULT_DRIVE_FOLDER = "1J_xUGo_bchzXDIGqSX04CU44c_Dm3SxS"
WIDTH, HEIGHT, FPS = 1920, 1080, 30
FRAMES = int(round(SECONDS * FPS))


def _shot(name: str):
    from shots_variants import all_variant_shots  # noqa: PLC0415

    for shot in all_variant_shots():
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
    if abs(info["seconds"] - SECONDS) > 0.15:
        problems.append(f"{path.name}: {info['seconds']:.2f}s")
    return problems


def _render_one(name: str, out_dir: Path, stills_only: bool, force: bool) -> dict:
    shot = _shot(name)
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
            "clip": str(mp4), "frames": entry.get("frames")}


def _upload(out_dir: Path, folder: str, names: list[str]) -> dict:
    sys.path.insert(0, str(TEMPLATE_ROOT / "tools"))
    from kit import drive  # noqa: PLC0415

    token = drive.refresh_token(
        WORKSPACE / "refactored" / "token.json",
        WORKSPACE / "refactored" / "credentials.json",
    )
    files = [out_dir / n / f"{n}.mp4" for n in names]
    files = [p for p in files if p.exists()]
    print(f"--- upload: {len(files)} MP4 -> Drive folder {folder} ---", flush=True)
    uploads = drive.upload_many(token, files, folder)
    links = {p.stem: drive.link_for(r) for p, r in uploads.items()}
    for name, link in sorted(links.items()):
        print(f"  [UP] {name} -> {link}", flush=True)
    return links


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--jobs", type=int, default=4)
    ap.add_argument("--only", nargs="*", default=None)
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--stills-only", action="store_true")
    ap.add_argument("--upload", action="store_true")
    ap.add_argument("--drive-folder", default=DEFAULT_DRIVE_FOLDER)
    args = ap.parse_args(argv)

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    names = args.only or variant_names()
    unknown = [n for n in names if n not in variant_names()]
    if unknown:
        raise SystemExit(f"unknown variant(s): {', '.join(unknown)}")

    entries: dict[str, dict] = {}
    jobs = max(1, min(args.jobs, len(names)))
    if jobs == 1:
        for name in names:
            entries[name] = _render_one(name, out_dir, args.stills_only, args.force)
            print(f"  [{'OK' if entries[name]['ok'] else 'FAIL'}] {name}", flush=True)
    else:
        with ProcessPoolExecutor(max_workers=jobs) as pool:
            futures = {pool.submit(_render_one, n, out_dir, args.stills_only,
                                   args.force): n for n in names}
            for future in as_completed(futures):
                name = futures[future]
                entries[name] = future.result()
                print(f"  [{'OK' if entries[name]['ok'] else 'FAIL'}] {name}", flush=True)

    problems = [p for e in entries.values() for p in e.get("problems", [])]
    for problem in problems:
        print(f"  [VERIFY-FAIL] {problem}", file=sys.stderr)

    stills = []
    for name in sorted(entries):
        still = out_dir / name / "still.png"
        if still.exists():
            stills.append((name, Image.open(still).convert("RGB")))
    if stills:
        contact_sheet(stills, out_dir / "contact_sheet.jpg", cols=4, cell_w=480)

    drive_links = None
    if args.upload and not problems and not args.stills_only:
        drive_links = _upload(out_dir, args.drive_folder, sorted(entries))

    manifest = {
        "schema": "chronon.web-anim-variants.v1",
        "generated": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "canvas": {"width": WIDTH, "height": HEIGHT, "fps": FPS, "frames": FRAMES},
        "count": len(entries),
        "items": entries,
    }
    if drive_links:
        manifest["drive"] = drive_links
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n",
                                           encoding="utf-8")

    ok = sum(1 for e in entries.values() if e.get("ok"))
    print(f"\nvariants: {ok}/{len(entries)} OK -> {out_dir}")
    return 0 if ok == len(entries) and not problems else 1


if __name__ == "__main__":
    raise SystemExit(main())
