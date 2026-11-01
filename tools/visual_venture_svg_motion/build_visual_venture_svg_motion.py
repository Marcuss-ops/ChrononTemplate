"""
Chronon Visual Venture SVG Vector Motion Suite
Generates valid chronon.render-plan.v3 compositions and SVG vector animations
directly replicating the Visual Venture dark-aesthetic vector motion graphics.
"""
import os, sys, json, math, subprocess, shutil

ROOT_DIR = r"C:\Users\pater\Pyt"
CHRONON_CLI = r"C:\Users\pater\Pyt\chronons\Chronon3d\build\chronon\win-release-clang\apps\chronon3d_cli\chronon3d_cli.exe"
BASE_DIR = r"C:\Users\pater\Pyt\chronons\ChrononTemplate\tools\visual_venture_svg_motion"
PLANS_DIR = os.path.join(BASE_DIR, "plans")
ASSETS_DIR = os.path.join(BASE_DIR, "assets")
RENDERS_DIR = os.path.join(BASE_DIR, "renders")
USER_ASSETS_DIR = r"C:\Users\pater\Pyt\assets\chronon_visual_venture_pack"

os.makedirs(PLANS_DIR, exist_ok=True)
os.makedirs(ASSETS_DIR, exist_ok=True)
os.makedirs(RENDERS_DIR, exist_ok=True)
os.makedirs(USER_ASSETS_DIR, exist_ok=True)

def kf_track(prop, raw_kfs, easing="in_out_sine"):
    seen = {}
    for kf in raw_kfs:
        seen[int(kf["frame"])] = kf["value"]
    kfs = [{"frame": f, "value": seen[f]} for f in sorted(seen.keys())]
    return {
        "property": prop,
        "easing": easing,
        "keyframes": kfs
    }

def make_bg(duration=90):
    return {
        "id": "bg_space",
        "type": "color",
        "color": [0.015, 0.015, 0.02, 1.0],
        "position": [0, 0],
        "size": [1920, 1080],
        "start_frame": 0,
        "duration_frames": duration,
        "effects": [
            {
                "type": "vignette",
                "radius": 0.85,
                "softness": 0.6,
                "amount": 0.5
            }
        ]
    }

# ==============================================================================
# 01: Reticle Target Scanner & Threat Lock-on (Visual Venture frames 0087-0093)
# ==============================================================================
def build_plan_01_target_scanner(duration=90):
    layers = [make_bg(duration)]

    # 1. Spotlight cone from top emitter down to center
    layers.append({
        "id": "spotlight_beam",
        "type": "shape",
        "position": [0, -100],
        "size": [1920, 1080],
        "start_frame": 0,
        "duration_frames": duration,
        "opacity": 0.18,
        "shape": {
            "type": "path",
            "path": [
                {"type": "move_to", "point": [0.0, -380.0]},
                {"type": "line_to", "point": [280.0, 350.0]},
                {"type": "line_to", "point": [-280.0, 350.0]},
                {"type": "close"}
            ],
            "fill": [0.95, 0.95, 1.0, 0.25],
            "stroke": {"color": "#FFFFFF", "width": 1.0}
        },
        "animation": {
            "tracks": [
                kf_track("opacity", [
                    {"frame": 0, "value": [0.10]},
                    {"frame": 35, "value": [0.22]},
                    {"frame": 60, "value": [0.15]},
                    {"frame": 90, "value": [0.22]}
                ], "in_out_sine")
            ]
        }
    })

    # 2. Top light emitter bulb
    layers.append({
        "id": "emitter_node",
        "type": "shape",
        "position": [0, -480],
        "size": [32, 32],
        "start_frame": 0,
        "duration_frames": duration,
        "shape": {
            "type": "ellipse",
            "fill": [1.0, 1.0, 1.0, 1.0],
            "stroke": {"color": "#FFFFFF", "width": 2.0}
        },
        "effects": [
            {"type": "glow", "radius": 24.0, "intensity": 0.9, "color": [1.0, 1.0, 1.0, 1.0]}
        ]
    })

    # 3. Four target spheres: 1 white origin, 3 yellow targets
    sphere_configs = [
        ("sphere_white", -105, 0, 32, [1.0, 1.0, 1.0, 1.0], "#FFFFFF"),
        ("sphere_yellow_1", -15, -15, 24, [1.0, 0.85, 0.1, 1.0], "#FFD700"),
        ("sphere_yellow_2", 55, -25, 18, [1.0, 0.85, 0.1, 1.0], "#FFD700"),
        ("sphere_yellow_3", 115, -30, 12, [1.0, 0.85, 0.1, 1.0], "#FFD700")
    ]
    for sid, sx, sy, srad, sfill, sstroke in sphere_configs:
        layers.append({
            "id": sid,
            "type": "shape",
            "position": [sx, sy],
            "size": [srad * 2, srad * 2],
            "start_frame": 0,
            "duration_frames": duration,
            "shape": {
                "type": "ellipse",
                "fill": sfill,
                "stroke": {"color": sstroke, "width": 1.5}
            },
            "effects": [
                {"type": "glow", "radius": 14.0, "intensity": 0.6, "color": sfill}
            ]
        })

    # 4. Corner target reticle brackets [ ] converging and locking
    layers.append({
        "id": "reticle_left_bracket",
        "type": "shape",
        "position": [-160, 0],
        "size": [80, 120],
        "start_frame": 15,
        "duration_frames": duration - 15,
        "shape": {
            "type": "path",
            "path": [
                {"type": "move_to", "point": [25.0, -50.0]},
                {"type": "line_to", "point": [-25.0, -50.0]},
                {"type": "line_to", "point": [-25.0, 50.0]},
                {"type": "line_to", "point": [25.0, 50.0]}
            ],
            "stroke": {"color": "#FFFFFF", "width": 3.5, "cap": "round", "join": "round"}
        },
        "effects": [
            {"type": "glow", "radius": 16.0, "intensity": 0.8, "color": [1.0, 1.0, 1.0, 1.0]}
        ],
        "animation": {
            "tracks": [
                kf_track("position", [
                    {"frame": 15, "value": [-260.0, 0.0]},
                    {"frame": 40, "value": [-160.0, 0.0]}
                ], "out_cubic"),
                kf_track("opacity", [
                    {"frame": 15, "value": [0.0]},
                    {"frame": 25, "value": [1.0]}
                ], "out_cubic")
            ]
        }
    })

    layers.append({
        "id": "reticle_right_bracket",
        "type": "shape",
        "position": [160, 0],
        "size": [80, 120],
        "start_frame": 15,
        "duration_frames": duration - 15,
        "shape": {
            "type": "path",
            "path": [
                {"type": "move_to", "point": [-25.0, -50.0]},
                {"type": "line_to", "point": [25.0, -50.0]},
                {"type": "line_to", "point": [25.0, 50.0]},
                {"type": "line_to", "point": [-25.0, 50.0]}
            ],
            "stroke": {"color": "#FFFFFF", "width": 3.5, "cap": "round", "join": "round"}
        },
        "effects": [
            {"type": "glow", "radius": 16.0, "intensity": 0.8, "color": [1.0, 1.0, 1.0, 1.0]}
        ],
        "animation": {
            "tracks": [
                kf_track("position", [
                    {"frame": 15, "value": [260.0, 0.0]},
                    {"frame": 40, "value": [160.0, 0.0]}
                ], "out_cubic"),
                kf_track("opacity", [
                    {"frame": 15, "value": [0.0]},
                    {"frame": 25, "value": [1.0]}
                ], "out_cubic")
            ]
        }
    })

    # 5. Red lock-on crosshair & cone alert at frame 42
    layers.append({
        "id": "red_lock_crosshair",
        "type": "shape",
        "position": [115, -30],
        "size": [44, 44],
        "start_frame": 42,
        "duration_frames": duration - 42,
        "shape": {
            "type": "ellipse",
            "stroke": {"color": "#FF2020", "width": 3.0}
        },
        "effects": [
            {"type": "glow", "radius": 22.0, "intensity": 0.95, "color": [1.0, 0.12, 0.12, 1.0]}
        ],
        "animation": {
            "tracks": [
                kf_track("scale", [
                    {"frame": 42, "value": [2.5, 2.5]},
                    {"frame": 52, "value": [1.0, 1.0]}
                ], "out_cubic"),
                kf_track("opacity", [
                    {"frame": 42, "value": [0.0]},
                    {"frame": 48, "value": [1.0]},
                    {"frame": 68, "value": [0.4]},
                    {"frame": 76, "value": [1.0]},
                    {"frame": 85, "value": [0.5]},
                    {"frame": 90, "value": [1.0]}
                ], "out_cubic")
            ]
        }
    })

    # Red warning cone beam targeting the node
    layers.append({
        "id": "red_warning_cone",
        "type": "shape",
        "position": [-300, -30],
        "size": [800, 200],
        "start_frame": 48,
        "duration_frames": duration - 48,
        "opacity": 0.45,
        "shape": {
            "type": "path",
            "path": [
                {"type": "move_to", "point": [-400.0, -120.0]},
                {"type": "line_to", "point": [415.0, 0.0]},
                {"type": "line_to", "point": [-400.0, 120.0]},
                {"type": "close"}
            ],
            "fill": [0.95, 0.05, 0.05, 0.35],
            "stroke": {"color": "#FF2525", "width": 1.5}
        },
        "effects": [
            {"type": "glow", "radius": 25.0, "intensity": 0.75, "color": [1.0, 0.1, 0.1, 1.0]}
        ],
        "animation": {
            "tracks": [
                kf_track("opacity", [
                    {"frame": 48, "value": [0.0]},
                    {"frame": 55, "value": [0.65]},
                    {"frame": 70, "value": [0.35]},
                    {"frame": 82, "value": [0.70]},
                    {"frame": 90, "value": [0.45]}
                ], "in_out_sine")
            ]
        }
    })

    return {
        "schema": "chronon.render-plan.v3",
        "version": 3,
        "job_id": "vv_reticle_target_scanner",
        "canvas": {"width": 1920, "height": 1080, "fps_num": 30, "fps_den": 1, "duration_frames": duration},
        "output": {"path": os.path.join(RENDERS_DIR, "vv_reticle_target_scanner.mp4").replace("\\", "/"), "format": "mp4"},
        "layers": layers
    }

