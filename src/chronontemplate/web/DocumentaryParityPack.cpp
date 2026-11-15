#include "chronontemplate/web/DocumentaryParityPack.hpp"

#include "chronontemplate/web/WebFontMeasure.hpp"

#include <algorithm>
#include <array>
#include <cmath>
#include <stdexcept>
#include <string>
#include <utility>

namespace chronontemplate::web {
namespace {

using Json = nlohmann::json;
using shot::measuredTextWidth;

constexpr int kW = 1920;
constexpr int kH = 1080;
constexpr int kFps = 30;
constexpr float kCameraZ = -1158.06f;
constexpr const char* kInterBold = "ChrononTemplate/assets/fonts/Inter-Bold.ttf";
constexpr const char* kInterBlack = "ChrononTemplate/assets/fonts/Inter-Black.ttf";
constexpr const char* kInterMedium = "ChrononTemplate/assets/fonts/Inter-Medium.ttf";
constexpr const char* kInterRegular = "ChrononTemplate/assets/fonts/Inter-Regular.ttf";
constexpr const char* kMono = "ChrononTemplate/assets/fonts/LiberationMono-Bold.ttf";
constexpr const char* kAstronaut =
    "ChrononTemplate/assets/astronaut_camera_transition_v1/humanity-astronaut-cutout-v2.png";
constexpr const char* kBanknote = "ChrononTemplate/assets/modern_documentary/banknote.png";
constexpr const char* kP7Gradient =
    "ChrononTemplate/assets/documentary_parity/p7_gradient.png";
constexpr const char* kP1Panel =
    "ChrononTemplate/assets/documentary_parity/p1_panel_opaque.png";

[[noreturn]] void fail(const std::string& message) {
    throw std::invalid_argument("DocumentaryParitySpec: " + message);
}

Json rgba(const std::string& hex, float alpha = 1.f) {
    if (hex.size() != 7 || hex.front() != '#')
        throw std::invalid_argument("DocumentaryParityPack: color must be #RRGGBB");
    const unsigned value = static_cast<unsigned>(std::stoul(hex.substr(1), nullptr, 16));
    return Json::array({((value >> 16) & 255U) / 255.0, ((value >> 8) & 255U) / 255.0,
                        (value & 255U) / 255.0, static_cast<double>(alpha)});
}

float wireY(float topDownY) { return static_cast<float>(kH) - topDownY; }

Json key(int frame, double value) { return Json{{"frame", frame}, {"value", value}}; }

Json track(const std::string& property, Json keys, const std::string& easing = "linear") {
    return Json{{"property", property}, {"easing", easing}, {"keyframes", std::move(keys)}};
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
    return Json{{"type", "chromatic_aberration"}, {"red_offset", red}, {"blue_offset", blue}};
}

Json effectLens(float curvature, float scale = 1.08f) {
    return Json{{"type", "lens_distortion"}, {"curvature", curvature},
                {"scale", scale}, {"center", Json::array({0.5, 0.5})}};
}

Json shape(const std::string& id, const std::string& type, float left, float top,
           float width, float height, const std::string& color, float alpha,
           float z, Json animation = Json::array(), const std::string& blend = "normal") {
    // Shapes are authored in canvas coordinates and lowered to the renderer's
    // centre-relative 3D position, exactly like the delivered Modern pack.
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
             Json animation = Json::array(), const std::string& blend = "normal") {
    Json layer = shape(id, "rounded_rect", left, top, width, height, color, alpha, z,
                       std::move(animation), blend);
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
    return Json{{"id", id}, {"type", "image"}, {"enable_3d", true}, {"asset", asset},
                {"position", Json::array({left + width * 0.5f - 960.f,
                                          540.f - (top + height * 0.5f), z})},
                {"size", Json::array({width, height})}, {"fit", "cover"},
                {"start_frame", 0}, {"duration_frames", duration}};
}

Json ground(const std::string& id, const std::string& color, int duration) {
    return Json{{"id", id}, {"type", "color"}, {"color", rgba(color, 1.f)},
                {"size", Json::array({kW, kH})}, {"position", Json::array({0.f, 0.f})},
                {"screen_space", true}, {"start_frame", 0},
                {"duration_frames", duration}};
}

Json typewriter(const std::string& id, int duration, int begin, int span) {
    const int done = std::min(duration - 1, begin + span);
    Json selector = {
        {"id", id + "_selector"}, {"unit", "grapheme"}, {"shape", "square"},
        {"order", "forward"}, {"combine", "replace"}, {"exclude_spaces", true},
        {"start", {{"easing", "linear"},
                   {"keyframes", Json::array({key(0, 0.0), key(begin, 0.0),
                                              key(done, 100.0),
                                              key(duration - 1, 100.0)})}}},
        {"end", {{"easing", "linear"},
                 {"keyframes", Json::array({key(0, 100.0),
                                            key(duration - 1, 100.0)})}}}};
    Json opacity = track("opacity", Json::array({key(0, 1.0), key(duration - 1, 1.0)}));
    return Json{{"id", id + "_typewriter"}, {"selectors", Json::array({selector})},
                {"properties", Json::array({opacity})}};
}

Json cameraAt(float focus, float fStop = 5.6f, bool dof = true, float x = 0.f,
              float y = 0.f, float z = kCameraZ, float roll = 0.f,
              float zoom = 1.f) {
    Json camera = {{"type", "perspective"},
                   {"position", Json::array({x, y, z})},
                   {"rotation_deg", Json::array({0.f, 0.f, roll})},
                   {"fov_deg", 50.f}, {"near", 1.f}, {"far", 10000.f},
                   {"zoom", zoom}, {"sensor_width_mm", 36.f},
                   {"lens_shift", Json::array({0.f, 0.f})},
                   {"dof", {{"enabled", dof}, {"focus_distance", focus},
                            {"max_blur", 26.f}, {"highlight_gain", 0.35f}}}};
    if (dof) camera["f_stop"] = fStop;
    return camera;
}

Json driftSamples(int duration, float amountX, float amountY, float amountRoll,
                  bool dof = false, float focus = 1158.06f, float fStop = 8.f) {
    Json samples = Json::array();
    for (int frame = 0; frame < duration; ++frame) {
        const float t = duration > 1 ? static_cast<float>(frame) /
                                      static_cast<float>(duration - 1) : 1.f;
        const float x = (t - 0.5f) * 2.f * amountX;
        const float y = std::sin(t * 6.2831853f) * amountY;
        const float roll = std::sin(t * 6.2831853f + 0.8f) * amountRoll;
        samples.push_back(Json{{"frame", frame},
                               {"camera", cameraAt(focus, fStop, dof, x, y,
                                                   kCameraZ, roll, 1.f)}});
    }
    return samples;
}

Json envelope(const std::string& jobId, int duration, Json layers, Json camera,
              Json samples, Json temporalBlur = nullptr) {
    Json plan = {{"schema", "chronon.render-plan.v3"}, {"version", 3},
                 {"job_id", jobId},
                 {"canvas", {{"width", kW}, {"height", kH}, {"fps_num", kFps},
                             {"fps_den", 1}, {"duration_frames", duration}}},
                 {"camera", std::move(camera)},
                 {"camera_samples", std::move(samples)},
                 {"layers", std::move(layers)},
                 {"output", {{"path", jobId + ".mp4"}, {"format", "mp4"},
                             {"codec", "h264"}}},
                 // Shapes and images are lit in 3D. Without an explicit rig the
                 // authored sRGB fills render darker than authored, so every
                 // fixture pins an unlit-key/ambient-white rig.
                 {"lighting_rig", {{"key_direction", Json::array({0.f, 0.f, 1.f})},
                                   {"key_intensity", 0.f},
                                   {"key_color", Json::array({1.f, 1.f, 1.f, 1.f})},
                                   {"ambient_intensity", 1.f},
                                   {"ambient_color", Json::array({1.f, 1.f, 1.f, 1.f})},
                                   {"rim_enabled", false}}}};
    if (!temporalBlur.is_null()) plan["temporal_motion_blur"] = std::move(temporalBlur);
    return plan;
}

// ─────────────────────────────────────────────────────────────── PARITY_01
Json buildMacroLcdTypewriter(int duration) {
    Json layers = Json::array();
    layers.push_back(ground("p1_ground", "#D7DADD", duration));

    // The optical wrap rides a full-frame opaque plate instead of a cropped
    // shape: the native lens path resamples tight layers to transparent, while
    // a full-frame source preserves the card edge and makes both the curvature
    // and the RGB split measurable. The plate background matches p1_ground, so
    // the frame is unchanged outside the card.
    Json panel = image("p1_panel", kP1Panel, 0.f, 0.f, kW, kH, 10.f, duration);
    panel["effects"] = Json::array({effectLens(-0.04f, 1.0f),
                                    effectScanlines(3.2f, 0.055f),
                                    effectChromatic(1.0f, -1.0f),
                                    effectVignette(0.35f, 0.68f, 0.62f),
                                    effectNoise(0.010f, 3101, 1.4f, true)});
    layers.push_back(std::move(panel));

    layers.push_back(rounded("p1_topbar", 96.f, 70.f, 1728.f, 86.f, 24.f,
                             "#FFFFFF", 1.f, 8.f));
    layers.push_back(text("p1_title", "COMMENTS  /  1.2M", 138.f, 92.f, 25.f,
                          kInterBold, "#20242A", duration, 4.f));
    layers.push_back(text("p1_sort", "TOP  •  NEWEST", 1600.f, 96.f, 17.f,
                          kMono, "#707A82", duration, 4.f));

    layers.push_back(ellipse("p1_avatar", 160.f, 220.f, 82.f, 82.f,
                             "#2B6070", 1.f, 5.f));
    layers.push_back(text("p1_handle", "@SpartanWilliamS043", 276.f, 208.f, 34.f,
                          kInterBold, "#171B20", duration, 4.f));
    layers.push_back(text("p1_meta", "10 months ago  •  reply", 276.f, 256.f, 22.f,
                          kInterRegular, "#6B747C", duration, 4.f));

    Json typed = text("p1_typed", "The feed is not a mirror. It is a market.",
                      276.f, 350.f, 56.f, kInterMedium, "#11151A",
                      duration, 2.f);
    typed["text_animators"] = Json::array({typewriter("p1_typed", duration, 18, 49)});
    typed["effects"] = Json::array({effectChromatic(2.5f, -2.5f)});
    layers.push_back(std::move(typed));

    // The panel's own white-on-grey bottom and right edges are the optical
    // probes: they stay large enough to survive the lens resample, unlike
    // thin overlay lines which the barrel filter can erase.
    layers.push_back(text("p1_footer", "MACRO LCD  /  k1 = -0.04  /  1.0 px CA",
                          138.f, 950.f, 15.f, kMono, "#6B747C", duration, 2.f));

    return envelope("parity_01_macro_lcd_typewriter", duration, std::move(layers),
                    cameraAt(1158.06f, 8.f, false), driftSamples(duration, 7.f, 5.f, 0.16f),
                    nullptr);
}

// ─────────────────────────────────────────────────────────────── PARITY_02
Json buildKineticWhipBars(int duration) {
    Json layers = Json::array();
    layers.push_back(ground("p2_ground", "#101214", duration));

    struct Beat { float x; float z; const char* word; const char* index; int enter; int leave; };
    const std::array<Beat, 3> beats{{
        {700.f, 40.f, "food", "01", 2, 35},
        {960.f, 0.f, "houses", "02", 38, 72},
        {1220.f, -40.f, "see", "03", 78, 112}}};

    for (int i = 0; i < 3; ++i) {
        const Beat& beat = beats[static_cast<std::size_t>(i)];
        const std::string suffix = std::to_string(i + 1);
        const int fadeIn = beat.enter;
        const int fadeOut = beat.leave;
        Json fade = track("opacity", Json::array({
            key(0, 0.0), key(fadeIn, 0.0), key(fadeIn + 3, 1.0),
            key(fadeOut, 1.0), key(fadeOut + 4, 0.0), key(duration - 1, 0.0)}));
        const float wordWidth = measuredTextWidth(beat.word, 142.f, kInterBlack);
        const float pad = 26.f;
        const float barWidth = wordWidth + pad * 2.f;
        const float barLeft = beat.x - barWidth * 0.5f;
        Json scaleKeys = Json::array({key(0, 0.0), key(fadeIn + 1, 0.0),
                                      key(fadeIn + 10, 1.0), key(duration - 1, 1.0)});
        Json posKeys = Json::array({key(0, -barWidth * 0.5),
                                    key(fadeIn + 1, -barWidth * 0.5),
                                    key(fadeIn + 10, 0.0),
                                    key(duration - 1, 0.0)});
        // PARITY_02: the bar and the text share one measured bounding box.
        // The bar is 26 px wider on each side and scales from its left edge.
        layers.push_back(rect("p2_bar_" + suffix, barLeft, 464.f, barWidth, 188.f,
                              "#F5C518", 0.98f, beat.z + 8.f,
                              Json::array({fade,
                                           track("scale_x", std::move(scaleKeys), "out_cubic"),
                                           track("position_x", std::move(posKeys), "out_cubic")})));
        layers.push_back(text("p2_word_" + suffix, beat.word, beat.x - wordWidth * 0.5f,
                              447.f, 142.f, kInterBlack, "#101216", duration,
                              beat.z - 6.f, Json::array({fade})));
        layers.push_back(text("p2_index_" + suffix, beat.index, barLeft + 4.f,
                              414.f, 18.f, kMono, "#3A3D2D", duration,
                              beat.z - 6.f, Json::array({fade})));
    }

    // Camera whip: 0 → houses in 7 frames, houses → see in 7 frames, then a
    // 20-frame dolly-out reveal. All three beats stay on distinct Z planes.
    Json samples = Json::array();
    const std::array<std::array<float, 4>, 7> stops{{
        {0.f, -260.f, 1.32f, 0.0f}, {20.f, -260.f, 1.32f, 0.0f},
        {27.f, 0.f, 1.32f, 0.0f}, {50.f, 0.f, 1.32f, 0.0f},
        {57.f, 260.f, 1.32f, 0.0f}, {90.f, 260.f, 1.32f, 0.0f},
        {112.f, 0.f, 1.0f, 0.0f}}};
    for (int frame = 0; frame < duration; ++frame) {
        float x = 0.f, zoom = 1.f, roll = 0.f;
        if (frame >= 112) {
            x = 0.f; zoom = 1.f;
        } else {
            for (std::size_t i = 1; i < stops.size(); ++i) {
                if (frame > static_cast<int>(stops[i][0])) continue;
                const auto& a = stops[i - 1];
                const auto& b = stops[i];
                const float t = b[0] > a[0]
                    ? (static_cast<float>(frame) - a[0]) / (b[0] - a[0]) : 1.f;
                const float e = t * t * (3.f - 2.f * t);
                x = a[1] + (b[1] - a[1]) * e;
                zoom = a[2] + (b[2] - a[2]) * e;
                break;
            }
        }
        roll = std::sin(static_cast<float>(frame) * 0.07f) * 0.10f;
        const float y = std::sin(static_cast<float>(frame) * 0.045f) * 3.5f;
        samples.push_back(Json{{"frame", frame},
                               {"camera", cameraAt(1158.06f, 8.f, false, x, y,
                                                   kCameraZ, roll, zoom)}});
    }

    return envelope("parity_02_kinetic_whip_bars", duration, std::move(layers),
                    cameraAt(1158.06f, 8.f, false, -260.f, 0.f, kCameraZ, 0.f, 1.32f),
                    std::move(samples),
                    Json{{"shutter_angle", 270.f}, {"samples", 16}});
}

// ─────────────────────────────────────────────────────────────── PARITY_03
Json buildRackFocusStack(int duration) {
    Json layers = Json::array();
    layers.push_back(ground("p3_ground", "#171A1F", duration));

    Json far = rounded("p3_far", 180.f, 230.f, 500.f, 300.f, 20.f,
                       "#E85D75", 1.f, 600.f);
    far["effects"] = Json::array({effectNoise(0.012f, 7001, 1.2f, false)});
    layers.push_back(std::move(far));
    layers.push_back(text("p3_far_label", "FAR  /  Z +600", 206.f, 258.f, 22.f,
                          kMono, "#2B1117", duration, 594.f));

    layers.push_back(rounded("p3_mid", 760.f, 230.f, 500.f, 300.f, 20.f,
                             "#3BB3D9", 1.f, 80.f));
    layers.push_back(text("p3_mid_label", "MID  /  Z +80", 786.f, 258.f, 22.f,
                          kMono, "#07222C", duration, 74.f));

    // The subject plane is the focus target at the end of the rack.
    layers.push_back(rounded("p3_subject", 1240.f, 238.f, 460.f, 300.f, 20.f,
                             "#F2C14E", 1.f, -180.f));
    layers.push_back(text("p3_subject_label", "SUBJECT  /  Z -180", 1264.f, 266.f,
                          22.f, kMono, "#2A2108", duration, -186.f));

    layers.push_back(rounded("p3_foreground", 560.f, 720.f, 300.f, 180.f, 18.f,
                             "#9B5DE5", 1.f, -600.f));
    layers.push_back(text("p3_foreground_label", "FG  /  Z -600", 588.f, 748.f, 20.f,
                          kMono, "#F4ECFF", duration, -606.f));

    Json samples = Json::array();
    for (int frame = 0; frame < duration; ++frame) {
        const float t = std::min(1.f, static_cast<float>(frame) / 90.f);
        const float e = t * t * (3.f - 2.f * t);
        const float focus = 1758.f - 780.f * e;
        const float zoom = 1.f + 0.035f * e;
        const float x = std::sin(t * 3.1f) * 4.f;
        samples.push_back(Json{{"frame", frame},
                               {"camera", cameraAt(focus, 1.8f, true, x, 0.f,
                                                   kCameraZ, 0.f, zoom)}});
    }

    return envelope("parity_03_rack_focus_stack", duration, std::move(layers),
                    cameraAt(1758.f, 1.8f, true, 0.f, 0.f, kCameraZ, 0.f, 1.f),
                    std::move(samples), nullptr);
}

// ─────────────────────────────────────────────────────────────── PARITY_04
Json buildParticleRainOcclusion(int duration) {
    Json layers = Json::array();
    layers.push_back(ground("p4_ground", "#0B0E12", duration));

    Json backdrop = rounded("p4_backdrop", 190.f, 120.f, 1540.f, 840.f, 22.f,
                            "#DCD6C7", 1.f, 600.f);
    backdrop["effects"] = Json::array({effectNoise(0.025f, 8801, 1.4f, true),
                                       effectVignette(0.12f, 0.78f, 0.7f)});
    layers.push_back(std::move(backdrop));
    layers.push_back(text("p4_backdrop_label", "BACKGROUND  /  Z +600", 226.f,
                          152.f, 18.f, kMono, "#3A3830", duration, 588.f));

    // One 250-instance environment emitter. Environment depth maps each note
    // to Z 0..100: behind the subject at Z -180, in front of the backdrop.
    Json emitter = Json::object();
    emitter["count"] = 250;
    emitter["seed"] = 94117;
    emitter["emitter_size"] = Json::array({1580.f, 1120.f});
    // Local emitter coordinates grow downward for the renderer's particle
    // lane, so falling banknotes use positive Y velocity and gravity.
    emitter["velocity_min"] = Json::array({-55.f, 85.f});
    emitter["velocity_max"] = Json::array({55.f, 230.f});
    emitter["lifetime"] = Json::array({7.f, 11.f});
    emitter["size"] = Json::array({78.f, 132.f});
    emitter["gravity"] = 42.f;
    emitter["turbulence"] = 14.f;
    emitter["air_drag"] = 0.06f;
    emitter["rotation"] = Json::array({-25.f, 25.f});
    emitter["angular_velocity"] = Json::array({-95.f, 95.f});
    emitter["sprite_scale"] = Json::array({0.82f, 1.16f});
    emitter["sprite_asset"] = kBanknote;
    emitter["environment"] = true;
    emitter["depth_range"] = Json::array({0.f, 1.f});
    emitter["bokeh"] = true;
    emitter["blend_mode"] = "normal";
    emitter["color_ramp"] = Json::array({
        Json{{"position", 0.0}, {"color", Json::array({1.0, 1.0, 1.0, 0.0})}},
        Json{{"position", 0.06}, {"color", Json::array({1.0, 1.0, 1.0, 0.98})}},
        Json{{"position", 0.86}, {"color", Json::array({1.0, 1.0, 1.0, 0.92})}},
        Json{{"position", 1.0}, {"color", Json::array({0.9, 0.9, 0.85, 0.0})}}});
    Json rain = {{"id", "p4_money_rain"}, {"type", "particles"},
                 {"enable_3d", true}, {"screen_space", false},
                 {"position", Json::array({0.f, 0.f, 0.f})},
                 {"size", Json::array({1920.f, 1080.f})},
                 {"start_frame", 0}, {"duration_frames", duration},
                 {"particle_emitter", std::move(emitter)}};
    layers.push_back(std::move(rain));

    Json subject = image("p4_subject", kAstronaut, 1270.f, 248.f, 560.f, 640.f,
                         -180.f, duration);
    subject["effects"] = Json::array({effectGlow(18.f, 0.35f, "#F7D77B")});
    layers.push_back(std::move(subject));
    layers.push_back(text("p4_subject_label", "SUBJECT  /  Z -180", 1276.f,
                          894.f, 17.f, kMono, "#15171A", duration, -188.f));

    Json foreground = rounded("p4_foreground", 170.f, 700.f, 330.f, 360.f, 60.f,
                              "#030405", 0.98f, -520.f);
    foreground["effects"] = Json::array({Json{{"type", "gaussian_blur"},
                                              {"radius", 3.5f}}});
    layers.push_back(std::move(foreground));

    return envelope("parity_04_particle_rain_occlusion", duration, std::move(layers),
                    cameraAt(1158.06f, 8.f, true, 0.f, 0.f, kCameraZ, 0.f, 1.f),
                    driftSamples(duration, 4.f, 3.f, 0.08f, true, 1158.06f, 8.f),
                    nullptr);
}

// ─────────────────────────────────────────────────────────────── PARITY_05
Json buildUiCardPanReveal(int duration) {
    Json layers = Json::array();
    layers.push_back(ground("p5_ground", "#0A0C10", duration));

    for (int i = 0; i < 7; ++i) {
        layers.push_back(rect("p5_grid_" + std::to_string(i), 0.f,
                              120.f + static_cast<float>(i) * 132.f, kW, 1.f,
                              "#8DA2B5", 0.10f, 9.f));
    }
    layers.push_back(text("p5_kicker", "PARITY 05  /  3D UI SURFACE", 120.f,
                          54.f, 18.f, kMono, "#AFC1D0", duration, 0.f));

    Json card = rounded("p5_card", 330.f, 220.f, 1260.f, 640.f, 24.f,
                        "#F4F1E8", 1.f, 0.f);
    card["rotation"] = Json::array({8.f, -18.f, -4.f});
    card["effects"] = Json::array({effectNoise(0.014f, 1951, 1.3f, true)});
    card["animation"] = Json{{"tracks", Json::array({
        track("rotation_x", Json::array({key(0, 8.0), key(45, 2.0), key(75, 0.0),
                                         key(duration - 1, 0.0)}), "out_cubic"),
        track("rotation_y", Json::array({key(0, -18.0), key(45, -5.0), key(75, 0.0),
                                         key(duration - 1, 0.0)}), "out_cubic"),
        track("rotation_z", Json::array({key(0, -4.0), key(45, -1.0), key(75, 0.0),
                                         key(duration - 1, 0.0)}), "out_cubic")})}};
    layers.push_back(std::move(card));
    layers.push_back(rect("p5_card_topline", 330.f, 220.f, 1260.f, 7.f,
                          "#63D6E3", 0.95f, -4.f));

    // Rounded viewport inside the card. It is deliberately empty of text so
    // the anti-aliasing probe measures the shape edge, not glyph coverage.
    layers.push_back(rounded("p5_viewport", 390.f, 300.f, 540.f, 320.f, 24.f,
                             "#142A34", 1.f, -10.f));
    layers.push_back(ellipse("p5_play", 622.f, 410.f, 96.f, 96.f,
                             "#F4F1E8", 0.96f, -14.f));
    layers.push_back(rect("p5_viewport_progress", 390.f, 620.f, 540.f, 5.f,
                          "#63D6E3", 0.9f, -14.f));
    layers.push_back(rect("p5_viewport_progress_fill", 390.f, 620.f, 218.f, 5.f,
                          "#F4F1E8", 0.95f, -16.f));
    layers.push_back(text("p5_viewport_label", "FEATURED  /  03:18", 420.f,
                          556.f, 17.f, kMono, "#A8D8E2", duration, -16.f));

    layers.push_back(text("p5_headline", "THE FEED", 1010.f, 330.f, 76.f,
                          kInterBlack, "#171513", duration, -8.f,
                          Json::array({track("opacity", Json::array({
                              key(0, 0.0), key(30, 0.0), key(38, 1.0),
                              key(duration - 1, 1.0)}))})));
    layers.push_back(text("p5_headline_two", "IS THE", 1010.f, 410.f, 76.f,
                          kInterBlack, "#171513", duration, -8.f,
                          Json::array({track("opacity", Json::array({
                              key(0, 0.0), key(34, 0.0), key(42, 1.0),
                              key(duration - 1, 1.0)}))})));
    layers.push_back(text("p5_headline_three", "PRODUCT.", 1010.f, 490.f, 76.f,
                          kInterBlack, "#E5484D", duration, -8.f,
                          Json::array({track("opacity", Json::array({
                              key(0, 0.0), key(38, 0.0), key(46, 1.0),
                              key(duration - 1, 1.0)}))})));
    layers.push_back(text("p5_subcopy", "A rounded surface is still a surface.\nThe camera does the rest.", 1012.f, 594.f, 23.f,
                          kInterRegular, "#544D42", duration, -8.f));

    Json samples = Json::array();
    for (int frame = 0; frame < duration; ++frame) {
        const float t = std::min(1.f, static_cast<float>(frame) / 75.f);
        const float e = t * t * (3.f - 2.f * t);
        const float x = -140.f * (1.f - e);
        const float y = 12.f * (1.f - e);
        const float zoom = 1.08f - 0.08f * e;
        samples.push_back(Json{{"frame", frame},
                               {"camera", cameraAt(1158.06f, 5.6f, true, x, y,
                                                   kCameraZ, 0.f, zoom)}});
    }

    return envelope("parity_05_ui_card_pan_reveal", duration, std::move(layers),
                    cameraAt(1158.06f, 5.6f, true, -140.f, 12.f, kCameraZ, 0.f, 1.08f),
                    std::move(samples), nullptr);
}

// ─────────────────────────────────────────────────────────────── PARITY_06
Json buildCrtHudCounter(int duration) {
    Json layers = Json::array();
    layers.push_back(ground("p6_ground", "#0C0E11", duration));

    Json plate = image("p6_plate", kAstronaut, 0.f, 0.f, kW, kH, 800.f, duration);
    plate["effects"] = Json::array({Json{{"type", "gaussian_blur"}, {"radius", 1.2f}},
                                    effectScanlines(3.f, 0.075f, 0.12f),
                                    effectChromatic(0.9f, -0.9f),
                                    effectNoise(0.035f, 4401, 1.5f, true),
                                    effectVignette(0.30f, 0.72f, 0.62f)});
    layers.push_back(std::move(plate));

    Json badge = rounded("p6_badge", 150.f, 118.f, 286.f, 66.f, 33.f,
                         "#E62E2D", 1.f, -8.f);
    badge["effects"] = Json::array({effectGlow(10.f, 0.55f, "#E62E2D")});
    layers.push_back(std::move(badge));
    const float badgeTextWidth = measuredTextWidth("chapter 5", 29.f, kInterBold);
    layers.push_back(text("p6_badge_text", "chapter 5",
                          150.f + (286.f - badgeTextWidth) * 0.5f, 131.f,
                          29.f, kInterBold, "#FFFFFF", duration, -14.f));

    Json titleGlow = text("p6_title_glow", "Too Big to Control", 150.f, 222.f,
                          84.f, kInterBlack, "#8DEBFF", duration, -18.f,
                          Json::array(), Json::array(), 0.58f, "screen");
    titleGlow["effects"] = Json::array({effectGlow(26.f, 1.25f, "#5DE5FF"),
                                        effectBloom(0.52f, 30.f, 0.65f)});
    layers.push_back(std::move(titleGlow));
    Json title = text("p6_title", "Too Big to Control", 150.f, 222.f, 84.f,
                      kInterBlack, "#F7F5EE", duration, -24.f);
    title["effects"] = Json::array({effectChromatic(1.5f, -1.5f)});
    layers.push_back(std::move(title));
    layers.push_back(text("p6_subtitle", "CHAPTER FIVE  /  THE CONTROL PROBLEM",
                          154.f, 362.f, 17.f, kMono, "#B9D8DE", duration, -24.f));

    // Tabular figures are enforced by the mono face and by three strings with
    // identical advance. The verifier samples 000 / 084 / 100 at the same x.
    layers.push_back(text("p6_counter", "084", 1510.f, 128.f, 64.f, kMono,
                          "#F7F5EE", duration, -24.f));
    layers.push_back(text("p6_counter_label", "PEOPLE CURED  /  100", 1514.f,
                          198.f, 15.f, kMono, "#B9D8DE", duration, -24.f));
    layers.push_back(rect("p6_counter_rule", 1512.f, 230.f, 286.f, 3.f,
                          "#E62E2D", 0.95f, -24.f));

    return envelope("parity_06_crt_hud_counter", duration, std::move(layers),
                    cameraAt(1158.06f, 8.f, false), driftSamples(duration, 3.f, 2.f, 0.06f),
                    nullptr);
}

// ─────────────────────────────────────────────────────────────── PARITY_07
Json buildDeterministicScrub(int duration) {
    Json layers = Json::array();
    // Shape linear-gradient fills currently render as the clear colour in
    // this build; the image layer is stable and carries a pre-dithered ramp.
    Json gradient = image("p7_gradient", kP7Gradient, -90.f, -50.f, 2100.f, 1180.f,
                          100.f, duration);
    gradient["effects"] = Json::array({effectNoise(0.006f, 7707, 1.0f, true)});
    layers.push_back(std::move(gradient));

    Json marker = rounded("p7_marker", 300.f, 470.f, 220.f, 220.f, 110.f,
                          "#63D6E3", 0.96f, 20.f);
    marker["animation"] = Json{{"tracks", Json::array({
        track("position_x", Json::array({key(0, -420.0), key(duration - 1, 420.0)}),
              "in_out_sine"),
        track("scale", Json::array({key(0, 0.55), key(75, 1.0),
                                    key(duration - 1, 0.55)}), "in_out_sine")})}};
    layers.push_back(std::move(marker));
    layers.push_back(text("p7_label", "FRAME 104  /  DETERMINISTIC SCRUB",
                          580.f, 560.f, 30.f, kMono, "#071015", duration, 10.f));
    layers.push_back(text("p7_note", "t = 3.450 s  ·  sequential == direct seek",
                          580.f, 610.f, 18.f, kMono, "#13242C", duration, 10.f));

    return envelope("parity_07_deterministic_scrub", duration, std::move(layers),
                    cameraAt(1158.06f, 8.f, false), driftSamples(duration, 2.f, 1.f, 0.04f),
                    nullptr);
}

}  // namespace

const char* documentaryParityName(DocumentaryParityRecipe recipe) {
    switch (recipe) {
        case DocumentaryParityRecipe::MacroLcdTypewriter:
            return "parity_01_macro_lcd_typewriter";
        case DocumentaryParityRecipe::KineticWhipBars:
            return "parity_02_kinetic_whip_bars";
        case DocumentaryParityRecipe::RackFocusStack:
            return "parity_03_rack_focus_stack";
        case DocumentaryParityRecipe::ParticleRainOcclusion:
            return "parity_04_particle_rain_occlusion";
        case DocumentaryParityRecipe::UiCardPanReveal:
            return "parity_05_ui_card_pan_reveal";
        case DocumentaryParityRecipe::CrtHudCounter:
            return "parity_06_crt_hud_counter";
        case DocumentaryParityRecipe::DeterministicScrub:
            return "parity_07_deterministic_scrub";
    }
    return "parity_unknown";
}

const char* documentaryParityTestId(DocumentaryParityRecipe recipe) {
    switch (recipe) {
        case DocumentaryParityRecipe::MacroLcdTypewriter: return "PARITY_01";
        case DocumentaryParityRecipe::KineticWhipBars: return "PARITY_02";
        case DocumentaryParityRecipe::RackFocusStack: return "PARITY_03";
        case DocumentaryParityRecipe::ParticleRainOcclusion: return "PARITY_04";
        case DocumentaryParityRecipe::UiCardPanReveal: return "PARITY_05";
        case DocumentaryParityRecipe::CrtHudCounter: return "PARITY_06";
        case DocumentaryParityRecipe::DeterministicScrub: return "PARITY_07";
    }
    return "PARITY_UNKNOWN";
}

std::array<DocumentaryParityRecipe, 7> allDocumentaryParityRecipes() {
    return {DocumentaryParityRecipe::MacroLcdTypewriter,
            DocumentaryParityRecipe::KineticWhipBars,
            DocumentaryParityRecipe::RackFocusStack,
            DocumentaryParityRecipe::ParticleRainOcclusion,
            DocumentaryParityRecipe::UiCardPanReveal,
            DocumentaryParityRecipe::CrtHudCounter,
            DocumentaryParityRecipe::DeterministicScrub};
}

void DocumentaryParitySpec::validate() const {
    if (fps != 30) fail("fps must be 30");
    if (durationFrames < 60 || durationFrames > 300)
        fail("durationFrames must be in [60,300] (max 10 s at 30 fps)");
    if (outputName.find('\n') != std::string::npos)
        fail("outputName must be a single line");
}

std::string DocumentaryParitySpec::planName() const {
    return std::string(documentaryParityName(recipe)) + "_v1";
}

std::string DocumentaryParitySpec::outputStem() const {
    return outputName.empty() ? planName() + ".mp4" : outputName;
}

nlohmann::json buildDocumentaryParityPlan(const DocumentaryParitySpec& spec) {
    spec.validate();
    const int duration = spec.durationFrames;
    nlohmann::json plan;
    switch (spec.recipe) {
        case DocumentaryParityRecipe::MacroLcdTypewriter:
            plan = buildMacroLcdTypewriter(duration);
            break;
        case DocumentaryParityRecipe::KineticWhipBars:
            plan = buildKineticWhipBars(duration);
            break;
        case DocumentaryParityRecipe::RackFocusStack:
            plan = buildRackFocusStack(duration);
            break;
        case DocumentaryParityRecipe::ParticleRainOcclusion:
            plan = buildParticleRainOcclusion(duration);
            break;
        case DocumentaryParityRecipe::UiCardPanReveal:
            plan = buildUiCardPanReveal(duration);
            break;
        case DocumentaryParityRecipe::CrtHudCounter:
            plan = buildCrtHudCounter(duration);
            break;
        case DocumentaryParityRecipe::DeterministicScrub:
            plan = buildDeterministicScrub(duration);
            break;
    }
    plan["job_id"] = spec.planName();
    plan["output"] = Json{{"path", spec.outputStem()}, {"format", "mp4"},
                          {"codec", "h264"}};
    return plan;
}

}  // namespace chronontemplate::web
