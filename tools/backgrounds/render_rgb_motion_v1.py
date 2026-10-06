#!/usr/bin/env python3
"""Expand deterministic RGB motion recipes into ordinary Chronon render-plan layers."""
from __future__ import annotations

import argparse
import json
import math
import random
import subprocess
from pathlib import Path

TEMPLATE = Path(__file__).resolve().parents[2]
WORKSPACE = TEMPLATE.parent
FAMILY_FILE = TEMPLATE / "catalog/rgb_motion_v1.json"
OUT = TEMPLATE / "out/rgb_motion_v1"
WIDTH, HEIGHT, FPS, SEGMENT = 960, 540, 30, 60
FONT = "Chronon3d/assets/fonts/Inter-Bold.ttf"
RGB = {"r": "#FF2638", "g": "#32FF92", "b": "#3187FF"}
SPECTRUM = ["#FF2B32", "#FF9D22", "#FFE746", "#41F477", "#25DDF1", "#426BFF", "#B646FF"]
CLI_CANDIDATES = (
    WORKSPACE / "Chronon3d/build/chronon/linux-video-fast-dev/apps/chronon3d_cli/chronon3d_cli",
    WORKSPACE / "Chronon3d/build/chronon/linux-fast-dev/apps/chronon3d_cli/chronon3d_cli",
)


def track(prop: str, values: list[tuple[int, float]], easing="linear") -> dict:
    canonical = {int(frame): float(value) for frame, value in values}
    return {"property": prop, "easing": easing,
            "keyframes": [{"frame": frame, "value": canonical[frame]} for frame in sorted(canonical)]}


def text_layer(id_: str, start: int, duration: int, *, color="#F8FAFF", x=WIDTH/2,
               y=HEIGHT/2, opacity=1.0, scale_keys=None, x_keys=None, y_keys=None,
               rotation_keys=None, effects=None, masks=None, blend="add") -> dict:
    tracks = [track("opacity", [(0, opacity), (duration-1, opacity)])]
    if scale_keys:
        tracks.append(track("scale", scale_keys))
    if x_keys:
        tracks.append(track("position_x", x_keys))
    if y_keys:
        tracks.append(track("position_y", y_keys))
    if rotation_keys:
        tracks.append(track("rotation_z", rotation_keys))
    result = {
        "id": id_, "type": "text", "start_frame": start, "duration_frames": duration,
        "text": "CHRONON", "size": [860, 190], "position": [x, y],
        "style": {"font": FONT, "font_size": 132, "min_font_size": 100,
                  "max_font_size": 132, "fit_mode": "shrink_only", "fill": color},
        "blend_mode": blend, "animation": {"tracks": tracks}
    }
    if effects:
        result["effects"] = effects
    if masks:
        result["masks"] = masks
    return result


def channel_branch(channel: str, start: int, duration: int, *, offset=(0.0, 0.0),
                   scale=1.0, rotation=0.0, opacity=1.0, phase=0.0,
                   motion=None, warp=False, radial=False) -> dict:
    effects = []
    if warp:
        effects.append({"type": "wave_warp", "direction": [0.0, 1.0],
                        "amplitude": 8.0, "wavelength": 90.0, "speed": .65, "phase": phase})
    if radial:
        effects.append({"type": "radial_blur", "center": [.5, .5], "amount": .28,
                        "render_samples": 8, "preview_samples": 4})
    x_keys = [(0, WIDTH/2 + offset[0]), (duration-1, WIDTH/2 + offset[0])]
    y_keys = [(0, HEIGHT/2 + offset[1]), (duration-1, HEIGHT/2 + offset[1])]
    if motion:
        x_keys = [(frame, WIDTH/2 + dx + offset[0]) for frame, dx, _ in motion]
        y_keys = [(frame, HEIGHT/2 + dy + offset[1]) for frame, _, dy in motion]
    return text_layer(f"rgb-{channel}-{start}-{phase}", start, duration,
                      color=RGB[channel], x_keys=x_keys, y_keys=y_keys,
                      scale_keys=[(0, scale), (duration-1, scale)],
                      rotation_keys=[(0, rotation), (duration-1, rotation)],
                      opacity=opacity, effects=effects)


