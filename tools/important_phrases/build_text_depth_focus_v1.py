#!/usr/bin/env python3
"""Build the text_depth_focus_v1 editorial word-focus render-plan family."""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
WORKSPACE = ROOT.parent
CHRONON = WORKSPACE / "Chronon3d"
DEFAULT_OUT = ROOT / "out/text_depth_focus_v1"
CLI = CHRONON / "build/chronon/linux-video-fast-dev/apps/chronon3d_cli/chronon3d_cli"
WIDTH, HEIGHT, FPS, FRAMES = 1920, 1080, 30, 150
FONT = "Chronon3d/assets/fonts/Inter-Bold.ttf"
PHRASE = "MAKE BETTER VIDEOS FASTER"
WORDS = PHRASE.split()
PRESET_IDS = (
    "text_focus_word_static",
    "text_focus_word_travel",
    "text_focus_near_to_far",
    "text_focus_far_to_near",
    "text_focus_center_out",
    "text_focus_edges_in",
    "text_focus_rack_duo",
    "text_focus_depth_cascade",
)
FOCUSED = "#F5F3F7"
SOFT = "#C9C4D0"
ACCENT = "#FFD36E"


def _track(prop: str, values: list[tuple[int, Any]], easing: str = "in_out_cubic") -> dict[str, Any]:
    return {"property": prop, "easing": easing,
            "keyframes": [{"frame": frame, "value": value} for frame, value in values]}


def _span_offsets(text: str) -> list[tuple[str, int, int]]:
    result = []
    cursor = 0
    for index, word in enumerate(text.split()):
        start = text.find(word, cursor)
        end = start + len(word)
        result.append((word, len(text[:start].encode("utf-8")), len(text[:end].encode("utf-8"))))
        cursor = end
    return result


def _word_animator(index: int, focus_keys: list[tuple[int, float]], *,
                   entry: bool = False, static_blur: float | None = None) -> dict[str, Any]:
    blur_keys = []
    scale_keys = []
    opacity_keys = []
    for frame, focus in focus_keys:
        distance = abs(index - focus)
        blur_keys.append({"frame": frame, "value": round(min(7.0, distance * 2.6), 3)})
        scale_keys.append({"frame": frame, "value": round(1.0 - min(distance, 2.0) * 0.012, 4)})
        opacity_keys.append({"frame": frame, "value": round(1.0 - min(distance, 3.0) * 0.055, 4)})
    if static_blur is not None:
        blur_keys = [{"frame": 0, "value": static_blur}, {"frame": FRAMES - 1, "value": static_blur}]
    if static_blur is not None and entry:
        blur_keys = [{"frame": 0, "value": max(5.0, static_blur)},
                     {"frame": 16, "value": static_blur},
                     {"frame": FRAMES - 1, "value": static_blur}]
        if index == 0:
            blur_keys = [{"frame": 0, "value": max(5.0, static_blur)},
                         {"frame": 16, "value": static_blur},
                         {"frame": FRAMES - 1, "value": static_blur}]
    elif static_blur is not None:
        blur_keys = [{"frame": 0, "value": static_blur},
                     {"frame": FRAMES - 1, "value": static_blur}]
    elif entry:
        settled_blur = blur_keys[0]["value"]
        blur_keys = [{"frame": 0, "value": max(5.0, settled_blur)},
                     {"frame": 16, "value": settled_blur},
                     {"frame": FRAMES - 1, "value": settled_blur}]
        scale_keys = [{"frame": 0, "value": max(0.94, scale_keys[0]["value"] - 0.035)},
                      {"frame": 16, "value": scale_keys[0]["value"]}, *scale_keys[1:]]
        opacity_keys = [{"frame": 0, "value": min(0.72, opacity_keys[0]["value"])},
                        {"frame": 16, "value": opacity_keys[0]["value"]}, *opacity_keys[1:]]
    return {
        "id": f"word-focus-{index}",
        "selectors": [{"id": f"word-selector-{index}", "unit": "glyph", "order": "forward",
                       "shape": "square", "combine": "replace", "exclude_spaces": True,
                       "semantic_id": f"word-{index}"}],
        "properties": [
            {"property": "blur", "easing": "linear", "keyframes": blur_keys},
            {"property": "scale", "easing": "linear", "keyframes": [
                {"frame": key["frame"], "value": [key["value"]]} for key in scale_keys]},
            {"property": "opacity", "easing": "linear", "keyframes": opacity_keys},
            {"property": "fill_color", "easing": "linear", "keyframes": [
                {"frame": 0, "value": _rgba(ACCENT if index == 2 else SOFT)},
                {"frame": FRAMES - 1, "value": _rgba(ACCENT if index == 2 else SOFT)}]},
        ],
    }


