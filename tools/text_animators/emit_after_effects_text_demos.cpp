// Emits six 1920x1080 / 30 fps RenderPlan V3 canaries for the After Effects
// text-parity discussion. Each plan isolates one native capability of the
// Chronon3D text lane:
//
//   01 range selectors     smooth reveal frontier + travelling band + wiggly drift
//   02 liquid melt         wiggly-selector dissolve driven by opacity/blur/scale
//   03 multi stroke        three concentric native text strokes + laser sweep
//   04 contact shadow      gel surface, soft glyph fusion, cast shadow, moving light
//   05 velocity blur       180-degree motion blur on a fast text move
//   06 kinetic tracking    per-run tracking animation with a wiggly accent
//
// The emitter only writes plans; Chronon3D owns shaping, rasterization and
// pixels. It deliberately uses only properties the GPU text lane can express
// (fill, opacity, blur, tracking, rotation, gel light, layer motion blur).
#include <nlohmann/json.hpp>

#include <array>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <string>
#include <vector>

using json = nlohmann::ordered_json;
namespace fs = std::filesystem;

namespace {

constexpr int kW = 1920;
constexpr int kH = 1080;
constexpr int kFps = 30;
constexpr int kFrames = 180;
constexpr const char* kHead = "assets/fonts/Inter-ExtraBold.ttf";
constexpr const char* kBody = "assets/fonts/Inter-Regular.ttf";

json kf(int frame, double value) { return {{"frame", frame}, {"value", value}}; }

json kfColor(int frame, std::array<double, 4> color) {
    return {{"frame", frame}, {"value", json::array({color[0], color[1], color[2], color[3]})}};
}

json kfVec3(int frame, std::array<double, 3> value) {
    return {{"frame", frame}, {"value", json::array({value[0], value[1], value[2]})}};
}

json track(const std::string& property, json keyframes, const std::string& easing = "linear") {
    return {{"property", property}, {"easing", easing}, {"keyframes", std::move(keyframes)}};
}

json animatorProperty(const std::string& property, json keyframes) {
    return {{"property", property}, {"easing", "linear"}, {"keyframes", std::move(keyframes)}};
}

json selector(const std::string& id, const char* unit, const char* shape, json start,
              json end, const char* order = "forward", json extras = json::object()) {
    json value = {
        {"id", id},
        {"unit", unit},
        {"shape", shape},
        {"order", order},
        {"combine", "replace"},
        {"exclude_spaces", true},
        {"start", {{"easing", "linear"}, {"keyframes", std::move(start)}}},
        {"end", {{"easing", "linear"}, {"keyframes", std::move(end)}}},
    };
    for (auto& [key, item] : extras.items()) value[key] = item;
    return value;
}

json fullSelector(const std::string& id, const char* unit = "glyph") {
    return selector(id, unit, "square", json::array({kf(0, 0)}), json::array({kf(0, 100)}));
}

json animator(const std::string& id, json selectors, json properties) {
    return {{"id", id}, {"selectors", std::move(selectors)}, {"properties", std::move(properties)}};
}

std::array<double, 4> hexRgba(const std::string& hex, double alpha = 1.0) {
    const auto channel = [&](std::size_t offset) {
        return static_cast<double>(std::stoi(hex.substr(offset, 2), nullptr, 16)) / 255.0;
    };
    return {channel(1), channel(3), channel(5), alpha};
}

json rgbaArray(const std::string& hex, double alpha = 1.0) {
    const auto c = hexRgba(hex, alpha);
    return json::array({c[0], c[1], c[2], c[3]});
}

json glow(double radius, double intensity, const std::string& hex, double alpha = 1.0) {
    return {{"type", "glow"},
            {"radius", radius},
            {"intensity", intensity},
            {"color", rgbaArray(hex, alpha)}};
}

json textStyle(const std::string& font, double size, const std::string& fill) {
    return {{"font", font},
            {"font_size", size},
            {"fill", fill},
            {"text_align", "center"},
            {"fit_mode", "shrink_only"},
            {"min_font_size", size * 0.45},
            {"max_font_size", size}};
}

json textLayer(const std::string& id, const std::string& text, double x, double y, double w,
               double h, const std::string& font, double size, const std::string& fill,
               int start = 0, int duration = kFrames) {
    return {{"id", id},
            {"type", "text"},
            {"text", text},
            {"size", {w, h}},
            {"position", {x, y}},
            {"start_frame", start},
            {"duration_frames", duration},
            {"style", textStyle(font, size, fill)}};
}

json planShell(const std::string& id) {
    return {
        {"schema", "chronon.render-plan.v3"},
        {"version", 3},
        {"job_id", id},
        {"canvas",
         {{"width", kW}, {"height", kH}, {"fps_num", kFps}, {"fps_den", 1},
          {"duration_frames", kFrames}}},
        {"layers", json::array()},
        {"output", {{"path", id + ".mp4"}, {"format", "mp4"}, {"codec", "h264"}}},
    };
}

void addBackdrop(json& plan, const std::string& accent, const std::string& number,
                 const std::string& caption) {
    json& layers = plan["layers"];
    layers.push_back({{"id", "backdrop"},
                      {"type", "shape"},
                      {"shape", {{"type", "rect"}, {"fill", rgbaArray("#03060C", 1.0)}}},
                      {"size", {kW, kH}},
                      {"position", {0, 0}},
                      {"start_frame", 0},
                      {"duration_frames", kFrames}});

    layers.push_back({
        {"id", "kicker"},
        {"type", "text"},
        {"text", "CHRONON3D  /  AFTER EFFECTS PARITY"},
        {"size", {900, 30}},
        {"position", {960, 82}},
        {"start_frame", 0},
        {"duration_frames", kFrames},
        {"style", textStyle(kBody, 20, "#6C8295")},
    });

    layers.push_back({
        {"id", "index"},
        {"type", "text"},
        {"text", number},
        {"size", {200, 30}},
        {"position", {1730, 82}},
        {"start_frame", 0},
        {"duration_frames", kFrames},
        {"style", textStyle(kHead, 20, accent)},
    });

    layers.push_back({
        {"id", "caption"},
        {"type", "text"},
        {"text", caption},
        {"size", {1500, 40}},
        {"position", {960, 986}},
        {"start_frame", 0},
        {"duration_frames", kFrames},
        {"style", textStyle(kBody, 22, "#8094A5")},
    });
}

json fadeTrack(int inStart, int inEnd, int outStart, int outEnd) {
    json keys = json::array({kf(0, 0)});
    if (inStart > 0) keys.push_back(kf(inStart, 0));
    keys.push_back(kf(inEnd, 1));
    keys.push_back(kf(outStart, 1));
    keys.push_back(kf(outEnd, 0));
    return track("opacity", std::move(keys));
}

json animationOf(json tracks) { return {{"tracks", std::move(tracks)}}; }

// 01 ── Range selectors: a smooth reveal frontier, a travelling band and a
// wiggly selector layered on the same run.
json rangeSelectorsPlan() {
    json plan = planShell("ae01_range_selectors");
    addBackdrop(plan, "#35D6FF", "01", "SMOOTH SELECTOR  /  TRAVELLING BAND  /  WIGGLY NOISE");

    json title = textLayer("range_selectors", "RANGE\nSELECTOR", 960, 505, 1600, 640, kHead, 160,
                           "#F2FBFF");
    title["style"]["stroke"] = {{"color", "#041018"}, {"width", 5}};
    title["style"]["glow"] = {{"radius", 30}, {"intensity", 0.35}, {"color", "#35D6FF"}};
    title["animation"] = animationOf(json::array({fadeTrack(0, 7, 168, 179)}));
    title["text_animators"] = json::array({
        // Suffix window: glyphs stay hidden until the frontier passes them.
        animator("reveal", json::array({selector("reveal_sel", "glyph", "smooth",
                                                json::array({kf(0, 0), kf(6, 0), kf(62, 100)}),
                                                json::array({kf(0, 100)}))}),
                 json::array({animatorProperty("opacity", json::array({kf(0, 0)}))})),
        // Travelling band: each glyph lifts and tilts while the band crosses it.
        animator("band", json::array({selector("band_sel", "glyph", "smooth",
                                              json::array({kf(0, 0), kf(40, 0), kf(142, 100)}),
                                              json::array({kf(0, 26), kf(40, 26), kf(142, 126)}))}),
                 json::array({animatorProperty("position_y", json::array({kf(0, -48)})),
                              animatorProperty("rotation", json::array({kf(0, -9)})),
                              animatorProperty("blur", json::array({kf(0, 5)}))})),
        // Wiggly selector: coherent per-glyph noise over the whole run.
        animator("wiggly", json::array({selector(
                              "wiggly_sel", "glyph", "wiggly",
                              json::array({kf(0, 0)}), json::array({kf(0, 100)}), "forward",
                              {{"wiggly_frequency", 5.5},
                               {"wiggly_amplitude", 0.62},
                               {"wiggly_seed", 17}})}),
                 json::array({animatorProperty("position_y", json::array({kf(0, 6)})),
                              animatorProperty("rotation", json::array({kf(0, 2.4)}))})),
    });

    plan["layers"].push_back(std::move(title));

    json note = textLayer("note", "u = i / (N-1)   ·   w = smoothstep(u, S, E)   ·   p(t) * w",
                          960, 728, 1500, 40, kBody, 22, "#5E7A8E");
    note["animation"] = animationOf(json::array({track("opacity", json::array({kf(0, 0), kf(40, 0), kf(70, 1)}))}));
    plan["layers"].push_back(std::move(note));
    return plan;
}

// 02 ── Liquid melt: the closest native analogue of a turbulent SDF dissolve.
// A wiggly selector gives every glyph its own organic clock; opacity, blur,
// scale and fill animate through the condense / hold / melt cycle.
json liquidMeltPlan() {
    json plan = planShell("ae02_liquid_melt");
    addBackdrop(plan, "#19E3C8", "02", "WIGGLY DISSOLVE  /  CONDENSE  /  MELT  /  HDR EDGE GLOW");

    json title = textLayer("liquid_melt", "LIQUID\nMELT", 960, 505, 1500, 620, kHead, 190,
                           "#CFFBFF");
    title["style"]["glow"] = {{"radius", 44}, {"intensity", 0.55}, {"color", "#19E3C8"}};
    // Layer effects on a text run are not safe on the GPU text lane: the
    // effect pass can suppress the run entirely. The native style glow above
    // is the supported HDR edge treatment here.
    title["animation"] = animationOf(json::array({fadeTrack(0, 5, 172, 179)}));
    title["text_animators"] = json::array({
        animator("melt", json::array({selector(
                              "melt_sel", "glyph", "wiggly",
                              json::array({kf(0, 0)}), json::array({kf(0, 100)}), "forward",
                              {{"wiggly_frequency", 4.2},
                               {"wiggly_amplitude", 0.78},
                               {"wiggly_seed", 23}})}),
                 json::array({
                     animatorProperty("opacity", json::array({kf(0, 0), kf(10, 0), kf(78, 1),
                                                              kf(126, 1), kf(176, 0)})),
                     animatorProperty("blur", json::array({kf(0, 30), kf(10, 30), kf(84, 0),
                                                           kf(126, 0), kf(176, 26)})),
                     animatorProperty("position_y", json::array({kf(0, 64), kf(10, 64), kf(84, 0),
                                                                kf(126, 0), kf(176, -54)})),
                     animatorProperty("scale", json::array({kf(0, 0.80), kf(10, 0.80), kf(84, 1.0),
                                                           kf(126, 1.0), kf(176, 0.92)})),
                     animatorProperty("fill_color", json::array({
                                                        kfColor(0, hexRgba("#19E3C8")),
                                                        kfColor(96, hexRgba("#FFFFFF")),
                                                        kfColor(176, hexRgba("#0C9BFF"))})),
                 })),
    });

    plan["layers"].push_back(std::move(title));

    json note = textLayer("note", "d'(x,y,t) = d(x,y) + FBM(x,y,t)   ·   alpha = p(t) * noise(i,t)",
                          960, 738, 1500, 40, kBody, 22, "#5E7A8E");
    note["animation"] = animationOf(json::array({track("opacity", json::array({kf(0, 0), kf(50, 0), kf(80, 1)}))}));
    plan["layers"].push_back(std::move(note));
    return plan;
}

json strokeTitle(const std::string& id, double strokeWidth, const std::string& strokeColor,
                 double glowRadius, const std::string& glowColor) {
    json layer = textLayer(id, "OUTLINE", 960, 512, 1500, 360, kHead, 214, "#05070D");
    layer["style"]["stroke"] = {{"color", strokeColor}, {"width", strokeWidth}};
    layer["effects"] = json::array({glow(glowRadius, 0.65, glowColor, 0.8)});
    return layer;
}

// 03 ── Multi-stroke: three native strokes on top of each other (wide blue
// halo, cyan mid stroke, bright fill) plus a laser sweep bar. Strokes are
// static per layer so the whole clip stays on the GPU text lane.
json multiStrokePlan() {
    json plan = planShell("ae03_multi_stroke_trim");
    addBackdrop(plan, "#00E5FF", "03", "CONCENTRIC STROKES  /  LASER SWEEP  /  NEON FILL");

    json outer = strokeTitle("stroke_outer", 26, "#1B3CFF", 40, "#1B3CFF");
    outer["opacity"] = 0.9;
    outer["animation"] = animationOf(json::array({track("scale", json::array({kf(0, 0.93), kf(48, 1.0)}), "out_cubic"),
                                                   fadeTrack(0, 10, 170, 179)}));
    plan["layers"].push_back(std::move(outer));

    json mid = strokeTitle("stroke_mid", 10, "#00E5FF", 22, "#00E5FF");
    mid["animation"] = animationOf(json::array({track("scale", json::array({kf(0, 0.96), kf(62, 1.0)}), "out_cubic"),
                                                 fadeTrack(18, 30, 170, 179)}));
    plan["layers"].push_back(std::move(mid));

    json fill = textLayer("fill", "OUTLINE", 960, 512, 1500, 360, kHead, 214, "#EAFDFF");
    fill["style"]["glow"] = {{"radius", 18}, {"intensity", 0.35}, {"color", "#9FF6FF"}};
    fill["animation"] = animationOf(json::array({track("opacity",
                                                        json::array({kf(0, 0), kf(86, 0), kf(116, 1), kf(170, 1), kf(179, 0)}),
                                                        "out_cubic")}));
    plan["layers"].push_back(std::move(fill));

    json sweep = {
        {"id", "laser_sweep"},
        {"type", "shape"},
        {"shape", {{"type", "rect"}, {"fill", rgbaArray("#DFFFFF", 0.95)}}},
        {"size", {360, 3}},
        {"position", {0, 0}},
        {"blend_mode", "add"},
        {"start_frame", 0},
        {"duration_frames", kFrames},
        {"animation",
         animationOf(json::array({
             track("position_x", json::array({kf(0, -1200), kf(24, -1200), kf(128, 1200)}), "in_out_cubic"),
             track("opacity", json::array({kf(0, 0), kf(24, 0), kf(34, 0.85), kf(120, 0.85), kf(140, 0)}),
                   "out_cubic"),
         }))},
    };
    plan["layers"].push_back(std::move(sweep));

    json note = textLayer("note", "stroke(d) = box(d - (0.5 - delta), omega)   ·   three passes",
                          960, 738, 1500, 40, kBody, 22, "#5E7A8E");
    note["animation"] = animationOf(json::array({track("opacity", json::array({kf(0, 0), kf(46, 0), kf(80, 1)}))}));
    plan["layers"].push_back(std::move(note));
    return plan;
}

// 04 ── Contact shadow: gel text with soft fusion, a real cast shadow and a
// moving gel light. Negative tracking lets neighbouring glyphs touch, so the
// shadow and the fused surface read as one mechanical block.
json contactShadowPlan() {
    json plan = planShell("ae04_contact_shadow");
    addBackdrop(plan, "#FF9A3D", "04", "GEL SURFACE  /  SOFT FUSION  /  MOVING LIGHT  /  CAST SHADOW");

    json title = textLayer("contact_shadow", "CONTACT", 960, 505, 1560, 380, kHead, 206,
                           "#8FE9FF");
    json& style = title["style"];
    style["gel_surface"] = true;
    style["gel_soft_fusion"] = true;
    style["gel_light"] = {{"azimuth_radians", -0.65}, {"elevation", 0.55}};
    style["shadow"] = {{"color", "#02080D"}, {"opacity", 0.55}, {"blur", 16}, {"offset", {10, 16}}};
    title["effects"] = json::array({glow(22, 0.4, "#FF9A3D", 0.55)});
    title["animation"] = animationOf(json::array({fadeTrack(0, 8, 170, 179)}));
    title["text_animators"] = json::array({
        animator("tracking", json::array({fullSelector("tracking_sel")}),
                 json::array({animatorProperty("tracking", json::array({kf(0, -16), kf(52, -16),
                                                                        kf(148, 6), kf(179, 0)}))})),
        animator("tilt", json::array({selector("tilt_sel", "glyph", "smooth",
                                              json::array({kf(0, 0), kf(34, 0), kf(150, 100)}),
                                              json::array({kf(0, 22), kf(34, 22), kf(150, 122)}), "from_center")}),
                 json::array({animatorProperty("rotation", json::array({kfVec3(0, {0, 24, 0})})),
                              animatorProperty("position_y", json::array({kf(0, -10)}))})),
        animator("sweep_light", json::array({fullSelector("light_sel")}),
                 json::array({animatorProperty("light_direction",
                                               json::array({kfVec3(0, {0.7, -0.6, 0.55}),
                                                            kfVec3(90, {0.1, -0.2, 0.9}),
                                                            kfVec3(179, {-0.7, -0.5, 0.5})}))})),
    });
    plan["layers"].push_back(std::move(title));

    json note = textLayer("note", "z(sample) > ray(z)   ·   8-step screen-space occlusion read",
                          960, 728, 1500, 40, kBody, 22, "#5E7A8E");
    note["animation"] = animationOf(json::array({track("opacity", json::array({kf(0, 0), kf(42, 0), kf(72, 1)}))}));
    plan["layers"].push_back(std::move(note));
    return plan;
}

// 05 ── Velocity blur: a fast pass across frame with a 180-degree shutter.
// Motion blur is a layer declaration, so the renderer samples the motion.
json velocityBlurPlan() {
    json plan = planShell("ae05_velocity_motion_blur");
    addBackdrop(plan, "#FF3D7F", "05", "180 DEGREE SHUTTER  /  VELOCITY BUFFER  /  NO STROBING");

    json title = textLayer("velocity", "VELOCITY", 960, 520, 1700, 340, kHead, 206, "#FFE9F2");
    title["style"]["glow"] = {{"radius", 38}, {"intensity", 0.65}, {"color", "#FF3D7F"}};
    title["effects"] = json::array({glow(46, 0.8, "#FF3D7F", 0.85)});
    title["motion_blur"] = {{"shutter_angle", 180}, {"samples", 16}};
    title["animation"] = animationOf(json::array({
                              track("position_x", json::array({kf(0, -780), kf(30, 0), kf(118, 0), kf(158, 840)}),
                                    "out_expo"),
                              track("opacity", json::array({kf(0, 0), kf(5, 1), kf(152, 1), kf(169, 0)}),
                                    "linear"),
                          }));
    plan["layers"].push_back(std::move(title));

    json note = textLayer("note", "v_shutter = (P_t - P_t-dt) * shutter / 360   ·   180 deg",
                          960, 738, 1500, 40, kBody, 22, "#5E7A8E");
    note["animation"] = animationOf(json::array({track("opacity", json::array({kf(0, 0), kf(36, 0), kf(66, 1)}))}));
    plan["layers"].push_back(std::move(note));
    return plan;
}

// 06 ── Kinetic tracking: one run re flows around its optical centre while a
// wiggly accent keeps individual glyphs alive.
json kineticTrackingPlan() {
    json plan = planShell("ae06_kinetic_tracking");
    addBackdrop(plan, "#B7FF4A", "06", "OPTICAL KERNING  /  CENTERED TRACKING  /  WIGGLY ACCENT");

    json title = textLayer("tracking", "TRACKING", 960, 512, 1720, 360, kHead, 194, "#F4FFE9");
    title["style"]["stroke"] = {{"color", "#07120A"}, {"width", 4}};
    title["style"]["glow"] = {{"radius", 26}, {"intensity", 0.3}, {"color", "#B7FF4A"}};
    title["animation"] = animationOf(json::array({fadeTrack(0, 6, 170, 179)}));
    title["text_animators"] = json::array({
        animator("tracking", json::array({fullSelector("tracking_sel")}),
                 json::array({animatorProperty("tracking", json::array({kf(0, 72), kf(18, 72),
                                                                        kf(72, -8), kf(104, -8),
                                                                        kf(146, 26), kf(179, 0)}))})),
        animator("wiggle", json::array({selector(
                             "wiggle_sel", "glyph", "wiggly",
                             json::array({kf(0, 0)}), json::array({kf(0, 100)}), "forward",
                             {{"wiggly_frequency", 4.8},
                              {"wiggly_amplitude", 0.55},
                              {"wiggly_seed", 31}})}),
                 json::array({animatorProperty("position_y", json::array({kf(0, 7)})),
                              animatorProperty("scale", json::array({kf(0, 1.015)})),
                              animatorProperty("rotation", json::array({kf(0, 1.4)}))})),
    });
    plan["layers"].push_back(std::move(title));

    json rule = {
        {"id", "baseline"},
        {"type", "shape"},
        {"shape", {{"type", "rect"}, {"fill", rgbaArray("#B7FF4A", 0.75)}}},
        {"size", {980, 3}},
        {"position", {0, 150}},
        {"start_frame", 0},
        {"duration_frames", kFrames},
        {"animation", animationOf(json::array({
                          track("scale_x", json::array({kf(0, 0), kf(24, 0), kf(96, 1)}), "out_cubic"),
                          track("opacity", json::array({kf(0, 0), kf(24, 0), kf(54, 1), kf(164, 1), kf(179, 0)}),
                                "linear"),
                      }))}};
    plan["layers"].push_back(std::move(rule));

    json note = textLayer("note", "x_i = sum(advance + tracking)   ·   anchor stays centred",
                          960, 738, 1500, 40, kBody, 22, "#5E7A8E");
    note["animation"] = animationOf(json::array({track("opacity", json::array({kf(0, 0), kf(44, 0), kf(74, 1)}))}));
    plan["layers"].push_back(std::move(note));
    return plan;
}

void writeJson(const fs::path& path, const json& value) {
    std::ofstream file(path);
    if (!file) throw std::runtime_error("cannot write " + path.string());
    file << value.dump(2) << '\n';
}

}// namespace

