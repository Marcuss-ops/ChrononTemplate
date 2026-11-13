#!/usr/bin/env python3
"""AE-parity text animator demos: Character Value, Character Alignment,
Anchor Point Grouping.

The three clips are authored as V3 render plans and rendered with the Vulkan
backend in `require_gpu_native` mode, so a plan that falls back to the
software text raster fails the run instead of silently degrading.

Usage:
    python3 build_ae_parity_text_demos.py --generate
    python3 build_ae_parity_text_demos.py --render
    python3 build_ae_parity_text_demos.py --verify
"""
from __future__ import annotations

import argparse
import json
import subprocess
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
ROOT = REPO / "RenderingGen/UploadDrive/ae_text_parity_20261109"
ASSETS = REPO / "Chronon3d"
CLI = REPO / "Chronon3d/build/chronon/linux-video-release/apps/chronon3d_cli/chronon3d_cli"

FPS = 30
FRAMES = 180
FONT = "assets/fonts/SF-Pro-Display-Semibold.otf"


def kf(frame: int, value) -> dict:
    return {"frame": frame, "value": value}


def track(prop: str, keys: list[dict]) -> dict:
    return {"property": prop, "easing": "linear", "keyframes": keys}


def selector(**overrides) -> dict:
    base = {
        "unit": "line",
        "shape": "square",
        "order": "forward",
        "combine": "replace",
        "exclude_spaces": True,
    }
    base.update(overrides)
    return base


def backdrop_layer() -> dict:
    return {
        "id": "backdrop",
        "type": "color",
        "color": [0.004, 0.008, 0.014, 1.0],
        "size": [1920.0, 1080.0],
        "position": [0.0, 0.0],
        "start_frame": 0,
        "duration_frames": FRAMES,
    }


def text_layer(
    layer_id: str,
    body: str,
    font_size: float,
    position: tuple[float, float],
    animators: list[dict],
    fade_in: int = 12,
    text_transitions: dict | None = None,
) -> dict:
    layer = {
        "id": layer_id,
        "type": "text",
        "text": body,
        "size": [1920.0, 1080.0],
        "position": [position[0], position[1]],
        "start_frame": 0,
        "duration_frames": FRAMES,
        "style": {
            "font": FONT,
            "font_size": font_size,
            "fill": "#F4FAFF",
        },
        "animation": {
            "tracks": [
                {
                    "property": "opacity",
                    "easing": "out_cubic",
                    "keyframes": [kf(0, 0.0), kf(fade_in, 1.0), kf(179, 1.0)],
                }
            ]
        },
        "text_animators": animators,
    }
    if text_transitions is not None:
        layer["text_transitions"] = text_transitions
    return layer


def plan_layers(job_id: str, layers: list[dict]) -> dict:
    return {
        "schema": "chronon.render-plan.v3",
        "version": 3,
        "job_id": job_id,
        "canvas": {
            "width": 1920,
            "height": 1080,
            "fps_num": FPS,
            "fps_den": 1,
            "duration_frames": FRAMES,
        },
        "layers": [backdrop_layer()] + layers,
        "output": {
            "path": f"{job_id}_1920x1080_6s.mp4",
            "format": "mp4",
            "codec": "h264",
        },
    }


def character_value_plan() -> dict:
    # Seven selectors, each targeting one glyph cell.  Every cell starts as
    # 'A' and flips to its authored target on its own stagger, so the clip
    # shows AAAAAAA -> CHRONON per letter instead of the old run-level
    # CCCCCCC/RRRRRRR substitution.  The authored source stays CHRONON and is
    # the immutable input of every frame.
    targets = [ord(ch) for ch in "CHRONON"]
    glyph_count = len(targets)
    animators = []
    for index, target in enumerate(targets):
        lo = index * 100.0 / glyph_count
        hi = (index + 1) * 100.0 / glyph_count
        change = 20 + index * 14
        animators.append({
            "id": f"value_glyph_{index}",
            "selectors": [
                selector(
                    unit="glyph",
                    start={"keyframes": [kf(0, lo)]},
                    end={"keyframes": [kf(0, hi)]},
                )
            ],
            "properties": [
                track(
                    "character_value",
                    [
                        kf(0, 65),
                        kf(change - 1, 65),
                        kf(change, target),
                        kf(179, target),
                    ],
                )
            ],
        })
    return plan_layers(
        "ae_text_01_character_value",
        [text_layer("title", "CHRONON", 150.0, (960.0, 540.0), animators)],
    )


