// Motion-design stress suite (20 cases, 4 modules).
//
// Each case authors a chronon.render-plan.v3 document, checks the contract the
// renderer must honour, and writes the plan to out/motion_design_stress/plans.
// The checks are deliberately split between:
//   * structural assertions on the emitted plan (the decoder contract), and
//   * closed-form maths for the invariants a renderer bug would break
//     (premultiplied alpha, Multiply, perspective parallax, cubic derivatives,
//     EV stops, 8-bit vs 16-bit quantisation, clamped vs zero edge sampling).
//
// The plans are the executable input for chronon3d_cli validate/render; the C++
// test keeps the authoring contract pinned without needing a GPU in CTest.

#include "motion_check.hpp"

#include <nlohmann/json.hpp>

#include <algorithm>
#include <chrono>
#include <cmath>
#include <cstdio>
#include <filesystem>
#include <fstream>
#include <initializer_list>
#include <random>
#include <string>
#include <vector>

namespace {

using json = nlohmann::json;
namespace fs = std::filesystem;
using chrononmotion_test::check;
using chrononmotion_test::checkNear;
using chrononmotion_test::section;

constexpr int W = 1920;
constexpr int H = 1080;
constexpr int FPS = 30;
constexpr const char* FONT = "assets/fonts/Inter-Bold.ttf";

std::string asset(const char* name) {
    return std::string("out/motion_design_stress/assets/") + name;
}

fs::path sourceRoot() {
#ifdef CHRONONTEMPLATE_SOURCE_DIR
    return fs::path(CHRONONTEMPLATE_SOURCE_DIR);
#else
    return fs::current_path();
#endif
}

json arr2(float a, float b) { return json::array({a, b}); }
json arr3(float a, float b, float c) { return json::array({a, b, c}); }
json rgba(int r, int g, int b, float a = 1.0f) {
    return json::array({r / 255.0f, g / 255.0f, b / 255.0f, a});
}

json basePlan(const std::string& id, int frames, int w = W, int h = H, int fps = FPS) {
    json p = json::object();
    p["schema"] = "chronon.render-plan.v3";
    p["version"] = 3;
    p["job_id"] = id;
    p["canvas"] = json{{"width", w}, {"height", h}, {"fps_num", fps}, {"fps_den", 1},
                       {"duration_frames", frames}};
    p["output"] = json{{"path", "out/motion_design_stress/render/" + id + ".mp4"},
                       {"format", "mp4"}, {"codec", "h264"}, {"color_space", "rec709"}};
    p["layers"] = json::array();
    return p;
}

json layerBase(const std::string& id, const std::string& type, float x, float y,
               float w, float h, int start, int duration) {
    return json{{"id", id}, {"type", type}, {"position", arr2(x, y)},
                {"size", arr2(w, h)}, {"start_frame", start},
                {"duration_frames", duration}, {"screen_space", true},
                {"enable_3d", false}};
}

json textLayer(const std::string& id, const std::string& text, float x, float y,
               float w, float h, int size, const std::string& fill = "#111111",
               int start = 0, int duration = 120) {
    json l = layerBase(id, "text", x, y, w, h, start, duration);
    l["text"] = text;
    l["style"] = json{{"font", FONT}, {"font_size", size}, {"min_font_size", size},
                      {"max_font_size", size}, {"fit_mode", "shrink_only"},
                      {"fill", fill}};
    return l;
}

json rectLayer(const std::string& id, float x, float y, float w, float h,
               const json& fill, float opacity = 1.0f,
               const std::string& blend = "normal", int start = 0, int duration = 120) {
    json l = layerBase(id, "shape", x, y, w, h, start, duration);
    l["shape"] = json{{"type", "rect"}, {"fill", fill}};
    l["opacity"] = opacity;
    l["blend_mode"] = blend;
    return l;
}

json imageLayer(const std::string& id, const std::string& path, float x, float y,
                float w, float h, int start, int duration, float z = 0.0f,
                bool enable3d = false) {
    json l = layerBase(id, "image", x, y, w, h, start, duration);
    l["asset"] = path;
    l["fit"] = "cover";
    if (enable3d || z != 0.0f) {
        l["position"] = arr3(x, y, z);
        l["enable_3d"] = true;
        l["screen_space"] = false;
    }
    return l;
}

json key(int frame, double value) {
    return json{{"frame", frame}, {"value", value}};
}

json keyArr(int frame, const json& value) {
    return json{{"frame", frame}, {"value", value}};
}

json track(const std::string& property,
           std::initializer_list<std::pair<int, double>> keys,
           const std::string& easing = "linear") {
    json frames = json::array();
    for (const auto& [frame, value] : keys) frames.push_back(key(frame, value));
    return json{{"property", property}, {"easing", easing}, {"keyframes", frames}};
}

json trackArr(const std::string& property,
              std::initializer_list<std::pair<int, json>> keys,
              const std::string& easing = "linear") {
    json frames = json::array();
    for (const auto& [frame, value] : keys) frames.push_back(keyArr(frame, value));
    return json{{"property", property}, {"easing", easing}, {"keyframes", frames}};
}

json animation(std::initializer_list<json> tracks) {
    json list = json::array();
    for (const json& t : tracks) list.push_back(t);
    return json{{"tracks", list}};
}

json dropShadow(float radius, float dx, float dy, float alpha) {
    return json{{"type", "drop_shadow"}, {"radius", radius}, {"offset", arr2(dx, dy)},
                {"color", json::array({0.0, 0.0, 0.0, alpha})}};
}

json glow(float radius, float intensity, const json& color = rgba(255, 255, 255, 0.9f)) {
    return json{{"type", "glow"}, {"radius", radius}, {"intensity", intensity},
                {"color", color}};
}

json gaussian(float radius) {
    return json{{"type", "gaussian_blur"}, {"radius", radius}, {"passes", 2}};
}

json chromatic(float red, float blue, const std::string& mode = "velocity") {
    json e = json{{"type", "chromatic_aberration"}, {"red_offset", red},
                  {"blue_offset", blue}, {"mode", mode}};
    if (mode == "velocity") e["velocity"] = arr2(0.0f, 1.0f);
    return e;
}

json directional(float angle, float length, int samples) {
    return json{{"type", "directional_blur"}, {"angle", angle}, {"length", length},
                {"samples", samples}};
}

json cameraAt(float focusDistance, float fStop, float maxBlur, float cameraZ = 0.0f) {
    return json{
        {"type", "perspective"},
        {"position", arr3(0.0f, 0.0f, cameraZ)},
        {"rotation_deg", arr3(0.0f, 180.0f, 0.0f)},
        {"fov_deg", 45.0f},
        {"focal_length_mm", 35.0f},
        {"f_stop", fStop},
        {"near", 1.0f},
        {"far", 10000.0f},
        {"zoom", 1.0f},
        {"dof", json{{"enabled", true}, {"focus_distance", focusDistance},
                     {"max_blur", maxBlur}}},
    };
}

fs::path plansDir() {
    return sourceRoot() / "out/motion_design_stress/plans";
}

json normaliseDurations(json plan) {
    const int duration = plan["canvas"]["duration_frames"].get<int>();
    for (json& layer : plan["layers"]) {
        int start = layer.value("start_frame", 0);
        int frames = layer.value("duration_frames", duration);
        if (start < 0) start = 0;
        if (start >= duration) start = 0;
        frames = std::min(frames, duration - start);
        layer["start_frame"] = start;
        layer["duration_frames"] = std::max(1, frames);
    }
    return plan;
}

// RenderPlan V3 screen_space positions are top-left coordinates. The suite is
// authored in the centre convention (the same numbers used by the motion
// tests), so shift every screen-space layer, including its position tracks, by
// half its size. Scale still pivots around the layer centre, which is exactly
// what keeps test 02's left edge pinned.
json normaliseScreenSpace(json plan) {
    for (json& layer : plan["layers"]) {
        if (!layer.value("screen_space", false) || !layer.contains("size")) continue;
        // Text and particle layers keep centre coordinates in the V3
        // screen-space contract; images, shapes and colour plates use
        // top-left coordinates. Particle sampling is emitter-local around
        // (0,0), so subtracting half the box here moved a full-canvas emitter
        // into the top-left quadrant.
        const std::string type = layer.value("type", "");
        if (type == "text" || type == "particles") continue;
        const float halfW = layer["size"][0].get<float>() * 0.5f;
        const float halfH = layer["size"][1].get<float>() * 0.5f;
        if (layer.contains("position") && layer["position"].is_array() &&
            layer["position"].size() >= 2) {
            layer["position"][0] = layer["position"][0].get<float>() - halfW;
            layer["position"][1] = layer["position"][1].get<float>() - halfH;
        }
        if (!layer.contains("animation") || !layer["animation"].contains("tracks")) continue;
        for (json& track : layer["animation"]["tracks"]) {
            const std::string property = track.value("property", "");
            // Dotted `position.x/y` tracks are absolute; underscored
            // `position_x/y` tracks are additive offsets and must keep their
            // zero-based values.
            const float shift = property == "position.x" ? halfW
                              : property == "position.y" ? halfH : 0.0f;
            if (shift == 0.0f || !track.contains("keyframes")) continue;
            for (json& frame : track["keyframes"]) {
                if (frame["value"].is_number()) {
                    frame["value"] = frame["value"].get<float>() - shift;
                }
            }
        }
    }
    return plan;
}

fs::path writePlan(const std::string& name, json plan) {
    plan = normaliseScreenSpace(normaliseDurations(std::move(plan)));
    fs::create_directories(plansDir());
    const fs::path path = plansDir() / (name + ".plan.json");
    std::ofstream out(path);
    out << plan.dump(2) << '\n';
    check(static_cast<bool>(out), ("plan written: " + name).c_str());
    return path;
}

bool finiteJson(const json& value) {
    if (value.is_number_float()) return std::isfinite(value.get<double>());
    if (value.is_array()) {
        for (const auto& item : value) if (!finiteJson(item)) return false;
    } else if (value.is_object()) {
        for (const auto& [k, item] : value.items()) {
            (void)k;
            if (!finiteJson(item)) return false;
        }
    }
    return true;
}

float multiply(float backdrop, float source, float alpha) {
    // Premultiplied-aware Multiply with layer opacity: b * (1 - a + a*s).
    return backdrop * (1.0f - alpha + alpha * source);
}

float screen(float a, float b) { return 1.0f - (1.0f - a) * (1.0f - b); }

float bezierX(double t, double x1, double x2) {
    return 3.0 * (1.0 - t) * (1.0 - t) * t * x1 +
           3.0 * (1.0 - t) * t * t * x2 + t * t * t;
}

double bezierY(double t, double y1, double y2) {
    return 3.0 * (1.0 - t) * (1.0 - t) * t * y1 +
           3.0 * (1.0 - t) * t * t * y2 + t * t * t;
}

double easeOutCubicBezier(double x) {
    double lo = 0.0, hi = 1.0;
    for (int i = 0; i < 48; ++i) {
        const double mid = 0.5 * (lo + hi);
        if (bezierX(mid, 0.16, 0.3) < x) lo = mid; else hi = mid;
    }
    return bezierY(0.5 * (lo + hi), 1.0, 1.0);
}

// ---------------------------------------------------------------- module 1
void test01_multiply_paper() {
    section("01 Multiply over paper grain");
    json p = basePlan("01_multiply_paper_grain", 120);
    p["layers"].push_back(imageLayer("paper", asset("paper_grain_1920x1080.png"),
                                     W / 2.0f, H / 2.0f, W, H, 0, 120));
    p["layers"].push_back(textLayer("headline", "THE ARCHIVE", W / 2.0f, 500.0f,
                                    1600.0f, 260.0f, 150, "#000000"));
    json highlight = rectLayer("highlight", W / 2.0f, 560.0f, 1400.0f, 220.0f,
                               rgba(0, 168, 255, 1.0f), 0.8f, "multiply");
    p["layers"].push_back(highlight);

    check(highlight["blend_mode"] == "multiply", "highlight uses Multiply");
    checkNear(highlight["opacity"].get<float>(), 0.8f, 1e-6f, "highlight opacity is 80%");

    const float cyan = 168.0f / 255.0f;
    checkNear(multiply(0.0f, cyan, 0.8f), 0.0f, 1e-7f, "black text stays pure black");
    const float grainLow = multiply(0.58f, cyan, 0.8f);
    const float grainHigh = multiply(0.66f, cyan, 0.8f);
    check(grainHigh - grainLow > 0.05f, "paper grain survives under the highlight");
    const float linear = multiply(0.62f, cyan, 0.8f);
    const float gammaMistake = std::pow(0.62f, 2.2f) * cyan;
    check(linear > gammaMistake + 0.15f, "linear-path result is not the gamma-space result");
    writePlan("01_multiply_paper_grain", p);
}

void test02_anchor_scale() {
    section("02 off-centre anchor + asymmetric X scale");
    json p = basePlan("02_anchor_left_scale", 16);
    p["layers"].push_back(imageLayer("paper", asset("paper_texture_1920x1080.png"),
                                     W / 2.0f, H / 2.0f, W, H, 0, 16));
    const char* lines[] = {"A SHORT LINE", "A CONSIDERABLY LONGER SECOND LINE",
                           "THE THIRD LINE IS THE LONGEST OF THE THREE"};
    // Measured from the rendered Inter-Bold 44px layout, with 8px visual
    // padding. The old fixture used one 900px bar at x=360 for every row,
    // which covered only part of the two longer lines and started far left of
    // the first one.
    const float lefts[] = {810.0f, 543.0f, 465.0f};
    const float widths[] = {300.0f, 840.0f, 990.0f};

    for (int row = 0; row < 3; ++row) {
        const float left = lefts[row];
        const float baseWidth = widths[row];
        const float y = 420.0f + row * 160.0f;
        p["layers"].push_back(textLayer("line" + std::to_string(row), lines[row],
                                        W / 2.0f, y, 1500.0f, 90.0f, 44));
        json scaleKeys = json::array();
        json xKeys = json::array();
        for (int frame : {0, 5, 10, 15}) {
            const float s = static_cast<float>(frame) / 15.0f;
            // The layer is authored at its 100%-scale centre (left + w/2).
            // position_x is an additive offset, so the left edge stays at
            // `left` for every scale when offset = -w/2 + w*s/2.
            const float offsetX = -baseWidth * 0.5f + baseWidth * s * 0.5f;
            scaleKeys.push_back(keyArr(frame, arr3(s, 1.0f, 1.0f)));
            xKeys.push_back(key(frame, offsetX));
        }
        json highlight = rectLayer("highlight" + std::to_string(row),
                                   left + baseWidth * 0.5f, y,
                                   baseWidth, 84.0f, rgba(0, 168, 255, 0.9f),
                                   0.8f, "multiply");
        highlight["animation"] = json{{"tracks",
            json::array({json{{"property", "position_x"}, {"easing", "linear"},
                              {"keyframes", xKeys}},
                         json{{"property", "scale"}, {"easing", "linear"},
                              {"keyframes", scaleKeys}}})}};
        p["layers"].push_back(highlight);
    }

    for (int row = 0; row < 3; ++row) {
        const float left = lefts[row];
        const float baseWidth = widths[row];
        // The paper backdrop is layer 0; each text/highlight pair follows.
        const json& hi = p["layers"][row * 2 + 2];
        const float baseCentreX = hi["position"][0].get<float>();
        checkNear(baseCentreX, left + baseWidth * 0.5f, 1e-3f,
                  "highlight is authored at its 100%-scale centre");
        for (int frame : {0, 5, 10, 15}) {
            const float s = static_cast<float>(frame) / 15.0f;
            const json& xTrack = hi["animation"]["tracks"][0]["keyframes"];
            const int index = frame == 0 ? 0 : (frame == 5 ? 1 : (frame == 10 ? 2 : 3));
            const float offsetX = xTrack[index]["value"].get<float>();
            checkNear(baseCentreX + offsetX - baseWidth * s * 0.5f, left, 1e-3f,
                      "left edge stays pinned during expansion");
        }
        checkNear(hi["size"][0].get<float>(), baseWidth, 1e-6f,
                  "highlight width is the unabridged base width");
        checkNear(hi["position"][1].get<float>(), 420.0f + row * 160.0f, 1e-6f,
                  "vertical alignment is constant across rows");
    }
    check(p["layers"][0]["id"] == "paper", "paper backdrop precedes the highlights");
    const float ascender = 44.0f * 0.8f;
    const float descender = 44.0f * 0.2f;
    check(ascender + descender == 44.0f, "ascender+descender model is stable");
    writePlan("02_anchor_left_scale", p);
}

void test03_rack_focus() {
    section("03 3D rack focus across ten planes");
    json p = basePlan("03_rack_focus_3d", 60);
    for (int i = 0; i < 10; ++i) {
        json row = textLayer("row" + std::to_string(i),
                             "FOCUS PLANE " + std::to_string(i + 1),
                             W / 2.0f, 180.0f + i * 80.0f, 1500.0f, 70.0f, 26,
                             "#F5F0E6");
        row["position"] = arr3(W / 2.0f, 180.0f + i * 80.0f, -600.0f - i * 100.0f);
        row["enable_3d"] = true;
        row["screen_space"] = false;
        // The rack-focus camera looks at the text from the back of the 3D
        // card, so the MTSDF glyph quads are mirrored. Flip the layer X axis
        // once at authoring time; the engine keeps the projected card
        // double-sided and the DoF/rack-focus contract unchanged.
        row["scale"] = arr3(-1.0f, 1.0f, 1.0f);
        row["animation"] = animation({track("rotation_x", {{0, 45.0}, {59, 45.0}})});
        p["layers"].push_back(row);
    }

    json samples = json::array();
    for (int frame = 0; frame < 60; ++frame) {
        const float focus = 600.0f + 900.0f * static_cast<float>(frame) / 59.0f;
        samples.push_back(json{{"frame", frame},
                               {"camera", cameraAt(focus, 1.4f, 28.0f)}});
    }
    p["camera"] = cameraAt(600.0f, 1.4f, 28.0f);
    p["camera_samples"] = samples;

    check(p["layers"].size() == 10, "ten 3D text rows");
    check(samples.size() == 60, "one camera sample per frame");
    float previous = -1.0f;
    float maxStep = 0.0f;
    for (const json& sample : samples) {
        const json& camera = sample["camera"];
        check(camera["dof"]["enabled"] == true, "DoF enabled on every sample");
        checkNear(camera["f_stop"].get<float>(), 1.4f, 1e-6f, "aperture is constant");
        checkNear(camera["dof"]["max_blur"].get<float>(), 28.0f, 1e-6f,
                  "blur cap is constant");
        const float focus = camera["dof"]["focus_distance"].get<float>();
        if (previous >= 0.0f) {
            check(focus >= previous, "focus distance is monotonic");
            maxStep = std::max(maxStep, focus - previous);
        }
        previous = focus;
    }
    checkNear(previous, 1500.0f, 1e-3f, "rack lands on the far plane");
    check(maxStep < 16.0f, "focus has no discontinuous jump");
    check(finiteJson(p), "all camera samples are finite");
    writePlan("03_rack_focus_3d", p);
}

void test04_micro_text_pan() {
    section("04 micro-typography under a slow pan");
    std::string dense;
    for (int i = 0; i < 42; ++i) {
        dense += "ARCHIVAL SOURCE 1938 / REEL " + std::to_string(i + 1) +
                 " / FRAME-ACCURATE TRANSCRIPT\n";
    }
    json p = basePlan("04_micro_text_pan", 120);
    json block = textLayer("dense_block", dense, 400.0f, 300.0f, 760.0f, 760.0f, 12);
    block["animation"] = animation({
        track("position_x", {{0, 300.0}, {119, 500.0}}),
        track("position_y", {{0, 200.0}, {119, 500.0}}),
    });
    p["layers"].push_back(block);

    check(block["style"]["font_size"] == 12, "12 px equivalent body size");
    check(block["style"]["min_font_size"] == 12, "shrink cannot drop below 12 px");
    check(block["style"]["fit_mode"] == "shrink_only", "fit keeps the authored size");
    const float dx = 200.0f / 119.0f;
    const float dy = 300.0f / 119.0f;
    check(dx > 0.0f && dx < 2.0f, "horizontal pan advances sub-2 px per frame");
    check(dy > 0.0f && dy < 3.0f, "vertical pan advances sub-3 px per frame");
    const json& keys = block["animation"]["tracks"][0]["keyframes"];
    check(keys.size() == 2, "pan is one continuous segment");
    check(keys[0]["frame"] != keys[1]["frame"], "pan has no duplicate time key");
    writePlan("04_micro_text_pan", p);
}

void test05_multi_highlight() {
    section("05 multi-highlight self-blending");
    json p = basePlan("05_multi_highlight", 120);
    p["layers"].push_back(imageLayer("paper", asset("paper_texture_1920x1080.png"),
                                     W / 2.0f, H / 2.0f, W, H, 0, 120));
    p["layers"].push_back(textLayer("body", "TWO MARKS CROSS THE SAME LINE",
                                    W / 2.0f, 520.0f, 1500.0f, 180.0f, 62, "#000000"));
    json cyan = rectLayer("hl_cyan", 900.0f, 500.0f, 1000.0f, 180.0f,
                          rgba(0, 168, 255, 1.0f), 0.8f, "multiply");
    cyan["animation"] = animation({track("rotation_z", {{0, 12.0}, {119, 12.0}})});
    json yellow = rectLayer("hl_yellow", 1000.0f, 560.0f, 900.0f, 160.0f,
                            rgba(255, 214, 64, 1.0f), 0.8f, "multiply");
    yellow["animation"] = animation({track("rotation_z", {{0, -8.0}, {119, -8.0}})});
    p["layers"].push_back(cyan);
    p["layers"].push_back(yellow);

    const float backdrop = 0.62f;
    const float single = multiply(backdrop, 168.0f / 255.0f, 0.8f);
    // Yellow's blue channel is 64/255: that is the channel that darkens where
    // the two Multiply marks overlap. Multiplying by yellow's red (1.0) would
    // correctly leave the reference channel unchanged.
    const float overlap = multiply(single, 64.0f / 255.0f, 0.8f);
    check(overlap < single, "crossing highlights darken");
    check(overlap >= 0.0f && overlap <= 1.0f, "Multiply stays inside the channel range");
    check(single >= 0.0f && single <= 1.0f, "single highlight stays inside gamut");
    check(cyan["blend_mode"] == "multiply" && yellow["blend_mode"] == "multiply",
          "both marks use Multiply");
    writePlan("05_multi_highlight", p);
}

// ---------------------------------------------------------------- module 2
void test06_alpha_cutout() {
    section("06 premultiplied alpha on a complex cutout");
    json p = basePlan("06_alpha_cutout", 120);
    json background = imageLayer("background", asset("paper_texture_1920x1080.png"),
                                 W / 2.0f, H / 2.0f, W, H, 0, 120, -500.0f, true);
    background["animation"] = animation({track("position_x", {{0, W / 2.0f - 18.0f},
                                                             {119, W / 2.0f + 18.0f}})});
    background["screen_space"] = true;  // this case is 2.5D in screen space
    json subject = imageLayer("subject", asset("cutout_hair_1920x1080.png"),
                              W / 2.0f, H / 2.0f, W, H, 0, 120, 0.0f, true);
    subject["screen_space"] = true;
    subject["animation"] = animation({track("position_x", {{0, W / 2.0f + 24.0f},
                                                          {119, W / 2.0f - 24.0f}})});
    p["layers"].push_back(background);
    p["layers"].push_back(subject);

    const fs::path cutout = sourceRoot() / asset("cutout_hair_1920x1080.png");
    check(fs::exists(cutout), "alpha cutout asset exists");
    if (fs::exists(cutout)) {
        check(fs::file_size(cutout) > 50'000, "cutout carries a real soft-alpha rim");
    }
    check(subject["position"][2].get<float>() == 0.0f, "subject sits at Z=0");
    check(background["position"][2].get<float>() == -500.0f, "background sits at Z=-500");

    std::mt19937 rng(20261114);
    std::uniform_real_distribution<float> channel(0.0f, 1.0f);
    std::uniform_real_distribution<float> alphaDist(0.01f, 1.0f);
    float worst = 0.0f;
    for (int i = 0; i < 512; ++i) {
        const float c = channel(rng);
        const float a = alphaDist(rng);
        const float premultiplied = c * a;
        const float roundTrip = premultiplied / a;
        worst = std::max(worst, std::fabs(roundTrip - c));
    }
    check(worst < 1e-5f, "premultiply/unpremultiply round-trips");

    const float c = 0.70f;
    const float a = 0.5f;
    const float overWhite = c * a + 1.0f * (1.0f - a);
    const float overBlack = c * a + 0.0f * (1.0f - a);
    checkNear(overBlack, c * a, 1e-6f, "no black fringe on a black backdrop");
    check(overWhite > c * a && overWhite < 1.0f, "no white fringe on a white backdrop");
    writePlan("06_alpha_cutout", p);
}

void test07_parallax_dolly() {
    section("07 2.5D parallax + cubic-bezier dolly");
    json p = basePlan("07_parallax_dolly", 60);
    for (const float z : {-1000.0f, -200.0f, -100.0f}) {
        json plane = imageLayer("plane_" + std::to_string(static_cast<int>(-z)),
                                asset("paper_texture_1920x1080.png"),
                                200.0f, H / 2.0f, W, H, 0, 60, z, true);
        p["layers"].push_back(plane);
    }

    json samples = json::array();
    for (int frame = 0; frame < 60; ++frame) {
        const double eased = easeOutCubicBezier(frame / 59.0);
        const float cameraZ = static_cast<float>(-60.0 * eased);
        samples.push_back(json{{"frame", frame},
                               {"camera", cameraAt(600.0f, 4.0f, 12.0f, cameraZ)}});
    }
    p["camera"] = cameraAt(600.0f, 4.0f, 12.0f, 0.0f);
    p["camera_samples"] = samples;

    auto projected = [](double cameraZ, double worldZ) {
        const double distance = cameraZ - worldZ;  // both are negative
        return 1000.0 * 200.0 / distance;
    };
    const double nearShift = std::fabs(projected(0.0, -100.0) - projected(-60.0, -100.0));
    const double midShift = std::fabs(projected(0.0, -200.0) - projected(-60.0, -200.0));
    const double farShift = std::fabs(projected(0.0, -1000.0) - projected(-60.0, -1000.0));
    check(nearShift > midShift * 2.0, "near plane travels much farther than the mid plane");
    check(midShift > farShift * 2.0, "mid plane travels farther than the far plane");
    check(finiteJson(p), "parallax samples are finite");

    check(samples.size() == 60, "60 dolly samples");
    const float z0 = samples[0]["camera"]["position"][2].get<float>();
    const float z1 = samples[1]["camera"]["position"][2].get<float>();
    const float zEnd = samples[59]["camera"]["position"][2].get<float>();
    checkNear(z0, 0.0f, 1e-6f, "dolly starts at rest");
    checkNear(zEnd, -60.0f, 1e-4f, "dolly lands at its end");
    check(z1 < z0, "dolly moves forward");
    check(std::fabs(z1 - z0) >
          std::fabs(zEnd - samples[58]["camera"]["position"][2].get<float>()),
          "cubic ease-out decelerates");
    writePlan("07_parallax_dolly", p);
}

void test08_dim_blur() {
    section("08 background dimming + gaussian blur");
    json p = basePlan("08_dim_blur", 20);
    p["layers"].push_back(imageLayer("bg_sharp", asset("paper_texture_1920x1080.png"),
                                     W / 2.0f, H / 2.0f, W, H, 0, 20));
    json blurred = imageLayer("bg_blurred", asset("paper_texture_1920x1080.png"),
                              W / 2.0f, H / 2.0f, W * 1.2f, H * 1.2f, 0, 20);
    blurred["effects"] = json::array({gaussian(40.0f)});
    blurred["animation"] = animation({track("opacity", {{0, 0.0}, {19, 1.0}})});
    p["layers"].push_back(blurred);
    json matte = rectLayer("dim_matte", W / 2.0f, H / 2.0f, W, H,
                           json::array({0.0, 0.0, 0.0, 1.0}), 0.0f, "normal");
    matte["animation"] = animation({track("opacity", {{0, 0.0}, {19, 0.8232233}})});
    p["layers"].push_back(matte);

    const float ev = std::pow(2.0f, -2.5f);
    checkNear(ev, 0.1767767f, 1e-6f, "-2.5 EV is 0.1768 linear");
    checkNear(1.0f - ev, 0.8232233f, 1e-6f, "black matte alpha matches -2.5 EV");
    check(blurred["size"][0].get<float>() > W, "blur plate is oversized horizontally");
    check(blurred["size"][1].get<float>() > H, "blur plate is oversized vertically");
    check(blurred["effects"][0]["radius"] == 40.0f, "gaussian radius is 40 px");

    int levels8 = 0;
    float previous8 = -1.0f;
    for (int i = 0; i < 256; ++i) {
        const int quantized = static_cast<int>(std::lround((i / 255.0f) * 255.0f));
        if (quantized != static_cast<int>(previous8)) {
            ++levels8;
            previous8 = static_cast<float>(quantized);
        }
    }
    const int levels16 = 65536;
    check(levels16 > levels8 * 200, "16-bit grading has far more tonal levels than 8-bit");
    writePlan("08_dim_blur", p);
}

void test09_particles() {
    section("09 Add/Screen particle overlays");
    json p = basePlan("09_particles_add_screen", 120);
    const json ramp = json::array({
        json{{"position", 0.0}, {"color", json::array({1.0, 0.92, 0.76, 0.0})}},
        json{{"position", 0.35}, {"color", json::array({1.0, 0.78, 0.42, 0.85})}},
        json{{"position", 1.0}, {"color", json::array({1.0, 0.62, 0.22, 1.0})}},
    });
    auto emitter = [&](int count, const std::string& blend) {
        return json{{"count", count}, {"seed", 4242}, {"emitter_size", arr2(W, H)},
                    {"velocity_min", arr2(-18.0f, -28.0f)},
                    {"velocity_max", arr2(18.0f, 28.0f)},
                    {"lifetime", arr2(2.0f, 7.0f)}, {"size", arr2(3.0f, 16.0f)},
                    {"blend_mode", blend}, {"bokeh", true},
                    {"depth_range", arr2(0.1f, 1.0f)},
                    {"sprite_asset", asset("dust_bokeh_256.png")},
                    {"color_ramp", ramp}, {"emissive", 2.0f},
                    {"turbulence", 0.35f}, {"twinkle", 0.4f}};
    };
    json dust = layerBase("dust_add", "particles", W / 2.0f, H / 2.0f, W, H, 0, 120);
    dust["particle_emitter"] = emitter(500, "add");
    dust["blend_mode"] = "add";
    json bokeh = layerBase("bokeh_screen", "particles", W / 2.0f, H / 2.0f, W, H, 0, 120);
    bokeh["particle_emitter"] = emitter(200, "screen");
    bokeh["blend_mode"] = "screen";
    p["layers"].push_back(dust);
    p["layers"].push_back(bokeh);

    check(dust["particle_emitter"]["count"] == 500, "500 dust motes");
    check(dust["particle_emitter"]["blend_mode"] == "add", "dust uses Add");
    check(bokeh["particle_emitter"]["blend_mode"] == "screen", "bokeh uses Screen");
    check(fs::exists(sourceRoot() / asset("dust_bokeh_256.png")), "bokeh sprite exists");

    const float addAlpha = 0.6f + 0.5f;
    const float screenAlpha = screen(0.6f, 0.5f);
    check(addAlpha > 1.0f, "Add may exceed alpha 1 in the HDR composite");
    check(screenAlpha <= 1.0f, "Screen keeps alpha inside [0,1]");
    checkNear(screenAlpha, 0.8f, 1e-6f, "Screen alpha formula");
    writePlan("09_particles_add_screen", p);
    // Regression lock: normaliseScreenSpace must not shift particle layers
    // from their centred basis to top-left. Sampling is emitter-local around
    // (0,0); subtracting half the box put the whole emitter in the top-left
    // quadrant.
    const json emitted = normaliseScreenSpace(p);
    checkNear(emitted["layers"][0]["position"][0].get<float>(), W / 2.0f, 1e-3f,
              "particle layer keeps its centre X through screen-space normalisation");
    checkNear(emitted["layers"][0]["position"][1].get<float>(), H / 2.0f, 1e-3f,
              "particle layer keeps its centre Y through screen-space normalisation");
}

void test10_zsort() {
    section("10 z-sorting across intersecting planes");
    json p = basePlan("10_zsort_intersect", 120);
    // This case is 2.5D in screen space, like 06: without screen_space the
    // images are treated as world-space boxes at their top-left and the
    // cutout/paper land in the bottom-right quadrant.
    json background = imageLayer("bg", asset("paper_texture_1920x1080.png"),
                                 W / 2.0f, H / 2.0f, W, H, 0, 120, -500.0f, true);
    background["screen_space"] = true;
    p["layers"].push_back(background);
    json subject = imageLayer("subject", asset("cutout_hair_1920x1080.png"),
                              W / 2.0f, H / 2.0f, W, H, 0, 120, 0.0f, true);
    subject["screen_space"] = true;
    p["layers"].push_back(subject);
    for (int band = 0; band < 2; ++band) {
        json layer = layerBase("motes_" + std::to_string(band), "particles",
                               W / 2.0f, H / 2.0f, W, H, 0, 120);
        layer["particle_emitter"] = json{
            {"count", 300}, {"seed", 900 + band}, {"emitter_size", arr2(W, H)},
            {"velocity_min", arr2(-6.0f, -10.0f)}, {"velocity_max", arr2(6.0f, 10.0f)},
            {"lifetime", arr2(3.0f, 8.0f)}, {"size", arr2(2.0f, 7.0f)},
            {"environment", true},
            {"depth_range", band == 0 ? arr2(0.0f, 0.45f) : arr2(0.55f, 1.0f)},
            {"blend_mode", "screen"},
            {"sprite_asset", asset("dust_bokeh_256.png")},
            {"color_ramp", json::array({
                json{{"position", 0.0}, {"color", json::array({1.0, 1.0, 1.0, 0.0})}},
                json{{"position", 1.0}, {"color", json::array({1.0, 0.9, 0.8, 1.0})}}})}};
        p["layers"].push_back(layer);
    }

    const std::string bgId = p["layers"][0]["id"];
    const std::string subjectId = p["layers"][1]["id"];
    const std::string nearId = p["layers"][3]["id"];
    check(bgId == "bg" && subjectId == "subject", "background precedes the cutout");
    check(nearId == "motes_1", "near motes are authored in front of the subject");
    check(p["layers"][2]["particle_emitter"]["depth_range"][1].get<float>() <
          p["layers"][3]["particle_emitter"]["depth_range"][0].get<float>(),
          "the two depth bands do not overlap");
    check(p["layers"][2]["particle_emitter"]["environment"] == true,
          "particles use environment depth for per-particle sorting");
    writePlan("10_zsort_intersect", p);
}

// ---------------------------------------------------------------- module 3
void test11_logo_rotation() {
    section("11 360-degree Y rotation + lighting");
    json p = basePlan("11_logo_rotate", 120);
    json logo = imageLayer("logo", asset("logo_field_notes_1024.png"),
                           960.0f, 540.0f, 620.0f, 620.0f, 0, 120, 0.0f, true);
    logo["screen_space"] = true;  // no camera in this lighting study
    logo["animation"] = animation({track("rotation_y",
                                         {{0, 0.0}, {30, 90.0}, {60, 180.0},
                                          {90, 270.0}, {120, 360.0}})});
    p["layers"].push_back(logo);
    p["lighting_rig"] = json{
        {"key_direction", arr3(0.3f, -0.7f, 0.6f)},
        {"key_color", json::array({1.0, 0.95, 0.9, 1.0})},
        {"key_intensity", 3.2f},
        {"ambient_color", json::array({0.35, 0.42, 0.5, 1.0})},
        {"ambient_intensity", 0.55f},
        {"rim_enabled", true},
        {"rim_color", json::array({0.2, 0.65, 1.0, 1.0})},
        {"rim_intensity", 1.4f},
        {"rim_power", 3.0f}};

    const json& keys = logo["animation"]["tracks"][0]["keyframes"];
    check(keys.size() == 5, "five rotation keys");
    checkNear(keys.front()["value"].get<float>(), 0.0f, 1e-6f, "rotation starts at 0");
    checkNear(keys.back()["value"].get<float>(), 360.0f, 1e-6f, "rotation reaches 360");
    for (size_t i = 1; i < keys.size(); ++i) {
        checkNear(keys[i]["value"].get<float>() - keys[i - 1]["value"].get<float>(),
                  90.0f, 1e-6f, "rotation advances in 90-degree steps");
    }
    check(p["lighting_rig"]["rim_enabled"] == true, "rim light is authored");
    writePlan("11_logo_rotate", p);
}

void test12_overshoot() {
    section("12 spring overshoot 112% -> 100%");
    json p = basePlan("12_overshoot", 13);
    json backdrop = layerBase("backdrop", "color", W / 2.0f, H / 2.0f, W, H, 0, 13);
    backdrop["color"] = json::array({0.04, 0.05, 0.06, 1.0});
    p["layers"].push_back(backdrop);
    json badge = rectLayer("badge", 640.0f, 400.0f, 640.0f, 180.0f,
                           json::array({1.0, 1.0, 1.0, 1.0}), 0.98f, "normal");
    badge["effects"] = json::array({dropShadow(36.0f, 18.0f, 24.0f, 0.45f)});
    badge["animation"] = animation({trackArr("scale", {
        {0, arr3(0.0f, 0.0f, 1.0f)},
        {4, arr3(0.90f, 0.90f, 1.0f)},
        {8, arr3(1.12f, 1.12f, 1.0f)},
        {12, arr3(1.0f, 1.0f, 1.0f)}}, "out_cubic")});
    p["layers"].push_back(badge);
    json amount = textLayer("amount", "$10,000", 640.0f, 400.0f, 560.0f, 100.0f,
                            52, "#111111", 0, 13);
    amount["animation"] = animation({track("opacity", {{0, 0.0}, {3, 1.0}, {12, 1.0}})});
    p["layers"].push_back(amount);

    const json& keys = badge["animation"]["tracks"][0]["keyframes"];
    check(keys.size() == 4, "four scale keys");
    checkNear(keys[2]["value"][0].get<float>(), 1.12f, 1e-6f, "peak is 112 percent");
    checkNear(keys.back()["value"][0].get<float>(), 1.0f, 1e-6f, "settle is exactly 100 percent");
    check(keys.back()["frame"] == 12, "settle lands on frame 12");
    bool monotonicAfterPeak = true;
    for (size_t i = 3; i < keys.size(); ++i) {
        if (keys[i]["value"][0].get<float>() > keys[i - 1]["value"][0].get<float>()) {
            monotonicAfterPeak = false;
        }
    }
    check(monotonicAfterPeak, "no residual oscillation after the overshoot");
    writePlan("12_overshoot", p);
}

void test13_motion_blur() {
    section("13 vector motion blur 180 vs 360 shutter");
    auto build = [](const std::string& id, float shutter, int samples) {
        json p = basePlan(id, 6);
        json badge = rectLayer("badge", 960.0f, 540.0f, 560.0f, 160.0f,
                               json::array({1.0, 1.0, 1.0, 1.0}), 1.0f, "normal");
        // Base centre is x=960; position_x is additive. Offsets move the
        // centre from 1900 (off right) to 100 (off left).
        badge["animation"] = animation({track("position_x",
                                              {{0, 940.0}, {5, -860.0}})});
        p["layers"].push_back(badge);
        p["temporal_motion_blur"] = json{{"shutter_angle", shutter}, {"samples", samples}};
        return p;
    };
    json a = build("13a_motion_blur_180", 180.0f, 8);
    json b = build("13b_motion_blur_360", 360.0f, 16);
    check(a["temporal_motion_blur"]["shutter_angle"] == 180.0f, "shutter A is 180");
    check(b["temporal_motion_blur"]["shutter_angle"] == 360.0f, "shutter B is 360");
    check(b["temporal_motion_blur"]["shutter_angle"].get<float>() ==
          a["temporal_motion_blur"]["shutter_angle"].get<float>() * 2.0f,
          "360 is twice the 180 exposure");
    check(b["temporal_motion_blur"]["samples"] == 16, "360 uses 16 sub-frames");
    check(b["temporal_motion_blur"]["samples"].get<int>() ==
          a["temporal_motion_blur"]["samples"].get<int>() * 2,
          "sub-frame count doubles with the shutter");
    writePlan("13a_motion_blur_180", a);
    writePlan("13b_motion_blur_360", b);
}

void test14_parenting() {
    section("14 parent-child non-uniform scale");
    json p = basePlan("14_parent_scale", 21);
    json group = rectLayer("group", 960.0f, 800.0f, 600.0f, 160.0f,
                           json::array({1.0, 1.0, 1.0, 1.0}), 1.0f, "normal");
    group["animation"] = animation({trackArr("scale", {
        {0, arr3(1.0f, 1.0f, 1.0f)},
        {20, arr3(1.4f, 0.9f, 1.0f)}}, "in_out_cubic")});
    p["layers"].push_back(group);

    json child = textLayer("amount", "$10,000", 960.0f, 800.0f, 560.0f, 100.0f,
                           52, "#111111", 0, 21);
    child["parent"] = "group";
    child["animation"] = animation({trackArr("scale", {
        {0, arr3(1.0f, 1.0f, 1.0f)}, {20, arr3(1.0f, 1.0f, 1.0f)}})});
    p["layers"].push_back(child);

    json compensated = textLayer("amount_compensated", "$10,000", 960.0f, 800.0f,
                                 560.0f, 100.0f, 52, "#111111", 0, 21);
    compensated["parent"] = "group";
    compensated["animation"] = animation({trackArr("scale", {
        {0, arr3(1.0f, 1.0f, 1.0f)},
        {20, arr3(1.0f / 1.4f, 1.0f / 0.9f, 1.0f)}})});
    p["layers"].push_back(compensated);

    const float parentX = 1.4f, parentY = 0.9f;
    checkNear(parentX, 1.4f, 1e-6f, "parent widens by 40 percent");
    checkNear(parentY, 0.9f, 1e-6f, "parent height compresses by 10 percent");
    checkNear(parentX * 1.0f, 1.4f, 1e-6f, "uncompensated child inherits X stretch");
    checkNear(parentY * 1.0f, 0.9f, 1e-6f, "uncompensated child inherits Y squash");
    checkNear(parentX * (1.0f / 1.4f), 1.0f, 1e-5f, "compensated X is uniform");
    checkNear(parentY * (1.0f / 0.9f), 1.0f, 1e-5f, "compensated Y is uniform");
    check(child["parent"] == "group" && compensated["parent"] == "group",
          "both text layers are parented to the badge");
    writePlan("14_parent_scale", p);
}

void test15_shadow_glow() {
    section("15 dynamic drop shadow + composite glow");
    json p = basePlan("15_shadow_glow", 120);
    const json rotation = animation({track("rotation_y",
                                           {{0, 0.0}, {30, 90.0}, {60, 180.0},
                                            {90, 270.0}, {120, 360.0}})});
    json shadow = imageLayer("logo_shadow", asset("logo_field_notes_1024.png"),
                             980.0f, 564.0f, 620.0f, 620.0f, 0, 120, -20.0f, true);
    shadow["screen_space"] = true;
    shadow["opacity"] = 0.55f;
    shadow["effects"] = json::array({dropShadow(80.0f, 30.0f, 40.0f, 0.55f)});
    shadow["animation"] = rotation;
    json logo = imageLayer("logo", asset("logo_field_notes_1024.png"),
                           960.0f, 540.0f, 620.0f, 620.0f, 0, 120, 0.0f, true);
    logo["screen_space"] = true;
    logo["effects"] = json::array({glow(90.0f, 0.8f,
                                        rgba(0, 168, 255, 0.85f))});
    logo["animation"] = rotation;
    p["layers"].push_back(shadow);
    p["layers"].push_back(logo);

    check(shadow["animation"] == logo["animation"],
          "shadow follows the same rotation curve as the logo");
    check(shadow["effects"][0]["radius"] == 80.0f, "soft shadow radius is 80 px");
    check(logo["effects"][0]["type"] == "glow", "logo carries an outer glow");
    checkNear(logo["effects"][0]["intensity"].get<float>(), 0.8f, 1e-6f,
              "glow intensity is 0.8");
    check(shadow["position"][2].get<float>() < logo["position"][2].get<float>(),
          "shadow plate sits behind the logo");
    writePlan("15_shadow_glow", p);
}

// ---------------------------------------------------------------- module 4
void test16_velocity_continuity() {
    section("16 velocity continuity across a six-frame cut");
    json a = basePlan("16a_whip_out", 4);
    json outLayer = rectLayer("card_a", 960.0f, 540.0f, 600.0f, 340.0f,
                              json::array({0.1, 0.6, 0.8, 1.0}), 1.0f, "normal");
    // Base centre is y=540; offsets are absolute-centre minus 540.
    outLayer["animation"] = animation({track("position_y", {
        {0, -540.0}, {1, -536.667}, {2, -473.333}, {3, 360.0}})});
    a["layers"].push_back(outLayer);

    json b = basePlan("16b_whip_in", 7);
    json inLayer = rectLayer("card_b", 960.0f, 540.0f, 600.0f, 340.0f,
                             json::array({0.8, 0.4, 0.2, 1.0}), 1.0f, "normal",
                             3, 4);
    inLayer["animation"] = animation({track("position_y", {
        {3, 360.0}, {4, 993.333}, {5, 1226.667}, {6, 1260.0}})});
    b["layers"].push_back(inLayer);

    const float velocityOut = 3.0f * 900.0f;  // d/dt 900*t^3 at t=1
    const float velocityIn = 3.0f * 900.0f;    // d/dt 900+900*(1-(1-t)^3) at t=0
    checkNear(velocityOut, velocityIn, 1e-6f,
              "outgoing and incoming analytic velocities match");
    checkNear(a["layers"][0]["animation"]["tracks"][0]["keyframes"][3]["value"].get<float>(),
              b["layers"][0]["animation"]["tracks"][0]["keyframes"][0]["value"].get<float>(),
              1e-6f, "position is continuous at the cut");
    const float linearOut = 900.0f / 3.0f;
    check(std::fabs(linearOut - velocityIn) > 100.0f,
          "a linear ramp would produce a visible velocity mismatch");
    writePlan("16a_whip_out", a);
    writePlan("16b_whip_in", b);
}

void test17_directional_blur() {
    section("17 directional blur at 150% frame height");
    json p = basePlan("17_directional_blur_edge", 60);
    json edgePlate = imageLayer("edge_plate", asset("paper_texture_1920x1080.png"),
                                960.0f, 540.0f, W, 1620.0f, 0, 60, -20.0f, true);
    edgePlate["screen_space"] = true;
    json source = imageLayer("source", asset("paper_texture_1920x1080.png"),
                             960.0f, 540.0f, W, H, 0, 60, 0.0f, true);
    source["screen_space"] = true;
    source["effects"] = json::array({directional(90.0f, 1620.0f, 32)});
    p["layers"].push_back(edgePlate);
    p["layers"].push_back(source);

    const json& effect = source["effects"][0];
    checkNear(effect["length"].get<float>(), H * 1.5f, 1e-3f,
              "blur length is 150 percent of frame height");
    checkNear(effect["angle"].get<float>(), 90.0f, 1e-6f, "blur runs vertically");
    check(effect["samples"] == 32, "32 directional samples");
    check(edgePlate["size"][1].get<float>() >= effect["length"].get<float>(),
          "oversized plate covers the full blur kernel");

    const int n = 200, edge = 50, radius = 80;
    std::vector<float> row(n, 0.0f);
    for (int i = 0; i < edge; ++i) row[i] = 1.0f;
    auto sample = [&](int index, bool clamp) {
        if (index < 0) return clamp ? row[0] : 0.0f;
        if (index >= n) return clamp ? row[n - 1] : 0.0f;
        return row[index];
    };
    auto blur = [&](int centre, bool clamp) {
        float sum = 0.0f;
        for (int k = -radius; k <= radius; ++k) sum += sample(centre + k, clamp);
        return sum / (2 * radius + 1);
    };
    const float clampedEdge = blur(0, true);
    const float zeroEdge = blur(0, false);
    check(clampedEdge > zeroEdge + 0.2f,
          "clamped edge sampling preserves luminance; zero padding does not");
    check(zeroEdge < 0.5f, "zero padding visibly darkens the top band");
    writePlan("17_directional_blur_edge", p);
}

void test18_uhd60() {
    section("18 4K60 stress with every effect live");
    const auto started = std::chrono::steady_clock::now();
    json p = basePlan("18_uhd60_stress", 600, 3840, 2160, 60);
    p["layers"].push_back(imageLayer("paper_4k", asset("paper_grain_3840x2160.png"),
                                     1920.0f, 1080.0f, 3840.0f, 2160.0f, 0, 600));
    json blurred = imageLayer("blurred_4k", asset("paper_grain_3840x2160.png"),
                              1920.0f, 1080.0f, 4608.0f, 2592.0f, 0, 600);
    blurred["effects"] = json::array({gaussian(60.0f)});
    p["layers"].push_back(blurred);
    p["layers"].push_back(imageLayer("subject_4k", asset("cutout_hair_1920x1080.png"),
                                     1920.0f, 1080.0f, 3840.0f, 2160.0f, 0, 600,
                                     0.0f, true));
    json title = textLayer("title_4k", "THE ARCHIVE / 4K60", 1920.0f, 420.0f,
                           3200.0f, 360.0f, 160, "#F5F0E6", 0, 600);
    title["effects"] = json::array({chromatic(14.0f, 14.0f)});
    p["layers"].push_back(title);
    for (int band = 0; band < 2; ++band) {
        json motes = layerBase("motes_" + std::to_string(band), "particles",
                               1920.0f, 1080.0f, 3840.0f, 2160.0f, 0, 600);
        motes["particle_emitter"] = json{
            {"count", 500}, {"seed", 77 + band}, {"emitter_size", arr2(3840.0f, 2160.0f)},
            {"velocity_min", arr2(-12.0f, -20.0f)},
            {"velocity_max", arr2(12.0f, 20.0f)},
            {"lifetime", arr2(2.0f, 8.0f)}, {"size", arr2(3.0f, 14.0f)},
            {"environment", true}, {"depth_range", arr2(0.1f, 1.0f)},
            {"blend_mode", band == 0 ? "add" : "screen"},
            {"sprite_asset", asset("dust_bokeh_256.png")},
            {"bokeh", true}, {"emissive", 1.6f}};
        p["layers"].push_back(motes);
    }
    json logo = imageLayer("logo_4k", asset("logo_field_notes_1024.png"),
                           1920.0f, 1080.0f, 1240.0f, 1240.0f, 0, 600, 0.0f, true);
    logo["screen_space"] = true;
    logo["animation"] = animation({track("rotation_y",
                                         {{0, 0.0}, {600, 360.0}})});
    logo["effects"] = json::array({glow(120.0f, 0.9f), dropShadow(100.0f, 40.0f, 50.0f, 0.5f)});
    p["layers"].push_back(logo);
    json matte = rectLayer("dim_4k", 1920.0f, 1080.0f, 3840.0f, 2160.0f,
                           json::array({0.0, 0.0, 0.0, 1.0}), 0.35f, "normal");
    p["layers"].push_back(matte);

    json samples = json::array();
    for (int frame = 0; frame < 600; frame += 2) {
        const float focus = 800.0f + 1000.0f * static_cast<float>(frame) / 599.0f;
        samples.push_back(json{{"frame", frame},
                               {"camera", cameraAt(focus, 2.8f, 36.0f)}});
    }
    p["camera"] = cameraAt(800.0f, 2.8f, 36.0f);
    p["camera_samples"] = samples;
    p["temporal_motion_blur"] = json{{"shutter_angle", 180.0f}, {"samples", 8}};
    p["layers"][0]["effects"] = json::array({directional(0.0f, 1200.0f, 24)});

    const auto elapsed = std::chrono::duration_cast<std::chrono::milliseconds>(
        std::chrono::steady_clock::now() - started).count();
    check(p["canvas"]["width"] == 3840 && p["canvas"]["height"] == 2160, "canvas is UHD");
    check(p["canvas"]["fps_num"] == 60, "60 fps");
    check(p["canvas"]["duration_frames"] == 600, "600 frames = 10 seconds");
    check(3840LL * 2160LL == 8'294'400LL, "8.29 megapixels per frame");
    check(p["layers"].size() >= 8, "stress plan keeps every layer family live");
    check(samples.size() == 300, "300 camera samples over the 10 seconds");
    check(p["layers"][4]["particle_emitter"]["count"] == 500 ||
          p["layers"][5]["particle_emitter"]["count"] == 500,
          "500-mote emitter is present");
    check(finiteJson(p), "4K plan has no non-finite value");
    check(elapsed < 5000, "plan construction stays under five seconds");
    const size_t bytes = p.dump().size();
    check(bytes < 8'000'000, "plan JSON stays below 8 MB");
    std::printf("  plan bytes: %zu, construction: %lld ms\n", bytes,
                static_cast<long long>(elapsed));
    writePlan("18_uhd60_stress", p);
}

void test19_chromatic() {
    section("19 chromatic aberration during the whip");
    json p = basePlan("19_chromatic_whip", 6);
    json card = textLayer("interview_word", "INTERVIEW", 960.0f, 540.0f,
                          1500.0f, 260.0f, 150, "#F5F0E6", 0, 6);
    card["effects"] = json::array({chromatic(-18.0f, 18.0f, "velocity")});
    card["animation"] = animation({track("position_x", {
        {0, 1900.0}, {1, 1600.0}, {2, 1300.0}, {3, 960.0},
        {4, 620.0}, {5, 300.0}})});
    p["layers"].push_back(card);

    const json& effect = card["effects"][0];
    check(effect["mode"] == "velocity", "aberration follows the velocity mode");
    check(effect["velocity"] == json::array({0.0f, 1.0f}),
          "aberration axis is the vertical whip axis");
    check(effect["red_offset"].get<float>() < 0.0f &&
          effect["blue_offset"].get<float>() > 0.0f,
          "red and blue separate in opposite directions");
    check(effect["red_offset"].get<float>() == -effect["blue_offset"].get<float>(),
          "channel split is symmetric");

    auto offsetAt = [](int frame) {
        const double t = frame / 5.0;
        const double velocity = -960.0 * (1.0 - t) * (1.0 - t);
        return 18.0 * std::fabs(velocity) / 960.0;
    };
    checkNear(static_cast<float>(offsetAt(0)), 18.0f, 1e-5f,
              "aberration is maximal at the cut");
    checkNear(static_cast<float>(offsetAt(3)), 18.0f * 0.16f, 1e-5f,
              "aberration decays through the landing");
    checkNear(static_cast<float>(offsetAt(5)), 0.0f, 1e-7f,
              "aberration is exactly zero on the landing frame");
    writePlan("19_chromatic_whip", p);
}

void test20_codecs() {
    section("20 multi-codec Rec.709 consistency");
    auto scene = [](const std::string& id) {
        json p = basePlan(id, 120);
        p["layers"].push_back(imageLayer("paper", asset("paper_grain_1920x1080.png"),
                                         W / 2.0f, H / 2.0f, W, H, 0, 120));
        json mark = rectLayer("highlight", W / 2.0f, 560.0f, 1400.0f, 220.0f,
                              rgba(0, 168, 255, 0.9f), 0.8f, "multiply");
        p["layers"].push_back(mark);
        p["layers"].push_back(textLayer("callout", "$10,000", 1280.0f, 760.0f,
                                        560.0f, 100.0f, 52, "#111111"));
        return p;
    };
    json h264 = scene("20a_h264_rec709");
    h264["output"] = json{{"path", "out/motion_design_stress/render/20a_h264_rec709.mp4"},
                          {"format", "mp4"}, {"codec", "h264"},
                          {"color_space", "rec709"}};
    json h265 = scene("20b_h265_rec709");
    h265["output"] = json{{"path", "out/motion_design_stress/render/20b_h265_rec709.mkv"},
                          {"format", "mkv"}, {"codec", "h265"},
                          {"color_space", "rec709"}};
    json lossless = scene("20c_lossless_rec709");
    lossless["output"] = json{
        {"path", "out/motion_design_stress/render/20c_lossless/frame_####.png"},
        {"format", "png_sequence"}, {"color_space", "rec709"}};

    check(h264["output"]["format"] == "mp4" && h264["output"]["codec"] == "h264",
          "delivery plan is MP4/H.264");
    check(h265["output"]["format"] == "mkv" && h265["output"]["codec"] == "h265",
          "delivery plan is MKV/H.265");
    check(lossless["output"]["format"] == "png_sequence",
          "lossless reference is a PNG sequence");
    check(h264["output"]["color_space"] == "rec709" &&
          h265["output"]["color_space"] == "rec709" &&
          lossless["output"]["color_space"] == "rec709",
          "all three outputs declare Rec.709");
    check(h264["layers"].dump() == h265["layers"].dump() &&
          h264["layers"].dump() == lossless["layers"].dump(),
          "all codecs render byte-identical layer descriptions");
    const float cyan = 168.0f / 255.0f;
    checkNear(cyan, 0.6588235f, 1e-6f, "cyan is authored in the same linear value");
    writePlan("20a_h264_rec709", h264);
    writePlan("20b_h265_rec709", h265);
    writePlan("20c_lossless_rec709", lossless);
}

}// namespace

int main() {
    std::printf("motion-design stress suite: 20 cases, 4 modules\n");
    test01_multiply_paper();
    test02_anchor_scale();
    test03_rack_focus();
    test04_micro_text_pan();
    test05_multi_highlight();

    test06_alpha_cutout();
    test07_parallax_dolly();
    test08_dim_blur();
    test09_particles();
    test10_zsort();

    test11_logo_rotation();
    test12_overshoot();
    test13_motion_blur();
    test14_parenting();
    test15_shadow_glow();

    test16_velocity_continuity();
    test17_directional_blur();
    test18_uhd60();
    test19_chromatic();
    test20_codecs();

    std::printf("\nplans: %s\n", plansDir().string().c_str());
    return chrononmotion_test::report();
}
