#include "chronontemplate/core/PlanLowering.hpp"
#include "chronontemplate/core/RenderPlanContentHost.hpp"
#include "fake_content_host.hpp"
#include "motion_check.hpp"

#include <chronon3d/animation/temporal/temporal_samples.hpp>

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
    // focus_distance is camera-space along the optical axis (canonical contract):
    // the lowering passes it through unchanged, world-Z derivation happens downstream.
    rig.setPosition({0.f, 0.f, -8.f}).clearTarget().setFocusDistance(420.f);
    rig.focusDistanceTrack().add(0.f, 420.f).add(1.f, 620.f);
    // Authored aperture truth is f/N: legacy gain 0.06 maps to f/11.2.
    // Zero denotes disabled, not a physical f-stop. Step to the minimum
    // supported aperture before interpolating, so no sampled pose is in (0, 0.7).
    rig.fStopTrack().addDiscrete(0.f, 0.f).add(1.f / 24.f, 0.7f).add(1.f, 11.2f);
    rig.maxBlurTrack().add(0.f, 10.f).add(1.f, 18.f);
    const auto dofPlan = lowerToRenderPlan(dofScene, {{dofTitle.id(), dofText}});
    check(dofPlan.camera && dofPlan.camera->dof_enabled,
          "animated DOF is enabled in the base plan even when the aperture opens after frame zero");
    check(dofPlan.camera_samples && dofPlan.camera_samples->size() == dofPlan.canvas.duration.integral(),
          "animated focus, aperture, and max blur lower as resolved frame samples");
    if (dofPlan.camera_samples && !dofPlan.camera_samples->empty()) {
        const auto& first = dofPlan.camera_samples->front().camera;
        const auto& last = dofPlan.camera_samples->back().camera;
        check(first.dof_focus_distance == 420.f && last.dof_focus_distance == 620.f &&
              first.dof_aperture == 0.f && first.dof_max_blur == 10.f &&
              last.dof_focus_distance >= 420.f && last.dof_focus_distance <= 620.f &&
              last.dof_f_stop > 0.f && last.dof_f_stop <= 11.2f &&
              last.dof_max_blur >= 10.f && last.dof_max_blur <= 18.f,
              "resolved camera samples preserve authored DoF endpoints");
    }

    const auto runtimeLowered = lowerToRuntimeRenderPlan(
        dofScene, {{dofTitle.id(), dofText}}, "animated-dof-camera-v1",
        "runtime-camera-test", "runtime-camera-test.mp4");
    check(runtimeLowered.plan.camera.has_value() &&
          !runtimeLowered.plan.camera_samples.has_value(),
          "runtime lowering keeps a static camera default and omits duplicate dense camera tracks");
    check(runtimeLowered.camera.fingerprint == "animated-dof-camera-v1",
          "runtime lowering carries the stable camera identity into the provider");
    const auto runtimeCamera = runtimeLowered.camera.sample(12.0);
    chrononmotion_test::checkNear(runtimeCamera.position[2], 8.f, 1e-5f,
              "runtime provider samples the CM3D rig at frame/fps time");
    chrononmotion_test::checkNear(runtimeCamera.dof_focus_distance, 520.f, 1e-4f,
              "runtime provider carries the fractional-time focus distance");

    // The parented provider retains a dedicated hierarchy after the authored
    // template is changed and destroyed, including at fractional shutter times.
    const auto parented = [&] {
        TemplateScene source("parented-runtime", 24.f, host, 640.f, 360.f);
        auto& controller = source.group("Camera Null");
        controller.layer().tracks.position.add(0.f, {10.f, 0.f, 0.f},
                                               chrononmotion::motion::Easing::easeInOut());
        controller.layer().tracks.position.add(1.f, {110.f, 0.f, 0.f});
        source.cameraRig().setParent(controller.id()).setPosition({5.f, 0.f, 0.f});
        return lowerToRuntimeRenderPlan(source, {}, "rig-parent-v1");
    }();
    const auto parentedFirst = parented.camera.sample(0.0);
    const auto parentedMiddle = parented.camera.sample(12.5);
    const auto parentedAgain = parented.camera.sample(0.0);
    chrononmotion_test::checkNear(parentedFirst.position[0], 15.f, 1e-4f,
                                 "parented runtime includes Null translation");
    check(parentedMiddle.position[0] > parentedFirst.position[0],
          "parented runtime samples the animated Null at fractional time");
    chrononmotion_test::checkNear(parentedAgain.position[0], parentedFirst.position[0], 1e-4f,
                                 "parented runtime remains deterministic after a seek");

    // The offline job supplies its exact C3D shutter schedule. Verify every
    // timestamp against the same parented runtime provider, including preroll.
    TemplateScene scheduled("scheduled-camera", 24.f, host, 640.f, 360.f);
    auto& scheduledParent = scheduled.group("Camera Null");
    scheduledParent.layer().tracks.position.add(0.f, {10.f, 0.f, 0.f},
                                                chrononmotion::motion::Easing::easeInOut());
    scheduledParent.layer().tracks.position.add(1.f, {110.f, 0.f, 0.f});
    scheduled.cameraRig().setParent(scheduledParent.id()).setPosition({5.f, 0.f, 0.f});
    const auto scheduledRuntime = lowerToRuntimeRenderPlan(scheduled, {}, "scheduled-camera-v1");
    std::vector<double> cameraTimes;
    for (int frame : {0, 12, 24}) {
        const auto shutter = chronon3d::temporal::make_temporal_sample_plan(
            chronon3d::temporal::TemporalSampleParams{}, 8, chronon3d::Frame{frame},
            chronon3d::FrameRate{24, 1}, 640, 360);
        check(shutter.valid(), "C3D job shutter schedule is valid");
        for (const auto& sample : shutter.contexts) cameraTimes.push_back(sample.time.frame);
    }
    std::sort(cameraTimes.begin(), cameraTimes.end());
    const auto scheduledPlan = lowerToRenderPlan(scheduled, {}, "scheduled", "scheduled.png", cameraTimes);
    check(scheduledPlan.camera_samples && scheduledPlan.camera_samples->size() == cameraTimes.size(),
          "Template forwards all C3D job shutter times to the Motion camera bake");
    if (scheduledPlan.camera_samples && scheduledPlan.camera_samples->size() == cameraTimes.size()) {
        for (std::size_t i = 0; i < cameraTimes.size(); ++i) {
            const auto& sample = scheduledPlan.camera_samples->at(i);
            check(sample.frame == cameraTimes[i], "Template preserves exact shutter timestamp");
            const auto direct = scheduledRuntime.camera.sample(sample.frame);
            for (int axis = 0; axis < 3; ++axis) {
                chrononmotion_test::checkNear(sample.camera.position[axis], direct.position[axis], 1e-4f,
                                              "Template offline and runtime world positions agree");
                chrononmotion_test::checkNear(sample.camera.rotation_deg[axis], direct.rotation_deg[axis], 1e-3f,
                                              "Template offline and runtime orientations agree");
            }
        }
    }
    bool emptyScheduleRejected = false;
    try { (void)lowerToRenderPlan(scheduled, {}, "scheduled", "scheduled.png", {}); }
    catch (const std::invalid_argument&) { emptyScheduleRejected = true; }
    check(emptyScheduleRejected, "explicit empty camera schedule fails closed");
    bool duplicateScheduleRejected = false;
    try { (void)lowerToRenderPlan(scheduled, {}, "scheduled", "scheduled.png", {1., 1.}); }
    catch (const std::invalid_argument&) { duplicateScheduleRejected = true; }
    check(duplicateScheduleRejected, "duplicate camera schedule entries fail closed");

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

    ImageRequest editorialEffects;
    editorialEffects.path = "archive.jpg";
    editorialEffects.lightLeak = 0.6f;
    editorialEffects.channelSplit = 4.f;
    editorialEffects.channelTrail = 3;
    editorialEffects.sliceDisplace = 0.8f;
    const auto editorialHandle = host.createImage(editorialEffects);
    const auto editorialPlan = makeImageLayerPlan(editorialEffects, editorialHandle);
    check(editorialPlan.effects.size() == 5 &&
          editorialPlan.effects[0].kind == LayerPlan::EffectKindPlan::LightRays &&
          editorialPlan.effects[1].kind == LayerPlan::EffectKindPlan::Glow &&
          editorialPlan.effects[2].kind == LayerPlan::EffectKindPlan::ChromaticAberration &&
          editorialPlan.effects[3].kind == LayerPlan::EffectKindPlan::Echo &&
          editorialPlan.effects[4].kind == LayerPlan::EffectKindPlan::MeshWarp,
          "image frame exposes composable light leak and channel/slice glitch looks");

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

    ShapeSpec pathSpec;
    pathSpec.size = {400.f, 300.f};
    pathSpec.name = "TrimLineGraph";
    pathSpec.geometry = ShapeGeometry::Path;
    pathSpec.fillEnabled = false;
    pathSpec.strokeColor = "#F8FAFC";
    pathSpec.strokeWidth = 4.5f;
    pathSpec.strokeCap = "round";
    pathSpec.strokeJoin = "round";
    pathSpec.strokeDashArray = {12.f, 6.f};
    pathSpec.strokeDashOffset = 2.f;
    pathSpec.path = {
        ShapePathCommand::moveTo(-96.f, 104.f),
        ShapePathCommand::lineTo(86.f, -96.f),
        ShapePathCommand::lineTo(172.f, 14.f)
    };
    pathSpec.trim = ShapeTrimSpec{
        .start = 0.f,
        .end = 0.f,
        .offset = 0.f,
        .easing = "out_cubic",
        .keyframes = {{0, 0.f, 0.f, 0.f}, {60, 0.f, 1.f, 0.f}}
    };
    pathSpec.glowRadius = 18.f;
    pathSpec.glowIntensity = 0.75f;
    pathSpec.glowColor = "#67E8F9";
    pathSpec.bloomThreshold = 0.75f;
    pathSpec.bloomRadius = 24.f;
    pathSpec.bloomIntensity = 0.45f;
    pathSpec.noiseAmount = 0.12f;
    pathSpec.animatedNoise = true;

    TemplateScene pathScene("path-trim-glow-lowering", 30.f, connectedHost, 1920.f, 1080.f);
    (void)pathScene.shape(pathSpec);
    const auto pathPlan = lowerToRenderPlan(pathScene, connectedHost);
    check(pathPlan.layers.size() == 1 && pathPlan.layers.front().shape &&
          pathPlan.layers.front().shape->type == ShapeContentTypePlan::Path &&
          pathPlan.layers.front().shape->path.size() == 3 &&
          pathPlan.layers.front().shape->stroke &&
          pathPlan.layers.front().shape->stroke->cap == "round" &&
          pathPlan.layers.front().shape->stroke->join == "round" &&
          pathPlan.layers.front().shape->stroke->dash_array.size() == 2 &&
          pathPlan.layers.front().shape->operators.size() == 1 &&
          pathPlan.layers.front().shape->operators.front().kind == PathOperatorKindPlan::Trim &&
          pathPlan.layers.front().shape->operators.front().trim_animation.has_value() &&
          pathPlan.layers.front().effects.size() == 3,
          "TemplateScene::shape lowers Path geometry, Trim animation, stroke cap/join/dash, Glow, Bloom, and Noise");
}
