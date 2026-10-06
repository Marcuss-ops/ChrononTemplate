#!/usr/bin/env python3
"""Author deterministic PHOTO MOTION V1 gallery and 15-second torture plans.

The 18 recipe ids are data in catalog/photo_motion_v1.json. Cards, stacks,
piles and reveals all lower to ordinary image/shape/text RenderPlan layers.
"""
from __future__ import annotations

import argparse
import json
import math
import random
import subprocess
from pathlib import Path
from typing import Any

TEMPLATE = Path(__file__).resolve().parents[2]
WORKSPACE = TEMPLATE.parent
CHRONON = WORKSPACE / "Chronon3d"
FAMILY_FILE = TEMPLATE / "catalog/photo_motion_v1.json"
OUT = TEMPLATE / "out/photo_motion_v1"
CLI_CANDIDATES = (
    CHRONON / "build/chronon/linux-video-fast-dev/apps/chronon3d_cli/chronon3d_cli",
    CHRONON / "build/chronon/linux-fast-dev/apps/chronon3d_cli/chronon3d_cli",
)
W, H, FPS, SEGMENT = 1920, 1080, 30, 60
CARD_W, CARD_H = 398.0, 478.0
PHOTO_ASSETS = (
    "ChrononTemplate/assets/images/card_penta_1.png",
    "ChrononTemplate/assets/images/card_penta_2.png",
    "ChrononTemplate/assets/images/card_penta_3.png",
    "ChrononTemplate/assets/images/card_penta_4.png",
)
FONT = "Chronon3d/assets/fonts/Inter-Regular.ttf"
FONT_BOLD = "Chronon3d/assets/fonts/Inter-Bold.ttf"


def track(prop: str, keys: list[tuple[int, Any]], easing: str = "out_cubic") -> dict:
    # Canonicalize equal-frame keys and keep every recipe random-access deterministic.
    unique = {int(frame): value for frame, value in keys}
    return {"property": prop, "easing": easing,
            "keyframes": [{"frame": frame, "value": unique[frame]}
                          for frame in sorted(unique)]}


def rgba(hex_color: str, alpha: float = 1.0) -> list[float]:
    value = hex_color.lstrip("#")
    return [int(value[i:i+2], 16) / 255.0 for i in (0, 2, 4)] + [alpha]


def layer(id_: str, kind: str, start: int, duration: int, **fields) -> dict:
    return {"id": id_, "type": kind, "start_frame": int(start),
            "duration_frames": int(duration), **fields}


def fill_layer(id_: str, start: int, duration: int, color: list[float]) -> dict:
    return layer(id_, "color", start, duration, color=color, size=[W, H],
                 position=[W / 2, H / 2], screen_space=True)


def text_layer(id_: str, text: str, start: int, duration: int, y: float,
               color: str, size: int, *, bold=False, opacity_keys=None) -> dict:
    keys = opacity_keys or [(0, 0.0), (7, 1.0), (duration - 7, 1.0), (duration - 1, 0.0)]
    return layer(id_, "text", start, duration, text=text, size=[1500, max(28, size * 1.7)],
                 position=[W / 2, y],
                 style={"font": FONT_BOLD if bold else FONT, "font_size": size,
                        "min_font_size": max(12, size - 8), "max_font_size": size,
                        "fit_mode": "shrink_only", "fill": color},
                 animation={"tracks": [track("opacity", keys)]})


def pose_track_values(base_center: tuple[float, float], child_offset: tuple[float, float],
                      poses: list[dict]) -> list[dict]:
    """Resolve one child layer's tracks from a rigid parent-card transform."""
    qx, qy = child_offset
    px, py = [], []
    for pose in poses:
        theta = math.radians(pose.get("rotation", 0.0))
        scale = pose.get("scale", 1.0)
        rx = scale * (math.cos(theta) * qx - math.sin(theta) * qy)
        ry = scale * (math.sin(theta) * qx + math.cos(theta) * qy)
        px.append((pose["frame"], pose["x"] - base_center[0] + rx - qx))
        py.append((pose["frame"], pose["y"] - base_center[1] + ry - qy))
    return [track("position_x", px), track("position_y", py),
            track("rotation_z", [(p["frame"], p.get("rotation", 0.0)) for p in poses]),
            track("scale", [(p["frame"], p.get("scale", 1.0)) for p in poses]),
            track("position_z", [(p["frame"], p.get("z", 0.0)) for p in poses]),
            track("opacity", [(p["frame"], p.get("opacity", 1.0)) for p in poses])]


