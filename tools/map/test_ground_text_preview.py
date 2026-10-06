import os
import math
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

BASE_DIR = "/home/pierone/src/go-master/projects/Pyt/VeloxEditing"
TEMPLATE_DIR = os.path.join(BASE_DIR, "ChrononTemplate")
TOOLS_MAP = os.path.join(TEMPLATE_DIR, "tools/map")

import sys
sys.path.insert(0, TOOLS_MAP)
import render_map_image_v2_opencv as generator
import dynamic_tile_pyramid as dyn
import fast_plate_sampler as fast

FONT_PATH = os.path.join(BASE_DIR, "Chronon3d/assets/fonts/Montserrat-ExtraBold.ttf")

# Get Brazil scene
scene = next(s for s in generator.SCENES if s[0] == 'brazil')
polys = generator.country_polygons(generator.feature('brazil'))
builder = generator.Builder(scene, polys)
pyramid = dyn.DynamicTilePyramid(provider='esri_sat')
sampler = fast.FastPlateSampler(pyramid, 1920, 1080)
sampler.prepare(builder.ANCHORS, builder.PREPARE_ZMIN, builder.PREPARE_ZMAX)

# Sample a clean frame at f=110
lat, lon, zoom = builder.pose(110)
builder.current_center = (lat, lon)
frame = sampler.sample(lat, lon, zoom, 1920, 1080)
builder._draw_country(frame, 110, zoom, 110/149)

# Now test rendering text with:
# 1. No card / no box
# 2. Pesce palla bulge (center larger / curved)
# 3. Ground shadow & glow
# 4. Map integration opacity (~0.85)

title = "BRAZIL"
cx, cy = builder._screen(builder.anchor[1], builder.anchor[0], zoom)
accent_rgb = (43, 228, 176)
accent_bgr = (176, 228, 43)

def render_ground_pesce_palla(frame, title, cx, cy, accent_bgr, bulge_amt=0.45, arch_amt=24, base_size=82, tracking=18, opacity=0.86):
    H, W = frame.shape[:2]
    L = len(title)
    mid = (L - 1) / 2.0
    
    char_sizes = []
    char_fonts = []
    char_offsets_y = []
    char_widths = []
    
    for i, ch in enumerate(title):
        u = (i - mid) / max(1.0, mid) # -1.0 to 1.0
        # Cosine or parabolic bulge: center letters are taller and broader
        b = math.cos(u * math.pi * 0.5)
        
        cur_size = int(base_size * (0.80 + bulge_amt * b))
        cur_y = int(-arch_amt * b)
        font = ImageFont.truetype(FONT_PATH, cur_size)
        
        char_sizes.append(cur_size)
        char_fonts.append(font)
        char_offsets_y.append(cur_y)
        char_widths.append(font.getlength(ch))
        
    total_w = sum(char_widths) + tracking * (L - 1)
    
    canvas_text = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    draw_t = ImageDraw.Draw(canvas_text)
    
    canvas_shadow = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    draw_s = ImageDraw.Draw(canvas_shadow)
    
    cur_x = cx - total_w / 2.0
    for i, ch in enumerate(title):
        font = char_fonts[i]
        w_ch = char_widths[i]
        y_off = char_offsets_y[i]
        ch_y = cy + y_off - char_sizes[i] // 2
        
        # Ground shadow: offset 10px downward, deep dark tone
        draw_s.text((cur_x, ch_y + 10), ch, font=font, fill=(4, 8, 14, 255))
        draw_t.text((cur_x, ch_y), ch, font=font, fill=(255, 255, 255, 255))
        cur_x += w_ch + tracking
        
    # Gaussian blur for realistic ground contact shadow
    shadow_np = np.asarray(canvas_shadow)
    s_blur = cv2.GaussianBlur(shadow_np[:, :, 3], (0, 0), 16).astype(np.float32) / 255.0
    
    # Ground glow: soft colored ambient light projected onto satellite terrain under the letters
    glow_blur = cv2.GaussianBlur(shadow_np[:, :, 3], (0, 0), 36).astype(np.float32) / 255.0
    
    # Apply ground glow
    for c in range(3):
        frame[:, :, c] = np.clip(frame[:, :, c].astype(np.float32) * (1.0 - glow_blur * 0.42 * opacity) + accent_bgr[c] * (glow_blur * 0.42 * opacity), 0, 255).astype(np.uint8)
        
    # Apply ground shadow
    s_weight = (s_blur * 0.72)[:, :, None]
    shadow_color = np.array([6, 12, 18], dtype=np.float32)
    frame_float = frame.astype(np.float32)
    frame_float = frame_float * (1.0 - s_weight) + shadow_color * s_weight
    
    # Apply text with map texture integration opacity (0.86)
    text_np = np.asarray(canvas_text)
    t_alpha = (text_np[:, :, 3].astype(np.float32) / 255.0 * opacity)[:, :, None]
    t_bgr = cv2.cvtColor(text_np[:, :, :3], cv2.COLOR_RGB2BGR).astype(np.float32)
    
    final = np.clip(frame_float * (1.0 - t_alpha) + t_bgr * t_alpha, 0, 255).astype(np.uint8)
    return final

out_img = render_ground_pesce_palla(frame, title, cx, cy, accent_bgr)
cv2.imwrite("ChrononTemplate/out/test_ground_brazil_clean.png", out_img)
print("Saved ChrononTemplate/out/test_ground_brazil_clean.png successfully!")
