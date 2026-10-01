#!/usr/bin/env python3
"""
Chronon Premium Effects V1 Canary Showcase Suite
Generates, validates, renders, and uploads 1920x1080 5s (150 frames @ 30fps) overlays
demonstrating the canonical premium effect architecture:
1. overlay_01_document_highlight (BrushProfile / Trim animation / Multiply blend)
2. overlay_02_paper_fold (FoldWarp + CreaseShading 3D paper crease)
3. overlay_03_frosted_glass (BackdropFilter blur, refraction, rim light, chromatic dispersion)
4. overlay_04_retro_crt_terminal (LensDistortion + ChromaticAberration + Bloom + Noise)
5. overlay_05_cinematic_halation_flare (LuminanceResponse warm halation + anamorphic streak)
6. overlay_06_desert_heatwave (TurbulentDisplace vertical atmospheric shimmer)
7. overlay_07_velocity_rgb_split (ChromaticAberration velocity-dependent RGB split)

Target Google Drive Folder: 1ATL0bnJXijNqFlKkgWye3PEAdAuQa1HI
"""

import os
import sys
import json
import math
import time
import subprocess
import urllib.request
import urllib.parse
from pathlib import Path

BASE_DIR = Path("/home/pierone/src/go-master/projects/Pyt/VeloxEditing")
CHRONON_CLI = BASE_DIR / "Chronon3d/build/chronon/linux-video-fast-dev/apps/chronon3d_cli/chronon3d_cli"
ASSETS_ROOT = BASE_DIR / "Chronon3d"
OUT_DIR = BASE_DIR / "ChrononTemplate/out/premium_effects_v1"
TOKEN_PATH = BASE_DIR / "refactored/token.json"
CREDS_PATH = BASE_DIR / "refactored/credentials.json"
DRIVE_FOLDER_ID = "1ATL0bnJXijNqFlKkgWye3PEAdAuQa1HI"

OUT_DIR.mkdir(parents=True, exist_ok=True)

WIDTH = 1920
HEIGHT = 1080
FPS = 30
DURATION_FRAMES = 150  # 5.0 seconds

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

def upload_to_drive(token, file_path, folder_id):
    boundary = "-------314159265358979323846"
    fname = file_path.name
    metadata = {
        "name": fname,
        "parents": [folder_id]
    }
    meta_json = json.dumps(metadata)
    file_bytes = file_path.read_bytes()
    mime_type = "video/mp4" if fname.endswith(".mp4") else "image/png"
    
    body = (
        f"--{boundary}\r\n"
        f"Content-Type: application/json; charset=UTF-8\r\n\r\n"
        f"{meta_json}\r\n"
        f"--{boundary}\r\n"
        f"Content-Type: {mime_type}\r\n\r\n"
    ).encode("utf-8") + file_bytes + f"\r\n--{boundary}--\r\n".encode("utf-8")
    
    url = "https://www.googleapis.com/upload/drive/v3/files?uploadType=multipart&fields=id,name,webViewLink"
    req = urllib.request.Request(
        url,
        data=body,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": f"multipart/related; boundary={boundary}",
            "Content-Length": str(len(body))
        }
    )
    with urllib.request.urlopen(req) as resp:
        return json.load(resp)

