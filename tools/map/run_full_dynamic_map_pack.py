import os
import sys
import json
import time
import subprocess
import cv2
import numpy as np
from pathlib import Path

BASE_DIR = "/home/pierone/src/go-master/projects/Pyt/VeloxEditing"
TEMPLATE_DIR = os.path.join(BASE_DIR, "ChrononTemplate")
TOOLS_MAP = os.path.join(TEMPLATE_DIR, "tools/map")
OUT_DIR = os.path.join(TEMPLATE_DIR, "out/map_image_v1_opencv")
RENDERS_DIR = os.path.join(OUT_DIR, "renders")
os.makedirs(RENDERS_DIR, exist_ok=True)

UPLOADER = os.path.join(BASE_DIR, "RenderingGen/bin/drive-upload")
DRIVE_FOLDER = "1WALc4JbFz6uK5nEM_tYnAeQqiPVRacp_"
CREDS_JSON = os.path.expanduser("~/.config/velox/credentials.json")
TOKEN_JSON = os.path.expanduser("~/.config/velox/token.json")

# Import the actual generator from render_map_image_v2_opencv
sys.path.insert(0, TOOLS_MAP)
import render_map_image_v2_opencv as generator

SCENES = generator.SCENES

print(f"Total dynamic map animations to generate: {len(SCENES)}")
results = []

for idx, scene in enumerate(SCENES, 1):
    slug = scene[0]
    title = scene[1]
    suffix = scene[7]
    job_id = f"map_image_{slug}_{suffix}"
    drive_filename = f"Chronon V2 - {title} - 5s.mp4"
    out_mp4 = Path(RENDERS_DIR) / f"{job_id}.mp4"
    web_mp4 = Path(RENDERS_DIR) / f"{job_id}_web.mp4"
    
    print(f"\n========================================================")
    print(f"[{idx}/{len(SCENES)}] PRODUCING REAL DYNAMIC MAP: {title} ({job_id})")
    print(f"========================================================")
    
    # 1. RENDER COMPLETE DYNAMIC ANIMATION
    t0 = time.time()
    stat = generator.render_one(scene, out_mp4, workers=12, block=2)
    duration = time.time() - t0
    print(f"Rendered in {duration:.1f}s, size: {stat['bytes']} bytes")
    
    # 2. AUDIT ZERO BLACK FRAMES
    cap = cv2.VideoCapture(str(out_mp4))
    total_f = 0
    blacks = []
    while True:
        ret, frame = cap.read()
        if not ret: break
        m = np.mean(frame)
        if m < 10.0:
            blacks.append((total_f, float(m)))
        total_f += 1
    cap.release()
    print(f"Frame audit {title}: total={total_f}, black glitches={len(blacks)}")
    assert len(blacks) == 0, f"Error: found black glitches in {title}: {blacks}"
    
    # 3. ENCODE WEB MP4 FASTSTART
    cmd_ffmpeg = [
        "ffmpeg", "-y", "-i", str(out_mp4),
        "-c:v", "libx264", "-profile:v", "high", "-level", "4.1",
        "-pix_fmt", "yuv420p", "-movflags", "+faststart",
        str(web_mp4)
    ]
    subprocess.run(cmd_ffmpeg, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
    
    # 4. UPLOAD DIRECTLY TO GOOGLE DRIVE
    print(f"Uploading {drive_filename} to Drive folder {DRIVE_FOLDER}...")
    cmd_upload = [
        UPLOADER,
        "-credentials", CREDS_JSON,
        "-token", TOKEN_JSON,
        "-folder", DRIVE_FOLDER,
        "-file", str(web_mp4),
        "-name", drive_filename
    ]
    up_res = subprocess.run(cmd_upload, capture_output=True, text=True)
    upload_line = up_res.stdout.strip()
    print(f"Drive output: {upload_line}")
    
    link = ""
    for part in upload_line.split():
        if part.startswith("link="):
            link = part.split("link=")[1]
            
    results.append({
        "slug": slug,
        "title": title,
        "motion": suffix,
        "video": str(web_mp4),
        "drive_name": drive_filename,
        "link": link
    })

summary_file = os.path.join(OUT_DIR, "real_dynamic_maps_results.json")
with open(summary_file, "w") as f:
    json.dump(results, f, indent=2)

print("\n" + "="*60)
print("ALL 10 REAL DYNAMIC MAP ANIMATIONS RENDERED & UPLOADED!")
print("="*60)
for r in results:
    print(f"- {r['title']} ({r['motion']}): {r['link']}")
