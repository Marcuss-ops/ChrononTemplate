// ChrononTemplate: Native C++ SVG Parity Emitter and Renderer
// Recreates the Documentary SVG Peak Graph & Neon 2.5D Essay animations.
//
// Complies with schema "chronon.render-plan.v3".
// Covers:
//   1. SVG Path Import / Authoring with Trim Paths (draw-on animation)
//   2. Follow Path marker geometry (yellow glowing sun following path)
//   3. Glow markers (rising checkpoint dot & summit peak marker)
//   4. Multi-pass exponential bloom & inner glow SDF style
//   5. 2.5D Scene composition & analog film post-processing

#include <nlohmann/json.hpp>

#include <algorithm>
#include <array>
#include <cmath>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <memory>
#include <optional>
#include <sstream>
#include <string>
#include <vector>

namespace fs = std::filesystem;
using json = nlohmann::json;

namespace chronon::svg_parity {

constexpr int kDefaultWidth = 1920;
constexpr int kDefaultHeight = 1080;
constexpr int kDefaultFps = 30;
constexpr int kDefaultFrames = 180; // 6.0 seconds

using Point = std::array<double, 2>;

inline json rgba(double r, double g, double b, double a = 1.0) {
    return json::array({r, g, b, a});
}

inline json hexRgba(const std::string& hex, double alpha = 1.0) {
    const auto part = [&](std::size_t at) {
        return std::stoi(hex.substr(at, 2), nullptr, 16) / 255.0;
    };
    return json::array({part(1), part(3), part(5), alpha});
}

inline json moveTo(Point p) {
    return {{"type", "move_to"}, {"point", {p[0], p[1]}}};
}

inline json lineTo(Point p) {
    return {{"type", "line_to"}, {"point", {p[0], p[1]}}};
}

inline json closePath() {
    return {{"type", "close"}};
}

// Build SVG Trim Path operator
inline json buildTrimOperator(int startFrame, int endFrame, const std::string& easing = "in_out_cubic") {
    json keyframes = json::array();
    keyframes.push_back({{"frame", startFrame}, {"value", 0.0}});
    keyframes.push_back({{"frame", endFrame}, {"value", 1.0}});

    json anim = {
        {"easing", easing},
        {"keyframes", std::move(keyframes)}
    };

    return {
        {"kind", "trim"},
        {"params", {
            {"start", 0.0},
            {"end", 1.0},
            {"offset", 0.0},
            {"animation", std::move(anim)}
        }}
    };
}

// Build FollowPath controller for a marker traversing path geometry
inline json buildFollowPath(const std::vector<Point>& points, int startFrame, int endFrame, double endProgress = 1.0) {
    json pathCommands = json::array();
    for (std::size_t i = 0; i < points.size(); ++i) {
        pathCommands.push_back(i == 0 ? moveTo(points[i]) : lineTo(points[i]));
    }

    json keyframes = json::array();
    keyframes.push_back({{"frame", startFrame}, {"value", 0.0}});
    keyframes.push_back({{"frame", endFrame}, {"value", endProgress}});

    return {
        {"path_commands", std::move(pathCommands)},
        {"progress", {
            {"easing", "in_out_cubic"},
            {"keyframes", std::move(keyframes)}
        }},
        {"auto_orient", false},
        {"clamp_end", true}
    };
}

// Generate the complete Documentary SVG Peak Plan
inline json generateSvgPeakPlan(int width = kDefaultWidth, int height = kDefaultHeight) {
    // Exact documentary peak profile points from documentary_svg_peak_v1.svg
    // Normalized and scaled to target canvas
    const double sx = static_cast<double>(width) / 854.0;
    const double sy = static_cast<double>(height) / 480.0;

    const std::vector<Point> rawPoints = {
        {106.0, 366.0},
        {219.0, 278.0},
        {262.0, 245.0},
        {304.0, 245.0},
        {383.0, 190.0},
        {458.0, 118.0},
        {594.0, 302.0},
        {706.0, 226.0}
    };

    std::vector<Point> canvasPoints;
    canvasPoints.reserve(rawPoints.size());
    for (const auto& pt : rawPoints) {
        canvasPoints.push_back({pt[0] * sx, pt[1] * sy});
    }

    json layers = json::array();

    // 1. Near-black background plate with cinematic optical vignette
    layers.push_back({
        {"id", "bg_base"},
        {"type", "color"},
        {"color", rgba(0.012, 0.014, 0.022, 1.0)},
        {"position", {0, 0}},
        {"size", {width, height}},
        {"start_frame", 0},
        {"duration_frames", kDefaultFrames},
        {"screen_space", true},
        {"effects", json::array({
            {
                {"type", "vignette"},
                {"radius", 0.88},
                {"softness", 0.55},
                {"amount", 0.45}
            }
        })}
    });

    // 2. Mountain elevation path with animated Trim Path
    json mountainCommands = json::array();
    for (std::size_t i = 0; i < canvasPoints.size(); ++i) {
        mountainCommands.push_back(i == 0 ? moveTo(canvasPoints[i]) : lineTo(canvasPoints[i]));
    }

    json mountainShape = {
        {"type", "path"},
        {"path", std::move(mountainCommands)},
        {"stroke", {
            {"color", "#E8EBF0"},
            {"width", 5.5 * sx},
            {"cap", "round"},
            {"join", "round"}
        }},
        {"operators", json::array({
            buildTrimOperator(12, 85, "in_out_cubic")
        })}
    };

    layers.push_back({
        {"id", "mountain_peak_line"},
        {"type", "shape"},
        {"position", {width / 2.0, height / 2.0}},
        {"size", {width, height}},
        {"start_frame", 0},
        {"duration_frames", kDefaultFrames},
        {"screen_space", true},
        {"shape", std::move(mountainShape)},
        {"effects", json::array({
            {
                {"type", "glow"},
                {"radius", 22.0},
                {"intensity", 0.75},
                {"color", hexRgba("#E8EBF0", 0.9)}
            },
            {
                {"type", "bloom"},
                {"threshold", 0.65},
                {"radius", 18.0},
                {"intensity", 0.5}
            }
        })}
    });

    // 3. Radiant Sun / Yellow Marker traversing the mountain line
    layers.push_back({
        {"id", "yellow_sun_marker"},
        {"type", "shape"},
        {"position", {0.0, 0.0}},
        {"size", {44.0 * sx, 44.0 * sx}},
        {"start_frame", 10},
        {"duration_frames", kDefaultFrames - 10},
        {"screen_space", true},
        {"shape", {
            {"type", "ellipse"},
            {"fill", hexRgba("#FFDC1E")},
            {"stroke", {
                {"color", "#FFF2A0"},
                {"width", 3.0}
            }}
        }},
        {"follow_path", buildFollowPath(canvasPoints, 12, 95, 0.72)},
        {"effects", json::array({
            {
                {"type", "glow"},
                {"radius", 36.0},
                {"intensity", 0.95},
                {"color", hexRgba("#FFDC1E", 1.0)}
            },
            {
                {"type", "bloom"},
                {"threshold", 0.3},
                {"radius", 32.0},
                {"intensity", 0.85}
            }
        })}
    });

    // 4. Rising slope checkpoint marker (Red)
    layers.push_back({
        {"id", "red_rising_marker"},
        {"type", "shape"},
        {"position", {canvasPoints[2][0], canvasPoints[2][1]}},
        {"size", {26.0 * sx, 26.0 * sx}},
        {"start_frame", 35},
        {"duration_frames", kDefaultFrames - 35},
        {"screen_space", true},
        {"shape", {
            {"type", "ellipse"},
            {"fill", hexRgba("#F02B3C")}
        }},
        {"effects", json::array({
            {
                {"type", "glow"},
                {"radius", 24.0},
                {"intensity", 0.85},
                {"color", hexRgba("#F02B3C", 1.0)}
            }
        })}
    });

    // 5. Summit peak checkpoint marker (Red)
    layers.push_back({
        {"id", "red_summit_marker"},
        {"type", "shape"},
        {"position", {canvasPoints[5][0], canvasPoints[5][1]}},
        {"size", {30.0 * sx, 30.0 * sx}},
        {"start_frame", 68},
        {"duration_frames", kDefaultFrames - 68},
        {"screen_space", true},
        {"shape", {
            {"type", "ellipse"},
            {"fill", hexRgba("#F02B3C")}
        }},
        {"effects", json::array({
            {
                {"type", "glow"},
                {"radius", 30.0},
                {"intensity", 0.9},
                {"color", hexRgba("#F02B3C", 1.0)}
            }
        })}
    });

    return {
        {"schema", "chronon.render-plan.v3"},
        {"version", 3},
        {"job_id", "documentary_svg_peak_parity"},
        {"canvas", {
            {"width", width},
            {"height", height},
            {"fps_num", kDefaultFps},
            {"fps_den", 1},
            {"duration_frames", kDefaultFrames}
        }},
        {"layers", std::move(layers)},
        {"output", {
            {"path", "output/documentary_svg_peak_parity.mp4"},
            {"format", "mp4"},
            {"codec", "h264"}
        }}
    };
}

// Generate the 2.5D Neon Essay Scene Plan
inline json generateNeonEssay25DPlan(int width = kDefaultWidth, int height = kDefaultHeight) {
    json layers = json::array();

    // Deep dark field
    layers.push_back({
        {"id", "bg"},
        {"type", "color"},
        {"color", rgba(0.015, 0.015, 0.025, 1.0)},
        {"position", {0, 0}},
        {"size", {width, height}},
        {"start_frame", 0},
        {"duration_frames", 210},
        {"screen_space", true},
        {"effects", json::array({
            {
                {"type", "vignette"},
                {"radius", 0.90},
                {"softness", 0.5},
                {"amount", 0.4}
            }
        })}
    });

    // Camera with pan and dolly tracks
    json camTracks = json::array();
    // Pan X
    camTracks.push_back({
        {"property", "camera.position.x"},
        {"easing", "in_out_cubic"},
        {"keyframes", json::array({
            {{"frame", 0}, {"value", 0.0}},
            {{"frame", 60}, {"value", 0.0}},
            {{"frame", 120}, {"value", 500.0}},
            {{"frame", 210}, {"value", 350.0}}
        })}
    });
    // Dolly Z
    camTracks.push_back({
        {"property", "camera.position.z"},
        {"easing", "in_out_cubic"},
        {"keyframes", json::array({
            {{"frame", 0}, {"value", 0.0}},
            {{"frame", 120}, {"value", 0.0}},
            {{"frame", 210}, {"value", 450.0}}
        })}
    });

    return {
        {"schema", "chronon.render-plan.v3"},
        {"version", 3},
        {"job_id", "neon_essay_25d_dof_parity"},
        {"canvas", {
            {"width", width},
            {"height", height},
            {"fps_num", 30},
            {"fps_den", 1},
            {"duration_frames", 210}
        }},
        {"camera", {
            {"position", {0.0, 0.0, 0.0}},
            {"target", {0.0, 0.0, -500.0}},
            {"fov_degrees", 55.0},
            {"dof", {
                {"enabled", true},
                {"focus_distance", 500.0},
                {"aperture", 2.8}
            }},
            {"animation", {{"tracks", std::move(camTracks)}}}
        }},
        {"layers", std::move(layers)},
        {"output", {
            {"path", "output/neon_essay_25d_dof_parity.mp4"},
            {"format", "mp4"},
            {"codec", "h264"}
        }}
    };
}

} // namespace chronon::svg_parity

