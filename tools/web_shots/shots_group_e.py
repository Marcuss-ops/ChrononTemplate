"""Group E — the 2026-10-27/28 web screenshots, rebuilt natively.

22 ivie_facebook          (mothers' groups Facebook post excerpt, yellow marker)
23 black_vault_foia       (Black Vault / Greenewald FOIA excerpt, two markers)
24 big_foot_pizza         (Pizza Hut 'The Big Foot' promo excerpt, olive markers)
25 pizza_sauce_caption    (blurred dark pizza + white rough-edged caption card)
26 pizza_hut_perception   (Pizza Hut perception article, yellow markers)
27 times_of_india_coxon   (TOI Jacob Coxon headline, white boxed highlights)
28 amodei_pace_frontier   (Dario Amodei dark-mode post, white selection boxes)

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


# --------------------------------------------------------------------------- #
# 25 — blurred dark pizza + white rough caption card
# --------------------------------------------------------------------------- #

def shot_25_pizza_sauce() -> Shot:
    def back(c: Canvas):
        c.rect(0, 0, 1920, 1080, "#131110")
        # huge dark pizza disc, heavily blurred
        c.ellipse(240, -180, 1520, 1240, "#2B241E")
        c.ellipse(360, -60, 1290, 1010, "#221C17")
        c.ellipse(240, -180, 1520, 1240, "#342B23", 0.6)
        for i in range(14):
            x = 400 + (i * 229) % 1050
            y = 20 + (i * 317) % 760
            c.ellipse(x, y, 130, 100, "#3B322A", 0.8)
        _blur(c, 26)
        c.vignette(0.62, 0.52)

    def anim(c: Canvas, t: float):
        s = _sweep(t, 0.12, 0.60)
        c.marker(80, 492, 1760 * s, 148, "#F7F7F5", 1.0, seed=25, rough=True)

    def front(c: Canvas):
        c.text(960, 566, "When they started changing the sauce, it went downhill.",
               52, "sans", "#101010", anchor="mm")

    return Shot(
        name="25_pizza_sauce_caption",
        source="Screenshot 2026-10-27 171918.png",
        seconds=3.0,
        description="Dark blurred pizza close-up with white rough caption card",
        cam_from=(1.0, 0.5, 0.5), cam_to=(1.05, 0.5, 0.5),
        grain=0.016, vig=0.34,
        build_static=back, draw_anim=anim, build_static_front=front,
    )


# --------------------------------------------------------------------------- #
# 26 — Pizza Hut perception article
# --------------------------------------------------------------------------- #

def shot_26_pizza_hut() -> Shot:
    sz = 48
    x = 150

    def back(c: Canvas):
        c.rect(0, 0, 1920, 1080, "#FDFCFA")
        c.noise(0.008, seed=2626)
        c.vignette(0.12, 0.75)

    def front(c: Canvas):
        col = "#1A1A1A"
        c.text(x, 15, ") of Pizza Hut's U.S., speaking at Yum's investor day", sz, "times", col)
        c.text(x, 87, "Wednesday, said he is \u201cdissatisfied\u201d with Pizza Hut's growth, telling investors", sz, "times", col)
        c.text(x, 158, "that the brand has \u201ca lot of work to do.\u201d", sz, "times", col)
        c.text(x, 345, "The biggest problem that Pizza Hut is facing is perception, Starrs said,", sz, "times", col)
        c.text(x, 425, "explaining that many of its customers don't associate Pizza Hut with delivery.", sz, "times", col)
        c.text(x, 504, "Most people think about ordering a pizza and carrying it out, or sitting down a", sz, "times", col)
        c.text(x, 584, "table and having a server bring a meal. Starrs said the facade of its locations", sz, "times", col)
        c.text(x, 663, "reinforces this idea and isn't helping to lure in diners.", sz, "times", col)
        c.text(x, 792, "\u201cWhen you drive by the location, it doesn't scream \u2018we deliver.\u2019\u201d Starrs said.", sz, "times", col)
        c.text(x, 915, "Pizza Hut has only recently getting into the delivery game. Today, 55 percent", sz, "times", col)
        c.text(x, 995, "of Pizza Hut's sales in the U.S. come from digital orders and only 10 percent of", sz, "times", col)
        c.text(x, 1073, "sales stem from diners coming into the chain and dining in. Going forward", sz, "times", col)

    def anim(c: Canvas, t: float):
        s1 = _sweep(t, 0.08, 0.45)
        s2 = _sweep(t, 0.28, 0.65)
        s3 = _sweep(t, 0.48, 0.85)
        y = "#F2C500"
        w = c.measure("The biggest problem that Pizza Hut is facing is perception,", sz, "times")
        c.marker(x - 6, 352, (w + 12) * s1, 62, y, 0.95, seed=261)
        w = c.measure("explaining that many of its customers don't associate Pizza Hut with delivery.", sz, "times")
        c.marker(x - 6, 432, (w + 12) * s1, 62, y, 0.95, seed=262)
        x7 = x + c.measure("table and having a server bring a meal. ", sz, "times")
        w = c.measure("Starrs said the facade of its locations", sz, "times")
        c.marker(x7 - 6, 591, (w + 12) * s2, 62, y, 0.95, seed=263)
        w = c.measure("reinforces this idea and isn't helping to lure in diners.", sz, "times")
        c.marker(x - 6, 670, (w + 12) * s2, 62, y, 0.95, seed=264)
        w = c.measure("\u201cWhen you drive by the location, it doesn't scream \u2018we deliver.\u2019\u201d", sz, "times")
        c.marker(x - 6, 799, (w + 12) * s3, 62, y, 0.95, seed=265)

    return Shot(
        name="26_pizza_hut_perception",
        source="Screenshot 2026-10-27 172102.png",
        seconds=3.0,
        description="Serif article: Pizza Hut's perception problem per CEO Kirk Starrs, yellow markers",
        cam_from=(1.02, 0.5, 0.5), cam_to=(1.07, 0.48, 0.52),
        grain=0.008, vig=0.12,
        build_static=back, build_static_front=front, draw_anim=anim,
    )


# --------------------------------------------------------------------------- #
# 27 — Times of India: Jacob Coxon headline
# --------------------------------------------------------------------------- #

def shot_27_times_of_india() -> Shot:
    HEAD1 = "Jacob Coxon, the ex-Anthropic researcher warning"
    HEAD2 = "AI could kill us all?"

    def back(c: Canvas):
        c.rect(0, 0, 1920, 1080, "#0D0D0C")
        # faint horizontal screen banding
        for y in range(0, 1080, 7):
            c.rect(0, y, 1920, 3, "#171716", 0.5)
        c.noise(0.012, seed=2727)
        c.vignette(0.34, 0.62)

    def front(c: Canvas):
        # masthead with soft pink glow
        for dx, dy, col, a in ((-4, -2, "#C0708A", 0.55), (4, 2, "#C0708A", 0.55),
                               (0, 0, "#C0708A", 0.35)):
            c.text(960 + dx, 142 + dy, "THE TIMES OF INDIA", 88, "serif-bold", col, anchor="ma", alpha=a)
        c.text(960, 142, "THE TIMES OF INDIA", 88, "serif-bold", "#F2E8EA", anchor="ma")
        c.text(960, 330, "News  \u00b7  Education News  \u00b7  News", 28, "sans-med", "#2E8B8B", anchor="ma", spacing=1.0)
        c.text(48, 415, "Who is", 62, "serif-bold", "#7A7A7A")
        c.text(307, 415, HEAD1, 62, "serif-bold", "#5B1E2B")
        c.text(690, 512, HEAD2, 62, "serif-bold", "#5B1E2B")
        para = [
            "A young researcher named Jacob Coxon resigned from Anthropic after working at OpenAI. He warned that artificial",
            "intelligence could end humanity by the decade's end. Coxon's concerns emerged after AI models demonstrated concerning",
            "capabilities and escaped testing environments. His public declaration amplified private debates within leading AI",
        ]
        y = 645
        for ln in para:
            c.text(960, y, ln, 27, "sans", "#6E6E6E", anchor="ma")
            y += 50
        c.text(30, 795, "TOI Education", 26, "sans", "#6E6E6E")
        c.text(1890, 795, "Sep 19, 2026, 15:11 IST", 26, "sans", "#6E6E6E", anchor="ra")
        # blurred landscape photo strip at the bottom
        c.rect(202, 937, 1515, 143, "#7C8794")
        c.ellipse(260, 900, 500, 260, "#4E6B3A", 0.9)
        c.ellipse(900, 890, 620, 280, "#587742", 0.9)
        c.ellipse(1380, 910, 420, 240, "#3F5C30", 0.9)
        c.ellipse(760, 950, 240, 190, "#8A93A0", 0.9)
        c.ellipse(1200, 985, 300, 120, "#A8B2BE", 0.7)
        # caption box
        c.rect(720, 982, 480, 60, "#141414", 0.92)
        c.text(960, 998, "alarm bells across the country.", 26, "sans", "#F2F2F2", anchor="ma")

    def anim(c: Canvas, t: float):
        s1 = _sweep(t, 0.12, 0.55)
        s2 = _sweep(t, 0.35, 0.78)
        c.rect(265, 398, 1610 * s1, 96, "#F5F0EE", 0.96)
        c.rect(650, 492, 635 * s2, 96, "#F5F0EE", 0.96)

    return Shot(
        name="27_times_of_india_coxon",
        source="Screenshot 2026-10-28 at 08-42-33 Elon Musk & Dario\u2019s Final Warning Why the AI Race Is Getting Dangerously Out of Control - YouTube.png",
        seconds=3.0,
        description="Times of India page on dark screen: Jacob Coxon AI warning headline in white boxes",
        cam_from=(1.0, 0.5, 0.5), cam_to=(1.045, 0.5, 0.48),
        grain=0.012, vig=0.30,
        build_static=back, build_static_front=front, draw_anim=anim,
    )


# --------------------------------------------------------------------------- #
# 28 — Dario Amodei dark-mode post
# --------------------------------------------------------------------------- #

def shot_28_amodei() -> Shot:
    H1 = "We Must Pace the Frontier: I\u2019ve written a new essay on why the AI"
    H2 = "industry should slow down, with a three-part plan for doing so."

    def back(c: Canvas):
        c.rect(0, 0, 1920, 1080, "#0A0A09")
        for y in range(0, 1080, 6):
            c.rect(0, y, 1920, 2, "#131312", 0.55)
        c.noise(0.010, seed=2828)
        c.vignette(0.30, 0.64)

    def front(c: Canvas):
        white = "#E7E9EA"
        grey = "#71767B"
        c.text(142, 55, "\u2190", 40, "dejavu", white)
        c.text(225, 52, "Post", 44, "sans-bold", white)
        # avatar: stylised head-and-shoulders on a photo-like grey disc
        c.ellipse(127, 187, 115, 115, "#8B8F94")
        c.ellipse(157, 205, 55, 62, "#3A3D41")
        c.ellipse(132, 262, 105, 72, "#2E3236")
        c.text(270, 192, "Dario Amodei", 40, "sans-bold", white)
        c.ellipse(575, 202, 40, 40, "#1D9BF0")
        c.line(585, 222, 594, 232, "#FFFFFF", 4)
        c.line(594, 232, 606, 211, "#FFFFFF", 4)
        c.rect(638, 200, 46, 42, "#E7E9EA", radius=7)
        c.text(661, 210, "AI", 22, "sans-bold", "#0A0A09", anchor="ma")
        c.text(270, 252, "@DarioAmodei", 34, "sans", grey)
        # hide + overflow icons
        c.ellipse(1680, 202, 42, 28, "#71767B", 0.0)
        c.line(1672, 226, 1722, 198, white, 4)
        c.ellipse(1682, 204, 38, 26, white, 0.9)
        c.ellipse(1692, 208, 18, 18, "#0A0A09")
        c.text(1770, 200, "\u2022\u2022\u2022", 34, "dejavu", white)
        # highlighted opening (white selection boxes, dark glyphs)
        c.text(125, 360, H1, 44, "sans", "#0E0F10")
        c.text(125, 425, H2, 44, "sans", "#0E0F10")
        # body
        body = [
            "Anthropic is unilaterally committing to the first of these steps. We\u2019ll",
            "provide third-party evaluators with permanent, employee-level access",
            "to our systems, so that they can verify adherence to our safety",
            "measures, report on incidents, and assess models\u2019 alignment during",
            "training.",
        ]
        y = 570
        for ln in body:
            c.text(125, y, ln, 44, "sans", white)
            y += 75
        c.text(125, 1005, "You can read the full post here:", 52, "sans", white)

    def anim(c: Canvas, t: float):
        s = _sweep(t, 0.12, 0.58)
        w1 = c.measure(H1, 44, "sans")
        w2 = c.measure(H2, 44, "sans")
        c.rect(118, 352, (w1 + 16) * s, 62, "#F2F2F0", 0.96)
        if s > 0.55:
            c.rect(118, 417, (w2 + 16) * min(1.0, (s - 0.55) / 0.45), 62, "#F2F2F0", 0.96)

    return Shot(
        name="28_amodei_pace_frontier",
        source="Screenshot 2026-10-28 at 08-42-54 Elon Musk & Dario\u2019s Final Warning Why the AI Race Is Getting Dangerously Out of Control - YouTube.png",
        seconds=3.0,
        description="Dark-mode Dario Amodei post: 'We Must Pace the Frontier' with white selection boxes",
        cam_from=(1.0, 0.5, 0.5), cam_to=(1.04, 0.51, 0.49),
        grain=0.010, vig=0.26,
        build_static=back, build_static_front=front, draw_anim=anim,
    )


GROUP_E = [
    shot_22_ivie,
    shot_23_black_vault,
    shot_24_big_foot,
    shot_25_pizza_sauce,
    shot_26_pizza_hut,
    shot_27_times_of_india,
    shot_28_amodei,
]
