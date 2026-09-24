// ChrononTemplate — restrained Modern Apple phrase motion presets.
#ifndef CHRONONTEMPLATE_APPLE_PHRASE_PACK_HPP
#define CHRONONTEMPLATE_APPLE_PHRASE_PACK_HPP

#include "chronontemplate/ImportantPhrasePack.hpp"

namespace chronontemplate {

    enum class ApplePhraseAnimation {
        FocusRise, SoftScale, WordCascade, LineCascade, PrecisionType,
        TrackingReveal, ExpandFromCenter, CompressIn, DepthFocus,
        ScaleSettle, BlurFocus, VerticalReveal, SoftOpacityReveal,
        HeroStatement, CinematicExit
    };

    [[nodiscard]] ClassicPhraseStyle applePhraseStyle();
    /// A still typographic specimen matching the supplied reference's bold,
    /// centered white sans-serif treatment. Its tracks are constant by design.
    [[nodiscard]] PhraseAnimationDefinition appleClassicStill();
    [[nodiscard]] const char* name(ApplePhraseAnimation animation);
    [[nodiscard]] PhraseAnimationDefinition definition(ApplePhraseAnimation animation);
    [[nodiscard]] std::vector<ApplePhraseAnimation> applePhraseAnimations();

}// namespace chronontemplate
#endif
