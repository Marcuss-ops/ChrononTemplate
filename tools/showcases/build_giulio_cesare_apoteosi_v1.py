#!/usr/bin/env python3
"""Prepare the Julius Caesar bust and emit the Chronon3D RenderPlan V3 scene.

The museum scan is decimated once into a value-only inline mesh. Chronon3D owns
the 3D render, the overhead spot, the orbiting camera, the depth of field and
the video frames; the source scan is used only as geometry.

The final title is a pre-blurred plate composited behind the bust by
tools/showcases/composite_giulio_cesare_apoteosi_v1.py. The software mesh
compositor paints mesh layers in layer order and ignores the per-layer depth
map across mesh layers, so a 3D title behind the bust covered the chest.The bust, camera, light rig, DoF and frames remain Chronon3D. The bust stays
static and a 360-degree camera orbit is baked into resolved camera_samples, one
sample per output frame.

Usage:
    python3 tools/showcases/build_giulio_cesare_apoteosi_v1.py
    python3 tools/showcases/build_giulio_cesare_apoteosi_v1.py --force
"""

from __future__ import annotations

import argparse
import json
import math
import struct
from pathlib import Path

import numpy as np

TEMPLATE_ROOT = Path(__file__).resolve().parents[2]
PROJECT_ROOT = TEMPLATE_ROOT.parent
ASSET_DIR = TEMPLATE_ROOT / "assets" / "giulio_cesare_apoteosi_v1"
SOURCE_STL = ASSET_DIR / "source" / "SMK_KAS297_Julius_Caesar_small.stl"
MESH_JSON = ASSET_DIR / "giulio_cesare_bust_mesh.json"
TITLE_MESH_JSON = ASSET_DIR / "giulio_cesare_title_mesh.json"
OUT_DIR = TEMPLATE_ROOT / "out" / "giulio_cesare_apoteosi_v1"
PLAN_JSON = OUT_DIR / "giulio_cesare_apoteosi_v4.plan.json"

WIDTH = 1920
HEIGHT = 1080
FPS = 30
FRAMES = 240
CAMERA_RADIUS = 1400.0
FOCUS_DISTANCE = 1400.0
BUST_SCALE = 680.0
BUST_BASE_Y = 200.0


def read_binary_stl(path: Path) -> tuple[np.ndarray, np.ndarray]:
    with path.open("rb") as stream:
        stream.read(80)
        count_bytes = stream.read(4)
        if len(count_bytes) != 4:
            raise ValueError(f"truncated STL header: {path}")
        count = struct.unpack("<I", count_bytes)[0]
        expected = count * 50
        payload = stream.read(expected)
        if len(payload) != expected:
            raise ValueError(f"truncated STL payload: {path}")
    dtype = np.dtype([("normal", "<f4", (3,)), ("vertices", "<f4", (3, 3)), ("attr", "<u2")])
    records = np.frombuffer(payload, dtype=dtype, count=count)
    return records["vertices"].reshape(-1, 3).astype(np.float64), records["normal"].astype(np.float64)