def resolve_rgb_channel_transform(start: int, duration: int, channels: dict,
                                  *, component_transform=False) -> list[dict]:
    """Typed RGB branch expansion; channels map r/g/b to independent transform options."""
    if duration < 2 or set(channels) - {"r", "g", "b"}:
        raise ValueError("RGB branch transform needs duration >= 2 and only r/g/b channels")
    layers = []
    for index, channel in enumerate(("r", "g", "b")):
        options = channels.get(channel, {})
        layers.append(channel_branch(channel, start, duration,
                                     offset=options.get("offset", (0.0, 0.0)),
                                     scale=options.get("scale", 1.0),
                                     rotation=options.get("rotation", 0.0),
                                     opacity=options.get("opacity", 1.0),
                                     phase=options.get("phase", index*2.1),
                                     warp=options.get("warp", False),
                                     radial=options.get("radial", False),
                                     motion=options.get("motion")))
    # A sharp neutral core restores legibility; selected recipes also exercise
    # Chronon3D's component-preserving, per-channel affine transform effect.
    core_effects = []
    if component_transform:
        effect = {"type": "rgb_channel_transform", "red_offset": 0, "blue_offset": 0}
        for channel in ("r", "g", "b"):
            options = channels.get(channel, {})
            effect[{"r":"red_transform","g":"green_transform","b":"blue_transform"}[channel]] = {
                "translation": list(options.get("effect_offset", options.get("offset", (0.0, 0.0)))),
                "scale": [options.get("scale", 1.0), options.get("scale", 1.0)],
                "rotation": options.get("rotation", 0.0),
                "opacity": options.get("opacity", 1.0),
            }
        core_effects = [effect]
    layers.append(text_layer(f"rgb-core-{start}", start, duration, color="#F8FAFF",
                             blend="normal", effects=core_effects))
    return layers


def resolve_slice_transform(start: int, duration: int, *, count=14, orientation="horizontal",
                            amplitude=58.0, seed=42, posterized=False) -> list[dict]:
    if not 1 <= count <= 32 or orientation not in {"horizontal", "vertical"}:
        raise ValueError("slice transform supports 1..32 horizontal/vertical slices")
    rng = random.Random(seed)
    extent = 190.0 if orientation == "horizontal" else 860.0
    slice_size = extent / count
    layers = []
    for index in range(count):
        displacement = round(rng.uniform(-amplitude, amplitude), 4)
        if posterized:
            displacement = round(displacement / 18.0) * 18.0
        hit = max(1, round((duration - 1) * .22))
        release = max(hit + 1, round((duration - 1) * .52))
        if orientation == "horizontal":
            mask = {"type": "rect", "mode": "intersect", "position": [0, -extent/2 + slice_size*(index+.5)],
                    "size": [860, slice_size + .5]}
            x_values = [(0, WIDTH/2), (hit, WIDTH/2+displacement),
                        (release, WIDTH/2+displacement), (duration-1, WIDTH/2)]
            y_values = [(0, HEIGHT/2), (duration-1, HEIGHT/2)]
        else:
            mask = {"type": "rect", "mode": "intersect", "position": [-extent/2 + slice_size*(index+.5), 0],
                    "size": [slice_size + .5, 190]}
            x_values = [(0, WIDTH/2), (duration-1, WIDTH/2)]
            y_values = [(0, HEIGHT/2), (hit, HEIGHT/2+displacement),
                        (release, HEIGHT/2+displacement), (duration-1, HEIGHT/2)]
        # Preserve strictly increasing frame indices even for micro cuts.
        x_values = sorted({frame: value for frame, value in x_values}.items())
        y_values = sorted({frame: value for frame, value in y_values}.items())
        x_values = [(frame, value) for frame, value in x_values]
        y_values = [(frame, value) for frame, value in y_values]
        layers.append(text_layer(f"slice-{orientation}-{index:02d}-{start}", start, duration,
                                 color=SPECTRUM[index % len(SPECTRUM)], x_keys=x_values,
                                 y_keys=y_values, masks=[mask], opacity=.92))
    layers.append(text_layer(f"slice-core-{start}", start, duration, color="#F8FAFF", blend="normal"))
    return layers


