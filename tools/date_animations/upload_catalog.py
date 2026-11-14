#!/usr/bin/env python3
"""Upload the rendered date animation catalog to the requested Drive folder.

- uploads all 13 MP4s (including Rolling Year, re-rendered without labels)
- rebuilds and uploads the 13-tile contact sheet from fresh final-video frames
- writes links, bytes and SHA-256 back to catalog.json and uploads it
"""
from __future__ import annotations

import sys as _velox_sys
from pathlib import Path as _VeloxPath
_velox_sys.path.insert(0, str(_VeloxPath(__file__).resolve().parents[3] / "tools"))
from stack_config import overlay_root as _overlay_root  # noqa: E402

import os
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[3]
CHRONON = ROOT / "ChrononTemplate"
CAT = CHRONON / "golden_plans" / "date_animation_catalog" / "catalog.json"
RENDERS = CHRONON / "renders" / "date_animation_catalog"
PREVIEW = RENDERS / "preview"
DRIVE = ROOT / "RenderingGen" / "renderinggen" / "drive-upload"
CREDS = ROOT / "RenderingGen" / "UploadDrive" / "credentials.json"
TOKEN = ROOT / "RenderingGen" / "UploadDrive" / "token.json"
FOLDER = _overlay_root()
FOLDER_URL = f"https://drive.google.com/drive/u/1/folders/{FOLDER}"


def upload(path: Path, name: str) -> dict:
    proc = subprocess.run(
        [str(DRIVE), "-credentials", str(CREDS), "-token", str(TOKEN),
         "-folder", FOLDER, "-file", str(path), "-name", name],
        text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
    )
    if proc.returncode != 0:
        raise RuntimeError(proc.stdout[-1600:])
    m = re.search(r"DRIVE_UPLOAD_PASS id=(\S+) link=(\S+) parent=(\S+) sha256=(\S+) bytes=(\d+)", proc.stdout)
    if not m:
        raise RuntimeError("no DRIVE_UPLOAD_PASS in:\n" + proc.stdout[-1600:])
    sha = hashlib.sha256(path.read_bytes()).hexdigest()
    if sha.lower() != m.group(4).lower():
        raise RuntimeError(f"sha mismatch for {path}")
    return {"drive_id": m.group(1), "link": m.group(2),
            "sha256": sha, "bytes": int(m.group(5))}


def refresh_preview(entry: dict) -> Path:
    p = PREVIEW / f"{entry['slug']}.png"
    video = CHRONON / entry["video"]
    if video.is_file():
        PREVIEW.mkdir(parents=True, exist_ok=True)
        proc = subprocess.run(
            ["ffmpeg", "-y", "-ss", "2", "-i", str(video), "-frames:v", "1", str(p)],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
        )
        if proc.returncode != 0:
            raise RuntimeError(f"preview extract failed for {entry['slug']}:\n{proc.stdout[-1200:]}")
    if not p.is_file():
        raise RuntimeError(f"missing preview for {entry['slug']}")
    return p


def make_sheet(catalog: dict) -> Path:
    tiles = []
    for entry in catalog["presets"]:
        p = refresh_preview(entry)
        im = Image.open(p).convert("RGB")
        im.thumbnail((384, 216))
        canvas = Image.new("RGB", (384, 246), (243, 241, 235))
        canvas.paste(im, (0, 0))
        draw = ImageDraw.Draw(canvas)
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 15)
        except Exception:
            font = None
        draw.text((10, 220), f"{entry['slug'][:2]}  {entry['title']}", fill=(30, 30, 30), font=font)
        tiles.append(canvas)
    cols, rows = 5, 3
    sheet = Image.new("RGB", (cols * 384, rows * 246), (243, 241, 235))
    for i, tile in enumerate(tiles):
        sheet.paste(tile, ((i % cols) * 384, (i // cols) * 246))
    out = RENDERS / "catalog_contact_sheet.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out)
    return out


def main() -> int:
    catalog = json.loads(CAT.read_text())
    missing = [e["slug"] for e in catalog["presets"] if e["status"] not in ("rendered", "existing")]
    if missing:
        print("not all presets rendered:", missing, file=sys.stderr)
        return 2

    for entry in catalog["presets"]:
        if entry["status"] != "rendered":
            continue
        path = CHRONON / entry["video"]
        if not path.is_file():
            print("missing render", path, file=sys.stderr)
            return 3
        name = f"DATEANIM_{entry['slug'].upper()}_1920x1080.mp4"
        print("upload", entry["slug"], flush=True)
        result = upload(path, name)
        entry.update(result)
        entry["drive_name"] = name
        CAT.write_text(json.dumps(catalog, indent=2, ensure_ascii=False) + "\n")

    sheet = make_sheet(catalog)
    sheet_result = upload(sheet, "DATEANIM_CATALOG_13_STILLS.png")
    CAT.write_text(json.dumps(catalog, indent=2, ensure_ascii=False) + "\n")
    catalog_result = upload(CAT, "DATEANIM_CATALOG_13.json")
    CAT.write_text(json.dumps(catalog, indent=2, ensure_ascii=False) + "\n")

    manifest = {
        "folder_id": FOLDER,
        "folder_url": FOLDER_URL,
        "contact_sheet": sheet_result,
        "catalog_json": catalog_result,
        "presets": [
            {
                "slug": e["slug"],
                "title": e["title"],
                "status": e["status"],
                "drive_name": e.get("drive_name"),
                "link": e.get("link"),
                "bytes": e.get("bytes"),
            }
            for e in catalog["presets"]
        ],
    }
    (RENDERS / "UPLOAD-MANIFEST.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print("folder", FOLDER_URL)
    print("contact_sheet", sheet_result["link"])
    print("catalog", catalog_result["link"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
