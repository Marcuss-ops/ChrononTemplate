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
OUT_DIR = os.path.join(TEMPLATE_DIR, "out/ground_pesce_palla_showcase")
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

FONT_PATH = os.path.join(BASE_DIR, "Chronon3d/assets/fonts/Montserrat-ExtraBold.ttf")

W = 1920
H = 1080
N = 150

def ease(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3.0 - 2.0 * t)

def clamp(v, mn=0.0, mx=1.0):
    return max(mn, min(mx, v))

# -------------------------------------------------------------
# CORE GROUND COMPOSITING: SHADOW, GLOW, OPACITY
# -------------------------------------------------------------
def composite_ground_letters(frame, char_data, accent_bgr, alpha_progress, opacity=0.86):
    """
    Renders individual letters onto the terrain with:
    - Soft ground contact shadow (Gaussian blur, offset downward)
    - Ambient neon ground glow
    - Subdued map opacity so terrain relief breathes through
    """
    if alpha_progress <= 0.005:
        return
        
    canvas_text = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    draw_t = ImageDraw.Draw(canvas_text)
    
    canvas_shadow = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    draw_s = ImageDraw.Draw(canvas_shadow)
    
    for ch, font, (x, y), size in char_data:
        # Shadow offset downward (+9px)
        draw_s.text((x, y + 9), ch, font=font, fill=(4, 8, 14, 255))
        # Text in pure white
        draw_t.text((x, y), ch, font=font, fill=(255, 255, 255, 255))
        
    shadow_np = np.asarray(canvas_shadow)
    s_channel = shadow_np[:, :, 3]
    if not np.any(s_channel):
        return
        
    # Gaussian blur for soft ground contact shadow
    s_blur = cv2.GaussianBlur(s_channel, (0, 0), 16).astype(np.float32) / 255.0
    
    # Gaussian blur for neon ambient glow on ground
    glow_blur = cv2.GaussianBlur(s_channel, (0, 0), 34).astype(np.float32) / 255.0
    
    cur_alpha = alpha_progress * opacity
    
    # 1. Apply ambient ground glow
    glow_weight = glow_blur * 0.40 * cur_alpha
    for c in range(3):
        frame[:, :, c] = np.clip(frame[:, :, c].astype(np.float32) * (1.0 - glow_weight) + accent_bgr[c] * glow_weight, 0, 255).astype(np.uint8)
        
    # 2. Apply ground contact shadow
    s_weight = (s_blur * 0.70 * alpha_progress)[:, :, None]
    shadow_color = np.array([5, 10, 16], dtype=np.float32)
    f_float = frame.astype(np.float32)
    f_float = f_float * (1.0 - s_weight) + shadow_color * s_weight
    
    # 3. Apply text with map texture integration opacity
    text_np = np.asarray(canvas_text)
    t_alpha = (text_np[:, :, 3].astype(np.float32) / 255.0 * cur_alpha)[:, :, None]
    t_bgr = cv2.cvtColor(text_np[:, :, :3], cv2.COLOR_RGB2BGR).astype(np.float32)
    
    frame[:] = np.clip(f_float * (1.0 - t_alpha) + t_bgr * t_alpha, 0, 255).astype(np.uint8)


# -------------------------------------------------------------
# 4 PESCE PALLA ANIMATION ENGINES (NO BOXES, NO RECTANGLES)
# -------------------------------------------------------------

def anim_convex_swell(title, cx, cy, progress, zoom_scale=1.0):
    """
    Option 1: Center taller & broader, sides taper down with earth curvature.
    Progressively swells up from flat to full globe curve as camera dives.
    """
    t = clamp((progress - 0.14) / 0.24)
    if t <= 0: return [], 0.0
    
    alpha = ease(t)
    # Swell factor increases as camera lands: starts flat (0.0) -> full bulge (0.45)
    bulge = 0.45 * ease(t)
    arch = 22.0 * ease(t)
    base_size = int(80 * zoom_scale)
    tracking = int(18 * zoom_scale)
    
    L = len(title)
    mid = (L - 1) / 2.0
    
    char_data_temp = []
    total_w = 0
    for i, ch in enumerate(title):
        u = (i - mid) / max(1.0, mid)
        # Cosine bell: 1.0 at center, 0.0 at edges
        b = math.cos(u * math.pi * 0.5)
        cur_size = int(base_size * (0.80 + bulge * b))
        cur_y_off = int(-arch * b)
        font = ImageFont.truetype(FONT_PATH, cur_size)
        w_ch = font.getlength(ch)
        char_data_temp.append((ch, font, cur_size, cur_y_off, w_ch))
        total_w += w_ch + (tracking if i < L - 1 else 0)
        
    start_x = cx - total_w / 2.0
    char_data = []
    cur_x = start_x
    for ch, font, cur_size, cur_y_off, w_ch in char_data_temp:
        y_pos = cy + cur_y_off - cur_size // 2
        char_data.append((ch, font, (cur_x, y_pos), cur_size))
        cur_x += w_ch + tracking
        
    return char_data, alpha


