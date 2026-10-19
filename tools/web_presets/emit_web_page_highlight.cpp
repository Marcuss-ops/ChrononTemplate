// Emit the native WebPageHighlightPack plans: three recipes · two themes.
// Every plan is pure render-plan V3 authored in C++ — nothing here touches a
// Pillow plate, a browser or a screenshot.
#include "chronontemplate/web/WebPageHighlightPack.hpp"

#include <filesystem>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <string>

namespace fs = std::filesystem;

namespace {

    chronontemplate::web::WebPageHighlightSpec specFor(
            chronontemplate::web::WebPageTheme theme,
            chronontemplate::web::WebPageRecipe recipe) {
        using namespace chronontemplate::web;
        WebPageHighlightSpec spec;
        spec.theme = theme;
        spec.recipe = recipe;
        spec.siteName = "CHRONON NEWS";
        spec.navLinks = {"NBA", "Football", "Business", "Culture"};
        spec.kicker = "NBA";
        spec.headlineLineOne = "Sources: Jonathan Kuminga";
        spec.headlineLineTwo = "demanding trade away from Warriors";
        spec.byline = "ANTHONY SLATER AND SHAMS CHARANIA";
        spec.dateline = "Jan 15, 2026  ·  San Francisco";
        spec.meta = "JAN 15, 2026  ·  08:58 PM";
        spec.bodyLines = {
            "SAN FRANCISCO — Eligible to be moved for the first",
            "time this summer, the fifth-year forward demanded a",
            "trade away from the Warriors, league sources said.",
            "The contract he signed restricts any deal until the",
            "trade window opens in the first week of February.",
            "His roller-coaster tenure reached its lowest point",
            "after a difficult stretch in the rotation, sources",
            "added, and the rotation spot never really returned.",
            "League executives expect the conversations to resume",
            "quickly once front offices are allowed to talk again.",
            "Golden State has weighed staged return plans before,",
            "including minutes charts and staged practice reps.",
        };
        spec.pickTitles = {"Trade buzz: the moves that could",
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
    if (argc != 2) throw std::runtime_error("usage: emit_web_page_highlight <out-dir>");
    const fs::path outDir = fs::absolute(argv[1]);
    fs::create_directories(outDir);

    using namespace chronontemplate::web;
    int written = 0;
    for (int themeIndex = 0; themeIndex <= 1; ++themeIndex) {
        const WebPageTheme theme = themeIndex == 0 ? WebPageTheme::Light : WebPageTheme::Dark;
        for (int recipeIndex = 0; recipeIndex <= 2; ++recipeIndex) {
            const WebPageRecipe recipe = static_cast<WebPageRecipe>(recipeIndex);
            const auto variant = specFor(theme, recipe);
            const auto plan = buildWebPageHighlightPlan(variant);
            const fs::path out = outDir / (variant.planName() + ".plan.json");
            std::ofstream file(out);
            if (!file) throw std::runtime_error("cannot write plan: " + out.string());
            file << plan.dump(2) << '\n';
            std::cout << "Wrote " << out << '\n';
            ++written;
        }
    }
    std::cout << written << " native plans (3 recipes x 2 themes, no Pillow)\n";
    return 0;
} catch (const std::exception& error) {
    std::cerr << error.what() << '\n';
    return 1;
}
