import os
import json
import subprocess
import time

BASE_DIR = "/home/pierone/src/go-master/projects/Pyt/VeloxEditing"
CLI_PATH = os.path.join(BASE_DIR, "Chronon3d/build/chronon/linux-video-fast-dev/apps/chronon3d_cli/chronon3d_cli")
OUT_DIR = os.path.join(BASE_DIR, "ChrononTemplate/out/modern_entities_with_text")
PLANS_DIR = os.path.join(OUT_DIR, "plans")
VIDEOS_DIR = os.path.join(OUT_DIR, "videos")
UPLOADER = os.path.join(BASE_DIR, "RenderingGen/bin/drive-upload")
CREDS = os.path.expanduser("~/.config/velox/credentials.json")
TOKEN = os.path.expanduser("~/.config/velox/token.json")
PARENT_FOLDER = "1Sc5gBaNCAsAkrfM-j9Ccm4kNwrKBBYuC"
SUBFOLDER = "Modern Entities With Text"

os.makedirs(PLANS_DIR, exist_ok=True)
os.makedirs(VIDEOS_DIR, exist_ok=True)

FONT_PATH = "ChrononTemplate/out/apple_spatial_entity_pack/assets/Montserrat-Bold.ttf"
PRISM_ASSET = "ChrononTemplate/out/modern_entities_with_text/assets/steve_jobs_monumental_prism_blur.png"
CARD_ASSET = "ChrononTemplate/out/modern_entities_with_text/assets/jobs_white_bg_card.png"

def make_title_layers():
    """Text enters big & sharp at frame 0..20, then when image card punches in (frame 22..55),
    the text scales down and gets Gaussian depth blurred (depth of field rack focus) to give
    a deep spatial separation and distance behind the foreground image card."""
    return [
        {
            "id": "pure_white_bg",
            "type": "color",
            "color": [1.0, 1.0, 1.0, 1.0],
            "start_frame": 0,
            "duration_frames": 90
        },
        {
            "id": "text_prism_blur",
            "type": "image",
            "asset": PRISM_ASSET,
            "size": [1920.0, 1080.0],
            "opacity": 0.85,
            "start_frame": 0,
            "duration_frames": 90,
            "animation": {
                "tracks": [
                    {"property": "opacity", "easing": "out_cubic", "keyframes": [
                        {"frame": 0, "value": 0.0},
                        {"frame": 18, "value": 0.85},
                        {"frame": 35, "value": 0.55},
                        {"frame": 89, "value": 0.55}
                    ]},
                    {"property": "scale", "easing": "out_cubic", "keyframes": [
                        {"frame": 0, "value": 1.08},
                        {"frame": 22, "value": 1.0},
                        {"frame": 52, "value": 0.82},
                        {"frame": 89, "value": 0.82}
                    ]},
                    {"property": "blur", "easing": "out_cubic", "keyframes": [
                        {"frame": 0, "value": 0.0},
                        {"frame": 22, "value": 0.0},
                        {"frame": 52, "value": 12.0},
                        {"frame": 89, "value": 12.0}
                    ]}
                ]
            }
        },
        {
            "id": "title_text",
            "type": "text",
            "text": "STEVE JOBS",
            "size": [1600.0, 220.0],
            "position": [960.0, 155.0],
            "style": {
                "font": FONT_PATH,
                "font_size": 180.0,
                "fill": "#0A0B0E"
            },
            "start_frame": 0,
            "duration_frames": 90,
            "animation": {
                "tracks": [
                    {"property": "opacity", "easing": "out_cubic", "keyframes": [
                        {"frame": 0, "value": 0.0},
                        {"frame": 18, "value": 1.0},
                        {"frame": 89, "value": 0.90}
                    ]},
                    {"property": "position_y", "easing": "out_cubic", "keyframes": [
                        {"frame": 0, "value": 30.0},
                        {"frame": 22, "value": 0.0},
                        {"frame": 52, "value": -25.0},
                        {"frame": 89, "value": -25.0}
                    ]},
                    {"property": "scale", "easing": "out_cubic", "keyframes": [
                        {"frame": 0, "value": 1.08},
                        {"frame": 22, "value": 1.0},
                        {"frame": 52, "value": 0.82},
                        {"frame": 89, "value": 0.82}
                    ]},
                    {"property": "blur", "easing": "out_cubic", "keyframes": [
                        {"frame": 0, "value": 0.0},
                        {"frame": 22, "value": 0.0},
                        {"frame": 52, "value": 14.0},
                        {"frame": 89, "value": 14.0}
                    ]}
                ]
            }
        }
    ]

