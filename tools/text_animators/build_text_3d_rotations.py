#!/usr/bin/env python3
"""Text 3D rotation lab for ChrononTemplate.

The demo exercises real layer-level 3D text: three rows rotate around Y (yaw),
X (pitch) and Z (roll) under the renderer's perspective camera.  The text
positions stay in canvas coordinates, so each word is centred on the canvas
before the camera projection; `[0, 0]` would be the top-left corner.

Usage:
    python3 tools/text_animators/build_text_3d_rotations.py --generate
    python3 tools/text_animators/build_text_3d_rotations.py --render
    python3 tools/text_animators/build_text_3d_rotations.py --verify
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import subprocess
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REPO = ROOT.parent
OUT = ROOT / "out" / "text_3d_rotations_v1"
ASSETS = REPO / "Chronon3d"
CLI = REPO / "Chronon3d/build/chronon/linux-video-release/apps/chronon3d_cli/chronon3d_cli"

W, H = 1920, 1080
FPS = 30
FRAMES = 180
FONT = "assets/fonts/Inter-Bold.ttf"
CAMERA_FOV_DEG = 45.0
CAMERA_DISTANCE = 1000.0


def kf(frame: int, value) -> dict:
    return {"frame": frame, "value": value}


def track(property_name: str, keys: list[dict], easing: str = "in_out_cubic") -> dict:
    return {"property": property_name, "easing": easing, "keyframes": keys}


def text_layer(
    layer_id: str,
    body: str,
    font_size: float,
    position: tuple[float, float],
    fill: str,
    *,
    width: float = 1100.0,
    height: float = 300.0,
    fade_in: int = 8,
    enable_3d: bool = False,
    tracks: list[dict] | None = None,
) -> dict:
    animation = [
        track(
            "opacity",
            [kf(0, 0.0), kf(fade_in, 1.0), kf(FRAMES - 1, 1.0)],
            "out_cubic",
        )
    ]
    if tracks:
        animation.extend(tracks)
    layer = {
        "id": layer_id,
        "type": "text",
        "text": body,
        "size": [float(width), float(height)],
        "position": [float(position[0]), float(position[1])],
        "start_frame": 0,
        "duration_frames": FRAMES,
        "style": {
            "font": FONT,
            "font_size": font_size,
            "fill": fill,
        },
        "animation": {"tracks": animation},
    }
    if enable_3d:
        layer["enable_3d"] = True
    return layer


def rotation_track(keys: list[dict]) -> dict:
    return track("rotation", keys, "in_out_cubic")


def camera() -> dict:
    # Positions remain in canvas coordinates; the camera supplies the
    # perspective.  Keep it head-on at z=0 so the demo is about rotation,
    # not about a moving camera.
    return {
        "type": "perspective",
        "position": [0.0, 0.0, -CAMERA_DISTANCE],
        "rotation_deg": [0.0, 0.0, 0.0],
        "fov_deg": CAMERA_FOV_DEG,
        "near": 1.0,
        "far": 10000.0,
        "zoom": 1.0,
    }


def camera_position(screen_x: float, screen_y: float) -> tuple[float, float]:
    """Convert an intended screen anchor to the head-on camera plane.

    The camera mirrors Y and magnifies the canvas plane by focal/distance,
    so authored 3D positions cannot be used as screen coordinates directly.
    """
    focal = (H * 0.5) / math.tan(math.radians(CAMERA_FOV_DEG) * 0.5)
    scale = focal / CAMERA_DISTANCE
    return (
        W * 0.5 + (screen_x - W * 0.5) / scale,
        H * 0.5 - (screen_y - H * 0.5) / scale,
    )


def build_plan() -> dict:
    # Stagger the three axes so each one is readable on its own:
    #   yaw   active  f10-f75
    #   pitch active  f45-f110
    #   roll  active  f90-f150
    # Every row settles at zero and holds for the final beat.
    yaw = rotation_track(
        [
            kf(0, [0.0, 0.0, 0.0]),
            kf(10, [0.0, 0.0, 0.0]),
            kf(32, [0.0, -45.0, 0.0]),
            kf(58, [0.0, 45.0, 0.0]),
            kf(78, [0.0, 0.0, 0.0]),
            kf(179, [0.0, 0.0, 0.0]),
        ]
    )
    pitch = rotation_track(
        [
            kf(0, [0.0, 0.0, 0.0]),
            kf(45, [0.0, 0.0, 0.0]),
            kf(62, [-38.0, 0.0, 0.0]),
            kf(88, [38.0, 0.0, 0.0]),
            kf(112, [0.0, 0.0, 0.0]),
            kf(179, [0.0, 0.0, 0.0]),
        ]
    )
    roll = rotation_track(
        [
            kf(0, [0.0, 0.0, 0.0]),
            kf(88, [0.0, 0.0, 0.0]),
            kf(104, [0.0, 0.0, -12.0]),
            kf(128, [0.0, 0.0, 12.0]),
            kf(152, [0.0, 0.0, 0.0]),
            kf(179, [0.0, 0.0, 0.0]),
        ]
    )

    layers = [
        text_layer(
            "kicker",
            "CHRONONTEMPLATE / TEXT 3D",
            22.0,
            (960.0, 74.0),
            "#6F849A",
            width=1200.0,
            height=80.0,
            fade_in=6,
        ),
        text_layer(
            "title",
            "ROTATION LAB",
            54.0,
            (960.0, 142.0),
            "#F4FAFF",
            width=1200.0,
            height=100.0,
            fade_in=6,
        ),
        text_layer(
            "label_yaw",
            "YAW / Y",
            24.0,
            (260.0, 350.0),
            "#6F849A",
            width=420.0,
            height=70.0,
        ),
        text_layer(
            "word_yaw",
            "CHRONON",
            104.0,
            camera_position(1200.0, 350.0),
            "#F4FAFF",
            width=1100.0,
            height=300.0,
            enable_3d=True,
            tracks=[yaw],
        ),
        text_layer(
            "label_pitch",
            "PITCH / X",
            24.0,
            (260.0, 570.0),
            "#6F849A",
            width=420.0,
            height=70.0,
        ),
        text_layer(
            "word_pitch",
            "DEPTH",
            120.0,
            camera_position(1200.0, 570.0),
            "#4DE3FF",
            width=1100.0,
            height=300.0,
            enable_3d=True,
            tracks=[pitch],
        ),
        text_layer(
            "label_roll",
            "ROLL / Z",
            24.0,
            (260.0, 790.0),
            "#6F849A",
            width=420.0,
            height=70.0,
        ),
        text_layer(
            "word_roll",
            "ROTATE",
            104.0,
            camera_position(1200.0, 790.0),
            "#FFB454",
            width=1100.0,
            height=300.0,
            enable_3d=True,
            tracks=[roll],
        ),
        text_layer(
            "footer",
            "LAYER-LEVEL PERSPECTIVE  /  NATIVE MTSDF",
            18.0,
            (960.0, 982.0),
            "#52667A",
            width=1200.0,
            height=60.0,
            fade_in=12,
        ),
    ]

    return {
        "schema": "chronon.render-plan.v3",
        "version": 3,
        "job_id": "text_3d_rotations_v1",
        "canvas": {
            "width": W,
            "height": H,
            "fps_num": FPS,
            "fps_den": 1,
            "duration_frames": FRAMES,
        },
        "camera": camera(),
        "layers": [
            {
                "id": "backdrop",
                "type": "color",
                "color": [0.004, 0.008, 0.014, 1.0],
                "size": [float(W), float(H)],
                "position": [0.0, 0.0],
                "start_frame": 0,
                "duration_frames": FRAMES,
            },
            *layers,
        ],
        "output": {
            "path": "text_3d_rotations_v1.mp4",
            "format": "mp4",
            "codec": "h264",
        },
    }


def generate() -> Path:
    OUT.mkdir(parents=True, exist_ok=True)
    plan_path = OUT / "text_3d_rotations_v1.plan.json"
    plan_path.write_text(json.dumps(build_plan(), indent=2) + "\n", encoding="utf-8")
    print(f"PLAN {plan_path.relative_to(REPO)}")
    return plan_path


def validate(plan_path: Path) -> None:
    result = subprocess.run(
        [str(CLI), "validate", "--plan", str(plan_path), "--assets-root", str(ASSETS)],
        cwd=REPO,
        text=True,
        capture_output=True,
    )
    if result.returncode != 0:
        tail = (result.stdout + result.stderr).strip().splitlines()[-12:]
        raise SystemExit(f"validation failed: {' | '.join(tail)}")


def probe(video: Path) -> dict:
    result = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-count_frames",
            "-select_streams",
            "v:0",
            "-show_entries",
            "stream=width,height,nb_read_frames,r_frame_rate:format=duration,size",
            "-of",
            "json",
            str(video),
        ],
        check=True,
        text=True,
        capture_output=True,
    )
    data = json.loads(result.stdout)
    stream = data["streams"][0]
    return {
        "width": int(stream["width"]),
        "height": int(stream["height"]),
        "fps": stream.get("r_frame_rate", "30/1"),
        "frames": int(stream.get("nb_read_frames") or 0),
        "duration_s": round(float(data["format"]["duration"]), 3),
        "bytes": int(data["format"]["size"]),
    }


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify(video: Path, plan_path: Path, log_path: Path, seconds: float) -> dict:
    info = probe(video)
    if (info["width"], info["height"], info["frames"]) != (W, H, FRAMES):
        raise SystemExit(f"unexpected probe: {info}")
    if info["fps"] != f"{FPS}/1":
        raise SystemExit(f"unexpected fps: {info['fps']}")

    log_text = log_path.read_text(encoding="utf-8", errors="replace")
    mtsdf_routes = log_text.count("route=mtsdf")
    if mtsdf_routes == 0:
        raise SystemExit("render log has no native MTSDF route")
    for marker in ("route=software", "UnsupportedCapability", "render failed"):
        if marker in log_text:
            raise SystemExit(f"render log contains {marker!r}")

    stills = {}
    stills_dir = OUT / "stills"
    stills_dir.mkdir(parents=True, exist_ok=True)
    for label, second in (("early", 1.2), ("mid", 3.0), ("late", 4.8)):
        still = stills_dir / f"text_3d_rotations_{label}.png"
        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-v",
                "error",
                "-ss",
                f"{second:.3f}",
                "-i",
                str(video),
                "-frames:v",
                "1",
                str(still),
            ],
            check=True,
        )
        stills[label] = {
            "path": str(still.relative_to(REPO)),
            "sha256": sha256(still),
        }

    timing = video.with_suffix(".mp4.timing.json")
    manifest = {
        "schema": "chronontemplate.text-3d-rotations.v1",
        "date": "2026-11-12",
        "job_id": "text_3d_rotations_v1",
        "contract": {
            "width": W,
            "height": H,
            "fps": f"{FPS}/1",
            "frames": FRAMES,
            "duration_s": 6.0,
            "font": FONT,
            "axes": ["yaw_y", "pitch_x", "roll_z"],
            "camera": camera(),
        },
        "plan": str(plan_path.relative_to(REPO)),
        "video": str(video.relative_to(REPO)),
        "log": str(log_path.relative_to(REPO)),
        "timing": str(timing.relative_to(REPO)) if timing.is_file() else None,
        "probe": info,
        "sha256": sha256(video),
        "render_seconds": seconds,
        "mtsdf_routes": mtsdf_routes,
        "stills": stills,
        "notes": (
            "Layer-level perspective rotation around Y, X and Z. Text positions "
            "stay in canvas coordinates; the camera is head-on. Not a claim of "
            "After Effects pixel parity."
        ),
    }
    (OUT / "MANIFEST.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    return manifest


def write_readme(manifest: dict) -> None:
    info = manifest["probe"]
    text = f"""# Text 3D rotation lab

