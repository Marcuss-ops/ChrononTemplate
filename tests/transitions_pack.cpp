#include "chronontemplate/transitions/TransitionPack.hpp"

#include "fake_content_host.hpp"
#include "motion_check.hpp"

#include <algorithm>
#include <cmath>
#include <stdexcept>
#include <string>
#include <vector>

using namespace chronontemplate;
using chronontemplate_test::FakeContentHost;
using chronontemplate_test::findLayer;
using chrononmotion_test::check;
using chrononmotion_test::checkNear;
using chrononmotion_test::section;

namespace {

    TransitionSpec specFor(TransitionLook look) {
        TransitionSpec spec;
        spec.look = look;
        spec.inFrame = 10;
        spec.duration = recommendedTransitionDuration(look);
        spec.name = "cut_" + std::string(transitionId(look));
        return spec;
    }

    void everyLookHasAStableCatalogId() {
        section("transitions expose stable catalog ids");
        const std::vector<TransitionLook> looks = transitionLooks();
        check(looks.size() == 16, "the pack ships eight legacy and eight rapid looks");
        const char* known[] = {"transition_wipe", "transition_push_through", "transition_dip_to_black",
                               "transition_dip_to_color", "transition_blinds", "transition_iris_circle",
                               "transition_glitch_slices", "transition_light_leak",
                               "lightleak_flash_sweep", "lightleak_corner_burn", "lightleak_whiteout",
                               "lightleak_diagonal_cut", "lightleak_double_pass", "lightleak_film_burn",
                               "lightleak_center_burst", "lightleak_horizontal_whip"};

        for (std::size_t i = 0; i < looks.size(); ++i) {
            check(std::string(transitionId(looks[i])) == known[i],
                  "each look keeps its stable snake-case id");
        }
    }

    void everyLookAssemblesSubmitsAndCoversTheMidpoint() {
        section("every transition assembles, covers the midpoint and clears");
        const std::vector<TransitionLook> looks = transitionLooks();
        for (const TransitionLook look : looks) {
            FakeContentHost host;
            TemplateScene scene("cut_scene", 30.f, host, 1920.f, 1080.f);
            const TransitionComposition cut = addTransition(scene, specFor(look));

            check(!cut.plates.empty(), "the cut authors at least one plate");
            check(cut.coverFrame >= cut.inFrame && cut.coverFrame <= cut.endFrame,
                  "the declared peak frame lies inside the cut window");
            check(cut.endFrame == cut.inFrame + specFor(look).duration,
                  "the cut ends where the spec says");
            check(cut.endFrame - cut.inFrame == specFor(look).duration,
                  "the cut duration matches the selected look's recommended frame count");
            check(scene.validate().empty(), "the assembled scene validates");

            // Lifetime is a whole-frame gate: one frame before `inFrame` and one
            // after `outFrame` the bridge still binds the layer but reports it
            // invisible (verified against the evaluated scene).
            const FrameSubmission before = scene.submit(cut.inFrame - 1);
            const FrameSubmission cover = scene.submit(cut.coverFrame);
            const FrameSubmission after = scene.submit(cut.endFrame + 1);

            int hiddenBefore = 0;
            int hiddenAfter = 0;
            float maxWindowOpacity = 0.f;
            for (const LayerHandle* plate : cut.plates) {
                const BoundLayer* b = findLayer(before, plate->id());
                const BoundLayer* c = findLayer(cover, plate->id());
                check(c != nullptr, "every plate is bound on the cover frame");
                if (b && !b->transform.visible) ++hiddenBefore;
                if (findLayer(after, plate->id()) != nullptr &&
                    !findLayer(after, plate->id())->transform.visible) {
                    ++hiddenAfter;
                }
            }
            check(hiddenBefore == static_cast<int>(cut.plates.size()),
                  "every plate is gated off before the transition");
            check(hiddenAfter == static_cast<int>(cut.plates.size()),
                  "every plate is gated off after the transition");

            // Sample the authored peak across every frame; the expected peak
            // differs between opaque whiteout and translucent light accents.
            for (int frame = cut.inFrame; frame <= cut.endFrame; ++frame) {
                const FrameSubmission window = scene.submit(frame);
                for (const BoundLayer& layer : window.layers) {
                    maxWindowOpacity = std::max(maxWindowOpacity, layer.transform.opacity);
                }
            }

            // A covering look reaches full opacity inside the window; the leak
            // wash peaks at its authored peak instead. (The sweep plates carry no
            // opacity keys — they cover geometrically — so their static opacity
            // of 1 is the covering value.)
            const float expectedPeak = (look == TransitionLook::LightLeak ||
                                        look == TransitionLook::LightLeakFlashSweep ||
                                        look == TransitionLook::LightLeakCornerBurn ||
                                        look == TransitionLook::LightLeakDiagonalCut ||
                                        look == TransitionLook::LightLeakDoublePass ||
                                        look == TransitionLook::LightLeakFilmBurn ||
                                        look == TransitionLook::LightLeakCenterBurst ||
                                        look == TransitionLook::LightLeakHorizontalWhip)
                    ? specFor(look).leakPeakOpacity : 1.f;
            check(maxWindowOpacity > expectedPeak - 0.05f,
                  "the transition covers or washes the cut inside its window");
        }
    }

