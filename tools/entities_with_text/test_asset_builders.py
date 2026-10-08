import math
from PIL import Image, ImageDraw, ImageFilter, ImageOps
import numpy as np
from pathlib import Path

out_dir = Path("ChrononTemplate/out/modern_entities_with_text/assets")
out_dir.mkdir(parents=True, exist_ok=True)

# 1. Build Studio Light Background (1920x1080)
w, h = 1920, 1080
bg = Image.new("RGBA", (w, h), (218, 218, 222, 255))
# Radial gradient overlay
x = np.linspace(-1, 1, w)
y = np.linspace(-1, 1, h)
xx, yy = np.meshgrid(x, y)
r = np.sqrt(xx**2 + (yy * 1.3)**2)
# center is brighter (235), edges darker (160)
val = np.clip(236 - r * 75, 145, 245).astype(np.uint8)
bg_arr = np.dstack([val, val, val + 2, np.full((h, w), 255, dtype=np.uint8)])
bg_img = Image.fromarray(bg_arr, mode="RGBA")
bg_img.save(out_dir / "studio_light_bg.png")
print("Generated studio_light_bg.png")

# 2. Build Curved CRT Widescreen Mask (Width: 1440, Height: 810)
# Top edge dips in center, bottom edge curves up in center
SW, SH = 1440, 810
scale = 2
MW, MH = SW * scale, SH * scale
mask_img = Image.new("L", (MW, MH), 0)
draw = ImageDraw.Draw(mask_img)

curve_dip = 34 * scale  # amount top dips and bottom rises in center
corner_r = 70 * scale

# Build polygon points along perimeter
pts = []
num_steps = 100

# Top edge from left to right (with rounded corners)
# x goes from corner_r to MW - corner_r
for i in range(num_steps + 1):
    t = i / num_steps
    px = corner_r + t * (MW - 2 * corner_r)
    # parabolic dip: 0 at ends, curve_dip at center
    # normalized u in [-1, 1]
    u = (t - 0.5) * 2.0
    py = curve_dip * (1.0 - u**2)
    pts.append((px, py))

# Right top corner arc to right edge
# Right edge from top to bottom
for i in range(num_steps + 1):
    t = i / num_steps
    py = corner_r + t * (MH - 2 * corner_r)
    # slight barrel bulge on sides
    v = (t - 0.5) * 2.0
    px = MW - (10 * scale) * (1.0 - v**2)
    pts.append((px, py))

# Bottom edge from right to left
for i in range(num_steps + 1):
    t = i / num_steps
    px = (MW - corner_r) - t * (MW - 2 * corner_r)
    u = (0.5 - t) * 2.0
    py = MH - curve_dip * (1.0 - u**2)
    pts.append((px, py))

# Left edge from bottom to top
for i in range(num_steps + 1):
    t = i / num_steps
    py = (MH - corner_r) - t * (MH - 2 * corner_r)
    v = (0.5 - t) * 2.0
    px = (10 * scale) * (1.0 - v**2)
    pts.append((px, py))

draw.polygon(pts, fill=255)

# Round corners by blurring boundary or drawing corner rounds
mask_smooth = mask_img.filter(ImageFilter.GaussianBlur(radius=corner_r // 2))
# threshold to get smooth round corners
mask_arr = np.array(mask_smooth)
final_mask_arr = np.where(mask_arr > 120, 255, 0).astype(np.uint8)
final_mask_hi = Image.fromarray(final_mask_arr, mode="L").filter(ImageFilter.GaussianBlur(radius=scale))
final_mask = final_mask_hi.resize((SW, SH), Image.Resampling.LANCZOS)
final_mask.save(out_dir / "curved_crt_mask.png")
print("Generated curved_crt_mask.png")

