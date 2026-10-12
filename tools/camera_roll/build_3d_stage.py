#!/usr/bin/env python3
"""Turn camera-motion certification plans into real 3D scenes.

The original plans put one flat title at Z=0 on a flat background, so the camera
move was only a 2D pan. This rebuilds the layers as a stack of text planes at
different depths, tilted with a layer rotation, so the camera's own perspective
produces parallax. Camera paths, the hero title and the caption are kept.

Depth convention (from the emitter): the camera sits at a negative Z and looks
toward +Z, so a larger Z is farther from the lens.

Renderer constraint (measured on the Vulkan backend): enable_3d text planes that
sit *between* the camera and the hero (negative Z) hide the hero on most frames.
So every decorative plane is placed behind the hero (Z > 0). The hero stays at
Z=0, so the depth stack is still real 3D: planes at Z 350, 700 and 1600.

usage: build_3d_stage.py <plans-dir> <out-plans-dir>
"""

import json
import sys
from pathlib import Path

TITLE_FONT = "assets/fonts/Bricolage-Grotesque.ttf"
CANVAS_W, CANVAS_H = 1920, 1080

# Category-matched plates from the repository's local asset library. The first
# image is a wide environmental plate; the second supplies a readable subject
# detail card. Both are real image textures on perspective camera-facing planes.
ASSET_SETS = {
    "map": ("assets/maps/italy_usa_basemap.png", "assets/maps/alps_relief.png"),
    "portrait": ("assets/images/ada_lovelace_portrait.png", "assets/images/alan_turing_portrait.png"),
    "photo": ("assets/editorial/industrial_port_dawn.png", "assets/images/minimalist_landscape.png"),
    "editorial": ("assets/editorial/industrial_port_dawn.png", "assets/images/minimalist_landscape.png"),
    "ui": ("assets/images/grid_tile.png", "assets/maps/test_esri_dark_cleveland.png"),
    "transition": ("assets/images/star_bumper_iridescent.png", "assets/images/short_phrase_light_plate.png"),
    "title": ("assets/images/minimalist_landscape.png", "assets/editorial/industrial_port_dawn.png"),
}


def asset_family(preset_id):
    if any(k in preset_id for k in ("map_", "country_", "geopolitical", "route_")):
        return "map"
    if any(k in preset_id for k in ("portrait",)):
        return "portrait"
    if any(k in preset_id for k in ("photo_", "ken_burns", "documentary", "low_angle")):
        return "photo"
    if any(k in preset_id for k in ("ui_", "dashboard", "chart_", "data_", "panel_", "product_ui")):
        return "ui"
    if any(k in preset_id for k in ("whip_", "dolly_", "orbit_", "roll_match", "occlusion", "impact_")):
        return "transition"
    if "title_" in preset_id or preset_id in ("soft_push_in", "soft_pull_back", "editorial_drift_left", "editorial_drift_right", "quiet_diagonal_drift"):
        return "title"
    return "editorial"


def image_plane(layer_id, asset, position, size, frames, opacity=1.0, rotation=None):
    plane = {
        "id": layer_id,
        "type": "image",
        "asset": asset,
        "size": size,
        "position": position,
        "fit": "cover",
        "start_frame": 0,
        "duration_frames": frames,
        "enable_3d": True,
        "opacity": opacity,
    }
    if rotation is not None:
        plane["rotation"] = rotation
    return plane


def shape_plane(layer_id, position, size, color, frames, rotation):
    return {
        "id": layer_id,
        "type": "shape",
        "size": size,
        "position": position,
        "rotation": rotation,
        "enable_3d": True,
        "start_frame": 0,
        "duration_frames": frames,
        "shape": {"type": "rect", "fill": color},
    }


def visual_plates(plan, frames):
    preset = plan.get("job_id", "").replace("camera_motion_cert_", "")
    family = asset_family(preset)
    wide, _detail = ASSET_SETS[family]
    # One real image texture per scene, mapped onto a large 3D plane behind all
    # type. The Vulkan renderer is stable with one 3D image plane; stacking
    # multiple image planes and 3D shapes in this camera composition caused
    # occasional empty frames, so use the proven one-plane setup. The plane is
    # still perspective-projected and participates in the camera move.
    return [
        image_plane("environment-plate", wide, [960, 540, 1250], [2900, 1750], frames,
                    opacity=0.68, rotation=[0, 0, 0]),
    ]