# ==============================================================================
# 02: Morse Code & Telemetry Data Matrix (Visual Venture frames 0117-0127)
# ==============================================================================
def build_plan_02_morse_crypto_matrix(duration=90):
    layers = [make_bg(duration)]

    row_y = [-160, 0, 160]

    for i, ry in enumerate(row_y):
        layers.append({
            "id": f"row_track_{i}",
            "type": "shape",
            "position": [0, ry],
            "size": [1920, 2],
            "start_frame": 0,
            "duration_frames": duration,
            "opacity": 0.08,
            "shape": {
                "type": "path",
                "path": [
                    {"type": "move_to", "point": [-600.0, 0.0]},
                    {"type": "line_to", "point": [600.0, 0.0]}
                ],
                "stroke": {"color": "#88B0D0", "width": 1.0}
            }
        })

    for i, ry in enumerate(row_y):
        f_mid = 20 * (i + 1)
        f_end = min(88, 40 * (i + 1))
        layers.append({
            "id": f"left_terminal_{i}",
            "type": "shape",
            "position": [-320, ry],
            "size": [40, 40],
            "start_frame": 0,
            "duration_frames": duration,
            "shape": {
                "type": "ellipse",
                "fill": [1.0, 1.0, 1.0, 1.0],
                "stroke": {"color": "#FFFFFF", "width": 2.0}
            },
            "effects": [
                {"type": "glow", "radius": 20.0, "intensity": 0.85, "color": [1.0, 1.0, 1.0, 1.0]}
            ],
            "animation": {
                "tracks": [
                    kf_track("opacity", [
                        {"frame": 0, "value": [0.7]},
                        {"frame": f_mid, "value": [1.0]},
                        {"frame": f_end, "value": [0.7]},
                        {"frame": 90, "value": [0.9]}
                    ], "in_out_sine")
                ]
            }
        })

    for i, ry in enumerate(row_y):
        layers.append({
            "id": f"right_alert_{i}",
            "type": "shape",
            "position": [320, ry],
            "size": [36, 36],
            "start_frame": 0,
            "duration_frames": duration,
            "shape": {
                "type": "ellipse",
                "fill": [1.0, 0.12, 0.12, 1.0],
                "stroke": {"color": "#FF2828", "width": 2.0}
            },
            "effects": [
                {"type": "glow", "radius": 22.0, "intensity": 0.9, "color": [1.0, 0.12, 0.12, 1.0]}
            ],
            "animation": {
                "tracks": [
                    kf_track("scale", [
                        {"frame": 0, "value": [1.0, 1.0]},
                        {"frame": 20 + i * 10, "value": [1.25, 1.25]},
                        {"frame": 45 + i * 10, "value": [1.0, 1.0]},
                        {"frame": 90, "value": [1.1, 1.1]}
                    ], "in_out_sine")
                ]
            }
        })

    for i, ry in enumerate(row_y):
        layers.append({
            "id": f"data_white_seg_{i}",
            "type": "shape",
            "position": [-80 + i * 30, ry - 18],
            "size": [75, 10],
            "start_frame": 0,
            "duration_frames": duration,
            "shape": {
                "type": "rounded_rect",
                "corner_radius": [5.0, 5.0, 5.0, 5.0],
                "fill": [1.0, 1.0, 1.0, 1.0]
            },
            "effects": [
                {"type": "glow", "radius": 14.0, "intensity": 0.75, "color": [1.0, 1.0, 1.0, 1.0]}
            ],
            "animation": {
                "tracks": [
                    kf_track("position", [
                        {"frame": 0, "value": [-120.0 + i * 40, ry - 18.0]},
                        {"frame": 28, "value": [110.0 - i * 30, ry - 18.0]},
                        {"frame": 58, "value": [-70.0 + i * 20, ry - 18.0]},
                        {"frame": 90, "value": [80.0, ry - 18.0]}
                    ], "in_out_cubic")
                ]
            }
        })

        layers.append({
            "id": f"data_white_seg2_{i}",
            "type": "shape",
            "position": [100 - i * 30, ry - 18],
            "size": [75, 10],
            "start_frame": 0,
            "duration_frames": duration,
            "shape": {
                "type": "rounded_rect",
                "corner_radius": [5.0, 5.0, 5.0, 5.0],
                "fill": [1.0, 1.0, 1.0, 1.0]
            },
            "effects": [
                {"type": "glow", "radius": 14.0, "intensity": 0.75, "color": [1.0, 1.0, 1.0, 1.0]}
            ],
            "animation": {
                "tracks": [
                    kf_track("position", [
                        {"frame": 0, "value": [80.0 - i * 20, ry - 18.0]},
                        {"frame": 35, "value": [-110.0 + i * 30, ry - 18.0]},
                        {"frame": 65, "value": [120.0 - i * 25, ry - 18.0]},
                        {"frame": 90, "value": [-60.0, ry - 18.0]}
                    ], "in_out_cubic")
                ]
            }
        })

        layers.append({
            "id": f"data_red_seg_{i}",
            "type": "shape",
            "position": [-50 + i * 25, ry + 18],
            "size": [80, 10],
            "start_frame": 0,
            "duration_frames": duration,
            "shape": {
                "type": "rounded_rect",
                "corner_radius": [5.0, 5.0, 5.0, 5.0],
                "fill": [1.0, 0.12, 0.12, 1.0]
            },
            "effects": [
                {"type": "glow", "radius": 16.0, "intensity": 0.85, "color": [1.0, 0.15, 0.15, 1.0]}
            ],
            "animation": {
                "tracks": [
                    kf_track("position", [
                        {"frame": 0, "value": [90.0 - i * 40, ry + 18.0]},
                        {"frame": 30, "value": [-130.0 + i * 30, ry + 18.0]},
                        {"frame": 60, "value": [100.0 - i * 20, ry + 18.0]},
                        {"frame": 90, "value": [-90.0, ry + 18.0]}
                    ], "in_out_cubic")
                ]
            }
        })

    return {
        "schema": "chronon.render-plan.v3",
        "version": 3,
        "job_id": "vv_morse_crypto_matrix",
        "canvas": {"width": 1920, "height": 1080, "fps_num": 30, "fps_den": 1, "duration_frames": duration},
        "output": {"path": os.path.join(RENDERS_DIR, "vv_morse_crypto_matrix.mp4").replace("\\", "/"), "format": "mp4"},
        "layers": layers
    }

