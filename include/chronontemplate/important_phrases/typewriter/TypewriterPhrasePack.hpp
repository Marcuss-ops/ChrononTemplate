// ChrononTemplate — the Typewriter important-phrase family.
//
// One file per family: this one owns the fifteen typed animations — the phrase
// appears glyph by glyph through the reveal window while the `_` underscore
// cursor trails, blinks, leads or holds. The shared look and the plan data
// types live in ImportantPhrasePack.hpp.
//
// The pack is data, not rendering: tools/important_phrases/
// emit_important_phrase_plans.cpp lowers these definitions to the Chronon3D
// render-plan contract. Every
// animation stays inside Chronon3D's canonical GPU text contract (see
// can_lower_gpu_text_animation), which is what lets the family render on the
// Vulkan lane with require_gpu_native instead of falling back to software
// text.

#ifndef CHRONONTEMPLATE_TYPEWRITER_PHRASE_PACK_HPP
#define CHRONONTEMPLATE_TYPEWRITER_PHRASE_PACK_HPP

#include "chronontemplate/important_phrases/ImportantPhrasePack.hpp"

#include <vector>

namespace chronontemplate {

    /// The fifteen Typewriter animations: the phrase typed in glyph by glyph
    /// through the reveal window while the `_` underscore cursor trails,
    /// blinks, leads or holds.
    enum class TypewriterPhraseAnimation {
        Fade,
        Cursor,
        CursorBlink,
        CursorHold,
        Lift,
        SlideIn,
        ScaleUp,
        BlurFocus,
        Soft,
        TrackingAssemble,
        Fast,
        Slow,
        DoubleBlink,
        CursorLeads,
        SoftLift
    };

    [[nodiscard]] const char* name(TypewriterPhraseAnimation animation);
    [[nodiscard]] PhraseAnimationDefinition definition(TypewriterPhraseAnimation animation);
    /// Payload-driven variant: scales the `_` cursor box by cursorScale
    /// (1.0 preserves the catalog authoring; clamps inside the emitter).
    [[nodiscard]] PhraseAnimationDefinition definitionScaled(TypewriterPhraseAnimation animation,
                                                             float cursorScale);
    [[nodiscard]] std::vector<TypewriterPhraseAnimation> typewriterPhraseAnimations();

}// namespace chronontemplate

#endif//CHRONONTEMPLATE_TYPEWRITER_PHRASE_PACK_HPP
