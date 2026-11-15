// Emit the five Modern Documentary native RenderPlan V3 documents.
//
// Usage: chronontemplate_emit_modern_documentary [output-dir]
// Default: out/modern_documentary_styles
//
// The emitter is deliberately tiny: all design lives in the pack, so emitted
// JSON can be diffed, validated and rendered by chronon3d_cli without Python,
// a browser, screenshots or a live web server.
#include "chronontemplate/web/ModernDocumentaryPack.hpp"

#include <nlohmann/json.hpp>

#include <filesystem>
#include <fstream>
#include <iostream>
#include <string>

namespace {

using nlohmann::json;

void writeJson(const std::filesystem::path& path, const json& value) {
    std::ofstream out(path, std::ios::binary | std::ios::trunc);
    if (!out) throw std::runtime_error("cannot open " + path.string());
    out << value.dump(2) << '\n';
    if (!out) throw std::runtime_error("cannot write " + path.string());
}

}  // namespace

int main(int argc, char** argv) {
    try {
        const std::filesystem::path outDir =
            argc > 1 ? std::filesystem::path(argv[1]) : "out/modern_documentary_styles";
        std::filesystem::create_directories(outDir);

        json manifest = {{"schema", "chronon.modern-documentary-pack.v1"},
                         {"canvas", {{"width", 1920}, {"height", 1080}, {"fps", 30}}},
                         {"recipes", json::array()}};

        for (const auto recipe : chronontemplate::web::allModernDocumentaryRecipes()) {
            chronontemplate::web::ModernDocumentarySpec spec;
            spec.recipe = recipe;
            spec.durationFrames = 150;
            const json plan = chronontemplate::web::buildModernDocumentaryPlan(spec);
            const std::filesystem::path path = outDir / (spec.planName() + ".plan.json");
            writeJson(path, plan);
            manifest["recipes"].push_back({
                {"id", spec.planName()},
                {"plan", path.string()},
                {"duration_frames", spec.durationFrames},
                {"fps", spec.fps},
                {"output", spec.outputStem()},
            });
            std::cout << path.string() << "  (" << plan["layers"].size() << " layers)\n";
        }

        writeJson(outDir / "manifest.json", manifest);
        std::cout << "manifest: " << (outDir / "manifest.json").string() << '\n';
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "modern documentary emit failed: " << error.what() << '\n';
        return 1;
    }
}