def resolve_multi_tap_trail(start: int, duration: int, *, taps=12, step=(0.0, 7.0),
                            palette=None, decay=.78, scale_step=0.0, rotation_step=0.0,
                            opacity=1.0) -> list[dict]:
    if not 1 <= taps <= 24 or not 0.0 <= decay <= 1.0:
        raise ValueError("multi-tap trail supports 1..24 taps and decay in [0,1]")
    colors = palette or SPECTRUM
    layers = []
    for index in reversed(range(taps)):
        tint = colors[round(index*(len(colors)-1)/max(taps-1, 1))]
        alpha = opacity * (decay ** index)
        dx, dy = step[0]*index, step[1]*index
        size = 1.0 + scale_step*index
        turn = rotation_step*index
        layers.append(text_layer(f"trail-tap-{index:02d}-{start}", start, duration,
                                 color=tint, x_keys=[(0, WIDTH/2+dx), (duration-1, WIDTH/2+dx)],
                                 y_keys=[(0, HEIGHT/2+dy), (duration-1, HEIGHT/2+dy)],
                                 scale_keys=[(0,size),(duration-1,size)],
                                 rotation_keys=[(0,turn),(duration-1,turn)], opacity=alpha))
    layers.append(text_layer(f"trail-core-{start}", start, duration, color="#FFFFFF", blend="normal"))
    return layers


def _sample_linear(keys: list[tuple[int, float]], frame: float) -> float:
    if frame <= keys[0][0]: return float(keys[0][1])
    if frame >= keys[-1][0]: return float(keys[-1][1])
    for (f0, v0), (f1, v1) in zip(keys, keys[1:]):
        if f0 <= frame <= f1:
            u = (frame-f0)/(f1-f0)
            return float(v0 + (v1-v0)*u)
    return float(keys[-1][1])


def resolve_velocity_rgb_channels(start: int, duration: int,
                                  trajectory: list[tuple[int,float,float]],
                                  *, split_seconds=.12) -> list[dict]:
    """Drive channel separation from finite-difference screen velocity."""
    if duration < 2 or len(trajectory) < 2 or not math.isfinite(split_seconds) or split_seconds < 0:
        raise ValueError("velocity RGB needs a bounded trajectory and nonnegative split time")
    x_track=[(int(f),float(x)) for f,x,_ in trajectory]
    y_track=[(int(f),float(y)) for f,_,y in trajectory]
    tracks={channel:[] for channel in ("r","g","b")}
    for frame in range(duration):
        prior=max(0,frame-1)
        x=_sample_linear(x_track,frame); y=_sample_linear(y_track,frame)
        vx=(_sample_linear(x_track,frame)-_sample_linear(x_track,prior))*FPS
        vy=(_sample_linear(y_track,frame)-_sample_linear(y_track,prior))*FPS
        for channel,sign in (("r",-1),("g",0),("b",1)):
            tracks[channel].append((frame,x+sign*vx*split_seconds,y+sign*vy*split_seconds))
    layers=[]
    for channel in ("r","g","b"):
        layers.append(channel_branch(channel,start,duration,motion=tracks[channel]))
    layers.append(text_layer(f"velocity-core-{start}",start,duration,color="#FFFFFF",blend="normal"))
    return layers


def resolve_analytic_temporal_channels(start: int, duration: int, trajectory: list[tuple[int,float,float]],
                                       offsets=(-2,0,2)) -> list[dict]:
    """Sample a pure transform trajectory at channel-specific times; no hidden frame cache."""
    if len(offsets) != 3 or len(trajectory) < 2:
        raise ValueError("temporal RGB transform needs three offsets and a trajectory")
    x_track=[(int(f),float(x)) for f,x,_ in trajectory]
    y_track=[(int(f),float(y)) for f,_,y in trajectory]
    result=[]
    for channel, offset in zip(("r","g","b"), offsets):
        xs=[]; ys=[]
        for frame in range(duration):
            sample=max(0,min(duration-1,frame+offset))
            xs.append((frame,WIDTH/2+_sample_linear(x_track,sample)))
            ys.append((frame,HEIGHT/2+_sample_linear(y_track,sample)))
        result.append(channel_branch(channel,start,duration,
                                    motion=[(f,x-WIDTH/2,y-HEIGHT/2)
                                            for f,(_,x),(_,y) in zip(range(duration),xs,ys)]))
    result.append(text_layer(f"temporal-core-{start}",start,duration,color="#FFFFFF",blend="normal"))
    return result