def alignment_row(mode: int, label: str, y: float, window: tuple[float, float]) -> list[dict]:
    lo, hi = window
    animator = {
        "id": f"alignment_{label.lower()}",
        "selectors": [
            selector(
                unit="glyph",
                start={"keyframes": [kf(0, lo)]},
                end={"keyframes": [kf(0, hi)]},
                amount={
                    "keyframes": [
                        kf(0, 0.0),
                        kf(20, 0.0),
                        kf(80, 100.0),
                        kf(140, 0.0),
                        kf(179, 0.0),
                    ]
                },
            )
        ],
        "properties": [track("character_alignment", [kf(0, mode)])],
    }
    marker = text_layer(
        f"marker_{label.lower()}", "X" + " " * 26 + "X", 110.0, (960.0, y), [animator]
    )
    caption = {
        "id": f"label_{label.lower()}",
        "type": "text",
        "text": label,
        "size": [1920.0, 1080.0],
        "position": [250.0, y],
        "start_frame": 0,
        "duration_frames": FRAMES,
        "style": {"font": FONT, "font_size": 40.0, "fill": "#5E7690"},
    }
    return [caption, marker]


def character_alignment_plan() -> dict:
    # One marker glyph per row travels to the row's alignment anchor.
    # LEFT row: the right-hand X moves to line_left (next to the left X).
    # CENTER row: the left X moves to the line centre.
    # RIGHT row: the left X moves to line_right (next to the right X).
    # The amount ramps 0 -> 100 -> 0, so each X travels out and back and
    # never leaves the frame-0 layout bounds.
    layers = []
    layers += alignment_row(0, "LEFT", 330.0, (51.0, 100.0))
    layers += alignment_row(1, "CENTER", 540.0, (0.0, 49.0))
    layers += alignment_row(2, "RIGHT", 750.0, (0.0, 49.0))
    return plan_layers("ae_text_02_character_alignment", layers)


def anchor_grouping_plan() -> dict:
    # Three disjoint word windows: word0 f0-49, word1 f50-99, word2
    # f100-149. Each 50-frame window pops its word once (scale 1 -> 0.70 ->
    # 1, rotation 0 -> 8 deg -> 0) around the word box centre, so the pivot
    # is visible as an in-place pulse. Shrink-only motion keeps the animated
    # word inside the authored layout bounds.
    start_keys = [kf(0, 0.0), kf(49, 0.0), kf(50, 36.0), kf(99, 36.0),
                  kf(100, 70.0), kf(179, 70.0)]
    end_keys = [kf(0, 30.0), kf(49, 30.0), kf(50, 63.0), kf(99, 63.0),
                kf(100, 97.0), kf(179, 97.0)]
    scale_keys = [kf(0, [1.0, 1.0]), kf(25, [0.70, 0.70]), kf(49, [1.0, 1.0]),
                  kf(50, [1.0, 1.0]), kf(75, [0.70, 0.70]), kf(99, [1.0, 1.0]),
                  kf(100, [1.0, 1.0]), kf(125, [0.70, 0.70]), kf(149, [1.0, 1.0]),
                  kf(179, [1.0, 1.0])]
    rotation_keys = [kf(0, [0.0, 0.0, 0.0]), kf(25, [0.0, 0.0, 8.0]),
                     kf(49, [0.0, 0.0, 0.0]), kf(50, [0.0, 0.0, 0.0]),
                     kf(75, [0.0, 0.0, 8.0]), kf(99, [0.0, 0.0, 0.0]),
                     kf(100, [0.0, 0.0, 0.0]), kf(125, [0.0, 0.0, 8.0]),
                     kf(149, [0.0, 0.0, 0.0]), kf(179, [0.0, 0.0, 0.0])]
    animator = {
        "id": "word_pivot_pop",
        "selectors": [
            selector(
                unit="word",
                start={"keyframes": start_keys},
                end={"keyframes": end_keys},
            )
        ],
        "properties": [
            # Word (1): every selected word scales/rotates around its own box
            # centre instead of its first glyph's origin.
            track("anchor_grouping", [kf(0, 1)]),
            {"property": "scale", "easing": "linear", "keyframes": scale_keys},
            {"property": "rotation", "easing": "linear", "keyframes": rotation_keys},
        ],
    }
    return plan_layers(
        "ae_text_03_anchor_grouping",
        [text_layer("title", "PAROLA PER PAROLA", 128.0, (960.0, 540.0), [animator])],
    )


