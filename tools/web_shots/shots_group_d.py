"""Group D — web shots 17-21, rebuilt natively.

17 guardian_biggest_frauds  (tilted Guardian SBF headline, two markers)
18 ftx_tweet_card           (Mario Gabriele FTX tweet + FTX card, player bar)
19 nyt_look_crazy_zoom      (NYT SBF profile zoom, "look crazy" marker)
20 indictment_summary       (tilted DOJ indictment page, "Bankman-Fried raised" marker)
21 guardian_seoul_missiles  (Guardian motion card + timeline line + player bar)

Each shot: static plate + animated marker sweep / camera drift + player
chrome where the paused-player reference shows it.
"""

from __future__ import annotations

from PIL import Image, ImageDraw

from web_shot_kit import Canvas, Shot, warp_perspective


def _ease(t: float) -> float:
    return t * t * (3.0 - 2.0 * t)


def _sweep(t: float, t0: float = 0.10, t1: float = 0.55) -> float:
    if t <= t0:
        return 0.0
    if t >= t1:
        return 1.0
    return _ease((t - t0) / (t1 - t0))


# --------------------------------------------------------------------------- #
# 17 — Guardian: "charged in one of 'biggest financial frauds' in US history"
# --------------------------------------------------------------------------- #

def shot_17_guardian_frauds() -> Shot:
    def back(c: Canvas):
        c.rect(0, 0, 1920, 1080, "#EFECE5")
        c.screen_grid(4, 0.035)

    def front(c: Canvas):
        c.text(110, 125, "Sam Bankman-Fried", 30, "sans-bold", "#7A2231")
        c.text(100, 195, "Sam Bankman-Fried charged in one of 'biggest", 78, "serif-bold", "#16161A")
        c.text(100, 325, "financial frauds' in US history", 78, "serif-bold", "#16161A")
        c.text(110, 520, "Indictment brings eight criminal counts against crypto entrepreneur arrested in the",
               34, "sans", "#67645F")
        c.text(110, 572, "Bahamas", 34, "sans", "#67645F")

    def anim(c: Canvas, t: float):
        s = _sweep(t, 0.10, 0.55)
        s2 = _sweep(t, 0.30, 0.75)
        x0 = 100 + c.measure("Sam Bankman-Fried charged in ", 78, "serif-bold")
        w1 = c.measure("one of 'biggest", 78, "serif-bold")
        c.marker(x0 - 6, 212, (w1 + 12) * s, 92, "#E6E32E", 0.95, seed=171)
        w2 = c.measure("financial frauds' in US history", 78, "serif-bold")
        c.marker(94, 342, (w2 + 12) * s2, 92, "#E6E32E", 0.95, seed=172)

    def warp_fn(frame: Image.Image, t: float) -> Image.Image:
        return warp_perspective(
            frame,
            [(0, 0), (1920, 0), (1920, 1080), (0, 1080)],
            [(80, 150), (1845, 90), (1815, 975), (55, 1035)],
            border_value=(239, 236, 229),
        )

    return Shot(
        name="17_guardian_biggest_frauds",
        source="Screenshot 2026-10-26 085706.png",
        seconds=3.0,
        description="Tilted Guardian page: SBF charged in one of 'biggest financial frauds' in US history",
        cam_from=(1.01, 0.5, 0.5), cam_to=(1.05, 0.48, 0.52),
        grain=0.010, vig=0.16,
        build_static=back, build_static_front=front, draw_anim=anim, warp_fn=warp_fn,
    )


# --------------------------------------------------------------------------- #
# 18 — Mario Gabriele FTX tweet with link card
# --------------------------------------------------------------------------- #

