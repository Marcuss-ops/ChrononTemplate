"""The web-animation pod: all 34 recipes at 1920x1080, verified and uploaded.

The 28 reference rebuilds already have verified native MP4s in
``artifacts/web_shots_folder_recreated_native_v1``. This pod reuses those,
renders the missing shots (01, 02, 07 and the six ``next_*`` recipes) through
the Python kit, verifies every clip with ffprobe, writes one manifest and a
contact sheet, then uploads the MP4s to the requested Google Drive folder.

Usage:
  python tools/web_shots/render_web_animations_pod.py
  python tools/web_shots/render_web_animations_pod.py --only next_caption_pop_card
  python tools/web_shots/render_web_animations_pod.py --jobs 3 --skip-upload
  python tools/web_shots/render_web_animations_pod.py --upload-only
  python tools/web_shots/render_web_animations_pod.py --drive-folder <id>

The default Drive folder is the one requested for this delivery. Upload is
opt-out: pass --skip-upload for a local-only run.
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

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from PIL import Image

from render_web_shots_rebuild_v1 import ALL_GROUPS
from shots_next import NEXT_GROUP
from web_shot_kit import contact_sheet

TEMPLATE_ROOT = HERE.parents[1]
WORKSPACE = HERE.parents[2]
DEFAULT_OUT = TEMPLATE_ROOT / "out" / "web_animations_pod_v1"
NATIVE_ARTIFACTS = TEMPLATE_ROOT / "artifacts" / "web_shots_folder_recreated_native_v1"
DEFAULT_DRIVE_FOLDER = "1J_xUGo_bchzXDIGqSX04CU44c_Dm3SxS"

ALL_FACTORIES = list(ALL_GROUPS) + list(NEXT_GROUP)
FACTORY_BY_NAME = {factory().name: factory for factory in ALL_FACTORIES}

WIDTH, HEIGHT, FPS, FRAMES = 1920, 1080, 30, 90


def _ffprobe() -> str:
    found = shutil.which("ffprobe")
    if found:
        return found
    raise SystemExit("ffprobe not found (install ffmpeg)")


def _ffmpeg() -> str:
    found = shutil.which("ffmpeg")
    if found:
        return found
    raise SystemExit("ffmpeg not found (install ffmpeg)")


def _probe(path: Path) -> dict:
    proc = subprocess.run(
        [_ffprobe(), "-v", "error", "-select_streams", "v:0",
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
        "frames": int(stream.get("nb_frames", FRAMES)),
        "seconds": float(data.get("format", {}).get("duration", 0.0)),
    }


def _verify(path: Path) -> list[str]:
    problems: list[str] = []
    if not path.exists() or path.stat().st_size == 0:
        return [f"{path.name}: missing or empty"]
    info = _probe(path)
    if info["codec"] != "h264":
        problems.append(f"{path.name}: codec {info['codec']} != h264")
    if (info["width"], info["height"]) != (WIDTH, HEIGHT):
        problems.append(f"{path.name}: {info['width']}x{info['height']} != 1920x1080")
    if info["frames"] != FRAMES:
        problems.append(f"{path.name}: {info['frames']} frames != {FRAMES}")
    if abs(info["seconds"] - 3.0) > 0.15:
        problems.append(f"{path.name}: {info['seconds']:.3f}s != 3.0s")
    return problems


def _extract_still(mp4: Path, still: Path) -> None:
    still.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [_ffmpeg(), "-y", "-v", "error", "-ss", "2.9", "-i", str(mp4),
         "-frames:v", "1", str(still)],
        check=True,
    )


def _render_one(name: str, out_dir: Path, reuse_native: bool, force: bool) -> dict:
    factory = FACTORY_BY_NAME.get(name)
    if factory is None:
        return {"name": name, "ok": False, "error": "unknown recipe"}
    shot_dir = out_dir / name
    mp4 = shot_dir / f"{name}.mp4"
    still = shot_dir / "still.png"
    shot_dir.mkdir(parents=True, exist_ok=True)

    if not force and mp4.exists() and still.exists():
        problems = _verify(mp4)
        return {"name": name, "ok": not problems, "reused": True,
                "problems": problems, "mp4": str(mp4)}

    native = NATIVE_ARTIFACTS / f"{name}.mp4"
    if reuse_native and not force and native.exists():
        shutil.copy2(native, mp4)
        if not still.exists():
            _extract_still(mp4, still)
        problems = _verify(mp4)
        return {"name": name, "ok": not problems, "native": True,
                "problems": problems, "mp4": str(mp4)}

    shot = factory()
    entry = shot.render_all(out_dir, write_frames=True)
    shutil.rmtree(shot_dir / "frames", ignore_errors=True)
    problems = _verify(mp4)
    return {"name": name, "ok": not problems, "rendered": True,
            "problems": problems, "mp4": str(mp4),
            "frames": entry.get("frames")}


def _assemble(out_dir: Path, entries: dict[str, dict], drive_links: dict | None) -> Path:
    stills = []
    for name in sorted(entries):
        still = out_dir / name / "still.png"
        if still.exists():
            stills.append((name, Image.open(still).convert("RGB")))
    if stills:
        contact_sheet(stills, out_dir / "contact_sheet.jpg", cols=4, cell_w=480)
    manifest = {
        "schema": "chronon.web-animations-pod.v1",
        "generated": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "canvas": {"width": WIDTH, "height": HEIGHT, "fps": FPS, "frames": FRAMES},
        "count": len(entries),
        "items": entries,
    }
    if drive_links:
        manifest["drive"] = drive_links
    path = out_dir / "manifest.json"
    path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return path


def _upload(out_dir: Path, folder: str, entries: dict[str, dict]) -> dict:
    sys.path.insert(0, str(TEMPLATE_ROOT / "tools"))
    from kit import drive  # noqa: PLC0415 - optional at import time

    token = drive.refresh_token(
        WORKSPACE / "refactored" / "token.json",
        WORKSPACE / "refactored" / "credentials.json",
    )
    files = [out_dir / name / f"{name}.mp4" for name in sorted(entries)]
    files = [path for path in files if path.exists()]
    print(f"--- upload: {len(files)} MP4 -> Drive folder {folder} ---")
    uploads = drive.upload_many(token, files, folder)
    links = {path.stem: drive.link_for(result) for path, result in uploads.items()}
    for name, link in sorted(links.items()):
        print(f"  [UP] {name} -> {link}")
    return links


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--only", nargs="*", default=None,
                        help="render only these recipe names")
    parser.add_argument("--jobs", type=int, default=1,
                        help="parallel render processes (default 1)")
    parser.add_argument("--force", action="store_true",
                        help="re-render/re-copy existing clips")
    parser.add_argument("--no-reuse-native", action="store_true",
                        help="render all 34 with Pillow instead of reusing the 25 native clips")
    parser.add_argument("--skip-upload", action="store_true", help="never touch Drive")
    parser.add_argument("--upload-only", action="store_true",
                        help="verify + upload the MP4s already in --out")
    parser.add_argument("--drive-folder", default=DEFAULT_DRIVE_FOLDER)
    args = parser.parse_args(argv)

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    selected = args.only or sorted(FACTORY_BY_NAME)
    unknown = [name for name in selected if name not in FACTORY_BY_NAME]
    if unknown:
        raise SystemExit(f"unknown recipe(s): {', '.join(unknown)}")

    entries: dict[str, dict] = {}
    problems: list[str] = []

    if args.upload_only:
        for name in selected:
            mp4 = out_dir / name / f"{name}.mp4"
            if mp4.exists():
                entries[name] = {"name": name, "mp4": str(mp4),
                                 "problems": _verify(mp4)}
    else:
        reuse = not args.no_reuse_native
        jobs = max(1, min(args.jobs, len(selected)))
        if jobs == 1:
            for name in selected:
                entry = _render_one(name, out_dir, reuse, args.force)
                entries[name] = entry
                print(f"  [{'OK' if entry.get('ok') else 'FAIL'}] {name}"
                      f"{' (native)' if entry.get('native') else ''}", flush=True)
        else:
            with ProcessPoolExecutor(max_workers=jobs) as pool:
                futures = {
                    pool.submit(_render_one, name, out_dir, reuse, args.force): name
                    for name in selected
                }
                for future in as_completed(futures):
                    name = futures[future]
                    entry = future.result()
                    entries[name] = entry
                    print(f"  [{'OK' if entry.get('ok') else 'FAIL'}] {name}"
                          f"{' (native)' if entry.get('native') else ''}", flush=True)

    for entry in entries.values():
        problems.extend(entry.get("problems", []))

    for problem in problems:
        print(f"  [VERIFY-FAIL] {problem}", file=sys.stderr)

    drive_links: dict | None = None
    if not args.skip_upload and not problems:
        drive_links = _upload(out_dir, args.drive_folder, entries)
    elif not args.skip_upload and problems:
        print("upload skipped: fix the verification failures first", file=sys.stderr)

    manifest = _assemble(out_dir, entries, drive_links)
    ok = sum(1 for entry in entries.values() if entry.get("ok"))
    print(f"web animations pod: {ok}/{len(selected)} OK "
          f"(manifest: {manifest})")
    return 0 if ok == len(selected) and not problems else 1


if __name__ == "__main__":
    raise SystemExit(main())