int main(int argc, char** argv) {
    const fs::path out = argc > 1 ? fs::path(argv[1]) : fs::path("out/after_effects_text_v1/plans");
    try {
        fs::create_directories(out);
        struct Demo {
            const char* id;
            const char* file;
            const char* feature;
            json plan;
        };
        std::vector<Demo> demos{
            {"ae01_range_selectors", "ae01_range_selectors.plan.json",
             "Range selectors: smooth reveal frontier, travelling band, wiggly selector",
             rangeSelectorsPlan()},
            {"ae02_liquid_melt", "ae02_liquid_melt.plan.json",
             "Liquid melt: wiggly-selector dissolve with opacity, blur, scale and fill",
             liquidMeltPlan()},
            {"ae03_multi_stroke_trim", "ae03_multi_stroke_trim.plan.json",
             "Multi-stroke trim: concentric native strokes plus a laser sweep",
             multiStrokePlan()},
            {"ae04_contact_shadow", "ae04_contact_shadow.plan.json",
             "Contact shadow: gel surface, soft fusion, cast shadow, moving light",
             contactShadowPlan()},
            {"ae05_velocity_motion_blur", "ae05_velocity_motion_blur.plan.json",
             "Velocity motion blur: 180-degree shutter on a fast text pass",
             velocityBlurPlan()},
            {"ae06_kinetic_tracking", "ae06_kinetic_tracking.plan.json",
             "Kinetic tracking: per-run tracking with a wiggly accent",
             kineticTrackingPlan()},
        };

        json manifest = {
            {"schema", "chronontemplate.after-effects-text-demos.v1"},
            {"canvas", {{"width", kW}, {"height", kH}}},
            {"fps", kFps},
            {"duration_frames", kFrames},
            {"duration_seconds", static_cast<double>(kFrames) / kFps},
            {"font_root", "assets/fonts"},
            {"plans", json::array()},
        };
        for (const auto& demo : demos) {
            writeJson(out / demo.file, demo.plan);
            manifest["plans"].push_back({{"id", demo.id},
                                         {"file", demo.file},
                                         {"feature", demo.feature},
                                         {"frames", kFrames},
                                         {"seconds", static_cast<double>(kFrames) / kFps}});
            std::cout << "emitted " << (out / demo.file).string() << '\n';
        }
        writeJson(out.parent_path() / "manifest.json", manifest);
        std::cout << "emitted " << (out.parent_path() / "manifest.json").string() << '\n';
    } catch (const std::exception& error) {
        std::cerr << "after-effects text demo emission failed: " << error.what() << '\n';
        return 1;
    }
    return 0;
}
