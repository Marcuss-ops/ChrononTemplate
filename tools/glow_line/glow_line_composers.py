"""Glow Line Composers for ChrononTemplate / Chronon3D.

Implements the three architectural tiers for documentary motion graphics:
  01 GlowLine_Basic: Baseline single-stroke line with standard glow filter.
  02 GlowLine_Cinematic: Multi-layer glow (ultra-sharp white core, tight saturated halo,
     wide atmospheric aura, physical bloom).
  03 GlowLine_DocusPremium: The full documentary flagship (multi-layer glow,
     arc-length bezier spline, leading light head flare, waypoint reactions with
     ripple shockwaves, energy micro-pulses, and organic head acceleration).
"""
import copy
import json
import math
import os
from typing import Dict, List, Tuple, Any

W, H, FPS, DURATION_FRAMES = 1920, 1080, 30, 150  # 5.0 seconds
REVEAL_START, REVEAL_END = 15, 105                # 3.0 seconds draw, 1.5 seconds settle/life

# ---------------------------------------------------------------------------
# Color utilities
# ---------------------------------------------------------------------------
def hex_to_rgba(hex_str: str, alpha: float = 1.0) -> List[float]:
    h = hex_str.lstrip("#")
    if len(h) == 6:
        r = int(h[0:2], 16) / 255.0
        g = int(h[2:4], 16) / 255.0
        b = int(h[4:6], 16) / 255.0
        return [r, g, b, float(alpha)]
    elif len(h) == 8:
        r = int(h[0:2], 16) / 255.0
        g = int(h[2:4], 16) / 255.0
        b = int(h[4:6], 16) / 255.0
        a = int(h[6:8], 16) / 255.0
        return [r, g, b, a * float(alpha)]
    return [1.0, 1.0, 1.0, float(alpha)]

# ---------------------------------------------------------------------------
# Smooth Bézier Spline & Arc-Length Parameterization
# ---------------------------------------------------------------------------
def eval_cubic_bezier(p0: List[float], cp1: List[float], cp2: List[float], p1: List[float], t: float) -> List[float]:
    t2 = t * t
    t3 = t2 * t
    mt = 1.0 - t
    mt2 = mt * mt
    mt3 = mt2 * mt
    x = mt3 * p0[0] + 3.0 * mt2 * t * cp1[0] + 3.0 * mt * t2 * cp2[0] + t3 * p1[0]
    y = mt3 * p0[1] + 3.0 * mt2 * t * cp1[1] + 3.0 * mt * t2 * cp2[1] + t3 * p1[1]
    return [x, y]

# Four key documentary waypoints across the canvas
WAYPOINTS = [
    {"id": "wp_01", "name": "WP-01", "label": "ALPHA // LAT 45.42", "pos": [300.0, 740.0]},
    {"id": "wp_02", "name": "WP-02", "label": "NODE-B // DELTA +1.8", "pos": [720.0, 360.0]},
    {"id": "wp_03", "name": "WP-03", "label": "VECTOR // SECTOR 07", "pos": [1220.0, 700.0]},
    {"id": "wp_04", "name": "WP-04", "label": "TERMINAL // TARGET", "pos": [1640.0, 340.0]},
]

# Cubic Bezier segments connecting the 4 waypoints smoothly
BEZIER_SEGMENTS = [
    (WAYPOINTS[0]["pos"], [440.0, 740.0], [580.0, 360.0], WAYPOINTS[1]["pos"]),
    (WAYPOINTS[1]["pos"], [860.0, 360.0], [1080.0, 700.0], WAYPOINTS[2]["pos"]),
    (WAYPOINTS[2]["pos"], [1360.0, 700.0], [1500.0, 340.0], WAYPOINTS[3]["pos"]),
]

def generate_dense_spline_points(samples_per_segment: int = 120) -> List[List[float]]:
    dense_pts = []
    for p0, cp1, cp2, p1 in BEZIER_SEGMENTS:
        for i in range(samples_per_segment):
            t = i / float(samples_per_segment)
            dense_pts.append(eval_cubic_bezier(p0, cp1, cp2, p1, t))
    dense_pts.append(BEZIER_SEGMENTS[-1][3])
    return dense_pts

