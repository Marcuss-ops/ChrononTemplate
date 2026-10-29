"""Group C — web shots 12-16, rebuilt natively.

12 sabotage_manual_glow   (CIA sabotage manual zoom, glowing yellow line)
13 foia_finkel_zoom       (FOIA / David Finkel tight zoom on grey screen grid)
14 vw_40_times            (VW Dieselgate serif zoom, "40 times" marker)
15 cnbc_sbf_profile_tilt  (tilted CNBC SBF profile page + orange chyron)
16 nbc_swindled_8b        (NBC TECH headline, two yellow markers, tilted)

Each shot: static plate + animated marker sweep / camera drift, plus the
small bottom-right player icon cluster where the reference shows it.
"""

from __future__ import annotations

from PIL import Image, ImageDraw, ImageFilter

from web_shot_kit import (Canvas, Shot, get_font, warp_perspective)


def _ease(t: float) -> float:
    return t * t * (3.0 - 2.0 * t)


def _sweep(t: float, t0: float = 0.10, t1: float = 0.55) -> float:
    if t <= t0:
        return 0.0
    if t >= t1:
        return 1.0
    return _ease((t - t0) / (t1 - t0))


# --------------------------------------------------------------------------- #
# 12 — CIA sabotage manual zoom, glowing yellow line
# --------------------------------------------------------------------------- #

def shot_12_sabotage_glow() -> Shot:
    GLOW_LINE = "ting fires, flooding warehouses, break"

    def back(c: Canvas):
        c.rect(0, 0, 1920, 1080, "#070706")
        for i in range(70):
            x = (i * 617) % 1920
            y = (i * 353) % 1080
            c.ellipse(x, y, 2 + (i % 2), 2 + (i % 2), "#8A8578", 0.10)
        c.noise(0.006, seed=1212)
        c.vignette(0.36, 0.60)

    def front(c: Canvas):
        x = -140
        c.text(x, 210, "was written during active wartime, the", 130, "serif", "#6B6156")
        c.text(x, 370, "gestions for causing physical violence", 130, "serif", "#4E4841")
        # soft glow behind the highlighted line
        layer = Image.new("RGBA", c.img.size, (0, 0, 0, 0))
        d = ImageDraw.Draw(layer)
        f = get_font("serif", 130, c.ss)
        d.text((x * c.ss, 530 * c.ss), GLOW_LINE, font=f, fill=(242, 205, 82, 210))
        c.img.alpha_composite(layer.filter(ImageFilter.GaussianBlur(16 * c.ss)))
        c.draw = ImageDraw.Draw(c.img, "RGBA")
        c.text(x, 530, GLOW_LINE, 130, "serif", "#F5D24A")
        c.text(x, 690, "s many suggestions for how to just get", 130, "serif", "#4E4841")
        c.text(x, 850, "ithin a bureaucracy or office setting.", 130, "serif", "#6B6156")

    return Shot(
        name="12_sabotage_manual_glow",
        source="Screenshot 2026-10-25 at 12-44-37 Unsettling Conspiracies That Turned Out True - YouTube.png",
        seconds=3.0,
        description="Dark zoom of the Simple Sabotage Field Manual text, one line glowing yellow",
        cam_from=(1.08, 0.38, 0.5), cam_to=(1.02, 0.55, 0.5),
        grain=0.014, vig=0.30,
        build_static=back, build_static_front=front,
    )


# --------------------------------------------------------------------------- #
# 13 — FOIA request zoom on a grey filmed-screen grid
# --------------------------------------------------------------------------- #

def shot_13_foia() -> Shot:
    L1 = "filed a Freedom of Information Act reques"
    L2 = "n Post reporter David Finkel in his book '"

    def back(c: Canvas):
        c.rect(0, 0, 1920, 1080, "#D9D8D3")
        c.screen_grid(3, 0.05)
        c.img = c.img.filter(ImageFilter.GaussianBlur(1.2 * c.ss))
        c.draw = ImageDraw.Draw(c.img, "RGBA")

    def front(c: Canvas):
        c.text(-90, 300, L1, 112, "helv-med", "#101010")
        c.text(-70, 470, L2, 112, "helv-med", "#101010")

    def anim(c: Canvas, t: float):
        s = _sweep(t, 0.10, 0.55)
        w = c.measure("filed a Freedom of Information Act", 112, "helv-med")
        c.marker(-95, 312, (w + 10) * s, 96, "#E6E32E", 0.95, seed=13)

    return Shot(
        name="13_foia_finkel_zoom",
        source="Screenshot 2026-10-25 at 12-47-03 Unsettling Conspiracies That Turned Out True - YouTube.png",
        seconds=3.0,
        description="Tight FOIA-request zoom with chroma fringe, marker over 'filed a Freedom of Information Act'",
        cam_from=(1.03, 0.5, 0.5), cam_to=(1.09, 0.47, 0.52),
        grain=0.012, vig=0.12, chroma=2.0,
        build_static=back, build_static_front=front, draw_anim=anim,
    )