def pose(frame: int, x: float, y: float, *, z=0.0, scale=1.0,
         rotation=0.0, opacity=1.0) -> dict:
    return {"frame": frame, "x": x, "y": y, "z": z,
            "scale": scale, "rotation": rotation, "opacity": opacity}


def card_parts(id_: str, asset: str, center: tuple[float, float], start: int,
               duration: int, poses: list[dict], style: dict, *, kind="photo",
               browser=False, image_mask=None, image_effects=None) -> list[dict]:
    """Emit card plate, image and optional caption as one rigid transform group."""
    cx, cy = center
    paper, ink = style["paper"], style["ink"]
    polaroid = kind == "polaroid"
    pad = 18.0 if polaroid else 9.0
    image_h = CARD_H - (106.0 if polaroid else 18.0) - (28.0 if browser else 0.0)
    image_y = -35.0 if polaroid else (14.0 if browser else 0.0)
    frame_fill = {"type": "rounded_rect", "radius": 9 if browser else (1 if polaroid else 22),
                  "fill": paper}
    frame = layer(f"{id_}-paper", "shape", start, duration,
                  size=[CARD_W, CARD_H], position=[cx, cy],
                  shape={**frame_fill, "fill": rgba(paper)},
                  style={"shadow": {"color": style["shadow"], "offset": [0, 18], "opacity": .42, "blur": 28}},
                  enable_3d=True,
                  animation={"tracks": pose_track_values(center, (0, 0), poses)})
    img_size = [CARD_W - 2 * pad, image_h]
    img_pos = [cx, cy + image_y]
    image = layer(f"{id_}-image", "image", start, duration, asset=asset,
                  size=img_size, position=img_pos, fit="cover",
                  radius=0 if polaroid else (7 if browser else 15), enable_3d=True,
                  style={"shadow": {"color": style["shadow"], "offset": [0, 5], "opacity": .28, "blur": 10}},
                  animation={"tracks": pose_track_values(center, (0, image_y), poses)})
    if image_mask:
        image["masks"] = [image_mask]
    if image_effects:
        image["effects"] = image_effects
    parts = [frame, image]
    if browser:
        bar_y = cy - CARD_H/2 + 19
        chrome = layer(f"{id_}-browser-chrome", "shape", start, duration,
                       size=[CARD_W - 2, 38], position=[cx, bar_y],
                       shape={"type": "rounded_rect", "radius": 8, "fill": rgba("#E7EAF0")},
                       enable_3d=True,
                       animation={"tracks": pose_track_values(center, (0, -CARD_H/2 + 19), poses)})
        parts.append(chrome)
        for dot_index, dot_color in enumerate(("#F16C68", "#E6B557", "#65B97A")):
            ox = -CARD_W/2 + 20 + dot_index * 18
            parts.append(layer(f"{id_}-browser-dot-{dot_index}", "shape", start, duration,
                               size=[9, 9], position=[cx + ox, bar_y],
                               shape={"type": "ellipse", "fill": rgba(dot_color)}, enable_3d=True,
                               animation={"tracks": pose_track_values(center, (ox, -CARD_H/2 + 19), poses)}))
    if polaroid:
        caption = layer(f"{id_}-caption", "text", start, duration,
                        text=f"ARCHIVE STILL  /  {int(id_.split('-')[-1]) + 1:02d}",
                        size=[CARD_W - 36, 44], position=[cx, cy + CARD_H/2 - 39],
                        style={"font": FONT_BOLD, "font_size": 17, "fill": ink,
                               "fit_mode": "shrink_only", "min_font_size": 13, "max_font_size": 17},
                        enable_3d=True,
                        animation={"tracks": pose_track_values(center, (0, CARD_H/2 - 39), poses)})
        parts.append(caption)
    return parts


def _rounded_mask(width: float, height: float, radius: float,
                  expansion_keys: list[tuple[int, float]]) -> dict:
    return {"type": "rounded_rect", "mode": "intersect", "position": [0, 0],
            "size": [width, height], "radius": min(radius, width/2, height/2),
            "expansion_track": {"keyframes": [
                {"frame": frame, "value": value} for frame, value in expansion_keys]}}


def _ellipse_mask(diameter: float, expansion_keys: list[tuple[int, float]]) -> dict:
    return {"type": "ellipse", "mode": "intersect", "position": [0, 0],
            "size": [diameter, diameter],
            "expansion_track": {"keyframes": [
                {"frame": frame, "value": value} for frame, value in expansion_keys]}}


