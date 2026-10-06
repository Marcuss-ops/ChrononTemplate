import os
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

BASE_DIR = "/home/pierone/src/go-master/projects/Pyt/VeloxEditing"
FONTS_DIR = os.path.join(BASE_DIR, "Chronon3d/assets/fonts")

FONT_HERO = os.path.join(FONTS_DIR, "Bricolage-Grotesque.ttf")
FONT_SANS = os.path.join(FONTS_DIR, "Plus-Jakarta-Sans.ttf")
FONT_MONO = os.path.join(FONTS_DIR, "UbuntuMono-R.ttf")

# Load a clean frame of Italy
frame_path = os.path.join(BASE_DIR, "ChrononTemplate/out/map_image_v1_opencv/renders/test_italy_f90.png")
img_bgr = cv2.imread(frame_path)
H, W = img_bgr.shape[:2]

# Let's clean the old plain "ITALY" text by inpainting or masking, or drawing a fresh card over it!
# Center of Italy is roughly around cx=980, cy=460
cx, cy = 980, 460
accent_rgb = (255, 116, 105) # Italy Coral Neon #FF7469
accent_bgr = (105, 116, 255)

card_w, card_h = 440, 210
x0 = cx - card_w // 2
y0 = cy - card_h // 2
x1 = x0 + card_w
y1 = y0 + card_h

# 1. DRAW FROSTED GLASS BACKGROUND WITH GLOW AURA
# Create an RGBA overlay
overlay = np.zeros((H, W, 4), dtype=np.uint8)
pil_overlay = Image.fromarray(overlay)
draw = ImageDraw.Draw(pil_overlay)

# Outer glow around the card
glow_mask = np.zeros((H, W), dtype=np.uint8)
cv2.rectangle(glow_mask, (x0-4, y0-4), (x1+4, y1+4), 255, -1)
glow_blur = cv2.GaussianBlur(glow_mask, (0, 0), 24)

# Draw dark glass plinth: deep translucent navy/black
draw.rounded_rectangle([x0, y0, x1, y1], radius=22, fill=(8, 16, 26, 215), outline=(accent_rgb[0], accent_rgb[1], accent_rgb[2], 255), width=2)

# Inner subtle gloss highlight at top
draw.rounded_rectangle([x0+4, y0+4, x1-4, y0+38], radius=16, fill=(255, 255, 255, 18))

# 2. TYPOGRAPHY
# Kicker
font_kicker = ImageFont.truetype(FONT_SANS, 16)
kicker_text = "SOUTHERN EUROPE  ·  IT"
draw.text((x0 + 26, y0 + 18), kicker_text, font=font_kicker, fill=accent_rgb)

# Hero Title
font_hero = ImageFont.truetype(FONT_HERO, 74)
hero_text = "ITALY"
draw.text((x0 + 24, y0 + 44), hero_text, font=font_hero, fill=(255, 255, 255))

# Divider line
draw.line([x0 + 24, y0 + 138, x1 - 24, y0 + 138], fill=(accent_rgb[0], accent_rgb[1], accent_rgb[2], 90), width=1)

# Metadata / Capital
font_mono = ImageFont.truetype(FONT_MONO, 17)
meta_text = "CAPITAL: ROME  ·  41.9° N, 12.5° E"
draw.text((x0 + 26, y0 + 152), meta_text, font=font_mono, fill=(185, 205, 225))

# Mini neon indicator dot
draw.ellipse([x0 + card_w - 38, y0 + 22, x0 + card_w - 26, y0 + 34], fill=accent_rgb)

# Convert overlay back to numpy
overlay_np = np.asarray(pil_overlay)

# Composite glow into frame
glow_colored = np.zeros_like(img_bgr, dtype=np.float32)
for c in range(3):
    glow_colored[:, :, c] = accent_bgr[c]
glow_alpha = (glow_blur.astype(np.float32) / 255.0) * 0.45
frame_float = img_bgr.astype(np.float32)
frame_float = frame_float * (1.0 - glow_alpha[:, :, None]) + glow_colored * glow_alpha[:, :, None]

# Composite card overlay
card_alpha = (overlay_np[:, :, 3].astype(np.float32) / 255.0)[:, :, None]
card_bgr = cv2.cvtColor(overlay_np[:, :, :3], cv2.COLOR_RGB2BGR).astype(np.float32)

final_frame = frame_float * (1.0 - card_alpha) + card_bgr * card_alpha
final_bgr = np.clip(final_frame, 0, 255).astype(np.uint8)

out_path = os.path.join(BASE_DIR, "ChrononTemplate/out/test_super_figo_italy.png")
cv2.imwrite(out_path, final_bgr)
print(f"Generated design preview: {out_path}")
