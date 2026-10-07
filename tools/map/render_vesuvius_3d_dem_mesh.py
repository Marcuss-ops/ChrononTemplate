#!/usr/bin/env python3
"""
Mount Vesuvius Real 3D DEM Terrain Mesh & Orbital Flyover Suite

Features:
1. Authentic Digital Elevation Model (DEM) displacement from AWS Terrarium tiles
   (true altitude in meters: Sea level 0m -> Gran Cono Crater 1,281m).
2. True 3D Triangulated Mesh (130,050 triangles) with surface normal vectors.
3. ModernGL EGL hardware rendering on NVIDIA RTX A4000 GPU (depth testing, dynamic sunlight shading).
4. Full 3D camera trajectory: Supersonic descent + 3D orbital sweep around the volcanic crater with real parallax.
5. High-end tactical HUD & floating holographic callout card (Urbanist + Inter typography).
6. Hardware-accelerated NVIDIA GPU NVENC H.264 video encoding at 1080p 30 FPS.
7. Automatic upload to Google Drive folder: 1WALc4JbFz6uK5nEM_tYnAeQqiPVRacp_.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import json
import math
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

import cv2
import moderngl
import numpy as np
from PIL import Image, ImageDraw, ImageFont

# Canvas & Timing
WIDTH = 1920
HEIGHT = 1080
FPS = 30
TOTAL_FRAMES = 180  # 6.0 seconds

# Target: Mount Vesuvius (Napoli, Italy)
TARGET_LAT = 40.8224
TARGET_LON = 14.4289
TARGET_NAME = "VESUVIO (GRAN CONO)"
TARGET_ELEV = 1281.0

# Paths
HERE = Path(__file__).resolve().parent
PROJECT_ROOT = HERE.parents[2]
CHRONON_TEMPLATE = HERE.parents[1]
FONTS_DIR = PROJECT_ROOT / "Chronon3d/assets/fonts"
OUT_DIR = CHRONON_TEMPLATE / "out/vesuvius_3d_dem"
OUT_DIR.mkdir(parents=True, exist_ok=True)
CACHE_DIR = PROJECT_ROOT / "Chronon3d/assets/maps/cache/dem_vesuvius"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

# Google Drive credentials
DRIVE_FOLDER_ID = "1WALc4JbFz6uK5nEM_tYnAeQqiPVRacp_"
CRED_PATH = PROJECT_ROOT / "RenderingGen/UploadDrive/credentials.json"
TOKEN_PATH = PROJECT_ROOT / "RenderingGen/UploadDrive/token.json"
DRIVE_BIN = PROJECT_ROOT / "RenderingGen/bin/drive-upload"

# Palette
COLOR_CYAN_HUD = (255, 240, 0)
COLOR_EMERALD_LOCK = (129, 185, 16)
COLOR_WHITE = (255, 255, 255)
COLOR_ORANGE_MAGMA = (20, 110, 255)


def smoothstep_c2(t: float) -> float:
    t = max(0.0, min(1.0, float(t)))
    return t * t * t * (t * (t * 6.0 - 15.0) + 10.0)


def fetch_tile(url: str, cache_file: Path) -> np.ndarray:
    if cache_file.exists():
        try:
            img = cv2.imread(str(cache_file), cv2.IMREAD_COLOR)
            if img is not None:
                return img
        except Exception:
            pass

    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Chronon3D-DEM/2.0)"})
    for _ in range(3):
        try:
            with urllib.request.urlopen(req, timeout=6) as r:
                raw = r.read()
                img = cv2.imdecode(np.frombuffer(raw, np.uint8), cv2.IMREAD_COLOR)
                if img is not None:
                    cache_file.parent.mkdir(parents=True, exist_ok=True)
                    cache_file.write_bytes(raw)
                    return img
        except Exception:
            time.sleep(0.1)

    return np.zeros((256, 256, 3), dtype=np.uint8)


def load_vesuvius_data(zoom: int = 13, tile_radius: int = 2):
    """Loads 5x5 tile grid for satellite texture and AWS Terrarium DEM."""
    lat_rad = math.radians(TARGET_LAT)
    n = 2.0 ** zoom
    center_tx = int((TARGET_LON + 180.0) / 360.0 * n)
    center_ty = int((1.0 - math.asinh(math.tan(lat_rad)) / math.pi) / 2.0 * n)

    grid_dim = 2 * tile_radius + 1
    tile_px = 256
    full_w = grid_dim * tile_px
    full_h = grid_dim * tile_px

    sat_grid = np.zeros((full_h, full_w, 3), dtype=np.uint8)
    dem_grid = np.zeros((full_h, full_w), dtype=np.float32)

    tasks = []
    for dy in range(-tile_radius, tile_radius + 1):
        for dx in range(-tile_radius, tile_radius + 1):
            tx = center_tx + dx
            ty = center_ty + dy
            dem_url = f"https://s3.amazonaws.com/elevation-tiles-prod/terrarium/{zoom}/{tx}/{ty}.png"
            sat_url = f"https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{zoom}/{ty}/{tx}"
            tasks.append((dx, dy, tx, ty, dem_url, sat_url))

    print(f"Fetching {len(tasks)} DEM & Sat tiles for Vesuvius at zoom {zoom}...")
    dem_cache_dir = CACHE_DIR / "dem"
    sat_cache_dir = CACHE_DIR / "sat"

    for dx, dy, tx, ty, dem_url, sat_url in tasks:
        x_off = (dx + tile_radius) * tile_px
        y_off = (dy + tile_radius) * tile_px

        dem_img = fetch_tile(dem_url, dem_cache_dir / f"{zoom}_{tx}_{ty}.png")
        R = dem_img[:, :, 2].astype(np.float32)
        G = dem_img[:, :, 1].astype(np.float32)
        B = dem_img[:, :, 0].astype(np.float32)
        elev = (R * 256.0 + G + B / 256.0) - 32768.0
        dem_grid[y_off:y_off + tile_px, x_off:x_off + tile_px] = elev

        sat_img = fetch_tile(sat_url, sat_cache_dir / f"{zoom}_{tx}_{ty}.jpg")
        sat_grid[y_off:y_off + tile_px, x_off:x_off + tile_px] = sat_img

    print(f"Stitched DEM grid: min={dem_grid.min():.1f}m, max={dem_grid.max():.1f}m")
    return sat_grid, dem_grid, zoom, full_w, full_h


def build_3d_terrain_mesh(sat_grid, dem_grid, zoom, full_w, full_h, mesh_res: int = 256):
    """Generates triangulated 3D mesh with positions, normals, and UVs."""
    lat_rad = math.radians(TARGET_LAT)
    m_per_px = (156543.03392 * math.cos(lat_rad)) / (2.0 ** zoom)
    terrain_size_m_x = full_w * m_per_px
    terrain_size_m_y = full_h * m_per_px

    dem_sub = cv2.resize(dem_grid, (mesh_res, mesh_res), interpolation=cv2.INTER_LINEAR)

    xs = np.linspace(-terrain_size_m_x * 0.5, terrain_size_m_x * 0.5, mesh_res, dtype=np.float32)
    ys = np.linspace(terrain_size_m_y * 0.5, -terrain_size_m_y * 0.5, mesh_res, dtype=np.float32)
    grid_x, grid_y = np.meshgrid(xs, ys)
    grid_z = dem_sub

    # Normal vectors
    dz_dx, dz_dy = np.gradient(grid_z, xs[1] - xs[0], ys[0] - ys[1])
    normals = np.stack([-dz_dx, -dz_dy, np.ones_like(grid_z)], axis=-1)
    norm_len = np.linalg.norm(normals, axis=-1, keepdims=True)
    normals /= np.maximum(norm_len, 1e-6)

    # UV coordinates
    uv_x, uv_y = np.meshgrid(np.linspace(0.0, 1.0, mesh_res, dtype=np.float32),
                             np.linspace(0.0, 1.0, mesh_res, dtype=np.float32))

    # Vertex buffer
    vertices = np.stack([grid_x, grid_y, grid_z,
                         normals[:, :, 0], normals[:, :, 1], normals[:, :, 2],
                         uv_x, uv_y], axis=-1).astype(np.float32).reshape(-1, 8)

    # Index buffer
    indices = []
    for j in range(mesh_res - 1):
        for i in range(mesh_res - 1):
            idx0 = j * mesh_res + i
            idx1 = idx0 + 1
            idx2 = (j + 1) * mesh_res + i
            idx3 = idx2 + 1
            indices.extend([idx0, idx2, idx1, idx1, idx2, idx3])

    indices = np.array(indices, dtype=np.uint32)

    # Exact crater target coordinates in world meters
    gx = (TARGET_LON + 180.0) / 360.0 * (2.0 ** zoom) * 256.0
    gy = (1.0 - math.asinh(math.tan(lat_rad)) / math.pi) / 2.0 * (2.0 ** zoom) * 256.0
    center_tx = int((TARGET_LON + 180.0) / 360.0 * (2.0 ** zoom))
    center_ty = int((1.0 - math.asinh(math.tan(lat_rad)) / math.pi) / 2.0 * (2.0 ** zoom))
    tile_radius = (full_w // 256 - 1) // 2
    origin_gx = (center_tx - tile_radius) * 256.0
    origin_gy = (center_ty - tile_radius) * 256.0
    cx_px = gx - origin_gx
    cy_px = gy - origin_gy
    crater_world_x = float((cx_px - full_w * 0.5) * m_per_px)
    crater_world_y = float(-(cy_px - full_h * 0.5) * m_per_px)
    crater_z = float(dem_grid[int(round(cy_px)), int(round(cx_px))])

    print(f"3D Mesh built: {len(vertices):,} vertices, {len(indices)//3:,} triangles")
    return vertices, indices, crater_world_x, crater_world_y, crater_z


class Vesuvius3DRenderer:
    """ModernGL EGL Hardware Renderer on NVIDIA GPU."""

    def __init__(self, vertices, indices, sat_texture_bgr, full_w, full_h):
        self.ctx = moderngl.create_context(standalone=True, backend="egl")
        self.ctx.enable(moderngl.DEPTH_TEST)
        self.ctx.enable(moderngl.CULL_FACE)

        self.fbo = self.ctx.framebuffer(
            color_attachments=[self.ctx.texture((WIDTH, HEIGHT), 4)],
            depth_attachment=self.ctx.depth_texture((WIDTH, HEIGHT))
        )

        v_shader = """
        #version 330
        in vec3 in_position;
        in vec3 in_normal;
        in vec2 in_uv;

        uniform mat4 u_mvp;
        uniform mat4 u_model;

        out vec3 v_world_pos;
        out vec3 v_normal;
        out vec2 v_uv;

        void main() {
            v_world_pos = (u_model * vec4(in_position, 1.0)).xyz;
            v_normal = normalize(mat3(u_model) * in_normal);
            v_uv = in_uv;
            gl_Position = u_mvp * vec4(in_position, 1.0);
        }
        """

        f_shader = """
        #version 330
        in vec3 v_world_pos;
        in vec3 v_normal;
        in vec2 v_uv;

        uniform sampler2D u_texture;
        uniform vec3 u_light_dir;
        uniform vec3 u_cam_pos;
        uniform vec3 u_fog_color;
        uniform float u_fog_start;
        uniform float u_fog_end;

        out vec4 fragColor;

        void main() {
            vec4 tex_col = texture(u_texture, v_uv);

            // Sun directional lighting with ambient term
            vec3 n = normalize(v_normal);
            vec3 l = normalize(u_light_dir);
            float diff = max(dot(n, l), 0.0);
            float ambient = 0.42;
            vec3 lit_color = tex_col.rgb * (ambient + (1.0 - ambient) * diff);

            // Distance fog to horizon
            float dist = length(u_cam_pos - v_world_pos);
            float fog_factor = clamp((dist - u_fog_start) / (u_fog_end - u_fog_start), 0.0, 1.0);
            vec3 final_color = mix(lit_color, u_fog_color, fog_factor * 0.88);

            fragColor = vec4(final_color, 1.0);
        }
        """

        self.prog = self.ctx.program(vertex_shader=v_shader, fragment_shader=f_shader)

        # Upload texture
        tex_rgb = cv2.cvtColor(sat_texture_bgr, cv2.COLOR_BGR2RGB)
        self.texture = self.ctx.texture((full_w, full_h), 3, tex_rgb.tobytes())
        self.texture.build_mipmaps()
        self.texture.filter = (moderngl.LINEAR_MIPMAP_LINEAR, moderngl.LINEAR)
        self.texture.use(0)
        self.prog["u_texture"].value = 0

        vbo = self.ctx.buffer(vertices.tobytes())
        ibo = self.ctx.buffer(indices.tobytes())
        self.vao = self.ctx.vertex_array(self.prog, [(vbo, "3f 3f 2f", "in_position", "in_normal", "in_uv")], index_buffer=ibo)

    def render_frame(self, eye: np.ndarray, target: np.ndarray, fov_deg: float = 50.0) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        self.fbo.use()
        self.ctx.clear(0.06, 0.08, 0.13, 1.0, depth=1.0)

        up = np.array([0.0, 0.0, 1.0], dtype=np.float32)
        f_dir = target - eye
        f_dir /= np.linalg.norm(f_dir)
        s_dir = np.cross(f_dir, up)
        s_dir /= np.linalg.norm(s_dir)
        u_dir = np.cross(s_dir, f_dir)

        view = np.eye(4, dtype=np.float32)
        view[0, :3] = s_dir
        view[1, :3] = u_dir
        view[2, :3] = -f_dir
        view[0, 3] = -np.dot(s_dir, eye)
        view[1, 3] = -np.dot(u_dir, eye)
        view[2, 3] = np.dot(f_dir, eye)

        fov_y = math.radians(fov_deg)
        aspect = float(WIDTH) / float(HEIGHT)
        near = 50.0
        far = 75000.0
        t_p = math.tan(fov_y / 2.0)

        proj = np.zeros((4, 4), dtype=np.float32)
        proj[0, 0] = 1.0 / (aspect * t_p)
        proj[1, 1] = 1.0 / t_p
        proj[2, 2] = -(far + near) / (far - near)
        proj[2, 3] = -(2.0 * far * near) / (far - near)
        proj[3, 2] = -1.0

        model = np.eye(4, dtype=np.float32)
        mvp = proj @ (view @ model)

        self.prog["u_mvp"].write(mvp.T.tobytes())
        self.prog["u_model"].write(model.T.tobytes())
        self.prog["u_cam_pos"].value = tuple(eye)
        # Sunlight direction from South-West
        self.prog["u_light_dir"].value = (0.55, -0.55, 0.75)
        self.prog["u_fog_color"].value = (0.06, 0.08, 0.13)
        self.prog["u_fog_start"].value = 9000.0
        self.prog["u_fog_end"].value = 32000.0

        self.vao.render()

        raw = self.fbo.read(components=3, dtype="f1")
        img = np.frombuffer(raw, dtype=np.uint8).reshape((HEIGHT, WIDTH, 3))
        # OpenGL framebuffer has Y=0 at bottom; flip vertically so top of frame is North/sky!
        img = np.flipud(img)
        # ModernGL returns RGB, convert to BGR for OpenCV
        return img[:, :, ::-1].copy(), mvp, view


class VesuviusHud:
    def __init__(self):
        try:
            self.font_title = ImageFont.truetype(str(FONTS_DIR / "Urbanist.ttf"), 30)
            self.font_sub = ImageFont.truetype(str(FONTS_DIR / "Inter-SemiBold.ttf"), 17)
            self.font_mono = ImageFont.truetype(str(FONTS_DIR / "UbuntuMono-R.ttf"), 18)
            self.font_mono_lg = ImageFont.truetype(str(FONTS_DIR / "UbuntuMono-R.ttf"), 28)
            self.font_card_title = ImageFont.truetype(str(FONTS_DIR / "Urbanist.ttf"), 24)
            self.font_card_sub = ImageFont.truetype(str(FONTS_DIR / "Inter-SemiBold.ttf"), 14)
        except Exception:
            self.font_title = self.font_sub = self.font_mono = self.font_mono_lg = ImageFont.load_default()
            self.font_card_title = self.font_card_sub = ImageFont.load_default()

    def draw_hud(self, frame: np.ndarray, eye_pos: np.ndarray, target_pos: np.ndarray,
                 mvp: np.ndarray, progress: float, pitch_deg: float, yaw_deg: float):
        h, w = frame.shape[:2]
        alt_m = float(eye_pos[2])

        # Project 3D crater center onto 2D screen
        crater_world = np.array([target_pos[0], target_pos[1], target_pos[2], 1.0], dtype=np.float32)
        clip_pt = mvp @ crater_world
        if clip_pt[3] > 0:
            ndc_x = clip_pt[0] / clip_pt[3]
            ndc_y = clip_pt[1] / clip_pt[3]
            ax = int((ndc_x * 0.5 + 0.5) * w)
            ay = int((-ndc_y * 0.5 + 0.5) * h)
        else:
            ax, ay = w // 2, h // 2

        # 1. 3D Crater Target Rings
        if progress > 0.35:
            p_lock = min(1.0, (progress - 0.35) / 0.25)
            for r_idx in range(3):
                t_p = (progress * 3.0 + r_idx * 0.33) % 1.0
                r_val = int(18 + 55 * t_p)
                a_val = max(0.0, 1.0 - t_p) * p_lock
                col_ring = (int(20 * a_val), int(110 * a_val), int(255 * a_val)) # Magma Orange/Red
                cv2.ellipse(frame, (ax, ay), (r_val, int(r_val * 0.65)), 0, 0, 360, col_ring, 2, cv2.LINE_AA)

            cv2.circle(frame, (ax, ay), 5, (20, 180, 255), -1, cv2.LINE_AA)
            cv2.circle(frame, (ax, ay), 7, (255, 255, 255), 2, cv2.LINE_AA)

            # Holographic leader ray
            stem_h = int(140 * p_lock)
            top_x = ax + 30
            top_y = ay - stem_h
            cv2.line(frame, (ax, ay), (top_x, top_y), (0, 240, 255), 2, cv2.LINE_AA)
            cv2.circle(frame, (top_x, top_y), 4, (0, 240, 255), -1, cv2.LINE_AA)

        # 2. PIL Typography
        pil_frame = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        draw = ImageDraw.Draw(pil_frame, "RGBA")

        # Top-Left HUD Badge
        b_w, b_h = 510, 125
        draw.rounded_rectangle([40, 40, 40 + b_w, 40 + b_h], radius=8,
                               fill=(12, 16, 24, 220), outline=(50, 75, 110, 255), width=1)
        draw.text((60, 56), "REAL 3D DEM TERRAIN MESH // 130K TRIANGLES", font=self.font_mono, fill=(0, 240, 255, 255))
        draw.text((60, 82), TARGET_NAME, font=self.font_title, fill=(255, 255, 255, 255))
        draw.text((60, 122), f"WGS84: {TARGET_LAT:.4f}° N, {TARGET_LON:.4f}° E | CRATER: 1,281m",
                  font=self.font_mono, fill=(160, 185, 215, 255))

        # Top-Right HUD Badge
        r_w, r_h = 470, 125
        r_x = w - 40 - r_w
        draw.rounded_rectangle([r_x, 40, r_x + r_w, 40 + r_h], radius=8,
                               fill=(12, 16, 24, 220), outline=(50, 75, 110, 255), width=1)
        alt_str = f"{alt_m / 1000.0:8.2f} km" if alt_m >= 1000.0 else f"{alt_m:8.0f} m"
        draw.text((r_x + 25, 56), "CAMERA EYE ALTITUDE (ASL)", font=self.font_mono, fill=(0, 240, 255, 255))
        draw.text((r_x + 25, 78), alt_str, font=self.font_mono_lg, fill=(255, 255, 255, 255))
        draw.text((r_x + 25, 122), f"3D PITCH: {pitch_deg:4.1f}° | BEARING: {yaw_deg:03.0f}° | GPU EGL",
                  font=self.font_mono, fill=(16, 185, 129, 255))

        # Bottom Timeline Bar
        bar_x = 80
        bar_w = w - 160
        bar_y = h - 50
        draw.rectangle([bar_x, bar_y, bar_x + bar_w, bar_y + 6], fill=(25, 35, 45, 220))
        fill_w = int(bar_w * progress)
        draw.rectangle([bar_x, bar_y, bar_x + fill_w, bar_y + 6], fill=(0, 240, 255, 255))
        draw.text((bar_x, bar_y - 24), "STATUS: 3D VOLCANIC CALDERA ORBITAL FLYOVER (DEM REAL GEOMETRY)",
                  font=self.font_mono, fill=(0, 240, 255, 255))

        # 3. Floating 3D Holographic Card over Caldera
        if progress > 0.45:
            card_p = min(1.0, (progress - 0.45) / 0.18)
            stem_h = int(140 * card_p)
            top_x = ax + 30
            top_y = ay - stem_h
            card_w, card_h = 480, 108
            cx_card = max(40 + card_w // 2, min(w - 40 - card_w // 2, top_x + 18 + card_w // 2))
            cy_card = max(180, min(h - 180, top_y - card_h // 2))
            box = [cx_card - card_w // 2, cy_card - card_h // 2, cx_card + card_w // 2, cy_card + card_h // 2]

            draw.rounded_rectangle(box, radius=8, fill=(255, 255, 255, int(245 * card_p)),
                                   outline=(255, 120, 20, int(255 * card_p)), width=2)
            draw.line([(top_x, top_y), (box[0], top_y)], fill=(0, 240, 255, int(255 * card_p)), width=2)

            if card_p > 0.05:
                draw.text((cx_card, box[1] + 20), "GRAN CONO DEL VESUVIO", font=self.font_card_title,
                          fill=(18, 22, 30, int(255 * card_p)), anchor="mm")
                draw.text((cx_card, box[1] + 48), "COMPLESSO SOMMA-VESUVIO // CALDERA CIRCOLARE",
                          font=self.font_card_sub, fill=(80, 90, 105, int(255 * card_p)), anchor="mm")
                meta_card = "PROFONDITÀ CRATERE: 305m  |  DIAMETRO: 450m"
                draw.text((cx_card, box[1] + 76), meta_card, font=self.font_card_sub,
                          fill=(210, 50, 10, int(255 * card_p)), anchor="mm")

        frame[:] = cv2.cvtColor(np.asarray(pil_frame), cv2.COLOR_RGB2BGR)


def render_vesuvius_3d_flyover():
    print("=================================================================")
    print("CHRONON REAL 3D DEM TERRAIN: MOUNT VESUVIUS ORBITAL FLYOVER")
    print("=================================================================")

    # 1. Load Real DEM & Satellite Tiles
    sat_grid, dem_grid, zoom, full_w, full_h = load_vesuvius_data(zoom=13, tile_radius=2)

    # 2. Build 3D Mesh
    vertices, indices, crater_world_x, crater_world_y, crater_z = build_3d_terrain_mesh(sat_grid, dem_grid, zoom, full_w, full_h, mesh_res=256)

    # 3. Init ModernGL EGL Renderer
    renderer = Vesuvius3DRenderer(vertices, indices, sat_grid, full_w, full_h)
    hud = VesuviusHud()

    out_mp4 = OUT_DIR / "vesuvius_3d_dem_orbital_flyover.mp4"

    # 4. Setup NVENC GPU Encoder
    cmd_nvenc = [
        "ffmpeg", "-y",
        "-f", "rawvideo",
        "-vcodec", "rawvideo",
        "-s", f"{WIDTH}x{HEIGHT}",
        "-pix_fmt", "bgr24",
        "-r", str(FPS),
        "-i", "-",
        "-c:v", "h264_nvenc",
        "-preset", "p5",
        "-cq", "18",
        "-pix_fmt", "yuv420p",
        "-movflags", "+faststart",
        str(out_mp4)
    ]

    try:
        proc = subprocess.Popen(cmd_nvenc, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        using_gpu = True
    except Exception:
        cmd_cpu = [
            "ffmpeg", "-y",
            "-f", "rawvideo",
            "-vcodec", "rawvideo",
            "-s", f"{WIDTH}x{HEIGHT}",
            "-pix_fmt", "bgr24",
            "-r", str(FPS),
            "-i", "-",
            "-c:v", "libx264",
            "-preset", "veryfast",
            "-crf", "18",
            "-pix_fmt", "yuv420p",
            "-movflags", "+faststart",
            str(out_mp4)
        ]
        proc = subprocess.Popen(cmd_cpu, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        using_gpu = False

    print(f"Video pipeline started. Encoder: {'NVIDIA NVENC (GPU)' if using_gpu else 'libx264 (CPU)'}")

    t_start = time.perf_counter()
    stills_saved = {}

    target = np.array([crater_world_x, crater_world_y, crater_z], dtype=np.float32)

    for f_idx in range(TOTAL_FRAMES):
        prog = f_idx / float(TOTAL_FRAMES - 1)
        eased_prog = smoothstep_c2(prog)

        # Flight Envelope:
        # Distance: 13 km -> 4.2 km from the crater
        dist_m = 13000.0 - 8800.0 * eased_prog
        # Pitch: 26° -> 48° (tilting down into the crater)
        pitch_deg = 26.0 + 22.0 * eased_prog
        # Yaw: Sweeping 110 degrees around the volcano (from SW to SE/East)
        yaw_deg = 15.0 + 105.0 * eased_prog

        pitch_rad = math.radians(pitch_deg)
        yaw_rad = math.radians(yaw_deg)

        cam_x = crater_world_x + dist_m * math.sin(yaw_rad) * math.cos(pitch_rad)
        cam_y = crater_world_y - dist_m * math.cos(yaw_rad) * math.cos(pitch_rad)
        cam_z = crater_z + dist_m * math.sin(pitch_rad)

        eye = np.array([cam_x, cam_y, cam_z], dtype=np.float32)

        # Render 3D terrain
        frame, mvp, view = renderer.render_frame(eye, target, fov_deg=50.0)

        # Draw HUD & 3D callout
        hud.draw_hud(frame, eye, target, mvp, prog, pitch_deg, yaw_deg)

        proc.stdin.write(frame.tobytes())

        if f_idx == 0:
            still_path = OUT_DIR / "vesuvius_01_approach_still.png"
            cv2.imwrite(str(still_path), frame)
            stills_saved["approach"] = still_path
        elif f_idx == int(TOTAL_FRAMES * 0.50):
            still_path = OUT_DIR / "vesuvius_02_caldera_orbit_still.png"
            cv2.imwrite(str(still_path), frame)
            stills_saved["orbit"] = still_path
        elif f_idx == TOTAL_FRAMES - 1:
            still_path = OUT_DIR / "vesuvius_03_close_crater_still.png"
            cv2.imwrite(str(still_path), frame)
            stills_saved["crater"] = still_path

        if f_idx % 30 == 0 or f_idx == TOTAL_FRAMES - 1:
            fps_cur = (f_idx + 1) / max(0.001, time.perf_counter() - t_start)
            print(f"  Frame {f_idx + 1:3d}/{TOTAL_FRAMES} (prog={prog * 100:5.1f}%, dist={dist_m/1000:4.1f}km, pitch={pitch_deg:4.1f}°, yaw={yaw_deg:4.1f}°, speed={fps_cur:4.1f} fps)")

    proc.stdin.close()
    proc.wait()

    elapsed = time.perf_counter() - t_start
    file_size_mb = out_mp4.stat().st_size / (1024 * 1024) if out_mp4.exists() else 0.0
    print(f"\nRender completed in {elapsed:.1f}s ({TOTAL_FRAMES / elapsed:.1f} FPS)!")
    print(f"Saved Real 3D DEM video ({file_size_mb:.2f} MB): {out_mp4}")

    return out_mp4, stills_saved


def upload_to_drive(video_path: Path):
    print(f"\nUploading Real 3D DEM video to Google Drive folder: {DRIVE_FOLDER_ID}...")
    drive_name = "00_vesuvius_real_3d_dem_caldera_orbit.mp4"
    print(f"  Uploading {drive_name} ({video_path})...")
    cmd = [
        str(DRIVE_BIN),
        "-credentials", str(CRED_PATH),
        "-token", str(TOKEN_PATH),
        "-folder", str(DRIVE_FOLDER_ID),
        "-file", str(video_path),
        "-name", drive_name
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode == 0:
        print(f"  ✓ Uploaded {drive_name}: {res.stdout.strip()}")
    else:
        print(f"  ✗ Failed {drive_name}: {res.stderr.strip()}")


if __name__ == "__main__":
    mp4_file, stills = render_vesuvius_3d_flyover()
    upload_to_drive(mp4_file)
