#!/usr/bin/env python3
"""Author the Editorial Visual Motion V1 catalog families.

This script is the single committed writer of the V1 milestone motion
vocabulary added on top of the hand-authored catalog:

    entity_caption_v1   6 shared legacy-safe text motions
    trump_entity_text_v1 15 premium Trump entity-name motions
    editorial_image_v1  14 editorial image motions
    text_3d_v1          10 premium text 2.5D/3D motions
    web                  +2 web focus motions (cursor focus, section spotlight)

It is idempotent: missing motions are inserted, authored changes replace their
matching catalog rows, and the result is validated against the same rules the
C++ emitter enforces (resting entrances, neutral 3D resting poses, keyframe
monotonicity). Re-running after a catalog refresh is a no-op.

Usage:
    tools/author_editorial_motions.py            apply the V1 families
    tools/author_editorial_motions.py --check    exit 1 if anything is missing
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

CATALOG = Path(__file__).resolve().parents[1] / "catalog/motion_catalog.v1.json"

CAMERA_BACKED = {"position_z", "rotation_x", "rotation_y"}
REMOVED_MOTION_IDS = {
    "text_3d_character_wave", "text_3d_depth_float", "text_3d_depth_push",
    "text_3d_glyph_depth_wave", "text_3d_word_yaw_cascade",
    "entity_caption_blur_reveal", "entity_caption_tracking_snap",
    "entity_caption_word_spring", "entity_caption_glyph_rise",
    "entity_caption_side_glide", "entity_caption_warm_reveal",
    "entity_caption_flip_settle", "entity_caption_word_drop",
    "entity_caption_focus_punch", "entity_caption_neon_breathe",
}


def track(prop, keys, easing="out_cubic"):
    return {"property": prop, "keyframes": [{"frame": f, "value": v} for f, v in keys], "easing": easing}


def animator(aid, kind, props, stagger=2, order="forward"):
    return {"id": aid, "selector": {"kind": kind, "shape": "square", "order": order, "stagger": stagger},
            "properties": props}


def validate_motion(m: dict) -> None:
    """The emitter's fail-closed rules, restated so bad data fails here first."""
    seen = -1
    for t in m.get("tracks", []):
        frames = [k["frame"] for k in t["keyframes"]]
        if frames[0] != 0 or any(b <= a for a, b in zip(frames, frames[1:])):
            raise SystemExit(f"{m['id']}: track {t['property']} keyframes must start at 0 and increase")
        if t["property"] in ("scale", "opacity") and t["keyframes"][-1]["value"] != 1:
            raise SystemExit(f"{m['id']}: {t['property']} must rest at 1")
        if t["property"] in CAMERA_BACKED and t["keyframes"][-1]["value"] != 0:
            raise SystemExit(f"{m['id']}: {t['property']} must rest at the neutral 0")
        seen = max(seen, frames[-1])
    requires_3d = any(t["property"] in CAMERA_BACKED for t in m.get("tracks", []))
    requires_3d = requires_3d or any(
        t["property"] in CAMERA_BACKED
        for a in m.get("text_animators", []) for t in a.get("properties", []))
    if bool(m.get("requires_3d", False)) != requires_3d:
        raise SystemExit(f"{m['id']}: requires_3d must match its camera-backed tracks")
    if m.get("enter", 0) <= 0 or seen > 400:
        raise SystemExit(f"{m['id']}: implausible enter/track extent")


def editorial_image(mid, enter, tracks, *, bounds=(40, 240)):
    m = {"id": mid, "category": "editorial_image_v1", "targets": ["image"], "unit": "layer",
         "enter": enter, "exit": 12, "tracks": tracks,
         "duration_bounds": {"minimum_frames": bounds[0], "maximum_frames": bounds[1]},
         "render_safe": True}
    if any(t["property"] in CAMERA_BACKED for t in tracks):
        m["requires_3d"] = True
    return m


def text_3d(mid, unit, enter, tracks, animators=None):
    # Tighten the whole entrance by 15% while keeping all authored holds,
    # fades, and transforms synchronized on the same frame grid.
    enter = max(1, round(enter * 0.85))
    tracks = [
        {**t, "keyframes": [
            {**k, "frame": round(k["frame"] * 0.85)} for k in t["keyframes"]
        ]}
        for t in tracks
    ]
    m = {"id": mid, "category": "text_3d_v1", "targets": ["text"], "unit": unit,
         "enter": enter, "tracks": tracks,
         "duration_bounds": {"minimum_frames": 30, "maximum_frames": 240},
         "render_safe": True, "requires_3d": True}
    if animators is not None:
        m["text_animators"] = animators
    return m