def anim_concave_flare(title, cx, cy, progress, zoom_scale=1.0):
    """
    Option 2: Sides larger & taller, center slimmer / more condensed.
    Creates a panoramic wide-stance perspective across the terrain.
    """
    t = clamp((progress - 0.14) / 0.24)
    if t <= 0: return [], 0.0
    
    alpha = ease(t)
    # Concave profile: edges larger (1.25), center slimmer (0.75)
    flare = 0.40 * ease(t)
    base_size = int(78 * zoom_scale)
    tracking = int(20 * zoom_scale)
    
    L = len(title)
    mid = (L - 1) / 2.0
    
    char_data_temp = []
    total_w = 0
    for i, ch in enumerate(title):
        u = (i - mid) / max(1.0, mid)
        # Parabolic dip: 0.0 at center, 1.0 at edges
        b = u * u
        cur_size = int(base_size * (0.80 + flare * b))
        cur_y_off = int(12.0 * b)
        font = ImageFont.truetype(FONT_PATH, cur_size)
        w_ch = font.getlength(ch)
        char_data_temp.append((ch, font, cur_size, cur_y_off, w_ch))
        total_w += w_ch + (tracking if i < L - 1 else 0)
        
    start_x = cx - total_w / 2.0
    char_data = []
    cur_x = start_x
    for ch, font, cur_size, cur_y_off, w_ch in char_data_temp:
        y_pos = cy + cur_y_off - cur_size // 2
        char_data.append((ch, font, (cur_x, y_pos), cur_size))
        cur_x += w_ch + tracking
        
    return char_data, alpha


def anim_ground_track_zoom(title, cx, cy, progress, zoom_scale=1.0):
    """
    Option 3: Full 1:1 ground lock. As the camera dives in from altitude,
    the text physically grows with the terrain like painted on the earth,
    with convex earth-curvature arch.
    """
    t = clamp((progress - 0.12) / 0.22)
    if t <= 0: return [], 0.0
    
    alpha = ease(t)
    # Scale tightly coupled with camera zoom depth
    depth_scale = 0.65 + 0.55 * ease(progress)
    base_size = int(82 * depth_scale)
    tracking = int(18 * depth_scale)
    bulge = 0.44
    arch = 24.0 * depth_scale
    
    L = len(title)
    mid = (L - 1) / 2.0
    
    char_data_temp = []
    total_w = 0
    for i, ch in enumerate(title):
        u = (i - mid) / max(1.0, mid)
        b = math.cos(u * math.pi * 0.5)
        cur_size = int(base_size * (0.82 + bulge * b))
        cur_y_off = int(-arch * b)
        font = ImageFont.truetype(FONT_PATH, cur_size)
        w_ch = font.getlength(ch)
        char_data_temp.append((ch, font, cur_size, cur_y_off, w_ch))
        total_w += w_ch + (tracking if i < L - 1 else 0)
        
    start_x = cx - total_w / 2.0
    char_data = []
    cur_x = start_x
    for ch, font, cur_size, cur_y_off, w_ch in char_data_temp:
        y_pos = cy + cur_y_off - cur_size // 2
        char_data.append((ch, font, (cur_x, y_pos), cur_size))
        cur_x += w_ch + tracking
        
    return char_data, alpha


def anim_wave_ripple(title, cx, cy, progress, zoom_scale=1.0):
    """
    Option 4: Dynamic bulge ripple wave across the letters during camera arrival,
    then settling into balanced convex globe arch.
    """
    t = clamp((progress - 0.14) / 0.26)
    if t <= 0: return [], 0.0
    
    alpha = ease(t)
    base_size = int(80 * zoom_scale)
    tracking = int(18 * zoom_scale)
    
    L = len(title)
    mid = (L - 1) / 2.0
    
    # Wave position sweeps from -1.5 to 1.5 across normalized letters
    wave_pos = -1.5 + 3.0 * ease(t)
    is_settled = (t >= 0.85)
    
    char_data_temp = []
    total_w = 0
    for i, ch in enumerate(title):
        u = (i - mid) / max(1.0, mid)
        if not is_settled:
            dist_to_wave = abs(u - wave_pos)
            wave_peak = math.exp(-3.5 * dist_to_wave * dist_to_wave)
            b = 0.2 + 0.6 * wave_peak
            cur_y_off = int(-26.0 * wave_peak)
        else:
            b = math.cos(u * math.pi * 0.5)
            cur_y_off = int(-22.0 * b)
            
        cur_size = int(base_size * (0.80 + 0.45 * b))
        font = ImageFont.truetype(FONT_PATH, cur_size)
        w_ch = font.getlength(ch)
        char_data_temp.append((ch, font, cur_size, cur_y_off, w_ch))
        total_w += w_ch + (tracking if i < L - 1 else 0)
        
    start_x = cx - total_w / 2.0
    char_data = []
    cur_x = start_x
    for ch, font, cur_size, cur_y_off, w_ch in char_data_temp:
        y_pos = cy + cur_y_off - cur_size // 2
        char_data.append((ch, font, (cur_x, y_pos), cur_size))
        cur_x += w_ch + tracking
        
    return char_data, alpha


