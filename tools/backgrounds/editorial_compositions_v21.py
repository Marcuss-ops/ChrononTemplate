#!/usr/bin/env python3
"""V2.1 — reusable editorial compositions over any background plate.

Grid: margin 120px, content width 1680. Type scale: TITLE 88-96, SUB 36,
BODY 30, MICRO 24, QUOTE 64-68. No grey placeholders: deterministic
archival photo fixture. Animated items (title fade+shift, quote stagger,
underline trace, photo push) are emitted as ffmpeg overlay specs; everything
else is baked into the static plate. Only numpy+PIL, no new deps.
"""

from __future__ import annotations

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H = 1920, 1080
MARGIN = 120
FONTS = "/home/pierone/src/go-master/projects/Pyt/VeloxEditing/ChrononTemplate/assets/fonts"
FB = f"{FONTS}/Play-Bold.ttf"
FR = f"{FONTS}/Play-Regular.ttf"

TITLE, SUB, BODY, MICRO, QUOTE = 96, 36, 30, 24, 68


def font(bold: bool, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(FB if bold else FR, size)


# ------------------------------------------------------------- fixtures

def archival_photo_fixture(w: int = 440, h: int = 460, seed: int = 7) -> Image.Image:
    """Deterministic sepia 'street scene, 1962' fixture: sky gradient, sun
    glow, building silhouettes, street, two figures, grain + vignette."""
    rng = np.random.default_rng(seed)
    yy = np.linspace(0, 1, h, dtype=np.float32)[:, None]
    sky = np.zeros((h, w, 3), np.float32)
    sky[:, :] = (168, 142, 108)
    sky *= (0.75 + 0.45 * (1 - yy))[:, :, None] if False else 1.0
    sky = (np.array([168, 142, 108], np.float32)[None, None, :]
           * (1 - yy[:, :, None] * 0.45))
    im = Image.fromarray(np.clip(sky, 0, 255).astype(np.uint8)).convert("RGBA")
    d = ImageDraw.Draw(im, "RGBA")
    # sun glow
    for r in range(120, 10, -12):
        d.ellipse([w * 0.68 - r, h * 0.26 - r, w * 0.68 + r, h * 0.26 + r],
                  fill=(235, 215, 175, 14))
    # buildings
    bx = 0
    i = 0
    while bx < w:
        bw = int(rng.uniform(50, 110))
        bh = int(rng.uniform(h * 0.25, h * 0.55))
        tone = int(rng.uniform(38, 62))
        d.rectangle([bx, h * 0.62 - bh, bx + bw, h * 0.62], fill=(tone, tone - 6, tone - 14, 255))
        # windows
        for wy in range(int(h * 0.62 - bh + 8), int(h * 0.62 - 8), 14):
            for wx in range(int(bx + 6), int(bx + bw - 6), 12):
                if rng.random() > 0.45:
                    d.rectangle([wx, wy, wx + 5, wy + 7], fill=(215, 190, 150, 200))
        bx += bw + int(rng.uniform(2, 10))
        i += 1
    # street
    d.rectangle([0, h * 0.62, w, h], fill=(52, 44, 36, 255))
    d.line([(0, h * 0.78), (w, h * 0.78)], fill=(200, 180, 150, 120), width=2)
    # two figures
    for fx, fh in [(w * 0.34, 120), (w * 0.46, 104)]:
        d.ellipse([fx - 11, h * 0.78 - fh - 22, fx + 11, h * 0.78 - fh], fill=(28, 24, 20, 255))
        d.rounded_rectangle([fx - 13, h * 0.78 - fh, fx + 13, h * 0.78 - 6], radius=6, fill=(28, 24, 20, 255))
    # grain + vignette + softness
    g = rng.normal(0, 7, (h, w)).astype(np.float32)
    arr = np.asarray(im.convert("RGB"), dtype=np.float32) + g[:, :, None]
    im = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8)).convert("RGBA")
    vg = Image.new("L", (w, h), 0)
    vd = ImageDraw.Draw(vg)
    vd.ellipse([-w * 0.2, -h * 0.2, w * 1.2, h * 1.2], fill=255)
    vg = vg.filter(ImageFilter.GaussianBlur(40))
    im.putalpha(vg.point(lambda v: int(255 - (255 - v) * 0.35)))
    return im.filter(ImageFilter.GaussianBlur(0.4))


