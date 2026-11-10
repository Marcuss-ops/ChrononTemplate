// Native C++ authoring for CameraRing_Text clips 07-12 (v6, clean ring).
//
// v6 keeps the halved bloom and pulls the camera ring back to a safe mask
// (0.09/0.64) with a controlled max radius, avoiding tile-sampler boxes.
//   - 6-mip RGBA16F pyramid, threshold 0.52, intensity 0.28-0.45
//   - camera ring inner 0.09 / outer 0.64, max blur 0.020-0.042
//   - ACES + exposure at the output boundary (applied by the render driver)
//   - center stays sharp; grain and motion are unchanged
//   - typographic apostrophe and thin spaces preserved from v3
//
// Plans are pure RenderPlan V3 data built here in C++; Python is only the
// render/verify/upload driver. Usage:
//   chronontemplate_emit_camera_ring_text_v6_clean <output-dir> [assets-root]

#include <nlohmann/json.hpp>

#include <algorithm>
#include <array>
#include <cctype>
#include <cmath>
#include <cstdint>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>

namespace fs = std::filesystem;
using json = nlohmann::ordered_json;

namespace {

constexpr int WIDTH = 1920;
constexpr int HEIGHT = 1080;
constexpr int FPS = 30;
constexpr int MAX_FRAMES = 300;  // 10 s at 30 fps
constexpr int FONT_SIZE = 132;
constexpr int RING_SAMPLES = 64;

struct Recipe {
    int index;
    const char* slug;
    const char* text;
    const char* font;
    const char* fill;
    std::array<double, 4> background;
    int frames;
    double ring_inner;
    double ring_outer;
    double ring_blur;
    double ring_chroma;
    double ring_stretch;
    const char* glow_color;
    double glow_radius;
    double glow_intensity;
    double atmo_radius;
    double atmo_intensity;
    double tracking_hold;
    const char* note;
};

const std::vector<Recipe>& recipes() {
    static const std::vector<Recipe> kRecipes = {
        {7, "Ogni_Dettaglio", "ogni dettaglio conta",
         "SF-Pro-Display-Semibold.otf", "#F8FCFF",
         {0.002, 0.01, 0.016, 1.0}, 300,
         0.10, 0.64, 0.024, 0.005, 1.15, "#7FD4FF", 34.0, 0.55,
         92.0, 0.30, 0.0,
         "SF Pro Semibold · blu notte · glow freddo su due scale"},
        {8, "Centro_Nitido", "centro nitido, bordi morbidi",
         "DMSans-Bold.ttf", "#FFF6EA",
         {0.026, 0.004, 0.01, 1.0}, 240,
         0.14, 0.78, 0.045, 0.005, 1.25, "#FFB36B", 30.0, 0.50,
         94.0, 0.28, 0.0,
         "DM Sans Bold · rosso cupo · transizione larga, niente blocchi"},
        {9, "Ogni_Dettaglio_A_Fuoco", "ogni dettaglio a fuoco",
         "SF-Pro-Display-Bold.otf", "#F4FFFB",
         {0.003, 0.024, 0.016, 1.0}, 180,
         0.12, 0.66, 0.022, 0.006, 0.92, "#5CFFC9", 32.0, 0.55,
         88.0, 0.30, 0.0,
         "SF Pro Bold · verde profondo · alone menta e fuoco stretto"},
        {10, "Resta_Ancora", "resta ancora un po\u2019",
         "PlayfairDisplay-MediumItalic.ttf", "#F8DDB4",
         {0.06, 0.032, 0.016, 1.0}, 240,
         0.14, 0.70, 0.016, 0.004, 1.10, "#FFB35C", 26.0, 0.40,
         90.0, 0.22, 0.0,
         "Playfair italico · ambra calda · apostrofo tipografico"},
        {11, "Guardala_Due_Volte", "guardala due volte",
         "DMSans-Bold.ttf", "#FFFFFF",
         {0.02, 0.004, 0.045, 1.0}, 180,
         0.12, 0.70, 0.004, 0.008, 1.30, "#3FFFE4", 38.0, 0.65,
         96.0, 0.38, 0.0,
         "DM Sans Bold · viola · core bianco, alone ciano"},
        {12, "Pulito_Preciso", "pulito.\u2009preciso.\u2009a\u2009fuoco.",
         "SF-Pro-Display-Semibold.otf", "#F7FAFF",
         {0.01, 0.028, 0.048, 1.0}, 210,
         0.12, 0.66, 0.022, 0.004, 0.90, "#8CC8FF", 30.0, 0.50,
         90.0, 0.28, -0.4,
         "SF Pro Semibold · blu freddo · punteggiatura serrata"},
    };
    return kRecipes;
}

json color(double r, double g, double b, double a = 1.0) {
    return json::array({r, g, b, a});
}

json pair(double x, double y) { return json::array({x, y}); }

json keyframe(int frame, const json& value) {
    return json{{"frame", frame}, {"value", value}};
}

json catalogParam(const char* name, double value) {
    return json{{"param", name}, {"value", value}};
}

std::string videoName(const Recipe& r) {
    const int seconds = static_cast<int>(std::lround(r.frames / static_cast<double>(FPS)));
    return "CameraRing_Text_" + (r.index < 10 ? std::string("0") : std::string()) +
           std::to_string(r.index) + "_" + r.slug + "_1920x1080_" +
           std::to_string(seconds) + "s_v6.mp4";
}

std::string planName(const Recipe& r) {
    return (r.index < 10 ? std::string("0") : std::string()) + std::to_string(r.index) +
           "_" + r.slug + ".plan.json";
}

std::string lower(std::string value) {
    for (char& c : value) c = static_cast<char>(std::tolower(static_cast<unsigned char>(c)));
    return value;
}

std::string clipId(const Recipe& r) {
    return (r.index < 10 ? std::string("0") : std::string()) + std::to_string(r.index) +
           "_" + lower(r.slug);
}

json bloomAnimation(const Recipe& r, double opacity_target) {
    json opacity = json::array({keyframe(0, 0.0), keyframe(12, opacity_target)});
    const std::array<int, 10> flicker_frames{36, 54, 72, 90, 108, 126, 150, 174, 198, 222};
    const std::array<double, 10> flicker_gain{0.97, 1.03, 0.985, 1.02, 0.99,
                                              1.015, 0.975, 1.025, 0.99, 1.01};
    for (std::size_t i = 0; i < flicker_frames.size(); ++i) {
        if (flicker_frames[i] < r.frames - 2)
            opacity.push_back(keyframe(flicker_frames[i], opacity_target * flicker_gain[i]));
    }
    opacity.push_back(keyframe(r.frames - 1, opacity_target));
    return json{{"tracks", json::array({
        json{{"property", "scale"},
             {"easing", "bezier"},
             {"bezier_curve", json::array({0.35, 0.7, 0.2, 1.0})},
             {"keyframes", json::array({keyframe(1, pair(0.94, 0.94)),
                                        keyframe(91, pair(1.0, 1.0)),
                                        keyframe(r.frames - 1, pair(1.012, 1.012))})}},
        json{{"property", "position"},
             {"easing", "linear"},
             {"keyframes", json::array({keyframe(1, pair(WIDTH / 2.0, HEIGHT / 2.0)),
                                        keyframe(91, pair(WIDTH / 2.0, HEIGHT / 2.0)),
                                        keyframe(r.frames - 1, pair(WIDTH / 2.0 + 2.0,
                                                                    HEIGHT / 2.0 - 1.0))})}},
        json{{"property", "opacity"}, {"easing", "out_cubic"}, {"keyframes", opacity}},
    })}};
}

json bloomTracking(const Recipe& r) {
    return json::array({json{
        {"id", "tracking_settle"},
        {"selectors", json::array({json{
            {"unit", "line"}, {"shape", "square"}, {"order", "forward"},
            {"combine", "replace"}, {"exclude_spaces", true},
        }})},
        {"properties", json::array({json{
            {"property", "tracking"},
            {"easing", "linear"},
            {"keyframes", json::array({keyframe(0, 8.0), keyframe(24, 0.0),
                                       keyframe(r.frames - 1, r.tracking_hold)})},
        }})},
    }});
}

json makeBloomLayer(const Recipe& r, const std::string& id) {
    const double threshold = 0.52;
    const double radius = std::min(96.0, r.atmo_radius);
    const double intensity = std::clamp(r.glow_intensity * 0.68, 0.28, 0.45);
    return json{
        {"id", id},
        {"type", "text"},
        {"text", r.text},
        {"size", pair(WIDTH, HEIGHT)},
        {"position", pair(WIDTH / 2.0, HEIGHT / 2.0)},
        {"start_frame", 0},
        {"duration_frames", r.frames},
        // Additive, not screen: the halo may exceed 1.0 and only the output
        // transform is allowed to compress it.
        {"blend_mode", "add"},
        {"style", json{
            {"font", std::string("assets/fonts/") + r.font},
            {"font_size", FONT_SIZE},
            {"fill", r.glow_color},
        }},
        // The native bloom pass requires exactly one effect on its carrier.
        {"effects", json::array({json{
            {"type", "bloom"},
            {"threshold", threshold},
            {"radius", radius},
            {"intensity", intensity},
        }})},
        {"animation", bloomAnimation(r, 0.86)},
        {"text_animators", bloomTracking(r)},
    };
}

json buildPlan(const Recipe& r) {
    if (r.frames <= 0 || r.frames > MAX_FRAMES) {
        throw std::runtime_error("recipe " + std::to_string(r.index) +
                                 " is not within 1..300 frames");
    }
    const std::string id = "camera_ring_text_" +
                           (r.index < 10 ? std::string("0") : std::string()) +
                           std::to_string(r.index) + "_" + lower(r.slug);
    const std::string titleId = lower(r.slug) + "_title";

    const json cameraRing = json{
        {"type", "camera_ring"},
        {"center", pair(0.5, 0.5)},
        {"axis_scale", pair(1.85, 0.72)},
        {"inner_radius", std::max(0.09, r.ring_inner * 0.85)},
        {"outer_radius", std::min(0.64, r.ring_outer * 0.85)},
        {"max_blur_radius", std::clamp(r.ring_blur * 1.8, 0.020, 0.042)},
        {"chroma_dispersion", std::clamp(r.ring_chroma * 1.5, 0.006, 0.012)},
        {"anamorphic_stretch", r.ring_stretch},
        {"samples", RING_SAMPLES},
    };


    const auto grainEffect = [] {
        return json{
            {"type", "catalog"},
            {"effect_id", "generate.noise"},
            {"params", json::array({catalogParam("amount", 0.85)})},
        };
    };

    json plan = {
        {"schema", "chronon.render-plan.v3"},
        {"version", 3},
        {"job_id", id},
        {"canvas", json{{"width", WIDTH}, {"height", HEIGHT}, {"fps_num", FPS},
                        {"fps_den", 1}, {"duration_frames", r.frames}}},
        {"layers", json::array()},
        {"output", json{{"path", videoName(r)}, {"format", "mp4"}, {"codec", "h264"}}},
    };

    plan["layers"].push_back(json{
        {"id", "backdrop"},
        {"type", "color"},
        {"color", json::array({r.background[0], r.background[1], r.background[2],
                               r.background[3]})},
        {"size", pair(WIDTH, HEIGHT)},
        {"position", pair(0, 0)},
        {"start_frame", 0},
        {"duration_frames", r.frames},
        {"effects", json::array({json{
            {"type", "vignette"}, {"radius", 0.68}, {"softness", 0.7},
            {"amount", 0.32}, {"color", color(0, 0, 0, 1)},
        }})},
    });


    plan["layers"].push_back(makeBloomLayer(r, titleId + "_bloom"));

    plan["layers"].push_back(json{
        {"id", titleId},
        {"type", "text"},
        {"text", r.text},
        {"size", pair(WIDTH, HEIGHT)},
        {"position", json::array({WIDTH / 2.0, HEIGHT / 2.0})},
        {"start_frame", 0},
        {"duration_frames", r.frames},
        {"style", json{
            {"font", std::string("assets/fonts/") + r.font},
            {"font_size", FONT_SIZE},
            {"fill", r.fill},
        }},
        {"effects", json::array({cameraRing})},
        {"animation", json{{"tracks", json::array({
            json{
                {"property", "scale"},
                {"easing", "bezier"},
                {"bezier_curve", json::array({0.35, 0.7, 0.2, 1.0})},
                {"keyframes", json::array({keyframe(1, pair(0.94, 0.94)),
                                           keyframe(91, pair(1.0, 1.0)),
                                           keyframe(r.frames - 1, pair(1.012, 1.012))})},
            },
            json{
                {"property", "position"},
                {"easing", "linear"},
                {"keyframes", json::array({keyframe(1, pair(WIDTH / 2.0, HEIGHT / 2.0)),
                                           keyframe(91, pair(WIDTH / 2.0, HEIGHT / 2.0)),
                                           keyframe(r.frames - 1, pair(WIDTH / 2.0 + 2.0,
                                                                       HEIGHT / 2.0 - 1.0))})},
            },
            json{
                {"property", "opacity"},
                {"easing", "out_cubic"},
                {"keyframes", json::array({keyframe(0, 0.0), keyframe(12, 1.0),
                                           keyframe(r.frames - 1, 1.0)})},
            },
        })}}},
        {"text_animators", json::array({json{
            {"id", "tracking_settle"},
            {"selectors", json::array({json{
                {"unit", "line"}, {"shape", "square"}, {"order", "forward"},
                {"combine", "replace"}, {"exclude_spaces", true},
            }})},
            {"properties", json::array({json{
                {"property", "tracking"},
                {"easing", "linear"},
                {"keyframes", json::array({keyframe(0, 8.0), keyframe(24, 0.0),
                                           keyframe(r.frames - 1, r.tracking_hold)})},
            }})},
        }})},
    });

    plan["layers"].push_back(json{
        {"id", "film_grain"},
        {"type", "color"},
        {"color", color(0, 0, 0, 1)},
        {"size", pair(WIDTH + 20, HEIGHT + 20)},
        {"position", pair(-10, -10)},
        {"start_frame", 0},
        {"duration_frames", r.frames},
        {"opacity", 0.012},
        {"blend_mode", "screen"},
        {"effects", json::array({grainEffect()})},
        {"animation", json{{"tracks", json::array({json{
            {"property", "position"},
            {"easing", "linear"},
            {"keyframes", json::array({keyframe(0, pair(-10, -10)),
                                       keyframe(r.frames - 1, pair(-8, -11))})},
        }})}}},
    });

    return plan;
}

void require(bool condition, const std::string& message) {
    if (!condition) throw std::runtime_error(message);
}

void validatePlan(const Recipe& r, const json& plan) {
    const std::string id = clipId(r);
    require(plan.at("schema") == "chronon.render-plan.v3", id + ": wrong schema");
    require(plan.at("version") == 3, id + ": wrong version");
    require(plan.at("canvas").at("width") == WIDTH, id + ": width is not 1920");
    require(plan.at("canvas").at("height") == HEIGHT, id + ": height is not 1080");
    require(plan.at("canvas").at("fps_num") == FPS, id + ": fps is not 30");
    require(plan.at("canvas").at("duration_frames") == r.frames, id + ": frame count mismatch");
    require(r.frames <= MAX_FRAMES, id + ": longer than 10 s");
    require(plan.at("layers").size() == 4,
            id + ": expected backdrop/bloom/title/film grain");
    require(plan.at("output").at("path") == videoName(r), id + ": output name mismatch");
    const std::string out = plan.at("output").at("path").get<std::string>();
    require(out.size() > 8 && out.substr(out.size() - 7) == "_v6.mp4",
            id + ": output is not a v6 mp4");
    require(out.find("_1920x1080_") != std::string::npos, id + ": output misses canvas tag");

    const json& bloom = plan.at("layers").at(1);
    require(bloom.at("type") == "text", id + ": bloom carrier is not text");
    require(bloom.at("blend_mode") == "add", id + ": bloom blend mismatch");
    require(bloom.at("style").at("fill") == std::string(r.glow_color),
            id + ": bloom fill mismatch");
    require(bloom.at("effects").size() == 1,
            id + ": bloom carrier must own exactly one effect");
    const json& bloomEffect = bloom.at("effects").at(0);
    require(bloomEffect.at("type") == "bloom", id + ": native bloom missing");
    require(bloomEffect.at("threshold") == 0.52, id + ": bloom threshold mismatch");
    require(bloomEffect.at("radius") == std::min(96.0, r.atmo_radius),
            id + ": bloom radius mismatch");
    require(bloomEffect.at("intensity") ==
                std::clamp(r.glow_intensity * 0.68, 0.28, 0.45),
            id + ": bloom intensity mismatch");
    require(bloom.contains("animation") && bloom.contains("text_animators"),
            id + ": bloom animation/tracking missing");

    const json& title = plan.at("layers").at(2);
    require(title.at("type") == "text", id + ": title is not a text layer");
    require(title.at("style").at("font_size") == FONT_SIZE, id + ": font is not 132 px");
    require(title.at("style").at("font") == std::string("assets/fonts/") + r.font,
            id + ": font path mismatch");
    require(title.at("effects").size() == 1,
            id + ": expected only the camera ring on the title");

    const json& ring = title.at("effects").at(0);
    require(ring.at("type") == "camera_ring", id + ": camera_ring missing");
    require(ring.at("samples") == RING_SAMPLES, id + ": camera ring is not 64 tap");
    require(ring.at("axis_scale").at(0) == 1.85 && ring.at("axis_scale").at(1) == 0.72,
            id + ": ring axis mismatch");
    require(ring.at("inner_radius") == std::max(0.09, r.ring_inner * 0.85),
            id + ": ring inner mismatch");
    require(ring.at("outer_radius") == std::min(0.64, r.ring_outer * 0.85),
            id + ": ring outer mismatch");
    require(ring.at("max_blur_radius") ==
                std::clamp(r.ring_blur * 1.8, 0.020, 0.042),
            id + ": ring blur mismatch");
    require(ring.at("chroma_dispersion") ==
                std::clamp(r.ring_chroma * 1.5, 0.006, 0.012),
            id + ": ring chroma mismatch");

    require(title.contains("text_animators") && title.at("text_animators").size() == 1,
            id + ": tracking animator missing");
    require(title.at("text_animators").at(0).at("properties").at(0).at("property") ==
                "tracking",
            id + ": tracking animator is not tracking");
    require(title.at("text_animators").at(0).at("properties").at(0)
                .at("keyframes").at(2).at("value") == r.tracking_hold,
            id + ": tracking hold mismatch");

    const json& tracks = title.at("animation").at("tracks");
    require(tracks.size() == 3, id + ": expected scale/position/opacity tracks");
    require(tracks.at(1).at("property") == "position", id + ": position drift missing");
    require(tracks.at(0).at("keyframes").at(2).at("value").at(0) > 1.0,
            id + ": scale drift missing");

    const json& filmGrain = plan.at("layers").at(3);
    require(filmGrain.at("blend_mode") == "screen", id + ": film grain blend mismatch");
    require(filmGrain.at("effects").at(0).at("type") == "catalog",
            id + ": film grain effect missing");
    require(filmGrain.at("effects").at(0).at("effect_id") == "generate.noise",
            id + ": film grain is not generate.noise");
    require(filmGrain.contains("animation"), id + ": film grain drift missing");
}

json seriesEntry(const Recipe& r, const fs::path& planPath) {
    const int seconds = static_cast<int>(std::lround(r.frames / static_cast<double>(FPS)));
    return json{
        {"id", clipId(r)},
        {"index", r.index},
        {"slug", r.slug},
        {"label", r.text},
        {"note", r.note},
        {"reference", "Chronon3d/docs/evidence/camera-ring-text-drive-20261108/"
                      "camera_ring_text_" + (r.index - 6 < 10 ? std::string("0") : std::string()) +
                      std::to_string(r.index - 6) + "_*_v2.mp4"},
        {"text", r.text},
        {"font", r.font},
        {"font_size", FONT_SIZE},
        {"fill", r.fill},
        {"glow_color", r.glow_color},
        {"bloom_threshold", 0.52},
        {"bloom_radius", std::min(96.0, r.atmo_radius)},
        {"bloom_intensity", std::clamp(r.glow_intensity * 0.68, 0.28, 0.45)},
        {"ring_inner", std::max(0.09, r.ring_inner * 0.85)},
        {"ring_outer", std::min(0.64, r.ring_outer * 0.85)},
        {"ring_blur", std::clamp(r.ring_blur * 1.8, 0.020, 0.042)},
        {"ring_chroma", std::clamp(r.ring_chroma * 1.5, 0.006, 0.012)},
        {"tone_map", "aces"},
        {"exposure", 1.0},
        {"background_rgb", json::array({r.background[0], r.background[1], r.background[2]})},
        {"frames", r.frames},
        {"duration_s", seconds},
        {"plan", "plans/" + planPath.filename().string()},
        {"mp4", "mp4/" + videoName(r)},
        {"drive_name", videoName(r)},
    };
}

}  // namespace

