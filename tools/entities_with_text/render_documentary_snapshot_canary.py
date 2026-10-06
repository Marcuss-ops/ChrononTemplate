#!/usr/bin/env python3
"""Render a title-to-archive-photo handoff from native ChrononMotion poses."""

import argparse
import json
import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WORKSPACE = ROOT.parent
DUMPER = ROOT / "build/chronontemplate_dump_documentary_snapshot_pose"
ADAPTER_DUMPER = ROOT / "build/documentary-adapter/chronontemplate_dump_documentary_snapshot_plan"
CLI = Path(os.environ.get("CHRONON_CLI", WORKSPACE /
          "Chronon3d/build/chronon/linux-video-fast-dev/apps/chronon3d_cli/chronon3d_cli"))
FPS, WIDTH, HEIGHT, FRAMES = 30, 1920, 1080, 121
PHOTO = "RenderingGen/testdata/golden/gerard_butler.jpg"
FONT = "ChrononTemplate/assets/fonts/didone_font_playfair_display_italic.ttf"

STYLE_GALLERY = [
    ("snapshot_clean", "Clean", "#F2F0EA", 3, 1.0, 1.0, 0.0, 0.0, 0),
    ("snapshot_archive", "Archive", "#E8E2D5", 8, 0.78, 1.08, 0.008, 0.12, 1986),
    ("snapshot_polaroid", "Polaroid", "#F8F4E8", 18, 1.0, 1.0, 0.0, 0.0, 0),
    ("snapshot_filmstrip", "Filmstrip", "#151515", 14, 1.0, 1.08, 0.012, 0.0, 35),
    ("snapshot_evidence", "Evidence", "#C92A32", 5, 1.0, 1.0, 0.0, 0.0, 0),
    ("snapshot_newspaper", "Newspaper", "#D8D0BE", 12, 0.0, 1.32, 0.01, 0.08, 1917),
    ("snapshot_bw_documentary", "B&W Documentary", "#E8E2D5", 6, 0.0, 1.16, 0.008, 0.10, 1960),
]


def _hex_rgba(value: str) -> list[float]:
    value = value.lstrip("#")
    return [int(value[i:i + 2], 16) / 255 for i in (0, 2, 4)] + [1.0]


def _assert_adapter_fit_bounds(raw_path: Path) -> None:
    """Check the final connected Fit card against decoded source pixels."""
    pixels = raw_path.read_bytes()
    expected_bytes = WIDTH * HEIGHT * 4
    if len(pixels) != expected_bytes:
        raise SystemExit(
            f"frame 120 has {len(pixels)} bytes; expected {expected_bytes} RGBA bytes")

    image_x, image_y, plate_x, plate_y = [], [], [], []
    for y in range(150, 930):
        for x in range(300, 1620):
            offset = (y * WIDTH + x) * 4
            r, g, b, alpha = pixels[offset:offset + 4]
            if alpha < 250:
                continue
            if r < 190 or g < 185 or b < 155:
                image_x.append(x)
                image_y.append(y)
            if abs(r - 206) <= 2 and abs(g - 194) <= 2 and abs(b - 170) <= 2:
                plate_x.append(x)
                plate_y.append(y)

    if not image_x or not plate_x:
        raise SystemExit("frame 120 is missing the opaque Fit image or archive frame")
    image_bounds = (min(image_x), min(image_y), max(image_x), max(image_y))
    plate_bounds = (min(plate_x), min(plate_y), max(plate_x), max(plate_y))
    image_width = image_bounds[2] - image_bounds[0] + 1
    image_height = image_bounds[3] - image_bounds[1] + 1
    source_aspect = 1920.0 / 1472.0
    rendered_aspect = image_width / image_height
    if abs(rendered_aspect / source_aspect - 1.0) > 0.03:
        raise SystemExit(
            f"Fit image aspect changed: rendered={rendered_aspect:.4f}, "
            f"source={source_aspect:.4f}, bounds={image_bounds}")
    margins = (
        image_bounds[0] - plate_bounds[0],
        image_bounds[1] - plate_bounds[1],
        plate_bounds[2] - image_bounds[2],
        plate_bounds[3] - image_bounds[3],
    )
    if any(margin < 4 or margin > 12 for margin in margins) or \
            max(margins) - min(margins) > 4:
        raise SystemExit(
            f"archive frame does not evenly follow fitted image bounds: "
            f"image={image_bounds}, plate={plate_bounds}, margins={margins}")
    print(f"Fit source/frame bounds PASS: image={image_bounds}, plate={plate_bounds}, "
          f"margins={margins}, aspect={rendered_aspect:.4f}")


