#!/usr/bin/env python3
"""render_typewriter_modern.py

Revives the retired Typewriter important-phrase family as fully authored
``chronon.render-plan.v3`` documents:

- a *modern* face: ``Inter-ExtraBold.ttf`` (the retired family used
  Montserrat-Bold);
- a *carino* glow: the native ``style.glow`` on the text and on the caret.
  Layer ``effects: bloom`` is avoided: it silently drops the layer on the
  Vulkan *video* sink (the caret vanished from every mp4 chunk while still
  rendering into single-frame PNGs), so both glow surfaces use style.glow;
- typing through the engine's GPU text contract: ONE reveal animator per run
  (selector window sweeping the typing frontier with the standard
  ``property(t) * weight(glyph, t)`` folding) plus, for the lift recipe, a
  second animator whose traveling band lifts each glyph during the hold.

The amber caret is an ordinary shape layer with its own tracks, so it stays
editable by the consuming tool.

Recipes (one plan per recipe):
  typewriter_modern_type           hard type-on (square window), caret glides
  typewriter_modern_cursor_blink   same typing + caret keeps blinking after
  typewriter_modern_soft_fade      per-glyph soft fade (RampDown reveal sweep)
  typewriter_modern_lift           hard type-on + slow lift wave through the
                                   glyphs during the hold

Render pipeline (the verified one on this host):
  chronon3d_cli --backend vulkan --video-sink raw --pipe-pixfmt yuv420p
  in bounded chunks, every chunk frame-scanned and re-rendered (up to
  --max-attempts) until clean, encoded per chunk with ``h264_nvenc`` and
  losslessly concatenated.

Usage:
  python tools/important_phrases/render_typewriter_modern.py               # emit plans only
  python tools/important_phrases/render_typewriter_modern.py --render      # GPU render all
  ... --recipe typewriter_modern_soft_fade                                  # one recipe only
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]          # .../ChrononTemplate
WORKSPACE = ROOT.parent                              # assets root
OUT_ROOT = ROOT / "out" / "typewriter_modern_v1"

WIDTH, HEIGHT = 1920, 1080
FPS = 30
DUR = 180                                            # generous reading hold
FONT_REL = "ChrononTemplate/assets/fonts/Inter-ExtraBold.ttf"
TEXT_WIDTH_TARGET = 1320.0
TEXT_MAX_FONT = 170.0
CENTER = (WIDTH / 2.0, HEIGHT / 2.0)

BG = [0.023, 0.035, 0.055, 1.0]                      # deep blue-black
INK = "#ECF3FA"
CARET = "#FFB454"                                    # amber caret
GLOW = {"radius": 10.0, "intensity": 0.28, "color": "#FFFFFF"}
CARET_GLOW = {"radius": 14.0, "intensity": 0.35, "color": "#FFB454"}
CHUNK = 60

RECIPE_DEFS = {
    "typewriter_modern_type": {
        "phrase": "IDEAS TYPE THEMSELVES.",
        "reveal": "square",        # hard glyph pop-on
        "caret": "glide",          # caret glides, stays solid
    },
    "typewriter_modern_cursor_blink": {
        "phrase": "BUILT FRAME BY FRAME.",
        "reveal": "square",
        "caret": "blink",          # caret keeps blinking after the type-on
    },
    "typewriter_modern_soft_fade": {
        "phrase": "EVERY LETTER, IN ORDER.",
        "reveal": "ramp_up",       # soft dissolve ahead of the frontier
        "caret": "glide",
    },
    "typewriter_modern_lift": {
        "phrase": "MOTION IS A LANGUAGE.",
        "reveal": "square",
        "caret": "glide",
        "lift": True,              # slow lift wave during the hold
    },
}


def hex_rgba(hex_color: str) -> list[float]:
    value = hex_color.lstrip("#")
    return [int(value[i:i + 2], 16) / 255.0 for i in (0, 2, 4)] + [1.0]


def track(prop: str, keyframes: list[dict]) -> dict:
    return {"property": prop, "easing": "linear", "keyframes": keyframes}


def kfs(pairs: list[tuple[int, float]]) -> list[dict]:
    return [{"frame": f, "value": v} for f, v in pairs]


def measure_phrase(phrase: str) -> float:
    """Font size that fits TEXT_WIDTH_TARGET, measured with PIL at tracking 0."""
    from PIL import ImageFont
    font_path = WORKSPACE / FONT_REL
    if not font_path.is_file():
        raise SystemExit(f"font missing: {font_path}")
    probe = 160
    font = ImageFont.truetype(str(font_path), probe)
    advance = font.getlength(phrase)
    if advance <= 0:
        raise SystemExit(f"cannot measure {phrase!r}")
    return min(TEXT_MAX_FONT, probe * (TEXT_WIDTH_TARGET / advance))


def glyph_starts(phrase: str, size: float) -> list[float]:
    """Cumulative start offsets [px] of each glyph."""
    from PIL import ImageFont
    font = ImageFont.truetype(str(WORKSPACE / FONT_REL), int(size))
    starts: list[float] = []
    x = 0.0
    for index in range(len(phrase)):
        starts.append(x)
        x += font.getlength(phrase[index])
    return starts


def typing_schedule(phrase: str) -> tuple[float, float]:
    """(type_start, type_end) frames at ~2.2 frames per character."""
    type_start = 12.0
    return type_start, type_start + len(phrase) * 2.2


# ── layers ────────────────────────────────────────────────────────────────────

def background_layer() -> dict:
    return {
        "id": "bg",
        "type": "shape",
        "size": [WIDTH, HEIGHT],
        "position": [WIDTH / 2.0, HEIGHT / 2.0],
        "start_frame": 0,
        "duration_frames": DUR,
        "shape": {"type": "rect", "fill": BG},
    }


def phrase_layer(layer_id: str, phrase: str, size: float) -> dict:
    return {
        "id": layer_id,
        "type": "text",
        "text": phrase,
        "size": [int(WIDTH * 0.97), int(size * 2.2)],
        "position": list(CENTER),
        "start_frame": 0,
        "duration_frames": DUR,
        "enable_3d": False,
        "style": {"font": FONT_REL, "font_size": size, "fill": INK,
                  "glow": dict(GLOW)},
        "spans": [{"start": 0, "end": len(phrase.encode("utf-8")),
                   "style": {"tracking": 0.0}}],
    }


def caret_layer(size: float) -> dict:
    caret_h = size * 0.86
    return {
        "id": "caret",
        "type": "shape",
        "size": [9.0, caret_h],
        "position": [CENTER[0], CENTER[1]],
        "start_frame": 0,
        "duration_frames": DUR,
        "enable_3d": False,
        "shape": {"type": "rect", "fill": hex_rgba(CARET)},
        "style": {"glow": dict(CARET_GLOW)},
    }


# ── animation authoring ──────────────────────────────────────────────────────

def reveal_animator(reveal: str, type_start: float, type_end: float) -> dict:
    """The typing window.

    Selector start/end are authored on the engine's *percent* scale (0-100 =
    the glyph run; the evaluator multiplies by 0.01 and clamps to [0, 1]).

    The shader folds the animator as ``opacity = 1 + (value - 1) * weight``,
    so a constant ``opacity: 1`` makes the reveal a NO-OP (verified: identical
    pixels at every frame). The working contract is therefore:

    - ``opacity`` property pinned to 0 → a glyph at weight w renders at
      ``1 - w``;
    - the window covers the *unrevealed tail*: ``start`` sweeps 0 → 100 while
      ``end`` rests at 100. Not-yet-typed glyphs sit inside the window
      (weight 1, hidden), typed glyphs fall out on the left (weight 0, solid).

    square: hard pop-on at the frontier (the whole tail sits inside the
    window at weight 1, so it snaps off/on cleanly — verified pixel-by-pixel).

    ramp_up soft fade: a moving window chases the frontier
    (start = frontier - width, end = frontier). Measured on this engine:

    - an *empty* window (start >= end) evaluates to weight 0 for every glyph
      → with opacity 0 the whole phrase is fully visible (frame-0 leak);
    - weight for ramp_up is 1 *after* end, ramps 1→0 across the window and 0
      before start, so a glyph is hidden while past the frontier, fades in as
      the window sweeps over it, and rests visible once the window moved on.

    Pre-typing the window is therefore ajar (start 0, end 0.5) so every glyph
    sits after `end` at weight 1 = hidden; at rest both edges reach 100 →
    empty window → weight 0 → fully visible."""
    if reveal not in ("square", "ramp_up"):
        raise ValueError(reveal)
    span = type_end - type_start
    if reveal == "square":
        start_kf = [(0, 0.0), (int(type_start), 0.0),
                    (int(type_end) + 1, 100.0), (DUR, 100.0)]
        end_kf = [(0, 100.0), (DUR, 100.0)]
    else:
        width = 14.0                                  # fade tail, in percent
        rate = 99.5 / span                            # percent per frame
        catch = width / rate                          # frames to close the tail
        start_kf = [(0, 0.0), (int(type_start), 0.0),
                    (int(type_end), 100.0 - width),
                    (int(type_end + catch), 100.0), (DUR, 100.0)]
        end_kf = [(0, 0.5), (int(type_start), 0.5),
                  (int(type_end), 100.0), (DUR, 100.0)]
    return {
        "selectors": [{
            "unit": "glyph",
            "shape": reveal,
            "order": "forward",
            "start": {"keyframes": kfs(start_kf)},
            "end": {"keyframes": kfs(end_kf)},
        }],
        "properties": [track("opacity", kfs([(0, 0.0), (DUR, 0.0)]))],
    }


def lift_animator(type_start: float, type_end: float) -> dict:
    """A slow life wave during the hold: a narrow band travels once through
    the run (percent scale). A glyph rises only while the band passes it,
    then settles — nothing is moved permanently."""
    wave_start = type_end + 10.0
    wave_end = wave_start + 90.0
    width = 24.0

    def band(frame: int) -> float:
        t = min(1.0, max(0.0, (frame - wave_start) / (wave_end - wave_start)))
        return -30.0 + t * 160.0

    front = [(0, -30.0 - width), (DUR, -30.0 - width)]
    back = [(0, -30.0 - width), (DUR, -30.0 - width)]
    step = 5
    for frame in range(int(wave_start), DUR + 1, step):
        if frame > wave_end:
            break
        front.append((frame, band(frame)))
        back.append((frame, band(frame) - width))
    return {
        "selectors": [{
            "unit": "glyph",
            "shape": "smooth",
            "order": "forward",
            "start": {"keyframes": kfs(back)},
            "end": {"keyframes": kfs(front)},
        }],
        "properties": [track("position_y", kfs([(0, -12.0), (DUR, -12.0)]))],
    }


def caret_tracks(mode: str, phrase: str, starts: list[float], total: float,
                 type_start: float, type_end: float) -> list[dict]:
    """The caret glides with the frontier and (blink mode) keeps blinking
    after the type-on finishes.

    Layer position tracks are authored as offsets from the *canvas centre*
    (the compiler subtracts canvas_width/2 from the layer position and adds
    each keyframe on top), so every x here is an offset, not an absolute
    screen coordinate."""
    left = CENTER[0] - total / 2.0
    n = len(phrase)
    x_keys: list[tuple[int, float]] = []
    span = type_end - type_start
    for frame in range(0, DUR, 2):
        progress = (frame - type_start) / span
        d = max(0.0, min(float(n), progress * n))
        k = min(n, int(d))
        absolute = left + (starts[k] if k < n else total)
        x_keys.append((frame, absolute - CENTER[0]))
    tracks = [track("position_x", kfs(x_keys))]

    if mode == "blink":
        opacity: list[tuple[int, float]] = [(0, 0.0), (int(type_start), 1.0),
                                            (int(type_end), 1.0)]
        frame = int(type_end) + 14
        on = False
        while frame + 20 < DUR:
            opacity.append((frame, 1.0 if on else 0.0))
            opacity.append((frame + 20, 1.0 if on else 0.0))
            on = not on
            frame += 34
        opacity.append((DUR, 1.0))
        tracks.append(track("opacity", kfs(opacity)))
    else:
        tracks.append(track("opacity", kfs([
            (0, 0.0), (int(type_start), 0.0),
            (int(type_start + 14.0), 1.0), (DUR, 1.0)])))
    return tracks


# ── plan assembly ────────────────────────────────────────────────────────────

def build_plan(recipe_name: str, recipe: dict, out_dir: Path) -> Path:
    phrase = recipe["phrase"]
    size = measure_phrase(phrase)
    from PIL import ImageFont
    font = ImageFont.truetype(str(WORKSPACE / FONT_REL), int(size))
    total = font.getlength(phrase)
    starts = glyph_starts(phrase, size)
    type_start, type_end = typing_schedule(phrase)

    base = phrase_layer("phrase", phrase, size)
    # the base layer is invisible; the typed copy carries every visible pixel
    base["animation"] = {"tracks": [track("opacity",
                                          kfs([(0, 0.0), (DUR, 0.0)]))]}

    typed = phrase_layer("phrase_typed", phrase, size)
    typed["text_animators"] = [reveal_animator(recipe["reveal"],
                                               type_start, type_end)]
    if recipe.get("lift"):
        typed["text_animators"].append(
            lift_animator(type_start, type_end))

    caret = caret_layer(size)
    caret["animation"] = {"tracks": caret_tracks(
        recipe.get("caret", "glide"), phrase, starts, total,
        type_start, type_end)}

    plan = {
        "schema": "chronon.render-plan.v3",
        "version": 3,
        "job_id": recipe_name,
        "canvas": {
            "width": WIDTH,
            "height": HEIGHT,
            "fps_num": FPS,
            "fps_den": 1,
            "duration_frames": DUR,
        },
        "layers": [background_layer(), base, caret, typed],
        "output": {
            "path": f"{recipe_name}.mp4",
            "format": "mp4",
            "codec": "h264",
        },
    }
    out_dir.mkdir(parents=True, exist_ok=True)
    plan_path = out_dir / f"{recipe_name}.plan.json"
    plan_path.write_text(json.dumps(plan, indent=2) + "\n", encoding="utf-8")
    return plan_path


# ── CLI + GPU pipeline ───────────────────────────────────────────────────────

def default_cli() -> Path:
    override = os.environ.get("CHRONON_CLI")
    if override:
        return Path(override)
    suffix = ".exe" if sys.platform.startswith("win") else ""
    build = WORKSPACE / "Chronon3d" / "build" / "chronon"
    candidates = sorted(build.glob(f"*/apps/chronon3d_cli/chronon3d_cli{suffix}"))
    if not candidates:
        raise SystemExit(f"chronon3d CLI not found under {build}; set CHRONON_CLI")
    return candidates[-1]


def scan_yuv(yuv: Path, plan_name: str, start: int) -> list[int]:
    """Frame indices carrying a glitch: a light/cream corner patch (surface
    backdrop loss onto a dark plate), or a centre board that lost the glowing
    text after the settle frame (legibility loss)."""
    from PIL import Image
    scan = yuv.with_suffix(".scan")
    scan.mkdir(exist_ok=True)
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "rawvideo",
                    "-pix_fmt", "yuv420p", "-s", f"{WIDTH}x{HEIGHT}",
                    "-r", str(FPS), "-i", str(yuv), "-vf", "scale=480:270",
                    str(scan / "f%05d.png")], check=True, cwd=WORKSPACE)
    bad: list[int] = []
    for index, path in enumerate(sorted(scan.glob("f*.png"))):
        im = Image.open(path).convert("RGB")
        w, h = im.size
        corners = [im.getpixel((3, 3)), im.getpixel((w - 4, 3)),
                   im.getpixel((3, h - 4)), im.getpixel((w - 4, h - 4))]
        # the plate is intentionally dark: a bright corner is a glitch patch
        lit = sum(1 for c in corners if sum(c) > 320)
        if lit >= 2:
            bad.append(index)
            continue
        if start + index >= 150:
            band = [im.getpixel((x, h // 2)) for x in range(96, 384, 8)]
            bright = sum(1 for px in band if sum(px) > 360)
            if bright < 4:
                bad.append(index)
    for path in scan.glob("*.png"):
        path.unlink()
    scan.rmdir()
    return bad


def render_plan(cli: Path, plan_path: Path, video: Path, max_attempts: int) -> None:
    plan_name = plan_path.stem
    scratch = video.parent / (video.stem + "_chunks")
    scratch.mkdir(parents=True, exist_ok=True)
    parts: list[Path] = []
    for start in range(0, DUR, CHUNK):
        end = min(start + CHUNK - 1, DUR - 1)
        part = scratch / f"part_{start:05d}.mp4"
        parts.append(part)
        for attempt in range(1, max_attempts + 1):
            yuv = part.with_suffix(".yuv")
            cmd = [str(cli), "render", "--backend", "vulkan",
                   "--plan", str(plan_path), "--assets-root", str(WORKSPACE),
                   "-o", str(yuv), "--video-sink", "raw",
                   "--pipe-pixfmt", "yuv420p",
                   "--start-frame", str(start), "--end-frame", str(end)]
            log = part.with_suffix(".log")
            print(f"[chunk] {plan_name} frames {start}-{end} "
                  f"attempt {attempt}", flush=True)
            t0 = time.monotonic()
            with open(log, "w") as handle:
                subprocess.run(cmd, check=True, cwd=WORKSPACE,
                               stdout=handle, stderr=subprocess.STDOUT)
            bad = scan_yuv(yuv, plan_name, start)
            if not bad:
                break
            yuv.unlink()
            print(f"[chunk] bad frames {bad[:8]}, re-rendering", flush=True)
        else:
            raise SystemExit(f"{plan_name}: chunk {start}-{end} stayed dirty "
                             f"after {max_attempts} attempts")
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "rawvideo",
                        "-pix_fmt", "yuv420p", "-s", f"{WIDTH}x{HEIGHT}",
                        "-r", str(FPS), "-i", str(yuv),
                        "-c:v", "h264_nvenc", str(part)], check=True,
                       cwd=WORKSPACE)
        yuv.unlink()
        print(f"[chunk] {end - start + 1} frames in "
              f"{time.monotonic() - t0:.1f}s", flush=True)
    listing = scratch / "concat.txt"
    listing.write_text("\n".join(f"file '{p.as_posix()}'" for p in parts) + "\n",
                       encoding="utf-8")
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0",
                    "-i", str(listing), "-c", "copy", str(video)],
                   check=True, cwd=WORKSPACE)
    listing.unlink()
    shutil.rmtree(scratch, ignore_errors=True)


def make_previews(video: Path) -> Path:
    """One contact sheet with five frames: mid-typing, late-typing, settled
    and hold frames, 640x360 pieces in a 5x1 tile."""
    sheet = video.parent / f"{video.stem}_contact_sheet.png"
    frames = [46, 66, 96, 150, 178]
    # select=46+66+… is a *constant* expression (always true → the tile picks
    # the first five frames, which are blank); each frame needs eq(n,X).
    select = "+".join(f"eq(n\,{f})" for f in frames)
    subprocess.run(
        ["ffmpeg", "-y", "-v", "error", "-i", str(video),
         "-vf", f"select={select},scale=640:360,tile=5x1",
         "-frames:v", "1", str(sheet)], check=True, cwd=WORKSPACE)
    return sheet


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--render", action="store_true",
                        help="validate and render with the Chronon3D CLI")
    parser.add_argument("--recipe", action="append", default=None,
                        help="emit/render only this recipe (repeatable)")
    parser.add_argument("--max-attempts", type=int, default=5)
    parser.add_argument("--cli", type=Path, default=None)
    args = parser.parse_args()

    wanted = args.recipe or list(RECIPE_DEFS)
    unknown = [name for name in wanted if name not in RECIPE_DEFS]
    if unknown:
        raise SystemExit(f"unknown recipes: {unknown}; known: {list(RECIPE_DEFS)}")

    plans_dir = OUT_ROOT / "plans"
    plan_paths: dict[str, Path] = {}
    for name in wanted:
        plan_paths[name] = build_plan(name, RECIPE_DEFS[name], plans_dir)
        print(f"Wrote {plan_paths[name]}")

    if not args.render:
        return 0

    cli = (args.cli or default_cli()).resolve()
    for name, plan_path in plan_paths.items():
        subprocess.run([str(cli), "validate", "--plan", str(plan_path),
                        "--assets-root", str(WORKSPACE)], check=True,
                       cwd=WORKSPACE)
        video = OUT_ROOT / f"{name}.mp4"
        render_plan(cli, plan_path, video, args.max_attempts)
        sheet = make_previews(video)
        print(f"Rendered {video}; previews: {sheet}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
