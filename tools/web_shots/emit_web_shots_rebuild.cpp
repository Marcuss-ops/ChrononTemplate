// Emette i piani nativi WebShotsRebuild (28) + WebShotsNext (6).
// Ogni piano e' RenderPlan V3 puro: nessun Pillow, nessun browser.
// Uso: emit_web_shots_rebuild <out-dir> [--only <shot>...]
#include "chronontemplate/web/WebShotsNextPack.hpp"
#include "chronontemplate/web/WebShotsRebuildPack.hpp"

#include <filesystem>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>

namespace fs = std::filesystem;

int main(int argc, char** argv) try {
    if (argc < 2) throw std::runtime_error("usage: emit_web_shots_rebuild <out-dir> [--only <name>...]");
    fs::path outDir = fs::absolute(argv[1]);
    fs::create_directories(outDir);
    std::vector<std::string> only;
    for (int i = 2; i < argc; ++i) {
        if (std::string(argv[i]) == "--only" && i + 1 < argc) { only.push_back(argv[++i]); }
        else if (std::string(argv[i]) != "--only") only.push_back(argv[i]);
    }
    auto wanted = [&](const std::string& n) {
        if (only.empty()) return true;
        for (auto& o : only) if (o == n) return true;
        return false;
    };
    using namespace chronontemplate::web;
    int written = 0;
    nlohmann::json moduleProfiles = nlohmann::json::array();
    for (WebShotId id : allWebShotIds()) {
        WebShotSpec spec; spec.id = id;
        if (!wanted(webShotName(id))) continue;
        moduleProfiles.push_back({{"shot", webShotName(id)},
                                  {"modules", webShotAnimationModules(id)}});
        auto plan = buildWebShotPlan(spec);
        fs::path out = outDir / (spec.planName() + ".plan.json");
        std::ofstream f(out);
        if (!f) throw std::runtime_error("cannot write " + out.string());
        f << plan.dump(2) << '\n';
        std::cout << "Wrote " << out << "  (" << webShotDescription(id) << ")\n";
        ++written;
    }
    {
        std::ofstream f(outDir / "animation_modules.json");
        if (!f) throw std::runtime_error("cannot write animation_modules.json");
        f << moduleProfiles.dump(2) << '\n';
    }
    // 6 nuove recipe con copy di esempio pronta da riusare come base
    std::vector<WebNextSpec> next = {
        {WebNextRecipe::DualMarkerCross, "Senate passes the chip export bill", "chip export bill",
         "Breaking — 10:42 ET", "Markets rally as export rules take hold."},
        {WebNextRecipe::GlowLinePulse, "Simple Sabotage Field Manual revealed", "Sabotage Field Manual",
         "Archive — declassified", "One glowing line carries the whole charge."},
        {WebNextRecipe::TiltSnapReveal, "Why this 30-year-old founder gave it away", "gave it away",
         "Profile — Tilt to flat", "The page snaps flat as the marker lands."},
        {WebNextRecipe::TimelineDash, "Missiles leave Seoul as region rattles", "leave Seoul",
         "Timeline — draw + ping", "The rail draws left to right, then the dot pings."},
        {WebNextRecipe::CaptionPopCard, "When the sauce changed, it went downhill", "sauce changed",
         "Caption — pop card", "White card pops over the dark blurred plate."},
        {WebNextRecipe::CrtFringeFlash, "GOVERNMENT TO DOUBLE CONTENT", "DOUBLE",
         "CRT — fringe flash", "Fringe copies flash under the white headline."},
    };
    for (auto& s : next) {
        if (!wanted(webNextName(s.recipe))) continue;
        auto plan = buildWebNextPlan(s);
        fs::path out = outDir / (s.planName() + ".plan.json");
        std::ofstream f(out);
        if (!f) throw std::runtime_error("cannot write " + out.string());
        f << plan.dump(2) << '\n';
        std::cout << "Wrote " << out << "  (next: " << webNextName(s.recipe) << ")\n";
        ++written;
    }
    std::cout << written << " native plans (28 rebuild + 6 next)\n";
    return 0;
} catch (const std::exception& e) {
    std::cerr << e.what() << '\n';
    return 1;
}
