"""Group E — the 2026-10-27/28 web screenshots, rebuilt natively.

22 ivie_facebook          (mothers' groups Facebook post excerpt, yellow marker)
23 black_vault_foia       (Black Vault / Greenewald FOIA excerpt, two markers)
24 big_foot_pizza         (Pizza Hut 'The Big Foot' promo excerpt, olive markers)

Per request none of these carry YouTube player chrome.
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


def _blur(c: Canvas, radius: float):
    c.img = c.img.filter(ImageFilter.GaussianBlur(radius * c.ss))
    c.draw = ImageDraw.Draw(c.img, "RGBA")


# --------------------------------------------------------------------------- #
# 22 — Ivie: Facebook mothers' groups post excerpt
# --------------------------------------------------------------------------- #

def shot_22_ivie() -> Shot:
    PHRASE = "she immediately reached out on Facebook to mothers' groups in the"

    def back(c: Canvas):
        c.rect(0, 0, 1920, 1080, "#E8E8E6")
        c.noise(0.010, seed=2222)
        c.vignette(0.16, 0.72)

    def front(c: Canvas):
        sz = 40
        x = 150
        c.text(x, 381, "Ivie said " + PHRASE, sz, "sans", "#232323")
        c.text(x, 462, "area and the post started to share rapidly. Within hours, the post had reached",
               sz, "sans", "#232323")
        c.text(x, 543, "Jennifer's friend who got in touch with her.", sz, "sans", "#232323")

    def anim(c: Canvas, t: float):
        s = _sweep(t, 0.10, 0.55)
        x0 = 150 + c.measure("Ivie said ", 40, "sans")
        w = c.measure(PHRASE, 40, "sans")
        c.marker(x0 - 6, 387, (w + 12) * s, 52, "#E8E300", 0.92, seed=22)

    return Shot(
        name="22_ivie_facebook",
        source="Screenshot 2026-10-27 140914.png",
        seconds=3.0,
        description="Light article excerpt: Ivie reached out to mothers' groups on Facebook, marker sweep",
        cam_from=(1.02, 0.5, 0.5), cam_to=(1.07, 0.48, 0.52),
        grain=0.010, vig=0.16,
        build_static=back, build_static_front=front, draw_anim=anim,
    )


# --------------------------------------------------------------------------- #
# 23 — Black Vault / Greenewald FOIA excerpt
# --------------------------------------------------------------------------- #

def shot_23_black_vault() -> Shot:
    def back(c: Canvas):
        c.rect(0, 0, 1920, 1080, "#EDECEA")
        c.noise(0.010, seed=2323)
        c.grad_rect(1120, 0, 800, 1080, (237, 236, 234), (196, 194, 190), alpha1=0.0, alpha2=0.55, vertical=False)

    def front(c: Canvas):
        sz = 54
        x = 90
        l1 = "searchable online database. The database is on the Black Vault, a website h"
        c.text(x, 114, l1, sz, "times", "#262624")
        ux = x + c.measure("searchable online database. The database is on the ", sz, "times")
        c.rect(ux, 172, c.measure("Black Vault", sz, "times"), 3, "#262624", 0.9)
        c.text(x, 224, "created in 1996 at the tender age of 15 to give the public access to", sz, "times", "#262624")
        c.text(x, 333, "government secrets.", sz, "times", "#262624")
        c.text(x, 406, "Since then, Greenewald has made over 5,000 Freedom of Information Act", sz, "times", "#262624")
        c.text(x, 497, "(FOIA) requests and has shared over 1.4 million pages of declassified", sz, "times", "#262624")
        c.text(x, 588, "documents on his website, shedding light on supposed government cover-", sz, "times", "#262624")
        c.text(x, 679, "ups ranging from UFOs to CIA mind-control experiments to the Benghazi", sz, "times", "#262624")
        c.text(x, 770, "embassy attacks in 2012.", sz, "times", "#262624")

    def anim(c: Canvas, t: float):
        s1 = _sweep(t, 0.10, 0.50)
        s2 = _sweep(t, 0.35, 0.80)
        sz = 54
        x = 90
        w1 = c.measure("created in 1996", sz, "times")
        c.marker(x - 6, 231, (w1 + 12) * s1, 62, "#E8E300", 0.92, seed=231)
        x2 = x + c.measure("(FOIA) requests and has shared ", sz, "times")
        w2 = c.measure("over 1.4 million pages of declassified", sz, "times")
        c.marker(x2 - 6, 504, (w2 + 12) * s2, 62, "#E8E300", 0.92, seed=232)
        x3 = x
        w3 = c.measure("documents on his website", sz, "times")
        c.marker(x3 - 6, 595, (w3 + 12) * s2, 62, "#E8E300", 0.92, seed=233)

    return Shot(
        name="23_black_vault_foia",
        source="Screenshot 2026-10-27 141145.png",
        seconds=3.0,
        description="Serif article zoom: Black Vault founder's 5,000+ FOIA requests, two marker sweeps",
        cam_from=(1.03, 0.5, 0.5), cam_to=(1.08, 0.47, 0.51),
        grain=0.010, vig=0.18,
        build_static=back, build_static_front=front, draw_anim=anim,
    )


# --------------------------------------------------------------------------- #
# 24 — Pizza Hut 'The Big Foot' promo excerpt
# --------------------------------------------------------------------------- #

def shot_24_big_foot() -> Shot:
    sz = 40
    x = 130
    # L1 fully marked; L2 mixes marked/plain; L3 plain then marked; L4 marked
    L1 = "In 1993, Pizza Hut released The Big Foot, a massive, 2 feet long by 1-foot"
    L2A = "wide square pizza creation."
    L2B = " This promotion helped lift Pizza Hut's"
    L3A = "sales to $5.7 billion,"
    L3B = " with The Big Foot accounting for 18%"
    L4 = "of total sales."

    def back(c: Canvas):
        c.rect(0, 0, 1920, 1080, "#F0EFEC")
        c.noise(0.010, seed=2424)
        c.vignette(0.16, 0.72)

    def front(c: Canvas):
        c.text(x, 390, "The Big Foot", 50, "sans-bold", "#141414")
        c.text(x, 495, L1, sz, "sans", "#141414")
        c.text(x, 556, L2A, sz, "sans", "#141414")
        xa = x + c.measure(L2A, sz, "sans")
        c.text(xa, 556, L2B, sz, "sans", "#8A8A8A")
        c.text(x, 617, L3A, sz, "sans", "#8A8A8A")
        xb = x + c.measure(L3A, sz, "sans")
        c.text(xb, 617, L3B, sz, "sans", "#141414")
        c.text(x, 678, L4, sz, "sans", "#141414")

    def anim(c: Canvas, t: float):
        s = _sweep(t, 0.10, 0.55)
        s2 = _sweep(t, 0.40, 0.85)
        col = "#B9A916"
        c.marker(x - 6, 501, (c.measure(L1, sz, "sans") + 12) * s, 52, col, 0.95, seed=241)
        c.marker(x - 6, 562, (c.measure(L2A, sz, "sans") + 12) * s, 52, col, 0.95, seed=242)
        xb = x + c.measure(L3A, sz, "sans")
        c.marker(xb - 6, 623, (c.measure(L3B, sz, "sans") + 12) * s2, 52, col, 0.95, seed=243)
        c.marker(x - 6, 684, (c.measure(L4, sz, "sans") + 12) * s2, 52, col, 0.95, seed=244)

    return Shot(
        name="24_big_foot_pizza",
        source="Screenshot 2026-10-27 171823.png",
        seconds=3.0,
        description="Wide article excerpt: Pizza Hut 'The Big Foot' promo of 1993, olive marker sweeps",
        cam_from=(1.02, 0.5, 0.52), cam_to=(1.06, 0.52, 0.5),
        grain=0.010, vig=0.16,
        build_static=back, build_static_front=front, draw_anim=anim,
    )


GROUP_E = [
    shot_22_ivie,
    shot_23_black_vault,
    shot_24_big_foot,
]