def typewriter_plan() -> dict:
    # The first keyframe types the destination over 120 frames.  Typewriter
    # uses grapheme clusters, so the reveal stays correct for composed text.
    transitions = {
        "keyframes": [
            {
                "frame": 0,
                "text": "",
                "transition": "typewriter",
                "typewriter": {
                    "chars_per_frame": 0,
                    "easing": "out_cubic",
                },
            },
            {"frame": 120, "text": "CHRONON 3D", "transition": "cut"},
        ]
    }
    layer = text_layer("typewriter", "CHRONON 3D", 150.0, (960.0, 540.0), [],
                       text_transitions=transitions)
    # A typewriter gap starts on a single space (mix=0) so the layout stays
    # alive.  The Vulkan MTSDF route rejects a text node with no resident
    # glyphs, so start the layer at frame 6, where the reveal already has its
    # first grapheme; frames 0..5 are the dark intro.
    layer["start_frame"] = 6
    layer["duration_frames"] = FRAMES - 6
    return plan_layers("ae_text_04_typewriter", [layer])


def scramble_plan() -> dict:
    # Deterministic noise settles into the destination: same seed + frame
    # always produces the same intermediate glyphs.  Keep the outgoing text
    # as wide as the destination: the tight text surface is sized from the
    # first layout, and a narrower "??????????" clipped the final C/D.
    transitions = {
        "keyframes": [
            {
                "frame": 0,
                "text": "CHRONON 3D",
                "transition": "scramble",
                "scramble": {
                    "seed": 42,
                    "char_pool": "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789#%",
                    "intensity": 2.0,
                },
            },
            {"frame": 120, "text": "CHRONON 3D", "transition": "cut"},
        ]
    }
    return plan_layers(
        "ae_text_05_scramble",
        [text_layer("scramble", "CHRONON 3D", 150.0, (960.0, 540.0), [],
                    text_transitions=transitions)],
    )


def morph_plan() -> dict:
    # Shared characters persist; incoming characters enter from the centre
    # and removed characters leave toward the centre.
    transitions = {
        "keyframes": [
            {
                "frame": 0,
                "text": "HELLO WORLD",
                "transition": "morph",
                "morph": {
                    "direction": "from_center",
                    "easing": "out_cubic",
                },
            },
            {"frame": 120, "text": "CHRONON 3D", "transition": "cut"},
        ]
    }
    return plan_layers(
        "ae_text_06_morph",
        [text_layer("morph", "CHRONON 3D", 150.0, (960.0, 540.0), [],
                    text_transitions=transitions)],
    )


def selector_parity_plan() -> dict:
    # One clip covering the selector-engine additions: temporal Wiggly,
    # per-glyph Expression, and Range Units=Index with Smoothness.  The text
    # layers stay inside the authored bounds; the animator offsets are small.
    temporal_wiggly = {
        "id": "temporal_wiggly",
        "selectors": [
            selector(
                unit="glyph",
                shape="wiggly",
                wiggly_frequency=1.1,
                wiggly_amplitude=0.65,
                wiggly_seed=7,
                wiggles_per_second=2.2,
                correlation=55.0,
                temporal_phase=0.0,
                spatial_phase=0.0,
                min_amount=12.0,
                max_amount=100.0,
                lock_dimensions=True,
                wiggly_mode="smooth",
            )
        ],
        "properties": [
            track("position", [kf(0, [0.0, 26.0])]),
            track("rotation", [kf(0, 6.0)]),
        ],
    }
    expression = {
        "id": "expression_ramp",
        "selectors": [
            selector(
                unit="glyph",
                shape="square",
                # Output is a percentage; the expression replaces the base
                # weight per glyph.  time is seconds, textIndex is 0-based.
                expression="50 + 50 * sin(time * 2.2 - textIndex * 0.75)",
            )
        ],
        "properties": [track("position", [kf(0, [0.0, 34.0])])],
    }
    index_smooth = {
        "id": "index_smooth",
        "selectors": [
            selector(
                unit="glyph",
                range_units="index",
                start={"keyframes": [kf(0, 0.0)]},
                end={"keyframes": [kf(0, 3.0)]},
                offset={"keyframes": [kf(0, 0.0), kf(179, 9.0)]},
                smoothness=70.0,
            )
        ],
        "properties": [
            track("position", [kf(0, [0.0, -44.0])]),
            track("fill_color", [kf(0, [1.0, 0.55, 0.10, 1.0])]),
        ],
    }
    return plan_layers(
        "ae_text_07_selector_parity",
        [
            text_layer("wiggly_line", "WIGGLY", 122.0, (960.0, 300.0),
                       [temporal_wiggly]),
            text_layer("expression_line", "EXPRESSION", 112.0, (960.0, 540.0),
                       [expression]),
            text_layer("index_line", "INDEX SMOOTH", 96.0, (960.0, 780.0),
                       [index_smooth]),
        ],
    )


