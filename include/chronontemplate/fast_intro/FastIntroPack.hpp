#ifndef CHRONONTEMPLATE_FAST_INTRO_PACK_HPP
#define CHRONONTEMPLATE_FAST_INTRO_PACK_HPP

#include "chronontemplate/core/TemplateScene.hpp"

#include <string>
#include <vector>

namespace chronontemplate::fast_intro {

    struct FastIntroSpec {
        std::string name{"fast_intro_v1"};
        std::string kicker{"CHRONON TEMPLATE"};
        std::string title{"THE STORY SO FAR"};
        std::string subtitle{"A short line that sets up the story."};
        std::vector<std::string> topics{"CONTEXT", "EVIDENCE", "WHAT CHANGED"};
        std::string accent{"#363530"};
        std::string font{"ChrononTemplate/assets/fonts/Inter-Regular.ttf"};
        int durationFrames{72};
        float width{1920.f};
        float height{1080.f};
    };

    /// Retro statistic collage Fast Intro:
    /// 1. Era contextual title ("1990s") with slow forward camera push.
    /// 2. Gigantic statistic number ("37.7 M") crossing the frame: still
    ///    overflowing the borders at 2.0s, fully legible at 2.75s, then
    ///    slipping away behind the collage during the transition.
    /// 3. Hero collage entering at ~3.0s from an extreme close-up pull-back
    ///    and composing at 88% of the frame width.
    /// 4. Optional lower third closing title sliding in from bottom (off by
    ///    default: the reference replica carries no closing title).
    struct RetroStatCollageSpec {
        std::string name{"retro_stat_collage_v1"};
        std::string eraTitle{"1990s"};
        std::string statistic{"37.7 M"};
        std::string closingTitle{""};
        std::string collagePath{"ChrononTemplate/assets/images/retro_collage.png"};
        std::string font{"ChrononTemplate/assets/fonts/Impact.ttf"};
        std::string bgCenterColor{"#FFD24A"};
        std::string bgOuterColor{"#0E0202"};
        float eraFontSize{360.f};
        float statisticFontSize{360.f};
        float closingFontSize{80.f};
        float collageScaleIn{6.5f};
        float statisticScaleIn{8.2f};
        float collageTargetWidthRatio{0.88f};
        int durationFrames{173};
        float width{1920.f};
        float height{1080.f};
    };

    /// Author the opening plate, title/subtitle, topic chips, draw rail and
    /// moving marker. All copy and accent color are supplied by the caller.
    [[nodiscard]] LayerHandle& addFastIntro(TemplateScene& scene,
                                            const FastIntroSpec& spec);

    /// Author the retro stat fast intro: warm radial gradient background with
    /// soft concentric bands, era title, crash zoom statistic and the hero
    /// collage pull-back reveal.
    [[nodiscard]] LayerHandle& addRetroStatCollage(TemplateScene& scene,
                                                  const RetroStatCollageSpec& spec);

    /// Convenience shorthand matching the fast intro recipe signature.
    inline LayerHandle& addRetroStatIntro(TemplateScene& scene,
                                         const std::string& collagePath,
                                         const std::string& fontPath) {
        RetroStatCollageSpec spec;
        spec.collagePath = collagePath;
        spec.font = fontPath;
        return addRetroStatCollage(scene, spec);
    }

    // ── Fast Intro v2: one unified parametric family ─────────────────────
    //
    // Replaces the four diverging one-offs (ivory v1, retro dual-source,
    // 24s match-cut script, hard-coded disaster chapter) with a single
    // spec + recipe enum. Every recipe:
    //  - hooks in frames 0-12 (no dead openings),
    //  - carries a slow camera push (no static plates),
    //  - caps scales to [0.02, 3.5] (no singular transforms, no 8x GPU spikes),
    //  - uses Inter-Black by default (legible at 854x480),
    //  - lays out relative to cx/cy so 1920x1080 and 1080x1920 both work.

    enum class FastIntroRecipe {
        OpeningPlate,  // dark cinematic successor of fast_intro_v1
        PunchStat,     // single-source successor of retro_stat_collage
        WhipMatch,     // parametric successor of build_match_cut_plan.py
        ChapterCard    // parametric successor of emit_disaster_chapter_intro
    };

    struct FastIntroV2Spec {
        FastIntroRecipe recipe{FastIntroRecipe::OpeningPlate};
        std::string name{"fast_intro_v2_opening"};
        std::string font{"ChrononTemplate/assets/fonts/Inter-Black.ttf"};
        int durationFrames{150};
        float width{1920.f};
        float height{1080.f};
        // OpeningPlate / ChapterCard copy
        std::string kicker{"CHRONON TEMPLATE"};
        std::string title{"THE STORY SO FAR"};
        std::string subtitle{"A short line that sets up the story."};
        std::string chapterLabel{""};  // non-empty => chapter band rendered
        std::vector<std::string> topics{};  // 0-4 pill chips (flexible, was exactly 3)
        std::string accent{"#FF4D2E"};
        std::string ground{"#0B0B0E"};
        // PunchStat copy
        std::string eraTitle{"1990s"};
        std::string statistic{"37.7 M"};
        std::string closingTitle{""};
        std::string collagePath{"ChrononTemplate/assets/images/retro_collage.png"};
        std::string bgCenterColor{"#FFD24A"};
        std::string bgOuterColor{"#0E0202"};
        // WhipMatch copy
        std::vector<std::string> plates{};  // image assets, 4-16
        int whipQuickFrames{8};
        int whipHoldFrames{15};
        float cameraPush{160.f};
    };

    struct FastIntroV2Choice {
        FastIntroRecipe recipe{};
        std::string id{};
        std::string label{};
        int defaultDuration{150};
    };

    [[nodiscard]] std::vector<FastIntroV2Choice> fastIntroV2Choices();
    [[nodiscard]] int fastIntroV2DurationFrames(const FastIntroV2Spec& spec);
    [[nodiscard]] LayerHandle& addFastIntroV2(TemplateScene& scene,
                                              const FastIntroV2Spec& spec);

} // namespace chronontemplate::fast_intro

#endif // CHRONONTEMPLATE_FAST_INTRO_PACK_HPP