int main(int argc, char** argv) {
    try {
        if (argc < 2 || argc > 3) {
            std::cerr << "usage: " << argv[0]
                      << " <output-dir> [assets-root]\n";
            return 2;
        }
        const fs::path outDir = argv[1];
        const fs::path assetsRoot = argc == 3 ? fs::path(argv[2]) : fs::path();
        fs::create_directories(outDir);

        json series = {
            {"schema", "chronontemplate.camera-ring-text-v6-clean-series.v1"},
            {"generator", "chronontemplate_emit_camera_ring_text_v6_clean"},
            {"canvas", json{{"width", WIDTH}, {"height", HEIGHT}, {"fps", FPS}}},
            {"recipe", json{{"ring", "bilinear 8px tile sampling"},
                            {"bloom", "native 6-mip RGBA16F pyramid, threshold 0.52, intensity 0.28-0.45"},
                            {"ring", "inner 0.09 / outer 0.64, max blur 0.020-0.042"},
                            {"grain", "catalog film grain over title, midtone weighted, 2px drift"},
                            {"motion", "push-in + 2px lateral drift"}}},
            {"clips", json::array()},
        };

        for (const Recipe& r : recipes()) {
            const fs::path planPath = outDir / planName(r);
            json plan = buildPlan(r);
            validatePlan(r, plan);
            if (!assetsRoot.empty()) {
                const fs::path font = assetsRoot / "assets" / "fonts" / r.font;
                require(fs::is_regular_file(font), "missing font: " + font.string());
            }
            std::ofstream handle(planPath);
            require(handle.good(), "cannot write " + planPath.string());
            handle << plan.dump(2) << '\n';
            handle.close();
            require(handle.good(), "failed writing " + planPath.string());

            series["clips"].push_back(seriesEntry(r, planPath));
            std::cout << planPath.string() << "  " << r.frames << "f  "
                      << videoName(r) << '\n';
        }

        const fs::path seriesPath = outDir / "series.json";
        std::ofstream handle(seriesPath);
        require(handle.good(), "cannot write " + seriesPath.string());
        handle << series.dump(2) << '\n';
        handle.close();
        std::cout << seriesPath.string() << "  " << series["clips"].size()
                  << " clips, all authored in C++\n";
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "camera-ring text series: " << error.what() << '\n';
        return 1;
    }
}
