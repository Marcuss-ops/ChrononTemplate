#!/usr/bin/env python3
"""Build a ten-style typewriter showcase with progressively richer cursors.

The motion and reveal timing come from ChrononTemplate's native phrase pack.
This projection only selects the ten best family members and styles their
separate cursor layer, keeping all animation authored in Chronon render plans.
"""

from __future__ import annotations

import json
from pathlib import Path

from PIL import ImageFont

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "out/typewriter_3d_underscore"
OUT = ROOT / "out/typewriter_cursor_family_v1"

# Ordered from a quiet, familiar caret to richer terminal and glow treatments.
# Each row reuses a distinct Chronon-authored typing rhythm and changes the
# native cursor shape, preserving the five-second 1920x1080 source design.
STYLES = [
    ("01_caret_clean", "tw3d_01_classic_linear", "rounded_rect", [12, 62], [0, 4], [0.96, 0.98, 1.0, 1.0]),
    ("02_underscore", "tw3d_02_accelerando_burst", "rounded_rect", [54, 12], [0, 27], [0.96, 0.98, 1.0, 1.0]),
    ("03_block_caret", "tw3d_03_decelerando_impact", "rect", [18, 58], [0, 0], [0.96, 0.98, 1.0, 1.0]),
    ("04_soft_dot", "tw3d_04_word_staccato", "ellipse", [24, 24], [0, 21], [0.96, 0.98, 1.0, 1.0]),
    ("05_terminal_block", "tw3d_05_smooth_soft_wave", "rect", [28, 56], [0, 0], [0.96, 0.98, 1.0, 1.0]),
    ("06_round_block", "tw3d_06_drop_in_glyph", "rounded_rect", [22, 58], [0, 0], [0.96, 0.98, 1.0, 1.0]),
    ("07_focus_neon", "tw3d_07_scale_pop_glyph", "rounded_rect", [12, 66], [0, 1], [0.36, 0.90, 0.98, 1.0]),
    ("08_tracking_pill", "tw3d_08_tracking_expansion", "ellipse", [40, 20], [0, 21], [1.0, 0.78, 0.42, 1.0]),
    ("09_dual_block", "tw3d_09_terminal_rapid", "rect", [20, 60], [0, 0], [0.55, 0.91, 0.99, 1.0]),
    ("10_leading_glow", "tw3d_10_two_stage_phrase", "rounded_rect", [18, 68], [0, 1], [0.45, 0.96, 0.69, 1.0]),
]


