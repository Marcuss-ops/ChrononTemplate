"""Group A — web shots already covered by existing packs, rebuilt natively.

01 kuminga_espn_article   (emit_web_article_fold.cpp content)
02 al_capone_title        (emit_archival_cards.cpp / archival card content)
07 crt_alcohol_headline   (DocumentaryReferenceStills::crt_headline)
08 rainmaking_nyt         (DocumentaryReferenceStills::nyt_title)
09 pinto_highlight        (DocumentaryReferenceStills::doc_video_highlight)
10 tax_exempt_nyt         (DocumentaryReferenceStills::nyt_excerpt)

Each shot: static plate + animated marker sweep / camera drift + YouTube
player chrome kept in frame like the paused-player references.
"""

from __future__ import annotations

from typing import Callable, List

from PIL import Image, ImageFilter, ImageOps

from web_shot_kit import Canvas, Shot, asset


def _ease(t: float) -> float:
    return t * t * (3.0 - 2.0 * t)


def _sweep(t: float, t0: float = 0.10, t1: float = 0.55) -> float:
    if t <= t0:
        return 0.0
    if t >= t1:
        return 1.0
    return _ease((t - t0) / (t1 - t0))


# --------------------------------------------------------------------------- #
# 01 — ESPN article on a floating paper plate (Kuminga trade request)
# --------------------------------------------------------------------------- #

def shot_01_kuminga() -> Shot:
    def back(c: Canvas):
        # dark desk backdrop with soft dust
        c.rect(0, 0, 1920, 1080, "#15161A")
        for i in range(140):
            x = (i * 613) % 1920
            y = (i * 331) % 1080
            c.ellipse(x, y, 2 + (i % 3), 2 + (i % 3), "#8A8E99", 0.10)
        c.grad_rect(0, 0, 1920, 1080, (10, 11, 14), (10, 11, 14), alpha1=0.0, alpha2=0.55)
        # paper plate, slightly rotated
        c.poly([(238, 46), (1706, 22), (1720, 1052), (252, 1076)], "#F4F2EE", 1.0)
        c.poly([(238, 46), (1706, 22), (1708, 40), (240, 64)], "#FFFFFF", 0.55)

    def front(c: Canvas):
        x = 320
        c.text(x, 108, "Sources: Jonathan Kuminga", 47, "sans-bold", "#202124")
        c.text(x, 172, "demanding trade away from Warriors", 47, "sans-bold", "#202124")
        c.text(x, 252, "Anthony Slater and Shams Charania", 18, "sans-med", "#5F6368")
        c.text(x, 282, "Jan 15, 2026, 08:58 PM", 15, "sans", "#80868B")
        # share / like row
        c.text(x, 330, "\u2b06 Share", 19, "sans-med", "#3C4043")
        c.text(x + 170, 330, "\u2661 Like", 19, "sans-med", "#3C4043")
        c.text(1345, 330, "\u2764\ufe0f\U0001f62d\U0001f622  4.0K", 17, "sans", "#5F6368")
        c.rect(x, 382, 1300, 1.5, "#DADCE0")

        sz = 22
        dark, blue = "#202124", "#1A73E8"
        c.text(x, 418, "SAN FRANCISCO -- On the first day he became eligible to be moved,",
               sz, "sans", dark)
        # line 2: black prefix, linked (blue) name, black suffix — drawn as
        # segments so the blue glyphs land exactly over their phrase
        p2a = "fifth-year forward "
        p2b = "Jonathan Kuminga"
        c.text(x, 458, p2a, sz, "sans", dark)
        x2 = x + c.measure(p2a, sz, "sans")
        c.text(x2, 458, p2b, sz, "sans", blue)
        c.text(x2 + c.measure(p2b, sz, "sans"), 458,
               " demanded a trade away from the", sz, "sans", dark)
        # line 3: linked team at line start, then black suffix
        p3a = "Golden State Warriors"
        c.text(x, 498, p3a, sz, "sans", blue)
        c.text(x + c.measure(p3a, sz, "sans"), 498,
               ", league sources told ESPN.", sz, "sans", dark)

        para2 = [
            "Kuminga could not be traded until Thursday, according to the terms",
            "of the contract he signed this summer. The trade deadline is Feb. 5.",
        ]
        y = 578
        for ln in para2:
            c.text(x, y, ln, 22, "sans", "#202124")
            y += 40

        para3 = [
            "Kuminga's roller-coaster tenure with the Warriors is perhaps at its",
            "lowest point. He started the first 12 games of the season -- with coach",
            "Steve Kerr calling him a secure starter following a hot start -- but a",
            "patch of struggles led to a demotion, landing poorly with the 23-year-old.",
        ]
        y = 668
        for ln in para3:
            c.text(x, y, ln, 22, "sans", "#202124")
            y += 40

        # Editor's picks card
        c.rect(1050, 812, 570, 260, "#FFFFFF", 0.9, radius=6)
        c.text(1080, 836, "EDITOR'S PICKS", 14, "sans-bold", "#5F6368", spacing=1.2)
        c.rect(1080, 872, 82, 62, "#C9D1D9", 1.0, radius=4)
        c.text(1180, 876, "NBA trade buzz: All the moves that", 16, "sans-med", "#1A73E8")
        c.text(1180, 900, "did and didn't happen on deadline day", 16, "sans-med", "#1A73E8")
        c.text(1180, 930, "ESPN", 13, "sans", "#80868B")
        c.rect(1080, 962, 82, 62, "#C9D1D9", 1.0, radius=4)
        c.text(1180, 966, "Six NBA trade proposals: How the", 16, "sans-med", "#1A73E8")
        c.text(1180, 990, "Lakers, Bucks, Warriors and others", 16, "sans-med", "#1A73E8")

    return Shot(
        name="01_kuminga_espn_article",
        source="Screenshot 2026-10-09 090957.png",
        seconds=3.0,
        description="ESPN article plate on dark desk: Kuminga demanding trade from Warriors",
        cam_from=(1.02, 0.5, 0.5), cam_to=(1.07, 0.47, 0.46),
        grain=0.010, vig=0.24,
        build_static=back, build_static_front=front,
    )