def _rgba(hex_color: str) -> list[float]:
    value = hex_color.lstrip("#")
    return [int(value[i:i + 2], 16) / 255.0 for i in (0, 2, 4)] + [1.0]


def _bake_focus(keys: list[tuple[int, float]]) -> list[tuple[int, float]]:
    """Bake eased focus samples so random-access evaluation has no boundary pops."""
    authored = sorted(keys)
    values: list[tuple[int, float]] = []
    for frame in range(FRAMES):
        if frame <= authored[0][0]:
            values.append((frame, authored[0][1]))
            continue
        if frame >= authored[-1][0]:
            values.append((frame, authored[-1][1]))
            continue
        segment = next(i for i in range(len(authored) - 1) if frame <= authored[i + 1][0])
        f0, v0 = authored[segment]
        f1, v1 = authored[segment + 1]
        t = (frame - f0) / max(1, f1 - f0)
        eased = t * t * (3.0 - 2.0 * t)
        values.append((frame, v0 + (v1 - v0) * eased))
    return values


def _focus_samples(order: list[int]) -> list[tuple[int, float]]:
    """Bake a smooth focus flight to linear animator keys (the renderer's contract)."""
    stop_frames = [round(index * (FRAMES - 1) / (len(order) - 1)) for index in range(len(order))]
    samples: list[tuple[int, float]] = []
    for frame in range(FRAMES):
        segment = min(len(order) - 2, next((i for i in range(len(order) - 1)
                         if frame <= stop_frames[i + 1]), len(order) - 2))
        start, end = stop_frames[segment], stop_frames[segment + 1]
        t = min(1.0, max(0.0, (frame - start) / max(1, end - start)))
        eased = t * t * (3.0 - 2.0 * t)
        value = order[segment] + (order[segment + 1] - order[segment]) * eased
        samples.append((frame, float(value)))
    return samples


def _ramp(start: int, end: int, order: list[int], *, held: int = 9) -> list[tuple[int, float]]:
    points: list[tuple[int, float]] = []
    usable = max(1, end - start - held * len(order))
    step = usable / max(1, len(order) - 1)
    for rank, word_index in enumerate(order):
        frame = start + round(rank * step)
        points.append((frame, float(word_index)))
    if points[0][0] != 0:
        points.insert(0, (0, points[0][1]))
    if points[-1][0] != FRAMES - 1:
        points.append((FRAMES - 1, points[-1][1]))
    return points


def _camera(focus_z: float, *, push: bool = False, enable_dof: bool = False) -> tuple[dict[str, Any], dict[str, Any] | None]:
    # The RenderPlan DOF bridge maps focus_distance to the legacy world-Z
    # focus plane. Keep authored depth positive (also required by the decoder).
    camera = {"type": "perspective", "position": [0, 0, -1000], "rotation_deg": [0, 0, 0],
              "fov_deg": 45, "near": 1, "far": 10000, "zoom": 1,
              "dof": {"enabled": enable_dof, "focus_distance": focus_z,
                      "aperture": 0.035, "max_blur": 12}}
    animation = None
    if push:
        animation = {"tracks": [_track("camera_position_z", [(0, -1000), (75, -970),
                                                                 (FRAMES - 1, -940)])]}
    return camera, animation


