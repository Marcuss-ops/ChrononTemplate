#include "chronontemplate/PlanLowering.hpp"
#include "fake_content_host.hpp"
#include "motion_check.hpp"

#include <stdexcept>

using namespace chronontemplate;
using namespace chronon3d::render_plan;
using chronontemplate_test::FakeContentHost;
using chrononmotion_test::check;

int main() {
    FakeContentHost host;
    TemplateScene scene("lowered", 24.f, host, 640.f, 360.f);
    auto& title = scene.text(TextSpec{.text = "Chronon", .font = "Inter.ttf", .fontSize = 48.f});
    title.position(320.f, 180.f).animate(FadeIn{.inFrame = 0, .duration = 8});

    LayerPlan text;
    text.type = LayerType::Text;
    text.text = "Chronon";
    text.font = "Inter.ttf";
    text.color = {0.f, 0.f, 0.f, 0.f};
    text.size = {180.f, 60.f};
    text.size_dimensions = 2;
    const auto plan = lowerToRenderPlan(scene, {{title.id(), text}}, "lowering-test", "test.png");
    check(plan.schema == kRenderPlanSchemaV3, "TemplateScene lowering emits V3");
    check(plan.canvas.width == 640 && plan.canvas.height == 360, "lowering preserves the template canvas");
    check(plan.layers.size() == 1 && plan.layers.front().id == std::to_string(title.id()),
          "lowering carries bound content with stable layer identity");
    check(plan.layers.front().animation.has_value(), "motion animation is baked into the RenderPlan");

    bool missingRejected = false;
    try { (void)lowerToRenderPlan(scene, {}); }
    catch (const std::invalid_argument&) { missingRejected = true; }
    check(missingRejected, "missing renderer content fails closed");

    bool extraRejected = false;
    try { (void)lowerToRenderPlan(scene, {{999999, text}}); }
    catch (const std::invalid_argument&) { extraRejected = true; }
    check(extraRejected, "content for an unbound layer fails closed");
}