# --------------------------------------------------------------------------- #
# 02 — Al Capone chapter title over B&W portrait
# --------------------------------------------------------------------------- #

def shot_02_capone() -> Shot:
    def back(c: Canvas):
        c.rect(0, 0, 1920, 1080, "#0B0B0C")
        img = Image.open(asset("assets", "archival_refs_v2", "al_capone_trio_source.png")).convert("L")
        w, h = img.size
        # tight crop on the standing central figure (hat, face, tie)
        crop = img.crop((int(w * 0.42), int(h * 0.02), int(w * 0.82), int(h * 0.90)))
        crop = ImageOps.fit(crop.convert("RGB"), (1920, 1080), Image.LANCZOS, centering=(0.5, 0.06))
        c.paste(crop, 0, 0, alpha=1.0)
        c.rect(0, 0, 1920, 1080, "#08080A", 0.30)
        c.grad_rect(0, 0, 1920, 360, (8, 8, 10), (8, 8, 10), alpha1=0.55, alpha2=0.0)
        c.grad_rect(0, 620, 1920, 460, (8, 8, 10), (8, 8, 10), alpha1=0.0, alpha2=0.85)
        c.vignette(0.52, 0.58)

    def front(c: Canvas):
        c.text(960, 442, "THE BRUTAL RISE AND FALL OF AL CAPONE", 54, "oswald-bold", "#F2F2F0", anchor="ma")
        c.rect(500, 548, 920, 2, "#E8E5DE", 0.85)
        c.text(960, 584, "AMERICAN HISTORY'S KINGPIN OF CRIME", 30, "oswald-med", "#E8E5DE", anchor="ma", spacing=2.0)

    return Shot(
        name="02_al_capone_title",
        source="Screenshot 2026-10-21 at 10-01-01 How Al Capone Took Over Chicago at 26 No AI - YouTube.png",
        seconds=3.0,
        description="Tight B&W Capone face crop with THE BRUTAL RISE AND FALL title treatment",
        cam_from=(1.05, 0.52, 0.42), cam_to=(1.0, 0.5, 0.5),
        grain=0.016, vig=0.34,
        build_static=back, build_static_front=front,
    )


# --------------------------------------------------------------------------- #
# 07 — CRT newspaper headline with chroma fringe (alcohol poison / benzine)
# --------------------------------------------------------------------------- #

