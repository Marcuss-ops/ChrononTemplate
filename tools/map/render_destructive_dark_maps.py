#!/usr/bin/env python3
"""Render five restrained country-map animations with a CUDA compositor and NVENC."""
from __future__ import annotations

import argparse
import json
import math
import os
import subprocess
import tempfile
import sys
from pathlib import Path

import cv2
import numpy as np
import torch
import torch.nn.functional as torch_F

if not torch.cuda.is_available():
    raise RuntimeError("CUDA is required for map rendering; refusing CPU rendering fallback")
GPU_DEVICE = torch.device("cuda")

WIDTH = 1920
HEIGHT = 1080
FPS = 30
SUBPIXEL_SHIFT = 8
SUBPIXEL_SCALE = 1 << SUBPIXEL_SHIFT

HERE = Path(__file__).resolve().parent
PROJECT_ROOT = HERE.parents[2]
CHRONON_TEMPLATE = HERE.parents[1]
CATALOG_DIR = CHRONON_TEMPLATE / "catalog"
GEOJSON_PATH = CATALOG_DIR / "ne_50m_admin_0_countries.geojson"
OUT_DIR = CHRONON_TEMPLATE / "out/destructive_dark_maps"
OUT_DIR.mkdir(parents=True, exist_ok=True)
OPENCV_OUT_DIR = CHRONON_TEMPLATE / "out/destructive_opencv_maps"
FLAG_DIR = CHRONON_TEMPLATE / "assets/flags"
PROJECT_ROOT = HERE.parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "Chronon3d/tools/cartography"))
import dynamic_tile_pyramid as dyn  # noqa: E402
import fast_plate_sampler as fast  # noqa: E402

RENDERER_MODE = "dark_map"
MAP_MOTION_SCENES = {
    "map_image_dark_map_italy_radar_lock": ("dark_map", 1),
    "map_image_opencv_italy_radar_lock": ("opencv", 1),
    "map_image_dark_map_japan_archipelago_chain": ("dark_map", 2),
    "map_image_opencv_japan_archipelago_chain": ("opencv", 2),
    "map_image_dark_map_russia_continental_laser": ("dark_map", 3),
    "map_image_opencv_russia_continental_laser": ("opencv", 3),
    "map_image_dark_map_germany_industrial_nodes": ("dark_map", 4),
    "map_image_opencv_germany_industrial_nodes": ("opencv", 4),
    "map_image_dark_map_saudi_arabia_desert_pipeline": ("dark_map", 5),
    "map_image_opencv_saudi_arabia_desert_pipeline": ("opencv", 5),
}
MAP_SCENE_FILES = {
    1: ("italy", "radar_lock", "01_italy_radar_lock.mp4"),
    2: ("japan", "archipelago_chain", "02_japan_archipelago_chain.mp4"),
    3: ("russia", "continental_laser", "03_russia_continental_laser.mp4"),
    4: ("germany", "industrial_nodes", "04_germany_industrial_nodes.mp4"),
    5: ("saudi_arabia", "desert_pipeline", "05_saudi_arabia_desert_pipeline.mp4"),
}


