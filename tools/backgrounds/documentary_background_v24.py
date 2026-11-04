#!/usr/bin/env python3
"""V24 — true internal animation for documentary backgrounds.

Camera LOCKED (no pan/crop of a static PNG). Every preset animates its own
material per-frame, deterministically (seed + frame index):

- 01 dark film grain .... live grain, new gaussian every frame
- 02 dark paper ......... live grain + slow breathing light
- 03 archival film ...... live grain + exposure flicker + scratch flicker + dust twinkle
- 04 deep navy .......... live grain + slow drifting ambient glow
- 05 warm documentary ... live grain + drifting warm pool
- 06 editorial ivory .... fine live grain + faint breathing (almost still, alive)
- 07 soft vignette ...... live grain + breathing vignette strength
- 08 matte charcoal ..... live grain only
- 09 film scratches ..... live grain + scratches that flicker/appear per frame
- 10 blurred backdrop ... live grain + bokeh blobs that slowly drift
- 11 newspaper paper .... live grain + breathing
- 12 faint lines ........ live grain + breathing (lines stay, editorial)
- 13 floating dust ...... live grain + 45 motes with velocity drift + twinkle (REAL float)
- 14 muted olive ........ live grain + drifting pool
- 15 soft light sweep ... live grain + diffuse pool that SWEEPS across frame

Only numpy+PIL. Static bases reused from documentary_background_v2 (baked
texture counts as static material); live components added per frame.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import subprocess
import sys
import zlib
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).parent))
from documentary_background_v2 import (
    build_v2, base_dark_graphite, _tint, _with,
    soft_vignette_overlay, diffuse_light_pool,
    value_noise_fbm,
)

W, H = 1920, 1080
FPS = 30
DUR = 8.0
FRAMES = 240

# normalized coordinate grids, precomputed once (float32)
_yy, _xx = np.mgrid[0:H, 0:W].astype(np.float32)
_NX = _xx / W
_NY = _yy / H

IDS = ["01_dark_film_grain", "02_dark_paper", "03_archival_film",
       "04_deep_navy_gradient", "05_warm_documentary", "06_editorial_ivory",
       "07_soft_vignette", "08_matte_charcoal", "09_subtle_film_scratches",
       "10_blurred_backdrop", "11_newspaper_paper", "12_faint_horizontal_lines",
       "13_floating_dust", "14_muted_olive", "15_soft_light_sweep"]

GRAIN_SIGMA = {
    "01_dark_film_grain": 3.0, "02_dark_paper": 2.6, "03_archival_film": 2.8,
    "04_deep_navy_gradient": 2.0, "05_warm_documentary": 2.2,
    "06_editorial_ivory": 2.0, "07_soft_vignette": 2.0, "08_matte_charcoal": 2.2,
    "09_subtle_film_scratches": 2.2, "10_blurred_backdrop": 2.0,
    "11_newspaper_paper": 2.2, "12_faint_horizontal_lines": 2.2,
    "13_floating_dust": 2.2, "14_muted_olive": 2.1, "15_soft_light_sweep": 2.0,
}


def _stable_seed(preset_id: str) -> int:
    """Stable per-preset seed. Python's hash() is randomized per process."""
    return zlib.crc32(preset_id.encode("utf-8")) & 0xFFFFFFFF