def web(mid, enter, tracks):
    return {"id": mid, "category": "web", "targets": ["image", "web"], "unit": "layer",
            "enter": enter, "exit": 12, "supported_content": ["browser"],
            "duration_bounds": {"minimum_frames": 40, "maximum_frames": 240},
            "required_properties": [t["property"] for t in tracks],
            "render_safe": True, "requires_3d": True, "requires_camera": True,
            "tracks": tracks}


IMAGE_MOTIONS = [
    editorial_image("image_collage_scatter", 54, [
        track("position_x", [(0, 90), (54, 0)]),
        track("position_y", [(0, -70), (54, 0)]),
        track("rotation_z", [(0, -5), (54, 0)], "in_out_cubic"),
        track("rotation_y", [(0, 12), (54, 0)], "in_out_cubic"),
        track("opacity", [(0, 0), (20, 1), (54, 1)])]),
    editorial_image("image_card_flip", 52, [
        track("rotation_y", [(0, -90), (52, 0)], "in_out_cubic"),
        track("position_z", [(0, 240), (52, 0)]),
        track("opacity", [(0, 0), (16, 1), (52, 1)])]),
    editorial_image("image_depth_cascade", 58, [
        track("position_z", [(0, 500), (58, 0)], "in_out_sine"),
        track("rotation_x", [(0, 10), (58, 0)], "in_out_sine"),
        track("opacity", [(0, 0), (26, 1), (58, 1)])]),
    editorial_image("image_depth_dolly", 52, [
        track("position_z", [(0, 420), (52, 0)], "in_out_sine"),
        track("scale", [(0, 1.08), (52, 1.0)], "in_out_sine"),
        track("opacity", [(0, 0), (24, 1), (52, 1)])]),
    editorial_image("image_document_push", 48, [
        track("position_z", [(0, -240), (48, 0)], "in_out_sine"),
        track("scale", [(0, 1.06), (48, 1.0)]),
        track("opacity", [(0, 0), (20, 1), (48, 1)])]),
    editorial_image("image_evidence_focus", 46, [
        track("scale", [(0, 1.18), (46, 1.0)], "in_out_cubic"),
        track("position_z", [(0, 100), (46, 0)]),
        track("opacity", [(0, 0.5), (46, 1.0)])]),
    editorial_image("image_float_settle", 50, [
        track("position_y", [(0, 36), (50, 0)], "in_out_sine"),
        track("position_z", [(0, 60), (50, 0)], "in_out_sine"),
        track("opacity", [(0, 0), (22, 1), (50, 1)])]),
    editorial_image("image_focus_push", 44, [
        track("scale", [(0, 1.12), (44, 1.0)]),
        track("position_z", [(0, -80), (44, 0)]),
        track("opacity", [(0, 0.4), (44, 1.0)])]),
    editorial_image("image_orbit_enter", 54, [
        track("rotation_y", [(0, 22), (54, 0)], "in_out_cubic"),
        track("rotation_x", [(0, 8), (54, 0)], "in_out_cubic"),
        track("position_z", [(0, 180), (54, 0)]),
        track("opacity", [(0, 0), (22, 1), (54, 1)])]),
    editorial_image("image_perspective_stack", 56, [
        track("rotation_x", [(0, 14), (56, 0)], "in_out_cubic"),
        track("position_z", [(0, 320), (56, 0)]),
        track("scale", [(0, 0.94), (56, 1.0)]),
        track("opacity", [(0, 0), (24, 1), (56, 1)])]),
    editorial_image("image_photo_drop", 44, [
        track("position_y", [(0, -160), (44, 0)]),
        track("rotation_z", [(0, 4), (44, 0)]),
        track("opacity", [(0, 0), (12, 1), (44, 1)])]),
    editorial_image("image_roll_in", 46, [
        track("position_x", [(0, -120), (46, 0)]),
        track("rotation_z", [(0, -8), (46, 0)]),
        track("opacity", [(0, 0), (18, 1), (46, 1)])]),
    editorial_image("image_tilt_parallax", 48, [
        track("rotation_x", [(0, -12), (48, 0)], "in_out_cubic"),
        track("position_y", [(0, 24), (48, 0)]),
        track("opacity", [(0, 0), (20, 1), (48, 1)])]),
    editorial_image("image_yaw_reveal", 50, [
        track("rotation_y", [(0, -38), (50, 0)], "in_out_cubic"),
        track("position_z", [(0, 200), (50, 0)]),
        track("opacity", [(0, 0), (20, 1), (50, 1)])]),
]

