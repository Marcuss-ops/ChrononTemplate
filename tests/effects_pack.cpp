// Effects pack: all twenty procedural overlays author layers, show inside
// their frame window, reject bad specs, and are deterministic per seed.
#include "chronontemplate/effects/EffectsPack.hpp"

#include "fake_content_host.hpp"
#include "motion_check.hpp"

#include <stdexcept>
#include <string>

using namespace chronontemplate;
using namespace chronontemplate::effects;
using chronontemplate_test::FakeContentHost;
using chronontemplate_test::findLayer;
using chrononmotion_test::check;
using chrononmotion_test::section;

namespace {

    constexpr std::size_t kKinds = 20;

    void check(bool condition, const std::string& what) {
        chrononmotion_test::check(condition, what.c_str());
    }

    EffectKind kindAt(std::size_t i) {
        return static_cast<EffectKind>(i);
    }

    void everyKindAuthorsVisibleLayers() {
        section("every effect authors visible layers");
        check(effectCount() == kKinds, "the pack declares twenty effects");
        for (std::size_t i = 0; i < kKinds; ++i) {
            const EffectKind kind = kindAt(i);
            FakeContentHost host;
            TemplateScene scene(effectName(kind), 30.f, host, 1920.f, 1080.f);
            EffectSpec spec;
            spec.startFrame = 10;
            spec.endFrame = 70;
            const auto layers = addEffect(scene, kind, spec);
            check(!layers.empty(), std::string(effectName(kind)) + " authors at least one layer");
            const FrameSubmission inside = scene.submit(30);
            bool anyVisible = false;
            for (const MotionLayerId id : layers) {
                const BoundLayer* bound = findLayer(inside, id);
                if (bound && bound->transform.visible) anyVisible = true;
            }
            check(anyVisible, std::string(effectName(kind)) + " is visible inside its window");
            const FrameSubmission after = scene.submit(90);
            bool anyAfter = false;
            for (const MotionLayerId id : layers) {
                const BoundLayer* bound = findLayer(after, id);
                if (bound && bound->transform.visible) anyAfter = true;
            }
            check(!anyAfter, std::string(effectName(kind)) + " is hidden after its window");
            check(scene.validate().empty(), std::string(effectName(kind)) + " validates");
        }
    }

    void namesAreUnique() {
        section("effect names");
        for (std::size_t i = 0; i < kKinds; ++i)
            for (std::size_t j = i + 1; j < kKinds; ++j)
                check(std::string(effectName(kindAt(i))) != effectName(kindAt(j)),
                      "effect names are unique");
        check(std::string(effectsId()) == "effects_overlay_v1", "effects id is stable");
    }

    void badSpecsThrow() {
        section("validation");
        auto throwsFor = [](EffectSpec spec) {
            FakeContentHost host;
            TemplateScene scene("v", 30.f, host, 1920.f, 1080.f);
            try {
                (void) addEffect(scene, EffectKind::FilmGrain, spec);
            } catch (const std::invalid_argument&) {
                return true;
            }
            return false;
        };
        EffectSpec tooStrong;
        tooStrong.intensity = 1.5f;
        check(throwsFor(tooStrong), "intensity above 1 throws");
        EffectSpec badOpacity;
        badOpacity.opacity = -0.1f;
        check(throwsFor(badOpacity), "negative opacity throws");
        EffectSpec emptyWindow;
        emptyWindow.startFrame = 20;
        emptyWindow.endFrame = 20;
        check(throwsFor(emptyWindow), "an empty frame window throws");
        EffectSpec badColor;
        badColor.color = "orange";
        check(throwsFor(badColor), "a non-hex colour throws");
    }

    void sameSeedIsDeterministic() {
        section("determinism");
        auto scratchCount = [](std::uint32_t seed) {
            FakeContentHost host;
            TemplateScene scene("det", 30.f, host, 1920.f, 1080.f);
            EffectSpec spec;
            spec.seed = seed;
            return addEffect(scene, EffectKind::FilmScratches, spec).size();
        };
        check(scratchCount(7) == scratchCount(7), "the same seed gives the same layout");
    }

} // namespace

int main() {
    everyKindAuthorsVisibleLayers();
    namesAreUnique();
    badSpecsThrow();
    sameSeedIsDeterministic();
    return chrononmotion_test::report();
}
