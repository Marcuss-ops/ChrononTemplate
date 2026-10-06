#!/usr/bin/env python3
"""Chronon Short Phrase Pack Compiler (v4 - Pure & Accurate).

Compiles the 12 short-phrase archetypes into chronon.render-plan.v2 plans.
- Rock-solid center hold (ZERO ambient drift wobble).
- Pixel-perfect background plates (true blue glow, dot grid, corner marks).
- Precise word / glyph timing and semantic highlights.
- Professional short phrase durations: 1.8s to 2.5s (54 - 75 frames @ 30 fps).
"""
import json, os, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
CHRONON3D = REPO / "Chronon3d"
OUT_DIR = HERE / "out"

DARK_PLATE = "assets/images/short_phrase_dark_plate.png"
LIGHT_PLATE = "assets/images/short_phrase_light_plate.png"
FONT = "assets/fonts/Inter-Bold.ttf"

BLUE_ACCENT = [0.42, 0.65, 1.0, 1.0]   # vibrant Apple/Chronon accent blue
WHITE = [1.0, 1.0, 1.0, 1.0]
BLACK = [0.03, 0.03, 0.03, 1.0]
GREY = [0.45, 0.45, 0.48, 1.0]


def track(prop, keys, easing="linear"):
    return {
        "property": prop,
        "keyframes": [{"frame": int(f), "value": v} for f, v in keys],
        "easing": easing
    }


def text_animator(anim_id, unit, shape, order, start_keys, end_keys, properties):
    return {
        "id": anim_id,
        "selectors": [
            {
                "id": f"{anim_id}_sel",
                "unit": unit,
                "shape": shape,
                "order": order,
                "combine": "replace",
                "exclude_spaces": True,
                "start": {"keyframes": [{"frame": int(f), "value": v} for f, v in start_keys], "easing": "linear"},
                "end": {"keyframes": [{"frame": int(f), "value": v} for f, v in end_keys], "easing": "linear"}
            }
        ],
        "properties": properties
    }


def make_plan(plan_id, duration_frames, bg_plate, text_layers):
    layers = [
        {
            "id": "background",
            "type": "image",
            "asset": bg_plate,
            "size": [1920, 1080],
            "position": [0, 0],
            "start_frame": 0,
            "duration_frames": duration_frames
        }
    ]
    layers.extend(text_layers)
    return {
        "schema": "chronon.render-plan.v2",
        "version": 2,
        "job_id": f"short_phrase_{plan_id}",
        "canvas": {
            "width": 1920,
            "height": 1080,
            "fps_num": 30,
            "fps_den": 1,
            "duration_frames": duration_frames
        },
        "layers": layers,
        "output": {
            "path": f"short_phrase_{plan_id}.mp4",
            "format": "mp4",
            "codec": "h264"
        }
    }


# ── Archetype 01: scale_settle_word ───────────────────────────────────────────
def plan_01():
    # "Clean" enters large & grey, soft blur -> settles white, rock steady hold -> clean fade
    dur = 54
    text_layer = {
        "id": "phrase",
        "type": "text",
        "text": "Clean",
        "size": [1920, 1080],
        "position": [960, 540],
        "style": {"font": FONT, "font_size": 140, "fill": "#FFFFFF", "stroke": {"color": "#000000", "width": 0}, "glow": {"radius": 0, "intensity": 0, "color": "#000000"}},
        "start_frame": 0,
        "duration_frames": dur,
        "animation": {
            "tracks": [
                track("scale", [[0, 1.30], [8, 0.98], [12, 1.0], [44, 1.0], [52, 0.96]], "out_cubic"),
                track("opacity", [[0, 0.25], [8, 1.0], [44, 1.0], [52, 0.0]], "linear"),
                track("blur", [[0, 6.0], [8, 0.0], [52, 0.0]], "out_cubic")
            ]
        }
    }
    return make_plan("01_scale_settle_word", dur, DARK_PLATE, [text_layer])


