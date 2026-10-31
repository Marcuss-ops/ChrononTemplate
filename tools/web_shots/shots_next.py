"""Web shots next — the six reusable recipes, ported from the C++ pack.

These are the Python equivalents of `WebShotsNextPack`:
dual marker cross, glow line pulse, tilt/snap settle, timeline draw, caption
pop card and CRT fringe flash. They use the same 1920x1080 authoring canvas and
the same `Shot` pipeline as the 28 reference rebuilds, so the pod can render
all 34 clips through one code path.
"""

from __future__ import annotations

from PIL import ImageDraw

from web_shot_kit import Canvas, Shot


def _ease(t: float) -> float:
    return max(0.0, min(1.0, t)) ** 2 * (3.0 - 2.0 * max(0.0, min(1.0, t)))


def _sweep(t: float, t0: float = 0.10, t1: float = 0.55) -> float:
    if t <= t0:
        return 0.0
    if t >= t1:
        return 1.0
    return _ease((t - t0) / (t1 - t0))


def _pulse(t: float, cycles: float = 1.4) -> float:
    import math
    return 0.75 + 0.25 * (0.5 + 0.5 * math.sin(2.0 * math.pi * cycles * t))


def shot_next_dual_marker_cross() -> Shot:
    HEAD = "Senate passes the chip export bill"
    HL = "chip export bill"

    def back(c: Canvas):
        c.rect(0, 0, 1920, 1080, "#EDECEA")
        c.noise(0.008, seed=3101)
        c.vignette(0.14, 0.74)

    def front(c: Canvas):
        c.text(200, 400, HEAD, 72, "helv-bold", "#141416")
        c.text(200, 640, "Breaking — 10:42 ET", 30, "sans", "#67645F")
        c.text(200, 700, "Markets rally as export rules take hold.", 30, "sans", "#67645F")

    def anim(c: Canvas, t: float):
        s1 = _sweep(t, 0.10, 0.52)
        s2 = _sweep(t, 0.30, 0.72)
        w = c.measure(HL, 72, "helv-bold")
        c.rect(200, 400, (w + 24) * s1, 92, "#E6E300", 0.92)
        c.rect(200, 520, (w + 24) * s2, 72, "#E4572E", 0.55)

    return Shot(
        name="next_dual_marker_cross",
        source="native recipe (WebShotsNextPack::DualMarkerCross)",
        seconds=3.0,
        description="Two crossed highlighter sweeps behind one editorial headline",
        cam_from=(1.0, 0.5, 0.5), cam_to=(1.02, 0.5, 0.5),
        grain=0.010, vig=0.16,
        build_static=back, build_static_front=front, draw_anim=anim,
    )


def shot_next_glow_line_pulse() -> Shot:
    HEAD = "Simple Sabotage Field Manual revealed"
    HL = "Sabotage Field Manual"

    def back(c: Canvas):
        c.rect(0, 0, 1920, 1080, "#0A0A0A")
        c.noise(0.012, seed=3102)
        c.vignette(0.30, 0.62)

    def front(c: Canvas):
        c.text(200, 430, HEAD, 78, "serif-it", "#F5D24A")
        c.text(200, 680, "Archive — declassified", 30, "sans", "#8A8578")

    def anim(c: Canvas, t: float):
        s = _sweep(t, 0.12, 0.58)
        a = _pulse(t, 1.2)
        w = c.measure(HL, 78, "serif-it")
        c.rect(200, 430, (w + 40) * s, 120, "#F5D24A", 0.32 * a)
        c.rect(200, 452, (w + 16) * s, 76, "#F5D24A", 0.88 * a)
        c.rect(200, 600, 900 * _sweep(t, 0.30, 0.78), 6, "#F5D24A", 0.9)

    return Shot(
        name="next_glow_line_pulse",
        source="native recipe (WebShotsNextPack::GlowLinePulse)",
        seconds=3.0,
        description="Pulsing glow band and drawn underline on a dark plate",
        cam_from=(1.0, 0.5, 0.5), cam_to=(1.015, 0.5, 0.5),
        grain=0.014, vig=0.30,
        build_static=back, build_static_front=front, draw_anim=anim,
    )


def shot_next_tilt_snap_reveal() -> Shot:
    HEAD = "Why this 30-year-old founder gave it away"
    HL = "gave it away"

    def back(c: Canvas):
        c.rect(0, 0, 1920, 1080, "#F4F3F0")
        c.noise(0.008, seed=3103)
        c.rect(0, 984, 1920, 96, "#080809")
        c.text(760, 1010, "PROFILE — TILT TO FLAT", 34, "oswald-bold", "#E8871E")

    def front(c: Canvas):
        c.text(140, 330, HEAD, 72, "helv-bold", "#0E0E10")
        c.text(140, 480, "The page snaps flat as the marker lands.", 34, "sans", "#4A4844")

    def anim(c: Canvas, t: float):
        s = _sweep(t, 0.10, 0.55)
        w = c.measure(HL, 72, "helv-bold")
        c.rect(140, 330, (w + 16) * s, 92, "#E6E300", 0.92)
        # the settle: a thin rule drops into place once the sweep lands
        c.rect(140, 600, 520 * _ease(min(1.0, max(0.0, (t - 0.25) / 0.45))), 4, "#0E0E10", 0.75)

    return Shot(
        name="next_tilt_snap_reveal",
        source="native recipe (WebShotsNextPack::TiltSnapReveal)",
        seconds=3.0,
        description="Editorial page settles flat while the final phrase is marked",
        cam_from=(1.0, 0.5, 0.5), cam_to=(1.02, 0.5, 0.5),
        grain=0.008, vig=0.14,
        build_static=back, build_static_front=front, draw_anim=anim,
    )


