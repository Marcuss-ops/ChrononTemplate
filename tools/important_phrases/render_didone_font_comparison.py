#!/usr/bin/env python3
"""Render and compare Didone font candidates at identical optical settings.

Renders one static 1920x1080 composition per candidate via Chronon3D, then
builds a labelled contact sheet. Upload is explicit and happens only after all
native plans and rendered frames have been validated.
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[2]
WORKSPACE = ROOT.parent
CLI_DEFAULT = WORKSPACE / "Chronon3d/build/chronon/linux-video-fast-dev/apps/chronon3d_cli/chronon3d_cli"
OUT_DEFAULT = ROOT / "out/didone_font_comparison_v1"
FONTS = [
    ("Bodoni 72 Book Italic", "assets/fonts/Bodoni72-BookItalic.ttf"),
    ("Bodoni 72 Bold (non-italic control)", "assets/fonts/Bodoni72-Bold.ttf"),
    ("Playfair Display Italic", "assets/fonts/PlayfairDisplay-Italic.ttf"),
    ("Didot Italic", "assets/fonts/Didot-Italic.ttf"),
    ("Libre Bodoni Italic", "assets/fonts/LibreBodoni-Italic.ttf"),
    ("Bodoni Moda Italic (control)", "assets/fonts/BodoniModa-Italic.ttf"),
]
WIDTH, HEIGHT = 1920, 1080
BG = [0.0, 0.0, 0.0, 1.0]
WHITE = "#F7F4EF"
RED = "#FF1018"
DURATION = 1
# Keep exact target copy, nominal size, tracking, line box and baselines fixed
# across every candidate; do not auto-fit each face and disguise width mismatch.
PHRASES = [
    ("è il valore più grande", WHITE),
    ("di ogni business", RED),
]
FONT_SIZE = 190


def _rgba(color: str) -> list[float]:
    value = color.lstrip("#")
    return [int(value[i:i + 2], 16) / 255 for i in (0, 2, 4)] + [1.0]


def _measure(font_path: Path, text: str, size: int) -> float:
    return ImageFont.truetype(str(font_path), size).getlength(text)


def build_plan(name: str, relative_font: str) -> dict[str, Any]:
    font_path = WORKSPACE / "Chronon3d" / relative_font
    size = FONT_SIZE
    line_y = [365, 680]
    layers: list[dict[str, Any]] = [
        {"id": "background", "type": "color", "color": BG,
         "size": [WIDTH, HEIGHT], "start_frame": 0,
         "duration_frames": DURATION},
    ]
    for index, ((text, color), y) in enumerate(zip(PHRASES, line_y)):
        measured_width = _measure(font_path, text, size)
        tracked_width = measured_width + (len(text) - 1) * -2.0
        if tracked_width > 1760:
            raise ValueError(f"{name}: {text!r} exceeds the shared 1760px comparison width at {size}px: {tracked_width:.1f}")
        layers.append({
            "id": f"sample-{index}", "type": "text", "text": text,
            "size": [1800, 240], "position": [960, y],
            "start_frame": 0, "duration_frames": DURATION,
            "style": {"font": relative_font, "font_size": float(size),
                      "fill": color},
            "spans": [{"start": 0, "end": len(text.encode("utf-8")),
                       "style": {"tracking": -2.0}}],
            "effects": [{"type": "bloom", "threshold": 0.90,
                         "radius": 12.0, "intensity": 0.10}] if color == WHITE else [],
            "animation": {"tracks": [{"property": "position_x", "easing": "linear",
                "keyframes": [{"frame": 0, "value": 0.0}]}]},
        })
    return {
        "schema": "chronon.render-plan.v3", "version": 3,
        "job_id": f"didone_font_{name.lower().replace(' ', '_').replace('(', '').replace(')', '')}",
        "canvas": {"width": WIDTH, "height": HEIGHT, "fps_num": 30,
                   "fps_den": 1, "duration_frames": DURATION},
        "layers": layers,
        "output": {"path": f"didone_font_{name}.mp4", "format": "mp4", "codec": "h264"},
    }


def validate_with_cli(cli: Path, plan_path: Path, assets_root: Path) -> None:
    subprocess.run([str(cli), "validate", "--plan", str(plan_path),
                    "--assets-root", str(assets_root)], check=True,
                   cwd=WORKSPACE, stdout=subprocess.DEVNULL)


def render_candidate(cli: Path, plan_path: Path, output: Path,
                     assets_root: Path) -> None:
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise RuntimeError("ffmpeg is required to decode the verified MP4 frame")
    video = output.with_suffix(".mp4")
    subprocess.run([str(cli), "render", "--plan", str(plan_path),
                    "--assets-root", str(assets_root), "--frames", "0",
                    "--output", str(video), "--backend", "vulkan",
                    "--gpu-hot-path-mode", "require_gpu_native",
                    "--hardware", "none", "--encoder-backend", "pipe",
                    "--profile", "preview"], check=True, cwd=WORKSPACE)
    if not video.is_file() or video.stat().st_size < 1000:
        raise RuntimeError(f"encoded render is missing or implausibly small: {video}")
    subprocess.run([ffmpeg, "-y", "-v", "error", "-i", str(video),
                    "-frames:v", "1", "-update", "1", str(output)],
                   check=True, cwd=WORKSPACE)
    if not output.is_file() or output.stat().st_size < 1000:
        raise RuntimeError(f"decoded frame is missing or implausibly small: {output}")
    with Image.open(output) as frame:
        if frame.size != (WIDTH, HEIGHT):
            raise RuntimeError(f"{output.name}: expected 1920x1080, got {frame.size}")
        frame.load()
        rgb = frame.convert("RGB")
        extrema = rgb.getextrema()
        if all(low == high for low, high in extrema):
            raise RuntimeError(f"{output.name}: decoded render contains no visible variation")
        # Sample foreground occupancy to reject blank/near-blank encodes.
        pixels = frame.convert("RGB")
        histogram = pixels.convert("L").histogram()
        foreground = sum(histogram[20:])
        if foreground < 5000:
            raise RuntimeError(f"{output.name}: decoded render is nearly blank")
        pixels.close()
        rgb.close()


def make_contact_sheet(out_dir: Path, rendered: list[tuple[str, Path]]) -> Path:
    thumb_w, thumb_h, gutter, label_h = 960, 540, 32, 56
    sheet = Image.new("RGB", (2 * thumb_w + 3 * gutter,
                               3 * (thumb_h + label_h) + 4 * gutter), (15, 15, 18))
    draw = ImageDraw.Draw(sheet)
    try:
        label_font = ImageFont.truetype(str(WORKSPACE / "Chronon3d/assets/fonts/Inter-SemiBold.ttf"), 26)
    except OSError:
        label_font = ImageFont.load_default()
    for index, (name, path) in enumerate(rendered):
        col, row = index % 2, index // 2
        x, y = gutter + col * (thumb_w + gutter), gutter + row * (thumb_h + label_h + gutter)
        draw.text((x, y + 10), name, font=label_font, fill=(242, 242, 245))
        with Image.open(path) as image:
            thumb = image.convert("RGB").resize((thumb_w, thumb_h), Image.LANCZOS)
            sheet.paste(thumb, (x, y + label_h))
    result = out_dir / "didone_font_comparison_contact_sheet.png"
    sheet.save(result, optimize=True)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=OUT_DEFAULT)
    parser.add_argument("--cli", type=Path, default=CLI_DEFAULT)
    parser.add_argument("--assets-root", type=Path, default=WORKSPACE / "Chronon3d")
    parser.add_argument("--render", action="store_true", help="render all candidates after native validation")
    parser.add_argument("--upload", action="store_true", help="upload verified frames + contact sheet to the Didone Drive folder")
    parser.add_argument("--drive-folder", default="1J_xUGo_bchzXDIGqSX04CU44c_Dm3SxS")
    parser.add_argument("--drive-credentials", type=Path,
                        default=Path.home() / ".config/velox/credentials.json")
    parser.add_argument("--drive-token", type=Path,
                        default=Path.home() / ".config/velox/token.json")
    args = parser.parse_args()
    cli, assets_root, out_dir = args.cli.resolve(), args.assets_root.resolve(), args.out.resolve()
    if not cli.is_file():
        raise SystemExit(f"Chronon3D CLI not found: {cli}")
    out_dir.mkdir(parents=True, exist_ok=True)
    validated: list[tuple[str, Path]] = []
    for display_name, relative_font in FONTS:
        if not (assets_root / relative_font).is_file():
            raise SystemExit(f"Font candidate missing under assets root: {assets_root / relative_font}")
        plan = build_plan(display_name, relative_font)
        plan_path = out_dir / f"{plan['job_id']}.plan.json"
        plan_path.write_text(json.dumps(plan, indent=2) + "\n", encoding="utf-8")
        validate_with_cli(cli, plan_path, assets_root)
        validated.append((display_name, plan_path))
        print(f"PLAN_VALID {display_name}: {plan_path}")
    if not args.render:
        print("Validated plans only. Pass --render to render the sample frames.")
        return 0

    rendered: list[tuple[str, Path]] = []
    for display_name, plan_path in validated:
        output = out_dir / f"{plan_path.stem.replace('.plan', '')}.png"
        render_candidate(cli, plan_path, output, assets_root)
        rendered.append((display_name, output))
        print(f"FRAME_RENDERED {display_name}: {output} ({output.stat().st_size} bytes)")
    contact_sheet = make_contact_sheet(out_dir, rendered)
    print(f"CONTACT_SHEET {contact_sheet} ({contact_sheet.stat().st_size} bytes)")
    manifest = out_dir / "didone_font_comparison_manifest.json"
    manifest.write_text(json.dumps({
        "status": "RENDERED_VERIFIED", "width": WIDTH, "height": HEIGHT,
        "fonts": [{"name": name, "path": str(path), "bytes": path.stat().st_size}
                  for name, path in rendered],
        "contact_sheet": {"path": str(contact_sheet), "bytes": contact_sheet.stat().st_size},
    }, indent=2) + "\n", encoding="utf-8")

    if args.upload:
        uploader = WORKSPACE / "RenderingGen/bin/drive-upload"
        credentials = args.drive_credentials.expanduser().resolve()
        token = args.drive_token.expanduser().resolve()
        for required in (uploader, credentials, token):
            if not required.is_file():
                raise SystemExit(f"Drive upload prerequisite missing: {required}")
        # Only the single overview sheet plus candidate frames are uploaded;
        # source plans/font files/manifests are not published.
        upload_results = []
        for _, path in [*rendered, ("comparison contact sheet", contact_sheet)]:
            result = subprocess.run([str(uploader), "-credentials", str(credentials),
                "-token", str(token), "-folder", args.drive_folder,
                "-file", str(path)], check=True, text=True, capture_output=True)
            line = result.stdout.strip()
            if "DRIVE_UPLOAD_PASS" not in line or f"parent={args.drive_folder}" not in line:
                raise RuntimeError(f"Drive did not verify upload for {path.name}: {line}")
            upload_results.append({"file": path.name, "result": line})
            print(line)
        (out_dir / "drive_upload_manifest.json").write_text(
            json.dumps({"folder": args.drive_folder, "uploads": upload_results}, indent=2) + "\n",
            encoding="utf-8")
        print(f"DRIVE_UPLOAD_COMPLETE files={len(upload_results)} folder={args.drive_folder}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, RuntimeError, subprocess.CalledProcessError) as error:
        print(f"DIDONE_FONT_COMPARISON_FAIL: {error}", file=sys.stderr)
        raise SystemExit(2)
