// Native C++ emitter for the Example Svg reference recreation.
//
// Source of truth: the 14 reference frames in drive_downloads/ExampleSvg
// (ref_01..ref_14, 1214x676). Measured traits reproduced here:
//   - near-black field, one large central glowing emblem (~30% of width),
//   - lime-yellow hot stroke (240,251,11) with a pulsing glow whose bright
//     share oscillates in the measured 1%..6.7% band,
//   - saturated red (234,0,52) lower-third bar bottom-left that changes
//     width in the late frames plus a faint red (134,14,7) wake,
//   - staggered line-drawing reveal (trim paths) across the whole shot.
//
// Emission is native C++ (scripts accumulate in the same convention as
// emit_oil_crisis_reference_plans.cpp); no Python is involved.
//
// Also emits three certification plans for the scene-glow/matte vocabulary
// on PNG image layers (static glow, pulsing glow via effect_param_tracks,
// and a luma track-matte pair).
#include <nlohmann/json.hpp>

#include <algorithm>
#include <array>
#include <optional>
#include <cmath>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <string>
#include <utility>
#include <vector>

namespace fs = std::filesystem;
using json = nlohmann::json;

namespace {

constexpr int kWidth = 1920;
constexpr int kHeight = 1080;
constexpr int kFps = 30;
constexpr int kFrames = 210;
constexpr double kCenterX = 960.0;
constexpr double kCenterY = 540.0;

using Point = std::array<double, 2>;

json rgba(const std::string& hex, double alpha = 1.0) {
    const auto part = [&](std::size_t at) {
        return std::stoi(hex.substr(at, 2), nullptr, 16) / 255.0;
    };
    return json::array({part(1), part(3), part(5), alpha});
}

json animation(std::vector<json> tracks) { return {{"tracks", std::move(tracks)}}; }

json trimOperator(int f0, int f1, double hold = 0.0) {
    json inner = json::array();
    inner.push_back({{"frame", f0}, {"value", {hold, hold, 0.0}}});
    inner.push_back({{"frame", f1}, {"value", {hold, 1.0, 0.0}}});
    json animation = json::object();
    animation["easing"] = "linear";
    animation["keyframes"] = std::move(inner);
    json params = json::object();
    params["start"] = 0.0;
    params["end"] = 1.0;
    params["offset"] = 0.0;
    params["animation"] = std::move(animation);
    json entry = json::object();
    entry["kind"] = "trim";
    entry["params"] = std::move(params);
    return entry;
}

struct GlowSpec {
    double radius;
    double intensity;
    json color;
};

json glowEffect(const GlowSpec& spec) {
    return {{"type", "glow"},
            {"radius", spec.radius},
            {"intensity", spec.intensity},
            {"color", spec.color}};
}

// Pulsing glow intensity sampled from the measured bright-share oscillation
// (ref bright share 0.9%..6.7% of pixels above luma 80 in the central cell).
json pulseTracks(int cycles, double hi, double finalLow) {
    json keyframes = json::array();
    const int span = kFrames / cycles;
    for (int c = 0; c < cycles; ++c) {
        const double low = (c == cycles - 1) ? finalLow : hi * 0.35;
        keyframes.push_back({{"frame", c * span}, {"value", low}});
        keyframes.push_back({{"frame", c * span + span / 2}, {"value", hi}});
    }
    std::sort(keyframes.begin(), keyframes.end(), [](const json& a, const json& b) {
        return a["frame"].get<int>() < b["frame"].get<int>();
    });
    return json::array({{{"effect_id", "light.glow"},
                         {"param", "intensity"},
                         {"easing", "in_out_sine"},
                         {"keyframes", std::move(keyframes)}}});
}

json opacityTrack(std::vector<std::pair<int, double>> keys,
                  const std::string& easing = "in_out_sine") {
    json keyframes = json::array();
    for (const auto& [frame, value] : keys)
        keyframes.push_back({{"frame", frame}, {"value", {value}}});
    return {{"property", "opacity"}, {"easing", easing}, {"keyframes", keyframes}};
}

json moveTo(Point p) { return {{"type", "move_to"}, {"point", {p[0], p[1]}}}; }
json lineTo(Point p) { return {{"type", "line_to"}, {"point", {p[0], p[1]}}}; }
json closePath() { return {{"type", "close"}}; }

json circleCommands(double radius, int steps = 96) {
    json commands = json::array();
    for (int i = 0; i <= steps; ++i) {
        const double angle = 2.0 * M_PI * i / steps;
        const Point p{radius * std::cos(angle), radius * std::sin(angle)};
        commands.push_back(i == 0 ? moveTo(p) : lineTo(p));
    }
    commands.push_back(closePath());
    return commands;
}

json shapeLayer(const std::string& id, json geometry, int start, int duration) {
    json layer = {{"id", id},
                  {"type", "shape"},
                  {"shape", std::move(geometry)},
                  {"size", {kWidth, kHeight}},
                  {"position", {kCenterX, kCenterY}},
                  {"start_frame", start},
                  {"duration_frames", duration},
                  {"screen_space", true}};
    return layer;
}

json ringLayer(const std::string& id, double radius, const std::string& strokeColor,
               double strokeWidth, json operators, int start,
               const std::optional<GlowSpec>& glow = std::nullopt) {
    json geometry = {{"type", "path"},
                     {"path", circleCommands(radius)},
                     {"stroke", {{"color", strokeColor},
                                 {"width", strokeWidth},
                                 {"cap", "round"},
                                 {"join", "round"}}}};
    if (!operators.is_null()) geometry["operators"] = json::array({std::move(operators)});
    auto layer = shapeLayer(id, std::move(geometry), start, kFrames - start);
    if (glow) layer["effects"] = json::array({glowEffect(*glow)});
    return layer;
}

json strokeLine(const std::string& id, Point from, Point to,
                const std::string& color, double width, int start,
                json operators, const std::optional<GlowSpec>& glow = std::nullopt) {
    json geometry = {{"type", "path"},
                     {"path", json::array({moveTo(from), lineTo(to)})},
                     {"stroke", {{"color", color},
                                 {"width", width},
                                 {"cap", "butt"},
                                 {"join", "round"}}}};
    if (!operators.is_null()) geometry["operators"] = json::array({std::move(operators)});
    auto layer = shapeLayer(id, std::move(geometry), start, kFrames - start);
    if (glow) layer["effects"] = json::array({glowEffect(*glow)});
    return layer;
}

json polygonLayer(const std::string& id, const std::vector<Point>& points,
                  const std::string& fill, int start, const std::optional<GlowSpec>& glow = std::nullopt,
                  json opacity = nullptr, json pulse = nullptr) {
    json commands = json::array();
    for (std::size_t i = 0; i < points.size(); ++i)
        commands.push_back(i == 0 ? moveTo(points[i]) : lineTo(points[i]));
    commands.push_back(closePath());
    json geometry = {{"type", "path"}, {"path", std::move(commands)},
                     {"fill", rgba(fill)}};
    auto layer = shapeLayer(id, std::move(geometry), start, kFrames - start);
    if (glow) layer["effects"] = json::array({glowEffect(*glow)});
    if (!opacity.is_null()) layer["animation"] = animation({std::move(opacity)});
    if (!pulse.is_null()) layer["effect_param_tracks"] = std::move(pulse);
    return layer;
}

// Certification plans: glow on PNG image layers (off/static/pulse) and a
// luma track matte over the same plate. PNG assets sit at the workspace root
// (test_f1.png plate, test_mask.png grayscale matte) and are referenced with
// assets-root = workspace root.
void writePlanFile(const fs::path& out, const json& doc) {
    std::ofstream stream(out);
    if (!stream)
        throw std::runtime_error("cannot write plan: " + out.string());
    stream << doc.dump(2) << '\n';
}

void emitGlowMatteCerts(const fs::path& plans) {
    constexpr int certFrames = 24;
    const std::string plate = "test_f1.png";
    const std::string matte = "test_mask.png";
    const std::array<std::string, 4> certJobs{"cert_glow_png_off",
                                              "cert_glow_png_static",
                                              "cert_glow_png_pulse",
                                              "cert_matte_luma"};
    for (const auto& job : certJobs) {
        json layers = json::array();
        layers.push_back({{"id", "bg"}, {"type", "color"},
                          {"color", rgba("#060606")},
                          {"size", {kWidth, kHeight}}, {"position", {0, 0}},
                          {"start_frame", 0}, {"duration_frames", certFrames},
                          {"screen_space", true}});
        json plateLayer = {{"id", "plate"},
                           {"type", "image"},
                           {"asset", plate},
                           {"size", {1220, 682}},
                           {"position", {kCenterX, kCenterY}},
                           {"fit", "contain"},
                           {"start_frame", 0},
                           {"duration_frames", certFrames},
                           {"screen_space", true}};
        if (job == "cert_glow_png_static" || job == "cert_glow_png_pulse") {
            plateLayer["effects"] = json::array({
                glowEffect(GlowSpec{26.0, 0.6, rgba("#F0FB0B")})});
        }
        if (job == "cert_glow_png_pulse") {
            plateLayer["effect_param_tracks"] = json::array({
                {{"effect_id", "light.glow"},
                 {"param", "intensity"},
                 {"easing", "in_out_sine"},
                 {"keyframes",
                  json::array({{{"frame", 0}, {"value", 0.15}},
                               {{"frame", 8}, {"value", 1.0}},
                               {{"frame", 16}, {"value", 0.15}},
                               {{"frame", 23}, {"value", 1.0}}})}}});
        }
        if (job == "cert_matte_luma") {
            layers.push_back({{"id", "plate"},
                              {"type", "image"},
                              {"asset", plate},
                              {"size", {1220, 682}},
                              {"position", {kCenterX, kCenterY}},
                              {"fit", "contain"},
                              {"start_frame", 0},
                              {"duration_frames", certFrames},
                              {"screen_space", true},
                              {"track_matte",
                               {{"source", "matte_luma"},
                                {"type", "luma"}}}});
            layers.push_back({{"id", "matte_luma"},
                              {"type", "image"},
                              {"asset", matte},
                              {"size", {1220, 682}},
                              {"position", {kCenterX, kCenterY}},
                              {"fit", "contain"},
                              {"start_frame", 0},
                              {"duration_frames", certFrames},
                              {"screen_space", true}});
        } else {
            layers.push_back(std::move(plateLayer));
        }
        json doc = {{"schema", "chronon.render-plan.v3"},
                    {"version", 3},
                    {"job_id", job},
                    {"canvas",
                     {{"width", kWidth}, {"height", kHeight}, {"fps_num", kFps},
                      {"fps_den", 1}, {"duration_frames", certFrames}}},
                    {"layers", std::move(layers)},
                    {"output",
                     {{"path", "output/example_svg/" + std::string(job) + ".mp4"},
                      {"format", "mp4"}, {"codec", "h264"}}}};
        writePlanFile(plans / (std::string(job) + ".plan.json"), doc);
    }
    std::cout << "Emitted " << certJobs.size()
              << " glow/matte certification plans in " << plans.string() << '\n';
}

} // namespace

