// Archival timeline reveal: beat math, authored layers, visibility windows.
#include "chronontemplate/documentary_effects/ArchivalTimelinePack.hpp"

#include "fake_content_host.hpp"
#include "motion_check.hpp"

#include <stdexcept>

using namespace chronontemplate;
using namespace chronontemplate::docfx;
using chronontemplate_test::FakeContentHost;
using chronontemplate_test::findLayer;
using chrononmotion_test::check;
using chrononmotion_test::checkNear;
using chrononmotion_test::section;

namespace {

    void axisDrawsLeftToRight() {
        section("axis reveal");
        ArchivalTimelineSpec spec;
        checkNear(axisReveal(spec, 0), 0.f, 1e-6f, "axis hidden at frame 0");
        checkNear(axisReveal(spec, 15), 0.f, 1e-6f, "axis holds before onset");
        checkNear(axisReveal(spec, 39), 1.f, 1e-6f, "axis complete at frame 39");
        checkNear(axisReveal(spec, 180), 1.f, 1e-6f, "axis stays drawn");
        const float mid = axisReveal(spec, 27);
        check(mid > 0.f && mid < 1.f, "axis is partial mid-draw");
    }

    ArchivalTimelineSpec spec_default() { return ArchivalTimelineSpec{}; }

    void layersCoverTheBeats() {
        section("layer windows");
        FakeContentHost host;
        TemplateScene scene("archival", 30.f, host, 1920.f, 1080.f);
        const auto layers = addArchivalTimelineReveal(scene, spec_default());
        check(layers.paper && layers.line && layers.year && layers.headline,
              "paper, axis, year and headline are authored");
        check(layers.background, "dust background is authored");
        const FrameSubmission early = scene.submit(10);
        check(!findLayer(early, layers.paper) ||
                  !findLayer(early, layers.paper)->transform.visible,
              "paper hidden before its rise");
        const FrameSubmission titled = scene.submit(100);
        for (MotionLayerId id : {layers.paper, layers.line, layers.year,
                                 layers.headlineShadow, layers.headline}) {
            const BoundLayer* bound = findLayer(titled, id);
            check(bound && bound->transform.visible, "every element draws at frame 100");
        }
        check(scene.validate().empty(), "the archival scene validates");
        check(std::string(archivalTimelineId()) == "docfx_archival_timeline_v1",
              "pack id is stable");
    }

    void badSpecsThrow() {
        section("validation");
        int throws = 0;
        using Mutate = void (*)(ArchivalTimelineSpec&);
        const Mutate muts[] = {
                 [](ArchivalTimelineSpec& s) { s.year.clear(); },
                 [](ArchivalTimelineSpec& s) { s.headline.clear(); },
                 [](ArchivalTimelineSpec& s) { s.paperAsset.clear(); },
                 [](ArchivalTimelineSpec& s) { s.paperWidth = 50.f; },
                 [](ArchivalTimelineSpec& s) { s.lineY = 50.f; },
                 [](ArchivalTimelineSpec& s) { s.sceneFrames = 60; },
        };
        for (Mutate mutate : muts) {
            FakeContentHost host;
            TemplateScene scene("v", 30.f, host, 1920.f, 1080.f);
            ArchivalTimelineSpec bad;
            mutate(bad);
            try {
                (void) addArchivalTimelineReveal(scene, bad);
            } catch (const std::invalid_argument&) {
                ++throws;
            }
        }
        check(throws == 6, "every malformed spec throws");
    }

} // namespace

int main() {
    axisDrawsLeftToRight();
    layersCoverTheBeats();
    badSpecsThrow();
    return chrononmotion_test::report();
}
