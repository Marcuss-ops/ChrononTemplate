#!/usr/bin/env python3
"""Runtime phrase typography: presets, Font/Shadow/Glow selection, gallery.

The catalog (`catalog/typography_styles.v1.json`) owns the pre-saved looks.
This runner is deliberately thin: it resolves one preset (optionally replacing
its font, shadow or glow), lowers it to a `chronon.render-plan.v2` document and
drives the real Chronon3D CLI.

Examples
--------
    # Browse the catalog
    tools/typography/typography_gallery.py --list

    # Resolve a preset and its runtime overrides without rendering
    tools/typography/typography_gallery.py --preset 02_playfair_carta --show
    tools/typography/typography_gallery.py --preset 02_playfair_carta \
        --font playfair_display_italic --shadow ink_editorial --glow gold_glow --show

    # One plan + one clip with explicit runtime choices
    tools/typography/typography_gallery.py --preset 02_playfair_carta \
        --font bodoni_moda --shadow ink_soft --glow champagne_glow \
        --text "La memoria è il primo testimone" \
        --plan-out /tmp/phrase.plan.json --render --output /tmp/phrase.mp4

    # Full 1920x1080 gallery: emit, render, verify, contact sheet
    tools/typography/typography_gallery.py --gallery

    # Upload the verified gallery to Drive
    tools/typography/typography_gallery.py --upload
"""

from __future__ import annotations

import sys as _velox_sys
from pathlib import Path as _VeloxPath
_velox_sys.path.insert(0, str(_VeloxPath(__file__).resolve().parents[3] / "tools"))
from stack_config import overlay_root as _overlay_root  # noqa: E402

import os
import argparse
import hashlib
import json
import math
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

from PIL import Image, ImageChops, ImageDraw, ImageFont, ImageStat

ROOT = Path(__file__).resolve().parents[2]          # ChrononTemplate
REPO = ROOT.parent                                  # repository root
ASSETS = REPO / "Chronon3d"
CATALOG = ROOT / "catalog" / "typography_styles.v1.json"
DEFAULT_OUT = REPO / "RenderingGen" / "UploadDrive" / "typography_styles_20261108"
UPLOADER = REPO / "RenderingGen" / "bin" / "drive-upload"
CREDENTIALS = REPO / "RenderingGen" / "UploadDrive" / "credentials.json"
TOKEN = REPO / "RenderingGen" / "UploadDrive" / "token.json"

DRIVE_FOLDER = _overlay_root()
DRIVE_SUBFOLDER = "Typography Styles V1 1080p"
DRIVE_FOLDER_URL = f"https://drive.google.com/drive/u/1/folders/{DRIVE_FOLDER}"

CLI_CANDIDATES = (
    ASSETS / "build/chronon/linux-video-release/apps/chronon3d_cli/chronon3d_cli",
    ASSETS / "build/chronon/linux-video-fast-dev/apps/chronon3d_cli/chronon3d_cli",
    ASSETS / "build/chronon/linux-fast-dev/apps/chronon3d_cli/chronon3d_cli",
)

OUT = DEFAULT_OUT
MAX_DURATION_S = 10.0


# --------------------------------------------------------------------------- #
# catalog and selection
# --------------------------------------------------------------------------- #
def fail(message: str) -> "NoReturn":
    raise SystemExit(f"typography_gallery: {message}")


def load_catalog(path: Path = CATALOG) -> dict[str, Any]:
    if not path.is_file():
        fail(f"missing catalog: {path}")
    catalog = json.loads(path.read_text(encoding="utf-8"))
    if catalog.get("schema") != "chronontemplate.typography-styles.v1":
        fail(f"unexpected catalog schema: {catalog.get('schema')!r}")
    return catalog


def normalized_id(value: str) -> str:
    return value.strip().lower().replace("-", "_")


def select_preset(catalog: dict[str, Any], wanted: str) -> dict[str, Any]:
    needle = normalized_id(wanted)
    exact = [p for p in catalog["presets"] if normalized_id(p["id"]) == needle]
    if exact:
        return exact[0]
    prefix = [p for p in catalog["presets"] if normalized_id(p["id"]).startswith(needle)]
    if len(prefix) == 1:
        return prefix[0]
    if not prefix:
        fail(f"unknown preset {wanted!r}; use --list")
    fail(f"ambiguous preset {wanted!r}: {', '.join(p['id'] for p in prefix)}")


def lookup(table: dict[str, Any], wanted: str, what: str) -> tuple[str, dict[str, Any]]:
    needle = normalized_id(wanted)
    for key, value in table.items():
        if normalized_id(key) == needle:
            return key, value
    fail(f"unknown {what} {wanted!r}; use --list")


def require_hex(value: str, what: str) -> str:
    text = value.strip().upper()
    if len(text) != 7 or text[0] != "#" or any(c not in "0123456789ABCDEF" for c in text[1:]):
        fail(f"{what} must be #RRGGBB, got {value!r}")
    return text


def hex_rgb(value: str) -> tuple[int, int, int]:
    text = require_hex(value, "color")
    return tuple(int(text[i : i + 2], 16) for i in (1, 3, 5))  # type: ignore[return-value]


def hex_rgba(value: str) -> list[float]:
    r, g, b = hex_rgb(value)
    return [r / 255.0, g / 255.0, b / 255.0, 1.0]