def weld(vertices: np.ndarray, faces: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    rounded = np.round(vertices, 4)
    unique, inverse = np.unique(rounded, axis=0, return_inverse=True)
    remapped = inverse.reshape(-1)[faces]
    valid = (
        (remapped[:, 0] != remapped[:, 1])
        & (remapped[:, 1] != remapped[:, 2])
        & (remapped[:, 2] != remapped[:, 0])
    )
    return unique, remapped[valid].astype(np.int64)


def decimate(vertices: np.ndarray, faces: np.ndarray, target_faces: int) -> tuple[np.ndarray, np.ndarray]:
    import fast_simplification

    reduction = max(0.0, min(0.99, 1.0 - target_faces / max(1, len(faces))))
    simplified = fast_simplification.simplify(
        vertices.astype(np.float32),
        faces.astype(np.int32),
        target_reduction=float(reduction),
        agg=7,
    )
    vertices, faces = simplified[0].astype(np.float64), simplified[1].astype(np.int64)
    return weld(vertices, faces)


def prepare_mesh(force: bool = False) -> dict:
    if MESH_JSON.exists() and not force and MESH_JSON.stat().st_mtime >= SOURCE_STL.stat().st_mtime:
        return json.loads(MESH_JSON.read_text())

    raw_vertices, _ = read_binary_stl(SOURCE_STL)
    vertices, faces = weld(raw_vertices, np.arange(len(raw_vertices), dtype=np.int64).reshape(-1, 3))
    vertices, faces = decimate(vertices, faces, target_faces=14000)

    # SMK scan is Z-up with the face toward -Y. Map it to Chronon's Y-up world:
    # (x, z, y), which leaves the face toward -Z (the camera at frame 0), then
    # normalize to a unit-height bust centered on its vertical axis.
    points = np.column_stack((vertices[:, 0], vertices[:, 2], vertices[:, 1]))
    if float(np.sum(np.einsum("ij,ij->i", points[faces[:, 0]], np.cross(points[faces[:, 1]], points[faces[:, 2]])))) < 0.0:
        faces = faces[:, ::-1]

    minimum = points.min(axis=0)
    maximum = points.max(axis=0)
    height = float(maximum[1] - minimum[1])
    if not math.isfinite(height) or height <= 0.0:
        raise ValueError("bust has invalid vertical extent")
    points[:, 0] -= 0.5 * (minimum[0] + maximum[0])
    points[:, 1] -= minimum[1]
    points[:, 2] -= 0.5 * (minimum[2] + maximum[2])
    points /= height
    points[:, 1] -= points[:, 1].min()

    # Area-weighted smooth normals make the decimated scan read as carved stone
    # instead of a faceted low-poly proxy.
    normals = np.zeros_like(points)
    triangles = points[faces]
    weighted = np.cross(triangles[:, 1] - triangles[:, 0], triangles[:, 2] - triangles[:, 0])
    for corner in range(3):
        np.add.at(normals, faces[:, corner], weighted)
    lengths = np.linalg.norm(normals, axis=1)
    nonzero = lengths > 1e-12
    normals[nonzero] /= lengths[nonzero, None]
    normals[~nonzero] = (0.0, 1.0, 0.0)

    mesh_vertices = []
    for position, normal in zip(points, normals):
        mesh_vertices.append({
            "position": [round(float(value), 6) for value in position],
            "normal": [round(float(value), 6) for value in normal],
            "uv": [0.0, 0.0],
        })

    mesh = {
        "source": {
            "file": str(SOURCE_STL.relative_to(PROJECT_ROOT)),
            "asset": "SMK KAS297 Julius Caesar",
            "triangles": int(len(faces)),
            "vertices": int(len(points)),
        },
        "material": {
            "diffuse": 0.92,
            "specular": 0.34,
            "shininess": 26.0,
            "rim_intensity": 0.18,
            "base_color": [0.68, 0.60, 0.48, 1.0],
            "metallic": 0.0,
            "roughness": 0.54,
        },
        "vertices": mesh_vertices,
        "indices": [int(index) for index in faces.reshape(-1)],
    }
    MESH_JSON.parent.mkdir(parents=True, exist_ok=True)
    MESH_JSON.write_text(json.dumps(mesh, separators=(",", ":"), allow_nan=False) + "\n")
    print(f"mesh: {len(points)} vertices, {len(faces)} triangles -> {MESH_JSON} ({MESH_JSON.stat().st_size / 1e6:.1f} MB)")
    return mesh


def add_collar(mesh: dict, sections: int = 96) -> dict:
    """Fill the annular gap between the bust cut and its socle.

    The SMK scan has a square museum peg at the joint. From every side the
    chest and the round socle read as two detached objects, with a ring of
    background visible around the peg. This lathe-turned collar overlaps the
    socle top and the chest cut, hides the peg, and makes the silhouette
    continuous while keeping the original sculpture geometry untouched.
    """
    profile = [
        (0.252, 0.178),
        (0.265, 0.194),
        (0.282, 0.196),
        (0.300, 0.182),
        (0.320, 0.189),
        (0.342, 0.202),
        (0.358, 0.203),
    ]
    verts: list[dict] = []
    faces: list[int] = []

    # Side surface. The profile is a polyline in (y, radius): its outward
    # normal in the meridian plane is (dy, -dr).
    for index, (y, radius) in enumerate(profile):
        if index == 0:
            dy, dr = profile[1][0] - y, profile[1][1] - radius
        elif index == len(profile) - 1:
            dy, dr = y - profile[index - 1][0], radius - profile[index - 1][1]
        else:
            dy = profile[index + 1][0] - profile[index - 1][0]
            dr = profile[index + 1][1] - profile[index - 1][1]
        normal_radial, normal_y = dy, -dr
        normal_length = math.hypot(normal_radial, normal_y)
        normal_radial /= normal_length
        normal_y /= normal_length
        for step in range(sections):
            theta = 2.0 * math.pi * step / sections
            cos_t, sin_t = math.cos(theta), math.sin(theta)
            verts.append({
                "position": [round(radius * cos_t, 6), round(y, 6), round(radius * sin_t, 6)],
                "normal": [round(normal_radial * cos_t, 6), round(normal_y, 6), round(normal_radial * sin_t, 6)],
                "uv": [0.0, 0.0],
            })

    for ring in range(len(profile) - 1):
        for step in range(sections):
            a = ring * sections + step
            b = ring * sections + (step + 1) % sections
            c = (ring + 1) * sections + step
            d = (ring + 1) * sections + (step + 1) % sections
            faces.extend([a, c, b, b, c, d])

    # Flat caps are hidden inside the plaster; add them so the collar remains
    # a closed solid and the shadow/depth passes see a watertight piece.
    for cap_y, cap_radius, cap_normal in (
        (profile[0][0], profile[0][1], -1.0),
        (profile[-1][0], profile[-1][1], 1.0),
    ):
        center = len(verts)
        verts.append({"position": [0.0, cap_y, 0.0], "normal": [0.0, cap_normal, 0.0], "uv": [0.0, 0.0]})
        ring_start = len(verts)
        for step in range(sections):
            theta = 2.0 * math.pi * step / sections
            cos_t, sin_t = math.cos(theta), math.sin(theta)
            verts.append({
                "position": [round(cap_radius * cos_t, 6), round(cap_y, 6), round(cap_radius * sin_t, 6)],
                "normal": [0.0, cap_normal, 0.0],
                "uv": [0.0, 0.0],
            })
        for step in range(sections):
            a = ring_start + step
            b = ring_start + (step + 1) % sections
            if cap_normal > 0.0:
                faces.extend([center, a, b])
            else:
                faces.extend([center, b, a])

    # Make the winding outward, independently of the cap convention above.
    positions = np.asarray([vertex["position"] for vertex in verts], dtype=np.float64)
    indices = np.asarray(faces, dtype=np.int64).reshape(-1, 3)
    signed_volume = float(np.sum(np.einsum(
        "ij,ij->i", positions[indices[:, 0]],
        np.cross(positions[indices[:, 1]], positions[indices[:, 2]]))) / 6.0)
    if signed_volume < 0.0:
        indices = indices[:, ::-1]

    offset = len(mesh["vertices"])
    mesh["vertices"].extend(verts)
    mesh["indices"].extend(int(index) + offset for index in indices.reshape(-1))
    mesh["collar"] = {
        "profile": [[round(y, 6), round(radius, 6)] for y, radius in profile],
        "sections": sections,
        "volume": round(abs(signed_volume), 6),
    }
    print(f"collar: {len(verts)} vertices, {len(indices)} triangles, volume {abs(signed_volume):.6f}")
    return mesh


def camera_at(angle_deg: float) -> dict:
    theta = math.radians(angle_deg)
    return {
        "type": "perspective",
        "position": [
            WIDTH / 2.0 + CAMERA_RADIUS * math.sin(theta),
            HEIGHT / 2.0,
            -CAMERA_RADIUS * math.cos(theta),
        ],
        "rotation_deg": [0.0, -angle_deg, 0.0],
        "fov_deg": 32.0,
        "near": 1.0,
        "far": 6000.0,
        "zoom": 1.0,
        "sensor_width_mm": 36.0,
        "lens_shift": [0.0, 0.0],
        "f_stop": 2.0,
        "iris_blades": 0,
        "dof": {
            "enabled": True,
            "focus_distance": FOCUS_DISTANCE,
            "max_blur": 30.0,
            "f_stop": 2.0,
            "iris_blades": 0,
            "highlight_gain": 0.0,
        },
    }


def load_title_mesh() -> dict:
    if not TITLE_MESH_JSON.exists():
        raise FileNotFoundError(f"missing title mesh: {TITLE_MESH_JSON}; run build_giulio_cesare_title_mesh.py")
    return json.loads(TITLE_MESH_JSON.read_text())


def build_camera_samples() -> list[dict]:
    """Resolve a 360-degree camera orbit at every output frame.

    The bust stays static. The camera circles it at constant radius and height,
    so the title and floor plate remain fixed while parallax and specular
    highlights reveal the sculpture. One sample per frame covers every shutter
    time without relying on interpolation.
    """
    return [
        {
            "frame": frame,
            "camera": camera_at(360.0 * frame / (FRAMES - 1)),
        }
        for frame in range(FRAMES)
    ]


def build_plan(mesh: dict, title: dict) -> dict:
    camera_samples = build_camera_samples()
    camera = camera_samples[0]["camera"]

    plan = {
        "schema": "chronon.render-plan.v3",
        "version": 3,
        "job_id": "giulio_cesare_apoteosi_v4",
        "canvas": {
            "width": WIDTH,
            "height": HEIGHT,
            "fps_num": FPS,
            "fps_den": 1,
            "duration_frames": FRAMES,
        },
        "camera": camera,
        "camera_samples": camera_samples,
        "lighting_rig": {
            "key_direction": [0.04, -0.88, -0.35],
            "key_intensity": 1.30,
            "key_color": [1.0, 0.92, 0.80, 1.0],
            "ambient_color": [0.48, 0.55, 0.68, 1.0],
            "ambient_intensity": 0.30,
            "rim_enabled": True,
            "rim_color": [0.70, 0.80, 1.0, 1.0],
            "rim_intensity": 0.45,
            "rim_power": 2.8,
        },
        # No screen-space background: on this software build it is composited
        # over the 3D scene in a quadrant, covering the bust. The native clear
        # is black and the 3D title/bust are depth-composited cleanly.
        "layers": [
            {
                # A real extruded title mesh behind the bust: depth testing
                # hides it behind the shoulders, and the camera DoF blurs it.
                "id": "giulio_cesare_title",
                "type": "mesh",
                "size": [1.0, 1.0],
                "position": [WIDTH / 2.0, 520.0, 1500.0],
                "scale": [229.0, 229.0, 229.0],
                "rotation": [0, 0, 0],
                "enable_3d": True,
                "screen_space": False,
                "loop": False,
                "opacity": 1.0,
                "start_frame": 0,
                "duration_frames": FRAMES,
                "color": [1, 1, 1, 1],
                "inline_mesh": {
                    "material": title["material"],
                    "vertices": title["vertices"],
                    "indices": title["indices"],
                },
            },
            {
                "id": "caesar_bust",
                "type": "mesh",
                "size": [BUST_SCALE, BUST_SCALE],
                "position": [WIDTH / 2.0, BUST_BASE_Y, 0.0],
                "scale": [BUST_SCALE, BUST_SCALE, BUST_SCALE],
                "rotation": [0, 0, 0],
                "enable_3d": True,
                "screen_space": False,
                "loop": False,
                "opacity": 1.0,
                "start_frame": 0,
                "duration_frames": FRAMES,
                "color": [1, 1, 1, 1],
                "inline_mesh": {
                    "material": mesh["material"],
                    "vertices": mesh["vertices"],
                    "indices": mesh["indices"],
                },
            },
            {
                "id": "overhead_spot",
                "type": "light",
                "position": [WIDTH / 2.0, 1500.0, 0.0],
                "enable_3d": True,
                "start_frame": 0,
                "duration_frames": FRAMES,
                "light": {
                    "kind": "spot",
                    "color": "#FFE2B6",
                    "intensity": 2.1,
                    "direction": [0.0, -0.985, 0.12],
                    "range": 5000.0,
                    "decay": 1.0,
                    "angle": 0.52,
                    "penumbra": 0.62,
                    "cast_shadow": False,
                },
            },
        ],
        "output": {
            "path": "out/giulio_cesare_apoteosi_v4.mp4",
            "format": "mp4",
        },
    }

    # The title is not a scene layer in v2: the software compositor ignores
    # cross-layer mesh depth and always painted it over the chest. The final
    # title is added by composite_giulio_cesare_apoteosi_v1.py as a blurred
    # plate behind the silhouette matte.
    layers = {layer["id"]: layer for layer in plan["layers"]}
    plan["layers"] = [layers["caesar_bust"]]
    return plan


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--force", action="store_true", help="re-decimate even when the mesh cache is fresh")
    args = parser.parse_args()

    mesh = add_collar(prepare_mesh(force=args.force))
    title = load_title_mesh()
    plan = build_plan(mesh, title)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    PLAN_JSON.write_text(json.dumps(plan, separators=(",", ":"), allow_nan=False) + "\n")
    print(f"plan: {PLAN_JSON} ({PLAN_JSON.stat().st_size / 1e6:.2f} MB)")


if __name__ == "__main__":
    main()
