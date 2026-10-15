// ChrononTemplate — Documentary Highlighting 4.0
//
// 15 Documentary & Investigative Highlighting Presets in 3 Visual Families:
//   Family A: Yellow Highlight — Investigative / Newspaper / Archival
//   Family B: Kinetic Typography — Modern Documentary / Dark Impact
//   Family C: Camera + Highlight — Footage / Source / Scanner / Multi-Region
//
// 100% GPU-native rendering on Vulkan.

#ifndef CHRONONTEMPLATE_HIGHLIGHT_PHRASE_PACK_HPP
#define CHRONONTEMPLATE_HIGHLIGHT_PHRASE_PACK_HPP

#include "chronontemplate/important_phrases/ImportantPhrasePack.hpp"

#include <vector>

namespace chronontemplate {

    enum class HighlightPhraseAnimation {
        // Family A: Yellow Highlight — Documentary & Investigative
        Doc01YellowMarkerSweep,
        Doc02MultiLineStaggerHighlight,
        Doc03DocumentaryQuoteMarker,
        Doc04ArchivalSourceHighlight,
        Doc05SelectivePhraseTracking,

        // Family B: Kinetic Typography — Modern Documentary
        Doc06RedKeywordPunch,
        Doc07WordImpactReveal,
        Doc08MixedFontEmphasis,
        Doc09CinematicUnderlineDraw,
        Doc10SelectiveContrastFocus,

        // Family C: Camera + Highlight — Documentary Footage & Sources
        Doc11HeadlineCinematicZoom,
        Doc12QuoteLineByLineReveal,
        Doc13AnalogScannerHighlight,
        Doc14DualHighlightSequence,
        Doc15DocumentarySourceFocus
    };

    [[nodiscard]] ClassicPhraseStyle highlightPhraseStyle();
    [[nodiscard]] ClassicPhraseStyle highlightPhraseStyle(HighlightPhraseAnimation animation);
    [[nodiscard]] const char* name(HighlightPhraseAnimation animation);
    [[nodiscard]] PhraseAnimationDefinition definition(HighlightPhraseAnimation animation);
    [[nodiscard]] std::vector<HighlightPhraseAnimation> highlightPhraseAnimations();

}// namespace chronontemplate

#endif//CHRONONTEMPLATE_HIGHLIGHT_PHRASE_PACK_HPP
