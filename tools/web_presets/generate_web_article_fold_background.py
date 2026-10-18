#!/usr/bin/env python3
"""Build a clean web article plate and leave its moving headline transparent."""
from PIL import Image, ImageDraw, ImageFilter, ImageFont
from pathlib import Path
import math
import random
import sys

out = Path(sys.argv[1])
W, H = 1920, 1080
rng = random.Random(18)

# Dark, out-of-focus context around the bright article page, matching the supplied video frame.
backdrop = Image.new("RGB", (W, H))
bp = backdrop.load()
for y in range(H):
    for x in range(W):
        nx = (x - W * .5) / (W * .67)
        ny = (y - H * .48) / (H * .72)
        glow = max(0.0, 1.0 - math.sqrt(nx * nx + ny * ny))
        v = int(19 + 12 * glow + rng.gauss(0, 1.1))
        bp[x, y] = (v, v + 1, v + 2)

# Soft, indistinct shapes suggest a webpage behind the focused article without adding readable UI.
ghost = Image.new("RGBA", (W, H), (0, 0, 0, 0))
gd = ImageDraw.Draw(ghost)
gd.rounded_rectangle((120, 100, 350, 900), radius=10, fill=(210, 213, 218, 24))
gd.rounded_rectangle((1580, 150, 1810, 870), radius=10, fill=(211, 214, 218, 22))
gd.rectangle((140, 125, 330, 150), fill=(255, 255, 255, 18))
gd.rectangle((1600, 180, 1785, 198), fill=(255, 255, 255, 16))
backdrop = Image.alpha_composite(backdrop.convert("RGBA"), ghost.filter(ImageFilter.GaussianBlur(22)))

# A straight-edged, bright article page, centered with a soft screen-like shadow.
page = (408, -10, 1512, 1090)
shadow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
ImageDraw.Draw(shadow).rectangle((page[0] + 6, page[1] + 2, page[2] + 6, page[3] + 2), fill=(0, 0, 0, 190))
backdrop = Image.alpha_composite(backdrop, shadow.filter(ImageFilter.GaussianBlur(30)))
draw = ImageDraw.Draw(backdrop)
draw.rectangle(page, fill=(250, 250, 249, 255))
draw.line((page[0], 0, page[0], H), fill=(224, 224, 222, 255), width=2)
draw.line((page[2], 0, page[2], H), fill=(224, 224, 222, 255), width=2)

root = Path(__file__).resolve().parents[2]
fonts = root / "out/web_article_fold/fonts"
bold = ImageFont.truetype(str(fonts / "Inter-Bold.ttf"), 17)
regular = ImageFont.truetype(str(fonts / "Inter-Regular.ttf"), 15)
body = ImageFont.truetype(str(fonts / "FreeSerif.ttf"), 21)
small = ImageFont.truetype(str(fonts / "Inter-Regular.ttf"), 13)

# Simple editorial masthead and metadata, like a full-page sports news article.
draw.text((453, 35), "SPORTS  /  NBA", font=bold, fill=(46, 61, 78, 255))
draw.text((1330, 37), "JAN 15, 2026   •   08:58 PM", font=small, fill=(106, 108, 111, 255))
draw.line((453, 72, 1467, 72), fill=(210, 212, 214, 255), width=2)

# The byline and article body stay softly defocused; the animated title is rendered separately.
copy = Image.new("RGBA", (W, H), (0, 0, 0, 0))
cd = ImageDraw.Draw(copy)
cd.text((453, 281), "ANTHONY SLATER AND SHAMS CHARANIA", font=bold, fill=(90, 92, 95, 245))
cd.text((453, 304), "Jan 15, 2026  ·  Reporting from San Francisco", font=small, fill=(126, 128, 130, 240))
cd.line((453, 342, 1467, 342), fill=(219, 220, 221, 255), width=1)
cd.text((453, 361), "↗  Share", font=small, fill=(87, 99, 111, 245))
cd.text((550, 361), "♡  Like", font=small, fill=(87, 99, 111, 245))
cd.text((1320, 361), "♥  4.0K", font=small, fill=(142, 89, 103, 235))
cd.line((453, 392, 1467, 392), fill=(226, 227, 228, 255), width=1)

def wrapped(text, font, max_width):
    rows, line = [], ""
    for word in text.split():
        candidate = (line + " " + word).strip()
        if line and font.getlength(candidate) > max_width:
            rows.append(line)
            line = word
        else:
            line = candidate
    if line:
        rows.append(line)
    return rows

left_copy = [
    "SAN FRANCISCO — On the first day he became eligible to be moved, fifth-year forward Jonathan Kuminga demanded a trade away from the Golden State Warriors, league sources told ESPN.",
    "Kuminga could not be traded until Thursday, according to the terms of the contract he signed this summer. The trade deadline is Feb. 5.",
    "Kuminga's roller-coaster tenure with the Warriors perhaps reached its lowest point after a difficult stretch in the rotation.",
    "He started the first 12 games of the season before a patch of struggles led to a demotion, landing poorly with the 23-year-old.",
]
right_copy = [
    "Kuminga has not seen the floor in the Warriors' past 13 games. Kerr buried him at the bottom of his deep rotation.",
    "Kuminga ruled himself out with back soreness an hour before a game against the Thunder on Jan. 2.",
    "The trade deadline is Feb. 5, according to the terms of the contract he signed this summer.",
]
for paragraphs, x, width in ((left_copy, 453, 500), (right_copy, 1000, 265)):
    y = 414
    for paragraph in paragraphs:
        for row in wrapped(paragraph, body, width):
            cd.text((x, y), row, font=body, fill=(86, 90, 95, 238))
            y += 30
        y += 18

# A quiet, blurred editorial recommendation sits in the right column, as in the reference.
cd.rectangle((1000, 730, 1467, 980), outline=(217, 219, 220, 235), width=1)
cd.text((1020, 750), "EDITOR'S PICKS", font=bold, fill=(111, 113, 115, 245))
cd.rectangle((1020, 785, 1080, 834), fill=(90, 119, 137, 220))
cd.text((1095, 786), "NBA trade buzz: moves that", font=small, fill=(66, 95, 125, 245))
cd.text((1095, 805), "could happen before deadline", font=small, fill=(66, 95, 125, 245))
cd.text((1095, 826), "ESPN  ·  NBA insiders", font=small, fill=(128, 130, 133, 230))
cd.line((1020, 852, 1445, 852), fill=(223, 224, 225, 235), width=1)
cd.rectangle((1020, 875, 1080, 924), fill=(114, 129, 138, 220))
cd.text((1095, 875), "Six trade proposals: how the", font=small, fill=(66, 95, 125, 245))
cd.text((1095, 894), "deadline could reshape the West", font=small, fill=(66, 95, 125, 245))
cd.text((1095, 915), "NBA insiders", font=small, fill=(128, 130, 133, 230))

backdrop = Image.alpha_composite(backdrop, copy.filter(ImageFilter.GaussianBlur(2.7)))
out.parent.mkdir(parents=True, exist_ok=True)
backdrop.convert("RGB").save(out, quality=96)