# ─────────────────────────────────────────────────────────────────────────────
# 1. Overlay 01: Document Highlight (Highlighter + Scribble Underline)
# ─────────────────────────────────────────────────────────────────────────────
def build_overlay_01_document_highlight():
    marker_trim_keys = [
        {"frame": 0, "value": 0.0},
        {"frame": 40, "value": 1.0},
        {"frame": 150, "value": 1.0}
    ]
    underline_trim_keys = [
        {"frame": 0, "value": 0.0},
        {"frame": 45, "value": 0.0},
        {"frame": 85, "value": 1.0},
        {"frame": 150, "value": 1.0}
    ]

    return {
        "schema": "chronon.render-plan.v3",
        "version": 3,
        "job_id": "premium_01_document_highlight",
        "canvas": {"width": WIDTH, "height": HEIGHT, "fps_num": FPS, "fps_den": 1, "duration_frames": DURATION_FRAMES},
        "output": {"path": str(OUT_DIR / "overlay_01_document_highlight.mp4"), "format": "mp4", "codec": "h264"},
        "layers": [
            # Paper document background
            {
                "id": "paper_bg",
                "type": "shape",
                "size": [WIDTH, HEIGHT],
                "position": [960, 540],
                "start_frame": 0,
                "duration_frames": DURATION_FRAMES,
                "shape": {
                    "type": "rect",
                    "fill": [0.97, 0.98, 0.99, 1.0]
                }
            },
            # Document Card
            {
                "id": "doc_card",
                "type": "shape",
                "size": [1400, 700],
                "position": [960, 540],
                "start_frame": 0,
                "duration_frames": DURATION_FRAMES,
                "shape": {
                    "type": "rect",
                    "radius": 16.0,
                    "fill": [1.0, 1.0, 1.0, 1.0],
                    "stroke": {"color": "#E2E8F0", "width": 2.0}
                },
                "effects": [
                    {"type": "drop_shadow", "offset": [0.0, 18.0], "radius": 32.0, "color": [0.0, 0.0, 0.0, 0.08]}
                ]
            },
            # Subheading
            {
                "id": "doc_header",
                "type": "text",
                "text": "FINANCIAL AUDIT REPORT — Q3 PERFORMANCE",
                "size": [1200, 36],
                "position": [960, 380],
                "start_frame": 0,
                "duration_frames": DURATION_FRAMES,
                "style": {
                    "font": "assets/fonts/Inter-Bold.ttf",
                    "font_size": 18.0,
                    "fill": "#64748B"
                }
            },
            # Main canary text: "THE KEY NUMBER IS 42%"
            {
                "id": "doc_statement",
                "type": "text",
                "text": "THE KEY NUMBER IS 42%",
                "size": [1200, 110],
                "position": [960, 520],
                "start_frame": 0,
                "duration_frames": DURATION_FRAMES,
                "style": {
                    "font": "assets/fonts/Poppins-Bold.ttf",
                    "font_size": 68.0,
                    "fill": "#0F172A"
                }
            },
            # Yellow Marker Highlight over "42%" (Multiply blend mode)
            {
                "id": "marker_highlight",
                "type": "shape",
                "size": [280, 84],
                "position": [1330, 520],
                "start_frame": 0,
                "duration_frames": DURATION_FRAMES,
                "blend_mode": "multiply",
                "opacity": 0.85,
                "shape": {
                    "type": "path",
                    "path": [
                        {"type": "move_to", "point": [-130.0, 0.0]},
                        {"type": "line_to", "point": [130.0, 0.0]}
                    ],
                    "stroke": {
                        "color": "#FACC15",
                        "width": 64.0
                    },
                    "operators": [
                        {
                            "kind": "trim",
                            "params": {
                                "start": 0.0,
                                "end": 0.0,
                                "animation": {
                                    "easing": "in_out_quad",
                                    "keyframes": marker_trim_keys
                                }
                            }
                        }
                    ]
                }
            },
            # Red hand-drawn scribble underline under "KEY NUMBER"
            {
                "id": "scribble_underline",
                "type": "shape",
                "size": [480, 40],
                "position": [880, 580],
                "start_frame": 0,
                "duration_frames": DURATION_FRAMES,
                "shape": {
                    "type": "path",
                    "path": [
                        {"type": "move_to", "point": [-220.0, 0.0]},
                        {"type": "cubic_to", "control1": [-110.0, -8.0], "control2": [0.0, 8.0], "point": [110.0, -4.0]},
                        {"type": "cubic_to", "control1": [160.0, -10.0], "control2": [190.0, 4.0], "point": [220.0, 2.0]}
                    ],
                    "stroke": {
                        "color": "#EF4444",
                        "width": 6.0
                    },
                    "operators": [
                        {
                            "kind": "trim",
                            "params": {
                                "start": 0.0,
                                "end": 0.0,
                                "animation": {
                                    "easing": "in_out_quad",
                                    "keyframes": underline_trim_keys
                                }
                            }
                        }
                    ]
                }
            },
            # Badge note
            {
                "id": "doc_footer",
                "type": "text",
                "text": "Confirmed by Board of Directors • Statistical Confidence 99.8%",
                "size": [1200, 30],
                "position": [960, 680],
                "start_frame": 0,
                "duration_frames": DURATION_FRAMES,
                "style": {
                    "font": "assets/fonts/Inter-Regular.ttf",
                    "font_size": 15.0,
                    "fill": "#94A3B8"
                }
            }
        ]
    }