def _assert_light_leak_follows_camera_speed(plan_path: Path) -> None:
    def scalar(value):
        return float(value[0] if isinstance(value, list) else value)

    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    camera_tracks = {track["property"]: track["keyframes"]
                     for track in plan.get("camera_animation", {}).get("tracks", [])}
    props = ("camera_position_x", "camera_position_y", "camera_position_z",
             "camera_rotation_x", "camera_rotation_y", "camera_rotation_z")
    if any(prop not in camera_tracks for prop in props):
        raise SystemExit("connected plan is missing camera pose tracks for leak synchronization")
    frame_count = int(plan["canvas"]["duration_frames"])
    samples = []
    for frame in range(frame_count):
        pose = []
        for prop in props:
            keys = camera_tracks[prop]
            exact = next((scalar(key["value"]) for key in keys if int(key["frame"]) == frame), None)
            if exact is None:
                raise SystemExit(f"camera track {prop} has no exact sample at frame {frame}")
            pose.append(float(exact))
        samples.append(pose)
    speed = [0.0]
    for before, after in zip(samples, samples[1:]):
        delta = [after[i] - before[i] for i in range(6)]
        delta[3:] = [value * 0.01745329252 * 900.0 for value in delta[3:]]
        speed.append(sum(value * value for value in delta) ** 0.5)
    leak = next((layer for layer in plan["layers"]
                 if layer.get("id") == "documentary-motion-light-leak"), None)
    if not leak:
        raise SystemExit("connected plan has no native light-leak layer")
    opacity = next((track["keyframes"] for track in leak.get("animation", {}).get("tracks", [])
                    if track.get("property") == "opacity"), None)
    if not opacity:
        raise SystemExit("native light-leak layer has no animated opacity track")
    opacity_by_frame = {int(key["frame"]): scalar(key["value"]) for key in opacity}
    leak_peak = max(opacity_by_frame, key=opacity_by_frame.get)
    speed_peak = max(range(len(speed)), key=speed.__getitem__)
    final_frame = frame_count - 1
    if abs(leak_peak - speed_peak) > 1 or opacity_by_frame.get(final_frame, 1.0) > 1e-5:
        raise SystemExit(f"light leak is not synchronized or settled: leak={leak_peak}, "
                         f"camera_speed={speed_peak}, final_opacity={opacity_by_frame.get(final_frame)}")
    print(f"Light leak motion sync PASS: peak frame={leak_peak}, "
          f"camera speed peak={speed_peak}, final opacity={opacity_by_frame[final_frame]:.4f}")


def _assert_red_portal_coverage(raw_path: Path) -> None:
    pixels = raw_path.read_bytes()
    expected_bytes = WIDTH * HEIGHT * 4
    if len(pixels) != expected_bytes:
        raise SystemExit(f"portal frame has {len(pixels)} bytes; expected {expected_bytes}")
    red = 0
    for offset in range(0, len(pixels), 4):
        r, g, b, alpha = pixels[offset:offset + 4]
        if alpha > 245 and r > 120 and r > g * 2 and r > b * 2:
            red += 1
    coverage = red / (WIDTH * HEIGHT)
    if coverage < 0.90:
        raise SystemExit(f"red portal coverage is only {coverage:.1%}; expected at least 90%")
    print(f"Red portal viewport coverage PASS: {coverage:.1%}")


