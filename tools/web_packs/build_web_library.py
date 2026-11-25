#!/usr/bin/env python3
"""One web delivery tree for the existing ChrononTemplate web packs.

The packs stay independent; this tool only decides where their plans live and
how the resulting clips are named. It exists so the web library is one folder
with explicit subfamilies instead of a pile of one-off out directories.

    python3 ChrononTemplate/tools/web_packs/build_web_library.py emit
    python3 ChrononTemplate/tools/web_packs/build_web_library.py render --jobs 4
    python3 ChrononTemplate/tools/web_packs/build_web_library.py verify
    python3 ChrononTemplate/tools/web_packs/build_web_library.py contacts

Asset paths are normalized to the repository root so every plan validates and
renders with a single --assets-root.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from normalize_web_shots import normalize_plan

ROOT = Path(__file__).resolve().parents[3]
TEMPLATE = ROOT / "ChrononTemplate"
BUILD = TEMPLATE / "build-map-anim"
CLI = ROOT / "Chronon3d/build/chronon/linux-fast-dev/apps/chronon3d_cli/chronon3d_cli"
OUT = TEMPLATE / "out/web_v1"

# family id, emitter
FAMILIES = [
    ("02_page_v2", "chronontemplate_emit_web_page_v2"),
    ("05_paper_reference", "chronontemplate_emit_web_paper_reference"),
    ("06_web_shots", "chronontemplate_emit_web_shots_rebuild_v4"),
]

# The V2 serif reference points at a font that is not checked in. Playfair is
# the checked-in serif used by the rest of the classic web family.
FONT_FALLBACKS = {
    "assets/fonts/FreeSerif.ttf": "ChrononTemplate/assets/fonts/PlayfairDisplay.ttf",
}


def log(message: str) -> None:
    print(message, flush=True)


def run(cmd: list[str], log_path: Path | None = None, cwd: Path = ROOT,
        timeout: float | None = None) -> subprocess.CompletedProcess:
    try:
        proc = subprocess.run(cmd, cwd=str(cwd), text=True, capture_output=True, timeout=timeout)
    except subprocess.TimeoutExpired as exc:
        stdout = exc.stdout if isinstance(exc.stdout, str) else ""
        stderr = exc.stderr if isinstance(exc.stderr, str) else ""
        proc = subprocess.CompletedProcess(cmd, 124, stdout, stderr + f"\ntimeout after {timeout}s")
    if log_path is not None:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        log_path.write_text(
            "$ " + " ".join(cmd) + "\n\nSTDOUT\n" + proc.stdout + "\nSTDERR\n" + proc.stderr,
            encoding="utf-8",
        )
    return proc


def normalize_assets(value):
    if isinstance(value, dict):
        return {key: normalize_assets(item) for key, item in value.items()}
    if isinstance(value, list):
        return [normalize_assets(item) for item in value]
    if isinstance(value, str):
        if value in FONT_FALLBACKS:
            return FONT_FALLBACKS[value]
        if value.startswith("assets/"):
            return "ChrononTemplate/" + value
    return value


def plan_stem(path: Path) -> str:
    return path.name.removesuffix(".plan.json")


def renumber_native_plans(plans_dir: Path) -> None:
    """Turn the authored 03..28 prefixes into a contiguous 01..22 sequence."""
    paths = sorted(plans_dir.glob("*.plan.json"))
    for index, path in enumerate(paths, 1):
        data = json.loads(path.read_text(encoding="utf-8"))
        if data.get("external"):
            continue
        old = plan_stem(path)
        suffix = old[3:] if len(old) > 3 and old[2] == "_" else old
        new = f"{index:02d}_{suffix}"
        if new == old:
            continue
        data["job_id"] = new
        output = data.get("output")
        if isinstance(output, dict):
            output["path"] = new + ".mp4"
        new_path = path.with_name(new + ".plan.json")
        new_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
        path.unlink()


def write_readme(manifest: dict) -> None:
    descriptions = {
        "02_page_v2": "WebPageV2: complete, highlight3d, long-phrase blurred × light/dark",
        "05_paper_reference": "Newspaper tilt, torn strip, blurred evidence, bridge collage, book highlight",
        "06_web_shots": "22 web shot reference normalizzate",
    }
    lines = [
        "# WEB — libreria animazioni",
        "",
        "Una sola cartella web con le sottofamiglie dei pack già esistenti in ChrononTemplate.",
        "Niente card inventata: ogni clip usa il pack nativo della propria famiglia.",
        "",
        "Canvas: 1920x1080, 30 fps, H.264. Ogni clip ha la durata del proprio piano",
        "(3–8 s). I piani sono in `plans/`, i video in `videos/`, il manifest completo in",
        "`manifest.json`.",
        "",
        "## Sottofamiglie",
        "",
        "| Cartella | Cosa contiene | Clip |",
        "|---|---|---:|",
    ]
    for family in manifest["families"]:
        lines.append(f"| `{family['id']}` | {descriptions.get(family['id'], '')} | {family['plans']} |")
    lines += [
        "",
        f"Totale: **{len(manifest['plans'])} animazioni**.",
        "",
        "## Note",
        "",
        "- `02_page_v2` usa `PlayfairDisplay.ttf` come fallback per il serif",
        "  `FreeSerif.ttf`, non presente nel repository.",
        "- Le 22 reference di `06_web_shots` vengono centrate e adattate al canvas da",
        "  `tools/web_packs/normalize_web_shots.py`.",
        "- I video sono renderizzati dal renderer Chronon3d con `--assets-root` sulla",
        "  radice del repository; i piani sono già normalizzati.",
        "- Pipeline ripetibile:",
        "  `python3 tools/web_packs/build_web_library.py emit`",
        "  `python3 tools/web_packs/build_web_library.py render --retry --jobs 1`",
        "  `python3 tools/web_packs/build_web_library.py verify`",
        "  `python3 tools/web_packs/build_web_library.py contacts`",
    ]
    (OUT / "README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def emit(args: argparse.Namespace) -> None:
    if OUT.exists():
        shutil.rmtree(OUT)
    (OUT / "plans").mkdir(parents=True)
    (OUT / "logs" / "emit").mkdir(parents=True)
    (OUT / "videos").mkdir(parents=True)

    failures: list[str] = []
    for family, target in FAMILIES:
        plans_dir = OUT / "plans" / family
        plans_dir.mkdir(parents=True, exist_ok=True)
        binary = BUILD / target
        if not binary.exists():
            failures.append(f"{family}: missing emitter {binary}")
            continue
        log(f"[emit] {family} <- {target}")
        command = [str(binary), str(plans_dir)]
        proc = run(command, OUT / "logs" / "emit" / f"{family}.log")
        if proc.returncode != 0:
            failures.append(f"{family}: emitter exit {proc.returncode}")
            log(proc.stderr[-2000:])
            continue
        count = len(list(plans_dir.glob("*.plan.json")))
        log(f"[emit] {family}: {count} plans")

    renumber_native_plans(OUT / "plans" / "06_web_shots")

    for plan_path in sorted((OUT / "plans").rglob("*.plan.json")):
        data = json.loads(plan_path.read_text(encoding="utf-8"))
        normalized = normalize_assets(data)
        if plan_path.parent.name == "06_web_shots":
            normalize_plan(normalized)
        plan_path.write_text(json.dumps(normalized, indent=2) + "\n", encoding="utf-8")

    validation_failures: list[str] = []
    plans = []
    for plan_path in sorted((OUT / "plans").rglob("*.plan.json")):
        data = json.loads(plan_path.read_text(encoding="utf-8"))
        canvas = data.get("canvas", {})
        family = plan_path.parent.name
        frames = int(canvas.get("duration_frames", 0))
        external = bool(data.get("external"))
        kind = "clip" if external else ("animation" if frames > 1 else "still")
        plans.append({
            "family": family,
            "name": plan_stem(plan_path),
            "plan": str(plan_path.relative_to(OUT)),
            "frames": frames,
            "fps": f"{canvas.get('fps_num', 0)}/{canvas.get('fps_den', 1)}",
            "width": canvas.get("width", 0),
            "height": canvas.get("height", 0),
            "layers": len(data.get("layers", [])),
            "camera": "camera" in data,
            "kind": kind,
            "source": data.get("source", ""),
            "description": data.get("description", ""),
        })
        if external:
            continue
        proc = run([str(CLI), "validate", "--plan", str(plan_path), "--assets-root", str(ROOT)],
                   OUT / "logs" / "emit" / f"validate_{family}_{plan_stem(plan_path)}.log")
        if proc.returncode != 0:
            validation_failures.append(f"{family}/{plan_stem(plan_path)}: {proc.stderr.strip()[-500:]}")
            log(f"[validate] FAIL {family}/{plan_stem(plan_path)}")

    manifest = {
        "schema": "chronon.web-library.v1",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "assets_root": str(ROOT),
        "families": [
            {
                "id": family,
                "emitter": target,
                "plans": sum(1 for plan in plans if plan["family"] == family),
                "animations": sum(1 for plan in plans if plan["family"] == family and plan["kind"] == "animation"),
                "clips": sum(1 for plan in plans if plan["family"] == family and plan["kind"] == "clip"),
                "stills": sum(1 for plan in plans if plan["family"] == family and plan["kind"] == "still"),
            }
            for family, target in FAMILIES
        ],
        "plans": plans,
        "failures": failures + validation_failures,
    }
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    write_readme(manifest)

    log(f"[emit] total plans={len(plans)} animations={sum(1 for p in plans if p['kind'] == 'animation')} clips={sum(1 for p in plans if p['kind'] == 'clip')} stills={sum(1 for p in plans if p['kind'] == 'still')}")
    log(f"[emit] failures={len(manifest['failures'])}")
    if manifest["failures"]:
        for failure in manifest["failures"]:
            log(f"[emit] FAIL {failure}")
        raise SystemExit(1)


def render_one(task: tuple[dict, int, int]) -> tuple[dict, bool, str]:
    plan, index, total = task
    plan_path = OUT / plan["plan"]
    dest = OUT / "videos" / plan["family"] / (plan["name"] + ".mp4")
    dest.parent.mkdir(parents=True, exist_ok=True)
    log_path = OUT / "logs" / "render" / plan["family"] / (plan["name"] + ".log")
    cmd = [
        str(CLI), "render",
        "--plan", str(plan_path),
        "--output", str(dest),
        "--assets-root", str(ROOT),
        "--backend", "vulkan",
        "--profile", "preview",
        "--hardware", "nvenc",
        "--fps", "30",
    ]
    log(f"[render {index}/{total}] {plan['family']}/{plan['name']}")
    proc = run(cmd, log_path, timeout=180)
    ok = proc.returncode == 0 and dest.exists() and dest.stat().st_size > 0
    if not ok:
        log(f"[render] FAIL {plan['family']}/{plan['name']} exit={proc.returncode}")
        if proc.stderr:
            log(proc.stderr[-1000:])
    return plan, ok, proc.stderr[-1000:]


def video_ok(plan: dict) -> bool:
    dest = OUT / "videos" / plan["family"] / (plan["name"] + ".mp4")
    if not dest.exists() or dest.stat().st_size <= 0:
        return False
    info = ffprobe(dest)
    return (
        info.get("codec_name") == "h264"
        and info.get("width") == plan["width"]
        and info.get("height") == plan["height"]
        and info.get("r_frame_rate") == plan["fps"]
        and int(info.get("nb_frames", 0)) == plan["frames"]
    )


def render(args: argparse.Namespace) -> None:
    manifest = json.loads((OUT / "manifest.json").read_text(encoding="utf-8"))
    animations = [plan for plan in manifest["plans"] if plan["kind"] == "animation"]
    if args.retry:
        animations = [plan for plan in animations if not video_ok(plan)]
        log(f"[render] retry missing/invalid={len(animations)}")
    (OUT / "logs" / "render").mkdir(parents=True, exist_ok=True)
    status = []
    tasks = [(plan, index + 1, len(animations)) for index, plan in enumerate(animations)]
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.jobs) as pool:
        futures = [pool.submit(render_one, task) for task in tasks]
        for future in concurrent.futures.as_completed(futures):
            plan, ok, error = future.result()
            status.append({"family": plan["family"], "name": plan["name"], "ok": ok, "error": error})
    status.sort(key=lambda row: (row["family"], row["name"]))
    (OUT / "render-status.json").write_text(json.dumps(status, indent=2) + "\n", encoding="utf-8")
    failures = [row for row in status if not row["ok"]]
    log(f"[render] done={len(status)} failures={len(failures)}")
    if failures:
        raise SystemExit(1)


def ffprobe(path: Path) -> dict:
    proc = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0",
         "-show_entries", "stream=codec_name,width,height,r_frame_rate,nb_frames,pix_fmt",
         "-of", "json", str(path)],
        text=True, capture_output=True,
    )
    if proc.returncode != 0:
        return {"error": proc.stderr.strip()}
    streams = json.loads(proc.stdout).get("streams", [])
    return streams[0] if streams else {"error": "no video stream"}


def verify(args: argparse.Namespace) -> None:
    manifest = json.loads((OUT / "manifest.json").read_text(encoding="utf-8"))
    results = []
    for plan in manifest["plans"]:
        if plan["kind"] not in ("animation", "clip"):
            continue
        video = OUT / "videos" / plan["family"] / (plan["name"] + ".mp4")
        info = ffprobe(video) if video.exists() else {"error": "missing video"}
        expected = {
            "width": plan["width"],
            "height": plan["height"],
            "frames": plan["frames"],
            "fps": plan["fps"],
        }
        ok = (
            info.get("codec_name") == "h264"
            and info.get("width") == expected["width"]
            and info.get("height") == expected["height"]
            and info.get("r_frame_rate") == expected["fps"]
            and int(info.get("nb_frames", 0)) == expected["frames"]
        )
        results.append({"family": plan["family"], "name": plan["name"], "ok": ok, **expected, "probe": info})
    (OUT / "verification.json").write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")
    failures = [row for row in results if not row["ok"]]
    log(f"[verify] checked={len(results)} failures={len(failures)}")
    for row in failures:
        log(f"[verify] FAIL {row['family']}/{row['name']} expected={row['width']}x{row['height']} {row['fps']} {row['frames']}f got={row['probe']}")
    if failures:
        raise SystemExit(1)


def contacts(args: argparse.Namespace) -> None:
    manifest = json.loads((OUT / "manifest.json").read_text(encoding="utf-8"))
    contact_dir = OUT / "contact_sheets"
    contact_dir.mkdir(parents=True, exist_ok=True)
    frames_dir = OUT / "contact_frames"
    for family, _ in FAMILIES:
        videos = sorted(
            path for path in (OUT / "videos" / family).glob("*.mp4")
            if not path.name.endswith(".partial.mp4") and path.stat().st_size > 0
        )
        if not videos:
            continue
        family_frames = frames_dir / family
        if family_frames.exists():
            shutil.rmtree(family_frames)
        family_frames.mkdir(parents=True, exist_ok=True)
        for video in videos:
            probe = ffprobe(video)
            frames = int(probe.get("nb_frames", 0) or 0)
            duration = frames / 30.0 if frames else 0.0
            if duration <= 0.0:
                continue
            # 0.5 s catches the entrance animation without sampling frame 0
            # (many layers start at opacity 0); the last half second catches
            # the settled end state.
            start = 0.5 if duration > 1.0 else 0.0
            end = max(0.0, duration - 0.5) if duration > 1.0 else max(0.0, duration * 0.9)
            for phase, at in (("start", start), ("mid", duration * 0.5), ("end", end)):
                out_png = family_frames / f"{video.stem}__{phase}.png"
                subprocess.run(
                    ["ffmpeg", "-y", "-v", "error", "-ss", f"{at:.3f}", "-i", str(video),
                     "-frames:v", "1", "-vf", "scale=400:225", str(out_png)],
                    check=True,
                )
        sheet = contact_dir / f"{family}.jpg"
        images = [
            family_frames / f"{video.stem}__{phase}.png"
            for video in videos
            for phase in ("start", "mid", "end")
            if (family_frames / f"{video.stem}__{phase}.png").exists()
        ]
        subprocess.run(
            ["montage", "-label", "%t", *[str(path) for path in images],
             "-thumbnail", "400x225", "-tile", "6x", "-geometry", "+6+6",
             "-background", "#111111", "-fill", "white", "-pointsize", "11", str(sheet)],
            check=True,
        )
        log(f"[contacts] {family}: {len(videos)} clips x 3 frames -> {sheet}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["emit", "render", "verify", "contacts"])
    parser.add_argument("--jobs", type=int, default=4)
    parser.add_argument("--retry", action="store_true", help="render only missing or invalid videos")
    args = parser.parse_args()
    if args.command == "emit":
        emit(args)
    elif args.command == "render":
        render(args)
    elif args.command == "verify":
        verify(args)
    elif args.command == "contacts":
        contacts(args)
    return 0


if __name__ == "__main__":
    sys.exit(main())
