#!/usr/bin/env python3
"""Rasterise the page plates used by the Match Cut fast intro (1920x1080 each).

Chronon owns all motion (camera whips, blur, pillarbox, vignette); this script only
draws the static newspaper / web "plates" the camera moves across.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = Path(__file__).resolve().parent
FONTS = HERE.parents[1] / "assets" / "fonts"
WIN = Path("C:/Windows/Fonts")
OUT = HERE.parents[1] / "assets" / "fast_intro_match_cut"
W, H = 1920, 1080

YEL = (250, 214, 10)
ORG = (232, 112, 20)
RED = (222, 30, 70)
BLU = (46, 110, 235)
GRN = (96, 235, 140)
INK = (28, 26, 24)


def F(name: str, size: int) -> ImageFont.FreeTypeFont:
    for base in (FONTS, WIN):
        p = base / name
        if p.exists():
            return ImageFont.truetype(str(p), size)
    raise FileNotFoundError(name)


PLAY_B = "PlayfairDisplay-Bold.ttf"
PLAY_BI = "PlayfairDisplay-BoldItalic.ttf"
PLAY_I = "PlayfairDisplay-Italic.ttf"
PLAY_BLK = "PlayfairDisplay-Black.ttf"
PLAY = "PlayfairDisplay.ttf"
ANTON = "Anton-Regular.ttf"
INTER = "Inter-Regular.ttf"
INTER_M = "Inter-Medium.ttf"
INTER_B = "Inter-Bold.ttf"
INTER_X = "Inter-ExtraBold.ttf"
INTER_K = "Inter-Black.ttf"
OSW = "Oswald-Bold.ttf"
GEO = "georgia.ttf"
GEO_I = "georgiai.ttf"
GEO_B = "georgiab.ttf"
TIMES = "times.ttf"
TIMES_I = "timesi.ttf"
TIMES_B = "timesbd.ttf"


def paper(base, crumple=0.10, seed=1, size=(W, H)) -> Image.Image:
    rng = np.random.default_rng(seed)
    w, h = size
    n = rng.random((h // 90 + 2, w // 90 + 2)).astype(np.float32)
    n = np.array(Image.fromarray((n * 255).astype(np.uint8)).resize((w, h), Image.BICUBIC)).astype(np.float32) / 255
    fine = rng.random((h, w)).astype(np.float32)
    k = 1.0 + (n - 0.5) * crumple * 2 + (fine - 0.5) * 0.018
    arr = np.clip(np.array(base, np.float32)[None, None, :] * k[..., None], 0, 255).astype(np.uint8)
    return Image.fromarray(arr, "RGB")


def flat(base) -> Image.Image:
    return Image.new("RGB", (W, H), base)


LAST = {"end": 0}


def tw(d, s, font) -> int:
    return int(d.textlength(s, font=font))


def text(d, xy, s, font, fill, anchor="la"):
    d.text(xy, s, font=font, fill=fill, anchor=anchor)


def hl(d, x, y, s, font, bg, fg, pad=(14, 6), anchor_baseline=False, radius=3):
    """Highlight chip with text; (x, y) is the left/middle of the chip."""
    w = tw(d, s, font)
    asc, desc = font.getmetrics()
    d.rounded_rectangle((x, y - asc // 2 - pad[1] - 6, x + w + pad[0] * 2, y + desc // 2 + pad[1] + 8), radius, fill=bg)
    d.text((x + pad[0], y), s, font=font, fill=fg, anchor="lm")
    LAST["end"] = x + w + pad[0] * 2
    return w + pad[0] * 2


def wrap(d, s, font, maxw):
    out, cur = [], ""
    for word in s.split():
        t = (cur + " " + word).strip()
        if tw(d, t, font) <= maxw:
            cur = t
        else:
            out.append(cur)
            cur = word
    if cur:
        out.append(cur)
    return out


def para(d, x, y, s, font, fill, maxw, lead):
    for line in wrap(d, s, font, maxw):
        d.text((x, y), line, font=font, fill=fill, anchor="la")
        y += lead
    return y


def vignette_edge(img, strength=0.35):
    xs = np.linspace(-1, 1, img.width)[None, :]
    ys = np.linspace(-1, 1, img.height)[:, None]
    r = np.clip((xs ** 2 * 0.7 + ys ** 2) / 1.7, 0, 1)
    a = 1 - strength * r ** 1.6
    return Image.fromarray((np.array(img, np.float32) * a[..., None]).astype(np.uint8))


def save(img, name):
    OUT.mkdir(parents=True, exist_ok=True)
    img.convert("RGB").save(OUT / f"{name}.png", optimize=True)
    print("wrote", name)


LOREM_A = ("Every great story flows from one moment to another, and the Match Cut is what turns that flow into emotion "
           "— connecting ideas with perfect rhythm and purpose. It's where vision meets precision, where every frame "
           "becomes a heartbeat in motion.")
LOREM_B = ("In the hands of a skilled editor, the Match Cut becomes a bridge of creativity — blending time, motion, and "
           "meaning into one seamless visual experience. Two separate worlds suddenly align, creating harmony out of contrast.")


# ---------------------------------------------------------------- newspaper plates
def news_masthead():
    im = paper((205, 204, 200), 0.12, 11)
    d = ImageDraw.Draw(im)
    text(d, (140, 130), "Newspaper", F(PLAY_B, 150), INK)  # small-caps feel
    d.line((120, 285, W - 120, 285), fill=(60, 58, 56), width=3)
    text(d, (140, 262), "Every match cut tells a story without words — a silent dialogue between two frames that share the same soul.",
         F(TIMES_I, 22), (90, 88, 86))
    d.line((120, 300, W - 120, 300), fill=(60, 58, 56), width=2)
    f = F(PLAY_B, 64)
    text(d, (140, 340), "MON", f, INK)
    text(d, (140, 410), "17.11", f, INK)
    text(d, (140, 480), "2025", f, INK)
    hl(d, 400, 380, "Match Cut", F(PLAY_BI, 92), YEL, INK, pad=(22, 6))
    text(d, (LAST["end"] + 26, 380), "Creates", F(PLAY_BI, 92), INK, "lm")
    text(d, (400, 500), "Seamless Stories", F(PLAY_BI, 92), INK, "lm")
    fb = F(TIMES_I, 27)
    y = 590
    for t in (LOREM_A, "Every match cut tells a story without words — a silent dialogue between two frames that share the same soul. "
              "With each cut, we build emotion, rhythm, and connection — bridging moments that once felt apart."):
        y = para(d, 140, y, t, fb, (60, 58, 56), W - 280, 36) + 12
    para(d, 140, y, LOREM_B, F(TIMES_I, 25), (80, 78, 76), W - 280, 33)
    return vignette_edge(im, 0.28)


def news_storytelling():
    im = paper((222, 222, 224), 0.20, 12)
    d = ImageDraw.Draw(im)
    text(d, (140, 150), "Monday | 17/11/2025", F(TIMES_I, 28), (110, 108, 106))
    f = F(PLAY_BI, 76)
    text(d, (130, 260), "Storytelling Begins with Harmony", f, INK, "lm")
    text(d, (130, 345), "A Perfect Visual Bridge", f, INK, "lm")
    d.rectangle((130, 440, 540, 800), fill=(176, 176, 178))
    # MATCH CUT chip (Anton)
    fa = F(ANTON, 52)
    hl(d, 640, 470, "MATCH CUT", fa, YEL, INK, pad=(14, 4), radius=2)
    text(d, (LAST["end"] + 26, 470), "A FRAME THAT", fa, (60, 58, 56), "lm")
    text(d, (640, 540), "CONNECTS WORLDS", fa, (60, 58, 56), "lm")
    fb = F(GEO, 33)
    y = para(d, 640, 610, "Every great story flows from one moment to another, and the Match Cut is what turns that flow into "
             "emotion — connecting ideas with perfect rhythm and purpose.", fb, (60, 58, 56), 1000, 46)
    para(d, 130, 860, "Between two frames lies a heartbeat — and it's the Match Cut that gives those moments life, making the "
         "audience feel the transition without ever seeing the seam.", F(GEO_I, 30), (80, 78, 76), W - 260, 42)
    return vignette_edge(im, 0.30)


def news_truth():
    im = paper((226, 214, 184), 0.10, 13)
    d = ImageDraw.Draw(im)
    f = F(PLAY_BLK, 150)
    text(d, (560, 60), "TRUTH BEHIND", f, (50, 40, 34))
    text(d, (560, 220), "THE HEADLINES", f, (50, 40, 34))
    # left narrow column
    fs = F(TIMES, 24)
    para(d, 60, 70, "Match Cut is a bridge of creativity, meaning into one seamless visual language that suddenly align, "
         "harmony out of cut is never abrupt, because the rhythm of the becomes a language that sound, color, and shape "
         "— a way to speak directly to the soul.", fs, (60, 52, 44), 430, 33)
    d.line((520, 40, 520, H - 40), fill=(90, 80, 70), width=3)
    hl(d, 560, 470, "Match Cut", F(INTER_M, 62), YEL, INK, pad=(18, 6), radius=2)
    text(d, (LAST["end"] + 26, 470), "Changes", F(INTER_M, 62), (60, 52, 44), "lm")
    fb = F(INTER_M, 28)
    para(d, 560, 560, "In the hands of a skilled editor, the Match Cut becomes a bridge of creativity — blending time, motion, "
         "and meaning into one seamless visual experience. Two separate worlds suddenly align, creating harmony out of contrast. "
         "The cut is never abrupt, because the rhythm itself becomes a language that transcends sound, color, and shape — "
         "a way to speak directly to the soul. The Match Cut appears, it feels less like editing and more like magic.",
         fb, (60, 52, 44), 1280, 40)
    return vignette_edge(im, 0.38)


def news_discover():
    im = paper((205, 192, 156), 0.14, 14)
    d = ImageDraw.Draw(im)
    text(d, (W // 2, 105), "DailyNews", F(PLAY, 150), (40, 34, 30), "mm")
    text(d, (W // 2, 205), "Truth Behind the Headlines", F(PLAY, 34), (60, 52, 44), "mm")
    d.line((100, 250, W - 100, 250), fill=(60, 52, 44), width=2)
    f = F(PLAY_BI, 62)
    text(d, (110, 330), "\u201cDiscover untold stories", f, (46, 38, 32), "lm")
    text(d, (110, 410), "shaping our world every day.\u201d", f, (46, 38, 32), "lm")
    fb = F(GEO, 40)
    x = 110
    text(d, (x, 520), "skilled editor, the", fb, (46, 38, 32), "lm")
    x += tw(d, "skilled editor, the", fb) + 22
    w = hl(d, x, 520, "Match Cut", F(GEO, 40), YEL, INK, pad=(16, 4), radius=3)
    text(d, (LAST["end"] + 26, 520), "becomes", fb, (46, 38, 32), "lm")
    para(d, 110, 580, "creativity — blending time, motion, and meaning into one seamless visual experience. "
         "The Match Cut becomes part of a greater whole, a story unfolding in motion. The Match Cut shapes the line between moments, "
         "allowing us to move like water through the narrative. What a cut, but a feeling that stays long after the scene fades.",
         fb, (46, 38, 32), W - 220, 54)
    d.rectangle((W - 130, 280, W - 60, H), fill=(150, 140, 122))
    return vignette_edge(im, 0.32)


# ---------------------------------------------------------------- newspaper close-ups
def crop_news(name, base, seed, blocks, hl_word=("Match Cut", YEL, "plain"), extra=None):
    """Generic big-type text close-up. blocks: list of (text, font, size, fill, y)."""
    im = paper(base, 0.12, seed)
    d = ImageDraw.Draw(im)
    last_y = None
    for kind, args in blocks:
        if kind == "t":
            s, fnt, sz, fill, x, y, anchor = args
            if y == last_y and anchor == "lm":
                x = LAST["end"] + 26
            text(d, (x, y), s, F(fnt, sz), fill, anchor)
            LAST["end"] = x + tw(d, s, F(fnt, sz))
            last_y = y
        elif kind == "hl":
            s, fnt, sz, bg, fg, x, y = args
            if y == last_y:
                x = LAST["end"] + 26
            hl(d, x, y, s, F(fnt, sz), bg, fg, pad=(22, 6), radius=3)
            last_y = y
        elif kind == "line":
            y = args
            d.line((0, y, W, y), fill=(70, 66, 62), width=3)
        elif kind == "bar":
            y0, y1, col = args
            d.rectangle((0, y0, W, y1), fill=col)
    return vignette_edge(im, 0.40)


def news_crops():
    ink, g = INK, (60, 58, 56)
    save(crop_news("c1", (226, 226, 224), 21, [
        ("t", ("Monday | November 17 | 2025", TIMES_I, 34, (110, 108, 106), 960, 60, "mm")),
        ("t", ("every great story flows from one moment", PLAY, 70, g, 40, 250, "lm")),
        ("t", ("another, and the", PLAY, 70, g, 40, 400, "lm")),
        ("hl", ("Match Cut", PLAY_B, 72, YEL, ink, 600, 400)),
        ("t", ("is what turns that", PLAY, 70, g, 1020, 400, "lm")),
        ("t", ("flow into emotion — connecting ideas with", PLAY, 70, g, 40, 550, "lm")),
        ("t", ("perfect rhythm and purpose.", PLAY, 70, g, 40, 700, "lm")),
        ("t", ("it's where vision meets precision, where every", PLAY_I, 66, g, 40, 850, "lm")),
    ]), "crop_news_flow")
    save(crop_news("c2", (222, 222, 220), 22, [
        ("t", ("STORIES CONNECTED BY FRAMES", ANTON, 190, ink, 40, 130, "lm")),
        ("line", 270),
        ("t", ("story flows", GEO, 78, g, 40, 400, "lm")),
        ("hl", ("Match Cut", PLAY_BI, 78, YEL, ink, 530, 400)),
        ("t", ("transform", GEO, 78, g, 1010, 400, "lm")),
        ("t", ("footage into visual poetry,", GEO, 78, g, 530, 520, "lm")),
        ("t", ("revealing meaning in motion.", GEO, 78, g, 530, 640, "lm")),
        ("t", ("Through perfect timing and", GEO, 78, g, 530, 760, "lm")),
        ("t", ("match cuts make creativity flow", GEO, 78, g, 40, 900, "lm")),
    ]), "crop_news_stories")
    save(crop_news("c3", (222, 220, 210), 23, [
        ("t", ("when storytelling meets precision,", PLAY, 64, g, 30, 90, "lm")),
        ("t", ("Match Cut reveals its true power —", PLAY, 64, g, 30, 200, "lm")),
        ("t", ("transforming simple edits into moments", PLAY, 64, g, 30, 310, "lm")),
        ("t", ("of pure cinematic harmony.", PLAY, 64, g, 30, 420, "lm")),
        ("bar", (520, 640, (60, 52, 46))),
        ("t", ("Where Motion Meets Meaning", PLAY_B, 66, (230, 226, 218), 30, 580, "lm")),
        ("t", ("skilled editor, the", GEO, 74, g, 30, 760, "lm")),
        ("hl", ("Match Cut", PLAY_BI, 74, YEL, ink, 560, 760)),
        ("t", ("transform", GEO, 74, g, 1060, 760, "lm")),
        ("t", ("image into visual poetry, revealing meaning", GEO, 70, g, 30, 900, "lm")),
    ]), "crop_news_motion")
    save(crop_news("c4", (216, 216, 212), 24, [
        ("t", ("cinematic harmony. Behind every", PLAY, 74, g, 30, 120, "lm")),
        ("t", ("unforgettable scene lies balance —", PLAY, 74, g, 30, 260, "lm")),
        ("t", ("silent conversation between frames, perfectly", PLAY, 74, g, 30, 400, "lm")),
        ("t", ("crafted the", PLAY, 74, g, 30, 540, "lm")),
        ("hl", ("Match Cut", INTER_M, 74, YEL, ink, 400, 540)),
        ("t", ("that ties the", PLAY, 74, g, 880, 540, "lm")),
        ("t", ("together. It's a meeting point of vision", PLAY, 74, g, 30, 680, "lm")),
        ("t", ("and patience, where meaning is built not", PLAY, 74, g, 30, 820, "lm")),
        ("t", ("by words but by rhythm. Each cut is a", PLAY, 74, g, 30, 960, "lm")),
    ]), "crop_news_harmony")
    save(crop_news("c5", (206, 200, 170), 25, [
        ("t", ("that subtle motion, stories find their pulse.", GEO, 60, g, 30, 120, "lm")),
        ("t", ("Great films are defined by that movement", GEO, 60, g, 30, 230, "lm")),
        ("t", ("remembered not only for their stories but", GEO, 60, g, 30, 340, "lm")),
        ("t", ("move, and the", GEO_B, 62, ink, 30, 450, "lm")),
        ("hl", ("Match Cut", INTER_B, 62, YEL, ink, 420, 450)),
        ("line", 560),
        ("t", ("From One Scene to Another", PLAY_BI, 84, (46, 38, 32), 40, 680, "lm")),
        ("t", ("— Perfectly Matched", PLAY_BI, 84, (46, 38, 32), 40, 800, "lm")),
        ("t", ("silent signature of every great edit.", GEO_I, 46, g, 40, 950, "lm")),
    ]), "crop_news_scene")
    save(crop_news("c6", (222, 222, 220), 26, [
        ("t", ("The viewer doesn't just see", GEO, 64, g, 700, 130, "lm")),
        ("t", ("they sense the rhythm of the", GEO, 64, g, 700, 240, "lm")),
        ("hl", ("Match Cut", INTER_B, 64, YEL, ink, 700, 350)),
        ("t", ("carries that", GEO, 64, g, 1160, 350, "lm")),
        ("t", ("intention across frames —", GEO, 64, g, 700, 470, "lm")),
        ("t", ("shaping how we feel, think,", GEO, 64, g, 700, 580, "lm")),
        ("t", ("remember a story. It's more", GEO, 64, g, 700, 690, "lm")),
        ("t", ("than a tool; it's a philosophy of", GEO, 64, g, 700, 800, "lm")),
        ("t", ("storytelling. Each", GEO, 64, g, 700, 910, "lm")),
    ]), "crop_news_viewer")
    save(crop_news("c7", (232, 232, 230), 27, [
        ("t", ("every unforgettable", PLAY_BI, 96, ink, 30, 120, "lm")),
        ("t", ("scene lies balance — a silent", PLAY_BI, 96, ink, 30, 250, "lm")),
        ("t", ("conversation between\u201d", PLAY_BI, 96, ink, 30, 380, "lm")),
        ("t", ("11.2025", TIMES_I, 40, g, 30, 490, "lm")),
        ("line", 520),
        ("t", ("every great story flows from one moment", GEO, 68, g, 30, 640, "lm")),
        ("t", ("another, and the", GEO, 68, g, 30, 760, "lm")),
        ("hl", ("Match Cut", INTER_B, 68, YEL, ink, 480, 760)),
        ("t", ("is what turns that", GEO, 68, g, 980, 760, "lm")),
        ("t", ("flow into emotion — connecting ideas with", GEO, 68, g, 30, 880, "lm")),
    ]), "crop_news_silent")
    save(crop_news("c8", (222, 222, 218), 28, [
        ("t", ("THE INVISIBLE HEARTBEAT", OSW, 150, ink, 30, 110, "lm")),
        ("t", ("Monday | November 17 | 2025", TIMES_I, 34, (110, 108, 106), 960, 220, "mm")),
        ("bar", (270, 400, (60, 52, 46))),
        ("t", ("The Intent Behind Every Frame", PLAY_B, 82, (234, 230, 222), 30, 335, "lm")),
        ("t", ("The Magic of", PLAY_B, 74, ink, 30, 500, "lm")),
        ("hl", ("Match Cut", INTER_B, 74, YEL, ink, 520, 500)),
        ("t", ("transitions", PLAY_B, 74, ink, 1040, 500, "lm")),
        ("t", ("vanish, and the story takes center stage.", PLAY_B, 62, ink, 30, 640, "lm")),
        ("t", ("What seems like a simple edit is, in truth, an invisible art —", TIMES_I, 40, g, 30, 760, "lm")),
        ("t", ("Match Cut, guiding the viewer's eye from one world to the next.", TIMES_I, 40, g, 30, 830, "lm")),
        ("t", ("without breaking immersion. It's the kind of mastery that hides.", TIMES_I, 40, g, 30, 900, "lm")),
    ]), "crop_news_magic")


# ---------------------------------------------------------------- web plates
def web_sports():
    im = flat((236, 236, 238))
    d = ImageDraw.Draw(im)
    d.rectangle((0, 0, W, 90), fill=YEL)
    text(d, (260, 40), "NBA   Cricket   Formula 1   Tennis   Golf        Standings   Results & Fixtures", F(INTER_B, 26), (30, 30, 30), "lm")
    d.rectangle((230, 140, 262, H), fill=YEL)
    text(d, (340, 250), "Envato Sports", F(INTER_X, 96), INK, "lm")
    d.line((340, 330, W - 200, 330), fill=INK, width=5)
    hl(d, 340, 430, "Match Cut", F(INTER_X, 88), YEL, INK, pad=(16, 6), radius=2)
    text(d, (LAST["end"] + 26, 430), "Momentum:", F(INTER_X, 88), INK, "lm")
    text(d, (340, 560), "Milan's Attack Shifts", F(INTER_X, 88), INK, "lm")
    para(d, 340, 680, "A perfect Match Cut captures the moment from defense to glory — one pass, one moment, suddenly the story "
         "changes. Football isn't edited in rhythm, where every cut mirrors timing, and control.", F(INTER_M, 34), (60, 60, 64), 900, 46)
    text(d, (340, 900), "Envato News | 4h | 132 comments", F(INTER_B, 28), (40, 150, 70), "lm")
    return vignette_edge(im, 0.35)


def web_essay_dark():
    im = flat((16, 14, 22))
    d = ImageDraw.Draw(im)
    text(d, (W // 2, 90), "Match Cut Essays:", F(INTER_X, 92), (236, 236, 240), "mm")
    text(d, (W // 2, 200), "Thought and Time", F(INTER_X, 92), (236, 236, 240), "mm")
    f = F(PLAY_I, 52)
    text(d, (120, 380), "long-form ideas benefit from graceful", f, (200, 200, 208), "lm")
    text(d, (120, 470), "transitions. The", f, (200, 200, 208), "lm")
    w = hl(d, 120 + tw(d, "transitions. The", f) + 24, 470, "Match Cut", F(PLAY_I, 52), ORG, (250, 250, 250), pad=(22, 6), radius=3)
    text(d, (120 + tw(d, "transitions. The", f) + 48 + w, 470), "links con", f, (200, 200, 208), "lm")
    text(d, (120, 560), "passages and pages, turning", f, (200, 200, 208), "lm")
    text(d, (120, 650), "thoughts into cohesive arguments.", f, (200, 200, 208), "lm")
    text(d, (W - 140, 800), "By Newton", F(INTER_B, 38), (210, 210, 216), "rm")
    d.rounded_rectangle((120, 920, 520, 990), 35, fill=(212, 28, 60))
    text(d, (320, 955), "FIND YOUR PRICE", F(INTER_X, 26), (255, 255, 255), "mm")
    d.rounded_rectangle((580, 920, 980, 990), 35, fill=(30, 160, 80))
    text(d, (780, 955), "REQUEST INFO", F(INTER_X, 26), (255, 255, 255), "mm")
    return vignette_edge(im, 0.55)


def web_news_red():
    im = flat((14, 14, 20))
    d = ImageDraw.Draw(im)
    text(d, (110, 80), "NEWS | ENVATO | 2 HOUR", F(INTER_M, 34), (150, 150, 160), "lm")
    hl(d, 110, 240, "Match Cut", F(INTER_K, 130), RED, (255, 255, 255), pad=(24, 6), radius=4)
    text(d, (LAST["end"] + 26, 240), "News:", F(INTER_K, 130), (240, 240, 244), "lm")
    text(d, (110, 400), "The Science of Cuts", F(INTER_K, 110), (240, 240, 244), "lm")
    text(d, (110, 520), "October 31, 2025", F(INTER_M, 34), (150, 150, 160), "lm")
    f = F(INTER_M, 40)
    para(d, 110, 600, "From classrooms to the cosmos, curiosity drives discovery. Education is not about memorizing facts — "
         "it's the courage to keep asking.", f, (150, 150, 162), W - 220, 54)
    text(d, (110, 800), "SOCIAL", F(INTER_B, 30), (240, 70, 110), "lm")
    text(d, (110, 860), "From the misty hills of Cappadocia to the golden deserts of Namibia", F(INTER_B, 38), (240, 240, 244), "lm")
    text(d, (110, 920), "Ivan Mehta - 2 hours ago", F(INTER_M, 28), (110, 110, 120), "lm")
    return vignette_edge(im, 0.45)


def web_push_red():
    im = flat((244, 244, 246))
    d = ImageDraw.Draw(im)
    f = F(INTER_K, 130)
    text(d, (40, 150), "push boundaries and", f, (24, 24, 28), "lm")
    text(d, (40, 340), "the", f, (24, 24, 28), "lm")
    hl(d, 40 + tw(d, "the", f) + 30, 340, "Match Cut", F(INTER_K, 130), RED, (255, 255, 255), pad=(26, 8), radius=3)
    text(d, (LAST["end"] + 26, 340), "con", f, (24, 24, 28), "lm")
    text(d, (40, 540), "breakthrough studios", f, (24, 24, 28), "lm")
    text(d, (40, 780), "From hidden alleys to sweeping vistas, the", F(INTER_B, 54), (50, 50, 56), "lm")
    text(d, (40, 870), "essence of discovery, turning fleeting", F(INTER_B, 54), (50, 50, 56), "lm")
    return vignette_edge(im, 0.40)


def web_fashion_blue():
    im = flat((14, 12, 22))
    d = ImageDraw.Draw(im)
    f = F(INTER_K, 110)
    text(d, (30, 140), "ing the", f, (240, 240, 245), "lm")
    hl(d, 30 + tw(d, "ing the", f) + 36, 140, "Match Cut", F(INTER_K, 110), BLU, (255, 255, 255), pad=(24, 6), radius=4)
    text(d, (LAST["end"] + 26, 140), "fashion", f, (240, 240, 245), "lm")
    text(d, (30, 300), "ratives flow from fabric", f, (240, 240, 245), "lm")
    for i, t in enumerate(("Seamless travel experience", "Comprehensive itinerary & travel guide",
                           "24/7 helpline during your tour", "Great customer reviews")):
        y = 470 + i * 110
        text(d, (30, y), "\u2713", F("DejaVuSans.ttf", 52), (60, 140, 255), "lm")
        text(d, (110, y), t, F(INTER_M, 62), (190, 190, 205), "lm")
    return vignette_edge(im, 0.50)


def web_green_news():
    im = flat((12, 12, 18))
    d = ImageDraw.Draw(im)
    text(d, (40, 70), "to the golden deserts of Namibia", F(INTER_B, 46), (230, 230, 240), "lm")
    text(d, (40, 140), "Ivan Mehta - 2 hours ago", F(INTER_M, 34), (100, 100, 112), "lm")
    d.line((0, 200, W, 200), fill=(40, 40, 50), width=3)
    text(d, (40, 270), "DESIGN", F(INTER_B, 38), (60, 200, 110), "lm")
    f = F(INTER_B, 78)
    text(d, (40, 400), "Artificial", f, (240, 240, 245), "lm")
    hl(d, 40 + tw(d, "Artificial", f) + 40, 400, "Match Cut", F(INTER_B, 78), GRN, (30, 30, 30), pad=(20, 6), radius=3)
    text(d, (LAST["end"] + 26, 400), "continues to", f, (240, 240, 245), "lm")
    text(d, (40, 540), "redefine industries, from health", f, (240, 240, 245), "lm")
    text(d, (40, 640), "Sarah Perez - 3 hours ago", F(INTER_M, 34), (100, 100, 112), "lm")
    text(d, (40, 780), "FASHION", F(INTER_B, 38), (240, 90, 120), "lm")
    text(d, (40, 880), "A new wave of designers is", F(INTER_B, 78), (240, 240, 245), "lm")
    return vignette_edge(im, 0.45)


def web_google():
    im = flat((246, 246, 250))
    d = ImageDraw.Draw(im)
    f = F(INTER_M, 40)
    for i, t in enumerate(("AI Mode", "All", "Images", "News", "Videos")):
        text(d, (30 + i * 250, 70), t, f, (30, 30, 36) if t == "All" else (120, 120, 130), "lm")
    d.line((0, 130, W, 130), fill=(210, 210, 216), width=3)
    hl(d, 270, 300, "Match Cut", F(INTER_B, 88), BLU, (255, 255, 255), pad=(22, 8), radius=2)
    text(d, (350, 410), "New Project", F(INTER_M, 48), (50, 50, 56), "lm")
    d.rounded_rectangle((1000, 240, 1900, 370), 65, outline=(40, 40, 48), width=4)
    text(d, (30, 600), "Match Cut that ties them together.", F(INTER_M, 82), (60, 60, 68), "lm")
    text(d, (30, 710), "It's a meeting point of vision and", F(INTER_M, 82), (60, 60, 68), "lm")
    text(d, (30, 820), "patience, where meaning is built not by", F(INTER_M, 82), (60, 60, 68), "lm")
    return vignette_edge(im, 0.42)


def web_numbered():
    im = flat((228, 232, 240))
    d = ImageDraw.Draw(im)
    text(d, (460, 70), "The Power of Precision", F(PLAY, 66), (60, 60, 66), "lm")
    text(d, (460, 150), "What seems like a simple edit", F(INTER_M, 48), (60, 60, 68), "lm")
    text(d, (460, 215), "is, in truth, an invisible art", F(INTER_M, 48), (60, 60, 68), "lm")
    d.line((0, 290, W, 290), fill=(90, 90, 100), width=3)
    d.rectangle((0, 330, 380, 620), fill=(70, 176, 232))
    text(d, (190, 480), "2", F(PLAY_BLK, 220), (232, 244, 252), "mm")
    hl(d, 460, 430, "Match Cut", F(PLAY, 66), (70, 176, 232), (30, 30, 36), pad=(20, 8), radius=2)
    text(d, (LAST["end"] + 26, 430), "that ties them", F(PLAY, 66), (60, 60, 66), "lm")
    text(d, (460, 540), "Within every transition lies", F(INTER_M, 50), (60, 60, 68), "lm")
    text(d, (460, 610), "and the Match Cut carries", F(INTER_M, 50), (60, 60, 68), "lm")
    d.line((0, 700, W, 700), fill=(90, 90, 100), width=3)
    text(d, (460, 800), "The Motion of Meaning", F(PLAY, 66), (60, 60, 66), "lm")
    text(d, (460, 880), "Great films are remembered", F(INTER_M, 48), (60, 60, 68), "lm")
    return vignette_edge(im, 0.36)


def web_wiki():
    im = flat((246, 246, 250))
    d = ImageDraw.Draw(im)
    hl(d, 700, 330, "Match Cut", F(PLAY_B, 104), YEL, INK, pad=(20, 8), radius=2)
    d.line((560, 450, 1500, 450), fill=(120, 120, 130), width=3)
    text(d, (580, 580), "Article", F(INTER_B, 78), (20, 20, 24), "lm")
    d.line((580, 640, 840, 640), fill=(20, 20, 24), width=6)
    text(d, (900, 580), "Talk", F(INTER_B, 78), (20, 20, 24), "lm")
    text(d, (580, 780), "Match Cut that ties them", F(INTER_M, 70), (40, 40, 48), "lm")
    text(d, (580, 880), "It's a meeting point of vision", F(INTER_M, 70), (40, 40, 48), "lm")
    return vignette_edge(im, 0.40)


def web_dev_dark():
    im = flat((14, 12, 20))
    d = ImageDraw.Draw(im)
    text(d, (20, 60), "Envato", F(PLAY, 40), (160, 160, 175), "lm")
    f = F(PLAY, 72)
    text(d, (20, 360), "Developers and researchers push b", f, (200, 200, 212), "lm")
    text(d, (20, 480), "volves. The", f, (200, 200, 212), "lm")
    hl(d, 20 + tw(d, "volves. The", f) + 24, 480, "Match Cut", F(PLAY, 72), BLU, (255, 255, 255), pad=(20, 6), radius=3)
    text(d, (LAST["end"] + 26, 480), "connects b", f, (200, 200, 212), "lm")
    text(d, (20, 600), "tudies to practical applications, sh", f, (200, 200, 212), "lm")
    text(d, (20, 940), "read the full story", F(INTER_M, 38), (60, 120, 230), "lm")
    return vignette_edge(im, 0.50)


def web_wild_maine():
    im = flat((236, 232, 224))
    d = ImageDraw.Draw(im)
    text(d, (W // 2, 170), "LIMITED MAINE", F(INTER_K, 260), (116, 78, 70), "mm")
    f = F("Inter-Bold.ttf", 90)
    text(d, (20, 480), ", wild,", f, (40, 36, 34), "lm")
    hl(d, 20 + tw(d, ", wild,", f) + 30, 480, "Match Cut", F(INTER_M, 90), ORG, (40, 24, 12), pad=(24, 8), radius=5)
    text(d, (LAST["end"] + 26, 480), "and ins", f, (40, 36, 34), "lm")
    text(d, (20, 620), "trending for its wealth of", f, (40, 36, 34), "lm")
    d.rounded_rectangle((-60, 900, 360, 1060), 70, fill=ORG)
    return vignette_edge(im, 0.50)


def web_design_green():
    im = flat((244, 244, 248))
    d = ImageDraw.Draw(im)
    text(d, (30, 100), "Digital", F(INTER_B, 38), (60, 190, 110), "lm")
    text(d, (30, 220), "Design: Frame", F(INTER_K, 150), (24, 24, 28), "lm")
    f = F(INTER_M, 70)
    text(d, (30, 440), "Creative studios craft experience", f, (50, 50, 60), "lm")
    text(d, (30, 560), "hot lead", f, (50, 50, 60), "lm")
    hl(d, 30 + tw(d, "hot lead", f) + 26, 560, "Match Cut", F(INTER_M, 70), (84, 200, 120), (255, 255, 255), pad=(20, 8), radius=3)
    text(d, (LAST["end"] + 26, 560), "to the ne", f, (50, 50, 60), "lm")
    text(d, (30, 680), "the designer's tool for creating", f, (50, 50, 60), "lm")
    text(d, (30, 820), "By Gene Maddaus", F(INTER_B, 44), (30, 30, 36), "lm")
    d.rounded_rectangle((30, 930, 480, 1010), 40, fill=(212, 28, 60))
    d.rounded_rectangle((520, 930, 970, 1010), 40, fill=(30, 160, 80))
    return vignette_edge(im, 0.40)


def main() -> None:
    save(news_masthead(), "news_masthead")
    save(news_storytelling(), "news_storytelling")
    save(news_truth(), "news_truth")
    save(news_discover(), "news_discover")
    news_crops()
    for fn, nm in ((web_sports, "web_sports"), (web_essay_dark, "web_essay"), (web_news_red, "web_news_red"),
                   (web_push_red, "web_push_red"), (web_fashion_blue, "web_fashion"), (web_green_news, "web_green_news"),
                   (web_google, "web_google"), (web_numbered, "web_numbered"), (web_wiki, "web_wiki"),
                   (web_dev_dark, "web_dev"), (web_wild_maine, "web_wild"), (web_design_green, "web_design")):
        save(fn(), nm)


if __name__ == "__main__":
    main()
