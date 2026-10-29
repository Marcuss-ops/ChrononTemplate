"""ChrononTemplate — web shots rebuild kit.

Shared drawing/animation toolkit used to recreate the supplied web screenshot
references as native 1920x1080 stills plus short animated clips. Every pixel is
authored with PIL/numpy/cv2 primitives: no reference screenshot is ever loaded
as an asset.

Pipeline per shot (see render_web_shots_rebuild_v1.py):
  1. the shot draws its static plate once (cached at supersampled resolution),
  2. per frame the animated overlays are drawn on a copy of that plate,
  3. a slow camera move crops/zooms the plate,
  4. post effects (grain, vignette, chroma fringe, CRT grid) are applied,
  5. frames -> PNG, ffmpeg -> mp4, hero frame -> still.png.
"""

from __future__ import annotations

import json
import os
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional, Sequence, Tuple

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

TEMPLATE_ROOT = Path(__file__).resolve().parents[2]
FONTS = TEMPLATE_ROOT / "assets" / "fonts"
CHRONON_FONTS = TEMPLATE_ROOT.parent / "Chronon3d" / "assets" / "fonts"

Color = Tuple[int, int, int, int]


def asset(*parts: str) -> str:
    """Project-root-relative asset path (independent of the caller's cwd)."""
    return str(TEMPLATE_ROOT.joinpath(*parts))

# --------------------------------------------------------------------------- #
# fonts
# --------------------------------------------------------------------------- #

_FONT_FILES = {
    "sans": "Inter-Regular.ttf",
    "sans-med": "Inter-Medium.ttf",
    "sans-semi": "Inter-SemiBold.ttf",
    "sans-bold": "Inter-Bold.ttf",
    "sans-xbold": "Inter-ExtraBold.ttf",
    "sans-black": "Inter-Black.ttf",
    "serif": "PlayfairDisplay.ttf",
    "serif-med": "PlayfairDisplay-MediumItalic.ttf",
    "serif-it": "PlayfairDisplay-Italic.ttf",
    "serif-bold": "PlayfairDisplay-Bold.ttf",
    "serif-bold-it": "PlayfairDisplay-BoldItalic.ttf",
    "serif-black-it": "PlayfairDisplay-BlackItalic.ttf",
    "oswald": "Oswald.ttf",
    "oswald-med": "Oswald-Medium.ttf",
    "oswald-bold": "Oswald-Bold.ttf",
    "impact": "Impact.ttf",
    "anton": "Anton-Regular.ttf",
    "abril": "AbrilFatface-Regular.ttf",
    "helv": "HelveticaNeue-Regular.otf",
    "helv-med": "HelveticaNeue-Medium.otf",
    "helv-bold": "HelveticaNeue-Bold.otf",
    "arial-bold": "Arial-Bold.ttf",
    "dejavu": "DejaVuSans.ttf",
    "times": "FreeSerif.ttf",
    "times-bold": "Georgia_Bold.ttf",
}

_font_cache: dict = {}


def font_path(name: str) -> Path:
    fname = _FONT_FILES.get(name, name)
    for base in (FONTS, CHRONON_FONTS):
        p = base / fname
        if p.exists():
            return p
    raise FileNotFoundError(f"font not found: {name} -> {fname}")


def get_font(name: str, size: float, ss: float = 1.0) -> ImageFont.FreeTypeFont:
    key = (name, round(size * ss, 1))
    f = _font_cache.get(key)
    if f is None:
        f = ImageFont.truetype(str(font_path(name)), max(1, int(round(size * ss))))
        _font_cache[key] = f
    return f


# --------------------------------------------------------------------------- #
# colors
# --------------------------------------------------------------------------- #

def rgba(value, alpha: float = 1.0) -> Color:
    """#RRGGBB or (r,g,b[,a]) -> (r,g,b,a) 0-255."""
    if isinstance(value, str):
        v = value.lstrip("#")
        r, g, b = (int(v[i:i + 2], 16) for i in (0, 2, 4))
        return (r, g, b, int(round(alpha * 255)))
    if len(value) == 4:
        return (value[0], value[1], value[2], int(round(value[3] * alpha)))
    return (value[0], value[1], value[2], int(round(alpha * 255)))