    void wipesAreFullyCoveringAtTheMidpoint() {
        section("sweep cuts are centered and opaque on the cover frame");
        for (const TransitionLook look : {TransitionLook::Wipe, TransitionLook::PushThrough}) {
            FakeContentHost host;
            TemplateScene scene("sweep", 30.f, host, 1920.f, 1080.f);
            const TransitionComposition cut = addTransition(scene, specFor(look));
            const FrameSubmission cover = scene.submit(22);
            check(cover.layers.size() == cut.plates.size(),
                  "each sweep plate submits on the cover frame");
            // The bar is twice the frame span and the sweep is linear, so at the
            // cover frame the bar's centre is the canvas centre. Anchor-aware:
            // the matrix translation is position - anchor, so the centred bar
            // reads (-span/2, -barH/2) = (-960, 0), and the canvas stays covered
            // while that translation stays in [-span, 0]. The plate carries no
            // opacity keys, so its static opacity of 1 is the cover.
            const BoundLayer* b = findLayer(cover, cut.plates[0]->id());
            check(b != nullptr, "the leading plate is bound on the cover frame");
            if (b) {
                check(b->transform.visible, "the leading plate is visible on the cover frame");
                check(std::fabs(b->transform.opacity - 1.f) < 1e-6f,
                      "the leading plate covers at full opacity");
                check(std::fabs(b->transform.world.elements[12] + 960.f) < 1e-3f,
                      "the bar is horizontally centred at the cover frame");
                check(std::fabs(b->transform.world.elements[13]) < 1e-3f,
                      "the bar is vertically centred at the cover frame");
            }
            // The canvas stays covered on the frames either side of the midpoint.
            for (const int frame : {20, 24}) {
                const FrameSubmission near = scene.submit(frame);
                const BoundLayer* side = findLayer(near, cut.plates[0]->id());
                check(side != nullptr, "the leading plate is bound across the cover window");
                if (side) {
                    const float tx = side->transform.world.elements[12];
                    check(tx <= 1e-3f && tx >= -1920.f - 1e-3f,
                          "the bar still spans the canvas beside the midpoint");
                }
            }
            check(scene.validate().empty(), "the sweep scene validates");
        }
    }

    void determinismHoldsFrameByFrame() {
        section("transition evaluation is a pure function of (scene, frame)");
        FakeContentHost host;
        TemplateScene scene("deterministic", 30.f, host, 1920.f, 1080.f);
        TransitionSpec spec = specFor(TransitionLook::Blinds);
        spec.slices = 5;
        const TransitionComposition cut = addTransition(scene, spec);

        for (const int frame : {12, 18, 22, 26, 33}) {
            const FrameSubmission first = scene.submit(frame);
            const FrameSubmission second = scene.submit(frame);
            check(first.layers.size() == second.layers.size(),
                  "repeated evaluation keeps the layer count");
            for (std::size_t i = 0; i < first.layers.size(); ++i) {
                const auto& a = first.layers[i].transform.world.elements;
                const auto& b = second.layers[i].transform.world.elements;
                bool identical = true;
                for (std::size_t k = 0; k < a.size(); ++k) {
                    if (a[k] != b[k]) identical = false;
                }
                check(identical, "the same frame always produces the same matrices");
            }
        }
        check(cut.plates.size() == 5, "blinds author one plate per slice");
    }

    void rapidLooksAreDeterministicAtArbitraryFrames() {
        section("rapid light looks are deterministic under random-access evaluation");
        for (const TransitionLook look : transitionLooks()) {
            if (!isRapidTransition(look)) continue;
            FakeContentHost host;
            TemplateScene scene("rapid_determinism", 30.f, host, 640.f, 360.f);
            const TransitionComposition cut = addTransition(scene, specFor(look));
            for (const int frame : {cut.inFrame, cut.coverFrame, cut.endFrame}) {
                const FrameSubmission first = scene.submit(frame);
                const FrameSubmission second = scene.submit(frame);
                check(first.layers.size() == second.layers.size(),
                      "repeated rapid-look sampling preserves the submitted layer count");
                for (std::size_t i = 0; i < first.layers.size(); ++i) {
                    const auto& a = first.layers[i].transform;
                    const auto& b = second.layers[i].transform;
                    bool identical = a.opacity == b.opacity && a.visible == b.visible;
                    for (std::size_t k = 0; k < a.world.elements.size(); ++k)
                        identical = identical && a.world.elements[k] == b.world.elements[k];
                    check(identical, "arbitrary-frame transform and opacity samples are bit-identical");
                }
            }
        }
    }

