// Emit the seven Documentary parity fixtures and their test metadata.
//
// Usage: chronontemplate_emit_documentary_parity [output-dir]
// Default: out/documentary_parity_suite
#include "chronontemplate/web/DocumentaryParityPack.hpp"

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

json metadata(chronontemplate::web::DocumentaryParityRecipe recipe,
              const std::string& planName) {
    using R = chronontemplate::web::DocumentaryParityRecipe;
    switch (recipe) {
        case R::MacroLcdTypewriter:
            return {{"key_frame", 72},
                    {"probe", "curvature + chroma + typewriter"},
                    {"thresholds", {{"chroma_px", {2.0, 3.0}},
                                    {"curvature", "negative barrel"},
                                    {"typewriter_rate", {24.5, 25.5}}}}};
        case R::KineticWhipBars:
            return {{"key_frame", 45},
                    {"probe", "bar bounding box + motion blur"},
                    {"thresholds", {{"bar_margin_px", 0.5},
                                    {"subframes", 16},
                                    {"whip_frames", 7}}}};
        case R::RackFocusStack:
            return {{"key_frame", 120},
                    {"probe", "four-plane CoC ordering"},
                    {"thresholds", {{"planes", 4},
                                    {"focus_start", 1758.0},
                                    {"focus_end", 978.0}}}};
        case R::ParticleRainOcclusion:
            return {{"key_frame", 90},
                    {"probe", "environment depth + subject occlusion"},
                    {"thresholds", {{"instances", 250},
                                    {"subject_z", -180.0},
                                    {"backdrop_z", 600.0}}}};
        case R::UiCardPanReveal:
            return {{"key_frame", 75},
                    {"probe", "rounded 3D card edge anti-aliasing"},
                    {"thresholds", {{"corner_radius", 24.0},
                                    {"camera_landing_x", 0.0}}}};
        case R::CrtHudCounter:
            return {{"key_frame", 75},
                    {"probe", "CRT HUD + tabular counter"},
                    {"thresholds", {{"badge_optical_centre_px", 0.5},
                                    {"counter_width_jitter_px", 0.0}}}};
        case R::DeterministicScrub:
            return {{"key_frame", 104},
                    {"probe", "sequential vs direct seek + tonal ramp"},
                    {"thresholds", {{"raw_mae", 0.0},
                                    {"frame", 104},
                                    {"seconds", 3.45}}}};
    }
    return {{"key_frame", 0}, {"probe", planName}};
}

}  // namespace

int main(int argc, char** argv) {
    try {
        const std::filesystem::path outDir =
            argc > 1 ? std::filesystem::path(argv[1]) : "out/documentary_parity_suite";
        std::filesystem::create_directories(outDir);

        json manifest = {{"schema", "chronon.documentary-parity-suite.v1"},
                         {"reference_parity", "NOT_RUN_NO_REFERENCE_FILES"},
                         {"canvas", {{"width", 1920}, {"height", 1080}, {"fps", 30}}},
                         {"fixtures", json::array()}};

        for (const auto recipe : chronontemplate::web::allDocumentaryParityRecipes()) {
            chronontemplate::web::DocumentaryParitySpec spec;
            spec.recipe = recipe;
            spec.durationFrames = 150;
            const json plan = chronontemplate::web::buildDocumentaryParityPlan(spec);
            const std::filesystem::path path = outDir / (spec.planName() + ".plan.json");
            writeJson(path, plan);
            json fixture = {
                {"test_id", chronontemplate::web::documentaryParityTestId(recipe)},
                {"id", spec.planName()},
                {"plan", path.string()},
                {"duration_frames", spec.durationFrames},
                {"fps", spec.fps},
                {"output", spec.outputStem()},
            };
            const json meta = metadata(recipe, spec.planName());
            for (auto it = meta.begin(); it != meta.end(); ++it) fixture[it.key()] = it.value();
            manifest["fixtures"].push_back(std::move(fixture));
            std::cout << path.string() << "  (" << plan["layers"].size() << " layers)\n";
        }

        writeJson(outDir / "manifest.json", manifest);
        std::cout << "manifest: " << (outDir / "manifest.json").string() << '\n';
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "documentary parity emit failed: " << error.what() << '\n';
        return 1;
    }
}