def _recipe_layers(recipe: dict, start: int, duration: int, index: int) -> list[dict]:
    ident=recipe["id"]
    if ident == "rgb_wave_in":
        return resolve_rgb_channel_transform(start,duration,{
            "r":{"offset":(-24,4),"rotation":-1.5,"phase":0,"warp":True},
            "g":{"offset":(0,0),"phase":2.1,"warp":True},
            "b":{"offset":(24,-4),"rotation":1.5,"phase":4.2,"warp":True}}, component_transform=True)
    if ident in {"rgb_slice_break","rgb_block_shuffle"}:
        return resolve_slice_transform(start,duration,count=18 if ident.endswith("break") else 24,
                                       amplitude=76 if ident.endswith("break") else 62,
                                       seed=int(recipe.get("seed", 1701))+index,posterized=ident.endswith("shuffle"))
    if ident in {"rgb_vertical_trail","rgb_prism_smear","rgb_ghost_echo","rgb_spectrum_drop"}:
        palette = list(RGB.values()) if ident == "rgb_ghost_echo" else SPECTRUM
        taps = 16 if ident in {"rgb_prism_smear","rgb_spectrum_drop"} else 12
        step=(0,9) if ident in {"rgb_vertical_trail","rgb_spectrum_drop"} else (5,3)
        return resolve_multi_tap_trail(start,duration,taps=taps,step=step,palette=palette,
                                       decay=.82 if ident == "rgb_ghost_echo" else .72,
                                       rotation_step=.12 if ident == "rgb_prism_smear" else 0)
    if ident == "rgb_velocity_snap":
        return resolve_velocity_rgb_channels(start,duration,
            [(0,-150,30),(10,-92,18),(22,-18,4),(34,0,0),(duration-1,0,0)], split_seconds=.12)
    if ident == "rgb_temporal_split":
        return resolve_analytic_temporal_channels(start,duration,[(0,-170,24),(16,0,0),(duration-1,0,0)],(-3,0,3))
    if ident == "rgb_radial_burst":
        return resolve_rgb_channel_transform(start,duration,{
            "r":{"offset":(-18,4),"scale":1.02,"rotation":-1.2,"radial":True},
            "g":{"offset":(0,0),"radial":True},
            "b":{"offset":(18,-4),"scale":1.02,"rotation":1.2,"radial":True}}, component_transform=True)
    raise ValueError(f"unknown rgb recipe: {ident}")


RAPID_TRANSITIONS = {
    "rgb_split_whip": 7,
    "rgb_snap": 5,
    "rgb_zoom_punch": 8,
    "rgb_horizontal_tear": 8,
    "rgb_glitch_cut": 6,
    "rgb_lens_snap": 8,
    "rgb_spin_blur": 8,
    "prismatic_flash": 8,
    "lightleak_rgb_combo": 10,
    "film_burn_rgb": 10,
}


def _set_track_keys(layer: dict, prop: str, keys: list[tuple[int, float]]) -> None:
    for item in layer["animation"]["tracks"]:
        if item["property"] == prop:
            item["keyframes"] = [{"frame": int(frame), "value": float(value)} for frame, value in keys]
            return
    layer["animation"]["tracks"].append(track(prop, keys))


