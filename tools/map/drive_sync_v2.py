#!/usr/bin/env python3
"""Drive sync v2: MP4s only, modernized renders.

Actions (all inside the user's Mappa folder 1WALc4...):
  del-stills N M   delete JPG stills [N:M] from map_systems_v1 subfolder
  update N M       in-place content update of MP4s [N:M] (ids/links unchanged)
  newfolder        create map_editorial_v1 + upload the 6 certified MP4s only
  verify           list both subfolders + report counts

Usage: drive_sync_v2.py <action> [lo] [hi]
State: out/map_systems_v1/drive_links_shared.json (old subfolder),
       out/map_editorial_v1/drive_links_ed.json (new, written by newfolder).
"""
from __future__ import annotations

import json
import sys
import urllib.parse
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
BASE_DIR = HERE.parents[2]
SYS_OUT = HERE.parents[1] / "out" / "map_systems_v1"
ED_OUT = HERE.parents[1] / "out" / "map_editorial_v1"

PARENT_FOLDER_ID = "1WALc4JbFz6uK5nEM_tYnAeQqiPVRacp_"
OLD_SUBFOLDER_ID = "11_zNtjGYE9uyTyQYYFN2tAb4cIWQuqV6"
ED_SUBFOLDER_NAME = "map_editorial_v1"

sys.path.insert(0, str(HERE))
from render_dynamic_map_3d_orbit_colosseum import (  # noqa: E402
    refresh_drive_token, upload_to_drive,
)


def api(token, method, url, data=None):
    body = json.dumps(data).encode() if data is not None else None
    headers = {"Authorization": "Bearer " + token}
    if body is not None:
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=body, headers=headers,
                                 method=method)
    with urllib.request.urlopen(req, timeout=180) as resp:
        raw = resp.read()
        return json.loads(raw) if raw else {}


def update_media(token, file_id, path: Path, mime: str):
    boundary = "-------ChrononDriveUpdate999"
    meta = json.dumps({"name": path.name})
    body = (
        f"--{boundary}\r\nContent-Type: application/json; charset=UTF-8\r\n\r\n"
        f"{meta}\r\n--{boundary}\r\nContent-Type: {mime}\r\n\r\n"
    ).encode() + path.read_bytes() + f"\r\n--{boundary}--\r\n".encode()
    url = ("https://www.googleapis.com/upload/drive/v3/files/" + file_id
           + "?uploadType=multipart&fields=id,modifiedTime,size")
    req = urllib.request.Request(
        url, data=body,
        headers={"Authorization": "Bearer " + token,
                 "Content-Type": f"multipart/related; boundary={boundary}",
                 "Content-Length": str(len(body))}, method="PATCH")
    with urllib.request.urlopen(req, timeout=300) as resp:
        return json.load(resp)


def mp4_list(outdir: Path):
    return sorted(outdir.glob("*.mp4"), key=lambda p: p.name)