# ── Archetype 02: shape_phrase_wipe ───────────────────────────────────────────
def plan_02():
    # Light theme: "It's really easy to manage." (clean wipe reveal across line)
    dur = 66
    text_layer = {
        "id": "phrase",
        "type": "text",
        "text": "It's really easy to manage.",
        "size": [1920, 1080],
        "position": [960, 540],
        "style": {"font": FONT, "font_size": 76, "fill": "#080808", "stroke": {"color": "#000000", "width": 0}, "glow": {"radius": 0, "intensity": 0, "color": "#000000"}},
        "start_frame": 0,
        "duration_frames": dur,
        "animation": {
            "tracks": [
                track("opacity", [[0, 0.0], [10, 0.0], [18, 1.0], [54, 1.0], [64, 0.0]], "linear")
            ]
        },
        "text_animators": [
            text_animator(
                "wipe_in", "glyph", "smooth", "forward",
                [[0, 0], [20, 100]], [[0, 15], [20, 100]],
                [track("opacity", [[0, 0.0], [20, 1.0]], "linear")]
            )
        ]
    }
    return make_plan("02_shape_phrase_wipe", dur, LIGHT_PLATE, [text_layer])


# ── Archetype 03: semantic_two_line ───────────────────────────────────────────
def plan_03():
    # Two lines: "Good text design is invisible / bad text design is unforgettable"
    # "invisible" (word 4) and "bad" (word 5) highlighted in blue, then settle to white
    dur = 78
    text_layer = {
        "id": "phrase",
        "type": "text",
        "text": "Good text design is invisible\nbad text design is unforgettable",
        "size": [1920, 1080],
        "position": [960, 540],
        "style": {"font": FONT, "font_size": 70, "fill": "#FFFFFF", "stroke": {"color": "#000000", "width": 0}, "glow": {"radius": 0, "intensity": 0, "color": "#000000"}},
        "start_frame": 0,
        "duration_frames": dur,
        "animation": {
            "tracks": [
                track("opacity", [[0, 0.0], [6, 1.0], [68, 1.0], [76, 0.0]], "linear")
            ]
        },
        "text_animators": [
            # Word stagger entrance
            text_animator(
                "words_in", "word", "smooth", "forward",
                [[0, 0], [28, 100]], [[0, 15], [28, 100]],
                [
                    track("opacity", [[0, 0.15], [28, 1.0]], "linear"),
                    track("position_y", [[0, 8.0], [28, 0.0]], "linear")
                ]
            ),
            # Emphasis blue for words 4 and 5 ("invisible" and "bad")
            text_animator(
                "emphasis_blue", "word", "square", "forward",
                [[0, 44]], [[0, 66]],
                [
                    track("fill_color", [
                        [0, BLUE_ACCENT], [32, BLUE_ACCENT], [48, WHITE], [dur - 1, WHITE]
                    ], "linear")
                ]
            )
        ]
    }
    return make_plan("03_semantic_two_line", dur, DARK_PLATE, [text_layer])


# ── Archetype 04: phrase_build_focus ──────────────────────────────────────────
def plan_04():
    # "Will make your video" - builds with focus on "your video" in blue
    dur = 72
    text_layer = {
        "id": "phrase",
        "type": "text",
        "text": "Will make your video",
        "size": [1920, 1080],
        "position": [960, 540],
        "style": {"font": FONT, "font_size": 88, "fill": "#FFFFFF", "stroke": {"color": "#000000", "width": 0}, "glow": {"radius": 0, "intensity": 0, "color": "#000000"}},
        "start_frame": 0,
        "duration_frames": dur,
        "animation": {
            "tracks": [
                track("opacity", [[0, 0.0], [5, 1.0], [64, 1.0], [71, 0.0]], "linear")
            ]
        },
        "text_animators": [
            text_animator(
                "build_in", "word", "smooth", "forward",
                [[0, 0], [22, 100]], [[0, 30], [22, 100]],
                [
                    track("opacity", [[0, 0.15], [22, 1.0]], "linear"),
                    track("position_x", [[0, -8.0], [22, 0.0]], "linear")
                ]
            ),
            text_animator(
                "focus_blue", "word", "square", "forward",
                [[0, 50]], [[0, 100]],
                [
                    track("fill_color", [
                        [0, BLUE_ACCENT], [26, BLUE_ACCENT], [42, WHITE], [dur - 1, WHITE]
                    ], "linear")
                ]
            )
        ]
    }
    return make_plan("04_phrase_build_focus", dur, DARK_PLATE, [text_layer])


