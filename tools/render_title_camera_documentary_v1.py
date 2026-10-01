#!/usr/bin/env python3
"""Render every native TitleCameraPack move with both contract example titles."""
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKSPACE = ROOT.parent
OUT = ROOT / "out/camera_title_documentary_v1"
POSE_DUMPER = ROOT / "build/titlecam-verify/chronontemplate_dump_title_camera_poses"
CLI = WORKSPACE / "Chronon3d/build/chronon/linux-video-fast-dev/apps/chronon3d_cli/chronon3d_cli"
ASSETS = WORKSPACE / "RenderingGen/testdata/golden"
FPS, WIDTH, HEIGHT, DURATION = 30, 1920, 1080, 136
TITLES = {"simplicity": "THE ART OF SIMPLICITY", "rome": "ROME"}


def sampled_poses():
    raw = subprocess.check_output([str(POSE_DUMPER)], text=True)
    lines = iter(raw.splitlines())
    result = {}
    while True:
        try:
            move = next(lines).strip()
        except StopIteration:
            break
        rows = []
        for _ in range(DURATION):
            row = [float(v) for v in next(lines).split()]
            rows.append(row)
        result[move] = rows
    if len(result) != 20:
        raise RuntimeError(f"expected poses for 20 presets, got {len(result)}")
    return result


def unwrap_degrees(values):
    result = [values[0]]
    for angle in values[1:]:
        prev = result[-1]
        while angle - prev > 180:
            angle -= 360
        while angle - prev < -180:
            angle += 360
        result.append(angle)
    return result


def track(prop, values):
    return {"property": prop, "easing": "linear", "keyframes": [
        {"frame": i, "value": round(v, 6)} for i, v in enumerate(values)]}


def plan_for(move, title_id, title, rows):
    # Samples are frame, position xyz, Euler xyz (degrees), and FOV from the
    # native C++ CameraRig. The render-plan channels preserve each pose sample.
    channels = list(zip(*[r[1:] for r in rows]))
    channels = [list(channels[0]), list(channels[1]), list(channels[2]),
                *[unwrap_degrees(list(c)) for c in channels[3:6]], list(channels[6])]
    # ChrononTemplate authors camera poses in canvas coordinates (center at
    # 960,540, z forward); render-plan 3D layers are center-relative and use
    # the renderer's -Z camera convention.
    channels[0] = [x - WIDTH / 2 for x in channels[0]]
    channels[1] = [y - HEIGHT / 2 for y in channels[1]]
    channels[2] = [-z for z in channels[2]]
    first = rows[0]
    short = title == "ROME"
    title_size = 188 if short else 112
    subtitle = move.removeprefix("title_camera_").replace("_", " ").upper()
    bg = {"id": "background", "type": "color", "color": [0.018, 0.028, 0.033, 1],
          "size": [WIDTH, HEIGHT], "screen_space": True, "start_frame": 0,
          "duration_frames": DURATION}
    title_layer = {"id": "hero-title", "type": "text", "text": title,
        "size": [1520, 270 if short else 200], "position": [960, 540, 0],
        "start_frame": 0, "duration_frames": DURATION, "enable_3d": True,
        "style": {"font": "assets/fonts/Inter-Bold.ttf", "font_size": title_size,
                  "fill": "#F2F0E8", "fit_mode": "shrink_only", "min_font_size": 54,
                  "max_font_size": title_size}}
    caption = {"id": "move-caption", "type": "text", "text": subtitle,
        "size": [1000, 54], "position": [960, 875, 0], "start_frame": 0,
        "duration_frames": DURATION, "enable_3d": True,
        "style": {"font": "assets/fonts/Inter-Bold.ttf", "font_size": 26,
                  "fill": "#92B4A6", "fit_mode": "shrink_only", "min_font_size": 20,
                  "max_font_size": 26}}
    properties = ["camera_position_x", "camera_position_y", "camera_position_z",
                  "camera_rotation_x", "camera_rotation_y", "camera_rotation_z", "camera_fov_deg"]
    return {"schema": "chronon.render-plan.v3", "version": 3,
        "job_id": f"camera_title_documentary_v1_{title_id}_{move}",
        "canvas": {"width": WIDTH, "height": HEIGHT, "fps_num": FPS, "fps_den": 1,
                   "duration_frames": DURATION},
        "camera": {"type": "perspective", "position": [round(channels[i][0], 6) for i in range(3)],
                   "rotation_deg": [round(x, 6) for x in first[4:7]], "fov_deg": round(first[7], 6),
                   "near": 1, "far": 10000, "zoom": 1},
        "camera_animation": {"tracks": [track(p, c) for p, c in zip(properties, channels)]},
        "layers": [bg, title_layer, caption],
        "output": {"path": f"{title_id}/{move}.mp4", "format": "mp4", "codec": "h264"}}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--generate-only", action="store_true", help="write plans without rendering")
    args = parser.parse_args()
    if not POSE_DUMPER.is_file():
        raise SystemExit(f"missing {POSE_DUMPER}; build target chronontemplate_dump_title_camera_poses first")
    if not args.generate_only and not CLI.is_file():
        raise SystemExit(f"missing Chronon3D CLI: {CLI}")
    poses = sampled_poses()
    render_jobs = []
    for title_id, title in TITLES.items():
        plan_dir = OUT / title_id / "plans"
        render_dir = OUT / title_id
        plan_dir.mkdir(parents=True, exist_ok=True)
        for move, rows in poses.items():
            plan = plan_for(move, title_id, title, rows)
            plan_path = plan_dir / f"{move}.plan.json"
            plan_path.write_text(json.dumps(plan, indent=2) + "\n")
            if not args.generate_only:
                output = render_dir / f"{move}.mp4"
                output.parent.mkdir(parents=True, exist_ok=True)
                render_jobs.append((plan_path, output))
    def render(job):
        plan_path, output = job
        subprocess.run([str(CLI), "render-plan", "--input", str(plan_path),
            "--assets-root", str(ASSETS), "--output", str(output), "--backend", "software",
            "--encode-preset", "veryfast"], check=True, cwd=WORKSPACE,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return output
    if render_jobs:
        with ThreadPoolExecutor(max_workers=4) as pool:
            futures = [pool.submit(render, job) for job in render_jobs]
            for future in as_completed(futures):
                print(future.result(), flush=True)
    print(f"Generated 40 render plans under {OUT}")


if __name__ == "__main__":
    main()