def main() -> int:
    action = sys.argv[1]
    lo = int(sys.argv[2]) if len(sys.argv) > 2 else 0
    hi = int(sys.argv[3]) if len(sys.argv) > 3 else 10 ** 9
    token = refresh_drive_token()
    if action == "del-stills":
        shared = json.loads((SYS_OUT / "drive_links_shared.json")
                            .read_text())["files"]
        jpgs = sorted(n for n in shared if n.endswith(".jpg"))[lo:hi]
        for name in jpgs:
            api(token, "DELETE",
                "https://www.googleapis.com/drive/v3/files/"
                + shared[name]["id"])
            print("deleted: " + name, flush=True)
        print(f"DEL-STILLS done {len(jpgs)}", flush=True)
    elif action == "update":
        shared = json.loads((SYS_OUT / "drive_links_shared.json")
                            .read_text())["files"]
        mp4s = mp4_list(SYS_OUT)[lo:hi]
        for path in mp4s:
            res = update_media(token, shared[path.name]["id"], path,
                               "video/mp4")
            print(f"updated: {path.name} size={res.get('size')} "
                  f"mtime={res.get('modifiedTime')}", flush=True)
        print(f"UPDATE done {len(mp4s)}", flush=True)
    elif action == "newfolder":
        q = ("mimeType='application/vnd.google-apps.folder' and "
             "trashed=false and name='" + ED_SUBFOLDER_NAME + "' and '"
             + PARENT_FOLDER_ID + "' in parents")
        found = api(token, "GET",
                    "https://www.googleapis.com/drive/v3/files?q="
                    + urllib.parse.quote(q) + "&fields=files(id,name)")
        if found.get("files"):
            sub_id = found["files"][0]["id"]
            print("reusing " + ED_SUBFOLDER_NAME + " " + sub_id, flush=True)
        else:
            sub_id = api(token, "POST",
                         "https://www.googleapis.com/drive/v3/files"
                         "?fields=id",
                         {"name": ED_SUBFOLDER_NAME,
                          "mimeType": "application/vnd.google-apps.folder",
                          "parents": [PARENT_FOLDER_ID]})["id"]
            print("created " + ED_SUBFOLDER_NAME + " " + sub_id, flush=True)
        links = {"subfolder_id": sub_id,
                 "subfolder_link": ("https://drive.google.com/drive/folders/"
                                    + sub_id + "?usp=drive_link"),
                 "files": {}}
        for path in mp4_list(ED_OUT):
            res = upload_to_drive(path, token, sub_id)
            fid = res.get("id")
            links["files"][path.name] = {
                "id": fid,
                "link": ("https://drive.google.com/file/d/" + fid
                         + "/view?usp=drivesdk")}
            print(path.name + " :: " + links["files"][path.name]["link"],
                  flush=True)
        (ED_OUT / "drive_links_ed.json").write_text(
            json.dumps(links, indent=2), encoding="utf-8")
        print(f"NEWFOLDER done {len(links['files'])} mp4s :: "
              + links["subfolder_link"], flush=True)
    elif action == "verify":
        for label, sub in (("systems", OLD_SUBFOLDER_ID),):
            q = ("'" + sub + "' in parents and trashed=false")
            res = api(token, "GET",
                      "https://www.googleapis.com/drive/v3/files?q="
                      + urllib.parse.quote(q)
                      + "&fields=files(name,mimeType)&pageSize=100")
            names = sorted(f["name"] for f in res.get("files", []))
            mp4 = sum(1 for n in names if n.endswith(".mp4"))
            jpg = sum(1 for n in names if n.endswith(".jpg"))
            other = [n for n in names
                     if not n.endswith((".mp4", ".jpg"))]
            print(f"{label}: total={len(names)} mp4={mp4} jpg={jpg} "
                  f"other={other}", flush=True)
        edp = ED_OUT / "drive_links_ed.json"
        if edp.is_file():
            links = json.loads(edp.read_text())
            sub = links["subfolder_id"]
            q = ("'" + sub + "' in parents and trashed=false")
            res = api(token, "GET",
                      "https://www.googleapis.com/drive/v3/files?q="
                      + urllib.parse.quote(q)
                      + "&fields=files(id,name,mimeType)&pageSize=100")
            entries = sorted(res.get("files", []), key=lambda f: f["name"])
            names = [f["name"] for f in entries]
            expected = sorted(p.name for p in mp4_list(ED_OUT))
            expected = [name for name in expected
                        if name in links.get("files", {})]
            actual_mp4 = sorted(f["name"] for f in entries
                                if f.get("mimeType") == "video/mp4")
            extras = [f for f in entries if f.get("mimeType") != "video/mp4"]
            missing = sorted(set(expected) - set(actual_mp4))
            if missing or extras or actual_mp4 != expected:
                raise RuntimeError(f"Drive editorial verification failed: missing={missing}, non_mp4={[f['name'] for f in extras]}, actual={actual_mp4}, expected={expected}")
            print(f"editorial: total={len(names)} mp4={len(actual_mp4)} "
                  f"other=0 names={names}", flush=True)
    else:
        raise SystemExit("unknown action: " + action)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
