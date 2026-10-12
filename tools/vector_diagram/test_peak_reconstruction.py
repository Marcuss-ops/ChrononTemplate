#!/usr/bin/env python3
"""Acceptance checks for the documentary peak-diagram family plans."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import reconstruct_peak_diagrams as diagrams


def layer(plan, ident):
    return next(item for item in plan["layers"] if item["id"] == ident)


def test_phase_b_is_one_continuous_canonical_path_with_visible_fill_separation():
    plan = diagrams.static_b()
    path = layer(plan, "diagram_path")
    assert path["shape"]["type"] == "path"
    assert len(path["shape"]["path"]) == len(diagrams.B_NORM)
    assert path["shape"]["path"][0]["type"] == "move_to"
    assert all(item["type"] == "line_to" for item in path["shape"]["path"][1:])
    assert "dash_array" not in path["shape"]["stroke"]
    assert path["shape"]["stroke"]["width"] == 2.5
    # Fill alpha is required by this bridge to keep the white path stroke enabled.
    assert path["shape"]["fill"] == diagrams.rgba("#030304")
    assert path["color"] == [1, 1, 1, 1]


def test_phase_b_markers_are_large_and_independent_of_the_path():
    plan = diagrams.static_b()
    yellow = layer(plan, "yellow_marker")
    rise = layer(plan, "red_rising_marker")
    peak = layer(plan, "red_peak_marker")
    assert yellow["size"] == [48, 48]
    assert yellow["effects"][0]["radius"] >= 45
    assert rise["size"][0] >= 20 and peak["size"][0] >= 20
    assert rise["opacity"] > 0.5 and peak["opacity"] > 0.5
    assert yellow["position"] != path_layer_position(plan)


def path_layer_position(plan):
    return layer(plan, "diagram_path")["position"]


def test_annotated_timeline_uses_static_geometry_and_fixed_yellow_anchor():
    plan = diagrams.annotated_b(animated=True, texture=True)
    path = layer(plan, "diagram_path")
    assert path["shape"]["path"] == diagrams.commands(diagrams.B_NORM)
    assert path["shape"]["operators"][0]["params"]["animation"]["keyframes"] == [
        {"frame": 10, "value": [0, 0, 0]},
        {"frame": 45, "value": [0, 1, 0]},
    ]
    assert layer(plan, "yellow_marker")["position"] == diagrams.screen_xy((0.40, 0.43))
    assert layer(plan, "red_rising_marker")["start_frame"] == 40
    assert layer(plan, "red_peak_marker")["start_frame"] == 60
    assert plan["canvas"]["duration_frames"] == 150


def test_path_stays_compact_and_inside_canvas():
    xs = [x for x, _ in diagrams.B_NORM]
    ys = [y for _, y in diagrams.B_NORM]
    assert 0.35 <= max(xs) - min(xs) <= 0.45
    assert all(0 < x < 1 and 0 < y < 1 for x, y in diagrams.B_NORM)


if __name__ == "__main__":
    tests = [value for name, value in globals().items() if name.startswith("test_")]
    for test in tests:
        test()
        print(f"PASS {test.__name__}")
    print(f"{len(tests)} focused acceptance checks passed")
