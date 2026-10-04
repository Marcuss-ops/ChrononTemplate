#!/usr/bin/env python3
"""Build and Vulkan-render a deterministic abstract/light-leak background gallery.

All imagery is authored as ordinary Chronon RenderPlan V3 shapes and gradients;
motion is frame-keyed and the same plans can be reused as background assets.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKSPACE = ROOT.parent
CHRONON_ROOT = WORKSPACE / "Chronon3d"
CLI_CANDIDATES = [
    CHRONON_ROOT / "build/chronon/linux-video-fast-dev/apps/chronon3d_cli/chronon3d_cli",
    CHRONON_ROOT / "build/chronon/linux-video-release/apps/chronon3d_cli/chronon3d_cli",
]
OUT = ROOT / "out/abstract_cinematic_backgrounds_v1"
W, H, FPS, FRAMES = 1920, 1080, 30, 120


def col(hex_color: str, alpha: float = 1.0) -> list[float]:
    value = hex_color.lstrip("#")
    return [int(value[i:i + 2], 16) / 255 for i in (0, 2, 4)] + [alpha]


def layer_base(name: str, color: str, start: int = 0, duration: int = FRAMES) -> dict:
    return {"id": f"{name}-base", "type": "color", "color": col(color),
            "size": [W, H], "start_frame": start, "duration_frames": duration}


def linear_fill(stops: list[tuple[float, str, float]], start=(0.5, 0.0), end=(0.5, 1.0)) -> dict:
    return {"type": "linear", "start": list(start), "end": list(end), "spread": "pad",
            "color_stops": [{"position": p, "color": col(c, a)} for p, c, a in stops]}


def radial_fill(stops: list[tuple[float, str, float]]) -> dict:
    return {"type": "radial", "center": [0.5, 0.5], "radius": 0.5, "spread": "pad",
            "color_stops": [{"position": p, "color": col(c, a)} for p, c, a in stops]}


def rect(name: str, fill: dict, start=0, duration=FRAMES) -> dict:
    return {"id": name, "type": "shape", "size": [W, H], "position": [W / 2, H / 2],
            "start_frame": start, "duration_frames": duration,
            "shape": {"type": "rect", "fill": fill}}


def radial_emitter(name: str, xy: tuple[float, float], size: tuple[float, float],
                   colors: list[tuple[float, str, float]], start=0, duration=FRAMES,
                   drift=(0.0, 0.0), phase=0.0, blend="screen") -> dict:
    # A short cyclic track gives smooth, deterministic drift and exact loop closure.
    x, y = xy
    dx, dy = drift
    keys = []
    for f, a in ((0, phase), (duration // 2, phase + math.pi), (duration, phase + 2 * math.pi)):
        keys.append({"frame": start + f,
                     "value": [x + dx * math.sin(a), y + dy * math.cos(a)]})
    return {"id": name, "type": "shape", "size": list(size), "position": [x, y],
            "start_frame": start, "duration_frames": duration,
            "blend_mode": blend,
            "shape": {"type": "ellipse", "fill": radial_fill(colors)},
            "animation": {"tracks": [{"property": "position", "easing": "in_out_sine",
                                        "keyframes": keys}]}}


def path_layer(name: str, points: list[list[float]], color: str, width: float,
               start=0, duration=FRAMES, opacity=0.8) -> dict:
    commands = [{"type": "move_to", "point": points[0]}]
    commands.extend({"type": "line_to", "point": p} for p in points[1:])
    return {"id": name, "type": "shape", "size": [W, H], "position": [0, 0],
            "start_frame": start, "duration_frames": duration,
            "shape": {"type": "path", "path": commands,
                      "stroke": {"color": col(color, opacity), "width": width,
                                 "cap": "round", "join": "round"}},
            "animation": {"tracks": [{"property": "position", "easing": "in_out_sine",
                                        "keyframes": [{"frame": start, "value": [0, 0]},
                                                      {"frame": start + duration // 2, "value": [0, -3]},
                                                      {"frame": start + duration, "value": [0, 0]}]}]}}


def scene(name: str, layers: list[dict]) -> tuple[str, list[dict]]:
    return name, layers


def recipes() -> list[tuple[str, list[dict]]]:
    out = []
    # Abstract family: shared gradient and ellipse/path primitives, with no per-look renderer.
    out.append(scene("abstract_aurora_horizon", [
        layer_base("aurora", "#03030B"),
        rect("aurora-sky", linear_fill([(0, "#050711", 1), (.48, "#140C35", 1), (.76, "#67258B", .72), (1, "#080712", 0)])),
        radial_emitter("aurora-ridge-violet", (520, 760), (1050, 560), [(0, "#F6B9FF", .50), (.3, "#C12EFF", .42), (1, "#7D28FF", 0)], drift=(36, 10)),
        radial_emitter("aurora-ridge-rose", (1370, 820), (980, 460), [(0, "#FFD6F5", .46), (.36, "#F53FA8", .34), (1, "#D12891", 0)], drift=(28, 8)),
    ]))
    for name, palette in (("abstract_liquid_neon", ["#12D9D0", "#7136FF", "#ED238E", "#FFAA38"]),
                          ("abstract_liquid_magenta", ["#5E20D1", "#EE218A", "#FF6BBD", "#31248D"])):
        layers = [layer_base(name, "#05030E")]
        for i, color in enumerate(palette):
            layers.append(radial_emitter(f"{name}-fluid-{i}", (360 + i * 420, 330 + (i % 2) * 400),
                (900, 820), [(0, color, .70), (.42, color, .38), (1, color, 0)],
                drift=(35 + 5 * i, 20 + 3 * i), phase=i * 1.2))
        out.append(scene(name, layers))
    out.append(scene("abstract_metaball_soft", [
        layer_base("metaball", "#080A18"),
        radial_emitter("metaball-a", (680, 520), (820, 760), [(0, "#C8F5FF", .72), (.52, "#357DC8", .50), (1, "#152051", 0)], drift=(42, 24)),
        radial_emitter("metaball-b", (1120, 560), (820, 760), [(0, "#F3C9FF", .70), (.52, "#9754D8", .50), (1, "#39174F", 0)], drift=(42, 24), phase=math.pi),
    ]))
    out.append(scene("abstract_glass_orb", [
        layer_base("glass", "#050714"),
        rect("glass-atmosphere", linear_fill([(0, "#07112A", 1), (1, "#130B30", 1)], (0, 0), (1, 1))),
        radial_emitter("glass-orb-fill", (960, 540), (620, 620), [(0, "#F9D8FF", .70), (.55, "#B04BEE", .45), (.82, "#552B9B", .20), (1, "#18112F", 0)]),
        radial_emitter("glass-orb-rim", (960, 540), (700, 700), [(0, "#FFFFFF", 0), (.68, "#F2A8FF", 0), (.83, "#EE9FFF", .48), (1, "#B649FF", 0)]),
    ]))
    out.append(scene("abstract_dual_orbs", [
        layer_base("dual", "#040611"),
        radial_emitter("dual-orb-left", (700, 540), (560, 560), [(0, "#FFFFFF", .85), (.34, "#E86EFF", .65), (1, "#8E27E8", 0)], drift=(26, 12)),
        radial_emitter("dual-orb-right", (1220, 540), (560, 560), [(0, "#EDFFFF", .82), (.34, "#48CFFD", .62), (1, "#1B5DE0", 0)], drift=(26, 12), phase=math.pi),
    ]))
    contour_layers = [layer_base("contours", "#03050C")]
    for i in range(25):
        y0 = 80 + i * 39
        pts = [[x, y0 + 17 * math.sin(x / 210 + i * .43) + 7 * math.sin(x / 91 - i * .2)]
               for x in range(-50, W + 51, 80)]
        contour_layers.append(path_layer(f"contour-{i:02d}", pts, "#DDEBFF", 1.15, opacity=.40 + .28 * (i % 3 == 0)))
    out.append(scene("abstract_topographic_contours", contour_layers))
    flow_layers = [layer_base("flow", "#080A13")]
    for i in range(58):
        x0 = 24 + i * 33
        pts = [[x0 + 38 * math.sin(y / 160 + i * .24) + 15 * math.sin(y / 67 - i * .18), y]
               for y in range(-40, H + 41, 36)]
        flow_layers.append(path_layer(f"flowline-{i:02d}", pts, "#C8E7FF", 1.0, opacity=.42))
    out.append(scene("abstract_flowlines_vertical", flow_layers))
    fold = [layer_base("fold", "#090714")]
    for i in range(18):
        x = i * 112 - 70
        shade = ["#37186A", "#6F36A8", "#B685D3", "#F2CE7A", "#7D54B6"][i % 5]
        fold.append({"id": f"fold-ribbon-{i:02d}", "type": "shape", "size": [170, H],
            "position": [x + 85, H / 2], "start_frame": 0, "duration_frames": FRAMES,
            "shape": {"type": "rect", "fill": linear_fill([(0, "#07050E", .05), (.40, shade, .50), (.72, "#FFF0B5", .72), (1, "#180C2A", .16)], (0, 0), (1, 0))},
            "animation": {"tracks": [{"property": "position", "easing": "in_out_sine", "keyframes": [
                {"frame": 0, "value": [x + 85, 540]}, {"frame": 60, "value": [x + 105, 540]}, {"frame": 120, "value": [x + 85, 540]}]}]}})
    out.append(scene("abstract_folded_ribbon", fold))
    out.append(scene("abstract_blue_atmosphere", [
        layer_base("blue-atmos", "#030813"),
        rect("blue-atmos-linear", linear_fill([(0, "#07182B", 1), (.54, "#071226", 1), (1, "#02050E", 1)], (0, 0), (1, 1))),
        radial_emitter("blue-field-a", (340, 500), (1150, 950), [(0, "#167DD1", .38), (.58, "#0C478B", .25), (1, "#0A2344", 0)], drift=(20, 14)),
        radial_emitter("blue-field-b", (1470, 650), (900, 800), [(0, "#38C9E4", .30), (.6, "#126B9A", .20), (1, "#092447", 0)], drift=(22, 12), phase=2.1),
    ]))

    # Cinematic film-leak family. Each recipe is a different arrangement of the same emitters.
    warm = [(0, "#FFF4B0", .92), (.18, "#FFD44C", .85), (.47, "#FF7A18", .64), (.76, "#B92718", .32), (1, "#2A0710", 0)]
    out.append(scene("cinematic_leak_soft_blob", [layer_base("leak", "#020203"),
        radial_emitter("warm-blob", (690, 520), (920, 820), warm, drift=(42, 24))]))
    out.append(scene("cinematic_leak_edge_burn", [layer_base("edge", "#010101"),
        radial_emitter("edge-burn", (1820, 440), (1150, 1300), warm, drift=(-65, 26))]))
    out.append(scene("cinematic_leak_warped_ring", [layer_base("ring", "#010101"),
        radial_emitter("ring-halo", (960, 540), (1150, 860), [(0, "#000000", 0), (.36, "#000000", 0), (.52, "#FFF07A", .92), (.64, "#FF5B18", .56), (1, "#8E130F", 0)], drift=(34, 20)),
        radial_emitter("ring-center", (900, 570), (570, 450), [(0, "#010101", 1), (1, "#080204", .7)])]))
    ribbon = [layer_base("ribbon", "#020102")]
    for i, (y, color, width) in enumerate(((330, "#FF3E15", 36), (390, "#FFB323", 23), (450, "#FFF5B0", 11), (520, "#FF6A18", 27))):
        pts = [[x, y + 110 * math.sin(x / 280 + i * .7) + 20 * math.sin(x / 90)] for x in range(-100, W + 101, 48)]
        ribbon.append(path_layer(f"leak-ribbon-{i}", pts, color, width, opacity=.80))
    out.append(scene("cinematic_leak_bezier_ribbon", ribbon))
    burst = [layer_base("burst", "#010101")]
    for i in range(16):
        angle = 2 * math.pi * i / 16
        p = [[960 + r * math.cos(angle) * (1 + .06 * math.sin(i * 7)),
              540 + r * math.sin(angle) * (1 + .06 * math.sin(i * 7))] for r in (10, 140, 390, 770)]
        burst.append(path_layer(f"burst-ray-{i:02d}", p, "#FF7C18" if i % 2 else "#FFE27A", 7 if i % 2 else 11, opacity=.62))
    burst.append(radial_emitter("burst-core", (960, 540), (500, 500), warm, drift=(20, 10)))
    out.append(scene("cinematic_leak_radial_burst", burst))
    out.append(scene("cinematic_leak_dual_blob", [layer_base("dual-burn", "#010101"),
        radial_emitter("dual-warm", (560, 600), (850, 1000), warm, drift=(40, 20)),
        radial_emitter("dual-amber", (1430, 420), (830, 1050), [(0, "#FFF2A0", .82), (.2, "#FFB51D", .75), (.55, "#ED4812", .48), (1, "#4B1008", 0)], drift=(35, 18), phase=math.pi)]))
    out.append(scene("cinematic_leak_film_burn", [layer_base("film", "#020000"),
        rect("film-wash", linear_fill([(0, "#180306", 1), (.38, "#6D160B", .60), (.67, "#ED4A0D", .78), (.86, "#FFD13D", .94), (1, "#FFF1A0", .52)], (0, 0), (1, 0))),
        radial_emitter("film-hotspot", (1480, 500), (780, 1100), warm, drift=(-45, 20))]))
    out.append(scene("cinematic_leak_hot_orb", [layer_base("hot-orb", "#010102"),
        radial_emitter("orb-core", (980, 540), (520, 520), [(0, "#FFFFFF", .98), (.14, "#FFF8C9", .98), (.42, "#FFD238", .84), (.68, "#FF6B15", .60), (1, "#A91514", 0)], drift=(30, 16)),
        radial_emitter("orb-halo", (980, 540), (960, 960), [(0, "#FFB32E", .28), (.55, "#FA4818", .22), (1, "#7D1210", 0)], drift=(30, 16))]))
    return out


def make_plan(name: str, layers: list[dict], output: Path, start=0, duration=FRAMES) -> dict:
    return {"schema": "chronon.render-plan.v3", "version": 3, "job_id": name,
            "canvas": {"width": W, "height": H, "fps_num": FPS, "fps_den": 1,
                       "duration_frames": duration},
            "output": {"path": str(output), "format": "mp4", "codec": "h264"},
            "layers": layers}


def run(cmd: list[str]) -> None:
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode:
        raise RuntimeError((result.stderr + result.stdout)[-5000:])


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plans-only", action="store_true")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--frames", type=int, default=FRAMES)
    args = parser.parse_args()
    if args.frames < 30 or args.frames > 1800:
        parser.error("--frames must be between 30 and 1800")
    OUT.mkdir(parents=True, exist_ok=True)
    cli = next((p for p in CLI_CANDIDATES if p.is_file()), None)
    if not args.plans_only and cli is None:
        raise SystemExit("Chronon3D CLI not found; build apps/chronon3d_cli/chronon3d_cli with Vulkan enabled")
    entries = []
    scene_specs = recipes()
    for name, authored_layers in scene_specs:
        video = OUT / f"{name}.mp4"
        plan_path = OUT / f"{name}.plan.json"
        plan = make_plan(name, authored_layers, video, duration=args.frames)
        plan_path.write_text(json.dumps(plan, indent=2) + "\n")
        if not args.plans_only and (args.force or not video.is_file() or video.stat().st_size == 0):
            run([str(cli), "render", "--plan", str(plan_path), "--assets-root", str(CHRONON_ROOT),
                 "--backend", "vulkan", "--video-sink", "ffmpeg", "--start-frame", "0",
                 "--end-frame", str(args.frames - 1), "--fps", str(FPS), "--codec", "h264",
                 "--preset", "fast", "--output", str(video)])
        poster = OUT / f"{name}.png"
        if not args.plans_only and (args.force or not poster.is_file()):
            run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-ss",
                 f"{(args.frames // 2) / FPS:.3f}", "-i", str(video), "-frames:v", "1", str(poster)])
        entries.append({"id": name, "kind": "video", "media_type": "video/mp4", "loop": True,
                        "render_mode": "chronon_vulkan", "path": video.name,
                        "poster": poster.name, "plan": plan_path.name,
                        "width": W, "height": H, "fps": FPS, "duration_frames": args.frames,
                        "sha256": hashlib.sha256(video.read_bytes()).hexdigest() if video.is_file() else None})
    (OUT / "catalog.v1.json").write_text(json.dumps({"schema_version": "chronon.background-catalog.v1",
        "generated_by": Path(__file__).name, "entries": entries}, indent=2) + "\n")
    print(f"Wrote {len(entries)} deterministic RenderPlan recipes to {OUT}")


if __name__ == "__main__":
    main()
