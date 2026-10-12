// Archival optical lens: the three presets carry the taratura table values,
// the frame style lowers to the native LensDistortion / ChromaticAberration /
// GaussianBlur effects in pipeline order, a flat frame stays effect-free,
// and out-of-range optics fail closed on both authoring paths.
#include "chronontemplate/single_images/ArchivalLensLook.hpp"

#include "chronontemplate/core/PlanLowering.hpp"
#include "fake_content_host.hpp"
#include "motion_check.hpp"

#include <stdexcept>

using namespace chronontemplate;
using chronontemplate_test::FakeContentHost;
using chrononmotion_test::check;
using chrononmotion_test::checkNear;
using chrononmotion_test::section;

namespace {

    void theThreePresetsCarryTheTableValues() {
        section("archival lens presets");
        const ImageFrameStyle wsj = archivalLensFrameStyle(ArchivalLensLook::WsjReddit);
        checkNear(wsj.lensCurvature, 0.07f, 1e-6f, "wsj curvature is +0.07");
        checkNear(wsj.lensScale, 1.07f, 1e-6f, "wsj scale is 1.07");
        checkNear(wsj.channelSplit, 1.5f, 1e-6f, "wsj rgb split is 1.5px");
        checkNear(wsj.softBlur, 0.8f, 1e-6f, "wsj blur is 0.8px");
        checkNear(wsj.grain, 0.02f, 1e-6f, "wsj grain is 2%");
        checkNear(wsj.vignette, 0.18f, 1e-6f, "wsj vignette is 0.18");
        const ImageFrameStyle crt = archivalLensFrameStyle(ArchivalLensLook::VintageCRT);
        checkNear(crt.lensCurvature, 0.17f, 1e-6f, "crt curvature is +0.17");
        checkNear(crt.lensScale, 1.10f, 1e-6f, "crt scale is 1.10");
        checkNear(crt.channelSplit, 2.0f, 1e-6f, "crt rgb split is 2.0px");
        checkNear(crt.softBlur, 1.5f, 1e-6f, "crt blur is 1.5px");
        checkNear(crt.grain, 0.03f, 1e-6f, "crt grain is 3%");
        checkNear(crt.vignette, 0.35f, 1e-6f, "crt vignette is 0.35");
        const ImageFrameStyle doc = archivalLensFrameStyle(ArchivalLensLook::DocumentarySubtle);
        checkNear(doc.lensCurvature, 0.035f, 1e-6f, "doc curvature is +0.035");
        checkNear(doc.lensScale, 1.04f, 1e-6f, "doc scale is 1.04");
        checkNear(doc.channelSplit, 0.7f, 1e-6f, "doc rgb split is 0.7px");
        checkNear(doc.softBlur, 0.4f, 1e-6f, "doc blur is 0.4px");
        checkNear(doc.grain, 0.01f, 1e-6f, "doc grain is 1%");
        checkNear(doc.vignette, 0.10f, 1e-6f, "doc vignette is 0.10");
        check(archivalLensLookIds().size() == 3 &&
              archivalLensLookIds()[0] == std::string("archival_lens_wsj_reddit") &&
              archivalLensLookIds()[1] == std::string("archival_lens_vintage_crt") &&
              archivalLensLookIds()[2] == std::string("archival_lens_documentary_subtle"),
              "the three look ids are stable and distinct");
    }

