#include "chronontemplate/vintage_documentary/VintageDocumentaryPack.hpp"

#include "chronontemplate/core/PlanLowering.hpp"

#include "fake_content_host.hpp"
#include "motion_check.hpp"

#include <stdexcept>

using namespace chronontemplate;
using namespace chronontemplate::vintage_documentary;
using chronontemplate_test::FakeContentHost;
using chronontemplate_test::findLayer;
using chrononmotion_test::check;
using chrononmotion_test::checkNear;
using chrononmotion_test::section;

namespace {

    VintageDocumentaryScene canonicalScene() {
        VintageDocumentaryScene spec;
        spec.name = "vintage_test";
        spec.photoAsset = "assets/test/square_bottle_test.png";
        spec.title.text = "TORINO 1978";
        spec.glitch.startFrame = 130;
        spec.glitch.durationFrames = 10;
        return spec;
    }

    void theSceneAuthorsEveryLayerWithItsRequests() {
        section("vintage documentary scene");
        FakeContentHost host;
        TemplateScene scene("vintage_test", 30.f, host, 1920.f, 1080.f);
        const auto layers = addVintageDocumentaryScene(scene, canonicalScene());
        check(layers.background != 0 && layers.photo != 0 && layers.glitch != 0,
              "background, photo and glitch handles are all live");

        // The glitch duplicate is the last image request: it carries the
        // slice/RGB-split/mosaic treatment, not the clean card grade.
        checkNear(host.lastImageRequest().sliceDisplace, 0.6f, 1e-5f,
                  "the glitch layer carries slice displacement");
        checkNear(host.lastImageRequest().channelSplit, 5.f, 1e-5f,
                  "the glitch layer carries the RGB split");
        check(host.lastImageRequest().mosaicBlockSize == 12,
              "the glitch layer carries mosaic blocks");
        checkNear(host.lastImageRequest().tornEdgeAmount, 7.f, 1e-5f,
                  "the glitch duplicate keeps the torn alpha edge");
        checkNear(host.lastImageRequest().scanlineIntensity, 0.06f, 1e-5f,
                  "the glitch duplicate keeps the analog scanlines");

        const auto* tint = host.findShapeRequest("vintage_test_photo_tint");
        check(tint != nullptr && tint->fillColor == "#D9A7A0",
              "the muted pink wash rides the photo");
        check(host.findShapeRequest("vintage_test_bg_ground") != nullptr,
              "the black ground is authored");
        check(host.findShapeRequest("vintage_test_bg_light") != nullptr,
              "the diffuse dark-red light is authored");
        check(host.findShapeRequest("vintage_test_bg_vignette") != nullptr,
              "the vignette plate is authored");
        check(host.findShapeRequest("vintage_test_dust_0") != nullptr,
              "deterministic film dust is authored");
        const auto* rule = host.findShapeRequest("vintage_test_divider");
        check(rule != nullptr && rule->fillColor == "#FFFFFF",
              "the white divider rule is authored");
        check(host.findShapeRequest("vintage_test_divider_halo") != nullptr,
              "the divider halo sandwich is authored");

        // Alive windows: the glitch layer draws only inside its window.
        const FrameSubmission early = scene.submit(100);
        const FrameSubmission during = scene.submit(135);
        const FrameSubmission late = scene.submit(149);
        const BoundLayer* gEarly = findLayer(early, layers.glitch);
        const BoundLayer* gDuring = findLayer(during, layers.glitch);
        const BoundLayer* gLate = findLayer(late, layers.glitch);
        check(gEarly && !gEarly->transform.visible, "the glitch layer is silent before its window");
        check(gDuring && gDuring->transform.visible, "the glitch layer draws inside its window");
        check(gLate && !gLate->transform.visible, "the glitch layer is silent after its window");
        const BoundLayer* photo = findLayer(during, layers.photo);
        check(photo && photo->transform.visible, "the clean card survives underneath the glitch");
        check(scene.validate().empty(), "the vintage scene validates");
    }

