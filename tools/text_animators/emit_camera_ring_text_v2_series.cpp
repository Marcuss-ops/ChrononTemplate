// Native C++ authoring for CameraRing_Text clips 07-12.
//
// The six reference clips (01-06) live in
// Chronon3d/docs/evidence/camera-ring-text-drive-20261108/. Every recipe here
// copies their stack exactly — 132 px lowercase text, dark vignetted plate,
// 64-tap camera ring, light.sdf_bevel, generate.noise, bezier push-in, fade
// and tracking settle — and changes only the phrase, palette, duration and
// the ring's outer/blur/chroma/stretch values. Plans are pure RenderPlan V3
// data built here in C++; Python is only the render/upload driver.
//
// Usage:
//   chronontemplate_emit_camera_ring_text_v2_series <output-dir> [assets-root]
//
// Writes six *.plan.json files plus series.json (the single source of truth
// for ids, durations, fonts and output names consumed by the render driver).

#include <nlohmann/json.hpp>

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
    std::array<double, 4> ring;  // outer, blur, chroma, stretch
    const char* note;
};

const std::vector<Recipe>& recipes() {
    static const std::vector<Recipe> kRecipes = {
        {7, "Ogni_Dettaglio", "ogni dettaglio conta",
         "SF-Pro-Display-Semibold.otf", "#DDF8FF",
         {0.002, 0.01, 0.016, 1.0}, 300, {0.60, 0.026, 0.006, 1.15},
         "SF Pro Semibold · blu notte · camera ring largo"},
        {8, "Centro_Nitido", "centro nitido, bordi morbidi",
         "DMSans-Bold.ttf", "#FFE7CF",
         {0.026, 0.004, 0.01, 1.0}, 240, {0.60, 0.024, 0.008, 1.30},
         "DM Sans Bold · rosso cupo · bordo caldo"},
        {9, "Ogni_Dettaglio_A_Fuoco", "ogni dettaglio a fuoco",
         "SF-Pro-Display-Bold.otf", "#E9FFF8",
         {0.003, 0.024, 0.016, 1.0}, 180, {0.62, 0.022, 0.008, 0.90},
         "SF Pro Bold · verde profondo · fuoco stretto"},
        {10, "Resta_Ancora", "resta ancora un po'",
         "PlayfairDisplay-MediumItalic.ttf", "#F4C98B",
         {0.06, 0.032, 0.016, 1.0}, 240, {0.60, 0.018, 0.006, 1.15},
         "Playfair italico · ambra calda · alone morbido"},
        {11, "Guardala_Due_Volte", "guardala due volte",
         "DMSans-Bold.ttf", "#6FFFE9",
         {0.02, 0.004, 0.045, 1.0}, 180, {0.60, 0.030, 0.016, 1.45},
         "DM Sans Bold · viola · cromia alta"},
        {12, "Pulito_Preciso", "pulito. preciso. a fuoco.",
         "SF-Pro-Display-Semibold.otf", "#EAF4FF",
         {0.01, 0.028, 0.048, 1.0}, 210, {0.60, 0.024, 0.006, 0.85},
         "SF Pro Semibold · blu freddo · pulito e centrato"},
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
           std::to_string(seconds) + "s_v2.mp4";
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

json buildPlan(const Recipe& r) {
    if (r.frames <= 0 || r.frames > MAX_FRAMES) {
        throw std::runtime_error("recipe " + std::to_string(r.index) +
                                 " is not within 1..300 frames");
    }
    const std::string id = "camera_ring_text_" +
                           (r.index < 10 ? std::string("0") : std::string()) +
                           std::to_string(r.index) + "_" + lower(r.slug);
    const std::string titleId = lower(r.slug) + "_title";

    const json bevel = json::array({
        catalogParam("bevel_width", 16.0),
        catalogParam("bevel_height", 12.0),
        catalogParam("rim_width", 3.0),
        catalogParam("rim_intensity", 0.75),
        catalogParam("highlight", 0.65),
        catalogParam("shade", 0.42),
        catalogParam("light_angle", -135.0),
        catalogParam("light_elevation", 38.0),
        catalogParam("shadow_distance", 12.0),
        catalogParam("shadow_softness", 6.0),
        catalogParam("shadow_opacity", 0.75),
    });

    const json cameraRing = json{
        {"type", "camera_ring"},
        {"center", pair(0.5, 0.5)},
        {"axis_scale", pair(1.85, 0.72)},
        {"inner_radius", 0.1},
        {"outer_radius", r.ring[0]},
        {"max_blur_radius", r.ring[1]},
        {"chroma_dispersion", r.ring[2]},
        {"anamorphic_stretch", r.ring[3]},
        {"samples", RING_SAMPLES},
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

    plan["layers"].push_back(json{
        {"id", titleId},
        {"type", "text"},
        {"text", r.text},
        {"size", pair(WIDTH, HEIGHT)},
        {"position", json::array({WIDTH / 2.0, HEIGHT / 2.0})},
        {"start_frame", 0},
        {"duration_frames", r.frames},
        {"style", json{{"font", std::string("assets/fonts/") + r.font},
                       {"font_size", FONT_SIZE},
                       {"fill", r.fill}}},
        {"effects", json::array({cameraRing, json{
            {"type", "catalog"}, {"effect_id", "light.sdf_bevel"}, {"params", bevel},
        }})},
        {"animation", json{{"tracks", json::array({
            json{
                {"property", "scale"},
                {"easing", "bezier"},
                {"bezier_curve", json::array({0.35, 0.7, 0.2, 1.0})},
                {"keyframes", json::array({keyframe(1, pair(0.94, 0.94)),
                                           keyframe(91, pair(1.0, 1.0))})},
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
                                           keyframe(r.frames - 1, 0.0)})},
            }})},
        }})},
    });

    plan["layers"].push_back(json{
        {"id", "film_grain"},
        {"type", "color"},
        {"color", color(0, 0, 0, 1)},
        {"size", pair(WIDTH, HEIGHT)},
        {"position", pair(0, 0)},
        {"start_frame", 0},
        {"duration_frames", r.frames},
        {"opacity", 0.006},
        {"blend_mode", "screen"},
        {"effects", json::array({json{
            {"type", "catalog"}, {"effect_id", "generate.noise"},
            {"params", json::array({catalogParam("amount", 0.85)})},
        }})},
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
    require(plan.at("layers").size() == 3, id + ": expected backdrop/title/grain");
    require(plan.at("output").at("path") == videoName(r), id + ": output name mismatch");
    const std::string out = plan.at("output").at("path").get<std::string>();
    require(out.size() > 8 && out.substr(out.size() - 7) == "_v2.mp4",
            id + ": output is not a v2 mp4");
    require(out.find("_1920x1080_") != std::string::npos, id + ": output misses canvas tag");

    const json& title = plan.at("layers").at(1);
    require(title.at("type") == "text", id + ": title is not a text layer");
    require(title.at("style").at("font_size") == FONT_SIZE, id + ": font is not 132 px");
    require(title.at("style").at("font") == std::string("assets/fonts/") + r.font,
            id + ": font path mismatch");
    require(title.at("effects").size() == 2, id + ": expected camera ring + bevel");

    const json& ring = title.at("effects").at(0);
    require(ring.at("type") == "camera_ring", id + ": camera_ring missing");
    require(ring.at("samples") == RING_SAMPLES, id + ": camera ring is not 64 tap");
    require(ring.at("axis_scale").at(0) == 1.85 && ring.at("axis_scale").at(1) == 0.72,
            id + ": ring axis mismatch");
    require(ring.at("outer_radius") == r.ring[0], id + ": ring outer mismatch");

    const json& bevel = title.at("effects").at(1);
    require(bevel.at("effect_id") == "light.sdf_bevel", id + ": bevel missing");
    require(bevel.at("params").size() == 11, id + ": bevel does not have 11 params");

    require(title.contains("text_animators") && title.at("text_animators").size() == 1,
            id + ": tracking animator missing");
    require(title.at("text_animators").at(0).at("properties").at(0).at("property") ==
                "tracking",
            id + ": tracking animator is not tracking");

    const json& grain = plan.at("layers").at(2);
    require(grain.at("effects").at(0).at("effect_id") == "generate.noise",
            id + ": film grain missing");
    require(grain.at("opacity") == 0.006, id + ": grain opacity mismatch");
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
            {"schema", "chronontemplate.camera-ring-text-v2-series.v1"},
            {"generator", "chronontemplate_emit_camera_ring_text_v2_series"},
            {"canvas", json{{"width", WIDTH}, {"height", HEIGHT}, {"fps", FPS}}},
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
