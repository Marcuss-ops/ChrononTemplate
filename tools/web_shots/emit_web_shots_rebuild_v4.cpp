// Emette i 28 piani nativi WebShotsRebuild v4.
// v4 = composizione v3 + reveal parola-per-parola a runtime, marker
// ri-temporizzati e drift di camera verso l'area evidenziata.
// Uso: emit_web_shots_rebuild_v4 <out-dir> [--only <shot>...]
#include "chronontemplate/web/WebShotsRebuildPack.hpp"

#include <filesystem>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>

namespace fs = std::filesystem;

int main(int argc, char** argv) try {
    if (argc < 2)
        throw std::runtime_error("usage: emit_web_shots_rebuild_v4 <out-dir> [--only <name>...]");
    fs::path outDir = fs::absolute(argv[1]);
    fs::create_directories(outDir);
    std::vector<std::string> only;
    for (int i = 2; i < argc; ++i) {
        if (std::string(argv[i]) == "--only" && i + 1 < argc) only.push_back(argv[++i]);
        else if (std::string(argv[i]) != "--only") only.push_back(argv[i]);
    }
    auto wanted = [&](const std::string& name) {
        if (only.empty()) return true;
        for (const auto& value : only) if (value == name) return true;
        return false;
    };
    using namespace chronontemplate::web;
    int written = 0;
    for (WebShotId id : allWebShotIds()) {
        if (!wanted(webShotName(id))) continue;
        WebShotSpec spec;
        spec.id = id;
        auto plan = buildWebShotPlanV4(spec);
        fs::path out = outDir / (spec.planNameV4() + ".plan.json");
        std::ofstream f(out);
        if (!f) throw std::runtime_error("cannot write " + out.string());
        f << plan.dump(2) << '\n';
        std::cout << "Wrote " << out << "  (" << webShotDescription(id) << ")\n";
        ++written;
    }
    std::cout << written << " v4 plans\n";
    return 0;
} catch (const std::exception& e) {
    std::cerr << e.what() << '\n';
    return 1;
}
