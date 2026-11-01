"""Render the three reference motion assets as 1080p H.264 MP4s."""
from pathlib import Path
import math
import shutil
import subprocess

import cv2
import numpy as np

BASE = Path(__file__).resolve().parent
RENDERS = BASE / "renders"
PACK = Path(__file__).resolve().parents[3] / "assets" / "chronon_visual_venture_pack"
W, H, FPS, FRAMES = 1920, 1080, 24, 192
GRAIN = np.random.default_rng(7103).normal(1.5, 4.5, (H, W, 1)).astype(np.float32)
JOBS = ["06_device_to_orbital_core", "07_red_orbital_pulse", "08_spotlight_signal_scan"]
WHITE = (242, 244, 248)
RED = (55, 48, 255)  # BGR


def smooth(a, b, x):
    t = max(0.0, min(1.0, (x - a) / (b - a)))
    return t * t * (3.0 - 2.0 * t)


def canvas():
    y, x = np.ogrid[:H, :W]
    r2 = ((x - W / 2) / 1000) ** 2 + ((y - H / 2) / 680) ** 2
    shade = np.clip(1 - .72 * r2, .25, 1)
    img = np.zeros((H, W, 3), np.uint8)
    for c, value in enumerate((22, 22, 24)):
        img[:, :, c] = (shade * value).astype(np.uint8)
    return img


def glow(img, draw, strength=1.0, blur=19):
    layer = np.zeros_like(img)
    draw(layer, strength)
    halo = cv2.GaussianBlur(layer, (0, 0), blur)
    cv2.addWeighted(img, 1, halo, .8, 0, img)
    cv2.addWeighted(img, 1, layer, 1, 0, img)


def rounded_rect(img, x, y, w, h, radius=14, color=WHITE, thickness=5):
    cv2.rectangle(img, (x + radius, y), (x + w - radius, y + h), color, thickness, cv2.LINE_AA)
    cv2.rectangle(img, (x, y + radius), (x + w, y + h - radius), color, thickness, cv2.LINE_AA)
    for cx, cy, start in ((x + radius, y + radius, 180), (x + w - radius, y + radius, 270),
                          (x + w - radius, y + h - radius, 0), (x + radius, y + h - radius, 90)):
        cv2.ellipse(img, (cx, cy), (radius, radius), 0, start, start + 90, color, thickness, cv2.LINE_AA)


def draw_orbit(img, t, scale=1.0, alpha=1.0, rotate=0.0, pulse=True):
    cx, cy = 960, 540
    rad = int(17 + 7 * (0.5 + 0.5 * math.sin(t * math.tau / 1.8))) if pulse else 32
    def paint(layer, amount):
        col = tuple(int(v * alpha * amount) for v in RED)
        cv2.circle(layer, (cx, cy), max(1, int(rad * scale)), col, -1, cv2.LINE_AA)
        for i in range(8):
            a = rotate + t * math.tau / 14 + i * math.tau / 8
            px, py = int(cx + math.cos(a) * 73 * scale), int(cy + math.sin(a) * 73 * scale)
            cv2.circle(layer, (px, py), 5, tuple(int(v * alpha * amount) for v in WHITE), -1, cv2.LINE_AA)
    glow(img, paint, blur=18)


def render_06(t):
    img = canvas()
    phase = t / 8.0
    grid_a = 1 - smooth(.18, .30, phase)
    grid_scale = 1 - .28 * smooth(.18, .30, phase)
    if grid_a > .01:
        def grid(layer, amount):
            sw = int(240 * grid_scale); sh = int(68 * grid_scale); gap = int(24 * grid_scale)
            x = 960 - sw // 2
            top = 431 - (3 * sh + 2 * gap) // 2
            col = tuple(int(c * grid_a * amount) for c in WHITE)
            for i in range(3): rounded_rect(layer, x, top + i * (sh + gap), sw, sh, 14, col, 5)
            cv2.line(layer, (960, top + sh), (960, top + sh + gap), col, 2, cv2.LINE_AA)
            cv2.line(layer, (960, top + sh * 2 + gap), (960, top + sh * 2 + gap * 2), col, 2, cv2.LINE_AA)
        glow(img, grid)
    device_a = smooth(.20, .34, phase) * (1 - smooth(.68, .78, phase))
    if device_a > .01:
        scale = .55 + .45 * smooth(.20, .34, phase)
        def device(layer, amount):
            x, y = int(960 - 60 * scale), int(438 - 93 * scale)
            rounded_rect(layer, x, y, int(120 * scale), int(186 * scale), 12, tuple(int(c * device_a * amount) for c in WHITE), 5)
            cv2.circle(layer, (int(943), int(478)), 11, tuple(int(c * device_a * amount) for c in WHITE), -1, cv2.LINE_AA)
            cv2.circle(layer, (int(977), int(478)), 7, tuple(int(c * device_a * amount) for c in (205, 205, 205)), -1, cv2.LINE_AA)
        glow(img, device)
    beam_a = .8 * smooth(.33, .42, phase) * (1 - smooth(.65, .76, phase))
    if beam_a > .01:
        overlay = img.copy()
        cv2.fillConvexPoly(overlay, np.array([[960, 218], [1100, 760], [820, 760]], np.int32), (230, 230, 230), cv2.LINE_AA)
        cv2.addWeighted(overlay, beam_a * .12, img, 1 - beam_a * .12, 0, img)
        cv2.line(img, (940, 220), (980, 220), WHITE, 8, cv2.LINE_AA)
    orbit_a = smooth(.65, .82, phase)
    if orbit_a > .01: draw_orbit(img, t, scale=.3 + .7 * smooth(.65, .82, phase), alpha=orbit_a, rotate=-math.pi / 2)
    return img