def build_style_gallery_plan() -> dict:
    layers = [{"id": "gallery-background", "type": "color", "color": [0.025, 0.026, 0.028, 1.0],
               "size": [WIDTH, HEIGHT], "screen_space": True, "start_frame": 0, "duration_frames": 1}]
    card_width, image_height, image_width = 218, 164, 208
    gap = 22
    total = len(STYLE_GALLERY) * card_width + (len(STYLE_GALLERY) - 1) * gap
    left = (WIDTH - total) / 2 + card_width / 2
    center_y = HEIGHT / 2 - 12
    for index, (style_id, label, border, border_width, saturation, contrast, grain, vignette, seed) in enumerate(STYLE_GALLERY):
        x = left + index * (card_width + gap)
        base_id = style_id.replace("_", "-")
        layers.append({"id": base_id + "-frame", "type": "shape",
                       "size": [card_width, image_height + 38], "position": [x, center_y],
                       "start_frame": 0, "duration_frames": 1,
                       "shape": {"type": "rect", "fill": _hex_rgba(border)}})
        layers.append({"id": base_id + "-image", "type": "image", "asset": PHOTO,
                       "size": [image_width, image_height],
                       "position": [x - WIDTH / 2, center_y - 4 - HEIGHT / 2],
                       "fit": "cover", "start_frame": 0, "duration_frames": 1,
                       "effects": (
                           ([{"type": "catalog", "effect_id": "color.saturation",
                             "params": [{"param": "value", "value": saturation}]}] if saturation != 1.0 else []) +
                           ([{"type": "catalog", "effect_id": "color.contrast",
                             "params": [{"param": "value", "value": contrast}]}] if contrast != 1.0 else []) +
                           ([{"type": "vignette", "radius": 0.72, "softness": 0.5, "amount": vignette}]
                            if vignette > 0.0 else []) +
                           ([{"type": "noise", "amount": grain, "seed": seed, "animated": False,
                             "size": 1.0, "color_mode": "monochrome"}] if grain > 0.0 else []))})
        layers.append({"id": base_id + "-label", "type": "text", "text": label,
                       "size": [card_width + 12, 44],
                       "position": [x, center_y + image_height / 2 + 48],
                       "start_frame": 0, "duration_frames": 1,
                       "style": {"font": FONT, "font_size": 22, "fill": "#F1EBDD"}})
    return {"schema": "chronon.render-plan.v3", "version": 3,
            "job_id": "documentary_snapshot_style_gallery_v1",
            "canvas": {"width": WIDTH, "height": HEIGHT, "fps_num": FPS,
                       "fps_den": 1, "duration_frames": 1},
            "layers": layers,
            "output": {"path": "documentary_snapshot_style_gallery_v1.mp4",
                       "format": "mp4", "codec": "h264"}}


def build_fit_gallery_plan() -> dict:
    """Compare native image contain, cover, and explicit normalized crop."""
    layers = [{"id": "fit-gallery-background", "type": "color",
               "color": [0.025, 0.026, 0.028, 1.0], "size": [WIDTH, HEIGHT],
               "screen_space": True, "start_frame": 0, "duration_frames": 1}]
    labels = [("fit", "FIT / CONTAIN", "contain", None),
              ("fill", "FILL / COVER", "cover", None),
              ("crop", "EXPLICIT CROP", "cover",
               {"enabled": True, "origin": [0.14, 0.08], "size": [0.72, 0.84]})]
    # The source is 1920x1472 (1.304:1); use a 1.82:1 card so Contain and
    # Cover produce clearly different visible bounds in the pixel review.
    card_width, card_height, image_width, image_height = 440, 300, 400, 220
    center_y = HEIGHT / 2 - 15
    centers = [WIDTH / 2 - 490, WIDTH / 2, WIDTH / 2 + 490]
    for (layer_id, label, fit, crop), x in zip(labels, centers):
        layers.append({"id": layer_id + "-frame", "type": "shape",
                       "size": [card_width, card_height], "position": [x, center_y],
                       "start_frame": 0, "duration_frames": 1,
                       "shape": {"type": "rect", "fill": [0.91, 0.88, 0.82, 1.0]}})
        image_layer = {"id": layer_id + "-image", "type": "image", "asset": PHOTO,
                       "size": [image_width, image_height],
                       "position": [x - WIDTH / 2, center_y - HEIGHT / 2],
                       "fit": fit, "start_frame": 0, "duration_frames": 1}
        if crop is not None:
            image_layer["crop"] = crop
        layers.append(image_layer)
        layers.append({"id": layer_id + "-label", "type": "text", "text": label,
                       "size": [card_width, 46], "position": [x, center_y + 194],
                       "start_frame": 0, "duration_frames": 1,
                       "style": {"font": FONT, "font_size": 26, "fill": "#F1EBDD"}})
    return {"schema": "chronon.render-plan.v3", "version": 3,
            "job_id": "documentary_snapshot_fit_gallery_v1",
            "canvas": {"width": WIDTH, "height": HEIGHT, "fps_num": FPS,
                       "fps_den": 1, "duration_frames": 1},
            "layers": layers,
            "output": {"path": "documentary_snapshot_fit_gallery_v1.mp4",
                       "format": "mp4", "codec": "h264"}}


