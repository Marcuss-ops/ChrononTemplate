#!/usr/bin/env python3
"""
Recreate 'Modern Entities With Text' animations in ChrononTemplate from user references:
1. Neon Glass Card + Luminous Neon Pill Badge (from ref 1XbW2CewH20NgTrDWtcdcavROd6MjXDbT)
2. Curved Widescreen CRT Display + Studio Typography (from ref 1JOquPOeHdSfLcBNPqEXCWPY2cbkETfSX)
Includes asset generation, plan construction, GPU rendering via chronon3d_cli,
and upload to Google Drive.
"""

import os
import math
import json
import time
import glob
import subprocess
import concurrent.futures
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter
import numpy as np

BASE_DIR = Path("/home/pierone/src/go-master/projects/Pyt/VeloxEditing")
OUT_DIR = BASE_DIR / "ChrononTemplate/out/modern_entities_with_text"
ASSETS_DIR = OUT_DIR / "assets"
PLANS_DIR = OUT_DIR / "plans"
VIDEOS_DIR = OUT_DIR / "videos"
FRAMES_DIR = OUT_DIR / "frames"
REF_DIR = BASE_DIR / "ChrononTemplate/out/modern_entities_ref"

CLI_PATH = BASE_DIR / "Chronon3d/build/chronon/linux-video-fast-dev/apps/chronon3d_cli/chronon3d_cli"
FONT_BOLD = "ChrononTemplate/out/apple_spatial_entity_pack/assets/Montserrat-Bold.ttf"
UPLOADER = BASE_DIR / "RenderingGen/bin/drive-upload"
CREDS = os.path.expanduser("~/.config/velox/credentials.json")
TOKEN = os.path.expanduser("~/.config/velox/token.json")
FOLDER_ID = "1Sc5gBaNCAsAkrfM-j9Ccm4kNwrKBBYuC"