def sample_arc_length_polyline(dense_pts: List[List[float]], num_uniform_samples: int = 240) -> Tuple[List[List[float]], float, List[float]]:
    """Uniformly resample curve by arc-length. Returns (resampled_pts, total_length, waypoint_progress_list)."""
    # 1. Compute cumulative lengths
    cum_lens = [0.0]
    total = 0.0
    for a, b in zip(dense_pts, dense_pts[1:]):
        seg_len = math.hypot(b[0] - a[0], b[1] - a[1])
        total += seg_len
        cum_lens.append(total)

    # 2. Resample at uniform arc-length intervals
    uniform_pts = []
    for i in range(num_uniform_samples):
        target = (i / float(num_uniform_samples - 1)) * total
        # Binary search / linear scan
        idx = 0
        while idx < len(cum_lens) - 1 and cum_lens[idx + 1] < target:
            idx += 1
        if idx >= len(cum_lens) - 1:
            uniform_pts.append(list(dense_pts[-1]))
        else:
            seg_len = cum_lens[idx + 1] - cum_lens[idx]
            frac = 0.0 if seg_len == 0 else (target - cum_lens[idx]) / seg_len
            x = dense_pts[idx][0] + frac * (dense_pts[idx + 1][0] - dense_pts[idx][0])
            y = dense_pts[idx][1] + frac * (dense_pts[idx + 1][1] - dense_pts[idx][1])
            uniform_pts.append([round(x, 2), round(y, 2)])

    # 3. Find closest arc-length progress for each waypoint
    wp_progress = []
    for wp in WAYPOINTS:
        wx, wy = wp["pos"]
        best_d = 1e9
        best_prog = 0.0
        for i, (ux, uy) in enumerate(uniform_pts):
            d = math.hypot(ux - wx, uy - wy)
            if d < best_d:
                best_d = d
                best_prog = i / float(num_uniform_samples - 1)
        wp_progress.append(best_prog)

    return uniform_pts, total, wp_progress

# Precompute the canonical polyline (48 samples for silky smooth bezier on 1080p)
_DENSE_PTS = generate_dense_spline_points(60)
UNIFORM_PTS, TOTAL_PATH_LENGTH, WAYPOINT_PROGRESS = sample_arc_length_polyline(_DENSE_PTS, 48)

# Convert to Chronon render-plan path commands
# In Chronon3D shape layer: position = [0, 0] centered, so points are relative to canvas center [960, 540]
HX, HY = W / 2.0, H / 2.0
RELATIVE_PATH_COMMANDS = [
    {"type": "move_to", "point": [round(UNIFORM_PTS[0][0] - HX, 2), round(UNIFORM_PTS[0][1] - HY, 2)]}
]
for pt in UNIFORM_PTS[1:]:
    RELATIVE_PATH_COMMANDS.append({
        "type": "line_to", "point": [round(pt[0] - HX, 2), round(pt[1] - HY, 2)]
    })

# Follow-path uses absolute canvas coordinates
ABSOLUTE_PATH_COMMANDS = [
    {"type": "move_to", "point": [round(UNIFORM_PTS[0][0], 2), round(UNIFORM_PTS[0][1], 2)]}
]
for pt in UNIFORM_PTS[1:]:
    ABSOLUTE_PATH_COMMANDS.append({
        "type": "line_to", "point": [round(pt[0], 2), round(pt[1], 2)]
    })

# ---------------------------------------------------------------------------
# Background and documentary grid
# ---------------------------------------------------------------------------
def make_documentary_background_layers() -> List[Dict[str, Any]]:
    layers = []
    # Base dark slate background with smooth optical vignette
    layers.append({
        "id": "bg_base",
        "type": "color",
        "color": hex_to_rgba("#07090E", 1.0),
        "position": [0, 0],
        "size": [W, H],
        "start_frame": 0,
        "duration_frames": DURATION_FRAMES,
        "effects": [
            {"type": "vignette", "radius": 0.85, "softness": 0.55, "amount": 0.45}
        ]
    })


    # Subtle horizontal & vertical data grid lines
    grid_path = []
    for x in range(160, W, 160):
        grid_path.extend([
            {"type": "move_to", "point": [float(x - HX), float(0 - HY)]},
            {"type": "line_to", "point": [float(x - HX), float(H - HY)]}
        ])
    for y in range(120, H, 120):
        grid_path.extend([
            {"type": "move_to", "point": [float(0 - HX), float(y - HY)]},
            {"type": "line_to", "point": [float(W - HX), float(y - HY)]}
        ])

    layers.append({
        "id": "bg_grid",
        "type": "shape",
        "position": [0, 0],
        "size": [W, H],
        "start_frame": 0,
        "duration_frames": DURATION_FRAMES,
        "opacity": 0.045,
        "shape": {
            "type": "path",
            "path": grid_path,
            "stroke": {"color": "#80A0C0", "width": 1.0}
        }
    })

    # Header title
    layers.append({
        "id": "doc_header_badge",
        "type": "shape",
        "position": [float(180 - HX), float(90 - HY)],
        "size": [180, 26],
        "start_frame": 0,
        "duration_frames": DURATION_FRAMES,
        "opacity": 0.8,
        "shape": {
            "type": "rect",
            "fill": hex_to_rgba("#101622", 0.8),
            "stroke": {"color": "#00A2FF", "width": 1.0}
        }
    })
    layers.append({
        "id": "doc_header_text",
        "type": "text",
        "text": "DOCUS // GLOW LINE COMPARISON",
        "position": [180.0, 95.0],
        "start_frame": 0,
        "duration_frames": DURATION_FRAMES,
        "opacity": 0.85,
        "style": {
            "font": "Chronon3d/assets/fonts/Inter-Regular.ttf",
            "font_size": 13.0,
            "fill": "#A8D4FF"
        }
    })
    return layers

