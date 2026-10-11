#!/usr/bin/env python3
"""Documentary-style data-viz samples (bar + step-line) in the CLI-renderable v3 dialect.

Mirrors CaptionsDataVizPack geometry (staggered growth, midpoint landing) with the
documentary finish: living paper background, Inter SemiBold ink, black stroke on
text, and blurred duplicate layers for title shadow + glow.
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve()
TEMPLATE = HERE.parents[2]
ROOT = TEMPLATE.parent
OUT = TEMPLATE / "out/dataviz_modern"
CLI = ROOT / "Chronon3d/build/chronon/linux-video-fast-dev/apps/chronon3d_cli/chronon3d_cli"
ASSETS_ROOT = ROOT / "Chronon3d"

FPS, FRAMES, WIDTH, HEIGHT = 30, 210, 1920, 1080
FONT = "assets/fonts/Inter-SemiBold.ttf"
INK = "#080808"
BAR = "#201F1C"
ACCENT = "#000000"
GRID = "#D8D5CC"

VALUES = [35.0, 80.0, 55.0, 95.0]
LABELS = ["Q1", "Q2", "Q3", "Q4"]
HIGHLIGHT = 3
TITLE = "CRESCITA TRIMESTRALE"


def track(prop: str, points: list[tuple[int, float]], easing: str = "out_cubic") -> dict:
    return {"property": prop, "easing": easing,
            "keyframes": [{"frame": f, "value": v} for f, v in points]}


def color(hex_color: str, alpha: float = 1.0) -> list[float]:
    v = hex_color.lstrip("#")
    return [int(v[i:i + 2], 16) / 255.0 for i in (0, 2, 4)] + [alpha]


def video_bg(frames: int) -> dict:
    return {"id": "background", "type": "video",
            "source": "assets/images/documentary_paper_alive.mp4",
            "size": [WIDTH, HEIGHT], "fit": "cover", "position": [0, 0],
            "start_frame": 0, "duration_frames": frames}


def shape(id_: str, x: float, y: float, w: float, h: float, fill: str,
          opacity: float = 1.0, radius: float = 0,
          motion: list[dict] | None = None) -> dict:
    geometry: dict = {"type": "rounded_rect" if radius else "rect", "fill": color(fill)}
    if radius:
        geometry["radius"] = radius
    layer = {"id": id_, "type": "shape", "shape": geometry, "size": [w, h],
             "position": [x, y], "opacity": opacity, "start_frame": 0,
             "duration_frames": FRAMES}
    if motion:
        layer["animation"] = {"tracks": motion}
    return layer


def text(id_: str, label: str, cx: float, cy: float, w: float, h: float,
         size: float, fill: str = INK, stroke: float = 0.0,
         motion: list[dict] | None = None) -> dict:
    style: dict = {"font": FONT, "font_size": size, "fill": fill,
                   "stroke": {"color": "#000000", "width": stroke},
                   "glow": {"radius": 0, "intensity": 0, "color": "#000000"}}
    layer = {"id": id_, "type": "text", "text": label, "size": [w, h],
             "position": [cx, cy], "style": style, "start_frame": 0,
             "duration_frames": FRAMES}
    if motion:
        layer["animation"] = {"tracks": motion}
    return layer


def blur_animator(layer_id: str, blur: float) -> list[dict]:
    return [{
        "id": f"{layer_id}_anim0_text",
        "selectors": [{
            "id": f"{layer_id}_anim0_selector",
            "unit": "glyph", "shape": "square", "order": "forward",
            "combine": "replace", "exclude_spaces": True,
            "start": {"keyframes": [{"frame": 0, "value": 0}], "easing": "linear"},
            "end": {"keyframes": [{"frame": 0, "value": 100}], "easing": "linear"},
        }],
        "properties": [{
            "property": "blur",
            "keyframes": [{"frame": f, "value": blur} for f in range(FRAMES)],
        }],
    }]


def title_with_finish(layers: list[dict], prefix: str, cx: float, cy: float,
                      w: float, h: float, size: float, label: str,
                      enter: int) -> None:
    """Hero title plus blurred black duplicates (glow + ambient + contact)."""
    fade = [track("opacity", [(0, 0.0), (enter, 1.0), (FRAMES - 15, 1.0), (FRAMES - 1, 0.0)], "linear"),
            track("position_y", [(0, 12.0), (enter, 0.0), (FRAMES - 15, 0.0), (FRAMES - 1, 12.0)])]
    main = text(f"{prefix}_title", label, cx, cy, w, h, size, INK, stroke=1.2, motion=fade)
    layers.append(main)
    for cid, dy, blur, op in [("glow", 0, 16.0, 0.40),
                              ("shadow_ambient", 6, 14.0, 0.35),
                              ("shadow_contact", 2, 4.0, 0.40)]:
        dup = text(f"{prefix}_{cid}", label, cx, cy + dy, w, h, size, "#000000", stroke=0.0,
                   motion=[track("opacity", [(0, 0.0), (enter, op),
                                            (FRAMES - 15, op), (FRAMES - 1, 0.0)], "linear"),
                           track("position_y", [(0, 12.0), (enter, 0.0),
                                               (FRAMES - 15, 0.0), (FRAMES - 1, 12.0)])])
        dup["text_animators"] = blur_animator(f"{prefix}_{cid}", blur)
        layers.append(dup)


def chart_geometry(n: int):
    chart_h = HEIGHT * 0.45
    floor_y = HEIGHT * 0.82
    left = WIDTH * 0.08
    width = WIDTH * (1.0 - 2.0 * 0.08)
    step = width / n
    bar_w = step * 0.6
    peak = 100
    grow = max(6, (peak - 10) // 2)
    return chart_h, floor_y, left, width, step, bar_w, peak, grow


def build_bar() -> list[dict]:
    layers: list[dict] = [video_bg(FRAMES)]
    n = len(VALUES)
    chart_h, floor_y, left, width, step, bar_w, peak, grow = chart_geometry(n)
    vmax = max(VALUES)
    # faint grid rules
    for j, gy in enumerate([floor_y - chart_h * f for f in (1.0, 0.75, 0.5, 0.25)]):
        layers.append(shape(f"grid-{j}", WIDTH / 2, gy, width, 2, GRID, opacity=0.9,
                            motion=[track("opacity", [(0, 0.0), (20 + j * 4, 0.9), (FRAMES - 1, 0.9)], "linear")]))
    # baseline
    layers.append(shape("baseline", WIDTH / 2, floor_y + 2, width, 3, BAR, opacity=0.85))
    for i, (val, lab) in enumerate(zip(VALUES, LABELS)):
        h = max(chart_h * 0.02, chart_h * val / vmax)
        cx = left + step * (i + 0.5)
        cy = floor_y - h / 2
        delay = i * 7
        land = 24 + delay
        fill = ACCENT if i == HIGHLIGHT else BAR
        # GPU fix: scale-only center growth (oil-showcase pattern). A position
        # track on a shape vanishes mid-ramp on Vulkan; text tracks fine.
        layers.append(shape(f"bar-{i}", cx, cy, bar_w, h, fill, radius=6,
                            motion=[track("scale_y", [(0, 0.02), (land, 1.0), (FRAMES - 1, 1.0)])]))
        layers.append(text(f"label-{i}", lab, cx, floor_y + 34, 200, 48, 26, INK, stroke=0.8,
                           motion=[track("opacity", [(0, 0.0), (land, 1.0), (FRAMES - 1, 1.0)], "linear")]))
        layers.append(text(f"value-{i}", f"{val:g}", cx, cy - h / 2 - 30, 200, 44, 24, INK, stroke=0.8,
                           motion=[track("opacity", [(0, 0.0), (land, 1.0), (FRAMES - 1, 1.0)], "linear")]))
    # highlight halo pulse
    hcx = left + step * (HIGHLIGHT + 0.5)
    layers.append(shape("halo", hcx, floor_y + 34, bar_w * 1.6, 14, ACCENT, opacity=0.5,
                        motion=[track("opacity", [(peak, 0.5), (peak + 20, 0.2), (peak + 40, 0.5),
                                                 (peak + 60, 0.2), (FRAMES - 1, 0.5)], "linear")]))
    # trend rule drawing left-to-right at the average
    avg = sum(VALUES) / len(VALUES)
    ay = floor_y - chart_h * avg / vmax
    layers.append(shape("trend", left + width / 2, ay, width, 4, ACCENT,
                        motion=[track("scale_x", [(peak - grow, 0.02), (peak, 1.0), (FRAMES - 1, 1.0)]),
                                track("opacity", [(0, 0.0), (peak - grow, 1.0), (FRAMES - 1, 1.0)], "linear")]))
    title_with_finish(layers, "bar", WIDTH / 2, 108, 1400, 80, 44, TITLE, enter=14)
    return layers


def build_line() -> list[dict]:
    layers: list[dict] = [video_bg(FRAMES)]
    n = len(VALUES)
    chart_h, floor_y, left, width, step, _, peak, grow = chart_geometry(n)
    vmax = max(VALUES)
    xs = [left + width * i / (n - 1) for i in range(n)]
    ys = [floor_y - chart_h * v / vmax for v in VALUES]
    thick = 5
    dot_r = 11
    for j, gy in enumerate([floor_y - chart_h * f for f in (1.0, 0.75, 0.5, 0.25)]):
        layers.append(shape(f"grid-{j}", WIDTH / 2, gy, width, 2, GRID, opacity=0.9,
                            motion=[track("opacity", [(0, 0.0), (20 + j * 4, 0.9), (FRAMES - 1, 0.9)], "linear")]))
    layers.append(shape("baseline", WIDTH / 2, floor_y + 2, width, 3, BAR, opacity=0.85))
    for i in range(n - 1):
        x0, y0, y1 = xs[i], ys[i], ys[i + 1]
        start = 10 + i * 9
        run_w = xs[i + 1] - x0
        layers.append(shape(f"run-{i}", x0 + run_w / 2, y0, run_w, thick, ACCENT,
                            motion=[track("scale_x", [(start, 0.02), (start + grow, 1.0), (FRAMES - 1, 1.0)])]))
        rise = y0 - y1
        if abs(rise) >= 0.5:
            top = min(y0, y1)
            layers.append(shape(f"riser-{i}", xs[i + 1], top + abs(rise) / 2, thick, abs(rise), ACCENT,
                                motion=[track("scale_y", [(start + grow // 2, 0.02), (start + grow, 1.0),
                                                          (FRAMES - 1, 1.0)])]))
    for i, (x, y, lab, val) in enumerate(zip(xs, ys, LABELS, VALUES)):
        land = 10 + i * 9 + grow
        hot = i == HIGHLIGHT
        layers.append(shape(f"dot-{i}", x, y, dot_r * 2, dot_r * 2, ACCENT if hot else BAR, radius=dot_r,
                            motion=[track("scale", [(land - grow, 0.02), (land, 1.0), (FRAMES - 1, 1.0)])]))
        layers.append(text(f"label-{i}", lab, x, floor_y + 34, 200, 48, 26, INK, stroke=0.8,
                           motion=[track("opacity", [(0, 0.0), (land, 1.0), (FRAMES - 1, 1.0)], "linear")]))
        layers.append(text(f"value-{i}", f"{val:g}", x, y - 44, 200, 44, 24, INK, stroke=0.8,
                           motion=[track("opacity", [(0, 0.0), (land, 1.0), (FRAMES - 1, 1.0)], "linear")]))
    title_with_finish(layers, "line", WIDTH / 2, 108, 1400, 80, 44, TITLE, enter=14)
    return layers


def write_plan(job_id: str, layers: list[dict]) -> Path:
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / f"{job_id}.plan.json"
    plan = {"schema": "chronon.render-plan.v3", "version": 3, "job_id": job_id,
            "canvas": {"width": WIDTH, "height": HEIGHT, "fps_num": FPS,
                       "fps_den": 1, "duration_frames": FRAMES},
            "layers": layers,
            "output": {"path": f"{job_id}.mp4", "format": "mp4", "codec": "h264"}}
    path.write_text(json.dumps(plan, ensure_ascii=False, indent=2) + "\n")
    print(f"Wrote {path} ({len(layers)} layers)")
    return path


def render(plan: Path) -> Path:
    target = OUT / f"{plan.stem.removesuffix('.plan')}.mp4"
    cmd = [str(CLI), "render", "--plan", str(plan), "--assets-root", str(ASSETS_ROOT),
           "--backend", "vulkan", "--hardware", "nvenc", "--encoder-backend", "pipe",
           "--codec", "h264", "--fps", "30", "--rate-control", "crf", "--crf", "26",
           "-o", str(target)]
    subprocess.run(cmd, cwd=ROOT, check=True)
    subprocess.run(["ffmpeg", "-y", "-ss", "00:00:05.000", "-i", str(target),
                    "-vframes", "1", str(OUT / f"{plan.stem.removesuffix('.plan')}_frame.png")],
                   capture_output=True)
    return target


if __name__ == "__main__":
    import sys

    only = sys.argv[1:] or ["bar", "line"]
    builders = {"bar": build_bar, "line": build_line}
    for name in only:
        plan = write_plan(f"dataviz_modern_{name}", builders[name]())
        render(plan)