A six-second ChrononTemplate demo for the `text_3d_v1` section. Three rows turn
the whole line around Y (yaw), X (pitch) and Z (roll) under a head-on
perspective camera, on the native MTSDF route.

- Contract: {info['width']}x{info['height']}, {info['fps']} fps, {info['frames']} frames, {info['duration_s']} s
- Video: `{manifest['video']}`
- SHA-256: `{manifest['sha256']}`
- Native route lines: `{manifest['mtsdf_routes']}` (`route=mtsdf`)
- Stills: `{', '.join(row['path'] for row in manifest['stills'].values())}`

Regenerate and render:

```bash
python3 ChrononTemplate/tools/text_animators/build_text_3d_rotations.py --render
```

The text position stays in canvas coordinates; `[0, 0]` is the top-left corner.
For a 3D text layer with a camera, centre it explicitly (`[960, y]` on a
1920x1080 canvas). The demo also converts each intended screen anchor through
the camera projection, so the YAW/PITCH/ROLL labels stay aligned even though
the camera mirrors and magnifies Y. The motion is layer-level perspective, not
a claim of pixel parity with After Effects.
"""
    (OUT / "README.md").write_text(text, encoding="utf-8")


def render() -> dict:
    if not CLI.is_file():
        raise SystemExit(f"chronon3d_cli not found: {CLI}")
    plan_path = generate()
    validate(plan_path)
    video = OUT / "text_3d_rotations_v1.mp4"
    log_path = OUT / "render.log"
    command = [
        str(CLI),
        "render",
        "--plan",
        str(plan_path),
        "--assets-root",
        str(ASSETS),
        "--backend",
        "vulkan",
        "--gpu-hot-path-mode",
        "require_gpu_native",
        "--tone-map",
        "aces",
        "--exposure",
        "1.0",
        "-o",
        str(video),
    ]
    started = time.time()
    with log_path.open("w", encoding="utf-8") as handle:
        handle.write(" ".join(command) + "\n\n")
        handle.flush()
        result = subprocess.run(
            command, cwd=REPO, stdout=handle, stderr=subprocess.STDOUT
        )
    if result.returncode != 0:
        tail = log_path.read_text(encoding="utf-8", errors="replace").strip().splitlines()[-12:]
        raise SystemExit(f"render failed: {' | '.join(tail)}")
    seconds = round(time.time() - started, 1)
    manifest = verify(video, plan_path, log_path, seconds)
    write_readme(manifest)
    print(f"RENDER {video.relative_to(REPO)} {seconds}s")
    print(f"SHA256 {manifest['sha256']}")
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--generate", action="store_true")
    parser.add_argument("--render", action="store_true")
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    if args.render:
        render()
    elif args.generate:
        generate()
    elif args.verify:
        plan_path = OUT / "text_3d_rotations_v1.plan.json"
        video = OUT / "text_3d_rotations_v1.mp4"
        log_path = OUT / "render.log"
        manifest = verify(video, plan_path, log_path, 0.0)
        write_readme(manifest)
        print(json.dumps(manifest["probe"], indent=2))
    else:
        parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