    void invalidSpecsFailClosed() {
        section("vintage documentary validation");
        int throws = 0;
        {
            FakeContentHost host;
            TemplateScene scene("v", 30.f, host, 1920.f, 1080.f);
            auto spec = canonicalScene();
            spec.photoAsset.clear();
            try {
                addVintageDocumentaryScene(scene, spec);
            } catch (const std::invalid_argument&) { ++throws; }
        }
        {
            FakeContentHost host;
            TemplateScene scene("v", 30.f, host, 1920.f, 1080.f);
            auto spec = canonicalScene();
            spec.photo.tintColor = "pink";
            try {
                addVintageDocumentaryScene(scene, spec);
            } catch (const std::invalid_argument&) { ++throws; }
        }
        {
            FakeContentHost host;
            TemplateScene scene("v", 30.f, host, 1920.f, 1080.f);
            auto spec = canonicalScene();
            spec.glitch.startFrame = 145; // 145+10 overflows the 150-frame scene
            try {
                addVintageDocumentaryScene(scene, spec);
            } catch (const std::invalid_argument&) { ++throws; }
        }
        {
            FakeContentHost host;
            TemplateScene scene("v", 30.f, host, 1920.f, 1080.f);
            auto spec = canonicalScene();
            spec.title.text.clear();
            try {
                addVintageDocumentaryScene(scene, spec);
            } catch (const std::invalid_argument&) { ++throws; }
        }
        check(throws == 4, "missing asset, bad hex, overflowing glitch and empty title all throw");
    }

    void loweringMapsTheNewFrameEffects() {
        section("vintage frame lowering");
        ContentHandle handle;
        handle.id = "image/test.png";
        handle.kind = chrononmotion::motion::ContentKind::Image;
        handle.metrics.naturalSize = chrononmotion::Vector2(640.f, 360.f);
        ImageRequest request;
        request.tornEdgeAmount = 7.f;
        request.tornEdgeScale = 9.f;
        request.tornEdgeSeed = 7;
        request.scanlineIntensity = 0.06f;
        request.scanlineSpacing = 0.004f;
        request.mosaicBlockSize = 12;
        const auto plan = makeImageLayerPlan(request, handle);
        bool torn = false, scan = false, mosaic = false;
        for (const auto& effect : plan.effects) {
            using Kind = chronon3d::render_plan::LayerPlan::EffectKindPlan;
            if (effect.kind == Kind::RoughenEdges) torn = true;
            if (effect.kind == Kind::WaveWarp) scan = true;
            if (effect.kind == Kind::Mosaic) mosaic = true;
        }
        check(torn && scan && mosaic,
              "torn edge, scanlines and mosaic lower to native effects");
        int badThrows = 0;
        {
            ImageRequest bad = request;
            bad.tornEdgeAmount = 65.f;
            try {
                makeImageLayerPlan(bad, handle);
            } catch (const std::invalid_argument&) { ++badThrows; }
        }
        {
            ImageRequest bad = request;
            bad.mosaicBlockSize = 1;
            try {
                makeImageLayerPlan(bad, handle);
            } catch (const std::invalid_argument&) { ++badThrows; }
        }
        {
            ImageRequest clean;
            try {
                const auto cleanPlan = makeImageLayerPlan(clean, handle);
                check(cleanPlan.effects.empty(), "a default frame lowers with no effects");
            } catch (const std::invalid_argument&) { ++badThrows; }
        }
        check(badThrows == 2, "oversized torn edge and 1px mosaic both throw");
    }

    void brushSamplersMirrorTheReferenceRenderer() {
        section("brush reveal samplers");
        BrushReveal brush;
        brush.startFrame = 0;
        brush.durationFrames = 60;
        // Progress: clamped smoothstep, mirroring the Python renderer.
        checkNear(brushRevealProgress(brush, -5), 0.f, 1e-6f,
                  "reveal progress is 0 before the window");
        checkNear(brushRevealProgress(brush, 0), 0.f, 1e-6f,
                  "reveal progress starts at 0");
        checkNear(brushRevealProgress(brush, 30), 0.5f, 1e-6f,
                  "reveal progress is 0.5 halfway");
        checkNear(brushRevealProgress(brush, 60), 1.f, 1e-6f,
                  "reveal progress lands at 1");
        checkNear(brushRevealProgress(brush, 200), 1.f, 1e-6f,
                  "reveal progress stays 1 after the window");
        // Edge: right-to-left sweeps 800 -> -40 over a 760px card.
        checkNear(brushEdgeX(brush, 0, 760.f), 800.f, 1e-4f,
                  "the R2L edge starts off-canvas right");
        checkNear(brushEdgeX(brush, 60, 760.f), -40.f, 1e-4f,
                  "the R2L edge ends off-canvas left");
        check(brushEdgeX(brush, 0, 760.f) > brushEdgeX(brush, 30, 760.f) &&
              brushEdgeX(brush, 30, 760.f) > brushEdgeX(brush, 60, 760.f),
              "the R2L edge decreases monotonically");
        BrushReveal ltr = brush;
        ltr.direction = BrushDirection::LeftToRight;
        checkNear(brushEdgeX(ltr, 0, 760.f), -40.f, 1e-4f,
                  "the L2R edge starts off-canvas left");
        checkNear(brushEdgeX(ltr, 60, 760.f), 800.f, 1e-4f,
                  "the L2R edge ends off-canvas right");
        // Push-in: ease-out 1.08 -> 1.0 over 70 frames.
        checkNear(brushPushScale(brush, 0), 1.08f, 1e-6f,
                  "the push-in starts at 1.08");
        checkNear(brushPushScale(brush, 70), 1.0f, 1e-6f,
                  "the push-in settles at 1.0");
        check(brushPushScale(brush, 0) > brushPushScale(brush, 35) &&
              brushPushScale(brush, 35) > brushPushScale(brush, 70),
              "the push-in decreases monotonically");
        BrushReveal off;
        off.enabled = false;
        checkNear(brushRevealProgress(off, 10), 1.f, 1e-6f,
                  "a disabled brush reads fully revealed");
        checkNear(brushPushScale(off, 10), 1.f, 1e-6f,
                  "a disabled brush reads no push");
    }

