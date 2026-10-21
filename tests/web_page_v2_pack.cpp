// WebPageV2Pack tests: six plans build, rotation stays in radians (V1-001),
// recipes differ (V1-002), validation stays fail-closed.
#include "chronontemplate/web/WebPageV2Pack.hpp"

#include <cassert>
#include <cmath>
#include <iostream>
#include <string>

namespace {

    using chronontemplate::web::WebPageV2Recipe;
    using chronontemplate::web::WebPageV2Spec;
    using chronontemplate::web::WebPageV2Theme;

    WebPageV2Spec demoSpec(WebPageV2Theme theme, WebPageV2Recipe recipe) {
        WebPageV2Spec spec;
        spec.theme = theme;
        spec.recipe = recipe;
        spec.headlineLineOne = "Sources: Kuminga camp";
        spec.headlineLineTwo = "pushing for Warriors exit";
        spec.kicker = "NBA TRADE DESK";
        spec.byline = "ANTHONY SLATER";
        spec.dateline = "Jan 15, 2026";
        spec.meta = "JAN 15, 2026";
        spec.leadLine = "Eligible to be moved for the first time.";
        spec.bodyLines = {"The fifth-year forward demanded a trade away",
                          "from the Warriors, league sources said."};
        spec.pickTitles = {"Trade buzz: moves that could"};
        spec.importantPhrase = "THE FEBRUARY DEADLINE";
        spec.contextPhrases = {"Executives around the league expect the",
                               "conversation to resume before the window opens,",
                               "sources added, and the rotation spot has not."};
        return spec;
    }

    void checkRotationRadians(const nlohmann::json& node, const std::string& plan) {
        if (node.is_object()) {
            if (node.value("property", "") == "rotation" && node.contains("keyframes")) {
                for (const auto& kf : node["keyframes"]) {
                    const auto& v = kf["value"];
                    if (v.is_array()) {
                        for (const auto& c : v) {
                            const double d = c.get<double>();
                            assert(std::fabs(d) <= 3.0 && "rotation must be radians (V1-001)");
                        }
                    } else {
                        assert(std::fabs(v.get<double>()) <= 3.0 && "rotation must be radians (V1-001)");
                    }
                }
            }
            for (const auto& [k, v] : node.items()) {
                (void)k;
                checkRotationRadians(v, plan);
            }
        } else if (node.is_array()) {
            for (const auto& v : node) checkRotationRadians(v, plan);
        }
    }

    bool hasLayerWith(const nlohmann::json& plan, const std::string& substr) {
        for (const auto& l : plan["layers"]) {
            if (l.value("id", "").find(substr) != std::string::npos) return true;
        }
        return false;
    }

    bool hasFold(const nlohmann::json& plan) {
        for (const auto& l : plan["layers"]) {
            for (const auto& a : l.value("text_animators", nlohmann::json::array())) {
                for (const auto& pr : a["properties"]) {
                    if (pr.value("property", "") == "rotation") return true;
                }
            }
        }
        return false;
    }

}// namespace

int main() {
    using namespace chronontemplate::web;
    int plans = 0;
    for (int themeIndex = 0; themeIndex <= 1; ++themeIndex) {
        const WebPageV2Theme theme = themeIndex == 0 ? WebPageV2Theme::Light : WebPageV2Theme::Dark;
        for (int recipeIndex = 0; recipeIndex <= 2; ++recipeIndex) {
            const WebPageV2Recipe recipe = static_cast<WebPageV2Recipe>(recipeIndex);
            const auto plan = buildWebPageV2Plan(demoSpec(theme, recipe));
            assert(plan.contains("layers") && !plan["layers"].empty());
            assert(plan.contains("camera"));
            checkRotationRadians(plan, demoSpec(theme, recipe).planName());
            ++plans;
        }
    }
    assert(plans == 6);

    // V1-002: Complete must NOT fold; Highlight3D MUST fold; both share chrome.
    const auto complete =
        buildWebPageV2Plan(demoSpec(WebPageV2Theme::Light, WebPageV2Recipe::Complete));
    const auto highlight =
        buildWebPageV2Plan(demoSpec(WebPageV2Theme::Light, WebPageV2Recipe::Highlight3D));
    assert(!hasFold(complete) && "Complete is the soft editorial recipe");
    assert(hasFold(highlight) && "Highlight3D folds the headline");
    assert(hasLayerWith(highlight, "headline_marker"));
    assert(hasLayerWith(complete, "kicker_bar"));
    assert(hasLayerWith(complete, "share_pill_0"));
    assert(hasLayerWith(complete, "sidebar_pick_0_num"));

    // Determinism: identical spec -> identical bytes.
    const auto a = buildWebPageV2Plan(demoSpec(WebPageV2Theme::Dark, WebPageV2Recipe::Complete));
    const auto b = buildWebPageV2Plan(demoSpec(WebPageV2Theme::Dark, WebPageV2Recipe::Complete));
    assert(a.dump() == b.dump());

    // Fail-closed validation still holds.
    bool threw = false;
    try {
        auto bad = demoSpec(WebPageV2Theme::Light, WebPageV2Recipe::Complete);
        bad.headlineLineOne.clear();
        buildWebPageV2Plan(bad);
    } catch (const std::invalid_argument&) {
        threw = true;
    }
    assert(threw && "empty headline must throw");

    std::cout << "web_page_v2_pack: 6 plans, radians-safe, recipes distinct — PASS\n";
    return 0;
}
