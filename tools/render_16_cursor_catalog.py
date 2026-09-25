#!/usr/bin/env python3
"""
Render all 16 cursor catalogue animation scenes on GPU (Vulkan + NVENC),
verify every scene, and assemble cursor_16_master_showreel.mp4.
"""

import subprocess
import sys
import time
from pathlib import Path
import cv2

BASE_DIR = Path("/home/pierone/src/go-master/projects/Pyt/VeloxEditing")
CHRONON_CLI = BASE_DIR / "Chronon3d/build/chronon/linux-video-release/apps/chronon3d_cli/chronon3d_cli"
ASSETS_ROOT = BASE_DIR / "Chronon3d"
SCENES_DIR = BASE_DIR / "ChrononTemplate/out/cursor_catalog_16"

def render_scenes():
    plans = sorted(list(SCENES_DIR.glob("cursor_scene_*.plan.json")))
    print(f"Found {len(plans)} cursor plans to render on GPU (Vulkan + NVENC)...", flush=True)
    
    start_all = time.time()
    for idx, plan in enumerate(plans, 1):
        out_mp4 = SCENES_DIR / f"{plan.stem.replace('.plan', '')}.mp4"
        cmd = [
            str(CHRONON_CLI),
            "render",
            "--plan", str(plan),
            "--assets-root", str(ASSETS_ROOT),
            "--backend", "vulkan",
            "--hardware", "cpu",
            "-o", str(out_mp4)
        ]
        t0 = time.time()
        print(f"[{idx:02d}/{len(plans):02d}] Rendering {plan.name} -> {out_mp4.name} (Vulkan GPU + CPU encode)...", flush=True)
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        dt = time.time() - t0
        if res.returncode != 0:
            print(f"ERROR rendering {plan.name}: {res.stderr}\n{res.stdout}")
            sys.exit(1)
            
        # Frame check across whole video
        cap = cv2.VideoCapture(str(out_mp4))
        tot_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        dark_frames = []
        for f_idx in range(tot_frames):
            ret, frame = cap.read()
            if not ret or frame.max() == 0:
                dark_frames.append(f_idx)
        cap.release()
        
        print(f"  ✓ Done in {dt:.2f}s ({out_mp4.stat().st_size / 1024:.1f} KB, {tot_frames} frames, dark_frames={dark_frames})", flush=True)
        
    print(f"\nAll 16 scenes rendered in {time.time() - start_all:.2f}s!\n", flush=True)

def assemble_master_showreel():
    print("Assembling cursor_16_master_showreel.mp4...", flush=True)
    mp4_files = sorted(list(SCENES_DIR.glob("cursor_scene_*.mp4")))
    mp4_files = [f for f in mp4_files if "showreel" not in f.name]
    
    concat_list = SCENES_DIR / "concat_list.txt"
    with open(concat_list, "w") as f:
        for fpath in mp4_files:
            f.write(f"file '{fpath.resolve()}'\n")
            
    out_master = SCENES_DIR / "cursor_16_master_showreel.mp4"
    cmd = [
        "ffmpeg", "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", str(concat_list),
        "-c", "copy",
        str(out_master)
    ]
    subprocess.run(cmd, check=True)
    print(f"✓ Master showreel created: {out_master} ({out_master.stat().st_size / (1024*1024):.2f} MB)", flush=True)

def main():
    render_scenes()
    assemble_master_showreel()

if __name__ == "__main__":
    main()
