#!/usr/bin/env python3
"""
Upload the newly rendered clip MP4s and preview PNG frames to the user-specified Google Drive folder.
"""

import os
import sys
import json
import urllib.request
import urllib.parse
from pathlib import Path

BASE_DIR = Path("/home/pierone/src/go-master/projects/Pyt/VeloxEditing")
OUT_DIR = BASE_DIR / "out" / "runtime_clips"
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

def upload_files():
    token = refresh_drive_token()
    boundary = "----Chronon3DClipUpload"
    
    # Files to upload: MP4s and PNGs
    mp4_files = sorted(list(OUT_DIR.glob("*.mp4")))
    png_files = sorted(list(OUT_DIR.glob("*.png")))
    all_files = mp4_files + png_files
    
    print(f"Found {len(all_files)} files to upload to Google Drive folder {FOLDER_ID}...")
    links = {}
    
    for idx, fpath in enumerate(all_files, 1):
        fname = fpath.name
        mime_type = "video/mp4" if fpath.suffix == ".mp4" else "image/png"
        print(f"[{idx}/{len(all_files)}] Uploading {fname} ({fpath.stat().st_size} bytes)...", flush=True)
        
        with open(fpath, "rb") as f:
            file_bytes = f.read()
            
        meta = json.dumps({"name": fname, "parents": [FOLDER_ID]})
        body = (
            f"--{boundary}\r\nContent-Type: application/json; charset=UTF-8\r\n\r\n{meta}\r\n"
            f"--{boundary}\r\nContent-Type: {mime_type}\r\n\r\n"
        ).encode() + file_bytes + f"\r\n--{boundary}--\r\n".encode()
        
        req = urllib.request.Request(
            "https://www.googleapis.com/upload/drive/v3/files?uploadType=multipart&fields=id,name",
            data=body,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": f"multipart/related; boundary={boundary}"
            },
            method="POST"
        )
        
        for attempt in range(3):
            try:
                with urllib.request.urlopen(req, timeout=120) as resp:
                    res = json.load(resp)
                    fid = res["id"]
                    link = f"https://drive.google.com/file/d/{fid}/view?usp=drivesdk"
                    links[fname] = link
                    print(f"  -> Uploaded! {link}", flush=True)
                    
                    # Set permissions (anyone with link can view)
                    try:
                        perm_req = urllib.request.Request(
                            f"https://www.googleapis.com/drive/v3/files/{fid}/permissions",
                            data=json.dumps({"role": "reader", "type": "anyone"}).encode(),
                            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
                            method="POST"
                        )
                        with urllib.request.urlopen(perm_req): pass
                    except: pass
                    break
            except Exception as e:
                print(f"  Retry {attempt+1} on error: {e}", flush=True)
                if attempt == 2:
                    print(f"Failed to upload {fname} after 3 attempts.")
                    
    print("\n=== GOOGLE DRIVE LINKS ===")
    for fname, link in links.items():
        print(f"{fname}: {link}")
    
    # Save links to a json file
    links_file = OUT_DIR / "drive_links.json"
    with open(links_file, "w") as f:
        json.dump(links, f, indent=2)
    print(f"\nSaved links to {links_file}")

if __name__ == "__main__":
    upload_files()