    void theLensLowersInPipelineOrder() {
        section("archival lens lowering");
        ImageRequest request;
        request.path = "archive.jpg";
        const ImageFrameStyle wsj = archivalLensFrameStyle(ArchivalLensLook::WsjReddit);
        request.lensCurvature = wsj.lensCurvature;
        request.lensScale = wsj.lensScale;
        request.channelSplit = wsj.channelSplit;
        request.softBlur = wsj.softBlur;
        request.grain = wsj.grain;
        request.vignette = wsj.vignette;
        FakeContentHost host;
        const auto handle = host.createImage(request);
        const auto plan = makeImageLayerPlan(request, handle);
        using Kind = chronon3d::render_plan::LayerPlan::EffectKindPlan;
        int lensAt = -1, splitAt = -1, blurAt = -1;
        for (std::size_t i = 0; i < plan.effects.size(); ++i) {
            if (plan.effects[i].kind == Kind::LensDistortion && lensAt < 0)
                lensAt = static_cast<int>(i);
            if (plan.effects[i].kind == Kind::ChromaticAberration && splitAt < 0)
                splitAt = static_cast<int>(i);
            if (plan.effects[i].kind == Kind::GaussianBlur && blurAt < 0)
                blurAt = static_cast<int>(i);
        }
        check(lensAt >= 0 && splitAt == lensAt + 1 && blurAt == splitAt + 1,
              "lens, rgb split and soft blur lower back-to-back in pipeline order");
        if (lensAt >= 0) {
            const auto& lens = plan.effects[static_cast<std::size_t>(lensAt)];
            checkNear(lens.lens_curvature, 0.07f, 1e-6f,
                      "the lowered lens keeps the authored curvature");
            checkNear(lens.lens_scale, 1.07f, 1e-6f,
                      "the lowered lens keeps the framing scale");
            check(lens.lens_center[0] == 0.5f && lens.lens_center[1] == 0.5f,
                  "the lowered lens stays centered");
        }
        // A flat default frame lowers with no effects at all.
        ImageRequest flat;
        flat.path = "archive.jpg";
        const auto flatPlan = makeImageLayerPlan(flat, host.createImage(flat));
        check(flatPlan.effects.empty(), "a flat frame lowers with no effects");
    }