def _diagonal_mask() -> dict:
    start = [
        {"type": "move_to", "point": [-220, -300]},
        {"type": "line_to", "point": [-140, -300]},
        {"type": "line_to", "point": [240, 300]},
        {"type": "line_to", "point": [160, 300]},
        {"type": "close"},
    ]
    end = [
        {"type": "move_to", "point": [-190, -240]},
        {"type": "line_to", "point": [190, -240]},
        {"type": "line_to", "point": [190, 240]},
        {"type": "line_to", "point": [-190, 240]},
        {"type": "close"},
    ]
    return {"type": "path", "mode": "intersect", "path": start, "target_path": end,
            "animation": {"keyframes": [
                {"frame": 0, "value": 0.0}, {"frame": 24, "value": 1.0}]}}


def background_layers(total: int, style: dict) -> list[dict]:
    return [fill_layer("photo-motion-background", 0, total, [0.025, 0.034, 0.05, 1.0]),
            layer("photo-motion-top-rule", "shape", 0, total,
                  size=[110, 3], position=[W/2, 101],
                  shape={"type": "rect", "fill": rgba(style["accent"])})]


def recipe_ids(family: dict) -> list[str]:
    ids = [recipe for group in family["recipe_groups"] for recipe in group["recipes"]]
    if len(ids) != 18 or len(set(ids)) != len(ids):
        raise ValueError("photo_motion_v1 must contain 18 unique recipes")
    return ids


def _polaroid_recipe(recipe: str, index: int, start: int, duration: int,
                     style: dict, asset: str) -> list[dict]:
    cx, cy = W / 2, H / 2 + 10
    if recipe.endswith("drop_settle"):
        poses = [pose(0, cx+120, cy-560, z=80, scale=1.08, rotation=-9, opacity=0),
                 pose(12, cx+10, cy+12, z=20, scale=.98, rotation=2.5),
                 pose(21, cx, cy, z=0, scale=1, rotation=0), pose(duration-1, cx, cy)]
    elif recipe.endswith("rotate_in"):
        poses = [pose(0, cx, cy, rotation=-20, scale=.85, opacity=0),
                 pose(18, cx, cy, rotation=4, scale=1.04), pose(30, cx, cy, rotation=-1),
                 pose(38, cx, cy, rotation=0), pose(duration-1, cx, cy)]
    elif recipe.endswith("push_focus"):
        poses = [pose(0,cx,cy,z=-60,scale=.92), pose(22,cx,cy,z=0,scale=1),
                 pose(44,cx,cy,z=0,scale=1.04), pose(duration-1,cx,cy,z=0,scale=1.04)]
    else:  # slide_swap
        poses = [pose(0,cx-640,cy,rotation=-3,opacity=0), pose(18,cx,cy,rotation=0),
                 pose(43,cx,cy,rotation=0), pose(58,cx+720,cy,rotation=5,opacity=0)]
    return card_parts(f"{recipe}-{index}", asset, (cx,cy), start, duration, poses,
                      style, kind="polaroid")


def _slot(slot: str) -> dict:
    return {
        "back2": {"dx": -36, "dy": -66, "z": -180, "scale": .82, "rotation": 3.2, "opacity": .52},
        "back1": {"dx": -18, "dy": -34, "z": -90, "scale": .91, "rotation": -2.0, "opacity": .78},
        "hero": {"dx": 0, "dy": 0, "z": 20, "scale": 1.0, "rotation": 0.0, "opacity": 1.0},
        "exit": {"dx": 42, "dy": 95, "z": 110, "scale": 1.08, "rotation": 5.0, "opacity": 0.0},
        "off": {"dx": 0, "dy": -440, "z": -280, "scale": .75, "rotation": 8.0, "opacity": 0.0},
    }[slot]


def resolve_stack_slots(card_count: int, active_index: int, *, browser=False) -> list[dict]:
    """Resolve active/back/exit card slots without per-card authored keyframes."""
    if card_count < 1 or not 0 <= active_index < card_count:
        raise ValueError("stack requires cards and a valid active index")
    slots = []
    for card_index in range(card_count):
        rel = card_index - active_index
        if rel == 0:
            name = "hero"
        elif rel == 1:
            name = "back1"
        elif rel == 2:
            name = "back2"
        elif rel < 0:
            name = "exit"
        else:
            name = "off"
        slots.append({"card_index": card_index, "slot": name, **_slot(name)})
    return slots


