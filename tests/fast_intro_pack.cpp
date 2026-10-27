#include "chronontemplate/fast_intro/FastIntroPack.hpp"

#include "fake_content_host.hpp"
#include "motion_check.hpp"

#include <stdexcept>
#include <string>

using namespace chronontemplate;
using namespace chronontemplate::fast_intro;
using chronontemplate_test::FakeContentHost;
using chrononmotion_test::check;
using chrononmotion_test::section;

namespace {

    constexpr float kFps = 30.f;

    void standardFastIntroComposition() {
        section("standard fast intro composition");
        FakeContentHost host;
        TemplateScene scene("fast_intro_scene", kFps, host);

        FastIntroSpec spec;
        LayerHandle& root = addFastIntro(scene, spec);
        (void)root;

        check(scene.validate().empty(), "standard fast intro validates without errors");
        check(scene.motion().layerCount() >= 7, "scene contains root, ground, rail, marker, kicker, title, subtitle and chips");
    }

    void retroStatCollageComposition() {
        section("retro stat collage composition");
        FakeContentHost host;
        TemplateScene scene("retro_stat_scene", kFps, host);

        RetroStatCollageSpec spec;
        spec.eraTitle = "1990s";
        spec.statistic = "37.7 M";
        spec.closingTitle = "BONUS SCENE";
        spec.collagePath = "ChrononTemplate/assets/images/retro_collage.png";
        spec.font = "ChrononTemplate/assets/fonts/Inter-Bold.ttf";

        LayerHandle& root = addRetroStatCollage(scene, spec);
        (void)root;

        check(scene.validate().empty(), "retro stat collage hierarchy validates without errors");
        check(scene.motion().layerCount() >= 7, "scene contains group, warm radial background, era, statistic, collage and closing title");

        // Verify bounds & validation
        check(scene.name() == "retro_stat_scene", "scene name is preserved");
        check(scene.fps() == 30.f, "scene fps is 30");

        // Test shorthand API
        TemplateScene scene2("retro_stat_shorthand", kFps, host);
        LayerHandle& root2 = addRetroStatIntro(scene2, spec.collagePath, spec.font);
        (void)root2;
        check(scene2.validate().empty(), "addRetroStatIntro shorthand produces a valid scene");
    }

    void validationRejections() {
        section("retro stat collage validation gates");
        FakeContentHost host;

        {
            TemplateScene scene("bad_spec", kFps, host);
            RetroStatCollageSpec spec;
            spec.eraTitle = "";
            bool threw = false;
            try {
                (void)addRetroStatCollage(scene, spec);
            } catch (const std::invalid_argument&) {
                threw = true;
            }
            check(threw, "empty eraTitle throws invalid_argument");
        }

        {
            TemplateScene scene("bad_duration", kFps, host);
            RetroStatCollageSpec spec;
            spec.durationFrames = 10;
            bool threw = false;
            try {
                (void)addRetroStatCollage(scene, spec);
            } catch (const std::invalid_argument&) {
                threw = true;
            }
            check(threw, "short duration throws invalid_argument");
        }
    }

} // namespace

int main() {
    standardFastIntroComposition();
    retroStatCollageComposition();
    validationRejections();
    return 0;
}
