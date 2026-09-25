#!/usr/bin/env python3
"""
Render all 12 cursor scenes using Vulkan + NVENC GPU pipeline,
then assemble cursor_master_showreel.mp4.
"""

import subprocess
import sys
import time
from pathlib import Path

BASE_DIR = Path("/home/pierone/src/go-master/projects/Pyt/VeloxEditing")
CHRONON_CLI = BASE_DIR / "Chronon3d/build/chronon/linux-video-release/apps/chronon3d_cli/chronon3d_cli"
ASSETS_ROOT = BASE_DIR / "Chronon3d"
SCENES_DIR = BASE_DIR / "ChrononTemplate/out/cursor_animations"

def render_scenes():
    plans = sorted(list(SCENES_DIR.glob("cursor_scene_*.plan.json")))
    print(f"Found {len(plans)} cursor plans to render on GPU...")
    
    start_all = time.time()
    for idx, plan in enumerate(plans, 1):
        out_mp4 = SCENES_DIR / f"{plan.stem.replace('.plan', '')}.mp4"
        cmd = [
            str(CHRONON_CLI),
            "render",
            "--plan", str(plan),
            "--assets-root", str(ASSETS_ROOT),
            "--backend", "vulkan",
            "--hardware", "nvenc",
            "-o", str(out_mp4)
        ]
        t0 = time.time()
        print(f"[{idx}/{len(plans)}] Rendering {plan.name} -> {out_mp4.name}...", flush=True)
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        dt = time.time() - t0
        if res.returncode != 0:
            print(f"ERROR rendering {plan.name}: {res.stderr}\n{res.stdout}")
            sys.exit(1)
        print(f"  ✓ Done in {dt:.2f}s ({out_mp4.stat().st_size} bytes)")
        
    print(f"\nAll scenes rendered in {time.time() - start_all:.2f}s!")

def assemble_master_showreel():
    print("\nAssembling cursor_master_showreel.mp4...")
    mp4_files = sorted(list(SCENES_DIR.glob("cursor_scene_*.mp4")))
    # Exclude showreel itself if it exists
    mp4_files = [f for f in mp4_files if "showreel" not in f.name]
    
    concat_list = SCENES_DIR / "concat_list.txt"
    with open(concat_list, "w") as f:
        for fpath in mp4_files:
            f.write(f"file '{fpath.resolve()}'\n")
            
    out_master = SCENES_DIR / "cursor_master_showreel.mp4"
    cmd = [
        "ffmpeg", "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", str(concat_list),
        "-c", "copy",
        str(out_master)
    ]
    subprocess.run(cmd, check=True)
    print(f"✓ Master showreel created: {out_master} ({out_master.stat().st_size} bytes)")

def main():
    render_scenes()
    assemble_master_showreel()

if __name__ == "__main__":
    main()