def resolve(
    catalog: dict[str, Any],
    preset: dict[str, Any],
    *,
    font: str | None = None,
    shadow: str | None = None,
    glow: str | None = None,
    fill: str | None = None,
    background: str | None = None,
    font_size: float | None = None,
) -> dict[str, Any]:
    """Merge a saved preset with the runtime Font / Shadow / Glow axes."""
    font_id, font_asset = lookup(catalog["fonts"], font or preset["font"], "font")
    shadow_id, shadow_asset = lookup(catalog["shadows"], shadow or preset["shadow"], "shadow")
    glow_id, glow_asset = lookup(catalog["glows"], glow or preset["glow"], "glow")

    size = float(font_size if font_size is not None else preset["font_size"])
    if not math.isfinite(size) or size < 20.0 or size > 512.0:
        fail(f"font size must be finite and inside [20, 512], got {size}")

    shadow_style = {k: v for k, v in shadow_asset.items() if k != "label"}
    glow_style = {k: v for k, v in glow_asset.items() if k != "label"}
    shadow_style["color"] = require_hex(shadow_style["color"], "shadow color")
    glow_style["color"] = require_hex(glow_style["color"], "glow color")

    return {
        "preset": preset["id"],
        "label": preset["label"],
        "note": preset.get("note", ""),
        "family": preset["family"],
        "family_label": next(
            (f["label"] for f in catalog["families"] if f["id"] == preset["family"]),
            preset["family"],
        ),
        "font": font_id,
        "font_asset": font_asset,
        "font_size": size,
        "font_size_explicit": font_size is not None,
        "fill": require_hex(fill or preset["fill"], "fill"),
        "background": require_hex(background or preset["background"], "background"),
        "shadow": shadow_id,
        "shadow_asset": shadow_asset,
        "shadow_style": shadow_style,
        "glow": glow_id,
        "glow_asset": glow_asset,
        "glow_style": glow_style,
    }


# --------------------------------------------------------------------------- #
# plan writing
# --------------------------------------------------------------------------- #
def fitted_font_size(
    resolved: dict[str, Any], text: str, box_width: float
) -> float:
    """Keep the phrase on one line without asking the renderer to shrink it.

    The plan has no reliable auto-fit sweet spot for display faces: a phrase
    that is a few pixels too wide falls back to the minimum size. Measuring the
    longest line here and only scaling the requested size by what is actually
    needed keeps wide italics (Bodoni, Didot) at a readable size.
    """
    requested = float(resolved["font_size"])
    if resolved.get("font_size_explicit"):
        return requested
    lines = text.splitlines() or [text]
    longest = max(lines, key=len)
    try:
        font = ImageFont.truetype(
            str(ASSETS / resolved["font_asset"]["path"]), max(1, int(round(requested)))
        )
    except OSError:
        return requested
    measured = float(font.getlength(longest))
    limit = box_width * 0.90
    if measured <= limit or measured <= 0.0:
        return requested
    return round(max(36.0, requested * limit / measured), 1)