def shot_18_ftx_tweet() -> Shot:
    def back(c: Canvas):
        c.rect(0, 0, 1920, 1080, "#E8E7E3")
        c.screen_grid(3, 0.04)
        c.vignette(0.18, 0.72)

    def front(c: Canvas):
        c.text(398, 205, "\u2190", 42, "dejavu", "#1B1B1D")
        c.text(470, 200, "Post", 42, "sans-bold", "#1B1B1D")
        # avatar + identity row
        c.ellipse(372, 268, 96, 96, "#9AA0A6")
        c.ellipse(397, 293, 46, 46, "#7E848A")
        c.text(500, 272, "Mario Gabriele", 36, "sans-bold", "#141416")
        c.ellipse(862, 282, 26, 26, "#E8842A")
        c.ellipse(902, 286, 30, 21, "#C9CCD1")
        c.rect(946, 279, 31, 31, "#1D9BF0", radius=9)
        c.line(953, 295, 962, 303, "#FFFFFF", 3.5)
        c.line(962, 303, 972, 285, "#FFFFFF", 3.5)
        c.text(500, 324, "@mariogabriele", 31, "sans", "#6E7076")
        c.text(1545, 278, "\u2022\u2022\u2022", 34, "dejavu", "#6E7076")
        # tweet body
        c.text(300, 420, "FTX is a wild company.", 37, "sans", "#17171A")
        c.text(348, 505, "\u2022  Worth $18b", 37, "sans", "#17171A")
        c.text(348, 558, "\u2022  Processing billions of dollars a day in trades", 37, "sans", "#17171A")
        c.text(348, 611, "\u2022  Has 6 engineers", 37, "sans", "#17171A")
        c.text(300, 700, "No joke. Crypto's fastest-growing exchange has been powered by a tiny,",
               37, "sans", "#17171A")
        c.text(300, 753, "hard-working team.", 37, "sans", "#17171A")
        # link card (cropped by the frame bottom like the reference)
        c.rect(278, 838, 1372, 360, "#D8D8D4", radius=22)
        c.rect(281, 841, 1366, 354, "#FCFCFB", radius=20)
        # card logos, left column
        c.rect(348, 890, 72, 72, "#2F7BF0", radius=15)
        c.line(384, 905, 384, 947, "#FFFFFF", 6)
        c.line(363, 926, 405, 926, "#FFFFFF", 6)
        c.ellipse(340, 996, 90, 62, "#5B3FD6")
        c.rect(470, 1002, 44, 60, "#D63B2F", radius=7)
        c.ellipse(342, 1082, 108, 62, "#2E8B57")
        c.ellipse(472, 1090, 84, 52, "#E8A02A")
        # FTX wordmark
        c.text(1140, 975, "FTX", 175, "serif-bold", "#17171A", anchor="mm")
        c.text(1140, 1098, "CRYPTO'S SPEEDRUNNER", 33, "sans-semi", "#17171A", anchor="mm", spacing=5.0)

    return Shot(
        name="18_ftx_tweet_card",
        source="Screenshot 2026-10-26 090129.png",
        seconds=3.0,
        description="Mario Gabriele tweet on FTX as a wild company with the FTX link card",
        cam_from=(1.02, 0.5, 0.52), cam_to=(1.06, 0.5, 0.48),
        grain=0.010, vig=0.18,
        build_static=back, build_static_front=front,
    )


# --------------------------------------------------------------------------- #
# 19 — NYT profile zoom: "I think it's important for people to think I look crazy."
# --------------------------------------------------------------------------- #

