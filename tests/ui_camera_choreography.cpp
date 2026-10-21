// The UI + smooth-camera choreography acceptance suite (90 frames, 30 fps).
//
// The tutorial grammar as gates:
//
//   P0  the panel rides one Null controller — root isNull, children parented,
//       no second parenting system;
//   1.  animated parenting end-to-end — children follow the root across the
//       entrance, zoom and pan windows;
//   2.  the camera travels without teleports and settles into the hold;
//   3.  framing fits the measured bounds — the eye sits no closer than the
//       optical law over the real panel size, and the title stays in the
//       safe area for all 90 frames;
//   4.  lowering to RenderPlan carries the baked motion, needs no new
//       LayerType for the controller, and declares the motion blur;
//   5.  bad specs fail closed instead of authoring junk.

#include "chronontemplate/ui_camera/UiCameraChoreography.hpp"

#include "chronontemplate/core/RenderPlanContentHost.hpp"

#include "fake_content_host.hpp"
#include "motion_check.hpp"

#include "chrononmotion/motion/CameraScreenSpace.hpp"

#include <cmath>
#include <stdexcept>
#include <string>

using namespace chronontemplate;
using chronontemplate_test::FakeContentHost;
using chrononmotion_test::check;
using chrononmotion_test::section;

namespace {

    constexpr float kW = 1920.f;
    constexpr float kH = 1080.f;
    constexpr float kFps = 30.f;

    [[nodiscard]] UiPanelSpec panelSpec() {
        UiPanelSpec spec;
        spec.title = "CHRONON UI";
        spec.font = "Inter-Bold.ttf";
        spec.fontSize = 96.f;
        return spec;
    }

    void nullControllerHierarchy() {
        section("P0: one Null controller carries the panel");
        FakeContentHost host;
        TemplateScene scene("ui_choreo", kFps, host, kW, kH);
        const UiPanelComposition panel = buildUiPanel(scene, panelSpec());

        const auto* root = scene.motion().findLayer(panel.root);
        check(root != nullptr && root->isNull(), "UiRoot is a Null controller with no content");
        const auto* card = scene.motion().findLayer(panel.card);
        const auto* title = scene.motion().findLayer(panel.title);
        const auto* icon = scene.motion().findLayer(panel.icon);
        check(card != nullptr && !card->isNull(), "the card is a content layer");
        check(title != nullptr && !title->isNull(), "the title is a content layer");
        check(icon != nullptr && !icon->isNull(), "the icon is a content layer");
        check(card->parentId == panel.root && title->parentId == panel.root &&
                  icon->parentId == panel.root,
              "card, title and icon are parented to the single UiRoot");
        check(panel.panelSize.x >= 900.f && panel.panelSize.y >= 500.f,
              "measured bounds cover at least the authored card");
        check(scene.validate().empty(), "the motion core validates the hierarchy");
    }

    void animatedParentingEndToEnd() {
        section("animated parenting end-to-end across entrance, zoom and pan");
        FakeContentHost host;
        TemplateScene scene("ui_choreo", kFps, host, kW, kH);
        const UiPanelComposition panel = buildUiPanel(scene, panelSpec());
        applyUiCameraChoreography(scene, UiCameraChoreographySpec{}, panel);

        const UiChoreographyReport report = validateUiChoreography(scene, UiCameraChoreographySpec{}, panel);
        for (const std::string& problem : report.problems)
            check(false, ("validate: " + problem).c_str());
        check(report.ok, "the 90-frame choreography validates clean");
    }

    void cameraTravelAndSettle() {
        section("camera travels without teleports, then settles");
        FakeContentHost host;
        TemplateScene scene("ui_choreo", kFps, host, kW, kH);
        const UiPanelComposition panel = buildUiPanel(scene, panelSpec());
        const UiCameraChoreographySpec spec;
        applyUiCameraChoreography(scene, spec, panel);

        auto& rig = scene.cameraRig();
        const auto first = rig.sample(0.f);
        const auto last = rig.sample(static_cast<float>(spec.totalFrames) / kFps);
        const float dolly = first.position.z - last.position.z;
        check(dolly > 50.f, "the camera pushes toward the panel across the window");
        check(last.target.x < first.target.x, "the lateral drift moves the aim toward the text");

        // The zoom visibly grows the panel: project the card half-width at
        // both ends with each frame's own pose.
        chrononmotion::motion::ScreenCameraIntrinsics intrinsics;
        intrinsics.viewport = chrononmotion::Vector2(kW, kH);
        intrinsics.fovDegrees = first.fov;
        const chrononmotion::Vector2 c0 =
            chrononmotion::motion::projectToScreen(chrononmotion::Vector3(960.f, 540.f, 0.f), first, intrinsics);
        const chrononmotion::Vector2 e0 = chrononmotion::motion::projectToScreen(
            chrononmotion::Vector3(960.f + 450.f, 540.f, 0.f), first, intrinsics);
        intrinsics.fovDegrees = last.fov;
        const chrononmotion::Vector2 c1 =
            chrononmotion::motion::projectToScreen(chrononmotion::Vector3(960.f, 540.f, 0.f), last, intrinsics);
        const chrononmotion::Vector2 e1 = chrononmotion::motion::projectToScreen(
            chrononmotion::Vector3(960.f + 450.f, 540.f, 0.f), last, intrinsics);
        check(std::fabs(e1.x - c1.x) > std::fabs(e0.x - c0.x),
              "the push grows the projected panel width");
    }

