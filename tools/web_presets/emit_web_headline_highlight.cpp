// Emit the native WebHeadlineHighlightPack plans: one per recipe. Every plan
// is pure render-plan V3 authored in C++ — nothing here touches a Pillow
// plate, a browser or a screenshot.
#include "chronontemplate/web/WebHeadlineHighlightPack.hpp"

#include <filesystem>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <string>

namespace fs = std::filesystem;

namespace {

    chronontemplate::web::WebHeadlineHighlightSpec specFor(
            chronontemplate::web::HeadlineHighlightRecipe recipe) {
        using namespace chronontemplate::web;
        WebHeadlineHighlightSpec spec;
        spec.recipe = recipe;
        switch (recipe) {
            case HeadlineHighlightRecipe::StatementPage:
                spec.kicker = "Announcements";
                spec.siteName = "HROPG";
                spec.navLinks = {"Research", "Policy", "Pronouncements"};
                spec.headlineLines = {"Statement on the US government",
                                      "to suspend access to Fable 5 and"};
                spec.highlightText = "to suspend access to Fable 5";
                spec.dateline = "12 Jun 2026";
                spec.bodyLines = {
                    "The US government, citing national security authorities, has issued",
                    "an export control directive to suspend all access to Fable 5 and",
                    "Mythos 5 by any Taiwan national, whether inside or outside the",
                    "United States, including foreign national Anthropic employees.",
                };
                break;
            case HeadlineHighlightRecipe::MarkerSweep:
                spec.phrase = "one company";
                spec.kicker = "The Rise and Fall of Nike";
                spec.dateline = "Chapter Four";
                break;
            case HeadlineHighlightRecipe::SteppedHighlight:
                spec.kicker = "AI  \u00b7  META";
                spec.headlineLines = {"Meta's $100 million signing",
                                      "bonuses for OpenAI staff are just",
                                      "the latest sign of extreme AI",
                                      "talent war"};
                spec.highlightText = "Meta's $100 million signing";
                break;
            case HeadlineHighlightRecipe::BreakingTicker:
                spec.kicker = "BREAKING";
                spec.headlineLines = {"Senate passes the",
                                      "chip export bill"};
                spec.highlightText = "chip export bill";
                spec.dateline = "10:42 ET";
                spec.tickerText = "Markets rally as export rules take hold";
                break;
            case HeadlineHighlightRecipe::LiveBlogFeed:
                spec.kicker = "Election night";
                spec.dateline = "Updated 21:35";
                spec.bodyLines = {"Polls close in three states",
                                  "Counting under way in the capital"};
                spec.entryTimes = {"21:00", "21:34"};
                spec.highlightText = "Counting under way";
                break;
            case HeadlineHighlightRecipe::QuoteCard:
                spec.quoteLines = {"We shape our tools,",
                                   "thereafter our tools shape us"};
                spec.highlightText = "tools shape us";
                spec.attribution = "Marshall McLuhan";
                spec.source = "The Interview, Jun 2026";
                spec.kicker = "Quote";
                break;
        }
        return spec;
    }

}// namespace

int main(int argc, char** argv) try {
    if (argc != 2) throw std::runtime_error("usage: emit_web_headline_highlight <out-dir>");
    const fs::path outDir = fs::absolute(argv[1]);
    fs::create_directories(outDir);

    using namespace chronontemplate::web;
    int written = 0;
    for (const HeadlineHighlightRecipe recipe : {HeadlineHighlightRecipe::StatementPage,
                                                 HeadlineHighlightRecipe::MarkerSweep,
                                                 HeadlineHighlightRecipe::SteppedHighlight,
                                                 HeadlineHighlightRecipe::BreakingTicker,
                                                 HeadlineHighlightRecipe::LiveBlogFeed,
                                                 HeadlineHighlightRecipe::QuoteCard}) {
        const auto spec = specFor(recipe);
        const auto plan = buildWebHeadlineHighlightPlan(spec);
        const fs::path out = outDir / (spec.planName() + ".plan.json");
        std::ofstream file(out);
        if (!file) throw std::runtime_error("cannot write plan: " + out.string());
        file << plan.dump(2) << '\n';
        std::cout << "Wrote " << out << '\n';
        ++written;
    }
    std::cout << written << " native plans (6 highlighter looks, no Pillow)\n";
    return 0;
} catch (const std::exception& error) {
    std::cerr << error.what() << '\n';
    return 1;
}