def make_waypoint_layers(interactive: bool = False, trigger_frames: List[int] = None) -> List[Dict[str, Any]]:
    """Static or animated waypoint indicators."""
    layers = []
    for i, wp in enumerate(WAYPOINTS):
        wx, wy = wp["pos"]
        rx, ry = float(wx - HX), float(wy - HY)
        tf = trigger_frames[i] if trigger_frames and i < len(trigger_frames) else REVEAL_START

        # Base marker circle
        marker_color = "#00D2FF" if interactive else "#4A627A"
        base_opacity = 0.35 if interactive else 0.70

        tracks = []
        if interactive:
            # Opacity ramp up when reached
            tracks.append({
                "property": "opacity",
                "easing": "out_cubic",
                "keyframes": [
                    {"frame": 0, "value": 0.25},
                    {"frame": max(0, tf - 2), "value": 0.25},
                    {"frame": tf + 6, "value": 1.0},
                    {"frame": DURATION_FRAMES - 1, "value": 0.9}
                ]
            })

        layers.append({
            "id": f"wp_marker_{wp['id']}",
            "type": "shape",
            "position": [rx, ry],
            "size": [16, 16],
            "start_frame": 0,
            "duration_frames": DURATION_FRAMES,
            "opacity": base_opacity if not interactive else 1.0,
            "shape": {
                "type": "ellipse",
                "fill": hex_to_rgba("#0A121E", 0.9),
                "stroke": {"color": "#00D2FF" if interactive else "#4A627A", "width": 1.8}
            },
            "effects": [
                {"type": "glow", "radius": 14.0 if interactive else 6.0, "intensity": 0.6 if interactive else 0.2, "color": hex_to_rgba("#00D2FF")}
            ] if interactive else [],
            **({"animation": {"tracks": tracks}} if tracks else {})
        })

        # Center dot
        layers.append({
            "id": f"wp_center_{wp['id']}",
            "type": "shape",
            "position": [rx, ry],
            "size": [5, 5],
            "start_frame": 0,
            "duration_frames": DURATION_FRAMES,
            "opacity": 0.9,
            "shape": {
                "type": "ellipse",
                "fill": hex_to_rgba("#FFFFFF", 1.0)
            }
        })

        # Waypoint label
        layers.append({
            "id": f"wp_label_{wp['id']}",
            "type": "text",
            "text": f"{wp['name']}: {wp['label']}",
            "position": [wx + 16.0, wy + 16.0],
            "start_frame": 0,
            "duration_frames": DURATION_FRAMES,
            "opacity": 0.65 if not interactive else 0.85,
            "style": {
                "font": "Chronon3d/assets/fonts/Inter-Regular.ttf",
                "font_size": 11.5,
                "fill": "#A0C4E8" if interactive else "#6A8298"
            }
        })

        # Shockwave ripple when triggered (Premium only)
        if interactive:
            ripple_tracks = [
                {
                    "property": "scale",
                    "easing": "out_cubic",
                    "keyframes": [
                        {"frame": tf, "value": 0.2},
                        {"frame": tf + 22, "value": 3.8}
                    ]
                },
                {
                    "property": "opacity",
                    "easing": "out_cubic",
                    "keyframes": [
                        {"frame": tf, "value": 1.0},
                        {"frame": tf + 22, "value": 0.0}
                    ]
                }
            ]
            layers.append({
                "id": f"wp_ripple_{wp['id']}",
                "type": "shape",
                "position": [rx, ry],
                "size": [24, 24],
                "start_frame": tf,
                "duration_frames": 24,
                "shape": {
                    "type": "ellipse",
                    "stroke": {"color": "#80F0FF", "width": 1.5}
                },
                "effects": [
                    {"type": "glow", "radius": 16.0, "intensity": 0.8, "color": hex_to_rgba("#00D2FF")}
                ],
                "animation": {"tracks": ripple_tracks}
            })

    return layers

