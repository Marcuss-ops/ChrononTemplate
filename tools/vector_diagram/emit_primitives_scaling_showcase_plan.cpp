// ChrononTemplate: Native C++ Emitter for primitives_scaling_parity_showcase
// Emits "chronon.render-plan.v3" plan demonstrating:
// 1. All primitives on 3 depth planes (Z = -400, Z = 0, Z = +150)
// 2. Non-scaling stroke test
// 3. Anchor / Pivot zero-drift invariance (CENTER, TOP_LEFT, BOTTOM_CENTER, CUSTOM)
// 4. Arc-Length LUT constant linear speed on trim & follow_path
// 5. 2.5D Camera pan & dolly out with DoF

#include <nlohmann/json.hpp>
#include <cmath>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <vector>

namespace fs = std::filesystem;
using json = nlohmann::json;

namespace chronon::showcase {

constexpr int kW = 1920;
constexpr int kH = 1080;
constexpr int kFps = 60;
constexpr int kTotalFrames = 360; // 6.0 seconds

inline json rgba(double r, double g, double b, double a = 1.0) {
    return json::array({r, g, b, a});
}

inline json generatePlan() {
    json layers = json::array();

    // 0. Dark background with vignette
    layers.push_back({
        {"id", "bg_dark"},
        {"type", "color"},
        {"color", rgba(0.015, 0.018, 0.025, 1.0)},
        {"size", {kW, kH}},
        {"position", {0, 0}},
        {"start_frame", 0},
        {"duration_frames", kTotalFrames},
        {"screen_space", true},
        {"effects", json::array({
            {{"type", "vignette"}, {"radius", 0.92}, {"softness", 0.5}, {"amount", 0.42}}
        })}
    });

    // 1. Grid of Primitives across 3 Depth Planes:
    // Plane 1: Far background (Z = -400)
    layers.push_back({
        {"id", "plane_far_rect_rounded"},
        {"type", "shape"},
        {"z_depth", -400.0},
        {"position", {450.0, 320.0}},
        {"size", {180.0, 120.0}},
        {"shape", {
            {"type", "rect"},
            {"rx", 18.0}, {"ry", 18.0},
            {"fill", rgba(0.15, 0.05, 0.25, 0.6)},
            {"stroke", {{"color", "#F030B0"}, {"width", 4.0}, {"non_scaling_stroke", true}}}
        }},
        {"effects", json::array({
            {{"type", "glow"}, {"radius", 18.0}, {"intensity", 0.7}, {"color", rgba(0.95, 0.2, 0.7, 1.0)}}
        })}
    });

    layers.push_back({
        {"id", "plane_far_cubic_bezier"},
        {"type", "shape"},
        {"z_depth", -400.0},
        {"position", {1400.0, 320.0}},
        {"size", {260.0, 140.0}},
        {"shape", {
            {"type", "path"},
            {"path", json::array({
                {{"type", "move_to"}, {"point", {-120.0, 40.0}}},
                {{"type", "cubic_to"}, {"c1", {-60.0, -80.0}}, {"c2", {60.0, 80.0}}, {"point", {120.0, -40.0}}}
            })},
            {"stroke", {{"color", "#00E0FF"}, {"width", 5.0}, {"non_scaling_stroke", true}}}
        }},
        {"effects", json::array({
            {{"type", "glow"}, {"radius", 22.0}, {"intensity", 0.8}, {"color", rgba(0.0, 0.88, 1.0, 1.0)}}
        })}
    });

    // Plane 2: Midground (Z = 0) with Non-Scaling Stroke verification
    layers.push_back({
        {"id", "midground_non_scaling_stroke_test"},
        {"type", "shape"},
        {"z_depth", 0.0},
        {"position", {960.0, 540.0}},
        {"size", {200.0, 200.0}},
        {"shape", {
            {"type", "ellipse"},
            {"fill", rgba(0.05, 0.2, 0.4, 0.5)},
            {"stroke", {{"color", "#FFFFFF"}, {"width", 4.0}, {"non_scaling_stroke", true}}}
        }},
        {"animation", {
            {"tracks", json::array({
                {
                    {"property", "scale"},
                    {"easing", "in_out_sine"},
                    {"keyframes", json::array({
                        {{"frame", 0}, {"value", {0.2, 0.2}}},
                        {{"frame", 180}, {"value", {3.0, 3.0}}},
                        {{"frame", 360}, {"value", {0.2, 0.2}}}
                    })}
                }
            })}
        }},
        {"effects", json::array({
            {{"type", "glow"}, {"radius", 24.0}, {"intensity", 0.85}, {"color", rgba(0.4, 0.8, 1.0, 1.0)}}
        })}
    });

    // 4 Pivot Invariance Test Shapes (CENTER, TOP_LEFT, BOTTOM_CENTER, CUSTOM)
    const std::vector<std::string> pivotNames = {"pivot_center", "pivot_top_left", "pivot_bottom_center", "pivot_custom"};
    const std::vector<std::array<double, 2>> pivotOffsets = {{0.5, 0.5}, {0.0, 0.0}, {0.5, 1.0}, {0.25, 0.75}};
    const std::vector<std::array<double, 2>> positions = {{480.0, 320.0}, {1440.0, 320.0}, {480.0, 760.0}, {1440.0, 760.0}};

    for (size_t i = 0; i < 4; ++i) {
        layers.push_back({
            {"id", pivotNames[i]},
            {"type", "shape"},
            {"z_depth", 0.0},
            {"position", {positions[i][0], positions[i][1]}},
            {"anchor_uv", {pivotOffsets[i][0], pivotOffsets[i][1]}},
            {"size", {140.0, 90.0}},
            {"shape", {
                {"type", "rect"},
                {"rx", 10.0}, {"ry", 10.0},
                {"fill", rgba(0.2, 0.1, 0.05, 0.6)},
                {"stroke", {{"color", "#FFB020"}, {"width", 3.5}, {"non_scaling_stroke", true}}}
            }},
            {"animation", {
                {"tracks", json::array({
                    {
                        {"property", "rotation"},
                        {"easing", "linear"},
                        {"keyframes", json::array({
                            {{"frame", 0}, {"value", 0.0}},
                            {{"frame", 360}, {"value", 6.2831853}}
                        })}
                    },
                    {
                        {"property", "scale"},
                        {"easing", "in_out_sine"},
                        {"keyframes", json::array({
                            {{"frame", 0}, {"value", {0.6, 0.6}}},
                            {{"frame", 180}, {"value", {1.5, 1.5}}},
                            {{"frame", 360}, {"value", {0.6, 0.6}}}
                        })}
                    }
                })}
            }}
        });
    }

    // Plane 3: Arc-Length Parameterization Polyline + Constant Velocity FollowPath Marker
    layers.push_back({
        {"id", "arc_length_trajectory"},
        {"type", "shape"},
        {"z_depth", 150.0},
        {"position", {960.0, 720.0}},
        {"size", {kW, kH}},
        {"shape", {
            {"type", "path"},
            {"path", json::array({
                {{"type", "move_to"}, {"point", {300.0, 720.0}}},
                {{"type", "line_to"}, {"point", {400.0, 720.0}}}, // Short segment
                {{"type", "line_to"}, {"point", {960.0, 480.0}}}, // Long steep segment
                {{"type", "line_to"}, {"point", {1020.0, 480.0}}}, // Short horizontal crest
                {{"type", "line_to"}, {"point", {1600.0, 720.0}}} // Long slope
            })},
            {"stroke", {{"color", "#E8EBF0"}, {"width", 5.0}, {"cap", "round"}, {"join", "round"}}},
            {"operators", json::array({
                {
                    {"kind", "trim"},
                    {"params", {
                        {"start", 0.0}, {"end", 1.0},
                        {"arc_length_lut", true},
                        {"animation", {
                            {"easing", "linear"},
                            {"keyframes", json::array({
                                {{"frame", 30}, {"value", 0.0}},
                                {{"frame", 300}, {"value", 1.0}}
                            })}
                        }}
                    }}
                }
            })}
        }}
    });

    // FollowPath Marker moving at strictly constant arc-length speed
    layers.push_back({
        {"id", "arc_length_constant_speed_marker"},
        {"type", "shape"},
        {"z_depth", 150.0},
        {"position", {0.0, 0.0}},
        {"size", {36.0, 36.0}},
        {"shape", {
            {"type", "ellipse"},
            {"fill", rgba(1.0, 0.88, 0.12, 1.0)},
            {"stroke", {{"color", "#FFFFFF"}, {"width", 2.5}}}
        }},
        {"follow_path", {
            {"arc_length_lut", true},
            {"progress", {
                {"easing", "linear"},
                {"keyframes", json::array({
                    {{"frame", 30}, {"value", 0.0}},
                    {{"frame", 300}, {"value", 1.0}}
                })}
            }}
        }},
        {"effects", json::array({
            {{"type", "glow"}, {"radius", 32.0}, {"intensity", 0.95}, {"color", rgba(1.0, 0.88, 0.12, 1.0)}}
        })}
    });

    return {
        {"schema", "chronon.render-plan.v3"},
        {"version", 3},
        {"job_id", "primitives_scaling_parity_showcase"},
        {"canvas", {
            {"width", kW},
            {"height", kH},
            {"fps_num", kFps},
            {"fps_den", 1},
            {"duration_frames", kTotalFrames}
        }},
        {"camera", {
            {"position", {0.0, 0.0, 0.0}},
            {"target", {0.0, 0.0, -1000.0}},
            {"focal_length", 1000.0},
            {"dof", {
                {"enabled", true},
                {"focus_distance", 1000.0},
                {"aperture", 2.8}
            }},
            {"animation", {
                {"tracks", json::array({
                    {
                        {"property", "camera.position.x"},
                        {"easing", "in_out_cubic"},
                        {"keyframes", json::array({
                            {{"frame", 0}, {"value", 0.0}},
                            {{"frame", 120}, {"value", 200.0}},
                            {{"frame", 240}, {"value", -200.0}},
                            {{"frame", 360}, {"value", 0.0}}
                        })}
                    },
                    {
                        {"property", "camera.position.z"},
                        {"easing", "in_out_cubic"},
                        {"keyframes", json::array({
                            {{"frame", 0}, {"value", 0.0}},
                            {{"frame", 180}, {"value", 350.0}}, // Dolly out
                            {{"frame", 360}, {"value", 0.0}}
                        })}
                    }
                })}
            }}
        }},
        {"layers", std::move(layers)},
        {"output", {
            {"path", "output/primitives_scaling_showcase.mp4"},
            {"format", "mp4"},
            {"codec", "h264"}
        }}
    };
}

} // namespace chronon::showcase

int main(int argc, char** argv) {
    try {
        fs::path outDir = "out/svg_parity";
        if (argc >= 2) outDir = fs::path(argv[1]);
        fs::create_directories(outDir);

        json plan = chronon::showcase::generatePlan();
        fs::path planPath = outDir / "primitives_scaling_parity.plan.json";
        std::ofstream(planPath) << plan.dump(2) << '\n';
        std::cout << "[SUCCESS] Emitted Showcase Plan: " << planPath.string() << '\n';
        return 0;
    } catch (const std::exception& e) {
        std::cerr << "[ERROR] " << e.what() << '\n';
        return 1;
    }
}
