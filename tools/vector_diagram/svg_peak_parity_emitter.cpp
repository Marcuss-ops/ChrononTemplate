// ChrononTemplate: Native C++ SVG Parity Emitter
//
// Emits the RenderPlan V3 documents for the Documentary SVG Peak scene and
// the 2.5D Neon Essay scene. Every scene value of the peak plan — geometry,
// framing, timing, easing, colors, checkpoints and camera — comes from the
// shared `svg_peak_scene.hpp` module, which parses the SVG asset and the
// scene preset at runtime. No scene coordinate or keyframe is duplicated in
// this file (certification tests SVG-02/SVG-03/INT-02).
//
// Plan conventions mirror `documentary_svg_peak_registry.py` (the Python
// generator whose plans are accepted by `chronon3d_cli validate`): the peak
// path lives in the SVG asset referenced by name, the marker's `follow_path`
// carries the same canvas-space geometry emitted from the same parse.
//
// Usage:
//   svg_peak_parity_emitter [outDir] [--svg path] [--preset path]
//
// Errors (SVG-08): every malformed input produces an explicit "[ERROR]"
// line and exit code 1 — never a crash.

#include "svg_peak_scene.hpp"

#include <nlohmann/json.hpp>

#include <array>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <string>
#include <vector>

namespace fs = std::filesystem;
using json = nlohmann::json;

namespace chronon::svg_parity {

inline json rgba(const std::array<double, 4>& c) {
    return json::array({c[0], c[1], c[2], c[3]});
}

inline json pathCommands(const std::vector<Vec2>& points) {
    json commands = json::array();
    for (std::size_t i = 0; i < points.size(); ++i) {
        commands.push_back({{"type", i == 0 ? "move_to" : "line_to"},
                            {"point", {points[i].x, points[i].y}}});
    }
    return commands;
}

inline json keyframe(int frame, double value) {
    return {{"frame", frame}, {"value", value}};
}

// RenderPlan V3 for the Documentary SVG Peak scene, driven entirely by the
// shared SceneSpec. The trim operator animates `#peak_line` inside the SVG
// asset; the marker follows the same geometry through `follow_path`.
inline json generateSvgPeakPlan(const SceneSpec& spec) {
    const int frames = spec.frames;

    json layers = json::array();

    layers.push_back({{"id", "background"},
                      {"type", "color"},
                      {"color", rgba(spec.background)},
                      {"size", {spec.width, spec.height}},
                      {"position", {0, 0}},
                      {"start_frame", 0},
                      {"duration_frames", frames}});

    json svgLayer = {{"id", "peak_svg"},
                     {"type", "shape"},
                     {"position", {spec.framingOffset[0], -spec.framingOffset[1]}},
                     {"size", {spec.width * spec.framingScale, spec.height * spec.framingScale}},
                     {"start_frame", 0},
                     {"duration_frames", frames}};
    svgLayer["shape"] = {
        {"type", "path"},
        {"asset", spec.assetName},
        {"operators", json::array({{{"kind", "trim"},
                                    {"target", "peak_line"},
                                    {"params",
                                     {{"start", 0.0},
                                      {"end", 0.0},
                                      {"animation",
                                       {{"easing", spec.trim.easing},
                                        {"keyframes",
                                         json::array({keyframe(spec.trim.keyframes[0].first, 0.0),
                                                      keyframe(spec.trim.keyframes[1].first, 1.0)})}}}}}}})}};
    layers.push_back(std::move(svgLayer));

    json markerLayer = {{"id", spec.markerId},
                        {"type", "shape"},
                        {"position", {0, 0}},
                        {"size", {spec.markerSize, spec.markerSize}},
                        {"start_frame", spec.marker.keyframes.front().first},
                        {"duration_frames", frames - spec.marker.keyframes.front().first},
                        {"shape", {{"type", "ellipse"}, {"fill", rgba(spec.markerFill)}}},
                        {"follow_path",
                         {{"path_commands", pathCommands(spec.pathPoints)},
                          {"progress",
                           {{"easing", spec.marker.easing},
                            {"keyframes",
                             json::array({keyframe(spec.marker.keyframes[0].first, 0.0),
                                          keyframe(spec.marker.keyframes[1].first,
                                                   spec.marker.keyframes[1].second)})}}},
                          {"auto_orient", false},
                          {"clamp_end", true}}}};
    if (spec.markerGlow.enabled) {
        markerLayer["effects"] = json::array({{{"type", "glow"},
                                               {"radius", spec.markerGlow.radius},
                                               {"intensity", spec.markerGlow.intensity},
                                               {"color", rgba(spec.markerGlow.color)}}});
    }
    layers.push_back(std::move(markerLayer));

    for (const CheckpointSpec& checkpoint : spec.checkpoints) {
        layers.push_back({{"id", checkpoint.id},
                          {"type", "shape"},
                          {"position", {checkpoint.center.x, -checkpoint.center.y}},
                          {"size", {checkpoint.radius * 2.0, checkpoint.radius * 2.0}},
                          {"start_frame", checkpoint.startFrame},
                          {"duration_frames", frames - checkpoint.startFrame},
                          {"shape", {{"type", "ellipse"}, {"fill", rgba(checkpoint.fill)}}}});
    }

    json plan = {{"schema", "chronon.render-plan.v3"},
                 {"version", 3},
                 {"job_id", spec.jobId},
                 {"canvas",
                  {{"width", spec.width},
                   {"height", spec.height},
                   {"fps_num", spec.fps},
                   {"fps_den", 1},
                   {"duration_frames", frames}}},
                 {"layers", std::move(layers)},
                 {"output", {{"path", spec.jobId + ".mp4"}, {"format", "mp4"}}}};

    if (spec.camera.enabled) {
        json tracks = json::array();
        auto pushTrack = [&](const char* property, const Track& track) {
            if (track.keyframes.empty()) return;
            json keyframes = json::array();
            for (const auto& [frame, value] : track.keyframes) {
                keyframes.push_back(keyframe(frame, value));
            }
            tracks.push_back({{"property", property},
                              {"easing", track.easing},
                              {"keyframes", std::move(keyframes)}});
        };
        pushTrack("camera.position.x", spec.camera.panX);
        pushTrack("camera.position.y", spec.camera.panY);
        pushTrack("camera.position.z", spec.camera.dollyZ);
        plan["camera"] = {{"position", {0.0, 0.0, 0.0}},
                          {"target", {0.0, 0.0, -500.0}},
                          {"fov_degrees", 55.0},
                          {"animation", {{"tracks", std::move(tracks)}}}};
    }

    return plan;
}

// The 2.5D Neon Essay scene plan (camera + DoF demo). Self-contained: it
// carries no peak-scene geometry and shares no data with the SVG asset.
inline json generateNeonEssay25DPlan(int width, int height) {
    json layers = json::array();

    layers.push_back({{"id", "bg"},
                      {"type", "color"},
                      {"color", json::array({0.015, 0.015, 0.025, 1.0})},
                      {"position", {0, 0}},
                      {"size", {width, height}},
                      {"start_frame", 0},
                      {"duration_frames", 210},
                      {"screen_space", true},
                      {"effects", json::array({{{"type", "vignette"},
                                                {"radius", 0.90},
                                                {"softness", 0.5},
                                                {"amount", 0.4}}})}});

    json camTracks = json::array();
    camTracks.push_back({{"property", "camera.position.x"},
                         {"easing", "in_out_cubic"},
                         {"keyframes", json::array({keyframe(0, 0.0), keyframe(60, 0.0),
                                                    keyframe(120, 500.0), keyframe(210, 350.0)})}});
    camTracks.push_back({{"property", "camera.position.z"},
                         {"easing", "in_out_cubic"},
                         {"keyframes", json::array({keyframe(0, 0.0), keyframe(120, 0.0),
                                                    keyframe(210, 450.0)})}});

    return {{"schema", "chronon.render-plan.v3"},
            {"version", 3},
            {"job_id", "neon_essay_25d_dof_parity"},
            {"canvas",
             {{"width", width},
              {"height", height},
              {"fps_num", 30},
              {"fps_den", 1},
              {"duration_frames", 210}}},
            {"camera",
             {{"position", {0.0, 0.0, 0.0}},
              {"target", {0.0, 0.0, -500.0}},
              {"fov_degrees", 55.0},
              {"dof", {{"enabled", true}, {"focus_distance", 500.0}, {"aperture", 2.8}}},
              {"animation", {{"tracks", std::move(camTracks)}}}}},
            {"layers", std::move(layers)},
            {"output",
             {{"path", "neon_essay_25d_dof_parity.mp4"}, {"format", "mp4"}, {"codec", "h264"}}}};
}

} // namespace chronon::svg_parity

