// The WebPageHighlightPack contract: theme inversion is symmetric, blur
// belongs only to the supporting context text, the important center phrase is
// never blurred, and every spec defect fails closed. Six pure plans, three
// recipes times two themes.
#include "chronontemplate/web/WebPageHighlightPack.hpp"

#include "motion_check.hpp"

#include <nlohmann/json.hpp>

#include <cmath>
#include <map>
#include <set>
#include <string>
#include <vector>

using json = nlohmann::json;
using namespace chronontemplate::web;
using chrononmotion_test::check;
using chrononmotion_test::section;

namespace {

    double channelValue(const std::string& hex, int index) {
        return static_cast<double>(std::stoul(hex.substr(1 + index * 2, 2), nullptr, 16)) / 255.0;
    }

    double luminance(const std::string& hex) {
        return 0.2126 * channelValue(hex, 0) + 0.7152 * channelValue(hex, 1) + 0.0722 * channelValue(hex, 2);
    }

    WebPageHighlightSpec baseSpec() {
        WebPageHighlightSpec spec;
        spec.headlineLineOne = "Sources: Jonathan Kuminga";
        spec.headlineLineTwo = "demanding trade away from Warriors";
        spec.byline = "ANTHONY SLATER AND SHAMS CHARANIA";
        spec.meta = "JAN 15, 2026  ·  08:58 PM";
        spec.bodyLines = {"SAN FRANCISCO — Eligible to be moved for the first",
                          "time this summer, the fifth-year forward demanded",
                          "a trade away from the Warriors, sources said.",
                          "League executives expect talks to resume quickly."};
        spec.pickTitles = {"Trade buzz: the moves that could land"};
        spec.importantPhrase = "THE FEBRUARY DEADLINE";
        spec.contextPhrases = {"Executives around the league expect the",
                               "conversation to resume before the window,",
                               "sources added, and the spot never returned."};
        return spec;
    }

    const json* findLayer(const json& plan, const std::string& id) {
        for (const auto& layer : plan.at("layers")) {
            if (layer.at("id").get<std::string>() == id) return &layer;
        }
        return nullptr;
    }

    bool hasBlurAnimator(const json& layer, float* blurValue = nullptr) {
        if (!layer.contains("text_animators")) return false;
        for (const auto& animator : layer.at("text_animators")) {
            for (const auto& track : animator.at("properties")) {
                if (track.at("property").get<std::string>() == "blur") {
                    if (blurValue) *blurValue = track.at("keyframes").front().at("value").get<float>();
                    return true;
                }
            }
        }
        return false;
    }

    void checksThePlanContract(const WebPageHighlightSpec& spec) {
        const json plan = buildWebPageHighlightPlan(spec);
        check(plan.at("schema") == "chronon.render-plan.v3" && plan.at("version") == 3,
              "every web-page plan is render-plan V3");
        check(plan.at("canvas").at("width") == 1920 && plan.at("canvas").at("height") == 1080 &&
              plan.at("canvas").at("fps_num") == 30 &&
              plan.at("canvas").at("duration_frames") == spec.durationFrames,
              "the canvas is 1920x1080 at 30 fps with the authored duration");
        check(plan.value("job_id", "") == spec.planName() &&
              plan.at("output").at("path").get<std::string>() == spec.outputStem(),
              "job id and mp4 output follow the recipe x theme identity");

        std::set<std::string> ids;
        for (const auto& layer : plan.at("layers")) {
            check(ids.insert(layer.at("id").get<std::string>()).second, "layer ids are unique");
        }
        check(plan.contains("camera") && plan.at("camera").at("type") == "perspective" &&
              plan.contains("camera_samples") && !plan.contains("camera_animation"),
              "the page rides a perspective push-in");

        // Blur contract per recipe: context text blurred, important text sharp.
        const std::vector<std::pair<std::string, bool>> sharpLayers =
            spec.recipe == WebPageRecipe::LongPhraseBlurred
                ? std::vector<std::pair<std::string, bool>>{
                      {"important_center_phrase", true}, {"long_context_top_0", false},
                      {"long_context_top_1", false}, {"long_context_bottom_0", false}}
                : std::vector<std::pair<std::string, bool>>{
                      {"headline_line_1", true}, {"masthead_kicker", true},
                      {"nav_action_text", true}, {"nav_link_0", false},
                      {"body_line_0", false}, {"sidebar_title", false},
                      {"footer_left", false}};
        for (const auto& [id, expectedSharp] : sharpLayers) {
            const json* layer = findLayer(plan, id);
            check(layer != nullptr, ("the " + id + " layer exists").c_str());
            const float blur = hasBlurAnimator(*layer) ? [&] {
                float value = 0.f;
                (void) hasBlurAnimator(*layer, &value);
                return value;
            }() : 0.f;
            check(expectedSharp ? (hasBlurAnimator(*layer) ? blur < 0.01f : true)
                                : (hasBlurAnimator(*layer) && blur > 2.f),
                  ("blur follows the grammar on " + id).c_str());
            if (hasBlurAnimator(*layer) && !expectedSharp) {
                for (const auto& animator : layer->at("text_animators")) {
                    for (const auto& track : animator.at("properties")) {
                        if (track.at("property") == "blur") {
                            check(track.at("easing") == "linear" &&
                                      track.at("keyframes").front().at("frame") == 0 &&
                                      track.at("keyframes").back().at("frame") ==
                                          spec.durationFrames - 1,
                                  ("the blur animator on " + id +
                                   " is baked linear over the clip").c_str());
                        }
                    }
                }
            }
        }

        // Recipe-scoped furniture exists exactly where it should.
        check((findLayer(plan, "headline_marker") != nullptr) ==
                  (spec.recipe == WebPageRecipe::Highlight3D),
              "the accent marker sweep belongs to Highlight3D only");
        check((findLayer(plan, "important_underline") != nullptr) ==
                  (spec.recipe == WebPageRecipe::LongPhraseBlurred),
              "the accent underline belongs to LongPhraseBlurred only");
        check((findLayer(plan, "nav_bar") != nullptr) ==
                  (spec.recipe != WebPageRecipe::LongPhraseBlurred),
              "the nav chrome belongs to the full-page recipes only");

        // The important center text always carries a per-glyph 3D fold.
        const std::string centerId = spec.recipe == WebPageRecipe::LongPhraseBlurred
                                         ? "important_center_phrase"
                                         : "headline_line_1";
        bool foldSeen = false;
        for (const auto& animator : findLayer(plan, centerId)->at("text_animators")) {
            for (const auto& track : animator.at("properties")) {
                if (track.at("property") == "rotation") foldSeen = true;
            }
        }
        check(foldSeen, ("the center phrase folds in 3D (" + centerId + ")").c_str());
    }

