// The paper-reference contract: five stable recipes, native V3 envelopes,
// deterministic plans, the native highlighter bands and fail-closed specs.
#include "chronontemplate/web/WebPaperReferencePack.hpp"

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

const json* layerById(const json& plan, const std::string& id) {
    for (const auto& layer : plan.at("layers"))
        if (layer.value("id", std::string{}) == id) return &layer;
    return nullptr;
}

/// Keyframe value of a track; -1 when the layer has no such track.
float keyValue(const json& layer, const std::string& property, bool first) {
    if (!layer.contains("animation")) return -1.f;
    for (const auto& track : layer.at("animation").at("tracks")) {
        if (track.value("property", std::string{}) != property) continue;
        const auto& keys = track.at("keyframes");
        return (first ? keys.front() : keys.back()).at("value").get<float>();
    }
    return -1.f;
}

/// Authored left edge in canvas px for center-positioned shape/image layers.
float leftEdge(const json& layer) {
    return layer.at("position")[0].get<float>() + 960.f -
           layer.at("size")[0].get<float>() * 0.5f;
}

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
    check(plan.contains("camera") && plan.at("camera").at("type") == "perspective",
          "the plan declares a perspective camera");
    check(!plan.contains("camera_samples"),
          "the plan does not carry obsolete camera samples");
}

void checksLayers(const json& plan) {
    std::set<std::string> ids;
    for (const auto& layer : plan.at("layers")) {
        check(ids.insert(layer.at("id").get<std::string>()).second,
              "layer ids are unique inside the plan");
        check(layer.at("position").is_array() && layer.at("position").size() >= 2,
              "every layer has a position");
        if (layer.at("type") == "image") {
            check(layer.contains("asset") && !layer.at("asset").get<std::string>().empty(),
                  "an image layer names its content asset");
        }
    }
    check(plan.at("layers").size() >= 2, "the recipe composes a real scene");
}

void checksRecipes() {
    section("paper reference recipes");
    const auto recipes = allPaperReferenceRecipes();
    check(recipes.size() == 5, "all five reference recipes are registered");
    const std::vector<std::string> expected = {
        "web_ref_newspaper_tilt", "web_ref_torn_strip", "web_ref_blurred_evidence",
        "web_ref_bridge_collage", "web_ref_book_highlight"};
    std::set<std::string> names;
    for (std::size_t i = 0; i < recipes.size(); ++i) {
        check(std::string(paperReferenceName(recipes[i])) == expected[i],
              "the recipe name is stable and ordered");
        check(names.insert(paperReferenceName(recipes[i])).second,
              "every recipe has a unique stable name");

        PaperReferenceSpec spec;
        spec.recipe = recipes[i];
        const json plan = buildPaperReferencePlan(spec);
        checksEnvelope(plan, spec.planName(), 180);
        checksLayers(plan);
        check(plan.at("output").at("path") == spec.planName() + ".mp4",
              "the output stem follows the plan name");
        check(buildPaperReferencePlan(spec).dump() == plan.dump(),
              "the emitted plan is deterministic");
    }
}

void checksReferenceMechanics() {
    section("paper reference mechanics");
    PaperReferenceSpec spec;

    spec.recipe = PaperReferenceRecipe::NewspaperTilt;
    const json page = buildPaperReferencePlan(spec);
    bool hasTiltPlate = false;
    bool hasSettle = false;
    for (const auto& layer : page.at("layers")) {
        if (layer.value("type", "") == "image" &&
            layer.value("asset", "").find("la_times_page_tilted.png") != std::string::npos) {
            hasTiltPlate = true;
        }
        if (layer.contains("animation")) {
            for (const auto& track : layer.at("animation").at("tracks")) {
                if (track.value("property", "") == "scale") hasSettle = true;
            }
        }
    }
    check(hasTiltPlate, "the newspaper uses the baked 2.5D page plate");
    check(hasSettle, "the newspaper page carries a slow settle track");

    spec.recipe = PaperReferenceRecipe::BookHighlight;
    const json book = buildPaperReferencePlan(spec);
    int bands = 0;
    int textIndex = -1;
    int lastBandIndex = -1;
    const auto& layers = book.at("layers");
    for (std::size_t i = 0; i < layers.size(); ++i) {
        const auto& layer = layers[i];
        const auto id = layer.value("id", std::string{});
        if (id.rfind("book_marker", 0) == 0 && id.find("_core") == std::string::npos) {
            ++bands;
            lastBandIndex = static_cast<int>(i);
            check(layer.value("blend_mode", std::string{}) != "multiply",
                  "the book highlighter is a bright normal-blend band");
        }
        if (id == "book_text") textIndex = static_cast<int>(i);
    }
    check(bands == 2, "the book highlighter uses two bands");
    check(textIndex > lastBandIndex,
          "the active paragraph stays above the highlighter");
}

