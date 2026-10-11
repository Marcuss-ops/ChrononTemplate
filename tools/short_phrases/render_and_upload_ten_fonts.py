#!/usr/bin/env python3
import json
import os
import subprocess
import sys
import time

FONTS = [
    ("01_sf_pro_bold", "assets/fonts/SF-Pro-Display-Bold.otf", "SF Pro Display Bold"),
    ("02_plus_jakarta_sans", "assets/fonts/Plus-Jakarta-Sans.ttf", "Plus Jakarta Sans"),
    ("03_inter_bold", "assets/fonts/Inter-Bold.ttf", "Inter Bold"),
    ("04_space_grotesk", "assets/fonts/Space-Grotesk.ttf", "Space Grotesk"),
    ("05_urbanist", "assets/fonts/Urbanist.ttf", "Urbanist"),
    ("06_outfit", "assets/fonts/Outfit.ttf", "Outfit"),
    ("07_manrope", "assets/fonts/Manrope.ttf", "Manrope"),
    ("08_sora", "assets/fonts/Sora.ttf", "Sora"),
    ("09_montserrat_bold", "assets/fonts/Montserrat-Bold.ttf", "Montserrat Bold"),
    ("10_dm_sans", "assets/fonts/DMSans-Bold.ttf", "DM Sans Bold"),
]

ROOT_DIR = "/home/pierone/src/go-master/projects/Pyt/VeloxEditing"
CHRONON_TEMPLATE_DIR = os.path.join(ROOT_DIR, "ChrononTemplate")
CHRONON3D_DIR = os.path.join(ROOT_DIR, "Chronon3d")
OUT_DIR = os.path.join(CHRONON_TEMPLATE_DIR, "out", "ten_fonts_showcase_living")
CLI_PATH = os.path.join(CHRONON3D_DIR, "build/chronon/linux-video-fast-dev/apps/chronon3d_cli/chronon3d_cli")
UPLOADER_PATH = os.path.join(ROOT_DIR, "RenderingGen/bin/drive-upload")
CREDS_PATH = os.path.join(ROOT_DIR, "RenderingGen/UploadDrive/credentials.json")
TOKEN_PATH = os.path.join(ROOT_DIR, "RenderingGen/UploadDrive/token.json")
DRIVE_FOLDER = "1Jln16q_OoGM208-PjZHZXyMzuMpBOua4"

def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    template_plan_path = os.path.join(OUT_DIR, "01_sf_pro_bold.plan.json")
    if not os.path.exists(template_plan_path):
        print(f"Template plan not found: {template_plan_path}")
        sys.exit(1)

    with open(template_plan_path, "r", encoding="utf-8") as f:
        base_plan = json.load(f)

    # Ensure background layer points to living documentary paper background
    base_plan["layers"][0] = {
        "id": "background",
        "type": "video",
        "source": "assets/images/documentary_paper_alive.mp4",
        "size": [1920, 1080],
        "fit": "cover",
        "position": [0, 0],
        "start_frame": 0,
        "duration_frames": 210
    }

    uploaded_results = []

    for idx, (key, font_asset, label) in enumerate(FONTS, 1):
        print(f"\n=======================================================")
        print(f"[{idx}/{len(FONTS)}] Processing: {label} ({key})")
        print(f"=======================================================")

        # 1. Generate plan
        plan = json.loads(json.dumps(base_plan))
        plan["job_id"] = f"living_paper_{key}"
        # Update font on layers 1 (ambient shadow), 2 (contact shadow), 3 (phrase text)
        for layer_idx in [1, 2, 3]:
            plan["layers"][layer_idx]["style"]["font"] = font_asset

        plan_path = os.path.join(OUT_DIR, f"{key}.plan.json")
        with open(plan_path, "w", encoding="utf-8") as f:
            json.dump(plan, f, indent=2)

        mp4_path = os.path.join(OUT_DIR, f"{key}_living.mp4")

        # 2. Render with CRF 26 to guarantee lightweight files (~1.7 MB - 2.5 MB)
        cmd_render = [
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
        print(f"Rendering {mp4_path}...")
        render_res = subprocess.run(cmd_render, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        render_time = time.time() - t0

        if render_res.returncode != 0:
            print(f"ERROR rendering {key}: exit {render_res.returncode}")
            print(render_res.stdout[-1000:])
            sys.exit(1)

        file_size_bytes = os.path.getsize(mp4_path)
        file_size_mb = file_size_bytes / (1024 * 1024)
        print(f"Rendered in {render_time:.1f}s - File size: {file_size_mb:.2f} MB ({file_size_bytes} bytes)")

        # 3. Upload to Google Drive
        print(f"Uploading {key}_living.mp4 to Google Drive folder {DRIVE_FOLDER}...")
        upload_cmd = [
            UPLOADER_PATH,
            "-credentials", CREDS_PATH,
            "-token", TOKEN_PATH,
            "-folder", DRIVE_FOLDER,
            "-name", f"{key}_living.mp4",
            "-file", mp4_path
        ]
        upload_res = subprocess.run(upload_cmd, capture_output=True, text=True)
        if upload_res.returncode != 0:
            print(f"ERROR uploading {key}: {upload_res.stderr}")
            sys.exit(1)

        drive_line = upload_res.stdout.strip()
        print(f"Upload success: {drive_line}")

        # Parse Drive link
        drive_link = ""
        for token in drive_line.split():
            if token.startswith("link="):
                drive_link = token.split("link=")[1]
                break

        uploaded_results.append({
            "key": key,
            "label": label,
            "font": font_asset,
            "size_mb": round(file_size_mb, 2),
            "link": drive_link,
            "raw": drive_line
        })

    print("\n\n=======================================================")
    print("ALL 10 FONTS RENDERED AND UPLOADED SUCCESSFULLY!")
    print("=======================================================")
    print(json.dumps(uploaded_results, indent=2))

    summary_file = os.path.join(OUT_DIR, "upload_summary.json")
    with open(summary_file, "w", encoding="utf-8") as f:
        json.dump(uploaded_results, f, indent=2)

if __name__ == "__main__":
    main()
