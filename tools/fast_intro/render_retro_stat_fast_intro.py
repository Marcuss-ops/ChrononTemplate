"""
ChrononTemplate - Retro Stat Fast Intro Render Pipeline
Renders the high-fidelity 5.77s Fast Intro (1920x1080 @ 30fps) with:
1. Camera-ring background: geometric gold/red ring tunnel the camera pulls
   back through (more rings enter the frame over time), soft-focused.
2. Depth-of-Field defocus pulses on the title/number and collage transitions.
3. Heavy rounded typography with dual 3D shadows and a fine mesh texture.
4. Crash-zoom statistic that crosses the frame as a blurred white mass.
5. Hero collage entering from an extreme close-up pull-back at 88% width.
6. Closing "LOONEY TUNES" title rising from below at the very end.
7. Synchronized AAC audio track
"""

import os
import math
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import subprocess

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "..", ".."))

WIDTH = 1920
HEIGHT = 1080
FPS = 30
TOTAL_FRAMES = 173  # 5.766s @ 30fps

ARTIFACTS_DIR = os.path.join(TEMPLATE_ROOT, "artifacts", "retro_stat_fast_intro")
FRAMES_DIR = os.path.join(ARTIFACTS_DIR, "frames")
OUTPUT_MP4 = os.path.join(ARTIFACTS_DIR, "retro_stat_fast_intro.mp4")
WORKSPACE_MP4 = os.path.abspath(os.path.join(TEMPLATE_ROOT, "..", "retro_stat_fast_intro.mp4"))

COLLAGE_PATH = os.path.join(TEMPLATE_ROOT, "assets", "images", "retro_collage.png")
FONT_PATH = os.path.join(TEMPLATE_ROOT, "assets", "fonts", "Inter-Black.ttf")
AUDIO_PATH = os.path.join(TEMPLATE_ROOT, "assets", "audio", "retro_stat_audio.aac")

os.makedirs(FRAMES_DIR, exist_ok=True)

cx = WIDTH // 2
cy = HEIGHT // 2 - 15

# -----------------------------------------------------------------------------
# 1. Camera-ring background (Looney Tunes tunnel, soft-focused)
# -----------------------------------------------------------------------------
print("[ChrononTemplate] Building camera-ring background...")

y_coords, x_coords = np.ogrid[:HEIGHT, :WIDTH]
dy = (y_coords - cy) / 0.96
dx = (x_coords - cx)
dist = np.sqrt(dx**2 + dy**2)

# The ring tunnel is geometric (each ring 1.38x the previous) and the camera
# pulls back through it, so more rings enter the frame as the video proceeds.
RING_ZOOM_KEYS = [(0, 2.55), (60, 1.72), (110, 1.16), (150, 1.0), (172, 0.94)]

RIM_COLOR = np.array([238, 148, 32], dtype=np.float32)    # orange-gold ring rim
BAND_COLOR = np.array([108, 22, 5], dtype=np.float32)     # deep red ring body


def build_background(ring_zoom):
    q = np.maximum(dist / (620.0 * ring_zoom), 1e-4)
    phase = np.log(q / 0.32) / np.log(1.38)
    band = 0.5 + 0.5 * np.cos(phase * 2.0 * np.pi)
    band = band ** 1.25
    # The ring modulation fades into the luminous gold core pool.
    ring_amp = np.clip((q - 0.22) / 0.45, 0.0, 1.0) ** 1.4
    # Radial luminance: bright gold pool at the core, deep red at the edges.
    r = dist / (1150.0 * ring_zoom)
    core = np.interp(r, [0.0, 0.22, 0.45, 0.7, 1.0, 1.3],
                        [1.18, 1.08, 0.92, 0.72, 0.5, 0.34])
    mix = (band * ring_amp)[..., None]
    bg = RIM_COLOR + (BAND_COLOR - RIM_COLOR) * mix
    return np.clip(bg * core[..., None], 0, 255)


# Very fine mesh texture, applied globally at the end (as in the reference).
mesh_x = (np.arange(WIDTH) % 5) == 0
mesh_y = (np.arange(HEIGHT) % 5) == 0
MESH_MASK = np.maximum(mesh_x[None, :], mesh_y[:, None]).astype(np.float32) * 0.055

