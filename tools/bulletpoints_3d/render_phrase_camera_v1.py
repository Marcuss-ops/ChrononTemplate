#!/usr/bin/env python3
"""Phrase Camera V1 — 5 animazioni camera cinematografiche per singola frase.

Regole rigide: nessuno shake/bounce/glow/motion-blur, FOV costante 40 deg,
frase 85-120px con safe margin >= 120px, rotazione max +-2 deg, zoom 4-12%.
Ogni scena dichiara la trasformazione reale usata (dolly / lateral_track /
orbit_yaw / dolly+defocus / diagonal_drift): mai uno zoom 2D spacciato per 3D.

Programma camera canonico simulato:
  dolly/lateral/drift = crop window su plate oversize (camera-plane vera),
  orbit_yaw           = warp prospettico pinhole reale a FOV costante,
  defocus             = blur dal compositing (non dalla camera).

Out: out/phrase_camera_v1/<file>.mp4 + pose json + bbox json +
     first/mid/last png + VALIDATION.json
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
    base_editorial_ivory,
    dust_overlay,
    soft_vignette_overlay,
)

W, H, FPS = 1920, 1080, 30
FOV_DEG = 40.0
FOCAL = (H / 2) / math.tan(math.radians(FOV_DEG) / 2)  # ~1484 px, costante
ORBIT_DIST = 2500.0  # distanza piano testuale, costante
OUT = ROOT / "out" / "phrase_camera_v1"
OUT.mkdir(parents=True, exist_ok=True)
FONTS = ROOT / "ChrononTemplate" / "assets" / "fonts"
FB, FR = str(FONTS / "Play-Bold.ttf"), str(FONTS / "Play-Regular.ttf")

ANTHRACITE_SEED, IVORY_SEED = 11, 44
OW, OH = 2400, 1350  # plate oversize per crop camera-plane
BASE_S = 1.15  # scala crop base (margine per dolly 0.94x)

# id, frase, durata, sub
SCENES = [
    ("phrase_camera_slow_push", "The Hidden Truth.", 4, None, "01 \u00b7 SLOW PUSH"),
    ("phrase_camera_side_reveal", "Nothing Was Accidental.", 3, None, "02 \u00b7 SIDE REVEAL"),
    ("phrase_camera_micro_orbit", "A New Beginning.", 4, "CINEMATIC TYPOGRAPHY", "03 \u00b7 MICRO ORBIT"),
    ("phrase_camera_focus_push", "The Final Decision.", 3, None, "04 \u00b7 FOCUS PUSH"),
    ("phrase_camera_diagonal_drift", "Everything Changed.", 5, None, "05 \u00b7 DIAGONAL DRIFT"),
]


def smoother(x):
    x = min(1.0, max(0.0, x))
    return x * x * x * (x * (x * 6 - 15) + 10)


def ease_in_out(x):
    x = min(1.0, max(0.0, x))
    return 0.5 - 0.5 * math.cos(math.pi * x)


def ease_out(x):
    x = min(1.0, max(0.0, x))
    return 1 - (1 - x) ** 3


def build_bg(ivory=False):
    if ivory:
        bg = base_editorial_ivory(IVORY_SEED).convert("RGBA").resize((OW, OH), Image.BILINEAR)
        dust = dust_overlay(OW, OH, 207, n=30)
    else:
        bg = base_dark_graphite(ANTHRACITE_SEED).convert("RGBA").resize((OW, OH), Image.BILINEAR)
        bg.alpha_composite(soft_vignette_overlay(OW, OH, 0.14, 16))
        dust = dust_overlay(OW, OH, 18, n=40)
    return bg.convert("RGB"), dust


BG_DARK, DUST_DARK = build_bg(False)
BG_IVORY, DUST_IVORY = build_bg(True)

F_KICK = ImageFont.truetype(FB, 30)
F_SUB = ImageFont.truetype(FR, 34)


def fit_font(draw, text, target=104, lo=85, hi=120):
    """Riduci il font finche' i margini laterali sono >= 140px (safe 120 + tol)."""
    size = min(hi, max(lo, target))
    while size > lo:
        f = ImageFont.truetype(FB, size)
        bb = draw.textbbox((0, 0), text, font=f)
        if (W - (bb[2] - bb[0])) / 2 >= 140:
            return f, size
        size -= 2
    f = ImageFont.truetype(FB, lo)
    return f, lo