def shot_07_crt_headline() -> Shot:
    LINES = ["GOVERNMENT TO DOUBLE", "ALCOHOL POISON CONTENT", "AND ALSO ADD BENZINE"]
    CENTERS = [855, 927, 1004]
    YS = [-22, 136, 284]

    def back(c: Canvas):
        c.rect(0, 0, 1920, 1080, "#080A0C")
        c.noise(0.004, seed=1984)
        c.grad_rect(0, 0, 1920, 520, (16, 18, 20), (16, 18, 20), alpha1=0.34, alpha2=0.0)
        img = Image.open(asset("assets", "archival_refs_v2", "al_capone_trio_source.png")).convert("RGB")
        c.paste(img, 232, 823, w=1440, h=257, alpha=1.0)
        c.rect(232, 823, 1440, 257, "#080A0C", 0.20)

    def front(c: Canvas):
        for i, line in enumerate(LINES):
            y = YS[i]
            x = CENTERS[i] - 1980 / 2.0
            # chroma split copies
            for dx, dy, col, a in ((-5, -1, "#D5D000", 0.62), (5, 1, "#67B9D4", 0.42)):
                c.text(x + dx, y + dy, line, 135, "serif-bold", col, alpha=a)
            c.text(x, y, line, 135, "serif-bold", "#DDE4E8")
        c.rect(420, 542, 335, 3, "#AEB7B3", 0.62)
        c.text(96, 574, "SMELL WARNS DRINKERS", 82, "oswald", "#DDE4E8")
        c.rect(910, 535, 4, 205, "#8ED8E9", 0.8)
        c.poly([(912, 516), (922, 526), (912, 536), (902, 526)], "#DDECF0", 0.92)

    def anim(c: Canvas, t: float):
        # per-letter yellow-green highlight sweep, caught mid-reveal like the
        # reference frame ("GOVERNMENT TO" boxed, "A" of ALCOHOL boxed)
        s = _sweep(t, 0.15, 0.65)
        targets = [(0, list(range(13))), (1, [0])]
        for li, idxs in targets:
            line = LINES[li]
            y = YS[li]
            x = CENTERS[li] - 1980 / 2.0
            n = len(idxs)
            for k, gi in enumerate(idxs):
                if (k + 1) / n > s:
                    break
                ch = line[gi]
                if ch == " ":
                    continue
                gx = x + c.measure(line[:gi], 135, "serif-bold")
                gw = c.measure(ch, 135, "serif-bold")
                c.rect(gx - 4, y + 12, gw + 8, 118, "#C9DC28", 0.85)

    return Shot(
        name="07_crt_alcohol_headline",
        source="Screenshot 2026-10-25 at 12-18-39 Unsettling Conspiracies That Turned Out True - YouTube.png",
        seconds=3.0,
        description="CRT-fringed vintage headline: GOVERNMENT TO DOUBLE ALCOHOL POISON CONTENT",
        cam_from=(1.0, 0.5, 0.5), cam_to=(1.045, 0.5, 0.42),
        grain=0.014, vig=0.26,
        build_static=back, build_static_front=front, draw_anim=anim,
    )


# --------------------------------------------------------------------------- #
# 08 — NYT headline with yellow marker ("Rainmaking Is Used As Weapon by U.S.")
# --------------------------------------------------------------------------- #

def shot_08_rainmaking() -> Shot:
    def back(c: Canvas):
        c.rect(0, 0, 1920, 1080, "#E9E8E6")
        c.noise(0.009, seed=912)

    def anim(c: Canvas, t: float):
        s = _sweep(t)
        c.marker(236, 222, 1474 * s, 101, "#E6E300", 0.97, seed=21)
        c.marker(237, 323, 333 * s, 99, "#E6E300", 0.97, seed=22)

    def front(c: Canvas):
        c.text(43, 208, "Rainmaking Is Used As Weapon", 95, "serif-black-it", "#10100F")
        c.text(-498, 308, "by U.S.", 97, "serif-black-it", "#10100F")
        c.rect(236, 477, 1484, 2, "#D1D0CD", 0.78)
        # NYT share pill + circles
        c.rect(258, 598, 352, 75, "#F2F1EF", 0.9, radius=38)
        c.text(278, 611, "\u25a3  Share full article", 25, "sans-semi", "#353432")
        c.ellipse(651, 594, 84, 84, "#F4F3F1", 0.9)
        c.text(672, 608, "\u2197", 35, "dejavu", "#353432")
        c.ellipse(775, 594, 84, 84, "#F4F3F1", 0.9)
        c.text(794, 605, "\u25af", 35, "dejavu", "#353432")
        c.text(-310, 774, "By Seymour M. Hersh  Special to The New York Times", 27, "sans-semi", "#454340")
        c.text(-570, 825, "July 3, 1972", 24, "sans-med", "#716E68")
        c.rect(236, 920, 1484, 1, "#D5D4D1", 0.82)

    return Shot(
        name="08_rainmaking_nyt",
        source="Screenshot 2026-10-25 at 12-23-00 Unsettling Conspiracies That Turned Out True - YouTube.png",
        seconds=3.0,
        description="NYT page: Rainmaking Is Used As Weapon by U.S. with marker sweep",
        cam_from=(1.02, 0.5, 0.5), cam_to=(1.0, 0.5, 0.52),
        grain=0.010, vig=0.16,
        build_static=back, draw_anim=anim, build_static_front=front,
    )


