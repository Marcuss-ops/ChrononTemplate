// The WebHeadlineHighlightPack contract: six pure plans, one per recipe,
// each with its own highlighter furniture, a sweep that lands mid-clip, and
// fail-closed spec defects.
#include "chronontemplate/web/WebHeadlineHighlightPack.hpp"

#include "motion_check.hpp"

#include <nlohmann/json.hpp>

#include <string>
#include <vector>

using json = nlohmann::json;
using namespace chronontemplate::web;
using chrononmotion_test::check;
using chrononmotion_test::section;

namespace {

    WebHeadlineHighlightSpec specFor(HeadlineHighlightRecipe recipe) {
        WebHeadlineHighlightSpec spec;
        spec.recipe = recipe;
        spec.kicker = "Announcements";
        spec.headlineLines = {"Statement on the US government",
                              "to suspend access to Fable 5 and"};
        spec.highlightText = "to suspend access to Fable 5";
        spec.dateline = "12 Jun 2026";
        spec.bodyLines = {"The US government, citing national security authorities,",
                          "has issued an export control directive to suspend access."};
        spec.phrase = "one company";
        spec.tickerText = "Markets rally as export rules take hold";
        spec.entryTimes = {"09:41", "10:15"};
        spec.quoteLines = {"We shape our tools,",
                           "thereafter our tools shape us"};
        spec.attribution = "Marshall McLuhan";
        spec.source = "The Interview, Jun 2026";
        switch (recipe) {
            case HeadlineHighlightRecipe::BreakingTicker:
                spec.kicker = "BREAKING";
                spec.headlineLines = {"Senate passes the", "chip export bill"};
                spec.highlightText = "chip export bill";
                spec.dateline = "10:42 ET";
                break;
            case HeadlineHighlightRecipe::LiveBlogFeed:
                spec.kicker = "Election night";
                spec.bodyLines = {"Polls close in three states", "Counting under way"};
                spec.entryTimes = {"21:00", "21:34"};
                spec.highlightText = "Counting under way";
                spec.dateline = "Updated 21:35";
                break;
            case HeadlineHighlightRecipe::QuoteCard:
                spec.highlightText = "tools shape us";
                break;
            default:
                break;
        }
        return spec;
    }

    const json* findLayer(const json& plan, const std::string& id) {
        for (const auto& layer : plan.at("layers")) {
            if (layer.at("id").get<std::string>() == id) return &layer;
        }
        return nullptr;
    }

    /// Every highlighter block must sweep in: scale_x grows 0 -> 1 inside the
    /// clip and the block is opaque enough to read as a marker.
    void sweepsIn(const json& plan, const std::string& id) {
        const json* layer = findLayer(plan, id);
        check(layer != nullptr, (id + " exists").c_str());
        if (!layer) return;
        bool swept = false;
        for (const auto& track : layer->at("animation").at("tracks")) {
            if (track.at("property") == "scale_x") {
                const auto& keys = track.at("keyframes");
                swept = keys.front().at("value").get<double>() == 0.0 &&
                        keys.back().at("value").get<double>() == 1.0 &&
                        keys.back().at("frame").get<int>() < plan.at("canvas").at("duration_frames").get<int>();
            }
        }
        check(swept, (id + " sweeps 0 -> 1 inside the clip").c_str());
    }

    void checksThePlanContract(const WebHeadlineHighlightSpec& spec) {
        const json plan = buildWebHeadlineHighlightPlan(spec);
        check(plan.at("schema") == "chronon.render-plan.v3" && plan.at("version") == 3,
              "every highlighter plan is render-plan V3");
        check(plan.at("canvas").at("width") == 1920 && plan.at("canvas").at("height") == 1080 &&
              plan.at("canvas").at("fps_num") == 30 &&
              plan.at("canvas").at("duration_frames") == spec.durationFrames,
              "the canvas is 1920x1080 at 30 fps with the authored duration");
        check(plan.value("job_id", "") == spec.planName() &&
              plan.at("output").at("path").get<std::string>() == spec.outputStem(),
              "job id and mp4 output follow the recipe identity");

        std::vector<std::string> ids;
        for (const auto& layer : plan.at("layers")) {
            const std::string id = layer.at("id").get<std::string>();
            check(std::find(ids.begin(), ids.end(), id) == ids.end(), "layer ids are unique");
            ids.push_back(id);
        }
        check(plan.contains("camera") && plan.contains("camera_samples") &&
                  !plan.contains("camera_animation"),
              "the page rides a sampled perspective push-in");
    }

