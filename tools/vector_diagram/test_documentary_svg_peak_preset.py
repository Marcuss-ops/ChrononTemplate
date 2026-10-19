#!/usr/bin/env python3
"""Focused checks for the registry-backed documentary SVG preset builder."""
from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import documentary_svg_peak_registry as registry


def by_id(plan: dict, layer_id: str) -> dict:
    return next(layer for layer in plan["layers"] if layer["id"] == layer_id)


def test_catalog_resolves_stable_svg_asset_and_builds_native_plan():
    preset = registry.load_preset()
    plan = registry.build_plan(preset)
    assert preset["id"] == plan["job_id"] == "documentary_svg_peak_v1"
    assert plan["schema"] == "chronon.render-plan.v3"
    assert plan["canvas"] == {
        "width": 854, "height": 480, "fps_num": 30, "fps_den": 1,
        "duration_frames": 150,
    }
    assert by_id(plan, "peak_svg")["shape"]["asset"] == "documentary_svg_peak_v1.svg"
    commands = by_id(plan, "yellow_marker")["follow_path"]["path_commands"]
    assert commands[0] == {"type": "move_to", "point": [106.0, 366.0]}
    assert len(commands) == 8
    assert registry.build_plan(preset) == registry.build_plan(preset)


def test_catalog_parameters_lower_into_timing_geometry_glow_and_framing():
    preset = copy.deepcopy(registry.load_preset())
    preset["canvas"]["duration_frames"] = 180
    preset["trim"] = {"start_frame": 12, "end_frame": 72}
    preset["marker"].update({"size": 30, "start_frame": 12,
                             "end_frame": 90, "progress_end": 0.8})
    preset["marker"]["glow"]["enabled"] = True
    preset["framing"] = {"scale": 1.2, "offset": [12.0, -8.0]}
    plan = registry.build_plan(preset)

    assert plan["canvas"]["duration_frames"] == 180
    trim = by_id(plan, "peak_svg")["shape"]["operators"][0]["params"]["animation"]["keyframes"]
    assert [key["frame"] for key in trim] == [12, 72]
    marker = by_id(plan, "yellow_marker")
    assert marker["size"] == [30.0, 30.0]
    progress = marker["follow_path"]["progress"]["keyframes"]
    assert [key["frame"] for key in progress] == [12, 90]
    assert progress[-1]["value"] == 0.8
    assert marker["effects"][0]["type"] == "glow"
    assert "animation" not in by_id(plan, "peak_svg")
    assert by_id(plan, "peak_svg")["position"] == [12.0, 8.0]
    assert by_id(plan, "peak_svg")["size"] == [854 * 1.2, 480 * 1.2]
    assert marker["follow_path"]["path_commands"][0]["point"] == [
        12 + (106 - 854 / 2) * 1.2 + 854 / 2,
        -8 + (366 - 480 / 2) * 1.2 + 480 / 2,
    ]


def test_unknown_preset_and_invalid_timing_fail_closed():
    try:
        registry.load_preset("missing")
    except KeyError:
        pass
    else:
        raise AssertionError("unknown preset id must fail closed")
    preset = copy.deepcopy(registry.load_preset())
    preset["trim"]["end_frame"] = preset["canvas"]["duration_frames"]
    try:
        registry.build_plan(preset)
    except ValueError:
        pass
    else:
        raise AssertionError("out-of-duration keyframes must fail closed")


if __name__ == "__main__":
    for name, value in sorted(globals().items()):
        if name.startswith("test_") and callable(value):
            value()
            print(f"PASS {name}")
