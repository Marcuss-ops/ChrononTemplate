// ChrononTemplate — the short-phrase family (1 to ~7 words).
//
// A short phrase does not need twelve engines: it needs one vocabulary of
// selectors (phrase / word / glyph), properties (position / scale / rotation /
// opacity / blur / tracking), a stagger and an exit. The twelve archetypes here
// are that vocabulary applied twelve ways — the recipes RenderingGen picks from
// when a phrase is short.
//
// The pack is data, not rendering, exactly like the important-phrase families:
// tools/emit_important_phrase_classic.cpp lowers these definitions to the
// Chronon3D render-plan contract and Chronon3D shapes the run. Every text
// animator stays inside Chronon3D's canonical GPU text contract (one selector,
// a forward glyph window or a full-run word emphasis), so the family renders on
// the Vulkan lane with require_gpu_native.
//
// The four-point star is NOT part of the text engine: it is a decor element
// (`short_phrase.decor.star_bumper`) that Motion3D rotates/scales and that
// compositing can place in front of the run.

#ifndef CHRONONTEMPLATE_SHORT_PHRASES_SHORT_PHRASE_PACK_HPP
#define CHRONONTEMPLATE_SHORT_PHRASES_SHORT_PHRASE_PACK_HPP

#include "chronontemplate/important_phrases/ImportantPhrasePack.hpp"

#include <cstddef>
#include <cstdint>
#include <string>
#include <vector>

namespace chronontemplate {

    /// The short-phrase archetypes. The ids are the wire names the
    /// catalog and the emitter consume (`short_phrase_*`).
    enum class ShortPhraseAnimation {
        ScaleSettleWord,         ///< scale + grey→white settle, for one strong word
        ShapePhraseWipe,         ///< phrase revealed while a shape crosses it
        SemanticTwoLine,         ///< two lines, the emphasised words lead in accent
        PhraseBuildFocus,        ///< the phrase builds in blocks, some words focused
        CharacterTrackingReveal, ///< almost letter by letter, wide tracking → normal
        WordMaskSequence,        ///< one word at a time in a fixed slot (leave → your → message)
        CharacterCascadeShapes,  ///< glyph cascade while decor shapes rotate
        WordCascadeSentence,     ///< word after word in, then out in the same order
        SemanticChainCurve,      ///< word cascade that folds away along an arc
        SimpleProgressivePhrase, ///< very clean progressive build, exits from the left
        SingleWordSwap,          ///< one word slot swaps out for the next
        CharacterWriteOn,        ///< an elegant glyph write-on, like typing
        EditorialBaselineRise,
        EditorialSideGlide,
        EditorialTrackingClose,
        EditorialFocusResolve,
        EditorialUnderlineDraw,
        EditorialRuleHandoff,
        EditorialGlyphCurtain,
        EditorialContrastSweep,
        EditorialQuietZoom,
        EditorialLiftAndRule,   ///< clean editorial recipes, append-only wire ids
        ProductHardMaskSlideUp,
        ProductKineticBlurIn,
        ProductWordStagger,
        ProductTrackingPullIn,
        ProductGradientSweep,
        ProductSubtitleDissolve,
        ProductDualToneReveal,
        ProductRollingTicker,
        ProductScaleSnap,
        ProductRadialExpansion,
        ProductDepthParallax,
        ProductGlintPass,     ///< product-motion recipes, append-only wire ids
        ProductLetterRise,
        ProductDigitalAssembly,
        ProductMaskedHeading,
        ProductSplitFlapText,
        ProductWarpText,
        ProductFoldText,
        ProductDecryptedText,
        ProductScrollReveal,
        ProductScrambledText,
        ProductGlareHover,
        ProductGlowCursor,
        ProductGradualBlur,
        ProductShapeBlur,
        EditorialPromptResponse,
        EditorialDiffPatch,
        EditorialTerminalFocus
    };

    /// How the phrase leaves. The entrance is the recipe; the exit is the beat
    /// the short-phrase families share.
    enum class ShortPhraseExit : std::uint8_t {
        Reverse,      ///< words leave in the same order they arrived
        Forward,      ///< words leave from the last to the first
        Wipe,         ///< a left-to-right wipe removes the run
        Scatter,      ///< units drift apart and fade
        ArcDissolve   ///< units bow along an arc while fading
    };