TEXT_3D_MOTIONS = [
    text_3d("text_3d_camera_push", "layer", 46, [
        track("position_z", [(0, 54), (46, 0)], "in_out_sine"),
        track("rotation_x", [(0, 7), (46, 0)], "in_out_cubic"),
        track("rotation_y", [(0, -10), (46, 0)], "in_out_cubic"),
        track("scale", [(0, 0.975), (46, 1.0)], "in_out_sine"),
        track("opacity", [(0, 0), (28, 1), (46, 1)])]),
    text_3d("text_3d_perspective_drop", "layer", 48, [
        track("rotation_x", [(0, -9), (48, 0)], "in_out_cubic"),
        track("rotation_y", [(0, 7), (48, 0)], "in_out_cubic"),
        track("position_y", [(0, -14), (48, 0)]),
        track("position_z", [(0, 44), (48, 0)], "out_cubic"),
        track("opacity", [(0, 0), (28, 1), (48, 1)])]),
    text_3d("text_3d_roll_depth", "layer", 46, [
        track("rotation_z", [(0, -2), (46, 0)], "in_out_cubic"),
        track("rotation_x", [(0, 7), (46, 0)], "in_out_cubic"),
        track("rotation_y", [(0, -8), (46, 0)], "in_out_cubic"),
        track("position_z", [(0, 36), (46, 0)], "in_out_sine"),
        track("opacity", [(0, 0), (28, 1), (46, 1)])]),
    text_3d("text_3d_tilt_rise", "layer", 46, [
        track("rotation_x", [(0, 8), (46, 0)], "in_out_cubic"),
        track("rotation_y", [(0, -6), (46, 0)], "in_out_cubic"),
        track("position_y", [(0, 12), (46, 0)]),
        track("position_z", [(0, 26), (46, 0)], "out_cubic"),
        track("opacity", [(0, 0), (28, 1), (46, 1)])]),
    text_3d("text_3d_word_cascade", "layer", 52, [
        track("position_y", [(0, 14), (52, 0)]),
        track("position_z", [(0, 38), (52, 0)], "out_cubic"),
        track("rotation_y", [(0, -8), (52, 0)], "in_out_cubic"),
        track("rotation_x", [(0, 6), (52, 0)], "in_out_cubic"),
        track("opacity", [(0, 0), (30, 1), (52, 1)])]),
    text_3d("text_3d_yaw_flip_in", "layer", 46, [
        track("rotation_y", [(0, -14), (46, 0)], "in_out_cubic"),
        track("rotation_x", [(0, 7), (46, 0)], "in_out_cubic"),
        track("position_z", [(0, 36), (46, 0)], "in_out_sine"),
        track("opacity", [(0, 0), (28, 1), (46, 1)])]),
    text_3d("text_3d_pitch_lift", "layer", 48, [
        track("rotation_x", [(0, 10), (48, 0)], "in_out_cubic"),
        track("rotation_y", [(0, -8), (48, 0)], "in_out_cubic"),
        track("position_y", [(0, 10), (48, 0)]),
        track("position_z", [(0, 32), (48, 0)], "out_cubic"),
        track("opacity", [(0, 0), (30, 1), (48, 1)])]),
    text_3d("text_3d_yaw_sweep", "layer", 48, [
        track("rotation_y", [(0, 12), (48, 0)], "in_out_cubic"),
        track("rotation_x", [(0, -6), (48, 0)], "in_out_cubic"),
        track("position_x", [(0, 34), (48, 0)]),
        track("position_z", [(0, 30), (48, 0)], "out_cubic"),
        track("opacity", [(0, 0), (30, 1), (48, 1)])]),
    text_3d("text_3d_double_axis_reveal", "layer", 48, [
        track("rotation_x", [(0, -9), (48, 0)], "in_out_cubic"),
        track("rotation_y", [(0, 11), (48, 0)], "in_out_cubic"),
        track("position_z", [(0, 46), (48, 0)], "in_out_sine"),
        track("opacity", [(0, 0), (30, 1), (48, 1)])]),
    text_3d("text_3d_orbit_lock", "layer", 50, [
        track("rotation_x", [(0, 9), (50, 0)], "in_out_cubic"),
        track("rotation_y", [(0, -12), (50, 0)], "in_out_cubic"),
        track("position_z", [(0, 52), (50, 0)], "in_out_sine"),
        track("opacity", [(0, 0), (30, 1), (50, 1)])]),
]

