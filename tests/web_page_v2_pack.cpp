// WebPageV2Pack tests: six plans build, framing stays centre-relative,
// reading order stays vertical, recipes differ (V1-002), validation stays
// fail-closed.
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
        spec.pickTitles = {"Trade buzz: moves that could",
                           "Second apron: the new math",
                           "Buyout market: who is available"};
        spec.importantPhrase = "THE FEBRUARY DEADLINE";
        spec.contextPhrases = {"Executives around the league expect the",
                               "conversation to resume before the window opens,",
                               "sources added, and the rotation spot has not",
                               "really returned since the difficult stretch.",
                               "Golden State has weighed staged return plans,"};
        return spec;
    }

    const nlohmann::json* findLayer(const nlohmann::json& plan, const std::string& id) {
        for (const auto& layer : plan["layers"]) {
            if (layer.value("id", "") == id) return &layer;
        }
        return nullptr;
    }

    const nlohmann::json& layer(const nlohmann::json& plan, const std::string& id) {
        const auto* found = findLayer(plan, id);
        assert(found != nullptr && "missing expected layer");
        return *found;
    }

    int layerIndex(const nlohmann::json& plan, const std::string& id) {
        int index = 0;
        for (const auto& layer : plan["layers"]) {
            if (layer.value("id", "") == id) return index;
            ++index;
        }
        return -1;
    }

    // Text is emitted centre-relative; shapes are still in canvas coordinates
    // at this stage. Normalise both to the 1920x1080 canvas before comparing.
    double canvasCenterX(const nlohmann::json& layer) {
        const auto& position = layer.at("position");
        return layer.value("type", "") == "text"
            ? position[0].get<double>() + 960.0
            : position[0].get<double>();
    }

    double canvasTop(const nlohmann::json& layer) {
        const auto& position = layer.at("position");
        const auto& size = layer.at("size");
        const double centerY = layer.value("type", "") == "text"
            ? position[1].get<double>() + 540.0
            : position[1].get<double>();
        return centerY - size[1].get<double>() * 0.5;
    }

    void assertCentredPage(const nlohmann::json& plan) {
        const auto& nav = layer(plan, "nav_bar");
        assert(std::fabs(canvasCenterX(nav) - 960.0) < 0.01);
        assert(std::fabs(canvasTop(nav)) < 0.01);
        assert(std::fabs(canvasCenterX(layer(plan, "footer_rule")) - 960.0) < 0.01);

        const auto& headline = layer(plan, "headline_line_1");
        const auto& lineTwo = layer(plan, "headline_line_2");
        const double headlineLeft = canvasCenterX(headline) - headline["size"][0].get<double>() * 0.5;
        const double lineTwoLeft = canvasCenterX(lineTwo) - lineTwo["size"][0].get<double>() * 0.5;
        assert(std::fabs(headlineLeft - lineTwoLeft) < 0.01);
        assert(headlineLeft >= 150.0 && headlineLeft <= 166.0);

        const auto& sidebar = layer(plan, "sidebar_panel");
        assert(std::fabs(canvasCenterX(sidebar) + sidebar["size"][0].get<double>() * 0.5 - 1770.0) < 0.01);
    }

    void assertVerticalOrder(const nlohmann::json& plan) {
        assert(canvasTop(layer(plan, "nav_bar")) < canvasTop(layer(plan, "masthead_kicker")));
        assert(canvasTop(layer(plan, "masthead_kicker")) < canvasTop(layer(plan, "headline_line_1")));
        assert(canvasTop(layer(plan, "headline_line_1")) < canvasTop(layer(plan, "headline_line_2")));
        assert(canvasTop(layer(plan, "headline_line_2")) < canvasTop(layer(plan, "masthead_byline")));
        assert(canvasTop(layer(plan, "masthead_byline")) < canvasTop(layer(plan, "masthead_rule")));
        assert(canvasTop(layer(plan, "masthead_rule")) < canvasTop(layer(plan, "body_lead")));
        assert(canvasTop(layer(plan, "body_lead")) < canvasTop(layer(plan, "body_line_0")));
        assert(canvasTop(layer(plan, "body_line_0")) < canvasTop(layer(plan, "footer_rule")));

        assert(canvasTop(layer(plan, "sidebar_panel")) < canvasTop(layer(plan, "sidebar_title")));
        assert(canvasTop(layer(plan, "sidebar_title")) < canvasTop(layer(plan, "sidebar_pick_0_num")));
        assert(canvasTop(layer(plan, "sidebar_pick_0_num")) < canvasTop(layer(plan, "sidebar_pick_1_num")));
        assert(canvasTop(layer(plan, "sidebar_pick_1_num")) < canvasTop(layer(plan, "sidebar_pick_2_num")));

        assert(layerIndex(plan, "web_page_paper") == 0);
        assert(layerIndex(plan, "nav_bar") < layerIndex(plan, "nav_logo"));
        assert(layerIndex(plan, "headline_line_1") < layerIndex(plan, "headline_line_2"));
        assert(layerIndex(plan, "body_line_0") < layerIndex(plan, "footer_rule"));
    }

    void assertLongPhraseOrder(const nlohmann::json& plan) {
        const auto& top0 = layer(plan, "long_context_top_0");
        const auto& top1 = layer(plan, "long_context_top_1");
        const auto& phrase = layer(plan, "important_center_phrase");
        const auto& underline = layer(plan, "important_underline");
        const auto& bottom0 = layer(plan, "long_context_bottom_0");
        const auto& bottom1 = layer(plan, "long_context_bottom_1");
        assert(canvasTop(top0) < canvasTop(top1));
        assert(canvasTop(top1) < canvasTop(phrase));
        assert(canvasTop(phrase) < canvasTop(underline));
        assert(canvasTop(underline) < canvasTop(bottom0));
        assert(canvasTop(bottom0) < canvasTop(bottom1));
        for (const auto* line : {&top0, &top1, &phrase, &bottom0, &bottom1}) {
            assert(std::fabs(canvasCenterX(*line)) < 0.01);
        }
        assert(std::fabs(canvasCenterX(underline) - 960.0) < 0.01);
    }

    bool hasLayerWith(const nlohmann::json& plan, const std::string& substr) {
        for (const auto& l : plan["layers"]) {
            if (l.value("id", "").find(substr) != std::string::npos) return true;
        }
        return false;
    }

    bool hasFold(const nlohmann::json& plan) {
        for (const auto& l : plan["layers"]) {
            if (l.value("id", "") != "headline_line_1") continue;
            const auto animation = l.value("animation", nlohmann::json::object());
            for (const auto& track : animation.value("tracks", nlohmann::json::array())) {
                if (track.value("property", "") == "rotation") return true;
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
            assert(std::fabs(plan["camera"]["position"][0].get<double>()) < 0.01);
            assert(std::fabs(plan["camera"]["position"][1].get<double>()) < 0.01);
            ++plans;
        }
    }
    assert(plans == 6);

    // V1-002: Complete must NOT fold; Highlight3D MUST fold; both share chrome.
    const auto complete =
        buildWebPageV2Plan(demoSpec(WebPageV2Theme::Light, WebPageV2Recipe::Complete));
    const auto highlight =
        buildWebPageV2Plan(demoSpec(WebPageV2Theme::Light, WebPageV2Recipe::Highlight3D));

    // Framing: both text and shapes are centre-relative, so the camera must
    // look at the world origin. A camera at (960,540) would double-shift them.
    const auto& cameraPosition = complete["camera"]["position"];
    assert(std::fabs(cameraPosition[0].get<double>()) < 0.01);
    assert(std::fabs(cameraPosition[1].get<double>()) < 0.01);
    for (const auto& layer : complete["layers"]) {
        if (layer.value("id", "") == "nav_logo") {
            assert(layer["position"][0].get<double>() < 0.0);
            assert(layer["position"][1].get<double>() > 0.0);
        }
    }
    assert(!hasFold(complete) && "Complete is the soft editorial recipe");
    assert(hasFold(highlight) && "Highlight3D tilts the headline");
    assert(hasLayerWith(highlight, "headline_marker"));
    assert(hasLayerWith(complete, "kicker_bar"));
    assert(hasLayerWith(complete, "share_pill_0"));
    assert(hasLayerWith(complete, "sidebar_pick_0_num"));

    assertCentredPage(complete);
    assertCentredPage(highlight);
    assertVerticalOrder(complete);
    assertVerticalOrder(highlight);
    assertLongPhraseOrder(
        buildWebPageV2Plan(demoSpec(WebPageV2Theme::Light, WebPageV2Recipe::LongPhraseBlurred)));

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

    std::cout << "web_page_v2_pack: 6 plans, centred, vertical order, recipes distinct — PASS\n";
    return 0;
}