def shot_19_look_crazy() -> Shot:
    def back(c: Canvas):
        c.rect(0, 0, 1920, 1080, "#E9E7E1")
        c.noise(0.01, seed=1919)
        c.vignette(0.18, 0.72)

    def front(c: Canvas):
        sz = 56
        x = -45
        c.text(x + 25, -8, "$40 billion.", sz, "serif-bold", "#2E2B27")
        c.text(x, 78, "As his business grew, Mr. Bankman-Fried began to establish a public", sz, "serif", "#57544F")
        c.text(x, 154, "profile, tweeting about his favorite video games and going on TV to explain", sz, "serif", "#57544F")
        # link-styled phrase
        lx = x + c.measure("profile, ", sz, "serif")
        c.text(lx, 154, "tweeting about his favorite", sz, "serif", "#7E858C")
        c.rect(lx, 196, c.measure("tweeting about his favorite", sz, "serif"), 3, "#7A8087", 0.85)
        c.text(x, 230, "crypto to the masses. But he refused to comport himself like a typical", sz, "serif", "#57544F")
        c.text(x, 306, "CNBC guest. Before one of his first TV appearances, Andy Croghan, a", sz, "serif", "#57544F")
        c.text(x, 382, "colleague at Alameda and FTX, urged him to clean up his look.", sz, "serif", "#57544F")
        c.text(x, 458, "\u201cI was like, \u2018Sam, you\u2019ve got to cut your hair, dude \u2014 it looks ridiculous,\u2019\u201d",
               sz, "serif", "#57544F")
        c.text(x, 534, "Mr. Croghan said. \u201cAnd he said, \u2018I honestly think it\u2019s negative EV for me to",
               sz, "serif", "#57544F")
        c.text(x, 610, "cut my hair. ", sz, "serif", "#57544F")
        px = x + c.measure("cut my hair. ", sz, "serif")
        c.text(px, 610, "I think it\u2019s important for people to think I look crazy.\u2019\u201d", sz, "serif", "#2E2B27")
        c.text(x, 686, "Mr. Croghan learned to embrace that strategy. Mr. Bankman-Fried often", sz, "serif", "#57544F")
        c.text(x, 762, "takes power naps on his beanbag between meetings. At the FTX office in", sz, "serif", "#57544F")
        c.text(x, 838, "Hong Kong, Mr. Croghan would arrange for high-profile visitors to arrive", sz, "serif", "#57544F")
        c.text(x, 914, "while Mr. Bankman-Fried was still sleeping, ushering them into a", sz, "serif", "#57544F")
        c.text(x, 990, "conference room with a view of the slumbering chief executive. Eventually", sz, "serif", "#57544F")
        c.text(x, 1066, "Bankman-Fried would rouse himself and walk into the meeting,", sz, "serif", "#57544F")
        # show logo, bottom-left
        for i, h in enumerate((38, 52, 42)):
            c.rect(18 + i * 18, 1060 - h, 10, h, "#F2F2F0")

    def anim(c: Canvas, t: float):
        s = _sweep(t, 0.12, 0.58)
        sz = 56
        x = -45
        px = x + c.measure("cut my hair. ", sz, "serif")
        w = c.measure("I think it\u2019s important for people to think I look crazy.\u2019\u201d", sz, "serif")
        c.marker(px - 8, 618, (w + 16) * s, 66, "#E9E600", 0.92, seed=19)

    return Shot(
        name="19_nyt_look_crazy_zoom",
        source="Screenshot 2026-10-26 090410.png",
        seconds=3.0,
        description="NYT SBF profile zoom, marker over 'I think it's important for people to think I look crazy.'",
        cam_from=(1.03, 0.5, 0.5), cam_to=(1.09, 0.47, 0.51),
        grain=0.010, vig=0.16,
        build_static=back, build_static_front=front, draw_anim=anim,
    )


# --------------------------------------------------------------------------- #
# 20 — tilted DOJ indictment page: SUMMARY section
# --------------------------------------------------------------------------- #