WEB_MOTIONS = [
    web("web_cursor_focus", 40, [
        track("position_z", [(0, 180), (40, 0)]),
        track("scale", [(0, 1.04), (40, 1.0)]),
        track("opacity", [(0, 0), (18, 1), (40, 1)])]),
    web("web_section_spotlight", 46, [
        track("position_z", [(0, 240), (46, 0)]),
        track("rotation_x", [(0, 10), (46, 0)]),
        track("opacity", [(0, 0), (20, 1), (46, 1)])]),
]

def caption_motion(mid, unit, enter, tracks, animators=None):
    m = {"id": mid, "category": "trump_entity_text_v1", "targets": ["text"],
         "unit": unit, "enter": enter, "tracks": tracks, "render_safe": True}
    if any(t["property"] in CAMERA_BACKED for t in tracks):
        m["requires_3d"] = True
    if animators is not None:
        m["text_animators"] = animators
    return m


CAPTION_MOTIONS = [
    caption_motion("trump_entity_text_01", "layer", 38, [
        track("position_x", [(0, 34), (38, 0)]), track("opacity", [(0, 0), (15, 1), (38, 1)])]),
    caption_motion("trump_entity_text_02", "layer", 40, [
        track("position_y", [(0, 24), (40, 0)]), track("opacity", [(0, 0), (16, 1), (40, 1)])]),
    caption_motion("trump_entity_text_03", "layer", 36, [
        track("scale", [(0, 0.90), (27, 1.015), (36, 1)], "out_cubic"),
        track("opacity", [(0, 0), (13, 1), (36, 1)])]),
    caption_motion("trump_entity_text_04", "layer", 42, [
        track("blur", [(0, 12), (24, 0), (42, 0)], "out_cubic"),
        track("opacity", [(0, 0), (14, 1), (42, 1)])]),
    caption_motion("trump_entity_text_05", "layer", 40, [
        track("rotation_z", [(0, -3), (40, 0)], "out_cubic"),
        track("position_y", [(0, 12), (40, 0)]), track("opacity", [(0, 0), (14, 1), (40, 1)])]),
    caption_motion("trump_entity_text_06", "layer", 42, [
        track("position_z", [(0, 48), (42, 0)], "in_out_sine"),
        track("rotation_y", [(0, -8), (42, 0)], "in_out_cubic"),
        track("opacity", [(0, 0), (18, 1), (42, 1)])]),
    caption_motion("trump_entity_text_07", "layer", 38, [
        track("position_x", [(0, -42), (38, 0)]), track("rotation_z", [(0, 2), (38, 0)]),
        track("opacity", [(0, 0), (14, 1), (38, 1)])]),
    caption_motion("trump_entity_text_08", "layer", 42, [
        track("rotation_y", [(0, 9), (42, 0)], "in_out_cubic"),
        track("position_z", [(0, 34), (42, 0)], "out_cubic"),
        track("opacity", [(0, 0), (17, 1), (42, 1)])]),
    caption_motion("trump_entity_text_09", "layer", 36, [
        track("scale_x", [(0, 0.76), (22, 1.02), (36, 1)]),
        track("opacity", [(0, 0), (12, 1), (36, 1)])]),
    caption_motion("trump_entity_text_10", "layer", 40, [
        track("position_x", [(0, 46), (40, 0)]), track("position_y", [(0, -12), (40, 0)]),
        track("opacity", [(0, 0), (16, 1), (40, 1)])]),
    caption_motion("trump_entity_text_11", "layer", 42, [
        track("rotation_x", [(0, -7), (42, 0)], "in_out_cubic"),
        track("position_y", [(0, 18), (42, 0)]), track("opacity", [(0, 0), (16, 1), (42, 1)])]),
    caption_motion("trump_entity_text_12", "layer", 38, [
        track("rotation_z", [(0, 4), (26, -1), (38, 0)], "in_out_cubic"),
        track("scale", [(0, 0.94), (38, 1)]), track("opacity", [(0, 0), (13, 1), (38, 1)])]),
    caption_motion("trump_entity_text_13", "layer", 44, [
        track("position_y", [(0, -22), (44, 0)]), track("position_z", [(0, 26), (44, 0)]),
        track("opacity", [(0, 0), (18, 1), (44, 1)])]),
    caption_motion("trump_entity_text_14", "layer", 40, [
        track("rotation_x", [(0, 5), (40, 0)], "in_out_cubic"),
        track("rotation_y", [(0, 7), (40, 0)], "in_out_cubic"),
        track("scale", [(0, 0.96), (40, 1)]), track("opacity", [(0, 0), (15, 1), (40, 1)])]),
    caption_motion("trump_entity_text_15", "layer", 42, [
        track("position_x", [(0, -25), (42, 0)]), track("position_z", [(0, 42), (42, 0)]),
        track("rotation_y", [(0, -6), (42, 0)], "in_out_cubic"),
        track("opacity", [(0, 0), (18, 1), (42, 1)])]),
]

