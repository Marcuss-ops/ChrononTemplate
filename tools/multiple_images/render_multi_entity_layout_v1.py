#!/usr/bin/env python3
"""
Chronon Multi-Entity Layout V1 Engine & Showcase Suite
Implements the multi_entity_layout_v1 architecture:
- EntityGroup
- LayoutResolver (Duo 620x720 @ x=480, x=1440)
- FocusScheduler (Primary focus, Secondary de-emphasis, Balanced settle)

Renders the 5 multi_image_duo_v1 presets (1920x1080, 5.0s @ 30fps):
1. duo_split_reveal
2. duo_depth_stagger
3. duo_cross_focus
4. duo_parallax_balance
5. duo_compare_hold

Zero edge halo, zero letterbox black bands, pre-baked 4x Lanczos anti-aliased cards.
Drive upload uses RenderingGen's verified uploader and the configured destination folder.
"""

import argparse
import copy
import hashlib
import json
import subprocess
import time
import importlib.util
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

VERIFY_SCRIPT = Path(__file__).with_name("verify_multi_image_duo_v1.py")


def load_verifier():
    spec = importlib.util.spec_from_file_location("verify_multi_image_duo_v1", VERIFY_SCRIPT)
    if spec is None or spec.loader is None:
        raise ImportError(f"Unable to load canary verifier: {VERIFY_SCRIPT}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]

TEMPLATE_DIR = Path(__file__).resolve().parents[2]
BASE_DIR = TEMPLATE_DIR.parent
CHRONON_DIR = BASE_DIR / "Chronon3d"
CHRONON_CLI = CHRONON_DIR / "build/chronon/linux-video-fast-dev/apps/chronon3d_cli/chronon3d_cli"
ASSETS_ROOT = CHRONON_DIR
OUT_DIR = TEMPLATE_DIR / "out/multi_image_duo_v1"
DRIVE_FOLDER_ID = "1J_xUGo_bchzXDIGqSX04CU44c_Dm3SxS"
DRIVE_UPLOADER = REPOSITORY_ROOT / "RenderingGen/bin/drive-upload"
DRIVE_CREDENTIALS = Path.home() / ".config/velox/credentials.json"
DRIVE_TOKEN = Path.home() / ".config/velox/token.json"

CANARY_VARIANTS = {
    "people": ("assets/images/dual_entity_left.png", "assets/images/dual_entity_right.png"),
    "brand": ("assets/images/card_quad_3.png", "assets/images/card_quad_4.png"),
    "generic": ("assets/images/minimalist_landscape.png", "assets/images/camera_reference.jpg"),
}
CANARY_PRESET = "duo_compare_hold"

def make_canary_plan(variant, image_paths):
    if variant not in CANARY_VARIANTS:
        raise ValueError(f"Unknown multi-image canary variant: {variant}")
    if len(image_paths) != 2:
        raise ValueError(f"{variant} canary requires exactly two image assets")
    plan = copy.deepcopy(PRESET_BUILDERS[CANARY_PRESET]())
    plan["job_id"] = f"canary_{variant}_{CANARY_PRESET}"
    plan["output"]["path"] = f"{plan['job_id']}.mp4"
    image_layers = [layer for layer in plan["layers"] if layer.get("type") == "image"]
    if len(image_layers) != 2:
        raise ValueError(f"{plan['job_id']} must contain exactly two image layers")
    for layer, asset in zip(image_layers, image_paths):
        layer["asset"] = asset
    return plan


def cli_arguments(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cli", type=Path, default=CHRONON_CLI, help="Chronon3D CLI executable")
    parser.add_argument("--assets-root", type=Path, default=ASSETS_ROOT, help="Chronon3D asset root")
    parser.add_argument("--output-dir", type=Path, default=OUT_DIR, help="Directory for plans and local renders")
    parser.add_argument("--validate-only", action="store_true", help="Write and validate plans without rendering")
    parser.add_argument("--canary-only", action="store_true", help="Build/render only the people, brand and generic canaries")
    parser.add_argument("--skip-canaries", action="store_true", help="Build/render the five standard presets only")
    parser.add_argument("--force-render", action="store_true", help="Render again instead of reusing existing MP4 files")
    parser.add_argument("--upload", action="store_true", help="Explicitly upload MP4 deliverables to the configured Google Drive folder via RenderingGen")
    parser.add_argument("--upload-only", action="store_true", help="Revalidate and upload existing verified suite MP4s without rerendering")
    parser.add_argument("--drive-uploader", type=Path, default=DRIVE_UPLOADER, help="RenderingGen drive-upload executable")
    parser.add_argument("--drive-credentials", type=Path, default=DRIVE_CREDENTIALS, help="Google OAuth credentials JSON")
    parser.add_argument("--drive-token", type=Path, default=DRIVE_TOKEN, help="Google OAuth token JSON")
    parser.add_argument("--drive-folder", default=DRIVE_FOLDER_ID, help="Destination Google Drive folder id")
    return parser.parse_args(argv)


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
        focus_keyframes.append({
            key["frame"]: max(key["value"]) if isinstance(key["value"], (list, tuple)) else key["value"]
            for key in scale_track.get("keyframes", [])
        })

        # Scene coordinates are relative to the canvas center. Allow the mild
        # focus scale while enforcing the documented inset on every side.
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
    probe = subprocess.run(
        [str(args.drive_uploader), "-h"], capture_output=True, text=True, check=False
    )
    if "-sha256" not in probe.stderr and "-sha256" not in probe.stdout:
        raise RuntimeError("RenderingGen drive-upload binary does not support the required SHA-256 verification flag")


def upload_deliverables(rendered_files, args):
    expected_names = {
        f"canary_{variant}_{CANARY_PRESET}.mp4" for variant in CANARY_VARIANTS
    } if args.canary_only else {
        *(f"{preset_id}.mp4" for preset_id in PRESET_BUILDERS),
        *(f"canary_{variant}_{CANARY_PRESET}.mp4" for variant in CANARY_VARIANTS),
    }
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


def _new_main(argv=None):
    global CHRONON_CLI, ASSETS_ROOT, OUT_DIR
    args = cli_arguments(argv)
    CHRONON_CLI = args.cli.resolve()
    ASSETS_ROOT = args.assets_root.resolve()
    OUT_DIR = args.output_dir.resolve()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    if args.upload_only:
        if args.canary_only or args.skip_canaries or args.validate_only or args.force_render:
            raise SystemExit("--upload-only requires the complete eight-file suite and cannot be combined with other selection/render flags")
        args.upload = True
    if args.upload and args.validate_only:
        raise SystemExit("--upload cannot be combined with --validate-only")
    if args.upload and args.canary_only:
        print("Upload is enabled explicitly; only the three canary MP4 files will be uploaded.", flush=True)
    if args.upload:
        validate_upload_setup(args)

    selected_plans = []
    if not args.canary_only:
        selected_plans.extend((item_id, builder()) for item_id, builder in PRESET_SUITE)
    if not args.skip_canaries:
        for variant, image_paths in CANARY_VARIANTS.items():
            selected_plans.append((f"canary_{variant}_{CANARY_PRESET}", make_canary_plan(variant, image_paths)))

    print(f"=== Starting Chronon multi_image_duo_v1 suite ({len(selected_plans)} plans) ===", flush=True)
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
        print(f"  ✓ [Validated] {plan_path.name}")

    if args.validate_only:
        print(f"PASS: validated {len(plan_files)} plans; no rendering or upload was performed.")
        return 0

    if args.upload_only:
        load_verifier().main([str(OUT_DIR), "--canaries"])
        upload_deliverables([OUT_DIR / f"{item_id}.mp4" for item_id, _ in plan_files], args)
        return 0

    def render_worker(item):
        item_id, plan_path = item
        out_mp4 = OUT_DIR / f"{item_id}.mp4"
        out_png = OUT_DIR / f"{item_id}.png"
        if (not args.force_render and out_mp4.exists() and out_mp4.stat().st_size > 500000
                and out_mp4.stat().st_mtime >= plan_path.stat().st_mtime):
            print(f"  ✓ Found current render {item_id}.mp4 ({out_mp4.stat().st_size:,} bytes)", flush=True)
            if not out_png.exists():
                subprocess.run(["ffmpeg", "-y", "-ss", "00:00:02.500", "-i", str(out_mp4), "-vframes", "1", str(out_png)],
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return [out_mp4] + ([out_png] if out_png.exists() else [])

        cmd = [
            str(CHRONON_CLI), "render", "--backend", "software", "--plan", str(plan_path),
            "--assets-root", str(ASSETS_ROOT), "-o", str(out_mp4), "--ffmpeg-mode", "pipe",
            "--codec", "h264", "--encode-preset", "fast"
        ]
        print(f"[Starting Render] {item_id} (150 frames @ 30fps)...", flush=True)
        start = time.time()
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if result.returncode != 0:
            print(f"  [ERROR] {item_id}: {result.stderr}\n{result.stdout}", flush=True)
            return []
        print(f"  ✓ Rendered {item_id}.mp4 in {time.time() - start:.1f}s ({out_mp4.stat().st_size:,} bytes)", flush=True)
        subprocess.run(["ffmpeg", "-y", "-ss", "00:00:02.500", "-i", str(out_mp4), "-vframes", "1", str(out_png)],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return [out_mp4] + ([out_png] if out_png.exists() else [])

    print(f"\n=== Rendering {len(plan_files)} compositions (max_workers=3) ===", flush=True)
    rendered_files = []
    with ThreadPoolExecutor(max_workers=3) as executor:
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
    verify_args = [str(OUT_DIR)]
    if args.canary_only:
        verify_args.append("--canaries-only")
    elif not args.skip_canaries:
        verify_args.append("--canaries")
    load_verifier().main(verify_args)
    if args.upload:
        upload_deliverables(rendered_files, args)
    else:
        print("Local-only mode: no Google Drive request was made (pass --upload to opt in).", flush=True)
    return 0


# Scene constants
WIDTH = 1920
HEIGHT = 1080
FPS = 30
DURATION_FRAMES = 150  # Exactly 5.0 seconds

# Recommended safe layout for 2 images:
# Left: x = 480, y = 540, w = 620, h = 720  -> center: [-480, 0]
# Right: x = 1440, y = 540, w = 620, h = 720 -> center: [480, 0]
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
        "duration_frames": DURATION_FRAMES
    }


# =============================================================================
# 1. duo_split_reveal
# 0.0 - 0.8s: left/right reveal
# 0.8 - 1.6s: settle
# 1.6 - 2.8s: focus left
# 2.8 - 4.0s: focus right
# 4.0 - 5.0s: both visible, balanced
# =============================================================================
def build_01_duo_split_reveal():
    return {
        "schema": "chronon.render-plan.v3",
        "version": 3,
        "job_id": "duo_split_reveal",
        "canvas": {"width": WIDTH, "height": HEIGHT, "fps_num": FPS, "fps_den": 1, "duration_frames": DURATION_FRAMES},
        "output": {"path": "duo_split_reveal.mp4", "format": "mp4", "codec": "h264"},
        "layers": [
            make_bg_layer(),
            # Left Card
            {
                "id": "card_left",
                "type": "image",
                "asset": IMAGE_LEFT,
                "size": [CARD_W, CARD_H],
                "position": [LEFT_X, 0],
                "radius": 0.0,
                "fit": "cover",
                "enable_3d": True,
                "start_frame": 0,
                "duration_frames": DURATION_FRAMES,
                "animation": {
                    "tracks": [
                        {"property": "position_x", "easing": "out_cubic", "keyframes": [
                            {"frame": 0, "value": -740.0},
                            {"frame": 24, "value": 0.0},
                            {"frame": 149, "value": 0.0}
                        ]},
                        {"property": "scale", "easing": "in_out_cubic", "keyframes": [
                            {"frame": 0, "value": 0.92},
                            {"frame": 24, "value": 1.0},
                            {"frame": 48, "value": 1.0},
                            {"frame": 60, "value": 1.04},
                            {"frame": 84, "value": 1.04},
                            {"frame": 96, "value": 0.96},
                            {"frame": 120, "value": 0.96},
                            {"frame": 132, "value": 1.0},
                            {"frame": 149, "value": 1.0}
                        ]},
                        {"property": "opacity", "easing": "in_out_cubic", "keyframes": [
                            {"frame": 0, "value": 0.0},
                            {"frame": 18, "value": 1.0},
                            {"frame": 84, "value": 1.0},
                            {"frame": 96, "value": 0.78},
                            {"frame": 120, "value": 0.78},
                            {"frame": 132, "value": 1.0},
                            {"frame": 149, "value": 1.0}
                        ]}
                    ]
                }
            },
            # Right Card
            {
                "id": "card_right",
                "type": "image",
                "asset": IMAGE_RIGHT,
                "size": [CARD_W, CARD_H],
                "position": [RIGHT_X, 0],
                "radius": 0.0,
                "fit": "cover",
                "enable_3d": True,
                "start_frame": 0,
                "duration_frames": DURATION_FRAMES,
                "animation": {
                    "tracks": [
                        {"property": "position_x", "easing": "out_cubic", "keyframes": [
                            {"frame": 0, "value": 740.0},
                            {"frame": 24, "value": 0.0},
                            {"frame": 149, "value": 0.0}
                        ]},
                        {"property": "scale", "easing": "in_out_cubic", "keyframes": [
                            {"frame": 0, "value": 0.92},
                            {"frame": 24, "value": 1.0},
                            {"frame": 48, "value": 1.0},
                            {"frame": 60, "value": 0.96},
                            {"frame": 84, "value": 0.96},
                            {"frame": 96, "value": 1.04},
                            {"frame": 120, "value": 1.04},
                            {"frame": 132, "value": 1.0},
                            {"frame": 149, "value": 1.0}
                        ]},
                        {"property": "opacity", "easing": "in_out_cubic", "keyframes": [
                            {"frame": 0, "value": 0.0},
                            {"frame": 18, "value": 1.0},
                            {"frame": 48, "value": 1.0},
                            {"frame": 60, "value": 0.78},
                            {"frame": 84, "value": 0.78},
                            {"frame": 96, "value": 1.0},
                            {"frame": 149, "value": 1.0}
                        ]}
                    ]
                }
            }
        ]
    }


# =============================================================================
# 2. duo_depth_stagger
# 0.0 - 0.7s: left in (Z negative)
# 0.2 - 0.9s: right in (Z negative)
# 1.0 - 2.1s: left focus
# 2.1 - 3.3s: right focus
# 3.3 - 5.0s: both calm
# =============================================================================
def build_02_duo_depth_stagger():
    return {
        "schema": "chronon.render-plan.v3",
        "version": 3,
        "job_id": "duo_depth_stagger",
        "canvas": {"width": WIDTH, "height": HEIGHT, "fps_num": FPS, "fps_den": 1, "duration_frames": DURATION_FRAMES},
        "output": {"path": "duo_depth_stagger.mp4", "format": "mp4", "codec": "h264"},
        "layers": [
            make_bg_layer(),
            # Left Card
            {
                "id": "card_left",
                "type": "image",
                "asset": IMAGE_LEFT,
                "size": [CARD_W, CARD_H],
                "position": [LEFT_X, 0],
                "radius": 0.0,
                "fit": "cover",
                "enable_3d": True,
                "start_frame": 0,
                "duration_frames": DURATION_FRAMES,
                "animation": {
                    "tracks": [
                        {"property": "position_z", "easing": "out_cubic", "keyframes": [
                            {"frame": 0, "value": -320.0},
                            {"frame": 21, "value": 0.0},
                            {"frame": 30, "value": 22.0},
                            {"frame": 63, "value": 22.0},
                            {"frame": 75, "value": -12.0},
                            {"frame": 99, "value": -12.0},
                            {"frame": 110, "value": 0.0},
                            {"frame": 149, "value": 0.0}
                        ]},
                        {"property": "scale", "easing": "out_cubic", "keyframes": [
                            {"frame": 0, "value": 0.86},
                            {"frame": 21, "value": 1.0},
                            {"frame": 30, "value": 1.045},
                            {"frame": 63, "value": 1.045},
                            {"frame": 75, "value": 0.96},
                            {"frame": 99, "value": 0.96},
                            {"frame": 110, "value": 1.0},
                            {"frame": 149, "value": 1.0}
                        ]},
                        {"property": "opacity", "easing": "out_cubic", "keyframes": [
                            {"frame": 0, "value": 0.0},
                            {"frame": 16, "value": 1.0},
                            {"frame": 63, "value": 1.0},
                            {"frame": 75, "value": 0.80},
                            {"frame": 99, "value": 0.80},
                            {"frame": 110, "value": 1.0},
                            {"frame": 149, "value": 1.0}
                        ]}
                    ]
                }
            },
            # Right Card
            {
                "id": "card_right",
                "type": "image",
                "asset": IMAGE_RIGHT,
                "size": [CARD_W, CARD_H],
                "position": [RIGHT_X, 0],
                "radius": 0.0,
                "fit": "cover",
                "enable_3d": True,
                "start_frame": 0,
                "duration_frames": DURATION_FRAMES,
                "animation": {
                    "tracks": [
                        {"property": "position_z", "easing": "out_cubic", "keyframes": [
                            {"frame": 6, "value": -320.0},
                            {"frame": 27, "value": 0.0},
                            {"frame": 30, "value": -12.0},
                            {"frame": 63, "value": -12.0},
                            {"frame": 75, "value": 22.0},
                            {"frame": 99, "value": 22.0},
                            {"frame": 110, "value": 0.0},
                            {"frame": 149, "value": 0.0}
                        ]},
                        {"property": "scale", "easing": "out_cubic", "keyframes": [
                            {"frame": 6, "value": 0.86},
                            {"frame": 27, "value": 1.0},
                            {"frame": 30, "value": 0.96},
                            {"frame": 63, "value": 0.96},
                            {"frame": 75, "value": 1.045},
                            {"frame": 99, "value": 1.045},
                            {"frame": 110, "value": 1.0},
                            {"frame": 149, "value": 1.0}
                        ]},
                        {"property": "opacity", "easing": "out_cubic", "keyframes": [
                            {"frame": 6, "value": 0.0},
                            {"frame": 22, "value": 0.80},
                            {"frame": 63, "value": 0.80},
                            {"frame": 75, "value": 1.0},
                            {"frame": 149, "value": 1.0}
                        ]}
                    ]
                }
            }
        ]
    }


# =============================================================================
# 3. duo_cross_focus
# 0.0 - 0.9s: both reveal
# 0.9 - 2.0s: left highlighted
# 2.0 - 3.1s: transition
# 3.1 - 4.2s: right highlighted
# 4.2 - 5.0s: both normalize
# =============================================================================
def build_03_duo_cross_focus():
    return {
        "schema": "chronon.render-plan.v3",
        "version": 3,
        "job_id": "duo_cross_focus",
        "canvas": {"width": WIDTH, "height": HEIGHT, "fps_num": FPS, "fps_den": 1, "duration_frames": DURATION_FRAMES},
        "output": {"path": "duo_cross_focus.mp4", "format": "mp4", "codec": "h264"},
        "layers": [
            make_bg_layer(),
            # Left Card
            {
                "id": "card_left",
                "type": "image",
                "asset": IMAGE_LEFT,
                "size": [CARD_W, CARD_H],
                "position": [LEFT_X, 0],
                "radius": 0.0,
                "fit": "cover",
                "enable_3d": True,
                "start_frame": 0,
                "duration_frames": DURATION_FRAMES,
                "animation": {
                    "tracks": [
                        {"property": "scale", "easing": "in_out_cubic", "keyframes": [
                            {"frame": 0, "value": 0.94},
                            {"frame": 27, "value": 1.0},
                            {"frame": 35, "value": 1.035},
                            {"frame": 60, "value": 1.035},
                            {"frame": 78, "value": 0.965},
                            {"frame": 126, "value": 0.965},
                            {"frame": 138, "value": 1.0},
                            {"frame": 149, "value": 1.0}
                        ]},
                        {"property": "position_z", "easing": "in_out_cubic", "keyframes": [
                            {"frame": 0, "value": 0.0},
                            {"frame": 35, "value": 20.0},
                            {"frame": 60, "value": 20.0},
                            {"frame": 78, "value": -15.0},
                            {"frame": 126, "value": -15.0},
                            {"frame": 138, "value": 0.0},
                            {"frame": 149, "value": 0.0}
                        ]},
                        {"property": "opacity", "easing": "in_out_cubic", "keyframes": [
                            {"frame": 0, "value": 0.0},
                            {"frame": 20, "value": 1.0},
                            {"frame": 60, "value": 1.0},
                            {"frame": 78, "value": 0.76},
                            {"frame": 126, "value": 0.76},
                            {"frame": 138, "value": 1.0},
                            {"frame": 149, "value": 1.0}
                        ]}
                    ]
                }
            },
            # Right Card
            {
                "id": "card_right",
                "type": "image",
                "asset": IMAGE_RIGHT,
                "size": [CARD_W, CARD_H],
                "position": [RIGHT_X, 0],
                "radius": 0.0,
                "fit": "cover",
                "enable_3d": True,
                "start_frame": 0,
                "duration_frames": DURATION_FRAMES,
                "animation": {
                    "tracks": [
                        {"property": "scale", "easing": "in_out_cubic", "keyframes": [
                            {"frame": 0, "value": 0.94},
                            {"frame": 27, "value": 1.0},
                            {"frame": 35, "value": 0.965},
                            {"frame": 60, "value": 0.965},
                            {"frame": 78, "value": 1.035},
                            {"frame": 126, "value": 1.035},
                            {"frame": 138, "value": 1.0},
                            {"frame": 149, "value": 1.0}
                        ]},
                        {"property": "position_z", "easing": "in_out_cubic", "keyframes": [
                            {"frame": 0, "value": 0.0},
                            {"frame": 35, "value": -15.0},
                            {"frame": 60, "value": -15.0},
                            {"frame": 78, "value": 20.0},
                            {"frame": 126, "value": 20.0},
                            {"frame": 138, "value": 0.0},
                            {"frame": 149, "value": 0.0}
                        ]},
                        {"property": "opacity", "easing": "in_out_cubic", "keyframes": [
                            {"frame": 0, "value": 0.0},
                            {"frame": 20, "value": 1.0},
                            {"frame": 35, "value": 0.76},
                            {"frame": 60, "value": 0.76},
                            {"frame": 78, "value": 1.0},
                            {"frame": 149, "value": 1.0}
                        ]}
                    ]
                }
            }
        ]
    }


# =============================================================================
# 4. duo_parallax_balance
# 0.0 - 0.8s: both in with yaw
# 0.8 - 2.0s: left focus
# 2.0 - 3.2s: right focus
# 3.2 - 5.0s: both in balanced state + continuous 2.5D drift
# =============================================================================
def build_04_duo_parallax_balance():
    return {
        "schema": "chronon.render-plan.v3",
        "version": 3,
        "job_id": "duo_parallax_balance",
        "canvas": {"width": WIDTH, "height": HEIGHT, "fps_num": FPS, "fps_den": 1, "duration_frames": DURATION_FRAMES},
        "output": {"path": "duo_parallax_balance.mp4", "format": "mp4", "codec": "h264"},
        "layers": [
            make_bg_layer(),
            # Left Card
            {
                "id": "card_left",
                "type": "image",
                "asset": IMAGE_LEFT,
                "size": [CARD_W, CARD_H],
                "position": [LEFT_X, 0],
                "radius": 0.0,
                "fit": "cover",
                "enable_3d": True,
                "start_frame": 0,
                "duration_frames": DURATION_FRAMES,
                "animation": {
                    "tracks": [
                        {"property": "rotation_y", "easing": "out_cubic", "keyframes": [
                            {"frame": 0, "value": -16.0},
                            {"frame": 24, "value": 0.0},
                            {"frame": 149, "value": -1.2}
                        ]},
                        {"property": "position_z", "easing": "in_out_cubic", "keyframes": [
                            {"frame": 0, "value": -150.0},
                            {"frame": 24, "value": 0.0},
                            {"frame": 35, "value": 25.0},
                            {"frame": 60, "value": 25.0},
                            {"frame": 75, "value": -10.0},
                            {"frame": 96, "value": -10.0},
                            {"frame": 110, "value": 0.0},
                            {"frame": 149, "value": 10.0}
                        ]},
                        {"property": "scale", "easing": "in_out_cubic", "keyframes": [
                            {"frame": 0, "value": 0.92},
                            {"frame": 24, "value": 1.0},
                            {"frame": 35, "value": 1.04},
                            {"frame": 60, "value": 1.04},
                            {"frame": 75, "value": 0.97},
                            {"frame": 96, "value": 0.97},
                            {"frame": 110, "value": 1.0},
                            {"frame": 149, "value": 1.015}
                        ]},
                        {"property": "opacity", "easing": "out_cubic", "keyframes": [
                            {"frame": 0, "value": 0.0},
                            {"frame": 18, "value": 1.0},
                            {"frame": 60, "value": 1.0},
                            {"frame": 75, "value": 0.80},
                            {"frame": 96, "value": 0.80},
                            {"frame": 110, "value": 1.0},
                            {"frame": 149, "value": 1.0}
                        ]}
                    ]
                }
            },
            # Right Card
            {
                "id": "card_right",
                "type": "image",
                "asset": IMAGE_RIGHT,
                "size": [CARD_W, CARD_H],
                "position": [RIGHT_X, 0],
                "radius": 0.0,
                "fit": "cover",
                "enable_3d": True,
                "start_frame": 0,
                "duration_frames": DURATION_FRAMES,
                "animation": {
                    "tracks": [
                        {"property": "rotation_y", "easing": "out_cubic", "keyframes": [
                            {"frame": 0, "value": 16.0},
                            {"frame": 24, "value": 0.0},
                            {"frame": 149, "value": 1.2}
                        ]},
                        {"property": "position_z", "easing": "in_out_cubic", "keyframes": [
                            {"frame": 0, "value": -150.0},
                            {"frame": 24, "value": 0.0},
                            {"frame": 35, "value": -10.0},
                            {"frame": 60, "value": -10.0},
                            {"frame": 75, "value": 25.0},
                            {"frame": 96, "value": 25.0},
                            {"frame": 110, "value": 0.0},
                            {"frame": 149, "value": 10.0}
                        ]},
                        {"property": "scale", "easing": "in_out_cubic", "keyframes": [
                            {"frame": 0, "value": 0.92},
                            {"frame": 24, "value": 1.0},
                            {"frame": 35, "value": 0.97},
                            {"frame": 60, "value": 0.97},
                            {"frame": 75, "value": 1.04},
                            {"frame": 96, "value": 1.04},
                            {"frame": 110, "value": 1.0},
                            {"frame": 149, "value": 1.015}
                        ]},
                        {"property": "opacity", "easing": "out_cubic", "keyframes": [
                            {"frame": 0, "value": 0.0},
                            {"frame": 18, "value": 1.0},
                            {"frame": 35, "value": 0.80},
                            {"frame": 60, "value": 0.80},
                            {"frame": 75, "value": 1.0},
                            {"frame": 149, "value": 1.0}
                        ]}
                    ]
                }
            }
        ]
    }


# =============================================================================
# 5. duo_compare_hold
# 0.0 - 0.7s: reveal both
# 0.7 - 1.8s: left priority
# 1.8 - 2.9s: right priority
# 2.9 - 5.0s: both on screen, equal weight (extended hold)
# =============================================================================
def build_05_duo_compare_hold():
    return {
        "schema": "chronon.render-plan.v3",
        "version": 3,
        "job_id": "duo_compare_hold",
        "canvas": {"width": WIDTH, "height": HEIGHT, "fps_num": FPS, "fps_den": 1, "duration_frames": DURATION_FRAMES},
        "output": {"path": "duo_compare_hold.mp4", "format": "mp4", "codec": "h264"},
        "layers": [
            make_bg_layer(),
            # Center delicate luminous divider line
            {
                "id": "center_divider",
                "type": "shape",
                "size": [6, 720],
                "position": [960, 540],
                "color": [0.0, 0.0, 0.0, 0.0],
                "start_frame": 0,
                "duration_frames": DURATION_FRAMES,
                "shape": {
                    "type": "path",
                    "path": [
                        {"type": "move_to", "point": [0, -360]},
                        {"type": "line_to", "point": [0, 360]}
                    ],
                    "stroke": {"color": "#38BDF8", "width": 2.0}
                },
                "effects": [
                    {"type": "glow", "radius": 12.0, "intensity": 0.5, "color": [0.2, 0.7, 1.0, 1.0]}
                ],
                "animation": {
                    "tracks": [
                        {"property": "scale_y", "easing": "out_cubic", "keyframes": [
                            {"frame": 10, "value": 0.0},
                            {"frame": 24, "value": 1.0}
                        ]},
                        {"property": "opacity", "easing": "out_cubic", "keyframes": [
                            {"frame": 10, "value": 0.0},
                            {"frame": 24, "value": 0.75},
                            {"frame": 87, "value": 0.5}
                        ]}
                    ]
                }
            },
            # Left Card
            {
                "id": "card_left",
                "type": "image",
                "asset": IMAGE_LEFT,
                "size": [CARD_W, CARD_H],
                "position": [LEFT_X, 0],
                "radius": 0.0,
                "fit": "cover",
                "enable_3d": True,
                "start_frame": 0,
                "duration_frames": DURATION_FRAMES,
                "animation": {
                    "tracks": [
                        {"property": "scale", "easing": "out_cubic", "keyframes": [
                            {"frame": 0, "value": 0.94},
                            {"frame": 21, "value": 1.0},
                            {"frame": 26, "value": 1.045},
                            {"frame": 54, "value": 1.045},
                            {"frame": 65, "value": 0.97},
                            {"frame": 87, "value": 0.97},
                            {"frame": 96, "value": 1.0},
                            {"frame": 149, "value": 1.015}
                        ]},
                        {"property": "position_z", "easing": "out_cubic", "keyframes": [
                            {"frame": 0, "value": 0.0},
                            {"frame": 26, "value": 24.0},
                            {"frame": 54, "value": 24.0},
                            {"frame": 65, "value": -10.0},
                            {"frame": 87, "value": -10.0},
                            {"frame": 96, "value": 0.0},
                            {"frame": 149, "value": 0.0}
                        ]},
                        {"property": "opacity", "easing": "out_cubic", "keyframes": [
                            {"frame": 0, "value": 0.0},
                            {"frame": 15, "value": 1.0},
                            {"frame": 54, "value": 1.0},
                            {"frame": 65, "value": 0.82},
                            {"frame": 87, "value": 0.82},
                            {"frame": 96, "value": 1.0},
                            {"frame": 149, "value": 1.0}
                        ]}
                    ]
                }
            },
            # Right Card
            {
                "id": "card_right",
                "type": "image",
                "asset": IMAGE_RIGHT,
                "size": [CARD_W, CARD_H],
                "position": [RIGHT_X, 0],
                "radius": 0.0,
                "fit": "cover",
                "enable_3d": True,
                "start_frame": 0,
                "duration_frames": DURATION_FRAMES,
                "animation": {
                    "tracks": [
                        {"property": "scale", "easing": "out_cubic", "keyframes": [
                            {"frame": 0, "value": 0.94},
                            {"frame": 21, "value": 1.0},
                            {"frame": 26, "value": 0.97},
                            {"frame": 54, "value": 0.97},
                            {"frame": 65, "value": 1.045},
                            {"frame": 87, "value": 1.045},
                            {"frame": 96, "value": 1.0},
                            {"frame": 149, "value": 1.015}
                        ]},
                        {"property": "position_z", "easing": "out_cubic", "keyframes": [
                            {"frame": 0, "value": 0.0},
                            {"frame": 26, "value": -10.0},
                            {"frame": 54, "value": -10.0},
                            {"frame": 65, "value": 24.0},
                            {"frame": 87, "value": 24.0},
                            {"frame": 96, "value": 0.0},
                            {"frame": 149, "value": 0.0}
                        ]},
                        {"property": "opacity", "easing": "out_cubic", "keyframes": [
                            {"frame": 0, "value": 0.0},
                            {"frame": 15, "value": 1.0},
                            {"frame": 26, "value": 0.82},
                            {"frame": 54, "value": 0.82},
                            {"frame": 65, "value": 1.0},
                            {"frame": 149, "value": 1.0}
                        ]}
                    ]
                }
            }
        ]
    }

PRESET_BUILDERS = {
    "duo_split_reveal": build_01_duo_split_reveal,
    "duo_depth_stagger": build_02_duo_depth_stagger,
    "duo_cross_focus": build_03_duo_cross_focus,
    "duo_parallax_balance": build_04_duo_parallax_balance,
    "duo_compare_hold": build_05_duo_compare_hold,
}
PRESET_SUITE = list(PRESET_BUILDERS.items())


def _legacy_main_unused():
    """Retired pre-contract runner retained only until existing callers migrate."""
    return

    # 1. Author and validate plans
    plan_files = []
    for item_id, builder in PRESET_SUITE:
        plan_data = builder()
        plan_path = OUT_DIR / f"{item_id}.plan.json"
        plan_path.write_text(json.dumps(plan_data, indent=2))

        vcmd = [str(CHRONON_CLI), "validate", "--plan", str(plan_path), "--assets-root", str(ASSETS_ROOT)]
        vres = subprocess.run(vcmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if vres.returncode != 0:
            print(f"  [VALIDATION FAIL] {item_id}: {vres.stderr}\n{vres.stdout}")
            sys.exit(1)
        plan_files.append((item_id, plan_path))
        print(f"  ✓ [Validated] {plan_path.name}")

    # 2. Render compositions concurrently
    def render_worker(item):
        item_id, plan_path = item
        out_mp4 = OUT_DIR / f"{item_id}.mp4"
        out_png = OUT_DIR / f"{item_id}.png"

        if out_mp4.exists() and out_mp4.stat().st_size > 500000:
            print(f"  ✓ Found existing valid render {item_id}.mp4 ({out_mp4.stat().st_size:,} bytes)", flush=True)
            if not out_png.exists():
                subprocess.run(["ffmpeg", "-y", "-ss", "00:00:02.500", "-i", str(out_mp4), "-vframes", "1", str(out_png)],
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            out_items = [out_mp4]
            if out_png.exists():
                out_items.append(out_png)
            return out_items

        cmd = [
            str(CHRONON_CLI),
            "render",
            "--backend", "software",
            "--plan", str(plan_path),
            "--assets-root", str(ASSETS_ROOT),
            "-o", str(out_mp4),
            "--ffmpeg-mode", "pipe",
            "--codec", "h264",
            "--encode-preset", "fast"
        ]
        print(f"[Starting Render] {item_id} (150 frames @ 30fps)...", flush=True)
        t0 = time.time()
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        dt = time.time() - t0
        if res.returncode != 0:
            print(f"  [ERROR] {item_id}: {res.stderr}\n{res.stdout}", flush=True)
            return []

        sz = out_mp4.stat().st_size if out_mp4.exists() else 0
        print(f"  ✓ Rendered {item_id}.mp4 in {dt:.1f}s ({sz:,} bytes)", flush=True)

        # Extract PNG poster at 2.5s (frame 75)
        subprocess.run(["ffmpeg", "-y", "-ss", "00:00:02.500", "-i", str(out_mp4), "-vframes", "1", str(out_png)],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        out_items = [out_mp4]
        if out_png.exists():
            out_items.append(out_png)
        return out_items

    print(f"\n=== Rendering {len(plan_files)} compositions (max_workers=3) ===", flush=True)
    t_start = time.time()
    rendered_files = []
    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = {executor.submit(render_worker, item): item for item in plan_files}
        for future in as_completed(futures):
            item = futures[future]
            try:
                files = future.result()
                rendered_files.extend(files)
            except Exception as e:
                print(f"  [EXCEPTION] {item[0]}: {e}", flush=True)
    print(f"=== All renders ready in {time.time() - t_start:.1f}s ===", flush=True)

    # 3. Upload to Google Drive folder 1X0nyiF82tMihNfRTAlij__bv7LwzZJ75
    print(f"\n=== Uploading to Google Drive ({DRIVE_FOLDER_ID}) ===", flush=True)
    token = refresh_drive_token()

    # List existing files in folder
    q = urllib.parse.quote(f"'{DRIVE_FOLDER_ID}' in parents and trashed = false")
    list_url = f"https://www.googleapis.com/drive/v3/files?q={q}&fields=files(id,name,webViewLink)"
    req = urllib.request.Request(list_url, headers={"Authorization": f"Bearer {token}"})
    existing = {}
    try:
        with urllib.request.urlopen(req) as resp:
            data = json.load(resp)
            for f in data.get("files", []):
                existing[f["name"]] = f
    except Exception as e:
        print(f"Could not list folder: {e}")

    uploads = []
    for fpath in rendered_files:
        fname = fpath.name
        if fname in existing:
            meta = existing[fname]
            fid = meta["id"]
            print(f"Updating existing {fname} in Google Drive (ID: {fid})...", flush=True)
            update_drive_file(token, fid, fpath)
            print(f"  ✓ Updated in place: {fname} Link: {meta.get('webViewLink')}")
            uploads.append(meta)
        else:
            print(f"Uploading {fname} ({fpath.stat().st_size:,} bytes)...", flush=True)
            meta = upload_to_drive(token, fpath, DRIVE_FOLDER_ID)
            uploads.append(meta)
            print(f"  ✓ Uploaded! ID: {meta.get('id')} Link: {meta.get('webViewLink')}")

    print("\n=== COMPLETE SUMMARY OF ALL 5 MULTI_IMAGE_DUO DELIVERABLES ===")
    for u in uploads:
        print(f"- {u.get('name')}: {u.get('id')} ({u.get('webViewLink')})")


def main(argv=None):
    return _new_main(argv)


if __name__ == "__main__":
    raise SystemExit(main())
