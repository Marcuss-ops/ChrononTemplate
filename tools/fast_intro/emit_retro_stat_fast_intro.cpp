#include "chronontemplate/fast_intro/FastIntroPack.hpp"
#include <nlohmann/json.hpp>

#include <cstdio>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <string>
#include <vector>

namespace fs = std::filesystem;
using Json = nlohmann::json;

namespace {

Json key(int frame, double value) {
    return {{"frame", frame}, {"value", value}};
}

Json key3(int frame, double x, double y, double z) {
    return {{"frame", frame}, {"value", {x, y, z}}};
}

Json track(const std::string& property, const Json& keyframes, const std::string& easing = "ease_out_cubic") {
    return {{"property", property}, {"easing", easing}, {"keyframes", keyframes}};
}

// hdr_rgba color stop for plan gradient fills (chronon.render-plan.v3).
Json colorStop(double position, const std::string& hex) {
    unsigned r = 0, g = 0, b = 0;
    if (hex.size() == 7 && hex[0] == '#')
        std::sscanf(hex.c_str(), "#%2x%2x%2x", &r, &g, &b);
    return {{"position", position},
            {"color", {r / 255.0, g / 255.0, b / 255.0, 1.0}}};
}

Json makePlan(const chronontemplate::fast_intro::RetroStatCollageSpec& spec) {
    Json plan;
    plan["schema"] = "chronon.render-plan.v3";
    plan["version"] = 3;
    plan["job_id"] = spec.name;
    plan["canvas"] = {
        {"width", static_cast<int>(spec.width)},
        {"height", static_cast<int>(spec.height)},
        {"fps_num", 30},
        {"fps_den", 1},
        {"duration_frames", spec.durationFrames}
    };

    Json layers = Json::array();
    const float cx = spec.width * 0.5f;
    const float cy = spec.height * 0.5f;

    // 1. Background Ground
    layers.push_back({
        {"id", spec.name + "_ground"},
        {"type", "color"},
        {"color", {0.05, 0.01, 0.01, 1.0}},
        {"size", {spec.width, spec.height}},
        {"position", {cx, cy}},
        {"start_frame", 0},
        {"duration_frames", spec.durationFrames}
    });

    // 2. Warm radial background: luminous yellow core, soft concentric
    //    orange bands and deep red edges (soft bands live in the gradient
    //    stops; the hard stroked rings and the technical grid are gone).
    Json glowStops = Json::array({
        colorStop(0.00, "#FFD24A"),
        colorStop(0.10, "#FFC12E"),
        colorStop(0.18, "#F79A16"),
        colorStop(0.26, "#EE7A10"),
        colorStop(0.34, "#F08A14"),
        colorStop(0.42, "#D95E0B"),
        colorStop(0.52, "#C24A08"),
        colorStop(0.62, "#B23A08"),
        colorStop(0.72, "#8E2206"),
        colorStop(0.85, "#5E0D04"),
        colorStop(1.00, "#0E0202")
    });
    const double glowSize = std::max(spec.width, spec.height) * 1.4;
    layers.push_back({
        {"id", spec.name + "_radial_glow"},
        {"type", "shape"},
        {"shape", {
            {"type", "ellipse"},
            {"fill", {{"enabled", true}, {"gradient", {
                {"type", "radial"},
                {"center", {0.5, 0.5}},
                {"radius", 0.5},
                {"color_stops", glowStops}
            }}}}
        }},
        {"size", {glowSize, glowSize}},
        {"position", {cx, cy - 20.f}},
        {"start_frame", 0},
        {"duration_frames", spec.durationFrames}
    });

    // 3. Era Title ("1990s")
    layers.push_back({
        {"id", spec.name + "_era"},
        {"type", "text"},
        {"text", spec.eraTitle},
        {"font", spec.font},
        {"font_size", spec.eraFontSize},
        {"color", "#F5F1EA"},
        {"position", {cx, cy}},
        {"start_frame", 0},
        {"duration_frames", 47},
        {"shadow", {
            {"color", "#1C0404"},
            {"opacity", 0.88},
            {"blur", 12.0},
            {"offset", {8.0, 14.0}}
        }},
        {"animation", {{"tracks", {
            track("scale", {key3(0, 1.0, 1.0, 1.0), key3(38, 1.14, 1.14, 1.0), key3(46, 1.45, 1.45, 1.0)}, "ease_in"),
            track("opacity", {key(0, 1.0), key(38, 1.0), key(46, 0.0)}, "ease_out")
        }}}}
    });

    // 4. Giant Statistic ("37.7 M") - frames 38 to 121: crosses the screen
    //    as a white mass, still overflows the borders at frame 60 (2.0s), is
    //    fully legible at frame 82 (2.75s) and lingers behind the collage.
    layers.push_back({
        {"id", spec.name + "_stat"},
        {"type", "text"},
        {"text", spec.statistic},
        {"font", spec.font},
        {"font_size", spec.statisticFontSize},
        {"color", "#F5F1EA"},
        {"position", {cx, cy}},
        {"start_frame", 38},
        {"duration_frames", 83}, // frames 38 to 121
        {"shadow", {
            {"color", "#1C0404"},
            {"opacity", 0.90},
            {"blur", 14.0},
            {"offset", {12.0, 16.0}}
        }},
        {"animation", {{"tracks", {
            track("scale", {key3(38, spec.statisticScaleIn, spec.statisticScaleIn, 1.0),
                            key3(48, 4.6, 4.6, 1.0),
                            key3(60, 2.7, 2.7, 1.0),
                            key3(72, 1.6, 1.6, 1.0),
                            key3(82, 1.0, 1.0, 1.0),
                            key3(121, 0.92, 0.92, 1.0)}, "ease_out"),
            track("position", {key3(38, cx + 320.0, cy + 140.0, 0.0),
                               key3(82, cx, cy, 0.0)}, "ease_out"),
            track("opacity", {key(38, 0.0), key(39, 1.0), key(82, 1.0), key(90, 0.75), key(108, 0.5), key(121, 0.0)}, "linear")
        }}}}
    });

    // 5. Character Ensemble Collage - frames 88 to end: extreme close-up
    //    pull-back that composes at 88% of the frame width.
    layers.push_back({
        {"id", spec.name + "_collage"},
        {"type", "image"},
        {"asset", spec.collagePath},
        {"size", {spec.width * spec.collageTargetWidthRatio, spec.height * 0.96f}},
        {"position", {cx, cy - 15.f}},
        {"start_frame", 88},
        {"duration_frames", spec.durationFrames - 88},
        {"animation", {{"tracks", {
            track("scale", {key3(88, spec.collageScaleIn, spec.collageScaleIn, 1.0),
                            key3(99, 2.4, 2.4, 1.0),
                            key3(120, 1.42, 1.42, 1.0),
                            key3(150, 1.04, 1.04, 1.0),
                            key3(162, 1.0, 1.0, 1.0),
                            key3(spec.durationFrames - 1, 1.0, 1.0, 1.0)}, "ease_out"),
            track("opacity", {key(88, 0.0), key(90, 1.0)}, "ease_out")
        }}}}
    });

    plan["layers"] = layers;
    return plan;
}

} // namespace

int main(int argc, char** argv) {
    const fs::path outDir = argc > 1
        ? argv[1]
        : "artifacts/retro_stat_fast_intro";

    try {
        fs::create_directories(outDir);

        chronontemplate::fast_intro::RetroStatCollageSpec spec;
        spec.name = "retro_stat_fast_intro";
        spec.eraTitle = "1990s";
        spec.statistic = "37.7 M";
        spec.closingTitle = "";
        spec.collagePath = "ChrononTemplate/assets/images/retro_collage.png";
        spec.font = "ChrononTemplate/assets/fonts/Impact.ttf";
        spec.durationFrames = 173;
        spec.width = 1920.f;
        spec.height = 1080.f;

        Json plan = makePlan(spec);
        const fs::path planPath = outDir / (spec.name + ".plan.json");
        std::ofstream out(planPath);
        if (!out) {
            std::cerr << "Could not open " << planPath << '\n';
            return 1;
        }
        out << plan.dump(2) << '\n';
        std::cout << "Successfully generated " << planPath << " with " 
                  << plan["layers"].size() << " layers.\n";
        return 0;
    } catch (const std::exception& e) {
        std::cerr << "emit_retro_stat_fast_intro failed: " << e.what() << '\n';
        return 1;
    }
}