# ------------------------------------------------------------ static bases
def get_static(pid: str) -> np.ndarray:
    """Static material as float32 HxWx3. No live grain inside."""
    if pid == "13_floating_dust":
        # graphite tinted, WITHOUT baked dust (dust is animated)
        im = _tint(base_dark_graphite(131), (20, 22, 27))
        return np.asarray(im.convert("RGB"), dtype=np.float32)
    if pid == "09_subtle_film_scratches":
        im = base_dark_graphite(91)
        return np.asarray(im.convert("RGB"), dtype=np.float32)
    if pid == "03_archival_film":
        # warm dark base + pool + vignette, WITHOUT baked scratches/dust
        base = np.zeros((H, W, 3), np.float32)
        base[:, :] = (20, 17, 13)
        base += value_noise_fbm(W, H, 88, 4, 7)[:, :, None] * np.array(
            [2.6, 2.2, 1.8], np.float32)
        im = Image.fromarray(np.clip(base, 0, 255).astype(np.uint8)).convert("RGBA")
        im.alpha_composite(diffuse_light_pool(W, H, (70, 50, 32), 0.08,
                                              cxr=0.5, cyr=0.5, spread=1.3))
        im.alpha_composite(soft_vignette_overlay(W, H, 0.14, 93))
        return np.asarray(im.convert("RGB"), dtype=np.float32)
    im = build_v2(pid)
    return np.asarray(im.convert("RGB"), dtype=np.float32)


# ------------------------------------------------------------ animated assets
def dust_params(seed: int, n: int = 45):
    rng = np.random.default_rng(seed)
    out = []
    for _ in range(n):
        out.append(dict(
            x0=rng.uniform(60, W - 60), y0=rng.uniform(60, H - 60),
            vx=rng.uniform(-16, 16), vy=rng.uniform(-11, 7),
            r=rng.uniform(1.6, 7.0),
            a=rng.uniform(30, 85),
            f=rng.uniform(0.15, 0.6), ph=rng.uniform(0, 2 * math.pi),
        ))
    return out


def scratch_masks(seed: int, xs: list):
    """Return list of (x, [(y0,y1),...]) segments."""
    rng = np.random.default_rng(seed)
    out = []
    for sx in xs:
        segs = []
        y = float(rng.uniform(0, 120))
        while y < H:
            seg = float(rng.uniform(30, 160))
            gap = float(rng.uniform(60, 260))
            segs.append((y, min(H, y + seg)))
            y += seg + gap
        out.append((sx, segs))
    return out


def _add_dust(base: np.ndarray, motes, t: float):
    """Splat gaussian motes with drift + twinkle. In-place add."""
    for m in motes:
        x = (m["x0"] + m["vx"] * t - 40) % (W + 80) - 40
        y = (m["y0"] + m["vy"] * t - 40) % (H + 80) - 40
        tw = 0.55 + 0.45 * math.sin(2 * math.pi * m["f"] * t + m["ph"])
        amp = m["a"] * tw
        r = m["r"]
        rad = int(math.ceil(r * 3))
        x0, y0 = int(round(x)), int(round(y))
        x1a, x1b = max(0, x0 - rad), min(W, x0 + rad + 1)
        y1a, y1b = max(0, y0 - rad), min(H, y0 + rad + 1)
        if x1b <= x1a or y1b <= y1a:
            continue
        gy = np.arange(y1a, y1b, dtype=np.float32) - y
        gx = np.arange(x1a, x1b, dtype=np.float32) - x
        gyy, gxx = np.meshgrid(gy, gx, indexing="ij")
        g = np.exp(-(gxx ** 2 + gyy ** 2) / (2 * (r / 1.6) ** 2)).astype(np.float32)
        base[y1a:y1b, x1a:x1b] += (g * amp)[:, :, None]


def _add_scratches(base: np.ndarray, masks, t: float, seed: int):
    """Scratches flicker: per-frame random alpha scale + +-1px jitter."""
    rng = np.random.default_rng(seed + int(round(t * FPS)) * 131)
    for sx, segs in masks:
        vis = rng.uniform(0.35, 1.0)  # some frames faint, some visible
        dx = int(rng.integers(-1, 2))
        x = min(W - 1, max(0, sx + dx))
        for y0, y1 in segs:
            if rng.random() < 0.12:
                continue  # segment blinks out this frame
            a = 22.0 * vis
            base[int(y0):int(y1), x] += a