def build_plan(
    catalog: dict[str, Any],
    resolved: dict[str, Any],
    text: str,
    duration_s: float,
) -> dict[str, Any]:
    canvas = catalog["canvas"]
    width, height, fps = int(canvas["width"]), int(canvas["height"]), int(canvas["fps"])
    if duration_s <= 0.0 or duration_s > MAX_DURATION_S:
        fail(f"duration must be inside (0, {MAX_DURATION_S:g}] seconds, got {duration_s}")
    frames = int(round(duration_s * fps))
    if frames < 30:
        fail("duration must produce at least 30 frames")

    enter = min(28, max(12, frames // 8))
    exit_start = frames - max(12, frames // 14)
    if exit_start <= enter + 2:
        exit_start = max(enter + 3, frames - 6)
    rise_end = min(frames - 1, enter + 20)
    scale_end = min(frames - 1, enter + 24)

    default_box = catalog["defaults"]["box"]
    box = [float(default_box[0]), float(default_box[1])]
    font_size = fitted_font_size(resolved, text, box[0])

    style: dict[str, Any] = {
        "font": resolved["font_asset"]["path"],
        "font_size": font_size,
        "fill": resolved["fill"],
        "text_align": catalog["defaults"]["text_align"],
        "stroke": {"color": "#000000", "width": 0},
    }
    if float(resolved["shadow_style"].get("opacity", 0.0)) > 0.0:
        style["shadow"] = dict(resolved["shadow_style"])
    if (
        float(resolved["glow_style"].get("radius", 0.0)) > 0.0
        and float(resolved["glow_style"].get("intensity", 0.0)) > 0.0
    ):
        style["glow"] = dict(resolved["glow_style"])

    tracks: list[dict[str, Any]] = [
        {
            "property": "opacity",
            "easing": "linear",
            "keyframes": [
                {"frame": 0, "value": 0.0},
                {"frame": enter, "value": 1.0},
                {"frame": exit_start, "value": 1.0},
                {"frame": frames - 1, "value": 0.0},
            ],
        },
        {
            "property": "position_y",
            "easing": "out_cubic",
            "keyframes": [
                {"frame": 0, "value": 18.0},
                {"frame": rise_end, "value": 0.0},
                {"frame": frames - 1, "value": 0.0},
            ],
        },
        {
            "property": "scale",
            "easing": "out_cubic",
            "keyframes": [
                {"frame": 0, "value": 0.988},
                {"frame": scale_end, "value": 1.0},
                {"frame": frames - 1, "value": 1.0},
            ],
        },
    ]

    plan = {
        "schema": "chronon.render-plan.v2",
        "version": 2,
        "job_id": f"typography_{resolved['preset']}",
        "canvas": {
            "width": width,
            "height": height,
            "fps_num": fps,
            "fps_den": 1,
            "duration_frames": frames,
        },
        "layers": [
            {
                "id": "background",
                "type": "color",
                "color": hex_rgba(resolved["background"]),
                "size": [width, height],
                # Colour layers are positioned from the canvas centre; the
                # explicit [0, 0] is the full-canvas plate.
                "position": [0, 0],
                "start_frame": 0,
                "duration_frames": frames,
            },
            {
                "id": "phrase",
                "type": "text",
                "text": text,
                "size": box,
                "position": [width / 2.0, height / 2.0],
                "style": style,
                "start_frame": 0,
                "duration_frames": frames,
                "animation": {"tracks": tracks},
            },
        ],
        "output": {"path": f"{resolved['preset']}.mp4", "format": "mp4", "codec": "h264"},
    }
    return plan


def plan_path(out_dir: Path, preset_id: str) -> Path:
    return out_dir / "plans" / f"{preset_id}.plan.json"


def mp4_path(out_dir: Path, preset_id: str) -> Path:
    return out_dir / "mp4" / f"{preset_id}.mp4"


def still_path(out_dir: Path, preset_id: str) -> Path:
    return out_dir / "stills" / f"{preset_id}.png"


def write_plan(plan: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(plan, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def find_cli() -> Path:
    for candidate in CLI_CANDIDATES:
        if candidate.is_file() and candidate.stat().st_mode & 0o111:
            return candidate
    fail("chronon3d_cli not found; build the linux-video release lane first")


# --------------------------------------------------------------------------- #
# manifest
# --------------------------------------------------------------------------- #
def empty_manifest(catalog: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema": "chronontemplate.typography-gallery.v1",
        "date": time.strftime("%Y-%m-%d"),
        "catalog": str(CATALOG.relative_to(REPO)),
        "title": catalog["title"],
        "canvas": catalog["canvas"],
        "drive": {
            "folder_id": DRIVE_FOLDER,
            "folder_url": DRIVE_FOLDER_URL,
            "subfolder": DRIVE_SUBFOLDER,
        },
        "entries": [],
    }


def fresh_entries(catalog: dict[str, Any], text: str, duration_s: float) -> list[dict[str, Any]]:
    entries = []
    for preset in catalog["presets"]:
        resolved = resolve(catalog, preset)
        plan = build_plan(catalog, resolved, text, duration_s)
        style = plan["layers"][1]["style"]
        entries.append(
            {
                "id": preset["id"],
                "label": preset["label"],
                "note": preset.get("note", ""),
                "family": preset["family"],
                "family_label": resolved["family_label"],
                "text": text,
                "duration_s": duration_s,
                "frames": int(round(duration_s * catalog["canvas"]["fps"])),
                "plan": f"plans/{preset['id']}.plan.json",
                "mp4": f"mp4/{preset['id']}.mp4",
                "still": f"stills/{preset['id']}.png",
                "style": {
                    "font": resolved["font"],
                    "font_family": resolved["font_asset"]["family"],
                    "font_path": resolved["font_asset"]["path"],
                    "font_size": style["font_size"],
                    "fill": resolved["fill"],
                    "background": resolved["background"],
                    "shadow": resolved["shadow"],
                    "glow": resolved["glow"],
                },
                "requested_font_size": resolved["font_size"],
                "shadow": resolved["shadow_style"],
                "glow": resolved["glow_style"],
            }
        )
    return entries


def load_manifest(out_dir: Path, catalog: dict[str, Any], text: str, duration_s: float) -> dict[str, Any]:
    path = out_dir / "manifest.json"
    fresh = empty_manifest(catalog)
    fresh["entries"] = fresh_entries(catalog, text, duration_s)
    if not path.is_file():
        return fresh
    try:
        old = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return fresh
    by_id = {entry["id"]: entry for entry in old.get("entries", [])}
    merged = []
    for entry in fresh["entries"]:
        previous = by_id.get(entry["id"])
        if previous:
            # A verified clip is reusable only for the same media: same resolved
            # style, same phrase and same frame count. Otherwise the fresh
            # selection is the truth and the clip must be rendered again.
            same_media = (
                previous.get("style") == entry["style"]
                and previous.get("text") == entry["text"]
                and previous.get("frames") == entry["frames"]
            )
            if same_media:
                for key in (
                    "width",
                    "height",
                    "fps",
                    "sha256",
                    "bytes",
                    "verified",
                    "verified_at",
                    "foreground_ratio",
                    "uploaded",
                    "drive_id",
                    "drive_url",
                    "drive_name",
                ):
                    if key in previous:
                        entry[key] = previous[key]
        merged.append(entry)
    fresh["entries"] = merged
    if "contact_sheet" in old:
        fresh["contact_sheet"] = old["contact_sheet"]
    return fresh


def save_manifest(out_dir: Path, manifest: dict[str, Any]) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )


def manifest_entry(manifest: dict[str, Any], preset_id: str) -> dict[str, Any]:
    for entry in manifest["entries"]:
        if entry["id"] == preset_id:
            return entry
    fail(f"preset {preset_id!r} is not in the manifest")


# --------------------------------------------------------------------------- #
# render and verify
# --------------------------------------------------------------------------- #
def validate(plan: Path, cli: Path) -> None:
    result = subprocess.run(
        [str(cli), "validate", "--plan", str(plan), "--assets-root", str(ASSETS)],
        cwd=REPO,
        text=True,
        capture_output=True,
    )
    if result.returncode != 0:
        tail = (result.stdout + result.stderr).strip().splitlines()[-8:]
        fail(f"plan validation failed for {plan.name}: " + " | ".join(tail))


def render(plan: Path, video: Path, cli: Path, log: Path) -> None:
    video.parent.mkdir(parents=True, exist_ok=True)
    log.parent.mkdir(parents=True, exist_ok=True)
    command = [
        str(cli),
        "render",
        "--plan",
        str(plan),
        "--assets-root",
        str(ASSETS),
        "--backend",
        "vulkan",
        "--hardware",
        "nvenc",
        "--encoder-backend",
        "pipe",
        "--codec",
        "h264",
        "--fps",
        "30",
        "--rate-control",
        "qp",
        "--qp",
        "18",
        "-o",
        str(video),
    ]
    with log.open("w", encoding="utf-8") as handle:
        handle.write(" ".join(command) + "\n\n")
        handle.flush()
        result = subprocess.run(command, cwd=REPO, stdout=handle, stderr=subprocess.STDOUT)
    if result.returncode != 0:
        tail = log.read_text(encoding="utf-8", errors="replace").strip().splitlines()[-12:]
        fail(f"render failed for {video.name}: " + " | ".join(tail))


def probe(video: Path) -> dict[str, Any]:
    result = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-count_frames",
            "-select_streams",
            "v:0",
            "-show_entries",
            "stream=width,height,nb_read_frames,r_frame_rate:format=duration,size",
            "-of",
            "json",
            str(video),
        ],
        check=True,
        text=True,
        capture_output=True,
    )
    data = json.loads(result.stdout)
    stream = data["streams"][0]
    frames = int(stream.get("nb_read_frames") or 0)
    return {
        "width": int(stream["width"]),
        "height": int(stream["height"]),
        "fps": stream.get("r_frame_rate", "30/1"),
        "frames": frames,
        "duration_s": round(float(data["format"]["duration"]), 3),
        "bytes": int(data["format"]["size"]),
    }


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def decode_still(video: Path, still: Path, seconds: float, expected_size: tuple[int, int]) -> Image.Image:
    still.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-v",
            "error",
            "-ss",
            f"{seconds:.3f}",
            "-i",
            str(video),
            "-frames:v",
            "1",
            "-update",
            "1",
            str(still),
        ],
        check=True,
        cwd=REPO,
    )
    with Image.open(still) as image:
        frame = image.convert("RGB")
    if frame.size != expected_size:
        fail(f"{still.name}: expected {expected_size[0]}x{expected_size[1]}, got {frame.size}")
    return frame.copy()