    void theStatementPageCarriesItsChrome() {
        section("statement page chrome + coral highlighter");
        const json plan = buildWebHeadlineHighlightPlan(specFor(HeadlineHighlightRecipe::StatementPage));
        for (const char* id : {"nav_bar", "nav_logo", "nav_link_0", "page_kicker",
                               "headline_line_0", "headline_line_1", "highlight_block",
                               "page_dateline", "body_line_0"}) {
            check(findLayer(plan, id) != nullptr, (std::string("statement page has ") + id).c_str());
        }
        sweepsIn(plan, "highlight_block");
    }

    void theMarkerSweepCarriesItsPaper() {
        section("marker sweep paper + yellow band");
        const json plan = buildWebHeadlineHighlightPlan(specFor(HeadlineHighlightRecipe::MarkerSweep));
        check(findLayer(plan, "sweep_paper") != nullptr, "the marker sweep has its paper");
        check(findLayer(plan, "sweep_phrase") != nullptr, "the marker sweep has its phrase");
        check(findLayer(plan, "paper_rule_0") != nullptr, "the paper is lined");
        sweepsIn(plan, "marker_band");
        sweepsIn(plan, "marker_band_lip");
    }

    void theSteppedHighlightSteps() {
        section("stepped highlight blocks");
        const json plan = buildWebHeadlineHighlightPlan(specFor(HeadlineHighlightRecipe::SteppedHighlight));
        check(findLayer(plan, "highlight_block_top") != nullptr, "the stepped look has its top block");
        check(findLayer(plan, "highlight_block_step") != nullptr, "the stepped look has its step block");
        check(findLayer(plan, "kicker_bullet") != nullptr, "the stepped look has a red kicker bullet");
        sweepsIn(plan, "highlight_block_top");
    }

    void theBreakingTickerTicks() {
        section("breaking ticker page");
        const json plan = buildWebHeadlineHighlightPlan(specFor(HeadlineHighlightRecipe::BreakingTicker));
        for (const char* id : {"bb_ground", "bb_kicker_bar", "bb_kicker", "bb_timestamp",
                               "bb_headline_0", "bb_highlight_top", "bb_highlight_step",
                               "bb_ticker_rule", "bb_ticker_tape"}) {
            check(findLayer(plan, id) != nullptr, (std::string("breaking ticker has ") + id).c_str());
        }
        sweepsIn(plan, "bb_highlight_top");
        const json* tape = findLayer(plan, "bb_ticker_tape");
        bool slides = false;
        for (const auto& track : tape->at("animation").at("tracks")) {
            if (track.at("property") == "position_x")
                slides = track.at("keyframes").front().at("value").get<double>() > 0.0 &&
                         track.at("keyframes").back().at("value").get<double>() == 0.0;
        }
        check(slides, "the ticker tape slides in from the right");
    }

    void theLiveBlogMarksItsLatest() {
        section("live-blog feed");
        const json plan = buildWebHeadlineHighlightPlan(specFor(HeadlineHighlightRecipe::LiveBlogFeed));
        for (const char* id : {"live_ground", "live_dot", "live_label", "live_title",
                               "live_updated", "live_time_0", "live_entry_0",
                               "live_time_1", "live_entry_1", "live_footer"}) {
            check(findLayer(plan, id) != nullptr, (std::string("live blog has ") + id).c_str());
        }
        sweepsIn(plan, "live_marker_1");
    }