# ─────────────────────────────────────────────────────────────────────────────
# 2. Overlay 02: Paper Fold (FoldWarp + CreaseShading 3D Crease)
# ─────────────────────────────────────────────────────────────────────────────
def build_overlay_02_paper_fold():
    return {
        "schema": "chronon.render-plan.v3",
        "version": 3,
        "job_id": "premium_02_paper_fold",
        "canvas": {"width": WIDTH, "height": HEIGHT, "fps_num": FPS, "fps_den": 1, "duration_frames": DURATION_FRAMES},
        "output": {"path": str(OUT_DIR / "overlay_02_paper_fold.mp4"), "format": "mp4", "codec": "h264"},
        "layers": [
            # Studio dark neutral background
            {
                "id": "studio_bg",
                "type": "shape",
                "size": [WIDTH, HEIGHT],
                "position": [960, 540],
                "start_frame": 0,
                "duration_frames": DURATION_FRAMES,
                "shape": {
                    "type": "rect",
                    "fill": [0.05, 0.07, 0.10, 1.0]
                }
            },
            # Document Card with FoldWarp and CreaseShading
            {
                "id": "folded_document",
                "type": "shape",
                "size": [1200, 720],
                "position": [960, 540],
                "start_frame": 0,
                "duration_frames": DURATION_FRAMES,
                "shape": {
                    "type": "rect",
                    "radius": 12.0,
                    "fill": [0.98, 0.98, 0.98, 1.0],
                    "stroke": {"color": "#E7E5E4", "width": 1.5}
                },
                "effects": [
                    {
                        "type": "fold_warp",
                        "axis": "vertical",
                        "position": 0.5,
                        "amount": 0.35,
                        "radius": 0.30,
                        "falloff": 1.2,
                        "perspective": 0.08
                    },
                    {
                        "type": "crease_shading",
                        "axis": "vertical",
                        "position": 0.5,
                        "width": 36.0,
                        "dark_side": 0.45,
                        "light_side": 0.25,
                        "softness": 0.60
                    },
                    {
                        "type": "drop_shadow",
                        "offset": [0.0, 32.0],
                        "radius": 48.0,
                        "color": [0.0, 0.0, 0.0, 0.30]
                    }
                ]
            },
            # Typography inside folded document
            {
                "id": "doc_title",
                "type": "text",
                "text": "CONFIDENTIAL ARCHITECTURE MEMO",
                "size": [900, 48],
                "position": [960, 420],
                "start_frame": 0,
                "duration_frames": DURATION_FRAMES,
                "style": {
                    "font": "assets/fonts/Space-Grotesk.ttf",
                    "font_size": 28.0,
                    "fill": "#1C1917"
                }
            },
            {
                "id": "doc_body",
                "type": "text",
                "text": "3D Bilinear Crease Warp • Realistic Paper Deformation • Deterministic Shading",
                "size": [900, 36],
                "position": [960, 500],
                "start_frame": 0,
                "duration_frames": DURATION_FRAMES,
                "style": {
                    "font": "assets/fonts/Inter-Regular.ttf",
                    "font_size": 18.0,
                    "fill": "#78716C"
                }
            },
            {
                "id": "doc_stamp",
                "type": "shape",
                "size": [180, 56],
                "position": [960, 600],
                "start_frame": 0,
                "duration_frames": DURATION_FRAMES,
                "shape": {
                    "type": "rect",
                    "radius": 8.0,
                    "fill": [0.86, 0.15, 0.15, 1.0],
                    "stroke": {"color": "#B91C1C", "width": 2.0}
                }
            },
            {
                "id": "stamp_text",
                "type": "text",
                "text": "VERIFIED V1",
                "size": [180, 30],
                "position": [960, 600],
                "start_frame": 0,
                "duration_frames": DURATION_FRAMES,
                "style": {
                    "font": "assets/fonts/Inter-Bold.ttf",
                    "font_size": 16.0,
                    "fill": "#FFFFFF"
                }
            }
        ]
    }