def verify_entry(entry: dict[str, Any], out_dir: Path, catalog: dict[str, Any]) -> None:
    video = out_dir / entry["mp4"]
    if not video.is_file():
        fail(f"{entry['id']}: missing clip {entry['mp4']}")
    info = probe(video)
    width = int(catalog["canvas"]["width"])
    height = int(catalog["canvas"]["height"])
    if (info["width"], info["height"]) != (width, height):
        fail(f"{entry['id']}: expected {width}x{height}, got {info['width']}x{info['height']}")
    if info["frames"] != entry["frames"]:
        fail(f"{entry['id']}: expected {entry['frames']} frames, got {info['frames']}")
    expected_duration = entry["frames"] / float(catalog["canvas"]["fps"])
    if abs(info["duration_s"] - expected_duration) > 0.15:
        fail(f"{entry['id']}: expected {expected_duration:.2f}s, got {info['duration_s']:.2f}s")

    # Sample the readable hold, not the fade.
    frame = decode_still(
        video,
        out_dir / entry["still"],
        expected_duration * 0.55,
        (width, height),
    )
    if max(ImageStat.Stat(frame).stddev) < 2.0:
        fail(f"{entry['id']}: decoded frame is flat")
    background = Image.new("RGB", (width, height), hex_rgb(entry["style"]["background"]))
    diff = ImageChops.difference(frame, background).convert("L")
    histogram = diff.histogram()
    changed = sum(histogram[40:])
    ratio = changed / float(width * height)
    if ratio < 0.0012:
        fail(f"{entry['id']}: no visible phrase on the decoded frame ({ratio:.4%} changed)")
    if ratio > 0.45:
        fail(f"{entry['id']}: decoded frame is not a clean phrase plate ({ratio:.2%} changed)")

    entry.update(
        width=info["width"],
        height=info["height"],
        fps=info["fps"],
        frames=info["frames"],
        duration_s=info["duration_s"],
        bytes=info["bytes"],
        sha256=sha256(video),
        verified=True,
        verified_at=time.strftime("%Y-%m-%dT%H:%M:%S"),
        foreground_ratio=round(ratio, 6),
    )


