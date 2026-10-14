#!/usr/bin/env python3
"""Phrase Camera V3 - fix dello zoom 4x + animazioni VISIBILI.

ROOT CAUSE V2: testo rasterizzato a 2x su plate 3840x2160 MA il campionatore
affine ingrandisce di 2x gia' a z=1 (finestra 960x540 -> 1920x1080).
Risultato: testo a 4x (frase croppata, kicker/sub fuori frame).

FIX: UN SOLO spazio coordinate. Plate bg/dust/testo tutti a PS=1.5x
(2880x1620), layout testo in coordinate plate = centro + (out-centro)*PS.
A z=1 l'ingrandimento netto e' 1x: quello che disegni e' quello che vedi.

Ampiezze V3 (visibili ma eleganti): drift 60px, track +-120px,
push fino 1.15x, pedestal 60px, zoom-out da 1.15. FOV 40 costante,
nessuno shake/bounce/glow/motion-blur, nessun int() nel path camera,
dither animato +-1.2 LSB anti-banding.

Out: out/phrase_camera_v2/<id>.mp4 (sovrascrive V2) + poses + meta + png.
"""
import json
import math
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from ChrononTemplate.tools.backgrounds.documentary_background_v2 import (
    base_dark_graphite,
    dust_overlay,
    soft_vignette_overlay,
)

W, H, FPS = 1920, 1080, 30
FOV_DEG = 40.0
FOCAL = (H / 2) / math.tan(math.radians(FOV_DEG) / 2)
ORBIT_DIST = 2500.0
OUT = ROOT / "out" / "phrase_camera_v2"
OUT.mkdir(parents=True, exist_ok=True)
FONTS = ROOT / "ChrononTemplate" / "assets" / "fonts"
FB, FR = str(FONTS / "Play-Bold.ttf"), str(FONTS / "Play-Regular.ttf")

PS = 1.5  # UNICA scala plate per bg, dust E testo
WP, HP = int(W * PS * 1.25), int(H * PS * 1.25)  # margine plate oltre la finestra camera
CXP, CYP = WP / 2, HP / 2


def X(x):
    return CXP + (x - W / 2) * PS


def Y(y):
    return CYP + (y - H / 2) * PS


def S(s):
    return s * PS


def smoother(x):
    x = min(1.0, max(0.0, x))
    return x * x * x * (x * (x * 6 - 15) + 10)


def ease_in_out(x):
    x = min(1.0, max(0.0, x))
    return 0.5 - 0.5 * math.cos(math.pi * x)


def ease_out(x):
    x = min(1.0, max(0.0, x))
    return 1 - (1 - x) ** 3


def build_plates():
    bg = base_dark_graphite(11).convert("RGBA").resize((WP, HP), Image.BILINEAR)
    bg.alpha_composite(soft_vignette_overlay(WP, HP, 0.14, 16))
    return bg.convert("RGB"), dust_overlay(WP, HP, 18, n=60)


BG, DUST = build_plates()

SCENES = [
    ("phrase_camera_diagonal_drift", "Everything Changed.", 5, "05 - DIAGONAL DRIFT", None),
    ("phrase_camera_crane_down", "The Road Ahead.", 4, "06 - CRANE DOWN", None),
    ("phrase_camera_track_right", "No Way Back.", 4, "07 - TRACK RIGHT", None),
    ("phrase_camera_orbit_return", "A Second Chance.", 4, "08 - ORBIT RETURN", None),
    ("phrase_camera_push_combo", "The Turning Point.", 5, "09 - PUSH COMBO", None),
    ("phrase_camera_tilt_rise", "Rising Above It All.", 4, "10 - TILT RISE", None),
    ("phrase_camera_zoom_out", "The Full Picture.", 4, "11 - ZOOM OUT", None),
    ("phrase_camera_diagonal_up", "Against The Current.", 5, "12 - DIAGONAL UP", None),
    ("phrase_camera_focus_settle", "The Hard Evidence.", 3, "13 - FOCUS SETTLE", None),
    ("phrase_camera_pedestal_push", "Higher Stakes.", 4, "14 - PEDESTAL PUSH", None),
    ("phrase_camera_lateral_settle", "Back To Center.", 3, "15 - LATERAL SETTLE", None),
    ("phrase_camera_depth_parallax", "Layers Of Truth.", 5, "16 - DEPTH PARALLAX", None),
    ("phrase_camera_arc_drift", "The Long Way Home.", 5, "17 - ARC DRIFT", None),
    ("phrase_camera_breathe", "Still Waters.", 5, "18 - BREATHE", None),
    ("phrase_camera_descend", "What Lies Beneath.", 4, "19 - DESCEND", None),
    ("phrase_camera_rise_reveal", "A New Dawn.", 4, "20 - RISE REVEAL", None),
]