# ─────────────────────────────────────────────────────────────────────────────
# 3. Overlay 03: Frosted Glass (BackdropFilter blur, refraction, rim light)
# ─────────────────────────────────────────────────────────────────────────────
def build_overlay_03_frosted_glass():
    circle1_keys = []
    circle2_keys = []
    for f in range(0, DURATION_FRAMES + 1, 5):
        t = f / DURATION_FRAMES
        circle1_keys.append({"frame": f, "value": 600.0 + math.sin(t * math.pi * 2.0) * 150.0})
        circle2_keys.append({"frame": f, "value": 1300.0 - math.cos(t * math.pi * 2.0) * 150.0})

    return {
        "schema": "chronon.render-plan.v3",
        "version": 3,
        "job_id": "premium_03_frosted_glass",
        "canvas": {"width": WIDTH, "height": HEIGHT, "fps_num": FPS, "fps_den": 1, "duration_frames": DURATION_FRAMES},
        "output": {"path": str(OUT_DIR / "overlay_03_frosted_glass.mp4"), "format": "mp4", "codec": "h264"},
        "layers": [
            # Dark background
            {
                "id": "glass_bg",
                "type": "shape",
                "size": [WIDTH, HEIGHT],
                "position": [960, 540],
                "start_frame": 0,
                "duration_frames": DURATION_FRAMES,
                "shape": {
                    "type": "rect",
                    "fill": [0.04, 0.06, 0.12, 1.0]
                }
            },
            # Moving colorful backdrop orb 1 (Magenta)
            {
                "id": "backdrop_orb1",
                "type": "shape",
                "size": [500, 500],
                "position": [600, 540],
                "start_frame": 0,
                "duration_frames": DURATION_FRAMES,
                "shape": {
                    "type": "ellipse",
                    "fill": [0.93, 0.28, 0.60, 0.85]
                },
                "animation": {
                    "tracks": [
                        {"property": "position_x", "easing": "linear", "keyframes": circle1_keys}
                    ]
                }
            },
            # Moving colorful backdrop orb 2 (Cyan)
            {
                "id": "backdrop_orb2",
                "type": "shape",
                "size": [550, 550],
                "position": [1300, 500],
                "start_frame": 0,
                "duration_frames": DURATION_FRAMES,
                "shape": {
                    "type": "ellipse",
                    "fill": [0.02, 0.71, 0.83, 0.85]
                },
                "animation": {
                    "tracks": [
                        {"property": "position_x", "easing": "linear", "keyframes": circle2_keys}
                    ]
                }
            },
            # Foreground Frosted Glass Card with BackdropFilter authority
            {
                "id": "frosted_glass_card",
                "type": "shape",
                "size": [960, 560],
                "position": [960, 540],
                "start_frame": 0,
                "duration_frames": DURATION_FRAMES,
                "shape": {
                    "type": "rect",
                    "radius": 24.0,
                    "fill": [1.0, 1.0, 1.0, 0.12]
                },
                "backdrop_filter": {
                    "blur": 32.0,
                    "brightness": 1.08,
                    "saturation": 1.15,
                    "refraction_strength": 0.08,
                    "rim_strength": 0.50,
                    "rim_width": 3.0,
                    "chromatic_dispersion": 0.05,
                    "grain": 0.03,
                    "opacity": 0.95
                }
            },
            # Glass Card Content
            {
                "id": "glass_badge",
                "type": "text",
                "text": "PREMIUM GLASS OS",
                "size": [800, 30],
                "position": [960, 390],
                "start_frame": 0,
                "duration_frames": DURATION_FRAMES,
                "style": {
                    "font": "assets/fonts/Space-Grotesk.ttf",
                    "font_size": 16.0,
                    "fill": "#38BDF8"
                }
            },
            {
                "id": "glass_title",
                "type": "text",
                "text": "Frosted Acrylic Glass",
                "size": [800, 64],
                "position": [960, 470],
                "start_frame": 0,
                "duration_frames": DURATION_FRAMES,
                "style": {
                    "font": "assets/fonts/Poppins-Bold.ttf",
                    "font_size": 44.0,
                    "fill": "#FFFFFF"
                }
            },
            {
                "id": "glass_desc",
                "type": "text",
                "text": "Non-layer BackdropFilter Authority • Refractive Dispersion • Edge Rim Light",
                "size": [800, 40],
                "position": [960, 560],
                "start_frame": 0,
                "duration_frames": DURATION_FRAMES,
                "style": {
                    "font": "assets/fonts/Inter-Regular.ttf",
                    "font_size": 18.0,
                    "fill": "#CBD5E1"
                }
            }
        ]
    }