# --------------------------------------------------------------------------- #
# commands
# --------------------------------------------------------------------------- #
def cmd_list(catalog: dict[str, Any]) -> int:
    print(f"{catalog['title']}\n")
    print(f"Canvas: {catalog['canvas']['width']}x{catalog['canvas']['height']} @ "
          f"{catalog['canvas']['fps']} fps · max {MAX_DURATION_S:g}s")
    print(f"Phrase: {catalog['default_phrase']!r}\n")
    for family in catalog["families"]:
        presets = [p for p in catalog["presets"] if p["family"] == family["id"]]
        print(f"{family['label']}  ({family['description']})")
        for preset in presets:
            font = catalog["fonts"][preset["font"]]["family"]
            print(
                f"  {preset['id']:<34} {preset['label']}\n"
                f"  {'':<34} font={font} · shadow={preset['shadow']} · glow={preset['glow']}"
            )
        print()
    print(f"Fonts   ({len(catalog['fonts'])}): {', '.join(catalog['fonts'])}")
    print(f"Shadows ({len(catalog['shadows'])}): {', '.join(catalog['shadows'])}")
    print(f"Glows   ({len(catalog['glows'])}): {', '.join(catalog['glows'])}")
    print("\nRuntime override example:")
    print("  tools/typography/typography_gallery.py --preset 02_playfair_carta \\")
    print("      --font bodoni_moda --shadow ink_editorial --glow gold_glow --show")
    return 0


def cmd_show(catalog: dict[str, Any], args: argparse.Namespace) -> int:
    preset = select_preset(catalog, args.preset)
    resolved = resolve(
        catalog,
        preset,
        font=args.font,
        shadow=args.shadow,
        glow=args.glow,
        fill=args.fill,
        background=args.background,
        font_size=args.font_size,
    )
    plan = build_plan(catalog, resolved, args.text or catalog["default_phrase"], args.duration)
    print(json.dumps({"selection": resolved, "plan": plan}, indent=2, ensure_ascii=False))
    return 0


def cmd_emit_one(catalog: dict[str, Any], args: argparse.Namespace) -> int:
    preset = select_preset(catalog, args.preset)
    resolved = resolve(
        catalog,
        preset,
        font=args.font,
        shadow=args.shadow,
        glow=args.glow,
        fill=args.fill,
        background=args.background,
        font_size=args.font_size,
    )
    plan = build_plan(catalog, resolved, args.text or catalog["default_phrase"], args.duration)
    output = Path(args.plan_out) if args.plan_out else plan_path(OUT, preset["id"])
    write_plan(plan, output)
    print(f"PLAN {output}")

    if args.render:
        cli = find_cli()
        validate(output, cli)
        target = Path(args.output) if args.output else mp4_path(OUT, preset["id"])
        render(output, target, cli, OUT / "logs" / f"{preset['id']}.log")
        info = probe(target)
        print(
            f"RENDER {target} · {info['width']}x{info['height']} · "
            f"{info['frames']}f · {info['duration_s']:.2f}s · {info['bytes'] / 1e6:.2f} MB"
        )
    return 0


def emit_all(catalog: dict[str, Any], out_dir: Path, text: str, duration_s: float) -> dict[str, Any]:
    manifest = load_manifest(out_dir, catalog, text, duration_s)
    for entry in manifest["entries"]:
        preset = select_preset(catalog, entry["id"])
        resolved = resolve(catalog, preset)
        plan = build_plan(catalog, resolved, text, duration_s)
        write_plan(plan, out_dir / entry["plan"])
        entry["frames"] = int(round(duration_s * catalog["canvas"]["fps"]))
        entry["duration_s"] = duration_s
        entry["text"] = text
        entry["requested_font_size"] = resolved["font_size"]
        entry["style"]["font_size"] = plan["layers"][1]["style"]["font_size"]
    (out_dir / "catalog").mkdir(parents=True, exist_ok=True)
    shutil.copyfile(CATALOG, out_dir / "catalog" / CATALOG.name)
    save_manifest(out_dir, manifest)
    print(f"EMITTED {len(manifest['entries'])} plans in {out_dir / 'plans'}")
    return manifest


def selected_entries(manifest: dict[str, Any], only: str) -> list[dict[str, Any]]:
    if not only:
        return manifest["entries"]
    wanted = [normalized_id(part) for part in only.split(",") if part.strip()]
    picked = []
    for entry in manifest["entries"]:
        eid = normalized_id(entry["id"])
        if any(eid == w or eid.startswith(w) for w in wanted):
            picked.append(entry)
    if not picked:
        fail(f"--only matched no preset: {only!r}")
    return picked


def render_all(
    catalog: dict[str, Any],
    out_dir: Path,
    manifest: dict[str, Any],
    cli: Path,
    only: str,
    force: bool,
) -> int:
    entries = selected_entries(manifest, only)
    failures: list[tuple[str, str]] = []
    for index, entry in enumerate(entries, start=1):
        preset_id = entry["id"]
        plan = out_dir / entry["plan"]
        video = out_dir / entry["mp4"]
        print(f"[{index}/{len(entries)}] {preset_id}", flush=True)
        try:
            validate(plan, cli)
            if video.is_file() and not force:
                try:
                    verify_entry(entry, out_dir, catalog)
                    save_manifest(out_dir, manifest)
                    print("  SKIP verified", flush=True)
                    continue
                except Exception:
                    print("  existing clip invalid, re-rendering", flush=True)
            render(plan, video, cli, out_dir / "logs" / f"{preset_id}.log")
            verify_entry(entry, out_dir, catalog)
            save_manifest(out_dir, manifest)
            print(
                f"  PASS {entry['frames']}f · {entry['duration_s']:.2f}s · "
                f"{entry['bytes'] / 1e6:.2f} MB · fg {entry['foreground_ratio']:.2%}",
                flush=True,
            )
        except Exception as error:
            failures.append((preset_id, str(error)))
            print(f"  FAIL {error}", flush=True)
    save_manifest(out_dir, manifest)
    if failures:
        print(f"FAILED {len(failures)}/{len(entries)}")
        for preset_id, error in failures:
            print(f"  {preset_id}: {error}")
        return 1
    print(f"RENDER_PASS {len(entries)}/{len(entries)}")
    return 0