# ---------------------------------------------------------------------------
# Tier 01: GlowLine_Basic (The Baseline Neon Tube)
# ---------------------------------------------------------------------------
def build_glow_line_basic_plan() -> Dict[str, Any]:
    """Tier 1: Single thick uniform colored line with a basic glow filter.
    Demonstrates the classic failure mode: artificial, thick, neon-pipe appearance.
    """
    layers = make_documentary_background_layers()
    layers.extend(make_waypoint_layers(interactive=False))

    # Version overlay indicator
    layers.append({
        "id": "tier_badge",
        "type": "text",
        "text": "01 // GlowLine_Basic (Single Layer / Neon Pipe)",
        "position": [960.0, 1020.0],
        "start_frame": 0,
        "duration_frames": DURATION_FRAMES,
        "opacity": 0.9,
        "style": {
            "font": "Chronon3d/assets/fonts/Inter-Regular.ttf",
            "font_size": 15.0,
            "fill": "#FF8888"
        }
    })

    # The single glowing line
    layers.append({
        "id": "basic_glow_line",
        "type": "shape",
        "position": [0, 0],
        "size": [W, H],
        "start_frame": 0,
        "duration_frames": DURATION_FRAMES,
        "shape": {
            "type": "path",
            "path": RELATIVE_PATH_COMMANDS,
            "stroke": {
                "color": "#00E5FF",
                "width": 6.0,
                "cap": "round",
                "join": "round"
            },
            "operators": [
                {
                    "kind": "trim",
                    "params": {
                        "start": 0.0, "end": 1.0, "offset": 0.0,
                        "animation": {
                            "easing": "linear",
                            "keyframes": [
                                {"frame": REVEAL_START, "value": [0.0, 0.0, 0.0]},
                                {"frame": REVEAL_END, "value": [0.0, 1.0, 0.0]}
                            ]
                        }
                    }
                }
            ]
        },
        "effects": [
            {"type": "glow", "radius": 22.0, "intensity": 0.85, "color": hex_to_rgba("#00E5FF")}
        ]
    })

    return {
        "schema": "chronon.render-plan.v3",
        "version": 3,
        "job_id": "glow_line_01_basic",
        "canvas": {"width": W, "height": H, "fps_num": FPS, "fps_den": 1, "duration_frames": DURATION_FRAMES},
        "layers": layers,
        "output": {"path": "GlowLine_Basic.mp4", "format": "mp4"}
    }

