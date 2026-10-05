#!/usr/bin/env python3
"""Create 43 deterministic five-second background-only Chronon videos.

The 43 source PNG/CSV artifacts referenced in the analysis were not attached to
this checkout. These are original reference-inspired recreations from the
provided family descriptions, not pixel-verified copies of the missing frames.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import shutil
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont, ImageStat

TEMPLATE = Path(__file__).resolve().parents[1]
WORKSPACE = TEMPLATE.parent
CHRONON = WORKSPACE / "Chronon3d"
OUT_DEFAULT = TEMPLATE / "out/background_recreation_v2"
CLI_DEFAULT = CHRONON / "build/chronon/linux-video-fast-dev/apps/chronon3d_cli/chronon3d_cli"
UPLOADER_DEFAULT = WORKSPACE / "RenderingGen/bin/drive-upload"
CREDENTIALS_DEFAULT = WORKSPACE / "refactored/credentials.json"
TOKEN_DEFAULT = WORKSPACE / "refactored/token.json"
DRIVE_FOLDER_DEFAULT = "1a5_U3jc82Jl2CpgPgY4c41koZz5tVhdP"
WIDTH, HEIGHT, FPS, FRAMES = 1920, 1080, 30, 150

# One stable row per deliverable; each row is independent and deterministic.
WAVE_PALETTES = [
    ("08264A", "1269B0", "33D5E9", "B2FFF1"), ("102C24", "278861", "75E2A3", "E2FFD0"),
    ("301344", "8244A8", "E57DC2", "FFD5EB"), ("2A142C", "A33D65", "F29B78", "FFE2B7"),
    ("101A3B", "394FC2", "60BDF0", "E2F8FF"), ("3A210F", "A85A20", "F4B348", "FFF0B4"),
    ("191A20", "34363B", "66696A", "B7B8B0"), ("29213F", "6555A4", "A2A0EE", "EAE3FF"),
    ("082F38", "147F88", "65D6C4", "D7FFF3"), ("24202A", "54404F", "A47878", "F1D5C9"),
    ("171936", "493A9C", "9384EC", "F1D8FF"), ("312016", "91542F", "DC9A58", "FFE0A0"),
    ("171D2C", "364E73", "729AC3", "DCEBFF"), ("27132C", "843B85", "D46BBE", "F7D2F4"),
    ("183229", "3A7A52", "9DC77A", "E9E6B3"), ("1C1831", "4D3179", "BA73CB", "FFD2D8"),
]
NEON_PALETTES = [
    ("061326", "087FA5", "29DDF2"), ("050D2A", "124FE1", "7EDBFF"),
    ("061A17", "168B54", "A2FF8A"), ("160929", "7F24D1", "F03CBB"),
    ("071A17", "13A478", "75FFD2"), ("091227", "2448C8", "DC46C8"),
    ("100A2A", "6631C9", "E363EF"), ("21070D", "B21E31", "FF8A5D"),
]
CINEMATIC_PALETTES = [
    ("020306", "40120D", "E34C16", "FFD56A"), ("030304", "4B1C0A", "D57A18", "FFF0A0"),
    ("030206", "38101E", "B82B42", "FFB16B"), ("02050A", "102C4C", "3581AD", "E5F4FF"),
    ("040208", "351242", "A42A75", "FF9ACB"), ("030403", "24361D", "778342", "E9D89A"),
    ("020307", "261C32", "70617F", "F0E4D2"), ("030304", "38170C", "B7491A", "FFE29A"),
    ("030206", "39120F", "E03E24", "FFF0C4"), ("02030A", "151A46", "5B61C9", "D3DAFF"),
    ("050207", "3F1438", "D03A8A", "FFE0D5"), ("030504", "17362B", "4D9870", "D9E6B0"),
    ("020306", "442414", "B9672F", "F3C477"), ("040308", "30204D", "9D55B0", "FFE3C3"),
    ("020205", "3A0909", "B81C13", "FF9B35"), ("02050A", "103341", "36A0AA", "E1FFE7"),
    ("030304", "34291A", "987339", "FFF0B2"), ("030205", "32182C", "A84758", "FFD6A5"),
    ("020306", "30251D", "846044", "F1D4AE"),
]


def _rgb(value: str, alpha: float = 1.0) -> list[float]:
    return [int(value[i:i + 2], 16) / 255.0 for i in (0, 2, 4)] + [alpha]


def _linear(stops: list[tuple[float, str, float]], start=(0.5, 0.0), end=(0.5, 1.0)) -> dict:
    return {"type": "linear", "start": list(start), "end": list(end), "spread": "pad",
            "color_stops": [{"position": p, "color": _rgb(color, alpha)} for p, color, alpha in stops]}


def _radial(stops: list[tuple[float, str, float]]) -> dict:
    return {"type": "radial", "center": [0.5, 0.5], "radius": 0.5, "spread": "pad",
            "color_stops": [{"position": p, "color": _rgb(color, alpha)} for p, color, alpha in stops]}


def _layer(id_: str, shape: dict, size: tuple[float, float], position: tuple[float, float], *,
           blend: str = "screen", opacity: float = 1.0, drift: tuple[float, float] = (0.0, 0.0)) -> dict:
    dx, dy = drift
    animation = None
    if dx or dy:
        animation = {"tracks": [
            {"property": "position", "easing": "in_out_sine", "keyframes": [
                {"frame": 0, "value": [position[0], position[1]]},
                {"frame": 49, "value": [position[0] + dx * 2.0, position[1] + dy * 2.0]},
                {"frame": 99, "value": [position[0] - dx * 1.5, position[1] - dy * 1.5]},
                {"frame": FRAMES - 1, "value": [position[0], position[1]]},
            ]},
            {"property": "scale", "easing": "in_out_sine", "keyframes": [
                {"frame": 0, "value": [1.0, 1.0]},
                {"frame": 49, "value": [1.72, 1.72]},
                {"frame": 99, "value": [0.52, 0.52]},
                {"frame": FRAMES - 1, "value": [1.0, 1.0]},
            ]},
            {"property": "opacity", "easing": "in_out_sine", "keyframes": [
                {"frame": 0, "value": opacity * 0.42},
                {"frame": 49, "value": opacity * 1.65},
                {"frame": 99, "value": opacity * 0.24},
                {"frame": FRAMES - 1, "value": opacity * 0.42},
            ]},
        ]}
    item = {"id": id_, "type": "shape", "shape": shape, "size": list(size),
            "position": list(position), "start_frame": 0, "duration_frames": FRAMES,
            "blend_mode": blend, "opacity": opacity}
    if animation:
        item["animation"] = animation
    return item


def _path_ribbon(id_: str, y: float, width: float, color: str, alpha: float, phase: float,
                 drift: float, *, x_scale: float = 1.0) -> dict:
    # Closed cubic strip: an ordinary RenderPlan path, not a background-specific shader.
    amp = 30 + (int(phase * 100) % 47)
    left, right = -WIDTH * 0.12, WIDTH * 1.12
    top = y - width / 2
    bottom = y + width / 2
    commands = [
        {"type": "move_to", "point": [left, top]},
        {"type": "cubic_to", "control1": [WIDTH * .22, top - amp],
         "control2": [WIDTH * .72, top + amp], "point": [right, top]},
        {"type": "line_to", "point": [right, bottom]},
        {"type": "cubic_to", "control1": [WIDTH * .72, bottom + amp],
         "control2": [WIDTH * .22, bottom - amp], "point": [left, bottom]},
        {"type": "close"},
    ]
    fill = _linear([(0, color, 0), (.44, color, alpha), (.56, color, min(1.0, alpha * 1.35)), (1, color, 0)],
                   (0, 0), (1, 1))
    return _layer(id_, {"type": "path", "path": commands, "fill": fill},
                  (WIDTH, HEIGHT), (0, 0), blend="screen", drift=(0, drift))


def _recipe(kind: str, index: int, colors: tuple[str, ...]) -> tuple[str, list[dict]]:
    ident = f"{kind}_{index + 1:02d}"
    dark, mid, bright = colors[:3]
    hi = colors[-1]
    layers: list[dict] = [
        {"id": f"{ident}-base", "type": "color", "color": _rgb(dark),
         "start_frame": 0, "duration_frames": FRAMES},
        _layer(f"{ident}-atmosphere", {"type": "rect", "fill": _linear([
            (0, dark, 1), (.40, mid, .56), (.72, bright, .34), (1, dark, 1)],
            (0, 0), (1, 1))}, (WIDTH, HEIGHT), (WIDTH / 2, HEIGHT / 2), blend="screen", opacity=.8),
    ]
    if kind == "wave":
        # Repeated sculpted ribbons with alternating highlight/shadow bands.
        fold_count = 3 + index % 4
        palette = list(colors)
        for fold in range(fold_count):
            y = HEIGHT * (.20 + .60 * ((fold + .5) / fold_count))
            tint = palette[(fold + index) % len(palette)]
            alpha = .64 + .05 * ((fold + index) % 4)
            layers.append(_layer(f"{ident}-fold-{fold + 1:02d}",
                {"type": "ellipse", "fill": _radial([
                    (0, tint, alpha), (.24, tint, alpha * .76),
                    (.62, tint, alpha * .30), (1, tint, 0)])},
                (WIDTH * (.48 + .08 * (fold % 3)), HEIGHT * (.56 + .08 * ((fold + index) % 3))),
                (WIDTH * (.34 + .12 * (fold % 3)), y), blend="screen", opacity=.92,
                drift=((1 if fold % 2 else -1) * (270 + index % 6 * 25),
                       (1 if fold % 3 else -1) * (90 + (fold * 9) % 40))))
            # Soft overlapping blooms keep the layered wave feel without hard horizontal edges.
    elif kind == "neon":
        # Bright beam, wide halo and two soft colored emitters.
        y = HEIGHT * (.37 + .07 * (index % 4))
        halo = colors[1]
        layers.append(_layer(f"{ident}-wide-glow",
            {"type": "ellipse", "fill": _radial([(0, hi, .70), (.24, bright, .52),
                (.62, halo, .20), (1, dark, 0)])}, (WIDTH * 1.35, HEIGHT * .72),
            (WIDTH / 2, y), blend="screen", opacity=.76,
            drift=(310 if index % 2 else -310, 165 if index % 3 else -165)))
        for bulb, x in enumerate((WIDTH * (.28 + .12 * (index % 3)), WIDTH * (.70 - .08 * (index % 2)))):
            tint = colors[(bulb + 1) % len(colors)]
            layers.append(_layer(f"{ident}-glow-{bulb + 1}",
                {"type": "ellipse", "fill": _radial([(0, hi if bulb == 0 else bright, .82),
                    (.24, tint, .48), (.68, tint, .12), (1, dark, 0)])},
                (620 + 35 * index % 240, 460 + 28 * index % 200), (x, y),
                blend="screen", opacity=.82,
                drift=((320 if bulb == 0 else -320), (150 if bulb == 0 else -135))))
        if index in (3, 6):
            layers.append(_layer(f"{ident}-color-orbit",
                {"type": "ellipse", "fill": _radial([(0, hi, .64), (.22, bright, .42),
                    (.72, halo, .10), (1, dark, 0)])},
                (WIDTH * .72, HEIGHT * 1.08), (WIDTH * .5, HEIGHT * .48),
                blend="screen", opacity=.70, drift=(330, -160)))
    else:
        # Layered edge/corner burns and organic-looking broad light leaks.
        side = index % 4
        center = [(-.05, .43), (1.04, .57), (.48, -.08), (.60, 1.08)][side]
        size = (WIDTH * (1.08 + .08 * (index % 4)), HEIGHT * (1.20 + .11 * (index % 3)))
        layers.append(_layer(f"{ident}-burn",
            {"type": "ellipse", "fill": _radial([(0, hi, .76), (.19, bright, .68),
                (.48, mid, .40), (.78, colors[1], .18), (1, dark, 0)])},
            size, (center[0] * WIDTH, center[1] * HEIGHT), blend="screen", opacity=.85,
            drift=((index % 2 * 2 - 1) * (285 + index % 5 * 20), 150 - index % 7 * 30)))
        for bloom in range(2 + index % 3):
            y = HEIGHT * (.22 + bloom * (.56 / (1 + index % 3)))
            tint = colors[(bloom + 1) % len(colors)]
            layers.append(_layer(f"{ident}-light-leak-{bloom + 1}",
                {"type": "ellipse", "fill": _radial([(0, hi, .48), (.24, tint, .38),
                    (.70, mid, .16), (1, dark, 0)])},
                (WIDTH * (.82 + .08 * (bloom % 2)), HEIGHT * (.68 + .08 * ((index + bloom) % 3))),
                (WIDTH * (.30 + .37 * (bloom % 2)), y), blend="screen", opacity=.70,
                drift=((1 if bloom % 2 else -1) * (275 + (index % 5) * 22),
                       (1 if bloom % 2 else -1) * (135 + bloom * 25))))
        layers.append(_layer(f"{ident}-flare-core",
            {"type": "ellipse", "fill": _radial([(0, hi, .7), (.16, bright, .54),
                (.6, mid, .12), (1, dark, 0)])},
            (420 + (index % 4) * 110, 300 + (index % 3) * 120),
            (WIDTH * (.22 + .19 * (index % 4)), HEIGHT * (.24 + .25 * (index % 3))),
            blend="add", opacity=.82, drift=((1 if index % 2 else -1) * 310,
                                                (1 if index % 3 else -1) * 180)))
    return ident, layers


def recipes() -> list[tuple[str, list[dict]]]:
    items = []
    for i, colors in enumerate(WAVE_PALETTES):
        items.append(_recipe("wave", i, colors))
    for i, colors in enumerate(NEON_PALETTES):
        items.append(_recipe("neon", i, colors))
    for i, colors in enumerate(CINEMATIC_PALETTES):
        items.append(_recipe("cinematic", i, colors))
    return items


def make_plan(name: str, layers: list[dict], output: Path) -> dict:
    return {"schema": "chronon.render-plan.v3", "version": 3, "job_id": name,
            "canvas": {"width": WIDTH, "height": HEIGHT, "fps_num": FPS,
                       "fps_den": 1, "duration_frames": FRAMES},
            "output": {"path": str(output), "format": "mp4", "codec": "h264"},
            "layers": layers}


def _run(command: list[str]) -> str:
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode:
        raise RuntimeError(f"command failed ({result.returncode}): {' '.join(command)}\n{(result.stderr + result.stdout)[-5000:]}")
    return result.stdout + result.stderr


def validate_video(path: Path, ident: str) -> dict[str, Any]:
    if not path.is_file() or path.stat().st_size == 0:
        raise RuntimeError(f"missing/empty MP4: {path}")
    probe = json.loads(_run(["ffprobe", "-v", "error", "-select_streams", "v:0",
        "-count_frames", "-show_entries", "stream=codec_name,width,height,r_frame_rate,nb_read_frames,duration",
        "-of", "json", str(path)]))
    streams = probe.get("streams", [])
    if len(streams) != 1:
        raise RuntimeError(f"{ident}: expected one video stream, found {len(streams)}")
    stream = streams[0]
    expected = {"width": WIDTH, "height": HEIGHT, "r_frame_rate": f"{FPS}/1", "nb_read_frames": str(FRAMES)}
    for key, value in expected.items():
        if str(stream.get(key)) != str(value):
            raise RuntimeError(f"{ident}: expected {key}={value}, got {stream.get(key)}")
    duration = float(stream.get("duration", 0))
    if not 4.98 <= duration <= 5.02:
        raise RuntimeError(f"{ident}: expected 5.0s duration, got {duration}")
    motion = validate_motion(path, ident)
    return {"id": ident, "file": path.name, "bytes": path.stat().st_size,
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "width": WIDTH,
            "height": HEIGHT, "fps": FPS, "frames": FRAMES, "duration_seconds": duration,
            "codec": stream.get("codec_name"), "motion_adjacent_mean_luma": motion}


def validate_motion(path: Path, ident: str) -> float:
    # Compare decoded frames, not just authored keyframes: motion must survive rendering.
    selection = r"select=eq(n\,0)+eq(n\,25)+eq(n\,49)+eq(n\,75)+eq(n\,99)+eq(n\,124)+eq(n\,149)"
    command = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-i", str(path),
               "-vf", selection, "-vsync", "0", "-f", "rawvideo",
               "-pix_fmt", "gray", "-"]
    result = subprocess.run(command, capture_output=True)
    if result.returncode:
        raise RuntimeError(f"{ident}: could not decode motion samples: {result.stderr.decode(errors='replace')[-1000:]}")
    frame_size = WIDTH * HEIGHT
    sample_count = 7
    if len(result.stdout) != frame_size * sample_count:
        raise RuntimeError(f"{ident}: decoded {len(result.stdout) // frame_size} of {sample_count} motion sample frames")
    frames = [result.stdout[index * frame_size:(index + 1) * frame_size]
              for index in range(sample_count)]
    adjacent_differences = []
    for first, second in zip(frames, frames[1:]):
        adjacent_differences.append(sum(abs(a - b) for a, b in zip(first, second)) / frame_size)
    mean_difference = sum(adjacent_differences) / len(adjacent_differences)
    if mean_difference < 0.35:
        raise RuntimeError(f"{ident}: rendered motion is too subtle (adjacent mean luma difference {mean_difference:.3f})")
    return mean_difference


def _layer_motion_span(layer: dict) -> float:
    for track in layer.get("animation", {}).get("tracks", []):
        if track.get("property") != "position":
            continue
        values = [key["value"] for key in track["keyframes"]]
        return max(math.dist(a, b) for a in values for b in values)
    return 0.0


def _assert_visible_motion(layers: list[dict], ident: str) -> None:
    moving = []
    for layer in layers:
        tracks = {track.get("property"): track for track in layer.get("animation", {}).get("tracks", [])}
        if _layer_motion_span(layer) < 80 or not {"position", "scale", "opacity"}.issubset(tracks):
            continue
        scale_values = [key["value"] for key in tracks["scale"]["keyframes"]]
        opacity_values = [key["value"] for key in tracks["opacity"]["keyframes"]]
        if (max(max(value) for value in scale_values) >= 1.5 and
                min(min(value) for value in scale_values) <= .8 and
                max(opacity_values) - min(opacity_values) >= .5):
            moving.append(layer)
    if len(moving) < 2:
        raise RuntimeError(f"{ident}: expected two strongly drifting, pulsing layers; found {len(moving)}")


def _assert_no_path_stripes(layers: list[dict], ident: str) -> None:
    if any(layer.get("shape", {}).get("type") == "path" for layer in layers):
        raise RuntimeError(f"{ident}: hard-edged path ribbons are disallowed in soft background compositions")


def _validate_recipe_visual_contracts(specs: list[tuple[str, list[dict]]]) -> None:
    for ident, layers in specs:
        _assert_visible_motion(layers, ident)
        _assert_no_path_stripes(layers, ident)


# Keep output metadata focused on the measured rendered behavior.




def validate_poster(path: Path, ident: str) -> list[float]:
    if not path.is_file() or path.stat().st_size == 0:
        raise RuntimeError(f"{ident}: missing rendered poster {path}")
    with Image.open(path) as image:
        if image.size != (WIDTH, HEIGHT):
            raise RuntimeError(f"{ident}: poster dimensions are {image.size}, expected {(WIDTH, HEIGHT)}")
        stats = ImageStat.Stat(image.convert("RGB"))
        deviations = [float(value) for value in stats.stddev]
        if min(deviations) < 1.0:
            raise RuntimeError(f"{ident}: poster appears blank/near-uniform; RGB standard deviations={deviations}")
        return deviations


def write_contact_sheet(entries: list[dict], out: Path) -> Path:
    columns, thumb_w, thumb_h, label_h = 6, 320, 180, 28
    rows = math.ceil(len(entries) / columns)
    margin, gap = 18, 12
    sheet = Image.new("RGB", (margin * 2 + columns * thumb_w + (columns - 1) * gap,
                               margin * 2 + rows * (thumb_h + label_h) + (rows - 1) * gap),
                       (16, 18, 28))
    draw = ImageDraw.Draw(sheet)
    try:
        font = ImageFont.truetype("DejaVuSans.ttf", 17)
    except OSError:
        font = ImageFont.load_default()
    for index, item in enumerate(entries):
        col_index, row_index = index % columns, index // columns
        x = margin + col_index * (thumb_w + gap)
        y = margin + row_index * (thumb_h + label_h + gap)
        with Image.open(out / f"{item['id']}.jpg") as source:
            thumb = source.convert("RGB").resize((thumb_w, thumb_h), Image.LANCZOS)
        sheet.paste(thumb, (x, y))
        draw.text((x + 3, y + thumb_h + 5), item["id"], fill=(242, 244, 250), font=font)
    path = out / "contact_sheet.jpg"
    sheet.save(path, quality=88, optimize=True)
    return path


def _upload(files: list[Path], entries: list[dict], args) -> list[dict]:
    if len(files) != 43 or len(entries) != 43:
        raise RuntimeError(f"refusing incomplete Drive upload: {len(files)} files, {len(entries)} verified receipts")
    for item, path in zip(entries, files):
        if item["file"] != path.name or hashlib.sha256(path.read_bytes()).hexdigest() != item["sha256"]:
            raise RuntimeError(f"local file changed after verification: {path}")
    for path in (args.uploader, args.credentials, args.token):
        if not path.is_file():
            raise FileNotFoundError(f"required upload file is unavailable: {path}")
    checkpoint = args.out / "drive_upload_receipts.v2.json"
    previous = {}
    if checkpoint.is_file():
        saved = json.loads(checkpoint.read_text())
        if saved.get("destination_folder_id") == args.drive_folder:
            previous = {row.get("file"): row for row in saved.get("uploads", [])
                        if row.get("drive_receipt") and row.get("sha256")}
    receipts = []
    for item, path in zip(entries, files):
        prior = previous.get(path.name)
        if prior and prior.get("sha256") == item["sha256"]:
            receipts.append(prior)
            print(f"UPLOAD_REUSE {path.name} sha256={item['sha256']}", flush=True)
            continue
        drive_name = f"{path.stem}_v2{path.suffix}"
        command = [str(args.uploader), "-credentials", str(args.credentials), "-token", str(args.token),
                   "-folder", args.drive_folder, "-file", str(path), "-name", drive_name,
                   "-sha256", item["sha256"]]
        output = _run(command)
        expected = ("DRIVE_UPLOAD_PASS ", f"parent={args.drive_folder}",
                    f"sha256={item['sha256']}", f"bytes={item['bytes']}")
        line = next((line for line in output.splitlines() if "DRIVE_UPLOAD_PASS " in line), "")
        if not line or any(token not in line for token in expected):
            raise RuntimeError(f"RenderingGen did not verify upload of {path.name}: {output[-2000:]}")
        receipts.append({**item, "drive_name": drive_name, "drive_receipt": line})
        checkpoint.write_text(json.dumps({"destination_folder_id": args.drive_folder,
            "uploads": [*previous.values(), *receipts]}, indent=2) + "\n")
        previous[path.name] = receipts[-1]
        print(line, flush=True)
    checkpoint.write_text(json.dumps({"destination_folder_id": args.drive_folder,
        "uploads": receipts}, indent=2) + "\n")
    return receipts


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=OUT_DEFAULT)
    parser.add_argument("--cli", type=Path, default=CLI_DEFAULT)
    parser.add_argument("--assets-root", type=Path, default=CHRONON)
    parser.add_argument("--plans-only", action="store_true")
    parser.add_argument("--validate-only", action="store_true")
    parser.add_argument("--render", action="store_true", help="render all 43 plans to H.264 MP4")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--backend", choices=("software", "vulkan"), default="software")
    parser.add_argument("--workers", type=int, default=3, help="bounded number of independent render jobs (1-4)")
    parser.add_argument("--upload", action="store_true", help="upload all 43 verified MP4s via RenderingGen")
    parser.add_argument("--uploader", type=Path, default=UPLOADER_DEFAULT)
    parser.add_argument("--credentials", type=Path, default=CREDENTIALS_DEFAULT)
    parser.add_argument("--token", type=Path, default=TOKEN_DEFAULT)
    parser.add_argument("--drive-folder", default=DRIVE_FOLDER_DEFAULT)
    parser.add_argument("--limit", type=int, default=0, help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    if args.limit < 0 or args.limit > 43:
        parser.error("--limit must be in [0,43]")
    if args.workers < 1 or args.workers > 4:
        parser.error("--workers must be in [1,4]")
    if args.upload and (args.plans_only or args.validate_only or args.limit):
        parser.error("--upload requires the complete rendered 43-file suite")
    args.out = args.out.resolve()
    args.out.mkdir(parents=True, exist_ok=True)
    specs = recipes()
    if len(specs) != 43 or len({name for name, _ in specs}) != 43:
        raise RuntimeError("background recipe inventory must contain exactly 43 unique ids")
    _validate_recipe_visual_contracts(specs)
    if args.limit:
        specs = specs[:args.limit]
    plan_paths: list[tuple[str, Path]] = []
    for ident, layers in specs:
        video = args.out / f"{ident}.mp4"
        plan_path = args.out / f"{ident}.plan.json"
        plan_path.write_text(json.dumps(make_plan(ident, layers, video), indent=2) + "\n")
        plan_paths.append((ident, plan_path))
    if args.plans_only:
        print(f"Wrote {len(plan_paths)} plans in {args.out}")
        return 0
    if not args.cli.is_file():
        raise FileNotFoundError(f"Chronon3D CLI not found: {args.cli}")
    for ident, plan in plan_paths:
        _run([str(args.cli), "validate", "--plan", str(plan), "--assets-root", str(args.assets_root)])
        print(f"VALIDATE_PASS {ident}", flush=True)
    if args.validate_only:
        print(f"Validated {len(plan_paths)} RenderPlans; rendering was not requested.")
        return 0
    if not args.render and not args.upload:
        print(f"Validated {len(plan_paths)} plans; pass --render to create videos.")
        return 0
    def render_one(item: tuple[str, Path]) -> tuple[str, Path, float]:
        ident, plan = item
        video = args.out / f"{ident}.mp4"
        elapsed = 0.0
        if args.force or not video.is_file() or video.stat().st_size == 0:
            command = [str(args.cli), "render", "--plan", str(plan), "--assets-root", str(args.assets_root),
                       "--backend", args.backend, "--fps", str(FPS), "--codec", "h264",
                       "--encode-preset", "fast", "--ffmpeg-mode", "pipe", "-o", str(video)]
            started = time.monotonic()
            _run(command)
            elapsed = time.monotonic() - started
        validate_video(video, ident)
        return ident, video, elapsed

    files_by_id: dict[str, Path] = {}
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {pool.submit(render_one, item): item[0] for item in plan_paths}
        for future in as_completed(futures):
            ident = futures[future]
            resolved_id, video, elapsed = future.result()
            files_by_id[resolved_id] = video
            message = f"RENDER_PASS {ident} elapsed={elapsed:.1f}s" if elapsed else f"REUSE_PASS {ident}"
            print(f"{message} bytes={video.stat().st_size}", flush=True)

    entries: list[dict] = []
    files: list[Path] = []
    for ident, _ in plan_paths:
        video = files_by_id[ident]
        entry = validate_video(video, ident)
        files.append(video)
        poster = args.out / f"{ident}.jpg"
        _run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-ss", "2.5", "-i", str(video),
              "-frames:v", "1", "-q:v", "3", str(poster)])
        entry["poster"] = poster.name
        entry["poster_rgb_stddev"] = validate_poster(poster, ident)
        entries.append(entry)
    contact_sheet = write_contact_sheet(entries, args.out)
    manifest = {"schema": "chronontemplate.background-recreation.v2", "source_note":
        "Reference-inspired designs; original reference ZIP/CSV were not available in this checkout.",
        "canvas": {"width": WIDTH, "height": HEIGHT, "fps": FPS, "frames": FRAMES,
                   "duration_seconds": FRAMES / FPS},
        "counts": {"wave": 16, "neon": 8, "cinematic": 19}, "videos": entries}
    manifest_path = args.out / "manifest.v2.json"
    manifest["contact_sheet"] = contact_sheet.name
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
    if args.upload:
        receipts = _upload(files, entries, args)
        manifest["destination_folder_id"] = args.drive_folder
        manifest["drive_uploads"] = receipts
        manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"BACKGROUND_SUITE_PASS videos={len(entries)} manifest={manifest_path}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