def verify_all(catalog: dict[str, Any], out_dir: Path, manifest: dict[str, Any]) -> int:
    failures = []
    for index, entry in enumerate(manifest["entries"], start=1):
        try:
            verify_entry(entry, out_dir, catalog)
            print(f"[{index}/{len(manifest['entries'])}] PASS {entry['id']}")
        except Exception as error:
            failures.append((entry["id"], str(error)))
            print(f"[{index}/{len(manifest['entries'])}] FAIL {entry['id']}: {error}")
    save_manifest(out_dir, manifest)
    if failures:
        print(f"VERIFY_FAILED {len(failures)}/{len(manifest['entries'])}")
        return 1
    print(f"VERIFY_PASS {len(manifest['entries'])}/{len(manifest['entries'])}")
    return 0


# --------------------------------------------------------------------------- #
# contact sheet
# --------------------------------------------------------------------------- #
def truncate(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont, width: int) -> str:
    if draw.textlength(text, font=font) <= width:
        return text
    suffix = "…"
    while text and draw.textlength(text + suffix, font=font) > width:
        text = text[:-1]
    return text + suffix


def build_contact_sheet(catalog: dict[str, Any], out_dir: Path, manifest: dict[str, Any]) -> Path:
    entries = manifest["entries"]
    missing = [entry["id"] for entry in entries if not (out_dir / entry["still"]).is_file()]
    if missing:
        fail(f"contact sheet needs stills first: {', '.join(missing[:4])}")

    tile_w, tile_h, label_h, gutter = 440, 248, 78, 22
    cols = 4
    rows = math.ceil(len(entries) / cols)
    width = 1920
    header = 128
    margin_x = (width - (cols * tile_w + (cols - 1) * gutter)) // 2
    height = header + rows * (tile_h + label_h) + (rows - 1) * gutter + 34

    sheet = Image.new("RGB", (width, height), (15, 15, 17))
    draw = ImageDraw.Draw(sheet)
    fonts = ASSETS / "assets" / "fonts"
    try:
        title_font = ImageFont.truetype(str(fonts / "Inter-SemiBold.ttf"), 32)
        subtitle_font = ImageFont.truetype(str(fonts / "Inter-Regular.ttf"), 16)
        label_font = ImageFont.truetype(str(fonts / "Inter-SemiBold.ttf"), 18)
        meta_font = ImageFont.truetype(str(fonts / "Inter-Light.ttf"), 13)
    except OSError:
        title_font = subtitle_font = label_font = meta_font = ImageFont.load_default()

    draw.text((margin_x, 30), "TYPOGRAPHY STYLES", font=title_font, fill=(245, 245, 247))
    draw.text(
        (margin_x, 72),
        f"{len(entries)} combinazioni pre-salvate · {catalog['canvas']['width']}×{catalog['canvas']['height']} · "
        f"{catalog['canvas']['fps']} fps · Font / Shadow / Glow selezionabili a runtime",
        font=subtitle_font,
        fill=(168, 168, 176),
    )
    draw.text(
        (width - margin_x, 34),
        f"Drive · {DRIVE_SUBFOLDER}",
        font=meta_font,
        fill=(130, 130, 140),
        anchor="ra",
    )

    for index, entry in enumerate(entries):
        col, row = index % cols, index // cols
        x = margin_x + col * (tile_w + gutter)
        y = header + row * (tile_h + label_h + gutter)
        with Image.open(out_dir / entry["still"]) as raw:
            thumb = raw.convert("RGB").resize((tile_w, tile_h), Image.LANCZOS)
        sheet.paste(thumb, (x, y))
        draw.rectangle((x, y, x + tile_w - 1, y + tile_h - 1), outline=(52, 52, 58), width=1)
        draw.text(
            (x, y + tile_h + 7),
            truncate(draw, f"{index + 1:02d} · {entry['label']}", label_font, tile_w),
            font=label_font,
            fill=(240, 240, 243),
        )
        shadow_label = catalog["shadows"][entry["style"]["shadow"]]["label"]
        glow_label = catalog["glows"][entry["style"]["glow"]]["label"]
        meta = (
            f"{entry['style']['font_family']} · ombra: {shadow_label} · glow: {glow_label}"
        )
        draw.text(
            (x, y + tile_h + 34),
            truncate(draw, meta, meta_font, tile_w),
            font=meta_font,
            fill=(160, 160, 168),
        )
        draw.text(
            (x, y + tile_h + 54),
            f"{entry['duration_s']:.0f}s · {entry['width']}×{entry['height']} · {entry['style']['background']} / "
            f"{entry['style']['fill']}",
            font=meta_font,
            fill=(120, 120, 128),
        )

    path = out_dir / "TYPOGRAPHY_STYLES_contact_sheet_1920x1080.png"
    sheet.save(path, optimize=True)
    manifest["contact_sheet"] = {
        "path": path.name,
        "bytes": path.stat().st_size,
        "sha256": sha256(path),
        "width": sheet.width,
        "height": sheet.height,
        "entries": len(entries),
    }
    save_manifest(out_dir, manifest)
    print(f"CONTACT_SHEET {path} · {sheet.width}x{sheet.height} · {len(entries)} entries")
    return path