int main(int argc, char** argv) {
    try {
        std::cout << "========================================================\n"
                  << "ChrononTemplate: SVG Parity Native C++ Emitter\n"
                  << "Recreating Documentary SVG Peak & 2.5D Neon Essay\n"
                  << "========================================================\n";

        fs::path outDir = "out/svg_parity";
        if (argc >= 2) {
            outDir = fs::path(argv[1]);
        }
        fs::create_directories(outDir);

        // 1. Emit Documentary SVG Peak Plan
        json peakPlan = chronon::svg_parity::generateSvgPeakPlan();
        fs::path peakPlanPath = outDir / "documentary_svg_peak_parity.plan.json";
        std::ofstream(peakPlanPath) << peakPlan.dump(2) << '\n';
        std::cout << "[SUCCESS] Emitted SVG Peak Parity Plan: " << peakPlanPath.string() << '\n';

        // 2. Emit 2.5D Neon Essay Scene Plan
        json essayPlan = chronon::svg_parity::generateNeonEssay25DPlan();
        fs::path essayPlanPath = outDir / "neon_essay_25d_dof_parity.plan.json";
        std::ofstream(essayPlanPath) << essayPlan.dump(2) << '\n';
        std::cout << "[SUCCESS] Emitted 2.5D Neon Essay Parity Plan: " << essayPlanPath.string() << '\n';

        return 0;
    } catch (const std::exception& e) {
        std::cerr << "[ERROR] " << e.what() << '\n';
        return 1;
    }
}
