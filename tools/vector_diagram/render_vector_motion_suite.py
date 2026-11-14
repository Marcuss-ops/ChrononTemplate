#!/usr/bin/env python3
"""Render, verify and upload the five-category vector motion suite.

The plans are authored in C++ by
`chronontemplate_emit_vector_motion_suite`; this driver only validates,
renders through Chronon3D's strict Vulkan/NVENC path, verifies the encoded
frames, stages the deliverables under RenderingGen/UploadDrive and uploads the
MP4s plus the manifest to the configured Drive folder.

Usage
-----
    cmake --build ChrononTemplate/build/dev-fast \
        --target chronontemplate_emit_vector_motion_suite
    ChrononTemplate/build/dev-fast/chronontemplate_emit_vector_motion_suite \
        ChrononTemplate/out/vector_motion_suite_v1
    python3 ChrononTemplate/tools/vector_diagram/render_vector_motion_suite.py \
        --render --upload
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
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

from PIL import Image, ImageChops, ImageStat

ROOT = Path(__file__).resolve().parents[2]          # ChrononTemplate
REPO = ROOT.parent
ASSETS = REPO / "Chronon3d"
OUT = ROOT / "out" / "vector_motion_suite_v1"
SERIES = OUT / "plans" / "series.json"
STAGING = REPO / "RenderingGen" / "UploadDrive" / "vector_motion_suite_20261109"
CLI = ASSETS / "build/chronon/linux-video-release/apps/chronon3d_cli/chronon3d_cli"
UPLOADER = REPO / "RenderingGen" / "bin" / "drive-upload"
sys.path.insert(0, str(REPO / "RenderingGen" / "UploadDrive"))
from drive_common import config_paths  # noqa: E402

CREDENTIALS, TOKEN = config_paths()
EMITTER = "chronontemplate_emit_vector_motion_suite"

WIDTH, HEIGHT, FPS = 1920, 1080, 30
MAX_FRAMES = 10 * FPS
DRIVE_FOLDER = _overlay_root()
DRIVE_URL = f"https://drive.google.com/drive/u/1/folders/{DRIVE_FOLDER}"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_series() -> list[dict[str, Any]]:
    if not SERIES.is_file():
        raise SystemExit(
            f"missing {SERIES}\n"
            f"build and run the C++ emitter first:\n"
            f"  cmake --build ChrononTemplate/build/dev-fast --target {EMITTER}\n"
            f"  ChrononTemplate/build/dev-fast/{EMITTER} {OUT}"
        )
    series = json.loads(SERIES.read_text(encoding="utf-8"))
    if series.get("generator") != EMITTER:
        raise SystemExit(f"{SERIES} was not emitted by {EMITTER}")
    canvas = series.get("canvas", {})
    if (canvas.get("width"), canvas.get("height"), canvas.get("fps")) != (
        WIDTH, HEIGHT, FPS
    ):
        raise SystemExit(f"unexpected series canvas: {canvas}")
    entries = series.get("clips", [])
    if len(entries) != 5:
        raise SystemExit(f"expected 5 clips in {SERIES}, found {len(entries)}")
    seen: set[str] = set()
    for entry in entries:
        clip_id = entry.get("id", "")
        if not clip_id or clip_id in seen:
            raise SystemExit(f"missing/duplicate clip id: {clip_id!r}")
        seen.add(clip_id)
        if not (OUT / entry["plan"]).is_file():
            raise SystemExit(f"missing C++ plan for {clip_id}: {entry['plan']}")
        if not 1 <= int(entry.get("frames", 0)) <= MAX_FRAMES:
            raise SystemExit(f"{clip_id}: duration outside 1..10 s")
        if entry.get("category") not in {
            "tactical_map_hud", "network_nodes", "validation_badge",
            "callout_annotation", "logo_morph",
        }:
            raise SystemExit(f"{clip_id}: unknown category {entry.get('category')!r}")
    print(f"SERIES {SERIES.relative_to(REPO)} ({len(entries)} clips from C++)")
    return entries


def validate(plan: Path) -> None:
    result = subprocess.run(
        [str(CLI), "validate", "--plan", str(plan), "--assets-root", str(ASSETS)],
        cwd=REPO, text=True, capture_output=True,
    )
    if result.returncode != 0:
        tail = (result.stdout + result.stderr).strip().splitlines()[-14:]
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
        "-o", str(video),
    ]
    validate(plan)
    started = time.time()
    with log.open("w", encoding="utf-8") as handle:
        handle.write(" ".join(command) + "\n\n")
        handle.flush()
        result = subprocess.run(command, cwd=REPO, stdout=handle,
                                stderr=subprocess.STDOUT)
    if result.returncode != 0:
        tail = log.read_text(encoding="utf-8", errors="replace").strip().splitlines()[-16:]
        raise SystemExit(f"render failed for {entry['id']}: " + " | ".join(tail))
    print(f"RENDER {entry['id']} in {time.time() - started:.1f}s")


def probe(video: Path) -> dict[str, Any]:
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-count_frames", "-select_streams", "v:0",
         "-show_entries",
         "stream=width,height,nb_read_frames,r_frame_rate:format=duration,size",
         "-of", "json", str(video)],
        check=True, text=True, capture_output=True,
    )
    data = json.loads(result.stdout)
    stream = data["streams"][0]
    return {
        "width": int(stream["width"]),
        "height": int(stream["height"]),
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
        raise SystemExit(
            f"{entry['id']}: expected 1920x1080, got "
            f"{info['width']}x{info['height']}"
        )
    if info["frames"] != entry["frames"]:
        raise SystemExit(
            f"{entry['id']}: expected {entry['frames']} frames, got {info['frames']}"
        )
    expected = entry["frames"] / FPS
    if abs(info["duration_s"] - expected) > 0.15:
        raise SystemExit(
            f"{entry['id']}: expected {expected:.2f}s, got {info['duration_s']:.2f}s"
        )

    ratios = []
    for tag, fraction in (("early", 0.18), ("mid", 0.55), ("late", 0.88)):
        frame = still(video, OUT / "stills" / f"{entry['id']}_{tag}.png",
                      expected * fraction)
        background = tuple(
            int(round(c * 255)) for c in entry["background_rgb"]
        )
        bg = Image.new("RGB", (WIDTH, HEIGHT), background)
        diff = ImageChops.difference(frame, bg).convert("L")
        changed = sum(diff.histogram()[32:]) / float(WIDTH * HEIGHT)
        if changed < 0.00035:
            raise SystemExit(
                f"{entry['id']}: empty frame at {fraction:.0%} ({changed:.4%})"
            )
        if max(ImageStat.Stat(frame).stddev) < 1.0:
            raise SystemExit(f"{entry['id']}: flat frame at {fraction:.0%}")
        ratios.append(round(changed, 6))

    entry.update(
        width=info["width"], height=info["height"], fps=info["fps"],
        frames=info["frames"], duration_s=info["duration_s"], bytes=info["bytes"],
        sha256=sha256(video), verified=True,
        verified_at=time.strftime("%Y-%m-%dT%H:%M:%S"),
        foreground_ratio=ratios[1], foreground_ratios=ratios,
        stills=[f"stills/{entry['id']}_{tag}.png"
                for tag in ("early", "mid", "late")],
    )
    print(f"VERIFY {entry['id']} {info['width']}x{info['height']} "
          f"{info['frames']}f fg={ratios}")


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
    (OUT / "upload_logs" / f"upload_{name}.log").write_text(
        output + "\n", encoding="utf-8"
    )
    if result.returncode != 0 or "DRIVE_UPLOAD_PASS" not in output:
        raise SystemExit(f"Drive refused {name}: {output[-1400:]}")
    fields = {
        part.split("=", 1)[0]: part.split("=", 1)[1]
        for part in output.split() if "=" in part
    }
    return {"id": fields.get("id", ""), "link": fields.get("link", "")}


def write_manifest(entries: list[dict[str, Any]]) -> None:
    manifest = {
        "schema": "chronontemplate.vector-motion-suite.v1",
        "date": time.strftime("%Y-%m-%d"),
        "generator": EMITTER,
        "canvas": {"width": WIDTH, "height": HEIGHT, "fps": FPS},
        "stack": {
            "authoring": f"C++ RenderPlan V3 emitter ({EMITTER})",
            "primitives": "native shape/path, cubic Bezier, trim, glow, "
                          "ring_segment, rounded_rect, gradients-free fills",
            "motion": "out_cubic / out_back / out_expo, trim paths, "
                      "arc-length sampled markers, staggered cascades",
            "backend": "vulkan / require_gpu_native / h264_nvenc",
        },
        "drive": {
            "folder_id": DRIVE_FOLDER,
            "folder_url": DRIVE_URL,
            "placement": "root",
        },
        "clips": entries,
    }
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    lines = [
        "# Vector Motion Suite — 5 categorie",
        "",
        "Suite vettoriale nativa in RenderPlan V3, generata in C++ da",
        f"`{EMITTER}` e renderizzata su Vulkan/NVENC.",
        f"Drive (root): {DRIVE_URL}",
        "",
        "| # | Categoria | Clip | Durata | File |",
        "|---|---|---|---|---|",
    ]
    for entry in entries:
        link = f"[apri]({entry['drive_url']})" if entry.get("drive_url") else "—"
        lines.append(
            f"| {entry['index']:02d} | {entry['category']} | "
            f"{entry['label']} | {entry['duration_s']:.0f}s | {link} |"
        )
    lines += [
        "",
        "## Ricetta",
        "",
        "```text",
        "canvas 1920x1080 @ 30 fps, massimo 300 frame per clip",
        "path Bézier cubiche con trim sequenziale e stroke round",
        "marker campionati su lunghezza d'arco (nessun follow_path a runtime)",
        "glow nativo, ring_segment, rounded_rect, vignette, blend screen/multiply",
        "entrate out_cubic/out_back/out_expo, cascate sfalsate, snap con overshoot",
        "```",
        "",
    ]
    (OUT / "UPLOAD-MANIFEST.md").write_text("\n".join(lines), encoding="utf-8")


def publish() -> None:
    STAGING.mkdir(parents=True, exist_ok=True)
    for name in ("plans", "mp4", "stills"):
        source = OUT / name
        if not source.is_dir():
            continue
        target = STAGING / name
        target.mkdir(parents=True, exist_ok=True)
        for item in source.iterdir():
            if item.is_file():
                shutil.copy2(item, target / item.name)
    for name in ("manifest.json", "UPLOAD-MANIFEST.md"):
        source = OUT / name
        if source.is_file():
            shutil.copy2(source, STAGING / name)


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
        selected = [
            e for e in entries if any(e["id"].startswith(w) for w in wanted)
        ]
        if not selected:
            raise SystemExit("--only matched no clip")

    if args.render:
        for entry in selected:
            render(entry)
            verify(entry)
            write_manifest(entries)
        publish()

    if args.upload:
        for entry in entries:
            if not entry.get("verified"):
                verify(entry)
        write_manifest(entries)
        publish()
        missing = [e["id"] for e in entries if not e.get("verified")]
        if missing:
            raise SystemExit(f"upload needs verified clips: {', '.join(missing)}")
        for entry in entries:
            if entry.get("uploaded") and entry.get("drive_url"):
                print(f"DRIVE_SKIP {entry['id']}")
                continue
            result = upload(OUT / entry["mp4"], entry["drive_name"])
            entry.update(uploaded=True, drive_id=result["id"],
                         drive_url=result["link"])
            write_manifest(entries)
            publish()
            print(f"DRIVE_PASS {entry['id']} {result['link']}")
        manifest_path = OUT / "UPLOAD-MANIFEST.md"
        result = upload(manifest_path, "VectorMotion_Suite_UPLOAD-MANIFEST.md")
        for entry in entries:
            entry["upload_manifest_url"] = result["link"]
        write_manifest(entries)
        publish()
        print(f"DRIVE_PASS manifest {result['link']}")

    write_manifest(entries)
    publish()
    print(f"OUT {OUT.relative_to(REPO)}")
    print(f"STAGING {STAGING.relative_to(REPO)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
