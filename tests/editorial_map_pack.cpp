#include "chronontemplate/core/PlanLowering.hpp"
#include "chronontemplate/core/RenderPlanContentHost.hpp"
#include "chronontemplate/map/EditorialMapPack.hpp"
#include "chrononmotion/motion/RenderPlanEmission.hpp"

#include "fake_content_host.hpp"
#include "motion_check.hpp"

#include <algorithm>
#include <array>
#include <string>

using namespace chronontemplate;
using chronontemplate_test::FakeContentHost;
using chrononmotion_test::check;
using chrononmotion_test::section;

namespace {

constexpr std::array<const char*, 6> kStyles{
    "editorial_vox", "paper_cutout", "dark_radar",
    "blueprint", "connection_arc", "floating_island",
};

void everySceneRoundTripsToARenderPlan() {
    section("six editorial DTOs parse, compose and lower to valid plans");
    for (const char* style : kStyles) {
        FakeContentHost host;
        const std::string stem = std::string("editorial_map_") + style;
        const EditorialMapScene spec =
            loadEditorialMapScene("tests/fixtures/" + stem + ".scene.json");

        check(spec.style == style, "fixture style matches its file name");
        check(spec.canvas.x == 1920.f && spec.canvas.y == 1080.f,
              "DTO preserves the 1920x1080 canvas");
        check(spec.fps == 30.f && spec.frameCount == 240,
              "DTO preserves 30 fps and 240 frames");
        check(!spec.labels.empty(), "DTO carries authored labels");
        check(std::all_of(spec.labels.begin(), spec.labels.end(),
                          [](const EditorialMapLabel& label) {
                              return !label.role.empty();
                          }),
              "every label carries a timing role");
        check(!spec.palette.background.empty(), "DTO carries the palette");

        if (std::string(style) == "connection_arc")
            check(spec.arc.has_value(), "connection_arc carries its Bezier arc");
        if (std::string(style) == "dark_radar")
            check(spec.radar.has_value(), "dark_radar carries its radar centre");
        if (std::string(style) == "floating_island")
            check(spec.leader.has_value(), "floating_island carries its leader");

        RenderPlanContentHost planHost({
            .createText = [&](const TextRequest& request) { return host.createText(request); },
            .createImage = [&](const ImageRequest& request) { return host.createImage(request); },
            .createVideo = [&](const VideoRequest& request) { return host.createVideo(request); },
            .createShape = [&](const ShapeRequest& request) { return host.createShape(request); },
            .currentFingerprint = [&](const ContentId& id) { return host.currentFingerprint(id); },
        });
        TemplateScene scene(stem, spec.fps, planHost, spec.canvas.x, spec.canvas.y);
        const EditorialMapComposition built = addEditorialMap(scene, spec);
        check(built.background != nullptr, "composition owns a background layer");
        check(built.endFrame == spec.frameCount - 1,
              "composition preserves the DTO frame window");
        check(built.layers.size() > 1, "composition emits more than the background");
        check(scene.validate().empty(), "composed TemplateScene validates");

        const auto plan = lowerToRenderPlan(scene, planHost, stem, stem + ".mp4");
        check(plan.schema == chronon3d::render_plan::kRenderPlanSchemaV3,
              "lowering emits a concrete V3 RenderPlan");
        check(plan.canvas.width == spec.canvas.x && plan.canvas.height == spec.canvas.y,
              "plan preserves the DTO canvas");
        check(plan.layers.size() == built.layers.size(),
              "every composed layer reaches the plan");
        const bool hasResolvedSamples = std::any_of(
            plan.layers.begin(), plan.layers.end(),
            [](const chronon3d::render_plan::LayerPlan& layer) {
                return !layer.transform_samples.empty();
            });
        check(hasResolvedSamples, "lowering materializes resolved transform samples");
        // A map animation must not finish in the first half of the clip and leave
        // a static tail. Every style needs at least one layer whose last sample
        // is in the final 10% of the frame window and differs from its first.
        bool lateMotion = false;
        for (const auto& layer : plan.layers) {
            if (layer.transform_samples.size() < 2) continue;
            const auto& first = layer.transform_samples.front();
            const auto& last = layer.transform_samples.back();
            if (last.frame < static_cast<double>(spec.frameCount - 1) * 0.9) continue;
            if (first.opacity != last.opacity || first.scale != last.scale ||
                first.position != last.position) {
                lateMotion = true;
                break;
            }
        }
        check(lateMotion,
              "every editorial style keeps a layer animating through the final 10% of the clip");
        bool fadingTextReachesVisibility = false;
        for (const auto& layer : plan.layers) {
            if (layer.type != chronon3d::render_plan::LayerType::Text) continue;
            for (const auto& sample : layer.transform_samples) {
                if (sample.opacity > 0.9f) fadingTextReachesVisibility = true;
            }
        }
        check(fadingTextReachesVisibility,
              "text opacity samples reach full visibility");
        const std::string planJson = chrononmotion::motion::renderPlanToJson(plan);
        check(planJson.find("\"transform_samples\"") != std::string::npos,
              "screen-space animation samples are serialized");
    }
}

void thePackRejectsAnUnknownStyle() {
    section("the editorial pack fails closed on an unknown style");
    FakeContentHost host;
    TemplateScene scene("editorial_map_unknown", 30.f, host, 1920.f, 1080.f);
    EditorialMapScene spec;
    spec.style = "unknown_style";
    spec.palette.background = "#000000";
    bool threw = false;
    try {
        (void)addEditorialMap(scene, spec);
    } catch (const std::invalid_argument&) {
        threw = true;
    }
    check(threw, "unknown style is rejected before any layer is authored");
}

}  // namespace

int main() {
    everySceneRoundTripsToARenderPlan();
    thePackRejectsAnUnknownStyle();
    return chrononmotion_test::report();
}