# Archetype 1: 3D Pitch Rise & Settle (Rise up with pitch tilt straightening)
card_tracks_01 = [
    {"property": "opacity", "easing": "out_cubic", "keyframes": [{"frame": 0, "value": 0.0}, {"frame": 22, "value": 0.0}, {"frame": 38, "value": 1.0}, {"frame": 89, "value": 1.0}]},
    {"property": "position_y", "easing": "out_cubic", "keyframes": [{"frame": 0, "value": 360.0}, {"frame": 22, "value": 360.0}, {"frame": 56, "value": 0.0}, {"frame": 75, "value": -6.0}, {"frame": 89, "value": 0.0}]},
    {"property": "rotation_x", "easing": "out_cubic", "keyframes": [{"frame": 0, "value": -18.0}, {"frame": 22, "value": -18.0}, {"frame": 56, "value": 0.0}, {"frame": 89, "value": 0.0}]},
    {"property": "scale", "easing": "out_cubic", "keyframes": [{"frame": 0, "value": 0.90}, {"frame": 22, "value": 0.90}, {"frame": 56, "value": 1.0}, {"frame": 89, "value": 1.015}]}
]

# Archetype 2: 3D Depth Punch Forward (Punch forward from deep Z-space)
card_tracks_02 = [
    {"property": "opacity", "easing": "out_cubic", "keyframes": [{"frame": 0, "value": 0.0}, {"frame": 22, "value": 0.0}, {"frame": 36, "value": 1.0}, {"frame": 89, "value": 1.0}]},
    {"property": "position_z", "easing": "out_cubic", "keyframes": [{"frame": 0, "value": 500.0}, {"frame": 22, "value": 500.0}, {"frame": 55, "value": 0.0}, {"frame": 75, "value": -18.0}, {"frame": 89, "value": 0.0}]},
    {"property": "scale", "easing": "out_cubic", "keyframes": [{"frame": 0, "value": 0.55}, {"frame": 22, "value": 0.55}, {"frame": 55, "value": 1.0}, {"frame": 75, "value": 1.02}, {"frame": 89, "value": 1.01}]}
]

# Archetype 3: 2.5D Isometric Float & Yaw Tilt (Angled lateral rise with 3D yaw and roll)
card_tracks_03 = [
    {"property": "opacity", "easing": "out_cubic", "keyframes": [{"frame": 0, "value": 0.0}, {"frame": 22, "value": 0.0}, {"frame": 38, "value": 1.0}, {"frame": 89, "value": 1.0}]},
    {"property": "position_y", "easing": "out_cubic", "keyframes": [{"frame": 0, "value": 280.0}, {"frame": 22, "value": 280.0}, {"frame": 56, "value": 0.0}, {"frame": 75, "value": -5.0}, {"frame": 89, "value": 0.0}]},
    {"property": "position_x", "easing": "out_cubic", "keyframes": [{"frame": 0, "value": -60.0}, {"frame": 22, "value": -60.0}, {"frame": 56, "value": 0.0}, {"frame": 75, "value": 1.0}, {"frame": 89, "value": 0.0}]},
    {"property": "rotation_y", "easing": "out_cubic", "keyframes": [{"frame": 0, "value": 22.0}, {"frame": 22, "value": 22.0}, {"frame": 56, "value": 0.0}, {"frame": 75, "value": -2.0}, {"frame": 89, "value": 0.0}]},
    {"property": "rotation_z", "easing": "out_cubic", "keyframes": [{"frame": 0, "value": -3.5}, {"frame": 22, "value": -3.5}, {"frame": 56, "value": 0.0}, {"frame": 75, "value": 0.5}, {"frame": 89, "value": 0.0}]},
    {"property": "scale", "easing": "out_cubic", "keyframes": [{"frame": 0, "value": 0.88}, {"frame": 22, "value": 0.88}, {"frame": 56, "value": 1.0}, {"frame": 89, "value": 1.015}]}
]