# ── Archetype 05: character_tracking_reveal ───────────────────────────────────
def plan_05():
    # "more expensive" - letter by letter with wide tracking settling to normal
    dur = 66
    text_layer = {
        "id": "phrase",
        "type": "text",
        "text": "more expensive",
        "size": [1920, 1080],
        "position": [960, 540],
        "style": {"font": FONT, "font_size": 96, "fill": "#FFFFFF", "stroke": {"color": "#000000", "width": 0}, "glow": {"radius": 0, "intensity": 0, "color": "#000000"}},
        "start_frame": 0,
        "duration_frames": dur,
        "animation": {
            "tracks": [
                track("opacity", [[0, 0.0], [4, 1.0], [58, 1.0], [65, 0.0]], "linear")
            ]
        },
        "text_animators": [
            text_animator(
                "char_reveal", "glyph", "smooth", "forward",
                [[0, 0], [22, 100]], [[0, 10], [22, 100]],
                [
                    track("opacity", [[0, 0.0], [22, 1.0]], "linear"),
                    track("tracking", [[0, 20.0], [22, 0.0]], "linear"),
                    track("position_x", [[0, 8.0], [22, 0.0]], "linear")
                ]
            )
        ]
    }
    return make_plan("05_character_tracking_reveal", dur, DARK_PLATE, [text_layer])


# ── Archetype 06: word_mask_sequence ──────────────────────────────────────────
def plan_06():
    # "leave" -> "your" -> "message" sequentially in central slot
    dur = 72
    # Static layer lifetime: start_frame=0, duration_frames=dur for all layers to guarantee Vulkan stability
    w0 = {
        "id": "word_0",
        "type": "text",
        "text": "leave",
        "size": [1920, 1080],
        "position": [960, 540],
        "style": {"font": FONT, "font_size": 130, "fill": "#FFFFFF", "stroke": {"color": "#000000", "width": 0}, "glow": {"radius": 0, "intensity": 0, "color": "#000000"}},
        "start_frame": 0,
        "duration_frames": dur,
        "animation": {
            "tracks": [
                track("opacity", [[0, 0.0], [4, 1.0], [18, 1.0], [23, 0.0], [dur - 1, 0.0]], "linear"),
                track("position_x", [[0, -20.0], [5, 0.0], [18, 0.0], [23, 20.0]], "out_cubic")
            ]
        }
    }
    w1 = {
        "id": "word_1",
        "type": "text",
        "text": "your",
        "size": [1920, 1080],
        "position": [960, 540],
        "style": {"font": FONT, "font_size": 130, "fill": "#FFFFFF", "stroke": {"color": "#000000", "width": 0}, "glow": {"radius": 0, "intensity": 0, "color": "#000000"}},
        "start_frame": 0,
        "duration_frames": dur,
        "animation": {
            "tracks": [
                track("opacity", [[0, 0.0], [22, 0.0], [26, 1.0], [40, 1.0], [45, 0.0], [dur - 1, 0.0]], "linear"),
                track("position_x", [[0, 0.0], [22, -20.0], [27, 0.0], [40, 0.0], [45, 20.0]], "out_cubic")
            ]
        }
    }
    w2 = {
        "id": "word_2",
        "type": "text",
        "text": "message",
        "size": [1920, 1080],
        "position": [960, 540],
        "style": {"font": FONT, "font_size": 130, "fill": "#FFFFFF", "stroke": {"color": "#000000", "width": 0}, "glow": {"radius": 0, "intensity": 0, "color": "#000000"}},
        "start_frame": 0,
        "duration_frames": dur,
        "animation": {
            "tracks": [
                track("opacity", [[0, 0.0], [44, 0.0], [48, 1.0], [66, 1.0], [71, 0.0]], "linear"),
                track("position_x", [[0, 0.0], [44, -20.0], [49, 0.0], [66, 0.0], [71, 20.0]], "out_cubic")
            ]
        }
    }
    return make_plan("06_word_mask_sequence", dur, DARK_PLATE, [w0, w1, w2])