# Depth planes behind the hero, far to near: (layer_id, z, y, rot_x, rot_y, size, font_size, fill)
DEPTH_PLANES = [
    ("depth-far", 1600, 540, 0, -22, [2300, 560], 300, "#1F2533"),
    ("depth-mid", 700, 680, -6, 14, [1500, 220], 150, "#2E3648"),
    ("depth-near", 350, 300, 4, -8, [1100, 140], 96, "#3D4760"),
]


def find_layer(layers, layer_id):
    for layer in layers:
        if layer.get("id") == layer_id:
            return layer
    return None


def text_plane(layer_id, text, z, y, rot_x, rot_y, size_xy, font_size, fill, frames):
    return {
        "id": layer_id,
        "type": "text",
        "text": text,
        "size": size_xy,
        "position": [960, y, z],
        "rotation": [rot_x, rot_y, 0],
        "start_frame": 0,
        "duration_frames": frames,
        "enable_3d": True,
        "style": {
            "font": TITLE_FONT,
            "font_size": font_size,
            "fill": fill,
            "fit_mode": "shrink_only",
            "min_font_size": 20,
            "max_font_size": font_size,
        },
    }


# Closest camera approach to the hero (camera Z may not go above this). Measured:
# with the camera at Z -564 (about 564 units from the hero) every text plane drops
# out for 3 frames on the Vulkan backend, while at -760 the frames render. So the
# dolly is stopped at -760; only fast_dolly_through reaches closer than this.
MIN_CAMERA_Z_DISTANCE_LIMIT = -760


def clamp_camera_closeness(plan):
    for track in plan.get("camera_animation", {}).get("tracks", []):
        if track.get("property") == "camera_position_z":
            for key in track["keyframes"]:
                key["value"] = min(key["value"], MIN_CAMERA_Z_DISTANCE_LIMIT)
    cam = plan["camera"]
    cam["position"][2] = min(cam["position"][2], MIN_CAMERA_Z_DISTANCE_LIMIT)


def build_stage(plan):
    frames = plan["canvas"]["duration_frames"]
    layers = plan["layers"]
    title = find_layer(layers, "hero-title")
    caption = find_layer(layers, "move-caption")
    title_text = title["text"] if title else ""
    caption_text = caption["text"] if caption else ""

    # Preserve any screen-space cover elements the preset staged (occluders, bars).
    keep = [l for l in layers if l.get("id") not in ("background", "hero-title", "move-caption")]

    words = title_text.split(" ")
    texts = [title_text.upper(), caption_text, words[-1] if words else ""]
    stage = [
        {
            "id": "background",
            "type": "color",
            "color": [0.025, 0.032, 0.045, 1.0],
            "size": [CANVAS_W, CANVAS_H],
            "screen_space": True,
            "start_frame": 0,
            "duration_frames": frames,
        }
    ]
    stage.extend(visual_plates(plan, frames))
    for (layer_id, z, y, rot_x, rot_y, size_xy, font_size, fill), text in zip(DEPTH_PLANES, texts):
        stage.append(text_plane(layer_id, text, z, y, rot_x, rot_y, size_xy, font_size, fill, frames))
    if title:
        hero = dict(title)
        hero["rotation"] = [0, 0, 0]
        stage.append(hero)
    if caption:
        cap = dict(caption)
        cap["rotation"] = [0, 0, 0]
        stage.append(cap)
    stage.extend(keep)
    return stage


def main():
    if len(sys.argv) != 3:
        print(__doc__)
        return 2
    src, dst = Path(sys.argv[1]), Path(sys.argv[2])
    dst.mkdir(parents=True, exist_ok=True)
    count = 0
    for path in sorted(src.glob("*.plan.json")):
        plan = json.loads(path.read_text())
        clamp_camera_closeness(plan)
        plan["layers"] = build_stage(plan)
        (dst / path.name).write_text(json.dumps(plan, indent=2) + "\n")
        count += 1
    print(f"built {count} 3D stage plans under {dst}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
