#!/usr/bin/env python3
"""camera_motion_pack.v1 catalog contract test.

The catalog is data (`catalog/camera_motion_pack.v1.json`) generated from the
C++-owned pack by `chronontemplate_emit_camera_motion_catalog`. This test pins
the contract without needing the CLI or a GPU:

  1.  the emitter exits 0 and prints valid JSON;
  2.  the document holds fifty recipes, ten per family, with unique
      `camera_motion_*` ids and the spec durations;
  3.  every recipe carries easing, requirements and valid windows;
  4.  the selection table covers the thirteen content kinds and only names
      real recipes, including the spec's priority thirteen;
  5.  the committed catalog is byte-for-byte what the emitter produces today —
      the file is generated, not hand-maintained.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

failures: list[str] = []


def check(name: str, condition: bool, detail: str = "") -> None:
    if condition:
        print(f"  [OK] {name}")
    else:
        failures.append(f"{name}{': ' + detail if detail else ''}")
        print(f"  [FAIL] {name} {detail}")


EXPECTED_DURATIONS = {
    "camera_motion_soft_push_in": 75, "camera_motion_soft_pull_back": 75,
    "camera_motion_editorial_drift_left": 84, "camera_motion_editorial_drift_right": 84,
    "camera_motion_title_rise": 50, "camera_motion_title_descend": 50,
    "camera_motion_quiet_diagonal_drift": 90, "camera_motion_type_depth_focus": 70,
    "camera_motion_type_micro_orbit": 100, "camera_motion_impact_punch_settle": 22,
    "camera_motion_ken_burns_in": 120, "camera_motion_ken_burns_out": 120,
    "camera_motion_portrait_upward_track": 85, "camera_motion_portrait_downward_track": 85,
    "camera_motion_photo_reveal_left": 70, "camera_motion_photo_reveal_right": 70,
    "camera_motion_low_angle_photo_reveal": 72, "camera_motion_portrait_hero_arc": 100,
    "camera_motion_documentary_parallax": 105, "camera_motion_photo_rack_focus": 78,
    "camera_motion_map_region_push": 90, "camera_motion_map_region_pull": 100,
    "camera_motion_map_eastward_track": 105, "camera_motion_map_westward_track": 105,
    "camera_motion_map_northward_track": 95, "camera_motion_map_southward_track": 95,
    "camera_motion_route_camera_sweep": 120, "camera_motion_country_focus_lock": 82,
    "camera_motion_country_comparison_pan": 110, "camera_motion_geopolitical_tilt_reveal": 98,
    "camera_motion_ui_panel_push": 63, "camera_motion_dashboard_pan": 100,
    "camera_motion_card_stack_parallax": 86, "camera_motion_corner_detail_inspect": 77,
    "camera_motion_data_detail_zoom": 70, "camera_motion_ui_overview_pull": 90,
    "camera_motion_side_by_side_compare": 110, "camera_motion_panel_angled_peek": 76,
    "camera_motion_chart_traverse": 105, "camera_motion_product_ui_micro_float": 150,
    "camera_motion_whip_pan_left": 14, "camera_motion_whip_pan_right": 14,
    "camera_motion_whip_pan_up": 16, "camera_motion_whip_pan_down": 16,
    "camera_motion_fast_dolly_through": 22, "camera_motion_reverse_dolly_reveal": 22,
    "camera_motion_roll_match_cut": 19, "camera_motion_orbit_handoff": 24,
    "camera_motion_foreground_occlusion_pass": 22, "camera_motion_focus_handoff": 28,
}

PRIORITY_THIRTEEN = {
    "camera_motion_soft_push_in", "camera_motion_impact_punch_settle",
    "camera_motion_ken_burns_in", "camera_motion_portrait_hero_arc",
    "camera_motion_documentary_parallax", "camera_motion_map_region_push",
    "camera_motion_route_camera_sweep", "camera_motion_country_focus_lock",
    "camera_motion_card_stack_parallax", "camera_motion_data_detail_zoom",
    "camera_motion_whip_pan_left", "camera_motion_fast_dolly_through",
    "camera_motion_foreground_occlusion_pass",
}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tool", required=True, help="camera motion emitter binary path")
    parser.add_argument("--catalog", required=True, help="committed catalog path")
    args = parser.parse_args()

    tool = Path(args.tool)
    catalog = Path(args.catalog)
    if not tool.is_file():
        print(f"FAIL: missing tool binary {tool}")
        return 1

    print("== the emitter prints valid JSON")
    first = subprocess.run([str(tool)], capture_output=True, text=True)
    check("emitter exits 0", first.returncode == 0, first.stderr.strip())
    if first.returncode != 0:
        print(f"\n{len(failures)} failure(s)")
        return 1
    try:
        document = json.loads(first.stdout)
    except json.JSONDecodeError as error:
        print(f"FAIL: stdout is not JSON: {error}")
        return 1

    print("== the document header")
    check("schema", document.get("schema") == "chronontemplate.camera-motion-pack.v1")
    check("version", document.get("version") == 1)
    check("catalog id", document.get("catalog_id") == "camera_motion_pack_v1")
    check("fps", document.get("fps") == 30)
    check("intensity ladder", document.get("intensity_ladder") == {"subtle": 0.5, "normal": 1.0, "strong": 1.5},
          str(document.get("intensity_ladder")))

    print("== the fifty recipes")
    recipes = document.get("recipes") or []
    check("fifty recipes", len(recipes) == 50, str(len(recipes)))
    ids = [r.get("id") for r in recipes]
    check("ids are unique", len(set(ids)) == len(ids))
    check("ids carry the camera_motion_ prefix", all(str(i).startswith("camera_motion_") for i in ids))
    check("durations match the spec", {r["id"]: r["duration_frames"] for r in recipes} == EXPECTED_DURATIONS)
    families: dict[str, int] = {}
    for recipe in recipes:
        families[recipe.get("family")] = families.get(recipe.get("family"), 0) + 1
        check(f"{recipe.get('id')} easing resolves",
              recipe.get("easing") in {"cinematic", "smooth", "gentle_out", "snappy_out", "whip_in", "whip_out"},
              str(recipe.get("easing")))
        req = recipe.get("requirements") or {}
        check(f"{recipe.get('id')} declares requirements",
              set(req) == {"dof", "planes_25d", "multi_plane", "two_shot", "occluder", "high_energy"})
        travel = recipe.get("travel_window") or {}
        check(f"{recipe.get('id')} travel window is ordered",
              0 <= travel.get("start", -1) < travel.get("end", -1) <= 1, str(travel))
    check("ten recipes per family",
          families == {"editorial_title": 10, "photo_documentary": 10, "map_geo": 10,
                       "dashboard_ui": 10, "transition": 10}, str(families))
    two_shot = {r["id"] for r in recipes if (r.get("requirements") or {}).get("two_shot")}
    check("two-shot only in the transition family",
          two_shot == {r["id"] for r in recipes if r.get("family") == "transition"} and len(two_shot) == 10)

    print("== the selection table")
    selection = document.get("selection") or {}
    check("thirteen content kinds", len(selection) == 13, str(sorted(selection)))
    known_ids = set(ids)
    suggested: set[str] = set()
    for kind, picks in selection.items():
        check(f"{kind} suggests at least one preset", bool(picks))
        check(f"{kind} only suggests real presets", all(p in known_ids for p in picks), str(picks))
        suggested.update(picks)
    check("the priority thirteen are selectable", PRIORITY_THIRTEEN.issubset(suggested))

    print("== the committed catalog is generated from the C++ pack")
    if not catalog.is_file():
        check("catalog file exists", False, str(catalog))
    else:
        check("catalog matches the emitter output", catalog.read_text() == first.stdout,
              "catalog/camera_motion_pack.v1.json is stale — regenerate it")
    second = subprocess.run([str(tool)], capture_output=True, text=True)
    check("the emitter is deterministic", second.stdout == first.stdout)

    if failures:
        print(f"\n{len(failures)} failure(s)")
        return 1
    print("\nall camera motion catalog contract checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
