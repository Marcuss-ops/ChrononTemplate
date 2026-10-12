#!/usr/bin/env python3
"""Upload map_systems_v1 to Drive: one folder, 15 mp4 + 15 stills + manifest.

Usage: upload_map_systems_v1.py [start_index [end_index]]
Writes links to out/map_systems_v1/drive_links.json (merged across runs).
"""
from __future__ import annotations

import json
import sys
import urllib.parse
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
BASE_DIR = HERE.parents[2]
OUT = HERE.parents[1] / "out" / "map_systems_v1"
TOKEN_PATH = BASE_DIR / "refactored/token.json"
CREDS_PATH = BASE_DIR / "refactored/credentials.json"
FOLDER_NAME = "map_systems_v1"
LINKS_PATH = OUT / "drive_links.json"

sys.path.insert(0, str(HERE))
from render_dynamic_map_3d_orbit_colosseum import (  # noqa: E402
    refresh_drive_token, upload_to_drive,
)

MIME = {".mp4": "video/mp4", ".jpg": "image/jpeg", ".json": "application/json",
        ".md": "text/markdown"}


def api(token, method, url, data=None, ctype="application/json"):
    req = urllib.request.Request(
        url, data=json.dumps(data).encode() if data is not None else None,
        headers={"Authorization": "Bearer " + token,
                 "Content-Type": ctype} if data is not None
        else {"Authorization": "Bearer " + token}, method=method)
    with urllib.request.urlopen(req, timeout=120) as resp:
        return json.load(resp)


def find_folder(token, name):
    q = ("mimeType='application/vnd.google-apps.folder' and "
         "trashed=false and name='" + name + "'")
    res = api(token, "GET", "https://www.googleapis.com/drive/v3/files?q="
              + urllib.parse.quote(q) + "&fields=files(id,name)")
    for f in res.get("files", []):
        if f["name"] == name:
            return f["id"]
    return None


def main():
    files = []
    for i in range(1, 16):
        slug = "%02d_" % i + ["simple_label", "region_zoom", "bracket_label",
            "photo_callout", "pulse_marker", "multi_locations", "focus_title",
            "route_line", "spotlight", "region_fill", "info_card",
            "vertical_callout", "icon_label", "label_reveal",
            "global_context"][i - 1]
        files.append(OUT / (slug + ".mp4"))
        files.append(OUT / (slug + ".jpg"))
    files += [OUT / "manifest.json", OUT / "README.md"]
    lo = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    hi = int(sys.argv[2]) if len(sys.argv) > 2 else len(files)
    token = refresh_drive_token()
    folder_id = find_folder(token, FOLDER_NAME)
    if folder_id is None:
        folder_id = api(token, "POST",
                        "https://www.googleapis.com/drive/v3/files?fields=id",
                        {"name": FOLDER_NAME,
                         "mimeType": "application/vnd.google-apps.folder"})["id"]
        print("created folder " + FOLDER_NAME + " " + folder_id, flush=True)
    else:
        print("reusing folder " + FOLDER_NAME + " " + folder_id, flush=True)
    links = {}
    if LINKS_PATH.is_file():
        links = json.loads(LINKS_PATH.read_text(encoding="utf-8"))
    links.setdefault("folder_id", folder_id)
    links.setdefault("files", {})
    for path in files[lo:hi]:
        res = upload_to_drive(path, token, folder_id)
        fid = res.get("id")
        link = "https://drive.google.com/file/d/" + fid + "/view?usp=drivesdk"
        links["files"][path.name] = {"id": fid, "link": link}
        print(path.name + " :: " + link, flush=True)
    LINKS_PATH.write_text(json.dumps(links, indent=2), encoding="utf-8")
    print("links saved: " + str(LINKS_PATH), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
