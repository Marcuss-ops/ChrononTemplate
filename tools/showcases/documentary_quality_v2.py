#!/usr/bin/env python3
"""Author and render five Documentary Graphics 2.0 reference scenes.

No browser, new renderer, duplicated path rasterizer, or network access is used.
The plans use canonical RenderPlan V3 text/image/shape/path layers. Text spans
are resolved by the renderer's native shaping/layout path; the restrained glow
connector is shared with the GlowLine DocusPremium composer.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys

HERE = Path(__file__).resolve()
TEMPLATE = HERE.parents[2]
ROOT = TEMPLATE.parent
OUT = TEMPLATE / "out/documentary_quality_v2"
CLI = ROOT / "Chronon3d/build/chronon/linux-video-fast-dev/apps/chronon3d_cli/chronon3d_cli"
W, H, FPS, FRAMES = 1920, 1080, 30, 240
IVORY, PAPER, INK, MUTED = "#F2EFE6", "#E7E0D2", "#1E2322", "#626762"
AMBER, RED, SLATE = "#B8874B", "#A94435", "#252B2D"
FONT = "Chronon3d/assets/fonts/Inter-Regular.ttf"
BOLD = "Chronon3d/assets/fonts/Inter-Bold.ttf"
SOURCE_PHOTO = "Chronon3d/assets/editorial/industrial_port_dawn.png"
PHOTO = "ChrononTemplate/out/documentary_quality_v2/assets/industrial_port_dawn.jpg"

spec = importlib.util.spec_from_file_location(
    "glow_line_composers", TEMPLATE / "tools/glow_line/glow_line_composers.py")
if spec is None or spec.loader is None:
    raise RuntimeError("cannot load shared documentary path-stroke composer")
_glow = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = _glow
spec.loader.exec_module(_glow)


def rgba(hex_color: str, alpha: float = 1.0) -> list[float]:
    c = hex_color.lstrip("#")
    return [int(c[i:i + 2], 16) / 255 for i in (0, 2, 4)] + [alpha]


def base(name: str, color: str = SLATE) -> dict:
    return {"schema": "chronon.render-plan.v3", "version": 3,
            "job_id": name,
            "canvas": {"width": W, "height": H, "fps_num": FPS,
                       "fps_den": 1, "duration_frames": FRAMES},
            "output": {"path": f"{name}.mp4", "format": "mp4", "codec": "h264"},
            "layers": [{"id": "ground", "type": "color", "color": rgba(color),
                        "size": [W, H], "position": [0, 0], "screen_space": True,
                        "start_frame": 0, "duration_frames": FRAMES}]}


def rect(id_: str, x: float, y: float, w: float, h: float, fill: str,
         *, opacity: float = 1, radius: float = 0, animation: dict | None = None) -> dict:
    shape = {"type": "rounded_rect" if radius else "rect", "fill": rgba(fill)}
    if radius:
        shape["radius"] = radius
    layer = {"id": id_, "type": "shape", "shape": shape, "size": [w, h],
             "position": [x, y], "screen_space": True, "opacity": opacity,
             "start_frame": 0, "duration_frames": FRAMES}
    if animation:
        layer["animation"] = {"tracks": animation}
    return layer


def text(id_: str, words: str, x: float, y: float, w: float, h: float,
         size: float, fill: str = INK, font: str = FONT,
         *, spans: list[dict] | None = None, start: int = 0,
         animation: dict | None = None, align: str | None = None) -> dict:
    style = {"font": font, "font_size": size, "fill": fill,
             "min_font_size": size, "max_font_size": size,
             "fit_mode": "shrink_only"}
    layer = {"id": id_, "type": "text", "text": words,
             "size": [w, h], "position": [x, y], "screen_space": True,
             "style": style, "start_frame": start,
             "duration_frames": FRAMES - start}
    if spans:
        layer["spans"] = spans
    if animation:
        layer["animation"] = {"tracks": animation}
    return layer


def image(id_: str, asset: str, x: float, y: float, w: float, h: float,
          fit: str = "cover", animation: dict | None = None) -> dict:
    layer = {"id": id_, "type": "image", "asset": asset,
             "size": [w, h], "position": [x, y], "fit": fit,
             "screen_space": True, "start_frame": 0, "duration_frames": FRAMES}
    if animation:
        layer["animation"] = {"tracks": animation}
    return layer


def track(prop: str, pairs: list[tuple[int, float]], easing: str = "in_out_sine") -> dict:
    return {"property": prop, "easing": easing,
            "keyframes": [{"frame": f, "value": v} for f, v in pairs]}


def span(content: str, phrase: str, semantic: str, color: str = AMBER,
         alpha: float = .30) -> dict:
    start = content.index(phrase)
    end = start + len(phrase)
    # RenderPlan text spans index UTF-8 bytes; use encoded lengths for accents.
    byte_start = len(content[:start].encode("utf-8"))
    byte_end = byte_start + len(phrase.encode("utf-8"))
    opacity = round(alpha * 255)
    suffix = f"{opacity:02X}"
    return {"start": byte_start, "end": byte_end, "semantic_id": semantic,
            "style": {"highlight": {"background": color + suffix,
                                     "padding_em": .08, "radius_em": .04}}}


def article() -> dict:
    p = base("01_documentary_article_highlight", "#D9D4C9")
    l = p["layers"]
    l += [rect("paper-sheet", 190, 92, 1540, 896, "#F3EFE5"),
          rect("masthead-rule", 260, 202, 1400, 2, "#B7B0A2"),
          text("masthead", "THE ARCHIVE REVIEW", 260, 128, 1000, 56, 38, INK, BOLD),
          text("issue", "INVESTIGATION  /  VOL. 04    ·    AUTUMN 1974", 1280, 142, 380, 34, 20, MUTED),
          text("section", "RECORDS & ROUTES", 260, 238, 700, 38, 23, AMBER, BOLD),
          text("headline", "The missing report\nfrom the harbor office", 260, 300, 780, 180, 66, INK, BOLD),
          text("standfirst", "A transfer recorded in the ledger points to a second copy, filed under a different date.",
               260, 495, 760, 104, 34, "#444945"),
          image("archive-photo", PHOTO, 1090, 274, 570, 350),
          text("photo-caption", "PORT OFFICE, EAST QUAY  /  ARCHIVE FRAME 01", 1090, 640, 570, 50, 20, MUTED),
          rect("body-rule", 260, 720, 1400, 2, "#B7B0A2"),
          text("body-copy", "The entry was overlooked.\n\nThe date, not the amount, changed the sequence.\nA duplicate was logged three days later.",
               260, 756, 1130, 170, 29, INK, FONT,
               spans=[span("The entry was overlooked.\n\nThe date, not the amount, changed the sequence.\nA duplicate was logged three days later.",
                            "date, not the amount", "article-date-detail")]),
          text("folio", "12  /  28", 1515, 920, 145, 34, 20, MUTED, FONT)]
    return p


def evidence_connection() -> dict:
    p = base("02_cinematic_evidence_connection", "#252A2A")
    l = p["layers"]
    l += [text("kicker", "INVESTIGATION  /  CONNECTION", 150, 112, 860, 42, 25, AMBER, BOLD),
          text("headline", "Two records.\nOne overlooked link.", 150, 184, 700, 174, 72, IVORY, BOLD),
          image("archive-source", PHOTO, 150, 420, 650, 430),
          rect("ledger-card", 1090, 395, 650, 455, "#EAE5DA"),
          text("ledger-heading", "TRANSFER REGISTER  /  FOLIO 08", 1140, 438, 550, 40, 23, MUTED, BOLD),
          rect("ledger-rule", 1140, 496, 550, 2, "#B9B3A7"),
          text("ledger-row1", "17 OCT 1974     COPY RECEIVED", 1140, 530, 550, 48, 27, INK),
          text("ledger-row2", "21 OCT 1974     ORIGINAL FILED", 1140, 610, 550, 48, 27, INK,
               spans=[span("21 OCT 1974     ORIGINAL FILED", "21 OCT 1974", "register-date")]),
          text("ledger-row3", "REF.  /  HARBOR OFFICE", 1140, 690, 550, 48, 24, MUTED),
          text("source-caption", "ARCHIVE PHOTOGRAPH  /  EAST QUAY", 150, 874, 660, 40, 22, IVORY),
          text("method-caption", "Editorial reconstruction · records shown as illustrative material",
               150, 946, 1300, 38, 20, "#B9BCB5")]
    # Connector terminates on the highlighted ledger date, not an arbitrary point.
    l.extend(_glow.build_docus_premium_documentary_layers(
        "date_connection", [(805, 620), (940, 620), (1012, 655), (1134, 655)],
        66, 126, FRAMES, AMBER))
    return p


def multiline_marker() -> dict:
    p = base("03_professional_multiline_marker", "#E9E3D6")
    l = p["layers"]
    l += [rect("document", 220, 92, 1480, 900, "#F6F1E7"),
          text("kicker", "ARCHIVE / DOCUMENT 1974", 315, 160, 950, 42, 24, AMBER, BOLD),
          text("headline", "The Missing Report", 315, 224, 1150, 92, 78, INK, BOLD),
          text("deck", "The investigation uncovered a previously unknown transfer of documents.",
               315, 342, 1170, 70, 36, "#414743"),
          rect("copy-rule", 315, 447, 1285, 2, "#B9B2A4")]
    lines = [
        ("line-1", "The evidence was overlooked in the first review.", "overlooked", 510),
        ("line-2", "A second copy appears three days after the original.", "three days", 606),
        ("line-3", "Its date changes the sequence of events.", "changes the sequence", 702),
    ]
    for lid, content, phrase, y in lines:
        l.append(text(lid, content, 315, y, 1285, 60, 38, INK,
                      spans=[span(content, phrase, lid + "-target")]))
    l += [image("document-photo", PHOTO, 315, 800, 320, 150),
          text("source-note", "Source image / east quay archive", 670, 820, 820, 54, 25, MUTED),
          text("folio", "EVIDENCE 03  ·  PARAGRAPHS 1–3", 670, 878, 860, 40, 21, AMBER, BOLD)]
    return p


def data_visualization() -> dict:
    p = base("04_documentary_data_visualization", "#F1EEE6")
    l = p["layers"]
    l += [text("kicker", "FINANCIAL DOCUMENTARY  /  DATA", 150, 105, 950, 42, 25, AMBER, BOLD),
          text("headline", "A 6.2% increase", 150, 175, 970, 100, 80, INK, BOLD),
          text("deck", "Change across the reporting period · illustrative dataset", 155, 286, 1200, 56, 31, MUTED),
          rect("chart-panel", 150, 390, 1620, 500, "#E7E2D8"),
          text("chart-title", "REPORTED TRANSFERS  /  INDEXED VALUE", 220, 430, 1200, 42, 23, MUTED, BOLD)]
    values = [42, 46, 48, 53, 55, 61]
    labels = ["Q1", "Q2", "Q3", "Q4", "Q1", "Q2"]
    x0, ybase, barw, gap, max_height = 285, 790, 112, 135, 260
    for i, (value, label) in enumerate(zip(values, labels)):
        x = x0 + i * gap
        height = max_height * value / max(values)
        color = AMBER if i == len(values) - 1 else "#8E9690"
        l.append(rect(f"bar-{i}", x, ybase-height, barw, height, color,
                      animation=[track("scale_y", [(0, .01), (48+i*8, 1), (FRAMES-1, 1)])]))
        l.append(text(f"bar-value-{i}", str(value), x-6, ybase-height-46, barw+12, 38, 24, INK, BOLD,
                      start=38+i*8, animation=[track("opacity", [(0, 0), (12, 1), (FRAMES-1, 1)])], align="center"))
        l.append(text(f"period-{i}", label, x-4, ybase+22, barw+8, 38, 22, MUTED, FONT, align="center"))
    l += [rect("baseline", 250, ybase, 1135, 2, "#727973"),
          text("chart-foot", "Source note: values are illustrative; not historical financial data.",
               220, 835, 1200, 34, 18, MUTED),
          text("growth", "+6.2%", 1450, 566, 270, 82, 50, AMBER, BOLD, align="center"),
          text("growth-note", "OVER THE PERIOD", 1450, 646, 270, 38, 20, MUTED, BOLD, align="center")]
    return p


def master() -> dict:
    p = base("05_documentary_master_composition", "#252A2A")
    l = p["layers"]
    l += [text("kicker", "ARCHIVE / DOCUMENT 1974", 145, 105, 950, 40, 24, AMBER, BOLD),
          text("headline", "The Missing\nReport", 145, 164, 780, 180, 82, IVORY, BOLD),
          text("standfirst", "One overlooked date connects the photograph to a second filing.",
               145, 375, 700, 90, 34, "#CFD0C9"),
          image("hero-archive-photo", PHOTO, 145, 520, 750, 430,
                animation=[track("scale", [(0, 1), (239, 1.035)])]),
          text("photo-caption", "EAST QUAY  /  ARCHIVE FRAME 01", 145, 968, 750, 34, 20, "#CFD0C9"),
          rect("record-card", 1080, 485, 700, 420, "#EAE5DA"),
          text("record-kicker", "TRANSFER REGISTER  /  FOLIO 08", 1132, 530, 590, 40, 22, MUTED, BOLD),
          rect("record-rule", 1132, 586, 590, 2, "#B9B3A7"),
          text("record-line-1", "17 OCT 1974     COPY RECEIVED", 1132, 622, 590, 50, 27, INK),
          text("record-line-2", "21 OCT 1974     ORIGINAL FILED", 1132, 704, 590, 50, 27, INK,
               spans=[span("21 OCT 1974     ORIGINAL FILED", "21 OCT 1974", "master-date")]),
          text("record-line-3", "REF.  /  HARBOR OFFICE", 1132, 786, 590, 46, 23, MUTED),
          text("source-note", "Illustrative editorial reconstruction", 1080, 930, 700, 36, 19, "#CFD0C9")]
    l.extend(_glow.build_docus_premium_documentary_layers(
        "master_evidence_link", [(895, 746), (980, 746), (1030, 729), (1122, 729)],
        84, 144, FRAMES, AMBER))
    return p


BUILDERS = [article, evidence_connection, multiline_marker, data_visualization, master]


def prepare_photo_asset(out: Path) -> Path:
    """Create a documentary source still below the 1 MB per-image budget."""
    from PIL import Image
    source = ROOT / SOURCE_PHOTO
    if not source.is_file():
        raise FileNotFoundError(source)
    destination = out / "assets/industrial_port_dawn.jpg"
    destination.parent.mkdir(parents=True, exist_ok=True)
    with Image.open(source) as original:
        image = original.convert("RGB")
        lanczos = getattr(Image, "Resampling", Image).LANCZOS
        image.thumbnail((1440, 960), lanczos)
        image.save(destination, format="JPEG", quality=78, optimize=True, progressive=True)
    if destination.stat().st_size >= 1_000_000:
        raise RuntimeError(f"optimized documentary image exceeds 1 MB: {destination.stat().st_size} bytes")
    return destination


def emit(out: Path = OUT) -> list[Path]:
    if not (ROOT / SOURCE_PHOTO).is_file():
        raise FileNotFoundError(ROOT / SOURCE_PHOTO)
    if not (ROOT / FONT).is_file() or not (ROOT / BOLD).is_file():
        raise FileNotFoundError("required Inter fonts are missing")
    out.mkdir(parents=True, exist_ok=True)
    prepare_photo_asset(out)
    paths = []
    for build in BUILDERS:
        plan = build()
        relative_photo = os.path.relpath(out.resolve() / "assets/industrial_port_dawn.jpg", ROOT)
        for layer in plan["layers"]:
            if layer.get("asset") == SOURCE_PHOTO:
                layer["asset"] = relative_photo
        name = plan["job_id"]
        plan["output"]["path"] = str((out / f"{name}.mp4").resolve())
        path = out / f"{name}.plan.json"
        path.write_text(json.dumps(plan, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        paths.append(path)
    return paths


def checked(command: list[str], cwd: Path = ROOT) -> None:
    result = subprocess.run(command, cwd=cwd, stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT, text=True)
    if result.returncode:
        tail = "\n".join(result.stdout.splitlines()[-50:])
        raise RuntimeError(f"command failed ({result.returncode}): {' '.join(command)}\n{tail}")


def render_all(out: Path = OUT, cli: Path = CLI) -> None:
    if not cli.is_file():
        raise FileNotFoundError(f"Chronon3D CLI missing: {cli}")
    plans = emit(out)
    # Remove only partial/intermediate files owned by this suite. Keep final
    # MP4s, plans, the source still, preview frames and manifest if rerunning.
    for pattern in ("*.partial.mp4", "*.repeat.mp4", "*.repeat.png", "*.rgba",
                    "*.repeat.rgba", "*.middle.rgba.png", "*.repeat.rgba.png",
                    "*.repeat.mp4.timing.json", "*.rgba.timing.json",
                    "*.repeat.rgba.timing.json", "*.middle.rgba.timing.json"):
        for temporary in out.glob(pattern):
            temporary.unlink()
    for plan in plans:
        name = plan.name.removesuffix(".plan.json")
        video = out / f"{name}.mp4"
        checked([str(cli), "render", "--plan", str(plan), "--assets-root", str(ROOT),
                 "--backend", "software", "--profile", "production", "--fps", "30",
                 "--rate-control", "crf", "--crf", "20", "--preset", "medium",
                 "--ffmpeg-mode", "pipe", "-o", str(video)])
        info = json.loads(subprocess.check_output([
            "ffprobe", "-v", "error", "-count_frames", "-select_streams", "v:0",
            "-show_entries", "stream=codec_name,width,height,avg_frame_rate,nb_read_frames,duration",
            "-of", "json", str(video)], text=True))["streams"][0]
        if (info.get("codec_name"), int(info.get("width", 0)), int(info.get("height", 0)),
            info.get("avg_frame_rate"), int(info.get("nb_read_frames", 0))) != ("h264", W, H, "30/1", FRAMES):
            raise RuntimeError(f"invalid video stream {name}: {info}")
        if abs(float(info.get("duration", 0)) - FRAMES / FPS) > .001:
            raise RuntimeError(f"invalid video duration {name}: {info}")
        # Decode representative frames through the exact output interface.
        for tag, frame in (("start", 0), ("middle", 120), ("end", 239)):
            png = out / f"{name}.{tag}.png"
            checked(["ffmpeg", "-y", "-v", "error", "-i", str(video), "-vf",
                     f"select=eq(n\\,{frame})", "-frames:v", "1", str(png)])
        # Repeat the midpoint through the raw pixel-truth sink. Encoded PNGs
        # may differ by metadata; raw RGBA hashes are a direct determinism check.
        repeat = out / f"{name}.repeat.rgba"
        reference = out / f"{name}.middle.rgba"
        reference_png = out / f"{name}.middle.rgba.png"
        repeat_png = out / f"{name}.repeat.rgba.png"
        checked([str(cli), "render", "--plan", str(plan), "--assets-root", str(ROOT),
                 "--backend", "software", "--profile", "production", "--start-frame", "120",
                 "--end-frame", "120", "--video-sink", "raw", "--pipe-pixfmt", "rgba",
                 "-o", str(repeat)])
        raw_frame = repeat.read_bytes()
        if len(raw_frame) != W * H * 4:
            raise RuntimeError(f"raw midpoint has {len(raw_frame)} bytes for {name}")
        checked([str(cli), "render", "--plan", str(plan), "--assets-root", str(ROOT),
                 "--backend", "software", "--profile", "production", "--start-frame", "120",
                 "--end-frame", "120", "--video-sink", "raw", "--pipe-pixfmt", "rgba",
                 "-o", str(reference)])
        expected_frame = reference.read_bytes()
        if len(expected_frame) != W * H * 4:
            raise RuntimeError(f"reference raw midpoint has {len(expected_frame)} bytes for {name}")
        if hashlib.sha256(expected_frame).digest() != hashlib.sha256(raw_frame).digest():
            raise RuntimeError(f"raw midpoint render is not deterministic for {name}")
        for tag, source in (("reference", reference), ("repeat", repeat)):
            png = reference_png if tag == "reference" else repeat_png
            checked(["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pixel_format", "rgba",
                     "-video_size", f"{W}x{H}", "-i", str(source), "-frames:v", "1", str(png)])
        reference.unlink()
        repeat.unlink()
        reference_png.unlink()
        repeat_png.unlink()
    photo_asset = out / "assets/industrial_port_dawn.jpg"
    manifest = {"resolution": [W, H], "fps": FPS, "duration_seconds": FRAMES/FPS,
                "backend": "software", "codec": "h264", "upload_performed": False,
                "photo_asset": {"path": "assets/industrial_port_dawn.jpg",
                                "bytes": photo_asset.stat().st_size,
                                "max_bytes": 999999},
                "videos": []}
    for plan in plans:
        name = plan.name.removesuffix(".plan.json")
        video = out / f"{name}.mp4"
        manifest["videos"].append({"name": name, "plan": plan.name,
            "video": video.name, "bytes": video.stat().st_size,
            "sha256": hashlib.sha256(video.read_bytes()).hexdigest(),
            "frames": {tag: f"{name}.{tag}.png" for tag in ("start", "middle", "end")},
            "determinism": "PASS"})
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=OUT)
    parser.add_argument("--cli", type=Path, default=CLI)
    parser.add_argument("--render", action="store_true")
    args = parser.parse_args()
    args.out = args.out.resolve()
    args.cli = args.cli.resolve()
    plans = emit(args.out)
    print(f"Emitted {len(plans)} documentary-quality V3 plans to {args.out}")
    if args.render:
        render_all(args.out, args.cli)
        print(f"Rendered and verified five H.264 MP4s in {args.out}")


if __name__ == "__main__":
    main()