# ==============================================================================
# 03: Hierarchical Architecture / Flowchart Pipeline (Visual Venture frames 0150-0155)
# ==============================================================================
def build_plan_03_hierarchy_flowchart(duration=90):
    layers = [make_bg(duration)]

    layers.append({
        "id": "container_box",
        "type": "shape",
        "position": [0, 0],
        "size": [600, 720],
        "start_frame": 0,
        "duration_frames": duration,
        "opacity": 0.35,
        "shape": {
            "type": "rounded_rect",
            "corner_radius": [24.0, 24.0, 24.0, 24.0],
            "stroke": {"color": "#6E8294", "width": 2.0}
        }
    })

    layers.append({
        "id": "connector_trunk",
        "type": "shape",
        "position": [0, 0],
        "size": [8, 500],
        "start_frame": 0,
        "duration_frames": duration,
        "shape": {
            "type": "path",
            "path": [
                {"type": "move_to", "point": [0.0, -220.0]},
                {"type": "line_to", "point": [0.0, 220.0]}
            ],
            "stroke": {"color": "#FFFFFF", "width": 3.0}
        },
        "effects": [
            {"type": "glow", "radius": 12.0, "intensity": 0.7, "color": [1.0, 1.0, 1.0, 1.0]}
        ]
    })

    node_y = [-200, 0, 200]
    for i, ny in enumerate(node_y):
        f_start = i * 24
        layers.append({
            "id": f"flow_card_{i+1}",
            "type": "shape",
            "position": [0, ny],
            "size": [460, 120],
            "start_frame": 0,
            "duration_frames": duration,
            "shape": {
                "type": "rounded_rect",
                "corner_radius": [18.0, 18.0, 18.0, 18.0],
                "fill": [0.03, 0.04, 0.06, 0.85],
                "stroke": {"color": "#FFFFFF" if i == 0 else "#667788", "width": 3.5 if i == 0 else 2.0}
            },
            "effects": [
                {"type": "glow", "radius": 22.0, "intensity": 0.85 if i == 0 else 0.4, "color": [1.0, 1.0, 1.0, 1.0]}
            ],
            "animation": {
                "tracks": [
                    kf_track("scale", [
                        {"frame": 0, "value": [0.95, 0.95]},
                        {"frame": max(1, f_start), "value": [0.95, 0.95]},
                        {"frame": f_start + 12, "value": [1.04, 1.04]},
                        {"frame": min(89, f_start + 24), "value": [1.0, 1.0]}
                    ], "out_cubic")
                ]
            }
        })

        layers.append({
            "id": f"card_dot_{i+1}",
            "type": "shape",
            "position": [-180, ny],
            "size": [22, 22],
            "start_frame": 0,
            "duration_frames": duration,
            "shape": {
                "type": "ellipse",
                "fill": [1.0, 1.0, 1.0, 1.0] if i == 0 else ([1.0, 0.8, 0.2, 1.0] if i == 1 else [1.0, 0.15, 0.15, 1.0]),
                "stroke": {"color": "#FFFFFF", "width": 1.5}
            },
            "effects": [
                {"type": "glow", "radius": 16.0, "intensity": 0.85, "color": [1.0, 1.0, 1.0, 1.0]}
            ]
        })

    layers.append({
        "id": "traveling_data_pulse",
        "type": "shape",
        "position": [0, -200],
        "size": [28, 28],
        "start_frame": 10,
        "duration_frames": duration - 10,
        "shape": {
            "type": "ellipse",
            "fill": [1.0, 1.0, 1.0, 1.0],
            "stroke": {"color": "#00E5FF", "width": 2.5}
        },
        "effects": [
            {"type": "glow", "radius": 24.0, "intensity": 0.95, "color": [0.2, 0.9, 1.0, 1.0]}
        ],
        "animation": {
            "tracks": [
                kf_track("position", [
                    {"frame": 10, "value": [0.0, -200.0]},
                    {"frame": 35, "value": [0.0, 0.0]},
                    {"frame": 60, "value": [0.0, 200.0]},
                    {"frame": 85, "value": [0.0, 200.0]}
                ], "in_out_cubic"),
                kf_track("scale", [
                    {"frame": 10, "value": [1.0, 1.0]},
                    {"frame": 35, "value": [1.4, 1.4]},
                    {"frame": 60, "value": [1.2, 1.2]},
                    {"frame": 85, "value": [1.5, 1.5]}
                ], "in_out_sine")
            ]
        }
    })

    return {
        "schema": "chronon.render-plan.v3",
        "version": 3,
        "job_id": "vv_hierarchy_flowchart",
        "canvas": {"width": 1920, "height": 1080, "fps_num": 30, "fps_den": 1, "duration_frames": duration},
        "output": {"path": os.path.join(RENDERS_DIR, "vv_hierarchy_flowchart.mp4").replace("\\", "/"), "format": "mp4"},
        "layers": layers
    }

