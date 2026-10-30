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

    void v2OpeningPlate() {
        section("v2 opening plate");
        FakeContentHost host;
        TemplateScene scene("v2_opening", kFps, host);
        FastIntroV2Spec spec;
        spec.recipe = FastIntroRecipe::OpeningPlate;
        spec.topics = {"CONTEXT", "EVIDENCE", "WHAT CHANGED"};
        LayerHandle& root = addFastIntroV2(scene, spec);
        (void)root;
        check(scene.validate().empty(), "v2 opening validates without errors");
        check(scene.motion().layerCount() >= 8, "opening has ground, aura, texts, rail, marker and pills");
        check(fastIntroV2Choices().size() == 4, "four v2 recipes registered");
    }

    void v2PunchStatCapped() {
        section("v2 punch stat capped scales");
        FakeContentHost host;
        TemplateScene scene("v2_punch", kFps, host);
        FastIntroV2Spec spec;
        spec.recipe = FastIntroRecipe::PunchStat;
        LayerHandle& root = addFastIntroV2(scene, spec);
        (void)root;
        check(scene.validate().empty(), "v2 punch validates without errors");
        check(scene.motion().layerCount() >= 9, "punch has ground, glow, 5 rings, era, stat and collage");
    }

    void v2WhipAndChapter() {
        section("v2 whip + chapter parametric");
        FakeContentHost host;
        {
            TemplateScene scene("v2_whip", kFps, host);
            FastIntroV2Spec spec;
            spec.recipe = FastIntroRecipe::WhipMatch;
            spec.durationFrames = 180;
            spec.plates = {"a.png", "b.png", "c.png", "d.png", "e.png", "f.png"};
            LayerHandle& root = addFastIntroV2(scene, spec);
            (void)root;
            check(scene.validate().empty(), "v2 whip validates without errors");
        }
        {
            TemplateScene scene("v2_chapter", kFps, host);
            FastIntroV2Spec spec;
            spec.recipe = FastIntroRecipe::ChapterCard;
            spec.chapterLabel = "CHAPTER 1";
            spec.title = "THE HITMAN HIDDEN IN A FAMILY PHOTO";
            LayerHandle& root = addFastIntroV2(scene, spec);
            (void)root;
            check(scene.validate().empty(), "v2 chapter validates without errors");
        }
        {
            TemplateScene scene("bad_whip", kFps, host);
            FastIntroV2Spec spec;
            spec.recipe = FastIntroRecipe::WhipMatch;
            spec.plates = {"only.png"};
            bool threw = false;
            try { (void)addFastIntroV2(scene, spec); } catch (const std::invalid_argument&) { threw = true; }
            check(threw, "whip with <4 plates throws invalid_argument");
        }
        {
            TemplateScene scene("bad_topics", kFps, host);
            FastIntroV2Spec spec;
            spec.recipe = FastIntroRecipe::OpeningPlate;
            spec.topics = {"a", "b", "c", "d", "e"};
            bool threw = false;
            try { (void)addFastIntroV2(scene, spec); } catch (const std::invalid_argument&) { threw = true; }
            check(threw, "opening with >4 topics throws invalid_argument");
        }
    }

} // namespace

int main() {
    standardFastIntroComposition();
    retroStatCollageComposition();
    validationRejections();
    v2OpeningPlate();
    v2PunchStatCapped();
    v2WhipAndChapter();
    return 0;
}
