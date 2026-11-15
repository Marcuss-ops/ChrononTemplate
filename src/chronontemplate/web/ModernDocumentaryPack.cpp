#include "chronontemplate/web/ModernDocumentaryPack.hpp"

#include "chronontemplate/web/WebFontMeasure.hpp"

#include <algorithm>
#include <array>
#include <cmath>
#include <stdexcept>
#include <string>
#include <utility>
#include <vector>

namespace chronontemplate::web {
namespace {

using Json = nlohmann::json;
using shot::measuredTextWidth;

constexpr int kW = 1920;
constexpr int kH = 1080;
constexpr int kFps = 30;
constexpr float kCameraDistance = 1158.06f;
constexpr const char* kInterBold = "ChrononTemplate/assets/fonts/Inter-Bold.ttf";
constexpr const char* kInterBlack = "ChrononTemplate/assets/fonts/Inter-Black.ttf";
constexpr const char* kInterMedium = "ChrononTemplate/assets/fonts/Inter-Medium.ttf";
constexpr const char* kInterRegular = "ChrononTemplate/assets/fonts/Inter-Regular.ttf";
constexpr const char* kPlayfairBold = "ChrononTemplate/assets/fonts/PlayfairDisplay-Bold.ttf";
constexpr const char* kPlayfair = "ChrononTemplate/assets/fonts/PlayfairDisplay.ttf";
constexpr const char* kMono = "ChrononTemplate/assets/fonts/LiberationMono-Bold.ttf";
constexpr const char* kAstronaut = "ChrononTemplate/assets/astronaut_camera_transition_v1/humanity-astronaut-matte.png";
constexpr const char* kAstronautCutout =
    "ChrononTemplate/assets/astronaut_camera_transition_v1/humanity-astronaut-cutout-v2.png";
constexpr const char* kBanknote = "ChrononTemplate/assets/modern_documentary/banknote.png";

[[noreturn]] void fail(const std::string& message) {
    throw std::invalid_argument("ModernDocumentarySpec: " + message);
}

Json rgba(const std::string& hex, float alpha = 1.f) {
    if (hex.size() != 7 || hex.front() != '#')
        throw std::invalid_argument("ModernDocumentaryPack: color must be #RRGGBB");
    const unsigned value = static_cast<unsigned>(std::stoul(hex.substr(1), nullptr, 16));
    return Json::array({((value >> 16) & 255U) / 255.0, ((value >> 8) & 255U) / 255.0,
                        (value & 255U) / 255.0, static_cast<double>(alpha)});
}

float wireY(float topDownY) { return static_cast<float>(kH) - topDownY; }

Json key(int frame, double value) {
    return Json{{"frame", frame}, {"value", value}};
}

Json track(const std::string& property, Json keys, const std::string& easing = "linear") {
    return Json{{"property", property}, {"easing", easing}, {"keyframes", std::move(keys)}};
}

/// Left-to-right marker reveal. scale_x and position_x are coupled so the
/// authored left edge stays pinned while the right edge travels.
Json sweepTracks(float width, int begin, int span) {
    Json scaleKeys = Json::array();
    Json positionKeys = Json::array();
    scaleKeys.push_back(key(0, 0.0));
    scaleKeys.push_back(key(begin, 0.0));
    scaleKeys.push_back(key(begin + span, 1.0));
    scaleKeys.push_back(key(begin + span + 1, 1.0));
    positionKeys.push_back(key(0, -width * 0.5));
    positionKeys.push_back(key(begin, -width * 0.5));
    positionKeys.push_back(key(begin + span, 0.0));
    positionKeys.push_back(key(begin + span + 1, 0.0));
    return Json::array({
        track("opacity", Json::array({key(0, 0.0), key(begin, 0.0),
                                      key(begin + 1, 1.0), key(begin + span + 1, 1.0)})),
        track("scale_x", std::move(scaleKeys), "in_out_cubic"),
        track("position_x", std::move(positionKeys), "in_out_cubic")});
}

Json effectNoise(float amount, unsigned seed, float size = 1.f, bool animated = true) {
    return Json{{"type", "noise"}, {"amount", amount}, {"seed", seed}, {"size", size},
                {"animated", animated}};
}

Json effectVignette(float amount, float radius = 0.72f, float softness = 0.58f) {
    return Json{{"type", "vignette"}, {"amount", amount}, {"radius", radius},
                {"softness", softness}};
}

Json effectGlow(float radius, float intensity, const std::string& color) {
    return Json{{"type", "glow"}, {"radius", radius}, {"intensity", intensity},
                {"color", rgba(color, 1.f)}};
}

Json effectBloom(float threshold, float radius, float intensity) {
    return Json{{"type", "bloom"}, {"threshold", threshold}, {"radius", radius},
                {"intensity", intensity}};
}

Json effectScanlines(float spacing, float amount, float phase = 0.f) {
    return Json{{"type", "scanlines"}, {"spacing_px", spacing}, {"amount", amount},
                {"phase", phase}};
}

Json effectChromatic(float red, float blue) {
    return Json{{"type", "chromatic_aberration"}, {"red_offset", red},
                {"blue_offset", blue}};
}

Json effectMeshGlitch(int cols = 8, int rows = 8, float amount = 0.012f) {
    // The decoder expects cols*rows x/y pairs, not one scalar per grid point.
    Json offsets = Json::array();
    for (int row = 0; row < rows; ++row) {
        const float sign = (row % 2 == 0) ? 1.f : -1.f;
        for (int col = 0; col < cols; ++col) {
            offsets.push_back(sign * amount * (1.f + static_cast<float>(col % 3) * 0.2f));
            offsets.push_back(0.f);
        }
    }
    return Json{{"type", "mesh_warp"}, {"cols", cols}, {"rows", rows},
                {"smoothness", 0.f}, {"offsets", std::move(offsets)}};
}

Json effectLens(float curvature, float scale = 1.08f) {
    return Json{{"type", "lens_distortion"}, {"curvature", curvature},
                {"scale", scale}, {"center", Json::array({0.5, 0.5})}};
}

Json effectDirectional(float angle, float length, int samples) {
    return Json{{"type", "directional_blur"}, {"angle", angle}, {"length", length},
                {"samples", samples}};
}

Json shape(const std::string& id, const std::string& type, float left, float top,
           float width, float height, const std::string& color, float alpha,
           float z, Json animation = Json::array(), const std::string& blend = "normal") {
    // Shape layers are center-relative, unlike text layers: the renderer maps
    // screen_x = 960 + position.x and screen_y = 540 - position.y.
    Json layer = {{"id", id}, {"type", "shape"}, {"enable_3d", true},
                  {"position", Json::array({left + width * 0.5f - 960.f,
                                            540.f - (top + height * 0.5f), z})},
                  {"size", Json::array({width, height})},
                  {"start_frame", 0},
                  {"shape", {{"type", type}, {"fill", rgba(color, alpha)}}}};
    if (!animation.empty()) layer["animation"] = Json{{"tracks", std::move(animation)}};
    if (blend != "normal") layer["blend_mode"] = blend;
    return layer;
}

Json rect(const std::string& id, float left, float top, float width, float height,
          const std::string& color, float alpha, float z, Json animation = Json::array(),
          const std::string& blend = "normal") {
    return shape(id, "rect", left, top, width, height, color, alpha, z,
                 std::move(animation), blend);
}

Json rounded(const std::string& id, float left, float top, float width, float height,
             float radius, const std::string& color, float alpha, float z,
             Json animation = Json::array()) {
    Json layer = shape(id, "rounded_rect", left, top, width, height, color, alpha, z,
                       std::move(animation));
    layer["shape"]["radius"] = radius;
    return layer;
}

Json ellipse(const std::string& id, float left, float top, float width, float height,
             const std::string& color, float alpha, float z) {
    return shape(id, "ellipse", left, top, width, height, color, alpha, z);
}

Json text(const std::string& id, const std::string& value, float left, float top,
          float size, const char* font, const std::string& color, int duration,
          float z, Json animation = Json::array(), Json animators = Json::array(),
          float opacity = 1.f, const std::string& blend = "normal") {
    const float content = std::max(10.f, measuredTextWidth(value, size, font));
    const float width = content * 1.15f;
    const float height = size * 1.6f;
    Json layer = {{"id", id}, {"type", "text"}, {"text", value},
                  {"size", Json::array({width, height})},
                  {"position", Json::array({left + content * 0.5f,
                                            wireY(top + height * 0.5f), z})},
                  {"enable_3d", true},
                  {"style", {{"font", font}, {"font_size", size}, {"fill", color}}},
                  {"start_frame", 0}, {"duration_frames", duration}};
    if (!animation.empty()) layer["animation"] = Json{{"tracks", std::move(animation)}};
    if (!animators.empty()) layer["text_animators"] = std::move(animators);
    if (opacity != 1.f) layer["opacity"] = opacity;
    if (blend != "normal") layer["blend_mode"] = blend;
    return layer;
}

Json image(const std::string& id, const char* asset, float left, float top,
           float width, float height, float z, int duration) {
    // Image layers share the shape convention: position is the frame center
    // relative to the canvas center, not an absolute wire coordinate.
    return Json{{"id", id}, {"type", "image"}, {"enable_3d", true}, {"asset", asset},
                {"position", Json::array({left + width * 0.5f - 960.f,
                                          540.f - (top + height * 0.5f), z})},
                {"size", Json::array({width, height})}, {"fit", "cover"},
                {"start_frame", 0}, {"duration_frames", duration}};
}

Json typewriter(const std::string& id, int duration, int begin, int span) {
    const int done = std::min(duration - 1, begin + span);
    Json selector = {{"id", id + "_selector"}, {"unit", "grapheme"},
                     {"shape", "square"}, {"order", "forward"},
                     {"combine", "replace"}, {"exclude_spaces", true},
                     {"start", {{"easing", "linear"},
                                {"keyframes", Json::array({
                                    key(0, 0.0), key(begin, 0.0), key(done, 100.0),
                                    key(duration - 1, 100.0)})}}},
                     {"end", {{"easing", "linear"},
                              {"keyframes", Json::array({
                                  key(0, 100.0), key(duration - 1, 100.0)})}}}};
    Json opacity = track("opacity", Json::array({key(0, 0.0), key(duration - 1, 0.0)}));
    return Json{{"id", id + "_typewriter"}, {"selectors", Json::array({selector})},
                {"properties", Json::array({opacity})}};
}

Json cameraAt(float focus, float zoom = 1.f, float x = 0.f, float y = 0.f,
              float z = -kCameraDistance, bool dof = true, float fStop = 1.8f) {
    Json camera = {{"type", "perspective"},
                   {"position", Json::array({x, y, z})},
                   {"rotation_deg", Json::array({0.f, 0.f, 0.f})},
                   {"fov_deg", 50.f}, {"near", 1.f}, {"far", 10000.f},
                   {"zoom", zoom}, {"sensor_width_mm", 36.f},
                   {"lens_shift", Json::array({0.f, 0.f})},
                   {"dof", {{"enabled", dof}, {"focus_distance", focus},
                            {"max_blur", 26.f}, {"highlight_gain", 0.35f}}}};
    if (dof) camera["f_stop"] = fStop;
    return camera;
}

Json cameraSamplesStatic(int duration, float zoom = 1.f, float fStop = 5.6f) {
    Json samples = Json::array();
    const Json camera = cameraAt(1158.06f, zoom, 0.f, 0.f, -kCameraDistance, true, fStop);
    for (int frame = 0; frame < duration; ++frame)
        samples.push_back(Json{{"frame", frame}, {"camera", camera}});
    return samples;
}

Json cameraSamplesRackFocus(int duration) {
    Json samples = Json::array();
    for (int frame = 0; frame < duration; ++frame) {
        const double t = duration > 1 ? static_cast<double>(frame) / (duration - 1) : 1.0;
        const double eased = t * t * (3.0 - 2.0 * t);        const float focus = static_cast<float>(1158.06 - 160.0 * eased);
        samples.push_back(Json{{"frame", frame},
                               {"camera", cameraAt(focus, 1.f, 0.f, 0.f, -kCameraDistance,
                                                    true, 2.8f)}});
    }
    return samples;
}

Json cameraSamplesWhip(int duration) {
    struct Stop { int frame; float x; float y; };
    const std::array<Stop, 9> stops{{
        {0, 0.f, 0.f}, {18, 0.f, 0.f}, {24, -460.f, 0.f}, {48, -460.f, 0.f},
        {54, 0.f, 0.f}, {82, 0.f, 0.f}, {88, 460.f, 0.f}, {116, 460.f, 0.f},
        {122, 0.f, 0.f}}};
    Json samples = Json::array();
    for (int frame = 0; frame < duration; ++frame) {
        float x = 0.f, y = 0.f;
        if (frame >= 122) {
            x = 0.f;
            y = 0.f;
        } else {
            for (std::size_t i = 1; i < stops.size(); ++i) {
                if (frame > stops[i].frame) continue;
                const Stop& a = stops[i - 1];
                const Stop& b = stops[i];
                const float t = b.frame > a.frame
                    ? static_cast<float>(frame - a.frame) / static_cast<float>(b.frame - a.frame)
                    : 1.f;
                const float e = t * t * (3.f - 2.f * t);
                x = a.x + (b.x - a.x) * e;
                y = a.y + (b.y - a.y) * e;
                break;
            }
        }
        const float zoom = 1.f + 0.035f * static_cast<float>(frame) / std::max(1, duration - 1);
        samples.push_back(Json{{"frame", frame},
                               {"camera", cameraAt(1158.06f, zoom, x, y,
                                                   -kCameraDistance, false)}});
    }
    return samples;
}

Json particleLayer(const std::string& id, int count, unsigned seed, float x, float y,
                   float z, const std::array<float, 2>& velocityMin,
                   const std::array<float, 2>& velocityMax,
                   const std::array<float, 2>& lifetime,
                   const std::array<float, 2>& size,
                   const std::array<float, 2>& spriteScale,
                   const std::array<float, 2>& rotation,
                   const std::array<float, 2>& angularVelocity,
                   float gravity, bool sprite, bool environment) {
    constexpr float kEmitterWidth = 1880.f;
    constexpr float kEmitterHeight = 180.f;
    Json emitter = Json::object();
    emitter["count"] = count;
    emitter["seed"] = seed;
    emitter["emitter_size"] = Json::array({kEmitterWidth, kEmitterHeight});
    emitter["velocity_min"] = Json::array({velocityMin[0], velocityMin[1]});
    emitter["velocity_max"] = Json::array({velocityMax[0], velocityMax[1]});
    emitter["lifetime"] = Json::array({lifetime[0], lifetime[1]});
    emitter["size"] = Json::array({size[0], size[1]});
    emitter["gravity"] = gravity;
    emitter["turbulence"] = 0.16f;
    emitter["air_drag"] = 0.08f;
    emitter["flow_strength"] = 0.f;
    emitter["rotation"] = Json::array({rotation[0], rotation[1]});
    emitter["angular_velocity"] = Json::array({angularVelocity[0], angularVelocity[1]});
    emitter["sprite_scale"] = Json::array({spriteScale[0], spriteScale[1]});
    emitter["color_ramp"] = Json::array({
        Json{{"position", 0.0}, {"color", Json::array({1.0, 1.0, 1.0, 0.0})}},
        Json{{"position", 0.08}, {"color", Json::array({1.0, 1.0, 1.0, 0.95})}},
        Json{{"position", 0.82}, {"color", Json::array({0.95, 0.95, 0.88, 0.82})}},
        Json{{"position", 1.0}, {"color", Json::array({0.9, 0.9, 0.8, 0.0})}}});
    emitter["blend_mode"] = "normal";
    if (sprite) emitter["sprite_asset"] = kBanknote;
    if (environment) {
        emitter["environment"] = true;
        emitter["bokeh"] = true;
        emitter["depth_range"] = Json::array({0.f, 1.f});
    }
    // Screen-space particle layers follow the screen-space box convention:
    // `position` names the top-left of the emitter box in canvas coordinates,
    // not its centre. Convert the intended emitter centre into that anchor,
    // otherwise the box half-height silently lifts the emitter off target.
    // Y grows downward in this lane, so rain uses positive velocity/gravity.
    return Json{{"id", id}, {"type", "particles"}, {"enable_3d", false},
                {"screen_space", true},
                {"position", Json::array({x - kEmitterWidth * 0.5f,
                                          y - kEmitterHeight * 0.5f})},
                {"start_frame", 0}, {"particle_emitter", std::move(emitter)}};
}

Json envelope(const std::string& jobId, int duration, Json layers, Json camera,
              Json cameraSamples, Json temporalBlur = nullptr) {
    Json plan = {{"schema", "chronon.render-plan.v3"}, {"version", 3},
                 {"job_id", jobId},
                 {"canvas", {{"width", kW}, {"height", kH}, {"fps_num", kFps},
                             {"fps_den", 1}, {"duration_frames", duration}}},
                 {"camera", std::move(camera)},
                 {"camera_samples", std::move(cameraSamples)},
                 {"layers", std::move(layers)},
                 {"output", {{"path", jobId + ".mp4"}, {"format", "mp4"},
                             {"codec", "h264"}}},
                 {"lighting_rig", {{"key_direction", Json::array({0.f, 0.f, 1.f})},
                                   {"key_intensity", 0.f},
                                   {"key_color", Json::array({1.f, 1.f, 1.f, 1.f})},
                                   {"ambient_intensity", 1.f},
                                   {"ambient_color", Json::array({1.f, 1.f, 1.f, 1.f})},
                                   {"rim_enabled", false}}}};
    if (!temporalBlur.is_null()) plan["temporal_motion_blur"] = std::move(temporalBlur);
    return plan;
}

Json buildVoxHighlight(int duration) {
    Json layers = Json::array();
    Json bg = rect("vox_desk", 0.f, 0.f, kW, kH, "#101214", 1.f, 40.f);
    bg["effects"] = Json::array({effectNoise(0.025f, 9101, 1.4f, true),
                                 effectVignette(0.34f)});
    layers.push_back(std::move(bg));

    Json shadow = rect("vox_page_shadow", 122.f, 86.f, 1690.f, 950.f, "#000000", 0.42f, 8.f);
    shadow["effects"] = Json::array({Json{{"type", "gaussian_blur"}, {"radius", 26.f}}});
    layers.push_back(std::move(shadow));

    Json page = rect("vox_page", 140.f, 62.f, 1640.f, 946.f, "#EDE9DE", 1.f, 0.f);
    page["effects"] = Json::array({effectNoise(0.035f, 2203, 1.1f, true),
                                   effectVignette(0.12f, 0.82f, 0.8f)});
    layers.push_back(std::move(page));

    for (int i = 0; i < 10; ++i) {
        const float y = 214.f + static_cast<float>(i) * 58.f;
        layers.push_back(rect("vox_rule_" + std::to_string(i), 210.f, y, 1060.f, 1.2f,
                              "#26251F", 0.09f, -1.f));
    }

    layers.push_back(text("vox_masthead", "THE ATLANTIC", 210.f, 104.f, 24.f, kInterBold,
                          "#21211D", duration, -2.f));
    layers.push_back(rect("vox_masthead_rule", 210.f, 146.f, 1500.f, 2.f, "#21211D",
                          0.38f, -3.f));
    layers.push_back(text("vox_kicker", "THE ATTENTION ECONOMY  /  CASE 01", 210.f, 172.f,
                          18.f, kInterBold, "#326C77", duration, -4.f));
    layers.push_back(text("vox_head_1", "What the feed", 198.f, 236.f, 96.f,
                          kPlayfairBold, "#181713", duration, -5.f));
    layers.push_back(text("vox_head_2", "actually costs", 198.f, 340.f, 96.f,
                          kPlayfairBold, "#181713", duration, -6.f));
    layers.push_back(text("vox_deck", "A quiet transfer of time, sold back as relevance.", 210.f,
                          466.f, 28.f, kPlayfair, "#4D4A42", duration, -7.f));

    const std::array<const char*, 4> body{{
        "The page looks still. Behind it, a market is counting",
        "every pause, every return, every small act of attention.",
        "The cost is not printed in the article. It is the article",
        "that keeps the reader inside the count."}};
    for (int i = 0; i < 4; ++i) {
        layers.push_back(text("vox_body_" + std::to_string(i), body[static_cast<std::size_t>(i)],
                              210.f, 548.f + static_cast<float>(i) * 38.f, 25.f,
                              kInterRegular, "#34322B", duration, -8.f - i));
    }

    const float markerWidth = measuredTextWidth("the attention economy", 47.f, kInterBold) + 34.f;
    layers.push_back(rect("vox_marker", 192.f, 738.f, markerWidth, 58.f, "#62D6E6", 0.90f,
                          -10.f, sweepTracks(markerWidth, 18, 36), "multiply"));
    layers.push_back(text("vox_key", "the attention economy", 210.f, 742.f, 47.f,
                          kInterBold, "#171611", duration, -24.f));
    layers.push_back(text("vox_key_tail", "is the product.", 210.f, 808.f, 47.f,
                          kInterBold, "#171611", duration, -25.f));

    layers.push_back(rect("vox_subject_rule", 1208.f, 470.f, 600.f, 2.f, "#191817",
                          0.28f, -12.f));
    Json subject = image("vox_subject", kAstronautCutout, 1208.f, 440.f, 600.f, 600.f, -160.f,
                         duration);
    subject["effects"] = Json::array({Json{{"type", "gaussian_blur"}, {"radius", 0.8f}}});
    layers.push_back(std::move(subject));
    layers.push_back(text("vox_subject_caption", "SUBJECT 01  /  THE VIEWER", 1208.f, 908.f,
                          17.f, kMono, "#201F1A", duration, -262.f));

    layers.push_back(particleLayer("vox_dust", 72, 4201, 960.f, 500.f, -45.f,
                                   {-12.f, 4.f}, {12.f, 36.f}, {2.4f, 5.8f},
                                   {1.f, 6.f}, {1.f, 1.f}, {0.f, 360.f}, {-22.f, 22.f},
                                   2.f, false, true));

    layers.push_back(text("vox_case", "01 / 05", 1510.f, 96.f, 18.f, kMono, "#3D3B31",
                          duration, -90.f, Json::array(), Json::array(), 0.82f));
    return envelope("web_modern_vox_highlight_v1", duration, std::move(layers),
                    cameraAt(1158.06f), cameraSamplesRackFocus(duration));
}

Json buildSplitGlitch(int duration) {
    Json layers = Json::array();
    Json bg = rect("split_ground", 0.f, 0.f, kW, kH, "#07090B", 1.f, 50.f);
    bg["effects"] = Json::array({effectNoise(0.045f, 8102, 1.2f, true),
                                 effectVignette(0.40f)});
    layers.push_back(std::move(bg));

    Json left = image("split_left_image", kAstronaut, 0.f, 0.f, 960.f, kH, 20.f, duration);
    left["effects"] = Json::array({Json{{"type", "halftone"}, {"size", 6}, {"angle", 18.f},
                                        {"amount", 0.58f}},
                                   effectNoise(0.10f, 660, 1.4f, true),
                                   effectVignette(0.24f)});
    layers.push_back(std::move(left));

    Json rightPaper = rect("split_right_paper", 960.f, 0.f, 960.f, kH, "#E9E3D5", 1.f, 20.f);
    rightPaper["effects"] = Json::array({effectNoise(0.04f, 112, 1.2f, true)});
    layers.push_back(std::move(rightPaper));

    layers.push_back(text("split_left_label", "THE ARCHIVE", 76.f, 70.f, 19.f, kMono,
                          "#E8E5DC", duration, 10.f));
    layers.push_back(text("split_left_time", "00:02:14:08", 76.f, 100.f, 14.f, kMono,
                          "#A8AAA6", duration, 9.f));
    layers.push_back(text("split_kicker", "CASE STUDY / 02", 1036.f, 94.f, 18.f, kInterBold,
                          "#5B4D3D", duration, 8.f));
    layers.push_back(text("split_head_1", "WHO", 1028.f, 240.f, 150.f, kInterBlack,
                          "#171513", duration, 6.f));
    layers.push_back(text("split_head_2", "PROFITS?", 1028.f, 380.f, 132.f, kInterBlack,
                          "#171513", duration, 5.f));
    layers.push_back(text("split_deck", "Attention is the inventory. The question is who owns the shelf.",
                          1036.f, 560.f, 25.f, kInterRegular, "#4E463C", duration, 4.f));

    Json shadow = rounded("split_card_shadow", 604.f, 690.f, 720.f, 300.f, 18.f,
                          "#000000", 0.62f, 2.f);
    shadow["effects"] = Json::array({Json{{"type", "gaussian_blur"}, {"radius", 30.f}}});
    layers.push_back(std::move(shadow));
    Json card = rounded("split_card", 590.f, 674.f, 720.f, 300.f, 18.f, "#F5F0E6", 1.f, -30.f);
    card["effects"] = Json::array({effectChromatic(4.f, -4.f), effectMeshGlitch(8, 8, 0.011f),
                                   effectScanlines(4.f, 0.055f),
                                   effectNoise(0.018f, 771, 1.0f, true)});
    layers.push_back(std::move(card));
    layers.push_back(rounded("split_card_topline", 590.f, 674.f, 720.f, 8.f, 4.f,
                             "#63D6E3", 1.f, -31.f));

    layers.push_back(text("split_card_label", "THE $10,000 QUESTION", 632.f, 728.f, 45.f,
                          kInterBlack, "#171513", duration, -33.f));
    layers.push_back(text("split_card_copy", "A card that follows the eye is still a card.",
                          634.f, 806.f, 24.f, kInterRegular, "#4B443A", duration, -34.f));
    layers.push_back(text("split_card_meta", "DATA / 04   •   Z-SPACE / 120", 634.f, 906.f,
                          14.f, kMono, "#746A5C", duration, -35.f));

    Json glitchA = text("split_glitch_cyan", "THE $10,000 QUESTION", 628.f, 728.f, 45.f,
                        kInterBlack, "#45E8FF", duration, -38.f, Json::array(), Json::array(),
                        0.f);
    glitchA["animation"] = Json{{"tracks", Json::array({
        track("opacity", Json::array({key(0, 0.0), key(42, 0.0), key(43, 0.42),
                                      key(44, 0.0), key(70, 0.0), key(71, 0.55),
                                      key(73, 0.0), key(duration - 1, 0.0)}))})}};
    layers.push_back(std::move(glitchA));
    Json glitchB = text("split_glitch_red", "THE $10,000 QUESTION", 636.f, 728.f, 45.f,
                        kInterBlack, "#FF4D61", duration, -39.f, Json::array(), Json::array(),
                        0.f);
    glitchB["animation"] = Json{{"tracks", Json::array({
        track("opacity", Json::array({key(0, 0.0), key(43, 0.0), key(44, 0.32),
                                      key(45, 0.0), key(72, 0.0), key(73, 0.46),
                                      key(75, 0.0), key(duration - 1, 0.0)}))})}};
    layers.push_back(std::move(glitchB));

    for (int i = 0; i < 5; ++i) {
        const float y = 710.f + static_cast<float>(i) * 48.f;
        Json band = rect("split_glitch_band_" + std::to_string(i), 590.f, y, 720.f, 4.f,
                         i % 2 == 0 ? "#45E8FF" : "#FF4D61", 0.0f, -40.f);
        band["animation"] = Json{{"tracks", Json::array({
            track("opacity", Json::array({key(0, 0.0), key(44 + i * 2, 0.0),
                                          key(45 + i * 2, 0.28), key(47 + i * 2, 0.0),
                                          key(duration - 1, 0.0)}))})}};
        layers.push_back(std::move(band));
    }

    // Energy seam. A thin filled strip plus a soft underlay is more reliable
    // across the Vulkan and software fill paths than a zero-area path; the
    // roughen/wave pair breaks the straight edge without an external matte.
    Json seamHalo = rect("split_energy_divider", 944.f, 52.f, 32.f, 976.f, "#59E6FF",
                         0.22f, -24.f);
    seamHalo["effects"] = Json::array({
        effectGlow(30.f, 2.4f, "#59E6FF"), effectBloom(0.54f, 26.f, 0.64f),
        Json{{"type", "roughen_edges"}, {"amount", 7.f}, {"scale", 18.f},
             {"complexity", 3}, {"seed", 17}}});
    layers.push_back(std::move(seamHalo));
    Json seamCore = rect("split_energy_core", 956.f, 52.f, 8.f, 976.f, "#E8FEFF",
                         0.98f, -25.f);
    seamCore["effects"] = Json::array({
        effectGlow(12.f, 1.8f, "#9DF6FF"),
        Json{{"type", "wave_warp"}, {"amplitude", 0.018f}, {"wavelength", 0.07f},
             {"speed", 1.4f}, {"direction", Json::array({0.f, 1.f})}},
        Json{{"type", "roughen_edges"}, {"amount", 4.f}, {"scale", 9.f},
             {"complexity", 2}, {"seed", 29}}});
    layers.push_back(std::move(seamCore));

    return envelope("web_modern_split_glitch_v1", duration, std::move(layers),
                    cameraAt(1158.06f, 1.f, 0.f, 0.f, -kCameraDistance, true, 5.6f),
                    cameraSamplesStatic(duration));
}

Json buildMacroUiRain(int duration) {
    Json layers = Json::array();
    Json bg = rect("macro_ground", 0.f, 0.f, kW, kH, "#090B0E", 1.f, 50.f);
    bg["effects"] = Json::array({effectNoise(0.045f, 5501, 1.4f, true),
                                 effectVignette(0.40f)});
    layers.push_back(std::move(bg));

    Json panel = rounded("macro_panel", 130.f, 58.f, 1660.f, 690.f, 26.f, "#15191F", 1.f, 20.f);
    panel["effects"] = Json::array({effectLens(-0.045f, 1.035f),
                                    effectScanlines(3.2f, 0.045f),
                                    effectNoise(0.016f, 612, 1.0f, true)});
    layers.push_back(std::move(panel));
    layers.push_back(rounded("macro_topbar", 130.f, 58.f, 1660.f, 82.f, 26.f, "#20252C", 1.f, 18.f));
    layers.push_back(text("macro_title", "COMMENTS  /  1.2M", 180.f, 82.f, 24.f, kInterBold,
                          "#E9EDF1", duration, 16.f));
    layers.push_back(text("macro_sort", "TOP  •  NEWEST", 1510.f, 86.f, 16.f, kMono,
                          "#98A3AC", duration, 15.f));

    const std::array<const char*, 4> authors{{"@market_mind", "@quiet_signal", "@aurelia",
                                             "@northstar"}};
    const std::array<const char*, 4> comments{{
        "This is not a feed. It is a pricing engine.",
        "The cursor is the only honest metric.",
        "I came for the story and stayed for the count.",
        "Every pause is inventory."}};
    const std::array<const char*, 4> likes{{"2.8K", "1.4K", "908", "712"}};
    for (int i = 0; i < 4; ++i) {
        const float y = 178.f + static_cast<float>(i) * 108.f;
        layers.push_back(ellipse("macro_avatar_" + std::to_string(i), 186.f, y + 10.f, 52.f,
                                 52.f, i % 2 == 0 ? "#2A5460" : "#5A4932", 1.f, 14.f));
        layers.push_back(text("macro_author_" + std::to_string(i), authors[static_cast<std::size_t>(i)],
                              262.f, y, 21.f, kInterBold, "#F2F5F7", duration, 13.f));
        layers.push_back(text("macro_comment_" + std::to_string(i), comments[static_cast<std::size_t>(i)],
                              262.f, y + 30.f, 27.f, kInterRegular, "#C7CFD5", duration, 12.f));
        layers.push_back(text("macro_like_" + std::to_string(i), likes[static_cast<std::size_t>(i)],
                              1680.f, y + 14.f, 15.f, kMono, "#91A0A9", duration, 12.f));
        layers.push_back(rect("macro_divider_" + std::to_string(i), 180.f, y + 82.f, 1540.f,
                              1.f, "#F2F5F7", 0.08f, 11.f));
    }

    Json typed = text("macro_typed", "The feed is not a mirror. It is a market.", 180.f,
                      620.f, 42.f, kInterMedium, "#F5F1E7", duration, 10.f);
    typed["text_animators"] = Json::array({typewriter("macro_typed", duration, 18, 78)});
    layers.push_back(std::move(typed));
    const float typedWidth = measuredTextWidth(
        "The feed is not a mirror. It is a market.", 42.f, kInterMedium);
    layers.push_back(rect("macro_cursor", 188.f + typedWidth, 622.f, 3.f, 50.f,
                          "#D8FF4F", 0.92f, 9.f,
                          Json::array({track("opacity", Json::array({
                              key(0, 0.0), key(16, 1.0), key(24, 0.0), key(32, 1.0),
                              key(40, 0.0), key(48, 1.0), key(56, 0.0), key(64, 1.0),
                              key(72, 0.0), key(80, 1.0), key(duration - 1, 0.0)}))})));

    // Layered crowd: deltas at different depths, softened independently.
    const std::array<float, 5> crowdX{{90.f, 390.f, 700.f, 1010.f, 1370.f}};
    const std::array<float, 5> crowdY{{812.f, 788.f, 830.f, 800.f, 842.f}};
    for (int i = 0; i < 5; ++i) {
        const float z = -26.f - static_cast<float>(i) * 5.f;
        Json head = ellipse("macro_crowd_head_" + std::to_string(i), crowdX[static_cast<std::size_t>(i)],
                            crowdY[static_cast<std::size_t>(i)], 104.f, 118.f, "#030405",
                            0.94f, z);
        head["effects"] = Json::array({Json{{"type", "gaussian_blur"},
                                            {"radius", i == 0 ? 3.f : 1.3f}}});
        layers.push_back(std::move(head));
        Json body = rounded("macro_crowd_body_" + std::to_string(i),
                            crowdX[static_cast<std::size_t>(i)] - 34.f,
                            crowdY[static_cast<std::size_t>(i)] + 92.f, 172.f, 240.f, 68.f,
                            "#030405", 0.94f, z - 0.4f);
        body["effects"] = Json::array({Json{{"type", "gaussian_blur"},
                                            {"radius", i == 0 ? 4.f : 1.8f}}});
        layers.push_back(std::move(body));
    }

    // The software particle lane renders one sampled element per layer. A
    // single 520-drop emitter therefore shows a single note; authoring the
    // shower as one-drop emitters keeps the same sampler, sprite, fake depth
    // and physics while letting the CPU lane draw the whole volume.
    constexpr int kMoneyDrops = 96;
    for (int i = 0; i < kMoneyDrops; ++i) {
        const std::string suffix = (i < 10 ? "0" : "") + std::to_string(i);
        layers.push_back(particleLayer(
            "macro_money_rain_" + suffix, 1,
            7719U + static_cast<unsigned>(i) * 977U, 960.f, 560.f, -48.f,
            {-70.f, 80.f}, {70.f, 180.f}, {4.0f, 6.5f},
            {90.f, 140.f}, {0.70f, 1.08f}, {-18.f, 18.f},
            {-95.f, 95.f}, 45.f, true, true));
    }

    Json productShadow = rounded("macro_product_shadow", 1332.f, 704.f, 430.f, 260.f,
                                 12.f, "#000000", 0.66f, -74.f);
    productShadow["effects"] = Json::array({Json{{"type", "gaussian_blur"}, {"radius", 26.f}}});
    layers.push_back(std::move(productShadow));
    Json product = rounded("macro_product", 1318.f, 682.f, 430.f, 260.f, 10.f, "#D8FF4F", 1.f,
                           -80.f);
    product["rotation"] = Json::array({0.f, 0.f, 7.f});
    product["effects"] = Json::array({effectGlow(14.f, 0.55f, "#D8FF4F")});
    layers.push_back(std::move(product));
    layers.push_back(text("macro_product_name", "LUNCHLY", 1360.f, 720.f, 58.f,
                          kInterBlack, "#11140C", duration, -96.f));
    layers.push_back(text("macro_product_line", "THE $10,000 QUESTION", 1362.f, 812.f, 16.f,
                          kMono, "#273018", duration, -97.f));
    layers.push_back(text("macro_product_meta", "SPONSORED  /  05", 1362.f, 868.f, 13.f,
                          kMono, "#3E4A25", duration, -98.f));

    layers.push_back(rounded("macro_chapter", 90.f, 8.f, 200.f, 44.f, 22.f, "#E5484D", 1.f,
                             -8.f));
    layers.push_back(text("macro_chapter_text", "CHAPTER 5", 118.f, 18.f, 17.f, kInterBold,
                          "#FFF7F2", duration, -13.f));
    layers.push_back(text("macro_timecode", "01:12:08:14", 1606.f, 126.f, 14.f, kMono,
                          "#D4D9DD", duration, -8.f));
    layers.push_back(text("macro_caption", "THE ATTENTION ECONOMY  /  MACRO VIEW", 76.f, 1022.f,
                          14.f, kMono, "#B7C0C7", duration, -8.f));

    return envelope("web_modern_macro_ui_rain_v1", duration, std::move(layers),
                    cameraAt(1158.06f, 1.02f, 0.f, 0.f, -kCameraDistance, true, 4.f),
                    cameraSamplesStatic(duration, 1.02f, 4.f));
}

Json buildKineticType(int duration) {
    Json layers = Json::array();
    // A full-frame screen-space plate stays put while the 3D camera whips; a
    // perspective background would expose the void at the frame edges.
    layers.push_back(Json{{"id", "kinetic_ground"}, {"type", "color"},
                          {"color", rgba("#111315", 1.f)},
                          {"size", Json::array({kW, kH})},
                          {"position", Json::array({0.f, 0.f})},
                          {"screen_space", true}, {"start_frame", 0},
                          {"duration_frames", duration}});

    struct Beat { float z; const char* word; const char* index; };
    const std::array<Beat, 4> beats{{
        {0.f, "FOOD", "01"}, {70.f, "HOUSES", "02"},
        {140.f, "SEE", "03"}, {210.f, "POWER", "04"}}};
    const std::array<int, 4> enters{{6, 42, 78, 114}};
    for (int i = 0; i < 4; ++i) {
        const Beat& beat = beats[static_cast<std::size_t>(i)];
        const std::string suffix = std::to_string(i);
        const int enter = enters[static_cast<std::size_t>(i)];
        const int exit = std::min(duration - 1, enter + 30);
        Json opacityKeys = Json::array({key(0, 0.0), key(enter, 0.0),
                                        key(enter + 5, 1.0), key(exit - 5, 1.0),
                                        key(exit, 0.0), key(duration - 1, 0.0)});
        const Json fade = track("opacity", std::move(opacityKeys), "out_cubic");
        Json scaleKeys = Json::array({key(0, 0.02), key(enter, 0.02),
                                      key(enter + 16, 1.0), key(duration - 1, 1.0)});
        layers.push_back(rect("kinetic_bar_" + suffix, 310.f, 448.f, 1300.f, 184.f,
                              "#E5D34B", 0.96f, beat.z,
                              Json::array({fade, track("scale_x", std::move(scaleKeys),
                                                       "out_cubic")})));
        const float wordWidth = measuredTextWidth(beat.word, 132.f, kInterBlack);
        // More negative z is closer to camera: the word must sit in front of
        // the bar, otherwise the opaque plate hides the whole line.
        layers.push_back(text("kinetic_word_" + suffix, beat.word, 960.f - wordWidth * 0.5f,
                              435.f, 132.f, kInterBlack, "#121410", duration,
                              beat.z - 6.f, Json::array({fade}), Json::array(), 1.f));
        layers.push_back(text("kinetic_index_" + suffix, beat.index, 340.f, 408.f, 18.f,
                              kMono, "#34382B", duration, beat.z - 6.f,
                              Json::array({fade})));
        layers.push_back(rect("kinetic_underline_" + suffix, 310.f, 636.f, 1300.f, 4.f,
                              "#F2F0E7", 0.42f, beat.z - 4.f,
                              Json::array({fade})));
    }

    return envelope("web_modern_kinetic_type_v1", duration, std::move(layers),
                    cameraAt(1158.06f, 1.f, 0.f, 0.f, -kCameraDistance, true, 16.f),
                    cameraSamplesStatic(duration, 1.f, 16.f),
                    Json{{"shutter_angle", 180.f}, {"samples", 8}});
}

Json buildVhsCarousel(int duration) {
    Json layers = Json::array();
    Json bg = rect("vhs_ground", 0.f, 0.f, kW, kH, "#07090B", 1.f, 50.f);
    bg["effects"] = Json::array({effectNoise(0.11f, 9301, 1.2f, true),
                                 effectScanlines(4.f, 0.09f),
                                 effectVignette(0.44f)});
    layers.push_back(std::move(bg));

    Json frameShadow = rounded("vhs_frame_shadow", 240.f, 130.f, 1440.f, 790.f, 38.f,
                               "#000000", 0.75f, 8.f);
    frameShadow["effects"] = Json::array({Json{{"type", "gaussian_blur"}, {"radius", 34.f}}});
    layers.push_back(std::move(frameShadow));
    Json frame = rounded("vhs_frame", 222.f, 104.f, 1440.f, 790.f, 38.f, "#2A2E31", 1.f, 0.f);
    frame["effects"] = Json::array({effectNoise(0.02f, 7, 1.f, true)});
    layers.push_back(std::move(frame));
    Json screen = rounded("vhs_screen", 278.f, 160.f, 1328.f, 676.f, 22.f, "#0B1115", 1.f,
                          -5.f);
    screen["effects"] = Json::array({effectScanlines(3.f, 0.10f, 0.15f),
                                     Json{{"type", "retro_tv"}, {"jitter_px", 2.0f},
                                          {"jitter_speed", 26.f}, {"smear_px", 5.f},
                                          {"bleed_strength", 0.24f}, {"luma_noise", 0.055f},
                                          {"seed", 77}},
                                     effectChromatic(2.2f, -2.2f),
                                     effectVignette(0.34f, 0.66f, 0.68f)});
    layers.push_back(std::move(screen));

    layers.push_back(text("vhs_rec", "● REC", 330.f, 198.f, 18.f, kMono, "#FF5D57",
                          duration, -8.f));
    layers.push_back(text("vhs_signal", "SIGNAL / 05", 1390.f, 200.f, 14.f, kMono,
                          "#B8DEE3", duration, -8.f));

    const std::array<const char*, 5> logos{{"SONY", "FOX", "CIA", "NBC", "MTV"}};
    const std::array<float, 5> logoX{{1300.f, 1560.f, 1820.f, 2080.f, 2340.f}};
    const Json carousel = track("position_x", Json::array({
        key(0, 0.0), key(18, 0.0), key(58, -980.0), key(64, -1040.0),
        key(70, -1010.0), key(104, -1010.0), key(112, -960.0),
        key(duration - 1, -960.0)}), "out_back");
    for (int i = 0; i < 5; ++i) {
        Json logo = text("vhs_logo_" + std::to_string(i), logos[static_cast<std::size_t>(i)],
                         logoX[static_cast<std::size_t>(i)], 410.f, 74.f, kInterBlack,
                         "#EEF4F2", duration, -12.f, Json::array({carousel}));
        logo["effects"] = Json::array({effectChromatic(3.4f, -3.4f),
                                       effectDirectional(0.f, 26.f, 16)});
        layers.push_back(std::move(logo));
    }

    // Tracking band and a hot, slightly misregistered title.
    Json band = rect("vhs_tracking_band", 278.f, 300.f, 1328.f, 42.f, "#D7F7FF", 0.12f, -14.f);
    band["effects"] = Json::array({Json{{"type", "wave_warp"}, {"amplitude", 0.08f},
                                        {"wavelength", 0.14f}, {"speed", 2.2f},
                                        {"direction", Json::array({1.f, 0.f})}},
                                   effectNoise(0.35f, 9, 1.0f, true)});
    layers.push_back(std::move(band));

    Json titleGlow = text("vhs_title_glow", "LULZSEC", 358.f, 42.f, 118.f, kInterBlack,
                          "#8DF6FF", duration, -18.f, Json::array(), Json::array(), 0.62f,
                          "screen");
    titleGlow["effects"] = Json::array({effectGlow(26.f, 1.5f, "#5DE5FF"),
                                        effectBloom(0.54f, 30.f, 0.72f)});
    layers.push_back(std::move(titleGlow));
    layers.push_back(text("vhs_title", "LULZSEC", 348.f, 42.f, 118.f, kInterBlack,
                          "#F4F0E8", duration, -20.f));

    Json typed = text("vhs_typed", "THE TRUTH IS A SEQUENCE OF FRAMES", 330.f, 944.f, 40.f,
                      kInterBold, "#F4F0E8", duration, -22.f);
    typed["text_animators"] = Json::array({typewriter("vhs_typed", duration, 22, 90)});
    layers.push_back(std::move(typed));
    layers.push_back(text("vhs_timecode", "00:04:13:08", 1490.f, 946.f, 16.f, kMono,
                          "#AFC7CB", duration, -23.f));

    Json overlay = rounded("vhs_glass", 278.f, 160.f, 1328.f, 676.f, 22.f, "#FFFFFF", 0.0f,
                           -26.f);
    overlay["effects"] = Json::array({effectChromatic(1.4f, -1.4f),
                                      effectScanlines(2.4f, 0.05f, 0.3f)});
    layers.push_back(std::move(overlay));

    return envelope("web_modern_vhs_carousel_v1", duration, std::move(layers),
                    cameraAt(1158.06f, 1.f, 0.f, 0.f, -kCameraDistance, true, 5.6f),
                    cameraSamplesStatic(duration));
}

}  // namespace

const char* modernDocumentaryName(ModernDocumentaryRecipe recipe) {
    switch (recipe) {
        case ModernDocumentaryRecipe::VoxHighlight: return "web_modern_vox_highlight";
        case ModernDocumentaryRecipe::SplitGlitch: return "web_modern_split_glitch";
        case ModernDocumentaryRecipe::MacroUiRain: return "web_modern_macro_ui_rain";
        case ModernDocumentaryRecipe::KineticType: return "web_modern_kinetic_type";
        case ModernDocumentaryRecipe::VhsCarousel: return "web_modern_vhs_carousel";
    }
    return "unknown";
}

std::array<ModernDocumentaryRecipe, 5> allModernDocumentaryRecipes() {
    return {ModernDocumentaryRecipe::VoxHighlight, ModernDocumentaryRecipe::SplitGlitch,
            ModernDocumentaryRecipe::MacroUiRain, ModernDocumentaryRecipe::KineticType,
            ModernDocumentaryRecipe::VhsCarousel};
}

void ModernDocumentarySpec::validate() const {
    if (fps != 30) fail("fps must be 30");
    if (durationFrames < 60 || durationFrames > 300)
        fail("durationFrames must be in [60,300] (max 10 s at 30 fps)");
    if (outputName.find('\n') != std::string::npos)
        fail("outputName must be a single line");
}

std::string ModernDocumentarySpec::planName() const {
    return std::string(modernDocumentaryName(recipe)) + "_v1";
}

std::string ModernDocumentarySpec::outputStem() const {
    return outputName.empty() ? planName() + ".mp4" : outputName;
}

nlohmann::json buildModernDocumentaryPlan(const ModernDocumentarySpec& spec) {
    spec.validate();
    const int duration = spec.durationFrames;
    nlohmann::json plan;
    switch (spec.recipe) {
        case ModernDocumentaryRecipe::VoxHighlight:
            plan = buildVoxHighlight(duration);
            break;
        case ModernDocumentaryRecipe::SplitGlitch:
            plan = buildSplitGlitch(duration);
            break;
        case ModernDocumentaryRecipe::MacroUiRain:
            plan = buildMacroUiRain(duration);
            break;
        case ModernDocumentaryRecipe::KineticType:
            plan = buildKineticType(duration);
            break;
        case ModernDocumentaryRecipe::VhsCarousel:
            plan = buildVhsCarousel(duration);
            break;
    }
    plan["job_id"] = spec.planName();
    plan["output"] = Json{{"path", spec.outputStem()}, {"format", "mp4"},
                          {"codec", "h264"}};
    return plan;
}

}  // namespace chronontemplate::web
