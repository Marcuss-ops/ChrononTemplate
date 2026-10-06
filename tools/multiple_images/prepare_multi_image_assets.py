#!/usr/bin/env python3
"""
Prepares high-resolution, anti-aliased cards for multi-image suites:
- Trio (3 images): 500x680, radius 24
- Quad (4 images): 540x400, radius 20
- Penta (5 images): 320x580, radius 20

4x Lanczos anti-aliasing pre-baked in alpha mask; zero edge halo, zero letterboxing.
"""

from PIL import Image, ImageDraw
from pathlib import Path

BASE_DIR = Path("/home/pierone/src/go-master/projects/Pyt/VeloxEditing")
ASSETS_DIR = BASE_DIR / "Chronon3d/assets/images"

SOURCES = [
    "/home/pierone/.gemini/antigravity-cli/brain/b6e6745b-aa4c-4e2b-b3b2-bd8fca8d781a/dual_entity_person_a_1790783902866.jpg",
    str(ASSETS_DIR / "people_sample_portrait_b.png"),
    str(ASSETS_DIR / "premium_sample_portrait.png"),
    str(ASSETS_DIR / "camera_reference.jpg"),
    str(ASSETS_DIR / "minimalist_landscape.png")
]


def prepare_card(src_path, dst_path, target_w, target_h, radius=24):
    im = Image.open(src_path).convert("RGB")
    src_w, src_h = im.size
    
    target_aspect = target_w / target_h
    src_aspect = src_w / src_h
    
    if src_aspect > target_aspect:
        new_w = int(src_h * target_aspect)
        offset_x = (src_w - new_w) // 2
        im = im.crop((offset_x, 0, offset_x + new_w, src_h))
    else:
        new_h = int(src_w / target_aspect)
        offset_y = (src_h - new_h) // 2
        im = im.crop((0, offset_y, src_w, offset_y + new_h))
        
    w_2x, h_2x = target_w * 2, target_h * 2
    im = im.resize((w_2x, h_2x), Image.Resampling.LANCZOS).convert("RGBA")
    
    scale = 4
    mask = Image.new("L", (w_2x * scale, h_2x * scale), 0)
    draw = ImageDraw.Draw(mask)
    draw.rounded_rectangle((0, 0, w_2x * scale - 1, h_2x * scale - 1), radius=radius * 2 * scale, fill=255)
    mask = mask.resize((w_2x, h_2x), Image.Resampling.LANCZOS)
    im.putalpha(mask)
    
    im.save(dst_path)
    print(f"Baked {dst_path.name} ({w_2x}x{h_2x})")


def main():
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    
    # 1. Trio cards (3 items, 500x680)
    print("Baking Trio cards (500x680)...")
    for i in range(3):
        dst = ASSETS_DIR / f"card_trio_{i+1}.png"
        prepare_card(SOURCES[i], dst, 500, 680, radius=24)
        
    # 2. Quad cards (4 items, 540x400)
    print("Baking Quad cards (540x400)...")
    for i in range(4):
        dst = ASSETS_DIR / f"card_quad_{i+1}.png"
        prepare_card(SOURCES[i], dst, 540, 400, radius=20)
        
    # 3. Penta cards (5 items, 320x580)
    print("Baking Penta cards (320x580)...")
    for i in range(5):
        dst = ASSETS_DIR / f"card_penta_{i+1}.png"
        prepare_card(SOURCES[i], dst, 320, 580, radius=20)

    print("All multi-image card assets successfully generated.")


if __name__ == "__main__":
    main()