# ---------------------------------------------------------------------------
# Tier 02: GlowLine_Cinematic (Multi-Layer Glow + Physical Bloom)
# ---------------------------------------------------------------------------
def build_glow_line_cinematic_plan() -> Dict[str, Any]:
    """Tier 2: Multi-layer glow architecture.
    Composes:
      1. Wide diffuse aura (Alone Largo, radius 42, intensity 0.28, deep blue)
      2. Tight saturated halo (Alone Stretto, radius 12, intensity 0.65, vibrant cyan)
      3. Ultra-crisp razor core (Core Bianco, width 2.0px, pure white)
      4. Linear physical bloom post-pass
    """
    layers = make_documentary_background_layers()
    layers.extend(make_waypoint_layers(interactive=False))

    # Version overlay indicator
    layers.append({
        "id": "tier_badge",
        "type": "text",
        "text": "02 // GlowLine_Cinematic (Multi-Layer Glow: Core 2.0px + Tight & Wide Halos + Bloom)",
        "position": [960.0, 1020.0],
        "start_frame": 0,
        "duration_frames": DURATION_FRAMES,
        "opacity": 0.9,
        "style": {
            "font": "Chronon3d/assets/fonts/Inter-Regular.ttf",
            "font_size": 15.0,
            "fill": "#A0E0FF"
        }
    })

    trim_animation = {
        "easing": "in_out_cubic",
        "keyframes": [
            {"frame": REVEAL_START, "value": [0.0, 0.0, 0.0]},
            {"frame": REVEAL_END, "value": [0.0, 1.0, 0.0]}
        ]
    }

    # 1. LAYER 1: Wide Diffuse Aura (Alone Largo)
    layers.append({
        "id": "cinematic_wide_aura",
        "type": "shape",
        "position": [0, 0],
        "size": [W, H],
        "start_frame": 0,
        "duration_frames": DURATION_FRAMES,
        "opacity": 0.55,
        "shape": {
            "type": "path",
            "path": RELATIVE_PATH_COMMANDS,
            "stroke": {
                "color": "#0055FF",
                "width": 14.0,
                "cap": "round",
                "join": "round"
            },
            "operators": [{"kind": "trim", "params": {"start": 0.0, "end": 1.0, "offset": 0.0, "animation": trim_animation}}]
        },
        "effects": [
            {"type": "glow", "radius": 46.0, "intensity": 0.35, "color": hex_to_rgba("#0066FF")}
        ]
    })

    # 2. LAYER 2: Tight Saturated Halo (Alone Stretto)
    layers.append({
        "id": "cinematic_tight_halo",
        "type": "shape",
        "position": [0, 0],
        "size": [W, H],
        "start_frame": 0,
        "duration_frames": DURATION_FRAMES,
        "opacity": 0.85,
        "shape": {
            "type": "path",
            "path": RELATIVE_PATH_COMMANDS,
            "stroke": {
                "color": "#00D2FF",
                "width": 5.0,
                "cap": "round",
                "join": "round"
            },
            "operators": [{"kind": "trim", "params": {"start": 0.0, "end": 1.0, "offset": 0.0, "animation": trim_animation}}]
        },
        "effects": [
            {"type": "glow", "radius": 12.0, "intensity": 0.70, "color": hex_to_rgba("#00E5FF")}
        ]
    })

    # 3. LAYER 3: Razor-Sharp Core (Core Bianco)
    layers.append({
        "id": "cinematic_sharp_core",
        "type": "shape",
        "position": [0, 0],
        "size": [W, H],
        "start_frame": 0,
        "duration_frames": DURATION_FRAMES,
        "opacity": 1.0,
        "shape": {
            "type": "path",
            "path": RELATIVE_PATH_COMMANDS,
            "stroke": {
                "color": "#FFFFFF",
                "width": 2.0,
                "cap": "round",
                "join": "round",
                "taper_start": 0.3,
                "taper_end": 0.3
            },
            "operators": [{"kind": "trim", "params": {"start": 0.0, "end": 1.0, "offset": 0.0, "animation": trim_animation}}]
        },
        "effects": [
            {"type": "bloom", "threshold": 0.72, "radius": 16.0, "intensity": 0.38}
        ]
    })

    return {
        "schema": "chronon.render-plan.v3",
        "version": 3,
        "job_id": "glow_line_02_cinematic",
        "canvas": {"width": W, "height": H, "fps_num": FPS, "fps_den": 1, "duration_frames": DURATION_FRAMES},
        "layers": layers,
        "output": {"path": "GlowLine_Cinematic.mp4", "format": "mp4"}
    }

def build_docus_premium_documentary_layers(
    layer_id: str,
    points: List[Tuple[float, float]],
    start_frame: int,
    end_frame: int,
    frames: int,
    color: str = "#A87542",
) -> List[Dict[str, Any]]:
    """Build a restrained editorial connector using the canonical path stroke.

    Documentary scenes need a precise, warm connector—not the neon comparison
    treatment used by the legacy tier gallery. This keeps the same path/stroke
    and trim primitives while limiting the treatment to a fine core and subtle
    5 px underlay. No glow filter, moving flare, grid, or decorative pulse.
    """
    if len(points) < 2 or not (0 <= start_frame < end_frame < frames):
        raise ValueError("documentary connector needs a path and valid reveal interval")
    def make_layer(suffix: str, width: float, opacity: float) -> Dict[str, Any]:
        commands = [{"type": "move_to" if i == 0 else "line_to",
                     "point": [round(x - HX, 3), round(y - HY, 3)]}
                    for i, (x, y) in enumerate(points)]
        return {
            "id": layer_id + suffix,
            "type": "shape",
            "position": [0, 0],
            "size": [W, H],
            "start_frame": 0,
            "duration_frames": frames,
            "opacity": opacity,
            "shape": {"type": "path", "path": commands,
                      "stroke": {"color": color, "width": width,
                                 "cap": "round", "join": "round"},
                      "operators": [{"kind": "trim", "params": {
                          "start": 0.0, "end": 0.0,
                          "animation": {"easing": "in_out_sine", "keyframes": [
                              {"frame": start_frame, "value": [0.0, 0.0]},
                              {"frame": end_frame, "value": [0.0, 1.0]}]}}}]}
        }
    return [make_layer("_soft", 5.0, 0.14), make_layer("_core", 1.8, 0.92)]