for d in [ASSETS_DIR, PLANS_DIR, VIDEOS_DIR, FRAMES_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# =========================================================================
# 1. ASSET BUILDERS: STYLE 1 (Neon Glass Card + Neon Pill Badge)
# =========================================================================

def build_neon_glass_card(src_image_path, out_filename, glow_rgb=(80, 255, 180), rim_width=3, card_w=620, card_h=680, radius=42):
    """Creates an anti-aliased rounded card with intense neon rim + multi-pass Gaussian bloom."""
    scale = 2
    CW, CH = card_w * scale, card_h * scale
    R = radius * scale
    spread = 60 * scale
    TW, TH = CW + spread * 2, CH + spread * 2

    # Open and center-crop source image
    if os.path.exists(src_image_path):
        src = Image.open(src_image_path).convert("RGBA")
        # Crop or fit to CW, CH
        src_aspect = src.width / src.height
        target_aspect = CW / CH
        if src_aspect > target_aspect:
            nw = int(src.height * target_aspect)
            x0 = (src.width - nw) // 2
            src = src.crop((x0, 0, x0 + nw, src.height))
        else:
            nh = int(src.width / target_aspect)
            y0 = (src.height - nh) // 2
            src = src.crop((0, y0, src.width, y0 + nh))
        src = src.resize((CW, CH), Image.Resampling.LANCZOS)
    else:
        src = Image.new("RGBA", (CW, CH), (20, 24, 30, 255))

    # Mask for card
    mask_hi = Image.new("L", (CW, CH), 0)
    m_draw = ImageDraw.Draw(mask_hi)
    m_draw.rounded_rectangle([0, 0, CW - 1, CH - 1], radius=R, fill=255)

    card = Image.new("RGBA", (CW, CH), (0, 0, 0, 0))
    # Dark glass base underneath photo
    glass_base = Image.new("RGBA", (CW, CH), (10, 12, 16, 255))
    card.paste(glass_base, (0, 0), mask=mask_hi)
    card.paste(src, (0, 0), mask=mask_hi)

    # Neon rim stroke
    rim_hi = Image.new("RGBA", (CW, CH), (0, 0, 0, 0))
    r_draw = ImageDraw.Draw(rim_hi)
    r_draw.rounded_rectangle([2, 2, CW - 3, CH - 3], radius=R, outline=(*glow_rgb, 255), width=rim_width * scale)
    card = Image.alpha_composite(card, rim_hi)

    # Multi-pass outer bloom
    canvas = Image.new("RGBA", (TW, TH), (0, 0, 0, 0))
    glow_base = Image.new("RGBA", (TW, TH), (0, 0, 0, 0))
    glow_color = Image.new("RGBA", (CW, CH), (*glow_rgb, 220))
    glow_base.paste(glow_color, (spread, spread), mask=mask_hi)

    g1 = glow_base.filter(ImageFilter.GaussianBlur(radius=8 * scale))
    g2 = glow_base.filter(ImageFilter.GaussianBlur(radius=22 * scale))
    g3 = glow_base.filter(ImageFilter.GaussianBlur(radius=48 * scale))

    canvas = Image.alpha_composite(canvas, g3)
    canvas = Image.alpha_composite(canvas, g2)
    canvas = Image.alpha_composite(canvas, g1)

    # Subtle drop shadow behind
    shadow_base = Image.new("RGBA", (TW, TH), (0, 0, 0, 0))
    shadow_fill = Image.new("RGBA", (CW, CH), (0, 0, 0, 180))
    shadow_base.paste(shadow_fill, (spread, spread + 12 * scale), mask=mask_hi)
    canvas = Image.alpha_composite(canvas, shadow_base.filter(ImageFilter.GaussianBlur(radius=16 * scale)))

    # Paste crisp card on top
    canvas.paste(card, (spread, spread), mask=card)

    final = canvas.resize((TW // scale, TH // scale), Image.Resampling.LANCZOS)
    out_p = ASSETS_DIR / out_filename
    final.save(out_p, "PNG")
    print(f"Created Neon Glass Card: {out_p} ({final.size})")
    return out_p


def build_neon_pill_badge(out_filename, glow_rgb=(80, 255, 180), pill_w=680, pill_h=110, rim_width=3):
    """Creates a high-contrast dark capsule pill with glowing neon stroke and outer bloom."""
    scale = 2
    PW, PH = pill_w * scale, pill_h * scale
    R = PH // 2
    spread = 40 * scale
    TW, TH = PW + spread * 2, PH + spread * 2

    mask_hi = Image.new("L", (PW, PH), 0)
    m_draw = ImageDraw.Draw(mask_hi)
    m_draw.rounded_rectangle([0, 0, PW - 1, PH - 1], radius=R, fill=255)

    pill = Image.new("RGBA", (PW, PH), (0, 0, 0, 0))
    # Dark charcoal fill
    bg = Image.new("RGBA", (PW, PH), (12, 14, 18, 245))
    pill.paste(bg, (0, 0), mask=mask_hi)

    # Crisp neon border
    r_draw = ImageDraw.Draw(pill)
    r_draw.rounded_rectangle([3, 3, PW - 4, PH - 4], radius=R, outline=(*glow_rgb, 255), width=rim_width * scale)

    # Bloom
    canvas = Image.new("RGBA", (TW, TH), (0, 0, 0, 0))
    glow_base = Image.new("RGBA", (TW, TH), (0, 0, 0, 0))
    glow_color = Image.new("RGBA", (PW, PH), (*glow_rgb, 200))
    glow_base.paste(glow_color, (spread, spread), mask=mask_hi)

    g1 = glow_base.filter(ImageFilter.GaussianBlur(radius=6 * scale))
    g2 = glow_base.filter(ImageFilter.GaussianBlur(radius=18 * scale))
    g3 = glow_base.filter(ImageFilter.GaussianBlur(radius=36 * scale))

    canvas = Image.alpha_composite(canvas, g3)
    canvas = Image.alpha_composite(canvas, g2)
    canvas = Image.alpha_composite(canvas, g1)

    canvas.paste(pill, (spread, spread), mask=pill)
    final = canvas.resize((TW // scale, TH // scale), Image.Resampling.LANCZOS)
    out_p = ASSETS_DIR / out_filename
    final.save(out_p, "PNG")
    print(f"Created Neon Pill Badge: {out_p} ({final.size})")
    return out_p


# =========================================================================
# 2. ASSET BUILDERS: STYLE 2 (Curved Widescreen CRT Display)
# =========================================================================

def build_curved_crt_mask(W=1400, H=790):
    scale = 2
    MW, MH = W * scale, H * scale
    mask = Image.new("L", (MW, MH), 0)
    draw = ImageDraw.Draw(mask)

    corner_r = 75 * scale
    dip_y = 28 * scale
    bulge_x = 8 * scale
    pts = []
    n_edge = 60

    # Top edge
    for i in range(n_edge + 1):
        t = i / n_edge
        px = corner_r + t * (MW - 2 * corner_r)
        u = (px - MW/2) / (MW/2)
        py = dip_y * (1.0 - u**2)
        pts.append((px, py))

    # Top-Right corner
    cx_tr = MW - corner_r
    cy_tr = corner_r + dip_y * (1.0 - ((cx_tr - MW/2)/(MW/2))**2)
    for i in range(1, 20):
        ang = -math.pi/2 + (i / 20) * (math.pi/2)
        pts.append((cx_tr + corner_r * math.cos(ang), cy_tr + corner_r * math.sin(ang)))

    # Right edge
    for i in range(n_edge + 1):
        t = i / n_edge
        py = corner_r + t * (MH - 2 * corner_r)
        v = (py - MH/2) / (MH/2)
        px = MW - (bulge_x * (1.0 - v**2))
        pts.append((px, py))

    # Bottom-Right corner
    cx_br = MW - corner_r
    cy_br = MH - corner_r - dip_y * (1.0 - ((cx_br - MW/2)/(MW/2))**2)
    for i in range(1, 20):
        ang = 0 + (i / 20) * (math.pi/2)
        pts.append((cx_br + corner_r * math.cos(ang), cy_br + corner_r * math.sin(ang)))

    # Bottom edge
    for i in range(n_edge + 1):
        t = i / n_edge
        px = (MW - corner_r) - t * (MW - 2 * corner_r)
        u = (px - MW/2) / (MW/2)
        py = MH - dip_y * (1.0 - u**2)
        pts.append((px, py))

    # Bottom-Left corner
    cx_bl = corner_r
    cy_bl = MH - corner_r - dip_y * (1.0 - ((cx_bl - MW/2)/(MW/2))**2)
    for i in range(1, 20):
        ang = math.pi/2 + (i / 20) * (math.pi/2)
        pts.append((cx_bl + corner_r * math.cos(ang), cy_bl + corner_r * math.sin(ang)))

    # Left edge
    for i in range(n_edge + 1):
        t = i / n_edge
        py = (MH - corner_r) - t * (MH - 2 * corner_r)
        v = (py - MH/2) / (MH/2)
        px = bulge_x * (1.0 - v**2)
        pts.append((px, py))

    # Top-Left corner
    cx_tl = corner_r
    cy_tl = corner_r + dip_y * (1.0 - ((cx_tl - MW/2)/(MW/2))**2)
    for i in range(1, 20):
        ang = math.pi + (i / 20) * (math.pi/2)
        pts.append((cx_tl + corner_r * math.cos(ang), cy_tl + corner_r * math.sin(ang)))

    draw.polygon(pts, fill=255)
    return mask.resize((W, H), Image.Resampling.LANCZOS)


def build_curved_screen_composite(src_image_path, out_filename, W=1400, H=790):
    mask = build_curved_crt_mask(W, H)
    pad = 80
    TW, TH = W + pad * 2, H + pad * 2

    src = Image.open(src_image_path).convert("RGBA")
    # Cover crop src to W, H
    s_aspect = src.width / src.height
    t_aspect = W / H
    if s_aspect > t_aspect:
        nw = int(src.height * t_aspect)
        x0 = (src.width - nw) // 2
        src = src.crop((x0, 0, x0 + nw, src.height))
    else:
        nh = int(src.width / t_aspect)
        y0 = (src.height - nh) // 2
        src = src.crop((0, y0, src.width, y0 + nh))
    src = src.resize((W, H), Image.Resampling.LANCZOS)

    screen = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    screen.paste(src, (0, 0), mask=mask)

    # Soft bezel outline
    bezel = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    b_draw = ImageDraw.Draw(bezel)
    # stroke mask edges
    bezel_stroke = mask.filter(ImageFilter.FIND_EDGES).filter(ImageFilter.GaussianBlur(radius=1.5))
    screen.paste(Image.new("RGBA", (W, H), (255, 255, 255, 80)), (0, 0), mask=bezel_stroke)

    # Composite onto canvas with ambient drop shadow
    canvas = Image.new("RGBA", (TW, TH), (0, 0, 0, 0))
    shadow_base = Image.new("RGBA", (TW, TH), (0, 0, 0, 0))
    shadow_color = Image.new("RGBA", (W, H), (20, 22, 28, 160))
    shadow_base.paste(shadow_color, (pad, pad + 14), mask=mask)
    shadow = shadow_base.filter(ImageFilter.GaussianBlur(radius=28))

    canvas = Image.alpha_composite(canvas, shadow)
    canvas.paste(screen, (pad, pad), mask=screen)

    out_p = ASSETS_DIR / out_filename
    canvas.save(out_p, "PNG")
    print(f"Created Curved CRT Composite: {out_p} ({canvas.size})")
    return out_p


def build_studio_light_bg(out_filename="studio_light_bg.png", w=1920, h=1080):
    x = np.linspace(-1, 1, w)
    y = np.linspace(-1, 1, h)
    xx, yy = np.meshgrid(x, y)
    r = np.sqrt(xx**2 + (yy * 1.25)**2)
    val = np.clip(236 - r * 80, 140, 245).astype(np.uint8)
    bg_arr = np.dstack([val, val, val + 2, np.full((h, w), 255, dtype=np.uint8)])
    bg_img = Image.fromarray(bg_arr)
    out_p = ASSETS_DIR / out_filename
    bg_img.save(out_p, "PNG")
    print(f"Created Studio Light BG: {out_p}")
    return out_p


def build_studio_dark_bg(out_filename="studio_dark_bg.png", w=1920, h=1080):
    x = np.linspace(-1, 1, w)
    y = np.linspace(-1, 1, h)
    xx, yy = np.meshgrid(x, y)
    r = np.sqrt(xx**2 + (yy * 1.25)**2)
    val = np.clip(24 - r * 14, 8, 30).astype(np.uint8)
    bg_arr = np.dstack([val, val + 2, val + 5, np.full((h, w), 255, dtype=np.uint8)])
    bg_img = Image.fromarray(bg_arr)
    out_p = ASSETS_DIR / out_filename
    bg_img.save(out_p, "PNG")
    print(f"Created Studio Dark BG: {out_p}")
    return out_p


# =========================================================================
# 3. EXTRACT REFERENCE SAMPLES & PREPARE ASSETS
# =========================================================================

print("\n--- Generating Master Assets for Modern Entities With Text ---")

# Extract Hoopin' logo artwork from Reference 1
ref1_p = REF_DIR / "ref_entity_01_Screenshot 2026-10-06 174051.png"
ref1_img = Image.open(ref1_p)
# The logo is centered in the tilted card: approx x: 420..770, y: 150..470
hoopin_crop = ref1_img.crop((410, 140, 785, 470))
hoopin_raw = ASSETS_DIR / "hoopin_raw_logo.png"
hoopin_crop.save(hoopin_raw)

# Extract Sixers player from Reference 2
ref2_p = REF_DIR / "ref_entity_02_Screenshot 2026-10-07 at 17-54-35 When You Give A Psychopath A Basketball - YouTube.png"
ref2_img = Image.open(ref2_p)
# Active player area inside the screen: x: 300..1700, y: 150..980
sixers_crop = ref2_img.crop((320, 160, 1680, 970))
sixers_raw = ASSETS_DIR / "sixers_player_raw.png"
sixers_crop.save(sixers_raw)

# Also retrieve clean portraits from repo
trump_portrait = BASE_DIR / "ChrononTemplate/out/apple_spatial_entity_pack/assets/trump_clean_cutout.png"
steve_portrait = BASE_DIR / "ChrononTemplate/out/apple_spatial_entity_pack/assets/steve_jobs_raw.jpg"

# 1. Build Backgrounds
build_studio_light_bg("studio_light_bg.png")
build_studio_dark_bg("studio_dark_bg.png")

# 2. Build Style 1 Assets: Neon Cards & Pill Badges
build_neon_glass_card(hoopin_raw, "card_hoopin_cyan_glow.png", glow_rgb=(80, 255, 180), card_w=600, card_h=660)
build_neon_pill_badge("pill_badge_cyan.png", glow_rgb=(80, 255, 180), pill_w=640, pill_h=100)

build_neon_glass_card(trump_portrait, "card_trump_cyan_glow.png", glow_rgb=(0, 240, 255), card_w=600, card_h=660)
build_neon_pill_badge("pill_badge_cyan_electric.png", glow_rgb=(0, 240, 255), pill_w=640, pill_h=100)

build_neon_glass_card(steve_portrait, "card_steve_gold_glow.png", glow_rgb=(255, 205, 40), card_w=600, card_h=660)
build_neon_pill_badge("pill_badge_gold.png", glow_rgb=(255, 205, 40), pill_w=640, pill_h=100)

# 3. Build Style 2 Assets: Curved CRT Screens
build_curved_screen_composite(sixers_raw, "curved_screen_sixers.png", W=1380, H=780)
build_curved_screen_composite(trump_portrait, "curved_screen_trump.png", W=1380, H=780)
build_curved_screen_composite(steve_portrait, "curved_screen_steve.png", W=1380, H=780)

print("All visual assets built successfully!\n")


# =========================================================================
# 4. DEFINE ANIMATIONS & BUILD PLANS
# =========================================================================

recipes = [
    # ---------------------------------------------------------------------
    # RECIPE 1: Exact Replica of Ref 1 - Hoopin N' Holleri 3D Neon Card + Pill
    # ---------------------------------------------------------------------
    {
        "id": "modern_entity_01_neon_glass_hoopin",
        "family": "Modern Entities With Text",
        "style_name": "Neon 3D Glass Card + Cyan Pill Badge (Hoopin N' Holleri)",
        "bg_type": "color",
        "bg_color": [0.03, 0.035, 0.045, 1.0],
        "card_asset": "card_hoopin_cyan_glow.png",
        "card_pos": [960.0, 480.0],
        "card_size": [720.0, 780.0],
        "card_3d": True,
        "card_tracks": [
            {"property": "position_y", "easing": "out_cubic", "keyframes": [{"frame": 0, "value": -45.0}, {"frame": 45, "value": 0.0}, {"frame": 89, "value": 0.0}]},
            {"property": "position_z", "easing": "out_cubic", "keyframes": [{"frame": 0, "value": 160.0}, {"frame": 45, "value": 0.0}, {"frame": 89, "value": 0.0}]},
            {"property": "rotation_y", "easing": "out_cubic", "keyframes": [{"frame": 0, "value": -26.0}, {"frame": 45, "value": -14.0}, {"frame": 89, "value": -14.0}]},
            {"property": "rotation_x", "easing": "out_cubic", "keyframes": [{"frame": 0, "value": 20.0}, {"frame": 45, "value": 12.0}, {"frame": 89, "value": 12.0}]},
            {"property": "rotation_z", "easing": "out_cubic", "keyframes": [{"frame": 0, "value": -6.0}, {"frame": 45, "value": -3.0}, {"frame": 89, "value": -3.0}]},
            {"property": "scale", "easing": "out_cubic", "keyframes": [{"frame": 0, "value": 0.88}, {"frame": 45, "value": 1.0}, {"frame": 89, "value": 1.015}]},
            {"property": "opacity", "easing": "out_cubic", "keyframes": [{"frame": 0, "value": 0.0}, {"frame": 18, "value": 1.0}, {"frame": 89, "value": 1.0}]}
        ],
        "pill_asset": "pill_badge_cyan.png",
        "pill_pos": [960.0, 895.0],
        "pill_size": [720.0, 180.0],
        "pill_tracks": [
            {"property": "scale_x", "easing": "out_back", "keyframes": [{"frame": 12, "value": 0.1}, {"frame": 38, "value": 1.05}, {"frame": 50, "value": 1.0}, {"frame": 89, "value": 1.0}]},
            {"property": "opacity", "easing": "out_cubic", "keyframes": [{"frame": 12, "value": 0.0}, {"frame": 26, "value": 1.0}, {"frame": 89, "value": 1.0}]}
        ],
        "title": "Hoppin N’ Holleri",
        "title_pos": [960.0, 895.0],
        "title_size": [600.0, 60.0],
        "title_color": "#FFFFFF",
        "title_font_size": 42.0,
        "title_tracks": [
            {"property": "opacity", "easing": "out_cubic", "keyframes": [{"frame": 18, "value": 0.0}, {"frame": 34, "value": 1.0}, {"frame": 89, "value": 1.0}]},
            {"property": "scale", "easing": "out_back", "keyframes": [{"frame": 18, "value": 0.85}, {"frame": 42, "value": 1.02}, {"frame": 52, "value": 1.0}, {"frame": 89, "value": 1.0}]}
        ]
    },

    # ---------------------------------------------------------------------
    # RECIPE 2: Neon Glass Card with Portrait + Cyan Pill
    # ---------------------------------------------------------------------
    {
        "id": "modern_entity_02_neon_card_portrait_cyan",
        "family": "Modern Entities With Text",
        "style_name": "Neon 3D Glass Card + Cyan Electric Pill Badge (Portrait Hero)",
        "bg_type": "color",
        "bg_color": [0.03, 0.035, 0.045, 1.0],
        "card_asset": "card_trump_cyan_glow.png",
        "card_pos": [960.0, 480.0],
        "card_size": [720.0, 780.0],
        "card_3d": True,
        "card_tracks": [
            {"property": "position_y", "easing": "out_cubic", "keyframes": [{"frame": 0, "value": -40.0}, {"frame": 45, "value": 0.0}, {"frame": 89, "value": 0.0}]},
            {"property": "position_z", "easing": "out_cubic", "keyframes": [{"frame": 0, "value": 180.0}, {"frame": 45, "value": 0.0}, {"frame": 89, "value": 0.0}]},
            {"property": "rotation_y", "easing": "out_cubic", "keyframes": [{"frame": 0, "value": 24.0}, {"frame": 45, "value": 14.0}, {"frame": 89, "value": 14.0}]},
            {"property": "rotation_x", "easing": "out_cubic", "keyframes": [{"frame": 0, "value": 18.0}, {"frame": 45, "value": 10.0}, {"frame": 89, "value": 10.0}]},
            {"property": "scale", "easing": "out_cubic", "keyframes": [{"frame": 0, "value": 0.9}, {"frame": 45, "value": 1.0}, {"frame": 89, "value": 1.015}]},
            {"property": "opacity", "easing": "out_cubic", "keyframes": [{"frame": 0, "value": 0.0}, {"frame": 18, "value": 1.0}, {"frame": 89, "value": 1.0}]}
        ],
        "pill_asset": "pill_badge_cyan_electric.png",
        "pill_pos": [960.0, 895.0],
        "pill_size": [720.0, 180.0],
        "pill_tracks": [
            {"property": "scale_x", "easing": "out_back", "keyframes": [{"frame": 12, "value": 0.1}, {"frame": 38, "value": 1.05}, {"frame": 50, "value": 1.0}, {"frame": 89, "value": 1.0}]},
            {"property": "opacity", "easing": "out_cubic", "keyframes": [{"frame": 12, "value": 0.0}, {"frame": 26, "value": 1.0}, {"frame": 89, "value": 1.0}]}
        ],
        "title": "DONALD J. TRUMP",
        "title_pos": [960.0, 895.0],
        "title_size": [600.0, 60.0],
        "title_color": "#FFFFFF",
        "title_font_size": 40.0,
        "title_tracks": [
            {"property": "opacity", "easing": "out_cubic", "keyframes": [{"frame": 18, "value": 0.0}, {"frame": 34, "value": 1.0}, {"frame": 89, "value": 1.0}]},
            {"property": "scale", "easing": "out_back", "keyframes": [{"frame": 18, "value": 0.85}, {"frame": 42, "value": 1.02}, {"frame": 52, "value": 1.0}, {"frame": 89, "value": 1.0}]}
        ]
    },

    # ---------------------------------------------------------------------
    # RECIPE 3: Exact Replica of Ref 2 - Curved CRT Widescreen Screen in Studio Light
    # ---------------------------------------------------------------------
    {
        "id": "modern_entity_03_curved_crt_sixers_studio",
        "family": "Modern Entities With Text",
        "style_name": "Curved Widescreen CRT Screen + Studio Vignette (Sixers #23)",
        "bg_type": "image",
        "bg_asset": "studio_light_bg.png",
        "bg_pos": [960.0, 540.0],
        "bg_size": [1920.0, 1080.0],
        "screen_asset": "curved_screen_sixers.png",
        "screen_pos": [960.0, 485.0],
        "screen_size": [1560.0, 950.0],
        "screen_3d": True,
        "screen_tracks": [
            {"property": "scale", "easing": "out_cubic", "keyframes": [{"frame": 0, "value": 0.90}, {"frame": 45, "value": 1.0}, {"frame": 89, "value": 1.018}]},
            {"property": "position_z", "easing": "out_cubic", "keyframes": [{"frame": 0, "value": 140.0}, {"frame": 45, "value": 0.0}, {"frame": 89, "value": 0.0}]},
            {"property": "position_y", "easing": "out_cubic", "keyframes": [{"frame": 0, "value": 30.0}, {"frame": 45, "value": 0.0}, {"frame": 89, "value": 0.0}]},
            {"property": "opacity", "easing": "out_cubic", "keyframes": [{"frame": 0, "value": 0.0}, {"frame": 18, "value": 1.0}, {"frame": 89, "value": 1.0}]}
        ],
        "title": "WORLD B. FREE",
        "subtitle": "PHILADELPHIA 76ERS • #23",
        "title_pos": [960.0, 975.0],
        "sub_pos": [960.0, 1025.0],
        "title_color": "#12151D",
        "sub_color": "#5A606E",
        "title_font_size": 42.0,
        "sub_font_size": 22.0,
        "text_tracks": [
            {"property": "position_y", "easing": "out_cubic", "keyframes": [{"frame": 16, "value": 24.0}, {"frame": 48, "value": 0.0}, {"frame": 89, "value": 0.0}]},
            {"property": "opacity", "easing": "out_cubic", "keyframes": [{"frame": 16, "value": 0.0}, {"frame": 34, "value": 1.0}, {"frame": 89, "value": 1.0}]}
        ]
    },

    # ---------------------------------------------------------------------
    # RECIPE 4: Curved Widescreen CRT in Dark Studio with Gold Glow
    # ---------------------------------------------------------------------
    {
        "id": "modern_entity_04_curved_crt_portrait_dark",
        "family": "Modern Entities With Text",
        "style_name": "Curved CRT Screen Dark Cinematic Studio (Steve Jobs)",
        "bg_type": "image",
        "bg_asset": "studio_dark_bg.png",
        "bg_pos": [960.0, 540.0],
        "bg_size": [1920.0, 1080.0],
        "screen_asset": "curved_screen_steve.png",
        "screen_pos": [960.0, 485.0],
        "screen_size": [1560.0, 950.0],
        "screen_3d": True,
        "screen_tracks": [
            {"property": "scale", "easing": "out_cubic", "keyframes": [{"frame": 0, "value": 0.91}, {"frame": 48, "value": 1.0}, {"frame": 89, "value": 1.02}]},
            {"property": "position_z", "easing": "out_cubic", "keyframes": [{"frame": 0, "value": 150.0}, {"frame": 48, "value": 0.0}, {"frame": 89, "value": 0.0}]},
            {"property": "opacity", "easing": "out_cubic", "keyframes": [{"frame": 0, "value": 0.0}, {"frame": 18, "value": 1.0}, {"frame": 89, "value": 1.0}]}
        ],
        "title": "STEVE JOBS",
        "subtitle": "CHIEF EXECUTIVE OFFICER • APPLE",
        "title_pos": [960.0, 975.0],
        "sub_pos": [960.0, 1025.0],
        "title_color": "#F2F4F8",
        "sub_color": "#FFC832",
        "title_font_size": 42.0,
        "sub_font_size": 22.0,
        "text_tracks": [
            {"property": "position_y", "easing": "out_cubic", "keyframes": [{"frame": 18, "value": 24.0}, {"frame": 50, "value": 0.0}, {"frame": 89, "value": 0.0}]},
            {"property": "opacity", "easing": "out_cubic", "keyframes": [{"frame": 18, "value": 0.0}, {"frame": 36, "value": 1.0}, {"frame": 89, "value": 1.0}]}
        ]
    },

    # ---------------------------------------------------------------------
    # RECIPE 5: Warm Gold Neon Glass Card + Gold Pill Badge
    # ---------------------------------------------------------------------
    {
        "id": "modern_entity_05_neon_card_gold",
        "family": "Modern Entities With Text",
        "style_name": "Neon 3D Glass Card + Warm Amber Gold Pill Badge",
        "bg_type": "color",
        "bg_color": [0.035, 0.03, 0.025, 1.0],
        "card_asset": "card_steve_gold_glow.png",
        "card_pos": [960.0, 480.0],
        "card_size": [720.0, 780.0],
        "card_3d": True,
        "card_tracks": [
            {"property": "position_y", "easing": "out_cubic", "keyframes": [{"frame": 0, "value": -40.0}, {"frame": 45, "value": 0.0}, {"frame": 89, "value": 0.0}]},
            {"property": "position_z", "easing": "out_cubic", "keyframes": [{"frame": 0, "value": 160.0}, {"frame": 45, "value": 0.0}, {"frame": 89, "value": 0.0}]},
            {"property": "rotation_y", "easing": "out_cubic", "keyframes": [{"frame": 0, "value": -22.0}, {"frame": 45, "value": -12.0}, {"frame": 89, "value": -12.0}]},
            {"property": "rotation_x", "easing": "out_cubic", "keyframes": [{"frame": 0, "value": 18.0}, {"frame": 45, "value": 10.0}, {"frame": 89, "value": 10.0}]},
            {"property": "scale", "easing": "out_cubic", "keyframes": [{"frame": 0, "value": 0.90}, {"frame": 45, "value": 1.0}, {"frame": 89, "value": 1.015}]},
            {"property": "opacity", "easing": "out_cubic", "keyframes": [{"frame": 0, "value": 0.0}, {"frame": 18, "value": 1.0}, {"frame": 89, "value": 1.0}]}
        ],
        "pill_asset": "pill_badge_gold.png",
        "pill_pos": [960.0, 895.0],
        "pill_size": [720.0, 180.0],
        "pill_tracks": [
            {"property": "scale_x", "easing": "out_back", "keyframes": [{"frame": 12, "value": 0.1}, {"frame": 38, "value": 1.05}, {"frame": 50, "value": 1.0}, {"frame": 89, "value": 1.0}]},
            {"property": "opacity", "easing": "out_cubic", "keyframes": [{"frame": 12, "value": 0.0}, {"frame": 26, "value": 1.0}, {"frame": 89, "value": 1.0}]}
        ],
        "title": "STEVE JOBS",
        "title_pos": [960.0, 895.0],
        "title_size": [600.0, 60.0],
        "title_color": "#FFFFFF",
        "title_font_size": 42.0,
        "title_tracks": [
            {"property": "opacity", "easing": "out_cubic", "keyframes": [{"frame": 18, "value": 0.0}, {"frame": 34, "value": 1.0}, {"frame": 89, "value": 1.0}]},
            {"property": "scale", "easing": "out_back", "keyframes": [{"frame": 18, "value": 0.85}, {"frame": 42, "value": 1.02}, {"frame": 52, "value": 1.0}, {"frame": 89, "value": 1.0}]}
        ]
    }
]


def compile_plan(recipe):
    video_path = str(VIDEOS_DIR / f"{recipe['id']}.mp4")
    layers = []

    # 1. Background Layer
    if recipe["bg_type"] == "color":
        layers.append({
            "id": "bg_color",
            "type": "color",
            "color": recipe["bg_color"],
            "start_frame": 0,
            "duration_frames": 90
        })
    elif recipe["bg_type"] == "image":
        layers.append({
            "id": "bg_image",
            "type": "image",
            "asset": str((ASSETS_DIR / recipe["bg_asset"]).relative_to(BASE_DIR)),
            "position": recipe["bg_pos"],
            "size": recipe["bg_size"],
            "fit": "cover",
            "start_frame": 0,
            "duration_frames": 90
        })

    # 2. Main Visual (Neon Card or Curved Screen)
    if "card_asset" in recipe:
        card_layer = {
            "id": "neon_card",
            "type": "image",
            "asset": str((ASSETS_DIR / recipe["card_asset"]).relative_to(BASE_DIR)),
            "position": recipe["card_pos"],
            "size": recipe["card_size"],
            "fit": "contain",
            "enable_3d": recipe.get("card_3d", True),
            "start_frame": 0,
            "duration_frames": 90,
            "animation": {
                "tracks": recipe["card_tracks"]
            }
        }
        layers.append(card_layer)
    elif "screen_asset" in recipe:
        screen_layer = {
            "id": "curved_crt_screen",
            "type": "image",
            "asset": str((ASSETS_DIR / recipe["screen_asset"]).relative_to(BASE_DIR)),
            "position": recipe["screen_pos"],
            "size": recipe["screen_size"],
            "fit": "contain",
            "enable_3d": recipe.get("screen_3d", True),
            "start_frame": 0,
            "duration_frames": 90,
            "animation": {
                "tracks": recipe["screen_tracks"]
            }
        }
        layers.append(screen_layer)

    # 3. Pill Badge (if present)
    if "pill_asset" in recipe:
        pill_layer = {
            "id": "neon_pill_badge",
            "type": "image",
            "asset": str((ASSETS_DIR / recipe["pill_asset"]).relative_to(BASE_DIR)),
            "position": recipe["pill_pos"],
            "size": recipe["pill_size"],
            "fit": "contain",
            "enable_3d": True,
            "start_frame": 0,
            "duration_frames": 90,
            "animation": {
                "tracks": recipe["pill_tracks"]
            }
        }
        layers.append(pill_layer)

    # 4. Text Title Layer
    title_layer = {
        "id": "title_text",
        "type": "text",
        "text": recipe["title"],
        "size": recipe.get("title_size", [1000.0, 70.0]),
        "position": recipe["title_pos"],
        "style": {
            "font": FONT_BOLD,
            "font_size": recipe["title_font_size"],
            "fill": recipe["title_color"]
        },
        "start_frame": 0,
        "duration_frames": 90
    }
    if "title_tracks" in recipe:
        title_layer["animation"] = {"tracks": recipe["title_tracks"]}
    elif "text_tracks" in recipe:
        title_layer["animation"] = {"tracks": recipe["text_tracks"]}
    layers.append(title_layer)

    # 5. Subtitle Layer (if present)
    if "subtitle" in recipe:
        sub_layer = {
            "id": "subtitle_text",
            "type": "text",
            "text": recipe["subtitle"],
            "size": [1000.0, 45.0],
            "position": recipe["sub_pos"],
            "style": {
                "font": FONT_BOLD,
                "font_size": recipe["sub_font_size"],
                "fill": recipe["sub_color"]
            },
            "start_frame": 0,
            "duration_frames": 90
        }
        if "text_tracks" in recipe:
            sub_layer["animation"] = {"tracks": recipe["text_tracks"]}
        layers.append(sub_layer)

    plan = {
        "schema": "chronon.render-plan.v2",
        "version": 2,
        "job_id": recipe["id"],
        "canvas": {
            "width": 1920,
            "height": 1080,
            "fps_num": 30,
            "fps_den": 1,
            "duration_frames": 90
        },
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
            "path": video_path,
            "format": "mp4",
            "codec": "h264"
        }
    }
    return plan


# =========================================================================
# 5. EMIT PLANS & RENDER PARALLEL GPU
# =========================================================================

plans = []
print("--- Compiling Render Plans for Modern Entities With Text ---")
for recipe in recipes:
    plan = compile_plan(recipe)
    plan_file = PLANS_DIR / f"{recipe['id']}.plan.json"
    with open(plan_file, "w") as f:
        json.dump(plan, f, indent=2)
    plans.append((recipe["id"], plan_file, plan["output"]["path"]))
    print(f"Generated Plan: {recipe['id']}")


def render_single_plan(plan_tuple):
    item_id, plan_path, video_path = plan_tuple
    frame_path = str(FRAMES_DIR / f"{item_id}_frame.png")
    
    cmd = [
        str(CLI_PATH), "render",
        "--plan", str(plan_path),
        "--assets-root", str(BASE_DIR)
    ]
    t0 = time.time()
    print(f"[{item_id}] Rendering on Chronon GPU...")
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    dt = time.time() - t0
    
    if proc.returncode != 0:
        print(f"[{item_id}] FAILED in {dt:.1f}s:\n{proc.stdout[-500:]}")
        return False, item_id, dt
    
    # Extract frame at 1.8s (frame 54, fully settled)
    ff_cmd = [
        "ffmpeg", "-y", "-ss", "00:00:01.800", "-i", video_path,
        "-vframes", "1", frame_path
    ]
    subprocess.run(ff_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    print(f"[{item_id}] PASSED in {dt:.1f}s -> {video_path}")
    return True, item_id, dt

print(f"\n--- Starting Parallel Render of {len(plans)} Modern Entity Plans ---")
with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
    render_results = list(executor.map(render_single_plan, plans))

print("\n--- Render Results Summary ---")
for ok, item_id, dt in render_results:
    st = "OK" if ok else "FAIL"
    print(f" - {item_id}: {st} ({dt:.1f}s)")


# =========================================================================
# 6. UPLOAD TO GOOGLE DRIVE VIA RENDERIGEN DRIVE-UPLOAD
# =========================================================================

print(f"\n--- Uploading All Rendered Videos to Google Drive Folder {FOLDER_ID} ---")
video_files = sorted(list(VIDEOS_DIR.glob("*.mp4")))
upload_results = []

def upload_single_file(vpath):
    fname = vpath.name
    cmd = [
        str(UPLOADER),
        "-credentials", CREDS,
        "-token", TOKEN,
        "-folder", FOLDER_ID,
        "-file", str(vpath),
        "-name", fname
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    out = proc.stdout.strip()
    if proc.returncode == 0:
        drive_id = ""
        link = ""
        sha256 = ""
        bytes_sz = 0
        for token in out.split():
            if token.startswith("id="):
                drive_id = token.split("=", 1)[1]
            elif token.startswith("link="):
                link = token.split("=", 1)[1]
            elif token.startswith("sha256="):
                sha256 = token.split("=", 1)[1]
            elif token.startswith("bytes="):
                try:
                    bytes_sz = int(token.split("=", 1)[1])
                except:
                    pass
        print(f" [UPLOAD PASS] {fname} -> {drive_id} ({link})", flush=True)
        return {
            "name": fname,
            "status": "SUCCESS",
            "drive_id": drive_id,
            "link": link,
            "sha256": sha256,
            "bytes": bytes_sz
        }
    else:
        err = proc.stderr.strip()
        print(f" [UPLOAD FAIL] {fname}: {err}", flush=True)
        return {
            "name": fname,
            "status": "FAIL",
            "error": err
        }

with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
    upload_results = list(executor.map(upload_single_file, video_files))

manifest = {
    "family": "Modern Entities With Text",
    "destination_folder": FOLDER_ID,
    "total_files": len(upload_results),
    "success_count": sum(1 for r in upload_results if r.get("status") == "SUCCESS"),
    "files": upload_results
}

manifest_path = OUT_DIR / "modern_entities_drive_manifest.json"
with open(manifest_path, "w") as f:
    json.dump(manifest, f, indent=2)

print(f"\n--- Drive Upload Finished: {manifest['success_count']} / {manifest['total_files']} Successful ---")
print(f"Manifest written to: {manifest_path}")
