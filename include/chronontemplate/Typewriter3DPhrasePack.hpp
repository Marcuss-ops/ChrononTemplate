// ChrononTemplate — 3D Typography with Glow & Typewriting motion presets.
//
// Combines 3D perspective / camera moves, MTSDF neon glow, and glyph-level
// typewriter reveal with modern web containers (rect stroke borders).
#ifndef CHRONONTEMPLATE_TYPEWRITER_3D_PHRASE_PACK_HPP
#define CHRONONTEMPLATE_TYPEWRITER_3D_PHRASE_PACK_HPP

#include "chronontemplate/ImportantPhrasePack.hpp"

#include <array>
#include <string>
#include <vector>

namespace chronontemplate {

    enum class Typewriter3DPhraseAnimation {
        OrbitGlow,
        PerspectiveTilt,
        DepthFloat,
        HeroCardSweep,
        StaggeredAscent,
        PaperCardWeb,
        DocCleanWhite,
        DocSearchBar,
        DocQuoteSerif,
        DocLowerThird,
        DocStatCard
    };

    struct Typewriter3DStyle {
        std::string font{"assets/fonts/Montserrat-Bold.ttf"};
        float font_size{60.f};
        std::array<float, 2> box{1200.f, 140.f};
        std::array<float, 2> position{960.f, 545.f};
        std::string fill{"#FFFFFF"};
        std::string glow{"#00E5FF"};
        float glow_radius{32.f};
        float glow_intensity{0.85f};
        // 3D Card container (Rect/RoundedRect Stroke)
        bool has_card{true};
        std::array<float, 2> card_size{1300.f, 360.f};
        float card_radius{28.f};
        std::string card_stroke{"#00E5FF"};
        float card_stroke_width{3.5f};
    };

    [[nodiscard]] Typewriter3DStyle typewriter3DStyle();
    [[nodiscard]] Typewriter3DStyle paperCardWebStyle();
    [[nodiscard]] Typewriter3DStyle docCleanWhiteStyle();
    [[nodiscard]] Typewriter3DStyle docSearchBarWebStyle();
    [[nodiscard]] Typewriter3DStyle docQuoteSerifStyle();
    [[nodiscard]] Typewriter3DStyle docLowerThirdStyle();
    [[nodiscard]] Typewriter3DStyle docStatCardStyle();
    [[nodiscard]] const char* name(Typewriter3DPhraseAnimation animation);
    [[nodiscard]] PhraseAnimationDefinition definition(Typewriter3DPhraseAnimation animation);
    [[nodiscard]] std::vector<Typewriter3DPhraseAnimation> typewriter3DPhraseAnimations();

}// namespace chronontemplate

#endif//CHRONONTEMPLATE_TYPEWRITER_3D_PHRASE_PACK_HPP