# -----------------------------------------------------------------------------
# 2. Typography Assets Generation (dual 3D shadows, smaller 'M' on baseline)
# -----------------------------------------------------------------------------
print("[ChrononTemplate] Rasterizing typography with dual 3D shadows...")

def render_styled_text(elements, base_font_size=380, spacing=25):
    fonts = [ImageFont.truetype(FONT_PATH, int(base_font_size * mult)) for _, mult in elements]

    bboxes = []
    widths = []
    heights = []
    for (text, _), font in zip(elements, fonts):
        bbox = font.getbbox(text)
        bboxes.append(bbox)
        widths.append(bbox[2] - bbox[0])
        heights.append(bbox[3] - bbox[1])

    total_w = sum(widths) + spacing * (len(elements) - 1)
    max_h = max(heights)

    pad = 80
    w = total_w + pad * 2
    h = max_h + pad * 2
    baseline_y = pad + max_h

    # 1. Base text layer (white)
    text_img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(text_img)
    cur_x = pad
    for (text, _), font, bbox in zip(elements, fonts, bboxes):
        elem_h = bbox[3] - bbox[1]
        elem_y = baseline_y - elem_h - bbox[1]
        draw.text((cur_x - bbox[0], elem_y), text, font=font, fill=(248, 246, 242, 255))
        cur_x += (bbox[2] - bbox[0]) + spacing

    # 2. Tight dark bevel / extrusion
    bevel_img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    bdraw = ImageDraw.Draw(bevel_img)
    cur_x = pad + 4
    for (text, _), font, bbox in zip(elements, fonts, bboxes):
        elem_h = bbox[3] - bbox[1]
        elem_y = baseline_y - elem_h - bbox[1] + 5
        bdraw.text((cur_x - bbox[0], elem_y), text, font=font, fill=(20, 4, 4, 230))
        cur_x += (bbox[2] - bbox[0]) + spacing
    bevel_img = bevel_img.filter(ImageFilter.GaussianBlur(radius=2.0))

    # 3. Deep soft drop shadow
    shadow_img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    sdraw = ImageDraw.Draw(shadow_img)
    cur_x = pad + 14
    for (text, _), font, bbox in zip(elements, fonts, bboxes):
        elem_h = bbox[3] - bbox[1]
        elem_y = baseline_y - elem_h - bbox[1] + 16
        sdraw.text((cur_x - bbox[0], elem_y), text, font=font, fill=(10, 2, 2, 210))
        cur_x += (bbox[2] - bbox[0]) + spacing
    shadow_img = shadow_img.filter(ImageFilter.GaussianBlur(radius=14.0))

    composite = Image.alpha_composite(shadow_img, bevel_img)
    composite = Image.alpha_composite(composite, text_img)

    cbbox = composite.getbbox()
    return composite.crop(cbbox), (w // 2 - cbbox[0], h // 2 - cbbox[1])


def white_bbox_size(plate):
    alpha = np.array(plate.split()[3])
    ys, xs = np.where(alpha > 200)
    return int(xs.max() - xs.min()), int(ys.max() - ys.min())


plate_era, (era_ox, era_oy) = render_styled_text([("1990s", 1.0)], base_font_size=290)
plate_stat, (stat_ox, stat_oy) = render_styled_text([("37.7", 1.0), ("M", 0.78)], base_font_size=390, spacing=95)
plate_closing, _ = render_styled_text([("LOONEY TUNES", 1.0)], base_font_size=215, spacing=30)

# Self-calibration: the stat keys below are fractions of the canvas width that
# the *visible glyphs* must span, matching the reference measurements.
stat_white_w, stat_white_h = white_bbox_size(plate_stat)

# -----------------------------------------------------------------------------
# 3. Hero Character Ensemble (transparent cutout, integrated with the background)
# -----------------------------------------------------------------------------
print("[ChrononTemplate] Preparing transparent hero ensemble...")
collage_native = Image.open(COLLAGE_PATH).convert("RGBA")

target_collage_w = int(WIDTH * 0.88)
target_collage_h = int(target_collage_w * collage_native.height / collage_native.width)
collage_hero = collage_native.resize((target_collage_w, target_collage_h), Image.Resampling.LANCZOS)

# -----------------------------------------------------------------------------
# 4. Easing & keyframe tracks (mirroring the retro_stat_collage recipe)
# -----------------------------------------------------------------------------
def clamp01(t):
    return 0.0 if t < 0.0 else (1.0 if t > 1.0 else float(t))

def ease_out_cubic(t):
    t = clamp01(t)
    return 1.0 - math.pow(1.0 - t, 3)

def ease_in_cubic(t):
    t = clamp01(t)
    return math.pow(t, 3)

def ease_linear(t):
    return clamp01(t)

def track_value(keys, frame_idx, ease=ease_out_cubic):
    """Piecewise keyframe interpolation."""
    if frame_idx <= keys[0][0]:
        return keys[0][1]
    if frame_idx >= keys[-1][0]:
        return keys[-1][1]
    for (f0, v0), (f1, v1) in zip(keys, keys[1:]):
        if f0 <= frame_idx <= f1:
            t = (frame_idx - f0) / float(f1 - f0)
            return v0 + (v1 - v0) * ease(t)
    return keys[-1][1]

# Title: steady shot that defocuses and fades as the number crashes in.
ERA_SCALE_KEYS = [(0, 1.0), (24, 0.96), (38, 0.9), (48, 0.86)]
ERA_OPACITY_KEYS = [(0, 1.0), (36, 1.0), (45, 0.0)]
ERA_BLUR_KEYS = [(24, 0.0), (32, 1.5), (38, 5.0), (45, 9.0)]

# Statistic: crashes in from the right as a blurred white mass, stays gigantic
# ("37.7" alone fills the frame at 2.0s), fully legible at 2.75s (63% width),
# then lingers behind the collage until 4.2s.
STAT_WIDTH_KEYS = [(38, 3.4), (45, 2.75), (52, 2.3), (60, 1.6), (70, 1.1),
                   (82, 0.66), (105, 0.55), (120, 0.52), (126, 0.51)]
STAT_OPACITY_KEYS = [(38, 0.0), (39, 1.0), (82, 1.0), (100, 0.85), (116, 0.55), (126, 0.0)]
STAT_OFFSET_X_KEYS = [(38, 1.35), (42, 1.05), (45, 0.85), (52, 0.25), (62, 0.05), (75, 0.0)]
STAT_OFFSET_Y_KEYS = [(38, 0.1), (52, 0.03), (75, 0.0)]
STAT_BLUR_KEYS = [(38, 22.0), (45, 12.0), (51, 4.0), (57, 0.6), (62, 0.0), (126, 0.0)]

# Collage: enters at 3.0s from an extreme defocused close-up, pulls back fast,
# dominates the frame at 4.0s and settles (~88% width) by 5.0s.
COLLAGE_SCALE_KEYS = [(86, 7.0), (88, 5.0), (92, 3.4), (96, 2.6), (99, 2.1),
                      (105, 1.72), (112, 1.42), (120, 1.15), (135, 1.05),
                      (150, 1.01), (172, 1.0)]
COLLAGE_OPACITY_KEYS = [(86, 0.0), (87, 1.0)]

# Global defocus pulses (depth of field) on the two big transitions.
DEFOCUS_KEYS = [(30, 0.0), (38, 5.5), (43, 8.0), (48, 4.5), (54, 1.4), (58, 0.0),
                (84, 0.0), (88, 3.6), (93, 2.8), (99, 1.2), (104, 0.0)]

# Closing title rising from below in the last second.
CLOSING_RISE_KEYS = [(152, 1.0), (172, 0.0)]  # 1.0 = fully below frame

# -----------------------------------------------------------------------------
# 5. Render Scene Frames
# -----------------------------------------------------------------------------
print(f"[ChrononTemplate] Rendering {TOTAL_FRAMES} frames...")

for frame_idx in range(TOTAL_FRAMES):
    t_sec = frame_idx / float(FPS)

    ring_zoom = track_value(RING_ZOOM_KEYS, frame_idx, ease=ease_linear)
    bg_rgb = build_background(ring_zoom)
    bg_rgb = np.clip(bg_rgb + np.random.default_rng(7).normal(0.0, 1.6, (HEIGHT, WIDTH, 1)), 0, 255).astype(np.uint8)
    bg_pil = Image.fromarray(cv2.cvtColor(bg_rgb, cv2.COLOR_RGB2RGBA))
    # Soft-focus background (depth of field).
    bg_pil = bg_pil.filter(ImageFilter.GaussianBlur(radius=2.2))
    frame_pil = bg_pil

    # SCENE 1: "1990s" (Frames 0 to 48)
    if frame_idx <= 48:
        era_scale = track_value(ERA_SCALE_KEYS, frame_idx)
        era_opacity = track_value(ERA_OPACITY_KEYS, frame_idx, ease=ease_linear)
        era_blur = track_value(ERA_BLUR_KEYS, frame_idx, ease=ease_linear)

        cur_w = max(1, int(plate_era.width * era_scale))
        cur_h = max(1, int(plate_era.height * era_scale))
        scaled_era = plate_era
        if era_blur > 0.5:
            scaled_era = plate_era.filter(ImageFilter.GaussianBlur(radius=float(era_blur / era_scale)))
        scaled_era = scaled_era.resize((cur_w, cur_h), Image.Resampling.BILINEAR)

        if era_opacity < 0.99:
            r, g, b, a = scaled_era.split()
            a = a.point(lambda v: int(v * era_opacity))
            scaled_era.putalpha(a)

        pos_x = cx - cur_w // 2
        pos_y = cy + 75 - cur_h // 2
        frame_pil.paste(scaled_era, (pos_x, pos_y), scaled_era)

    # SCENE 2: "37.7 M" (Frames 38 to 126)
    if 38 <= frame_idx <= 126:
        target_white_w = track_value(STAT_WIDTH_KEYS, frame_idx) * WIDTH
        stat_scale = target_white_w / float(stat_white_w)
        stat_opacity = track_value(STAT_OPACITY_KEYS, frame_idx, ease=ease_linear)
        offset_x = int(track_value(STAT_OFFSET_X_KEYS, frame_idx) * WIDTH)
        offset_y = int(track_value(STAT_OFFSET_Y_KEYS, frame_idx) * HEIGHT)
        stat_blur = track_value(STAT_BLUR_KEYS, frame_idx, ease=ease_linear)

        # Blur on the base plate so the huge crash-zoom rasters stay cheap.
        stat_plate = plate_stat
        if stat_blur > 0.5:
            stat_plate = plate_stat.filter(ImageFilter.GaussianBlur(radius=float(stat_blur / stat_scale)))

        cur_w = max(1, int(stat_plate.width * stat_scale))
        cur_h = max(1, int(stat_plate.height * stat_scale))
        scaled_stat = stat_plate.resize((cur_w, cur_h), Image.Resampling.BILINEAR)

        if stat_opacity < 0.99:
            r, g, b, a = scaled_stat.split()
            a = a.point(lambda v: int(v * stat_opacity))
            scaled_stat.putalpha(a)

        pos_x = cx - cur_w // 2 + offset_x
        pos_y = cy - cur_h // 2 + offset_y
        frame_pil.paste(scaled_stat, (pos_x, pos_y), scaled_stat)

    # SCENE 3: Hero Character Ensemble (Frames 86 to 172)
    if frame_idx >= 86:
        c_scale = track_value(COLLAGE_SCALE_KEYS, frame_idx)
        c_opacity = track_value(COLLAGE_OPACITY_KEYS, frame_idx, ease=ease_linear)
        c_blur = min(22.0, max(0.0, (c_scale - 1.3) * 2.6))

        collage_plate = collage_hero
        if c_blur > 0.5:
            collage_plate = collage_hero.filter(ImageFilter.GaussianBlur(radius=float(c_blur / c_scale)))

        cur_w = max(1, int(collage_plate.width * c_scale))
        cur_h = max(1, int(collage_plate.height * c_scale))
        scaled_c = collage_plate.resize((cur_w, cur_h), Image.Resampling.BILINEAR)

        if c_opacity < 0.99:
            r, g, b, a = scaled_c.split()
            a = a.point(lambda v: int(v * c_opacity))
            scaled_c.putalpha(a)

        # The pivot drifts from the face down to the ensemble centre as we pull back.
        settle = clamp01((7.0 - c_scale) / 6.0)
        pivot_x = 0.50 * target_collage_w
        pivot_y = (0.40 + 0.06 * settle) * target_collage_h

        pos_x = cx - int(pivot_x * c_scale)
        pos_y = cy - int(pivot_y * c_scale)
        frame_pil.paste(scaled_c, (pos_x, pos_y), scaled_c)

    # SCENE 4: Closing "LOONEY TUNES" rising from below (Frames 152 to 172)
    if frame_idx >= 152:
        rise = track_value(CLOSING_RISE_KEYS, frame_idx, ease=ease_out_cubic)
        closing_y = (cy + 640) - 205 * (1.0 - rise)
        pos_x = cx - plate_closing.width // 2
        pos_y = int(closing_y - plate_closing.height // 2)
        frame_pil.paste(plate_closing, (pos_x, pos_y), plate_closing)

    # Global post-processing: depth-of-field defocus pulse, then fine mesh.
    defocus = track_value(DEFOCUS_KEYS, frame_idx, ease=ease_linear)
    if defocus > 0.4:
        frame_pil = frame_pil.filter(ImageFilter.GaussianBlur(radius=float(defocus)))

    frame_bgr = cv2.cvtColor(np.array(frame_pil), cv2.COLOR_RGBA2BGR)
    frame_bgr = np.clip(frame_bgr.astype(np.float32) * (1.0 - MESH_MASK)[:, :, None], 0, 255).astype(np.uint8)

    out_frame_path = os.path.join(FRAMES_DIR, f"frame_{frame_idx:04d}.png")
    cv2.imwrite(out_frame_path, frame_bgr)

    if frame_idx % 30 == 0 or frame_idx == TOTAL_FRAMES - 1:
        print(f"  Frame {frame_idx:03d}/{TOTAL_FRAMES - 1} rendered ({t_sec:.2f}s)")

# -----------------------------------------------------------------------------
# 6. Encode Video with Audio
# -----------------------------------------------------------------------------
print("[ChrononTemplate] Encoding MP4 with FFmpeg and muxing audio...")
cmd = [
    "ffmpeg", "-y",
    "-r", str(FPS),
    "-i", os.path.join(FRAMES_DIR, "frame_%04d.png"),
    "-i", AUDIO_PATH,
    "-c:v", "libx264",
    "-preset", "slow",
    "-crf", "18",
    "-pix_fmt", "yuv420p",
    "-c:a", "aac",
    "-b:a", "192k",
    "-shortest",
    OUTPUT_MP4
]
res = subprocess.run(cmd, capture_output=True, text=True)
if res.returncode != 0:
    print("FFmpeg error:", res.stderr)
else:
    print(f"[ChrononTemplate] SUCCESS: Artifact saved to {OUTPUT_MP4}")
    # Also deliver to workspace
    import shutil
    shutil.copy2(OUTPUT_MP4, WORKSPACE_MP4)
    print(f"[ChrononTemplate] Deliverable copied to workspace: {WORKSPACE_MP4}")

# -----------------------------------------------------------------------------
# 7. Contact Sheet of Keyframes
# -----------------------------------------------------------------------------
checkpoints = [39, 60, 82, 99, 120, 150]
checkpoint_imgs = []
for idx in checkpoints:
    fpath = os.path.join(FRAMES_DIR, f"frame_{idx:04d}.png")
    img = cv2.imread(fpath)
    small = cv2.resize(img, (480, 270))
    t = idx / float(FPS)
    cv2.putText(small, f"Frame {idx} ({t:.2f}s)", (14, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
    checkpoint_imgs.append(small)

row1 = cv2.hconcat(checkpoint_imgs[:4])
# pad second row to the same tile count
blank = np.zeros_like(checkpoint_imgs[0])
row2 = cv2.hconcat(checkpoint_imgs[4:] + [blank] * (4 - len(checkpoint_imgs[4:])))
contact_sheet = cv2.vconcat([row1, row2])
sheet_path = os.path.join(ARTIFACTS_DIR, "contact_sheet.png")
cv2.imwrite(sheet_path, contact_sheet)
print(f"[ChrononTemplate] Contact sheet written to {sheet_path}")
