"""Verify the 28 native rebuild plans through the Chronon3d CLI.

For every emitted `*_native_v1.plan.json` this renders three sample frames
(0, 60, 89) through the canonical executor, checks that each frame is a full
1920x1080 composition with real content, and compares it against the matching
frame of the committed native MP4. The raw stream of a single frame is ~8 MB,
so it is deleted right after the check.

Usage (from ChrononTemplate/):
  python tools/web_shots/verify_rebuild_cli.py
  python tools/web_shots/verify_rebuild_cli.py --frames 0 60 89 --tolerance 26
  python tools/web_shots/verify_rebuild_cli.py --only 03_alexis_arquette_article
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image

import numpy as np

HERE = Path(__file__).resolve().parent
TEMPLATE_ROOT = HERE.parents[1]
WORKSPACE = HERE.parents[2]
PLANS = TEMPLATE_ROOT / "out" / "web_animations_20261030" / "plans"
NATIVE = TEMPLATE_ROOT / "artifacts" / "web_shots_folder_recreated_native_v1"
CLI = (WORKSPACE / "Chronon3d" / "build" / "chronon" / "linux-video-release" /
       "apps" / "chronon3d_cli" / "chronon3d_cli")
FPS = 30
W, H = 1920, 1080


def _render_frame(plan: Path, frame: int, raw: Path) -> None:
    subprocess.run([
        str(CLI), "render", "--plan", str(plan),
        "--assets-root", str(WORKSPACE), "--backend", "vulkan",
        "--video-sink", "raw", "--pipe-pixfmt", "rgba",
        "--profile", "preview", "--start-frame", str(frame),
        "--end-frame", str(frame), "-o", str(raw), "-v", "error",
    ], check=True, capture_output=True, text=True)


def _read_frame(raw: Path) -> Image.Image:
    """First frame of the stream: every render below is a single-frame range."""
    with open(raw, "rb") as fh:
        data = fh.read(W * H * 4)
    if len(data) != W * H * 4:
        raise SystemExit(f"{raw.name}: short stream ({len(data)} bytes)")
    return Image.frombytes("RGBA", (W, H), data).convert("RGB")


def _native_frame(clip: Path, frame: int, out: Path) -> Image.Image | None:
    if not clip.exists():
        return None
    # Seek mezzo frame prima del target: -ss esatto sull'ultimo frame (89/30 =
    # 2.967 s su un clip di 3.000 s) cade oltre la fine e non produce output.
    seek = max(0.0, (frame - 0.5) / FPS)
    subprocess.run([
        "ffmpeg", "-y", "-v", "error", "-ss", f"{seek:.3f}", "-i", str(clip),
        "-frames:v", "1", str(out),
    ], check=True)
    if not out.exists():
        return None
    return Image.open(out).convert("RGB")


def _stats(image: Image.Image) -> dict:
    arr = np.asarray(image).astype(np.int16)
    dark = arr.sum(axis=2) < 45
    content = ~dark
    rows = np.where(content.any(axis=1))[0]
    cols = np.where(content.any(axis=0))[0]
    return {
        "mean": round(float(arr.mean()), 1),
        "black_pct": round(100.0 * float(dark.mean()), 2),
        "bbox": [int(cols.min()), int(rows.min()), int(cols.max()), int(rows.max())]
        if len(cols) and len(rows) else None,
        "edge_coverage": {
            "left": bool(content[:, :8].any()),
            "right": bool(content[:, -8:].any()),
            "top": bool(content[:8, :].any()),
            "bottom": bool(content[-8:, :].any()),
        },
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--plans", type=Path, default=PLANS)
    ap.add_argument("--frames", type=int, nargs="+", default=[0, 60, 89])
    ap.add_argument("--only", nargs="*", default=None)
    # Il diff verso gli MP4 nativi e' riportato, non usato come gate: quei
    # clip sono stati resi con la camera vecchia (z=-1320), quindi lo scarto
    # include di proposito il cambio di scala 1.14. Il gate resta su cornice,
    # contenuto e percentuale di nero.
    ap.add_argument("--tolerance", type=float, default=None,
                    help="optional gate: max mean abs diff vs the native frame")
    ap.add_argument("--report", type=Path,
                    default=TEMPLATE_ROOT / "out" / "web_animations_20261030" / "rebuild_cli_report.json")
    args = ap.parse_args(argv)

    plans = sorted(p for p in args.plans.glob("*_native_v1.plan.json"))
    if args.only:
        wanted = set(args.only)
        plans = [p for p in plans if p.name.replace("_native_v1.plan.json", "") in wanted]
    if not plans:
        raise SystemExit("no plans matched")

    tmp = Path(tempfile.mkdtemp(prefix="rebuild_cli_", dir=str(TEMPLATE_ROOT / "out")))
    rows = []
    failures = 0
    for index, plan in enumerate(plans, 1):
        name = plan.name.replace("_native_v1.plan.json", "")
        clip = NATIVE / f"{name}.mp4"
        entry = {"shot": name, "frames": {}}
        for frame in args.frames:
            raw = tmp / f"{name}_{frame}.rgba"
            try:
                _render_frame(plan, frame, raw)
                image = _read_frame(raw)
            finally:
                raw.unlink(missing_ok=True)
            stats = _stats(image)
            native = _native_frame(clip, frame, tmp / f"{name}_{frame}_native.png")
            diff = None
            if native is not None:
                a = np.asarray(image).astype(np.int16)
                b = np.asarray(native).astype(np.int16)
                diff = round(float(np.abs(a - b).mean()), 1)
            problems = []
            if stats["black_pct"] > 92.0:
                problems.append(f"frame {frame}: {stats['black_pct']}% near-black")
            # bbox = [xmin, ymin, xmax, ymax]: la larghezza e' xmax - xmin.
            if stats["bbox"] and (stats["bbox"][2] - stats["bbox"][0]) < W * 0.5:
                problems.append(f"frame {frame}: content only "
                                f"{stats['bbox'][2] - stats['bbox'][0]}px wide")
            if diff is not None and args.tolerance is not None and diff > args.tolerance:
                problems.append(f"frame {frame}: diff {diff} > {args.tolerance} vs native")
            entry["frames"][frame] = {"stats": stats, "diff_vs_native": diff,
                                      "problems": problems}
            failures += len(problems)
            image.save(tmp / f"{name}_{frame}.png")
        entry["ok"] = not any(f["problems"] for f in entry["frames"].values())
        rows.append(entry)
        print(f"[{index}/{len(plans)}] {name}: "
              f"{'OK' if entry['ok'] else 'FAIL'}", flush=True)

    stills = []
    for entry in rows:
        for frame in args.frames:
            p = tmp / f"{entry['shot']}_{frame}.png"
            if p.exists():
                stills.append((f"{entry['shot']} f{frame}", Image.open(p).convert("RGB")))
    if stills:
        from web_shot_kit import contact_sheet  # noqa: PLC0415 - path set below
        contact_sheet(stills, args.report.with_name("rebuild_cli_contact.jpg"),
                      cols=6, cell_w=320)

    report = {
        "cli": str(CLI),
        "frames": args.frames,
        "count": len(rows),
        "failures": failures,
        "shots": rows,
    }
    args.report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"\n{len(rows) - sum(1 for r in rows if not r['ok'])}/{len(rows)} shots OK, "
          f"{failures} problems -> {args.report}")
    return 0 if failures == 0 else 1


if __name__ == "__main__":
    sys.path.insert(0, str(HERE))
    raise SystemExit(main())