# Archetype 4: 2.5D Elastic Pop & Overshoot (Snappy dynamic bounce and settle)
card_tracks_04 = [
    {"property": "opacity", "easing": "out_cubic", "keyframes": [{"frame": 0, "value": 0.0}, {"frame": 22, "value": 0.0}, {"frame": 34, "value": 1.0}, {"frame": 89, "value": 1.0}]},
    {"property": "scale", "easing": "out_cubic", "keyframes": [{"frame": 0, "value": 0.65}, {"frame": 22, "value": 0.65}, {"frame": 50, "value": 1.05}, {"frame": 68, "value": 0.985}, {"frame": 82, "value": 1.008}, {"frame": 89, "value": 1.01}]},
    {"property": "position_y", "easing": "out_cubic", "keyframes": [{"frame": 0, "value": 200.0}, {"frame": 22, "value": 200.0}, {"frame": 50, "value": -14.0}, {"frame": 68, "value": 4.0}, {"frame": 89, "value": 0.0}]}
]

# Archetype 5: Cinematic Spatial Dolly Push (Smooth 3D push in and subtle yaw glide)
card_tracks_05 = [
    {"property": "opacity", "easing": "out_cubic", "keyframes": [{"frame": 0, "value": 0.0}, {"frame": 22, "value": 0.0}, {"frame": 38, "value": 1.0}, {"frame": 89, "value": 1.0}]},
    {"property": "position_x", "easing": "out_cubic", "keyframes": [{"frame": 0, "value": 120.0}, {"frame": 22, "value": 120.0}, {"frame": 58, "value": 0.0}, {"frame": 75, "value": -3.0}, {"frame": 89, "value": 0.0}]},
    {"property": "position_y", "easing": "out_cubic", "keyframes": [{"frame": 0, "value": 180.0}, {"frame": 22, "value": 180.0}, {"frame": 58, "value": 0.0}, {"frame": 75, "value": -2.0}, {"frame": 89, "value": 0.0}]},
    {"property": "rotation_y", "easing": "out_cubic", "keyframes": [{"frame": 0, "value": -18.0}, {"frame": 22, "value": -18.0}, {"frame": 58, "value": 0.0}, {"frame": 89, "value": 0.0}]},
    {"property": "scale", "easing": "out_cubic", "keyframes": [{"frame": 0, "value": 0.86}, {"frame": 22, "value": 0.86}, {"frame": 58, "value": 1.0}, {"frame": 89, "value": 1.018}]}
]

presets = [
    ("modern_entity_06_editorial_filmstrip_jobs", card_tracks_01, "3D Pitch Rise & Settle (Updated Standard)"),
    ("modern_entity_06b_steve_jobs_3d_depth_punch", card_tracks_02, "3D Depth Punch Forward from Z-space"),
    ("modern_entity_06c_steve_jobs_25d_isometric_float", card_tracks_03, "2.5D Isometric Float & Yaw Tilt"),
    ("modern_entity_06d_steve_jobs_25d_elastic_overshoot", card_tracks_04, "2.5D Elastic Pop & Snappy Overshoot"),
    ("modern_entity_06e_steve_jobs_cinematic_spatial_push", card_tracks_05, "Cinematic Spatial Dolly Push & Angle")
]