def build_plan(preset_id: str) -> dict[str, Any]:
    if preset_id not in PRESET_IDS:
        raise ValueError(f"unknown text depth-focus preset: {preset_id}")
    static_targets = {
        "text_focus_word_static": 2,
        "text_focus_rack_duo": 2,
    }
    sequences = {
        "text_focus_word_travel": [0, 1, 2, 3],
        "text_focus_near_to_far": [0, 1, 2, 3],
        "text_focus_far_to_near": [3, 2, 1, 0],
        "text_focus_center_out": [1, 2, 0, 3],
        "text_focus_edges_in": [0, 3, 1, 2],
        "text_focus_depth_cascade": [0, 1, 2, 3],
    }
    layers: list[dict[str, Any]] = [{"id": "background", "type": "color",
        "color": [0.018, 0.022, 0.035, 1], "size": [WIDTH, HEIGHT],
        "screen_space": True, "start_frame": 0, "duration_frames": FRAMES}]
    layout = [(-625, "MAKE"), (-205, "BETTER"), (260, "VIDEOS"), (690, "FASTER")]
    is_depth = preset_id in {"text_focus_near_to_far", "text_focus_far_to_near", "text_focus_depth_cascade"}
    if preset_id in static_targets:
        target = static_targets[preset_id]
        timeline = [(0, float(target)), (FRAMES - 1, float(target))]
    else:
        order = sequences[preset_id]
        timeline = _ramp(0, FRAMES - 1, order)
    z_positions = [500.0, 560.0, 620.0, 680.0] if is_depth else [0.0] * len(WORDS)
    camera, camera_animation = _camera(620.0, push=True,
        enable_dof=preset_id == "text_focus_depth_cascade") if is_depth else (None, None)


    for index, ((x, word), span, z) in enumerate(zip(layout, _span_offsets(PHRASE), z_positions)):
        text = word
        text_span = {"start": 0, "end": len(word.encode("utf-8")), "semantic_id": f"word-{index}",
                     "style": {"color": FOCUSED if index == 2 else SOFT}}
        animated_keys = timeline
        if preset_id in sequences and preset_id != "text_focus_word_travel":
            animated_keys = _focus_samples(sequences[preset_id])
        if preset_id == "text_focus_center_out":
            # The two inner words hold center focus before attention moves to the edges.
            animated_keys = [(0, 1.5), (40, 1.5), (75, 0.0), (149, 3.0)]
        elif preset_id == "text_focus_edges_in":
            # Begin on the outside words and glide inward; midpoint is intentionally blended.
            animated_keys = [(0, 0.0), (38, 3.0), (76, 1.0), (112, 2.0), (149, 2.5)]
        elif preset_id == "text_focus_rack_duo":
            animated_keys = [(0, 0.0), (54, 2.0), (96, 2.0), (149, 3.0)]
        elif preset_id == "text_focus_depth_cascade":
            animated_keys = [(0, 0.0), (36, 1.0), (76, 2.0), (112, 3.0), (149, 3.0)]
        elif preset_id == "text_focus_word_travel":
            animated_keys = [(0, 0.0), (42, 1.0), (78, 2.0), (114, 3.0), (149, 3.0)]
        elif preset_id in {"text_focus_near_to_far", "text_focus_far_to_near"}:
            animated_keys = _focus_samples(sequences[preset_id])
        dof_focus_word = preset_id == "text_focus_depth_cascade"
        if dof_focus_word:
            animated_keys = [(0, 2.0), (FRAMES - 1, 2.0)]

        if preset_id not in static_targets and not dof_focus_word:
            animated_keys = _bake_focus(animated_keys)
        selected_static = preset_id in static_targets
        if dof_focus_word:
            static_blur = 0.0
        elif selected_static:
            static_blur = 0.0 if index == static_targets[preset_id] else min(7.0, abs(index - static_targets[preset_id]) * 2.6)
        else:
            static_blur = None
        animator = _word_animator(index, animated_keys, static_blur=static_blur,
                                  entry=preset_id == "text_focus_word_static")
        layer_position = [WIDTH / 2 + x, HEIGHT / 2, z] if is_depth else [WIDTH / 2 + x, HEIGHT / 2]
        layer: dict[str, Any] = {
            "id": f"word-{index}", "type": "text", "text": text,
            "size": [390 if len(word) > 5 else 310, 180], "position": layer_position,
            "enable_3d": is_depth, "spans": [text_span],
            "style": {"font": FONT, "font_size": 112, "min_font_size": 86,
                      "max_font_size": 112, "fit_mode": "shrink_only", "fill": FOCUSED},
            "start_frame": 0, "duration_frames": FRAMES,
            "text_animators": [animator],
        }
        if preset_id == "text_focus_word_static":
            layer["animation"] = {"tracks": [_track("scale", [(0, 0.98), (16, 1), (FRAMES - 1, 1)])]}
        if preset_id == "text_focus_depth_cascade":
            layer["animation"] = {"tracks": [_track("position_z", [(0, 20), (24, 0),
                                                                       (FRAMES - 1, 0)])]}
        layers.append(layer)
    layers.append({"id": "editorial-kicker", "type": "text", "text": "CHRONON  /  DEPTH STUDY",
        "size": [600, 44], "position": [WIDTH / 2, 145], "screen_space": True,
        "style": {"font": "Chronon3d/assets/fonts/Inter-Regular.ttf", "font_size": 20,
                  "min_font_size": 18, "max_font_size": 20, "fit_mode": "shrink_only",
                  "fill": "#8D8A96"}, "start_frame": 0, "duration_frames": FRAMES})
    plan: dict[str, Any] = {
        "schema": "chronon.render-plan.v3", "version": 3, "job_id": preset_id,
        "canvas": {"width": WIDTH, "height": HEIGHT, "fps_num": FPS, "fps_den": 1,
                   "duration_frames": FRAMES},
        "layers": layers,
        "output": {"path": f"{preset_id}.mp4", "format": "mp4", "codec": "h264"},
    }
    if is_depth:
        plan["camera"] = camera
        if camera_animation:
            plan["camera_animation"] = camera_animation
    validate_plan(plan)
    return plan


