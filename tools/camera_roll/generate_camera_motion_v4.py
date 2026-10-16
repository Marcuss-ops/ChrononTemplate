#!/usr/bin/env python3
"""Emit one render-plan per camera motion preset (v4).

Spec values mirror ChrononTemplate/include/chronontemplate/camera_roll/CameraMotionPresets.def.
Image and text layers sit at 3D position [0, 0, 0] (centred), which is how the
Chronon3d renderer places them. Usage:
    python3 generate_camera_motion_v4.py <plans-dir>
"""
import json
import sys
from pathlib import Path

WIDTH, HEIGHT, FPS = 1920, 1080, 30
CAMERA_Z = -880.0   # base distance from the z=0 plane, same as emit_camera_1950_story
CAMERA_FOV = 50.0
PX_PER_FRAC = 1920.0  # framing fractions -> camera x units

PHOTO = "assets/images/camera_reference.jpg"
TITLE_FONT = "assets/fonts/Bricolage-Grotesque.ttf"
CAPTION_FONT = "assets/fonts/Inter-Regular.ttf"

# id, duration (frames), spec overrides
PRESETS = [
    ("title_slow_push", 90, dict(distStart=1.08, distEnd=1.00, easing="in_out_cubic")),
    ("title_lateral_drift", 96, dict(xStart=0.05, xEnd=-0.05, easing="in_out_cubic")),
    ("title_rise_settle", 72, dict(distStart=1.03, distEnd=1.00, yStart=0.04, yEnd=0.0, easing="out_cubic")),
    ("portrait_arc", 108, dict(distStart=1.04, distEnd=1.00, yawStart=-12.0, yawEnd=12.0, easing="in_out_cubic")),
    ("archive_reveal", 84, dict(distStart=1.10, distEnd=1.00, xStart=0.06, xEnd=0.0, easing="out_cubic")),
    ("rack_focus_portrait", 78, dict(distStart=1.04, distEnd=1.00, easing="in_out_cubic")),
    ("map_region_push", 96, dict(distStart=1.15, distEnd=0.92, easing="in_out_cubic")),
    ("map_route_track", 120, dict(xStart=-0.08, xEnd=0.08, yStart=0.03, yEnd=-0.03, easing="in_out_cubic")),
    ("map_country_tilt", 100, dict(distStart=1.05, distEnd=0.95, pitchStart=-10.0, pitchEnd=0.0, easing="out_cubic")),
    ("ui_panel_push", 64, dict(distStart=1.08, distEnd=1.00, easing="out_cubic")),
    ("ui_card_parallax", 90, dict(xStart=-0.04, xEnd=0.04, yawStart=-6.0, yawEnd=6.0, easing="in_out_cubic")),
    ("ui_micro_float", 150, dict(xMid=0.012, yMid=-0.012, posMidAt=0.5, easing="in_out_cubic")),
    ("whip_pan_left", 14, dict(xEnd=-0.38, easing="out_expo")),
    ("whip_pan_right", 14, dict(xEnd=0.38, easing="out_expo")),
    ("dolly_handoff", 22, dict(distStart=1.00, distEnd=0.70, easing="out_expo")),
]


def keys_linear(frames, start, end):
    return [{"frame": 0, "value": start}, {"frame": frames - 1, "value": end}]


def track(prop, keys, easing):
    return {"property": prop, "easing": easing, "keyframes": keys}


def build_tracks(frames, s):
    easing = s["easing"]
    if "xMid" in s:
        mid = int(frames * s["posMidAt"])
        xs = [{"frame": 0, "value": 0.0}, {"frame": mid, "value": s["xMid"] * PX_PER_FRAC},
              {"frame": frames - 1, "value": 0.0}]
        ys = [{"frame": 0, "value": 0.0}, {"frame": mid, "value": s["yMid"] * HEIGHT},
              {"frame": frames - 1, "value": 0.0}]
        dist = [{"frame": 0, "value": CAMERA_Z}, {"frame": frames - 1, "value": CAMERA_Z}]
        yaw = pitch = [{"frame": 0, "value": 0.0}, {"frame": frames - 1, "value": 0.0}]
    else:
        ds, de = s.get("distStart", 1.0), s.get("distEnd", 1.0)
        xs = keys_linear(frames, s.get("xStart", 0.0) * PX_PER_FRAC, s.get("xEnd", 0.0) * PX_PER_FRAC)
        ys = keys_linear(frames, s.get("yStart", 0.0) * HEIGHT, s.get("yEnd", 0.0) * HEIGHT)
        dist = keys_linear(frames, CAMERA_Z * ds, CAMERA_Z * de)
        yaw = keys_linear(frames, s.get("yawStart", 0.0), s.get("yawEnd", 0.0))
        pitch = keys_linear(frames, s.get("pitchStart", 0.0), s.get("pitchEnd", 0.0))
    return [
        track("camera_position_x", xs, easing),
        track("camera_position_y", ys, easing),
        track("camera_position_z", dist, easing),
        track("camera_rotation_x", pitch, easing),
        track("camera_rotation_y", yaw, easing),
    ]


def build_plan(preset_id, frames, spec):
    caption = preset_id.replace("_", " ").upper()
    return {
        "schema": "chronon.render-plan.v3",
        "version": 3,
        "job_id": f"camera_motion_v4_{preset_id}",
        "canvas": {"width": WIDTH, "height": HEIGHT, "fps_num": FPS, "fps_den": 1,
                   "duration_frames": frames},
        "camera": {"type": "perspective", "position": [0, 0, CAMERA_Z],
                   "rotation_deg": [0, 0, 0], "fov_deg": CAMERA_FOV,
                   "near": 1, "far": 10000, "zoom": 1, "dof": {"enabled": False}},
        "camera_animation": {"tracks": build_tracks(frames, spec)},
        "layers": [
            {"id": "bg", "type": "color", "color": [0.025, 0.032, 0.045, 1.0],
             "size": [WIDTH, HEIGHT], "screen_space": True,
             "start_frame": 0, "duration_frames": frames},
            {"id": "photo", "type": "image", "asset": PHOTO, "size": [920, 520],
             "position": [0, 0, 0], "fit": "contain", "enable_3d": True,
             "start_frame": 0, "duration_frames": frames},
            {"id": "title", "type": "text", "text": "THE CAMERA TELLS THE STORY",
             "size": [1520, 120], "position": [0, -380, 0], "enable_3d": True,
             "start_frame": 0, "duration_frames": frames,
             "style": {"font": TITLE_FONT, "font_size": 84, "fill": "#F2F0E8"}},
            {"id": "caption", "type": "text", "text": caption,
             "size": [1000, 54], "position": [0, 380, 0], "enable_3d": True,
             "start_frame": 0, "duration_frames": frames,
             "style": {"font": CAPTION_FONT, "font_size": 26, "fill": "#C9BFAE"}},
        ],
        "output": {"path": f"{preset_id}.mp4", "format": "mp4", "codec": "h264"},
    }


def main():
    if len(sys.argv) != 2:
        print("usage: generate_camera_motion_v4.py <plans-dir>", file=sys.stderr)
        return 2
    out = Path(sys.argv[1])
    out.mkdir(parents=True, exist_ok=True)
    for preset_id, frames, overrides in PRESETS:
        spec = {"easing": "linear", **overrides}
        plan = build_plan(preset_id, frames, spec)
        (out / f"{preset_id}.json").write_text(json.dumps(plan, indent=2) + "\n")
        print(out / f"{preset_id}.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