# --------------------------------------------------------------------------- #
# Drive
# --------------------------------------------------------------------------- #
def drive_upload(local: Path, name: str) -> dict[str, str]:
    for required in (UPLOADER, CREDENTIALS, TOKEN):
        if not required.exists():
            fail(f"missing Drive prerequisite: {required}")
    result = subprocess.run(
        [
            str(UPLOADER),
            "-credentials",
            str(CREDENTIALS),
            "-token",
            str(TOKEN),
            "-folder",
            DRIVE_FOLDER,
            "-subfolder",
            DRIVE_SUBFOLDER,
            "-file",
            str(local),
            "-name",
            name,
            "-sha256",
            sha256(local),
        ],
        text=True,
        capture_output=True,
        timeout=600,
    )
    output = (result.stdout + "\n" + result.stderr).strip()
    log = OUT / "upload_logs" / f"upload_{name}.log"
    log.parent.mkdir(parents=True, exist_ok=True)
    log.write_text(output + "\n", encoding="utf-8")
    if result.returncode != 0 or "DRIVE_UPLOAD_PASS" not in output:
        fail(f"Drive refused {name}: {output[-1200:]}")
    fields = {
        part.split("=", 1)[0]: part.split("=", 1)[1]
        for part in output.split()
        if "=" in part
    }
    return {"id": fields.get("id", ""), "link": fields.get("link", "")}


def upload_all(catalog: dict[str, Any], out_dir: Path, manifest: dict[str, Any]) -> int:
    unverified = [e["id"] for e in manifest["entries"] if not e.get("verified")]
    if unverified:
        fail(f"upload needs verified clips; run --verify first: {', '.join(unverified[:4])}")
    shot = out_dir / manifest.get("contact_sheet", {}).get("path", "")
    if not shot.is_file():
        fail("upload needs the contact sheet; run --sheet first")

    failures: list[tuple[str, str]] = []
    for index, entry in enumerate(manifest["entries"], start=1):
        if entry.get("uploaded") and entry.get("drive_url"):
            print(f"[{index}/{len(manifest['entries'])}] DRIVE_SKIP {entry['id']}")
            continue
        local = out_dir / entry["mp4"]
        name = f"TYPOGRAPHY_{entry['id'].upper()}_1920x1080.mp4"
        try:
            result = drive_upload(local, name)
            entry.update(uploaded=True, drive_id=result["id"], drive_url=result["link"], drive_name=name)
            save_manifest(out_dir, manifest)
            print(f"[{index}/{len(manifest['entries'])}] DRIVE_PASS {entry['id']} {result['link']}")
        except Exception as error:
            failures.append((entry["id"], str(error)))
            print(f"[{index}/{len(manifest['entries'])}] DRIVE_FAIL {entry['id']}: {error}")

    extras = [
        (shot, "TYPOGRAPHY_STYLES_contact_sheet_1920x1080.png"),
        (out_dir / "catalog" / CATALOG.name, CATALOG.name),
    ]
    for local, name in extras:
        key = name
        if manifest.get("uploads", {}).get(key, {}).get("drive_url"):
            print(f"DRIVE_SKIP {name}")
            continue
        try:
            result = drive_upload(local, name)
            manifest.setdefault("uploads", {})[key] = result | {"uploaded": True}
            save_manifest(out_dir, manifest)
            print(f"DRIVE_PASS {name} {result['link']}")
        except Exception as error:
            failures.append((name, str(error)))
            print(f"DRIVE_FAIL {name}: {error}")

    write_upload_manifest(catalog, out_dir, manifest)
    if manifest.get("uploads", {}).get("TYPOGRAPHY_STYLES_UPLOAD-MANIFEST.md", {}).get("drive_url"):
        print("DRIVE_SKIP TYPOGRAPHY_STYLES_UPLOAD-MANIFEST.md")
    else:
        try:
            result = drive_upload(
                out_dir / "TYPOGRAPHY_STYLES_UPLOAD-MANIFEST.md",
                "TYPOGRAPHY_STYLES_UPLOAD-MANIFEST.md",
            )
            manifest.setdefault("uploads", {})["TYPOGRAPHY_STYLES_UPLOAD-MANIFEST.md"] = result | {
                "uploaded": True
            }
            save_manifest(out_dir, manifest)
            print(f"DRIVE_PASS TYPOGRAPHY_STYLES_UPLOAD-MANIFEST.md {result['link']}")
        except Exception as error:
            failures.append(("TYPOGRAPHY_STYLES_UPLOAD-MANIFEST.md", str(error)))
            print(f"DRIVE_FAIL TYPOGRAPHY_STYLES_UPLOAD-MANIFEST.md: {error}")

    if failures:
        print(f"UPLOAD_FAILED {len(failures)}")
        return 1
    print(f"UPLOAD_PASS {len(manifest['entries'])}/{len(manifest['entries'])} + extras")
    return 0


