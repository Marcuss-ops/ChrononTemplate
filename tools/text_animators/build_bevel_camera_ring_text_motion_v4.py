#!/usr/bin/env python3
"""Render/upload driver for the CameraRing_Text 07-12 v4 HDR bloom series.

The six plans are authored in C++ by
`chronontemplate_emit_camera_ring_text_v4_hdr_bloom` (tools/text_animators).
That emitter owns the recipe: 132 px lowercase text, dark vignetted plate,
64-tap camera ring with bilinear tile sampling, one native HDR bloom layer
(6-mip RGBA16F pyramid, Karis prefilter, additive composite), catalog film
grain, bezier push-in with micro-drift, fade and tracking settle. It writes
`plans/series.json`, the single source of truth for ids, durations, fonts,
plan paths and output names.

This Python file is only the orchestration layer: it validates the emitted
plans, renders them through Chronon3D's strict GPU path with ACES at the
output boundary, verifies the MP4s and uploads them to Drive. It never builds
or edits RenderPlan JSON.

Usage
-----
    chronontemplate_emit_camera_ring_text_v4_hdr_bloom \
        RenderingGen/UploadDrive/camera_ring_text_v4_hdr_bloom_20261109/plans Chronon3d
    python3 ChrononTemplate/tools/text_animators/build_bevel_camera_ring_text_motion_v4.py \
        --render --upload
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

from PIL import Image, ImageChops, ImageStat

ROOT = Path(__file__).resolve().parents[2]          # ChrononTemplate
REPO = ROOT.parent
ASSETS = REPO / "Chronon3d"
OUT = REPO / "RenderingGen" / "UploadDrive" / "camera_ring_text_v4_hdr_bloom_20261109"
SERIES = OUT / "plans" / "series.json"
CLI = ASSETS / "build/chronon/linux-video-release/apps/chronon3d_cli/chronon3d_cli"
UPLOADER = REPO / "RenderingGen" / "bin" / "drive-upload"
CREDENTIALS = REPO / "RenderingGen" / "UploadDrive" / "credentials.json"
TOKEN = REPO / "RenderingGen" / "UploadDrive" / "token.json"
EMITTER = "chronontemplate_emit_camera_ring_text_v4_hdr_bloom"

WIDTH, HEIGHT, FPS = 1920, 1080, 30
DRIVE_FOLDER = "1J_xUGo_bchzXDIGqSX04CU44c_Dm3SxS"
DRIVE_URL = f"https://drive.google.com/drive/u/1/folders/{DRIVE_FOLDER}"
REFERENCE_DIR = "Chronon3d/docs/evidence/camera-ring-text-drive-20261108"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def merge_existing(entries: list[dict[str, Any]]) -> None:
    path = OUT / "manifest.json"
    if not path.is_file():
        return
    try:
        previous = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return
    by_id = {clip["id"]: clip for clip in previous.get("clips", [])}
    for entry in entries:
        old = by_id.get(entry["id"])
        if not old:
            continue
        for key in (
            "width", "height", "fps", "frames", "duration_s", "bytes", "sha256",
            "verified", "verified_at", "foreground_ratio", "foreground_ratios",
            "stills", "uploaded", "drive_id", "drive_url", "drive_name",
            "upload_manifest_url",
        ):
            if key in old:
                entry[key] = old[key]


def load_series() -> list[dict[str, Any]]:
    """Read the C++-emitted series; never author plan data here."""
    if not SERIES.is_file():
        raise SystemExit(
            f"missing {SERIES}\n"
            f"build and run the C++ emitter first:\n"
            f"  cmake --build ChrononTemplate/build/dev-fast --target {EMITTER}\n"
            f"  ChrononTemplate/build/dev-fast/{EMITTER} "
            f"{SERIES.parent} Chronon3d"
        )
    try:
        series = json.loads(SERIES.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise SystemExit(f"invalid {SERIES}: {error}") from error
    if series.get("generator") != EMITTER:
        raise SystemExit(f"{SERIES} was not emitted by {EMITTER}")
    canvas = series.get("canvas", {})
    if (canvas.get("width"), canvas.get("height"), canvas.get("fps")) != (WIDTH, HEIGHT, FPS):
        raise SystemExit(f"unexpected series canvas: {canvas}")

    entries = series.get("clips", [])
    if len(entries) != 6:
        raise SystemExit(f"expected 6 clips in {SERIES}, found {len(entries)}")
    seen: set[str] = set()
    for entry in entries:
        clip_id = entry.get("id", "")
        if not clip_id or clip_id in seen:
            raise SystemExit(f"missing/duplicate clip id: {clip_id!r}")
        seen.add(clip_id)
        plan = OUT / entry["plan"]
        if not plan.is_file():
            raise SystemExit(f"missing C++ plan for {clip_id}: {plan}")
        if not entry.get("mp4") or not entry.get("drive_name"):
            raise SystemExit(f"incomplete series entry for {clip_id}")
        if int(entry.get("font_size", 0)) != 132:
            raise SystemExit(f"{clip_id}: C++ plan is not using 132 px text")
        if not 1 <= int(entry.get("frames", 0)) <= 10 * FPS:
            raise SystemExit(f"{clip_id}: duration is outside 1..10 s")
    merge_existing(entries)
    print(f"SERIES {SERIES.relative_to(REPO)} ({len(entries)} clips from C++)")
    return entries


def validate(plan: Path) -> None:
    result = subprocess.run(
        [str(CLI), "validate", "--plan", str(plan), "--assets-root", str(ASSETS)],
        cwd=REPO, text=True, capture_output=True,
    )
    if result.returncode != 0:
        tail = (result.stdout + result.stderr).strip().splitlines()[-10:]
        raise SystemExit(f"validation failed for {plan.name}: " + " | ".join(tail))


def render(entry: dict[str, Any]) -> None:
    plan = OUT / entry["plan"]
    video = OUT / entry["mp4"]
    video.parent.mkdir(parents=True, exist_ok=True)
    log = OUT / "logs" / f"{entry['id']}.log"
    log.parent.mkdir(parents=True, exist_ok=True)
    command = [
        str(CLI), "render",
        "--plan", str(plan),
        "--assets-root", str(ASSETS),
        "--backend", "vulkan",
        "--gpu-hot-path-mode", "require_gpu_native",
        "--tone-map", "aces",
        "--exposure", "1.0",
        "-o", str(video),
    ]
    validate(plan)
    started = time.time()
    with log.open("w", encoding="utf-8") as handle:
        handle.write(" ".join(command) + "\n\n")
        handle.flush()
        result = subprocess.run(command, cwd=REPO, stdout=handle, stderr=subprocess.STDOUT)
    if result.returncode != 0:
        tail = log.read_text(encoding="utf-8", errors="replace").strip().splitlines()[-12:]
        raise SystemExit(f"render failed for {entry['id']}: " + " | ".join(tail))
    print(f"RENDER {entry['id']} in {time.time() - started:.1f}s")


def probe(video: Path) -> dict[str, Any]:
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-count_frames", "-select_streams", "v:0",
         "-show_entries", "stream=width,height,nb_read_frames,r_frame_rate:format=duration,size",
         "-of", "json", str(video)],
        check=True, text=True, capture_output=True,
    )
    data = json.loads(result.stdout)
    stream = data["streams"][0]
    return {
        "width": int(stream["width"]), "height": int(stream["height"]),
        "fps": stream.get("r_frame_rate", "30/1"),
        "frames": int(stream.get("nb_read_frames") or 0),
        "duration_s": round(float(data["format"]["duration"]), 3),
        "bytes": int(data["format"]["size"]),
    }


def still(video: Path, path: Path, seconds: float) -> Image.Image:
    path.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        ["ffmpeg", "-y", "-v", "error", "-ss", f"{seconds:.3f}", "-i", str(video),
         "-frames:v", "1", "-update", "1", str(path)],
        check=True, cwd=REPO,
    )
    with Image.open(path) as image:
        return image.convert("RGB").copy()


def verify(entry: dict[str, Any]) -> None:
    video = OUT / entry["mp4"]
    info = probe(video)
    if (info["width"], info["height"]) != (WIDTH, HEIGHT):
        raise SystemExit(f"{entry['id']}: expected 1920x1080, got {info['width']}x{info['height']}")
    if info["frames"] != entry["frames"]:
        raise SystemExit(f"{entry['id']}: expected {entry['frames']} frames, got {info['frames']}")
    expected = entry["frames"] / FPS
    if abs(info["duration_s"] - expected) > 0.15:
        raise SystemExit(f"{entry['id']}: expected {expected:.2f}s, got {info['duration_s']:.2f}s")

    ratios = []
    for tag, fraction in (("early", 0.18), ("mid", 0.55), ("late", 0.88)):
        frame = still(video, OUT / "stills" / f"{entry['id']}_{tag}.png", expected * fraction)
        bg = Image.new("RGB", (WIDTH, HEIGHT), tuple(int(c * 255) for c in entry["background_rgb"]))
        diff = ImageChops.difference(frame, bg).convert("L")
        changed = sum(diff.histogram()[40:]) / float(WIDTH * HEIGHT)
        if changed < 0.0004:
            raise SystemExit(f"{entry['id']}: empty frame at {fraction:.0%} ({changed:.4%})")
        if max(ImageStat.Stat(frame).stddev) < 1.0:
            raise SystemExit(f"{entry['id']}: flat frame at {fraction:.0%}")
        ratios.append(round(changed, 6))

    entry.update(
        width=info["width"], height=info["height"], fps=info["fps"],
        frames=info["frames"], duration_s=info["duration_s"], bytes=info["bytes"],
        sha256=sha256(video), verified=True,
        verified_at=time.strftime("%Y-%m-%dT%H:%M:%S"),
        foreground_ratio=ratios[1], foreground_ratios=ratios,
        stills=[f"stills/{entry['id']}_{tag}.png" for tag in ("early", "mid", "late")],
    )
    print(f"VERIFY {entry['id']} {info['width']}x{info['height']} {info['frames']}f fg={ratios}")


def upload(local: Path, name: str) -> dict[str, str]:
    for required in (UPLOADER, CREDENTIALS, TOKEN):
        if not required.exists():
            raise SystemExit(f"missing Drive prerequisite: {required}")
    result = subprocess.run(
        [str(UPLOADER), "-credentials", str(CREDENTIALS), "-token", str(TOKEN),
         "-folder", DRIVE_FOLDER, "-file", str(local), "-name", name,
         "-sha256", sha256(local)],
        text=True, capture_output=True, timeout=600,
    )
    output = (result.stdout + "\n" + result.stderr).strip()
    (OUT / "upload_logs").mkdir(parents=True, exist_ok=True)
    (OUT / "upload_logs" / f"upload_{name}.log").write_text(output + "\n", encoding="utf-8")
    if result.returncode != 0 or "DRIVE_UPLOAD_PASS" not in output:
        raise SystemExit(f"Drive refused {name}: {output[-1200:]}")
    fields = {part.split("=", 1)[0]: part.split("=", 1)[1] for part in output.split() if "=" in part}
    return {"id": fields.get("id", ""), "link": fields.get("link", "")}


def write_manifest(entries: list[dict[str, Any]]) -> None:
    manifest = {
        "schema": "chronontemplate.camera-ring-text-v4-hdr-bloom-series.v1",
        "date": time.strftime("%Y-%m-%d"),
        "generator": EMITTER,
        "reference": f"{REFERENCE_DIR}/camera_ring_text_01_calories_v2.mp4",
        "canvas": {"width": WIDTH, "height": HEIGHT, "fps": FPS},
        "stack": {
            "authoring": f"C++ RenderPlan V3 emitter ({EMITTER})",
            "text": "132 px, phrase-specific face and fill",
            "camera_ring": "64 tap, elliptical wide mask, bilinear 8px sample grid",
            "bevel": "none (removed: it reconstructed a sharp glyph edge after the ring blur)",
            "bloom": "native 6-mip RGBA16F pyramid, Karis prefilter, 13-tap down / 9-tap up, additive composite",
            "output": "ACES tone map + exposure 1.0 at the output boundary",
            "grain": "catalog generate.noise over title, 2 px drift",
            "motion": "push-in + 2 px lateral drift", 
            "backend": "vulkan / require_gpu_native / nvenc",
        },
        "drive": {"folder_id": DRIVE_FOLDER, "folder_url": DRIVE_URL, "placement": "root"},
        "clips": entries,
    }
    (OUT / "manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    lines = [
        "# CameraRing_Text v4 HDR bloom — clips 07-12",
        "",
        "Bloom HDR nativo: piramide 6 mip RGBA16F, prefilter Karis, down 13 tap,",
        "up 9 tap, composito additivo; ACES ed esposizione 1.0 al confine di output.",
        f"Piani RenderPlan V3 generati in C++ da `{EMITTER}`.",
        f"Drive (root): {DRIVE_URL}",
        "",
        "| # | Frase | Font | Durata | Clip |",
        "|---|---|---|---|---|",
    ]
    for entry in entries:
        link = f"[apri]({entry['drive_url']})" if entry.get("drive_url") else "—"
        lines.append(
            f"| {entry['id'][:2]} | {entry['label']} | {entry['font']} | "
            f"{entry['duration_s']:.0f}s | {link} |"
        )
    lines += [
        "",
        "## Ricetta",
        "",
        "```text",
        "testo 132 px, layering lowercase",
        "camera_ring 64 tap, maschera ellittica 1.85 x 0.72, griglia 8 px interpolata",
        "bloom nativo 6 mip RGBA16F, threshold 0.30, additivo, niente layer gaussian",
        "ACES + exposure 1.0, generate.noise catalog, vignette, niente bevel",
        "push-in bezier 0.94 -> 1.012 (frame 1-fine), drift 2 px, fade 12f, tracking 8 -> 0 (24f)",
        "```",
        "",
    ]
    (OUT / "UPLOAD-MANIFEST.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--render", action="store_true")
    parser.add_argument("--upload", action="store_true")
    parser.add_argument("--only", default="")
    args = parser.parse_args()

    if not CLI.is_file():
        raise SystemExit(f"chronon3d_cli not found: {CLI}")

    entries = load_series()
    selected = entries
    if args.only:
        wanted = [part.strip() for part in args.only.split(",") if part.strip()]
        selected = [e for e in entries if any(e["id"].startswith(w) for w in wanted)]
        if not selected:
            raise SystemExit("--only matched no clip")

    if args.render:
        for entry in selected:
            render(entry)
            verify(entry)
            write_manifest(entries)

    if args.upload:
        missing = [e["id"] for e in entries if not e.get("verified")]
        if missing:
            raise SystemExit(f"upload needs verified clips: {', '.join(missing)}")
        for entry in entries:
            if entry.get("uploaded") and entry.get("drive_url"):
                print(f"DRIVE_SKIP {entry['id']}")
                continue
            result = upload(OUT / entry["mp4"], entry["drive_name"])
            entry.update(uploaded=True, drive_id=result["id"], drive_url=result["link"])
            write_manifest(entries)
            print(f"DRIVE_PASS {entry['id']} {result['link']}")
        if not any(e.get("upload_manifest_url") for e in entries):
            manifest_path = OUT / "UPLOAD-MANIFEST.md"
            result = upload(manifest_path, "CameraRing_Text_07-12_v4_HDR_UPLOAD-MANIFEST.md")
            for entry in entries:
                entry["upload_manifest_url"] = result["link"]
            write_manifest(entries)
            print(f"DRIVE_PASS manifest {result['link']}")

    write_manifest(entries)
    print(f"OUT {OUT.relative_to(REPO)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
