#!/usr/bin/env python3
import json
import os
import subprocess
import sys
import time
from PIL import Image

VARIANTS = [
    ("01_helvetica_neue_bold", "assets/fonts/HelveticaNeue-Bold.otf", "Helvetica Neue Bold"),
    ("02_helvetica_neue_medium", "assets/fonts/HelveticaNeue-Medium.otf", "Helvetica Neue Medium"),
    ("03_arial_bold", "assets/fonts/Arial-Bold.ttf", "Arial Bold"),
]

ROOT_DIR = "/home/pierone/src/go-master/projects/Pyt/VeloxEditing"
CHRONON_TEMPLATE_DIR = os.path.join(ROOT_DIR, "ChrononTemplate")
CHRONON3D_DIR = os.path.join(ROOT_DIR, "Chronon3d")
OUT_DIR = os.path.join(CHRONON_TEMPLATE_DIR, "out", "paper_helvetica_comparison")
CLI_PATH = os.path.join(CHRONON3D_DIR, "build/chronon/linux-video-fast-dev/apps/chronon3d_cli/chronon3d_cli")
UPLOADER_PATH = os.path.join(ROOT_DIR, "RenderingGen/bin/drive-upload")
CREDS_PATH = os.path.join(ROOT_DIR, "RenderingGen/UploadDrive/credentials.json")
TOKEN_PATH = os.path.join(ROOT_DIR, "RenderingGen/UploadDrive/token.json")
DRIVE_FOLDER = "1Jln16q_OoGM208-PjZHZXyMzuMpBOua4"
BASE_PLAN_PATH = os.path.join(CHRONON_TEMPLATE_DIR, "out/short_phrase_plans/short_phrase_product_text_shimmer.plan.json")

def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    with open(BASE_PLAN_PATH, "r", encoding="utf-8") as f:
        base_plan = json.load(f)

    results = []

    for idx, (key, font_asset, label) in enumerate(VARIANTS, 1):
        print(f"\n=======================================================")
        print(f"[{idx}/{len(VARIANTS)}] Rendering {label} ({key})")
        print(f"=======================================================")

        plan = json.loads(json.dumps(base_plan))
        plan["job_id"] = f"paper_{key}"
        # Update fonts on shadow layers and main text
        for layer in plan["layers"]:
            if layer.get("type") == "text":
                layer["style"]["font"] = font_asset

        plan_path = os.path.join(OUT_DIR, f"{key}.plan.json")
        with open(plan_path, "w", encoding="utf-8") as f:
            json.dump(plan, f, indent=2)

        mp4_path = os.path.join(OUT_DIR, f"{key}.mp4")

        cmd = [
            CLI_PATH, "render",
            "--plan", plan_path,
            "--assets-root", CHRONON3D_DIR,
            "--backend", "vulkan",
            "--hardware", "nvenc",
            "--encoder-backend", "pipe",
            "--codec", "h264",
            "--fps", "30",
            "--rate-control", "crf",
            "--crf", "26",
            "-o", mp4_path
        ]

        t0 = time.time()
        print(f"Executing: {' '.join(cmd)}")
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        t_el = time.time() - t0

        if res.returncode != 0:
            print(f"FAILED {key}: exit {res.returncode}")
            print(res.stdout[-1000:])
            sys.exit(1)

        size_bytes = os.path.getsize(mp4_path)
        size_mb = size_bytes / (1024 * 1024)
        print(f"Rendered in {t_el:.1f}s - {size_mb:.2f} MB ({size_bytes} bytes)")

        # Extract frame 3.0s for visual preview crop
        frame_png = os.path.join(OUT_DIR, f"{key}_frame.png")
        crop_png = os.path.join(OUT_DIR, f"{key}_crop.png")
        subprocess.run(["ffmpeg", "-y", "-ss", "00:00:03.000", "-i", mp4_path, "-vframes", "1", frame_png],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if os.path.exists(frame_png):
            img = Image.open(frame_png)
            crop = img.crop((550, 420, 1370, 660))
            crop.save(crop_png)

        # Upload to Google Drive
        drive_name = f"{key}.mp4"
        print(f"Uploading {drive_name} to Google Drive ({DRIVE_FOLDER})...")
        upload_cmd = [
            UPLOADER_PATH,
            "-credentials", CREDS_PATH,
            "-token", TOKEN_PATH,
            "-folder", DRIVE_FOLDER,
            "-name", drive_name,
            "-file", mp4_path
        ]
        up_res = subprocess.run(upload_cmd, capture_output=True, text=True)
        if up_res.returncode != 0:
            print(f"ERROR uploading: {up_res.stderr}")
            sys.exit(1)

        drive_line = up_res.stdout.strip()
        print(f"Upload result: {drive_line}")
        drive_link = ""
        for token in drive_line.split():
            if token.startswith("link="):
                drive_link = token.split("link=")[1]
                break

        results.append({
            "key": key,
            "label": label,
            "font": font_asset,
            "size_mb": round(size_mb, 2),
            "link": drive_link,
            "crop_png": crop_png
        })

    summary_file = os.path.join(OUT_DIR, "summary.json")
    with open(summary_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    print("\n\nAll variants rendered and uploaded successfully!")
    print(json.dumps(results, indent=2))

if __name__ == "__main__":
    main()
