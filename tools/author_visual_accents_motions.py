#!/usr/bin/env python3
"""Author the Visual Accents V1 catalog families.

Single committed writer of the four official V1 families:

    brush_v1       12 document traits + 11 phrase-ready path/stroke variants
    web_rect_v1    12 browser-card / UI-panel motions (2.5D rounded rect)
    paint_v1       12 area/matte reveal motions (field mask recipes)
    light_leak_v1  12 luminous overlay motions (screen/add light recipes)

Rules enforced here mirror the C++ emitter and the Go consumer:
  * idempotent — re-running after a catalog refresh is a no-op;
  * every layer track starts at frame 0 with strictly increasing frames;
  * scale/opacity entrances rest at exactly 1, positions/rotations at 0;
  * requires_3d matches the camera-backed tracks (z / rotation_x / rotation_y);
  * every motion carries the V1 registry metadata (targets, unit, bounds,
    render_safe).

Usage:
    tools/author_visual_accents_motions.py            apply the V1 families
    tools/author_visual_accents_motions.py --check    exit 1 if anything is missing
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

CATALOG = Path(__file__).resolve().parents[1] / "catalog/motion_catalog.v1.json"

CAMERA_BACKED = {"position_z", "rotation_x", "rotation_y"}

# The path kinds the RenderingGen brush lowerer syntrhesizes into LayerPath
# commands. Keep in sync with overlay/visual_accents_recipe.go.
BRUSH_PATH_KINDS = {
    "line", "ellipse", "check", "cross", "arrow",
    "scribble", "wave", "corner_marks", "double_line", "rounded_rect",
    "underline", "underline_double", "underline_wave",
}


def track(prop, keys, easing="out_cubic"):
    return {"property": prop,
            "keyframes": [{"frame": f, "value": v} for f, v in keys],
            "easing": easing}


def layer_motion(mid, category, enter, tracks, *, targets=None, exit_=10,
                 bounds=(30, 240), unit="layer", recipe=None, requires_3d=None,
                 supported_content=None):
    for t in tracks:
        frames = [k["frame"] for k in t["keyframes"]]
        if frames[0] != 0 or any(b <= a for a, b in zip(frames, frames[1:])):
            raise SystemExit(f"{mid}: track {t['property']} keyframes must start at 0 and increase")
        if t["property"] in ("scale", "opacity") and t["keyframes"][-1]["value"] != 1:
            raise SystemExit(f"{mid}: {t['property']} must rest at 1")
        if t["property"] in CAMERA_BACKED and t["keyframes"][-1]["value"] != 0:
            raise SystemExit(f"{mid}: {t['property']} must rest at the neutral 0")
    has3d = any(t["property"] in CAMERA_BACKED for t in tracks)
    if requires_3d is None:
        requires_3d = has3d
    if bool(requires_3d) != has3d:
        raise SystemExit(f"{mid}: requires_3d={requires_3d} does not match camera-backed tracks ({has3d})")
    seen = max(k["frame"] for t in tracks for k in t["keyframes"])
    if enter <= 0 or seen > 400 or seen > bounds[1]:
        raise SystemExit(f"{mid}: implausible enter/track extent")
    motion = {
        "id": mid, "category": category,
        "targets": targets or ["image"], "unit": unit,
        "duration_bounds": {"minimum_frames": bounds[0], "maximum_frames": bounds[1]},
        "render_safe": True,
        "requires_3d": bool(requires_3d),
        "requires_camera": bool(requires_3d),
        "enter": enter, "exit": exit_,
        "tracks": tracks,
    }
    if supported_content:
        motion["supported_content"] = supported_content
    if recipe:
        motion["image_recipe"] = recipe
    return motion


# ── shared recipe builders ───────────────────────────────────────────────────


def path_component(cid, path_kind, stroke, trim=None, opacity=None,
                   placement="after_image"):
    if path_kind not in BRUSH_PATH_KINDS:
        raise SystemExit(f"{cid}: unsupported brush path_kind {path_kind}")
    component = {
        "id": cid, "type": "shape", "shape": "path", "path_kind": path_kind,
        "sync_transform": True, "placement": placement,
        "stroke": stroke,
    }
    if trim:
        component["trim"] = trim
    if opacity is not None:
        component["opacity"] = opacity
    return component


def trim_op(enter, hold=12):
    # Trim keyframes are [start, end] pairs over the path parameter — the
    # stroke draws from 0% to 100% and holds.
    return {"start": 0.0, "end": 1.0,
            "animation": track("trim", [(0, [0.0, 0.0]), (enter, [0.0, 1.0]), (enter + hold, [0.0, 1.0])],
                               "in_out_quad")}


def rect_component(cid, radius_scale=1.0, fill=None, stroke=None, tracks=None,
                   gradient=None, shadow=False, sync=True, size_scale=None,
                   opacity=None, placement="before_image", effects=None):
    component = {
        "id": cid, "type": "shape", "shape": "rounded_rect",
        "radius_scale": radius_scale, "sync_transform": sync,
        "placement": placement,
    }
    if fill:
        component["fill"] = fill
    if stroke:
        component["stroke"] = stroke
    if gradient:
        component["gradient"] = gradient
    if tracks:
        component["tracks"] = tracks
    if size_scale:
        component["size_scale"] = size_scale
    if opacity is not None:
        component["opacity"] = opacity
    if shadow:
        component["effects"] = [{"type": "drop_shadow", "offset": [0, 18],
                                 "radius": 32, "color": [0, 0, 0, 0.28]}]
    if effects:
        component["effects"] = effects
    return component


def glow_component(cid, color_rgba, tracks=None, opacity=1.0, size_scale=None,
                   placement="before_image", position_offset=None, effects=None):
    component = {
        "id": cid, "type": "shape", "shape": "ellipse",
        "sync_transform": False, "canvas_size": False,
        "placement": placement,
        "fill": color_rgba,
        "effects": effects or [{"type": "gaussian_blur", "radius": 128},
                               {"type": "glow", "radius": 96, "intensity": 0.6,
                                "color": [1.0, 0.8, 0.5, 1.0]}],
    }
    if tracks:
        component["tracks"] = tracks
    if opacity is not None:
        component["opacity"] = opacity
    if size_scale:
        component["size_scale"] = size_scale
    if position_offset:
        component["position_offset"] = position_offset
    return component


def field_mask(seed, frequency, progress_keys, generator="simplex", feather=40.0,
               operators=None, octaves=4, easing="in_out_sine"):
    field = {"generator": generator, "seed": seed, "frequency": frequency,
             "octaves": octaves}
    if operators:
        field["operators"] = operators
    return {
        "kind": "field",
        "generator": generator,
        "seed": seed,
        "feather": feather,
        "field": field,
        "progress": track("mask_progress", progress_keys, easing),
    }


# ── 1. BRUSH V1 — vector traits: path + stroke + trim ───────────────────────


def brush_motion(mid, enter, path_kind, stroke, hold=12):
    components = [path_component(f"{mid}_stroke", path_kind, stroke, trim=trim_op(enter, hold))]
    tracks = [track("opacity", [(0, 0), (6, 1)])]
    return layer_motion(mid, "brush_v1", enter, tracks,
                        targets=["image", "text", "shape"],
                        bounds=(20, 240),
                        recipe={"components": components})


def brush_family():
    marker = {"color": "#FACC15", "width": 56}
    ink = {"color": "#0F172A", "width": 5}
    chalk = {"color": "#F8FAFC", "width": 9}
    original = [
        brush_motion("brush_marker_highlight", 36, "line", marker),
        brush_motion("brush_dynamic_underline", 30, "line", ink),
        brush_motion("brush_circle_focus", 40, "ellipse", ink),
        brush_motion("brush_arrow_point", 36, "arrow", ink),
        brush_motion("brush_check_mark", 22, "check", ink, hold=8),
        brush_motion("brush_cross_out", 30, "cross", ink),
        brush_motion("brush_scribble_frame", 44, "rounded_rect", chalk),
        brush_motion("brush_double_underline", 38, "double_line", ink),
        brush_motion("brush_corner_accent", 28, "corner_marks", ink),
        brush_motion("brush_signature_sweep", 46, "wave", ink),
        brush_motion("brush_chalk_reveal", 44, "scribble", chalk),
        brush_motion("brush_pencil_circle", 40, "ellipse", ink),
    ]
    # Phrase variants adapted from the approved Brush reference examples.
    # Their strokes use bright ink so they remain legible on dark editorial
    # plates, while the original document-oriented Brush motions stay intact.
    phrase_specs = [
        ("brush_phrase_red_underline", "underline", {"color": "#E12636", "width": 12}, 34),
        ("brush_phrase_white_underline", "underline", {"color": "#F1F0EB", "width": 4}, 30),
        ("brush_phrase_lower_rule", "underline", {"color": "#E12636", "width": 6}, 32),
        ("brush_phrase_circle_focus", "ellipse", {"color": "#F1F0EB", "width": 5}, 40),
        ("brush_phrase_white_light_sweep", "underline_wave", {"color": "#E8E7E2", "width": 3}, 36),
        ("brush_phrase_arrow_point", "arrow", {"color": "#F1F0EB", "width": 4}, 36),
        ("brush_phrase_red_brush_underline", "underline_wave", {"color": "#E12636", "width": 15}, 42),
        ("brush_phrase_signature_flourish", "underline_wave", {"color": "#E8E7E2", "width": 3}, 42),
        ("brush_phrase_gold_marker", "line", {"color": "#D9A64E", "width": 28}, 34),
        ("brush_phrase_red_endpoint_rule", "underline", {"color": "#E12636", "width": 5}, 36),
        ("brush_phrase_white_double_underline", "underline_double", {"color": "#E8E7E2", "width": 3}, 40),
    ]
    variants = [brush_motion(mid, enter, path_kind, stroke) for mid, path_kind, stroke, enter in phrase_specs]
    return original + variants


# ── 2. WEB RECT V1 — browser cards and UI panels ────────────────────────────


def web_rect_family():
    border = {"color": "#E2E8F0", "width": 2}
    motions = []
    specs = [
        ("web_rect_scale_in", 36,
         [track("scale", [(0, 0.94), (36, 1)]), track("opacity", [(0, 0), (18, 1)])], False),
        ("web_rect_slide_up", 38,
         [track("position_y", [(0, 46), (38, 0)]), track("opacity", [(0, 0), (20, 1)])], False),
        ("web_rect_depth_push", 44,
         [track("position_z", [(0, -150), (44, 0)]), track("scale", [(0, 0.96), (44, 1)]),
          track("opacity", [(0, 0), (20, 1)])], True),
        ("web_rect_yaw_open", 44,
         [track("rotation_y", [(0, -15), (44, 0)]), track("opacity", [(0, 0), (18, 1)])], True),
        ("web_rect_tilt_settle", 42,
         [track("rotation_x", [(0, 6), (42, 0)]), track("rotation_y", [(0, -4), (42, 0)]),
          track("opacity", [(0, 0), (18, 1)])], True),
        ("web_rect_border_trace", 40,
         [track("opacity", [(0, 0), (10, 1)])], False),
        ("web_rect_mask_reveal", 40,
         [track("opacity", [(0, 0), (12, 1)])], False),
        ("web_rect_stack_fan", 46,
         [track("rotation_z", [(0, -4), (46, 0)]), track("opacity", [(0, 0), (18, 1)])], False),
        ("web_rect_grid_assemble", 46,
         [track("position_y", [(0, 30), (46, 0)]), track("scale", [(0, 0.97), (46, 1)]),
          track("opacity", [(0, 0), (20, 1)])], False),
        ("web_rect_focus_expand", 44,
         [track("scale", [(0, 0.94), (44, 1)]), track("opacity", [(0, 0), (18, 1)])], False),
        ("web_rect_section_zoom", 46,
         [track("scale", [(0, 1.06), (46, 1)]), track("opacity", [(0, 0), (14, 1)])], False),
        ("web_rect_split_panel", 44,
         [track("position_x", [(0, -24), (44, 0)]), track("opacity", [(0, 0), (18, 1)])], False),
    ]
    for mid, enter, tracks, r3d in specs:
        fade = max(enter - 6, 8)
        components = [
            rect_component("backdrop", fill=[1, 1, 1, 1], stroke=border, shadow=True,
                           tracks=[track("opacity", [(0, 0), (fade, 1)])]),
            rect_component("gloss", opacity=0.0,
                           gradient={"type": "linear",
                                     "color_stops": [
                                         {"position": 0.0, "color": [1, 1, 1, 0.5]},
                                         {"position": 1.0, "color": [1, 1, 1, 0.0]}],
                                     "start": [0, 0], "end": [0, 1]},
                           size_scale=[1.0, 0.5],
                           tracks=[track("opacity", [(0, 0), (fade, 1)])]),
        ]
        if mid == "web_rect_border_trace":
            components.append(path_component(
                "trace", "rounded_rect", {"color": "#38BDF8", "width": 3},
                trim=trim_op(enter)))
        if mid == "web_rect_mask_reveal":
            components.append(rect_component(
                "shade", fill=[0.06, 0.09, 0.16, 1.0],
                tracks=[track("opacity", [(0, 1), (enter, 0)])], sync=True))
        motions.append(layer_motion(mid, "web_rect_v1", enter, tracks,
                                    targets=["image"], bounds=(30, 240),
                                    requires_3d=r3d,
                                    recipe={"components": components}))
    return motions


# ── 3. PAINT V1 — organic area reveals through field masks ──────────────────


def paint_motion(mid, enter, mask):
    tracks = [track("opacity", [(0, 0), (8, 1)])]
    return layer_motion(mid, "paint_v1", enter, tracks,
                        targets=["image"], bounds=(30, 240),
                        recipe={"mask": mask})


def paint_family():
    return [
        paint_motion("paint_brush_wipe", 42,
                     field_mask(11, 2.5, [(0, 0.0), (42, 1.0), (60, 1.0)],
                                generator="perlin", feather=48,
                                operators=[{"kind": "warp", "amount": 0.35}])),
        paint_motion("paint_blob_reveal", 42,
                     field_mask(22, 3.5, [(0, 0.0), (42, 1.0), (60, 1.0)],
                                generator="simplex", feather=56)),
        paint_motion("paint_ink_spread", 46,
                     field_mask(33, 4.0, [(0, 0.0), (46, 1.0), (64, 1.0)],
                                generator="fractal", feather=40, octaves=5)),
        paint_motion("paint_dry_brush_reveal", 48,
                     field_mask(44, 5.0, [(0, 0.0), (48, 1.0), (66, 1.0)],
                                generator="fractal", feather=72, octaves=5)),
        paint_motion("paint_edge_crawl", 44,
                     field_mask(55, 3.0, [(0, 0.0), (44, 1.0), (60, 1.0)],
                                generator="stripes", feather=36,
                                operators=[{"kind": "smoothstep", "edge": 0.5, "softness": 0.3}])),
        paint_motion("paint_color_swipe", 40,
                     field_mask(66, 1.0, [(0, 0.0), (40, 1.0), (56, 1.0)],
                                generator="linear", feather=40,
                                operators=[{"kind": "warp", "amount": 0.25}])),
        paint_motion("paint_splash_focus", 34,
                     field_mask(77, 3.0, [(0, 0.0), (34, 1.0), (52, 1.0)],
                                generator="radial", feather=52)),
        paint_motion("paint_mask_morph", 46,
                     field_mask(88, 3.5, [(0, 0.0), (46, 1.0), (64, 1.0)],
                                generator="cellular", feather=44)),
        paint_motion("paint_duotone_overlay", 40,
                     field_mask(99, 3.0, [(0, 0.0), (40, 1.0), (56, 1.0)],
                                generator="perlin", feather=64)),
        paint_motion("paint_peel_reveal", 44,
                     field_mask(111, 1.5, [(0, 0.0), (44, 1.0), (60, 1.0)],
                                generator="linear", feather=30,
                                operators=[{"kind": "warp", "amount": 0.4}])),
        paint_motion("paint_wave_fill", 46,
                     field_mask(122, 3.0, [(0, 0.0), (46, 1.0), (64, 1.0)],
                                generator="rings", feather=48)),
        paint_motion("paint_multi_blob_merge", 50,
                     field_mask(133, 4.5, [(0, 0.0), (50, 1.0), (68, 1.0)],
                                generator="simplex", feather=44)),
    ]


# ── 4. LIGHT LEAK V1 — luminous overlays through screen/add light ───────────


def leak_motion(mid, enter, components, extra_tracks=None):
    tracks = extra_tracks or [track("opacity", [(0, 0), (10, 1)])]
    return layer_motion(mid, "light_leak_v1", enter, tracks,
                        targets=["image"], bounds=(30, 300),
                        recipe={"components": components})


def light_leak_family():
    warm = [1.0, 0.72, 0.35, 1.0]
    amber = [1.0, 0.82, 0.55, 1.0]
    cool = [0.62, 0.80, 1.0, 1.0]
    white = [1.0, 1.0, 1.0, 1.0]
    motions = []

    # edge_warm: a large soft glow enters from the left edge.
    motions.append(leak_motion("lightleak_edge_warm", 48, [
        glow_component("edge_glow", warm, size_scale=[0.55, 2.4], opacity=0.9,
                       tracks=[track("position_x", [(0, -700), (48, 0)], "out_cubic")]),
    ]))

    # corner_bloom: soft bloom anchored at the top-left corner.
    motions.append(leak_motion("lightleak_corner_bloom", 52, [
        glow_component("corner_glow", amber, size_scale=[1.6, 1.6], opacity=0.75,
                       position_offset=[-540, -330],
                       tracks=[track("scale", [(0, 0.6), (52, 1)], "out_cubic")]),
    ]))

    # horizontal_sweep: luminous band crosses the frame.
    motions.append(leak_motion("lightleak_horizontal_sweep", 54, [
        glow_component("band", warm, size_scale=[2.2, 0.5], opacity=0.85,
                       tracks=[track("position_x", [(0, -900), (54, 900)], "in_out_sine")]),
    ]))

    # diagonal_sweep: rotated band sweeping diagonally.
    motions.append(leak_motion("lightleak_diagonal_sweep", 54, [
        glow_component("diag_band", amber, size_scale=[2.2, 0.5], opacity=0.85,
                       tracks=[track("position_x", [(0, -900), (54, 900)], "in_out_sine"),
                               track("position_y", [(0, 500), (54, -500)], "in_out_sine")]),
    ]))

    # dual_edge: two opposed soft glows converging.
    motions.append(leak_motion("lightleak_dual_edge", 52, [
        glow_component("left_glow", warm, size_scale=[0.5, 2.2], opacity=0.7,
                       tracks=[track("position_x", [(0, -650), (52, -80)], "out_cubic")]),
        glow_component("right_glow", cool, size_scale=[0.5, 2.2], opacity=0.7,
                       placement="after_image",
                       tracks=[track("position_x", [(0, 650), (52, 80)], "out_cubic")]),
    ]))

    # prismatic: white band with a tiny constant RGB fringe. The band sweeps
    # in and rests centered — an entrance that exits the frame is an exit.
    motions.append(leak_motion("lightleak_prismatic", 50, [
        glow_component("prism_band", white, size_scale=[1.8, 0.45], opacity=0.8,
                       effects=[{"type": "gaussian_blur", "radius": 96},
                                {"type": "chromatic_aberration", "mode": "constant", "amount": 0.03}],
                       tracks=[track("position_x", [(0, -800), (50, 0)], "in_out_sine")]),
    ]))

    # pulse: centered glow appears, grows and settles.
    motions.append(leak_motion("lightleak_pulse", 46, [
        glow_component("pulse_glow", warm, size_scale=[1.5, 1.5], opacity=0.8,
                       tracks=[track("scale", [(0, 0.7), (24, 1.05), (46, 1)], "in_out_sine"),
                               track("opacity", [(0, 0), (18, 1), (46, 1)])]),
    ]))

    # film_burn: white-hot center that floods the frame; the burn then reads
    # as the transition matte itself. The plate rests at scale 1 after the
    # flood (the exit re-frame is the plan's job, not the entrance's).
    motions.append(leak_motion("lightleak_film_burn", 60, [
        glow_component("burn_core", white, size_scale=[2.6, 2.6], opacity=1.0,
                       tracks=[track("opacity", [(0, 0), (26, 1), (44, 1), (60, 1)], "in_out_sine"),
                               track("scale", [(0, 0.4), (44, 1.3), (60, 1.0)], "in_out_sine")],
                       placement="after_image"),
    ]))

    # soft_flare: wide, very diffuse amber light.
    motions.append(leak_motion("lightleak_soft_flare", 52, [
        glow_component("flare", amber, size_scale=[2.0, 2.0], opacity=0.55,
                       tracks=[track("scale", [(0, 0.85), (52, 1)], "out_cubic")]),
    ]))

    # focus_glow: radial light grows behind the entity; entity breathes 1->1.02->1.
    motions.append(leak_motion(
        "lightleak_focus_glow", 46,
        [glow_component("focus_halo", amber, size_scale=[1.4, 1.4], opacity=0.55,
                        tracks=[track("scale", [(0, 0.7), (46, 1.1)], "out_cubic")])],
        extra_tracks=[track("scale", [(0, 1), (23, 1.02), (46, 1)], "in_out_sine")]))

    # anamorphic_pass: wide horizontal cool streak.
    motions.append(leak_motion("lightleak_anamorphic_pass", 50, [
        glow_component("streak", cool, size_scale=[3.2, 0.18], opacity=0.75,
                       effects=[{"type": "gaussian_blur", "radius": 64},
                                {"type": "glow", "radius": 80, "intensity": 0.5,
                                 "color": [0.6, 0.8, 1.0, 1.0]}],
                       tracks=[track("opacity", [(0, 0), (20, 1), (50, 1)])]),
    ]))

    # bokeh_pass: soft discs drifting upward.
    bokeh = []
    discs = [(-0.30, 0.20, 0.28, 0.50), (0.25, -0.10, 0.22, 0.45),
             (0.05, 0.30, 0.18, 0.40), (-0.12, -0.28, 0.15, 0.35)]
    for index, (dx, dy, size, op) in enumerate(discs):
        bokeh.append(glow_component(f"bokeh_{index}", amber,
                                    size_scale=[size, size],
                                    position_offset=[dx * 960, dy * 540],
                                    opacity=op, placement="after_image",
                                    tracks=[track("position_y", [(0, 0), (50, -60 * (index + 1))], "linear")]))
    motions.append(leak_motion("lightleak_bokeh_pass", 50, bokeh))

    return motions


FAMILIES = {
    "brush_v1": brush_family,
    "web_rect_v1": web_rect_family,
    "paint_v1": paint_family,
    "light_leak_v1": light_leak_family,
}

FAMILY_COUNTS = {"brush_v1": 23, "web_rect_v1": 12, "paint_v1": 12, "light_leak_v1": 12}


def build_all() -> dict:
    motions = {}
    for family, builder in FAMILIES.items():
        rows = builder()
        expected = FAMILY_COUNTS[family]
        if len(rows) != expected:
            raise SystemExit(f"{family}: built {len(rows)} motions, want {expected}")
        for row in rows:
            if row["id"] in motions:
                raise SystemExit(f"duplicate motion id {row['id']}")
            motions[row["id"]] = row
    return motions


def validate_against_existing(catalog: dict, motions: dict) -> None:
    existing = {m["id"]: m for m in catalog.get("motions", [])}
    for mid, motion in motions.items():
        if mid in existing and existing[mid] != motion:
            raise SystemExit(
                f"{mid}: catalog already contains a different definition; "
                "the authoring tool is idempotent and never rewrites existing rows")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true",
                        help="exit 1 if any V1 motion is missing")
    args = parser.parse_args()

    catalog = json.loads(CATALOG.read_text())
    motions = build_all()
    validate_against_existing(catalog, motions)

    existing_ids = {m["id"] for m in catalog["motions"]}
    missing = [mid for mid in motions if mid not in existing_ids]
    if args.check:
        if missing:
            print(f"missing {len(missing)} visual accents motions: {missing}", file=sys.stderr)
            raise SystemExit(1)
        print("visual accents V1: all 59 motions present (brush_v1=23, other families=12 each)")
        return

    added = [m for mid, m in motions.items() if mid not in existing_ids]
    catalog["motions"].extend(added)
    catalog["motions"].sort(key=lambda m: m["id"])
    CATALOG.write_text(json.dumps(catalog, indent=2) + "\n")
    print(f"visual accents V1: added {len(added)} motions "
          f"({', '.join(f'{k}={FAMILY_COUNTS[k]}' for k in FAMILIES)})")


if __name__ == "__main__":
    main()
