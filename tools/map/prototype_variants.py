import math
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import os

BASE_DIR = "/home/pierone/src/go-master/projects/Pyt/VeloxEditing"
FONT_PATH = os.path.join(BASE_DIR, "Chronon3d/assets/fonts/Montserrat-Bold.ttf")

def ease(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3.0 - 2.0 * t)

def clamp(v, mn=0.0, mx=1.0):
    return max(mn, min(mx, v))

def draw_badge_mask_slide_up(frame, title, cx, cy, accent_rgb, accent_bgr, progress):
    H, W = frame.shape[:2]
    t = clamp((progress - 0.16) / 0.20)
    if t <= 0: return
    
    font = ImageFont.truetype(FONT_PATH, 44)
    tw = font.getlength(title)
    card_w = max(260, int(tw + 70))
    card_h = 72
    
    # 1. Badge width horizontal reveal
    t_w = clamp(t / 0.6)
    w_cur = int(card_w * (0.2 + 0.8 * ease(t_w)))
    alpha_badge = clamp(t / 0.4)
    
    x0 = int(cx - w_cur // 2)
    y0 = int(cy - card_h // 2)
    x1 = x0 + w_cur
    y1 = y0 + card_h
    
    # Outer soft glow
    glow_mask = np.zeros((H, W), dtype=np.uint8)
    cv2.rectangle(glow_mask, (max(0, x0-4), max(0, y0-4)), (min(W-1, x1+4), min(H-1, y1+4)), 255, -1)
    glow_blur = cv2.GaussianBlur(glow_mask, (0, 0), 16).astype(np.float32) / 255.0
    for c in range(3):
        frame[:, :, c] = np.clip(frame[:, :, c].astype(np.float32) * (1.0 - glow_blur * 0.3 * alpha_badge) + accent_bgr[c] * (glow_blur * 0.3 * alpha_badge), 0, 255).astype(np.uint8)
        
    overlay = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    
    # Dark black pill
    draw.rounded_rectangle([x0, y0, x1, y1], radius=card_h//2, fill=(8, 14, 22, int(230 * alpha_badge)), outline=(accent_rgb[0], accent_rgb[1], accent_rgb[2], int(255 * alpha_badge)), width=2)
    
    # Specular sheen
    draw.rounded_rectangle([x0+4, y0+3, x1-4, y0+card_h//2-2], radius=card_h//4, fill=(255, 255, 255, int(15 * alpha_badge)))
    
    # 2. Text slide-up with clipping to badge interior
    t_text = clamp((t - 0.25) / 0.75)
    if t_text > 0:
        y_slide = int((1.0 - ease(t_text)) * 42)
        text_surf = Image.new('RGBA', (card_w, card_h), (0, 0, 0, 0))
        t_draw = ImageDraw.Draw(text_surf)
        
        # Draw text centered vertically and horizontally
        b = t_draw.textbbox((0, 0), title, font=font)
        tx = (card_w - (b[2] - b[0])) // 2
        ty = (card_h - (b[3] - b[1])) // 2 + y_slide - 3
        t_draw.text((tx, ty), title, font=font, fill=(255, 255, 255, int(255 * ease(t_text))))
        
        # Paste inside badge
        overlay.alpha_composite(text_surf, (cx - card_w // 2, cy - card_h // 2))
        
    overlay_np = np.asarray(overlay)
    o_alpha = (overlay_np[:, :, 3].astype(np.float32) / 255.0)[:, :, None]
    o_bgr = cv2.cvtColor(overlay_np[:, :, :3], cv2.COLOR_RGB2BGR).astype(np.float32)
    frame[:] = np.clip(frame.astype(np.float32) * (1.0 - o_alpha) + o_bgr * o_alpha, 0, 255).astype(np.uint8)

def draw_badge_elastic_pop_flare(frame, title, cx, cy, accent_rgb, accent_bgr, progress):
    H, W = frame.shape[:2]
    t = clamp((progress - 0.16) / 0.26)
    if t <= 0: return
    
    font = ImageFont.truetype(FONT_PATH, 44)
    tw = font.getlength(title)
    card_w = max(260, int(tw + 70))
    card_h = 72
    
    # Spring physics
    spring_s = 1.0 + 0.38 * math.exp(-6.5 * t) * math.cos(math.pi * 3.2 * t) if t < 1.0 else 1.0
    spring_y = -40.0 * math.exp(-7.0 * t) * math.cos(math.pi * 2.2 * t) if t < 1.0 else 0.0
    
    w_cur = int(card_w * spring_s)
    h_cur = int(card_h * spring_s)
    cy_cur = int(cy + spring_y)
    
    x0 = int(cx - w_cur // 2)
    y0 = int(cy_cur - h_cur // 2)
    x1 = x0 + w_cur
    y1 = y0 + h_cur
    
    # Flare intensity on impact (t ~ 0.4 to 0.7)
    flare = max(0.0, 1.0 - abs(t - 0.45) / 0.22)
    border_w = 4 if flare > 0.4 else 2
    
    # Outer glow with flare burst
    glow_strength = 0.32 + 0.45 * flare
    glow_mask = np.zeros((H, W), dtype=np.uint8)
    cv2.rectangle(glow_mask, (max(0, x0-8), max(0, y0-8)), (min(W-1, x1+8), min(H-1, y1+8)), 255, -1)
    glow_blur = cv2.GaussianBlur(glow_mask, (0, 0), int(16 + 18 * flare)).astype(np.float32) / 255.0
    
    for c in range(3):
        frame[:, :, c] = np.clip(frame[:, :, c].astype(np.float32) * (1.0 - glow_blur * glow_strength) + accent_bgr[c] * (glow_blur * glow_strength), 0, 255).astype(np.uint8)
        
    overlay = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    alpha = clamp(t / 0.25)
    
    # Draw pill
    draw.rounded_rectangle([x0, y0, x1, y1], radius=h_cur//2, fill=(8, 14, 22, int(230 * alpha)), outline=(accent_rgb[0], accent_rgb[1], accent_rgb[2], int(255 * alpha)), width=border_w)
    
    # Draw text scaled with spring
    font_scaled = ImageFont.truetype(FONT_PATH, int(44 * spring_s))
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

def draw_badge_tracking_expansion(frame, title, cx, cy, accent_rgb, accent_bgr, progress):
    H, W = frame.shape[:2]
    t = clamp((progress - 0.16) / 0.24)
    if t <= 0: return
    
    font = ImageFont.truetype(FONT_PATH, 42)
    # Tracking smoothly expands from -2px to +14px
    tracking = -2.0 + 16.0 * ease(t)
    
    # Calculate tracked text width
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
    
    # Soft background glow
    glow_mask = np.zeros((H, W), dtype=np.uint8)
    cv2.rectangle(glow_mask, (max(0, x0-4), max(0, y0-4)), (min(W-1, x1+4), min(H-1, y1+4)), 255, -1)
    glow_blur = cv2.GaussianBlur(glow_mask, (0, 0), 16).astype(np.float32) / 255.0
    for c in range(3):
        frame[:, :, c] = np.clip(frame[:, :, c].astype(np.float32) * (1.0 - glow_blur * 0.3 * alpha) + accent_bgr[c] * (glow_blur * 0.3 * alpha), 0, 255).astype(np.uint8)
        
    overlay = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    
    # Dark black pill
    draw.rounded_rectangle([x0, y0, x1, y1], radius=card_h//2, fill=(8, 14, 22, int(225 * alpha)), outline=(accent_rgb[0], accent_rgb[1], accent_rgb[2], int(255 * alpha)), width=2)
    draw.rounded_rectangle([x0+4, y0+3, x1-4, y0+card_h//2-2], radius=card_h//4, fill=(255, 255, 255, int(15 * alpha)))
    
    # Draw tracked letters
    cursor = cx - tw_tracked // 2
    ty = y0 + (card_h - 40) // 2 - 2
    for ch in title:
        draw.text((cursor, ty), ch, font=font, fill=(255, 255, 255, int(255 * alpha)))
        cursor += font.getlength(ch) + tracking
        
    # Gentle breathing accent dot at right edge
    dot_pulse = 0.6 + 0.4 * math.sin(progress * 8.0)
    dot_alpha = int(255 * alpha * dot_pulse)
    draw.ellipse([x1 - 24, y0 + card_h//2 - 4, x1 - 16, y0 + card_h//2 + 4], fill=(accent_rgb[0], accent_rgb[1], accent_rgb[2], dot_alpha))
    
    overlay_np = np.asarray(overlay)
    o_alpha = (overlay_np[:, :, 3].astype(np.float32) / 255.0)[:, :, None]
    o_bgr = cv2.cvtColor(overlay_np[:, :, :3], cv2.COLOR_RGB2BGR).astype(np.float32)
    frame[:] = np.clip(frame.astype(np.float32) * (1.0 - o_alpha) + o_bgr * o_alpha, 0, 255).astype(np.uint8)

def draw_badge_typewriter_cursor(frame, title, cx, cy, accent_rgb, accent_bgr, progress):
    H, W = frame.shape[:2]
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
    
    # Typewriter progression
    t_type = clamp((t - 0.15) / 0.75)
    num_chars = int(t_type * (len(title) + 1))
    visible_text = title[:num_chars]
    
    # Text position
    b = draw.textbbox((0, 0), title, font=font)
    total_w = b[2] - b[0]
    tx0 = cx - total_w // 2
    ty = y0 + (card_h - (b[3] - b[1])) // 2 - 3
    
    draw.text((tx0, ty), visible_text, font=font, fill=(255, 255, 255, int(255 * alpha)))
    
    # Blinking / pulsing neon cursor
    cur_w = font.getlength(visible_text)
    cur_x = tx0 + cur_w + 3
    if t_type < 1.0 or (int(progress * 15) % 2 == 0):
        draw.rectangle([cur_x, ty + 6, cur_x + 9, ty + 40], fill=(accent_rgb[0], accent_rgb[1], accent_rgb[2], int(255 * alpha)))
        
    overlay_np = np.asarray(overlay)
    o_alpha = (overlay_np[:, :, 3].astype(np.float32) / 255.0)[:, :, None]
    o_bgr = cv2.cvtColor(overlay_np[:, :, :3], cv2.COLOR_RGB2BGR).astype(np.float32)
    frame[:] = np.clip(frame.astype(np.float32) * (1.0 - o_alpha) + o_bgr * o_alpha, 0, 255).astype(np.uint8)

print("Functions loaded successfully!")

# Generate preview frames
cap = cv2.VideoCapture(os.path.join(BASE_DIR, "ChrononTemplate/out/map_image_v1_opencv/renders/map_image_italy_beacon_arrival.mp4"))
cap.set(cv2.CAP_PROP_POS_FRAMES, 35) # During transition
ret, f_early = cap.read()
cap.set(cv2.CAP_PROP_POS_FRAMES, 75) # Settled
ret, f_late = cap.read()
cap.release()

accent_rgb = (255, 130, 118)
accent_bgr = (118, 130, 255)
cx, cy = 980, 460

# We need a clean frame without the old badge for previewing.
# In the actual video generator, it draws over the raw basemap!
print("Ready to integrate into video renderer.")
