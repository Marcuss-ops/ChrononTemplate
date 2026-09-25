#!/usr/bin/env python3
"""
High-speed GPU runner to render all 30 kinetic Envato replica scenes and concatenate into master showreel.
Uses:
- Vulkan hardware rasterizer + native NVENC hardware video encoder (>120 FPS).
- Automatic token refresh and sequential upload to Google Drive folder 1ATL0bnJXijNqFlKkgWye3PEAdAuQa1HI.
"""

import os
import sys
import subprocess
import json
import time
import urllib.request
import urllib.parse
from pathlib import Path

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

def render_scenes():
    scenes = [f"envato_scene_{i:02d}" for i in range(1, 31)]
    rendered = []
    
    print("\n=======================================================", flush=True)
    print("🚀 LAUNCHING VULKAN GPU + NVENC BATCH RENDERING (30 SCENES)", flush=True)
    print("=======================================================\n", flush=True)
    
    start_all = time.time()
    for idx, sc in enumerate(scenes, 1):
        plan_file = OUT_DIR / f"{sc}.plan.json"
        mp4_file = OUT_DIR / f"{sc}.mp4"
        
        t0 = time.time()
        print(f"[{idx:02d}/30] Rendering {sc} via GPU Vulkan + NVENC...", end=" ", flush=True)
        
        gpu_cmd = [
            str(CLI_BIN), "render",
            "--plan", str(plan_file),
            "--backend", "vulkan",
            "--hardware", "nvenc",
            "--assets-root", str(CHRONON_DIR),
            "-o", str(mp4_file)
        ]
        
        res = subprocess.run(gpu_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if res.returncode != 0:
            tail = res.stderr.decode(errors='ignore')[-500:] if res.stderr else ""
            print(f"\n  [WARN] GPU Vulkan failed ({tail.strip()}), falling back to software CPU...", flush=True)
            cpu_cmd = [
                str(CLI_BIN), "render",
                "--plan", str(plan_file),
                "--backend", "software",
                "--hardware", "nvenc",
                "--assets-root", str(CHRONON_DIR),
                "-o", str(mp4_file)
            ]
            res2 = subprocess.run(cpu_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            if res2.returncode != 0:
                print(f"FAILED {sc}: {res2.stderr.decode(errors='ignore')[-300:]}", flush=True)
                continue
                
        dur_s = time.time() - t0
        sz_kb = mp4_file.stat().st_size / 1024.0 if mp4_file.exists() else 0
        print(f"DONE in {dur_s:.2f}s ({sz_kb:.1f} KB)", flush=True)
        rendered.append(mp4_file)
        
    total_render_time = time.time() - start_all
    print(f"\nAll {len(rendered)} scenes rendered in {total_render_time:.2f}s! (~{total_render_time/len(rendered):.2f}s per video)", flush=True)
    
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
    print(f"Master showreel ready! Size: {master_file.stat().st_size / 1024:.1f} KB\n", flush=True)

    # Upload all files one by one to Google Drive
    print(f"Starting sequential upload to Google Drive folder: {FOLDER_ID} ...", flush=True)
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import upload_envato_replica
    upload_envato_replica.upload_all()

if __name__ == "__main__":
    render_scenes()