    void validationRejectsBadSpecs() {
        section("invalid specs are rejected fail-closed");
        FakeContentHost host;
        TemplateScene scene("gate", 30.f, host, 1920.f, 1080.f);

        TransitionSpec shortSpec = specFor(TransitionLook::Wipe);
        shortSpec.duration = 1;
        bool threw = false;
        try {
            (void) addTransition(scene, shortSpec);
        } catch (const std::invalid_argument&) {
            threw = true;
        }
        check(threw, "a one-frame duration is rejected");

        TransitionSpec sliceSpec = specFor(TransitionLook::Blinds);
        sliceSpec.slices = 0;
        threw = false;
        try {
            (void) addTransition(scene, sliceSpec);
        } catch (const std::invalid_argument&) {
            threw = true;
        }
        check(threw, "a zero slice count is rejected");

        TransitionSpec rapidSpec = specFor(TransitionLook::LightLeakWhiteout);
        rapidSpec.duration = transitionDurationBounds(rapidSpec.look).minimumFrames - 1;
        threw = false;
        try {
            (void) addTransition(scene, rapidSpec);
        } catch (const std::invalid_argument&) {
            threw = true;
        }
        check(threw, "a named rapid look rejects durations below its declared window");

        TransitionSpec leakSpec = specFor(TransitionLook::LightLeak);
        leakSpec.leakPeakOpacity = 0.f;
        threw = false;
        try {
            (void) addTransition(scene, leakSpec);
        } catch (const std::invalid_argument&) {
            threw = true;
        }
        check(threw, "a zero leak peak opacity is rejected");
    }

    void rapidTimingAndSelectorWeightsAreExplicit() {
        section("rapid looks publish timing classes and a normalized suggested distribution");
        int weightTotal = 0;
        for (const TransitionWeight& weight : recommendedTransitionWeights()) {
            check(isRapidTransition(weight.look), "suggested selector weights name supported rapid looks");
            weightTotal += weight.percent;
        }
        check(weightTotal == 100, "suggested selector percentages sum to 100");
        check(transitionTimingClass(TransitionLook::LightLeakWhiteout) == TransitionTimingClass::Micro,
              "recommended 6-frame whiteout is classified as MICRO");
        check(transitionTimingClass(TransitionLook::LightLeakFlashSweep) == TransitionTimingClass::Normal,
              "recommended 8-frame sweep is classified as NORMAL");
        check(transitionTimingClass(TransitionLook::LightLeakDoublePass) == TransitionTimingClass::Hero,
              "recommended 12-frame double pass is classified as HERO");
        for (const TransitionLook look : transitionLooks()) {
            const auto bounds = transitionDurationBounds(look);
            if (!isRapidTransition(look)) continue;
            const int duration = recommendedTransitionDuration(look);
            check(duration >= bounds.minimumFrames && duration <= bounds.maximumFrames,
                  "each rapid look's recommendation is inside its range");
        }
    }

    void motionBlurIsOptInAndDeclared() {
        section("motion blur is an opt-in scene declaration");
        FakeContentHost host;
        TemplateScene plain("plain", 30.f, host, 1920.f, 1080.f);
        (void) addTransition(plain, specFor(TransitionLook::Wipe));
        check(!plain.temporalMotionBlur().has_value(),
              "a transition without motion blur leaves the scene declaration unset");

        TemplateScene blurred("blurred", 30.f, host, 1920.f, 1080.f);
        TransitionSpec spec = specFor(TransitionLook::Wipe);
        spec.enableMotionBlur = true;
        (void) addTransition(blurred, spec);
        check(blurred.temporalMotionBlur().has_value(), "the opt-in declares the setting");
        check(std::fabs(blurred.temporalMotionBlur()->shutterAngle - 180.f) < 1e-5f,
              "the shutter angle is the declared one");
        check(blurred.temporalMotionBlur()->samples == 8, "the sample count is the declared one");
    }

}// namespace

int main() {

    everyLookHasAStableCatalogId();
    everyLookAssemblesSubmitsAndCoversTheMidpoint();
    wipesAreFullyCoveringAtTheMidpoint();
    determinismHoldsFrameByFrame();
    validationRejectsBadSpecs();
    rapidLooksAreDeterministicAtArbitraryFrames();
    rapidTimingAndSelectorWeightsAreExplicit();
    motionBlurIsOptInAndDeclared();
    return chrononmotion_test::report();
}
