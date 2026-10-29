"""Group B — web shots 03-06 and 11, rebuilt natively.

03 alexis_arquette_article   (news.com.au article + Italian YouTube chrome)
04 corll_warehouse_excerpt   (dark document excerpt, red marker sweep)
05 they_were_the_economy     (red-band serif caption on woven dark ground)
06 thug_teacher_quote        (blurred documentary quote plate, gold marker)
11 acoustic_kitty_field_test (sepia archival documents + serif caption)

Each shot: static plate + animated marker sweep / camera drift + player
chrome where the paused-player reference shows it.
"""

from __future__ import annotations

from PIL import Image, ImageDraw, ImageFilter

from web_shot_kit import Canvas, Shot, asset, get_font


def _ease(t: float) -> float:
    return t * t * (3.0 - 2.0 * t)


def _sweep(t: float, t0: float = 0.10, t1: float = 0.55) -> float:
    if t <= t0:
        return 0.0
    if t >= t1:
        return 1.0
    return _ease((t - t0) / (t1 - t0))


# --------------------------------------------------------------------------- #
# 03 — news.com.au: Alexis Arquette tell-all memoir article
# --------------------------------------------------------------------------- #

def shot_03_alexis() -> Shot:
    def back(c: Canvas):
        c.rect(0, 0, 1920, 1080, "#FAFAF8")
        c.grad_rect(0, 0, 1920, 220, (238, 238, 234), (238, 238, 234), alpha1=0.5, alpha2=0.0)

    def front(c: Canvas):
        c.text(100, 48, "Alexis Arquette was planning a tell-all", 88, "sans-black", "#14161A")
        c.text(100, 172, "memoir before she died", 88, "sans-black", "#14161A")
        c.text(100, 372, "news.com.au", 32, "sans-bold", "#17181B")
        c.text(100, 430, "13 Sep, 2016 10:30 AM", 26, "sans", "#56595E")
        # clock icon + read time
        c.ellipse(520, 432, 28, 28, "#56595E")
        c.ellipse(525, 437, 18, 18, "#FAFAF8")
        c.line(534, 441, 534, 449, "#56595E", 2.5)
        c.line(534, 449, 540, 452, "#56595E", 2.5)
        c.text(566, 430, "3 mins to read", 26, "sans", "#56595E")
        c.rect(100, 532, 1800, 2, "#D7D6D3", 0.9)
        # Save / share row (share clipped by the frame edge like the reference)
        c.poly([(1590, 640), (1632, 640), (1632, 708), (1611, 692), (1590, 708)], "#1A1A1A")
        c.text(1652, 655, "Save", 30, "sans-med", "#1A1A1A")
        c.poly([(1806, 648), (1856, 648), (1856, 704), (1806, 704)], "#1A1A1A")
        c.poly([(1818, 664), (1831, 646), (1844, 664)], "#FAFAF8")
        c.rect(1826, 660, 10, 34, "#FAFAF8")
        c.text(1868, 655, "Sh", 30, "sans-med", "#1A1A1A")

        # paused video banner at the bottom (Comedy Central roast frame)
        c.rect(100, 808, 1820, 272, "#EDE23F")
        c.rect(150, 850, 180, 150, "#D7262E", radius=10)
        c.text(168, 872, "COMEDY", 26, "sans-bold", "#FFFFFF")
        c.text(168, 908, "CENTRAL", 26, "sans-bold", "#FFFFFF")
        c.ellipse(560, 880, 210, 110, "#1B4F9B")
        c.text(665, 908, "BUD", 26, "sans-bold", "#FFFFFF", anchor="ma")
        c.text(665, 940, "LIGHT", 26, "sans-bold", "#FFFFFF", anchor="ma")
        c.rect(990, 828, 190, 200, "#E86FA0")
        c.text(1085, 856, "RIDE", 30, "sans-bold", "#7E1B66", anchor="ma")
        c.text(1085, 896, "OF", 30, "sans-bold", "#7E1B66", anchor="ma")
        c.text(1085, 936, "FAVOR", 30, "sans-bold", "#7E1B66", anchor="ma")
        c.rect(1440, 855, 210, 140, "#7B6BD6")
        c.text(1545, 878, "THINK", 24, "sans-bold", "#FFFFFF", anchor="ma")
        c.text(1545, 910, "OUTSIDE", 24, "sans-bold", "#FFFFFF", anchor="ma")
        c.text(1545, 942, "THE SUN", 24, "sans-bold", "#FFFFFF", anchor="ma")
        # blonde hair + face entering from the bottom
        c.ellipse(820, 940, 330, 280, "#E8C87A")
        c.ellipse(890, 980, 190, 220, "#E7C2A0")

    def anim(c: Canvas, t: float):
        s = _sweep(t, 0.08, 0.5)
        c.marker(98, 172, 385 * s, 108, "#F2E933", 0.95, seed=11)

    return Shot(
        name="03_alexis_arquette_article",
        source="Screenshot 2026-10-25 200405.png",
        seconds=3.0,
        description="news.com.au article: Alexis Arquette tell-all memoir, memoir marked yellow",
        cam_from=(1.0, 0.5, 0.5), cam_to=(1.05, 0.52, 0.55),
        grain=0.010, vig=0.16, chroma=1.0,
        build_static=back, build_static_front=front, draw_anim=anim,
    )


