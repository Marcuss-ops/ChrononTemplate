#include "chronontemplate/backgrounds/BackgroundPack.hpp"

#include "fake_content_host.hpp"
#include "motion_check.hpp"

#include <cmath>
#include <stdexcept>
#include <string>

using namespace chronontemplate;
using chronontemplate_test::FakeContentHost;
using chronontemplate_test::findLayer;
using chrononmotion_test::check;
using chrononmotion_test::section;

namespace {

    void everyLookHasAStableId() {
        section("background looks have stable ids");
        const std::vector<BackgroundLook> looks = backgroundLooks();
        check(looks.size() == 5, "the pack exposes five looks");
        for (const BackgroundLook look : looks) {
            const std::string id = backgroundLookId(look);
            check(id.rfind("bg_", 0) == 0, "every look id is namespaced with bg_");
        }
    }

    void everyLookBuildsAFullFrameBackground() {
        section("background looks build and submit");
        for (const BackgroundLook look : backgroundLooks()) {
            FakeContentHost host;
            TemplateScene scene(std::string("bg_") + backgroundLookId(look), 30.f, host,
                                1920.f, 1080.f);
            const BackgroundComposition built = addBackground(scene, BackgroundSpec{.look = look});

            check(built.ground != nullptr, "every look authors a ground layer");
            check(built.endFrame == 150, "every look ends at its authored in-frame plus duration");

            const FrameSubmission start = scene.submit(0);
            const FrameSubmission middle = scene.submit(75);
            const FrameSubmission end = scene.submit(150);
            const BoundLayer* ground = findLayer(middle, built.ground->id());
            check(ground && ground->draws(), "the ground draws at the middle of the clip");
            if (ground) {
                check(ground->content.isImage(), "the ground is a rasterized shape layer");
                check(std::isfinite(ground->transform.opacity) &&
                              ground->transform.opacity >= 0.f && ground->transform.opacity <= 1.f,
                      "the ground opacity stays finite and in range");
            }
            for (LayerHandle* accent : built.accents) {
                const BoundLayer* a = findLayer(start, accent->id());
                const BoundLayer* b = findLayer(middle, accent->id());
                const BoundLayer* c = findLayer(end, accent->id());
                check(a && b && c, "every accent layer submits across the clip");
                if (b) {
                    check(std::isfinite(b->transform.opacity),
                          "every accent opacity stays finite");
                }
            }
            check(scene.validate().empty(), "every background scene validates");
        }
    }

    void thePackRejectsInvalidSpecs() {
        section("background pack validates its spec");
        FakeContentHost host;
        TemplateScene scene("bg_bad", 30.f, host, 1920.f, 1080.f);

        bool threwBars = false;
        try {
            (void) addBackground(scene, BackgroundSpec{.look = BackgroundLook::LetterboxBars,
                                                       .barFraction = 0.75f});
        } catch (const std::invalid_argument&) {
            threwBars = true;
        }
        check(threwBars, "a bar fraction outside [0, 0.5) is rejected");

        bool threwDuration = false;
        try {
            (void) addBackground(scene, BackgroundSpec{.duration = 0});
        } catch (const std::invalid_argument&) {
            threwDuration = true;
        }
        check(threwDuration, "a non-positive duration is rejected");
    }

}// namespace

int main() {
    everyLookHasAStableId();
    everyLookBuildsAFullFrameBackground();
    thePackRejectsInvalidSpecs();
    return chrononmotion_test::report();
}
