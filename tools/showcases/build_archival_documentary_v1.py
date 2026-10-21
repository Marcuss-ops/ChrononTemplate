#!/usr/bin/env python3
"""Author and render four archival-documentary reference scenes.

No browser, no new renderer, no Blender. The four looks are composed from
canonical RenderPlan V3 image/shape/text layers plus the engine's native
noise / film_grade / chromatic / drop_shadow effects. The paper, dust and
photo textures are generated deterministically with Pillow so every asset is
reproducible byte-for-byte.

Scenes (1920x1080, 30 fps, 150 frames each):

  01_torn_paper_portrait_v1      yellowed graph paper, torn white card,
                                 archival photo, centred name, grain + RGB split
  02_bw_archive_print_v1         worn grey ground, dust, double black border,
                                 white matte, B/W print, grain and scratches
  03_vintage_film_projection_v1  black ground, diffuse halo, rounded window,
                                 projected B/W frame with gate weave + flicker
  04_double_portrait_archive_v1  parchment, two sepia cut portraits with
                                 irregular edges, centred names, archive labels

Usage:
  python3 tools/showcases/build_archival_documentary_v1.py --emit
  python3 tools/showcases/build_archival_documentary_v1.py --validate
  python3 tools/showcases/build_archival_documentary_v1.py --render --backend vulkan
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageEnhance, ImageFilter, ImageOps

HERE = Path(__file__).resolve()
TEMPLATE = HERE.parents[2]
ROOT = TEMPLATE.parent
OUT = TEMPLATE / "out/archival_documentary_v1"
ASSETS = OUT / "assets"
CLI = ROOT / "Chronon3d/build/chronon/linux-video-fast-dev/apps/chronon3d_cli/chronon3d_cli"
PEOPLE = TEMPLATE / "assets/famous_people_trio_v1/sources"

W, H, FPS, FRAMES = 1920, 1080, 30, 150
GEORGIA = "Chronon3d/assets/fonts/Georgia_Bold.ttf"
INTER = "Chronon3d/assets/fonts/Inter-Regular.ttf"
INTER_BOLD = "Chronon3d/assets/fonts/Inter-Bold.ttf"

# --------------------------------------------------------------------------
# deterministic texture helpers
# --------------------------------------------------------------------------


def noise_gray(size: tuple[int, int], cell: int, seed: int) -> Image.Image:
    """Value noise: random bytes upscaled with bicubic interpolation."""
    w, h = size
    sw, sh = max(2, w // cell), max(2, h // cell)
    data = random.Random(seed).randbytes(sw * sh)
    small = Image.frombytes("L", (sw, sh), data)
    return small.resize((w, h), Image.BICUBIC)


def fbm_gray(size: tuple[int, int], seed: int, cells=(110, 38, 9)) -> Image.Image:
    acc = noise_gray(size, cells[0], seed)
    for i, cell in enumerate(cells[1:], start=1):
        acc = Image.blend(acc, noise_gray(size, cell, seed + 7717 * i), 0.5)
    return acc


def radial_mask(size: tuple[int, int], inner: float = 0.62) -> Image.Image:
    """0 in the centre, 1 at the edges, smooth falloff."""
    w, h = size
    sw, sh = max(8, w // 16), max(8, h // 16)
    m = Image.new("L", (sw, sh), 255)
    d = ImageDraw.Draw(m)
    cx, cy = sw / 2, sh / 2
    rx, ry = sw * inner / 2, sh * inner / 2
    d.ellipse([cx - rx, cy - ry, cx + rx, cy + ry], fill=0)
    m = m.resize((w, h), Image.BICUBIC)
    return m.filter(ImageFilter.GaussianBlur(min(w, h) * 0.03))


def scaled(mask: Image.Image, lo: int, hi: int) -> Image.Image:
    return mask.point(lambda v: lo + (hi - lo) * v // 255)


def multiply_scalar(img: Image.Image, mask: Image.Image) -> Image.Image:
    if mask.mode != "L":
        mask = mask.convert("L")
    return ImageChops.multiply(img, Image.merge("RGB", (mask, mask, mask)))


def edge_offsets(count: int, amp: float, rng: random.Random) -> list[float]:
    waves = [(2, rng.uniform(0.5, 1.0)), (5, rng.uniform(0.3, 0.7)),
             (13, rng.uniform(0.14, 0.4)), (31, rng.uniform(0.05, 0.16))]
    phases = [rng.uniform(0, math.tau) for _ in waves]
    out = []
    for i in range(count):
        t = i / count
        v = sum(a * math.sin(math.tau * f * t + p) for (f, a), p in zip(waves, phases))
        out.append(v * amp + rng.uniform(-amp * 0.2, amp * 0.2))
    return out


def rough_mask(size: tuple[int, int], seed: int, amp: float = 16.0,
               inset: int = 26, fringe: bool = True) -> Image.Image:
    """Torn-paper alpha: jagged polygon perimeter with a fibrous deckle."""
    w, h = size
    m = Image.new("L", (w, h), 0)
    d = ImageDraw.Draw(m)
    rng = random.Random(seed)
    steps = 200
    top = edge_offsets(steps, amp, rng)
    right = edge_offsets(steps, amp, rng)
    bottom = edge_offsets(steps, amp, rng)
    left = edge_offsets(steps, amp, rng)
    pts: list[tuple[float, float]] = []
    for i in range(steps):
        pts.append((inset + (w - 2 * inset) * i / steps, inset + top[i]))
    for i in range(steps):
        pts.append((w - inset + right[i], inset + (h - 2 * inset) * i / steps))
    for i in range(steps):
        pts.append((w - inset - (w - 2 * inset) * i / steps, h - inset + bottom[i]))
    for i in range(steps):
        pts.append((inset + left[i], h - inset - (h - 2 * inset) * i / steps))
    d.polygon(pts, fill=255)
    m = m.filter(ImageFilter.GaussianBlur(1.4))
    m = m.point(lambda v: 255 if v > 150 else (0 if v < 95 else int((v - 95) * 255 / 55)))
    if fringe:
        fr = ImageDraw.Draw(m)
        for i in range(1800):
            px, py = pts[rng.randrange(len(pts))]
            ox = rng.uniform(-amp * 0.75, amp * 0.75)
            oy = rng.uniform(-amp * 0.75, amp * 0.75)
            r = rng.uniform(0.6, 2.2)
            fr.ellipse([px + ox - r, py + oy - r, px + ox + r, py + oy + r],
                       fill=rng.randrange(90, 240))
    return m.filter(ImageFilter.GaussianBlur(0.7))


def paper_base(size: tuple[int, int], base: tuple[int, int, int], seed: int,
               *, blotch=(200, 255), fiber: float = 0.05, edge: float = 0.22,
               stains: int = 6, stain_alpha: int = 80) -> Image.Image:
    w, h = size
    img = Image.new("RGB", size, base)
    blot = scaled(fbm_gray(size, seed), blotch[0], blotch[1])
    img = multiply_scalar(img, blot)
    fine = noise_gray(size, 1, seed + 3331)
    img = Image.blend(img, Image.merge("RGB", (fine, fine, fine)), fiber)
    if stains:
        layer = Image.new("RGBA", size, (0, 0, 0, 0))
        dl = ImageDraw.Draw(layer)
        rng = random.Random(seed + 991)
        for _ in range(stains):
            cx, cy = rng.uniform(0, w), rng.uniform(0, h)
            rx, ry = rng.uniform(w * 0.05, w * 0.22), rng.uniform(h * 0.05, h * 0.28)
            tone = rng.choice([(142, 104, 58), (128, 92, 50), (156, 124, 78)])
            dl.ellipse([cx - rx, cy - ry, cx + rx, cy + ry],
                       fill=tone + (stain_alpha,))
        layer = layer.filter(ImageFilter.GaussianBlur(min(w, h) * 0.045))
        img = Image.alpha_composite(img.convert("RGBA"), layer).convert("RGB")
    dark = scaled(radial_mask(size, 0.55), 255, int(255 * (1 - edge)))
    return multiply_scalar(img, dark)


def save_jpg(img: Image.Image, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    img.convert("RGB").save(path, quality=94, subsampling=1)


def save_png(img: Image.Image, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    img.save(path)


# --------------------------------------------------------------------------
# asset builders
# --------------------------------------------------------------------------


def build_graph_paper(path: Path) -> None:
    size = (W, H)
    img = paper_base(size, (233, 223, 194), 1942, blotch=(204, 255), fiber=0.06,
                     edge=0.30, stains=7, stain_alpha=70)
    grid = Image.new("RGB", size, (255, 255, 255))
    dg = ImageDraw.Draw(grid)
    minor, major = (222, 217, 203), (201, 165, 148)
    for x in range(0, W + 1, 22):
        dg.line([(x, 0), (x, H)], fill=minor, width=1)
    for y in range(0, H + 1, 22):
        dg.line([(0, y), (W, y)], fill=minor, width=1)
    for x in range(0, W + 1, 110):
        dg.line([(x, 0), (x, H)], fill=major, width=1)
    for y in range(0, H + 1, 110):
        dg.line([(0, y), (W, y)], fill=major, width=1)
    img = Image.blend(img, ImageChops.multiply(img, grid), 0.8)
    # fold creases
    folds = Image.new("RGBA", size, (0, 0, 0, 0))
    df = ImageDraw.Draw(folds)
    df.line([(int(W * 0.31), 0), (int(W * 0.33), H)], fill=(90, 74, 48, 46), width=3)
    df.line([(int(W * 0.31) + 4, 0), (int(W * 0.33) + 4, H)], fill=(255, 250, 232, 52), width=2)
    df.line([(0, int(H * 0.62)), (W, int(H * 0.60))], fill=(90, 74, 48, 38), width=3)
    folds = folds.filter(ImageFilter.GaussianBlur(3.5))
    img = Image.alpha_composite(img.convert("RGBA"), folds).convert("RGB")
    save_jpg(img, path)


def build_parchment(path: Path) -> None:
    size = (W, H)
    img = paper_base(size, (226, 209, 176), 4212, blotch=(196, 252), fiber=0.07,
                     edge=0.30, stains=9, stain_alpha=95)
    mottle = noise_gray(size, 24, 5150).point(lambda v: 236 + v * 19 // 255)
    img = multiply_scalar(img, mottle)
    save_jpg(img, path)


def build_worn_grey(path: Path) -> None:
    size = (W, H)
    img = paper_base(size, (150, 149, 145), 777, blotch=(214, 252), fiber=0.08,
                     edge=0.34, stains=8, stain_alpha=55)
    save_jpg(img, path)


def build_torn_card(path: Path) -> None:
    size = (1080, 880)
    rng = random.Random(4242)
    fill = paper_base(size, (247, 244, 236), 881, blotch=(232, 255), fiber=0.05,
                      edge=0.10, stains=3, stain_alpha=42)
    alpha = rough_mask(size, 19420, amp=17.0, inset=30)
    card = fill.convert("RGBA")
    card.putalpha(alpha)
    save_png(card, path)


def _tone(img: Image.Image, *, mode: str, contrast: float = 1.08,
          brightness: float = 1.0, grain: float = 0.035, seed: int = 7) -> Image.Image:
    gray = ImageOps.grayscale(img)
    gray = ImageOps.autocontrast(gray, cutoff=1)
    gray = ImageEnhance.Contrast(gray).enhance(contrast)
    gray = ImageEnhance.Brightness(gray).enhance(brightness)
    if mode == "sepia":
        toned = ImageOps.colorize(gray, (44, 30, 17), (246, 231, 202))
    elif mode == "warm_bw":
        toned = ImageOps.colorize(gray, (26, 24, 22), (243, 240, 233))
    else:
        toned = gray.convert("RGB")
    if grain > 0:
        n = noise_gray(toned.size, 1, seed).convert("RGB")
        toned = Image.blend(toned, n, grain)
        toned = Image.blend(toned, ImageChops.screen(toned, n.point(lambda v: v // 6)), 0.12)
    return toned


def _face_crop(img: Image.Image, ratio: float, zoom: float = 1.0) -> Image.Image:
    """Crop a portrait toward the head, then force the target aspect."""
    w, h = img.size
    cw = int(min(w, h * ratio) / zoom)
    ch = int(cw / ratio)
    left = (w - cw) // 2
    top = int((h - ch) * 0.18)
    return img.crop((left, top, left + cw, top + ch))


def build_photo(path: Path, source: Path, size: tuple[int, int], mode: str,
                seed: int, *, ratio: float | None = None, torn: float | None = None,
                radius: int | None = None, grain: float = 0.035,
                contrast: float = 1.08) -> None:
    img = Image.open(source).convert("RGB")
    ratio = ratio or size[0] / size[1]
    img = _face_crop(img, ratio, zoom=1.08)
    img = img.resize(size, Image.LANCZOS)
    img = _tone(img, mode=mode, contrast=contrast, grain=grain, seed=seed)
    if torn is not None:
        alpha = rough_mask(size, seed + 13, amp=torn, inset=max(6, int(torn * 0.8)))
        rgba = img.convert("RGBA")
        rgba.putalpha(alpha)
        save_png(rgba, path)
        return
    if radius is not None:
        mask = Image.new("L", size, 0)
        ImageDraw.Draw(mask).rounded_rectangle([0, 0, size[0] - 1, size[1] - 1],
                                               radius=radius, fill=255)
        rgba = img.convert("RGBA")
        rgba.putalpha(mask.filter(ImageFilter.GaussianBlur(0.6)))
        save_png(rgba, path)
        return
    save_jpg(img, path)


def build_scratches(img: Image.Image, seed: int, count: int = 26,
                    hairs: int = 5) -> Image.Image:
    """Bake sparse archival scratches and hair lines into a photo."""
    w, h = img.size
    rng = random.Random(seed)
    layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    for _ in range(count):
        x = rng.uniform(0, w)
        y0 = rng.uniform(0, h * 0.7)
        y1 = y0 + rng.uniform(h * 0.15, h * 0.55)
        tone = (248, 246, 240) if rng.random() < 0.75 else (28, 26, 24)
        d.line([(x, y0), (x + rng.uniform(-4, 4), y1)], fill=tone + (rng.randrange(38, 110),),
               width=1)
    for _ in range(hairs):
        x0, y0 = rng.uniform(0, w), rng.uniform(0, h)
        pts = [(x0, y0)]
        for _ in range(5):
            x0 += rng.uniform(-w * 0.06, w * 0.06)
            y0 += rng.uniform(-h * 0.05, h * 0.05)
            pts.append((x0, y0))
        d.line(pts, fill=(30, 28, 26, rng.randrange(60, 130)), width=1)
    layer = layer.filter(ImageFilter.GaussianBlur(0.6))
    return Image.alpha_composite(img.convert("RGBA"), layer).convert("RGB")


def build_dust_overlay(path: Path, seed: int, count: int = 520) -> None:
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    rng = random.Random(seed)
    for _ in range(count):
        x, y = rng.uniform(0, W), rng.uniform(0, H)
        r = rng.uniform(0.8, 3.4)
        tone = (246, 243, 236) if rng.random() < 0.72 else (18, 16, 14)
        d.ellipse([x - r, y - r, x + r, y + r], fill=tone + (rng.randrange(26, 120),))
    for _ in range(34):
        x = rng.uniform(0, W)
        y0 = rng.uniform(0, H * 0.8)
        d.line([(x, y0), (x + rng.uniform(-6, 6), y0 + rng.uniform(60, H * 0.5))],
               fill=(250, 248, 242, rng.randrange(22, 60)), width=1)
    save_png(layer, path)


def build_vignette_overlay(path: Path, strength: float = 0.55) -> None:
    m = radial_mask((W, H), 0.42).filter(ImageFilter.GaussianBlur(H * 0.05))
    curve = m.point(lambda v: int(min(255, max(0, (v - 60) * 255 / 195) * strength)))
    overlay = Image.new("RGBA", (W, H), (12, 10, 8, 0))
    overlay.putalpha(curve)
    save_png(overlay, path)


def build_halo_overlay(path: Path) -> None:
    m = radial_mask((W, H), 0.9)
    curve = m.point(lambda v: int((255 - v) ** 2 / 255 * 0.55))
    halo = Image.new("RGBA", (W, H), (255, 251, 240, 0))
    halo.putalpha(curve)
    save_png(halo, path)


def emit_assets() -> None:
    ASSETS.mkdir(parents=True, exist_ok=True)
    build_graph_paper(ASSETS / "graph_paper.jpg")
    build_parchment(ASSETS / "parchment.jpg")
    build_worn_grey(ASSETS / "worn_grey.jpg")
    build_torn_card(ASSETS / "torn_card.png")

    build_photo(ASSETS / "photo_armstrong_bw.jpg", PEOPLE / "neil_armstrong.jpg",
                (800, 560), "warm_bw", 11, grain=0.03)
    g = Image.open(PEOPLE / "john_glenn.jpg").convert("RGB")
    g = _tone(_face_crop(g, 1040 / 700, zoom=1.05).resize((1040, 700), Image.LANCZOS),
              mode="warm_bw", contrast=1.14, grain=0.045, seed=23)
    save_jpg(build_scratches(g, 23), ASSETS / "photo_glenn_print.jpg")
    build_photo(ASSETS / "film_still_ride.png", PEOPLE / "sally_ride.jpg",
                (1180, 664), "warm_bw", 31, radius=26, grain=0.05, contrast=1.2)
    build_photo(ASSETS / "sepia_glenn.png", PEOPLE / "john_glenn.jpg",
                (520, 660), "sepia", 41, torn=9.0, grain=0.03)
    build_photo(ASSETS / "sepia_ride.png", PEOPLE / "sally_ride.jpg",
                (520, 660), "sepia", 47, torn=9.0, grain=0.03)

    build_dust_overlay(ASSETS / "dust_grey.png", 3301)
    build_dust_overlay(ASSETS / "dust_film.png", 4409, count=380)
    build_vignette_overlay(ASSETS / "vignette.png", 0.55)
    build_vignette_overlay(ASSETS / "vignette_soft.png", 0.38)
    build_halo_overlay(ASSETS / "halo.png")


# --------------------------------------------------------------------------
# plan helpers (RenderPlan V3, screen_space = top-left positions)
# --------------------------------------------------------------------------


def base(name: str, ground: list[float]) -> dict:
    return {"schema": "chronon.render-plan.v3", "version": 3, "job_id": name,
            "canvas": {"width": W, "height": H, "fps_num": FPS, "fps_den": 1,
                       "duration_frames": FRAMES},
            "output": {"path": f"{name}.mp4", "format": "mp4", "codec": "h264"},
            "layers": [{"id": "ground", "type": "color", "color": ground,
                        "size": [W, H], "position": [0, 0], "screen_space": True,
                        "start_frame": 0, "duration_frames": FRAMES}]}


def track(prop: str, pairs: list[tuple[int, float]], easing: str = "linear") -> dict:
    return {"property": prop, "easing": easing,
            "keyframes": [{"frame": f, "value": v} for f, v in pairs]}


def image(id_: str, asset: str, x: float, y: float, w: float, h: float, *,
          opacity: float = 1.0, radius: float | None = None,
          blend: str | None = None, effects: list[dict] | None = None,
          animation: dict | None = None) -> dict:
    layer = {"id": id_, "type": "image", "asset": asset, "size": [w, h],
             "position": [x, y], "fit": "cover", "screen_space": True,
             "opacity": opacity, "start_frame": 0, "duration_frames": FRAMES}
    if radius is not None:
        layer["radius"] = radius
    if blend:
        layer["blend_mode"] = blend
    if effects:
        layer["effects"] = effects
    if animation:
        layer["animation"] = {"tracks": animation}
    return layer


def rect(id_: str, x: float, y: float, w: float, h: float, fill: list[float], *,
         opacity: float = 1.0, radius: float | None = None,
         animation: dict | None = None) -> dict:
    shape = {"type": "rounded_rect" if radius else "rect", "fill": fill}
    if radius:
        shape["radius"] = radius
    layer = {"id": id_, "type": "shape", "shape": shape, "size": [w, h],
             "position": [x, y], "screen_space": True, "opacity": opacity,
             "start_frame": 0, "duration_frames": FRAMES}
    if animation:
        layer["animation"] = {"tracks": animation}
    return layer


def text(id_: str, words: str, x: float, y: float, w: float, h: float, size: float,
         fill: str, font: str = INTER, *, align: str = "center",
         tracking: float | None = None, animation: dict | None = None,
         opacity: float = 1.0) -> dict:
    style = {"font": font, "font_size": size, "fill": fill, "text_align": align,
             "min_font_size": size, "max_font_size": size, "fit_mode": "shrink_only"}
    layer = {"id": id_, "type": "text", "text": words, "size": [w, h],
             "position": [x, y], "screen_space": True, "style": style,
             "opacity": opacity, "start_frame": 0, "duration_frames": FRAMES}
    if tracking is not None:
        style["tracking"] = tracking
    if animation:
        layer["animation"] = {"tracks": animation}
    return layer


def grain_overlay(id_: str = "film_grain", amount: float = 0.34,
                  seed: int = 515, opacity: float = 0.13) -> dict:
    return {"id": id_, "type": "shape",
            "shape": {"type": "rect", "fill": [0.5, 0.5, 0.5, 1.0]},
            "size": [W, H], "position": [0, 0], "screen_space": True,
            "opacity": opacity, "blend_mode": "screen",
            "start_frame": 0, "duration_frames": FRAMES,
            "effects": [{"type": "noise", "amount": amount, "size": 1.3,
                         "seed": seed, "animated": True,
                         "color_mode": "monochrome",
                         "shadow_response": 1.0, "midtone_response": 1.0,
                         "highlight_response": 0.8}]}


def a(asset: str) -> str:
    return f"ChrononTemplate/out/archival_documentary_v1/assets/{asset}"


# --------------------------------------------------------------------------
# the four scenes
# --------------------------------------------------------------------------


def scene_01() -> dict:
    p = base("01_torn_paper_portrait_v1", [0.09, 0.08, 0.07, 1.0])
    l = p["layers"]
    push_paper = [track("scale", [(0, 1.0), (FRAMES, 1.045)])]
    push_card = [track("scale", [(0, 1.0), (FRAMES, 1.085)]),
                 track("opacity", [(0, 0.0), (8, 0.0), (30, 1.0)], "out_cubic")]
    l += [image("graph_paper", a("graph_paper.jpg"), 0, 0, W, H,
                animation=push_paper),
          image("torn_card", a("torn_card.png"), 420, 62, 1080, 880,
                effects=[{"type": "drop_shadow", "radius": 26,
                          "offset": [10, 18], "color": [0.06, 0.05, 0.04, 0.45]}],
                animation=push_card),
          image("portrait", a("photo_armstrong_bw.jpg"), 560, 190, 800, 560,
                effects=[{"type": "film_grade", "grain": 0.06, "seed": 1942,
                          "grain_size": 1.4, "shadow_response": 1.1,
                          "midtone_response": 1.0, "highlight_response": 0.7},
                         {"type": "rgb_channel_transform", "red_offset": 1.1,
                          "blue_offset": -1.1}],
                animation=[track("scale", [(0, 1.0), (FRAMES, 1.085)])]),
          text("name", "NEIL ARMSTRONG", 560, 792, 800, 74, 54, "#23201B", GEORGIA,
               animation=[track("scale", [(0, 1.0), (FRAMES, 1.08)]),
                          track("opacity", [(0, 0.0), (26, 0.0), (52, 1.0)], "out_cubic")]),
          text("caption", "APOLLO 11   ·   21 JULY 1969", 560, 872, 800, 44, 23,
               "#6B6154", INTER,
               animation=[track("scale", [(0, 1.0), (FRAMES, 1.08)]),
                          track("opacity", [(0, 0.0), (40, 0.0), (66, 1.0)], "out_cubic")]),
          image("vignette", a("vignette.png"), 0, 0, W, H),
          grain_overlay("film_grain", 0.32, 515, 0.13)]
    return p


def scene_02() -> dict:
    p = base("02_bw_archive_print_v1", [0.11, 0.11, 0.105, 1.0])
    l = p["layers"]
    zoom = [track("scale", [(0, 1.0), (FRAMES, 1.035)])]
    l += [image("worn_grey", a("worn_grey.jpg"), 0, 0, W, H, animation=zoom),
          image("dust", a("dust_grey.png"), 0, 0, W, H, opacity=0.55,
                blend="screen", animation=zoom),
          rect("mount_black", 336, 74, 1248, 932, [0.035, 0.034, 0.032, 1.0],
               animation=zoom),
          rect("hairline_black", 378, 116, 1164, 848, [0.05, 0.049, 0.046, 1.0],
               animation=zoom),
          rect("white_matte", 386, 124, 1148, 832, [0.937, 0.925, 0.895, 1.0],
               animation=zoom),
          image("print", a("photo_glenn_print.jpg"), 440, 190, 1040, 700,
                effects=[{"type": "film_grade", "grain": 0.07, "seed": 808,
                          "grain_size": 1.6, "shadow_response": 1.2,
                          "midtone_response": 1.0, "highlight_response": 0.6}],
                animation=zoom),
          text("label", "ARCHIVE PRINT   /   FRAME 014", 440, 906, 1040, 40, 21,
               "#4A443B", INTER, animation=zoom),
          image("vignette", a("vignette_soft.png"), 0, 0, W, H),
          grain_overlay("film_grain", 0.30, 622, 0.12)]
    return p


def scene_03() -> dict:
    p = base("03_vintage_film_projection_v1", [0.012, 0.011, 0.010, 1.0])
    l = p["layers"]
    rng = random.Random(1969)
    weave_x = [(0, 0.0)] + [(f, round(rng.uniform(-2.6, 2.6), 2))
                            for f in range(12, FRAMES, 12)] + [(FRAMES, 0.0)]
    weave_y = [(0, 0.0)] + [(f, round(rng.uniform(-1.8, 1.8), 2))
                            for f in range(9, FRAMES, 11)] + [(FRAMES, 0.0)]
    flicker = [(0, 1.0), (31, 1.0), (32, 0.92), (33, 1.0), (68, 1.0), (69, 0.95),
               (70, 1.0), (104, 1.0), (105, 0.90), (106, 1.0), (128, 1.0),
               (129, 0.96), (130, 1.0), (FRAMES, 1.0)]
    l += [image("halo", a("halo.png"), 0, 0, W, H),
          image("projected_frame", a("film_still_ride.png"), 370, 208, 1180, 664,
                radius=26,
                effects=[{"type": "film_grade", "grain": 0.10, "seed": 777,
                          "grain_size": 1.8, "shadow_response": 1.4,
                          "midtone_response": 1.1, "highlight_response": 0.5},
                         {"type": "halation", "radius_px": 26.0,
                          "threshold": 0.66, "softness": 0.25, "intensity": 0.30},
                         {"type": "lens_distortion", "curvature": 0.06,
                          "scale": 1.0}],
                animation=[track("position_x", weave_x),
                           track("position_y", weave_y),
                           track("opacity", flicker),
                           track("scale", [(0, 1.0), (FRAMES, 1.02)])]),
          image("dust", a("dust_film.png"), 0, 0, W, H, opacity=0.5,
                blend="screen",
                animation=[track("position_y", [(0, 0.0), (FRAMES, -26.0)]),
                           track("position_x", [(0, 0.0), (FRAMES, 9.0)])]),
          image("vignette", a("vignette.png"), 0, 0, W, H),
          grain_overlay("emulsion_grain", 0.42, 1201, 0.16)]
    return p


def scene_04() -> dict:
    p = base("04_double_portrait_archive_v1", [0.16, 0.14, 0.11, 1.0])
    l = p["layers"]
    dolly = [track("scale", [(0, 1.0), (FRAMES, 1.03)])]
    left_in = [track("opacity", [(0, 0.0), (24, 1.0)], "out_cubic"),
               track("scale", [(0, 0.96), (30, 1.0), (46, 1.0), (FRAMES, 1.05)],
                     "in_out_sine")]
    right_in = [track("opacity", [(10, 0.0), (36, 1.0)], "out_cubic"),
                track("scale", [(10, 0.96), (42, 1.0), (52, 1.0), (FRAMES, 1.05)],
                      "in_out_sine")]
    names_in = [track("opacity", [(0, 0.0), (44, 0.0), (70, 1.0)], "out_cubic"),
                track("scale", [(0, 1.0), (52, 1.0), (FRAMES, 1.05)], "in_out_sine")]
    l += [image("parchment", a("parchment.jpg"), 0, 0, W, H, animation=dolly),
          image("portrait_left", a("sepia_glenn.png"), 388, 176, 520, 660,
                animation=left_in,
                effects=[{"type": "drop_shadow", "radius": 18,
                          "offset": [6, 12], "color": [0.10, 0.08, 0.05, 0.40]}]),
          image("portrait_right", a("sepia_ride.png"), 1012, 176, 520, 660,
                animation=right_in,
                effects=[{"type": "drop_shadow", "radius": 18,
                          "offset": [-6, 12], "color": [0.10, 0.08, 0.05, 0.40]}]),
          text("name_left", "JOHN GLENN", 388, 866, 520, 60, 40, "#2E241A", GEORGIA,
               animation=names_in),
          text("label_left", "NASA ARCHIVE  /  1962", 388, 926, 520, 36, 19,
               "#6E5C46", INTER, animation=names_in),
          text("name_right", "SALLY RIDE", 1012, 866, 520, 60, 40, "#2E241A", GEORGIA,
               animation=names_in),
          text("label_right", "NASA ARCHIVE  /  1983", 1012, 926, 520, 36, 19,
               "#6E5C46", INTER, animation=names_in),
          image("vignette", a("vignette_soft.png"), 0, 0, W, H),
          grain_overlay("film_grain", 0.26, 3313, 0.11)]
    return p


SCENES = {"01_torn_paper_portrait_v1": scene_01,
          "02_bw_archive_print_v1": scene_02,
          "03_vintage_film_projection_v1": scene_03,
          "04_double_portrait_archive_v1": scene_04}


def emit(out: Path) -> list[Path]:
    out.mkdir(parents=True, exist_ok=True)
    plans = []
    for name, builder in SCENES.items():
        plan = out / f"{name}.plan.json"
        plan.write_text(json.dumps(builder(), indent=2) + "\n")
        plans.append(plan)
    return plans


def checked(cmd: list[str]) -> None:
    print("+", " ".join(str(c) for c in cmd))
    subprocess.run(cmd, check=True)


def validate(plans: list[Path], cli: Path) -> None:
    for plan in plans:
        checked([str(cli), "validate", "--plan", str(plan), "--assets-root", str(ROOT)])


def render(plans: list[Path], cli: Path, out: Path, backend: str) -> None:
    for plan in plans:
        name = plan.name.removesuffix(".plan.json")
        video = out / f"{name}.mp4"
        cmd = [str(cli), "render", "--plan", str(plan), "--assets-root", str(ROOT),
               "--backend", backend, "--profile", "preview", "--fps", "30",
               "--rate-control", "crf", "--crf", "19"]
        if backend == "vulkan":
            cmd += ["--hardware", "nvenc", "--encode-preset", "p5"]
        cmd += ["--ffmpeg-mode", "pipe", "-o", str(video)]
        checked(cmd)
        info = json.loads(subprocess.check_output([
            "ffprobe", "-v", "error", "-count_frames", "-select_streams", "v:0",
            "-show_entries", "stream=codec_name,width,height,avg_frame_rate,nb_read_frames,duration",
            "-of", "json", str(video)], text=True))["streams"][0]
        expected = ("h264", W, H, f"{FPS}/1", FRAMES)
        got = (info.get("codec_name"), int(info.get("width", 0)), int(info.get("height", 0)),
               info.get("avg_frame_rate"), int(info.get("nb_read_frames", 0)))
        if got != expected:
            raise RuntimeError(f"invalid video stream {name}: {got}")
        for tag, frame in (("start", 0), ("middle", FRAMES // 2), ("end", FRAMES - 1)):
            checked(["ffmpeg", "-y", "-v", "error", "-i", str(video), "-vf",
                     f"select=eq(n\\,{frame})", "-frames:v", "1",
                     str(out / f"{name}.{tag}.png")])
        print(f"{name}: {video.stat().st_size} bytes sha256="
              f"{hashlib.sha256(video.read_bytes()).hexdigest()[:16]}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=OUT)
    parser.add_argument("--cli", type=Path, default=CLI)
    parser.add_argument("--emit", action="store_true", help="assets + plans only")
    parser.add_argument("--validate", action="store_true")
    parser.add_argument("--render", action="store_true")
    parser.add_argument("--backend", default="vulkan", choices=["vulkan", "software"])
    args = parser.parse_args()
    out = args.out.resolve()
    cli = args.cli.resolve()

    if args.emit or not (args.validate or args.render):
        emit_assets()
        print(f"Assets written to {ASSETS}")
    plans = emit(out)
    print(f"Emitted {len(plans)} plans to {out}")
    if args.validate:
        validate(plans, cli)
        print("All plans validate against the live RenderPlan contract")
    if args.render:
        render(plans, cli, out, args.backend)
        print(f"Rendered {len(plans)} H.264 MP4s in {out}")


if __name__ == "__main__":
    main()