# ─────────────────────────────────────────────────────────────────────────────
# 4. Overlay 04: Retro CRT Terminal (LensDistortion + Bloom + Noise)
# ─────────────────────────────────────────────────────────────────────────────
def build_overlay_04_retro_crt_terminal():
    return {
        "schema": "chronon.render-plan.v3",
        "version": 3,
        "job_id": "premium_04_retro_crt_terminal",
        "canvas": {"width": WIDTH, "height": HEIGHT, "fps_num": FPS, "fps_den": 1, "duration_frames": DURATION_FRAMES},
        "output": {"path": str(OUT_DIR / "overlay_04_retro_crt_terminal.mp4"), "format": "mp4", "codec": "h264"},
        "layers": [
            # Terminal background
            {
                "id": "crt_bg",
                "type": "shape",
                "size": [WIDTH, HEIGHT],
                "position": [960, 540],
                "start_frame": 0,
                "duration_frames": DURATION_FRAMES,
                "shape": {
                    "type": "rect",
                    "fill": [0.01, 0.04, 0.02, 1.0]
                }
            },
            # CRT Bezel Screen Frame
            {
                "id": "crt_screen",
                "type": "shape",
                "size": [1500, 900],
                "position": [960, 540],
                "start_frame": 0,
                "duration_frames": DURATION_FRAMES,
                "shape": {
                    "type": "rect",
                    "radius": 32.0,
                    "fill": [0.02, 0.10, 0.05, 1.0],
                    "stroke": {"color": "#15803D", "width": 3.0}
                }
            },
            # Terminal text contents
            {
                "id": "crt_header",
                "type": "text",
                "text": "CHRONON3D CORE KERNEL v2.5 [SYSTEM DIAGNOSTIC]",
                "size": [1300, 36],
                "position": [960, 240],
                "start_frame": 0,
                "duration_frames": DURATION_FRAMES,
                "style": {
                    "font": "assets/fonts/Space-Grotesk.ttf",
                    "font_size": 22.0,
                    "fill": "#4ADE80"
                }
            },
            {
                "id": "crt_log1",
                "type": "text",
                "text": "> INITIALIZING BARREL LENS DISTORTION (CURVATURE=0.20)... OK",
                "size": [1300, 32],
                "position": [960, 340],
                "start_frame": 0,
                "duration_frames": DURATION_FRAMES,
                "style": {
                    "font": "assets/fonts/Space-Grotesk.ttf",
                    "font_size": 18.0,
                    "fill": "#22C55E"
                }
            },
            {
                "id": "crt_log2",
                "type": "text",
                "text": "> ENGAGING PHOSPHOR PERSISTENCE & CHROMATIC DISPERSION... OK",
                "size": [1300, 32],
                "position": [960, 410],
                "start_frame": 0,
                "duration_frames": DURATION_FRAMES,
                "style": {
                    "font": "assets/fonts/Space-Grotesk.ttf",
                    "font_size": 18.0,
                    "fill": "#22C55E"
                }
            },
            {
                "id": "crt_log3",
                "type": "text",
                "text": "> ALL AUTHORITY PRESETS VALIDATED: 45 CANONICAL PRIMITIVES MOUNTED",
                "size": [1300, 32],
                "position": [960, 480],
                "start_frame": 0,
                "duration_frames": DURATION_FRAMES,
                "style": {
                    "font": "assets/fonts/Space-Grotesk.ttf",
                    "font_size": 18.0,
                    "fill": "#86EFAC"
                }
            },
            {
                "id": "crt_reticle",
                "type": "shape",
                "size": [300, 300],
                "position": [960, 680],
                "start_frame": 0,
                "duration_frames": DURATION_FRAMES,
                "shape": {
                    "type": "ellipse",
                    "fill": [0.0, 0.0, 0.0, 0.0],
                    "stroke": {"color": "#22C55E", "width": 2.0}
                }
            },
            # CRT Post-Processing Adjustment Layer
            {
                "id": "crt_post_pipeline",
                "type": "adjustment",
                "effects": [
                    {
                        "type": "lens_distortion",
                        "curvature": 0.20,
                        "scale": 0.98,
                        "center": [0.5, 0.5]
                    },
                    {
                        "type": "bloom",
                        "threshold": 0.35,
                        "radius": 24.0,
                        "intensity": 0.85
                    },
                    {
                        "type": "vignette",
                        "radius": 0.65,
                        "softness": 0.50,
                        "amount": 0.80
                    },
                    {
                        "type": "noise",
                        "amount": 0.04
                    }
                ]
            }
        ]
    }