namespace {

struct Options {
    std::filesystem::path outDir = "out/svg_parity";
    std::string svg = "tools/vector_diagram/assets/documentary_svg_peak_v1.svg";
    std::string preset = "catalog/documentary_svg_peak_v1.json";
};

void printUsage() {
    std::cout << "Usage: svg_peak_parity_emitter [outDir] [--svg path] [--preset path]\n";
}

} // namespace

int main(int argc, char** argv) {
    using namespace chronon::svg_parity;

    Options options;
    try {
        for (int i = 1; i < argc; ++i) {
            const std::string arg = argv[i];
            if (arg == "--help" || arg == "-h") {
                printUsage();
                return 0;
            }
            if (arg == "--svg" && i + 1 < argc) {
                options.svg = argv[++i];
            } else if (arg == "--preset" && i + 1 < argc) {
                options.preset = argv[++i];
            } else if (!arg.empty() && arg[0] != '-') {
                options.outDir = arg;
            } else {
                throw SceneError("unknown argument: " + arg);
            }
        }

        std::cout << "========================================================\n"
                  << "ChrononTemplate: SVG Parity Native C++ Emitter\n"
                  << "Scene source of truth: " << options.svg << " + " << options.preset << "\n"
                  << "========================================================\n";

        fs::create_directories(options.outDir);

        // Documentary SVG Peak plan: every value comes from the shared module.
        const SceneSpec spec = loadSceneSpec(options.svg, options.preset);
        const json peakPlan = generateSvgPeakPlan(spec);
        const fs::path peakPlanPath = options.outDir / (spec.jobId + ".plan.json");
        std::ofstream(peakPlanPath) << peakPlan.dump(2) << '\n';
        std::cout << "[SUCCESS] Emitted SVG Peak Parity Plan: " << peakPlanPath.string() << '\n';

        // 2.5D Neon Essay scene plan.
        const json essayPlan = generateNeonEssay25DPlan(spec.width, spec.height);
        const fs::path essayPlanPath = options.outDir / "neon_essay_25d_dof_parity.plan.json";
        std::ofstream(essayPlanPath) << essayPlan.dump(2) << '\n';
        std::cout << "[SUCCESS] Emitted 2.5D Neon Essay Parity Plan: " << essayPlanPath.string() << '\n';

        return 0;
    } catch (const SceneError& e) {
        std::cerr << "[ERROR] " << e.what() << '\n';
        return 1;
    } catch (const std::exception& e) {
        std::cerr << "[ERROR] unexpected failure: " << e.what() << '\n';
        return 1;
    }
}
