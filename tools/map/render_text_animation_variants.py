import os
import sys
import math
import json
import time
import subprocess
from pathlib import Path
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

BASE_DIR = "/home/pierone/src/go-master/projects/Pyt/VeloxEditing"
TEMPLATE_DIR = os.path.join(BASE_DIR, "ChrononTemplate")
TOOLS_MAP = os.path.join(TEMPLATE_DIR, "tools/map")
OUT_DIR = os.path.join(TEMPLATE_DIR, "out/text_animation_variants")
RENDERS_DIR = os.path.join(OUT_DIR, "renders")
os.makedirs(RENDERS_DIR, exist_ok=True)

sys.path.insert(0, TOOLS_MAP)
import render_map_image_v2_opencv as generator
import geo_runtime as geo
import dynamic_tile_pyramid as dyn
import fast_plate_sampler as fast
import fast_geo_camera as harness

UPLOADER = os.path.join(BASE_DIR, "RenderingGen/bin/drive-upload")
DRIVE_FOLDER = "1WALc4JbFz6uK5nEM_tYnAeQqiPVRacp_"
CREDS_JSON = os.path.expanduser("~/.config/velox/credentials.json")
TOKEN_JSON = os.path.expanduser("~/.config/velox/token.json")

FONT_PATH = os.path.join(BASE_DIR, "Chronon3d/assets/fonts/Montserrat-Bold.ttf")

W = 1920
H = 1080
N = 150

def ease(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3.0 - 2.0 * t)

def clamp(v, mn=0.0, mx=1.0):
    return max(mn, min(mx, v))

# -------------------------------------------------------------
# 4 DISTINCT TEXT ANIMATION ENGINES ON THE BLACK PILL BADGE
# -------------------------------------------------------------