def camera_state(rid, f, n):
    t = f / (n - 1)
    S_ = {"dust_pan": 1.4, "dust_zoom_k": 1.8}
    if rid == "phrase_camera_diagonal_drift":
        e = smoother(t)
        return {"transform": "diagonal_drift", "scale": 1.00 + 0.06 * e,
                "off": [60.0 * (1 - e), 60.0 * (1 - e)], "yaw": 0.0, "blur": 0.0, **S_}
    if rid == "phrase_camera_crane_down":
        e = smoother(t)
        return {"transform": "crane_down", "scale": 1.00 + 0.05 * e,
                "off": [0.0, 80.0 * (1 - e)], "yaw": 0.0, "blur": 0.0, **S_}
    if rid == "phrase_camera_track_right":
        e = ease_in_out(t)
        return {"transform": "lateral_track", "scale": 1.0,
                "off": [-120.0 + 240.0 * e, 0.0], "yaw": 0.0, "blur": 0.0, **S_}
    if rid == "phrase_camera_orbit_return":
        e = ease_in_out(t)
        return {"transform": "orbit_yaw", "scale": 1.0,
                "off": [0.0, 0.0], "yaw": 2.0 - 4.0 * e, "blur": 0.0, **S_}
    if rid == "phrase_camera_push_combo":
        e = smoother(t)
        return {"transform": "dolly+lateral", "scale": 1.00 + 0.12 * e,
                "off": [-60.0 + 120.0 * e, 0.0], "yaw": 0.0, "blur": 0.0, **S_}
    if rid == "phrase_camera_tilt_rise":
        e = smoother(t)
        return {"transform": "tilt_rise", "scale": 1.00 + 0.07 * e,
                "off": [0.0, -90.0 * (1 - e)], "yaw": 0.0, "blur": 0.0, **S_}
    if rid == "phrase_camera_zoom_out":
        e = smoother(t)
        return {"transform": "dolly_out", "scale": 1.15 - 0.15 * e,
                "off": [0.0, 0.0], "yaw": 0.0, "blur": 0.0, **S_}
    if rid == "phrase_camera_diagonal_up":
        e = smoother(t)
        return {"transform": "diagonal_drift", "scale": 1.00 + 0.06 * e,
                "off": [70.0 * (1 - e), -70.0 * (1 - e)], "yaw": 0.0, "blur": 0.0, **S_}
    if rid == "phrase_camera_focus_settle":
        e = ease_out(t)
        return {"transform": "dolly+defocus_compositing", "scale": 1.08 - 0.08 * e,
                "off": [0.0, 0.0], "yaw": 0.0, "blur": 2.5 * (1 - e), **S_}
    if rid == "phrase_camera_pedestal_push":
        e = smoother(t)
        return {"transform": "pedestal_push", "scale": 1.00 + 0.12 * e,
                "off": [0.0, -60.0 + 70.0 * e], "yaw": 0.0, "blur": 0.0, **S_}
    if rid == "phrase_camera_lateral_settle":
        e = ease_out(t)
        return {"transform": "lateral_track", "scale": 1.0,
                "off": [120.0 * (1 - e), 0.0], "yaw": 0.0, "blur": 0.0, **S_}
    if rid == "phrase_camera_depth_parallax":
        e = smoother(t)
        d = dict(S_)
        d.update({"dust_pan": 2.2, "dust_zoom_k": 2.5})
        return {"transform": "dolly", "scale": 1.00 + 0.08 * e,
                "off": [0.0, 0.0], "yaw": 0.0, "blur": 0.0, **d}
    if rid == "phrase_camera_arc_drift":
        return {"transform": "arc_drift", "scale": 1.00 + 0.05 * smoother(t),
                "off": [-60.0 + 120.0 * t, 25.0 * math.sin(math.pi * t)],
                "yaw": 0.0, "blur": 0.0, **S_}
    if rid == "phrase_camera_breathe":
        e = smoother(t)
        return {"transform": "dolly", "scale": 1.00 + 0.04 * e,
                "off": [0.0, 0.0], "yaw": 0.0, "blur": 0.0, **S_}
    if rid == "phrase_camera_descend":
        e = ease_out(t)
        return {"transform": "descend", "scale": 1.08 - 0.08 * e,
                "off": [0.0, 80.0 * (1 - e)], "yaw": 0.0, "blur": 0.0, **S_}
    if rid == "phrase_camera_rise_reveal":
        e = smoother(t)
        return {"transform": "tilt_rise", "scale": 1.00 + 0.07 * e,
                "off": [0.0, -90.0 * (1 - e)], "yaw": 0.0, "blur": 0.0, **S_}
    raise ValueError(rid)