def _radial(base: np.ndarray, cxr: float, cyr: float, rx: float, ry: float,
            color: tuple, strength: float):
    d2 = ((_NX - cxr) / (rx / W)) ** 2 + ((_NY - cyr) / (ry / H)) ** 2
    m = np.clip(1.0 - np.sqrt(d2), 0, 1).astype(np.float32)
    m = m * m * (3 - 2 * m)  # smoothstep-ish
    m *= strength
    col = np.array(color, np.float32)[None, None, :]
    base += m[:, :, None] * col


# per-preset animated asset caches
_ASSETS: dict = {}


def get_assets(pid: str):
    if pid in _ASSETS:
        return _ASSETS[pid]
    a: dict = {}
    if pid == "13_floating_dust":
        a["motes"] = dust_params(1313, 45)
    elif pid == "03_archival_film":
        a["masks"] = scratch_masks(886, [612, 1188])
        a["motes"] = dust_params(887, 14)
    elif pid == "09_subtle_film_scratches":
        a["masks"] = scratch_masks(909, [560, 1080, 1540])
    elif pid == "07_soft_vignette":
        v = np.asarray(soft_vignette_overlay(W, H, 1.0, 707).split()[3],
                       dtype=np.float32) / 255.0
        a["vig"] = v
    elif pid == "10_blurred_backdrop":
        a["blobs"] = [
            dict(fx=0.22, fy=0.30, r=300, col=(10, 7, 5), ax=26, ay=14, f=1 / 8, ph=0.0),
            dict(fx=0.78, fy=0.68, r=340, col=(5, 8, 7), ax=-22, ay=12, f=1 / 8, ph=1.7),
            dict(fx=0.51, fy=0.48, r=260, col=(7, 7, 10), ax=18, ay=-12, f=1 / 8, ph=3.4),
            dict(fx=0.62, fy=0.25, r=150, col=(9, 10, 14), ax=-14, ay=10, f=1 / 8, ph=5.0),
        ]
    _ASSETS[pid] = a
    return a


