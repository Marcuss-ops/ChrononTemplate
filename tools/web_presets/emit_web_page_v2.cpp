// Emit the WebPageV2Pack plans: three recipes · two themes, render-safe.
// Rotation is authored in radians (the V1 degree bug killed video exports).
#include "chronontemplate/web/WebPageV2Pack.hpp"

#include <filesystem>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <string>

namespace fs = std::filesystem;

namespace {

    chronontemplate::web::WebPageV2Spec specFor(
            chronontemplate::web::WebPageV2Theme theme,
            chronontemplate::web::WebPageV2Recipe recipe) {
        using namespace chronontemplate::web;
        WebPageV2Spec spec;
        spec.theme = theme;
        spec.recipe = recipe;
        spec.siteName = "CHRONON NEWS";
        spec.navLinks = {"NBA", "Football", "Business", "Culture"};
        spec.kicker = "NBA TRADE DESK";
        spec.headlineLineOne = "Sources: Kuminga camp";
        spec.headlineLineTwo = "pushing for Warriors exit";
        spec.byline = "ANTHONY SLATER";
        spec.dateline = "Jan 15, 2026 · San Francisco";
        spec.meta = "JAN 15, 2026 · 08:58 PM";
        spec.leadLine = "Eligible to be moved for the first time this summer.";
        spec.bodyLines = {
            "The fifth-year forward demanded a trade away",
            "from the Warriors, league sources said, ending",
            "weeks of tension over his rotation spot.",
            "The contract he signed restricts any deal until",
            "the trade window opens in the first week of",
            "February, when talks are expected to resume",
            "quickly once front offices can negotiate again.",
            "Golden State has weighed staged return plans,",
            "including minutes charts and practice reps.",
            "His camp believes a fresh start lifts both sides.",
        };
        spec.pickTitles = {"Trade buzz: moves that could",
                           "land before the February window",
                           "How the deadline reshapes the West"};
        spec.importantPhrase = "THE FEBRUARY DEADLINE";
        spec.contextPhrases = {
            "Executives around the league expect the",
            "conversation to resume before the window opens,",
            "sources added, and the rotation spot has not",
            "really returned since the difficult stretch.",
            "Golden State has weighed staged return plans,",
            "with minutes charts drafted for each option.",
        };
        return spec;
    }

}// namespace

int main(int argc, char** argv) try {
    if (argc != 2) throw std::runtime_error("usage: emit_web_page_v2 <out-dir>");
    const fs::path outDir = fs::absolute(argv[1]);
    fs::create_directories(outDir);

    using namespace chronontemplate::web;
    int written = 0;
    for (int themeIndex = 0; themeIndex <= 1; ++themeIndex) {
        const WebPageV2Theme theme = themeIndex == 0 ? WebPageV2Theme::Light : WebPageV2Theme::Dark;
        for (int recipeIndex = 0; recipeIndex <= 2; ++recipeIndex) {
            const WebPageV2Recipe recipe = static_cast<WebPageV2Recipe>(recipeIndex);
            const auto variant = specFor(theme, recipe);
            const auto plan = buildWebPageV2Plan(variant);
            const fs::path out = outDir / (variant.planName() + ".plan.json");
            std::ofstream file(out);
            if (!file) throw std::runtime_error("cannot write plan: " + out.string());
            file << plan.dump(2) << '\n';
            std::cout << "Wrote " << out << '\n';
            ++written;
        }
    }
    std::cout << written << " native V2 plans (3 recipes x 2 themes, radians-safe)\n";
    return 0;
} catch (const std::exception& error) {
    std::cerr << error.what() << '\n';
    return 1;
}
