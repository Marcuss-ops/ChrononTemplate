#!/usr/bin/env python3
"""Replace the ten delivered editorial preview videos, retaining Drive IDs."""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
from kit.drive import refresh_token

FOLDER = "12uXxT3uTNlLFclxsDxndq9U8KhF98CN_"


def update(directory: Path, previous_manifest: Path) -> None:
    previous = json.loads(previous_manifest.read_text())
    verification = json.loads((directory / "verification.json").read_text())
    local = {r["file"]: r for r in verification["videos"]}
    rows = previous["videos"]
    if previous["destination_folder"] != FOLDER or len(rows) != 10 or {r["file"] for r in rows} != set(local):
        raise ValueError("expected the exact ten previously delivered files in the requested folder")
    for row in rows:
        path = directory / row["file"]
        if hashlib.sha256(path.read_bytes()).hexdigest() != local[path.name]["sha256"]:
            raise ValueError(f"{path.name}: video changed after verification")
    oauth = ROOT.parent / "RenderingGen/UploadDrive"
    token = refresh_token(oauth / "token.json", oauth / "credentials.json")
    headers = {"Authorization": f"Bearer {token}"}
    result = {"destination_folder": FOLDER, "videos": []}
    for row in rows:
        file_id = row["id"]
        base = f"https://www.googleapis.com/drive/v3/files/{urllib.parse.quote(file_id, safe='')}"
        metadata_url = base + "?fields=id,name,parents,size,webViewLink&supportsAllDrives=true"
        with urllib.request.urlopen(urllib.request.Request(metadata_url, headers=headers), timeout=60) as response:
            metadata = json.load(response)
        if metadata["name"] != row["file"] or FOLDER not in metadata["parents"]:
            raise ValueError(f"{row['file']}: original Drive ID does not match its name/parent")
        path = directory / row["file"]
        payload = path.read_bytes()
        request = urllib.request.Request(
            f"https://www.googleapis.com/upload/drive/v3/files/{file_id}?uploadType=media&supportsAllDrives=true",
            data=payload, headers={**headers, "Content-Type": "video/mp4"}, method="PATCH",
        )
        with urllib.request.urlopen(request, timeout=120) as response:
            updated = json.load(response)
        if updated["id"] != file_id:
            raise ValueError("Drive returned a different file ID")
        with urllib.request.urlopen(urllib.request.Request(metadata_url, headers=headers), timeout=60) as response:
            metadata = json.load(response)
        with urllib.request.urlopen(urllib.request.Request(base + "?alt=media&supportsAllDrives=true", headers=headers), timeout=120) as response:
            remote = response.read()
        digest = hashlib.sha256(remote).hexdigest()
        if digest != local[path.name]["sha256"] or len(remote) != len(payload) or int(metadata["size"]) != len(payload):
            raise ValueError(f"{path.name}: remote content verification failed")
        result["videos"].append({"file": path.name, "id": file_id, "parent": FOLDER,
                                 "link": metadata.get("webViewLink", row["link"]),
                                 "sha256": digest, "bytes": len(payload), "remote_download_verified": True})
        (directory / "upload_manifest.json").write_text(json.dumps(result, indent=2) + "\n")
        print(f"DRIVE_UPDATE_PASS file={path.name} id={file_id} sha256={digest} bytes={len(payload)}", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    parser.add_argument("--previous-manifest", type=Path, required=True)
    args = parser.parse_args()
    update(args.directory.resolve(), args.previous_manifest.resolve())
