import os
import json
import urllib.request
import re

OUT_DIR = r"C:\Users\pater\Pyt\ChrononTemplate\assets\icons"
os.makedirs(OUT_DIR, exist_ok=True)

HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}

lucide_icons = [
    "cpu", "brain", "rocket", "globe", "atom", "satellite", 
    "zap", "flame", "shield", "activity", "database", 
    "sparkles", "radar", "telescope", "compass", "dna"
]

print(f"Downloading {len(lucide_icons)} Lucide vector SVGs...")
for icon in lucide_icons:
    url = f"https://raw.githubusercontent.com/lucide-icons/lucide/main/icons/{icon}.svg"
    out_path = os.path.join(OUT_DIR, f"{icon}.svg")
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req) as resp, open(out_path, "wb") as f:
            f.write(resp.read())
        print(f"  [OK] {icon}.svg ({os.path.getsize(out_path)} bytes)")
    except Exception as e:
        print(f"  [ERR] {icon}: {e}")

# Transparent PNG assets (tech / badges / planetary / cyber)
png_urls = [
    ("nasa_insignia.png", "https://upload.wikimedia.org/wikipedia/commons/e/e5/NASA_logo.svg"), # we can also fetch real PNGs
    ("apollo11.png", "https://upload.wikimedia.org/wikipedia/commons/thumb/2/27/Apollo_11_insignia.png/600px-Apollo_11_insignia.png"),
    ("voyager_golden_record.png", "https://upload.wikimedia.org/wikipedia/commons/thumb/5/56/Voyager_Golden_Record_Cover.png/600px-Voyager_Golden_Record_Cover.png"),
    ("hologram_reticle.png", "https://raw.githubusercontent.com/FortAwesome/Font-Awesome/master/svgs/solid/crosshairs.svg")
]

print("\nDownloading High-Quality Transparent PNG assets...")
for name, url in [
    ("apollo11_badge.png", "https://upload.wikimedia.org/wikipedia/commons/thumb/2/27/Apollo_11_insignia.png/600px-Apollo_11_insignia.png"),
    ("voyager_record.png", "https://upload.wikimedia.org/wikipedia/commons/thumb/5/56/Voyager_Golden_Record_Cover.png/600px-Voyager_Golden_Record_Cover.png"),
    ("earth_globe.png", "https://upload.wikimedia.org/wikipedia/commons/thumb/2/22/Earth_Western_Hemisphere_transparent_background.png/600px-Earth_Western_Hemisphere_transparent_background.png"),
    ("moon_transparent.png", "https://upload.wikimedia.org/wikipedia/commons/thumb/e/e1/FullMoon2010.png/600px-FullMoon2010.png")
]:
    out_path = os.path.join(OUT_DIR, name)
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req) as resp, open(out_path, "wb") as f:
            f.write(resp.read())
        print(f"  [OK] {name} ({os.path.getsize(out_path)} bytes)")
    except Exception as e:
        print(f"  [ERR] {name}: {e}")

print("Download complete.")