def selector_closure_plan() -> dict:
    # Three rows pin the closed selector contracts:
    #  - an index-unit range with a wide smoothness feather;
    #  - a per-glyph expression using only the validated selector profile;
    #  - per-glyph Y rotation above the old 89-degree shear limit, which the
    #    native MTSDF path must render through the exact orthographic branch.
    # The glyph selector on the 3D row is deliberately not a full-run Word
    # selector, so the GPU route consumes resolved per-glyph states.
    smooth = {
        "id": "smooth_window",
        "selectors": [
            selector(
                unit="glyph",
                range_units="index",
                start={"keyframes": [kf(0, 0.0)]},
                end={"keyframes": [kf(0, 4.0)]},
                offset={"keyframes": [kf(0, 0.0), kf(179, 10.0)]},
                smoothness=85.0,
            )
        ],
        "properties": [
            track("position", [kf(0, [0.0, 30.0])]),
            track("fill_color", [kf(0, [1.0, 0.55, 0.10, 1.0])]),
        ],
    }
    expression = {
        "id": "closed_expression",
        "selectors": [
            selector(
                unit="glyph",
                expression="50 + 50 * sin(time * 2.4 - textIndex * 0.85)",
            )
        ],
        "properties": [
            track("position", [kf(0, [0.0, 42.0])]),
            track("fill_color", [kf(0, [0.10, 0.85, 1.0, 1.0])]),
        ],
    }
    exact_3d = {
        "id": "exact_3d",
        "selectors": [selector(unit="glyph")],
        "properties": [
            {
                "property": "rotation",
                "easing": "linear",
                "keyframes": [
                    kf(0, [0.0, 0.0, 0.0]),
                    kf(25, [0.0, 0.0, 0.0]),
                    # Hold beyond the 89-degree threshold; do not return to
                    # the tan/shear branch inside the visible hold.
                    kf(50, [0.0, 120.0, 0.0]),
                    kf(179, [0.0, 120.0, 0.0]),
                ],
            }
        ],
    }
    exact_caption = text_layer(
        "exact_caption", "EXACT ORTHOGRAPHIC / Y = 120 DEG", 26.0,
        (960.0, 930.0), [])
    exact_caption["style"]["fill"] = "#5E7690"
    return plan_layers(
        "ae_text_08_selector_closure",
        [
            text_layer("title", "AE SELECTOR CLOSURE", 44.0, (960.0, 110.0), []),
            text_layer("smooth_line", "SMOOTHNESS", 108.0, (960.0, 340.0), [smooth]),
            text_layer("expression_line", "EXPRESSION", 108.0, (960.0, 570.0), [expression]),
            text_layer("exact_3d_line", "3D EXACT", 132.0, (960.0, 800.0), [exact_3d]),
            exact_caption,
        ],
    )


PLANS = {
    "01_character_value": character_value_plan,
    "02_character_alignment": character_alignment_plan,
    "03_anchor_grouping": anchor_grouping_plan,
    "04_typewriter": typewriter_plan,
    "05_scramble": scramble_plan,
    "06_morph": morph_plan,
    "07_selector_parity": selector_parity_plan,
    "08_selector_closure": selector_closure_plan,
}


def generate(only: str = "") -> list[Path]:
    plans_dir = ROOT / "plans"
    plans_dir.mkdir(parents=True, exist_ok=True)
    written = []
    for stem, builder in PLANS.items():
        if only and stem != only:
            continue
        path = plans_dir / f"{stem}.plan.json"
        path.write_text(json.dumps(builder(), indent=2) + "\n", encoding="utf-8")
        written.append(path)
        print(f"PLAN {path.relative_to(REPO)}")
    return written