def affine_sample(plate, z, ox, oy):
    """Float, UNICO spazio coordinate: plate px per output px = PS/z (1:1 a z=1)."""
    k = PS / z
    a = k
    c = WP / 2 + (ox - W / 2) * k
    f_ = HP / 2 + (oy - H / 2) * k
    return plate.transform((W, H), Image.AFFINE, (a, 0.0, c, 0.0, a, f_),
                           resample=Image.BILINEAR)


def orbit_warp(img, yaw_deg):
    if abs(yaw_deg) < 1e-9:
        return img
    th = math.radians(yaw_deg)
    cx = W / 2
    du = np.arange(W, dtype=np.float64) - cx
    denom = FOCAL * math.cos(th) + du * math.sin(th)
    xs = du * ORBIT_DIST / denom
    src = xs / ORBIT_DIST * FOCAL + cx
    arr = np.asarray(img)
    x0 = np.floor(src).astype(int)
    frac = (src - x0).astype(np.float32)
    x0c = np.clip(x0, 0, W - 1)
    x1c = np.clip(x0 + 1, 0, W - 1)
    w = frac[None, :, None]
    out = (arr[:, x0c].astype(np.float32) * (1 - w)
           + arr[:, x1c].astype(np.float32) * w).astype(np.uint8)
    valid = (src >= 0) & (src < W)
    if arr.shape[2] == 4:
        out[:, ~valid, 3] = 0
    return Image.fromarray(out, mode="RGBA")


def build_text_plate(phrase, kicker, sub):
    """Layout in coordinate plate X()/Y()/S(): a z=1 esce 1:1 in output."""
    plate = Image.new("RGBA", (WP, HP), (0, 0, 0, 0))
    d = ImageDraw.Draw(plate)
    fk = ImageFont.truetype(FB, int(30 * PS))
    size = 104
    while size > 85:
        ff = ImageFont.truetype(FB, int(size * PS))
        bb = d.textbbox((0, 0), phrase, font=ff)
        if (WP - (bb[2] - bb[0])) / PS / 2 >= 150:
            break
        size -= 2
    ff = ImageFont.truetype(FB, int(size * PS))
    ink, mut = (245, 243, 238, 255), (200, 200, 205, 255)
    kb = d.textbbox((0, 0), kicker, font=fk)
    kx = CXP - (kb[2] - kb[0]) / 2 - kb[0]
    d.text((kx, Y(240)), kicker, font=fk, fill=mut)
    bb = d.textbbox((0, 0), phrase, font=ff)
    twp, thp = bb[2] - bb[0], bb[3] - bb[1]
    px = CXP - twp / 2 - bb[0]
    py = Y(520) - thp / 2 - bb[1]
    d.text((px, py), phrase, font=ff, fill=ink)
    if sub:
        fs = ImageFont.truetype(FR, int(34 * PS))
        sb = d.textbbox((0, 0), sub, font=fs)
        d.text((CXP - (sb[2] - sb[0]) / 2 - sb[0], Y(640)), sub, font=fs, fill=mut)
    return plate, size, (twp / PS, thp / PS)