def _stack_recipe(recipe: str, index: int, start: int, duration: int,
                  style: dict, assets: tuple[str, ...]) -> list[dict]:
    browser = recipe.endswith("browser_shuffle")
    count = 4 if browser else 3
    centers = (W/2, H/2 + 22)
    parts = []
    mode = "vertical" if recipe.endswith("vertical_cycle") else "depth"
    for card_index in range(count):
        # Slot states are generated at endpoints; the layer tracks interpolate them.
        first = resolve_stack_slots(count, 0, browser=browser)[card_index]
        final_active = 1 if card_index < 2 else 0
        second = resolve_stack_slots(count, 1, browser=browser)[card_index]
        if mode == "vertical":
            first = dict(first, dy=first["dy"]*1.3, scale=first["scale"]*.96)
            second = dict(second, dy=second["dy"]*1.3, scale=second["scale"]*.96)
        poses = []
        for f, slot in ((0, first), (18, first), (30, second), (duration-1, second)):
            poses.append(pose(f, centers[0] + slot["dx"], centers[1] + slot["dy"],
                              z=slot["z"], scale=slot["scale"], rotation=slot["rotation"],
                              opacity=slot["opacity"]))
        if recipe.endswith("focus_handoff"):
            poses = [pose(0, centers[0]-120, centers[1], z=-70, scale=.9),
                     pose(18, centers[0], centers[1], z=20, scale=1),
                     pose(30, centers[0]+24, centers[1]+84, z=100, scale=1.06, opacity=.2),
                     pose(duration-1, centers[0]+24, centers[1]+84, z=100, scale=1.06, opacity=.2)] if card_index == 0 else poses
        parts.extend(card_parts(f"{recipe}-{index}-card-{card_index}", assets[card_index % len(assets)],
                                centers, start, duration, poses, style,
                                browser=browser))
    return parts


def deterministic_pile_slots(count: int, seed: int) -> list[dict]:
    rng = random.Random(seed)
    slots = []
    for index in range(count):
        slots.append({"index": index,
                      "x": round(rng.uniform(-22, 22), 4),
                      "y": round(rng.uniform(-18, 18), 4),
                      "rotation": round(rng.uniform(-7.0, 7.0), 4),
                      "z": float(index * 9),
                      "scale": round(rng.uniform(.965, 1.0), 4)})
    return slots


def _pile_recipe(recipe: str, index: int, start: int, duration: int,
                 style: dict, assets: tuple[str, ...], seed=412) -> list[dict]:
    slots = deterministic_pile_slots(4, seed + index)
    center = (W/2, H/2 + 34)
    result = []
    top_index = max(slot["index"] for slot in slots)
    for slot in slots:
        card_index = slot["index"]
        target_x, target_y = center[0] + slot["x"], center[1] + slot["y"]
        target_rot = slot["rotation"]
        if recipe == "photo_pile_drop":
            poses = [pose(0,target_x+(card_index%2)*75-35,target_y-520,z=180+slot["z"],
                         scale=.88,rotation=target_rot+13,opacity=0),
                     pose(10,target_x,target_y+12,z=slot["z"]+12,scale=1.02,rotation=target_rot-2),
                     pose(18,target_x,target_y,z=slot["z"],scale=slot["scale"],rotation=target_rot),
                     pose(duration-1,target_x,target_y,z=slot["z"],scale=slot["scale"],rotation=target_rot)]
        elif card_index == top_index and recipe == "photo_pile_top_slide":
            poses = [pose(0,target_x,target_y,z=slot["z"],rotation=target_rot),
                     pose(34,target_x-540,target_y-40,z=slot["z"]+80,rotation=target_rot-8,opacity=0),
                     pose(duration-1,target_x-540,target_y-40,z=slot["z"]+80,rotation=target_rot-8,opacity=0)]
        elif card_index == top_index and recipe == "photo_pile_top_flip":
            poses = [pose(0,target_x,target_y,z=slot["z"],rotation=target_rot),
                     pose(25,target_x,target_y-12,z=slot["z"]+60,scale=.92,rotation=target_rot),
                     pose(38,target_x,target_y+470,z=slot["z"]+110,scale=.82,rotation=target_rot+8,opacity=0),
                     pose(duration-1,target_x,target_y+470,z=slot["z"]+110,scale=.82,rotation=target_rot+8,opacity=0)]
        elif card_index == top_index and recipe == "photo_pile_top_throw":
            poses = [pose(0,target_x,target_y,z=slot["z"],rotation=target_rot),
                     pose(20,target_x+70,target_y-500,z=slot["z"]+240,scale=1.08,rotation=target_rot-8),
                     pose(37,target_x+850,target_y-780,z=slot["z"]+400,scale=.88,rotation=target_rot-28,opacity=0),
                     pose(duration-1,target_x+850,target_y-780,z=slot["z"]+400,scale=.88,rotation=target_rot-28,opacity=0)]
        else:
            poses = [pose(0,target_x,target_y,z=slot["z"],scale=slot["scale"],rotation=target_rot),
                     pose(duration-1,target_x,target_y,z=slot["z"],scale=slot["scale"],rotation=target_rot)]
        result.extend(card_parts(f"{recipe}-{index}-pile-{card_index}", assets[card_index],
                                 center, start, duration, poses, style, kind="polaroid"))
    return result