def build_cursor_track(text_layer: dict) -> list[dict]:
    """Follow the exact selector interval using Poppins glyph advances."""
    selector = text_layer["text_animators"][0]["selectors"][0]
    start_keys = selector["start"]["keyframes"]
    start_frame, end_frame = start_keys[0]["frame"], start_keys[-1]["frame"]
    content = text_layer["text"]
    font_path = ROOT.parent / "Chronon3d/assets/fonts/Poppins-Bold.ttf"
    font = ImageFont.truetype(str(font_path), round(text_layer["style"]["font_size"]))
    glyph_ends = []
    for index, char in enumerate(content):
        if not char.isspace():
            glyph_ends.append(font.getlength(content[:index + 1]))
    if not glyph_ends:
        return []
    full_width = font.getlength(content)
    output = []
    for frame in range(150):
        progress = min(1.0, max(0.0, (frame - start_frame) / (end_frame - start_frame)))
        glyph_progress = progress * len(glyph_ends)
        whole = min(len(glyph_ends) - 1, int(glyph_progress))
        fraction = glyph_progress - int(glyph_progress)
        if progress >= 1.0:
            offset = full_width * 0.5
        elif glyph_progress <= 0:
            offset = -full_width * 0.5
        else:
            previous = glyph_ends[whole - 1] if whole > 0 else 0.0
            current = glyph_ends[whole]
            offset = previous + (current - previous) * fraction - full_width * 0.5
        text_drift = 0.0
        for track in text_layer.get("animation", {}).get("tracks", []):
            if track.get("property") == "position_x":
                keys = track["keyframes"]
                for left, right in zip(keys, keys[1:]):
                    if left["frame"] <= frame <= right["frame"]:
                        span = right["frame"] - left["frame"]
                        ratio = 0 if span == 0 else (frame - left["frame"]) / span
                        text_drift = left["value"] + (right["value"] - left["value"]) * ratio
                        break
                else:
                    text_drift = keys[0]["value"] if frame < keys[0]["frame"] else keys[-1]["value"]
        output.append({"frame": frame, "value": round(offset + text_drift, 2)})
    return output


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    manifest = []
    for output_name, source_id, shape, size, offset, fill in STYLES:
        source_path = SOURCE / f"{source_id}.plan.json"
        plan = json.loads(source_path.read_text())
        cursor = next((layer for layer in plan["layers"] if layer["id"] == "cursor_underscore"), None)
        if cursor is None:
            raise SystemExit(f"{source_path} has no native cursor layer")
        text_layer = next(layer for layer in plan["layers"] if layer["type"] == "text")
        cursor["id"] = "typewriter_cursor"
        cursor["shape"]["type"] = shape
        cursor["shape"]["fill"] = fill
        if shape in {"rounded_rect", "rect"}:
            cursor["shape"].pop("radius", None)
            if shape == "rounded_rect":
                cursor["shape"]["radius"] = 2.0
        cursor["size"] = size
        cursor["position"] = [960.0, 540.0 + offset[1]]
        cursor.pop("rotation", None)
        cursor.pop("enable_3d", None)
        # Keep the caret continuously visible. The source pack contains a
        # periodic opacity blink, including frames where it stays hidden for
        # the rest of the clip; the cursor should track typing and then remain
        # parked at the end of the completed phrase.
        cursor_animation = cursor.setdefault("animation", {}).setdefault("tracks", [])
        cursor_animation[:] = [track for track in cursor_animation if track.get("property") != "opacity"]
        cursor_animation[:] = [track for track in cursor_animation if track.get("property") != "position_x"]
        cursor_animation.append({"property": "position_x", "easing": "linear", "keyframes": build_cursor_track(text_layer)})
        for key in ("rotation_x", "rotation_y", "rotation_z", "position_z"):
            for track in cursor.get("animation", {}).get("tracks", []):
                if track.get("property") == key:
                    cursor["animation"]["tracks"].remove(track)
        for layer in plan["layers"]:
            if layer["type"] == "text":
                layer["enable_3d"] = False
                layer.pop("rotation", None)
                if len(layer.get("position", [])) > 2:
                    layer["position"] = layer["position"][:2]
                for track in layer.get("animation", {}).get("tracks", []):
                    if track.get("property") in {"rotation_x", "rotation_y", "rotation_z", "position_z"}:
                        layer["animation"]["tracks"].remove(track)
                if layer.get("id") != "typewriter_cursor":
                    layer.get("style", {}).get("glow", {}).update({"radius": 14.0, "intensity": 0.24})
                for animator in layer.get("text_animators", []):
                    for selector in animator.get("selectors", []):
                        # Current Chronon v3 tracks infer their property from
                        # the selector field; the older pack plans serialized
                        # this redundant key and the current schema rejects it.
                        for boundary in ("start", "end"):
                            selector.get(boundary, {}).pop("property", None)
                            if boundary in selector:
                                selector[boundary]["easing"] = "linear"
                    for property_track in animator.get("properties", []):
                        property_track["easing"] = "linear"
        plan["job_id"] = f"chronontemplate_{output_name}"
        plan["output"]["path"] = f"{output_name}.mp4"
        target = OUT / f"{output_name}.plan.json"
        target.write_text(json.dumps(plan, indent=2, ensure_ascii=False) + "\n")
        manifest.append({
            "id": output_name,
            "source_motion": source_id,
            "cursor": {"shape": shape, "size": size, "fill": fill},
            "plan": target.name,
            "output": f"{output_name}.mp4",
        })
    (OUT / "manifest.json").write_text(json.dumps({
        "family": "typewriter_cursor_v1",
        "ordering": "simple_to_advanced",
        "canvas": {"width": 1920, "height": 1080, "fps": 30, "duration_seconds": 5},
        "motion_source": "ChrononTemplate TypewriterPhrasePack",
        "motions": manifest,
    }, indent=2, ensure_ascii=False) + "\n")
    print(f"prepared {len(manifest)} typewriter cursor plans in {OUT}")


if __name__ == "__main__":
    main()