# --------------------------------------------------------------------------- #
# 14 — VW Dieselgate serif zoom, "40 times the permitted levels" marked
# --------------------------------------------------------------------------- #

def shot_14_vw() -> Shot:
    def back(c: Canvas):
        c.rect(0, 0, 1920, 1080, "#E9E8E2")
        c.screen_grid(3, 0.05)
        c.vignette(0.16, 0.72)

    def front(c: Canvas):
        sz = 103
        x = -120
        c.text(x, 150, "sting in May 2014 that led the California Air R", sz, "times", "#A6A39B")
        c.text(x, 300, "lkswagen was conducted by researchers at Wes", sz, "times", "#A6A39B")
        c.text(x, 450, "missions from two VW models equipped with th", sz, "times", "#A6A39B")
        c.text(x, 600, "sel engine. The researchers found that when tes", sz, "times", "#A6A39B")
        x5 = -140
        c.text(x5, 750, "most ", sz, "times", "#A6A39B")
        x_bold = x5 + c.measure("most ", sz, "times")
        c.text(x_bold, 750, "40 times", sz, "times-bold", "#2E2C28")
        x_tail = x_bold + c.measure("40 times", sz, "times-bold")
        c.text(x_tail, 750, " the permitted levels of nitrogen", sz, "times", "#A6A39B")

    def anim(c: Canvas, t: float):
        s = _sweep(t, 0.10, 0.55)
        x5 = -140
        x_bold = x5 + c.measure("most ", 103, "times")
        w = c.measure("40 times", 103, "times-bold") + c.measure(" the permitted levels", 103, "times")
        c.marker(x_bold - 8, 758, (w + 16) * s, 92, "#E6E32E", 0.95, seed=14)

    return Shot(
        name="14_vw_40_times",
        source="Screenshot 2026-10-25 at 12-51-15 Unsettling Conspiracies That Turned Out True - YouTube.png",
        seconds=3.0,
        description="Serif zoom of the VW emissions story, '40 times the permitted levels' marked yellow",
        cam_from=(1.02, 0.5, 0.5), cam_to=(1.08, 0.53, 0.47),
        grain=0.010, vig=0.14,
        build_static=back, build_static_front=front, draw_anim=anim,
    )


# --------------------------------------------------------------------------- #
# 15 — tilted CNBC SBF profile page with black letterbox + orange chyron
# --------------------------------------------------------------------------- #

def shot_15_cnbcsbf() -> Shot:
    def back(c: Canvas):
        c.rect(0, 0, 1920, 1080, "#EDEBE7")
        c.screen_grid(4, 0.04)

    def front(c: Canvas):
        # top nav bar
        c.poly([(112, 196), (138, 186), (138, 226), (112, 226)], "#55565A")
        c.ellipse(206, 194, 30, 30, "#55565A")
        c.ellipse(214, 202, 15, 15, "#EDEBE7")
        nav = [("Home", 150), ("Companies", 320), ("Markets", 555), ("Street Talk", 725),
               ("Politics", 950), ("Policy", 1130), ("World", 1285), ("Property", 1425)]
        for label, x in nav:
            c.text(x, 200, label, 28, "helv", "#55565A")
        c.rect(552, 244, 112, 3, "#2B6FD6")
        # headline
        c.text(960, 340, "Why this 30-year-old crypto", 122, "serif", "#1B1B1D", anchor="ma")
        c.text(960, 500, "billionaire wants to give his", 122, "serif", "#1B1B1D", anchor="ma")
        c.text(960, 660, "fortune away", 122, "serif", "#1B1B1D", anchor="ma")
        # italic deck
        deck = ("Sam Bankman-Fried is worth $26 billion, but he drives a Toyota Corolla, "
                "sleeps on a beanbag and has a Robin Hood-like philosophy.")
        c.text(960, 900, deck, 40, "serif-it", "#6C6B68", anchor="ma")

    def warp_fn(frame: Image.Image, t: float) -> Image.Image:
        out = warp_perspective(
            frame,
            [(0, 0), (1920, 0), (1920, 1080), (0, 1080)],
            [(150, 240), (1830, 130), (1800, 975), (70, 895)],
            border_value=(237, 235, 231),
        )
        d = ImageDraw.Draw(out)
        d.rectangle((0, 0, 1920, 128), fill=(8, 8, 9))
        d.rectangle((0, 984, 1920, 1080), fill=(8, 8, 9))
        f = get_font("oswald-bold", 42, 1.0)
        d.text((960, 1030), "HE DECIDED THAT", font=f, fill=(232, 135, 30), anchor="mm")
        # small show logo, bottom-left
        for i, h in enumerate((34, 46, 38)):
            d.rectangle((28 + i * 16, 1042 - h, 28 + i * 16 + 9, 1042), fill=(210, 210, 210))
        return out

    return Shot(
        name="15_cnbcsbf_profile_tilt",
        source="Screenshot 2026-10-26 085622.png",
        seconds=3.0,
        description="Tilted CNBC profile page: 'Why this 30-year-old crypto billionaire wants to give his fortune away'",
        cam_from=(1.0, 0.5, 0.5), cam_to=(1.035, 0.5, 0.5),
        grain=0.012, vig=0.18,
        build_static=back, build_static_front=front, warp_fn=warp_fn,
    )


