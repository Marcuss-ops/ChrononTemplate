#!/usr/bin/env python3
"""Generate synchronized typewriter previews for date and numeric titles."""
from __future__ import annotations

import json
import math
import random
from pathlib import Path
from PIL import ImageFont

ROOT = Path(__file__).resolve().parents[1]
ASSET_ROOT = ROOT.parent / "Chronon3d"
OUT = ROOT / "out/typewriter_modern_v1"
W, H, FPS, FRAMES = 1920, 1080, 30, 150
WHITE, RED = "#F5F7FA", "#FF202A"
BRIC = "assets/fonts/Bricolage-Grotesque.ttf"
# Match the modern Short Phrases pack: every text layer uses Bricolage Grotesque.
MONO = BRIC
SPACE_AFTER_FINAL_GLYPH = 0.32  # em units, leaves a readable final caret gap.
FONT_METRICS: dict[tuple[str, int], ImageFont.FreeTypeFont] = {}

STYLES = [
    ("01_monospace_block_cursor", "Modern terminal block cursor", "30 SEP 2026", "date", "mono_block"),
    ("02_kinetic_scramble", "Kinetic scramble / matrix", "12/10/2026", "date", "scramble"),
    ("03_soft_opacity_ramp", "Soft opacity typewriter", "42.8%", "number", "soft"),
    ("04_character_bounce", "Per-glyph bounce overshoot", "18 MAY 2026", "date", "bounce"),
    ("05_backspace_correction", "Type and backspace correction", "1998 → 2026", "date", "correction"),
    ("06_glow_beam_sweep", "Glow beam sweep", "+18.6%", "number", "beam"),
    ("07_word_snap", "Word-snap typewriter", "Q4 · 2025", "date", "word"),
    ("08_mechanical_y_shift", "Mechanical y-shift pop", "30 SEP 2026", "date", "yshift"),
    ("09_highlighter_expansion", "Highlighter box expansion", "€3.4B", "number", "highlight"),
    ("10_weight_ramp", "Thin-to-heavy weight ramp", "42.8%", "number", "weight"),
    ("11_dynamic_auto_wrap", "Dynamic multiline auto-wrap", "18 MAY\n2026", "date", "wrap"),
    ("12_glitch_pop", "RGB glitch-pop", "12/10/2026", "date", "glitch"),
    ("13_elastic_leading_cursor", "Elastic leading cursor", "€3.4B", "number", "spring"),
    ("14_focal_blur_dissolve", "Focal blur dissolve", "1998 → 2026", "date", "blur"),
    ("15_paper_punch_stencil", "Paper punch stencil", "+18.6%", "number", "punch"),
]


def font_metrics(font_path: str, size: float) -> ImageFont.FreeTypeFont:
    key = (font_path, int(round(size)))
    if key not in FONT_METRICS:
        FONT_METRICS[key] = ImageFont.truetype(str(ASSET_ROOT / font_path), key[1])
    return FONT_METRICS[key]


def sampled_track(prop: str, keyframes: list[tuple[int, float]], easing: str = "linear") -> dict:
    """Sample layer tracks per frame, with deterministic easing for the few eased accents."""
    ordered = {int(frame): value for frame, value in keyframes}
    frames = sorted(ordered)
    result = []
    for frame in range(FRAMES):
        if frame <= frames[0]:
            value = ordered[frames[0]]
        elif frame >= frames[-1]:
            value = ordered[frames[-1]]
        else:
            i = next(i for i in range(len(frames) - 1) if frames[i] <= frame <= frames[i + 1])
            left, right = frames[i], frames[i + 1]
            t = (frame - left) / (right - left)
            if easing == "out_cubic":
                t = 1 - (1 - t) ** 3
            elif easing == "out_back":
                c = 1.70158
                t = 1 + (c + 1) * (t - 1) ** 3 + c * (t - 1) ** 2
            value = ordered[left] + (ordered[right] - ordered[left]) * t
        result.append({"frame": frame, "value": value})
    return {"property": prop, "easing": "linear", "keyframes": result}


def layer_track(prop: str, frames: list[tuple[int, float]], easing: str = "linear") -> dict:
    """Sparse layer track; renderer handles easing for layer transform properties."""
    ordered = {int(frame): value for frame, value in frames}
    return {"property": prop, "easing": easing,
            "keyframes": [{"frame": frame, "value": ordered[frame]} for frame in sorted(ordered)]}


