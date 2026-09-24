// ChrononTemplate — the Classic important-phrase family.
//
// One file per family: this one owns the fourteen "normal" phrase animations —
// the timeless layer entrances, the staggered glyph reveals, the whole-run
// focuses and the full-run word emphases. The shared look and the plan data
// types live in ImportantPhrasePack.hpp; the Typewriter family has its own
// file and stays available even while a pipeline only renders one family.
//
// The pack is data, not rendering: tools/emit_important_phrase_classic.cpp
// lowers these definitions to the Chronon3D render-plan contract. Every
// animation stays inside Chronon3D's canonical GPU text contract (see
// can_lower_gpu_text_animation), which is what lets the family render on the
// Vulkan lane with require_gpu_native instead of falling back to software
// text.

#ifndef CHRONONTEMPLATE_CLASSIC_PHRASE_PACK_HPP
#define CHRONONTEMPLATE_CLASSIC_PHRASE_PACK_HPP

#include "chronontemplate/ImportantPhrasePack.hpp"

#include <vector>

namespace chronontemplate {

    /// The fourteen Classic phrase animations. The first seven move the phrase
    /// as one layer (the "normal" entrances), three stage it unit by unit
    /// through the staggered windows, two focus the whole run, and the last two
    /// are full-run word emphases.
    enum class ClassicPhraseAnimation {
        Fade,
        Rise,
        Drop,
        SlideFromLeft,
        SlideFromRight,
        ScalePop,
        ZoomSettle,
        Typewriter,
        GlyphLift,
        GlyphTrackingIn,
        TrackingTighten,
        BlurFocus,
        WordEmphasis,
        WordScaleIn
    };

    [[nodiscard]] const char* name(ClassicPhraseAnimation animation);
    [[nodiscard]] PhraseAnimationDefinition definition(ClassicPhraseAnimation animation);
    [[nodiscard]] std::vector<ClassicPhraseAnimation> classicPhraseAnimations();

}// namespace chronontemplate

#endif//CHRONONTEMPLATE_CLASSIC_PHRASE_PACK_HPP