def _sample_track(keys: list[dict[str, Any]], frame: int) -> float:
    if frame <= keys[0]["frame"]:
        return float(keys[0]["value"])
    for left, right in zip(keys, keys[1:]):
        if frame <= right["frame"]:
            t = (frame - left["frame"]) / (right["frame"] - left["frame"])
            return float(left["value"]) + (float(right["value"]) - float(left["value"])) * t
    return float(keys[-1]["value"])


def validate_plan(plan: dict[str, Any]) -> None:
    if plan.get("schema") != "chronon.render-plan.v3" or plan.get("version") != 3:
        raise ValueError("text depth-focus plans must use RenderPlan V3")
    plan_id = plan.get("job_id")
    if plan_id not in PRESET_IDS:
        raise ValueError(f"unknown text depth-focus plan id: {plan_id}")
    canvas = plan.get("canvas", {})
    if canvas != {"width": WIDTH, "height": HEIGHT, "fps_num": FPS,
                  "fps_den": 1, "duration_frames": FRAMES}:
        raise ValueError(f"{plan_id}: expected a 5s 1920x1080/30 timeline")
    layers = plan.get("layers", [])
    if len(layers) != len(WORDS) + 2 or len({layer.get("id") for layer in layers}) != len(layers):
        raise ValueError(f"{plan_id}: expected four distinct words, background, and kicker")
    word_layers = layers[1:1 + len(WORDS)]
    spans = []
    for index, (layer, expected_word) in enumerate(zip(word_layers, WORDS)):
        if layer.get("text") != expected_word or layer.get("type") != "text":
            raise ValueError(f"{plan_id}: word layer order changed at {index}")
        if not layer.get("enable_3d", False) and len(layer.get("position", [])) == 3:
            raise ValueError(f"{plan_id}/{layer['id']}: 3D position requires enable_3d")
        if len(layer.get("spans", [])) != 1 or layer["spans"][0]["semantic_id"] != f"word-{index}":
            raise ValueError(f"{plan_id}/{layer['id']}: each word must expose stable semantic identity")
        spans.append(layer["spans"][0])
        animators = layer.get("text_animators", [])
        if len(animators) != 1:
            raise ValueError(f"{plan_id}/{layer['id']}: expected one renderer-native word animator")
        properties = {item["property"] for item in animators[0]["properties"]}
        if not {"blur", "scale", "opacity", "fill_color"}.issubset(properties):
            raise ValueError(f"{plan_id}/{layer['id']}: word animator is missing a supported focus property")
        if "position_z" in properties:
            raise ValueError(f"{plan_id}/{layer['id']}: Z belongs to the 3D layer transform, not a text animator")
        for prop in animators[0]["properties"]:
            frames = [key["frame"] for key in prop["keyframes"]]
            if frames != sorted(set(frames)) or frames[0] < 0 or frames[-1] >= FRAMES:
                raise ValueError(f"{plan_id}/{layer['id']}: invalid {prop['property']} keyframe timeline")
            if prop["property"] in {"blur", "opacity"}:
                values = [key["value"] for key in prop["keyframes"]]
                if any(not isinstance(value, (int, float)) or value < 0 or
                       (prop["property"] == "opacity" and value > 1) for value in values):
                    raise ValueError(f"{plan_id}/{layer['id']}: invalid {prop['property']} keyframe value")
        if layer.get("animation"):
            tracks = layer["animation"]["tracks"]
            if any(track["property"] == "position_z" for track in tracks) and not layer.get("enable_3d"):
                raise ValueError(f"{plan_id}/{layer['id']}: Z animation requires enable_3d")
    expected_ranges = _span_offsets(PHRASE)
    full_text = " ".join(layer["text"] for layer in word_layers)
    if full_text != PHRASE or len(expected_ranges) != len(spans):
        raise ValueError(f"{plan_id}: phrase layout is not stable")
    if plan_id == "text_focus_word_static":
        for index, layer in enumerate(word_layers):
            blur = next(item for item in layer["text_animators"][0]["properties"] if item["property"] == "blur")
            expected = 0 if index == 2 else min(7, abs(index - 2) * 2.6)
            if abs(float(blur["keyframes"][-1]["value"]) - expected) > 1e-5:
                raise ValueError("static focus must settle VIDEOS sharp and blur other words by distance")
    if plan_id in {"text_focus_near_to_far", "text_focus_far_to_near", "text_focus_depth_cascade"}:
        z = [float(layer["position"][2]) for layer in word_layers]
        if z != [500, 560, 620, 680]:
            raise ValueError(f"{plan_id}: depth order changed")
        if not plan.get("camera") or plan["camera"]["position"][2] != -1000:
            raise ValueError(f"{plan_id}: depth presets require the authored perspective camera")
    if plan_id in {"text_focus_near_to_far", "text_focus_far_to_near"}:
        if plan["camera"]["dof"]["enabled"]:
            raise ValueError("moving editorial focus must not be masked by static camera DOF")
        blur = [next(prop for prop in layer["text_animators"][0]["properties"]
                     if prop["property"] == "blur")["keyframes"] for layer in word_layers]
        if not all(len(track) == FRAMES for track in blur):
            raise ValueError("moving editorial focus requires continuous baked per-word blur")
    if plan_id == "text_focus_depth_cascade":
        dof = plan.get("camera", {}).get("dof", {})
        if not dof.get("enabled") or dof.get("focus_distance") != 620:
            raise ValueError("depth cascade must focus the true camera DOF plane on VIDEOS")
        blur = [next(prop for prop in layer["text_animators"][0]["properties"]
                     if prop["property"] == "blur")["keyframes"] for layer in word_layers]
        if any(any(key["value"] != 0 for key in track) for track in blur):
            raise ValueError("depth cascade must let camera DOF, not editorial blur, resolve focus")
        z_anim = [next(track for track in layer["animation"]["tracks"] if track["property"] == "position_z")
                  for layer in word_layers]
        if any(track["keyframes"][0]["value"] != 20
               for track, layer in zip(z_anim, word_layers)):
            raise ValueError("depth cascade must settle each word onto its physical Z plane")
    if "camera_animation" in plan:
        props = {track["property"] for track in plan["camera_animation"]["tracks"]}
        if not props.issubset({"camera_position_x", "camera_position_y", "camera_position_z",
                               "camera_rotation_x", "camera_rotation_y", "camera_rotation_z",
                               "camera_fov_deg", "camera_zoom"}):
            raise ValueError("camera uses a property unsupported by the current render-plan contract")