int main(int argc, char** argv) {
    try {
        if (argc != 2)
            throw std::runtime_error(
                "usage: chronontemplate_emit_example_svg_recreation_plans <workspace-root>");
        const fs::path root = fs::absolute(argv[1]);
        const fs::path plans = root / "output" / "example_svg";
        fs::create_directories(plans);

        const std::string lime = "#F0FB0B";     // measured 240,251,11
        const std::string limeSoft = "#BCE204"; // halo falloff color
        const std::string preIgnite = "#7D7D64";
        const std::string redBar = "#EA0034";   // measured 234,0,52
        const std::string redWake = "#860E07";  // measured 134,14,7

        json layers = json::array();

        // 0 — near-black plate + gentle vignette (refs mean RGB 3..5/255).
        layers.push_back(
            {{"id", "bg"}, {"type", "color"}, {"color", rgba("#060606")},
             {"size", {kWidth, kHeight}}, {"position", {0, 0}},
             {"start_frame", 0}, {"duration_frames", kFrames},
             {"screen_space", true},
             {"effects",
              json::array({{{"type", "vignette"}, {"radius", 0.95},
                            {"softness", 0.6}, {"amount", 0.25}}})}});

        // 1 — outer neutral ring draws first (ref_02 grigia che entra).
        layers.push_back(ringLayer(
            "ring_outer", 150.0, preIgnite, 9.0, trimOperator(18, 96), 18,
            GlowSpec{20.0, 0.25, rgba("#8D8F62")}));

        // 2 — inner lime ring ignites and pulses for the whole shot.
        layers.push_back(ringLayer(
            "ring_inner", 93.0, lime, 9.0, trimOperator(40, 130), 40,
            GlowSpec{26.0, 0.4, rgba(limeSoft)}));
        layers.back()["effect_param_tracks"] = pulseTracks(6, 0.85, 0.45);

        // 3 — six spoke bars, staggered draws (ref_01 columnar rack).
        const std::array<double, 6> angles{90.0, 30.0, -30.0, -90.0, -150.0, 150.0};
        for (int i = 0; i < 6; ++i) {
            const double rad = angles[i] * M_PI / 180.0;
            const Point from{45.0 * std::cos(rad), 45.0 * std::sin(rad)};
            const Point to{142.0 * std::cos(rad), 142.0 * std::sin(rad)};
            layers.push_back(strokeLine(
                "spoke_" + std::to_string(i), from, to, lime, 7.0,
                70 + i * 8, trimOperator(70 + i * 8, 150 + i * 4),
                GlowSpec{22.0, 0.35, rgba(limeSoft)}));
            layers.back()["effect_param_tracks"] = pulseTracks(6, 0.85, 0.45);
        }

        // 4 — solid core bar with dark slot (the @@@ block of ref_01).
        layers.push_back(polygonLayer(
            "core_bar",
            {{-110.0, 64.0}, {110.0, 64.0}, {110.0, 96.0}, {-110.0, 96.0}},
            lime, 100,
            GlowSpec{30.0, 0.5, rgba(limeSoft)},
            opacityTrack({{100, 0.15}, {140, 0.75}, {kFrames - 1, 0.75}}),
            pulseTracks(6, 0.85, 0.45)));
        layers.back()["shape"]["operators"] = json::array({trimOperator(100, 165)});

        // 5 — red diagonal wake sweeping through at mid (ref_05 accent).
        layers.push_back(strokeLine(
            "red_sweep", {-190.0, 90.0}, {190.0, -90.0}, redWake, 6.0, 130,
            trimOperator(140, 192), GlowSpec{18.0, 0.3, rgba(redWake)}));

        // 6 — central core diamond ignites at the reveal midpoint.
        layers.push_back(polygonLayer(
            "core", {{0.0, -46.0}, {46.0, 0.0}, {0.0, 46.0}, {-46.0, 0.0}},
            lime, 110, GlowSpec{34.0, 0.55, rgba(limeSoft)},
            opacityTrack({{110, 0.0}, {150, 0.9}, {168, 0.35}, {186, 0.9},
                          {kFrames - 1, 0.6}}),
            pulseTracks(6, 0.85, 0.45)));

        // 7 — saturated red lower-third bar, bottom-left (ref_11..ref_14).
        layers.push_back(strokeLine(
            "lower_third", {-560.0, 474.0}, {220.0, 474.0}, redBar, 16.0, 36,
            trimOperator(40, 78), GlowSpec{14.0, 0.25, rgba(redBar)}));
        layers.push_back(strokeLine(
            "lower_third_tail", {240.0, 474.0}, {420.0, 474.0}, redBar, 16.0,
            78, nullptr, GlowSpec{14.0, 0.25, rgba(redBar)}));

        // 8 — small white wordmark bottom-left (ref corner marks).
        layers.push_back(
            {{"id", "wordmark"},
             {"type", "text"},
             {"text", "CHRONON — SVG RECREATION"},
             {"size", {520, 60}},
             {"position", {60, 960}},
             {"style",
              {{"font", "Chronon3d/assets/fonts/Inter-Bold.ttf"},
               {"font_size", 34},
               {"fill", "#F5F5F5"}}},
             {"start_frame", 30},
             {"duration_frames", kFrames - 30},
             {"screen_space", true},
             {"animation", animation({opacityTrack({{30, 0.0}, {58, 0.9}})})}});

        json doc = {{"schema", "chronon.render-plan.v3"},
                    {"version", 3},
                    {"job_id", "example_svg_recreation"},
                    {"canvas",
                     {{"width", kWidth}, {"height", kHeight}, {"fps_num", kFps},
                      {"fps_den", 1}, {"duration_frames", kFrames}}},
                    {"layers", std::move(layers)},
                    {"output",
                     {{"path", "output/example_svg/example_svg_recreation.mp4"},
                      {"format", "mp4"}, {"codec", "h264"}}}};

        const fs::path out = plans / "example_svg_recreation.plan.json";
        writePlanFile(out, doc);
        std::cout << "Emitted native C++ plan: " << out.string() << '\n';

        // ── glow-on-PNG + track-matte certification plans (24 frames) ───────
        emitGlowMatteCerts(plans);
        return 0;
    } catch (const std::exception& error) {
        std::cerr << error.what() << '\n';
        return 1;
    }
}