# ─────────────────────────────────────────────────────────────────────────────
# 5. Overlay 05: Cinematic Halation & Anamorphic Flare
# ─────────────────────────────────────────────────────────────────────────────
def build_overlay_05_cinematic_halation_flare():
    return {
        "schema": "chronon.render-plan.v3",
        "version": 3,
        "job_id": "premium_05_cinematic_halation_flare",
        "canvas": {"width": WIDTH, "height": HEIGHT, "fps_num": FPS, "fps_den": 1, "duration_frames": DURATION_FRAMES},
        "output": {"path": str(OUT_DIR / "overlay_05_cinematic_halation_flare.mp4"), "format": "mp4", "codec": "h264"},
        "layers": [
            # Deep cinematic letterbox dark background
            {
                "id": "film_bg",
                "type": "shape",
                "size": [WIDTH, HEIGHT],
                "position": [960, 540],
                "start_frame": 0,
                "duration_frames": DURATION_FRAMES,
                "shape": {
                    "type": "rect",
                    "fill": [0.03, 0.03, 0.04, 1.0]
                }
            },
            # Bright luminous typography plate that feeds the halation response
            {
                "id": "cinema_title",
                "type": "text",
                "text": "STELLAR ODYSSEY",
                "size": [1400, 110],
                "position": [960, 480],
                "start_frame": 0,
                "duration_frames": DURATION_FRAMES,
                "style": {
                    "font": "assets/fonts/Poppins-Bold.ttf",
                    "font_size": 76.0,
                    "fill": "#FFFFFF"
                },
                "effects": [
                    {
                        "type": "luminance_response",
                        "threshold": 0.60,
                        "softness": 0.25,
                        "radius": 24.0,
                        "intensity": 1.40,
                        "tint": [1.0, 0.32, 0.12, 1.0],
                        "blend": "screen"
                    },
                    {
                        "type": "directional_blur",
                        "angle": 0.0,
                        "length": 80.0
                    },
                    {"type": "glow", "radius": 36.0, "intensity": 0.40, "color": [0.2, 0.6, 1.0, 1.0]}
                ]
            },
            {
                "id": "cinema_sub",
                "type": "text",
                "text": "SHOT ON 70MM ANAMORPHIC • LUMINANCE RESPONSE KERNEL",
                "size": [1400, 36],
                "position": [960, 600],
                "start_frame": 0,
                "duration_frames": DURATION_FRAMES,
                "style": {
                    "font": "assets/fonts/Space-Grotesk.ttf",
                    "font_size": 20.0,
                    "fill": "#94A3B8"
                }
            },
            # Subtle film grain pass
            {
                "id": "film_grain",
                "type": "adjustment",
                "effects": [
                    {"type": "vignette", "radius": 0.75, "softness": 0.45, "amount": 0.60},
                    {"type": "noise", "amount": 0.03}
                ]
            }
        ]
    }

# ─────────────────────────────────────────────────────────────────────────────
# 6. Overlay 06: Desert Heatwave (TurbulentDisplace vertical atmospheric shimmer)
# ─────────────────────────────────────────────────────────────────────────────
def build_overlay_06_desert_heatwave():
    return {
        "schema": "chronon.render-plan.v3",
        "version": 3,
        "job_id": "premium_06_desert_heatwave",
        "canvas": {"width": WIDTH, "height": HEIGHT, "fps_num": FPS, "fps_den": 1, "duration_frames": DURATION_FRAMES},
        "output": {"path": str(OUT_DIR / "overlay_06_desert_heatwave.mp4"), "format": "mp4", "codec": "h264"},
        "layers": [
            # Sunset sky gradient
            {
                "id": "sky_bg",
                "type": "shape",
                "size": [WIDTH, HEIGHT],
                "position": [960, 540],
                "start_frame": 0,
                "duration_frames": DURATION_FRAMES,
                "shape": {
                    "type": "rect",
                    "fill": [0.85, 0.40, 0.15, 1.0]
                }
            },
            # Sun disk
            {
                "id": "sun_disk",
                "type": "shape",
                "size": [360, 360],
                "position": [960, 450],
                "start_frame": 0,
                "duration_frames": DURATION_FRAMES,
                "shape": {
                    "type": "ellipse",
                    "fill": [0.99, 0.94, 0.54, 1.0]
                },
                "effects": [
                    {"type": "glow", "radius": 64.0, "intensity": 0.60, "color": [1.0, 0.7, 0.2, 1.0]}
                ]
            },
            # Distant mountain silhouettes
            {
                "id": "mountains",
                "type": "shape",
                "size": [WIDTH, 400],
                "position": [960, 750],
                "start_frame": 0,
                "duration_frames": DURATION_FRAMES,
                "shape": {
                    "type": "path",
                    "path": [
                        {"type": "move_to", "point": [-960.0, 200.0]},
                        {"type": "line_to", "point": [-600.0, -80.0]},
                        {"type": "line_to", "point": [-200.0, 60.0]},
                        {"type": "line_to", "point": [200.0, -120.0]},
                        {"type": "line_to", "point": [600.0, 20.0]},
                        {"type": "line_to", "point": [960.0, -60.0]},
                        {"type": "line_to", "point": [960.0, 200.0]},
                        {"type": "close"}
                    ],
                    "fill": [0.16, 0.04, 0.02, 1.0]
                }
            },
            # Typographic title subjected to heatwave shimmer
            {
                "id": "heat_title",
                "type": "text",
                "text": "MOJAVE HEATWAVE",
                "size": [1200, 100],
                "position": [960, 480],
                "start_frame": 0,
                "duration_frames": DURATION_FRAMES,
                "style": {
                    "font": "assets/fonts/Poppins-Bold.ttf",
                    "font_size": 72.0,
                    "fill": "#FFFFFF"
                }
            },
            # Heatwave Turbulent Displacement adjustment layer
            {
                "id": "heatwave_sim",
                "type": "adjustment",
                "effects": [
                    {
                        "type": "turbulent_displace",
                        "amount": 0.12,
                        "size": 0.08,
                        "evolution": 12.0,
                        "evolution_speed": 1.5,
                        "complexity": 4
                    },
                    {
                        "type": "directional_blur",
                        "angle": 90.0,
                        "length": 4.0
                    }
                ]
            }
        ]
    }