def framed_photo(size=(480, 600), seed: int = 7):
    """White-bordered photo card with caption strip; returns (card, inner_xy)."""
    cw, ch = size
    card = Image.new("RGBA", (cw, ch), (235, 232, 225, 255))
    ph = archival_photo_fixture(cw - 48, ch - 130, seed).resize((cw - 48, ch - 130))
    card.alpha_composite(ph, (24, 24))
    d = ImageDraw.Draw(card, "RGBA")
    f = font(False, 22)
    d.text((24, ch - 88), "ARCHIVE PHOTO - Via Roma, 1962", font=f, fill=(40, 38, 34, 255))
    d.text((24, ch - 56), "Plate 25 - restored print", font=f, fill=(90, 86, 78, 255))
    return card


# ------------------------------------------------------------- helpers

def text_w(draw: ImageDraw.ImageDraw, s: str, f) -> int:
    b = draw.textbbox((0, 0), s, font=f)
    return b[2] - b[0]


def underline_geom(draw, x: int, y_baseline: int, s: str, f, thick: int = 4, gap: int = 12):
    w = text_w(draw, s, f)
    asc, _ = f.getmetrics()
    y0 = y_baseline + gap
    return (x, y0, w, thick)


# ------------------------------------------------------------- compositions
# Each returns dict(plate=Image, photo=Image|None, anim={...}) where anim
# holds ffmpeg overlay specs with fixed params (documented in report).

def comp_A(bg: Image.Image, dark: bool, photo_card: Image.Image) -> dict:
    """DOCUMENTARY FEATURE: kicker, 2-line 96pt title, 36pt sub, rule,
    framed photo right. Animated: title fade+rise, underline trace, photo push."""
    ink = (245, 243, 238) if dark else (26, 25, 23)
    sub = (245, 243, 238, 220) if dark else (26, 25, 23, 210)
    plate = bg.copy()
    d = ImageDraw.Draw(plate, "RGBA")
    fk, ft, fs = font(True, MICRO), font(True, TITLE), font(False, SUB)
    d.text((MARGIN, 150), "DOCUMENTARY FEATURE", font=fk,
           fill=ink if isinstance(ink, tuple) and len(ink) == 3 else ink)
    d.line([(MARGIN, 196), (MARGIN + 120, 196)], fill=ink + (255,) if len(ink) == 3 else ink, width=4)
    # sub + rule baked (title animated via overlay)
    d.text((MARGIN, 470), "An investigation into the events", font=fs, fill=sub)
    d.text((MARGIN, 516), "that changed everything.", font=fs, fill=sub)
    d.line([(MARGIN, 590), (MARGIN + 200, 590)], fill=(ink[0], ink[1], ink[2], 110), width=2)
    # underline geometry under line-1 word "Hidden" (title drawn animated at same coords)
    t1 = "The Hidden Story"
    uw = text_w(d, "The ", ft)  # offset of "Hidden"
    hl_w = text_w(d, "Hidden", ft)
    asc, _ = ft.getmetrics()
    uy = 210 + asc + 16
    ug = (MARGIN + uw, uy, hl_w, 5)
    return {"plate": plate, "photo": photo_card, "theme": "dark" if dark else "ivory",
            "anim": {
                "title": {"text": t1, "size": TITLE, "x": MARGIN, "y": 210,
                          "fade_dur": 0.8, "rise_px": 18},
                "title2": {"text": "Episode 03", "size": SUB, "x": MARGIN, "y": 330,
                           "fade_dur": 0.8, "rise_px": 14, "delay": 0.25},
                "underline": {"x": ug[0], "y": ug[1], "w": ug[2], "h": ug[3],
                              "delay": 1.0, "dur": 0.6},
                "photo": {"x": 1290, "y": 300, "push_px": 16, "dur": 8.0},
                "ink": "#F5F3EE" if dark else "#1A1917"}}


