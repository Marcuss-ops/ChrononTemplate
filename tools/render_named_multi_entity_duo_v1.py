#!/usr/bin/env python3
"""Five animated x2 portrait compositions with synchronized entity names."""
from __future__ import annotations

import copy
import importlib.util
import sys
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS))

from kit import Suite, SuiteItem  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
TEMPLATE_DIR = ROOT / "ChrononTemplate"
OUT_DIR = TEMPLATE_DIR / "out/named_multi_entity_duo_v1"
DRIVE_FOLDER_ID = "1SXQQaEwJ2mk9_u0T2Fl15DQ1C6_A8kcX"
FONT = "Chronon3d/assets/fonts/Inter-Bold.ttf"

DUO_SCRIPT = TOOLS / "render_multi_entity_layout_v1.py"
DUO_SPEC = importlib.util.spec_from_file_location("named_duo_motion_source", DUO_SCRIPT)
assert DUO_SPEC and DUO_SPEC.loader
DUO = importlib.util.module_from_spec(DUO_SPEC)
DUO_SPEC.loader.exec_module(DUO)

PEOPLE = (
    {
        "name": "NEIL ARMSTRONG",
        "asset": "ChrononTemplate/assets/famous_people_trio_v1/neil_armstrong.png",
    },
    {
        "name": "SALLY RIDE",
        "asset": "ChrononTemplate/assets/famous_people_trio_v1/sally_ride.png",
    },
)


def build_named_plan(preset_id: str, builder) -> dict:
    """Reuse one certified duo motion, adding captions tied to each image's tracks."""
    plan = copy.deepcopy(builder())
    plan["job_id"] = f"named_{preset_id}"
    plan["output"]["path"] = str(OUT_DIR / f"named_{preset_id}.mp4")
    image_layers = [layer for layer in plan["layers"] if layer.get("type") == "image"]
    if len(image_layers) != 2:
        raise ValueError(f"{preset_id}: expected exactly two image layers")

    for index, (image, person) in enumerate(zip(image_layers, PEOPLE, strict=True)):
        image["asset"] = person["asset"]
        tracks = image.get("animation", {}).get("tracks", [])
        # Text follows the portrait's reveal and focus emphasis without
        # inheriting image-only position/rotation/depth channels.
        opacity = next(track for track in tracks if track["property"] == "opacity")
        scale = next(track for track in tracks if track["property"] == "scale")
        canvas_x = 960 + image["position"][0]
        plan["layers"].append({
            "id": f"entity_name_{'left' if index == 0 else 'right'}",
            "type": "text",
            "text": person["name"],
            "position": [canvas_x, 966],
            "size": [580, 64],
            "style": {
                "font": FONT,
                "font_size": 34,
                "min_font_size": 26,
                "max_font_size": 34,
                "fit_mode": "shrink_only",
                "fill": "#F4F1E8",
            },
            "start_frame": 0,
            "duration_frames": DUO.DURATION_FRAMES,
            "animation": {"tracks": [copy.deepcopy(opacity), copy.deepcopy(scale)]},
        })
    DUO.validate_plan_contract(plan["job_id"], plan)
    return plan


ANIMATIONS = tuple(
    (f"named_{preset_id}", lambda preset_id=preset_id, builder=builder: build_named_plan(preset_id, builder))
    for preset_id, builder in DUO.PRESET_SUITE
)

SUITE = Suite(
    name="named_multi_entity_duo_v1",
    out_dir=OUT_DIR,
    drive_folder=DRIVE_FOLDER_ID,
    assets_root=ROOT,
    items=[SuiteItem(name, build) for name, build in ANIMATIONS],
    items_meta={
        name: {
            "entities": [person["name"] for person in PEOPLE],
            "caption_font": FONT,
        }
        for name, _ in ANIMATIONS
    },
)

if __name__ == "__main__":
    from kit import run_suite
    raise SystemExit(run_suite(SUITE))