def shot_next_timeline_dash() -> Shot:
    HEAD = "Missiles leave Seoul as region rattles"
    HL = "leave Seoul"

    def back(c: Canvas):
        c.rect(0, 0, 1920, 1080, "#202020")
        c.noise(0.010, seed=3104)
        c.rect(355, 480, 1200, 4, "#8A8A8A", 0.6)

    def front(c: Canvas):
        c.text(355, 262, HEAD, 64, "arial-bold", "#F4F4F2")
        c.text(355, 540, "The rail draws left to right, then the dot pings.", 30, "dejavu", "#8E8E8E")

    def anim(c: Canvas, t: float):
        s = _sweep(t, 0.10, 0.56)
        c.rect(355, 477, 1200 * s, 10, "#E4572E", 0.95)
        if s > 0.86:
            r = 46 * min(1.0, (s - 0.86) / 0.14)
            c.ellipse(355 + 1200 * s - r / 2, 480 - r / 2, r, r, "#E4572E", 1.0)

    return Shot(
        name="next_timeline_dash",
        source="native recipe (WebShotsNextPack::TimelineDash)",
        seconds=3.0,
        description="Timeline rail draws across the frame and the end dot pings",
        cam_from=(1.0, 0.5, 0.5), cam_to=(1.015, 0.5, 0.5),
        grain=0.012, vig=0.26,
        build_static=back, build_static_front=front, draw_anim=anim,
    )


def shot_next_caption_pop_card() -> Shot:
    HEAD = "When the sauce changed, it went downhill"

    def draw_full(c: Canvas, t: float):
        c.rect(0, 0, 1920, 1080, "#131110")
        c.ellipse(240, -180, 1520, 1240, "#2B241E")
        c.ellipse(360, -60, 1290, 1010, "#221C17")
        for i in range(5):
            c.ellipse(400 + 229 * i % 1050, 20 + 317 * i % 760, 130, 100, "#3B322A", 0.8)
        # pop: 0.90 -> 1.00 over the first 22 frames, then hold
        p = min(1.0, t / 0.24)
        s = 0.90 + 0.10 * _ease(p)
        w = c.measure(HEAD, 52, "sans") + 120
        h = 148
        x, y = 960 - w * s / 2, 566 - h * s / 2
        c.rect(x, y, w * s, h * s, "#F7F7F5", 1.0, radius=6)
        c.text(960, 566, HEAD, 52 * s, "sans", "#101010", anchor="mm")

    return Shot(
        name="next_caption_pop_card",
        source="native recipe (WebShotsNextPack::CaptionPopCard)",
        seconds=3.0,
        description="White caption card pops over the dark blurred pizza plate",
        cam_from=(1.0, 0.5, 0.5), cam_to=(1.02, 0.5, 0.5),
        grain=0.014, vig=0.30,
        draw_full=draw_full,
    )


def shot_next_crt_fringe_flash() -> Shot:
    HEAD = "GOVERNMENT TO DOUBLE CONTENT"
    HL = "DOUBLE"

    def draw_full(c: Canvas, t: float):
        c.rect(0, 0, 1920, 1080, "#080A0C")
        c.noise(0.014, seed=3106)
        c.vignette(0.28, 0.64)
        x, y = 105, 205
        size = 96
        # chroma fringe: yellow and cyan copies under the white headline
        c.text(x - 10, y - 10, HEAD, size, "serif-bold", "#D5D000", alpha=0.58)
        c.text(x + 10, y + 10, HEAD, size, "serif-bold", "#67B9D4", alpha=0.44)
        c.text(x, y, HEAD, size, "serif-bold", "#DDE4E8")
        s = _sweep(t, 0.12, 0.55)
        hx = x + c.measure(HEAD[:HEAD.index(HL)], size, "serif-bold")
        hw = c.measure(HL, size, "serif-bold")
        c.rect(hx - 4, y + 12, (hw + 8) * s, 116, "#C9DC28", 0.85 * s)
        c.text(x, 560, "CRT — fringe flash", 34, "oswald", "#DDE4E8")

    return Shot(
        name="next_crt_fringe_flash",
        source="native recipe (WebShotsNextPack::CrtFringeFlash)",
        seconds=3.0,
        description="Serif CRT headline with RGB fringe and a flash marker reveal",
        cam_from=(1.0, 0.5, 0.5), cam_to=(1.02, 0.5, 0.5),
        grain=0.016, vig=0.28,
        draw_full=draw_full,
    )


NEXT_GROUP = [
    shot_next_dual_marker_cross,
    shot_next_glow_line_pulse,
    shot_next_tilt_snap_reveal,
    shot_next_timeline_dash,
    shot_next_caption_pop_card,
    shot_next_crt_fringe_flash,
]


def all_next_shots() -> list[Shot]:
    return [factory() for factory in NEXT_GROUP]