# --------------------------------------------------------------------------- #
# 04 — dark document excerpt: Dean Corll / Roy Ames warehouse raid
# --------------------------------------------------------------------------- #

def shot_04_corll() -> Shot:
    def back(c: Canvas):
        c.rect(0, 0, 1920, 1080, "#0A0A0A")
        c.noise(0.006, seed=55)
        c.vignette(0.34, 0.62)

    def front(c: Canvas):
        serif = "times"
        sz = 44
        x = 95
        c.text(x, 10, "hardcore child pornography; films depicting children in sexual bondage. In one of these", sz, serif, "#D8D3C9")
        c.text(x, 66, "letters, Smith had written that a particular film would\u2019ve been better if the producers", sz, serif, "#D8D3C9")
        p3 = "had, \u201ctossed in a stiff 14-year old.\u201d"
        c.text(x, 122, p3, sz, serif, "#D8D3C9")
        c.text(x + c.measure(p3, sz, serif) + 6, 116, "55", 22, serif, "#C9A227")
        c.text(215, 178, "A little over a year later in February 1975 another warehouse belonging to Roy", sz, serif, "#F2EEE6")
        p5 = "Ames was raided and two more tons of child pornography was seized."
        c.text(x, 234, p5, sz, serif, "#D8D3C9")
        c.text(x + c.measure(p5, sz, serif) + 6, 228, "56", 22, serif, "#C9A227")
        c.text(x + c.measure(p5, sz, serif) + 38, 234, "This time,", sz, serif, "#D8D3C9")
        p6 = "Houston PD identified 11 of Dean Corll\u2019s victims in the pornographic materials."
        c.text(x, 290, p6, sz, serif, "#D8D3C9")
        c.text(x + c.measure(p6, sz, serif) + 6, 284, "57", 22, serif, "#C9A227")
        c.text(x, 346, "\u201cJuvenile officers say 11 boys who were victims in the Houston mass murders case", 42, "serif-it", "#D8D3C9")
        p8 = "are pictured in sex materials seized in what police called a homosexual ring.\u201d"
        c.text(x, 402, p8, 42, "serif-it", "#D8D3C9")
        c.text(x + c.measure(p8, 42, "serif-it") + 6, 396, "58", 22, serif, "#C9A227")

        c.rect(60, 470, 1800, 2, "#39362F", 0.9)

        quote = [
            "\u201cJuvenile Lt. H.A Contreras said Detective John St. John and a partner met",
            "with officers Wednesday about the case of photographer Roy Clifton Ames,",
            "convicted in 1975 for using the mails to distribute obscene material. Ames",
            "was sentenced to a Springfield Mo., federal prison after photographs of 11",
            "Houston area victims of the mass murders were seized following the arrests",
            "and murder convictions of Elmer Wayne Henley Jr. and David Owen Brooks.",
        ]
        y = 560
        for ln in quote:
            c.text(140, y, ln, 44, serif, "#C9C4BA")
            y += 56

    def anim(c: Canvas, t: float):
        s = _sweep(t, 0.12, 0.58)
        prefix = "A little over a year later in February 1975 another warehouse"
        w = c.measure(prefix, 44, "times")
        c.marker(205, 186, (w + 10) * s, 52, "#B3121B", 0.88, seed=51)

    return Shot(
        name="04_corll_warehouse_excerpt",
        source="Screenshot 2026-10-25 200506.png",
        seconds=3.0,
        description="Dark document excerpt on the Corll case, red marker on the 1975 warehouse raid line",
        cam_from=(1.02, 0.5, 0.5), cam_to=(1.07, 0.46, 0.48),
        grain=0.012, vig=0.30,
        build_static=back, build_static_front=front, draw_anim=anim,
    )