    void themeInversion() {
        section("web theme inversion");
        struct Row {
            std::string paper, ink, body;
        };
        const Row light{paletteFor(WebPageTheme::Light).paper,
                        paletteFor(WebPageTheme::Light).ink,
                        paletteFor(WebPageTheme::Light).body};
        const Row dark{paletteFor(WebPageTheme::Dark).paper,
                       paletteFor(WebPageTheme::Dark).ink,
                       paletteFor(WebPageTheme::Dark).body};
        check(luminance(light.ink) < 0.25 && luminance(light.body) < 0.45,
              "the light page reads ink-dark");
        check(luminance(dark.ink) > 0.7 && luminance(dark.body) > 0.55,
              "the dark page reads paper-light");
        check(std::fabs(luminance(light.paper) - luminance(dark.paper)) > 0.5,
              "the pages themselves swap tone, not just the text");

        WebPageHighlightSpec spec = baseSpec();
        const json lightPlan = buildWebPageHighlightPlan(spec);
        spec.theme = WebPageTheme::Dark;
        const json darkPlan = buildWebPageHighlightPlan(spec);
        check(lightPlan.at("job_id") != darkPlan.at("job_id") &&
                  lightPlan.at("layers").size() == darkPlan.at("layers").size(),
              "both themes emit the same layout under swapped job ids");
        bool inverseSeen = false;
        for (const auto& layer : darkPlan.at("layers")) {
            if (layer.at("id") == "masthead_byline") {
                inverseSeen = layer.at("style").at("fill") == paletteFor(WebPageTheme::Dark).ink;
            }
        }
        check(inverseSeen, "headline-level text follows the dark palette");
    }

    void failsClosed() {
        section("web spec fail-closed");
        const auto throws = [](WebPageHighlightSpec spec, const char* what) {
            try {
                (void) buildWebPageHighlightPlan(spec);
            } catch (const std::invalid_argument&) {
                check(true, what);
                return;
            }
            (void) spec;
            check(false, what);
        };

        WebPageHighlightSpec spec = baseSpec();
        spec.headlineLineOne.clear();
        throws(spec, "a complete recipe without a headline fails closed");

        spec = baseSpec();
        spec.bodyLines.clear();
        throws(spec, "an article page without body lines fails closed");

        spec = baseSpec();
        spec.bodyLines.assign(81, "too many body lines for one page");
        throws(spec, "more than eighty body lines fails closed");

        spec = baseSpec();
        spec.durationFrames = 60;
        throws(spec, "sub-two-second plans fail closed");

        spec = baseSpec();
        spec.recipe = WebPageRecipe::LongPhraseBlurred;
        spec.importantPhrase.clear();
        throws(spec, "the blurred-phrase recipe without its center phrase fails closed");

        spec = baseSpec();
        spec.recipe = WebPageRecipe::LongPhraseBlurred;
        spec.importantPhrase = "THE FEBRUARY DEADLINE";
        spec.contextPhrases.clear();
        throws(spec, "the blurred-phrase recipe without context fails closed");
    }

}// namespace

int main() {
    section("web page highlight pack");
    for (const int themeIndex : {0, 1}) {
        for (const int recipeIndex : {0, 1, 2}) {
            WebPageHighlightSpec spec = baseSpec();
            spec.theme = static_cast<WebPageTheme>(themeIndex);
            spec.recipe = static_cast<WebPageRecipe>(recipeIndex);
            checksThePlanContract(spec);
        }
    }
    themeInversion();
    failsClosed();
    return 0;
}