def validate(plan_path: Path) -> None:
    result = subprocess.run(
        [str(CLI), "validate", "--plan", str(plan_path), "--assets-root", str(ASSETS)],
        cwd=REPO, text=True, capture_output=True,
    )
    if result.returncode != 0:
        tail = (result.stdout + result.stderr).strip().splitlines()[-10:]
        raise SystemExit(f"validation failed for {plan_path.name}: " + " | ".join(tail))


def probe(video: Path) -> dict:
    result = subprocess.run(
        [
            "ffprobe", "-v", "error", "-count_frames", "-select_streams", "v:0",
            "-show_entries",
            "stream=width,height,nb_read_frames,r_frame_rate:format=duration,size",
            "-of", "json", str(video),
        ],
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


def render(only: str = "") -> dict:
    if not CLI.is_file():
        raise SystemExit(f"chronon3d_cli not found: {CLI}")
    videos_dir = ROOT / "videos"
    logs_dir = ROOT / "logs"
    videos_dir.mkdir(parents=True, exist_ok=True)
    logs_dir.mkdir(parents=True, exist_ok=True)

    manifest = {}

    for plan_path in generate(only):
        stem = plan_path.name.removesuffix(".plan.json")
        video = videos_dir / f"{stem}_1920x1080_6s.mp4"
        log = logs_dir / f"{stem}.log"
        validate(plan_path)
        command = [
            str(CLI), "render",
            "--plan", str(plan_path),
            "--assets-root", str(ASSETS),
            "--backend", "vulkan",
            "--gpu-hot-path-mode", "require_gpu_native",
            "--tone-map", "aces",
            "--exposure", "1.0",
            "-o", str(video),
        ]
        started = time.time()
        with log.open("w", encoding="utf-8") as handle:
            handle.write(" ".join(command) + "\n\n")
            handle.flush()
            result = subprocess.run(
                command, cwd=REPO, stdout=handle, stderr=subprocess.STDOUT)
        if result.returncode != 0:
            tail = log.read_text(encoding="utf-8", errors="replace").strip().splitlines()[-12:]
            raise SystemExit(f"render failed for {stem}: " + " | ".join(tail))
        info = probe(video)
        info["plan"] = str(plan_path.relative_to(REPO))
        info["video"] = str(video.relative_to(REPO))
        info["log"] = str(log.relative_to(REPO))
        info["seconds"] = round(time.time() - started, 1)
        manifest[stem] = info
        print(f"RENDER {stem} {info['seconds']}s {info['width']}x{info['height']} "
              f"{info['frames']} frames")

    manifest_path = ROOT / (
        "MANIFEST.json" if not only else f"MANIFEST_{only}.json")
    manifest_path.write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"MANIFEST {manifest_path.relative_to(REPO)}")
    return manifest


def verify(only: str = "") -> dict:
    stills_dir = ROOT / "stills"
    stills_dir.mkdir(parents=True, exist_ok=True)
    videos_dir = ROOT / "videos"
    report = {}
    for video in sorted(videos_dir.glob("*.mp4")):
        if only and not video.stem.startswith(only):
            continue
        info = probe(video)
        report[video.stem] = info
        if (info["width"], info["height"], info["frames"]) != (1920, 1080, FRAMES):
            raise SystemExit(f"unexpected probe for {video.name}: {info}")
        stem = video.stem.removesuffix("_1920x1080_6s")
        for label, second in (("early", 1.0), ("mid", 2.6), ("late", 4.2)):
            still = stills_dir / f"{stem}_{label}.png"
            subprocess.run(
                ["ffmpeg", "-y", "-v", "error", "-ss", f"{second:.3f}",
                 "-i", str(video), "-frames:v", "1", str(still)],
                check=True,
            )
        print(f"VERIFY {video.name} {info['width']}x{info['height']} "
              f"{info['frames']} frames")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--generate", action="store_true")
    parser.add_argument("--render", action="store_true")
    parser.add_argument("--verify", action="store_true")
    parser.add_argument("--only", default="",
                        help="restrict generate/render/verify to one plan stem")
    args = parser.parse_args()
    if args.render:
        render(args.only)
        verify(args.only)
    elif args.generate:
        generate(args.only)
    elif args.verify:
        verify(args.only)
    else:
        parser.print_help()
