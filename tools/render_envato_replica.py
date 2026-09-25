#!/usr/bin/env python3
"""
Sequential runner to render all 30 Envato replica scenes and concatenate into master showreel.
All work happens inside ChrononTemplate/out/envato_scenes/.
"""

import os
import sys
import subprocess
import json
import urllib.request
import urllib.parse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

BASE_DIR = Path("/home/pierone/src/go-master/projects/Pyt/VeloxEditing")
CHRONON_DIR = BASE_DIR / "Chronon3d"
TEMPLATE_DIR = BASE_DIR / "ChrononTemplate"
OUT_DIR = TEMPLATE_DIR / "out" / "envato_scenes"
CLI_BIN = CHRONON_DIR / "build" / "chronon" / "linux-video-release" / "apps" / "chronon3d_cli" / "chronon3d_cli"
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

def render_scenes(force_gpu_rerender: bool = True):
    scenes = [f"envato_scene_{i:02d}" for i in range(1, 31)]
    rendered = []
    
    for idx, sc in enumerate(scenes, 1):
        plan_file = OUT_DIR / f"{sc}.plan.json"
        mp4_file = OUT_DIR / f"{sc}.mp4"
        
        # After RampUp GPU fix the binary is new (13:19) but old software MP4s
        # remain on disk (12:45-13:03). Force GPU re-render so the 30 are
        # native_mtsdf + NVENC instead of stale CPU artifacts.
        if not force_gpu_rerender and mp4_file.exists() and mp4_file.stat().st_size > 10000:
            print(f"[{idx}/30] Already rendered {sc}.mp4 ({mp4_file.stat().st_size} bytes)", flush=True)
            rendered.append(mp4_file)
            continue
            
        print(f"[{idx}/30] Rendering {sc} (GPU vulkan require_gpu_native → fallback software)...", flush=True)
        # Primary: Vulkan native text (MTSDF) + native NVENC. The RampUp
        # typewriter (02/10/11) is now lowerable after commit 07516f4e1, so
        # require_gpu_native succeeds for all 30 and keeps zero-readback.
        # Keep an explicit software fallback for the runner contract.
        gpu_cmd = [
            str(CLI_BIN), "render",
            "--plan", str(plan_file),
            "--backend", "vulkan",
            "--gpu-hot-path-mode", "require_gpu_native",
            "--assets-root", str(CHRONON_DIR),
            "--fps", "30",
            "-o", str(mp4_file)
        ]
        res = subprocess.run(gpu_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if res.returncode != 0:
            tail = res.stderr.decode(errors='ignore')[-800:] if res.stderr else ""
            print(f"  GPU lane failed for {sc} (rc={res.returncode}), falling back to software: {tail[-400:]}", flush=True)
            cpu_cmd = [
                str(CLI_BIN), "render",
                "--plan", str(plan_file),
                "--backend", "software",
                "--assets-root", str(CHRONON_DIR),
                "--fps", "30",
                "-o", str(mp4_file)
            ]
            res2 = subprocess.run(cpu_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            if res2.returncode != 0:
                print(f"ERROR rendering {sc} (software fallback also failed): {res2.stderr.decode(errors='ignore')[-600:]}", flush=True)
                continue
            print(f"  Software fallback succeeded for {sc}", flush=True)
        
        sz = mp4_file.stat().st_size if mp4_file.exists() else 0
        print(f"[{idx}/30] Finished {sc}.mp4 ({sz} bytes)", flush=True)
        rendered.append(mp4_file)
        
    # Build master showreel using ffmpeg concat
    concat_list_file = OUT_DIR / "concat_list.txt"
    with open(concat_list_file, "w") as f:
        for rf in rendered:
            f.write(f"file '{rf.resolve()}'\n")
            
    master_file = OUT_DIR / "envato_master_showreel.mp4"
    print(f"\nConcatenating {len(rendered)} scenes into {master_file.name}...", flush=True)
    concat_cmd = [
        "ffmpeg", "-y", "-f", "concat", "-safe", "0",
        "-i", str(concat_list_file),
        "-c", "copy",
        str(master_file)
    ]
    subprocess.run(concat_cmd, check=True)
    print(f"Master showreel generated! Size: {master_file.stat().st_size} bytes\n", flush=True)

    # Upload all files one by one to Google Drive
    print(f"Starting sequential upload to Google Drive folder: {FOLDER_ID} ...", flush=True)
    import upload_envato_replica
    upload_envato_replica.upload_all()

if __name__ == "__main__":
    render_scenes()

