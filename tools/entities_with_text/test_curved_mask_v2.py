import math
from PIL import Image, ImageDraw, ImageFilter
import numpy as np

W, H = 1440, 810
scale = 2
MW, MH = W * scale, H * scale

# We can also compute coordinate warp!
# For any point (x, y) on the canvas, map it through barrel/pincushion:
# A pincushion warp where top/bottom edges bend:
mask = Image.new("L", (MW, MH), 0)
draw = ImageDraw.Draw(mask)

# Or construct the polygon properly:
corner_r = 75 * scale
dip_y = 28 * scale
bulge_x = 8 * scale

# Generate points along the curved perimeter
pts = []

# 1. Top edge: from x = corner_r to MW - corner_r
n_edge = 60
for i in range(n_edge + 1):
    t = i / n_edge
    px = corner_r + t * (MW - 2 * corner_r)
    # normalized u from -1 to 1
    u = (px - MW/2) / (MW/2)
    py = dip_y * (1.0 - u**2)
    pts.append((px, py))

# Top-Right corner arc
cx_tr = MW - corner_r
cy_tr = corner_r + dip_y * (1.0 - ((cx_tr - MW/2)/(MW/2))**2)
for i in range(1, 20):
    ang = -math.pi/2 + (i / 20) * (math.pi/2)
    pts.append((cx_tr + corner_r * math.cos(ang), cy_tr + corner_r * math.sin(ang)))

# 2. Right edge: from y = corner_r to MH - corner_r
for i in range(n_edge + 1):
    t = i / n_edge
    py = corner_r + t * (MH - 2 * corner_r)
    v = (py - MH/2) / (MH/2)
    px = MW - (bulge_x * (1.0 - v**2))
    pts.append((px, py))

# Bottom-Right corner arc
cx_br = MW - corner_r
cy_br = MH - corner_r - dip_y * (1.0 - ((cx_br - MW/2)/(MW/2))**2)
for i in range(1, 20):
    ang = 0 + (i / 20) * (math.pi/2)
    pts.append((cx_br + corner_r * math.cos(ang), cy_br + corner_r * math.sin(ang)))

# 3. Bottom edge: from x = MW - corner_r down to corner_r
for i in range(n_edge + 1):
    t = i / n_edge
    px = (MW - corner_r) - t * (MW - 2 * corner_r)
    u = (px - MW/2) / (MW/2)
    py = MH - dip_y * (1.0 - u**2)
    pts.append((px, py))

# Bottom-Left corner arc
cx_bl = corner_r
cy_bl = MH - corner_r - dip_y * (1.0 - ((cx_bl - MW/2)/(MW/2))**2)
for i in range(1, 20):
    ang = math.pi/2 + (i / 20) * (math.pi/2)
    pts.append((cx_bl + corner_r * math.cos(ang), cy_bl + corner_r * math.sin(ang)))

# 4. Left edge: from y = MH - corner_r up to corner_r
for i in range(n_edge + 1):
    t = i / n_edge
    py = (MH - corner_r) - t * (MH - 2 * corner_r)
    v = (py - MH/2) / (MH/2)
    px = bulge_x * (1.0 - v**2)
    pts.append((px, py))

# Top-Left corner arc
cx_tl = corner_r
cy_tl = corner_r + dip_y * (1.0 - ((cx_tl - MW/2)/(MW/2))**2)
for i in range(1, 20):
    ang = math.pi + (i / 20) * (math.pi/2)
    pts.append((cx_tl + corner_r * math.cos(ang), cy_tl + corner_r * math.sin(ang)))

draw.polygon(pts, fill=255)

out = mask.resize((W, H), Image.Resampling.LANCZOS)
out.save("ChrononTemplate/out/modern_entities_with_text/assets/curved_crt_mask_v2.png")
print("Saved curved_crt_mask_v2.png")