def _mask_recipe(recipe: str, index: int, start: int, duration: int,
                 style: dict, asset: str) -> list[dict]:
    center = (W/2, H/2+20)
    w, h = 600.0, 700.0
    expansion = [(-max(w,h), 0), (22, 0)]
    mask = _rounded_mask(w, h, 60, [(0, -max(w,h)), (22, 0)])
    effects = None
    poses = [pose(0,*center,scale=.94), pose(16,*center,scale=1.22),
             pose(30,*center,scale=1.0), pose(duration-1,*center,scale=1.0)]
    if recipe == "photo_slit_reveal":
        mask = _rounded_mask(w, 170, 84, [(0,-500),(24,0)])
    elif recipe == "photo_circle_focus":
        mask = _ellipse_mask(510, [(0,-400),(24,0)])
    elif recipe == "photo_diagonal_wipe":
        mask = _diagonal_mask()
    elif recipe == "photo_radial_burst":
        mask = _ellipse_mask(640, [(0,-500),(26,0)])
        effects = [{"type":"radial_blur","center":[.5,.5],"amount":1.0,
                    "render_samples":10,"preview_samples":6}]
        poses = [pose(0,*center,scale=.72),pose(10,*center,scale=1.3),
                 pose(24,*center,scale=1.04),pose(duration-1,*center,scale=1.0)]
    elif recipe == "photo_mask_expand":
        mask = _rounded_mask(w, h, 26, [(0,-680),(23,0)])
        poses = [pose(0,*center,scale=.94),pose(23,*center,scale=1),pose(duration-1,*center,scale=1)]
    elif recipe == "photo_capsule_zoom_reveal":
        mask = _rounded_mask(w, 190, 95, [(0,-500),(18,0),(48,260)])
        poses = [pose(0,*center,scale=1),pose(8,*center,scale=1.36),
                 pose(22,*center,scale=1.05),pose(duration-1,*center,scale=1.02)]
        effects = [{"type":"radial_blur","center":[.5,.5],"amount":.42,
                    "render_samples":8,"preview_samples":4}]
    img = layer(f"{recipe}-{index}-masked-photo", "image", start, duration,
                asset=asset, size=[w,h], position=list(center), fit="cover", enable_3d=True,
                masks=[mask], style={"shadow":{"color":style["shadow"],"offset":[0,14],"opacity":.42,"blur":24}},
                animation={"tracks": [track("scale",[(p["frame"],p["scale"]) for p in poses])]},
                **({"effects":effects} if effects else {}))
    return [img]


def build_gallery(family: dict | None = None) -> dict:
    family = family or json.loads(FAMILY_FILE.read_text())
    styles = family["style_tokens"]
    recipe_list = [(group["id"], recipe) for group in family["recipe_groups"] for recipe in group["recipes"]]
    ids = recipe_ids(family)
    total = SEGMENT * len(ids)
    style_names = ("archive", "browser", "tabletop", "darkroom")
    layers = background_layers(total, styles["archive"])
    for index, (group, recipe) in enumerate(recipe_list):
        start, style_name = index*SEGMENT, style_names[index % len(style_names)]
        style = styles[style_name]
        layers.append(text_layer(f"{recipe}-eyebrow", f"PHOTO MOTION V1  /  {group.upper()}",
                                 start+1, SEGMENT-1, 118, style["accent"], 15, bold=True))
        layers.append(text_layer(f"{recipe}-name", recipe.replace("_", " ").upper(),
                                 start+4, SEGMENT-4, 173, "#F2F4F7", 26, bold=True))
        asset = PHOTO_ASSETS[index % len(PHOTO_ASSETS)]
        if group == "photo_cards":
            layers.extend(_polaroid_recipe(recipe,index,start,SEGMENT,style,asset))
        elif group == "depth_stack":
            layers.extend(_stack_recipe(recipe,index,start,SEGMENT,style,PHOTO_ASSETS))
        elif group == "photo_pile":
            layers.extend(_pile_recipe(recipe,index,start,SEGMENT,style,PHOTO_ASSETS,seed=421))
        else:
            layers.extend(_mask_recipe(recipe,index,start,SEGMENT,style,asset))
    return {"schema":"chronon.render-plan.v3","version":3,"job_id":"canary_photo_motion_v1",
            "canvas":{"width":W,"height":H,"fps_num":FPS,"fps_den":1,"duration_frames":total},
            "layers":layers,"output":{"path":"canary_photo_motion_v1.mp4","format":"mp4","codec":"h264"}}