# --------------------------------------------------------------------------- #
# 09 — blurred documentary plate, Pinto crash-test claim in gold
# --------------------------------------------------------------------------- #

def shot_09_pinto() -> Shot:
    def back(c: Canvas):
        img = Image.open(asset("assets", "images", "investigative_journalist_blurred_bg.png")).convert("RGB")
        img = img.filter(ImageFilter.GaussianBlur(6))
        c.paste(img, 0, 0, w=1920, h=1080)
        c.rect(0, 0, 1920, 1080, "#80685B", 0.24)
        # vignette baked into the plate
        for r, a in ((0, 0),):
            pass
        c.vignette(0.62, 0.67)

    def anim(c: Canvas, t: float):
        s = _sweep(t, 0.05, 0.5)
        c.marker(133, 453, 1554 * s, 56, "#8F7313", 0.78, seed=31)

    def front(c: Canvas):
        c.text(-600, 430, "Records later revealed that", 48, "sans", "#F1EEE9")
        c.text(1300, 430, "before", 48, "sans", "#F1EEE9")
        c.text(-5, 442, "Ford secretly crash-tested the Pinto more than forty times", 55, "sans", "#F1D923")
        c.text(-169, 533, "the fuel tank ruptured in every test performed at speeds over twenty-five miles per hour.", 47, "sans", "#EEEAE5")

    return Shot(
        name="09_pinto_highlight",
        source="Screenshot 2026-10-25 at 12-25-51 Unsettling Conspiracies That Turned Out True - YouTube.png",
        seconds=3.0,
        description="Blurred documentary plate: Ford Pinto crash-test claim highlighted gold",
        cam_from=(1.0, 0.5, 0.5), cam_to=(1.05, 0.52, 0.5),
        grain=0.014, vig=0.18,
        build_static=back, draw_anim=anim, build_static_front=front,
    )


# --------------------------------------------------------------------------- #
# 10 — NYT excerpt, tight zoom, "lost its tax-exempt status" marked
# --------------------------------------------------------------------------- #

def shot_10_tax_exempt() -> Shot:
    def back(c: Canvas):
        c.rect(0, 0, 1920, 1080, "#E9E8E6")
        c.noise(0.012, seed=731)

    def anim(c: Canvas, t: float):
        s = _sweep(t, 0.12, 0.58)
        c.marker(348, 376, 1215 * s, 126, "#E9E600", 0.97, seed=41)

    def front(c: Canvas):
        serif = "serif"
        c.text(-244, 180, "Federal authorities ruled that the church's activities were", 78, serif, "#77736F")
        c.rect(1137, 277, 714, 4, "#8191B1", 0.76)
        c.text(-262, 367, "and it lost its tax-exempt status.", 79, serif, "#11100F")
        c.text(-454, 545, "ordered to pay those taxes. Years of", 77, serif, "#77736F")
        c.text(-262, 718, "appeals followed and lawsuits flooded the IRS.", 77, serif, "#77736F")
        c.text(-453, 887, "From 1973-1977, something was", 77, serif, "#77736F")

    return Shot(
        name="10_tax_exempt_nyt",
        source="Screenshot 2026-10-25 at 12-28-56 Unsettling Conspiracies That Turned Out True - YouTube.png",
        seconds=3.0,
        description="Tight NYT excerpt zoom: church lost its tax-exempt status, marker sweep",
        cam_from=(1.03, 0.5, 0.5), cam_to=(1.08, 0.46, 0.52),
        grain=0.010, vig=0.14,
        build_static=back, draw_anim=anim, build_static_front=front,
    )


GROUP_A = [
    shot_01_kuminga,
    shot_02_capone,
    shot_07_crt_headline,
    shot_08_rainmaking,
    shot_09_pinto,
    shot_10_tax_exempt,
]