# --------------------------------------------------------------------------- #
# canvas — 1920x1080 authoring space, rasterized at supersampled resolution
# --------------------------------------------------------------------------- #

class Canvas:
    def __init__(self, ss: float = 1.5, image: Optional[Image.Image] = None):
        self.ss = ss
        self.W, self.H = 1920, 1080
        self.PW, self.PH = int(self.W * ss), int(self.H * ss)
        self.img = image if image is not None else Image.new("RGBA", (self.PW, self.PH), (0, 0, 0, 0))
        self.draw = ImageDraw.Draw(self.img, "RGBA")

    # -- coordinate helpers -------------------------------------------------- #
    def _s(self, v: float) -> float:
        return v * self.ss

    def srect(self, x, y, w, h):
        s = self.ss
        return (x * s, y * s, (x + w) * s, (y + h) * s)

    # -- primitives ---------------------------------------------------------- #
    def _blend(self, bbox, fn):
        """Composite a translucent primitive through a scratch layer.

        PIL's ImageDraw overwrites destination pixels (alpha included) instead
        of compositing, so fills with alpha < 255 are drawn onto a transparent
        layer clipped to `bbox` and alpha-composited over the canvas.
        """
        x0, y0, x1, y1 = bbox
        gx0, gy0 = max(0, int(np.floor(x0))), max(0, int(np.floor(y0)))
        gx1, gy1 = min(self.PW, int(np.ceil(x1)) + 1), min(self.PH, int(np.ceil(y1)) + 1)
        if gx1 <= gx0 or gy1 <= gy0:
            return
        layer = Image.new("RGBA", (gx1 - gx0, gy1 - gy0), (0, 0, 0, 0))
        fn(ImageDraw.Draw(layer, "RGBA"), (-gx0, -gy0))
        self.img.alpha_composite(layer, (gx0, gy0))
        self.draw = ImageDraw.Draw(self.img, "RGBA")

    def _shape(self, col, bbox, fn):
        if col[3] >= 255:
            fn(self.draw, (0.0, 0.0))
        else:
            self._blend(bbox, fn)

    def rect(self, x, y, w, h, fill, alpha: float = 1.0, radius: float = 0.0):
        box = self.srect(x, y, w, h)
        col = rgba(fill, alpha)

        def fn(d, off):
            b = (box[0] + off[0], box[1] + off[1], box[2] + off[0], box[3] + off[1])
            if radius > 0:
                d.rounded_rectangle(b, radius=radius * self.ss, fill=col)
            else:
                d.rectangle(b, fill=col)

        self._shape(col, box, fn)

    def grad_rect(self, x, y, w, h, c1, c2, vertical: bool = True, alpha1: float = 1.0, alpha2: float = 1.0):
        """Linear gradient rectangle rendered in plate space."""
        s = self.ss
        x0, y0, x1, y1 = self.srect(x, y, w, h)
        x0, y0, x1, y1 = int(x0), int(y0), int(x1), int(y1)
        gw, gh = max(1, x1 - x0), max(1, y1 - y0)
        steps = gh if vertical else gw
        arr = np.zeros((gh, gw, 4), dtype=np.uint8)
        a1, a2 = int(alpha1 * 255), int(alpha2 * 255)
        for i in range(steps):
            t = i / max(1, steps - 1)
            c = tuple(int(round(c1[k] + (c2[k] - c1[k]) * t)) for k in range(3))
            a = int(round(a1 + (a2 - a1) * t))
            if vertical:
                arr[i, :, :] = (c[0], c[1], c[2], a)
            else:
                arr[:, i, :] = (c[0], c[1], c[2], a)
        self.img.alpha_composite(Image.fromarray(arr, "RGBA"), (x0, y0))

    def ellipse(self, x, y, w, h, fill, alpha: float = 1.0):
        box = self.srect(x, y, w, h)
        col = rgba(fill, alpha)

        def fn(d, off):
            d.ellipse((box[0] + off[0], box[1] + off[1], box[2] + off[0], box[3] + off[1]), fill=col)

        self._shape(col, box, fn)

    def line(self, x1, y1, x2, y2, fill, width: float = 2.0, alpha: float = 1.0):
        s = self.ss
        col = rgba(fill, alpha)
        wd = max(1, int(width * s))
        pts = (x1 * s, y1 * s, x2 * s, y2 * s)
        bbox = (min(pts[0], pts[2]) - wd, min(pts[1], pts[3]) - wd,
                max(pts[0], pts[2]) + wd, max(pts[1], pts[3]) + wd)

        def fn(d, off):
            d.line((pts[0] + off[0], pts[1] + off[1], pts[2] + off[0], pts[3] + off[1]),
                   fill=col, width=wd)

        self._shape(col, bbox, fn)

    def poly(self, points: Sequence[Tuple[float, float]], fill, alpha: float = 1.0):
        s = self.ss
        col = rgba(fill, alpha)
        pts = [(p[0] * s, p[1] * s) for p in points]
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        bbox = (min(xs) - 2, min(ys) - 2, max(xs) + 2, max(ys) + 2)

        def fn(d, off):
            d.polygon([(p[0] + off[0], p[1] + off[1]) for p in pts], fill=col)

        self._shape(col, bbox, fn)

    # -- text ---------------------------------------------------------------- #
    def measure(self, text: str, size: float, font: str = "sans", spacing: float = 0.0) -> float:
        f = get_font(font, size, self.ss)
        w = f.getlength(text) / self.ss
        return w + spacing * max(0, len(text) - 1)

    def text(self, x, y, text: str, size: float, font: str = "sans", fill="#000000",
             alpha: float = 1.0, spacing: float = 0.0, anchor: str = "la"):
        f = get_font(font, size, self.ss)
        s = self.ss
        col = rgba(fill, alpha)
        if spacing:
            cx = x
            for ch in text:
                self._glyph(cx * s, y * s, ch, f, col, anchor)
                cx += f.getlength(ch) / s + spacing
        else:
            self._glyph(x * s, y * s, text, f, col, anchor)

    def _glyph(self, px, py, txt, f, col, anchor):
        def fn(d, off):
            d.text((px + off[0], py + off[1]), txt, font=f, fill=col, anchor=anchor)

        if col[3] >= 255:
            fn(self.draw, (0.0, 0.0))
        else:
            bbox = self.draw.textbbox((px, py), txt, font=f, anchor=anchor)
            self._blend((bbox[0] - 2, bbox[1] - 2, bbox[2] + 2, bbox[3] + 2), fn)

    def text_block(self, x, y, lines: Sequence[str], size: float, font: str = "sans",
                   fill="#000000", alpha: float = 1.0, leading: float = 1.55, spacing: float = 0.0):
        cy = y
        for ln in lines:
            self.text(x, cy, ln, size, font, fill, alpha, spacing)
            cy += size * leading

    # -- images -------------------------------------------------------------- #
    def paste(self, img: Image.Image, x, y, w=None, h=None, alpha: float = 1.0):
        s = self.ss
        tw = int((w if w else img.width / s) * s)
        th = int((h if h else img.height / s) * s)
        im = img.resize((max(1, tw), max(1, th)), Image.LANCZOS)
        if im.mode != "RGBA":
            im = im.convert("RGBA")
        if alpha < 1.0:
            a = im.getchannel("A").point(lambda v: int(v * alpha))
            im.putalpha(a)
        self.img.alpha_composite(im, (int(x * s), int(y * s)))

    # -- marker (highlighter) ------------------------------------------------ #
    def marker(self, x, y, w, h, fill="#E9E600", alpha: float = 0.96, sweep: float = 1.0,
               seed: int = 7, rough: bool = True):
        """Rough-edged highlighter swipe; `sweep` 0..1 reveals left->right."""
        if sweep <= 0.002:
            return
        ww = w * min(1.0, sweep)
        s = self.ss
        rnd = np.random.default_rng(seed)
        pts_top, pts_bot = [], []
        n = max(6, int(ww / 26))
        for i in range(n + 1):
            tx = x + ww * i / n
            jt = (rnd.uniform(-0.9, 0.9) * (h * 0.045)) if rough else 0.0
            jb = (rnd.uniform(-0.9, 0.9) * (h * 0.045)) if rough else 0.0
            pts_top.append((tx, y + jt))
            pts_bot.append((tx, y + h + jb))
        self.poly(pts_top + pts_bot[::-1], fill, alpha)
        # slightly denser core band, like a marker pressed harder
        self.rect(x, y + h * 0.22, ww, h * 0.56, fill, min(1.0, alpha * 1.05) if alpha < 1 else 1.0)

    # -- misc ---------------------------------------------------------------- #
    def noise(self, amount: float = 0.02, seed: int = 0):
        arr = np.asarray(self.img).astype(np.int16)
        rnd = np.random.default_rng(seed)
        n = rnd.normal(0, amount * 255 * 0.35, arr.shape[:2])[:, :, None]
        arr[:, :, :3] = np.clip(arr[:, :, :3] + n, 0, 255)
        self.img = Image.fromarray(arr.astype(np.uint8), "RGBA")
        self.draw = ImageDraw.Draw(self.img, "RGBA")

    def vignette(self, amount: float = 0.28, radius: float = 0.72):
        w, h = self.img.size
        yy, xx = np.mgrid[0:h, 0:w]
        cx, cy = w / 2, h / 2
        d = np.sqrt(((xx - cx) / (w / 2)) ** 2 + ((yy - cy) / (h / 2)) ** 2)
        mask = np.clip((d - radius) / max(0.05, (1.45 - radius)), 0, 1) ** 1.6
        arr = np.asarray(self.img).astype(np.float32)
        arr[:, :, :3] *= (1.0 - mask[:, :, None] * amount)
        self.img = Image.fromarray(arr.astype(np.uint8), "RGBA")
        self.draw = ImageDraw.Draw(self.img, "RGBA")

    def scanlines(self, period: int = 4, alpha: float = 0.06, color="#000000"):
        col = rgba(color, alpha)
        step = period * int(max(1, self.ss))
        bar = max(1, int(self.ss))

        def fn(d, off):
            for y in range(0, self.PH, step):
                d.rectangle((off[0], y + off[1], self.PW + off[0], y + bar + off[1]), fill=col)

        self._shape(col, (0, 0, self.PW, self.PH), fn)

    def screen_grid(self, step: int = 3, alpha: float = 0.05):
        """Faint filmed-screen pixel grid (LCD moiré look)."""
        col = rgba("#7d8791", alpha)
        s = int(max(1, round(step * self.ss)))

        def fn(d, off):
            for x in range(0, self.PW, s):
                d.rectangle((x + off[0], off[1], x + 1 + off[0], self.PH + off[1]), fill=col)
            for y in range(0, self.PH, s):
                d.rectangle((off[0], y + off[1], self.PW + off[0], y + 1 + off[1]), fill=col)

        self._shape(col, (0, 0, self.PW, self.PH), fn)

    def clone(self) -> "Canvas":
        return Canvas(self.ss, self.img.copy())