# ==============================================================================
# 04: Surveillance Reconnaissance Scanner Spotlight (Visual Venture frames 0211-0213)
# ==============================================================================
def build_plan_04_surveillance_scanner(duration=90):
    layers = [make_bg(duration)]

    layers.append({
        "id": "scanner_viewport_card",
        "type": "shape",
        "position": [0, -30],
        "size": [420, 500],
        "start_frame": 0,
        "duration_frames": duration,
        "shape": {
            "type": "rounded_rect",
            "corner_radius": [28.0, 28.0, 28.0, 28.0],
            "fill": [0.02, 0.02, 0.03, 0.8],
            "stroke": {"color": "#FFFFFF", "width": 3.0}
        },
        "effects": [
            {"type": "glow", "radius": 22.0, "intensity": 0.8, "color": [1.0, 1.0, 1.0, 1.0]}
        ]
    })

    layers.append({
        "id": "tracked_agent_white",
        "type": "shape",
        "position": [-40, 40],
        "size": [56, 56],
        "start_frame": 0,
        "duration_frames": duration,
        "shape": {
            "type": "ellipse",
            "fill": [1.0, 1.0, 1.0, 1.0],
            "stroke": {"color": "#FFFFFF", "width": 2.0}
        },
        "effects": [
            {"type": "glow", "radius": 20.0, "intensity": 0.85, "color": [1.0, 1.0, 1.0, 1.0]}
        ]
    })
    layers.append({
        "id": "tracked_agent_aux",
        "type": "shape",
        "position": [50, 60],
        "size": [36, 36],
        "start_frame": 0,
        "duration_frames": duration,
        "shape": {
            "type": "ellipse",
            "fill": [0.55, 0.60, 0.68, 1.0],
            "stroke": {"color": "#8899AA", "width": 1.5}
        },
        "effects": [
            {"type": "glow", "radius": 14.0, "intensity": 0.6, "color": [0.6, 0.7, 0.8, 1.0]}
        ]
    })

    layers.append({
        "id": "overhead_sensor_bar",
        "type": "shape",
        "position": [0, -180],
        "size": [140, 18],
        "start_frame": 0,
        "duration_frames": duration,
        "shape": {
            "type": "rounded_rect",
            "corner_radius": [9.0, 9.0, 9.0, 9.0],
            "fill": [1.0, 1.0, 1.0, 1.0]
        },
        "effects": [
            {"type": "glow", "radius": 22.0, "intensity": 0.9, "color": [1.0, 1.0, 1.0, 1.0]}
        ],
        "animation": {
            "tracks": [
                kf_track("position", [
                    {"frame": 0, "value": [-60.0, -180.0]},
                    {"frame": 45, "value": [60.0, -180.0]},
                    {"frame": 90, "value": [-60.0, -180.0]}
                ], "in_out_sine")
            ]
        }
    })

    layers.append({
        "id": "sensor_spotlight_cone",
        "type": "shape",
        "position": [0, -50],
        "size": [380, 280],
        "start_frame": 0,
        "duration_frames": duration,
        "opacity": 0.22,
        "shape": {
            "type": "path",
            "path": [
                {"type": "move_to", "point": [-70.0, -130.0]},
                {"type": "line_to", "point": [70.0, -130.0]},
                {"type": "line_to", "point": [140.0, 140.0]},
                {"type": "line_to", "point": [-140.0, 140.0]},
                {"type": "close"}
            ],
            "fill": [1.0, 1.0, 1.0, 0.35],
            "stroke": {"color": "#FFFFFF", "width": 1.0}
        },
        "animation": {
            "tracks": [
                kf_track("position", [
                    {"frame": 0, "value": [-40.0, -50.0]},
                    {"frame": 45, "value": [40.0, -50.0]},
                    {"frame": 90, "value": [-40.0, -50.0]}
                ], "in_out_sine")
            ]
        }
    })

    dot_spacing = 42
    dot_start_x = - (8 * dot_spacing) / 2
    for d in range(9):
        dx = dot_start_x + d * dot_spacing
        layers.append({
            "id": f"telemetry_dot_{d}",
            "type": "shape",
            "position": [dx, 310],
            "size": [18, 18],
            "start_frame": 0,
            "duration_frames": duration,
            "shape": {
                "type": "ellipse",
                "fill": [1.0, 1.0, 1.0, 1.0],
                "stroke": {"color": "#FFFFFF", "width": 1.0}
            },
            "effects": [
                {"type": "glow", "radius": 14.0, "intensity": 0.75, "color": [1.0, 1.0, 1.0, 1.0]}
            ],
            "animation": {
                "tracks": [
                    kf_track("opacity", [
                        {"frame": 0, "value": [0.3]},
                        {"frame": max(1, (d * 9)), "value": [1.0]},
                        {"frame": min(89, (d * 9) + 12), "value": [0.3]},
                        {"frame": 90, "value": [0.6]}
                    ], "in_out_sine")
                ]
            }
        })

    return {
        "schema": "chronon.render-plan.v3",
        "version": 3,
        "job_id": "vv_surveillance_scanner",
        "canvas": {"width": 1920, "height": 1080, "fps_num": 30, "fps_den": 1, "duration_frames": duration},
        "output": {"path": os.path.join(RENDERS_DIR, "vv_surveillance_scanner.mp4").replace("\\", "/"), "format": "mp4"},
        "layers": layers
    }