def build_torture(family: dict | None = None) -> dict:
    family = family or json.loads(FAMILY_FILE.read_text())
    styles=family["style_tokens"]
    duration=15*FPS
    layers=background_layers(duration,styles["tabletop"])
    ids=set(recipe_ids(family))
    sequence=("photo_polaroid_drop_settle","photo_stack_depth_cycle","photo_pile_drop",
              "photo_pile_top_flip","photo_capsule_zoom_reveal","photo_radial_burst")
    for index,recipe in enumerate(sequence):
        if recipe not in ids: raise ValueError(f"torture recipe missing from catalog: {recipe}")
        start=index*75
        style=styles[("archive","browser","tabletop","darkroom")[index%4]]
        asset=PHOTO_ASSETS[index%len(PHOTO_ASSETS)]
        layers.append(text_layer(f"torture-label-{index}",recipe.upper().replace("_"," "),
                                 start+2,73,125,style["accent"],17,bold=True))
        if recipe.startswith("photo_polaroid"):
            layers.extend(_polaroid_recipe(recipe,index,start,75,style,asset))
        elif recipe.startswith("photo_stack"):
            layers.extend(_stack_recipe(recipe,index,start,75,style,PHOTO_ASSETS))
        elif recipe.startswith("photo_pile"):
            layers.extend(_pile_recipe(recipe,index,start,75,style,PHOTO_ASSETS,seed=912))
        else:
            layers.extend(_mask_recipe(recipe,index,start,75,style,asset))
    return {"schema":"chronon.render-plan.v3","version":3,"job_id":"canary_photo_motion_torture_v1",
            "canvas":{"width":W,"height":H,"fps_num":FPS,"fps_den":1,"duration_frames":duration},
            "layers":layers,"output":{"path":"canary_photo_motion_torture_v1.mp4","format":"mp4","codec":"h264"}}


def build_plans(family: dict | None = None) -> dict[str,dict]:
    family=family or json.loads(FAMILY_FILE.read_text())
    return {"canary_photo_motion_v1":build_gallery(family),
            "canary_photo_motion_torture_v1":build_torture(family)}


def main() -> int:
    parser=argparse.ArgumentParser(description=__doc__)
    mode=parser.add_mutually_exclusive_group()
    mode.add_argument("--plans",action="store_true",help="write gallery and torture plans")
    mode.add_argument("--validate",action="store_true",help="write and validate plans with Chronon3D")
    mode.add_argument("--render",action="store_true",help="write, validate and render plans")
    parser.add_argument("--cli",type=Path,help="chronon3d_cli path")
    args=parser.parse_args()
    OUT.mkdir(parents=True,exist_ok=True)
    plans=build_plans()
    for job_id,plan in plans.items():
        path=OUT/f"{job_id}.plan.json"
        path.write_text(json.dumps(plan,indent=2)+"\n")
        print(f"wrote {path}")
    if args.validate or args.render:
        cli=args.cli or next((candidate for candidate in CLI_CANDIDATES if candidate.is_file()),None)
        if cli is None: parser.error("chronon3d_cli not found; pass --cli")
        for job_id in plans:
            path=OUT/f"{job_id}.plan.json"
            subprocess.run([str(cli),"validate","--plan",str(path),"--assets-root",str(WORKSPACE)],check=True)
            print(f"validated {job_id}",flush=True)
            if args.render:
                subprocess.run([str(cli),"render","--plan",str(path),"--assets-root",str(WORKSPACE),
                                "--output",str(OUT/f"{job_id}.mp4"),"--backend","software"],check=True)
    return 0


if __name__=="__main__":
    raise SystemExit(main())