def render_07(t):
    img = canvas()
    cv2.circle(img, (960, 540), 120, (150, 155, 165), 2, cv2.LINE_AA)
    ripple_r = int(54 + 126 * ((t * FPS / (2.4 * FPS)) % 1))
    ripple_a = 1 - ((t / 2.4) % 1)
    cv2.circle(img, (960, 540), ripple_r, tuple(int(v * ripple_a) for v in RED), 2, cv2.LINE_AA)
    def ring(layer, amount):
        for i in range(8):
            a = t * math.tau / 14 + i * math.tau / 8
            x, y = int(960 + math.cos(a) * 126), int(540 + math.sin(a) * 126)
            cv2.circle(layer, (x, y), 5 if i % 2 else 6, WHITE, -1, cv2.LINE_AA)
    glow(img, ring, blur=16)
    def core(layer, amount):
        r = int(31 + 12 * (0.5 + .5 * math.sin(t * math.tau / 2)))
        cv2.circle(layer, (960, 540), r, RED, -1, cv2.LINE_AA)
    glow(img, core, blur=24)
    return img


def render_08(t):
    img = canvas()
    overlay = img.copy()
    cv2.fillConvexPoly(overlay, np.array([[960, 240], [1250, 850], [670, 850]], np.int32), (220, 220, 220), cv2.LINE_AA)
    cv2.addWeighted(overlay, .08, img, .92, 0, img)
    xoff = int(-90 + 180 * (.5 - .5 * math.cos(t * math.tau / 4)))
    cv2.line(img, (785 + xoff, 240), (1135 + xoff, 240), (95, 95, 95), 2, cv2.LINE_AA)
    cv2.line(img, (925 + xoff, 240), (995 + xoff, 240), WHITE, 8, cv2.LINE_AA)
    def details(layer, amount):
        cv2.circle(layer, (960, 240), 12, WHITE, -1, cv2.LINE_AA)
        cv2.circle(layer, (920, 710), 18, WHITE, -1, cv2.LINE_AA)
        cv2.circle(layer, (1000, 710), 10, (205, 209, 217), -1, cv2.LINE_AA)
        pr = int(15 + 40 * ((t / 2) % 1)); pa = 1 - ((t / 2) % 1)
        cv2.circle(layer, (920, 710), pr, tuple(int(c * pa) for c in WHITE), 2, cv2.LINE_AA)
        pulse = .65 + .35 * math.sin(t * math.tau / 1.5)
        for i in range(7):
            x = 780 + i * 60
            cv2.circle(layer, (x, 890), 5, tuple(int(c * pulse) for c in WHITE), -1, cv2.LINE_AA)
    glow(img, details, blur=18)
    return img


def camera_move_ref(img, t, name):
    p=(t/8.0)%1
    if name.startswith("06_"):
        zoom=1+.13*(.5-.5*math.cos(math.tau*p)); dx=65*math.sin(math.tau*p); dy=-85*math.sin(math.pi*p); angle=0
    elif name.startswith("07_"):
        zoom=1.12-.12*(.5-.5*math.cos(math.tau*p)); dx=0; dy=0; angle=3*math.sin(math.tau*p)
    else:
        zoom=1+.18*(.5-.5*math.cos(math.tau*p)); dx=-100*math.sin(math.tau*p); dy=25*math.cos(math.tau*p); angle=-1.5*math.sin(math.tau*p)
    matrix=cv2.getRotationMatrix2D((W/2,H/2),angle,zoom)
    matrix[0,2]+=dx; matrix[1,2]+=dy
    return cv2.warpAffine(img,matrix,(W,H),flags=cv2.INTER_LINEAR,borderMode=cv2.BORDER_REFLECT)


RENDERERS = {"06_device_to_orbital_core": render_06, "07_red_orbital_pulse": render_07, "08_spotlight_signal_scan": render_08}


def main():
    RENDERS.mkdir(parents=True, exist_ok=True)
    PACK.mkdir(parents=True, exist_ok=True)
    for name, render_frame in RENDERERS.items():
        target = RENDERS / f"{name}.mp4"
        encoder = cv2.VideoWriter(str(target), cv2.VideoWriter_fourcc(*"mp4v"), FPS, (W, H))
        if not encoder.isOpened():
            raise RuntimeError(f"Could not open video writer for {target}")
        try:
            for frame in range(FRAMES):
                image=camera_move_ref(render_frame(frame/FPS),frame/FPS,name)
                encoder.write(np.clip(image.astype(np.float32)+GRAIN,0,255).astype(np.uint8))
        finally:
            encoder.release()
        # Re-encode to broadly compatible H.264 and mirror into the shared pack.
        h264 = target.with_name(target.stem + "_h264.mp4")
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(target), "-an", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "17", "-preset", "fast", "-movflags", "+faststart", str(h264)], check=True)
        target.unlink()
        h264.rename(target)
        shutil.copy2(target, PACK / target.name)
        print(f"Rendered {target.name}: {target.stat().st_size:,} bytes", flush=True)


if __name__ == "__main__":
    main()
