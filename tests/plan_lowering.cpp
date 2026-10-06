#include "chronontemplate/core/PlanLowering.hpp"
#include "chronontemplate/core/RenderPlanContentHost.hpp"
#include "fake_content_host.hpp"
#include "motion_check.hpp"

#include <algorithm>
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

    TemplateScene dofScene("animated-doF", 24.f, host, 640.f, 360.f);
    auto& dofTitle = dofScene.text(TextSpec{.text = "Archive", .font = "Inter.ttf", .fontSize = 48.f});
    LayerPlan dofText = text;
    dofText.text = "Archive";
    auto& rig = dofScene.cameraRig();
    // Use the Motion camera's -Z forward axis so the converted focus planes
    // stay inside RenderPlan's positive world-Z focus range.
    rig.setPosition({0.f, 0.f, -8.f}).clearTarget().setFocusDistance(420.f);
    rig.focusDistanceTrack().add(0.f, 420.f).add(1.f, 620.f);
    rig.apertureTrack().add(0.f, 0.f).add(1.f, 0.06f);
    rig.maxBlurTrack().add(0.f, 10.f).add(1.f, 18.f);
    const auto dofPlan = lowerToRenderPlan(dofScene, {{dofTitle.id(), dofText}});
    check(dofPlan.camera && dofPlan.camera->dof_enabled,
          "animated DOF is enabled in the base plan even when the aperture opens after frame zero");
    const auto findTrack = [&](CameraPropertyPlan property) -> const CameraTrackPlan* {
        if (!dofPlan.camera_animation) return nullptr;
        for (const auto& track : *dofPlan.camera_animation)
            if (track.property == property) return &track;
        return nullptr;
    };
    const auto* focus = findTrack(CameraPropertyPlan::FocusDistance);
    const auto* aperture = findTrack(CameraPropertyPlan::Aperture);
    const auto* maxBlur = findTrack(CameraPropertyPlan::MaxBlur);
    check(focus && aperture && maxBlur,
          "animated focus, aperture, and max blur lower as native camera properties");
    check(focus && focus->keyframes.front().value.front() == 428.f &&
          focus->keyframes.back().value.front() == 628.f &&
          aperture && aperture->keyframes.front().value.front() == 0.f &&
          aperture->keyframes.back().value.front() == 0.06f &&
          maxBlur && maxBlur->keyframes.front().value.front() == 10.f &&
          maxBlur->keyframes.back().value.front() == 18.f,
          "native DOF camera tracks preserve their authored endpoint values");

    ImageRequest imageRequest;
    imageRequest.path = "archive.jpg";
    imageRequest.fit = ImageFitMode::Cover;
    imageRequest.targetSize = {320.f, 180.f};
    imageRequest.crop = {true, {0.1f, 0.2f}, {0.8f, 0.7f}};
    imageRequest.crop.flipX = true;
    imageRequest.cornerRadius = 12.f;
    imageRequest.borderColor = "#E8E2D5";
    imageRequest.borderWidth = 6.f;
    imageRequest.saturation = 0.78f;
    imageRequest.contrast = 1.08f;
    imageRequest.grain = 0.02f;
    imageRequest.vignette = 0.12f;
    imageRequest.grainSeed = 1986;
    const auto imageHandle = host.createImage(imageRequest);
    const auto imagePlan = makeImageLayerPlan(imageRequest, imageHandle);
    check(imagePlan.type == LayerType::Image && imagePlan.asset == imageHandle.id &&
          imagePlan.fit == FitMode::Cover && imagePlan.crop && imagePlan.crop->enabled &&
          imagePlan.crop->flip_x &&
          imagePlan.size_dimensions == 2,
          "image ContentHost adapter maps identity, viewport, fit, normalized crop, and content flip");
    const float effectiveCropAspect =
        (imageHandle.metrics.naturalSize.x * imagePlan.crop->size[0]) /
        (imageHandle.metrics.naturalSize.y * imagePlan.crop->size[1]);
    check(imagePlan.crop->origin[0] >= imageRequest.crop.origin.x &&
          imagePlan.crop->origin[1] >= imageRequest.crop.origin.y &&
          imagePlan.crop->origin[0] + imagePlan.crop->size[0] <=
              imageRequest.crop.origin.x + imageRequest.crop.size.x + 1e-6f &&
          imagePlan.crop->origin[1] + imagePlan.crop->size[1] <=
              imageRequest.crop.origin.y + imageRequest.crop.size.y + 1e-6f &&
          std::fabs(effectiveCropAspect - 320.f / 180.f) < 1e-5f,
          "cover fits the explicit crop to the target aspect without stretching its source");
    check(imagePlan.radius == 12.f && imagePlan.style && imagePlan.style->background &&
          imagePlan.style->background->color == "#E8E2D5" &&
          imagePlan.style->background->padding[0] == 6.f,
          "image ContentHost adapter maps rounded corners and frame border");
    check(imagePlan.effects.size() == 4 &&
          imagePlan.effects[0].canonical_effect_id == "color.saturation" &&
          imagePlan.effects[1].canonical_effect_id == "color.contrast" &&
          imagePlan.effects[2].kind == LayerPlan::EffectKindPlan::Noise &&
          imagePlan.effects[2].seed == 1986 &&
          imagePlan.effects[3].kind == LayerPlan::EffectKindPlan::Vignette,
          "image ContentHost adapter maps saturation, contrast, stable grain, and vignette");

    const ShapeRequest shapeRequest{{640.f, 360.f}, "#C92A32", "RedPortal"};
    const auto shapeHandle = host.createShape(shapeRequest);
    const auto shapePlan = makeShapeLayerPlan(shapeRequest, shapeHandle);
    check(shapePlan.type == LayerType::Shape && shapePlan.shape &&
          shapePlan.shape->type == ShapeContentTypePlan::Rect &&
          shapePlan.size == std::array<float, 2>{640.f, 360.f},
          "shape ContentHost adapter maps a native filled rectangle");

    ShapeRequest radialRequest{{64.f, 64.f}, "#FFFFFF", "RadialGlow"};
    radialRequest.geometry = ShapeGeometry::Ellipse;
    radialRequest.radialGradient = ShapeRadialGradient{
        .center = {0.5f, 0.5f}, .radius = 0.5f,
        .stops = {{0.f, "#38BDF8", 0.85f}, {1.f, "#38BDF8", 0.f}}};
    const auto radialHandle = host.createShape(radialRequest);
    const auto radialPlan = makeShapeLayerPlan(radialRequest, radialHandle);
    check(radialPlan.shape && radialPlan.shape->type == ShapeContentTypePlan::Ellipse &&
          radialPlan.shape->gradient && !radialPlan.shape->fill_color &&
          radialPlan.shape->gradient->opacity_stops.size() == 2 &&
          radialPlan.shape->gradient->opacity_stops.back().opacity == 0.f,
          "native ellipses preserve radial color and opacity stops in RenderPlan lowering");

    ShapeRequest nativeField{{640.f, 360.f}, "#0B0E14", "Field"};
    nativeField.field = chronon3d::graphics::Field2D{
        .generator = chronon3d::graphics::Field2DGenerator::Fractal,
        .seed = 73, .frequency = 4.f, .octaves = 5};
    nativeField.fieldRamp = chronon3d::graphics::GradientDefinition::linear(
        {0.f, 0.5f}, {1.f, 0.5f}, {{0.f, {0.1f, 0.05f, 0.2f, 0.2f}},
                                  {0.5f, {0.6f, 0.2f, 0.8f, 0.8f}},
                                  {1.f, {0.9f, 0.8f, 1.f, 1.f}}});
    nativeField.fieldRenderScale = 2;
    nativeField.fieldDrift = chronon3d::Vec2{0.02f, -0.01f};
    nativeField.noiseAmount = 0.12f;
    nativeField.noiseSeed = 1986;
    nativeField.animatedNoise = true;
    nativeField.noiseSize = 2.5f;
    const auto fieldHandle = host.createShape(nativeField);
    const auto fieldLayer = makeShapeLayerPlan(nativeField, fieldHandle);
    check(fieldLayer.shape && fieldLayer.shape->field && fieldLayer.shape->field_ramp &&
          fieldLayer.shape->field_render_scale == 2 && fieldLayer.shape->field_drift &&
          fieldLayer.effects.size() == 1 && fieldLayer.effects.front().kind == LayerPlan::EffectKindPlan::Noise &&
          fieldLayer.effects.front().noise_size == 2.5f && fieldLayer.effects.front().animated,
          "shape lowering retains native field/ramp/drift and seeded animated grain controls");

    ShapeRequest nativeMesh{{640.f, 360.f}, "#0B0E14", "Mesh"};
    nativeMesh.gradientMesh = chronon3d::graphics::GradientMesh::four_corner(
        {0.1f, 0.1f, 0.2f, 1.f}, {0.8f, 0.1f, 0.3f, 1.f},
        {0.1f, 0.7f, 0.8f, 1.f}, {0.9f, 0.8f, 1.f, 1.f});
    const auto meshLayer = makeShapeLayerPlan(nativeMesh, host.createShape(nativeMesh));
    check(meshLayer.shape && meshLayer.shape->gradient_mesh &&
          meshLayer.shape->gradient_mesh->nodes.size() == 4 && !meshLayer.shape->fill_color,
          "shape lowering retains native GradientMesh nodes without a solid-color alias");

    FakeContentHost assetBackend;
    RenderPlanContentHost connectedHost(RenderPlanContentBackend{
        .createText = [&](const TextRequest& request) { return assetBackend.createText(request); },
        .createImage = [&](const ImageRequest& request) { return assetBackend.createImage(request); },
        .createVideo = [&](const VideoRequest& request) { return assetBackend.createVideo(request); },
        .createShape = [&](const ShapeRequest& request) { return assetBackend.createShape(request); },
        .currentFingerprint = [&](const ContentId& id) { return assetBackend.currentFingerprint(id); }});
    TemplateScene connectedScene("content-host-lowering", 24.f, connectedHost, 640.f, 360.f);
    connectedScene.setTemporalMotionBlur(180.f, 4);
    auto& connectedText = connectedScene.text(TextSpec{.text = "Archive", .font = "Inter.ttf", .fontSize = 42.f});
    auto& connectedImage = connectedScene.image(ImageSpec{
        .path = "archive.jpg", .frame = {.cornerRadius = 8.f, .borderColor = "#E8E2D5",
            .borderWidth = 4.f, .saturation = 0.82f, .contrast = 1.12f,
            .grain = 0.02f, .vignette = 0.1f, .grainSeed = 1940},
        .fit = ImageFitMode::Cover, .targetSize = {300.f, 180.f}});
    auto& connectedShape = connectedScene.shape(ShapeSpec{{300.f, 180.f}, "#C92A32", "Portal"});
    (void)connectedText;
    (void)connectedImage;
    (void)connectedShape;
    const auto connectedPlan = lowerToRenderPlan(connectedScene, connectedHost);
    check(connectedPlan.temporal_motion_blur &&
          connectedPlan.temporal_motion_blur->shutter_angle == 180.f &&
          connectedPlan.temporal_motion_blur->samples == 4,
          "TemplateScene lowers temporal shutter blur as a native RenderPlan setting");
    check(connectedPlan.layers.size() == 3,
          "ContentHost callback adapter lowers every created content binding");

    TemplateScene styledScene("styled-map-label", 24.f, connectedHost, 640.f, 360.f);
    const TextSpec styledSpec{
        .text = "ROME", .font = "Inter.ttf", .fontSize = 30.f, .color = "#F8F5EA",
        .name = "map_label", .stroke = TextStrokeStyle{"#07121A", 2.f},
        .shadow = TextShadowStyle{"#000000", 0.7f, 8.f, {1.f, 3.f}},
        .glow = TextGlowStyle{"#68E1FD", 18.f, 0.2f},
        .background = TextBackgroundStyle{"#07121A", 0.65f, 10.f, {8.f, 5.f}}};
    (void)styledScene.text(styledSpec);
    const auto styledPlan = lowerToRenderPlan(styledScene, connectedHost);
    check(styledPlan.layers.size() == 1 && styledPlan.layers.front().style &&
          styledPlan.layers.front().style->stroke && styledPlan.layers.front().style->shadow &&
          styledPlan.layers.front().style->glow && styledPlan.layers.front().style->background,
          "map typography controls lower to Chronon's native stroke, shadow, glow, and chip fields");
    if (styledPlan.layers.size() == 1 && styledPlan.layers.front().style) {
        const auto& style = *styledPlan.layers.front().style;
        check(style.stroke && style.stroke->width && *style.stroke->width == 2.f &&
              style.shadow && style.shadow->opacity && *style.shadow->opacity == 0.7f &&
              style.glow && style.glow->radius == 18.f &&
              style.background && style.background->opacity && *style.background->opacity == 0.65f,
              "text effects preserve caller-authored values across the connected RenderPlan boundary");
    }
    const auto connectedImagePlan = std::find_if(connectedPlan.layers.begin(), connectedPlan.layers.end(),
        [](const LayerPlan& layer) { return layer.type == LayerType::Image; });
    const auto connectedShapePlan = std::find_if(connectedPlan.layers.begin(), connectedPlan.layers.end(),
        [](const LayerPlan& layer) { return layer.type == LayerType::Shape; });
    const auto& connectedNaturalSize = connectedImage.layer().content.metrics.naturalSize;
    const float connectedCropAspect = connectedImagePlan != connectedPlan.layers.end() &&
                                      connectedImagePlan->crop
        ? (connectedNaturalSize.x * connectedImagePlan->crop->size[0]) /
              (connectedNaturalSize.y * connectedImagePlan->crop->size[1])
        : 0.f;
    check(connectedImagePlan != connectedPlan.layers.end() && connectedImagePlan->crop &&
          connectedImagePlan->crop->enabled && connectedImagePlan->fit == FitMode::Cover &&
          std::fabs(connectedCropAspect - 300.f / 180.f) < 1e-5f &&
          connectedImagePlan->effects.size() == 4 && connectedImagePlan->style &&
          connectedImagePlan->style->background,
          "ContentHost adapter carries a source-bounded cover crop, frame, and look into the connected plan");
    check(connectedShapePlan != connectedPlan.layers.end() && connectedShapePlan->shape &&
          connectedShapePlan->shape->fill_color.has_value(),
          "ContentHost adapter carries the red portal as a native shape plan");
}
