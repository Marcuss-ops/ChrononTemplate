#!/usr/bin/env python3
"""Copy map_systems_v1 files server-side into the user's Drive folder.

Creates subfolder `map_systems_v1` inside PARENT_FOLDER_ID, then files.copy
each of the 32 uploaded files (no re-upload bandwidth) and grants
anyone-reader, mirroring the original uploads. Resumable: skips names
already present. Writes new links to drive_links_shared.json.
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

PARENT_FOLDER_ID = "1WALc4JbFz6uK5nEM_tYnAeQqiPVRacp_"
SUBFOLDER_NAME = "map_systems_v1"

sys.path.insert(0, str(HERE))
from render_dynamic_map_3d_orbit_colosseum import refresh_drive_token  # noqa: E402


def api(token, method, url, data=None):
    body = json.dumps(data).encode() if data is not None else None
    headers = {"Authorization": "Bearer " + token}
    if body is not None:
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=body, headers=headers,
                                 method=method)
    with urllib.request.urlopen(req, timeout=120) as resp:
        raw = resp.read()
        return json.loads(raw) if raw else {}


def main():
    token = refresh_drive_token()
    parent = api(token, "GET",
                 "https://www.googleapis.com/drive/v3/files/"
                 + PARENT_FOLDER_ID + "?fields=id,name,mimeType")
    print("parent: " + parent.get("name") + " (" + parent.get("id") + ")",
          flush=True)
    q = ("mimeType='application/vnd.google-apps.folder' and trashed=false "
         "and name='" + SUBFOLDER_NAME + "' and '" + PARENT_FOLDER_ID
         + "' in parents")
    found = api(token, "GET", "https://www.googleapis.com/drive/v3/files?q="
                + urllib.parse.quote(q) + "&fields=files(id,name)")
    if found.get("files"):
        sub_id = found["files"][0]["id"]
        print("reusing subfolder " + SUBFOLDER_NAME + " " + sub_id,
              flush=True)
    else:
        sub_id = api(token, "POST",
                     "https://www.googleapis.com/drive/v3/files?fields=id",
                     {"name": SUBFOLDER_NAME,
                      "mimeType": "application/vnd.google-apps.folder",
                      "parents": [PARENT_FOLDER_ID]})["id"]
        print("created subfolder " + SUBFOLDER_NAME + " " + sub_id,
              flush=True)
    existing = api(token, "GET",
                   "https://www.googleapis.com/drive/v3/files?q="
                   + urllib.parse.quote("'" + sub_id + "' in parents and "
                                        "trashed=false")
                   + "&fields=files(id,name)&pageSize=100")
    have = {f["name"]: f["id"] for f in existing.get("files", [])}
    src = json.loads((OUT / "drive_links.json").read_text())["files"]
    links = {"parent_folder_id": PARENT_FOLDER_ID, "subfolder_id": sub_id,
             "subfolder_link": ("https://drive.google.com/drive/folders/"
                                + sub_id + "?usp=drive_link"),
             "files": {}}
    for name, info in sorted(src.items()):
        if name in have:
            fid = have[name]
            print("skip (present): " + name, flush=True)
        else:
            fid = api(token, "POST",
                      "https://www.googleapis.com/drive/v3/files/"
                      + info["id"] + "/copy?fields=id",
                      {"name": name, "parents": [sub_id]})["id"]
            try:
                api(token, "POST",
                    "https://www.googleapis.com/drive/v3/files/" + fid
                    + "/permissions", {"role": "reader", "type": "anyone"})
            except Exception as exc:
                print("permission note " + name + ": " + str(exc)[:100],
                      flush=True)
            print(name + " :: copied " + fid, flush=True)
        links["files"][name] = {
            "id": fid,
            "link": ("https://drive.google.com/file/d/" + fid
                     + "/view?usp=drivesdk")}
    (OUT / "drive_links_shared.json").write_text(json.dumps(links, indent=2),
                                                 encoding="utf-8")
    print("NEW FOLDER LINK: " + links["subfolder_link"], flush=True)
    print("links saved (files: %d)" % len(links["files"]), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