# --------------------------------------------------------------------------- #
# 16 — NBC TECH: "How Sam Bankman-Fried swindled $8 billion..."
# --------------------------------------------------------------------------- #

def shot_16_nbc() -> Shot:
    L1 = "How Sam Bankman-Fried swindled $8"
    L2 = "billion in customer money, according"

    def back(c: Canvas):
        c.rect(0, 0, 1920, 1080, "#F4F3F0")
        c.screen_grid(3, 0.04)

    def front(c: Canvas):
        c.text(140, 150, "TECH", 26, "sans-bold", "#6E6E6E", spacing=3.0)
        c.text(120, 210, L1, 74, "helv-bold", "#0E0E10")
        c.text(120, 322, L2, 74, "helv-bold", "#0E0E10")
        c.text(120, 434, "to federal prosecutors", 74, "helv-bold", "#0E0E10")
        c.text(125, 575, "PUBLISHED SUN, DEC 18 2022\u00b78:00 AM EST | UPDATED MON, DEC 19 2022\u00b72:06 PM EST",
               22, "sans-med", "#6F7076", spacing=1.6)
        # author row
        for ax in (130, 510):
            c.ellipse(ax, 655, 80, 80, "#9AA0A6")
            c.ellipse(ax + 22, 677, 36, 36, "#7E848A")
        c.text(235, 650, "Rohan Goswami", 27, "sans-bold", "#1A1A1C")
        c.text(235, 692, "@IN/ROHANGOSWAMINBC/", 21, "sans-semi", "#2E6FD6")
        c.text(235, 726, "@ROGOSWAMI", 21, "sans-semi", "#2E6FD6")
        c.text(615, 650, "MacKenzie Sigalos", 27, "sans-bold", "#1A1A1C")
        c.text(615, 692, "@KENZIESIGALOS", 21, "sans-semi", "#2E6FD6")

    def anim(c: Canvas, t: float):
        s = _sweep(t, 0.10, 0.55)
        s2 = _sweep(t, 0.30, 0.75)
        x0 = 120 + c.measure("How Sam Bankman-Fried ", 74, "helv-bold")
        w1 = c.measure("swindled $8", 74, "helv-bold")
        c.marker(x0 - 6, 222, (w1 + 12) * s, 88, "#E6E32E", 0.95, seed=161)
        w2 = c.measure("billion in customer money,", 74, "helv-bold")
        c.marker(114, 334, (w2 + 12) * s2, 88, "#E6E32E", 0.95, seed=162)

    def warp_fn(frame: Image.Image, t: float) -> Image.Image:
        out = warp_perspective(
            frame,
            [(0, 0), (1920, 0), (1920, 1080), (0, 1080)],
            [(70, 120), (1855, 60), (1835, 1005), (55, 955)],
        )
        d = ImageDraw.Draw(out)
        d.rectangle((0, 1072, 1920, 1080), fill=(46, 125, 50))
        return out

    return Shot(
        name="16_nbc_swindled_8b",
        source="Screenshot 2026-10-26 085659.png",
        seconds=3.0,
        description="NBC TECH headline on SBF swindling $8 billion, two yellow markers, tilted page",
        cam_from=(1.01, 0.5, 0.5), cam_to=(1.05, 0.51, 0.48),
        grain=0.010, vig=0.14,
        build_static=back, build_static_front=front, draw_anim=anim, warp_fn=warp_fn,
    )


GROUP_C = [
    shot_12_sabotage_glow,
    shot_13_foia,
    shot_14_vw,
    shot_15_cnbcsbf,
    shot_16_nbc,
]