# --------------------------------------------------------------------------- #
# post effects on the final 1920x1080 frame
# --------------------------------------------------------------------------- #

def post_frame(img: Image.Image, grain: float = 0.012, vig: float = 0.22,
               chroma: float = 0.0, seed: int = 0) -> Image.Image:
    arr = np.asarray(img.convert("RGB")).astype(np.float32)
    if chroma > 0:
        px = max(1, int(round(chroma)))
        arr[:, :, 0] = np.roll(arr[:, :, 0], px, axis=1)
        arr[:, :, 2] = np.roll(arr[:, :, 2], -px, axis=1)
    if grain > 0:
        rnd = np.random.default_rng(seed)
        arr += rnd.normal(0, grain * 255 * 0.4, arr.shape[:2])[:, :, None]
    if vig > 0:
        h, w = arr.shape[:2]
        yy, xx = np.mgrid[0:h, 0:w]
        d = np.sqrt(((xx - w / 2) / (w / 2)) ** 2 + ((yy - h / 2) / (h / 2)) ** 2)
        mask = np.clip((d - 0.72) / 0.7, 0, 1) ** 1.6
        arr *= (1.0 - mask[:, :, None] * vig)
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), "RGB")


def apply_camera(plate: Image.Image, zoom: float = 1.0, cx: float = 0.5, cy: float = 0.5) -> Image.Image:
    """Crop `plate` (any resolution) around a center and resize to 1920x1080."""
    w, h = plate.size
    cw, ch = w / zoom, h / zoom
    x0 = cx * w - cw / 2
    y0 = cy * h - ch / 2
    x0 = max(0, min(w - cw, x0))
    y0 = max(0, min(h - ch, y0))
    return plate.crop((int(x0), int(y0), int(x0 + cw), int(y0 + ch))).resize(
        (1920, 1080), Image.LANCZOS)


