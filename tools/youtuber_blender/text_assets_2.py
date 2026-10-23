"""PIL texture assets for scenes 06-20. Run with system python3."""
import os
import math

ASSETS = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'assets')
FONT_DIR = '/mnt/c/Users/pater/Pyt/Chronon3d/assets/fonts'


def _fnt(name, size):
    from PIL import ImageFont
    return ImageFont.truetype(os.path.join(FONT_DIR, name), size)


def s06_seal():
    from PIL import Image, ImageDraw
    W, H = 1400, 1400
    img = Image.new('RGB', (W, H), (26, 42, 120))
    d = ImageDraw.Draw(img)
    d.ellipse([60, 60, W - 60, H - 60], outline=(210, 180, 60), width=18)
    d.rectangle([430, 350, 970, 1080], fill=(238, 236, 230))
    # red compass star
    cx, cy = 700, 700
    for i in range(16):
        a = i * math.pi / 8
        r1 = 250 if i % 2 == 0 else 95
        d.polygon([(cx, cy),
                   (cx + r1 * math.cos(a - 0.12), cy + r1 * math.sin(a - 0.12)),
                   (cx + r1 * math.cos(a + 0.12), cy + r1 * math.sin(a + 0.12))],
                  fill=(168, 22, 28))
    f = _fnt('Inter-Bold.ttf', 96)
    d.text((W // 2, 120), 'AGENCY', font=f, fill=(225, 215, 190), anchor='ma')
    img.save(os.path.join(ASSETS, 's06_seal.png'))


def _paper(W, H, bg=(233, 231, 224)):
    from PIL import Image, ImageDraw
    img = Image.new('RGB', (W, H), bg)
    d = ImageDraw.Draw(img)
    return img, d


def s09_doc():
    img, d = _paper(1800, 1200)
    f = _fnt('Georgia_Bold.ttf', 74)
    fr = _fnt('Georgia_Bold.ttf', 60)
    d.text((120, 120), '"Stargate Project".', font=f, fill=(60, 60, 62))
    d.text((120, 330), 'primarily involved ', font=fr, fill=(70, 70, 72))
    d.text((640, 330), 'remote viewing', font=fr, fill=(40, 70, 150))
    d.text((120, 500), 'project was overseen until 1987 by Lt.', font=fr, fill=(70, 70, 72))
    d.text((120, 670), 'Albert Stubblebine, and later president', font=fr, fill=(70, 70, 72))
    img.save(os.path.join(ASSETS, 's09_doc.png'))


def s10_doc():
    img, d = _paper(1800, 1000)
    f = _fnt('Georgia_Bold.ttf', 88)
    fr = _fnt('Georgia_Bold.ttf', 58)
    d.text((300, 140), 'Over the years more than 20 psychics were employed.', font=f, fill=(30, 30, 32))
    d.text((300, 350), 'some ended up in psychiatric hospitals, others', font=fr, fill=(110, 110, 112))
    d.text((300, 500), 'obsessed with crop circles and aliens.', font=fr, fill=(110, 110, 112))
    img.save(os.path.join(ASSETS, 's10_doc.png'))


def s11_title():
    from PIL import Image, ImageDraw
    W, H = 1600, 900
    img = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    f1 = _fnt('Inter-Bold.ttf', 92)
    f2 = _fnt('Inter-Bold.ttf', 130)
    d.text((W // 2, 260), '1979', font=f1, fill=(235, 232, 226, 255), anchor='mm')
    d.text((W // 2, 470), 'PROJECT STARGATE CHALLENGE', font=f2, fill=(240, 196, 40, 255), anchor='mm')
    img.save(os.path.join(ASSETS, 's11_title.png'))


def s12_map():
    from PIL import Image, ImageDraw
    W, H = 1000, 800
    img = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([40, 40, W - 40, H - 40], radius=60, outline=(240, 150, 40), width=18)
    pts = [(150, 600), (300, 420), (480, 500), (620, 300), (820, 380)]
    for a, b in zip(pts, pts[1:]):
        d.line([a, b], fill=(240, 150, 40), width=10)
    d.ellipse([800, 330, 870, 400], outline=(240, 150, 40), width=12)
    img.save(os.path.join(ASSETS, 's12_map.png'))


def s13_news():
    img, d = _paper(1200, 1500, (228, 226, 218))
    f = _fnt('Georgia_Bold.ttf', 86)
    fr = _fnt('Georgia_Bold.ttf', 44)
    d.text((600, 120), 'The Washington Post', font=f, fill=(40, 40, 42), anchor='ma')
    d.line([80, 240, 1120, 240], fill=(60, 60, 60), width=5)
    d.text((600, 320), 'Voodoo Gap', font=f, fill=(30, 30, 32), anchor='ma')
    d.text((600, 440), 'Looms as Latest', font=f, fill=(30, 30, 32), anchor='ma')
    d.text((600, 560), 'Weapons Crisis', font=f, fill=(30, 30, 32), anchor='ma')
    for i in range(12):
        d.line([90, 700 + i * 58, 1110, 700 + i * 58], fill=(90, 90, 92), width=14)
    img.save(os.path.join(ASSETS, 's13_news.png'))


def s14_nyt():
    img, d = _paper(1800, 1200, (222, 220, 212))
    f = _fnt('Georgia_Bold.ttf', 108)
    fr = _fnt('Georgia_Bold.ttf', 56)
    d.text((900, 140), 'Science Times', font=f, fill=(40, 40, 42), anchor='ma')
    d.text((240, 330), 'Pentagon Is Said to Have', font=fr, fill=(40, 40, 42))
    d.text((240, 430), 'Checked War Psychics', font=fr, fill=(40, 40, 42))
    d.text((950, 330), 'A Powerful New Tool', font=f, fill=(35, 35, 37))
    for i in range(8):
        d.line([950, 520 + i * 56, 1740, 520 + i * 56], fill=(95, 95, 97), width=13)
    for i in range(5):
        d.line([240, 600 + i * 56, 860, 600 + i * 56], fill=(95, 95, 97), width=13)
    img.save(os.path.join(ASSETS, 's14_nyt.png'))


def s15_memo():
    img, d = _paper(1800, 1100, (226, 224, 216))
    fr = _fnt('Georgia_Bold.ttf', 62)
    d.text((110, 120), 'A Defense Department spokesman said', font=fr, fill=(48, 48, 50))
    d.text((110, 260), 'last week that officials', font=fr, fill=(48, 48, 50))
    d.text((110, 400), '1984 "and can find no monies that have been', font=fr, fill=(48, 48, 50))
    d.text((110, 540), 'spent for E.S.P. programs." But in an interview', font=fr, fill=(48, 48, 50))
    d.text((110, 680), 'Defense Intelligence Agency indicated that', font=fr, fill=(120, 120, 122))
    img.save(os.path.join(ASSETS, 's15_memo.png'))


def s16_cards():
    from PIL import Image, ImageDraw
    W, H = 1600, 900
    img = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([340, 90, 1260, 620], radius=26, fill=(26, 42, 120, 255))
    f = _fnt('Inter-Bold.ttf', 108)
    d.text((800, 260), 'PROJECT', font=f, fill=(235, 232, 226, 255), anchor='mm')
    d.text((800, 420), 'STARGATE', font=f, fill=(235, 232, 226, 255), anchor='mm')
    f2 = _fnt('Inter-Bold.ttf', 72)
    d.text((800, 540), 'AND REMOTE VIEWING TECHNOLOGY', font=f2, fill=(215, 210, 200, 255), anchor='mm')
    f3 = _fnt('Inter-Bold.ttf', 120)
    d.text((800, 750), 'STAR GATE PROJECT TRUTH', font=f3, fill=(240, 196, 40, 255), anchor='mm')
    img.save(os.path.join(ASSETS, 's16_cards.png'))


def s18_google():
    img, d = _paper(1800, 1100, (250, 250, 252))
    f = _fnt('Inter-Bold.ttf', 76)
    fr = _fnt('Inter-Regular.ttf', 44)
    d.text((240, 110), 'Google', font=f, fill=(66, 100, 190))
    d.rounded_rectangle([420, 90, 1700, 190], radius=50, outline=(180, 180, 185), width=4)
    d.text((460, 112), 'STAR GATE PROJECT: AN OVERVIEW', font=fr, fill=(30, 30, 32))
    d.text((240, 280), 'All     Images     Videos     News     Forums', font=fr, fill=(90, 90, 95))
    d.line([220, 350, 1700, 350], fill=(210, 210, 215), width=3)
    d.text((240, 420), 'CIA (.gov)', font=fr, fill=(30, 30, 32))
    d.text((240, 500), 'STAR GATE PROJECT: AN OVERVIEW', font=f, fill=(70, 60, 190))
    d.text((240, 610), '(S/NF/SG/LIMDIS) Primary focus of the STAR GATE', font=fr, fill=(80, 80, 85))
    d.text((240, 690), 'parapsychological and related biophysical', font=fr, fill=(80, 80, 85))
    img.save(os.path.join(ASSETS, 's18_google.png'))


def s17_crt():
    from PIL import Image, ImageDraw
    W, H = 1400, 900
    img = Image.new('RGB', (W, H), (20, 60, 22))
    d = ImageDraw.Draw(img)
    f = _fnt('Inter-Bold.ttf', 130)
    d.text((W // 2, H // 2), 'Shutting down', font=f, fill=(80, 255, 110), anchor='mm')
    for y in range(0, H, 12):
        d.line([0, y, W, y], fill=(12, 40, 14), width=2)
    img.save(os.path.join(ASSETS, 's17_crt.png'))


def s18_fakenews():
    from PIL import Image, ImageDraw
    W, H = 1800, 600
    img = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    f = _fnt('Inter-Bold.ttf', 220)
    d.text((W // 2, H // 2), 'FAKE NEWS', font=f, fill=(255, 110, 110, 255), anchor='mm')
    # LED dot effect
    px = img.load()
    for y in range(0, H, 10):
        for x in range(0, W, 10):
            r, g, b, a = px[x, y]
            if a > 40 and (x // 10 + y // 10) % 2 == 0:
                px[x, y] = (0, 0, 0, 0)
    img.save(os.path.join(ASSETS, 's18_fakenews.png'))


def s20_globe():
    from PIL import Image, ImageDraw
    W = 1200
    img = Image.new('RGBA', (W, W), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.ellipse([60, 60, W - 60, W - 60], fill=(16, 20, 34, 255), outline=(200, 60, 60), width=10)
    # continents blobs
    d.polygon([(300, 350), (520, 300), (600, 420), (500, 560), (350, 540)], fill=(222, 218, 206, 255))
    d.polygon([(520, 560), (640, 540), (680, 700), (560, 830), (500, 700)], fill=(222, 218, 206, 255))
    d.polygon([(300, 350), (520, 300), (560, 380), (420, 460)], fill=(210, 40, 40, 255))
    d.ellipse([420, 330, 470, 380], fill=(240, 200, 40, 255))
    img.save(os.path.join(ASSETS, 's20_globe.png'))


ALL = {
    's06_seal.png': s06_seal, 's09_doc.png': s09_doc, 's10_doc.png': s10_doc,
    's11_title.png': s11_title, 's12_map.png': s12_map, 's13_news.png': s13_news,
    's14_nyt.png': s14_nyt, 's15_memo.png': s15_memo, 's16_cards.png': s16_cards,
    's17_crt.png': s17_crt, 's18_google.png': s18_google, 's18_fakenews.png': s18_fakenews,
    's20_globe.png': s20_globe,
}


def generate_all():
    os.makedirs(ASSETS, exist_ok=True)
    for name, fn in ALL.items():
        fn()
        print('generated', name)


if __name__ == '__main__':
    generate_all()