    void outOfRangeOpticsFailClosed() {
        section("archival lens validation");
        int throws = 0;
        FakeContentHost host;
        const auto loweringThrows = [&](ImageRequest request) {
            request.path = "archive.jpg";
            try {
                (void) makeImageLayerPlan(request, host.createImage(request));
            } catch (const std::invalid_argument&) { ++throws; }
        };
        ImageRequest bad;
        bad.lensCurvature = 2.f;
        loweringThrows(bad);
        bad = ImageRequest{};
        bad.lensScale = 0.5f;
        loweringThrows(bad);
        bad = ImageRequest{};
        bad.softBlur = -1.f;
        loweringThrows(bad);
        bad = ImageRequest{};
        bad.softBlur = 100.f;
        loweringThrows(bad);
        const auto sceneThrows = [&](ImageFrameStyle frame) {
            FakeContentHost sceneHost;
            TemplateScene scene("v", 30.f, sceneHost, 1920.f, 1080.f);
            try {
                (void) scene.image(ImageSpec{.path = "archive.jpg",
                                             .name = "lens",
                                             .frame = frame});
            } catch (const std::invalid_argument&) { ++throws; }
        };
        ImageFrameStyle badFrame;
        badFrame.lensCurvature = -2.f;
        sceneThrows(badFrame);
        badFrame = ImageFrameStyle{};
        badFrame.lensScale = 5.f;
        sceneThrows(badFrame);
        check(throws == 6, "every out-of-range optic throws on both paths");
        // The presets author cleanly through a real scene.
        FakeContentHost sceneHost;
        TemplateScene scene("lens_scene", 30.f, sceneHost, 1920.f, 1080.f);
        LayerHandle& image = scene.image(
            ImageSpec{.path = "archive.jpg",
                      .name = "lens",
                      .frame = archivalLensFrameStyle(ArchivalLensLook::DocumentarySubtle)});
        image.position(960.f, 540.f);
        check(scene.validate().empty(), "the lensed scene validates");
        checkNear(sceneHost.lastImageRequest().lensCurvature, 0.035f, 1e-6f,
                  "the scene carries the preset curvature to Chronon");
    }

} // namespace

    void theReelChoreographyMirrorsTheRenderer() {
        section("archival reel choreography");
        ArchivalLensReel reel;
        check(reelSegmentForFrame(reel, -1) == 0, "negative frames clamp to segment 0");
        check(reelSegmentForFrame(reel, 0) == 0 && reelSegmentForFrame(reel, 89) == 0,
              "frames 0-89 are the article segment");
        check(reelSegmentForFrame(reel, 90) == 1 && reelSegmentForFrame(reel, 179) == 1,
              "frames 90-179 are the CRT segment");
        check(reelSegmentForFrame(reel, 180) == 2 && reelSegmentForFrame(reel, 269) == 2,
              "frames 180-269 are the documentary segment");
        check(reelSegmentForFrame(reel, 500) == 2, "overflow frames clamp to segment 2");
        // Article: zoom 1.06 -> 1.11, pan 0 -> 22px.
        checkNear(reelZoom(reel, 0), 1.06f, 1e-6f, "article zoom starts at 1.06");
        checkNear(reelZoom(reel, 89), 1.11f, 1e-6f, "article zoom ends at 1.11");
        checkNear(reelPanX(reel, 0), 0.f, 1e-6f, "article pan starts at 0");
        checkNear(reelPanX(reel, 89), 22.f, 1e-6f, "article pan ends at 22px");
        check(reelZoom(reel, 0) < reelZoom(reel, 45) && reelZoom(reel, 45) < reelZoom(reel, 89),
              "article zoom grows monotonically");
        // CRT: zoom locked, slow sine breath.
        checkNear(reelZoom(reel, 90), 1.f, 1e-6f, "crt zoom is locked at 1.0");
        checkNear(reelPanX(reel, 90), 0.f, 1e-6f, "crt drift starts at 0");
        check(std::abs(reelPanX(reel, 112)) <= 3.0001f && std::abs(reelPanY(reel, 112)) <= 2.0001f,
              "crt drift stays within +-3/+-2px");
        // Documentary: gentle push 1.00 -> 1.05, centered.
        checkNear(reelZoom(reel, 180), 1.0f, 1e-6f, "documentary push starts at 1.0");
        checkNear(reelZoom(reel, 269), 1.05f, 1e-6f, "documentary push ends at 1.05");
        checkNear(reelPanX(reel, 200), 0.f, 1e-6f, "documentary holds lateral center");
        checkNear(reelPanY(reel, 200), 0.f, 1e-6f, "documentary holds vertical center");
    }

    void theCenterpieceShotIsCalmAndValidated() {
        section("centerpiece stretched shot");
        const ImageFrameStyle style = centerpieceStretchedStyle();
        checkNear(style.lensCurvature, 0.20f, 1e-6f, "centerpiece curvature is +0.20");
        checkNear(style.lensScale, 1.14f, 1e-6f, "centerpiece scale is 1.14");
        checkNear(style.channelSplit, 2.f, 1e-6f, "centerpiece rgb split is 2px");
        CenterpieceStretched shot;
        validateCenterpiece(shot);
        checkNear(shot.cardWidth, 720.f, 1e-6f, "the card is medium, never fullscreen");
        checkNear(shot.cardHeight, 900.f, 1e-6f, "the card keeps portrait framing");
        checkNear(centerpiecePush(shot, 0), 1.0f, 1e-6f, "push starts at 1.0");
        checkNear(centerpiecePush(shot, 149), 1.02f, 1e-6f, "push ends at 1.02");
        check(centerpiecePush(shot, 0) < centerpiecePush(shot, 75) &&
              centerpiecePush(shot, 75) < centerpiecePush(shot, 149),
              "push grows monotonically and stays subtle");
        int throws = 0;
        CenterpieceStretched bad = shot;
        bad.cardWidth = 3000.f;
        try { validateCenterpiece(bad); } catch (const std::invalid_argument&) { ++throws; }
        bad = shot;
        bad.pushTo = 0.9f;
        try { validateCenterpiece(bad); } catch (const std::invalid_argument&) { ++throws; }
        bad = shot;
        bad.edgeStretch = 2.f;
        try { validateCenterpiece(bad); } catch (const std::invalid_argument&) { ++throws; }
        check(throws == 3, "oversize card, inverted push and wild stretch all throw");
        // The style lowers through the same native lens path.
        ImageRequest request;
        request.path = "ride.jpg";
        request.lensCurvature = style.lensCurvature;
        request.lensScale = style.lensScale;
        request.channelSplit = style.channelSplit;
        request.softBlur = style.softBlur;
        FakeContentHost host;
        const auto plan = makeImageLayerPlan(request, host.createImage(request));
        using Kind = chronon3d::render_plan::LayerPlan::EffectKindPlan;
        bool lens = false;
        for (const auto& effect : plan.effects)
            if (effect.kind == Kind::LensDistortion) lens = true;
        check(lens, "the centerpiece style lowers to a native lens");
    }

int main() {
    theThreePresetsCarryTheTableValues();
    theLensLowersInPipelineOrder();
    outOfRangeOpticsFailClosed();
    theReelChoreographyMirrorsTheRenderer();
    theCenterpieceShotIsCalmAndValidated();
    return chrononmotion_test::report();
}
