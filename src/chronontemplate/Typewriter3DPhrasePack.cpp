#include "chronontemplate/Typewriter3DPhrasePack.hpp"

#include <stdexcept>
#include <utility>

namespace chronontemplate {

    namespace {

        PhraseTrack track(const std::string& property, std::vector<PhraseKeyframe> keys,
                          const std::string& easing = "out_cubic") {
            return PhraseTrack{property, easing, std::move(keys)};
        }

        PhraseTrack cursorTrail(float half, int enter) {
            return track("position_x", {{0, -half}, {enter, half}}, "out_cubic");
        }

        PhraseTrack cursorBlink(int period, int from, int until) {
            std::vector<PhraseKeyframe> keys{{0, 0.f}, {5, 1.f}};
            if (from > 5) keys.push_back({from, 1.f});
            float value = 0.f;
            for (int frame = from + period / 2; frame < until; frame += period / 2) {
                keys.push_back({frame, value});
                value = 1.f - value;
            }
            keys.push_back({until, 1.f});
            return track("opacity", keys, "linear");
        }

        PhraseTextAnimator typedReveal(const std::string& window,
                                       std::vector<PhraseTrack> preTyping) {
            std::vector<PhraseTrack> properties;
            for (auto& property : preTyping) properties.push_back(std::move(property));
            return {PhraseSelector{"glyph", "forward", window}, std::move(properties)};
        }

    }// namespace

    Typewriter3DStyle typewriter3DStyle() {
        return Typewriter3DStyle{};
    }

    Typewriter3DStyle paperCardWebStyle() {
        Typewriter3DStyle s;
        s.font = "assets/fonts/Inter-SemiBold.ttf";
        s.font_size = 48.f;
        s.box = {1100.f, 100.f};
        s.position = {960.f, 540.f};
        s.fill = "#111111";
        s.glow = "#000000";
        s.glow_radius = 8.f;
        s.glow_intensity = 0.22f;
        s.has_card = true;
        s.card_size = {1180.f, 220.f};
        s.card_radius = 24.f;
        s.card_stroke = "#E5E5E0";
        s.card_stroke_width = 1.5f;
        return s;
    }

    Typewriter3DStyle docCleanWhiteStyle() {
        Typewriter3DStyle s;
        s.font = "assets/fonts/Inter-Regular.ttf";
        s.font_size = 54.f;
        s.box = {1200.f, 90.f};
        s.position = {960.f, 780.f};
        s.fill = "#FFFFFF";
        s.glow = "#000000";
        s.glow_radius = 12.f;
        s.glow_intensity = 0.35f;
        s.has_card = false;
        return s;
    }

    Typewriter3DStyle docSearchBarWebStyle() {
        Typewriter3DStyle s;
        s.font = "assets/fonts/Inter-SemiBold.ttf";
        s.font_size = 40.f;
        s.box = {940.f, 80.f};
        s.position = {960.f, 540.f};
        s.fill = "#1E293B";
        s.glow = "#000000";
        s.glow_radius = 8.f;
        s.glow_intensity = 0.18f;
        s.has_card = true;
        s.card_size = {1080.f, 100.f};
        s.card_radius = 50.f;
        s.card_stroke = "#E2E8F0";
        s.card_stroke_width = 1.5f;
        return s;
    }

    Typewriter3DStyle docQuoteSerifStyle() {
        Typewriter3DStyle s;
        s.font = "assets/fonts/Georgia_Bold.ttf";
        s.font_size = 48.f;
        s.box = {1200.f, 100.f};
        s.position = {960.f, 540.f};
        s.fill = "#111111";
        s.glow = "#000000";
        s.glow_radius = 8.f;
        s.glow_intensity = 0.20f;
        s.has_card = true;
        s.card_size = {1280.f, 260.f};
        s.card_radius = 20.f;
        s.card_stroke = "#E5E5E0";
        s.card_stroke_width = 1.2f;
        return s;
    }

    Typewriter3DStyle docLowerThirdStyle() {
        Typewriter3DStyle s;
        s.font = "assets/fonts/Inter-Bold.ttf";
        s.font_size = 38.f;
        s.box = {300.f, 50.f};
        s.position = {640.f, 815.f};
        s.fill = "#FFFFFF";
        s.glow = "#000000";
        s.glow_radius = 10.f;
        s.glow_intensity = 0.30f;
        s.has_card = false;
        return s;
    }

    Typewriter3DStyle docStatCardStyle() {
        Typewriter3DStyle s;
        s.font = "assets/fonts/Inter-Bold.ttf";
        s.font_size = 64.f;
        s.box = {260.f, 90.f};
        s.position = {600.f, 540.f};
        s.fill = "#0F172A";
        s.glow = "#000000";
        s.glow_radius = 8.f;
        s.glow_intensity = 0.20f;
        s.has_card = true;
        s.card_size = {1160.f, 180.f};
        s.card_radius = 20.f;
        s.card_stroke = "#E2E8F0";
        s.card_stroke_width = 1.5f;
        return s;
    }