def comp_B(bg: Image.Image, dark: bool) -> dict:
    """ARCHIVE DOCUMENT: title 88, body 30 x3, key sentence highlighted
    (flat box, no glow), underline trace under title."""
    ink = (245, 243, 238) if dark else (26, 25, 23)
    plate = bg.copy()
    d = ImageDraw.Draw(plate, "RGBA")
    fk, ft, fb = font(True, MICRO), font(True, 88), font(False, BODY)
    d.text((MARGIN, 150), "INSIDE THE REPORT", font=fk, fill=ink)
    body = ["The investigation uncovered a series of decisions",
            "that had remained out of public view for decades."]
    y = 500
    for line in body:
        d.text((MARGIN, y), line, font=fb, fill=ink)
        y += 52
    key = "The evidence was hidden in plain sight."
    kw = text_w(d, key, fb)
    box = (255, 250, 235) if dark else (30, 30, 34)
    txt = (20, 20, 22) if dark else (245, 243, 238)
    pad = 14
    d.rectangle([MARGIN - pad, y - 8, MARGIN + kw + pad, y + 44], fill=box + (255,))
    d.text((MARGIN, y), key, font=fb, fill=txt)
    asc, _ = font(True, 88).getmetrics()
    ug = (MARGIN, 150 + 44 + asc + 14, text_w(d, "Inside the Report", font(True, 88)), 5)
    return {"plate": plate, "photo": None, "theme": "dark" if dark else "ivory",
            "anim": {
                "title": {"text": "Inside the Report", "size": 88, "x": MARGIN, "y": 194,
                          "fade_dur": 0.7, "rise_px": 16},
                "underline": {"x": ug[0], "y": ug[1], "w": ug[2], "h": ug[3],
                              "delay": 0.9, "dur": 0.6},
                "ink": "#F5F3EE" if dark else "#1A1917"}}


def comp_C(bg: Image.Image, dark: bool) -> dict:
    """CINEMATIC QUOTE: 68pt two-line centered quote, staggered reveal."""
    ink = (245, 243, 238) if dark else (26, 25, 23)
    plate = bg.copy()
    d = ImageDraw.Draw(plate, "RGBA")
    fk = font(True, MICRO)
    label = "UNA CITAZIONE D'ARCHIVIO"
    lw = text_w(d, label, fk)
    d.text(((W - lw) / 2, 300), label, font=fk, fill=ink)
    return {"plate": plate, "photo": None, "theme": "dark" if dark else "ivory",
            "anim": {"lines": [
                {"text": "\u201cLa carta ricorda", "size": QUOTE, "y": 470, "delay": 0.3},
                {"text": "cio che la citta dimentica.\u201d", "size": QUOTE, "y": 560, "delay": 0.5},
                {"text": "- Archivio di Via Roma, 1962", "size": 26, "y": 700, "delay": 0.9, "attr": True}],
                "fade_dur": 0.6, "ink": "#F5F3EE" if dark else "#1A1917"}}


# ------------------------------------------------------------- stroke matrix

def stroke_matrix_plate() -> Image.Image:
    """Antialiased matrix (2x supersample): weights, curve, underline, taper."""
    S = 2
    im = Image.new("RGBA", (W * S, H * S), (13, 14, 17, 255))
    d = ImageDraw.Draw(im, "RGBA")
    fk = ImageFont.truetype(FB, MICRO * S)
    fr = ImageFont.truetype(FR, 30 * S)
    fb = ImageFont.truetype(FB, 44 * S)
    y = 120 * S
    d.text((120 * S, 60 * S), "STROKE QUALITY MATRIX - weights / curve / underline / taper / reveal", font=fk, fill=(200, 200, 205, 255))
    rows = [("0.75 px", 1.5), ("1.5 px", 3), ("3 px", 6), ("6 px", 12)]
    for label, px in rows:
        d.text((120 * S, y), label, font=fr, fill=(220, 220, 225, 255))
        d.line([(420 * S, y + 20 * S), (1800 * S, y + 20 * S)], fill=(240, 240, 245, 255), width=max(1, int(px)))
        y += 110 * S
    # curve (bezier approx)
    d.text((120 * S, y), "curva 3 px", font=fr, fill=(220, 220, 225, 255))
    pts = []
    import math
    for i in range(101):
        t = i / 100
        x = 420 + t * 1380
        yy = 40 * math.sin(t * math.pi * 2) - t * 30
        pts.append((x * S, (y / S + 20 + yy) * S))
    d.line(pts, fill=(240, 240, 245, 255), width=6, joint="curve")
    y += 130 * S
    # underline
    d.text((120 * S, y), "underline 4 px", font=fr, fill=(220, 220, 225, 255))
    s = "La carta ricorda"
    d.text((420 * S, y - 10 * S), s, font=fb, fill=(245, 243, 238, 255))
    b = d.textbbox((420 * S, y - 10 * S), s, font=fb)
    d.rectangle([b[0], b[3] + 8 * S, b[2], b[3] + 12 * S], fill=(240, 200, 120, 255))
    y += 130 * S
    # taper
    d.text((120 * S, y), "taper 8>1 px", font=fr, fill=(220, 220, 225, 255))
    d.polygon([(420 * S, y + 12 * S), (1800 * S, y + 19 * S), (1800 * S, y + 21 * S), (420 * S, y + 28 * S)], fill=(240, 240, 245, 255))
    return im.resize((W, H), Image.LANCZOS)