# ==============================================================================
# 05: Orbital Radar Constellation & Reactor Core (Visual Venture frames 0233-0244)
# ==============================================================================
def build_plan_05_orbital_radar_core(duration=90):
    layers = [make_bg(duration)]

    for r in [120, 220, 320]:
        layers.append({
            "id": f"radar_ring_{r}",
            "type": "shape",
            "position": [0, 0],
            "size": [r * 2, r * 2],
            "start_frame": 0,
            "duration_frames": duration,
            "opacity": 0.22,
            "shape": {
                "type": "ellipse",
                "stroke": {"color": "#80A0C0", "width": 1.5}
            }
        })

    layers.append({
        "id": "reactor_core_glow",
        "type": "shape",
        "position": [0, 0],
        "size": [140, 140],
        "start_frame": 0,
        "duration_frames": duration,
        "shape": {
            "type": "ellipse",
            "fill": [1.0, 0.08, 0.08, 1.0],
            "stroke": {"color": "#FF4040", "width": 3.0}
        },
        "effects": [
            {"type": "glow", "radius": 36.0, "intensity": 1.0, "color": [1.0, 0.08, 0.08, 1.0]}
        ],
        "animation": {
            "tracks": [
                kf_track("scale", [
                    {"frame": 0, "value": [1.0, 1.0]},
                    {"frame": 45, "value": [1.18, 1.18]},
                    {"frame": 90, "value": [1.0, 1.0]}
                ], "in_out_sine")
            ]
        }
    })

    layers.append({
        "id": "core_nucleus_hot",
        "type": "shape",
        "position": [0, 0],
        "size": [50, 50],
        "start_frame": 0,
        "duration_frames": duration,
        "shape": {
            "type": "ellipse",
            "fill": [1.0, 0.95, 0.95, 1.0]
        },
        "effects": [
            {"type": "glow", "radius": 18.0, "intensity": 0.9, "color": [1.0, 1.0, 1.0, 1.0]}
        ]
    })

    num_constellation_dots = 12
    ring_radius = 220.0
    for i in range(num_constellation_dots):
        angle_deg = (i * 360.0 / num_constellation_dots)
        angle_rad = math.radians(angle_deg)
        x0 = ring_radius * math.cos(angle_rad)
        y0 = ring_radius * math.sin(angle_rad)

        angle_rad_end = math.radians(angle_deg + 60.0)
        x1 = ring_radius * math.cos(angle_rad_end)
        y1 = ring_radius * math.sin(angle_rad_end)

        layers.append({
            "id": f"constellation_dot_{i}",
            "type": "shape",
            "position": [x0, y0],
            "size": [18, 18],
            "start_frame": 0,
            "duration_frames": duration,
            "shape": {
                "type": "ellipse",
                "fill": [1.0, 1.0, 1.0, 1.0],
                "stroke": {"color": "#FFFFFF", "width": 1.2}
            },
            "effects": [
                {"type": "glow", "radius": 14.0, "intensity": 0.8, "color": [1.0, 1.0, 1.0, 1.0]}
            ],
            "animation": {
                "tracks": [
                    kf_track("position", [
                        {"frame": 0, "value": [x0, y0]},
                        {"frame": 90, "value": [x1, y1]}
                    ], "linear"),
                    kf_track("scale", [
                        {"frame": 0, "value": [0.8, 0.8]},
                        {"frame": max(1, (i * 7)), "value": [1.35, 1.35]},
                        {"frame": min(89, (i * 7) + 15), "value": [0.8, 0.8]},
                        {"frame": 90, "value": [1.0, 1.0]}
                    ], "in_out_sine")
                ]
            }
        })

    layers.append({
        "id": "inner_satellite_node",
        "type": "shape",
        "position": [120, 0],
        "size": [24, 24],
        "start_frame": 0,
        "duration_frames": duration,
        "shape": {
            "type": "ellipse",
            "fill": [0.75, 0.82, 0.90, 1.0],
            "stroke": {"color": "#FFFFFF", "width": 1.5}
        },
        "effects": [
            {"type": "glow", "radius": 16.0, "intensity": 0.75, "color": [0.7, 0.85, 1.0, 1.0]}
        ],
        "animation": {
            "tracks": [
                kf_track("position", [
                    {"frame": 0, "value": [120.0, 0.0]},
                    {"frame": 22, "value": [0.0, 120.0]},
                    {"frame": 45, "value": [-120.0, 0.0]},
                    {"frame": 68, "value": [0.0, -120.0]},
                    {"frame": 90, "value": [120.0, 0.0]}
                ], "linear")
            ]
        }
    })

    return {
        "schema": "chronon.render-plan.v3",
        "version": 3,
        "job_id": "vv_orbital_radar_core",
        "canvas": {"width": 1920, "height": 1080, "fps_num": 30, "fps_den": 1, "duration_frames": duration},
        "output": {"path": os.path.join(RENDERS_DIR, "vv_orbital_radar_core.mp4").replace("\\", "/"), "format": "mp4"},
        "layers": layers
    }

# ==============================================================================
# Animated SVG Generation (Pure standard SVG with CSS animations for asset pack)
# ==============================================================================
def generate_svg_assets():
    svg_01 = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1920 1080" width="100%" height="100%" style="background:#040407;">
  <defs>
    <filter id="glow-white" x="-50%" y="-50%" width="200%" height="200%">
      <feGaussianBlur stdDeviation="6" result="blur" />
      <feMerge><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge>
    </filter>
    <filter id="glow-red" x="-50%" y="-50%" width="200%" height="200%">
      <feGaussianBlur stdDeviation="8" result="blur" />
      <feMerge><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge>
    </filter>
    <linearGradient id="beamGrad" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="#ffffff" stop-opacity="0.4"/>
      <stop offset="100%" stop-color="#ffffff" stop-opacity="0.02"/>
    </linearGradient>
    <linearGradient id="redConeGrad" x1="0" y1="0.5" x2="1" y2="0.5">
      <stop offset="0%" stop-color="#ff2020" stop-opacity="0.0"/>
      <stop offset="100%" stop-color="#ff2020" stop-opacity="0.5"/>
    </linearGradient>
    <style>
      @keyframes reticleLeft {
        0%, 15% { transform: translateX(-80px); opacity: 0; }
        35%, 100% { transform: translateX(0px); opacity: 1; }
      }
      @keyframes reticleRight {
        0%, 15% { transform: translateX(80px); opacity: 0; }
        35%, 100% { transform: translateX(0px); opacity: 1; }
      }
      @keyframes redLock {
        0%, 40% { transform: scale(2.2); opacity: 0; }
        50% { transform: scale(1.0); opacity: 1; }
        65% { opacity: 0.3; }
        75% { opacity: 1; }
        85% { opacity: 0.4; }
        100% { opacity: 1; transform: scale(1.0); }
      }
      @keyframes coneAlert {
        0%, 45% { opacity: 0; }
        55% { opacity: 0.7; }
        70% { opacity: 0.3; }
        80% { opacity: 0.8; }
        100% { opacity: 0.5; }
      }
      .bracket-l { animation: reticleLeft 3s infinite alternate cubic-bezier(0.16, 1, 0.3, 1); transform-origin: 800px 540px; }
      .bracket-r { animation: reticleRight 3s infinite alternate cubic-bezier(0.16, 1, 0.3, 1); transform-origin: 1120px 540px; }
      .lock-target { animation: redLock 3s infinite cubic-bezier(0.16, 1, 0.3, 1); transform-origin: 1075px 510px; }
      .cone-alert { animation: coneAlert 3s infinite; }
    </style>
  </defs>

  <polygon points="960,60 1240,890 680,890" fill="url(#beamGrad)" stroke="#ffffff" stroke-width="1" stroke-opacity="0.2"/>
  <circle cx="960" cy="60" r="16" fill="#ffffff" filter="url(#glow-white)"/>
  <polygon class="cone-alert" points="660,390 1075,510 660,630" fill="url(#redConeGrad)" stroke="#ff2020" stroke-width="1.5" stroke-opacity="0.6"/>
  <circle cx="855" cy="540" r="32" fill="#ffffff" filter="url(#glow-white)"/>
  <circle cx="945" cy="525" r="24" fill="#FFD700" filter="url(#glow-white)"/>
  <circle cx="1015" cy="515" r="18" fill="#FFD700" filter="url(#glow-white)"/>
  <circle cx="1075" cy="510" r="12" fill="#FFD700" filter="url(#glow-white)"/>

  <g class="bracket-l">
    <path d="M 825,490 L 775,490 L 775,590 L 825,590" fill="none" stroke="#ffffff" stroke-width="3.5" stroke-linecap="round" stroke-linejoin="round" filter="url(#glow-white)"/>
  </g>
  <g class="bracket-r">
    <path d="M 1095,490 L 1145,490 L 1145,590 L 1095,590" fill="none" stroke="#ffffff" stroke-width="3.5" stroke-linecap="round" stroke-linejoin="round" filter="url(#glow-white)"/>
  </g>

  <circle class="lock-target" cx="1075" cy="510" r="22" fill="none" stroke="#ff2020" stroke-width="3" filter="url(#glow-red)"/>