def camera_state(rid, f, n):
    """Ritorna dict con la posa campionabile + trasformazione dichiarata."""
    t = f / (n - 1)
    if rid == "phrase_camera_slow_push":
        e = smoother(t)
        return {"transform": "dolly", "scale": 1.00 + 0.12 * e,
                "off": [0.0, 0.0], "yaw": 0.0, "blur": 0.0, "easing": "smootherstep"}
    if rid == "phrase_camera_side_reveal":
        e = ease_in_out(t)
        return {"transform": "lateral_track", "scale": 1.0,
                "off": [115.0 * (1 - e), 0.0], "yaw": 0.0, "blur": 0.0,
                "easing": "ease_in_out_sine"}
    if rid == "phrase_camera_micro_orbit":
        e = ease_in_out(t)
        return {"transform": "orbit_yaw", "scale": 1.0,
                "off": [0.0, 0.0], "yaw": -2.0 + 4.0 * e, "blur": 0.0,
                "easing": "ease_in_out_sine"}
    if rid == "phrase_camera_focus_push":
        e = ease_out(t)
        return {"transform": "dolly+defocus_compositing", "scale": 0.94 + 0.06 * e,
                "off": [0.0, 0.0], "yaw": 0.0, "blur": 2.0 * (1 - e),
                "easing": "ease_out_cubic"}
    if rid == "phrase_camera_diagonal_drift":
        e = smoother(t)
        return {"transform": "diagonal_drift", "scale": 1.00 + 0.04 * e,
                "off": [20.0 * (1 - e), 20.0 * (1 - e)], "yaw": 0.0, "blur": 0.0,
                "easing": "smootherstep"}
    raise ValueError(rid)


def crop_plane(plate, scale, off, par=1.0):
    s = BASE_S * scale
    ww, hh = OW / s, OH / s
    x0 = min(max(0.0, (OW - ww) / 2 + off[0] * par), OW - ww)
    y0 = min(max(0.0, (OH - hh) / 2 + off[1] * par), OH - hh)
    return plate.crop((int(x0), int(y0), int(x0 + ww), int(y0 + hh))).resize((W, H), Image.BILINEAR)


def orbit_warp(img, yaw_deg):
    """Warp prospettico pinhole reale: piano ruotato di yaw attorno a Y, FOV fisso.
    Mappa per-colonne u(X) = cx + f*X*cos/(D - X*sin), ricampionata vettorialmente."""
    if abs(yaw_deg) < 1e-9:
        return img
    th = math.radians(yaw_deg)
    cx = W / 2
    a = np.arange(W, dtype=np.float64) - cx  # coordinate camera desiderate
    # coordinate mondo X che proiettano su ciascuna colonna: inverti u(X)
    # u = cx + f*X*cos/(D - X*sin) -> X = (u-cx)*D / (f*cos + (u-cx)*sin)
    du = a
    denom = FOCAL * math.cos(th) + du * math.sin(th)
    xs = du * ORBIT_DIST / denom  # mondo, origine al centro del piano
    src = (xs / ORBIT_DIST * FOCAL + cx)  # colonna sorgente sul piano frontale
    arr = np.asarray(img)
    x0 = np.floor(src).astype(int)
    frac = (src - x0).astype(np.float32)
    x0c = np.clip(x0, 0, W - 1)
    x1c = np.clip(x0 + 1, 0, W - 1)
    w = frac[None, :, None] if arr.ndim == 3 else frac[None, :]
    left = arr[:, x0c]
    right = arr[:, x1c]
    out = (left * (1 - w) + right * w).astype(np.uint8)
    # maschera fuori-piano (sorgente fuori frame) -> trasparente se RGBA
    valid = (src >= 0) & (src < W)
    if arr.shape[2] == 4:
        out[:, ~valid, 3] = 0
    return Image.fromarray(out, mode="RGBA" if arr.shape[2] == 4 else "RGB")


