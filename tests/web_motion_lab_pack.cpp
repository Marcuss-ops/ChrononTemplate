// The Web Motion Lab contract: six new web-animation grammars, all pure
// RenderPlan V3 documents at 1920x1080 / 30 fps with authored durations.
//
// The test pins what must not drift: the six stable identities, the 6 s
// default inside the 10 s ceiling, unique layer ids, measured text boxes, a
// deterministic plan, and fail-closed validation.
#include "chronontemplate/web/WebMotionLabPack.hpp"

#include "motion_check.hpp"

#include <nlohmann/json.hpp>

#include <cmath>
#include <set>
#include <string>
#include <vector>

using json = nlohmann::json;
using namespace chronontemplate::web;
using chrononmotion_test::check;
using chrononmotion_test::section;

namespace {

const char* kHeadline = "The frame remembers what the eye forgets";
const char* kHighlight = "remembers";

void checksEnvelope(const json& plan, const std::string& jobId, int duration) {
    check(plan.at("schema") == "chronon.render-plan.v3" && plan.at("version") == 3,
          "the plan is render-plan V3");
    check(plan.at("job_id") == jobId, "the job id follows the recipe identity");
    const auto& canvas = plan.at("canvas");
    check(canvas.at("width") == 1920 && canvas.at("height") == 1080,
          "the canvas is 1920x1080");
    check(canvas.at("fps_num") == 30 && canvas.at("fps_den") == 1,
          "the canvas is 30 fps");
    check(canvas.at("duration_frames") == duration,
          "the canvas carries the authored duration");
    check(plan.at("output").at("format") == "mp4" &&
              plan.at("output").at("codec") == "h264",
          "the output is H.264 mp4");
    check(plan.contains("camera"), "the plan declares a camera");
    check(!plan.contains("camera_samples"),
          "the plan does not carry obsolete camera samples");
    check(plan.at("camera").at("type") == "perspective",
          "the camera is perspective");
}

void checksLayers(const json& plan) {
    std::set<std::string> ids;
    bool hasText = false;
    for (const auto& layer : plan.at("layers")) {
        check(ids.insert(layer.at("id").get<std::string>()).second,
              "layer ids are unique inside the plan");
        const std::string type = layer.at("type").get<std::string>();
        check(layer.at("position").is_array() && layer.at("position").size() >= 2,
              "every layer has a position");
        check(std::isfinite(layer.at("position")[0].get<float>()) &&
                  std::isfinite(layer.at("position")[1].get<float>()),
              "the layer position is finite");
        if (type == "color") {
            check(layer.value("screen_space", false) ||
                      (layer.contains("size") && layer["size"][0] == 1920 &&
                       layer["size"][1] == 1080),
                  "a full-bleed color plate covers the canvas");
        }
        if (type == "text") {
            hasText = true;
            check(layer.contains("style"), "a text layer carries a style block");
            check(layer.at("size")[0].get<float>() >= 60.f,
                  "the text box is measured from the copy");
        }
    }
    check(hasText, "every recipe authors at least one text layer");
}

void checksRecipes() {
    section("web motion lab recipes");
    const auto recipes = allWebLabRecipes();
    check(recipes.size() == 6, "all six lab recipes are registered");

    const std::vector<std::string> expected = {
        "lab_aperture_scan", "lab_split_flap", "lab_halftone_dissolve",
        "lab_ink_bloom", "lab_parallax_depth", "lab_slice_glitch"};
    std::set<std::string> names;
    for (std::size_t i = 0; i < recipes.size(); ++i) {
        const WebLabRecipe recipe = recipes[i];
        check(std::string(webLabName(recipe)) == expected[i],
              "the recipe name is stable and ordered");
        check(names.insert(webLabName(recipe)).second,
              "every recipe has a unique stable name");

        WebLabSpec spec;
        spec.recipe = recipe;
        spec.headline = kHeadline;
        spec.highlight = kHighlight;
        spec.subline = "MOTION LAB / CONTRACT";
        const json plan = buildWebLabPlan(spec);
        checksEnvelope(plan, spec.planName(), 180);
        checksLayers(plan);
        check(plan.at("output").at("path") == spec.planName() + ".mp4",
              "the output stem follows the plan name");
        check(plan.at("layers").size() >= 8,
              "the recipe composes a real scene, not a placeholder");
        check(buildWebLabPlan(spec).dump() == plan.dump(),
              "the emitted plan is deterministic");
    }
}

void checksCenterRecipes() {
    section("web motion lab center cuts");
    const auto recipes = allWebCenterRecipes();
    check(recipes.size() == 6, "the center family registers all six recipes");

    const std::vector<std::string> expected = {
        "lab_aperture_scan_center", "lab_split_flap_center",
        "lab_halftone_dissolve_center", "lab_ink_bloom_center",
        "lab_parallax_depth_center", "lab_slice_glitch_center"};
    const std::set<std::string> chrome = {
        "kicker", "meta", "subline", "footer", "footer_rule", "scan_label",
        "caption", "headline_rule", "recover_rule", "ticker", "ticker_bar",
        "status", "status_dot", "lock_rule", "ghost"};

    for (std::size_t i = 0; i < recipes.size(); ++i) {
        const WebLabRecipe recipe = recipes[i];
        check(std::string(webCenterLabName(recipe)) == expected[i],
              "the center recipe name is stable and ordered");

        WebLabSpec spec;
        spec.recipe = recipe;
        spec.center = true;
        spec.headline = kHeadline;
        spec.highlight = kHighlight;
        spec.subline = "MOTION LAB / CENTER CONTRACT";
        const json plan = buildWebLabPlan(spec);
        checksEnvelope(plan, spec.planName(), 180);
        checksLayers(plan);
        check(plan.at("job_id").get<std::string>().find("_center") !=
                  std::string::npos,
              "the center plan carries the center identity");
        for (const auto& layer : plan.at("layers")) {
            check(chrome.count(layer.at("id").get<std::string>()) == 0,
                  "the center cut drops the editorial chrome layers");
        }
        check(buildWebLabPlan(spec).dump() == plan.dump(),
              "the center plan is deterministic");
    }
}

void checksDurationCeiling() {
    section("web motion lab duration ceiling");
    for (const int duration : {30, 180, 300}) {
        WebLabSpec spec;
        spec.headline = kHeadline;
        spec.highlight = kHighlight;
        spec.durationFrames = duration;
        const json plan = buildWebLabPlan(spec);
        checksEnvelope(plan, spec.planName(), duration);
        check(plan.at("canvas").at("duration_frames") == duration,
              "a duration inside [30,300] is accepted");
    }
}

void failsClosed() {
    section("web motion lab fail-closed");
    const auto throws = [](auto&& build, const char* what) {
        try {
            (void)build();
        } catch (const std::invalid_argument&) {
            check(true, what);
            return;
        }
        check(false, what);
    };

    throws([] {
        WebLabSpec spec;
        spec.durationFrames = 20;
        return buildWebLabPlan(spec);
    }, "a sub-second plan fails closed");

    throws([] {
        WebLabSpec spec;
        spec.durationFrames = 301;
        return buildWebLabPlan(spec);
    }, "a plan longer than 10 s fails closed");

    throws([] {
        WebLabSpec spec;
        spec.fps = 24;
        return buildWebLabPlan(spec);
    }, "a non-30 fps plan fails closed");

    throws([] {
        WebLabSpec spec;
        spec.headline.clear();
        return buildWebLabPlan(spec);
    }, "an empty headline fails closed");

    throws([] {
        WebLabSpec spec;
        spec.highlight = "not in the headline";
        return buildWebLabPlan(spec);
    }, "a highlight absent from the headline fails closed");
}

}  // namespace

int main() {
    checksRecipes();
    checksCenterRecipes();
    checksDurationCeiling();
    failsClosed();
    return chrononmotion_test::report();
}