def text_layer(layer_id, text, font=BRIC, size=122, fill=WHITE, pos=(960, 540),
               box=(1740, 430), glow=None, stroke="#000000", stroke_width=0,
               layer_tracks=None, text_animators=None, background=None, scale=None):
    style = {"font": font, "font_size": size, "fill": fill,
             "stroke": {"color": stroke, "width": stroke_width}}
    if glow:
        style["glow"] = {"radius": glow[0], "intensity": glow[1], "color": glow[2]}
    if background:
        style["background"] = background
    layer = {"id": layer_id, "type": "text", "text": text, "size": list(box),
             "position": list(pos), "style": style, "start_frame": 0,
             "duration_frames": FRAMES}
    if layer_tracks:
        layer["animation"] = {"tracks": layer_tracks}
    if text_animators:
        layer["text_animators"] = text_animators
    if scale:
        layer["scale"] = list(scale)
    return layer


def reveal_units(text: str, unit: str) -> int:
    if unit == "word":
        return len(text.split())
    # Spaces occupy selector glyph units and consume a cursor stop even though
    # they have no visible ink. Newlines affect layout but are not glyphs.
    return sum(1 for char in text if char != "\n")


def frontier(unit_count: int, start_frame: int, end_frame: int) -> list[tuple[int, float]]:
    """Piecewise-constant selector frontier; glyph k releases on the cursor's kth stop."""
    if unit_count <= 0:
        return [(0, 100.0), (FRAMES - 1, 100.0)]
    duration = max(1, end_frame - start_frame)
    # Emit a key at every frame: sparse keys would interpolate between stops,
    # releasing a glyph gradually before the cursor reaches it.
    keys = []
    for frame in range(FRAMES):
        count = 0 if frame < start_frame else min(unit_count, (frame - start_frame) * unit_count // duration)
        keys.append((frame, 100.0 * count / unit_count))
    return keys


def type_on_mask(text, start_frame, end_frame, unit="glyph", shape="square", ident="type_on"):
    units = reveal_units(text, unit)
    # A square boundary is intentional: smooth/ramp shapes affect glyphs
    # before the frontier reaches them, violating cursor-led timing.
    sel = {"id": ident + "_selector", "unit": unit, "shape": "square",
           "order": "forward", "combine": "replace", "exclude_spaces": False,
           "start": {"easing": "linear", "keyframes": [
               {"frame": frame, "value": value} for frame, value in frontier(units, start_frame, end_frame)]},
           "end": {"easing": "linear", "keyframes": [{"frame": 0, "value": 100.0}]}}
    # Opacity=0 is the hidden state. The expanding square selector removes that
    # opacity from the already typed prefix only; future glyphs stay transparent.
    prop = {"property": "opacity", "easing": "linear", "keyframes": [
        {"frame": 0, "value": 0.0}, {"frame": FRAMES - 1, "value": 0.0}]}
    return {"id": ident, "selectors": [sel], "properties": [prop]}


def cursor_positions(text, font, size, start_frame, end_frame, unit="glyph", gap=8.0, spring=False):
    face = font_metrics(font, size)
    lines = text.split("\n")
    line_widths = [face.getlength(line) for line in lines]
    bbox = face.getbbox("Ag")
    line_height = max(size, bbox[3] - bbox[1]) * 1.12
    stops = []
    for line_index, line in enumerate(lines):
        baseline_y = (line_index - (len(lines) - 1) / 2.0) * line_height
        left = -line_widths[line_index] / 2.0
        prefix = ""
        if unit == "word":
            words = line.split()
            prefix_words = []
            for word in words:
                prefix_words.append(word)
                prefix = " ".join(prefix_words)
                stops.append((left + face.getlength(prefix) + gap, baseline_y))
        else:
            for char in line:
                prefix += char
                # Match the selector's glyph indexing: spaces advance the
                # cursor even though they do not paint a visible character.
                stops.append((left + face.getlength(prefix) + gap, baseline_y))
    if not stops:
        stops = [(0.0, 0.0)]
    # For per-glyph typing, park on the first glyph's cell from frame zero;
    # the first release reveals it under the cursor, then the cursor advances.
    # Word-snap starts before the first whole-word release.
    initial_x = stops[0][0] if unit == "glyph" else (
        -line_widths[0] / 2.0 - gap - face.getlength("I") / 2.0)
    total = len(stops)
    span = max(1, end_frame - start_frame)
    positions = []
    ys = []
    for frame in range(FRAMES):
        # Match `frontier()` exactly: the cursor pauses before a glyph and
        # advances to its trailing edge on the same frame that glyph is released.
        count = 0 if frame < start_frame else min(total, (frame - start_frame) * total // span)
        if count <= 0:
            x, y = initial_x, 0.0
        else:
            x, y = stops[min(count - 1, total - 1)]
            if count >= total:
                x += size * SPACE_AFTER_FINAL_GLYPH
        if spring and count > 0 and count < total:
            next_x, _ = stops[count]
            x = x + (next_x - x) * 0.35
        positions.append((frame, x))
        ys.append((frame, y))
    cursor_width = face.getlength("I")
    x_track = [(frame, x - cursor_width / 2.0) for frame, x in positions]
    y_track = ys
    return x_track, y_track


def cursor_layer(text, font, size, reveal_end, glyph="I", spring=False, color=RED,
                 start_frame=0, unit="glyph"):
    x_keys, y_keys = cursor_positions(text, font, size, start_frame, reveal_end, unit, spring=spring)
    blink = [(0, 1.0), (max(1, start_frame + reveal_end), 1.0),
             (min(FRAMES - 1, start_frame + reveal_end + 1), 0.0)]
    for frame in range(start_frame + reveal_end + 8, FRAMES - 1, 8):
        blink.extend([(frame, 1.0), (min(frame + 4, FRAMES - 1), 0.0)])
    tracks = [sampled_track("position_x", x_keys, "out_back" if spring else "linear"),
              sampled_track("position_y", y_keys), layer_track("opacity", blink)]
    return text_layer("cursor", glyph, font, size, color, (960, 540), (100, 320),
                      glow=(26, 0.95, color), stroke="#350006", stroke_width=2,
                      layer_tracks=tracks)


def make_plan(entry):
    ident, title, text, family, kind = entry
    font = BRIC
    size = 122
    reveal_end = 46 if kind in ("mono_block", "word") else 56
    if kind == "correction":
        main_start, reveal_end = 44, 94
    elif kind == "mistake_placeholder":
        main_start, reveal_end = 0, 1
    elif kind == "scramble":
        main_start, reveal_end = 20, 58
    elif kind == "wrap":
        main_start, reveal_end = 0, 56
    else:
        main_start = 0
    main_text = text
    main_font = font
    main_size = size
    main_box = (1740, 430)
    main_pos = (960, 540)
    background = None
    layers = [{"id": "background", "type": "color", "color": [.018, .025, .04, 1.0],
               "size": [W, H], "start_frame": 0, "duration_frames": FRAMES}]
    unit = "word" if kind == "word" else "glyph"
    shape = "smooth" if kind == "soft" else "square"
    extra_main = []
    overlay_specs = []

    if kind == "scramble":
        rng = random.Random(20261006)
        # Swap only same-advance numeric glyphs: the matrix characters occupy
        # exactly the final title's glyph positions while keeping the cursor
        # frontier and all separators geometrically synchronized.
        same_advance_digit = {"0": "6", "6": "0", "4": "8", "8": "4"}
        for index in range(4):
            digit_index = 0
            scrambled = []
            for char in text:
                if char.isdigit():
                    swap = (digit_index + index) % 2 == 0
                    scrambled.append(same_advance_digit.get(char, char) if swap else char)
                    digit_index += 1
                else:
                    scrambled.append(char)
            scramble_text = "".join(scrambled)
            overlay_specs.append((f"scramble_{index+1}", scramble_text, font, size,
                                 "#55F3C1", 0, 5 + index * 5, "glyph"))
    elif kind == "correction":
        wrong = "1998 → 2025"
        mistake_layer = text_layer("intentional_mistake", wrong, size=size, fill="#AAB4C2",
                                   box=main_box,
                                   layer_tracks=[layer_track("opacity", [(0, 0), (5, 1), (40, 1), (41, 0), (FRAMES-1, 0)])],
                                   text_animators=[type_on_mask(wrong, 5, 35, "glyph", ident="mistake_type_on")])
        # The overlay must sit above the final corrected title; its opacity
        # envelope makes it disappear before the correct reveal begins.
        layers.append(mistake_layer)
    elif kind == "bounce":
        for i in range(reveal_units(text, "glyph")):
            first = i / reveal_units(text, "glyph")
            last = (i + 1) / reveal_units(text, "glyph")
            start, finish = round(4 + i * 2.25), round(4 + i * 2.25) + 4
            extra_main.append({"id": f"bounce_{i}", "selectors": [
                {"id": f"bounce_selector_{i}", "unit": "glyph", "shape": "square", "order": "forward",
                 "combine": "replace", "exclude_spaces": False,
                 "start": {"easing": "linear", "keyframes": [{"frame": 0, "value": first*100}, {"frame": FRAMES-1, "value": first*100}]},
                 "end": {"easing": "linear", "keyframes": [{"frame": 0, "value": last*100}, {"frame": FRAMES-1, "value": last*100}]}}],
                "properties": [sampled_track("scale", [(0, .01), (start, 1.15), (finish, 1.0), (FRAMES-1, 1.0)], "out_back")]})
    elif kind == "beam":
        overlay_specs.append(("glow_beam", text, font, size, "#FF4650", 0, reveal_end, "glyph"))
    elif kind == "highlight":
        marker_text = "█" * 20
        layers.append(text_layer("marker_box", marker_text, BRIC, 22, "#F7B53B",
                                 (960, 590), (800, 54), text_animators=[type_on_mask(marker_text, 0, reveal_end, "glyph", ident="marker_on")]))
    elif kind == "weight":
        main_font = BRIC
        overlay_specs.append(("bold_weight_ramp", text, BRIC, size, WHITE, 0, reveal_end, "glyph"))
    elif kind == "wrap":
        main_text = "18 MAY\n2026"
        main_box = (1120, 520)
        main_pos = (960, 540)
    elif kind == "glitch":
        overlay_specs.extend([("rgb_cyan", text, font, size, "#30DFFF", 0, 4, "glyph"),
                              ("rgb_red", text, font, size, "#FF3344", 0, 4, "glyph")])
    elif kind == "punch":
        for i in range(reveal_units(text, "glyph")):
            first = i / reveal_units(text, "glyph")
            last = (i + 1) / reveal_units(text, "glyph")
            born = round(i * 2.1)
            extra_main.append({"id": f"punch_{i}", "selectors": [
                {"id": f"punch_selector_{i}", "unit": "glyph", "shape": "square", "order": "forward",
                 "combine": "replace", "exclude_spaces": False,
                 "start": {"easing": "linear", "keyframes": [{"frame": 0, "value": first*100}, {"frame": FRAMES-1, "value": first*100}]},
                 "end": {"easing": "linear", "keyframes": [{"frame": 0, "value": last*100}, {"frame": FRAMES-1, "value": last*100}]}}],
                "properties": [sampled_track("scale", [(0, 1.05), (born+2, 1.0), (FRAMES-1, 1.0)], "out_back"),
                               sampled_track("position_y", [(0, (i % 3 - 1) * 1.25), (born+2, 0.0), (FRAMES-1, 0.0)], "out_back")]})

    main_animators = extra_main + [type_on_mask(main_text, main_start, reveal_end, unit, shape)]
    if kind == "soft":
        main_animators = [type_on_mask(main_text, 0, reveal_end, "glyph", "square")]
    if kind == "blur":
        main_animators = [type_on_mask(main_text, 0, reveal_end, "glyph", "square"),
                          {"id": "focus_resolve", "selectors": [
                              {"id": "all_glyphs", "unit": "glyph", "shape": "square", "order": "forward",
                               "combine": "replace", "exclude_spaces": False,
                               "start": {"easing": "linear", "keyframes": [{"frame": 0, "value": 0}, {"frame": FRAMES-1, "value": 0}]},
                               "end": {"easing": "linear", "keyframes": [{"frame": 0, "value": 100}]}}],
                           "properties": [sampled_track("blur", [(0, 15), (5, 0), (FRAMES-1, 0)], "out_cubic")] }]

    top_overlays = []
    for layer_id, layer_text_value, layer_font, layer_size, color, start, end, layer_unit in overlay_specs:
        effect = None
        offset_x = 0.0
        tracks = []
        if layer_id.startswith("scramble_"):
            index = int(layer_id.split("_")[1])
            onset = main_start + start
            finish = main_start + end
            fade = min(FRAMES - 1, finish + 8 + index * 3)
            tracks = [layer_track("opacity", [(0, .0), (onset, .0),
                                                (min(onset + 1, FRAMES - 1), .85),
                                                (max(onset + 1, finish - 1), .85), (fade, .0),
                                                (FRAMES - 1, .0)])]
        elif layer_id == "glow_beam":
            effect = (58, 1.5, "#FF1828")
            tracks = [layer_track("opacity", [(0, .0), (start, .0), (start + 4, .9),
                                                (end - 2, .9), (end + 6, .0), (FRAMES - 1, .0)])]
        elif layer_id.startswith("rgb_"):
            offset_x = -7.0 if layer_id.endswith("cyan") else 7.0
            flicker = [(0, 0.0), (start, 0.0), (start + 1, .9), (start + 2, .0),
                       (end, .0), (end + 1, 0.0)]
            for burst in (18, 36, 52):
                if start < burst < end:
                    flicker.extend([(burst - 1, .0), (burst, .9), (burst + 1, .9), (burst + 2, .0)])
            flicker.append((FRAMES - 1, .0))
            tracks = [layer_track("opacity", flicker),
                      layer_track("position_x", [(0, offset_x), (FRAMES - 1, offset_x)])]
        elif layer_id == "bold_weight_ramp":
            tracks = [layer_track("opacity", [(0, .0), (start, .0), (end, 1.0), (FRAMES - 1, 1.0)])]
        # Every text overlay follows the exact main glyph-release schedule;
        # effect opacity/flicker may decorate typed glyphs but cannot reveal
        # future ones ahead of the cursor.
        overlay = text_layer(layer_id, layer_text_value, layer_font, layer_size, color,
                             box=main_box, glow=effect,
                             layer_tracks=tracks,
                             text_animators=[type_on_mask(layer_text_value, start, end,
                                                          layer_unit, ident=f"{layer_id}_gate")])
        if offset_x or layer_id in ("glow_beam", "bold_weight_ramp"):
            top_overlays.append(overlay)
        else:
            layers.append(overlay)

    correction_overlay = next((layer for layer in layers if layer["id"] == "intentional_mistake"), None)
    if correction_overlay is not None:
        layers.remove(correction_overlay)
    main_layer_tracks = None
    if kind == "correction":
        # Keep the corrected source hidden until the mistaken copy has been erased.
        main_layer_tracks = [layer_track("opacity", [(0, 0.0), (43, 0.0), (44, 1.0),
                                                       (FRAMES - 1, 1.0)])]
    layers.append(text_layer("date_or_value", main_text, main_font, main_size, WHITE,
                             pos=main_pos, box=main_box, layer_tracks=main_layer_tracks,
                             text_animators=main_animators))
    layers.extend(top_overlays)
    if correction_overlay is not None:
        layers.append(correction_overlay)
    cursor_start = main_start
    cursor_unit = unit
    cursor_duration = reveal_end - main_start
    layers.append(cursor_layer(main_text, main_font, main_size, cursor_duration,
                               glyph="I",
                               spring=kind == "spring", start_frame=cursor_start,
                               unit=cursor_unit))
    plan = {"schema": "chronon.render-plan.v2", "version": 2,
            "job_id": "typewriter_modern_" + ident,
            "canvas": {"width": W, "height": H, "fps_num": FPS, "fps_den": 1, "duration_frames": FRAMES},
            "layers": layers,
            "output": {"path": ident + ".mp4", "format": "mp4", "codec": "h264"}}
    return plan


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    entries = []
    for item in STYLES:
        plan = make_plan(item)
        (OUT / (item[0] + ".plan.json")).write_text(json.dumps(plan, ensure_ascii=False, indent=2) + "\n")
        runtime_effect = {
            "mono_block": "monospace_block_cursor", "scramble": "kinetic_scramble",
            "soft": "soft_opacity_ramp", "bounce": "character_bounce",
            "correction": "backspace_correction", "beam": "glow_beam_sweep",
            "word": "word_snap", "yshift": "mechanical_y_shift",
            "highlight": "highlighter_expansion", "weight": "weight_ramp",
            "wrap": "dynamic_auto_wrap", "glitch": "glitch_pop",
            "spring": "elastic_leading_cursor", "blur": "focal_blur_dissolve",
            "punch": "paper_punch_stencil",
        }[item[4]]
        runtime_motion_id = f"typewriter_modern_{item[0][:2]}_{runtime_effect}"
        entries.append({"id": item[0], "name": item[1], "display_text": item[2], "family": item[3],
                        "runtime_motion_id": runtime_motion_id,
                        "effect": item[4], "plan": item[0] + ".plan.json", "output": item[0] + ".mp4",
                        "status": "generated"})
    manifest = {"schema": "chronontemplate.typewriter-modern-previews.v1",
                "description": "15 modern typewriter styles with cursor-synchronized date/number reveals.",
                "canvas": {"width": W, "height": H, "fps": FPS, "duration_seconds": 5},
                "drive_parent_folder_id": "1ddGa7OvaDEnGGbBIrH-ZtFhNPNcrt68H",
                "drive_parent_folder_url": "https://drive.google.com/drive/u/1/folders/1ddGa7OvaDEnGGbBIrH-ZtFhNPNcrt68H",
                "animations": entries}
    (OUT / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
    print(f"Generated {len(entries)} synchronized plans in {OUT}")


if __name__ == "__main__":
    main()