CAPTION_MOTION_IDS = [
    "text_depth_in", "text_fade_up", "text_scale_punch",
    "text_word_rise", "text_word_stagger", "text_yaw_in",
] + [m["id"] for m in CAPTION_MOTIONS]


def expected_motions() -> list[dict]:
    motions = IMAGE_MOTIONS + TEXT_3D_MOTIONS + WEB_MOTIONS + CAPTION_MOTIONS
    for m in motions:
        validate_motion(m)
    return motions


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="verify without writing")
    args = parser.parse_args()

    doc = json.loads(CATALOG.read_text())
    existing = {m["id"]: m for m in doc["motions"]}

    expected = expected_motions()
    missing = [m for m in expected if m["id"] not in existing]
    stale = [m for m in expected if m["id"] in existing and existing[m["id"]] != m]
    removed = [mid for mid in sorted(REMOVED_MOTION_IDS) if mid in existing]
    missing_captions = [mid for mid in CAPTION_MOTION_IDS if mid not in existing]

    if args.check:
        if missing or stale or missing_captions or removed:
            for m in missing:
                print(f"missing: {m['id']}", file=sys.stderr)
            for m in stale:
                print(f"drifted: {m['id']}", file=sys.stderr)
            for mid in missing_captions:
                print(f"missing caption motion: {mid}", file=sys.stderr)
            for mid in removed:
                print(f"must be removed: {mid}", file=sys.stderr)
            return 1
        print(f"editorial V1 motions present and identical ({len(expected)} authored + 6 shared captions)")
        return 0

    if not missing and not stale and not missing_captions and not removed:
        print("nothing to do: all V1 motions already present")
        return 0

    raw = CATALOG.read_text()
    to_write = missing + stale
    if removed:
        doc["motions"] = [m for m in doc["motions"] if m["id"] not in REMOVED_MOTION_IDS]
        raw = json.dumps(doc, indent=2, ensure_ascii=False) + "\n"
    if missing:
        # Insert each motion before the first motion that sorts after it, so
        # the file keeps its alphabetical-by-id layout.
        for m in missing:
            ids = sorted(x["id"] for x in doc["motions"])
            following = next((i for i in ids if i > m["id"]), None)
            marker = ('    {\n      "id": "%s",' % following) if following else None
            if marker and raw.count(marker) == 1:
                raw = raw.replace(marker, block_for(m) + ",\n" + marker)
            else:
                raise SystemExit(f"no unique insertion anchor for {m['id']}")
    for m in stale:
        raw = replace_motion_block(raw, m)
    CATALOG.write_text(raw)

    # Re-verify from disk.
    check = json.loads(CATALOG.read_text())
    have = {m["id"]: m for m in check["motions"]}
    for m in expected:
        if have.get(m["id"]) != m:
            raise SystemExit(f"post-write verification failed for {m['id']}")
    print(f"applied: {[m['id'] for m in to_write]}")
    return 0


def block_for(m: dict) -> str:
    return "\n".join("    " + line for line in json.dumps(m, indent=2, ensure_ascii=False).split("\n"))


def replace_motion_block(raw: str, motion: dict) -> str:
    marker = '    {\n      "id": "%s",' % motion["id"]
    if raw.count(marker) != 1:
        raise SystemExit(f"no unique replacement block for {motion['id']}")
    start = raw.index(marker)
    depth = 0
    in_string = False
    escaped = False
    end = None
    for i in range(start, len(raw)):
        char = raw[i]
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            continue
        if char == '"':
            in_string = True
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                end = i + 1
                break
    if end is None:
        raise SystemExit(f"unterminated replacement block for {motion['id']}")
    return raw[:start] + block_for(motion) + raw[end:]


if __name__ == "__main__":
    raise SystemExit(main())
