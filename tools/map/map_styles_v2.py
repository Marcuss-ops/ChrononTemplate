#!/usr/bin/env python3
"""Six modern editorial map styles, same engine as the world scenes.

Styles (one showcase scene each):
- dark:      night-mode plate, white label box, Francia/Paris.
- route:     animated A->B route, Cartagena -> Madrid.
- bubbles:   seizure bubbles over Italian ports.
- flyin:     exponential world -> city zoom, Tokyo.
- timeline:  year-by-year pins over Italy, 2021-2025.
- split:     side-by-side Napoli vs Milano price panels.

Plates are Web Mercator (same math as editorial_world_map, hence
RenderingGen-compatible); frames are piped to ffmpeg. Pure PIL + stdlib.

Usage:
    python3 map_styles_v2.py --list
    python3 map_styles_v2.py --style dark --out dark.mp4
    python3 map_styles_v2.py --style dark --still 140 --out frame.png
    python3 map_styles_v2.py --all --out-dir ../../out/map_styles_v2
"""
from __future__ import annotations

import argparse
import math
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageDraw

import editorial_world_map as wm
import reference_map_italy as rm

HERE = Path(__file__).resolve().parent
W, H, FPS, FRAMES = wm.W, wm.H, wm.FPS, wm.FRAMES

LIGHT = {"SEA": rm.SEA, "LAND": rm.LAND, "BORDER": rm.BORDER,
         "GRID": rm.GRID, "PROV": rm.PROVINCE_LINE}
DARK = {"SEA": (13, 17, 26), "LAND": (30, 38, 52), "BORDER": (64, 78, 100),
        "GRID": (22, 28, 40), "PROV": (45, 55, 75)}


# ---------------------------------------------------------------------------
# generic plate renderer (size-aware, palette-aware)
# ---------------------------------------------------------------------------

def _draw_ring(draw, win, ring, fill, ss, width, w, h) -> None:
    pts = []
    for lon, lat in ring:
        x, y = win.to_raster(lat, lon)
        pts.append((x * ss, y * ss))
    if len(pts) > 1:
        draw.line(pts + [pts[0]], fill=fill, width=max(1, int(width * ss)), joint="curve")


def render_plate(win, w, h, highlight=None, pal=None, ss: int = 2):
    """Render (base, fill_mask, line_mask) at w x h for a Web Mercator window."""
    pal = pal or LIGHT
    big = (w * ss, h * ss)
    base = Image.new("RGB", big, pal["SEA"])
    draw = ImageDraw.Draw(base)
    step = 160 * ss
    for x in range(0, big[0], step):
        draw.line([(x, 0), (x, big[1])], fill=pal["GRID"], width=ss)
    for y in range(0, big[1], step):
        draw.line([(0, y), (big[0], y)], fill=pal["GRID"], width=ss)
    for feature in wm._countries(str(wm.COUNTRIES)):
        for polygon in wm._polygons(feature.get("geometry") or {}):
            outer = [win.to_raster(lat, lon) for lon, lat in polygon[0]]
            if max(x for x, _ in outer) < -w or min(x for x, _ in outer) > 2 * w:
                continue
            draw.polygon([(x * ss, y * ss) for x, y in outer], fill=pal["LAND"])
    for feature in wm._countries(str(wm.COUNTRIES)):
        for polygon in wm._polygons(feature.get("geometry") or {}):
            for ring in polygon:
                _draw_ring(draw, win, ring, pal["BORDER"], ss, 2, w, h)
    fill = Image.new("L", big, 0)
    line = Image.new("L", big, 0)
    if highlight:
        fill_draw = ImageDraw.Draw(fill)
        line_draw = ImageDraw.Draw(line)
        for feature in highlight:
            for polygon in wm._polygons(feature.get("geometry") or {}):
                outer_ss = [(x * ss, y * ss) for x, y in
                            (win.to_raster(lat, lon) for lon, lat in polygon[0])]
                fill_draw.polygon(outer_ss, fill=255)
                for ring in polygon:
                    pts_ss = [(x * ss, y * ss) for x, y in
                              (win.to_raster(lat, lon) for lon, lat in ring)]
                    line_draw.line(pts_ss + [pts_ss[0]], fill=255,
                                   width=2 * ss, joint="curve")
    down = (w, h)
    return (base.resize(down, Image.LANCZOS),
            fill.resize(down, Image.LANCZOS),
            line.resize(down, Image.LANCZOS))