def warp_perspective(img: Image.Image, src: Sequence[Tuple[float, float]],
                     dst: Sequence[Tuple[float, float]], size=(1920, 1080),
                     border_value: Optional[Tuple[int, int, int]] = None) -> Image.Image:
    import cv2
    src_a = np.float32(src)
    dst_a = np.float32(dst)
    m = cv2.getPerspectiveTransform(src_a, dst_a)
    if border_value is None:
        mode, value = cv2.BORDER_REPLICATE, (0, 0, 0)
    else:
        mode, value = cv2.BORDER_CONSTANT, tuple(int(v) for v in border_value)
    out = cv2.warpPerspective(np.asarray(img.convert("RGB")), m, size,
                              flags=cv2.INTER_LANCZOS4, borderMode=mode, borderValue=value)
    return Image.fromarray(out, "RGB")


# --------------------------------------------------------------------------- #
# YouTube player chrome (kept in frame like the paused-player references)
# --------------------------------------------------------------------------- #

def player_bar(c: Canvas, timestamp: str, progress: float, chapter: Optional[str] = None,
               muted: bool = True, light: bool = False):
    W = 1920
    c.grad_rect(0, 936, W, 144, (5, 6, 7), (5, 6, 7), alpha1=0.0, alpha2=0.55)
    # seek bar
    c.rect(18, 1004, 1884, 3, "#B8B8B8", 0.56)
    played = 1884 * max(0.0, min(1.0, progress))
    c.rect(18, 1003, played, 5, "#F00032", 1.0)
    c.ellipse(18 + played - 6, 999, 13, 13, "#F00032")
    c.text(31, 1011, "\u25b6", 31, "dejavu", "#F5F5F5")
    c.text(77, 1014, "\u25d8))" if not muted else "\u25d7))", 20, "dejavu", "#E9E9E9")
    c.rect(150, 1013, 172, 40, "#2b2b2b", 0.62, radius=18)
    c.text(236, 1018, timestamp, 20, "sans", "#E8E8E8", anchor="ma")
    if chapter:
        c.rect(332, 1013, 150, 40, "#2b2b2b", 0.62, radius=18)
        c.text(407, 1019, chapter, 17, "sans-med", "#DADADA", anchor="ma")
        c.text(466, 1018, "\u203a", 22, "dejavu", "#DADADA")
    # right icon cluster
    c.rect(1668, 1013, 234, 40, "#2b2b2b", 0.62, radius=18)
    c.text(1690, 1019, "\u229e   \u2699   CC   \u26f6", 18, "dejavu", "#E9E9E9")