    Typewriter3DStyle docUnderlineDrawStyle() {
        Typewriter3DStyle s;
        s.font = "assets/fonts/Poppins-Bold.ttf";
        s.font_size = 52.f;
        s.box = {1200.f, 100.f};
        s.position = {960.f, 510.f};
        s.fill = "#FFFFFF";
        s.glow = "#000000";
        s.glow_radius = 10.f;
        s.glow_intensity = 0.28f;
        s.has_card = false;
        return s;
    }

    Typewriter3DStyle docWordStageStyle() {
        Typewriter3DStyle s;
        s.font = "assets/fonts/Poppins-Bold.ttf";
        s.font_size = 96.f;
        s.box = {800.f, 140.f};
        s.position = {960.f, 540.f};
        s.fill = "#FFFFFF";
        s.glow = "#000000";
        s.glow_radius = 12.f;
        s.glow_intensity = 0.25f;
        s.has_card = false;
        return s;
    }

    Typewriter3DStyle docTrailerScaleStyle() {
        Typewriter3DStyle s;
        s.font = "assets/fonts/Montserrat-Bold.ttf";
        s.font_size = 60.f;
        s.box = {1400.f, 120.f};
        s.position = {960.f, 540.f};
        s.fill = "#FFFFFF";
        s.glow = "#000000";
        s.glow_radius = 10.f;
        s.glow_intensity = 0.35f;
        s.has_card = false;
        return s;
    }

    Typewriter3DStyle docCountUpStatStyle() {
        Typewriter3DStyle s;
        s.font = "assets/fonts/Sora.ttf";
        s.font_size = 76.f;
        s.box = {600.f, 100.f};
        s.position = {960.f, 520.f};
        s.fill = "#0F172A";
        s.glow = "#000000";
        s.glow_radius = 8.f;
        s.glow_intensity = 0.22f;
        s.has_card = true;
        s.card_size = {760.f, 240.f};
        s.card_radius = 24.f;
        s.card_stroke = "#E2E8F0";
        s.card_stroke_width = 1.5f;
        return s;
    }

    const char* name(Typewriter3DPhraseAnimation animation) {
        switch (animation) {
            case Typewriter3DPhraseAnimation::OrbitGlow: return "typewriter_3d_orbit_glow";
            case Typewriter3DPhraseAnimation::PerspectiveTilt: return "typewriter_3d_perspective_tilt";
            case Typewriter3DPhraseAnimation::DepthFloat: return "typewriter_3d_depth_float";
            case Typewriter3DPhraseAnimation::HeroCardSweep: return "typewriter_3d_hero_card_sweep";
            case Typewriter3DPhraseAnimation::StaggeredAscent: return "typewriter_3d_staggered_ascent";
            case Typewriter3DPhraseAnimation::PaperCardWeb: return "typewriter_doc_paper_card_web";
            case Typewriter3DPhraseAnimation::DocCleanWhite: return "typewriter_doc_clean_white";
            case Typewriter3DPhraseAnimation::DocSearchBar: return "typewriter_doc_search_bar";
            case Typewriter3DPhraseAnimation::DocQuoteSerif: return "typewriter_doc_quote_serif";
            case Typewriter3DPhraseAnimation::DocLowerThird: return "typewriter_doc_lower_third";
            case Typewriter3DPhraseAnimation::DocStatCard: return "typewriter_doc_stat_card";
            case Typewriter3DPhraseAnimation::DocUnderlineDraw: return "typewriter_doc_underline_draw";
            case Typewriter3DPhraseAnimation::DocWordStage: return "typewriter_doc_word_stage";
            case Typewriter3DPhraseAnimation::DocTrailerScale: return "typewriter_doc_trailer_scale";
            case Typewriter3DPhraseAnimation::DocCountUpStat: return "typewriter_doc_count_up_stat";
        }
        throw std::invalid_argument("chronontemplate::name: unknown 3D typewriter animation");
    }

