// Emit the five native paper-reference plans as RenderPlan V3 documents.
#include "chronontemplate/web/WebPaperReferencePack.hpp"

#include <nlohmann/json.hpp>

#include <filesystem>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <string>

namespace fs = std::filesystem;

int main(int argc, char** argv) try {
    if (argc != 2) {
        throw std::runtime_error(
            "usage: chronontemplate_emit_web_paper_reference <output-dir>");
    }
    const fs::path out = fs::absolute(argv[1]);
    fs::create_directories(out);
    for (const auto recipe : chronontemplate::web::allPaperReferenceRecipes()) {
        chronontemplate::web::PaperReferenceSpec spec;
        spec.recipe = recipe;
        const auto plan = chronontemplate::web::buildPaperReferencePlan(spec);
        const fs::path path = out / (spec.planName() + ".plan.json");
        std::ofstream file(path);
        if (!file) throw std::runtime_error("cannot write " + path.string());
        file << plan.dump(2) << '\n';
        std::cout << path.string() << '\n';
    }
    return 0;
} catch (const std::exception& error) {
    std::cerr << error.what() << '\n';
    return 1;
}