</svg>"""
    with open(os.path.join(ASSETS_DIR, "01_reticle_target_scanner.svg"), "w", encoding="utf-8") as f:
        f.write(svg_01)
    with open(os.path.join(USER_ASSETS_DIR, "01_reticle_target_scanner.svg"), "w", encoding="utf-8") as f:
        f.write(svg_01)

    svg_02 = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1920 1080" width="100%" height="100%" style="background:#040407;">
  <defs>
    <filter id="glow-white" x="-50%" y="-50%" width="200%" height="200%">
      <feGaussianBlur stdDeviation="5" result="blur" />
      <feMerge><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge>
    </filter>
    <filter id="glow-red" x="-50%" y="-50%" width="200%" height="200%">
      <feGaussianBlur stdDeviation="7" result="blur" />
      <feMerge><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge>
    </filter>
    <style>
      @keyframes slideWhiteA {
        0%, 100% { transform: translateX(0px); }
        50% { transform: translateX(180px); }
      }
      @keyframes slideWhiteB {
        0%, 100% { transform: translateX(0px); }
        50% { transform: translateX(-160px); }
      }
      @keyframes slideRed {
        0%, 100% { transform: translateX(0px); }
        50% { transform: translateX(-190px); }
      }
      @keyframes pulseAlert {
        0%, 100% { transform: scale(1); opacity: 0.8; }
        50% { transform: scale(1.25); opacity: 1; }
      }
      .bar-white-1 { animation: slideWhiteA 2.4s infinite ease-in-out; }
      .bar-white-2 { animation: slideWhiteB 2.8s infinite ease-in-out; }
      .bar-red { animation: slideRed 2.6s infinite ease-in-out; }
      .alert-dot { animation: pulseAlert 1.8s infinite ease-in-out; transform-origin: center; }
    </style>
  </defs>

  <!-- Row 1 -->
  <line x1="360" y1="380" x2="1560" y2="380" stroke="#88B0D0" stroke-width="1" stroke-opacity="0.15"/>
  <circle cx="640" cy="380" r="20" fill="#ffffff" filter="url(#glow-white)"/>
  <circle class="alert-dot" cx="1280" cy="380" r="18" fill="#ff2424" filter="url(#glow-red)" style="transform-origin: 1280px 380px;"/>
  <rect class="bar-white-1" x="800" y="362" width="75" height="10" rx="5" fill="#ffffff" filter="url(#glow-white)"/>
  <rect class="bar-white-2" x="1000" y="362" width="75" height="10" rx="5" fill="#ffffff" filter="url(#glow-white)"/>
  <rect class="bar-red" x="870" y="388" width="80" height="10" rx="5" fill="#ff2424" filter="url(#glow-red)"/>

  <!-- Row 2 -->
  <line x1="360" y1="540" x2="1560" y2="540" stroke="#88B0D0" stroke-width="1" stroke-opacity="0.15"/>
  <circle cx="640" cy="540" r="20" fill="#ffffff" filter="url(#glow-white)"/>
  <circle class="alert-dot" cx="1280" cy="540" r="18" fill="#ff2424" filter="url(#glow-red)" style="transform-origin: 1280px 540px; animation-delay: 0.3s;"/>
  <rect class="bar-white-2" x="830" y="522" width="75" height="10" rx="5" fill="#ffffff" filter="url(#glow-white)"/>
  <rect class="bar-white-1" x="1030" y="522" width="75" height="10" rx="5" fill="#ffffff" filter="url(#glow-white)"/>
  <rect class="bar-red" x="840" y="548" width="80" height="10" rx="5" fill="#ff2424" filter="url(#glow-red)" style="animation-delay: 0.4s;"/>

  <!-- Row 3 -->
  <line x1="360" y1="700" x2="1560" y2="700" stroke="#88B0D0" stroke-width="1" stroke-opacity="0.15"/>
  <circle cx="640" cy="700" r="20" fill="#ffffff" filter="url(#glow-white)"/>
  <circle class="alert-dot" cx="1280" cy="700" r="18" fill="#ff2424" filter="url(#glow-red)" style="transform-origin: 1280px 700px; animation-delay: 0.6s;"/>
  <rect class="bar-white-1" x="860" y="682" width="75" height="10" rx="5" fill="#ffffff" filter="url(#glow-white)"/>
  <rect class="bar-white-2" x="970" y="682" width="75" height="10" rx="5" fill="#ffffff" filter="url(#glow-white)"/>
  <rect class="bar-red" x="920" y="708" width="80" height="10" rx="5" fill="#ff2424" filter="url(#glow-red)" style="animation-delay: 0.8s;"/>
</svg>"""
    with open(os.path.join(ASSETS_DIR, "02_morse_crypto_matrix.svg"), "w", encoding="utf-8") as f:
        f.write(svg_02)
    with open(os.path.join(USER_ASSETS_DIR, "02_morse_crypto_matrix.svg"), "w", encoding="utf-8") as f:
        f.write(svg_02)

    svg_03 = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1920 1080" width="100%" height="100%" style="background:#040407;">
  <defs>
    <filter id="glow-white" x="-50%" y="-50%" width="200%" height="200%">
      <feGaussianBlur stdDeviation="6" result="blur" />
      <feMerge><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge>
    </filter>
    <filter id="glow-cyan" x="-50%" y="-50%" width="200%" height="200%">
      <feGaussianBlur stdDeviation="8" result="blur" />
      <feMerge><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge>
    </filter>
    <style>
      @keyframes pulseData {
        0% { transform: translateY(0px); opacity: 0; }
        15% { opacity: 1; }
        50% { transform: translateY(200px); }
        85% { opacity: 1; }
        100% { transform: translateY(400px); opacity: 0; }
      }
      .data-packet { animation: pulseData 3.2s infinite ease-in-out; }
    </style>
  </defs>

  <rect x="660" y="180" width="600" height="720" rx="24" fill="none" stroke="#6E8294" stroke-width="2" stroke-dasharray="8 6" opacity="0.45"/>
  <line x1="960" y1="340" x2="960" y2="740" stroke="#ffffff" stroke-width="3" filter="url(#glow-white)"/>

  <rect x="730" y="280" width="460" height="120" rx="18" fill="#080b10" stroke="#ffffff" stroke-width="3.5" filter="url(#glow-white)"/>
  <circle cx="780" cy="340" r="11" fill="#ffffff" filter="url(#glow-white)"/>

  <rect x="730" y="480" width="460" height="120" rx="18" fill="#080b10" stroke="#778899" stroke-width="2"/>
  <circle cx="780" cy="540" r="11" fill="#FFD700" filter="url(#glow-white)"/>

  <rect x="730" y="680" width="460" height="120" rx="18" fill="#080b10" stroke="#778899" stroke-width="2"/>
  <circle cx="780" cy="740" r="11" fill="#FF2828" filter="url(#glow-white)"/>

  <circle class="data-packet" cx="960" cy="340" r="14" fill="#ffffff" stroke="#00E5FF" stroke-width="2.5" filter="url(#glow-cyan)"/>