def render_scene(rid, phrase, dur_s, kicker, sub):
    n = dur_s * FPS
    text_plate, f_size, (tw, th) = build_text_plate(phrase, kicker, sub)
    dst = OUT / f"{rid}.mp4"
    cmd = ["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
           "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
           "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "20",
           "-preset", "veryfast", "-movflags", "+faststart", str(dst)]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    poses, prev, first_arr = [], None, None
    cdiffs, min_margin = [], 1e9
    rng = np.random.default_rng(1000 + len(rid))
    for f in range(n):
        st = camera_state(rid, f, n)
        ox, oy = st["off"]
        frame = affine_sample(BG, st["scale"], ox * 0.35, oy * 0.35).convert("RGBA")
        zd = 1 + (st["scale"] - 1) * st["dust_zoom_k"]
        frame.alpha_composite(affine_sample(DUST, zd, ox * st["dust_pan"], oy * st["dust_pan"]).convert("RGBA"))
        fg = affine_sample(text_plate, st["scale"], ox, oy)
        if st["yaw"]:
            fg = orbit_warp(fg, st["yaw"])
        if st["blur"] > 0.01:
            fg = fg.filter(ImageFilter.GaussianBlur(st["blur"]))
        frame = Image.alpha_composite(frame, fg)
        arr = np.asarray(frame.convert("RGB"), dtype=np.float32)
        arr += rng.normal(0, 1.2, (H, W, 1)).astype(np.float32)
        arr = np.clip(arr, 0, 255)
        if prev is not None:
            cdiffs.append(float(np.abs(arr - prev).mean()))
        if first_arr is None:
            first_arr = arr.copy()
        prev = arr
        proc.stdin.write(arr.astype(np.uint8).tobytes())
        hw, hh = tw * st["scale"] / 2, th * st["scale"] / 2
        top = min(205.0, 520 - hh)
        bot = max(700.0 if sub else 520 + hh, 520 + hh)
        bbox = [W / 2 - ox - hw, top - oy, W / 2 - ox + hw, bot - oy]
        min_margin = min(min_margin, min(bbox[0], bbox[1], W - bbox[2], H - bbox[3]))
        poses.append({"frame": f, "t_s": round(f / FPS, 3),
                      "transform": st["transform"], "scale": round(st["scale"], 4),
                      "off": [round(ox, 2), round(oy, 2)], "yaw": round(st["yaw"], 3),
                      "blur": round(st["blur"], 3), "fov_deg": FOV_DEG})
        if f in (0, n // 2, n - 1):
            frame.convert("RGB").save(OUT / f"{rid}_{'first' if f == 0 else 'mid' if f == n // 2 else 'last'}.png")
    proc.stdin.close()
    proc.wait()
    ok = proc.returncode == 0
    mid = cdiffs[len(cdiffs) // 10:-len(cdiffs) // 10 or None]
    cmin, cmax = min(cdiffs), max(cdiffs)
    mmean = sum(mid) / len(mid)
    first_last = float(np.abs(prev - first_arr).mean())
    smooth_ok = (max(mid) / max(mmean, 1e-6)) < 8.0 and first_last > 1.0
    ok = ok and smooth_ok
    cmean = sum(cdiffs) / len(cdiffs)
    meta = {"id": rid, "phrase": phrase, "font_px": f_size, "fov_deg": FOV_DEG,
            "frames": n, "duration_s": dur_s, "min_margin_px": round(min_margin, 1),
            "cdiff_min": round(cmin, 3), "cdiff_max": round(cmax, 3),
            "cdiff_mean": round(cmean, 3), "first_last": round(first_last, 2),
            "file": f"{rid}.mp4"}
    (OUT / f"{rid}.poses.json").write_text(json.dumps(poses))
    (OUT / f"{rid}.meta.json").write_text(json.dumps(meta, indent=1))
    print(("ok " if ok else "FAIL ") + f"{rid}.mp4 cdiff {cmin:.2f}/{cmean:.2f}/{cmax:.2f} f-l={first_last:.1f}"
          + ("" if smooth_ok else " JUDDER"), flush=True)
    return ok, meta


if __name__ == "__main__":
    only = sys.argv[1:]
    metas, bad = [], []
    for rid, phrase, dur, kick, sub in SCENES:
        if only and rid not in only and rid.replace("phrase_camera_", "") not in only:
            continue
        ok, meta = render_scene(rid, phrase, dur, kick, sub)
        (metas if ok else bad).append(meta if ok else rid)
    (OUT / "VALIDATION.json").write_text(json.dumps(metas, indent=1))
    sys.exit(1 if bad else 0)
