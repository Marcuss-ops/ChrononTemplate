// Emits the twelve native web-motion classics as RenderPlan V3 documents.
// Usage: emit_web_motion_classics <out-dir> [--only <slug|number>...]
#include "chronontemplate/web/MotionClassicsPack.hpp"

#include <filesystem>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>

namespace fs = std::filesystem;

int main(int argc, char** argv) try {
    if (argc < 2) {
        throw std::runtime_error(
            "usage: emit_web_motion_classics <out-dir> [--only <slug|number>...]");
    }

    const fs::path outDir = fs::absolute(argv[1]);
    fs::create_directories(outDir);

    std::vector<std::string> only;
    for (int i = 2; i < argc; ++i) {
        if (std::string(argv[i]) == "--only" && i + 1 < argc) {
            only.emplace_back(argv[++i]);
        } else {
            only.emplace_back(argv[i]);
        }
    }

    auto wanted = [&](const chronontemplate::web::MotionClassicSpec& spec) {
        if (only.empty()) return true;
        const std::string number = std::to_string(spec.index);
        for (const std::string& value : only) {
            if (value == spec.slug || value == number || value == spec.planName() ||
                value == spec.videoName()) {
                return true;
            }
        }
        return false;
    };

    nlohmann::json manifest = {
        {"schema", "chronon.web-motion-classics.v1"},
        {"source", "ChrononTemplate C++ WebMotionClassicsPack"},
        {"renderer",
         {{"engine", "Chronon3d"},
          {"plan_schema", "chronon.render-plan.v3"},
          {"backend", "vulkan"},
          {"encoder", "h264"}}},
        {"canvas",
         {{"width", 1920}, {"height", 1080}, {"fps_num", 30}, {"fps_den", 1},
          {"duration_frames", 90}, {"duration_seconds", 3.0}}},
        {"clips", nlohmann::json::array()}};

    int written = 0;
    for (const auto& spec : chronontemplate::web::motionClassicSpecs()) {
        if (!wanted(spec)) continue;

        nlohmann::json plan = chronontemplate::web::buildMotionClassicPlan(spec);
        const fs::path planPath = outDir / (spec.planName() + ".plan.json");
        std::ofstream planFile(planPath);
        if (!planFile) throw std::runtime_error("cannot write " + planPath.string());
        planFile << plan.dump(2) << '\n';

        manifest["clips"].push_back(
            {{"index", spec.index},
             {"slug", spec.slug},
             {"title", spec.title},
             {"description", spec.description},
             {"plan", spec.planName() + ".plan.json"},
             {"video", spec.videoName()},
             {"duration_frames", spec.durationFrames},
             {"fps", spec.fps}});
        std::cout << "Wrote " << planPath << "  (" << spec.title << ")\n";
        ++written;
    }

    std::ofstream manifestFile(outDir / "manifest.json");
    if (!manifestFile) throw std::runtime_error("cannot write manifest.json");
    manifestFile << manifest.dump(2) << '\n';
    std::cout << written << " native plans\n";
    return written == 12 ? 0 : 1;
} catch (const std::exception& error) {
    std::cerr << error.what() << '\n';
    return 1;
}