def all_plans() -> list[dict[str, Any]]:
    return [build_plan(preset) for preset in PRESET_IDS]


def write_plans(out_dir: Path) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    paths = []
    for plan in all_plans():
        path = out_dir / f"{plan['job_id']}.plan.json"
        path.write_text(json.dumps(plan, indent=2) + "\n", encoding="utf-8")
        paths.append(path)
    manifest = {"schema": "chronontemplate.text-depth-focus.v1", "family": "text_depth_focus_v1",
        "renderer_contract": "RenderPlan V3; semantic word TextAnimator blur/scale/opacity, 3D layer position_z, camera DOF",
        "canvas": {"width": WIDTH, "height": HEIGHT, "fps": FPS, "frames": FRAMES},
        "phrase": PHRASE, "presets": list(PRESET_IDS), "plans": [path.name for path in paths]}
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return paths


def verify_video(path: Path) -> None:
    result = subprocess.run(["ffprobe", "-v", "error", "-count_frames", "-select_streams", "v:0",
        "-show_entries", "stream=width,height,avg_frame_rate,nb_read_frames", "-of", "json", str(path)],
        capture_output=True, text=True, check=True)
    stream = json.loads(result.stdout)["streams"][0]
    actual = (int(stream["width"]), int(stream["height"]), int(stream["nb_read_frames"]), stream["avg_frame_rate"])
    if actual != (WIDTH, HEIGHT, FRAMES, "30/1") or path.stat().st_size < 2000:
        raise RuntimeError(f"{path.name}: invalid encoded deliverable {actual}")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--cli", type=Path, default=CLI)
    parser.add_argument("--validate-only", action="store_true")
    parser.add_argument("--render", action="store_true")
    parser.add_argument("--render-all", action="store_true")
    parser.add_argument("--preset", action="append", choices=PRESET_IDS,
                        help="select one or more presets to render; validation still covers the complete family")
    parser.add_argument("--render-backend", choices=("software", "vulkan"), default="software")
    parser.add_argument("--mirror-output-dir", type=Path)
    args = parser.parse_args(argv)
    paths = write_plans(args.out.resolve())
    if args.validate_only or args.render or args.render_all:
        if not args.cli.is_file():
            raise SystemExit(f"Chronon3D CLI not found: {args.cli}")
        for path in paths:
            subprocess.run([str(args.cli), "validate", "--plan", str(path), "--assets-root", str(WORKSPACE),
                            "--profile", "preview"], check=True, stdout=subprocess.DEVNULL)
            print(f"Validated {path.stem}", flush=True)
    if args.validate_only:
        return 0
    if args.render and args.render_all:
        parser.error("choose --render or --render-all")
    if args.preset and (args.render_all or not args.render):
        parser.error("--preset requires --render and cannot be combined with --render-all")
    selected_ids = set(args.preset or [])
    selected = ([path for path in paths if path.stem.removesuffix(".plan") in selected_ids]
                if args.preset else paths if args.render_all else paths[:1] if args.render else [])
    mirror = args.mirror_output_dir.resolve() if args.mirror_output_dir else None
    if mirror:
        mirror.mkdir(parents=True, exist_ok=True)
    for path in selected:
        plan_id = path.name.removesuffix(".plan.json")
        video = path.with_suffix("").with_suffix(".mp4")
        subprocess.run([str(args.cli), "render", "--backend", args.render_backend,
            "--plan", str(path), "--assets-root", str(WORKSPACE), "-o", str(video),
            "--ffmpeg-mode", "pipe", "--codec", "h264", "--encode-preset", "fast"], check=True)
        verify_video(video)
        if mirror:
            for item in [path, video, Path(f"{video}.timing.json")]:
                if item.is_file():
                    shutil.copy2(item, mirror / item.name)
        print(f"Rendered and verified {plan_id}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