    void framingFitsMeasuredBounds() {
        section("framing fits the measured bounds, never the authored numbers");
        const float required =
            uiFramingDistance(900.f, 50.f, chrononmotion::Vector2(kW, kH), 0.78f);
        check(required > 600.f && required < 1080.f,
              "the optical law puts a 900-unit panel inside a 1920 frame at fov 50");
        check(uiFramingDistance(450.f, 50.f, chrononmotion::Vector2(kW, kH), 0.78f) < required,
              "a narrower subject sits closer under the same law");

        FakeContentHost host;
        TemplateScene scene("ui_choreo", kFps, host, kW, kH);
        const UiPanelComposition panel = buildUiPanel(scene, panelSpec());
        applyUiCameraChoreography(scene, UiCameraChoreographySpec{}, panel);
        const float eyeZ = scene.cameraRig().sample(0.f).position.z;
        const float need = uiFramingDistance(panel.panelSize.x, 50.f,
                                             chrononmotion::Vector2(kW, kH), 0.78f) * 1.12f;
        check(eyeZ + 1.f >= need, "the eye sits no closer than the fitted distance");
    }

    void loweringNeedsNoNewLayerType() {
        section("lowering rides the existing RenderPlan contract");
        FakeContentHost backend;
        RenderPlanContentHost host(RenderPlanContentBackend{
            .createText = [&](const TextRequest& request) { return backend.createText(request); },
            .createImage = [&](const ImageRequest& request) { return backend.createImage(request); },
            .createVideo = [&](const VideoRequest& request) { return backend.createVideo(request); },
            .createShape = [&](const ShapeRequest& request) { return backend.createShape(request); },
            .currentFingerprint = [&](const ContentId& id) { return backend.currentFingerprint(id); }});
        TemplateScene scene("ui_choreo", kFps, host, kW, kH);
        const UiPanelComposition panel = buildUiPanel(scene, panelSpec());
        const UiCameraChoreographySpec spec;
        applyUiCameraChoreography(scene, spec, panel);

        const auto plan = lowerToRenderPlan(scene, host, "ui_choreography_v1", "ui_choreography.mp4");
        check(plan.canvas.width == 1920 && plan.canvas.height == 1080,
              "the canary lowers at 1920x1080");
        check(plan.canvas.duration.integral() == spec.totalFrames + 1,
              "the canary covers all 90 frames plus the settle hold");
        bool hasController = false;
        bool childrenBaked = true;
        for (const auto& layer : plan.layers) {
            if (layer.id == std::to_string(panel.root))
                hasController = true;
            if (layer.id == std::to_string(panel.card) || layer.id == std::to_string(panel.title) ||
                layer.id == std::to_string(panel.icon))
                childrenBaked = childrenBaked && layer.animation.has_value();
        }
        check(hasController, "the Null controller lowers as a transparent color layer");
        check(childrenBaked, "card, title and icon carry baked animation tracks");
        check(plan.camera_samples && plan.camera_samples->size() == spec.totalFrames + 1,
              "position, rotation and fov lower as CM3D-resolved camera samples");
        if (plan.camera_samples && plan.camera_samples->size() > 2) {
            const auto& first = plan.camera_samples->front().camera;
            const auto& middle = plan.camera_samples->at(plan.camera_samples->size() / 2).camera;
            const auto& last = plan.camera_samples->back().camera;
            check(first.position != middle.position || first.rotation_deg != middle.rotation_deg ||
                  first.fov_deg != middle.fov_deg || middle.position != last.position ||
                  middle.rotation_deg != last.rotation_deg || middle.fov_deg != last.fov_deg,
                  "resolved camera samples contain the authored motion");
        }
        check(plan.temporal_motion_blur && plan.temporal_motion_blur->samples == 8,
              "the choreography declares its temporal motion blur");
    }

    void badSpecsFailClosed() {
        section("bad specs fail closed");
        bool threw = false;
        try {
            FakeContentHost host;
            TemplateScene scene("ui_bad", kFps, host, kW, kH);
            UiPanelSpec bad = panelSpec();
            bad.title.clear();
            (void)buildUiPanel(scene, bad);
        } catch (const std::invalid_argument&) {
            threw = true;
        }
        check(threw, "an empty title is refused");

        threw = false;
        try {
            FakeContentHost host;
            TemplateScene scene("ui_bad", kFps, host, kW, kH);
            const UiPanelComposition panel = buildUiPanel(scene, panelSpec());
            UiCameraChoreographySpec bad;
            bad.zoomDuration = 0;
            applyUiCameraChoreography(scene, bad, panel);
        } catch (const std::invalid_argument&) {
            threw = true;
        }
        check(threw, "a zero-length zoom window is refused");

        threw = false;
        try {
            (void)uiFramingDistance(0.f, 50.f, chrononmotion::Vector2(kW, kH));
        } catch (const std::invalid_argument&) {
            threw = true;
        }
        check(threw, "a zero-width subject is refused by the framing law");
    }

}// namespace

int main() {
    nullControllerHierarchy();
    animatedParentingEndToEnd();
    cameraTravelAndSettle();
    framingFitsMeasuredBounds();
    loweringNeedsNoNewLayerType();
    badSpecsFailClosed();
    return chrononmotion_test::report();
}