void checksVisualContracts() {
    section("paper reference visual contracts");
    PaperReferenceSpec spec;

    // Flat lighting: the rig carries paper and ink at full albedo.
    for (auto recipe : allPaperReferenceRecipes()) {
        spec.recipe = recipe;
        const json plan = buildPaperReferencePlan(spec);
        check(plan.contains("lighting_rig"), "every recipe carries a lighting rig");
        const auto& rig = plan.at("lighting_rig");
        check(rig.at("ambient_intensity").get<float>() == 1.f,
              "the rig lifts ambient light to full albedo");
        check(rig.at("key_intensity").get<float>() == 0.f,
              "the rig adds no directional falloff");
        check(rig.at("rim_enabled") == false, "the rig adds no rim light");
    }

    spec.recipe = PaperReferenceRecipe::NewspaperTilt;
    const json paper = buildPaperReferencePlan(spec);
    const json* plate = layerById(paper, "la_times_page");
    check(plate != nullptr && keyValue(*plate, "scale", true) >= 1.f,
          "the full-bleed page keeps frame coverage at scale 1");
    check(plate != nullptr && keyValue(*plate, "scale", false) >
                                  keyValue(*plate, "scale", true),
          "the newspaper drifts with a slow push-in");

    spec.recipe = PaperReferenceRecipe::BlurredEvidence;
    const json evidence = buildPaperReferencePlan(spec);
    int markers = 0;
    bool card = false;
    for (const auto& layer : evidence.at("layers")) {
        const auto id = layer.value("id", std::string{});
        if (id.rfind("evidence_marker_", 0) == 0 &&
            id.find("_core") == std::string::npos)
            ++markers;
        if (layer.value("type", std::string{}) == "shape") {
            const auto& size = layer.at("size");
            if (size[0].get<float>() * size[1].get<float>() > 0.4f * 1920.f * 1080.f)
                card = true;
        }
    }
    check(markers == 4, "the evidence highlight starts late, spans and ends early");
    check(!card, "the evidence paragraph is not framed by a card");
    const json* tail = layerById(evidence, "evidence_marker_3");
    check(tail != nullptr && leftEdge(*tail) > 1100.f &&
              tail->at("size")[0].get<float>() < 300.f,
          "the evidence sweep begins on the last words of line 4");
    const json* head = layerById(evidence, "evidence_marker_6");
    check(head != nullptr && head->at("size")[0].get<float>() < 400.f,
          "the evidence sweep stops at Arizona State");

    spec.recipe = PaperReferenceRecipe::BookHighlight;
    const json book = buildPaperReferencePlan(spec);
    const json* bookText = layerById(book, "book_text");
    check(bookText != nullptr && bookText->at("size")[0].get<float>() > 4000.f,
          "the book plate is cropped macro");
    const json* bookLine = layerById(book, "book_marker_line_1");
    check(bookLine != nullptr && bookLine->at("size")[0].get<float>() > 1400.f,
          "the book highlighter spans most of the frame width");

    spec.recipe = PaperReferenceRecipe::BridgeCollage;
    const json bridge = buildPaperReferencePlan(spec);
    const json* photo = layerById(bridge, "golden_gate_photo");
    const json* badge = layerById(bridge, "mlb_box");
    check(photo != nullptr && leftEdge(*photo) == 496.f,
          "the photo keeps the reference frame offset");
    check(badge != nullptr && leftEdge(*badge) < leftEdge(*photo) - 20.f &&
              leftEdge(*badge) + badge->at("size")[0].get<float>() >
                  leftEdge(*photo),
          "the MLB badge straddles the photo border");
    const json* continuation = layerById(bridge, "collage_left_text");
    check(continuation != nullptr, "the defocused previous paragraph survives at the left");
    const json* title1 = layerById(bridge, "collage_title_1");
    const json* title2 = layerById(bridge, "collage_title_2");
    // Text boxes are padded 10% and centered on the run, so the run's left
    // edge is boxCenter - size/2.2, not the box position.
    const auto runLeft = [](const json& layer) {
        return layer.at("position")[0].get<float>() -
               layer.at("size")[0].get<float>() / 2.2f;
    };
    check(title1 != nullptr && title2 != nullptr &&
              std::abs(runLeft(*title1) - runLeft(*title2)) < 1.f,
          "the collage title keeps a left-aligned two-line block");
}

void failsClosed() {
    section("paper reference fail-closed");
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
        PaperReferenceSpec spec;
        spec.durationFrames = 20;
        return buildPaperReferencePlan(spec);
    }, "a sub-second plan fails closed");
    throws([] {
        PaperReferenceSpec spec;
        spec.durationFrames = 301;
        return buildPaperReferencePlan(spec);
    }, "a plan longer than 10 s fails closed");
    throws([] {
        PaperReferenceSpec spec;
        spec.fps = 24;
        return buildPaperReferencePlan(spec);
    }, "a non-30 fps plan fails closed");
}

}  // namespace

int main() {
    checksRecipes();
    checksReferenceMechanics();
    checksVisualContracts();
    failsClosed();
    return chrononmotion_test::report();
}