</svg>"""
    with open(os.path.join(ASSETS_DIR, "03_hierarchy_flowchart.svg"), "w", encoding="utf-8") as f:
        f.write(svg_03)
    with open(os.path.join(USER_ASSETS_DIR, "03_hierarchy_flowchart.svg"), "w", encoding="utf-8") as f:
        f.write(svg_03)

    svg_04 = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1920 1080" width="100%" height="100%" style="background:#040407;">
  <defs>
    <filter id="glow-white" x="-50%" y="-50%" width="200%" height="200%">
      <feGaussianBlur stdDeviation="6" result="blur" />
      <feMerge><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge>
    </filter>
    <linearGradient id="scannerBeamGrad" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="#ffffff" stop-opacity="0.45"/>
      <stop offset="100%" stop-color="#ffffff" stop-opacity="0.03"/>
    </linearGradient>
    <style>
      @keyframes sweepSensor {
        0%, 100% { transform: translateX(-60px); }
        50% { transform: translateX(60px); }
      }
      @keyframes pulseDot {
        0%, 100% { opacity: 0.3; transform: scale(0.9); }
        50% { opacity: 1; transform: scale(1.2); }
      }
      .sweeper { animation: sweepSensor 3.6s infinite ease-in-out; }
      .p-dot { animation: pulseDot 2s infinite ease-in-out; transform-origin: center; }
    </style>
  </defs>

  <rect x="750" y="260" width="420" height="500" rx="28" fill="#05060a" stroke="#ffffff" stroke-width="3" filter="url(#glow-white)"/>
  <circle cx="920" cy="550" r="28" fill="#ffffff" filter="url(#glow-white)"/>
  <circle cx="1010" cy="570" r="18" fill="#8899AA" filter="url(#glow-white)"/>

  <g class="sweeper">
    <polygon points="890,340 1030,340 1100,610 820,610" fill="url(#scannerBeamGrad)" stroke="#ffffff" stroke-width="1" stroke-opacity="0.2"/>
    <rect x="890" y="331" width="140" height="18" rx="9" fill="#ffffff" filter="url(#glow-white)"/>
  </g>

  <g>
    <circle class="p-dot" cx="792" cy="850" r="9" fill="#ffffff" filter="url(#glow-white)" style="animation-delay: 0.0s; transform-origin: 792px 850px;"/>
    <circle class="p-dot" cx="834" cy="850" r="9" fill="#ffffff" filter="url(#glow-white)" style="animation-delay: 0.2s; transform-origin: 834px 850px;"/>
    <circle class="p-dot" cx="876" cy="850" r="9" fill="#ffffff" filter="url(#glow-white)" style="animation-delay: 0.4s; transform-origin: 876px 850px;"/>
    <circle class="p-dot" cx="918" cy="850" r="9" fill="#ffffff" filter="url(#glow-white)" style="animation-delay: 0.6s; transform-origin: 918px 850px;"/>
    <circle class="p-dot" cx="960" cy="850" r="9" fill="#ffffff" filter="url(#glow-white)" style="animation-delay: 0.8s; transform-origin: 960px 850px;"/>
    <circle class="p-dot" cx="1002" cy="850" r="9" fill="#ffffff" filter="url(#glow-white)" style="animation-delay: 1.0s; transform-origin: 1002px 850px;"/>
    <circle class="p-dot" cx="1044" cy="850" r="9" fill="#ffffff" filter="url(#glow-white)" style="animation-delay: 1.2s; transform-origin: 1044px 850px;"/>
    <circle class="p-dot" cx="1086" cy="850" r="9" fill="#ffffff" filter="url(#glow-white)" style="animation-delay: 1.4s; transform-origin: 1086px 850px;"/>
    <circle class="p-dot" cx="1128" cy="850" r="9" fill="#ffffff" filter="url(#glow-white)" style="animation-delay: 1.6s; transform-origin: 1128px 850px;"/>
  </g>
</svg>"""
    with open(os.path.join(ASSETS_DIR, "04_surveillance_scanner.svg"), "w", encoding="utf-8") as f:
        f.write(svg_04)
    with open(os.path.join(USER_ASSETS_DIR, "04_surveillance_scanner.svg"), "w", encoding="utf-8") as f:
        f.write(svg_04)

    svg_05 = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1920 1080" width="100%" height="100%" style="background:#040407;">
  <defs>
    <filter id="glow-red-core" x="-50%" y="-50%" width="200%" height="200%">
      <feGaussianBlur stdDeviation="12" result="blur" />
      <feMerge><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge>
    </filter>
    <filter id="glow-white" x="-50%" y="-50%" width="200%" height="200%">
      <feGaussianBlur stdDeviation="6" result="blur" />
      <feMerge><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge>
    </filter>
    <style>
      @keyframes rotateConstellation {
        0% { transform: rotate(0deg); }
        100% { transform: rotate(360deg); }
      }
      @keyframes orbitSatellite {
        0% { transform: rotate(0deg); }
        100% { transform: rotate(-360deg); }
      }
      @keyframes pulseReactor {
        0%, 100% { transform: scale(1); }
        50% { transform: scale(1.15); }
      }
      .constellation-ring { animation: rotateConstellation 24s linear infinite; transform-origin: 960px 540px; }
      .satellite-track { animation: orbitSatellite 8s linear infinite; transform-origin: 960px 540px; }
      .reactor-iris { animation: pulseReactor 2.5s infinite ease-in-out; transform-origin: 960px 540px; }
    </style>
  </defs>

  <circle cx="960" cy="540" r="120" fill="none" stroke="#80A0C0" stroke-width="1.5" stroke-opacity="0.25"/>
  <circle cx="960" cy="540" r="220" fill="none" stroke="#80A0C0" stroke-width="1.5" stroke-opacity="0.25"/>
  <circle cx="960" cy="540" r="320" fill="none" stroke="#80A0C0" stroke-width="1.5" stroke-opacity="0.25"/>

  <circle class="reactor-iris" cx="960" cy="540" r="70" fill="#FF1515" stroke="#FF4040" stroke-width="3" filter="url(#glow-red-core)"/>
  <circle cx="960" cy="540" r="25" fill="#ffffff" filter="url(#glow-white)"/>

  <g class="satellite-track">
    <circle cx="1080" cy="540" r="12" fill="#C0D0E0" stroke="#ffffff" stroke-width="1.5" filter="url(#glow-white)"/>
  </g>

  <g class="constellation-ring">
    <circle cx="1180" cy="540" r="9" fill="#ffffff" filter="url(#glow-white)"/>
    <circle cx="1150" cy="650" r="9" fill="#ffffff" filter="url(#glow-white)"/>
    <circle cx="1070" cy="730" r="9" fill="#ffffff" filter="url(#glow-white)"/>
    <circle cx="960" cy="760" r="9" fill="#ffffff" filter="url(#glow-white)"/>
    <circle cx="850" cy="730" r="9" fill="#ffffff" filter="url(#glow-white)"/>
    <circle cx="770" cy="650" r="9" fill="#ffffff" filter="url(#glow-white)"/>
    <circle cx="740" cy="540" r="9" fill="#ffffff" filter="url(#glow-white)"/>
    <circle cx="770" cy="430" r="9" fill="#ffffff" filter="url(#glow-white)"/>
    <circle cx="850" cy="350" r="9" fill="#ffffff" filter="url(#glow-white)"/>
    <circle cx="960" cy="320" r="9" fill="#ffffff" filter="url(#glow-white)"/>
    <circle cx="1070" cy="350" r="9" fill="#ffffff" filter="url(#glow-white)"/>
    <circle cx="1150" cy="430" r="9" fill="#ffffff" filter="url(#glow-white)"/>
  </g>