# ── Archetype 07: character_cascade_shapes ────────────────────────────────────
def plan_07():
    # Light theme: "Really smooth." (glyph cascade 25-40ms)
    dur = 68
    text_layer = {
        "id": "phrase",
        "type": "text",
        "text": "Really smooth.",
        "size": [1920, 1080],
        "position": [960, 540],
        "style": {"font": FONT, "font_size": 96, "fill": "#080808", "stroke": {"color": "#000000", "width": 0}, "glow": {"radius": 0, "intensity": 0, "color": "#000000"}},
        "start_frame": 0,
        "duration_frames": dur,
        "animation": {
            "tracks": [
                track("opacity", [[0, 0.0], [4, 1.0], [60, 1.0], [67, 0.0]], "linear")
            ]
        },
        "text_animators": [
            text_animator(
                "cascade", "glyph", "smooth", "forward",
                [[0, 0], [24, 100]], [[0, 10], [24, 100]],
                [
                    track("opacity", [[0, 0.0], [24, 1.0]], "linear"),
                    track("position_y", [[0, 16.0], [24, 0.0]], "linear")
                ]
            )
        ]
    }
    return make_plan("07_character_cascade_shapes", dur, LIGHT_PLATE, [text_layer])


# ── Archetype 08: word_cascade_sentence ───────────────────────────────────────
def plan_08():
    # "Clean. Simple. Attractive." - word by word entry with blue accent -> white
    dur = 78
    text_layer = {
        "id": "phrase",
        "type": "text",
        "text": "Clean. Simple. Attractive.",
        "size": [1920, 1080],
        "position": [960, 540],
        "style": {"font": FONT, "font_size": 92, "fill": "#FFFFFF", "stroke": {"color": "#000000", "width": 0}, "glow": {"radius": 0, "intensity": 0, "color": "#000000"}},
        "start_frame": 0,
        "duration_frames": dur,
        "animation": {
            "tracks": [
                track("opacity", [[0, 0.0], [4, 1.0], [68, 1.0], [76, 0.0]], "linear")
            ]
        },
        "text_animators": [
            text_animator(
                "word_stagger", "word", "smooth", "forward",
                [[0, 0], [26, 100]], [[0, 25], [26, 100]],
                [
                    track("opacity", [[0, 0.2], [26, 1.0]], "linear"),
                    track("position_x", [[0, -6.0], [26, 0.0]], "linear"),
                    track("fill_color", [
                        [0, BLUE_ACCENT], [18, BLUE_ACCENT], [26, WHITE], [dur - 1, WHITE]
                    ], "linear")
                ]
            )
        ]
    }
    return make_plan("08_word_cascade_sentence", dur, DARK_PLATE, [text_layer])


