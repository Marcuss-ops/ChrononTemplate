"""Render the native web-shot plans (RenderPlan V3) to clips + hero stills.

Companion of ``render_web_shots_rebuild_v1.py``: that one draws the reference
frames with Pillow, this one renders the *same* 34 shots through the Chronon3d
executor, so the two artifacts can be compared frame for frame.

The 28 web shots are the deliverable; the six ``next_*`` recipes belong to a
separate experimental pack and are skipped unless ``--include-next`` is passed.

Input: corrected plans in ``out/web_shots_rebuild_native_gpu_v1``. Each clip
is rendered by the Vulkan backend and encoded by the NVIDIA NVENC hardware
encoder. Hero stills are extracted from the encoded video, so they match the
actual GPU render.

Per shot it writes:
  <out>/<shot>/still.png        — hero frame (``--still-frame``, default 30)
  <out>/<shot>/<shot>.mp4       — 90-frame clip at the plan's fps/resolution
plus contact_sheet.jpg and manifest.json at the output root.

Existing outputs are skipped unless --force, so the run is resumable.

Usage (from anywhere):
  python tools/web_shots/render_web_shots_native_v1.py [--out DIR]
      [--plans DIR] [--only NAME ...] [--force]
      [--still-frame N]
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
TEMPLATE_ROOT = HERE.parents[1]
WORKSPACE = HERE.parents[2]  # contains ChrononTemplate/, i.e. the asset root

DEFAULT_CLI = (TEMPLATE_ROOT.parent / "Chronon3d" / "build" / "chronon" /
               "win-release-clang" / "apps" / "chronon3d_cli" / "chronon3d_cli.exe")
DEFAULT_PLANS = TEMPLATE_ROOT / "out" / "web_shots_rebuild_native_gpu_v1"
DEFAULT_EMITTER = TEMPLATE_ROOT / "out" / "emit_web_shots_rebuild.exe"


def _ffmpeg() -> str:
    found = shutil.which("ffmpeg")
    if found:
        return found
    for candidate in ("C:/Ffmpeg/ffmpeg.exe", "C:/Ffmpeg/ffmpeg"):
        if Path(candidate).exists():
            return candidate
    raise SystemExit("ffmpeg not found (set PATH or install it)")


def _ffprobe() -> str:
    found = shutil.which("ffprobe")
    if found:
        return found
    for candidate in ("C:/Ffmpeg/ffprobe.exe", "C:/Ffmpeg/ffprobe"):
        if Path(candidate).exists():
            return candidate
    raise SystemExit("ffprobe not found (set PATH or install it)")


def shot_name(plan_path: Path) -> str:
    stem = plan_path.name
    if stem.endswith(".plan.json"):
        stem = stem[: -len(".plan.json")]
    if stem.endswith("_native_v1"):
        return stem[: -len("_native_v1")]
    if stem.startswith("next_") and stem.endswith("_v1"):
        return stem[: -len("_v1")]
    return stem


def load_plan(plan_path: Path) -> dict:
    return json.loads(plan_path.read_text(encoding="utf-8"))


def render_shot(cli: Path, plan_path: Path, out_root: Path, still_frame: int,
                force: bool) -> dict:
    plan = load_plan(plan_path)
    canvas = plan["canvas"]
    width, height = int(canvas["width"]), int(canvas["height"])
    fps_num, fps_den = int(canvas.get("fps_num", 30)), int(canvas.get("fps_den", 1))
    frames = int(canvas["duration_frames"])
    fps = fps_num / fps_den

    name = shot_name(plan_path)
    shot_dir = out_root / name
    still_path = shot_dir / "still.png"
    clip_path = shot_dir / f"{name}.mp4"

    if not force and still_path.exists() and clip_path.exists():
        return {
            "shot": name, "plan": plan_path.name, "seconds": round(frames / fps, 3),
            "fps": fps, "frames": frames, "still": f"{name}/still.png",
            "clip": f"{name}/{name}.mp4", "skipped": True,
        }

    shot_dir.mkdir(parents=True, exist_ok=True)
    # Vulkan -> raw RGBA frames from the canonical executor, then NVENC encode
    # via ffmpeg (the Chronon3d build has no in-process nvenc on this device).
    raw_path = shot_dir / f"{name}.raw.rgba"
    subprocess.run([
        str(cli), "render", "--plan", str(plan_path),
        "--assets-root", str(WORKSPACE), "--backend", "vulkan",
        "--video-sink", "raw", "--pipe-pixfmt", "rgba",
        "--profile", "preview", "-o", str(raw_path), "-v", "error",
    ], check=True)

    # Hero still straight from the raw RGBA stream: the reference stills are
    # lossless Pillow output, so comparing them against an NVENC-decoded frame
    # only measured codec softness (blurred text, ringing), not renderer error.
    hero_frame = min(max(still_frame, 0), frames - 1)
    frame_bytes = width * height * 4
    from PIL import Image as _Image
    with open(raw_path, "rb") as fh:
        fh.seek(frame_bytes * hero_frame)
        frame_data = fh.read(frame_bytes)
    if len(frame_data) != frame_bytes:
        raise SystemExit(f"{name}: raw stream shorter than {frames} frames")
    _Image.frombytes("RGBA", (width, height), frame_data).convert("RGB").save(still_path)

    # High-quality NVENC: the default CQ crushed 1080p serif text into mush.
    subprocess.run([
        _ffmpeg(), "-y", "-v", "error",
        "-f", "rawvideo", "-pix_fmt", "rgba",
        "-s", f"{width}x{height}", "-r", str(int(round(fps))),
        "-i", str(raw_path),
        "-c:v", "h264_nvenc", "-preset", "p5", "-rc", "vbr", "-cq", "16",
        "-b:v", "0", "-profile:v", "high", "-pix_fmt", "yuv420p",
        "-movflags", "+faststart",
        str(clip_path),
    ], check=True)
    raw_path.unlink(missing_ok=True)
    probe = subprocess.run([
        _ffprobe(), "-v", "error", "-select_streams", "v:0",
        "-show_entries", "stream=codec_name,width,height,nb_frames",
        "-of", "json", str(clip_path),
    ], check=True, capture_output=True, text=True)
    stream = json.loads(probe.stdout)["streams"][0]
    if (int(stream["width"]) != width or int(stream["height"]) != height
            or int(stream.get("nb_frames", frames)) != frames):
        raise SystemExit(f"{name}: encoded video metadata mismatch: {stream}")

    return {
        "shot": name, "plan": plan_path.name, "seconds": round(frames / fps, 3),
        "fps": fps, "frames": frames, "width": width, "height": height,
        "still": f"{name}/still.png", "clip": f"{name}/{name}.mp4",
        "renderer": "chronontemplate C++ RenderPlan -> Chronon3D Vulkan -> h264_nvenc",
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--plans", default=str(DEFAULT_PLANS), help="plan directory")
    ap.add_argument("--out", default=str(TEMPLATE_ROOT / "artifacts" / "web_shots_native_gpu_v1"),
                    help="output root (default: artifacts/web_shots_native_gpu_v1)")
    ap.add_argument("--cli", default=str(DEFAULT_CLI), help="chronon3d_cli executable")
    ap.add_argument("--only", nargs="*", default=None, help="render only these shot names")
    ap.add_argument("--still-frame", type=int, default=89, help="hero still frame (default final frame)")
    ap.add_argument("--emitter", default=str(DEFAULT_EMITTER), help="C++ RenderPlan emitter executable")
    ap.add_argument("--include-next", action="store_true",
                    help="also render the 6 experimental next_* recipes (not references)")
    ap.add_argument("--force", action="store_true", help="re-render existing outputs")
    args = ap.parse_args(argv)

    cli = Path(args.cli)
    if not cli.exists():
        raise SystemExit(f"chronon3d_cli not found: {cli}")
    plans_dir = Path(args.plans)
    emitter = Path(args.emitter)
    if emitter.exists():
        plans_dir.mkdir(parents=True, exist_ok=True)
        subprocess.run([str(emitter), str(plans_dir)], check=True)
    plans = sorted(p for p in plans_dir.glob("*.plan.json")
                   if args.include_next or not p.name.startswith("next_"))
    if not plans:
        raise SystemExit(f"no plans in {args.plans}")

    out_root = Path(args.out)
    out_root.mkdir(parents=True, exist_ok=True)

    entries = []
    for plan_path in plans:
        name = shot_name(plan_path)
        if args.only and name not in args.only:
            continue
        entry = render_shot(cli, plan_path, out_root, args.still_frame, args.force)
        entries.append(entry)
        tag = "skip" if entry.get("skipped") else "render"
        print(f"[{tag}] {name}", flush=True)

    if not entries:
        print("[done] no shots matched --only", flush=True)
        return 1

    if not args.only:
        sys.path.insert(0, str(HERE))
        from PIL import Image
        from web_shot_kit import contact_sheet

        stills = [(e["shot"], Image.open(out_root / e["still"])) for e in entries]
        contact_sheet(stills, out_root / "contact_sheet.jpg")
        manifest = {
            "schema": "chronon.web-shots-native.v1",
            "generated": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "renderer": "ChrononTemplate C++ RenderPlan V3 -> Chronon3D Vulkan -> NVIDIA h264_nvenc",
            "count": len(entries),
            "shots": entries,
        }
        (out_root / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        print(f"[done] {len(entries)} shots -> {out_root}", flush=True)
    else:
        print(f"[done] {len(entries)} shots rendered (run without --only to assemble)", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