def draw_mask_slide_up(frame, title, cx, cy, accent_rgb, accent_bgr, progress):
    t = clamp((progress - 0.16) / 0.22)
    if t <= 0: return
    
    font = ImageFont.truetype(FONT_PATH, 44)
    tw = font.getlength(title)
    card_w = max(260, int(tw + 72))
    card_h = 72
    
    # 1. Badge width expansion
    t_w = clamp(t / 0.55)
    w_cur = int(card_w * (0.2 + 0.8 * ease(t_w)))
    alpha_badge = clamp(t / 0.35)
    
    x0 = int(cx - w_cur // 2)
    y0 = int(cy - card_h // 2)
    x1 = x0 + w_cur
    y1 = y0 + card_h
    
    # Outer glow
    glow_mask = np.zeros((H, W), dtype=np.uint8)
    cv2.rectangle(glow_mask, (max(0, x0-4), max(0, y0-4)), (min(W-1, x1+4), min(H-1, y1+4)), 255, -1)
    glow_blur = cv2.GaussianBlur(glow_mask, (0, 0), 16).astype(np.float32) / 255.0
    for c in range(3):
        frame[:, :, c] = np.clip(frame[:, :, c].astype(np.float32) * (1.0 - glow_blur * 0.32 * alpha_badge) + accent_bgr[c] * (glow_blur * 0.32 * alpha_badge), 0, 255).astype(np.uint8)
        
    overlay = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    
    # Pill background
    draw.rounded_rectangle([x0, y0, x1, y1], radius=card_h//2, fill=(8, 14, 22, int(230 * alpha_badge)), outline=(accent_rgb[0], accent_rgb[1], accent_rgb[2], int(255 * alpha_badge)), width=2)
    
    # 2. Text slide-up with clipping to badge interior
    t_text = clamp((t - 0.22) / 0.78)
    if t_text > 0 and w_cur > 20:
        y_slide = int((1.0 - ease(t_text)) * 40)
        text_surf = Image.new('RGBA', (w_cur, card_h), (0, 0, 0, 0))
        t_draw = ImageDraw.Draw(text_surf)
        
        b = t_draw.textbbox((0, 0), title, font=font)
        tx = (w_cur - (b[2] - b[0])) // 2
        ty = (card_h - (b[3] - b[1])) // 2 + y_slide - 3
        t_draw.text((tx, ty), title, font=font, fill=(255, 255, 255, int(255 * ease(t_text))))
        
        pill_mask = Image.new('L', (w_cur, card_h), 0)
        ImageDraw.Draw(pill_mask).rounded_rectangle([0, 0, w_cur, card_h], radius=card_h//2, fill=255)
        text_surf.putalpha(Image.composite(text_surf.getchannel('A'), Image.new('L', (w_cur, card_h), 0), pill_mask))
        overlay.alpha_composite(text_surf, (x0, y0))
        
    overlay_np = np.asarray(overlay)
    o_alpha = (overlay_np[:, :, 3].astype(np.float32) / 255.0)[:, :, None]
    o_bgr = cv2.cvtColor(overlay_np[:, :, :3], cv2.COLOR_RGB2BGR).astype(np.float32)
    frame[:] = np.clip(frame.astype(np.float32) * (1.0 - o_alpha) + o_bgr * o_alpha, 0, 255).astype(np.uint8)


def draw_elastic_pop_flare(frame, title, cx, cy, accent_rgb, accent_bgr, progress):
    t = clamp((progress - 0.16) / 0.26)
    if t <= 0: return
    
    font = ImageFont.truetype(FONT_PATH, 44)
    tw = font.getlength(title)
    card_w = max(260, int(tw + 72))
    card_h = 72
    
    spring_s = 1.0 + 0.38 * math.exp(-6.5 * t) * math.cos(math.pi * 3.2 * t) if t < 1.0 else 1.0
    spring_y = -40.0 * math.exp(-7.0 * t) * math.cos(math.pi * 2.2 * t) if t < 1.0 else 0.0
    
    w_cur = int(card_w * spring_s)
    h_cur = int(card_h * spring_s)
    cy_cur = int(cy + spring_y)
    
    x0 = int(cx - w_cur // 2)
    y0 = int(cy_cur - h_cur // 2)
    x1 = x0 + w_cur
    y1 = y0 + h_cur
    
    flare = max(0.0, 1.0 - abs(t - 0.45) / 0.22)
    border_w = 4 if flare > 0.4 else 2
    
    glow_strength = 0.32 + 0.45 * flare
    glow_mask = np.zeros((H, W), dtype=np.uint8)
    cv2.rectangle(glow_mask, (max(0, x0-8), max(0, y0-8)), (min(W-1, x1+8), min(H-1, y1+8)), 255, -1)
    glow_blur = cv2.GaussianBlur(glow_mask, (0, 0), int(16 + 18 * flare)).astype(np.float32) / 255.0
    
    for c in range(3):
        frame[:, :, c] = np.clip(frame[:, :, c].astype(np.float32) * (1.0 - glow_blur * glow_strength) + accent_bgr[c] * (glow_blur * glow_strength), 0, 255).astype(np.uint8)
        
    overlay = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    alpha = clamp(t / 0.25)
    
    draw.rounded_rectangle([x0, y0, x1, y1], radius=h_cur//2, fill=(8, 14, 22, int(230 * alpha)), outline=(accent_rgb[0], accent_rgb[1], accent_rgb[2], int(255 * alpha)), width=border_w)
    
    font_scaled = ImageFont.truetype(FONT_PATH, max(20, int(44 * spring_s)))
    b = draw.textbbox((0, 0), title, font=font_scaled)
    tw_s = b[2] - b[0]
    th_s = b[3] - b[1]
    tx = cx - tw_s // 2
    ty = cy_cur - th_s // 2 - 3
    draw.text((tx, ty), title, font=font_scaled, fill=(255, 255, 255, int(255 * alpha)))
    
    overlay_np = np.asarray(overlay)
    o_alpha = (overlay_np[:, :, 3].astype(np.float32) / 255.0)[:, :, None]
    o_bgr = cv2.cvtColor(overlay_np[:, :, :3], cv2.COLOR_RGB2BGR).astype(np.float32)
    frame[:] = np.clip(frame.astype(np.float32) * (1.0 - o_alpha) + o_bgr * o_alpha, 0, 255).astype(np.uint8)


def draw_tracking_expansion(frame, title, cx, cy, accent_rgb, accent_bgr, progress):
    t = clamp((progress - 0.16) / 0.24)
    if t <= 0: return
    
    font = ImageFont.truetype(FONT_PATH, 42)
    tracking = -2.0 + 16.0 * ease(t)
    
    base_w = sum(font.getlength(ch) for ch in title)
    tw_tracked = int(base_w + tracking * (len(title) - 1))
    
    card_w = max(260, tw_tracked + 68)
    card_h = 70
    alpha = ease(t)
    
    y_float = int((1.0 - ease(t)) * 16)
    x0 = int(cx - card_w // 2)
    y0 = int(cy - card_h // 2 + y_float)
    x1 = x0 + card_w
    y1 = y0 + card_h
    
    glow_mask = np.zeros((H, W), dtype=np.uint8)
    cv2.rectangle(glow_mask, (max(0, x0-4), max(0, y0-4)), (min(W-1, x1+4), min(H-1, y1+4)), 255, -1)
    glow_blur = cv2.GaussianBlur(glow_mask, (0, 0), 16).astype(np.float32) / 255.0
    for c in range(3):
        frame[:, :, c] = np.clip(frame[:, :, c].astype(np.float32) * (1.0 - glow_blur * 0.3 * alpha) + accent_bgr[c] * (glow_blur * 0.3 * alpha), 0, 255).astype(np.uint8)
        
    overlay = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    
    draw.rounded_rectangle([x0, y0, x1, y1], radius=card_h//2, fill=(8, 14, 22, int(225 * alpha)), outline=(accent_rgb[0], accent_rgb[1], accent_rgb[2], int(255 * alpha)), width=2)
    
    cursor = cx - tw_tracked // 2
    ty = y0 + (card_h - 40) // 2 - 2
    for ch in title:
        draw.text((cursor, ty), ch, font=font, fill=(255, 255, 255, int(255 * alpha)))
        cursor += font.getlength(ch) + tracking
        
    dot_pulse = 0.6 + 0.4 * math.sin(progress * 8.0)
    dot_alpha = int(255 * alpha * dot_pulse)
    draw.ellipse([x1 - 24, y0 + card_h//2 - 4, x1 - 16, y0 + card_h//2 + 4], fill=(accent_rgb[0], accent_rgb[1], accent_rgb[2], dot_alpha))
    
    overlay_np = np.asarray(overlay)
    o_alpha = (overlay_np[:, :, 3].astype(np.float32) / 255.0)[:, :, None]
    o_bgr = cv2.cvtColor(overlay_np[:, :, :3], cv2.COLOR_RGB2BGR).astype(np.float32)
    frame[:] = np.clip(frame.astype(np.float32) * (1.0 - o_alpha) + o_bgr * o_alpha, 0, 255).astype(np.uint8)


def draw_typewriter_cursor(frame, title, cx, cy, accent_rgb, accent_bgr, progress):
    t = clamp((progress - 0.16) / 0.22)
    if t <= 0: return
    
    font = ImageFont.truetype(FONT_PATH, 44)
    tw = font.getlength(title)
    card_w = max(260, int(tw + 76))
    card_h = 72
    alpha = clamp(t / 0.25)
    
    x0 = int(cx - card_w // 2)
    y0 = int(cy - card_h // 2)
    x1 = x0 + card_w
    y1 = y0 + card_h
    
    glow_mask = np.zeros((H, W), dtype=np.uint8)
    cv2.rectangle(glow_mask, (max(0, x0-4), max(0, y0-4)), (min(W-1, x1+4), min(H-1, y1+4)), 255, -1)
    glow_blur = cv2.GaussianBlur(glow_mask, (0, 0), 16).astype(np.float32) / 255.0
    for c in range(3):
        frame[:, :, c] = np.clip(frame[:, :, c].astype(np.float32) * (1.0 - glow_blur * 0.3 * alpha) + accent_bgr[c] * (glow_blur * 0.3 * alpha), 0, 255).astype(np.uint8)
        
    overlay = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    
    draw.rounded_rectangle([x0, y0, x1, y1], radius=card_h//2, fill=(8, 14, 22, int(230 * alpha)), outline=(accent_rgb[0], accent_rgb[1], accent_rgb[2], int(255 * alpha)), width=2)
    
    t_type = clamp((t - 0.15) / 0.75)
    num_chars = int(t_type * (len(title) + 1))
    visible_text = title[:num_chars]
    
    b = draw.textbbox((0, 0), title, font=font)
    total_w = b[2] - b[0]
    tx0 = cx - total_w // 2
    ty = y0 + (card_h - (b[3] - b[1])) // 2 - 3
    
    draw.text((tx0, ty), visible_text, font=font, fill=(255, 255, 255, int(255 * alpha)))
    
    cur_w = font.getlength(visible_text)
    cur_x = tx0 + cur_w + 3
    if t_type < 1.0 or (int(progress * 15) % 2 == 0):
        draw.rectangle([cur_x, ty + 6, cur_x + 9, ty + 40], fill=(accent_rgb[0], accent_rgb[1], accent_rgb[2], int(255 * alpha)))
        
    overlay_np = np.asarray(overlay)
    o_alpha = (overlay_np[:, :, 3].astype(np.float32) / 255.0)[:, :, None]
    o_bgr = cv2.cvtColor(overlay_np[:, :, :3], cv2.COLOR_RGB2BGR).astype(np.float32)
    frame[:] = np.clip(frame.astype(np.float32) * (1.0 - o_alpha) + o_bgr * o_alpha, 0, 255).astype(np.uint8)


VARIANTS = [
    ('style_1_mask_slide_up', 'Style 1 - Mask Slide Up', draw_mask_slide_up),
    ('style_3_tracking_expansion', 'Style 3 - Tracking Expansion', draw_tracking_expansion)
]

TARGET_NATIONS = ['italy', 'brazil']

class ShowcaseBuilder(generator.Builder):
    def __init__(self, scene, polygons, variant_func):
        super().__init__(scene, polygons)
        self.variant_func = variant_func

    def _draw_title(self, frame, f, progress, pts):
        title = self.title.upper()
        pose_zoom = self.pose(f)[2]
        title_lat, title_lon = (43.25, 12.5) if self.slug == 'italy' else self.anchor
        cx, cy = self._screen(title_lon, title_lat, pose_zoom)
        cx = max(240, min(W - 240, cx))
        cy = max(130, min(H - 130, cy))
        accent_rgb = (int(self.hex[1:3], 16), int(self.hex[3:5], 16), int(self.hex[5:7], 16))
        accent_bgr = self.accent
        self.variant_func(frame, title, cx, cy, accent_rgb, accent_bgr, progress)

def main():
    scenes_by_slug = {s[0]: s for s in generator.SCENES}
    results = []

    print(f"Starting Text Animation Showcase Production for: {TARGET_NATIONS}")
    print(f"Styles: {[v[1] for v in VARIANTS]}")

    for country_slug in TARGET_NATIONS:
        scene = scenes_by_slug[country_slug]
        country_name = scene[1]
        polys = generator.country_polygons(generator.feature(country_slug))

        # Initialize and prefetch tile pyramid once per country
        print(f"\n==================================================")
        print(f"PREPARING BASEMAP FOR: {country_name}")
        print(f"==================================================")
        base_builder = generator.Builder(scene, polys)
        pyramid = dyn.DynamicTilePyramid(provider='esri_sat')
        sampler = fast.FastPlateSampler(pyramid, W, H)
        sampler.prepare(base_builder.ANCHORS, base_builder.PREPARE_ZMIN, base_builder.PREPARE_ZMAX)

        for var_key, var_name, var_func in VARIANTS:
            job_id = f"{country_slug}_{var_key}"
            drive_filename = f"Chronon V2 - {var_name} - {country_name}.mp4"
            raw_mp4 = Path(RENDERS_DIR) / f"{job_id}_raw.mp4"
            web_mp4 = Path(RENDERS_DIR) / f"{job_id}_web.mp4"
            thumb_png = Path(RENDERS_DIR) / f"{job_id}_thumb.png"

            print(f"\n--- [RENDERING] {country_name} | {var_name} ---")
            builder = ShowcaseBuilder(scene, polys, var_func)
            
            t0 = time.time()
            stat = harness.encode_with_pool(builder, sampler, raw_mp4, workers=12, block=2, preset='veryfast', crf=18)
            t_render = time.time() - t0
            print(f"Rendered in {t_render:.1f}s ({stat['bytes']} bytes)")

            # Zero black frames audit
            cap = cv2.VideoCapture(str(raw_mp4))
            total_f = 0
            blacks = []
            while True:
                ret, frame = cap.read()
                if not ret: break
                if total_f == 75: # Save thumbnail frame
                    cv2.imwrite(str(thumb_png), frame)
                m = np.mean(frame)
                if m < 10.0:
                    blacks.append((total_f, float(m)))
                total_f += 1
            cap.release()
            print(f"Audit {country_name} {var_name}: total={total_f}, blacks={len(blacks)}")
            assert len(blacks) == 0, f"Error: black frame glitch in {job_id}"

            # GPU-Safe Re-encode
            cmd_ffmpeg = [
                "ffmpeg", "-y", "-i", str(raw_mp4),
                "-c:v", "libx264", "-profile:v", "high", "-level", "4.1",
                "-pix_fmt", "yuv420p", "-movflags", "+faststart",
                str(web_mp4)
            ]
            subprocess.run(cmd_ffmpeg, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)

            # Upload to Drive
            print(f"Uploading {drive_filename} to Drive...")
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
                "country": country_name,
                "variant_key": var_key,
                "variant_name": var_name,
                "video": str(web_mp4),
                "thumbnail": str(thumb_png),
                "drive_name": drive_filename,
                "link": link
            })

    # Save summary json
    summary_path = os.path.join(OUT_DIR, "text_animation_variants_results.json")
    with open(summary_path, "w") as f:
        json.dump(results, f, indent=2)

    print("\n" + "="*60)
    print("ALL TEXT ANIMATION VARIANTS COMPLETE & UPLOADED!")
    print("="*60)
    for r in results:
        print(f"- {r['country']} | {r['variant_name']}: {r['link']}")

if __name__ == "__main__":
    main()