# --------------------------------------------------------------------------- #
# shot contract + renderer
# --------------------------------------------------------------------------- #

@dataclass
class Shot:
    name: str
    source: str                     # original screenshot filename (for the manifest)
    seconds: float = 3.0
    fps: int = 30
    still_t: float = 1.0            # normalized time of the hero still
    description: str = ""

    # camera move: (zoom, cx, cy) as functions of t in [0,1]
    cam_from: Tuple[float, float, float] = (1.0, 0.5, 0.5)
    cam_to: Tuple[float, float, float] = (1.06, 0.5, 0.5)

    grain: float = 0.012
    vig: float = 0.20
    chroma: float = 0.0

    build_static: Optional[Callable[[Canvas], None]] = None
    # front plate composited AFTER the animated overlays (keeps the marker
    # swipes behind the glyphs of the text layer)
    build_static_front: Optional[Callable[[Canvas], None]] = None
    draw_anim: Optional[Callable[[Canvas, float], None]] = None
    draw_full: Optional[Callable[[Canvas, float], None]] = None  # if set, redraws everything
    # optional perspective stage: receives the composed frame and returns the
    # final composited image (used by the tilted-page shots)
    warp_fn: Optional[Callable[[Image.Image, float], Image.Image]] = None

    def camera(self, t: float):
        z0, x0, y0 = self.cam_from
        z1, x1, y1 = self.cam_to
        return (z0 + (z1 - z0) * t, x0 + (x1 - x0) * t, y0 + (y1 - y0) * t)

    def render_frame(self, static: Optional[Image.Image], t: float,
                     front: Optional[Image.Image] = None) -> Image.Image:
        if self.draw_full is not None:
            c = Canvas()
            self.draw_full(c, t)
        else:
            c = Canvas(image=static.copy() if static is not None else None)
            if self.draw_anim is not None:
                self.draw_anim(c, t)
            if front is not None:
                c.img.alpha_composite(front)
                c.draw = ImageDraw.Draw(c.img, "RGBA")
        zoom, cx, cy = self.camera(t)
        frame = apply_camera(c.img, zoom, cx, cy)
        if self.warp_fn is not None:
            frame = self.warp_fn(frame, t)
        return post_frame(frame, self.grain, self.vig, self.chroma, seed=int(t * 1000) & 0xFFFF)

    def render_still(self) -> Image.Image:
        return self.render_frame(self._static(), self.still_t, self._static_front())

    def _static(self) -> Optional[Image.Image]:
        if self.draw_full is not None or self.build_static is None:
            return None
        c = Canvas()
        self.build_static(c)
        return c.img

    def _static_front(self) -> Optional[Image.Image]:
        if self.draw_full is not None or self.build_static_front is None:
            return None
        c = Canvas()
        self.build_static_front(c)
        return c.img

    def render_all(self, out_root: Path, write_frames: bool = True) -> dict:
        shot_dir = out_root / self.name
        frames_dir = shot_dir / "frames"
        shot_dir.mkdir(parents=True, exist_ok=True)
        if write_frames:
            frames_dir.mkdir(parents=True, exist_ok=True)
        static = self._static()
        front = self._static_front()
        n = max(2, int(round(self.seconds * self.fps)))
        for i in range(n):
            t = i / (n - 1)
            frame = self.render_frame(static, t, front)
            if write_frames:
                frame.save(frames_dir / f"frame_{i:04d}.png")
        still = self.render_frame(static, self.still_t, front)
        still_path = shot_dir / "still.png"
        still.save(still_path)
        mp4 = shot_dir / f"{self.name}.mp4"
        subprocess.run([
            "ffmpeg", "-y", "-v", "error",
            "-framerate", str(self.fps),
            "-start_number", "0",
            "-i", str(frames_dir / "frame_%04d.png"),
            "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18",
            str(mp4),
        ], check=True)
        return {
            "shot": self.name,
            "source": self.source,
            "description": self.description,
            "seconds": self.seconds,
            "fps": self.fps,
            "frames": n,
            "still": str(still_path.relative_to(out_root)),
            "clip": str(mp4.relative_to(out_root)),
        }


def contact_sheet(stills: Sequence[Tuple[str, Image.Image]], out: Path,
                  cols: int = 3, cell_w: int = 640):
    cell_h = int(cell_w * 9 / 16)
    label_h = 34
    rows = (len(stills) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * cell_w, rows * (cell_h + label_h)), (18, 18, 20))
    d = ImageDraw.Draw(sheet)
    f = get_font("sans-med", 19, 1.0)
    for i, (name, img) in enumerate(stills):
        r, col = divmod(i, cols)
        thumb = img.convert("RGB").resize((cell_w, cell_h), Image.LANCZOS)
        y = r * (cell_h + label_h)
        sheet.paste(thumb, (col * cell_w, y))
        d.text((col * cell_w + 10, y + cell_h + 7), name, font=f, fill=(225, 225, 225))
    sheet.save(out, quality=88)