def render_scene(rid, phrase, dur_s, sub, kicker):
    n = dur_s * FPS
    ivory = rid == "phrase_camera_focus_push"
    bg_plate, dust_plate = (BG_IVORY, DUST_IVORY) if ivory else (BG_DARK, DUST_DARK)
    ink = (30, 30, 32) if ivory else (245, 243, 238)
    mut = (90, 88, 84) if ivory else (200, 200, 205)

    probe = Image.new("RGBA", (W, H))
    f_font, f_size = fit_font(ImageDraw.Draw(probe), phrase)
    bb = ImageDraw.Draw(probe).textbbox((0, 0), phrase, font=f_font)
    tw, th = bb[2] - bb[0], bb[3] - bb[1]
    tx, ty = (W - tw) / 2 - bb[0], (H - th) / 2 - bb[1] - 20

    dst = OUT / f"{rid}.mp4"
    cmd = ["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
           "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
           "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "20",
           "-preset", "veryfast", "-movflags", "+faststart", str(dst)]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    poses, min_margin, bboxes = [], 1e9, {}
    for f in range(n):
        st = camera_state(rid, f, n)
        frame = crop_plane(bg_plate, st["scale"], st["off"]).convert("RGBA")
        frame.alpha_composite(crop_plane(dust_plate, st["scale"], st["off"]).convert("RGBA"))
        fg = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(fg)
        kb = d.textbbox((0, 0), kicker, font=F_KICK)
        d.text(((W - (kb[2] - kb[0])) / 2, 150), kicker, font=F_KICK,
               fill=mut + (255,))
        # frase: scala apparente attorno al centro + offset camera (mondo statico)
        pw, ph = int(tw * st["scale"]), int(th * st["scale"])
        txt = Image.new("RGBA", (tw + 40, th + 40), (0, 0, 0, 0))
        ImageDraw.Draw(txt).text((20 - bb[0], 20 - bb[1]), phrase, font=f_font,
                                 fill=ink + (255,))
        if st["blur"] > 0.01:
            txt = txt.filter(ImageFilter.GaussianBlur(st["blur"]))
        txt = txt.resize((pw + int(40 * st["scale"]), ph + int(40 * st["scale"])), Image.BILINEAR)
        if rid == "phrase_camera_micro_orbit":
            # la frase resta un piano: e' la camera a orbitare (warp = posa camera)
            warp_src = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            warp_src.alpha_composite(txt, (int(tx + tw / 2 - txt.width / 2),
                                           int(ty + th / 2 - txt.height / 2)))
            fg = Image.alpha_composite(fg, orbit_warp(warp_src, st["yaw"]))
            corners = [(-tw / 2, -th / 2), (tw / 2, -th / 2),
                       (tw / 2, th / 2), (-tw / 2, th / 2)]
            th2 = math.radians(st["yaw"])
            proj = [(W / 2 + FOCAL * (x * math.cos(th2)) / (ORBIT_DIST - x * math.sin(th2)),
                     H / 2 - 20 + y) for x, y in corners]
            xs = [p[0] for p in proj]
            bbox = [min(xs), H / 2 - 20 - th / 2, max(xs), H / 2 - 20 + th / 2]
        else:
            cx_, cy_ = tx + tw / 2 - st["off"][0], ty + th / 2 - 20 - st["off"][1]
            # nota: offset sottratto = camera che si muove, mondo fermo
            fg.alpha_composite(txt, (int(cx_ - txt.width / 2), int(cy_ - txt.height / 2 + 20)))
            bbox = [cx_ - pw / 2, cy_ - ph / 2, cx_ + pw / 2, cy_ + ph / 2]
        if sub:
            sb = d.textbbox((0, 0), sub, font=F_SUB)
            fg_text = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            ImageDraw.Draw(fg_text).text(((W - (sb[2] - sb[0])) / 2, ty + th + 60),
                                         sub, font=F_SUB, fill=mut + (255,))
            fg = Image.alpha_composite(fg, fg_text)
            bbox[3] = max(bbox[3], ty + th + 60 + (sb[3] - sb[1]))
        frame = Image.alpha_composite(frame, fg)
        margin = min(bbox[0], bbox[1], W - bbox[2], H - bbox[3])
        min_margin = min(min_margin, margin)
        poses.append({"frame": f, "t_s": round(f / FPS, 3), **{k: (round(v, 3) if isinstance(v, float) else v) for k, v in st.items()},
                      "fov_deg": FOV_DEG,
                      "crop_window": [int(OW / (BASE_S * st["scale"])), int(OH / (BASE_S * st["scale"]))]})
        if f in (0, n // 2, n - 1):
            frame.convert("RGB").save(OUT / f"{rid}_{'first' if f == 0 else 'mid' if f == n // 2 else 'last'}.png")
            if f == n // 2:
                bboxes["mid_bbox"] = [round(v, 1) for v in bbox]
        proc.stdin.write(frame.convert("RGB").tobytes())
    proc.stdin.close()
    proc.wait()
    ok = proc.returncode == 0
    meta = {"id": rid, "phrase": phrase, "font_px": f_size, "fov_deg": FOV_DEG,
            "frames": n, "duration_s": dur_s, "min_margin_px": round(min_margin, 1),
            "bbox": bboxes, "file": f"{rid}.mp4"}
    (OUT / f"{rid}.poses.json").write_text(json.dumps(poses))
    (OUT / f"{rid}.meta.json").write_text(json.dumps(meta, indent=1))
    print(("ok " if ok else "FAIL ") + f"{rid}.mp4 margin={min_margin:.0f}px font={f_size}px", flush=True)
    return ok, meta


if __name__ == "__main__":
    only = sys.argv[1:]
    metas, bad = [], []
    for rid, phrase, dur, sub, kick in SCENES:
        if only and rid not in only and rid.replace("phrase_camera_", "") not in only:
            continue
        ok, meta = render_scene(rid, phrase, dur, sub, kick)
        (metas if ok else bad).append(meta if ok else rid)
    (OUT / "VALIDATION.json").write_text(json.dumps(metas, indent=1))
    sys.exit(1 if bad else 0)
