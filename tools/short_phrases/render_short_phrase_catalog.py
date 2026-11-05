#!/usr/bin/env python3
"""Render and review the 27 short-phrase recipes in the current catalog.

The official emitter lowers the C++ archetypes to chronon.render-plan.v2/v3.
This runner keeps the catalog review reproducible:

    --emit              emit all 27 plans + manifest.json
    --render --batch N  render batch N (9 clips each, resumable)
    --verify            probe every MP4 and decode a mid-hold preview
    --sheet             build the contact sheet from verified previews
    --upload            upload the 27 MP4s + sheet to Drive

Every clip is 1920x1080, 30 fps, 210 frames (7.00 s), matching the official
tools/short_phrases/render_short_phrases.sh lane: Vulkan + NVENC + QP 18.

Usage:
    tools/short_phrases/render_short_phrase_catalog.py --emit
    tools/short_phrases/render_short_phrase_catalog.py --render --batch 1
    tools/short_phrases/render_short_phrase_catalog.py --verify
    tools/short_phrases/render_short_phrase_catalog.py --sheet
    tools/short_phrases/render_short_phrase_catalog.py --upload
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import subprocess
import sys
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont, ImageStat

ROOT = Path(__file__).resolve().parents[2]
REPO = ROOT.parent
ASSETS = REPO / "Chronon3d"
OUT = ROOT / "out" / "short_phrase_catalog_v1"
PLANS = OUT / "plans"
MP4 = OUT / "mp4"
PREVIEW = OUT / "preview"
LOGS = OUT / "logs"
CATALOG = ROOT / "catalog" / "short_phrase_motion.v1.json"

EMITTER = ROOT / "build/dev-fast/chronontemplate_emit_short_phrase_plans"
CLI = ASSETS / "build/chronon/linux-video-release/apps/chronon3d_cli/chronon3d_cli"
UPLOADER = REPO / "RenderingGen/bin/drive-upload"
CREDENTIALS = REPO / "RenderingGen/UploadDrive/credentials.json"
TOKEN = REPO / "RenderingGen/UploadDrive/token.json"

DRIVE_FOLDER = "1J_xUGo_bchzXDIGqSX04CU44c_Dm3SxS"
DRIVE_SUBFOLDER = "Short Phrase Animations v1"
BATCH_SIZE = 9

W, H, FPS, FRAMES = 1920, 1080, 30, 210
DURATION_S = FRAMES / FPS
PREVIEW_SECONDS = 4.0

FAMILY_ORDER = {"classic": 0, "editorial": 1, "product": 2}
FAMILY_LABEL = {"classic": "classic", "editorial": "editorial", "product": "product_video"}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_catalog() -> dict[str, dict[str, Any]]:
    data = json.loads(CATALOG.read_text())
    return {entry["id"]: entry for entry in data["recipes"]}


def load_manifest() -> dict[str, Any]:
    path = PLANS / "manifest.json"
    if not path.is_file():
        raise SystemExit(f"missing emitted manifest: {path}")
    return json.loads(path.read_text())


def review_manifest() -> dict[str, Any]:
    path = OUT / "manifest.json"
    if path.is_file():
        return json.loads(path.read_text())
    manifest = load_manifest()
    catalog = load_catalog()
    entries = []
    for animation in manifest["animations"]:
        recipe = catalog.get(animation["id"], {})
        entries.append(
            {
                **animation,
                "family": recipe.get("family", "unknown"),
                "subcategory": recipe.get("subcategory", ""),
                "runtime_enabled": recipe.get("runtime_enabled", False),
                "timing": recipe.get("timing", {}),
            }
        )
    return {
        "schema": "chronontemplate.short-phrase-catalog-review.v1",
        "source_catalog": str(CATALOG.relative_to(ROOT)),
        "canvas": manifest["canvas"],
        "style": manifest.get("style", {}),
        "drive": {"folder_id": DRIVE_FOLDER, "subfolder": DRIVE_SUBFOLDER},
        "animations": entries,
    }


def save_review(review: dict[str, Any]) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "manifest.json").write_text(
        json.dumps(review, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )


def entry_order(entry: dict[str, Any]) -> tuple[int, str]:
    return (FAMILY_ORDER.get(entry["family"], 9), entry["id"])


def emit() -> int:
    for directory in (PLANS, MP4, PREVIEW, LOGS):
        directory.mkdir(parents=True, exist_ok=True)
    subprocess.run([str(EMITTER), str(PLANS)], check=True, cwd=ROOT)
    manifest = load_manifest()
    print(f"EMITTED {len(manifest['animations'])} plans in {PLANS.relative_to(ROOT)}")
    return 0


def validate(plan: Path) -> None:
    subprocess.run(
        [str(CLI), "validate", "--plan", str(plan), "--assets-root", str(ASSETS)],
        check=True,
        cwd=REPO,
        stdout=subprocess.DEVNULL,
    )


def probe(path: Path) -> dict[str, Any]:
    result = subprocess.run(
        [
            "ffprobe", "-v", "error", "-count_frames", "-select_streams", "v:0",
            "-show_entries", "stream=width,height,nb_read_frames,r_frame_rate:format=duration",
            "-of", "json", str(path),
        ],
        check=True, text=True, capture_output=True,
    )
    stream = json.loads(result.stdout)["streams"][0]
    data = json.loads(result.stdout)
    frames = int(stream.get("nb_read_frames") or stream.get("nb_frames") or 0)
    return {
        "width": int(stream["width"]),
        "height": int(stream["height"]),
        "frames": frames,
        "duration_s": round(float(data["format"]["duration"]), 3),
    }


def decode_preview(video: Path, image: Path) -> None:
    subprocess.run(
        [
            "ffmpeg", "-y", "-v", "error", "-ss", f"{PREVIEW_SECONDS}",
            "-i", str(video), "-frames:v", "1", "-update", "1", str(image),
        ],
        check=True,
        cwd=REPO,
    )
    with Image.open(image) as frame:
        if frame.size != (W, H):
            raise RuntimeError(f"{image.name}: expected 1920x1080, got {frame.size}")
        rgb = frame.convert("RGB")
        if max(ImageStat.Stat(rgb).stddev) < 2.0:
            raise RuntimeError(f"{image.name}: decoded frame has no visible variation")
        if len(rgb.getcolors(maxcolors=1_000_000) or []) < 8:
            raise RuntimeError(f"{image.name}: decoded frame is flat")


def verify_entry(entry: dict[str, Any]) -> dict[str, Any]:
    slug = entry["id"]
    video = MP4 / f"{slug}.mp4"
    if not video.is_file():
        raise RuntimeError(f"missing render: {video.relative_to(ROOT)}")
    info = probe(video)
    if (info["width"], info["height"]) != (W, H):
        raise RuntimeError(f"{slug}: expected 1920x1080, got {info['width']}x{info['height']}")
    if info["frames"] != FRAMES:
        raise RuntimeError(f"{slug}: expected {FRAMES} frames, got {info['frames']}")
    if abs(info["duration_s"] - DURATION_S) > 0.12:
        raise RuntimeError(f"{slug}: expected {DURATION_S:.2f}s, got {info['duration_s']:.2f}s")
    image = PREVIEW / f"{slug}.png"
    decode_preview(video, image)
    entry.update(
        mp4=f"mp4/{video.name}",
        preview=f"preview/{image.name}",
        width=info["width"],
        height=info["height"],
        frames=info["frames"],
        duration_s=info["duration_s"],
        sha256=sha256(video),
        bytes=video.stat().st_size,
    )
    return entry


def selected_entries(review: dict[str, Any], batch: int, only: str) -> list[dict[str, Any]]:
    entries = sorted(review["animations"], key=entry_order)
    if only:
        entries = [e for e in entries if only in e["id"]]
    elif batch:
        start = (batch - 1) * BATCH_SIZE
        entries = entries[start : start + BATCH_SIZE]
    if not entries:
        raise SystemExit("no catalog entries match the selection")
    return entries


def persist_entry(review: dict[str, Any], entry: dict[str, Any]) -> None:
    by_id = {e["id"]: e for e in review["animations"]}
    by_id[entry["id"]] = entry
    review["animations"] = sorted(by_id.values(), key=entry_order)
    save_review(review)


def render(batch: int, only: str, force: bool) -> int:
    review = review_manifest()
    entries = selected_entries(review, batch, only)
    print(f"BATCH {batch or '-'} · {len(entries)} clips")
    failures: list[tuple[str, str]] = []
    for index, entry in enumerate(entries, start=1):
        slug = entry["id"]
        plan = PLANS / entry["plan"]
        video = MP4 / f"{slug}.mp4"
        print(f"[{index}/{len(entries)}] {slug}", flush=True)
        try:
            validate(plan)
            if video.is_file() and not force:
                try:
                    entry = verify_entry(entry)
                    persist_entry(review, entry)
                    print(f"  SKIP verified {video.name}", flush=True)
                    continue
                except Exception:
                    print(f"  existing file invalid, re-rendering", flush=True)
            LOGS.mkdir(parents=True, exist_ok=True)
            log = LOGS / f"{slug}.log"
            with log.open("w") as handle:
                subprocess.run(
                    [
                        str(CLI), "render",
                        "--plan", str(plan),
                        "--assets-root", str(ASSETS),
                        "--backend", "vulkan",
                        "--hardware", "nvenc",
                        "--encoder-backend", "pipe",
                        "--codec", "h264",
                        "--fps", str(FPS),
                        "--rate-control", "qp",
                        "--qp", "18",
                        "-o", str(video),
                    ],
                    check=True,
                    cwd=REPO,
                    stdout=handle,
                    stderr=subprocess.STDOUT,
                )
            entry = verify_entry(entry)
            persist_entry(review, entry)
            print(
                f"  PASS {entry['frames']}f · {entry['duration_s']:.2f}s · "
                f"{entry['bytes'] / 1024 / 1024:.2f} MB",
                flush=True,
            )
        except Exception as error:  # keep rendering the batch; report at the end
            failures.append((slug, str(error)))
            print(f"  FAIL {error}", flush=True)
    # Persist every successfully verified entry, including skipped ones.
    by_id = {e["id"]: e for e in review["animations"]}
    by_id.update({e["id"]: e for e in entries})
    review["animations"] = sorted(by_id.values(), key=entry_order)
    save_review(review)
    if failures:
        print(f"FAILED {len(failures)}/{len(entries)}")
        for slug, error in failures:
            print(f"  {slug}: {error}")
        return 1
    print(f"BATCH_OK {len(entries)}/{len(entries)}")
    return 0


def verify() -> int:
    review = review_manifest()
    failures = []
    entries = sorted(review["animations"], key=entry_order)
    for index, entry in enumerate(entries, start=1):
        try:
            verify_entry(entry)
            print(f"[{index}/{len(entries)}] PASS {entry['id']}")
        except Exception as error:
            failures.append((entry["id"], str(error)))
            print(f"[{index}/{len(entries)}] FAIL {entry['id']}: {error}")
    save_review(review)
    if failures:
        print(f"VERIFY_FAILED {len(failures)}/{len(entries)}")
        return 1
    print(f"VERIFY_PASS {len(entries)}/{len(entries)}")
    return 0


def contact_sheet(review: dict[str, Any]) -> Path:
    entries = sorted(review["animations"], key=entry_order)
    missing = [e["id"] for e in entries if not (PREVIEW / f"{e['id']}.png").is_file()]
    if missing:
        raise SystemExit(f"contact sheet needs {len(missing)} more previews: {missing[:5]}")
    thumb_w, thumb_h, gutter, label_h = 440, 248, 22, 56
    cols = 4
    rows = math.ceil(len(entries) / cols)
    sheet = Image.new(
        "RGB",
        (cols * thumb_w + (cols + 1) * gutter, rows * (thumb_h + label_h) + (rows + 1) * gutter),
        (18, 18, 20),
    )
    draw = ImageDraw.Draw(sheet)
    font_dir = ASSETS / "assets" / "fonts"
    try:
        title_font = ImageFont.truetype(str(font_dir / "Inter-SemiBold.ttf"), 21)
        meta_font = ImageFont.truetype(str(font_dir / "Inter-Light.ttf"), 15)
    except OSError:
        title_font = ImageFont.load_default()
        meta_font = ImageFont.load_default()
    for index, entry in enumerate(entries):
        col, row = index % cols, index // cols
        x = gutter + col * (thumb_w + gutter)
        y = gutter + row * (thumb_h + label_h + gutter)
        with Image.open(PREVIEW / f"{entry['id']}.png") as frame:
            thumb = frame.convert("RGB").resize((thumb_w, thumb_h), Image.LANCZOS)
            sheet.paste(thumb, (x, y + label_h))
        draw.text(
            (x, y + 2), f"{index + 1:02d} · {entry['title']}",
            font=title_font, fill=(242, 242, 245),
        )
        meta = (
            f"{FAMILY_LABEL.get(entry['family'], entry['family'])} · "
            f"{entry['unit']} · exit {entry['exit']} · {entry['word_count']} words"
        )
        draw.text((x, y + 30), meta, font=meta_font, fill=(168, 168, 176))
    path = OUT / "SHORT_PHRASE_CATALOG_contact_sheet.png"
    sheet.save(path, optimize=True)
    return path


def sheet() -> int:
    review = review_manifest()
    path = contact_sheet(review)
    review["contact_sheet"] = {
        "path": path.name,
        "bytes": path.stat().st_size,
        "sha256": sha256(path),
    }
    save_review(review)
    print(f"CONTACT_SHEET {path.relative_to(ROOT)} ({len(review['animations'])} clips)")
    return 0


def drive_upload(path: Path, name: str) -> dict[str, str]:
    result = subprocess.run(
        [
            str(UPLOADER),
            "-credentials", str(CREDENTIALS),
            "-token", str(TOKEN),
            "-folder", DRIVE_FOLDER,
            "-subfolder", DRIVE_SUBFOLDER,
            "-file", str(path),
            "-name", name,
            "-sha256", sha256(path),
        ],
        check=True, text=True, capture_output=True,
    )
    line = result.stdout.strip().splitlines()[-1] if result.stdout.strip() else ""
    if "DRIVE_UPLOAD_PASS" not in line:
        raise RuntimeError(f"Drive did not verify {path.name}: {line}")
    fields = dict(part.split("=", 1) for part in line.split() if "=" in part)
    return {
        "result": line,
        "drive_id": fields.get("id", ""),
        "link": fields.get("link", ""),
    }


def upload() -> int:
    for required in (UPLOADER, CREDENTIALS, TOKEN):
        if not required.is_file():
            raise SystemExit(f"missing Drive prerequisite: {required}")
    review = review_manifest()
    entries = sorted(review["animations"], key=entry_order)
    failures = []
    for index, entry in enumerate(entries, start=1):
        if entry.get("uploaded") and entry.get("link"):
            print(f"[{index}/{len(entries)}] DRIVE_SKIP {entry['id']}")
            continue
        video = MP4 / f"{entry['id']}.mp4"
        name = f"SHORT_PHRASE_{entry['id'].removeprefix('short_phrase_').upper()}_1920x1080.mp4"
        try:
            result = drive_upload(video, name)
            entry.update(
                uploaded=True,
                drive_id=result["drive_id"],
                link=result["link"],
                drive_name=name,
            )
            print(f"[{index}/{len(entries)}] DRIVE_PASS {entry['id']} {result['link']}")
        except Exception as error:
            failures.append((entry["id"], str(error)))
            print(f"[{index}/{len(entries)}] DRIVE_FAIL {entry['id']}: {error}")
    shot = OUT / review.get("contact_sheet", {}).get("path", "")
    if shot.is_file() and not review.get("contact_sheet", {}).get("uploaded"):
        try:
            result = drive_upload(shot, "SHORT_PHRASE_CATALOG_contact_sheet.png")
            review["contact_sheet"].update(
                uploaded=True,
                drive_id=result["drive_id"],
                link=result["link"],
                drive_name="SHORT_PHRASE_CATALOG_contact_sheet.png",
            )
            print(f"DRIVE_PASS contact_sheet {result['link']}")
        except Exception as error:
            failures.append(("contact_sheet", str(error)))
            print(f"DRIVE_FAIL contact_sheet: {error}")
    review["drive"] = {"folder_id": DRIVE_FOLDER, "subfolder": DRIVE_SUBFOLDER}
    save_review(review)
    write_upload_manifest(review)
    if failures:
        print(f"UPLOAD_FAILED {len(failures)}")
        return 1
    print(f"UPLOAD_PASS {len(entries)}/{len(entries)}")
    return 0


def write_upload_manifest(review: dict[str, Any]) -> None:
    entries = sorted(review["animations"], key=entry_order)
    lines = [
        "# Short phrase animations — catalogo attuale",
        "",
        f"Drive: https://drive.google.com/drive/folders/{DRIVE_FOLDER}",
        f"Sottocartella: {DRIVE_SUBFOLDER}",
        "",
        "Tutti i clip: 1920×1080, 30 fps, 210 frame (7,00 s), H.264 QP 18.",
        "",
        "| # | Famiglia | Titolo | Frase | Uscita | Video |",
        "|---|---|---|---|---|---|",
    ]
    for index, entry in enumerate(entries, start=1):
        link = f"[apri]({entry['link']})" if entry.get("link") else "—"
        phrase = entry["phrase"].replace("|", "\\|")
        lines.append(
            f"| {index:02d} | {FAMILY_LABEL.get(entry['family'], entry['family'])} | "
            f"{entry['title']} | {phrase} | {entry['exit']} | {link} |"
        )
    if review.get("contact_sheet", {}).get("link"):
        lines += ["", f"Contact sheet: {review['contact_sheet']['link']}"]
    (OUT / "UPLOAD-MANIFEST.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--emit", action="store_true")
    parser.add_argument("--render", action="store_true")
    parser.add_argument("--verify", action="store_true")
    parser.add_argument("--sheet", action="store_true")
    parser.add_argument("--upload", action="store_true")
    parser.add_argument("--batch", type=int, default=0, choices=range(0, 4))
    parser.add_argument("--only", default="")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    if not (args.emit or args.render or args.verify or args.sheet or args.upload):
        parser.print_help()
        return 0
    for required in (CLI, ASSETS, EMITTER):
        if not required.exists():
            raise SystemExit(f"missing renderer prerequisite: {required}")
    if args.emit:
        return emit()
    if args.render:
        return render(args.batch, args.only, args.force)
    if args.verify:
        return verify()
    if args.sheet:
        return sheet()
    return upload()


if __name__ == "__main__":
    sys.exit(main())