def _ffmpeg(out: Path):
    cmd = ["ffmpeg", "-v", "error", "-y",
           "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS),
           "-i", "-",
           "-c:v", "libx264", "-preset", "medium", "-crf", "18",
           "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(out)]
    return subprocess.Popen(cmd, stdin=subprocess.PIPE)


def _write_mp4(out: Path, frames) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    proc = _ffmpeg(out)
    assert proc.stdin is not None
    try:
        for img in frames:
            proc.stdin.write(img.tobytes())
    finally:
        proc.stdin.close()
    if proc.wait() != 0:
        raise SystemExit(proc.returncode)
    print(f"wrote {out}")


def _label_box(draw_img, text, cx, cy, font, box_fill, text_fill):
    tw = font.getlength(text)
    pad, bh = 26, 60
    right = min(max(cx, 20 + tw + 2 * pad), W - 20)
    left = right - (tw + 2 * pad)
    top = cy - bh / 2
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    d.rectangle((left, top, right, top + bh), fill=box_fill)
    d.text((left + 26, cy + 12), text, font=font, fill=text_fill, anchor="ls")
    return layer, (left, top, right, top + bh)


# ---------------------------------------------------------------------------
# 1. dark
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class DarkCtx:
    base: Image.Image
    fill: Image.Image
    line: Image.Image
    marker: tuple[float, float]


def dark_prepare():
    scene = {"slug": "x", "kind": "country", "iso3": "FRA"}
    features, _ = wm.highlight_features(scene)
    win = wm.fit_window(*wm.main_territory_bounds(features))
    base, fill, line = render_plate(win, W, H, features, pal=DARK)
    lon, lat = wm.city_point("Paris", "FR")
    return DarkCtx(base, fill, line, win.to_raster(lat, lon))


def dark_frame(ctx: DarkCtx, f: int) -> Image.Image:
    img = Image.blend(Image.new("RGB", (W, H), DARK["SEA"]), ctx.base,
                      rm._ramp(f, 0, 20))
    area_a = rm._ramp(f, 30, 50)
    if area_a > 0:
        img.paste(rm.YELLOW, (0, 0), ctx.fill.point(lambda v: int(v * area_a)))
        img.paste((30, 24, 8), (0, 0), ctx.line.point(lambda v: int(v * area_a)))
    img = img.convert("RGBA")
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    mx, my = ctx.marker
    dot_r = 7.0 * rm._ramp(f, 55, 65)
    if dot_r > 0.5:
        l = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        ImageDraw.Draw(l).ellipse((mx - dot_r, my - dot_r, mx + dot_r, my + dot_r),
                                  fill=(255, 255, 255, 255))
        ov = Image.alpha_composite(ov, l)
    if rm._ramp(f, 70, 84) > 0:
        box, _ = _label_box(None, "rete", mx + rm.BOX_DX, my + rm.BOX_DY,
                            rm._font("Inter-SemiBold.ttf", 34),
                            (245, 245, 245, 255), (15, 15, 15, 255))
        ov = Image.alpha_composite(ov, box)
        ov = Image.alpha_composite(
            ov, rm._text_layer("Francia · Paris", rm._font("Inter-Regular.ttf", 30),
                               (190, 190, 190), (rm.FIG_X, rm.FIG_Y - 110),
                               alpha=rm._ramp(f, 80, 92)))
    if rm._ramp(f, 100, 126) > 0:
        ff = rm.ImageFont.truetype(str(rm.FONT_DIR / "BodoniModa-Italic.ttf"), 96)
        fig = "2 milioni"
        w = ff.getlength(fig)
        ov = Image.alpha_composite(
            ov, rm._text_layer(fig, ff, (235, 70, 90), (rm.FIG_X, rm.FIG_Y),
                               clip_x=rm.FIG_X + w * rm._ramp(f, 100, 126)))
        ov = Image.alpha_composite(
            ov, rm._text_layer("in contanti", rm._font("Inter-Regular.ttf", 40),
                               (175, 175, 175), (rm.FIG_X + w + 14, rm.FIG_Y),
                               alpha=rm._ramp(f, 122, 142)))
    return Image.alpha_composite(img, ov).convert("RGB")


# ---------------------------------------------------------------------------
# 2. route Cartagena -> Madrid
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class RouteCtx:
    base: Image.Image
    win: object
    a: tuple[float, float]  # raster endpoints
    b: tuple[float, float]
    ctrl: tuple[float, float]


def route_prepare():
    alon, alat = wm.city_point("Cartagena", "CO")
    blon, blat = wm.city_point("Madrid", "ES")
    win = wm.fit_window(min(alon, blon) - 8, max(alon, blon) + 8,
                        min(alat, blat) - 6, max(alat, blat) + 6)
    base, _, _ = render_plate(win, W, H)
    a = win.to_raster(alat, alon)
    b = win.to_raster(blat, blon)
    mx, my = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2
    lift = math.dist(a, b) * 0.22
    return RouteCtx(base, win, a, b, (mx, my - lift))


def _bezier(ctx: RouteCtx, t: float):
    u = 1 - t
    return (u * u * ctx.a[0] + 2 * u * t * ctx.ctrl[0] + t * t * ctx.b[0],
            u * u * ctx.a[1] + 2 * u * t * ctx.ctrl[1] + t * t * ctx.b[1])


def route_frame(ctx: RouteCtx, f: int) -> Image.Image:
    img = Image.blend(Image.new("RGB", (W, H), rm.SEA), ctx.base, rm._ramp(f, 0, 20))
    img = img.convert("RGBA")
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    t = rm._ramp(f, 35, 115)
    if t > 0:
        n = max(2, int(60 * t))
        pts = [_bezier(ctx, i / (n - 1)) for i in range(n)]
        l = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        ImageDraw.Draw(l).line(pts, fill=(214, 40, 57, 255), width=5, joint="curve")
        ov = Image.alpha_composite(ov, l)
        hx, hy = pts[-1]
        l2 = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        ImageDraw.Draw(l2).ellipse((hx - 9, hy - 9, hx + 9, hy + 9),
                                   fill=(214, 40, 57, 255),
                                   outline=(255, 255, 255, 255), width=3)
        ov = Image.alpha_composite(ov, l2)
    for (pt, name, fam) in ((ctx.a, "Cartagena", 20), (ctx.b, "Madrid", 100)):
        if rm._ramp(f, fam, fam + 10) > 0:
            l = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            ImageDraw.Draw(l).ellipse((pt[0] - 7, pt[1] - 7, pt[0] + 7, pt[1] + 7),
                                      fill=rm.INK + (255,))
            ov = Image.alpha_composite(ov, l)
            box, _ = _label_box(None, name, pt[0] - 40, pt[1] - 80,
                                rm._font("Inter-SemiBold.ttf", 30),
                                rm.INK + (255,), (255, 255, 255, 255))
            ov = Image.alpha_composite(ov, box)
    if rm._ramp(f, 105, 125) > 0:
        ff = rm.ImageFont.truetype(str(rm.FONT_DIR / "BodoniModa-Italic.ttf"), 96)
        fig = "rotta atlantica"
        w = ff.getlength(fig)
        ov = Image.alpha_composite(
            ov, rm._text_layer(fig, ff, rm.RED, (rm.FIG_X, rm.FIG_Y),
                               clip_x=rm.FIG_X + w * rm._ramp(f, 105, 130)))
    return Image.alpha_composite(img, ov).convert("RGB")


# ---------------------------------------------------------------------------
# 3. bubbles: seizures by port
# ---------------------------------------------------------------------------

PORTS = [  # (city, kg seized, editorial 2025)
    ("Napoli", 1200), ("Gioia Tauro", 900), ("Genova", 600),
    ("Catania", 350), ("Livorno", 280),
]


@dataclass(frozen=True)
class BubblesCtx:
    base: Image.Image
    pins: tuple  # (x, y, radius, label, value, t0)


def bubbles_prepare():
    features = wm.country_features("ITA")
    win = wm.fit_window(*wm.main_territory_bounds(features))
    base, _, _ = render_plate(win, W, H, features)
    pins = []
    for i, (city, kg) in enumerate(PORTS):
        lon, lat = wm.city_point(city, "IT")
        x, y = win.to_raster(lat, lon)
        pins.append((x, y, 9 + 1.05 * math.sqrt(kg), city, kg, 20 + i * 14))
    return BubblesCtx(base, tuple(pins))


def bubbles_frame(ctx: BubblesCtx, f: int) -> Image.Image:
    img = Image.blend(Image.new("RGB", (W, H), rm.SEA), ctx.base, rm._ramp(f, 0, 20))
    img = img.convert("RGBA")
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    font = rm._font("Inter-SemiBold.ttf", 28)
    for x, y, r, label, kg, t0 in ctx.pins:
        a = rm._ramp(f, t0, t0 + 12)
        if a <= 0:
            continue
        rr = r * (0.6 + 0.4 * a)
        l = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(l)
        d.ellipse((x - rr, y - rr, x + rr, y + rr),
                  fill=(214, 40, 57, int(140 * a)),
                  outline=(120, 20, 30, int(255 * a)), width=3)
        d.text((x + rr + 8, y - 14), f"{label} {kg} kg", font=font,
               fill=rm.INK + (int(255 * a),))
        ov = Image.alpha_composite(ov, l)
    if rm._ramp(f, 100, 120) > 0:
        ff = rm.ImageFont.truetype(str(rm.FONT_DIR / "BodoniModa-Italic.ttf"), 96)
        fig = "3,3 tonnellate"
        w = ff.getlength(fig)
        ov = Image.alpha_composite(
            ov, rm._text_layer(fig, ff, rm.RED, (rm.FIG_X, rm.FIG_Y),
                               clip_x=rm.FIG_X + w * rm._ramp(f, 100, 126)))
        ov = Image.alpha_composite(
            ov, rm._text_layer("sequestrate nei porti", rm._font("Inter-Regular.ttf", 40),
                               rm.GREY_TEXT, (rm.FIG_X, rm.FIG_Y + 105),
                               alpha=rm._ramp(f, 122, 142)))
    return Image.alpha_composite(img, ov).convert("RGB")


# ---------------------------------------------------------------------------
# 4. fly-in: world -> Tokyo
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class FlyCtx:
    world: Image.Image
    city: Image.Image
    city_xy: tuple[float, float]  # Tokyo raster pos in the world plate
    z0: int
    z1: int


def fly_prepare():
    lon, lat = wm.city_point("Tokyo", "JP")
    z0 = 2
    w0 = wm.Window.centered_on(lat, lon, z0, W, H)
    world, _, _ = render_plate(w0, W, H, None, ss=1)
    features = wm.country_features("JPN")
    z1 = wm.fit_window(*wm.main_territory_bounds(features)).zoom
    w1 = wm.Window.centered_on(lat, lon, z1, W, H)
    base, fill, line = render_plate(w1, W, H, features)
    city = base.copy()
    city.paste(rm.YELLOW, (0, 0), fill)
    city.paste(rm.ITA_LINE, (0, 0), line)
    return FlyCtx(world, city, w0.to_raster(lat, lon), z0, z1)


def fly_frame(ctx: FlyCtx, f: int) -> Image.Image:
    p = rm._ramp(f, 0, 118)
    scale = 2 ** ((ctx.z1 - ctx.z0) * p)
    cx, cy = ctx.city_xy
    cw, ch = W / scale, H / scale
    crop = ctx.world.crop((int(cx - cw / 2), int(cy - ch / 2),
                           int(cx + cw / 2), int(cy + ch / 2)))
    zoomed = crop.resize((W, H), Image.BILINEAR).convert("RGBA")
    a = rm._ramp(f, 78, 108)
    img = Image.blend(zoomed, ctx.city.convert("RGBA"), a)
    if f < 60:
        return img.convert("RGB")
    # end-card overlay on the sharp plate
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    mx, my = W / 2, H / 2
    dot_r = 7.0 * rm._ramp(f, 100, 110)
    if dot_r > 0.5:
        l = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        ImageDraw.Draw(l).ellipse((mx - dot_r, my - dot_r, mx + dot_r, my + dot_r),
                                  fill=rm.INK + (255,))
        ov = Image.alpha_composite(ov, l)
    if rm._ramp(f, 108, 120) > 0:
        box, _ = _label_box(None, "porto", mx - 57, my + 89,
                            rm._font("Inter-SemiBold.ttf", 34),
                            rm.INK + (255,), (255, 255, 255, 255))
        ov = Image.alpha_composite(ov, box)
        ff = rm.ImageFont.truetype(str(rm.FONT_DIR / "BodoniModa-Italic.ttf"), 96)
        fig = "250 chili"
        w = ff.getlength(fig)
        ov = Image.alpha_composite(
            ov, rm._text_layer(fig, ff, rm.RED, (rm.FIG_X, rm.FIG_Y),
                               clip_x=rm.FIG_X + w * rm._ramp(f, 112, 135)))
        ov = Image.alpha_composite(
            ov, rm._text_layer("di cocaina", rm._font("Inter-Regular.ttf", 40),
                               rm.GREY_TEXT, (rm.FIG_X + w + 14, rm.FIG_Y),
                               alpha=rm._ramp(f, 128, 145)))
    return Image.alpha_composite(img, ov).convert("RGB")


# ---------------------------------------------------------------------------
# 5. timeline Italy 2021-2025
# ---------------------------------------------------------------------------

YEARS = [("Milano", 2021), ("Roma", 2022), ("Napoli", 2023),
         ("Palermo", 2024), ("Torino", 2025)]


@dataclass(frozen=True)
class TimeCtx:
    base: Image.Image
    pins: tuple  # (x, y, label, year, t0)


def timeline_prepare():
    features = wm.country_features("ITA")
    win = wm.fit_window(*wm.main_territory_bounds(features))
    base, fill, _ = render_plate(win, W, H, features)
    plate = base.copy()
    plate.paste(rm.YELLOW, (0, 0), fill)
    pins = []
    for i, (city, year) in enumerate(YEARS):
        lon, lat = wm.city_point(city, "IT")
        pins.append((*win.to_raster(lat, lon), f"{city} · {year}", year, 15 + i * 22))
    return TimeCtx(plate, tuple(pins))


def timeline_frame(ctx: TimeCtx, f: int) -> Image.Image:
    img = Image.blend(Image.new("RGB", (W, H), rm.SEA), ctx.base, rm._ramp(f, 0, 15))
    img = img.convert("RGBA")
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    font = rm._font("Inter-SemiBold.ttf", 30)
    year_font = rm._font("Inter-Bold.ttf", 72)
    cur = None
    for x, y, label, year, t0 in ctx.pins:
        a = rm._ramp(f, t0, t0 + 10)
        if a <= 0:
            continue
        cur = year
        l = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(l)
        r = 4 + 5 * a
        d.ellipse((x - r, y - r, x + r, y + r), fill=rm.INK + (int(255 * a),))
        d.text((x + 12, y - 16), label, font=font, fill=rm.INK + (int(255 * a),))
        ov = Image.alpha_composite(ov, l)
    if cur:
        ov = Image.alpha_composite(
            ov, rm._text_layer(str(cur), year_font, (60, 60, 60), (120, 200)))
    if rm._ramp(f, 120, 135) > 0:
        ff = rm.ImageFont.truetype(str(rm.FONT_DIR / "BodoniModa-Italic.ttf"), 96)
        fig = "5 piazze"
        w = ff.getlength(fig)
        ov = Image.alpha_composite(
            ov, rm._text_layer(fig, ff, rm.RED, (rm.FIG_X, rm.FIG_Y),
                               clip_x=rm.FIG_X + w * rm._ramp(f, 120, 140)))
        ov = Image.alpha_composite(
            ov, rm._text_layer("in 5 anni", rm._font("Inter-Regular.ttf", 40),
                               rm.GREY_TEXT, (rm.FIG_X + w + 14, rm.FIG_Y),
                               alpha=rm._ramp(f, 132, 147)))
    return Image.alpha_composite(img, ov).convert("RGB")


# ---------------------------------------------------------------------------
# 6. split Napoli vs Milano
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class SplitCtx:
    left: Image.Image
    right: Image.Image


def split_prepare():
    halves = []
    for city in ("Napoli", "Milano"):
        lon, lat = wm.city_point(city, "IT")
        win = wm.Window.centered_on(lat, lon, 8, W // 2, H)
        base, fill, line = render_plate(win, W // 2, H, None)
        plate = base.copy()
        plate.paste(rm.YELLOW, (0, 0), fill)
        x, y = win.to_raster(lat, lon)
        d = ImageDraw.Draw(plate)
        d.ellipse((x - 7, y - 7, x + 7, y + 7), fill=(22, 22, 22))
        halves.append(plate)
    canvas = Image.new("RGB", (W, H))
    canvas.paste(halves[0], (0, 0))
    canvas.paste(halves[1], (W // 2, 0))
    d = ImageDraw.Draw(canvas)
    d.line([(W // 2, 0), (W // 2, H)], fill=(255, 255, 255), width=6)
    return SplitCtx(canvas, canvas)


def split_frame(ctx: SplitCtx, f: int) -> Image.Image:
    img = Image.blend(Image.new("RGB", (W, H), rm.SEA), ctx.left, rm._ramp(f, 0, 20))
    img = img.convert("RGBA")
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    specs = [(120, "Napoli", "45 €/g", 40), (W // 2 + 120, "Milano", "60 €/g", 55)]
    for x, label, price, t0 in specs:
        if rm._ramp(f, t0, t0 + 12) <= 0:
            continue
        box, _ = _label_box(None, label, x + 130, 300,
                            rm._font("Inter-SemiBold.ttf", 34),
                            rm.INK + (255,), (255, 255, 255, 255))
        ov = Image.alpha_composite(ov, box)
        ff = rm.ImageFont.truetype(str(rm.FONT_DIR / "BodoniModa-Italic.ttf"), 88)
        ov = Image.alpha_composite(
            ov, rm._text_layer(price, ff, rm.RED, (x, 560),
                               alpha=rm._ramp(f, t0 + 10, t0 + 25)))
    return Image.alpha_composite(img, ov).convert("RGB")


# ---------------------------------------------------------------------------
# registry + CLI
# ---------------------------------------------------------------------------

STYLES = {
    "dark": (dark_prepare, dark_frame),
    "route": (route_prepare, route_frame),
    "bubbles": (bubbles_prepare, bubbles_frame),
    "flyin": (fly_prepare, fly_frame),
    "timeline": (timeline_prepare, timeline_frame),
    "split": (split_prepare, split_frame),
}


def render_style(slug: str, out: Path) -> None:
    prepare, frame = STYLES[slug]
    ctx = prepare()
    _write_mp4(out, (frame(ctx, f) for f in range(FRAMES)))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--list", action="store_true")
    parser.add_argument("--style", help="one of: " + ", ".join(STYLES))
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--out", type=Path)
    parser.add_argument("--out-dir", type=Path)
    parser.add_argument("--still", type=int, default=None)
    args = parser.parse_args()
    if args.list:
        print(*STYLES, sep="\n")
        return 0
    if args.all:
        out_dir = args.out_dir or (HERE.parents[1] / "out" / "map_styles_v2")
        for slug in STYLES:
            render_style(slug, out_dir / f"{slug}.mp4")
        return 0
    if not args.style or not args.out:
        parser.error("--style and --out are required (or use --all / --list)")
    prepare, frame = STYLES[args.style]
    args.out.parent.mkdir(parents=True, exist_ok=True)
    ctx = prepare()
    if args.still is not None:
        frame(ctx, args.still).save(args.out)
        print(f"wrote {args.out}")
        return 0
    _write_mp4(args.out, (frame(ctx, f) for f in range(FRAMES)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