# ---------------------------------------------------------------------------
# Tier 03: GlowLine_DocusPremium (The Documentary Flagship)
# ---------------------------------------------------------------------------
# The premium editorial treatment above is intentionally distinct from this
# neon comparison-gallery recipe retained for backwards-compatible demos.
# ---------------------------------------------------------------------------
# Tier 03: GlowLine_DocusPremium (The Documentary Flagship)
# ---------------------------------------------------------------------------

# legacy comparison gallery implementation follows.
def ease_in_out_cubic(p: float) -> float:
    p = max(0.0, min(1.0, float(p)))
    return 4.0 * p * p * p if p < 0.5 else 1.0 - math.pow(-2.0 * p + 2.0, 3.0) / 2.0

def _build_glow_line_docus_premium_legacy_plan() -> Dict[str, Any]:
    """Tier 3: The complete Docus / Reacts flagship experience.
    Features:
      - Multi-layer glow (ultra-crisp white core 2.0px + saturated halo + wide aura)
      - High-intensity leading light head flare guiding the revelation
      - Waypoint triggers with ripple shockwaves & flash activations
      - Subtle energy pulses traveling along the line
      - Deterministic pulse & organic head acceleration
    """
    # Calculate exact frame trigger for each waypoint based on arc-length progress
    total_reveal_frames = REVEAL_END - REVEAL_START
    waypoint_trigger_frames = []
    # Invert ease_in_out_cubic to find exact frame when progress reaches wp_p
    for prog in WAYPOINT_PROGRESS:
        # Binary search for frame
        low, high = 0.0, 1.0
        for _ in range(16):
            mid = (low + high) * 0.5
            if ease_in_out_cubic(mid) < prog:
                low = mid
            else:
                high = mid
        f = REVEAL_START + int(round(low * total_reveal_frames))
        waypoint_trigger_frames.append(f)

    layers = make_documentary_background_layers()
    layers.extend(make_waypoint_layers(interactive=True, trigger_frames=waypoint_trigger_frames))

    # Version overlay indicator
    layers.append({
        "id": "tier_badge",
        "type": "text",
        "text": "03 // GlowLine_DocusPremium (Multi-Layer + Light Head + Node Ripple Flash + Energy Pulses)",
        "position": [960.0, 1020.0],
        "start_frame": 0,
        "duration_frames": DURATION_FRAMES,
        "opacity": 0.95,
        "style": {
            "font": "Chronon3d/assets/fonts/Inter-Regular.ttf",
            "font_size": 15.0,
            "fill": "#55FFD2"
        }
    })

    trim_animation = {
        "easing": "in_out_cubic",
        "keyframes": [
            {"frame": REVEAL_START, "value": [0.0, 0.0, 0.0]},
            {"frame": REVEAL_END, "value": [0.0, 1.0, 0.0]}
        ]
    }

    # 1. Wide Atmospheric Aura
    layers.append({
        "id": "premium_wide_aura",
        "type": "shape",
        "position": [0, 0],
        "size": [W, H],
        "start_frame": 0,
        "duration_frames": DURATION_FRAMES,
        "opacity": 0.60,
        "shape": {
            "type": "path",
            "path": RELATIVE_PATH_COMMANDS,
            "stroke": {
                "color": "#0066FF",
                "width": 16.0,
                "cap": "round",
                "join": "round"
            },
            "operators": [{"kind": "trim", "params": {"start": 0.0, "end": 1.0, "offset": 0.0, "animation": trim_animation}}]
        },
        "effects": [
            {"type": "glow", "radius": 48.0, "intensity": 0.38, "color": hex_to_rgba("#0077FF")}
        ]
    })

    # 2. Tight Luminous Halo
    layers.append({
        "id": "premium_tight_halo",
        "type": "shape",
        "position": [0, 0],
        "size": [W, H],
        "start_frame": 0,
        "duration_frames": DURATION_FRAMES,
        "opacity": 0.88,
        "shape": {
            "type": "path",
            "path": RELATIVE_PATH_COMMANDS,
            "stroke": {
                "color": "#00E0FF",
                "width": 5.2,
                "cap": "round",
                "join": "round"
            },
            "operators": [{"kind": "trim", "params": {"start": 0.0, "end": 1.0, "offset": 0.0, "animation": trim_animation}}]
        },
        "effects": [
            {"type": "glow", "radius": 14.0, "intensity": 0.75, "color": hex_to_rgba("#00F0FF")}
        ]
    })

    # 3. Razor-Sharp White Core
    layers.append({
        "id": "premium_sharp_core",
        "type": "shape",
        "position": [0, 0],
        "size": [W, H],
        "start_frame": 0,
        "duration_frames": DURATION_FRAMES,
        "opacity": 1.0,
        "shape": {
            "type": "path",
            "path": RELATIVE_PATH_COMMANDS,
            "stroke": {
                "color": "#FFFFFF",
                "width": 2.0,
                "cap": "round",
                "join": "round",
                "taper_start": 0.4,
                "taper_end": 0.2
            },
            "operators": [{"kind": "trim", "params": {"start": 0.0, "end": 1.0, "offset": 0.0, "animation": trim_animation}}]
        },
        "effects": [
            {"type": "bloom", "threshold": 0.70, "radius": 18.0, "intensity": 0.45}
        ]
    })

    # 4. Energy Micro-Pulses (Subtle luminous secondary wave traveling along the line)
    layers.append({
        "id": "premium_energy_pulse",
        "type": "shape",
        "position": [0, 0],
        "size": [W, H],
        "start_frame": 108,
        "duration_frames": 38,
        "opacity": 0.8,
        "shape": {
            "type": "path",
            "path": RELATIVE_PATH_COMMANDS,
            "stroke": {
                "color": "#FFFFFF",
                "width": 2.8,
                "cap": "round",
                "join": "round"
            },
            "operators": [
                {
                    "kind": "trim",
                    "params": {
                        "start": 0.0, "end": 1.0, "offset": 0.0,
                        "animation": {
                            "easing": "out_cubic",
                            "keyframes": [
                                {"frame": 108, "value": [0.0, 0.12, 0.0]},
                                {"frame": 142, "value": [0.88, 1.0, 0.0]}
                            ]
                        }
                    }
                }
            ]
        },
        "effects": [
            {"type": "glow", "radius": 18.0, "intensity": 0.9, "color": hex_to_rgba("#00E5FF")}
        ],
        "animation": {
            "tracks": [
                {
                    "property": "opacity",
                    "easing": "in_out_sine",
                    "keyframes": [
                        {"frame": 108, "value": 0.0},
                        {"frame": 118, "value": 0.85},
                        {"frame": 138, "value": 0.85},
                        {"frame": 145, "value": 0.0}
                    ]
                }
            ]
        }
    })

    # 5. Leading Light Head (Hot Flare traveling precisely at line tip during reveal)
    head_opacity_tracks = [
        {
            "property": "opacity",
            "easing": "out_cubic",
            "keyframes": [
                {"frame": 0, "value": 0.0},
                {"frame": REVEAL_START, "value": 1.0},
                {"frame": REVEAL_END, "value": 1.0},
                {"frame": REVEAL_END + 15, "value": 0.4},
                {"frame": DURATION_FRAMES - 1, "value": 0.3}
            ]
        }
    ]

    # Outer Head Flare
    layers.append({
        "id": "premium_head_outer_flare",
        "type": "shape",
        "position": [0, 0],
        "size": [24, 24],
        "start_frame": 0,
        "duration_frames": DURATION_FRAMES,
        "shape": {
            "type": "ellipse",
            "fill": hex_to_rgba("#00E5FF", 0.75)
        },
        "follow_path": {
            "path_commands": ABSOLUTE_PATH_COMMANDS,
            "progress": {
                "easing": "in_out_cubic",
                "keyframes": [
                    {"frame": REVEAL_START, "value": 0.0},
                    {"frame": REVEAL_END, "value": 1.0}
                ]
            },
            "auto_orient": False,
            "clamp_end": True
        },
        "effects": [
            {"type": "glow", "radius": 24.0, "intensity": 0.95, "color": hex_to_rgba("#00D2FF")}
        ],
        "animation": {"tracks": head_opacity_tracks}
    })

    # Diamond White Core Head Dot
    layers.append({
        "id": "premium_head_core_dot",
        "type": "shape",
        "position": [0, 0],
        "size": [8, 8],
        "start_frame": 0,
        "duration_frames": DURATION_FRAMES,
        "shape": {
            "type": "ellipse",
            "fill": hex_to_rgba("#FFFFFF", 1.0)
        },
        "follow_path": {
            "path_commands": ABSOLUTE_PATH_COMMANDS,
            "progress": {
                "easing": "in_out_cubic",
                "keyframes": [
                    {"frame": REVEAL_START, "value": 0.0},
                    {"frame": REVEAL_END, "value": 1.0}
                ]
            },
            "auto_orient": False,
            "clamp_end": True
        },
        "effects": [
            {"type": "bloom", "threshold": 0.60, "radius": 14.0, "intensity": 0.7}
        ],
        "animation": {"tracks": head_opacity_tracks}
    })

    return {
        "schema": "chronon.render-plan.v3",
        "version": 3,
        "job_id": "glow_line_03_docus_premium",
        "canvas": {"width": W, "height": H, "fps_num": FPS, "fps_den": 1, "duration_frames": DURATION_FRAMES},
        "layers": layers,
        "output": {"path": "GlowLine_DocusPremium.mp4", "format": "mp4"}
    }


