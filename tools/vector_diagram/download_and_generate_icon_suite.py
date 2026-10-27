import os
import urllib.request
import re
import resvg_py
from PIL import Image, ImageFilter, ImageOps
import numpy as np

BASE_DIR = r"C:\Users\pater\Pyt\ChrononTemplate\assets\icons"
SVG_DIR = os.path.join(BASE_DIR, "svg")
PNG_WHITE_DIR = os.path.join(BASE_DIR, "png_white")
PNG_NEON_DIR = os.path.join(BASE_DIR, "png_neon")

for d in [SVG_DIR, PNG_WHITE_DIR, PNG_NEON_DIR]:
    os.makedirs(d, exist_ok=True)

HEADERS = {'User-Agent': 'Mozilla/5.0'}

# 1. Lucide icons list
lucide_icons = {
    "cpu": ("cyan", "#00F0FF"),
    "brain": ("magenta", "#FF007F"),
    "rocket": ("amber", "#FFB703"),
    "satellite": ("cyan", "#00F0FF"),
    "atom": ("cyan", "#00F0FF"),
    "globe": ("amber", "#FFB703"),
    "shield": ("emerald", "#00FF88"),
    "activity": ("coral", "#FF3366"),
    "database": ("purple", "#B5179E"),
    "zap": ("yellow", "#FFE600"),
    "flame": ("orange", "#FF5400"),
    "sparkles": ("gold", "#FFD700"),
    "radar": ("lime", "#70E000"),
    "telescope": ("amber", "#FFB703"),
    "compass": ("cyan", "#00F0FF"),
    "dna": ("magenta", "#FF007F")
}

# 2. Simple Icons list (tech / industry)
simple_icons = {
    "vulkan": ("red", "#E60000"),
    "cplusplus": ("blue", "#00599C"),
    "python": ("yellow", "#FFD43B"),
    "linux": ("gold", "#FCC624"),
    "nasa": ("cyan", "#00F0FF")
}

print("=== Step 1: Downloading Curated Vector SVGs ===")

# Download Lucide
for name, (theme, color) in lucide_icons.items():
    url = f"https://raw.githubusercontent.com/lucide-icons/lucide/main/icons/{name}.svg"
    svg_path = os.path.join(SVG_DIR, f"{name}.svg")
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req) as resp:
            content = resp.read().decode('utf-8')
        with open(svg_path, "w", encoding='utf-8') as f:
            f.write(content)
        print(f"  [OK] Lucide: {name}.svg")
    except Exception as e:
        print(f"  [FAIL] Lucide {name}: {e}")

# Download Simple Icons
for name, (theme, color) in simple_icons.items():
    url = f"https://cdn.jsdelivr.net/npm/simple-icons@v9/icons/{name}.svg"
    svg_path = os.path.join(SVG_DIR, f"{name}.svg")
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req) as resp:
            content = resp.read().decode('utf-8')
        with open(svg_path, "w", encoding='utf-8') as f:
            f.write(content)
        print(f"  [OK] SimpleIcon: {name}.svg")
    except Exception as e:
        print(f"  [FAIL] SimpleIcon {name}: {e}")

print("\n=== Step 2: Rasterizing 512x512 Transparent PNGs (Crisp White + Neon Glow) ===")

def hex_to_rgb(hex_str):
    hex_str = hex_str.lstrip('#')
    return tuple(int(hex_str[i:i+2], 16) for i in (0, 2, 4))

all_icons = {}
for k, v in lucide_icons.items():
    all_icons[k] = v[1]
for k, v in simple_icons.items():
    all_icons[k] = v[1]

for name, hex_color in all_icons.items():
    svg_path = os.path.join(SVG_DIR, f"{name}.svg")
    if not os.path.exists(svg_path):
        continue
    
    with open(svg_path, "r", encoding="utf-8") as f:
        raw_svg = f.read()

    # Create white version for rendering
    # Replace stroke="currentColor" or fill="currentColor" with "#FFFFFF"
    white_svg = raw_svg
    if 'stroke="currentColor"' in white_svg:
        white_svg = white_svg.replace('stroke="currentColor"', 'stroke="#FFFFFF"')
    if 'fill="currentColor"' in white_svg:
        white_svg = white_svg.replace('fill="currentColor"', 'fill="#FFFFFF"')
    if 'fill="none"' not in white_svg and 'fill=' not in white_svg:
        white_svg = white_svg.replace('<svg ', '<svg fill="#FFFFFF" ')

    # Ensure width and height are 512 without touching stroke-width!
    if re.search(r'(?<![-a-zA-Z])width="[^"]+"', white_svg):
        white_svg = re.sub(r'(?<![-a-zA-Z])width="[^"]+"', 'width="512"', white_svg)
    else:
        white_svg = white_svg.replace('<svg ', '<svg width="512" ')

    if re.search(r'(?<![-a-zA-Z])height="[^"]+"', white_svg):
        white_svg = re.sub(r'(?<![-a-zA-Z])height="[^"]+"', 'height="512"', white_svg)
    else:
        white_svg = white_svg.replace('<svg ', '<svg height="512" ')

    try:
        png_data = resvg_py.svg_to_bytes(svg_string=white_svg)
        white_png_path = os.path.join(PNG_WHITE_DIR, f"{name}.png")
        with open(white_png_path, "wb") as f:
            f.write(png_data)

        # Now load with PIL to create multi-pass neon bloom PNG
        img = Image.open(white_png_path).convert("RGBA")
        
        # Extract alpha as mask
        r, g, b, alpha = img.split()
        
        # Generate Neon Glow
        neon_rgb = hex_to_rgb(hex_color)
        
        # Glow base: colored silhouette
        glow_base = Image.new("RGBA", (512, 512), neon_rgb + (0,))
        glow_base.putalpha(alpha)

        # Multi-layer gaussian blur for deep glow
        b1 = glow_base.filter(ImageFilter.GaussianBlur(radius=4))
        b2 = glow_base.filter(ImageFilter.GaussianBlur(radius=12))
        b3 = glow_base.filter(ImageFilter.GaussianBlur(radius=28))
        b4 = glow_base.filter(ImageFilter.GaussianBlur(radius=64))

        # Composite glow passes
        glow = Image.new("RGBA", (512, 512), (0, 0, 0, 0))
        glow = Image.alpha_composite(glow, b4)
        glow = Image.alpha_composite(glow, b3)
        glow = Image.alpha_composite(glow, b2)
        glow = Image.alpha_composite(glow, b1)

        # Overlay crisp white core (tinted slightly with neon color)
        core_color = tuple(min(255, int(c * 0.3 + 255 * 0.7)) for c in neon_rgb)
        core_img = Image.new("RGBA", (512, 512), core_color + (0,))
        core_img.putalpha(alpha)
        
        final_neon = Image.alpha_composite(glow, core_img)
        neon_png_path = os.path.join(PNG_NEON_DIR, f"{name}_neon.png")
        final_neon.save(neon_png_path, format="PNG")

        print(f"  [OK] Rendered 512x512 {name}.png + {name}_neon.png")
    except Exception as e:
        print(f"  [FAIL] Render {name}: {e}")

print("\nAll icons downloaded and processed successfully!")
