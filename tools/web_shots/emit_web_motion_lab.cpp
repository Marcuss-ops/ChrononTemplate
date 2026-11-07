// Emette i sei piani nativi Web Motion Lab.
// Uso: emit_web_motion_lab <out-dir> [--center] [--only <slug|number>...]
#include "chronontemplate/web/WebMotionLabPack.hpp"

#include <filesystem>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>

namespace fs = std::filesystem;

int main(int argc, char** argv) try {
    if (argc < 2) {
        throw std::runtime_error("usage: emit_web_motion_lab <out-dir> [--only <slug|number>...]");
    }
    const fs::path outDir = fs::absolute(argv[1]);
    fs::create_directories(outDir);

    std::vector<std::string> only;
    bool center = false;
    for (int i = 2; i < argc; ++i) {
        const std::string arg = argv[i];
        if (arg == "--center") {
            center = true;
        } else if (arg == "--only" && i + 1 < argc) {
            only.emplace_back(argv[++i]);
        } else if (arg != "--only") {
            only.emplace_back(arg);
        }
    }
    const auto wanted = [&](const chronontemplate::web::WebLabRecipe recipe, int index) {
        if (only.empty()) return true;
        const std::string name = center ? chronontemplate::web::webCenterLabName(recipe)
                                        : chronontemplate::web::webLabName(recipe);
        const std::string number = std::to_string(index);
        for (const std::string& value : only) {
            if (value == name || value == number) return true;
        }
        return false;
    };

    nlohmann::json manifest = {
        {"schema", center ? "chronon.web-motion-lab.center.v1"
                           : "chronon.web-motion-lab.v1"},
        {"source", center ? "ChrononTemplate C++ WebMotionLabPack (center cut)"
                           : "ChrononTemplate C++ WebMotionLabPack"},
        {"variant", center ? "center" : "chrome"},
        {"renderer",
         {{"engine", "Chronon3d"},
          {"plan_schema", "chronon.render-plan.v3"},
          {"backend", "vulkan"},
          {"encoder", "h264"}}},
        {"canvas",
         {{"width", 1920}, {"height", 1080}, {"fps_num", 30}, {"fps_den", 1},
          {"duration_frames", 180}, {"duration_seconds", 6.0}}},
        {"clips", nlohmann::json::array()}};

    int written = 0;
    int index = 0;
    for (const auto recipe : chronontemplate::web::allWebLabRecipes()) {
        ++index;
        if (!wanted(recipe, index)) continue;

        chronontemplate::web::WebLabSpec spec;
        spec.recipe = recipe;
        spec.center = center;
        switch (recipe) {
            case chronontemplate::web::WebLabRecipe::SplitFlap:
                spec.headline = "Field notes land at 20:26";
                spec.highlight = "20:26";
                spec.subline = "DEPARTURES / SIGNAL BOARD 06";
                break;
            case chronontemplate::web::WebLabRecipe::HalftoneDissolve:
                spec.headline = "Attention is a finite resource";
                spec.highlight = "finite";
                spec.subline = "A PAGE MADE OF DOTS";
                break;
            case chronontemplate::web::WebLabRecipe::InkBloom:
                spec.headline = "The story bleeds through the page";
                spec.highlight = "bleeds through";
                spec.subline = "WET EDGE / MARKER STUDY";
                break;
            case chronontemplate::web::WebLabRecipe::ParallaxDepth:
                spec.headline = "Three planes, one frame";
                spec.highlight = "one frame";
                spec.subline = "DEPTH / MOTION STUDY";
                break;
            case chronontemplate::web::WebLabRecipe::SliceGlitch:
                spec.headline = "The signal remembers the noise";
                spec.highlight = "remembers";
                spec.subline = "TRANSMISSION / RECOVERY";
                break;
            case chronontemplate::web::WebLabRecipe::ApertureScan:
            default:
                spec.headline = "The frame remembers what the eye forgets";
                spec.highlight = "remembers";
                spec.subline = "MOTION LAB / APERTURE";
                break;
        }
        if (center && recipe == chronontemplate::web::WebLabRecipe::SliceGlitch) {
            spec.headline = "SIGNAL RECOVERED";
            spec.highlight = "RECOVERED";
        }
        spec.durationFrames = 180;
        spec.fps = 30;

        const nlohmann::json plan = chronontemplate::web::buildWebLabPlan(spec);
        const fs::path planPath = outDir / (spec.planName() + ".plan.json");
        std::ofstream planFile(planPath);
        if (!planFile) throw std::runtime_error("cannot write " + planPath.string());
        planFile << plan.dump(2) << '\n';

        manifest["clips"].push_back(
            {{"index", index},
             {"slug", center ? chronontemplate::web::webCenterLabName(recipe)
                              : chronontemplate::web::webLabName(recipe)},
             {"plan", spec.planName() + ".plan.json"},
             {"video", spec.outputStem()},
             {"duration_frames", spec.durationFrames},
             {"fps", spec.fps},
             {"headline", spec.headline}});
        std::cout << "Wrote " << planPath << "  (" << spec.headline << ")\n";
        ++written;
    }

    std::ofstream manifestFile(outDir / "manifest.json");
    if (!manifestFile) throw std::runtime_error("cannot write manifest.json");
    manifestFile << manifest.dump(2) << '\n';
    std::cout << written << " motion lab plans\n";
    return written == 0 ? 1 : 0;
} catch (const std::exception& error) {
    std::cerr << error.what() << '\n';
    return 1;
}
