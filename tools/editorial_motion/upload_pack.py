#!/usr/bin/env python3
"""Upload editorial_motion_pack_v1 to the requested Google Drive folder.

Uses the shared RenderingGen drive-upload binary and credential resolution.
The 25 verified 1080p MP4s, the contact sheet, the catalog and the upload
manifest land in a dedicated child folder of the supplied parent.

    VELOX_CONFIG_DIR=/path/to/velox \
      python3 ChrononTemplate/tools/editorial_motion/upload_pack.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
TEMPLATE = ROOT / "ChrononTemplate"
PACK = TEMPLATE / "golden_plans" / "editorial_motion_pack_v1"
CATALOG = PACK / "catalog.json"
RENDERS = TEMPLATE / "renders" / "editorial_motion_pack_v1"
UPLOADER = ROOT / "RenderingGen" / "bin" / "drive-upload"
PARENT_FOLDER = "1J_xUGo_bchzXDIGqSX04CU44c_Dm3SxS"
PARENT_URL = f"https://drive.google.com/drive/u/1/folders/{PARENT_FOLDER}"
SUBFOLDER = "Editorial_Motion_Pack_V1_20261110"

sys.path.insert(0, str(ROOT / "RenderingGen" / "UploadDrive"))
from drive_common import (  # noqa: E402
    config_paths,
    parse_upload_output,
    run_upload,
    sha256_file,
)


def entries(catalog: dict):
    for family in catalog["families"]:
        for preset in family["presets"]:
            yield family, preset


def upload(path: Path, name: str, credentials: Path, token: Path) -> dict:
    digest = sha256_file(path)
    last = ""
    for attempt in range(2):
        code, output = run_upload(
            UPLOADER, path, credentials, token, PARENT_FOLDER, SUBFOLDER,
            name, digest, timeout=900)
        last = output
        if code == 0 and "DRIVE_UPLOAD_PASS" in output:
            return {
                "drive_name": name,
                "drive_sha256": digest,
                "bytes": path.stat().st_size,
                **parse_upload_output(output),
            }
        if attempt == 0:
            print(f"[retry] {name}: rc={code} {output[:300]}", flush=True)
    raise RuntimeError(f"upload failed for {name}: {last[-1200:]}")


def main() -> int:
    catalog = json.loads(CATALOG.read_text())
    missing = []
    payload = []
    for family, preset in entries(catalog):
        if preset.get("status") != "rendered" or not preset.get("video"):
            missing.append(preset["id"])
            continue
        video = TEMPLATE / preset["video"]
        if not video.is_file():
            missing.append(preset["id"])
            continue
        payload.append((family, preset, video))
    if missing:
        print("not rendered: " + ", ".join(missing), file=sys.stderr)
        return 2

    credentials, token = config_paths()
    for required in (UPLOADER, credentials, token):
        if not required.is_file():
            print(f"missing upload requirement: {required}", file=sys.stderr)
            print("Set VELOX_CONFIG_DIR to the directory containing "
                  "credentials.json and token.json.", file=sys.stderr)
            return 3

    uploaded = []
    for family, preset, video in payload:
        name = f"EDITORIAL_MOTION_{preset['id'].upper()}_1920x1080.mp4"
        print(f"[upload] {name}", flush=True)
        result = upload(video, name, credentials, token)
        preset.update(result)
        uploaded.append({"id": preset["id"], "family": family["id"], **result})
        CATALOG.write_text(json.dumps(catalog, indent=2, ensure_ascii=False) + "\n")

    extras = []
    sheet = TEMPLATE / catalog.get("contact_sheet", "")
    if catalog.get("contact_sheet") and sheet.is_file():
        print(f"[upload] {sheet.name}", flush=True)
        result = upload(sheet, "EDITORIAL_MOTION_CATALOG_CONTACT_SHEET.jpg",
                        credentials, token)
        extras.append({"local": str(sheet.relative_to(TEMPLATE)), **result})
    print("[upload] EDITORIAL_MOTION_CATALOG.json", flush=True)
    catalog_result = upload(CATALOG, "EDITORIAL_MOTION_CATALOG.json",
                            credentials, token)
    extras.append({"local": str(CATALOG.relative_to(TEMPLATE)), **catalog_result})

    manifest = {
        "schema": "chronontemplate.editorial-motion-pack.drive.v1",
        "parent_folder_id": PARENT_FOLDER,
        "parent_url": PARENT_URL,
        "subfolder": SUBFOLDER,
        "clip_count": len(uploaded),
        "canvas": catalog["canvas"],
        "duration_frames": catalog["duration_frames"],
        "clips": uploaded,
        "extras": extras,
    }
    manifest_path = RENDERS / "UPLOAD-MANIFEST.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n")
    print("[upload] UPLOAD-MANIFEST.json", flush=True)
    manifest_result = upload(manifest_path, "EDITORIAL_MOTION_UPLOAD_MANIFEST.json",
                             credentials, token)
    manifest["manifest_upload"] = manifest_result
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n")
    print("DRIVE_UPLOADS_ALL_PASS", flush=True)
    print("subfolder", SUBFOLDER, "parent", PARENT_URL)
    print("manifest", manifest_result.get("link"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