# ------------------------------------------------------------ per-frame render
def _live_grain(rng: np.random.Generator, sigma: float) -> np.ndarray:
    """Per-frame grain at half res, upscaled: temporally alive but
    spatially correlated 2x2 so H.264 -tune grain can keep it at sane
    bitrates (full-res white grain costs ~40MB/8s, half-res ~8MB)."""
    half = rng.normal(0, sigma * 1.15, (H // 2, W // 2)).astype(np.float32)
    return np.asarray(Image.fromarray(half).resize((W, H), Image.BILINEAR),
                      dtype=np.float32)


def render_frame(pid: str, idx: int, static: np.ndarray, assets: dict) -> np.ndarray:
    """Return uint8 HxWx3 frame. Deterministic in idx."""
    t = idx / FPS
    rng = np.random.default_rng((1000 + idx * 7919 + _stable_seed(pid)) & 0xFFFFFFFF)
    base = static.copy()
    sigma = GRAIN_SIGMA[pid]

    if pid == "01_dark_film_grain":
        base += _live_grain(rng, sigma)[:, :, None]
    elif pid == "02_dark_paper":
        base += _live_grain(rng, sigma)[:, :, None]
        base += math.sin(2 * math.pi * t / DUR) * 1.6
    elif pid == "03_archival_film":
        base += _live_grain(rng, sigma)[:, :, None]
        base += rng.normal(0, 1.6)  # exposure flicker, global
        _add_scratches(base, assets["masks"], t, 886)
        _add_dust(base, assets["motes"], t)
    elif pid == "04_deep_navy_gradient":
        base += _live_grain(rng, sigma)[:, :, None]
        cx = 0.78 + 0.022 * math.sin(2 * math.pi * t / DUR)
        cy = 0.22 + 0.014 * math.cos(2 * math.pi * t / DUR)
        _radial(base, cx, cy, W * 0.9, H * 0.95, (5, 10, 18), 0.55)
    elif pid == "05_warm_documentary":
        base += _live_grain(rng, sigma)[:, :, None]
        cx = 0.5 + 0.03 * math.sin(2 * math.pi * t / DUR)
        cy = 0.45 + 0.02 * math.cos(2 * math.pi * t / DUR)
        _radial(base, cx, cy, W * 0.8, H * 0.85, (9, 6, 3.4), 0.6)
    elif pid == "06_editorial_ivory":
        base += _live_grain(rng, sigma)[:, :, None]
        base += math.sin(2 * math.pi * t / DUR) * 1.0
    elif pid == "07_soft_vignette":
        base += _live_grain(rng, sigma)[:, :, None]
        s = 0.10 + 0.025 * math.sin(2 * math.pi * t / DUR)
        base -= (assets["vig"] * 255 * s)[:, :, None] * np.array([1, 1, 1.1], np.float32)
    elif pid == "08_matte_charcoal":
        base += _live_grain(rng, sigma)[:, :, None]
    elif pid == "09_subtle_film_scratches":
        base += _live_grain(rng, sigma)[:, :, None]
        _add_scratches(base, assets["masks"], t, 909)
    elif pid == "10_blurred_backdrop":
        base += _live_grain(rng, sigma)[:, :, None]
        for b in assets["blobs"]:
            cx = b["fx"] + (b["ax"] / W) * math.sin(2 * math.pi * b["f"] * t + b["ph"])
            cy = b["fy"] + (b["ay"] / H) * math.sin(2 * math.pi * b["f"] * t + b["ph"] + 1.0)
            _radial(base, cx, cy, b["r"] * 2.2, b["r"] * 2.2, b["col"], 0.5)
    elif pid == "11_newspaper_paper":
        base += _live_grain(rng, sigma)[:, :, None]
        base += math.sin(2 * math.pi * t / DUR) * 1.2
    elif pid == "12_faint_horizontal_lines":
        base += _live_grain(rng, sigma)[:, :, None]
        base += math.sin(2 * math.pi * t / DUR) * 1.2
    elif pid == "13_floating_dust":
        base += _live_grain(rng, sigma)[:, :, None]
        base += math.sin(2 * math.pi * t / DUR) * 1.5
        _add_dust(base, assets["motes"], t)
    elif pid == "14_muted_olive":
        base += _live_grain(rng, sigma)[:, :, None]
        cx = 0.5 + 0.025 * math.sin(2 * math.pi * t / DUR + 1.0)
        _radial(base, cx, 0.45, W * 0.85, H * 0.9, (6, 7, 5), 0.5)
    elif pid == "15_soft_light_sweep":
        base += _live_grain(rng, sigma)[:, :, None]
        cx = 0.35 + 0.30 * (t / DUR)  # true sweep left->right over 8s
        _radial(base, cx, 0.40, W * 1.1, H * 1.2, (26, 25, 23), 0.5)
    else:
        raise ValueError(pid)

    return np.clip(base, 0, 255).astype(np.uint8)


# ------------------------------------------------------------ prototype CLI
def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _render_prototype(preset_id: str, out_dir: Path, frames: int, fps: int) -> dict:
    """Render one prototype as a bounded rawvideo -> ffmpeg stream.

    Only one 1920x1080 RGB frame is materialized at a time; six thumbnails are
    retained for the contact sheet. This is the OOM-safe path for the host.
    """
    global FPS, DUR
    FPS = fps
    DUR = frames / float(fps)
    static = get_static(preset_id)
    assets = get_assets(preset_id)
    video = out_dir / f"{preset_id}_v2.mp4"
    contact = out_dir / f"{preset_id}_v2_contact.jpg"
    sample_at = {round(i * (frames - 1) / 5) for i in range(6)} if frames > 1 else {0}
    thumbnails: list[Image.Image] = []
    command = [
        "ffmpeg", "-y", "-nostats", "-loglevel", "error",
        "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
        "-r", str(fps), "-i", "-", "-an", "-c:v", "libx264",
        "-preset", "veryfast", "-crf", "18", "-pix_fmt", "yuv420p",
        "-movflags", "+faststart", str(video),
    ]
    process = subprocess.Popen(
        command, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
    )
    written = 0
    try:
        for idx in range(frames):
            frame = render_frame(preset_id, idx, static, assets)
            if idx in sample_at:
                thumbnails.append(
                    Image.fromarray(frame).resize((480, 270), Image.LANCZOS)
                )
            try:
                process.stdin.write(frame.tobytes())
            except BrokenPipeError:
                break
            written += 1
        try:
            process.stdin.close()
        except BrokenPipeError:
            pass
        stderr = process.stderr.read().decode("utf-8", "replace")
        rc = process.wait()
    finally:
        if process.poll() is None:
            process.kill()
            process.wait()
    if rc != 0:
        raise RuntimeError(f"ffmpeg failed for {preset_id} (rc={rc}): {stderr.strip()}")
    if written != frames:
        raise RuntimeError(f"{preset_id}: wrote {written}/{frames} frames; ffmpeg: {stderr.strip()}")

    columns, rows = 2, 3
    sheet = Image.new("RGB", (columns * 480, rows * 270), (0, 0, 0))
    for i, thumb in enumerate(thumbnails[: columns * rows]):
        sheet.paste(thumb, ((i % columns) * 480, (i // columns) * 270))
    sheet.save(contact, quality=90)

    return {
        "preset": preset_id,
        "version": "2.0",
        "video": str(video),
        "contact_sheet": str(contact),
        "width": W,
        "height": H,
        "fps": fps,
        "frames": frames,
        "duration_seconds": frames / float(fps),
        "seed": _stable_seed(preset_id),
        "size_bytes": video.stat().st_size,
        "sha256": _sha256_file(video),
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate the documentary background 2.0 prototypes (bounded memory)."
    )
    parser.add_argument(
        "--out-dir", type=Path,
        default=Path(__file__).resolve().parents[2] / "out" / "docbg_v2",
    )
    parser.add_argument("--preset", action="append", choices=IDS)
    parser.add_argument("--all", action="store_true", help="render all 15 presets")
    parser.add_argument("--frames", type=int, default=FRAMES)
    parser.add_argument("--fps", type=int, default=FPS)
    parser.add_argument("--report", type=Path)
    parser.add_argument("--seed", type=int, default=12045,
                        help="recorded project seed; per-preset seeds stay stable")
    args = parser.parse_args()
    if args.frames <= 0 or args.fps <= 0:
        parser.error("--frames and --fps must be positive")

    requested = set(IDS) if args.all else set(
        args.preset or ["01_dark_film_grain", "06_editorial_ivory", "03_archival_film"]
    )
    selected = [preset for preset in IDS if preset in requested]
    if not selected:
        parser.error("no known preset selected")

    out_dir = args.out_dir.resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    entries = []
    for preset_id in selected:
        print(f"[docbg] {preset_id}: {args.frames} frame @ {args.fps} fps -> {out_dir}", flush=True)
        entry = _render_prototype(preset_id, out_dir, args.frames, args.fps)
        entries.append(entry)
        print(
            f"[docbg] {preset_id}: {entry['size_bytes']} byte, "
            f"sha256={entry['sha256'][:16]}", flush=True,
        )

    report = {
        "schema": "chronontemplate.docbg_v2.prototypes.v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "generator": str(Path(__file__).resolve()),
        "width": W,
        "height": H,
        "fps": args.fps,
        "frames": args.frames,
        "duration_seconds": args.frames / float(args.fps),
        "seed": args.seed,
        "notes": (
            "Prototipi 2.0 per la review visiva; non sostituiscono il contratto "
            "procedural_documentary_v2 (7 background + 10 highlight)."
        ),
        "entries": entries,
    }
    report_path = (args.report or (out_dir / "report.json")).resolve()
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"[docbg] report: {report_path}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
