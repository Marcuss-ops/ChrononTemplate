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
        spec.siteName = "ARTICLE";
        spec.navLinks = {};
        spec.kicker = "ARTICLE";
        spec.headlineLineOne = "Massacre at the 1972 Olympic";
        spec.headlineLineTwo = "Games";
        spec.byline = "MUNICH, GERMANY · SEPTEMBER 1972";
        spec.dateline = "Historical archive";
        spec.meta = "1972 OLYMPIC GAMES";
        spec.bodyLines = {
            "The David Berger National Memorial honors David Berger,",
            "an American-Israeli citizen and one of the eleven",
            "Israeli athletes murdered at the 1972 Olympic Games",
            "in Munich, Germany. The memorial stands on the grounds",
            "of the Mandel Jewish Community Center in Cleveland.",
            "This article details the tragedy and remembers the",
            "athletes whose lives were taken during the attack.",
        };
        spec.pickTitles = {"David Berger National Memorial",
                           "The Munich Olympic attack",
                           "Remembering the eleven athletes"};
        spec.importantPhrase = "11 Israeli athletes";
        spec.contextPhrases = {
            "David Berger was among the eleven Israeli athletes",
            "murdered during the 1972 Olympic Games in Munich.",
            "The memorial in Cleveland honors his memory and",
            "the lives of all those lost in the tragedy.",
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