# ── Archetype 09: semantic_chain_curve ────────────────────────────────────────
def plan_09():
    # "we draw attention to something important" - words build, "attention" & "important" blue
    dur = 84
    text_layer = {
        "id": "phrase",
        "type": "text",
        "text": "we draw attention to something important",
        "size": [1920, 1080],
        "position": [960, 540],
        "style": {"font": FONT, "font_size": 56, "fill": "#FFFFFF", "stroke": {"color": "#000000", "width": 0}, "glow": {"radius": 0, "intensity": 0, "color": "#000000"}},
        "start_frame": 0,
        "duration_frames": dur,
        "animation": {
            "tracks": [
                track("opacity", [[0, 0.0], [5, 1.0], [74, 1.0], [82, 0.0]], "linear")
            ]
        },
        "text_animators": [
            text_animator(
                "chain_in", "word", "smooth", "forward",
                [[0, 0], [30, 100]], [[0, 20], [30, 100]],
                [
                    track("opacity", [[0, 0.2], [30, 1.0]], "linear"),
                    track("position_y", [[0, 8.0], [30, 0.0]], "linear")
                ]
            ),
            # Words 2 ("attention") and 5 ("important")
            text_animator(
                "key_blue", "word", "square", "forward",
                [[0, 30]], [[0, 95]],
                [
                    track("fill_color", [
                        [0, BLUE_ACCENT], [36, BLUE_ACCENT], [52, WHITE], [dur - 1, WHITE]
                    ], "linear")
                ]
            )
        ]
    }
    return make_plan("09_semantic_chain_curve", dur, DARK_PLATE, [text_layer])


# ── Archetype 10: simple_progressive_phrase ───────────────────────────────────
def plan_10():
    # "Just what I needed" - clean progressive build, incoming word blue then white
    dur = 66
    text_layer = {
        "id": "phrase",
        "type": "text",
        "text": "Just what I needed",
        "size": [1920, 1080],
        "position": [960, 540],
        "style": {"font": FONT, "font_size": 86, "fill": "#FFFFFF", "stroke": {"color": "#000000", "width": 0}, "glow": {"radius": 0, "intensity": 0, "color": "#000000"}},
        "start_frame": 0,
        "duration_frames": dur,
        "animation": {
            "tracks": [
                track("opacity", [[0, 0.0], [4, 1.0], [58, 1.0], [65, 0.0]], "linear")
            ]
        },
        "text_animators": [
            text_animator(
                "prog_in", "word", "smooth", "forward",
                [[0, 0], [22, 100]], [[0, 25], [22, 100]],
                [
                    track("opacity", [[0, 0.2], [22, 1.0]], "linear"),
                    track("fill_color", [
                        [0, BLUE_ACCENT], [16, BLUE_ACCENT], [22, WHITE], [dur - 1, WHITE]
                    ], "linear")
                ]
            )
        ]
    }
    return make_plan("10_simple_progressive_phrase", dur, DARK_PLATE, [text_layer])


