"""PIL-based texture assets for the Youtuberstle scenes.

Run with the SYSTEM python3 (Blender's python has no PIL):
    python3 text_assets.py
Scene scripts only load the generated PNGs from ./assets.
"""
import os

ASSETS = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'assets')
FONT_DIR = '/mnt/c/Users/pater/Pyt/Chronon3d/assets/fonts'


def _fnt(name, size):
    from PIL import ImageFont
    return ImageFont.truetype(os.path.join(FONT_DIR, name), size)


# ------------------------------------------------------------------ scene 02

def s02_polaroid(seed):
    from PIL import Image, ImageDraw
    W, H = 520, 620
    img = Image.new('RGB', (W, H), (232, 230, 224))
    d = ImageDraw.Draw(img)
    fnt = _fnt('Inter-Regular.ttf', 34)
    d.rectangle([40, 40, W - 40, H - 170], fill=(28 + seed * 9 % 30, 28 + seed * 7 % 30, 30 + seed * 5 % 26))
    for i in range(6):
        x = 60 + (i * 71 + seed * 37) % (W - 190)
        y = 120 + (i * 97 + seed * 23) % (H - 380)
        d.ellipse([x, y, x + 52, y + 64], fill=(96 + i * 14, 96 + i * 12, 98 + i * 13))
    d.text((W // 2, H - 120), f'ARCHIVE {seed:02d}', font=fnt, fill=(70, 70, 72), anchor='ma')
    img.save(os.path.join(ASSETS, f's02_pola{seed - 3}.png'))


def s02_title():
    from PIL import Image, ImageDraw
    W, H = 1900, 900
    img = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    f1 = _fnt('Inter-Bold.ttf', 132)
    f2 = _fnt('Inter-Bold.ttf', 88)
    d.text((120, 200), 'SOME CONSPIRACY THEORIES', font=f1, fill=(196, 32, 38, 255))
    d.text((120, 400), 'THAT TURNED OUT TRUE.', font=f2, fill=(232, 228, 222, 255))
    d.text((1180, 560), 'PART 2', font=f2, fill=(232, 228, 222, 255))
    img.save(os.path.join(ASSETS, 's02_title.png'))


def s02_tv():
    from PIL import Image, ImageDraw
    W, H = 1000, 720
    img = Image.new('RGB', (W, H), (10, 10, 12))
    d = ImageDraw.Draw(img)
    fnt = _fnt('Inter-Bold.ttf', 118)
    d.text((W // 2, 110), 'THIS IS', font=fnt, fill=(226, 222, 214), anchor='ma')
    d.text((W // 2 + 60, 260), 'REAL', font=fnt, fill=(232, 196, 40), anchor='ma')
    d.polygon([(250, 640), (500, 380), (750, 640)], outline=(46, 120, 60), width=14)
    d.ellipse([420, 470, 580, 600], outline=(70, 200, 120), width=12)
    d.ellipse([478, 512, 522, 558], fill=(40, 180, 90))
    for i in range(14):
        x = 120 + i * 58
        d.polygon([(x, 700), (x + 26, 640), (x + 52, 700)], fill=(150, 26, 30))
    img.save(os.path.join(ASSETS, 's02_tv.png'))


# ------------------------------------------------------------------ scene 03

def s03_grid():
    from PIL import Image, ImageDraw, ImageFilter
    W, H = 1920, 1080
    img = Image.new('RGB', (W, H), (14, 14, 18))
    d = ImageDraw.Draw(img)
    cols = [(180, 46, 40), (40, 70, 160), (150, 110, 30), (60, 130, 70), (140, 50, 120),
            (40, 120, 140), (170, 90, 30), (90, 40, 150), (50, 150, 90)]
    for r in range(3):
        for c in range(4):
            x, y = c * 480 + 8, r * 360 + 8
            base = cols[(r * 4 + c) % len(cols)]
            d.rectangle([x, y, x + 464, y + 344], fill=base)
            d.rectangle([x + 60, y + 70, x + 400, y + 200], fill=tuple(min(255, v + 60) for v in base))
            d.rectangle([x + 20, y + 280, x + 340, y + 310], fill=(235, 235, 235))
    img = img.filter(ImageFilter.GaussianBlur(6))
    img.save(os.path.join(ASSETS, 's03_grid.png'))


def s03_channel():
    from PIL import Image, ImageDraw
    W, H = 1920, 1080
    img = Image.new('RGB', (W, H), (16, 16, 20))
    d = ImageDraw.Draw(img)
    fb = _fnt('Inter-Bold.ttf', 92)
    fr = _fnt('Inter-Regular.ttf', 46)
    fs = _fnt('Inter-Bold.ttf', 52)
    d.rectangle([0, 0, W, 300], fill=(38, 30, 22))
    d.text((420, 90), 'Visual', font=fb, fill=(240, 200, 90))
    d.text((760, 90), 'internet culture', font=fb, fill=(240, 200, 90))
    d.ellipse([330, 330, 560, 560], fill=(60, 60, 66))
    d.ellipse([365, 375, 525, 535], fill=(120, 105, 95))
    d.text((610, 340), 'Visual Venture', font=fb, fill=(245, 245, 245))
    d.text((610, 470), '@VisualVenture', font=fr, fill=(170, 170, 175))
    d.text((610, 550), '"My mission is to make the world a better place."', font=fr, fill=(215, 215, 215))
    d.rounded_rectangle([610, 650, 1000, 750], radius=50, fill=(245, 245, 245))
    d.text((805, 672), 'Subscribe', font=fs, fill=(20, 20, 20), anchor='ma')
    d.line([330, 850, 1590, 850], fill=(60, 60, 64), width=4)
    d.text((330, 890), 'Home     Videos     Shorts     Playlists     Posts', font=fr, fill=(200, 200, 205))
    img.save(os.path.join(ASSETS, 's03_channel.png'))


# ------------------------------------------------------------------ scene 04

def s04_title():
    from PIL import Image, ImageDraw
    W, H = 1600, 420
    img = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    fnt = _fnt('Inter-Bold.ttf', 190)
    d.text((W // 2, 210), 'CHAPTER 1', font=fnt, fill=(255, 244, 240, 255), anchor='mm')
    img.save(os.path.join(ASSETS, 's04_title.png'))


# ------------------------------------------------------------------ scene 05

def s05_flag():
    from PIL import Image, ImageDraw
    W, H = 600, 400
    img = Image.new('RGB', (W, H), (150, 26, 30))
    d = ImageDraw.Draw(img)
    d.ellipse([240, 110, 360, 230], outline=(240, 190, 40), width=16)
    d.line([270, 90, 330, 250], fill=(240, 190, 40), width=16)
    d.line([230, 150, 370, 150], fill=(240, 190, 40), width=10)
    img.save(os.path.join(ASSETS, 's05_flag.png'))


ALL = {
    's02_title.png': s02_title,
    's02_tv.png': s02_tv,
    's03_grid.png': s03_grid,
    's03_channel.png': s03_channel,
    's04_title.png': s04_title,
    's05_flag.png': s05_flag,
}


def generate_all():
    os.makedirs(ASSETS, exist_ok=True)
    for i in range(4):
        s02_polaroid(i + 3)
    for name, fn in ALL.items():
        fn()
        print('generated', name)


if __name__ == '__main__':
    generate_all()
