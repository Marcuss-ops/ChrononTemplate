#!/usr/bin/env python3
"""
Upload all 12 cursor animation scenes and master showreel to Google Drive
folder: 1ATL0bnJXijNqFlKkgWye3PEAdAuQa1HI
"""

import os
import sys
import json
import urllib.request
import urllib.parse
from pathlib import Path

BASE_DIR = Path("/home/pierone/src/go-master/projects/Pyt/VeloxEditing")
OUT_DIR = BASE_DIR / "ChrononTemplate" / "out" / "cursor_animations"
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

def upload_all():
    token = refresh_drive_token()
    boundary = "----Chronon3DCursorUpload"
    
    mp4_files = sorted(list(OUT_DIR.glob("cursor_scene_*.mp4")))
    master = OUT_DIR / "cursor_master_showreel.mp4"
    if master.exists() and master not in mp4_files:
        mp4_files.append(master)
        
    print(f"Found {len(mp4_files)} cursor videos to upload to Google Drive...")
    links = {}
    
    for idx, fpath in enumerate(mp4_files, 1):
        fname = fpath.name
        print(f"[{idx}/{len(mp4_files)}] Uploading {fname} ({fpath.stat().st_size} bytes)...", flush=True)
        try:
            fid, url = upload_file(token, fpath, boundary)
            links[fname] = {"id": fid, "url": url}
            print(f"  ✓ {fname}: {url}")
        except urllib.error.HTTPError as e:
            if e.code == 401:
                print("  Token expired during upload, refreshing...")
                token = refresh_drive_token()
                fid, url = upload_file(token, fpath, boundary)
                links[fname] = {"id": fid, "url": url}
                print(f"  ✓ {fname}: {url}")
            else:
                print(f"  ✗ Failed to upload {fname}: {e}")
                
    summary_path = OUT_DIR / "upload_links.json"
    with open(summary_path, "w") as f:
        json.dump(links, f, indent=2)
    print(f"\nAll uploads finished! Summary written to {summary_path}")
    return links

if __name__ == "__main__":
    upload_all()