def _track(prop: str, values: list[float]) -> dict:
    return {"property": prop, "easing": "linear", "keyframes": [
        {"frame": frame, "value": round(value, 6)} for frame, value in enumerate(values)]}


def build_plan(pose_rows: list[list[float]], recipe: str = "doc_title_snap_down") -> dict:
    channels = list(zip(*[row[1:] for row in pose_rows]))
    x, y, z, rx, ry, rz, fov, focus_distances, focus_planes, aperture_values = [list(channel) for channel in channels]
    x = [value - WIDTH / 2 for value in x]
    # Match the established TitleCamera bridge: camera positions are centered
    # around the canvas while 3D layer positions remain in canvas coordinates.
    # ChrononMotion's forward -Z axis is inverted for RenderPlan's +Z view.
    y = [value - HEIGHT / 2 for value in y]
    z = [-v for v in z]
    # RenderPlan 3D images use center-relative XY; the text layer uses canvas
    # coordinates. Translate the snapshot anchor from the template canvas.
    image_x, image_y, image_z = 0, 960 - HEIGHT / 2, 80
    focus_recipe = recipe == "doc_title_focus_drop"
    layers = [
        {"id": "documentary-ground", "type": "color", "color": [0.018, 0.020, 0.021, 1.0],
         "size": [WIDTH, HEIGHT], "screen_space": True, "start_frame": 0,
         "duration_frames": FRAMES},
        {"id": "documentary-title", "type": "text", "text": "THE STORY OF ROME",
         "size": [1720, 230], "position": [WIDTH / 2, 300, 0], "enable_3d": True,
         "start_frame": 0, "duration_frames": FRAMES,
         "style": {"font": FONT, "font_size": 138, "min_font_size": 80,
                   "max_font_size": 138, "fit_mode": "shrink_only", "fill": "#F1EBDD"}},
        {"id": "documentary-snapshot", "type": "image", "asset": PHOTO,
         "size": [1240, 700], "position": [image_x, image_y, image_z],
         "fit": "cover", "enable_3d": True, "start_frame": 0, "duration_frames": FRAMES},
    ]
    if not focus_recipe:
        layers[2]["animation"] = {"tracks": [{"property": "opacity", "easing": "out_cubic",
            "keyframes": [{"frame": 0, "value": 0.0}, {"frame": 45, "value": 0.0},
                          {"frame": 53, "value": 1.0}, {"frame": 120, "value": 1.0}]}]}
    if recipe == "doc_title_push_through_snapshot":
        layers.append({
            "id": "documentary-red-portal", "type": "shape",
            # Shape payload positions use canvas-space coordinates; unlike the
            # image projection contract, they include the canvas center offset.
            "size": [1240, 700], "position": [image_x + WIDTH / 2,
                                             image_y + HEIGHT / 2, image_z - 2],
            "enable_3d": True, "start_frame": 0, "duration_frames": FRAMES,
            "shape": {"type": "rect", "fill": [0.788, 0.165, 0.196, 1.0]},
            "animation": {"tracks": [{"property": "opacity", "easing": "linear",
                "keyframes": [{"frame": 0, "value": 0.0}, {"frame": 45, "value": 0.0},
                              {"frame": 53, "value": 1.0}, {"frame": 120, "value": 0.0}]}]}})
    properties = ["camera_position_x", "camera_position_y", "camera_position_z",
                  "camera_rotation_x", "camera_rotation_y", "camera_rotation_z", "camera_fov_deg"]
    camera = {"type": "perspective", "position": [x[0], y[0], z[0]],
              "rotation_deg": [rx[0], ry[0], rz[0]], "fov_deg": fov[0],
              "near": 1.0, "far": 10000.0, "zoom": 1.0}
    camera_tracks = [_track(prop, values) for prop, values in
                     zip(properties, [x, y, z, rx, ry, rz, fov])]
    if focus_recipe:
        # The existing RenderPlan DOF compositor consumes its legacy focus
        # plane in render-space world Z. Derive that plane from the native
        # shot's sampled target, while retaining the rig's physical distance
        # in the dumper output for contract/debug inspection.
        camera["dof"] = {"enabled": True, "focus_distance": focus_planes[0],
                         "aperture": aperture_values[0], "max_blur": 24.0}
        camera_tracks.append(_track("camera_focus_distance", focus_planes))
        camera_tracks.append(_track("camera_aperture", aperture_values))
    plan = {"schema": "chronon.render-plan.v3", "version": 3,
            "job_id": recipe + "_canary_v1",
            "canvas": {"width": WIDTH, "height": HEIGHT, "fps_num": FPS,
                       "fps_den": 1, "duration_frames": FRAMES},
            "camera": camera,
            "camera_animation": {"tracks": camera_tracks},
            "layers": layers,
            "output": {"path": recipe + "_canary_v1.mp4",
                       "format": "mp4", "codec": "h264"}}
    if focus_recipe:
        plan["temporal_motion_blur"] = {"shutter_angle": 180.0, "samples": 4}
    return plan


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--render", action="store_true", help="render with the local Chronon3D CLI")
    parser.add_argument("--out", type=Path, default=ROOT / "out/documentary_snapshot_v1")
    parser.add_argument("--cli", type=Path, default=CLI)
    parser.add_argument("--recipe", choices=["doc_title_snap_down", "doc_title_push_through_snapshot",
                                              "doc_title_focus_drop"],
                        default="doc_title_snap_down")
    parser.add_argument("--style-gallery", action="store_true",
                        help="render one contact sheet with all seven SnapshotStyle looks")
    parser.add_argument("--fit-gallery", action="store_true",
                        help="render native Fit, Fill, and explicit Crop cards")
    parser.add_argument("--adapter-lowered", action="store_true",
                        help="render the real DocumentarySnapshotPack through RenderPlanContentHost")
    parser.add_argument("--snapshot-fit", choices=("fit", "fill", "crop"), default="fit",
                        help="image fit mode for the connected adapter canary")
    parser.add_argument("--snapshot-style",
                        choices=("clean", "archive", "polaroid", "filmstrip", "evidence",
                                 "newspaper", "bw-documentary"), default="archive",
                        help="SnapshotStyle used by the connected adapter canary")
    parser.add_argument("--documentary-recipe",
                        choices=("snap-down", "pullback-reveal", "push-through-snapshot",
                                 "whip-to-photo", "focus-drop", "reveal-90", "corner-turn",
                                 "foreground-photo-pass", "photo-stack", "filmstrip-handoff",
                                 "split-depth", "archive-crane-reveal", "torture"), default="snap-down",
                        help="DocumentarySnapshotPack recipe used by the connected canary")
    parser.add_argument("--render-sequence", action="store_true",
                        help="render the adapter-lowered torture plan as a full video")
    parser.add_argument("--backend", choices=("software", "vulkan"), default="software",
                        help="Chronon3D backend for a full sequence render")
    parser.add_argument("--frames", type=int, nargs="+", default=(0, 45, 53, 120),
                        help="frames to decode from the connected adapter canary")
    args = parser.parse_args()
    args.out = args.out.resolve()
    args.cli = args.cli.resolve()
    if args.style_gallery or args.fit_gallery:
        gallery_name = "documentary_snapshot_fit_gallery_v1" if args.fit_gallery else "documentary_snapshot_style_gallery_v1"
        plan = build_fit_gallery_plan() if args.fit_gallery else build_style_gallery_plan()
        args.out.mkdir(parents=True, exist_ok=True)
        if any(frame < 0 or frame > 120 for frame in args.frames):
            raise SystemExit("connected adapter frames must be between 0 and 120")
        plan_path = args.out / f"{gallery_name}.plan.json"
        plan_path.write_text(json.dumps(plan, indent=2) + "\n", encoding="utf-8")
        if not args.render:
            print(f"Wrote {plan_path}")
            return 0
        if not args.cli.is_file():
            raise SystemExit(f"Chronon3D CLI not found: {args.cli}")
        subprocess.run([str(args.cli), "validate", "--plan", str(plan_path),
                        "--assets-root", str(WORKSPACE), "--profile", "preview"],
                       check=True, cwd=WORKSPACE)
        video = args.out / f"{gallery_name}.mp4"
        subprocess.run([str(args.cli), "render", "--backend", "software", "--plan", str(plan_path),
                        "--assets-root", str(WORKSPACE), "-o", str(video), "--ffmpeg-mode", "pipe",
                        "--codec", "h264", "--encode-preset", "fast"],
                       check=True, cwd=WORKSPACE)
        image = args.out / f"{gallery_name}.png"
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(video), "-frames:v", "1", str(image)],
                       check=True, cwd=WORKSPACE)
        print(f"Rendered {video} and decoded pixel-truth frame {image}")
        return 0
    if args.adapter_lowered:
        if not ADAPTER_DUMPER.is_file():
            raise SystemExit(f"missing {ADAPTER_DUMPER}; configure with CHRONON3D_INCLUDE_DIR and build chronontemplate_dump_documentary_snapshot_plan")
        if not args.cli.is_file():
            raise SystemExit(f"Chronon3D CLI not found: {args.cli}")
        args.out.mkdir(parents=True, exist_ok=True)
        style_suffix = "" if args.snapshot_style == "archive" else f"_{args.snapshot_style}"
        recipe_suffix = "" if args.documentary_recipe == "snap-down" else f"_{args.documentary_recipe}"
        plan_path = args.out / f"documentary_snapshot_adapter_canary{style_suffix}{recipe_suffix}_v1.plan.json"
        subprocess.run([str(ADAPTER_DUMPER), str(plan_path), args.snapshot_fit,
                        args.snapshot_style, args.documentary_recipe],
                       check=True, cwd=WORKSPACE)
        plan = json.loads(plan_path.read_text(encoding="utf-8"))
        final_frame = int(plan["canvas"]["duration_frames"]) - 1
        if any(frame < 0 or frame > final_frame for frame in args.frames):
            raise SystemExit(f"connected adapter frames must be between 0 and {final_frame}")
        _assert_light_leak_follows_camera_speed(plan_path)
        subprocess.run([str(args.cli), "validate", "--plan", str(plan_path),
                        "--assets-root", str(WORKSPACE), "--profile", "preview"],
                       check=True, cwd=WORKSPACE)
        if not args.render and not args.render_sequence:
            print(f"Validated connected adapter plan: {plan_path}")
            return 0
        if args.render_sequence:
            if args.documentary_recipe != "torture":
                raise SystemExit("--render-sequence requires --documentary-recipe torture")
            video = args.out / "documentary_title_snapshot_torture_v1.mp4"
            subprocess.run([str(args.cli), "render", "--backend", args.backend, "--plan", str(plan_path),
                            "--assets-root", str(WORKSPACE), "-o", str(video), "--ffmpeg-mode", "pipe",
                            "--codec", "h264", "--encode-preset", "fast"], check=True, cwd=WORKSPACE)
            probe = subprocess.check_output(["ffprobe", "-v", "error", "-count_frames", "-select_streams",
                                             "v:0", "-show_entries", "stream=width,height,nb_read_frames",
                                             "-of", "json", str(video)], text=True)
            stream = json.loads(probe)["streams"][0]
            if (stream.get("width"), stream.get("height"), int(stream.get("nb_read_frames", 0))) != (WIDTH, HEIGHT, final_frame + 1):
                raise SystemExit(f"torture canary metadata mismatch: {stream}")
            print(f"Rendered 20-second twelve-recipe sequence: {video}")
            return 0
        for frame in args.frames:
            raw = args.out / f"documentary_snapshot_adapter{style_suffix}{recipe_suffix}_frame_{frame:03d}.rgba"
            subprocess.run([str(args.cli), "render", "--backend", args.backend, "--plan", str(plan_path),
                            "--assets-root", str(WORKSPACE), "--video-sink", "raw", "--pipe-pixfmt", "rgba",
                            "--start-frame", str(frame), "--end-frame", str(frame), "-o", str(raw)],
                           check=True, cwd=WORKSPACE)
            image = args.out / f"documentary_snapshot_adapter{style_suffix}{recipe_suffix}_frame_{frame:03d}.png"
            subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pixel_format", "rgba",
                            "-video_size", f"{WIDTH}x{HEIGHT}", "-i", str(raw), "-frames:v", "1", str(image)],
                           check=True, cwd=WORKSPACE)
            multi_snapshot_recipes = {"photo-stack", "filmstrip-handoff", "archive-crane-reveal"}
            if (frame == final_frame and args.snapshot_fit == "fit" and
                    args.documentary_recipe not in multi_snapshot_recipes | {"torture"}):
                _assert_adapter_fit_bounds(raw)
            if frame == 53 and args.documentary_recipe == "push-through-snapshot":
                _assert_red_portal_coverage(raw)
        print(f"Rendered {args.snapshot_style} raw pixel-truth frames {', '.join(map(str, args.frames))} in {args.out}")
        return 0
    if not DUMPER.is_file():
        raise SystemExit(f"missing {DUMPER}; build chronontemplate_dump_documentary_snapshot_pose")
    rows = [[float(value) for value in line.split()]
            for line in subprocess.check_output([str(DUMPER), args.recipe], text=True).splitlines()]
    if len(rows) != FRAMES or any(len(row) != 11 for row in rows):
        raise SystemExit(f"native pose dumper returned {len(rows)} rows with unexpected columns; expected {FRAMES} rows of 11 values")
    plan = build_plan(rows, args.recipe)
    args.out.mkdir(parents=True, exist_ok=True)
    plan_path = args.out / f"{args.recipe}_canary_v1.plan.json"
    plan_path.write_text(json.dumps(plan, indent=2) + "\n", encoding="utf-8")
    if not args.render:
        print(f"Wrote {plan_path}")
        return 0
    if not args.cli.is_file():
        raise SystemExit(f"Chronon3D CLI not found: {args.cli}")
    subprocess.run([str(args.cli), "validate", "--plan", str(plan_path),
                    "--assets-root", str(WORKSPACE), "--profile", "preview"],
                   check=True, cwd=WORKSPACE)
    video = args.out / f"{args.recipe}_canary_v1.mp4"
    subprocess.run([str(args.cli), "render", "--backend", "software", "--plan", str(plan_path),
                    "--assets-root", str(WORKSPACE), "-o", str(video), "--ffmpeg-mode", "pipe",
                    "--codec", "h264", "--encode-preset", "fast"], check=True, cwd=WORKSPACE)
    probe = subprocess.check_output(["ffprobe", "-v", "error", "-count_frames", "-select_streams",
                                     "v:0", "-show_entries", "stream=width,height,nb_read_frames",
                                     "-of", "json", str(video)], text=True)
    stream = json.loads(probe)["streams"][0]
    if (stream.get("width"), stream.get("height"), int(stream.get("nb_read_frames", 0))) != (WIDTH, HEIGHT, FRAMES):
        raise SystemExit(f"canary render metadata mismatch: {stream}")
    print(f"Rendered {video}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
