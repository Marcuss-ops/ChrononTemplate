#!/usr/bin/env python3
"""camera_motion_pack.v1 catalog contract test.

The catalog is data (`catalog/camera_motion_pack.v1.json`) generated from the
C++-owned pack by `chronontemplate_emit_camera_motion_catalog`. This test pins
the contract without needing the CLI or a GPU:

  1.  the emitter exits 0 and prints valid JSON;
  2.  the document holds twenty-five recipes (fifteen editorial + ten web3d),
      with unique `camera_motion_*` ids and the spec durations;
  3.  every recipe carries easing, requirements and valid windows;
  4.  the selection table covers the thirteen content kinds, only names
      real recipes, and every recipe is selectable from some content kind;
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
    "camera_motion_title_slow_push": 90, "camera_motion_title_lateral_drift": 96,
    "camera_motion_title_rise_settle": 72,
    "camera_motion_portrait_arc": 108, "camera_motion_archive_reveal": 84,
    "camera_motion_rack_focus_portrait": 78,
    "camera_motion_map_region_push": 96, "camera_motion_map_route_track": 120,
    "camera_motion_map_country_tilt": 100,
    "camera_motion_ui_panel_push": 64, "camera_motion_ui_card_parallax": 90,
    "camera_motion_ui_micro_float": 150,
    "camera_motion_whip_pan_left": 14, "camera_motion_whip_pan_right": 14,
    "camera_motion_dolly_handoff": 22,
    "camera_motion_web3d_product_push": 96, "camera_motion_web3d_orbit": 120,
    "camera_motion_web3d_arc_left": 105, "camera_motion_web3d_arc_right": 105,
    "camera_motion_web3d_rise_reveal": 90, "camera_motion_web3d_top_down": 108,
    "camera_motion_web3d_lateral_slide": 96, "camera_motion_web3d_dolly_arc": 90,
    "camera_motion_web3d_crane_down": 100, "camera_motion_web3d_slow_drift": 150,
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

    print("== the twenty-five recipes")
    recipes = document.get("recipes") or []
    check("twenty-five recipes", len(recipes) == 25, str(len(recipes)))
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
    check("recipes per family",
          families == {"editorial_title": 3, "photo_documentary": 3, "map_geo": 3,
                       "dashboard_ui": 3, "transition": 3, "web3d": 10}, str(families))
    two_shot = {r["id"] for r in recipes if (r.get("requirements") or {}).get("two_shot")}
    check("two-shot only in the transition family",
          two_shot == {r["id"] for r in recipes if r.get("family") == "transition"} and len(two_shot) == 3)

    print("== the selection table")
    selection = document.get("selection") or {}
    check("fourteen content kinds", len(selection) == 14, str(sorted(selection)))
    known_ids = set(ids)
    suggested: set[str] = set()
    for kind, picks in selection.items():
        check(f"{kind} suggests at least one preset", bool(picks))
        check(f"{kind} only suggests real presets", all(p in known_ids for p in picks), str(picks))
        suggested.update(picks)
    check("every recipe is selectable", known_ids <= suggested, str(sorted(known_ids - suggested)))

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