def shot_20_indictment() -> Shot:
    def back(c: Canvas):
        c.rect(0, 0, 1920, 1080, "#F3F2EF")

    def front(c: Canvas):
        c.text(760, 35, "SUMMARY", 50, "times-bold", "#232323", spacing=4.0)
        c.rect(755, 97, 302, 3, "#232323")
        c.text(120, 150, "1.", 58, "times", "#232323")
        x = 225
        c.text(x, 140, "From at least May 2019 through November 2022, Bankman-Fried engaged in a", 58, "times", "#232323")
        c.text(x, 258, "scheme to defraud equity investors in FTX Trading Ltd. (\u201cFTX\u201d), the crypto asset trading", 58, "times", "#232323")
        c.text(x, 376, "platform of which he was CEO and co-founder, at the same time that he was also defrauding the", 58, "times", "#232323")
        c.text(x, 494, "platform\u2019s customers. ", 58, "times", "#232323")
        px = x + c.measure("platform\u2019s customers. ", 58, "times")
        c.text(px, 494, "Bankman-Fried raised", 58, "times", "#232323")
        c.text(px + c.measure("Bankman-Fried raised", 58, "times"), 494,
               " more than $1.8 billion from investors, including", 58, "times", "#232323")
        c.text(x, 612, "investors, who bought an equity stake in FTX believing that FTX had appropriate controls", 58, "times", "#232323")
        c.text(x, 730, "and management measures.  Unbeknownst to those investors (and to FTX\u2019s trading", 58, "times", "#232323")
        c.text(x, 848, "customers), Bankman-Fried was orchestrating a massive, years-long fraud, diverting billions of", 58, "times", "#232323")
        c.text(x, 966, "customer funds for his own personal benefit and to help grow", 58, "times", "#232323", alpha=0.55)

    def anim(c: Canvas, t: float):
        s = _sweep(t, 0.10, 0.55)
        x = 225
        px = x + c.measure("platform\u2019s customers. ", 58, "times")
        w = c.measure("Bankman-Fried raised", 58, "times")
        c.marker(px - 6, 502, (w + 12) * s, 64, "#E8C84A", 0.95, seed=20)

    def warp_fn(frame: Image.Image, t: float) -> Image.Image:
        return warp_perspective(
            frame,
            [(0, 0), (1920, 0), (1920, 1080), (0, 1080)],
            [(75, 135), (1860, 70), (1830, 1010), (45, 955)],
            border_value=(243, 242, 239),
        )

    return Shot(
        name="20_indictment_summary",
        source="Screenshot 2026-10-26 090523.png",
        seconds=3.0,
        description="Tilted DOJ indictment SUMMARY section, marker over 'Bankman-Fried raised'",
        cam_from=(1.0, 0.5, 0.5), cam_to=(1.04, 0.52, 0.47),
        grain=0.010, vig=0.18,
        build_static=back, build_static_front=front, draw_anim=anim, warp_fn=warp_fn,
    )


# --------------------------------------------------------------------------- #
# 21 — Guardian motion card: US missiles leaving South Korea
# --------------------------------------------------------------------------- #

def shot_21_seoul_missiles() -> Shot:
    def back(c: Canvas):
        c.rect(0, 0, 1920, 1080, "#202020")
        c.noise(0.02, seed=2121)
        c.vignette(0.30, 0.66)

    def front(c: Canvas):
        c.text(360, 180, "The Guardian", 58, "serif-bold", "#E4572E")
        c.text(355, 262, "Hasty redeployment of US missiles", 76, "arial-bold", "#F4F4F2")
        c.text(355, 372, "from South Korea to Middle East", 76, "arial-bold", "#F4F4F2")
        c.text(355, 482, "leaves Seoul rattled", 76, "arial-bold", "#F4F4F2")
        # timeline connector with rounded corners
        col = "#C9C9C9"
        c.line(89, 1085, 89, 845, col, 4)
        c.line(89, 845, 129, 805, col, 4)
        c.line(129, 805, 707, 805, col, 4)
        c.line(707, 805, 747, 765, col, 4)
        c.line(747, 765, 747, 573, col, 4)
        c.line(747, 573, 787, 533, col, 4)
        c.line(787, 533, 1735, 533, col, 4)
        c.ellipse(1735 - 23, 533 - 23, 46, 46, "#E4572E")
        # monospace caption
        c.text(818, 575, "South Korea's president has sought to reassure", 30, "dejavu", "#8E8E8E", spacing=1.2)
        c.text(818, 614, "the public that the country is able to deter", 30, "dejavu", "#8E8E8E", spacing=1.2)
        c.text(818, 653, "threats from the North.", 30, "dejavu", "#8E8E8E", spacing=1.2)

    def anim(c: Canvas, t: float):
        s = _sweep(t, 0.10, 0.55)
        c.rect(350, 378, 1295 * s, 100, "#E4572E", 0.95)

    return Shot(
        name="21_guardian_seoul_missiles",
        source="Screenshot 2026-10-26 at 11-13-55 America\u2019s deadly miscalculation in Iran - YouTube.png",
        seconds=3.0,
        description="Guardian motion card: US missiles redeployed from South Korea to Middle East, timeline line",
        cam_from=(1.0, 0.5, 0.5), cam_to=(1.04, 0.51, 0.49),
        grain=0.014, vig=0.26,
        build_static=back, build_static_front=front, draw_anim=anim,
    )


GROUP_D = [
    shot_17_guardian_frauds,
    shot_18_ftx_tweet,
    shot_19_look_crazy,
    shot_20_indictment,
    shot_21_seoul_missiles,
]
