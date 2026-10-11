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
        check(looks.size() == 8, "the pack ships eight rapid light looks");
        const char* known[] = {"lightleak_flash_sweep", "lightleak_corner_burn", "lightleak_whiteout",
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

            // Every rapid look is a light wash peaking at its authored peak.
            // Whiteout layers a full-opacity white wash on top of the warm one.
            const float expectedPeak = (look == TransitionLook::LightLeakWhiteout)
                    ? 1.f : specFor(look).leakPeakOpacity;
            check(maxWindowOpacity > expectedPeak - 0.05f,
                  "the transition washes the cut inside its window");
        }
    }

    void determinismHoldsFrameByFrame() {
        section("transition evaluation is a pure function of (scene, frame)");
        FakeContentHost host;
        TemplateScene scene("deterministic", 30.f, host, 1920.f, 1080.f);
        TransitionSpec spec = specFor(TransitionLook::LightLeakDoublePass);
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
        check(cut.plates.size() == 2, "double pass authors two crossing beams");
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

        TransitionSpec shortSpec = specFor(TransitionLook::LightLeakFlashSweep);
        shortSpec.duration = 1;
        bool threw = false;
        try {
            (void) addTransition(scene, shortSpec);
        } catch (const std::invalid_argument&) {
            threw = true;
        }
        check(threw, "a one-frame duration is rejected");

        TransitionSpec sliceSpec = specFor(TransitionLook::LightLeakFlashSweep);
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

        TransitionSpec leakSpec = specFor(TransitionLook::LightLeakFlashSweep);
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
        (void) addTransition(plain, specFor(TransitionLook::LightLeakFlashSweep));
        check(!plain.temporalMotionBlur().has_value(),
              "a transition without motion blur leaves the scene declaration unset");

        TemplateScene blurred("blurred", 30.f, host, 1920.f, 1080.f);
        TransitionSpec spec = specFor(TransitionLook::LightLeakFlashSweep);
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
    determinismHoldsFrameByFrame();
    validationRejectsBadSpecs();
    rapidLooksAreDeterministicAtArbitraryFrames();
    rapidTimingAndSelectorWeightsAreExplicit();
    motionBlurIsOptInAndDeclared();
    return chrononmotion_test::report();
}