# ─────────────────────────────────────────────────────────────────────────────
# 7. Overlay 07: Velocity RGB Split
# ─────────────────────────────────────────────────────────────────────────────
def build_overlay_07_velocity_rgb_split():
    pos_x_keys = [
        {"frame": 0, "value": 300.0},
        {"frame": 40, "value": 300.0},
        {"frame": 75, "value": 960.0},
        {"frame": 110, "value": 1620.0},
        {"frame": 150, "value": 1620.0}
    ]

    return {
        "schema": "chronon.render-plan.v3",
        "version": 3,
        "job_id": "premium_07_velocity_rgb_split",
        "canvas": {"width": WIDTH, "height": HEIGHT, "fps_num": FPS, "fps_den": 1, "duration_frames": DURATION_FRAMES},
        "output": {"path": str(OUT_DIR / "overlay_07_velocity_rgb_split.mp4"), "format": "mp4", "codec": "h264"},
        "layers": [
            # Technical dark cyber background
            {
                "id": "cyber_bg",
                "type": "shape",
                "size": [WIDTH, HEIGHT],
                "position": [960, 540],
                "start_frame": 0,
                "duration_frames": DURATION_FRAMES,
                "shape": {
                    "type": "rect",
                    "fill": [0.04, 0.06, 0.09, 1.0]
                }
            },
            # Speed guideline accents
            {
                "id": "speed_lines",
                "type": "shape",
                "size": [WIDTH, 120],
                "position": [960, 540],
                "start_frame": 0,
                "duration_frames": DURATION_FRAMES,
                "shape": {
                    "type": "path",
                    "path": [
                        {"type": "move_to", "point": [-960.0, -30.0]},
                        {"type": "line_to", "point": [960.0, -30.0]},
                        {"type": "move_to", "point": [-960.0, 30.0]},
                        {"type": "line_to", "point": [960.0, 30.0]}
                    ],
                    "stroke": {"color": "#1E293B", "width": 2.0}
                }
            },
            # High speed animated data card with Chromatic Aberration (Velocity mode)
            {
                "id": "velocity_card",
                "type": "shape",
                "size": [460, 160],
                "position": [300, 540],
                "start_frame": 0,
                "duration_frames": DURATION_FRAMES,
                "shape": {
                    "type": "rect",
                    "radius": 20.0,
                    "fill": [0.23, 0.51, 0.96, 1.0],
                    "stroke": {"color": "#60A5FA", "width": 2.0}
                },
                "effects": [
                    {
                        "type": "chromatic_aberration",
                        "mode": "velocity",
                        "amount": 0.04,
                        "velocity": [25.0, 0.0]
                    },
                    {
                        "type": "drop_shadow",
                        "offset": [0.0, 20.0],
                        "radius": 32.0,
                        "color": [0.0, 0.0, 0.0, 0.35]
                    }
                ],
                "animation": {
                    "tracks": [
                        {"property": "position_x", "easing": "in_out_quad", "keyframes": pos_x_keys}
                    ]
                }
            },
            # Text inside moving card
            {
                "id": "card_label",
                "type": "text",
                "text": "HIGH VELOCITY",
                "size": [400, 32],
                "position": [300, 520],
                "start_frame": 0,
                "duration_frames": DURATION_FRAMES,
                "style": {
                    "font": "assets/fonts/Inter-Bold.ttf",
                    "font_size": 22.0,
                    "fill": "#FFFFFF"
                },
                "animation": {
                    "tracks": [
                        {"property": "position_x", "easing": "in_out_quad", "keyframes": pos_x_keys}
                    ]
                }
            },
            {
                "id": "card_sub",
                "type": "text",
                "text": "Velocity RGB Split Authority",
                "size": [400, 24],
                "position": [300, 560],
                "start_frame": 0,
                "duration_frames": DURATION_FRAMES,
                "style": {
                    "font": "assets/fonts/Inter-Regular.ttf",
                    "font_size": 15.0,
                    "fill": "#DBEAFE"
                },
                "animation": {
                    "tracks": [
                        {"property": "position_x", "easing": "in_out_quad", "keyframes": pos_x_keys}
                    ]
                }
            }
        ]
    }