    /// The decorative element some recipes carry.
    enum class ShortPhraseDecor : std::uint8_t {
        None,
        StarBumper    ///< the four-point soft star
    };

    /// One short-phrase recipe: the phrase motion plus the editorial extras the
    /// short-phrase families add — the semantic emphasis, the exit mode and the
    /// optional decor element.
    struct ShortPhraseDefinition {
        std::string id{};
        std::string title{};
        std::string phrase{};
        int enter{24};      ///< entrance length in frames @ the pack's 30 fps
        std::vector<PhraseTrack> tracks{};              ///< layer-level motion
        std::vector<PhraseTextAnimator> textAnimators{};///< per-unit motion
        std::vector<std::size_t> emphasis{};            ///< word indices RenderingGen marked important
        ShortPhraseExit exit{ShortPhraseExit::Reverse};
        ShortPhraseDecor decor{ShortPhraseDecor::None};
        std::vector<PhraseAccent> accents{};            ///< optional under-phrase marks
        float font_size{0.f};                           ///< optional per-recipe size override
        /// Light theme (white background, black text) used by the shape-assisted
        /// recipes. Colour tracks use the pseudo properties `fill_blue` and
        /// `fill_gray` / `fill_orange`: a 0..1 amount of the accent / grey mixed over the resting fill.
        bool light{false};
        /// Additional native text copies used by prism, cut and replacement
        /// treatments. They are separate render-plan text layers, not DOM clones.
        struct TextOverlay {
            std::string id{};
            std::string text{};
            std::string fill{"#FFFFFF"};
            float offset_x{0.f};
            float offset_y{0.f};
            float opacity{1.f};
            std::vector<PhraseTrack> tracks{};
            std::vector<PhraseTextAnimator> textAnimators{};
        };
        std::vector<TextOverlay> textOverlays{};
        bool drawMainPhrase{true};
        std::string fill_color{};
        /// Explicit note when a React source interaction/effect is approximated by native RenderPlan motion.
        std::string adaptation_note{};
        /// White editorial paper palette with ink-black typography.
        bool white_background{false};
    };

    /// The decor bumper, kept out of the text engine as its own definition.
    struct ShortPhraseDecorDefinition {
        std::string id{};
        std::string shape{"four_point_star"};
        std::vector<PhraseTrack> tracks{};
    };

    /// The standard timing of a short phrase, in frames @ 30 fps. `minFrames`
    /// and `maxFrames` bracket a sensible clip; `inFrames + holdFrames +
    /// outFrames` is the documented structure inside that bracket.
    struct ShortPhraseTiming {
        int wordCount{0};
        int minFrames{0};
        int maxFrames{0};
        int inFrames{0};
        int holdFrames{0};
        int outFrames{0};
    };

    [[nodiscard]] const char* name(ShortPhraseAnimation animation);
    [[nodiscard]] ShortPhraseDefinition definition(ShortPhraseAnimation animation);
    [[nodiscard]] std::vector<ShortPhraseAnimation> shortPhraseAnimations();

    /// The decor definition for `decor` (`short_phrase.decor.star_bumper`).
    /// Throws `std::invalid_argument` for `ShortPhraseDecor::None`.
    [[nodiscard]] ShortPhraseDecorDefinition shortPhraseDecor(ShortPhraseDecor decor);

    /// How many whitespace-separated words a phrase holds.
    [[nodiscard]] std::size_t shortPhraseWordCount(const std::string& phrase);

    /// The standard timing envelope for a phrase of `wordCount` words:
    ///   1–2 words: 1.2–1.6 s | 3–4: 1.5–2.0 s | 5–7: 1.8–2.5 s  @ 30 fps.
    /// A count outside [1, 7] falls back to the nearest band.
    [[nodiscard]] ShortPhraseTiming shortPhraseTiming(int wordCount);

    /// The recipes RenderingGen may pick for a phrase of `wordCount` words.
    /// Empty outside the short-phrase range (1–7).
    [[nodiscard]] std::vector<ShortPhraseAnimation> shortPhraseSuggestions(int wordCount);

}// namespace chronontemplate

#endif//CHRONONTEMPLATE_SHORT_PHRASES_SHORT_PHRASE_PACK_HPP