def write_upload_manifest(catalog: dict[str, Any], out_dir: Path, manifest: dict[str, Any]) -> None:
    lines = [
        "# Typography Styles — Font / Shadow / Glow",
        "",
        f"Drive: {DRIVE_FOLDER_URL}",
        f"Sottocartella: `{DRIVE_SUBFOLDER}`",
        "",
        f"Canvas: {catalog['canvas']['width']}×{catalog['canvas']['height']}, "
        f"{catalog['canvas']['fps']} fps, H.264 QP 18.",
        "Ogni clip mostra la stessa frase con una combinazione pre-salvata diversa.",
        "",
        "| # | Preset | Font | Ombra | Glow | Clip |",
        "|---|---|---|---|---|---|",
    ]
    for index, entry in enumerate(manifest["entries"], start=1):
        link = f"[apri]({entry['drive_url']})" if entry.get("drive_url") else "—"
        shadow = catalog["shadows"][entry["style"]["shadow"]]["label"]
        glow = catalog["glows"][entry["style"]["glow"]]["label"]
        lines.append(
            f"| {index:02d} | {entry['label']} | {entry['style']['font_family']} | "
            f"{shadow} | {glow} | {link} |"
        )
    sheet = manifest.get("contact_sheet", {})
    sheet_upload = manifest.get("uploads", {}).get("TYPOGRAPHY_STYLES_contact_sheet_1920x1080.png", {})
    if sheet:
        lines += [
            "",
            f"Contact sheet: {sheet_upload.get('link') or sheet.get('path', '')}",
        ]
    lines += [
        "",
        "## Come si sceglie a runtime",
        "",
        "```sh",
        "ChrononTemplate/tools/typography/typography_gallery.py --list",
        "ChrononTemplate/tools/typography/typography_gallery.py --preset 02_playfair_carta \\",
        "  --font bodoni_moda --shadow ink_editorial --glow gold_glow \\",
        "  --text \"La memoria è il primo testimone\" \\",
        "  --plan-out /tmp/phrase.plan.json --render --output /tmp/phrase.mp4",
        "```",
        "",
        "Il preset sceglie la combinazione; `--font`, `--shadow` e `--glow` la"
        " sovrascrivono senza toccare il catalogo.",
    ]
    (out_dir / "TYPOGRAPHY_STYLES_UPLOAD-MANIFEST.md").write_text(
        "\n".join(lines) + "\n", encoding="utf-8"
    )


# --------------------------------------------------------------------------- #
# entry point
# --------------------------------------------------------------------------- #
def main() -> int:
    global OUT
    parser = argparse.ArgumentParser(
        description="Runtime phrase typography: pre-saved Font/Shadow/Glow combinations.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--list", action="store_true", help="list families, presets and selectable axes")
    parser.add_argument("--preset", help="preset id (or unique prefix)")
    parser.add_argument("--font", help="runtime font id override")
    parser.add_argument("--shadow", help="runtime shadow id override")
    parser.add_argument("--glow", help="runtime glow id override")
    parser.add_argument("--fill", help="runtime text color override (#RRGGBB)")
    parser.add_argument("--background", help="runtime background color override (#RRGGBB)")
    parser.add_argument("--font-size", type=float, help="runtime font size override")
    parser.add_argument("--text", help="phrase to render (default: catalog phrase)")
    parser.add_argument("--duration", type=float, default=8.0, help="clip length in seconds (max 10)")
    parser.add_argument("--show", action="store_true", help="print the resolved selection and plan")
    parser.add_argument("--plan-out", help="write one plan to this path")
    parser.add_argument("--render", action="store_true", help="render the selected preset")
    parser.add_argument("--output", help="output MP4 for --render")
    parser.add_argument("--out-dir", default=str(DEFAULT_OUT), help="gallery output directory")
    parser.add_argument("--all", action="store_true", help="emit every preset")
    parser.add_argument("--only", default="", help="comma-separated preset ids for render/verify")
    parser.add_argument("--force", action="store_true", help="re-render clips that already exist")
    parser.add_argument("--verify", action="store_true", help="probe clips, decode stills, check visibility")
    parser.add_argument("--sheet", action="store_true", help="build the 1920-wide contact sheet")
    parser.add_argument("--upload", action="store_true", help="upload the verified gallery to Drive")
    parser.add_argument("--gallery", action="store_true", help="emit + render + verify + contact sheet")
    args = parser.parse_args()

    catalog = load_catalog()
    OUT = Path(args.out_dir).expanduser().resolve()
    text = args.text or catalog["default_phrase"]

    if args.list:
        return cmd_list(catalog)
    if args.show:
        if not args.preset:
            fail("--show needs --preset")
        return cmd_show(catalog, args)
    if args.preset:
        return cmd_emit_one(catalog, args)

    if args.gallery:
        manifest = emit_all(catalog, OUT, text, args.duration)
        cli = find_cli()
        result = render_all(catalog, OUT, manifest, cli, args.only, args.force)
        if result != 0:
            return result
        if verify_all(catalog, OUT, manifest) != 0:
            return 1
        build_contact_sheet(catalog, OUT, manifest)
        return 0

    if args.all or args.verify or args.sheet or args.upload:
        manifest = load_manifest(OUT, catalog, text, args.duration)
        if args.all:
            manifest = emit_all(catalog, OUT, text, args.duration)
        if args.render and not args.verify and not args.sheet and not args.upload:
            cli = find_cli()
            result = render_all(catalog, OUT, manifest, cli, args.only, args.force)
            if result != 0:
                return result
            manifest = load_manifest(OUT, catalog, text, args.duration)
        if args.verify:
            if verify_all(catalog, OUT, manifest) != 0:
                return 1
            manifest = load_manifest(OUT, catalog, text, args.duration)
        if args.sheet:
            if build_contact_sheet(catalog, OUT, manifest) is None:
                return 1
            manifest = load_manifest(OUT, catalog, text, args.duration)
        if args.upload:
            if upload_all(catalog, OUT, manifest) != 0:
                return 1
        return 0

    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