    std::vector<Typewriter3DPhraseAnimation> typewriter3DPhraseAnimations() {
        return {
            Typewriter3DPhraseAnimation::OrbitGlow,
            Typewriter3DPhraseAnimation::PerspectiveTilt,
            Typewriter3DPhraseAnimation::DepthFloat,
            Typewriter3DPhraseAnimation::HeroCardSweep,
            Typewriter3DPhraseAnimation::StaggeredAscent,
            Typewriter3DPhraseAnimation::PaperCardWeb,
            Typewriter3DPhraseAnimation::DocCleanWhite,
            Typewriter3DPhraseAnimation::DocSearchBar,
            Typewriter3DPhraseAnimation::DocQuoteSerif,
            Typewriter3DPhraseAnimation::DocLowerThird,
            Typewriter3DPhraseAnimation::DocStatCard,
            Typewriter3DPhraseAnimation::DocUnderlineDraw,
            Typewriter3DPhraseAnimation::DocWordStage,
            Typewriter3DPhraseAnimation::DocTrailerScale,
            Typewriter3DPhraseAnimation::DocCountUpStat
        };
    }

    PhraseAnimationDefinition definition(Typewriter3DPhraseAnimation animation) {
        constexpr int enter = 60;// 2 s entrance @ 30 fps
        const std::vector<PhraseTrack> typing{track("opacity", {{0, 0.f}, {enter, 0.f}}, "linear")};

        switch (animation) {
            case Typewriter3DPhraseAnimation::OrbitGlow:
                return {"typewriter_3d_orbit_glow", "3D Orbit Glow Typewriter",
                        "CREATIVE MOTION ENGINE", enter,
                        {track("opacity", {{0, 0.f}, {15, 1.f}, {enter + 30, 1.f}}, "linear"),
                         track("position_z", {{0, -150.f}, {enter, 0.f}}, "out_cubic")},
                        {typedReveal("reveal", typing)},
                        PhraseCursor{"_", {60.f, 100.f}, {960.f, 545.f},
                                     {cursorTrail(430.f, enter), cursorBlink(12, enter, enter + 40)}}};

            case Typewriter3DPhraseAnimation::PerspectiveTilt:
                return {"typewriter_3d_perspective_tilt", "3D Perspective Tilt Typewriter",
                        "FUTURE OF ANIMATION", enter,
                        {track("opacity", {{0, 0.f}, {10, 1.f}, {enter + 30, 1.f}}, "linear"),
                         track("rotation_x", {{0, 15.f}, {enter, 0.f}}, "out_cubic")},
                        {typedReveal("reveal", typing)},
                        PhraseCursor{"_", {60.f, 100.f}, {960.f, 545.f},
                                     {cursorTrail(410.f, enter), cursorBlink(10, enter, enter + 45)}}};

            case Typewriter3DPhraseAnimation::DepthFloat:
                return {"typewriter_3d_depth_float", "3D Depth Float Typewriter",
                        "BEYOND TWO DIMENSIONS", enter,
                        {track("opacity", {{0, 0.f}, {20, 1.f}, {enter + 30, 1.f}}, "linear"),
                         track("scale", {{0, 0.8f}, {enter, 1.0f}}, "out_back")},
                        {typedReveal("reveal_soft", typing)},
                        PhraseCursor{"_", {60.f, 100.f}, {960.f, 545.f},
                                     {cursorTrail(440.f, enter), cursorBlink(12, enter, enter + 40)}}};

            case Typewriter3DPhraseAnimation::HeroCardSweep:
                return {"typewriter_3d_hero_card_sweep", "3D Hero Card Sweep Typewriter",
                        "DESIGNED FOR VELOX", enter,
                        {track("opacity", {{0, 0.f}, {12, 1.f}, {enter + 30, 1.f}}, "linear"),
                         track("position_y", {{0, 40.f}, {enter, 0.f}}, "out_cubic")},
                        {typedReveal("reveal", typing)},
                        PhraseCursor{"_", {60.f, 100.f}, {960.f, 545.f},
                                     {cursorTrail(390.f, enter), cursorBlink(14, enter, enter + 40)}}};

            case Typewriter3DPhraseAnimation::StaggeredAscent:
                return {"typewriter_3d_staggered_ascent", "3D Staggered Ascent Typewriter",
                        "NEXT GENERATION GRAPHICS", enter,
                        {track("opacity", {{0, 0.f}, {10, 1.f}, {enter + 30, 1.f}}, "linear")},
                        {typedReveal("reveal",
                                     {track("position_y", {{0, -35.f}, {enter, -35.f}}, "linear")})},
                        PhraseCursor{"_", {60.f, 100.f}, {960.f, 545.f},
                                     {cursorTrail(450.f, enter), cursorBlink(12, enter, enter + 40)}}};

            case Typewriter3DPhraseAnimation::PaperCardWeb:
                return {"typewriter_doc_paper_card_web", "Documentary Web Paper Card",
                        "The Architecture of Modern Systems.", enter,
                        {track("opacity", {{0, 0.f}, {10, 1.f}, {enter + 50, 1.f}, {enter + 65, 0.f}}, "linear"),
                         track("position_y", {{0, 18.f}, {12, 0.f}}, "out_cubic")},
                        {typedReveal("ramp", typing)},
                        PhraseCursor{}};

            case Typewriter3DPhraseAnimation::DocCleanWhite:
                return {"typewriter_doc_clean_white", "Documentary Clean White Caption",
                        "LA FORZA DI UN CAMPIONE", enter,
                        {track("opacity", {{0, 0.f}, {8, 1.f}, {enter + 45, 1.f}, {enter + 60, 0.f}}, "linear")},
                        {typedReveal("ramp", typing)},
                        PhraseCursor{}};

            case Typewriter3DPhraseAnimation::DocSearchBar:
                return {"typewriter_doc_search_bar", "Documentary Web Search Bar",
                        "how the modern internet was built", enter,
                        {track("opacity", {{0, 0.f}, {10, 1.f}, {enter + 50, 1.f}, {enter + 65, 0.f}}, "linear"),
                         track("position_y", {{0, 16.f}, {12, 0.f}}, "out_cubic")},
                        {typedReveal("ramp", typing)},
                        PhraseCursor{}};

            case Typewriter3DPhraseAnimation::DocQuoteSerif:
                return {"typewriter_doc_quote_serif", "Documentary Editorial Quote",
                        "“Simplicity is prerequisite for reliability.”", enter,
                        {track("opacity", {{0, 0.f}, {10, 1.f}, {enter + 50, 1.f}, {enter + 65, 0.f}}, "linear"),
                         track("position_y", {{0, 16.f}, {12, 0.f}}, "out_cubic")},
                        {typedReveal("ramp", typing)},
                        PhraseCursor{}};

            case Typewriter3DPhraseAnimation::DocLowerThird:
                return {"typewriter_doc_lower_third", "Documentary Lower Third",
                        "ARLO CHEN", enter,
                        {track("opacity", {{0, 0.f}, {8, 1.f}, {enter + 45, 1.f}, {enter + 60, 0.f}}, "linear")},
                        {typedReveal("ramp", typing)},
                        PhraseCursor{}};

            case Typewriter3DPhraseAnimation::DocStatCard:
                return {"typewriter_doc_stat_card", "Documentary Stat Callout Card",
                        "73% of all digital interactions are now automated.", enter,
                        {track("opacity", {{0, 0.f}, {10, 1.f}, {enter + 50, 1.f}, {enter + 65, 0.f}}, "linear"),
                         track("position_y", {{0, 16.f}, {12, 0.f}}, "out_cubic")},
                        {typedReveal("ramp", typing)},
                        PhraseCursor{}};

            case Typewriter3DPhraseAnimation::DocUnderlineDraw:
                return {"typewriter_doc_underline_draw", "Documentary Underline Draw-On",
                        "PRECISION OVER PERFECTION", enter,
                        {track("opacity", {{0, 0.f}, {8, 1.f}, {enter + 45, 1.f}, {enter + 60, 0.f}}, "linear")},
                        {typedReveal("ramp", typing)},
                        PhraseCursor{}};

            case Typewriter3DPhraseAnimation::DocWordStage:
                return {"typewriter_doc_word_stage", "Kinetic Minimal Word Stage",
                        "IDEAS SHAPE OUR REALITY", enter,
                        {track("opacity", {{0, 0.f}, {4, 1.f}, {enter + 50, 1.f}, {enter + 60, 0.f}}, "linear"),
                         track("scale", {{0, 1.08f}, {18, 1.0f}}, "out_cubic")},
                        {typedReveal("ramp", typing)},
                        PhraseCursor{}};

            case Typewriter3DPhraseAnimation::DocTrailerScale:
                return {"typewriter_doc_trailer_scale", "Cinematic Trailer Scale Extrude",
                        "BEYOND THE SURFACE", enter,
                        {track("opacity", {{0, 0.f}, {8, 1.f}, {enter + 40, 1.f}, {enter + 55, 0.f}}, "linear"),
                         track("scale", {{0, 1.32f}, {45, 1.0f}}, "out_cubic")},
                        {typedReveal("ramp", typing)},
                        PhraseCursor{}};

            case Typewriter3DPhraseAnimation::DocCountUpStat:
                return {"typewriter_doc_count_up_stat", "Documentary Stepped Count-Up",
                        "99.9% SYSTEM AVAILABILITY", enter,
                        {track("opacity", {{0, 0.f}, {10, 1.f}, {enter + 50, 1.f}, {enter + 65, 0.f}}, "linear"),
                         track("position_y", {{0, 16.f}, {12, 0.f}}, "out_cubic")},
                        {typedReveal("ramp", typing)},
                        PhraseCursor{}};
        }
        throw std::invalid_argument("chronontemplate::definition: unknown 3D typewriter animation");
    }

}// namespace chronontemplate