def write_motion_manifest():
    manifest = {
        "version": 1,
        "width": WIDTH,
        "height": HEIGHT,
        "fps": FPS,
        "duration_seconds": 5,
        "render_backend": "torch_cuda",
        "video_encoder": "h264_nvenc",
        "motions": [],
    }
    for scene_id, (map_id, animation, filename) in MAP_SCENE_FILES.items():
        for renderer, directory in (("dark_map", OUT_DIR), ("opencv", OPENCV_OUT_DIR)):
            motion_id = f"map_image_{renderer}_{map_id}_{animation}"
            manifest["motions"].append({
                "motion_id": motion_id,
                "renderer": renderer,
                "map_id": map_id,
                "animation": animation,
                "scene": scene_id,
                "file": str((directory / filename).relative_to(CHRONON_TEMPLATE)),
            })
    (CHRONON_TEMPLATE / "out/map_animation_renderers_v1.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

# Aesthetic color palettes (BGR for OpenCV)
COLOR_OCEAN_DARK = (14, 12, 10)         # Deep black/charcoal ocean
COLOR_OCEAN_BLUE = (120, 68, 42)        # Steel blue ocean (Latin America style)
COLOR_LAND_DARK = (24, 21, 18)          # Landmass slate
COLOR_LAND_DEEP = (16, 14, 12)          # Darker landmass
COLOR_BORDER_MUTED = (44, 40, 36)       # Country boundaries
COLOR_GRID_BLUE = (145, 95, 65)         # Cartographic grid lines
COLOR_GRID_CYAN = (180, 140, 80)        # Bright grid accents

COLOR_COUNTRY_GLOW = (68, 92, 190)       # Muted warm coral for the highlighted country
FLAG_BRIGHTNESS = 0.80


def smooth_swoop(t: float) -> float:
    t = max(0.0, min(1.0, float(t)))
    return t * t * (3.0 - 2.0 * t)

def ease_out_cubic(t: float) -> float:
    t = max(0.0, min(1.0, float(t)))
    return 1.0 - (1.0 - t) ** 3

def ease_in_cubic(t: float) -> float:
    t = max(0.0, min(1.0, float(t)))
    return t * t * t

def lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


def geographic_bounds(rings: list[np.ndarray]) -> tuple[float, float, float, float]:
    points = np.concatenate(rings, axis=0)
    return (float(points[:, 0].min()), float(points[:, 0].max()),
            float(points[:, 1].min()), float(points[:, 1].max()))


class GeoEngine:
    def __init__(self, geojson_path: Path = GEOJSON_PATH):
        with open(geojson_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        self.country_rings: dict[str, list[np.ndarray]] = {}
        self.all_land_rings: list[tuple[np.ndarray, float, float, float, float]] = []

        for f in data["features"]:
            name = f.get("properties", {}).get("ADMIN")
            geom = f["geometry"]
            coords = []
            if geom["type"] == "Polygon":
                coords = geom["coordinates"]
            elif geom["type"] == "MultiPolygon":
                for p in geom["coordinates"]:
                    coords.extend(p)

            country_list = []
            for r in coords:
                if len(r) >= 3:
                    arr = np.asarray(r, dtype=np.float32)
                    stride = max(1, math.ceil(len(arr) / 600))
                    arr_country = arr[::stride]
                    if len(arr_country) >= 3:
                        country_list.append(arr_country)

                    arr_land = arr[::4]
                    if len(arr_land) >= 3:
                        min_lon, min_lat = float(arr_land[:, 0].min()), float(arr_land[:, 1].min())
                        max_lon, max_lat = float(arr_land[:, 0].max()), float(arr_land[:, 1].max())
                        self.all_land_rings.append((arr_land, min_lon, max_lon, min_lat, max_lat))

            if name:
                self.country_rings[name] = country_list

    def get_country_rings(self, name: str) -> list[np.ndarray]:
        return self.country_rings.get(name, [])


GEO = GeoEngine()


class DynamicCamera:
    def __init__(self, start_pose: tuple[float, float, float],
                 end_pose: tuple[float, float, float],
                 total_frames: int, provider: str = "esri_sat"):
        self.start_pose = start_pose
        self.end_pose = end_pose
        self.total_frames = max(1, total_frames)
        self.basemap_sampler = None
        if RENDERER_MODE == "opencv":
            scales = (start_pose[2], end_pose[2])
            zooms = [math.log2(scale * 360.0 / 256.0) for scale in scales]
            self.basemap_sampler = fast.FastPlateSampler(
                dyn.DynamicTilePyramid(provider=provider), WIDTH, HEIGHT)
            self.basemap_sampler.prepare(
                [(start_pose[1], start_pose[0]), (end_pose[1], end_pose[0])],
                max(0, math.floor(min(zooms))), math.ceil(max(zooms)) + 1)

    def get_pose(self, frame_idx: int) -> tuple[float, float, float]:
        t = smooth_swoop(frame_idx / float(self.total_frames))
        lon = lerp(self.start_pose[0], self.end_pose[0], t)
        lat = lerp(self.start_pose[1], self.end_pose[1], t)
        scale = lerp(self.start_pose[2], self.end_pose[2], t)
        return lon, lat, scale

    def project_point(self, lon: float, lat: float, c_lon: float, c_lat: float, scale: float) -> tuple[int, int]:
        x = WIDTH / 2.0 + (lon - c_lon) * scale
        lat_clamped = max(-85.0, min(85.0, lat))
        c_lat_clamped = max(-85.0, min(85.0, c_lat))
        y_m = math.log(math.tan(math.pi / 4.0 + math.radians(lat_clamped) / 2.0))
        cy_m = math.log(math.tan(math.pi / 4.0 + math.radians(c_lat_clamped) / 2.0))
        y = HEIGHT / 2.0 - (y_m - cy_m) * scale * (180.0 / math.pi)
        return int(round(x)), int(round(y))

    def project_rings(self, rings: list[np.ndarray], c_lon: float, c_lat: float, scale: float) -> list[np.ndarray]:
        c_lat_clamped = max(-85.0, min(85.0, c_lat))
        cy_m = math.log(math.tan(math.pi / 4.0 + math.radians(c_lat_clamped) / 2.0))
        scale_deg = scale * (180.0 / math.pi)

        polys = []
        for r in rings:
            lons = r[:, 0]
            lats = np.clip(r[:, 1], -85.0, 85.0)
            xs = WIDTH / 2.0 + (lons - c_lon) * scale
            yms = np.log(np.tan(np.pi / 4.0 + np.radians(lats) / 2.0))
            ys = HEIGHT / 2.0 - (yms - cy_m) * scale_deg
            pts = np.rint(np.stack([xs, ys], axis=-1) * SUBPIXEL_SCALE).astype(np.int32)
            polys.append(pts)
        return polys

    def render_base(self, c_lon: float, c_lat: float, scale: float,
                    ocean_color=COLOR_OCEAN_DARK, land_color=COLOR_LAND_DARK,
                    border_color=COLOR_BORDER_MUTED, with_grid: bool = True) -> np.ndarray:
        if self.basemap_sampler is not None:
            zoom = math.log2(scale * 360.0 / 256.0)
            frame = self.basemap_sampler.sample_subpixel(c_lat, c_lon, zoom, WIDTH, HEIGHT)
            frame = cv2.addWeighted(frame, 0.77, np.zeros_like(frame), 0.23, 0)
            return frame
        frame = np.zeros((HEIGHT, WIDTH, 3), dtype=np.uint8)
        frame[:] = ocean_color

        if with_grid:
            # Cartographic coordinate grid like Latin America scene
            for x in range(0, WIDTH, 75):
                cv2.line(frame, (x, 0), (x, HEIGHT), COLOR_GRID_BLUE, 1, cv2.LINE_AA)
            for y in range(0, HEIGHT, 75):
                cv2.line(frame, (0, y), (WIDTH, y), COLOR_GRID_BLUE, 1, cv2.LINE_AA)

        lon_margin = (WIDTH / 2.0 + 200) / max(0.1, scale)
        vis_min_lon = c_lon - lon_margin
        vis_max_lon = c_lon + lon_margin

        c_lat_clamped = max(-85.0, min(85.0, c_lat))
        cy_m = math.log(math.tan(math.pi / 4.0 + math.radians(c_lat_clamped) / 2.0))
        scale_deg = scale * (180.0 / math.pi)

        ym_top = cy_m - (-200 - HEIGHT / 2.0) / scale_deg
        ym_bot = cy_m - (HEIGHT + 200 - HEIGHT / 2.0) / scale_deg
        vis_max_lat = math.degrees(2.0 * math.atan(math.exp(ym_top)) - math.pi / 2.0)
        vis_min_lat = math.degrees(2.0 * math.atan(math.exp(ym_bot)) - math.pi / 2.0)

        visible_polys = []
        for arr, min_lon, max_lon, min_lat, max_lat in GEO.all_land_rings:
            if max_lon < vis_min_lon or min_lon > vis_max_lon or max_lat < vis_min_lat or min_lat > vis_max_lat:
                continue
            lons = arr[:, 0]
            lats = np.clip(arr[:, 1], -85.0, 85.0)
            xs = WIDTH / 2.0 + (lons - c_lon) * scale
            yms = np.log(np.tan(np.pi / 4.0 + np.radians(lats) / 2.0))
            ys = HEIGHT / 2.0 - (yms - cy_m) * scale_deg
            pts = np.rint(np.stack([xs, ys], axis=-1) * SUBPIXEL_SCALE).astype(np.int32)
            visible_polys.append(pts)

        if visible_polys:
            cv2.fillPoly(frame, visible_polys, land_color, shift=SUBPIXEL_SHIFT)
            cv2.polylines(frame, visible_polys, True, border_color, 1, cv2.LINE_AA,
                          shift=SUBPIXEL_SHIFT)

        return frame


class GPUMapFrame:
    """CUDA compositor for a single prepared basemap frame."""

    _kernels: dict[float, torch.Tensor] = {}

    def __init__(self, frame: np.ndarray):
        self.pixels = torch.from_numpy(np.ascontiguousarray(frame)).to(
            device=GPU_DEVICE, dtype=torch.float32
        ).permute(2, 0, 1).contiguous()

    @staticmethod
    def mask(mask: np.ndarray | torch.Tensor) -> torch.Tensor:
        if isinstance(mask, torch.Tensor):
            return mask
        tensor = torch.from_numpy(np.ascontiguousarray(mask)).to(device=GPU_DEVICE, dtype=torch.float32)
        return tensor if np.issubdtype(mask.dtype, np.floating) else tensor / 255.0

    @classmethod
    def gaussian(cls, mask: np.ndarray | torch.Tensor, sigma: float) -> torch.Tensor:
        source = cls.mask(mask)
        if sigma not in cls._kernels:
            radius = max(1, int(math.ceil(3 * sigma)))
            coords = torch.arange(-radius, radius + 1, device=GPU_DEVICE, dtype=torch.float32)
            kernel = torch.exp(-(coords * coords) / (2 * sigma * sigma))
            cls._kernels[sigma] = (kernel / kernel.sum()).view(1, 1, 1, -1)
        kernel_x = cls._kernels[sigma]
        kernel_y = kernel_x.transpose(2, 3).contiguous()
        source = source.view(1, 1, HEIGHT, WIDTH)
        radius = kernel_x.shape[-1] // 2
        source = torch_F.pad(source, (radius, radius, 0, 0), mode="replicate")
        source = torch_F.conv2d(source, kernel_x)
        source = torch_F.pad(source, (0, 0, radius, radius), mode="replicate")
        return torch_F.conv2d(source, kernel_y)[0, 0]

    def blend_mask(self, mask: np.ndarray | torch.Tensor,
                   color_bgr: tuple[int, int, int], opacity: float):
        if opacity <= 0:
            return
        alpha = (self.mask(mask) * float(opacity)).clamp_(0.0, 1.0).unsqueeze(0)
        color = torch.tensor(color_bgr, device=GPU_DEVICE, dtype=torch.float32).view(3, 1, 1)
        self.pixels.mul_(1.0 - alpha).add_(color * alpha)

    def blend_patch(self, image_bgr: np.ndarray, mask: np.ndarray | torch.Tensor,
                    x: int, y: int, opacity: float):
        """Composite a flag texture into its projected country-mask bounds on CUDA."""
        if opacity <= 0 or image_bgr.size == 0:
            return
        height, width = image_bgr.shape[:2]
        target = self.pixels[:, y:y + height, x:x + width]
        alpha = (self.mask(mask) * float(opacity)).clamp_(0.0, 1.0).unsqueeze(0)
        source = torch.from_numpy(np.ascontiguousarray(image_bgr)).to(
            device=GPU_DEVICE, dtype=torch.float32
        ).permute(2, 0, 1)
        target.mul_(1.0 - alpha).add_(source * alpha)

    def to_numpy(self) -> np.ndarray:
        return self.pixels.clamp_(0, 255).byte().permute(1, 2, 0).contiguous().cpu().numpy()


class DynamicEffects:
    @staticmethod
    def draw_country_flag(frame: GPUMapFrame, flag_path: Path, polys: list[np.ndarray],
                          progress: float, camera_pose: tuple[float, float, float],
                          geo_bounds: tuple[float, float, float, float]):
        """Project a subdued flag texture and clip it to the country's vector silhouette."""
        if progress <= 0.001 or not polys:
            return
        country_mask = np.zeros((HEIGHT, WIDTH), dtype=np.uint8)
        cv2.fillPoly(country_mask, polys, 255, shift=SUBPIXEL_SHIFT)
        all_points = np.concatenate(polys, axis=0).astype(np.float32) / SUBPIXEL_SCALE
        bx, by, bw, bh = cv2.boundingRect(all_points)
        x0, y0 = max(0, bx), max(0, by)
        x1, y1 = min(WIDTH, bx + bw), min(HEIGHT, by + bh)
        if x0 >= x1 or y0 >= y1:
            return
        flag = cv2.imread(str(flag_path), cv2.IMREAD_COLOR)
        if flag is None:
            raise FileNotFoundError(f"Country flag asset missing: {flag_path}")
        c_lon, c_lat, scale = camera_pose
        min_lon, max_lon, min_lat, max_lat = geo_bounds
        min_lon, max_lon = sorted((min_lon, max_lon))
        min_lat, max_lat = sorted((min_lat, max_lat))
        mercator = lambda lat: math.log(math.tan(math.pi / 4.0 + math.radians(max(-85.0, min(85.0, lat))) / 2.0))
        min_merc, max_merc = mercator(min_lat), mercator(max_lat)
        c_merc = mercator(c_lat)
        map_x = np.broadcast_to(
            c_lon + ((np.arange(x0, x1, dtype=np.float32)[None, :] + 0.5 - WIDTH / 2.0) / scale),
            (y1 - y0, x1 - x0),
        )
        map_y = np.broadcast_to(
            c_merc + (HEIGHT / 2.0 - (np.arange(y0, y1, dtype=np.float32)[:, None] + 0.5)) / (scale * 180.0 / math.pi),
            (y1 - y0, x1 - x0),
        )
        src_x = (map_x - min_lon) / max(1e-6, max_lon - min_lon) * (flag.shape[1] - 1)
        src_y = (max_merc - map_y) / max(1e-6, max_merc - min_merc) * (flag.shape[0] - 1)
        flag = cv2.remap(flag, src_x.astype(np.float32), src_y.astype(np.float32),
                         cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
        flag = np.clip(flag.astype(np.float32) * FLAG_BRIGHTNESS, 0, 255).astype(np.uint8)
        mask_patch = country_mask[y0:y1, x0:x1]
        frame.blend_patch(flag, mask_patch, x0, y0, ease_out_cubic(progress))

    @staticmethod
    def draw_outline_glow(frame: GPUMapFrame, polys: list[np.ndarray],
                          color_bgr: tuple[int, int, int], progress: float = 1.0,
                          thickness: int = 3, halo_strength: float = 1.2):
        if progress <= 0.001 or not polys:
            return
        edge = np.zeros((HEIGHT, WIDTH), dtype=np.uint8)

        if progress >= 0.999:
            cv2.polylines(edge, polys, True, 255, thickness, cv2.LINE_AA, shift=SUBPIXEL_SHIFT)
        else:
            for poly in polys:
                if len(poly) < 2:
                    continue
                points = poly.astype(np.float64) / SUBPIXEL_SCALE
                seg_lens = np.sqrt(np.sum(np.diff(points, axis=0) ** 2, axis=1))
                total_len = float(seg_lens.sum())
                budget = total_len * progress
                if budget <= 0:
                    continue
                for i, d in enumerate(seg_lens):
                    if budget <= 0:
                        break
                    p1 = points[i]
                    p2 = points[(i + 1) % len(poly)]
                    ratio = min(1.0, budget / max(1e-6, d))
                    p_end = p1 + (p2 - p1) * ratio
                    start_fixed = tuple(np.rint(p1 * SUBPIXEL_SCALE).astype(int))
                    end_fixed = tuple(np.rint(p_end * SUBPIXEL_SCALE).astype(int))
                    cv2.line(edge, start_fixed, end_fixed, 255, thickness, cv2.LINE_AA, shift=SUBPIXEL_SHIFT)
                    budget -= d

        edge_gpu = frame.mask(edge)
        for sigma, weight in [(24, 0.40 * halo_strength), (10, 0.65 * halo_strength), (3, 0.90 * halo_strength)]:
            frame.blend_mask(frame.gaussian(edge_gpu, sigma), color_bgr, weight)
        bright = tuple(int(min(255, c * 0.72 + 255 * 0.28)) for c in color_bgr)
        frame.blend_mask(edge_gpu, bright, 0.90)

def write_video_h264(frames: list[np.ndarray], out_path: Path):
    cmd_nvenc = [
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
        "-f", "rawvideo",
        "-vcodec", "rawvideo",
        "-s", f"{WIDTH}x{HEIGHT}",
        "-pix_fmt", "bgr24",
        "-r", str(FPS),
        "-i", "-",
        "-c:v", "h264_nvenc",
        "-gpu", "0",
        "-preset", "p5",
        "-cq", "18",
        "-pix_fmt", "yuv420p",
        "-movflags", "+faststart",
        str(out_path)
    ]
    proc = subprocess.Popen(cmd_nvenc, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    for f in frames:
        try:
            proc.stdin.write(f.tobytes())
        except BrokenPipeError:
            break
    proc.stdin.close()
    error = proc.stderr.read().decode("utf-8", errors="replace")
    proc.wait()
    if proc.returncode != 0:
        raise RuntimeError(f"GPU NVENC encoding failed for {out_path}: {error.strip()}")


class H264NVENCStream:
    """Stream rendered frames to NVENC without retaining a full clip in RAM."""

    def __init__(self, out_path: Path):
        cmd = [
            "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
            "-f", "rawvideo", "-vcodec", "rawvideo",
            "-s", f"{WIDTH}x{HEIGHT}", "-pix_fmt", "bgr24", "-r", str(FPS),
            "-i", "-", "-c:v", "h264_nvenc", "-gpu", "0", "-preset", "p5",
            "-cq", "18", "-pix_fmt", "yuv420p", "-movflags", "+faststart",
            str(out_path),
        ]
        self._stderr = tempfile.TemporaryFile()
        self._proc = subprocess.Popen(cmd, stdin=subprocess.PIPE,
                                      stdout=subprocess.DEVNULL, stderr=self._stderr)

    def __enter__(self):
        return self

    def write(self, frame: np.ndarray):
        if self._proc.stdin is None:
            raise RuntimeError("NVENC stream is already closed")
        self._proc.stdin.write(np.ascontiguousarray(frame).tobytes())

    def close(self):
        if self._proc.stdin is not None:
            self._proc.stdin.close()
            self._proc.stdin = None
        self._stderr.seek(0)
        error = self._stderr.read().decode("utf-8", errors="replace")
        self._stderr.close()
        self._proc.wait()
        if self._proc.returncode != 0:
            raise RuntimeError(f"GPU NVENC streaming failed: {error.strip()}")

    def __exit__(self, exc_type, exc, traceback):
        if exc_type is None:
            self.close()
        else:
            if self._proc.stdin is not None:
                self._proc.stdin.close()
                self._proc.stdin = None
            self._proc.terminate()
            self._proc.wait()
            self._stderr.close()
        return False


# -----------------------------------------------------------------------------
# 5 DISTINCT DESTRUCTIVE DARK ANIMATIONS (1 NATION PER VIDEO)
# -----------------------------------------------------------------------------

def render_italy_radar_lock(out_mp4: Path, num_frames=150):
    """1. ITALY: Tactical Radar Scan & Target Lock HUD with GPS Coordinates."""
    print("Rendering 1/5: Italy Tactical Radar Lock...")
    # Camera starts over high Europe and dives tightly into Italy
    cam = DynamicCamera(start_pose=(10.0, 48.0, 9.0),
                        end_pose=(12.8, 42.0, 36.0),
                        total_frames=num_frames)

    it_rings = GEO.get_country_rings("Italy")
    it_bounds = geographic_bounds(it_rings)
    frames = []

    for f in range(num_frames):
        c_lon, c_lat, scale = cam.get_pose(f)
        frame = cam.render_base(c_lon, c_lat, scale, ocean_color=COLOR_OCEAN_BLUE,
                                land_color=COLOR_LAND_DEEP, border_color=(45, 40, 36), with_grid=False)
        frame = GPUMapFrame(frame)

        it_polys = cam.project_rings(it_rings, c_lon, c_lat, scale)
        country_progress = smooth_swoop((f - 16) / 38.0)
        DynamicEffects.draw_country_flag(frame, FLAG_DIR / "it.png", it_polys, country_progress,
                                         (c_lon, c_lat, scale), it_bounds)
        DynamicEffects.draw_outline_glow(frame, it_polys, COLOR_COUNTRY_GLOW,
                                         progress=country_progress, thickness=2, halo_strength=0.72)

        frames.append(frame.to_numpy())

    write_video_h264(frames, out_mp4)
    print("Done Italy")


def render_japan_archipelago_chain(out_mp4: Path, num_frames=150):
    """2. JAPAN: Archipelago Chain-Reaction Wave & Pacific Pulse."""
    print("Rendering 2/5: Japan Archipelago Chain...")
    cam = DynamicCamera(start_pose=(147.0, 33.0, 9.5),
                        end_pose=(138.5, 37.0, 27.0),
                        total_frames=num_frames)

    jp_rings = GEO.get_country_rings("Japan")
    jp_bounds = geographic_bounds(jp_rings)
    frames = []

    for f in range(num_frames):
        c_lon, c_lat, scale = cam.get_pose(f)
        frame = cam.render_base(c_lon, c_lat, scale, ocean_color=COLOR_OCEAN_BLUE,
                                land_color=COLOR_LAND_DEEP, border_color=(42, 38, 35), with_grid=False)
        frame = GPUMapFrame(frame)

        jp_polys = cam.project_rings(jp_rings, c_lon, c_lat, scale)

        country_progress = smooth_swoop((f - 10) / 48.0)
        DynamicEffects.draw_country_flag(frame, FLAG_DIR / "jp.png", jp_polys, country_progress,
                                         (c_lon, c_lat, scale), jp_bounds)
        DynamicEffects.draw_outline_glow(frame, jp_polys, COLOR_COUNTRY_GLOW,
                                         progress=country_progress, thickness=2, halo_strength=0.72)

        frames.append(frame.to_numpy())

    write_video_h264(frames, out_mp4)
    print("Done Japan")


def render_russia_continental_laser(out_mp4: Path, num_frames=150):
    """3. RUSSIA: understated projected country name and outline glow."""
    print("Rendering 3/5: Russia Continental Laser...")
    # Epic transcontinental glide across Eurasia
    cam = DynamicCamera(start_pose=(45.0, 62.0, 4.4),
                        end_pose=(95.0, 58.0, 5.8),
                        total_frames=num_frames)

    ru_rings = GEO.get_country_rings("Russia")
    ru_bounds = geographic_bounds(ru_rings)
    frames = []

    for f in range(num_frames):
        c_lon, c_lat, scale = cam.get_pose(f)
        frame = cam.render_base(c_lon, c_lat, scale, ocean_color=(15, 13, 11),
                                land_color=COLOR_LAND_DEEP, border_color=(38, 35, 32), with_grid=False)
        frame = GPUMapFrame(frame)

        ru_polys = cam.project_rings(ru_rings, c_lon, c_lat, scale)

        country_progress = smooth_swoop(f / 65.0)
        DynamicEffects.draw_country_flag(frame, FLAG_DIR / "ru.png", ru_polys, country_progress,
                                         (c_lon, c_lat, scale), ru_bounds)
        DynamicEffects.draw_outline_glow(frame, ru_polys, COLOR_COUNTRY_GLOW,
                                         progress=country_progress, thickness=2, halo_strength=0.62)

        frames.append(frame.to_numpy())

    write_video_h264(frames, out_mp4)
    print("Done Russia")


def render_germany_industrial_nodes(out_mp4: Path, num_frames=150):
    """4. GERMANY: Central Europe Hub & Logistic Network Beams."""
    print("Rendering 4/5: Germany Industrial Network...")
    cam = DynamicCamera(start_pose=(10.0, 52.0, 10.0),
                        end_pose=(10.4, 51.2, 38.0),
                        total_frames=num_frames)

    de_rings = GEO.get_country_rings("Germany")
    de_bounds = geographic_bounds(de_rings)
    frames = []

    for f in range(num_frames):
        c_lon, c_lat, scale = cam.get_pose(f)
        frame = cam.render_base(c_lon, c_lat, scale, ocean_color=COLOR_OCEAN_BLUE,
                                land_color=COLOR_LAND_DEEP, border_color=(45, 42, 38), with_grid=False)
        frame = GPUMapFrame(frame)

        de_polys = cam.project_rings(de_rings, c_lon, c_lat, scale)

        country_progress = smooth_swoop(f / 50.0)
        DynamicEffects.draw_country_flag(frame, FLAG_DIR / "de.png", de_polys, country_progress,
                                         (c_lon, c_lat, scale), de_bounds)
        DynamicEffects.draw_outline_glow(frame, de_polys, COLOR_COUNTRY_GLOW,
                                         progress=country_progress, thickness=2, halo_strength=0.72)

        frames.append(frame.to_numpy())

    write_video_h264(frames, out_mp4)
    print("Done Germany")


def render_saudi_arabia_desert_pipeline(out_mp4: Path, num_frames=150):
    """5. SAUDI ARABIA: Desert Grid, Strategic Chokepoints & Red Sea / Gulf Corridors."""
    print("Rendering 5/5: Saudi Arabia Strategic Chokepoints...")
    # Flight from Red Sea diagonally across Saudi desert towards Persian Gulf
    cam = DynamicCamera(start_pose=(39.0, 20.0, 11.5),
                        end_pose=(48.0, 24.5, 23.0),
                        total_frames=num_frames)

    sa_rings = GEO.get_country_rings("Saudi Arabia")
    sa_bounds = geographic_bounds(sa_rings)
    frames = []

    for f in range(num_frames):
        c_lon, c_lat, scale = cam.get_pose(f)
        frame = cam.render_base(c_lon, c_lat, scale, ocean_color=COLOR_OCEAN_BLUE,
                                land_color=COLOR_LAND_DEEP, border_color=(45, 40, 36), with_grid=False)
        frame = GPUMapFrame(frame)

        sa_polys = cam.project_rings(sa_rings, c_lon, c_lat, scale)

        country_progress = smooth_swoop(f / 50.0)
        DynamicEffects.draw_country_flag(frame, FLAG_DIR / "sa.png", sa_polys, country_progress,
                                         (c_lon, c_lat, scale), sa_bounds)
        DynamicEffects.draw_outline_glow(frame, sa_polys, COLOR_COUNTRY_GLOW,
                                         progress=country_progress, thickness=2, halo_strength=0.72)

        frames.append(frame.to_numpy())

    write_video_h264(frames, out_mp4)
    print("Done Saudi Arabia")


def run_single(work: tuple[int, str]):
    global RENDERER_MODE
    scene_id, renderer = work
    RENDERER_MODE = renderer
    out_dir = OUT_DIR if renderer == "dark_map" else OPENCV_OUT_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    scenes = {
        1: (render_italy_radar_lock, out_dir / "01_italy_radar_lock.mp4"),
        2: (render_japan_archipelago_chain, out_dir / "02_japan_archipelago_chain.mp4"),
        3: (render_russia_continental_laser, out_dir / "03_russia_continental_laser.mp4"),
        4: (render_germany_industrial_nodes, out_dir / "04_germany_industrial_nodes.mp4"),
        5: (render_saudi_arabia_desert_pipeline, out_dir / "05_saudi_arabia_desert_pipeline.mp4"),
    }
    fn, path = scenes[scene_id]
    fn(path)


def main():
    parser = argparse.ArgumentParser(description="Render destructive dark map animations (GPU accelerated)")
    parser.add_argument("--scene", type=int, choices=range(1, 6), help="Render specific scene 1-5")
    parser.add_argument("--renderer", choices=("dark_map", "opencv"), default="dark_map",
                        help="dark vector atlas or OpenCV imagery underlay; effects and scene timing are shared")
    parser.add_argument("--motion-id", choices=tuple(MAP_MOTION_SCENES),
                        help="render the exact selectable RenderingGen map motion")
    args = parser.parse_args()

    if not torch.cuda.is_available():
        raise RuntimeError("CUDA is required; no CPU rendering fallback is configured")
    encoder_list = subprocess.run(["ffmpeg", "-hide_banner", "-encoders"], capture_output=True,
                                  text=True, check=True).stdout
    if "h264_nvenc" not in encoder_list:
        raise RuntimeError("FFmpeg h264_nvenc is required; no software encoder fallback is configured")
    print(f"GPU renderer active: {torch.cuda.get_device_name(0)}; encoder=h264_nvenc")

    if args.motion_id:
        renderer, scene_id = MAP_MOTION_SCENES[args.motion_id]
        run_single((scene_id, renderer))
    elif args.scene:
        run_single((args.scene, args.renderer))
    elif args.renderer == "opencv":
        for scene_id in range(1, 6):
            run_single((scene_id, args.renderer))
    else:
        # A single CUDA owner avoids forked CUDA contexts and VRAM oversubscription.
        for scene_id in range(1, 6):
            run_single((scene_id, args.renderer))

    output = OUT_DIR if args.renderer == "dark_map" else OPENCV_OUT_DIR
    write_motion_manifest()
    print(f"\nAll 5 {args.renderer} scenes rendered to: {output}")


if __name__ == "__main__":
    main()