    void brushSpecsFailClosed() {
        section("brush reveal validation");
        int throws = 0;
        const auto bad = [&](auto mutate) {
            FakeContentHost host;
            TemplateScene scene("v", 30.f, host, 1920.f, 1080.f);
            auto spec = canonicalScene();
            mutate(spec.brush);
            try {
                (void) addVintageDocumentaryScene(scene, spec);
            } catch (const std::invalid_argument&) { ++throws; }
        };
        bad([](BrushReveal& b) { b.durationFrames = 0; });
        bad([](BrushReveal& b) { b.startFrame = 140; }); // 140+60 overflows
        bad([](BrushReveal& b) { b.bristleAmplitudePx = 200.f; });
        bad([](BrushReveal& b) { b.edgeSoftnessPx = 0.f; });
        bad([](BrushReveal& b) { b.slant = 2.f; });
        bad([](BrushReveal& b) { b.pushFrom = 0.9f; });
        bad([](BrushReveal& b) { b.pushTo = 1.2f; }); // pushTo > pushFrom
        bad([](BrushReveal& b) { b.leadColor = "gold"; });
        bad([](BrushReveal& b) { b.pushDurationFrames = 400; });
        check(throws == 9, "every out-of-range brush spec throws");
        // Disabled brush skips validation and keeps the legacy entrance.
        FakeContentHost host;
        TemplateScene scene("v", 30.f, host, 1920.f, 1080.f);
        auto spec = canonicalScene();
        spec.brush.enabled = false;
        spec.brush.durationFrames = 0; // ignored while disabled
        const auto layers = addVintageDocumentaryScene(scene, spec);
        check(layers.photo != 0 && scene.validate().empty(),
              "a disabled brush still authors a valid scene");
    }

    void brushSceneAuthorsThePushIn() {
        section("brush scene push-in");
        FakeContentHost host;
        TemplateScene scene("brush_push", 30.f, host, 1920.f, 1080.f);
        auto spec = canonicalScene();
        spec.brush.photoAsset = "assets/famous_people_trio_v1/sources/neil_armstrong.jpg";
        const auto layers = addVintageDocumentaryScene(scene, spec);
        check(host.lastImageRequest().path ==
              "assets/famous_people_trio_v1/sources/neil_armstrong.jpg",
              "the brush photo asset reaches the glitch duplicate request");
        // Push-in 1.08 -> 1.0: the card world scale settles across the window.
        const FrameSubmission early = scene.submit(0);
        const FrameSubmission settled = scene.submit(70);
        const BoundLayer* a = findLayer(early, layers.photo);
        const BoundLayer* b = findLayer(settled, layers.photo);
        check(a && b && a->transform.visible && b->transform.visible,
              "the pushed card stays visible across its window");
        if (a && b) {
            const float sa = a->transform.world[0];
            const float sb = b->transform.world[0];
            check(sa > sb && sa / sb < 1.2f,
                  "the card scale eases down from the 1.08 push");
        }
        check(scene.validate().empty(), "the brush scene validates");
    }

} // namespace

int main() {
    theSceneAuthorsEveryLayerWithItsRequests();
    invalidSpecsFailClosed();
    loweringMapsTheNewFrameEffects();
    brushSamplersMirrorTheReferenceRenderer();
    brushSpecsFailClosed();
    brushSceneAuthorsThePushIn();
    return chrononmotion_test::report();
}