# --------------------------------------------------------------------------- #
# 05 — caption band: "they were the economy"
# --------------------------------------------------------------------------- #

def shot_05_economy() -> Shot:
    def back(c: Canvas):
        c.rect(0, 0, 1920, 1080, "#191413")
        # diagonal woven texture
        for i in range(-1080, 1920, 26):
            c.line(i, 0, i + 1080, 1080, "#2B2320", 2, 0.35)
        for i in range(-1080, 1920, 44):
            c.line(i + 1080, 0, i, 1080, "#221B19", 2, 0.30)
        c.noise(0.02, seed=12)
        c.vignette(0.42, 0.62)

    def anim(c: Canvas, t: float):
        s = _sweep(t, 0.10, 0.55)
        c.marker(170, 430, 1600 * s, 210, "#7E1417", 0.92, seed=9)

    def front(c: Canvas):
        c.text(960, 535, "they were the economy", 148, "times", "#F5E7C8", anchor="mm")

    return Shot(
        name="05_they_were_the_economy",
        source="Screenshot 2026-10-25 200835.png",
        seconds=3.0,
        description="Cream serif caption 'they were the economy' on a dark red band over woven dark ground",
        cam_from=(1.0, 0.5, 0.5), cam_to=(1.06, 0.5, 0.5),
        grain=0.014, vig=0.36,
        build_static=back, draw_anim=anim, build_static_front=front,
    )


# --------------------------------------------------------------------------- #
# 06 — blurred documentary quote plate (gold marker on the quote)
# --------------------------------------------------------------------------- #

def shot_06_thug_quote() -> Shot:
    def back(c: Canvas):
        img = Image.open(asset("assets", "images", "investigative_journalist_blurred_bg.png")).convert("RGB")
        img = img.filter(ImageFilter.GaussianBlur(22))
        c.paste(img, 0, 0, w=1920, h=1080)
        c.rect(0, 0, 1920, 1080, "#3A1F14", 0.35)
        c.vignette(0.52, 0.62)

    X = 300
    SZ = 52
    STEP = 72
    L6 = "middle school. \u201cI broke my teacher\u2019s"
    L7 = "arm,\u201d he says matter-of-factly. \u201cTook his"

    def front(c: Canvas):
        y = 40
        lines = [
            "\u2026buying the cocaine, but when I got out I",
            "did what I wanted to do \u2013 fighting, all",
            "kinds of shit.\u201d A few years later, after a",
            "dispute over Thug\u2019s classroom antics",
            "turned physical, he got kicked out of",
            L6,
            L7,
            "ass out. Pussy-ass n***a.\u201d He spent the",
            "next four years in a harsh",
            "juvenile detention system. \u201cSeven in the",
        ]
        for ln in lines:
            c.text(X, y, ln, SZ, "sans", "#F2EFEA")
            y += STEP
        # gold phrase over the marker band
        x6 = X + c.measure("middle school. \u201c", SZ, "sans")
        c.text(x6, 40 + 5 * STEP, "I broke my teacher\u2019s", SZ, "sans", "#F5B301")
        c.text(X, 40 + 6 * STEP, "arm,\u201d", SZ, "sans", "#F5B301")

    def anim(c: Canvas, t: float):
        s = _sweep(t, 0.10, 0.55)
        x6 = X + c.measure("middle school. \u201c", SZ, "sans")
        w6 = c.measure("I broke my teacher\u2019s", SZ, "sans")
        c.marker(x6 - 8, 40 + 5 * STEP + 8, (w6 + 16) * s, 58, "#8A6A08", 0.92, seed=61)
        w7 = c.measure("arm,\u201d", SZ, "sans")
        c.marker(X - 8, 40 + 6 * STEP + 8, (w7 + 16) * s, 58, "#8A6A08", 0.92, seed=62)

    return Shot(
        name="06_thug_teacher_quote",
        source="Screenshot 2026-10-25 202808.png",
        seconds=3.0,
        description="Blurred documentary quote plate on Thug's school years, gold marker on the teacher quote",
        cam_from=(1.02, 0.5, 0.5), cam_to=(1.06, 0.53, 0.52),
        grain=0.014, vig=0.30,
        build_static=back, draw_anim=anim, build_static_front=front,
    )