    void theQuoteCardCredits() {
        section("quote card");
        const json plan = buildWebHeadlineHighlightPlan(specFor(HeadlineHighlightRecipe::QuoteCard));
        for (const char* id : {"quote_ground", "quote_card", "quote_bar", "quote_mark",
                               "quote_line_0", "quote_line_1", "quote_highlight",
                               "quote_by", "quote_source"}) {
            check(findLayer(plan, id) != nullptr, (std::string("quote card has ") + id).c_str());
        }
        sweepsIn(plan, "quote_highlight");
    }

    void recipesDiffer() {
        section("recipes are distinct plans");
        const std::vector<HeadlineHighlightRecipe> all{
            HeadlineHighlightRecipe::StatementPage, HeadlineHighlightRecipe::MarkerSweep,
            HeadlineHighlightRecipe::SteppedHighlight, HeadlineHighlightRecipe::BreakingTicker,
            HeadlineHighlightRecipe::LiveBlogFeed, HeadlineHighlightRecipe::QuoteCard};
        std::vector<json> plans;
        for (const auto recipe : all) plans.push_back(buildWebHeadlineHighlightPlan(specFor(recipe)));
        for (std::size_t i = 0; i < plans.size(); ++i) {
            for (std::size_t j = i + 1; j < plans.size(); ++j) {
                check(plans[i].at("job_id") != plans[j].at("job_id"),
                      "each recipe owns its job id");
                check(plans[i].dump() != plans[j].dump(), "each recipe authors different layers");
            }
        }
    }

    void failsClosed() {
        section("web headline spec fail-closed");
        const auto throws = [](WebHeadlineHighlightSpec spec, const char* what) {
            try {
                (void) buildWebHeadlineHighlightPlan(spec);
            } catch (const std::invalid_argument&) {
                check(true, what);
                return;
            }
            check(false, what);
        };

        WebHeadlineHighlightSpec spec = specFor(HeadlineHighlightRecipe::MarkerSweep);
        spec.phrase.clear();
        throws(spec, "a marker sweep without its phrase fails closed");

        spec = specFor(HeadlineHighlightRecipe::StatementPage);
        spec.headlineLines.clear();
        throws(spec, "a statement page without headline lines fails closed");

        spec = specFor(HeadlineHighlightRecipe::StatementPage);
        spec.highlightText.clear();
        throws(spec, "a headline page without its highlight text fails closed");

        spec = specFor(HeadlineHighlightRecipe::SteppedHighlight);
        spec.kicker.clear();
        throws(spec, "a stepped highlight without its kicker fails closed");

        spec = specFor(HeadlineHighlightRecipe::BreakingTicker);
        spec.tickerText.clear();
        throws(spec, "a breaking ticker without its tape fails closed");

        spec = specFor(HeadlineHighlightRecipe::BreakingTicker);
        spec.highlightText = "absent phrase";
        throws(spec, "a breaking highlight outside the headline fails closed");

        spec = specFor(HeadlineHighlightRecipe::LiveBlogFeed);
        spec.entryTimes.pop_back();
        throws(spec, "a live blog with a missing timestamp fails closed");

        spec = specFor(HeadlineHighlightRecipe::QuoteCard);
        spec.attribution.clear();
        throws(spec, "a quote card without attribution fails closed");

        spec = specFor(HeadlineHighlightRecipe::StatementPage);
        spec.durationFrames = 20;
        throws(spec, "sub-two-second plans fail closed");
    }

}// namespace

int main() {
    section("web headline highlight pack");
    for (const HeadlineHighlightRecipe recipe : {HeadlineHighlightRecipe::StatementPage,
                                                 HeadlineHighlightRecipe::MarkerSweep,
                                                 HeadlineHighlightRecipe::SteppedHighlight,
                                                 HeadlineHighlightRecipe::BreakingTicker,
                                                 HeadlineHighlightRecipe::LiveBlogFeed,
                                                 HeadlineHighlightRecipe::QuoteCard}) {
        checksThePlanContract(specFor(recipe));
    }
    theStatementPageCarriesItsChrome();
    theMarkerSweepCarriesItsPaper();
    theSteppedHighlightSteps();
    theBreakingTickerTicks();
    theLiveBlogMarksItsLatest();
    theQuoteCardCredits();
    recipesDiffer();
    failsClosed();
    return chrononmotion_test::report();
}
