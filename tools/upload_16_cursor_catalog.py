#!/usr/bin/env python3
"""
Upload all 16 cursor catalogue animation scenes and master showreel to Google Drive
folder: 1ATL0bnJXijNqFlKkgWye3PEAdAuQa1HI
"""

import os
import sys
import json
import urllib.request
import urllib.parse
from pathlib import Path

BASE_DIR = Path("/home/pierone/src/go-master/projects/Pyt/VeloxEditing")
OUT_DIR = BASE_DIR / "ChrononTemplate" / "out" / "cursor_catalog_16"
TOKEN_PATH = BASE_DIR / "refactored" / "token.json"
CREDS_PATH = BASE_DIR / "refactored" / "credentials.json"
FOLDER_ID = "1ATL0bnJXijNqFlKkgWye3PEAdAuQa1HI"

def refresh_drive_token():
    with open(TOKEN_PATH) as f:
        tok_data = json.load(f)
    with open(CREDS_PATH) as f:
        creds = json.load(f)
    client_info = creds.get("installed") or creds.get("web")
    client_id = client_info["client_id"]
    client_secret = client_info["client_secret"]
    refresh_token = tok_data.get("refresh_token")
    
    params = {
        "client_id": client_id,
        "client_secret": client_secret,
        "refresh_token": refresh_token,
        "grant_type": "refresh_token"
    }
    data = urllib.parse.urlencode(params).encode()
    req = urllib.request.Request("https://oauth2.googleapis.com/token", data=data)
    with urllib.request.urlopen(req) as resp:
        res = json.load(resp)
        new_token = res["access_token"]
        tok_data["access_token"] = new_token
        with open(TOKEN_PATH, "w") as f:
            json.dump(tok_data, f, indent=2)
        return new_token

def upload_file(token, fpath, boundary):
    fname = fpath.name
    metadata = {
        "name": fname,
        "parents": [FOLDER_ID]
    }
    meta_json = json.dumps(metadata)
    file_bytes = fpath.read_bytes()
    
    body = (
        f"--{boundary}\r\n"
        f"Content-Type: application/json; charset=UTF-8\r\n\r\n"
        f"{meta_json}\r\n"
        f"--{boundary}\r\n"
        f"Content-Type: video/mp4\r\n\r\n"
    ).encode("utf-8") + file_bytes + f"\r\n--{boundary}--\r\n".encode("utf-8")
    
    req = urllib.request.Request(
        "https://www.googleapis.com/upload/drive/v3/files?uploadType=multipart",
        data=body,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": f"multipart/related; boundary={boundary}"
        },
        method="POST"
    )
    
    with urllib.request.urlopen(req) as resp:
        res = json.load(resp)
        file_id = res["id"]
        
    # Make public readable
    perm_body = json.dumps({"role": "reader", "type": "anyone"}).encode("utf-8")
    perm_req = urllib.request.Request(
        f"https://www.googleapis.com/drive/v3/files/{file_id}/permissions",
        data=perm_body,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        },
        method="POST"
    )
    try:
        with urllib.request.urlopen(perm_req):
            pass
    except Exception as e:
        print(f"  Warning setting public permission: {e}")
        
    view_url = f"https://drive.google.com/file/d/{file_id}/view?usp=sharing"
    return file_id, view_url

def update_file_media(token, file_id, fpath):
    file_bytes = fpath.read_bytes()
    req = urllib.request.Request(
        f"https://www.googleapis.com/upload/drive/v3/files/{file_id}?uploadType=media",
        data=file_bytes,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "video/mp4"
        },
        method="PATCH"
    )
    with urllib.request.urlopen(req) as resp:
        res = json.load(resp)
        return res["id"]

def upload_or_update(token, fpath, boundary, existing_id=None):
    if existing_id:
        try:
            print(f"  Updating existing file {existing_id} on Drive...", flush=True)
            fid = update_file_media(token, existing_id, fpath)
            view_url = f"https://drive.google.com/file/d/{fid}/view?usp=sharing"
            return fid, view_url
        except Exception as e:
            print(f"  Update failed ({e}), falling back to fresh upload...", flush=True)
    return upload_file(token, fpath, boundary)

def upload_all():
    token = refresh_drive_token()
    boundary = "----Chronon3DCursorUpload16"
    
    mp4_files = sorted(list(OUT_DIR.glob("cursor_scene_*.mp4")))
    master = OUT_DIR / "cursor_16_master_showreel.mp4"
    if master.exists() and master not in mp4_files:
        mp4_files.append(master)
        
    out_json = OUT_DIR / "upload_links.json"
    results = {}
    if out_json.exists():
        try:
            with open(out_json) as f:
                results = json.load(f)
        except Exception:
            results = {}

    print(f"Found {len(mp4_files)} videos to upload/update on Google Drive folder {FOLDER_ID}...", flush=True)
    
    for idx, fpath in enumerate(mp4_files, 1):
        fsize_mb = fpath.stat().st_size / (1024 * 1024)
        print(f"[{idx:02d}/{len(mp4_files):02d}] Uploading/updating {fpath.name} ({fsize_mb:.2f} MB)...", flush=True)
        existing_id = results.get(fpath.name, {}).get("id")
        fid, vurl = upload_or_update(token, fpath, boundary, existing_id)
        results[fpath.name] = {
            "id": fid,
            "url": vurl,
            "size_bytes": fpath.stat().st_size
        }
        print(f"  ✓ Live on Drive: {vurl}", flush=True)
        with open(out_json, "w") as f:
            json.dump(results, f, indent=2)
        
    print(f"\nAll {len(mp4_files)} files uploaded/updated successfully! Links saved to {out_json}")

if __name__ == "__main__":
    upload_all()
