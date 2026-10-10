#!/usr/bin/env python3
"""Generate and render the 1950 vintage camera story animation.

Choreography:
1. Vintage image rises from bottom to center.
2. Camera executes a punchy push-zoom (dolly push + FOV tightening) on the image.
3. Wavy dashed line appears and guides camera travel across 3D space.
4. Camera lands on new focal center where '1950' appears in modern short-phrase typography.
"""

import json
import math
import os
import subprocess
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parents[2]
WORKSPACE = ROOT.parent
OUT_DIR = ROOT / "out/camera_1950_story"
ASSETS_DIR = OUT_DIR / "assets"
CLI = WORKSPACE / "Chronon3d/build/chronon/linux-video-fast-dev/apps/chronon3d_cli/chronon3d_cli"

WIDTH, HEIGHT, FPS = 1920, 1080, 30
TOTAL_FRAMES = 210  # 7.0 seconds

def ensure_dirs():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)

def generate_vintage_photo():
    """Create an archival vintage photograph card."""
    w, h = 860, 580
    border = 28
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Cream white card border with subtle rounded edge
    draw.rounded_rectangle([0, 0, w - 1, h - 1], radius=16, fill=(244, 241, 234, 255), outline=(210, 204, 192, 255), width=2)

    # Inner photo area
    pw = w - border * 2
    ph = h - border * 2 - 20
    photo = Image.new("RGBA", (pw, ph), (30, 28, 26, 255))
    pdraw = ImageDraw.Draw(photo)

    # Draw archival architectural skyline / documentary scene in duotone sepia
    for y in range(ph):
        ratio = y / ph
        r = int(24 + ratio * 45)
        g = int(22 + ratio * 38)
        b = int(20 + ratio * 32)
        pdraw.line([(0, y), (pw, y)], fill=(r, g, b, 255))

    # Add geometric vintage architectural silhouettes
    # Buildings
    buildings = [
        (40, 360, 120, ph), (140, 280, 230, ph), (220, 320, 300, ph),
        (280, 210, 360, ph), (350, 160, 410, ph),  # spire
        (400, 260, 490, ph), (480, 300, 580, ph), (570, 230, 670, ph),
        (660, 310, 750, ph)
    ]
    for (x1, y1, x2, y2) in buildings:
        pdraw.rectangle([x1, y1, x2, y2], fill=(16, 14, 12, 255))
        # Warm window grid dots
        for wx in range(x1 + 12, x2 - 12, 16):
            for wy in range(y1 + 18, y2 - 20, 22):
                pdraw.rectangle([wx, wy, wx + 6, wy + 10], fill=(195, 165, 120, 160))

    # Vignette shadow around edges
    overlay = Image.new("RGBA", (pw, ph), (0, 0, 0, 0))
    ovdraw = ImageDraw.Draw(overlay)
    for i in range(40):
        alpha = int(80 * (1.0 - i / 40.0))
        ovdraw.rectangle([i, i, pw - 1 - i, ph - 1 - i], outline=(10, 8, 6, alpha))
    photo = Image.alpha_composite(photo, overlay)

    img.paste(photo, (border, border))

    # Fine print caption on bottom border
    cdraw = ImageDraw.Draw(img)
    cdraw.text((border + 6, h - border - 8), "ARCHIVIO STORICO - MID-CENTURY URBAN HORIZON", fill=(120, 115, 105, 255))

    out_path = ASSETS_DIR / "vintage_photo_1950.png"
    img.save(out_path)
    print(f"Generated vintage photo: {out_path}")
    return out_path

def generate_wavy_dashed_line():
    """Create a crisp wavy dashed line connector."""
    w, h = 1400, 400
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    points = []
    # Generate smooth sinusoidal wavy spline
    total_steps = 700
    for i in range(total_steps):
        t = i / float(total_steps - 1)
        x = 40 + t * (w - 80)
        # S-curve oscillation
        y = h / 2.0 + math.sin(t * math.pi * 3.2) * 110.0
        points.append((x, y))

    # Draw dashed pattern
    dash_len = 16
    gap_len = 12
    cycle = dash_len + gap_len

    dist = 0.0
    for i in range(len(points) - 1):
        p1 = points[i]
        p2 = points[i + 1]
        dx = p2[0] - p1[0]
        dy = p2[1] - p1[1]
        seg_len = math.hypot(dx, dy)
        dist += seg_len

        # Check if in dash phase
        in_cycle = dist % cycle
        if in_cycle < dash_len:
            # Draw segment with anti-aliasing width
            draw.line([p1, p2], fill=(242, 240, 232, 230), width=5)

    # Start node (small anchor ring)
    sx, sy = points[0]
    draw.ellipse([sx - 10, sy - 10, sx + 10, sy + 10], fill=(242, 240, 232, 255), outline=(218, 165, 32, 255), width=3)

    # End node (target beacon ring)
    ex, ey = points[-1]
    draw.ellipse([ex - 14, ey - 14, ex + 14, ey + 14], fill=(218, 165, 32, 255), outline=(242, 240, 232, 255), width=3)
    draw.ellipse([ex - 6, ey - 6, ex + 6, ey + 6], fill=(255, 255, 255, 255))

    out_path = ASSETS_DIR / "wavy_dashed_line.png"
    img.save(out_path)
    print(f"Generated wavy dashed line: {out_path}")
    return out_path

