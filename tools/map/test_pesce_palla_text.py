import os
import math
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

BASE_DIR = "/home/pierone/src/go-master/projects/Pyt/VeloxEditing"
FONTS_DIR = os.path.join(BASE_DIR, "Chronon3d/assets/fonts")
FONT_PATH = os.path.join(FONTS_DIR, "Montserrat-ExtraBold.ttf")

# Load base frame of Brazil
cap = cv2.VideoCapture(os.path.join(BASE_DIR, "ChrononTemplate/out/map_image_v1_opencv/renders/map_image_brazil_glow_reveal_web.mp4"))
cap.set(cv2.CAP_PROP_POS_FRAMES, 100)
ret, frame = cap.read()
cap.release()

H, W = frame.shape[:2]
cx, cy = 960, 520 # Brazil center
title = "BRAZIL"
accent_rgb = (43, 228, 176) # Teal #2BE4B0
accent_bgr = (176, 228, 43)

def render_pesce_palla_title(base_img, title, cx, cy, accent_rgb, accent_bgr, bulge_amt=0.35, arch_amt=18, tracking=14, base_size=68, opacity=0.88):
    img = base_img.copy()
    L = len(title)
    mid = (L - 1) / 2.0
    
    # 1. Compute per-character metrics with pufferfish bulge
    char_sizes = []
    char_fonts = []
    char_offsets_y = []
    char_widths = []
    
    for i, ch in enumerate(title):
        # normalized distance from center: -1.0 to 1.0
        u = (i - mid) / max(1.0, mid)
        # bulge profile: 1.0 at center, 0.0 at edges
        b = max(0.0, 1.0 - u * u)
        
        cur_size = int(base_size * (1.0 + bulge_amt * b))
        cur_y = int(-arch_amt * b)
        font = ImageFont.truetype(FONT_PATH, cur_size)
        
        char_sizes.append(cur_size)
        char_fonts.append(font)
        char_offsets_y.append(cur_y)
        char_widths.append(font.getlength(ch))
        
    total_w = sum(char_widths) + tracking * (L - 1)
    
    # 2. Render to high-res RGBA layers (Text + Shadow + Glow)
    # Canvas for text
    canvas_text = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    draw_t = ImageDraw.Draw(canvas_text)
    
    # Canvas for ground shadow
    canvas_shadow = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    draw_s = ImageDraw.Draw(canvas_shadow)
    
    cur_x = cx - total_w / 2.0
    for i, ch in enumerate(title):
        font = char_fonts[i]
        w_ch = char_widths[i]
        y_off = char_offsets_y[i]
        
        # Center this character on its baseline
        ch_y = cy + y_off - char_sizes[i] // 2
        
        # Shadow: offset downward and slightly blurred
        draw_s.text((cur_x, ch_y + 8), ch, font=font, fill=(5, 12, 18, 240))
        
        # Text: pure white
        draw_t.text((cur_x, ch_y), ch, font=font, fill=(255, 255, 255, 255))
        
        cur_x += w_ch + tracking
        
    # Blur shadow with OpenCV
    shadow_np = np.asarray(canvas_shadow)
    shadow_alpha = shadow_np[:, :, 3]
    shadow_blur = cv2.GaussianBlur(shadow_alpha, (0, 0), 12)
    
    # Ground glow behind text (accent neon tint on terrain)
    glow_mask = cv2.GaussianBlur(shadow_alpha, (0, 0), 28).astype(np.float32) / 255.0
    
    # Composite Glow onto frame
    glow_strength = 0.40 * opacity
    for c in range(3):
        img[:, :, c] = np.clip(img[:, :, c].astype(np.float32) * (1.0 - glow_mask * glow_strength) + accent_bgr[c] * (glow_mask * glow_strength), 0, 255).astype(np.uint8)
        
    # Composite Shadow onto frame
    s_alpha = (shadow_blur.astype(np.float32) / 255.0 * 0.70)[:, :, None]
    img = (img.astype(np.float32) * (1.0 - s_alpha) + np.array([8, 14, 20], dtype=np.float32) * s_alpha).astype(np.uint8)
    
    # Composite Text onto frame with subdued map opacity (0.86)
    text_np = np.asarray(canvas_text)
    t_alpha = (text_np[:, :, 3].astype(np.float32) / 255.0 * opacity)[:, :, None]
    t_rgb = text_np[:, :, :3]
    t_bgr = cv2.cvtColor(t_rgb, cv2.COLOR_RGB2BGR).astype(np.float32)
    
    final = np.clip(img.astype(np.float32) * (1.0 - t_alpha) + t_bgr * t_alpha, 0, 255).astype(np.uint8)
    return final

# Test 1: Pufferfish center-bulged (classic curved globe arch)
res1 = render_pesce_palla_title(frame, "BRAZIL", cx, cy, accent_rgb, accent_bgr, bulge_amt=0.40, arch_amt=22, tracking=16, base_size=74, opacity=0.86)
cv2.imwrite("ChrononTemplate/out/test_pesce_palla_brazil.png", res1)

print("Saved test_pesce_palla_brazil.png!")
