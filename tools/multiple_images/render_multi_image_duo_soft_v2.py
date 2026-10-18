#!/usr/bin/env python3
"""
Chronon Multi-Image Duo Soft V2 Suite.

Five NEW soft animations for the first multiple-image group: two nearby
images rendered as one detached group (card_left + card_right, same slots
as multi_image_duo_v1). Soft grammar: opacity-led reveals, small drifts
(<=64px), gentle scales inside [0.90, 1.02], slow in_out_sine/out_cubic
easings, and a calm left -> right focus exchange before the balanced hold.

Same deliverable contract as duo_v1 (1920x1080, 5.0s @ 30fps, 150 frames);
Drive upload uses RenderingGen's verified uploader and the configured
destination folder.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

VERIFY_SCRIPT = Path(__file__).with_name("verify_multi_image_duo_v1.py")


def load_verifier():
    spec = importlib.util.spec_from_file_location("verify_multi_image_duo_v1", VERIFY_SCRIPT)
    if spec is None or spec.loader is None:
        raise ImportError(f"Unable to load duo verifier: {VERIFY_SCRIPT}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]

TEMPLATE_DIR = Path(__file__).resolve().parents[2]
BASE_DIR = TEMPLATE_DIR.parent
CHRONON_DIR = BASE_DIR / "Chronon3d"
CHRONON_CLI = CHRONON_DIR / "build/chronon/linux-video-fast-dev/apps/chronon3d_cli/chronon3d_cli"
ASSETS_ROOT = CHRONON_DIR
OUT_DIR = TEMPLATE_DIR / "out/multi_image_duo_soft_v2"
DRIVE_FOLDER_ID = "1J_xUGo_bchzXDIGqSX04CU44c_Dm3SxS"
DRIVE_UPLOADER = REPOSITORY_ROOT / "RenderingGen/bin/drive-upload"
DRIVE_CREDENTIALS = Path("/home/pierone/.config/velox/credentials.json")
DRIVE_TOKEN = Path("/home/pierone/.config/velox/token.json")

# Scene constants (identical slots to multi_image_duo_v1: one detached group).
WIDTH = 1920
HEIGHT = 1080
FPS = 30
DURATION_FRAMES = 150  # Exactly 5.0 seconds
CARD_W = 620
CARD_H = 720
LEFT_X = -480
RIGHT_X = 480

IMAGE_LEFT = "assets/images/card_620x720_left.png"
IMAGE_RIGHT = "assets/images/card_620x720_right.png"


def make_bg_layer():
    return {
        "id": "studio_dark_bg",
        "type": "color",
        "color": [0.03, 0.04, 0.07, 1.0],
        "start_frame": 0,
        "duration_frames": DURATION_FRAMES,
    }


def _tr(prop, keys, easing="in_out_sine"):
    return {
        "property": prop,
        "easing": easing,
        "keyframes": [{"frame": f, "value": v} for f, v in keys],
    }


def _soft_card(layer_id, asset, base_x, tracks):
    return {
        "id": layer_id,
        "type": "image",
        "asset": asset,
        "size": [CARD_W, CARD_H],
        "position": [base_x, 0],
        "radius": 0.0,
        "fit": "cover",
        "enable_3d": True,
        "start_frame": 0,
        "duration_frames": DURATION_FRAMES,
        "animation": {"tracks": tracks},
    }


def _new_plan(job_id):
    return {
        "schema": "chronon.render-plan.v3",
        "version": 3,
        "job_id": job_id,
        "canvas": {"width": WIDTH, "height": HEIGHT, "fps_num": FPS, "fps_den": 1, "duration_frames": DURATION_FRAMES},
        "output": {"path": f"{job_id}.mp4", "format": "mp4", "codec": "h264"},
        "layers": [make_bg_layer()],
    }


# Shared soft focus exchange: left breathes at 48-84 while right rests,
# right breathes at 96-132 while left rests, both settle at 1.0 by 132.
def _focus_left():
    keys = [(0, 1.0), (36, 1.0), (48, 1.0), (60, 1.02), (84, 1.02),
            (96, 0.98), (120, 0.98), (132, 1.0), (149, 1.0)]
    return keys


def _focus_right():
    keys = [(0, 1.0), (36, 1.0), (48, 0.98), (60, 0.98), (84, 0.98),
            (96, 1.02), (120, 1.02), (132, 1.0), (149, 1.0)]
    return keys


# =============================================================================
# 1. duo_soft_bloom_rise — both rise +46px with opacity bloom, left leads 8f
# =============================================================================
def build_01_duo_soft_bloom_rise():
    plan = _new_plan("duo_soft_bloom_rise")
    plan["layers"].append(_soft_card("card_left", IMAGE_LEFT, LEFT_X, [
        _tr("position_y", [(0, 46.0), (30, 0.0), (149, 0.0)]),
        _tr("scale", [(0, 0.94), (36, 1.0)] + _focus_left()[2:], easing="in_out_cubic"),
        _tr("opacity", [(0, 0.0), (24, 1.0), (149, 1.0)], easing="out_cubic"),
    ]))
    plan["layers"].append(_soft_card("card_right", IMAGE_RIGHT, RIGHT_X, [
        _tr("position_y", [(0, 46.0), (8, 46.0), (38, 0.0), (149, 0.0)]),
        _tr("scale", [(0, 0.94), (8, 0.94), (44, 1.0)] + _focus_right()[2:], easing="in_out_cubic"),
        _tr("opacity", [(0, 0.0), (8, 0.0), (32, 1.0), (149, 1.0)], easing="out_cubic"),
    ]))
    return plan


# =============================================================================
# 2. duo_soft_drift_settle — slow lateral drift inward from +/-64px
# =============================================================================
def build_02_duo_soft_drift_settle():
    plan = _new_plan("duo_soft_drift_settle")
    plan["layers"].append(_soft_card("card_left", IMAGE_LEFT, LEFT_X, [
        _tr("position_x", [(0, -64.0), (48, 0.0), (149, 0.0)]),
        _tr("scale", [(0, 0.94), (36, 1.0)] + _focus_left()[2:], easing="in_out_cubic"),
        _tr("opacity", [(0, 0.0), (30, 1.0), (149, 1.0)], easing="out_cubic"),
    ]))
    plan["layers"].append(_soft_card("card_right", IMAGE_RIGHT, RIGHT_X, [
        _tr("position_x", [(0, 64.0), (6, 64.0), (54, 0.0), (149, 0.0)]),
        _tr("scale", [(0, 0.94), (6, 0.94), (42, 1.0)] + _focus_right()[2:], easing="in_out_cubic"),
        _tr("opacity", [(0, 0.0), (6, 0.0), (36, 1.0), (149, 1.0)], easing="out_cubic"),
    ]))
    return plan


# =============================================================================
# 3. duo_soft_cross_bloom — simultaneous bloom 0.90 -> 1.0, focus crosses
# =============================================================================
def build_03_duo_soft_cross_bloom():
    plan = _new_plan("duo_soft_cross_bloom")
    plan["layers"].append(_soft_card("card_left", IMAGE_LEFT, LEFT_X, [
        _tr("scale", [(0, 0.90), (40, 1.0)] + _focus_left()[2:], easing="in_out_cubic"),
        _tr("opacity", [(0, 0.0), (28, 1.0), (149, 1.0)], easing="out_cubic"),
    ]))
    plan["layers"].append(_soft_card("card_right", IMAGE_RIGHT, RIGHT_X, [
        _tr("scale", [(0, 0.90), (40, 1.0)] + _focus_right()[2:], easing="in_out_cubic"),
        _tr("opacity", [(0, 0.0), (4, 0.0), (32, 1.0), (149, 1.0)], easing="out_cubic"),
    ]))
    return plan


# =============================================================================
# 4. duo_soft_breathe_hold — together in, breathing hold, calm exchange
# =============================================================================
def build_04_duo_soft_breathe_hold():
    plan = _new_plan("duo_soft_breathe_hold")
    plan["layers"].append(_soft_card("card_left", IMAGE_LEFT, LEFT_X, [
        _tr("scale", [(0, 0.96), (40, 1.0), (60, 1.015), (90, 1.015),
                      (102, 1.0), (132, 1.0), (149, 1.0)], easing="in_out_cubic"),
        _tr("opacity", [(0, 0.0), (30, 1.0), (149, 1.0)], easing="out_cubic"),
    ]))
    plan["layers"].append(_soft_card("card_right", IMAGE_RIGHT, RIGHT_X, [
        _tr("scale", [(0, 0.96), (40, 1.0), (60, 1.0), (90, 1.0),
                      (102, 1.015), (126, 1.015), (138, 1.0), (149, 1.0)], easing="in_out_cubic"),
        _tr("opacity", [(0, 0.0), (30, 1.0), (149, 1.0)], easing="out_cubic"),
    ]))
    return plan


# =============================================================================
# 5. duo_soft_stagger_glow — staggered opacity-led entrances, tiny rise
# =============================================================================
def build_05_duo_soft_stagger_glow():
    plan = _new_plan("duo_soft_stagger_glow")
    plan["layers"].append(_soft_card("card_left", IMAGE_LEFT, LEFT_X, [
        _tr("position_y", [(0, 24.0), (28, 0.0), (149, 0.0)]),
        _tr("scale", [(0, 0.95), (32, 1.0)] + _focus_left()[2:], easing="in_out_cubic"),
        _tr("opacity", [(0, 0.0), (24, 1.0), (149, 1.0)], easing="out_cubic"),
    ]))
    plan["layers"].append(_soft_card("card_right", IMAGE_RIGHT, RIGHT_X, [
        _tr("position_y", [(0, 24.0), (12, 24.0), (40, 0.0), (149, 0.0)]),
        _tr("scale", [(0, 0.95), (12, 0.95), (44, 1.0)] + _focus_right()[2:], easing="in_out_cubic"),
        _tr("opacity", [(0, 0.0), (12, 0.0), (36, 1.0), (149, 1.0)], easing="out_cubic"),
    ]))
    return plan


PRESET_BUILDERS = {
    "duo_soft_bloom_rise": build_01_duo_soft_bloom_rise,
    "duo_soft_drift_settle": build_02_duo_soft_drift_settle,
    "duo_soft_cross_bloom": build_03_duo_soft_cross_bloom,
    "duo_soft_breathe_hold": build_04_duo_soft_breathe_hold,
    "duo_soft_stagger_glow": build_05_duo_soft_stagger_glow,
}
PRESET_SUITE = list(PRESET_BUILDERS.items())


def validate_plan_contract(item_id, plan_data):
    canvas = plan_data.get("canvas", {})
    expected_canvas = {"width": WIDTH, "height": HEIGHT, "fps_num": FPS, "fps_den": 1, "duration_frames": DURATION_FRAMES}
    if canvas != expected_canvas:
        raise ValueError(f"{item_id}: expected the 1920x1080, 30fps, 150-frame canvas; got {canvas}")

    image_layers = [layer for layer in plan_data.get("layers", []) if layer.get("type") == "image"]
    if len(image_layers) != 2:
        raise ValueError(f"{item_id}: expected exactly two simultaneous image layers, found {len(image_layers)}")
    expected_centers = [(LEFT_X, 0), (RIGHT_X, 0)]
    max_scale = 1.05
    focus_keyframes = []
    for index, (layer, center) in enumerate(zip(image_layers, expected_centers)):
        if tuple(layer.get("position", ())) != center or layer.get("size") != [CARD_W, CARD_H]:
            raise ValueError(f"{item_id}: image {index} violates the stable left/right card layout")
        if layer.get("start_frame") != 0 or layer.get("duration_frames") != DURATION_FRAMES:
            raise ValueError(f"{item_id}: image {index} does not span the complete five-second scene")
        tracks = layer.get("animation", {}).get("tracks", [])
        opacity = next((track for track in tracks if track.get("property") == "opacity"), None)
        if opacity is None:
            raise ValueError(f"{item_id}: image {index} must retain an explicit visible opacity track")
        keyframes = opacity.get("keyframes", [])
        reveal_frames = [key["frame"] for key in keyframes if key.get("value", 0) >= 0.75]
        reveal_deadline_frame = int(DURATION_FRAMES * 0.45)
        if not reveal_frames or min(reveal_frames) > reveal_deadline_frame:
            raise ValueError(f"{item_id}: both images must be visible by 45% of the scene")
        if any(key.get("value", 0) < 0.75 for key in keyframes if key.get("frame", 0) >= 68):
            raise ValueError(f"{item_id}: image {index} must remain visible after the reveal")
        scale_track = next((track for track in tracks if track.get("property") == "scale"), None)
        if scale_track is None:
            raise ValueError(f"{item_id}: image {index} must have an explicit bounded focus scale")
        scale_values = [key.get("value", 1.0) for key in scale_track.get("keyframes", [])]
        scale_values = [component for value in scale_values for component in (value if isinstance(value, (list, tuple)) else [value])]
        if not scale_values or min(scale_values) < 0.85 or max(scale_values) > max_scale:
            raise ValueError(f"{item_id}: image {index} focus scale must remain between 0.85x and {max_scale}x")
        focus_keyframes.append({key["frame"]: key["value"] for key in scale_track.get("keyframes", [])})

        absolute_x = WIDTH / 2 + center[0]
        absolute_y = HEIGHT / 2 + center[1]
        half_w = layer["size"][0] * max_scale / 2
        half_h = layer["size"][1] * max_scale / 2
        if absolute_x - half_w < 0 or absolute_x + half_w > WIDTH or absolute_y - half_h < 0 or absolute_y + half_h > HEIGHT:
            raise ValueError(f"{item_id}: image {index} exceeds the 1920x1080 safe area")

    common_focus_frames = set(focus_keyframes[0]) & set(focus_keyframes[1])
    left_primary = any(focus_keyframes[0][frame] > focus_keyframes[1][frame] for frame in common_focus_frames)
    right_primary = any(focus_keyframes[1][frame] > focus_keyframes[0][frame] for frame in common_focus_frames)
    if not left_primary or not right_primary:
        raise ValueError(f"{item_id}: the focus scheduler must transfer primary focus from left to right")

    return True


def validate_upload_setup(args):
    if not args.drive_uploader.is_file():
        raise FileNotFoundError(
            f"RenderingGen drive-upload binary not found: {args.drive_uploader}; "
            "build it with `cd RenderingGen/renderinggen && go build -o ../bin/drive-upload ./cmd/drive-upload`"
        )
    for credentials in (args.drive_credentials, args.drive_token):
        if not credentials.is_file():
            raise FileNotFoundError(
                f"Google Drive credential file not found: {credentials}; provide it with "
                "--drive-credentials / --drive-token (the uploader will not create credentials)"
            )
    probe = subprocess.run([str(args.drive_uploader), "-h"], capture_output=True, text=True, check=False)
    if "-sha256" not in probe.stderr and "-sha256" not in probe.stdout:
        raise RuntimeError("RenderingGen drive-upload binary does not support the required SHA-256 verification flag")


def upload_deliverables(rendered_files, args):
    expected_names = {f"{preset_id}.mp4" for preset_id in PRESET_BUILDERS}
    mp4_files = sorted({path.resolve() for path in rendered_files if path.suffix.lower() == ".mp4"}, key=lambda path: path.name)
    actual_names = {path.name for path in mp4_files}
    if actual_names != expected_names:
        raise RuntimeError(
            f"Refusing incomplete/unexpected Drive upload: expected {sorted(expected_names)}, "
            f"found {sorted(actual_names)}"
        )
    validate_upload_setup(args)

    print(f"\n=== Uploading {len(mp4_files)} verified MP4 files via RenderingGen to Drive folder {args.drive_folder} ===", flush=True)
    for file_path in mp4_files:
        digest = hashlib.sha256(file_path.read_bytes()).hexdigest()
        command = [
            str(args.drive_uploader),
            "-credentials", str(args.drive_credentials),
            "-token", str(args.drive_token),
            "-folder", args.drive_folder,
            "-file", str(file_path),
            "-name", file_path.name,
            "-sha256", digest,
        ]
        result = subprocess.run(command, check=True, capture_output=True, text=True)
        output = result.stdout.strip()
        expected_parent = f"parent={args.drive_folder}"
        expected_sha = f"sha256={digest}"
        if "DRIVE_UPLOAD_PASS " not in output or expected_parent not in output or expected_sha not in output:
            raise RuntimeError(f"RenderingGen upload verification failed for {file_path.name}: {output or result.stderr.strip()}")
        if f"bytes={file_path.stat().st_size}" not in output:
            raise RuntimeError(f"RenderingGen reported a byte-count mismatch for {file_path.name}: {output}")
        print(output, flush=True)


def cli_arguments(argv=None):
    global CHRONON_CLI, ASSETS_ROOT, OUT_DIR
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cli", type=Path, default=CHRONON_CLI, help="Chronon3D CLI executable")
    parser.add_argument("--assets-root", type=Path, default=ASSETS_ROOT, help="Chronon3D asset root")
    parser.add_argument("--output-dir", type=Path, default=OUT_DIR, help="Directory for plans and local renders")
    parser.add_argument("--validate-only", action="store_true", help="Write and validate plans without rendering")
    parser.add_argument("--force-render", action="store_true", help="Render again instead of reusing existing MP4 files")
    parser.add_argument("--upload", action="store_true", help="Upload verified MP4 deliverables to the configured Google Drive folder")
    parser.add_argument("--upload-only", action="store_true", help="Revalidate and upload existing verified suite MP4s without rerendering")
    parser.add_argument("--drive-uploader", type=Path, default=DRIVE_UPLOADER, help="RenderingGen drive-upload executable")
    parser.add_argument("--drive-credentials", type=Path, default=DRIVE_CREDENTIALS, help="Google OAuth credentials JSON")
    parser.add_argument("--drive-token", type=Path, default=DRIVE_TOKEN, help="Google OAuth token JSON")
    parser.add_argument("--drive-folder", default=DRIVE_FOLDER_ID, help="Destination Google Drive folder id")
    return parser.parse_args(argv)


def main(argv=None):
    global CHRONON_CLI, ASSETS_ROOT, OUT_DIR
    args = cli_arguments(argv)
    CHRONON_CLI = args.cli.resolve()
    ASSETS_ROOT = args.assets_root.resolve()
    OUT_DIR = args.output_dir.resolve()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    if args.upload_only:
        if args.validate_only or args.force_render:
            raise SystemExit("--upload-only cannot be combined with other selection/render flags")
        args.upload = True
    if args.upload and args.validate_only:
        raise SystemExit("--upload cannot be combined with --validate-only")
    if args.upload:
        validate_upload_setup(args)

    selected_plans = [(item_id, builder()) for item_id, builder in PRESET_SUITE]
    print(f"=== Starting Chronon multi_image_duo_soft_v2 suite ({len(selected_plans)} plans) ===", flush=True)
    plan_files = []
    for item_id, plan_data in selected_plans:
        validate_plan_contract(item_id, plan_data)
        plan_data["output"]["path"] = f"{item_id}.mp4"
        plan_path = OUT_DIR / f"{item_id}.plan.json"
        plan_path.write_text(json.dumps(plan_data, indent=2) + "\n")
        for layer in plan_data["layers"]:
            if layer.get("type") == "image":
                asset_path = ASSETS_ROOT / layer["asset"]
                if not asset_path.is_file():
                    raise SystemExit(f"Missing image asset for {item_id}: {asset_path}")
        if not CHRONON_CLI.is_file():
            raise SystemExit(f"Chronon3D CLI not found: {CHRONON_CLI}; pass --cli to override")

        vcmd = [str(CHRONON_CLI), "validate", "--plan", str(plan_path), "--assets-root", str(ASSETS_ROOT)]
        vres = subprocess.run(vcmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if vres.returncode != 0:
            raise SystemExit(f"[VALIDATION FAIL] {item_id}:\n{vres.stderr}\n{vres.stdout}")
        plan_files.append((item_id, plan_path))
        print(f"  [Validated] {plan_path.name}")

    if args.validate_only:
        print(f"PASS: validated {len(plan_files)} plans; no rendering or upload was performed.")
        return 0

    if args.upload_only:
        load_verifier().main([str(OUT_DIR)])
        upload_deliverables([OUT_DIR / f"{item_id}.mp4" for item_id, _ in plan_files], args)
        return 0

    def render_worker(item):
        item_id, plan_path = item
        out_mp4 = OUT_DIR / f"{item_id}.mp4"
        out_png = OUT_DIR / f"{item_id}.png"
        if (not args.force_render and out_mp4.exists() and out_mp4.stat().st_size > 500000
                and out_mp4.stat().st_mtime >= plan_path.stat().st_mtime):
            print(f"  Found current render {item_id}.mp4 ({out_mp4.stat().st_size:,} bytes)", flush=True)
            if not out_png.exists():
                subprocess.run(["ffmpeg", "-y", "-ss", "00:00:02.500", "-i", str(out_mp4), "-vframes", "1", str(out_png)],
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return [out_mp4] + ([out_png] if out_png.exists() else [])
        cmd = [
            str(CHRONON_CLI), "render", "--backend", "software", "--plan", str(plan_path),
            "--assets-root", str(ASSETS_ROOT), "-o", str(out_mp4), "--ffmpeg-mode", "pipe",
            "--codec", "h264", "--encode-preset", "fast",
        ]
        print(f"[Starting Render] {item_id} (150 frames @ 30fps)...", flush=True)
        start = time.time()
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if result.returncode != 0:
            print(f"  [ERROR] {item_id}: {result.stderr}\n{result.stdout}", flush=True)
            return []
        print(f"  Rendered {item_id}.mp4 in {time.time() - start:.1f}s ({out_mp4.stat().st_size:,} bytes)", flush=True)
        subprocess.run(["ffmpeg", "-y", "-ss", "00:00:02.500", "-i", str(out_mp4), "-vframes", "1", str(out_png)],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return [out_mp4] + ([out_png] if out_png.exists() else [])

    print(f"\n=== Rendering {len(plan_files)} compositions (max_workers=2) ===", flush=True)
    rendered_files = []
    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = {executor.submit(render_worker, item): item for item in plan_files}
        for future in as_completed(futures):
            item_id, _ = futures[future]
            try:
                files = future.result()
            except Exception as exc:
                raise RuntimeError(f"Render failed for {item_id}: {exc}") from exc
            if not files or not (OUT_DIR / f"{item_id}.mp4").is_file():
                raise RuntimeError(f"Render failed for {item_id}; see renderer output above")
            rendered_files.extend(files)
    print(f"=== All {len(plan_files)} renders are ready ===", flush=True)
    # verify_video checks the shared duo slots: same geometry, so the v1
    # verifier validates the soft suite without modification.
    verifier = load_verifier()
    frames_dir = OUT_DIR / "verify_frames"
    manifest = []
    for item_id, _ in plan_files:
        record = verifier.verify_video(OUT_DIR / f"{item_id}.mp4", frames_dir)
        manifest.append(record)
        print(f"verified {item_id}.mp4: cards L/R coverage "
              f"{record['left_card_coverage']}/{record['right_card_coverage']}", flush=True)
    (OUT_DIR / "soft_v2_verify_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    if args.upload:
        upload_deliverables(rendered_files, args)
    else:
        print("Local-only mode: no Google Drive request was made (pass --upload to opt in).", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