def _rapid_transition_layers(ident: str, duration: int, start: int = 0) -> list[dict]:
    end = duration - 1
    mid = max(1, end // 2)
    if ident == "rgb_snap":
        peak = max(1, round(end * .35))
        def motion(sign: float):
            return [(frame, sign * 18.0 * (frame / peak if frame <= peak else
                                           max(0.0, (end - frame) / (end - peak))), 0.0)
                    for frame in range(duration)]
        return resolve_rgb_channel_transform(start, duration, {
            "r": {"motion": motion(-1.0), "effect_offset": (-18.0, 0.0)},
            "g": {"motion": motion(0.0)},
            "b": {"motion": motion(1.0), "effect_offset": (18.0, 0.0)},
        }, component_transform=True)
    if ident == "rgb_split_whip":
        return resolve_velocity_rgb_channels(
            start, duration, [(0, -190.0, 0.0), (mid, 0.0, 0.0), (end, 190.0, 0.0)],
            split_seconds=.018)
    if ident == "rgb_zoom_punch":
        layers = resolve_rgb_channel_transform(start, duration, {
            "r": {"offset": (-8, 0), "effect_offset": (-8, 0), "radial": True},
            "g": {"radial": True},
            "b": {"offset": (8, 0), "effect_offset": (8, 0), "radial": True},
        }, component_transform=True)
        for layer in layers[:3]:
            _set_track_keys(layer, "scale", [(0, .88), (mid, 1.16), (end, 1.0)])
        return layers
    if ident in {"rgb_horizontal_tear", "rgb_glitch_cut"}:
        count = 6 if ident == "rgb_horizontal_tear" else 4
        amplitude = 48.0 if ident == "rgb_horizontal_tear" else 72.0
        slices = resolve_slice_transform(start, duration, count=count, orientation="horizontal",
                                         amplitude=amplitude, seed=1986)
        split = resolve_rgb_channel_transform(start, duration, {
            "r": {"offset": (-5, 0)}, "g": {}, "b": {"offset": (5, 0)},
        }, component_transform=True)
        return slices + split
    if ident == "rgb_lens_snap":
        def motion(offset: float):
            return [(frame, offset * (1.0 - frame / end), 0.0) for frame in range(duration)]
        return resolve_rgb_channel_transform(start, duration, {
            "r": {"motion": motion(-24.0), "effect_offset": (-24.0, 0.0), "radial": True},
            "g": {"radial": True},
            "b": {"motion": motion(24.0), "effect_offset": (24.0, 0.0), "radial": True},
        }, component_transform=True)
    if ident == "rgb_spin_blur":
        layers = resolve_rgb_channel_transform(start, duration, {
            "r": {"offset": (-8, 0), "effect_offset": (-8, 0), "radial": True},
            "g": {"radial": True},
            "b": {"offset": (8, 0), "effect_offset": (8, 0), "radial": True},
        }, component_transform=True)
        for layer, turns in zip(layers[:3], (-.10, 0.0, .10)):
            _set_track_keys(layer, "rotation_z", [(0, turns), (mid, 0.0), (end, -turns)])
        return layers
    if ident in {"prismatic_flash", "lightleak_rgb_combo", "film_burn_rgb"}:
        channels = resolve_rgb_channel_transform(start, duration, {
            "r": {"offset": (-12, 0), "radial": ident == "prismatic_flash"},
            "g": {"radial": ident != "film_burn_rgb"},
            "b": {"offset": (12, 0), "radial": ident == "prismatic_flash"},
        })
        if ident == "prismatic_flash":
            # A short white core flash with rainbow channel fringes.
            flash = text_layer(f"prismatic-whiteout-{start}", start, duration,
                               color="#FFFFFF", blend="normal")
            _set_track_keys(flash, "opacity", [(0, 0.0), (mid, .92), (end, 0.0)])
            return channels[:3] + [flash]
        if ident == "lightleak_rgb_combo":
            # Oversized warm source crosses behind the channel fringes; the
            # renderer's canonical color/effect pipeline supplies the bloom.
            leak = text_layer(f"warm-leak-{start}", start, duration, color="#FF8A35",
                              x_keys=[(0, -WIDTH*.65), (mid, WIDTH*.5), (end, WIDTH*1.65)],
                              scale_keys=[(0, 2.4), (mid, 3.2), (end, 2.4)], opacity=.34)
            return channels[:3] + [leak]
        slices = resolve_slice_transform(start, duration, count=5, amplitude=44,
                                         seed=4104, orientation="horizontal")
        return slices + channels[:3]
    raise ValueError(f"unknown rapid RGB transition: {ident}")


def build_transition_plans() -> dict[str, dict]:
    """Build the ten proposal RGB and hybrid accents as renderable short cuts."""
    plans = {}
    for ident, duration in RAPID_TRANSITIONS.items():
        layers = [_backplate(0, duration),
                  text_layer(f"transition-source-{ident}", 0, duration,
                             color="#F8FAFF", blend="normal")]
        layers.extend(_rapid_transition_layers(ident, duration))
        plans[ident] = {
            "schema": "chronon.render-plan.v3", "version": 3, "job_id": ident,
            "canvas": {"width": WIDTH, "height": HEIGHT, "fps_num": FPS,
                       "fps_den": 1, "duration_frames": duration},
            "layers": layers,
            "output": {"path": f"{ident}.mp4", "format": "mp4", "codec": "h264"},
        }
    return plans


def _backplate(start: int, duration: int) -> dict:
    return {"id":f"rgb-backplate-{start}","type":"color","start_frame":start,
            "duration_frames":duration,"color":[.004,.007,.018,1],"size":[WIDTH,HEIGHT],
            "position":[WIDTH/2,HEIGHT/2],"screen_space":True}


def build_gallery(family=None) -> dict:
    family=family or json.loads(FAMILY_FILE.read_text())
    recipes=family["recipes"]
    total=SEGMENT*len(recipes)
    layers=[_backplate(0,total)]
    for index,recipe in enumerate(recipes):
        start=index*SEGMENT
        layers.extend(_recipe_layers(recipe,start,SEGMENT,index))
    return {"schema":"chronon.render-plan.v3","version":3,"job_id":"canary_rgb_motion_v1",
            "canvas":{"width":WIDTH,"height":HEIGHT,"fps_num":FPS,"fps_den":1,"duration_frames":total},
            "layers":layers,"output":{"path":"canary_rgb_motion_v1.mp4","format":"mp4","codec":"h264"}}


def build_torture(family=None) -> dict:
    family=family or json.loads(FAMILY_FILE.read_text())
    recipes=family["recipes"]
    total=10*FPS
    sequence=("rgb_wave_in","rgb_slice_break","rgb_vertical_trail","rgb_radial_burst","rgb_velocity_snap")
    by_id={r["id"]:r for r in recipes}
    layers=[_backplate(0,total)]
    segment=60
    for index,ident in enumerate(sequence):
        start=index*segment
        layers.extend(_recipe_layers(by_id[ident],start,segment,index))
    return {"schema":"chronon.render-plan.v3","version":3,"job_id":"rgb_motion_torture_v1",
            "canvas":{"width":WIDTH,"height":HEIGHT,"fps_num":FPS,"fps_den":1,"duration_frames":total},
            "layers":layers,"output":{"path":"rgb_motion_torture_v1.mp4","format":"mp4","codec":"h264"}}


def build_plans(family=None) -> dict[str,dict]:
    family=family or json.loads(FAMILY_FILE.read_text())
    return {"canary_rgb_motion_v1":build_gallery(family),"rgb_motion_torture_v1":build_torture(family)}


def main() -> int:
    parser=argparse.ArgumentParser(description=__doc__)
    mode=parser.add_mutually_exclusive_group()
    mode.add_argument("--plans",action="store_true")
    mode.add_argument("--validate",action="store_true")
    mode.add_argument("--render",action="store_true")
    parser.add_argument("--transitions",action="store_true",
                        help="emit the ten rapid RGB transition plans instead of the long gallery")
    parser.add_argument("--cli",type=Path)
    args=parser.parse_args()
    out_dir = OUT / "transitions" if args.transitions else OUT
    out_dir.mkdir(parents=True,exist_ok=True)
    plans=build_transition_plans() if args.transitions else build_plans()
    for job_id,plan in plans.items():
        path=out_dir/f"{job_id}.plan.json"
        path.write_text(json.dumps(plan,indent=2)+"\n")
        print(f"wrote {path}")
    if args.validate or args.render:
        cli=args.cli or next((p for p in CLI_CANDIDATES if p.is_file()),None)
        if cli is None: parser.error("chronon3d_cli not found; pass --cli")
        for job_id in plans:
            path=out_dir/f"{job_id}.plan.json"
            subprocess.run([str(cli),"validate","--plan",str(path),"--assets-root",str(WORKSPACE)],check=True)
            if args.render:
                subprocess.run([str(cli),"render","--plan",str(path),"--assets-root",str(WORKSPACE),
                                "--output",str(out_dir/f"{job_id}.mp4"),"--backend","software"],check=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
