// ChrononTemplate — long central phrases with animated under-phrase accents.
//
// The recipes keep a calm, readable phrase on screen, then draw a colored
// underline/highlight beneath it. The accents are lowered as independent GPU
// shape layers by the important-phrase plan emitter.

#ifndef CHRONONTEMPLATE_PHRASE_HIGHLIGHT_PACK_HPP
#define CHRONONTEMPLATE_PHRASE_HIGHLIGHT_PACK_HPP

#include "chronontemplate/important_phrases/ImportantPhrasePack.hpp"

#include <vector>

namespace chronontemplate {

    enum class PhraseHighlightAnimation {
        RedUnderlineSweep,
        WarmMarkerSweep,
        CenterOutUnderline,
        DoubleRule,
        DelayedAccent,
        SoftPulse,
        ShortKeywordRule,
        StaggeredLines,
        IvoryUnderline,
        RedMarkerPulse,
        OffsetDoubleRule,
        GoldDrawOn,
        CenterDash,
        TripleEditorialRule,
        SplitMarker,
        SlowReveal
    };

    [[nodiscard]] const char* name(PhraseHighlightAnimation animation);
    [[nodiscard]] PhraseAnimationDefinition definition(PhraseHighlightAnimation animation);
    [[nodiscard]] std::vector<PhraseHighlightAnimation> phraseHighlightAnimations();

}// namespace chronontemplate

#endif//CHRONONTEMPLATE_PHRASE_HIGHLIGHT_PACK_HPP