def generate_and_render_all():
    results = []
    for job_id, tracks, desc in presets:
        print(f"\n==========================================")
        print(f"Building & Rendering: {job_id}")
        print(f"Description: {desc}")
        print(f"==========================================")
        
        layers = make_title_layers()
        hero_layer = {
            "id": "jobs_rounded_image",
            "type": "image",
            "asset": CARD_ASSET,
            "position": [960.0, 640.0],
            "size": [1160.0, 690.0],
            "fit": "contain",
            "enable_3d": True,
            "start_frame": 0,
            "duration_frames": 90,
            "animation": {"tracks": tracks}
        }
        layers.append(hero_layer)
        
        plan = {
            "schema": "chronon.render-plan.v2",
            "version": 2,
            "job_id": job_id,
            "canvas": {"width": 1920, "height": 1080, "fps_num": 30, "fps_den": 1, "duration_frames": 90},
            "layers": layers,
            "camera": {
                "type": "perspective",
                "position": [960.0, 540.0, -1400.0],
                "rotation_deg": [0.0, 0.0, 0.0],
                "fov_deg": 55.0,
                "near": 1.0,
                "far": 5000.0,
                "zoom": 1.0
            },
            "output": {
                "path": os.path.join(VIDEOS_DIR, f"{job_id}.mp4"),
                "format": "mp4",
                "codec": "h264"
            }
        }
        
        plan_path = os.path.join(PLANS_DIR, f"{job_id}.plan.json")
        with open(plan_path, "w") as f:
            json.dump(plan, f, indent=2)
        print(f"Saved plan: {plan_path}")
        
        # Render with chronon3d_cli
        cmd_render = [
            CLI_PATH, "render",
            "--plan", plan_path,
            "--assets-root", BASE_DIR
        ]
        t0 = time.time()
        print("Rendering on GPU...")
        res = subprocess.run(cmd_render, capture_output=True, text=True)
        if res.returncode != 0:
            print(f"ERROR rendering {job_id}: {res.stderr}")
            continue
        print(f"Rendered in {time.time() - t0:.1f}s")
        
        # Create preview frame at frame 60 (2.0s)
        video_path = os.path.join(VIDEOS_DIR, f"{job_id}.mp4")
        preview_path = os.path.join(VIDEOS_DIR, f"{job_id}_preview.jpg")
        cmd_prev = [
            "ffmpeg", "-y", "-ss", "00:00:02.000", "-i", video_path,
            "-vframes", "1", "-q:v", "2", preview_path
        ]
        subprocess.run(cmd_prev, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        print(f"Created preview: {preview_path}")
        
        # Upload video to Google Drive
        print(f"Uploading {job_id}.mp4 to Google Drive...")
        cmd_upload = [
            UPLOADER,
            "-credentials", CREDS,
            "-token", TOKEN,
            "-folder", PARENT_FOLDER,
            "-subfolder", SUBFOLDER,
            "-file", video_path,
            "-name", f"{job_id}.mp4"
        ]
        up_res = subprocess.run(cmd_upload, capture_output=True, text=True)
        print(up_res.stdout.strip())
        
        link = ""
        for token in up_res.stdout.split():
            if token.startswith("link="):
                link = token.split("link=")[1]
                
        # Also upload preview image
        cmd_upload_prev = [
            UPLOADER,
            "-credentials", CREDS,
            "-token", TOKEN,
            "-folder", PARENT_FOLDER,
            "-subfolder", SUBFOLDER,
            "-file", preview_path,
            "-name", f"{job_id}_preview.jpg"
        ]
        up_prev_res = subprocess.run(cmd_upload_prev, capture_output=True, text=True)
        prev_link = ""
        for token in up_prev_res.stdout.split():
            if token.startswith("link="):
                prev_link = token.split("link=")[1]
                
        results.append({
            "id": job_id,
            "desc": desc,
            "video_link": link,
            "preview_link": prev_link
        })
        
    print("\n================ ALL JOBS COMPLETED! ================")
    print(json.dumps(results, indent=2))
    with open(os.path.join(VIDEOS_DIR, "proiezioni_steve_jobs_summary.json"), "w") as f:
        json.dump(results, f, indent=2)

if __name__ == "__main__":
    generate_and_render_all()