def build_glow_line_docus_premium_plan() -> Dict[str, Any]:
    """Documentary-quality evidence connector, authored as a finished scene.

    The original neon comparison reel remains available internally as
    ``_build_glow_line_docus_premium_legacy_plan``. This public preset keeps
    the canonical multi-layer path stroke but places it in an editorial scene
    and removes the grid, electric blue, blooms, flares, ripples, and pulses.
    """
    frames = 240
    layers: List[Dict[str, Any]] = [
        {"id": "archive_photo", "type": "image",
         "asset": "Chronon3d/assets/editorial/industrial_port_dawn.png",
         "size": [1120, 760], "position": [100, 150], "fit": "cover",
         "start_frame": 0, "duration_frames": frames,
         "animation": {"tracks": [{"property": "scale", "easing": "in_out_sine",
             "keyframes": [{"frame": 0, "value": 1.0}, {"frame": 239, "value": 1.025}]}]}},
        {"id": "page_tint", "type": "color", "color": [0.055, 0.057, 0.056, 1.0],
         "size": [1920, 1080], "position": [0, 0], "screen_space": True,
         "start_frame": 0, "duration_frames": frames},
        {"id": "chapter", "type": "text", "text": "ARCHIVE / INDUSTRIAL PORT",
         "position": [1360, 180], "size": [850, 42], "screen_space": True,
         "start_frame": 0, "duration_frames": frames,
         "style": {"font": "Chronon3d/assets/fonts/Inter-Bold.ttf", "font_size": 26,
                   "fill": "#C9A777"}},
        {"id": "headline", "type": "text", "text": "A quiet change\nin the shipping record",
         "position": [1360, 310], "size": [850, 210], "screen_space": True,
         "start_frame": 0, "duration_frames": frames,
         "style": {"font": "Chronon3d/assets/fonts/Inter-Bold.ttf", "font_size": 66,
                   "fill": "#F1EEE6"}},
        {"id": "caption", "type": "text",
         "text": "The image is the source. The line connects it to the record being examined.",
         "position": [1360, 525], "size": [760, 118], "screen_space": True,
         "start_frame": 0, "duration_frames": frames,
         "style": {"font": "Chronon3d/assets/fonts/Inter-Regular.ttf", "font_size": 34,
                   "fill": "#D0CEC7"}},
        {"id": "source_label", "type": "text", "text": "SOURCE FRAME  /  01",
         "position": [130, 875], "size": [560, 44], "screen_space": True,
         "start_frame": 0, "duration_frames": frames,
         "style": {"font": "Chronon3d/assets/fonts/Inter-Regular.ttf", "font_size": 24,
                   "fill": "#D0CEC7"}},
        {"id": "record_label", "type": "text", "text": "SHIPPING RECORD  /  02",
         "position": [1260, 770], "size": [570, 44], "screen_space": True,
         "start_frame": 0, "duration_frames": frames,
         "style": {"font": "Chronon3d/assets/fonts/Inter-Regular.ttf", "font_size": 24,
                   "fill": "#D0CEC7"}},
    ]
    layers.extend(build_docus_premium_documentary_layers(
        "evidence_link", [(650.0, 760.0), (840.0, 760.0), (1040.0, 690.0),
                          (1200.0, 690.0)], 72, 142, frames, "#C9A777"))
    plan = {"schema": "chronon.render-plan.v3", "version": 3,
            "job_id": "GlowLine_DocusPremium",
            "canvas": {"width": W, "height": H, "fps_num": FPS,
                       "fps_den": 1, "duration_frames": frames},
            "layers": layers,
            "output": {"path": "GlowLine_DocusPremium.mp4",
                       "format": "mp4", "codec": "h264"}}
    return plan


def build_glow_line_docus_premium_legacy_plan() -> Dict[str, Any]:
    """Compatibility entrypoint for the archived neon comparison reel."""
    return _build_glow_line_docus_premium_legacy_plan()