# ── Archetype 11: single_word_swap ────────────────────────────────────────────
def plan_11():
    # "Intro" -> "style" (blue) -> "animation" in central slot
    dur = 72
    # Static layer lifetime: start_frame=0, duration_frames=dur for all layers to guarantee Vulkan stability
    w0 = {
        "id": "swap_0",
        "type": "text",
        "text": "Intro",
        "size": [1920, 1080],
        "position": [960, 540],
        "style": {"font": FONT, "font_size": 130, "fill": "#FFFFFF", "stroke": {"color": "#000000", "width": 0}, "glow": {"radius": 0, "intensity": 0, "color": "#000000"}},
        "start_frame": 0,
        "duration_frames": dur,
        "animation": {
            "tracks": [
                track("scale", [[0, 0.92], [5, 1.0], [18, 1.0], [23, 1.04], [dur - 1, 1.0]], "out_cubic"),
                track("opacity", [[0, 0.0], [4, 1.0], [18, 1.0], [23, 0.0], [dur - 1, 0.0]], "linear")
            ]
        }
    }
    w1 = {
        "id": "swap_1",
        "type": "text",
        "text": "style",
        "size": [1920, 1080],
        "position": [960, 540],
        "style": {"font": FONT, "font_size": 130, "fill": "#6BA3FF", "stroke": {"color": "#000000", "width": 0}, "glow": {"radius": 0, "intensity": 0, "color": "#000000"}},
        "start_frame": 0,
        "duration_frames": dur,
        "animation": {
            "tracks": [
                track("scale", [[0, 1.0], [22, 0.92], [27, 1.0], [40, 1.0], [45, 1.04], [dur - 1, 1.0]], "out_cubic"),
                track("opacity", [[0, 0.0], [22, 0.0], [26, 1.0], [40, 1.0], [45, 0.0], [dur - 1, 0.0]], "linear")
            ]
        }
    }
    w2 = {
        "id": "swap_2",
        "type": "text",
        "text": "animation",
        "size": [1920, 1080],
        "position": [960, 540],
        "style": {"font": FONT, "font_size": 130, "fill": "#FFFFFF", "stroke": {"color": "#000000", "width": 0}, "glow": {"radius": 0, "intensity": 0, "color": "#000000"}},
        "start_frame": 0,
        "duration_frames": dur,
        "animation": {
            "tracks": [
                track("scale", [[0, 1.0], [44, 0.92], [49, 1.0], [66, 1.0], [71, 1.04]], "out_cubic"),
                track("opacity", [[0, 0.0], [44, 0.0], [48, 1.0], [66, 1.0], [71, 0.0]], "linear")
            ]
        }
    }
    return make_plan("11_single_word_swap", dur, DARK_PLATE, [w0, w1, w2])


# ── Archetype 12: character_write_on ──────────────────────────────────────────
def plan_12():
    # "Thanks for watching!" - elegant character write-on (typing cascade)
    dur = 72
    text_layer = {
        "id": "phrase",
        "type": "text",
        "text": "Thanks for watching!",
        "size": [1920, 1080],
        "position": [960, 540],
        "style": {"font": FONT, "font_size": 86, "fill": "#FFFFFF", "stroke": {"color": "#000000", "width": 0}, "glow": {"radius": 0, "intensity": 0, "color": "#000000"}},
        "start_frame": 0,
        "duration_frames": dur,
        "animation": {
            "tracks": [
                track("opacity", [[0, 0.0], [4, 1.0], [64, 1.0], [71, 0.0]], "linear")
            ]
        },
        "text_animators": [
            text_animator(
                "typing", "glyph", "smooth", "forward",
                [[0, 0], [24, 100]], [[0, 8], [24, 100]],
                [
                    track("opacity", [[0, 0.0], [24, 1.0]], "linear")
                ]
            ),
            # Subtle blue focus on "watching!"
            text_animator(
                "watching_blue", "word", "square", "forward",
                [[0, 66]], [[0, 100]],
                [
                    track("fill_color", [
                        [0, BLUE_ACCENT], [26, BLUE_ACCENT], [38, WHITE], [dur - 1, WHITE]
                    ], "linear")
                ]
            )
        ]
    }
    return make_plan("12_character_write_on", dur, DARK_PLATE, [text_layer])


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    generators = {
        "01_scale_settle_word": plan_01,
        "02_shape_phrase_wipe": plan_02,
        "03_semantic_two_line": plan_03,
        "04_phrase_build_focus": plan_04,
        "05_character_tracking_reveal": plan_05,
        "06_word_mask_sequence": plan_06,
        "07_character_cascade_shapes": plan_07,
        "08_word_cascade_sentence": plan_08,
        "09_semantic_chain_curve": plan_09,
        "10_simple_progressive_phrase": plan_10,
        "11_single_word_swap": plan_11,
        "12_character_write_on": plan_12
    }
    for name, gen in generators.items():
        plan = gen()
        out_file = OUT_DIR / f"{name}.plan.json"
        out_file.write_text(json.dumps(plan, indent=2))
        print(f"Generated {out_file.name}")


if __name__ == "__main__":
    main()