def build_render_plan(photo_rel, line_rel):
    """Build chronon.render-plan.v3 with exact camera and layer tracks."""
    # Chronon coordinate system:
    # Camera in canvas coords has center (0,0), -Z is forward.
    # Subject 1 (photo): position [0, 0, 0] (center of canvas in 3D)
    # Subject 2 (1950 date): position [1500, 0, 0] (offset to the right)
    # Wavy line connector: between [0, 0] and [1500, 0]

    # Camera choreography:
    # Frame 0..40: Camera at rest (0, 0, -920). Photo rises to center.
    # Frame 40..80: Push zoom onto photo: Z moves -920 -> -540, FOV tightens 52 -> 43.
    # Frame 80..135: Wavy line appears. Camera executes an editorial ArcCarry transition:
    #                X bows out to +190 and returns to 0.
    #                Y crests by -45 and returns to 0.
    #                Z pulls back from -540 to -880.
    #                Yaw (rot_y) banks smoothly by +9.5 deg at the apex.
    # Frame 135..210: Camera lands squarely on (0, 0, -880). '1950' appears centered.

    cam_pos_x = []
    cam_pos_y = []
    cam_pos_z = []
    cam_rot_y = []
    cam_fov   = []

    def ease_in_out_cubic(t):
        return 4.0 * t * t * t if t < 0.5 else 1.0 - math.pow(-2.0 * t + 2.0, 3) / 2.0

    for f in range(TOTAL_FRAMES):
        if f <= 40:
            x = 0.0
            y = 0.0
            z = -920.0
            ry = 0.0
            fov = 52.0
        elif f <= 80:
            # Push Zoom on photo
            t = (f - 40) / 40.0
            e = ease_in_out_cubic(t)
            x = 0.0
            y = 0.0
            z = -920.0 + e * 380.0  # -920 -> -540
            ry = 0.0
            fov = 52.0 - e * 9.0    # 52 -> 43
        elif f <= 135:
            # ArcCarry camera transition
            t = (f - 80) / 55.0
            e = ease_in_out_cubic(t)
            # Lateral bow that swings out and returns
            bow = math.sin(e * math.pi)
            x = bow * 220.0
            y = -bow * 50.0
            z = -540.0 - e * 340.0   # -540 -> -880
            ry = bow * 9.5          # Banking yaw
            fov = 43.0 + e * 7.0    # 43 -> 50
        else:
            # Hold centered on 1950
            x = 0.0
            y = 0.0
            z = -880.0
            ry = 0.0
            fov = 50.0

        cam_pos_x.append(x)
        cam_pos_y.append(y)
        cam_pos_z.append(z)
        cam_rot_y.append(ry)
        cam_fov.append(fov)

    # Tracks
    def make_track(prop, vals):
        return {
            "property": prop,
            "easing": "linear",
            "keyframes": [{"frame": i, "value": round(v, 4)} for i, v in enumerate(vals)]
        }

    camera_anim = {
        "tracks": [
            make_track("camera_position_x", cam_pos_x),
            make_track("camera_position_y", cam_pos_y),
            make_track("camera_position_z", cam_pos_z),
            make_track("camera_rotation_y", cam_rot_y),
            make_track("camera_fov_deg", cam_fov)
        ]
    }

    # Background layer
    bg_layer = {
        "id": "bg_dark",
        "type": "color",
        "color": [0.038, 0.042, 0.048, 1.0],
        "size": [WIDTH, HEIGHT],
        "screen_space": True,
        "start_frame": 0,
        "duration_frames": TOTAL_FRAMES
    }

    # Photo layer: starts below screen, rises to center by frame 35
    photo_layer = {
        "id": "vintage_photo",
        "type": "image",
        "asset": str(photo_rel),
        "size": [860, 580],
        "position": [960, 540, 0],
        "fit": "contain",
        "start_frame": 0,
        "duration_frames": 95,
        "enable_3d": True,
        "animation": {
            "tracks": [
                {
                    "property": "position_y",
                    "easing": "out_cubic",
                    "keyframes": [
                        {"frame": 0, "value": 550.0},
                        {"frame": 35, "value": 0.0}
                    ]
                },
                {
                    "property": "opacity",
                    "easing": "linear",
                    "keyframes": [
                        {"frame": 0, "value": 0.0},
                        {"frame": 14, "value": 1.0},
                        {"frame": 75, "value": 1.0},
                        {"frame": 90, "value": 0.0}
                    ]
                }
            ]
        }
    }

    # Wavy dashed line connector: spans across center [960, 540]
    line_layer = {
        "id": "wavy_connector",
        "type": "image",
        "asset": str(line_rel),
        "size": [1280, 360],
        "position": [960, 540, 0],
        "fit": "contain",
        "start_frame": 75,
        "duration_frames": 65,
        "enable_3d": True,
        "animation": {
            "tracks": [
                {
                    "property": "opacity",
                    "easing": "out_cubic",
                    "keyframes": [
                        {"frame": 0, "value": 0.0},
                        {"frame": 12, "value": 1.0},
                        {"frame": 48, "value": 1.0},
                        {"frame": 60, "value": 0.0}
                    ]
                }
            ]
        }
    }

    # 1950 Date layer: centered at [960, 520, 0]
    date_layer = {
        "id": "date_1950",
        "type": "text",
        "text": "1950",
        "size": [700, 220],
        "position": [960, 510, 0],
        "start_frame": 120,
        "duration_frames": TOTAL_FRAMES - 120,
        "enable_3d": True,
        "style": {
            "font": "Chronon3d/assets/fonts/Inter-Bold.ttf",
            "font_size": 160,
            "fill": "#F2F0E8",
            "fit_mode": "shrink_only",
            "min_font_size": 80,
            "max_font_size": 160
        },
        "animation": {
            "tracks": [
                {
                    "property": "opacity",
                    "easing": "out_cubic",
                    "keyframes": [
                        {"frame": 0, "value": 0.0},
                        {"frame": 20, "value": 1.0}
                    ]
                },
                {
                    "property": "scale",
                    "easing": "out_cubic",
                    "keyframes": [
                        {"frame": 0, "value": 0.82},
                        {"frame": 24, "value": 1.0}
                    ]
                }
            ]
        }
    }

    # Modern short phrase subtitle pill / rule below the date
    subtitle_layer = {
        "id": "date_subtitle",
        "type": "text",
        "text": "L'INIZIO DELLA NUOVA ERA",
        "size": [800, 50],
        "position": [960, 635, 0],
        "start_frame": 130,
        "duration_frames": TOTAL_FRAMES - 130,
        "enable_3d": True,
        "style": {
            "font": "Chronon3d/assets/fonts/Inter-Bold.ttf",
            "font_size": 28,
            "fill": "#E5C378",
            "fit_mode": "shrink_only",
            "min_font_size": 18,
            "max_font_size": 28
        },
        "animation": {
            "tracks": [
                {
                    "property": "opacity",
                    "easing": "out_cubic",
                    "keyframes": [
                        {"frame": 0, "value": 0.0},
                        {"frame": 20, "value": 1.0}
                    ]
                }
            ]
        }
    }

    # Gold accent line under the subtitle
    rule_layer = {
        "id": "accent_rule",
        "type": "shape",
        "size": [180, 4],
        "position": [960, 675, 0],
        "start_frame": 134,
        "duration_frames": TOTAL_FRAMES - 134,
        "enable_3d": True,
        "shape": {
            "type": "rounded_rect",
            "radius": 2,
            "fill": [0.898, 0.765, 0.471, 0.9]
        },
        "animation": {
            "tracks": [
                {
                    "property": "scale_x",
                    "easing": "out_cubic",
                    "keyframes": [
                        {"frame": 0, "value": 0.0},
                        {"frame": 22, "value": 1.0}
                    ]
                }
            ]
        }
    }

    plan = {
        "schema": "chronon.render-plan.v3",
        "version": 3,
        "job_id": "chronon_1950_camera_story_v1",
        "canvas": {
            "width": WIDTH,
            "height": HEIGHT,
            "fps_num": FPS,
            "fps_den": 1,
            "duration_frames": TOTAL_FRAMES
        },
        "camera": {
            "type": "perspective",
            "position": [cam_pos_x[0], cam_pos_y[0], cam_pos_z[0]],
            "rotation_deg": [0, cam_rot_y[0], 0],
            "fov_deg": cam_fov[0],
            "near": 1,
            "far": 10000,
            "zoom": 1
        },
        "camera_animation": camera_anim,
        "layers": [
            bg_layer,
            photo_layer,
            line_layer,
            date_layer,
            subtitle_layer,
            rule_layer
        ],
        "output": {
            "path": "camera_1950_story.mp4",
            "format": "mp4",
            "codec": "h264"
        }
    }

    plan_path = OUT_DIR / "camera_1950_story.plan.json"
    with open(plan_path, "w") as f:
        json.dump(plan, f, indent=2)
    print(f"Generated render plan: {plan_path}")
    return plan_path

def main():
    ensure_dirs()
    photo_path = generate_vintage_photo()
    line_path = generate_wavy_dashed_line()

    # Paths relative to WORKSPACE root
    photo_rel = os.path.relpath(photo_path, WORKSPACE)
    line_rel = os.path.relpath(line_path, WORKSPACE)

    plan_path = build_render_plan(photo_rel, line_rel)

    out_mp4 = OUT_DIR / "camera_1950_story.mp4"
    cmd = [
        str(CLI), "render",
        "--plan", str(plan_path),
        "--assets-root", str(WORKSPACE),
        "-o", str(out_mp4)
    ]
    print("Executing render command:")
    print(" ".join(cmd))
    subprocess.check_call(cmd)
    print(f"\nSUCCESS! Rendered video saved to: {out_mp4}")

if __name__ == "__main__":
    main()