# --------------------------------------------------------------------------- #
# 11 — Acoustic Kitty: "The First (and Last) Field Test" over sepia documents
# --------------------------------------------------------------------------- #

def shot_11_acoustic_kitty() -> Shot:
    def back(c: Canvas):
        c.rect(0, 0, 1920, 1080, "#4E4640")
        # scattered archival papers
        c.poly([(0, 120), (760, 40), (820, 620), (60, 700)], "#D6C7A8", 0.95)
        c.poly([(600, 0), (1500, 60), (1440, 560), (560, 520)], "#C9B896", 0.9)
        c.poly([(1150, 260), (1920, 180), (1920, 900), (1100, 860)], "#E2D3B0", 0.92)
        c.poly([(0, 640), (900, 560), (980, 1080), (0, 1080)], "#B3A184", 0.9)
        # dark blue corner scrap
        c.poly([(0, 0), (360, 0), (230, 300), (0, 240)], "#2E3C5E", 0.95)
        # faint handwriting-like strokes
        for i in range(22):
            x0 = 120 + (i * 173) % 1500
            y0 = 300 + (i * 247) % 620
            c.line(x0, y0, x0 + 130 + (i % 4) * 40, y0 + (i % 3) * 6 - 6, "#8A7A62", 3, 0.55)
        # big blurred ink stamp text
        c.text(820, 700, "C-90", 220, "times-bold", "#2A211A", alpha=0.7)
        c.img = c.img.filter(ImageFilter.GaussianBlur(9 * c.ss))
        c.draw = ImageDraw.Draw(c.img, "RGBA")
        c.rect(0, 0, 1920, 1080, "#3A2E22", 0.16)
        c.vignette(0.42, 0.66)

    def front(c: Canvas):
        c.text(270, 376, "The First (and Last) Field Test", 64, "times-bold", "#F2EFE8")
        body = [
            "After years of development and an estimated cost of $20 million",
            "(roughly $170 million today), Acoustic Kitty was ready for the real",
            "world.",
        ]
        y = 478
        for ln in body:
            c.text(270, y, ln, 54, "times", "#EDE8DF")
            y += 78
        x0 = 270 + c.measure("After years of development and an estimated cost of ", 54, "times")
        c.text(x0, 478, "$20 million", 54, "times", "#B08A2E")

    def anim(c: Canvas, t: float):
        s = _sweep(t, 0.08, 0.5)
        x0 = 270 + c.measure("After years of development and an estimated cost of ", 54, "times")
        w = c.measure("$20 million", 54, "times")
        c.marker(x0 - 8, 486, (w + 16) * s, 62, "#E8DC4A", 0.90, seed=71)

    return Shot(
        name="11_acoustic_kitty_field_test",
        source="Screenshot 2026-10-25 at 12-39-03 Unsettling Conspiracies That Turned Out True - YouTube.png",
        seconds=3.0,
        description="Sepia archival documents with Acoustic Kitty field-test caption, $20 million marked",
        cam_from=(1.05, 0.52, 0.5), cam_to=(1.0, 0.5, 0.5),
        grain=0.016, vig=0.30,
        build_static=back, draw_anim=anim, build_static_front=front,
    )


GROUP_B = [
    shot_03_alexis,
    shot_04_corll,
    shot_05_economy,
    shot_06_thug_quote,
    shot_11_acoustic_kitty,
]