</svg>"""
    with open(os.path.join(ASSETS_DIR, "05_orbital_radar_core.svg"), "w", encoding="utf-8") as f:
        f.write(svg_05)
    with open(os.path.join(USER_ASSETS_DIR, "05_orbital_radar_core.svg"), "w", encoding="utf-8") as f:
        f.write(svg_05)

    print("SVG assets generated successfully!")

# ==============================================================================
# Main execution & validation
# ==============================================================================
def main():
    print("--- 1. Generating SVG assets ---")
    generate_svg_assets()

    print("\n--- 2. Building Chronon RenderPlans ---")
    plans = [
        ("01_reticle_target_scanner.plan.json", build_plan_01_target_scanner()),
        ("02_morse_crypto_matrix.plan.json", build_plan_02_morse_crypto_matrix()),
        ("03_hierarchy_flowchart.plan.json", build_plan_03_hierarchy_flowchart()),
        ("04_surveillance_scanner.plan.json", build_plan_04_surveillance_scanner()),
        ("05_orbital_radar_core.plan.json", build_plan_05_orbital_radar_core())
    ]

    plan_paths = []
    for filename, plan_dict in plans:
        p_path = os.path.join(PLANS_DIR, filename)
        with open(p_path, "w", encoding="utf-8") as f:
            json.dump(plan_dict, f, indent=2)
        with open(os.path.join(USER_ASSETS_DIR, filename), "w", encoding="utf-8") as f:
            json.dump(plan_dict, f, indent=2)
        print(f"Wrote plan: {filename} ({len(plan_dict['layers'])} layers)")
        plan_paths.append((filename, p_path))

    print("\n--- 3. Validating plans with chronon3d_cli.exe ---")
    for filename, p_path in plan_paths:
        cmd = [CHRONON_CLI, "validate", "--assets-root", ROOT_DIR, "--plan", p_path]
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode == 0 and '"status": "PASS"' in res.stdout:
            print(f"[PASS] {filename} successfully certified by Chronon3d validator!")
        else:
            print(f"[FAIL] {filename}:")
            print(res.stdout)
            print(res.stderr)
            sys.exit(1)

    print("\n--- 4. Rendering animations via Chronon Vulkan pipeline ---")
    for filename, p_path in plan_paths:
        job_name = filename.replace(".plan.json", "")
        frames_dir = os.path.join(RENDERS_DIR, f"temp_frames_{job_name}")
        os.makedirs(frames_dir, exist_ok=True)

        frame_pattern = os.path.join(frames_dir, "frame_####.png")
        print(f"\n[CHRONON RENDERING] {job_name} (90 frames @ 30fps Vulkan)...")

        render_cmd = [
            CHRONON_CLI, "render",
            "--assets-root", ROOT_DIR,
            "--plan", p_path,
            "-o", frame_pattern,
            "--frames", "0-89"
        ]
        r_res = subprocess.run(render_cmd, capture_output=True, text=True)
        if r_res.returncode != 0:
            print(f"Error rendering {job_name}:")
            print(r_res.stdout)
            print(r_res.stderr)
            sys.exit(1)

        mp4_out = os.path.join(RENDERS_DIR, f"{job_name}.mp4")
        user_mp4_out = os.path.join(USER_ASSETS_DIR, f"{job_name}.mp4")
        ffmpeg_cmd = [
            "ffmpeg", "-y",
            "-framerate", "30",
            "-i", os.path.join(frames_dir, "frame_%04d.png"),
            "-c:v", "libx264",
            "-pix_fmt", "yuv420p",
            "-crf", "16",
            "-preset", "fast",
            mp4_out
        ]
        f_res = subprocess.run(ffmpeg_cmd, capture_output=True, text=True)
        if f_res.returncode == 0:
            shutil.copyfile(mp4_out, user_mp4_out)
            print(f"[RENDERED MP4] {job_name}.mp4 ({os.path.getsize(mp4_out) / 1024:.1f} KB)")
        else:
            print(f"FFmpeg encode error for {job_name}:", f_res.stderr)

        shutil.rmtree(frames_dir, ignore_errors=True)

    # Clean patch script
    if os.path.exists(r"C:\Users\pater\Pyt\patch_script.py"):
        os.remove(r"C:\Users\pater\Pyt\patch_script.py")

    print("\n=======================================================")
    print("ALL 5 CHRONON VECTOR ANIMATIONS GENERATED & RENDERED!")
    print(f"Plans directory:   {PLANS_DIR}")
    print(f"Assets directory:  {ASSETS_DIR}")
    print(f"Renders directory: {RENDERS_DIR}")
    print(f"User pack:         {USER_ASSETS_DIR}")
    print("=======================================================")

if __name__ == "__main__":
    main()