SHOWCASE_SUITE = [
    ("overlay_01_document_highlight", build_overlay_01_document_highlight),
    ("overlay_02_paper_fold", build_overlay_02_paper_fold),
    ("overlay_03_frosted_glass", build_overlay_03_frosted_glass),
    ("overlay_04_retro_crt_terminal", build_overlay_04_retro_crt_terminal),
    ("overlay_05_cinematic_halation_flare", build_overlay_05_cinematic_halation_flare),
    ("overlay_06_desert_heatwave", build_overlay_06_desert_heatwave),
    ("overlay_07_velocity_rgb_split", build_overlay_07_velocity_rgb_split),
]

def main():
    print(f"=== Starting Chronon Premium Effects V1 Showcase Suite ({len(SHOWCASE_SUITE)} items) ===", flush=True)

    # 1. Write plans and validate
    plan_files = []
    for item_id, builder in SHOWCASE_SUITE:
        plan_data = builder()
        plan_path = OUT_DIR / f"{item_id}.plan.json"
        plan_path.write_text(json.dumps(plan_data, indent=2))

        # Validate with absolute assets root
        vcmd = [str(CHRONON_CLI), "validate", "--plan", str(plan_path), "--assets-root", str(ASSETS_ROOT)]
        vres = subprocess.run(vcmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if vres.returncode != 0:
            print(f"  [VALIDATION FAIL] {item_id}: {vres.stderr}\n{vres.stdout}")
            sys.exit(1)
        plan_files.append((item_id, plan_path))
        print(f"  ✓ [Validated] {plan_path.name}")

    # 2. Render each composition directly to MP4 via GPU pipe + NVENC
    rendered_files = []
    for item_id, plan_path in plan_files:
        out_mp4 = OUT_DIR / f"{item_id}.mp4"
        out_png = OUT_DIR / f"{item_id}.png"
        if out_mp4.exists() and out_mp4.stat().st_size > 20000:
            print(f"\n[Already Rendered] {out_mp4.name} ({out_mp4.stat().st_size:,} bytes)")
            rendered_files.append(out_mp4)
            if not out_png.exists():
                subprocess.run(["ffmpeg", "-y", "-ss", "00:00:02", "-i", str(out_mp4), "-vframes", "1", str(out_png)],
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            if out_png.exists():
                rendered_files.append(out_png)
            continue

        cmd = [
            str(CHRONON_CLI),
            "render",
            "--backend", "software",
            "--plan", str(plan_path),
            "--assets-root", str(ASSETS_ROOT),
            "-o", str(out_mp4),
            "--ffmpeg-mode", "pipe",
            "--codec", "h264_nvenc"
        ]
        print(f"\n[Rendering GPU/NVENC Pipe] {item_id} -> {out_mp4.name}...", flush=True)
        t0 = time.time()
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        dt = time.time() - t0
        if res.returncode != 0:
            print(f"  [ERROR] {res.stderr}\n{res.stdout}")
            continue

        sz = out_mp4.stat().st_size if out_mp4.exists() else 0
        print(f"  ✓ Rendered & Encoded in {dt:.1f}s ({sz:,} bytes)")
        rendered_files.append(out_mp4)

        # Extract PNG poster at 2.0s
        out_png = OUT_DIR / f"{item_id}.png"
        subprocess.run(["ffmpeg", "-y", "-ss", "00:00:02", "-i", str(out_mp4), "-vframes", "1", str(out_png)],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if out_png.exists():
            rendered_files.append(out_png)

    # 3. Upload to Google Drive folder 1ATL0bnJXijNqFlKkgWye3PEAdAuQa1HI
    print(f"\n=== Uploading {len(rendered_files)} media files to Google Drive ({DRIVE_FOLDER_ID}) ===", flush=True)
    token = refresh_drive_token()
    uploads = []
    for fpath in rendered_files:
        print(f"Uploading {fpath.name} ({fpath.stat().st_size:,} bytes)...", flush=True)
        meta = upload_to_drive(token, fpath, DRIVE_FOLDER_ID)
        uploads.append(meta)
        print(f"  ✓ Uploaded! ID: {meta.get('id')}")

    print("\n=== SUMMARY OF COMPLETED PREMIUM EFFECTS OVERLAYS ===")
    for u in uploads:
        print(f"- {u.get('name')}: {u.get('id')} ({u.get('webViewLink')})")

if __name__ == "__main__":
    main()