VARIANTS = [
    ('style_1_convex_swell', 'Style 1 - Rigonfiamento Sferico Globale', anim_convex_swell),
    ('style_2_concave_flare', 'Style 2 - Centro Sottile e Lati Larghi', anim_concave_flare),
    ('style_3_ground_track_zoom', 'Style 3 - Proiezione Terreno e Zoom 1-1', anim_ground_track_zoom),
    ('style_4_wave_ripple', 'Style 4 - Onda di Rigonfiamento Dinamico', anim_wave_ripple)
]

TARGET_NATIONS = ['brazil', 'italy']

class GroundShowcaseBuilder(generator.Builder):
    def __init__(self, scene, polygons, anim_func):
        super().__init__(scene, polygons)
        self.anim_func = anim_func

    def _draw_title(self, frame, f, progress, pts):
        title = self.title.upper()
        pose_zoom = self.pose(f)[2]
        title_lat, title_lon = (43.0, 12.5) if self.slug == 'italy' else self.anchor
        cx, cy = self._screen(title_lon, title_lat, pose_zoom)
        cx = max(240, min(W - 240, cx))
        cy = max(130, min(H - 130, cy))
        
        # In Brazil, shift slightly down towards Amazon core
        if self.slug == 'brazil':
            cy += 40
            
        accent_bgr = self.accent
        zoom_scale = 2.0 ** ((pose_zoom - 5.0) * 0.4)
        
        char_data, alpha_val = self.anim_func(title, cx, cy, progress, zoom_scale=zoom_scale)
        composite_ground_letters(frame, char_data, accent_bgr, alpha_val, opacity=0.86)


def main():
    scenes_by_slug = {s[0]: s for s in generator.SCENES}
    results = []

    print(f"Starting Ground Pesce Palla Showcase Production for: {TARGET_NATIONS}")
    print(f"Styles: {[v[1] for v in VARIANTS]}")

    for country_slug in TARGET_NATIONS:
        scene = scenes_by_slug[country_slug]
        country_name = scene[1]
        polys = generator.country_polygons(generator.feature(country_slug))

        print(f"\n==================================================")
        print(f"PREPARING BASEMAP TILES FOR: {country_name}")
        print(f"==================================================")
        base_builder = generator.Builder(scene, polys)
        pyramid = dyn.DynamicTilePyramid(provider='esri_sat')
        sampler = fast.FastPlateSampler(pyramid, W, H)
        sampler.prepare(base_builder.ANCHORS, base_builder.PREPARE_ZMIN, base_builder.PREPARE_ZMAX)

        for var_key, var_name, var_func in VARIANTS:
            job_id = f"{country_slug}_{var_key}"
            drive_filename = f"Chronon V2 Ground - {var_name} - {country_name}.mp4"
            raw_mp4 = Path(RENDERS_DIR) / f"{job_id}_raw.mp4"
            web_mp4 = Path(RENDERS_DIR) / f"{job_id}_web.mp4"
            thumb_png = Path(RENDERS_DIR) / f"{job_id}_thumb.png"

            print(f"\n--- [RENDERING] {country_name} | {var_name} ---")
            builder = GroundShowcaseBuilder(scene, polys, var_func)
            
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
                if total_f == 85: # Thumbnail frame during settled camera
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
    summary_path = os.path.join(OUT_DIR, "ground_showcase_results.json")
    with open(summary_path, "w") as f:
        json.dump(results, f, indent=2)

    print("\n" + "="*60)
    print("ALL GROUND PESCE PALLA VARIANTS COMPLETE & UPLOADED!")
    print("="*60)
    for r in results:
        print(f"- {r['country']} | {r['variant_name']}: {r['link']}")

if __name__ == "__main__":
    main()
