#include "chronontemplate/short_phrases/ShortPhrasePack.hpp"

#include <cctype>
#include <stdexcept>
#include <utility>

namespace chronontemplate {

    namespace {

        PhraseTrack track(const std::string& property, std::vector<PhraseKeyframe> keys,
                          const std::string& easing = "out_cubic") {
            return PhraseTrack{property, easing, std::move(keys)};
        }

        PhraseTrack fadeIn(int enter, int over) {
            return track("opacity", {{0, 0.f}, {over, 1.f}, {enter, 1.f}}, "linear");
        }

        PhraseTextAnimator animator(PhraseSelector selector, std::vector<PhraseTrack> properties) {
            return PhraseTextAnimator{std::move(selector), std::move(properties)};
        }

    }// namespace

    const char* name(ShortPhraseAnimation animation) {
        switch (animation) {
            case ShortPhraseAnimation::ScaleSettleWord: return "short_phrase_scale_settle_word";
            case ShortPhraseAnimation::ShapePhraseWipe: return "short_phrase_shape_phrase_wipe";
            case ShortPhraseAnimation::SemanticTwoLine: return "short_phrase_semantic_two_line";
            case ShortPhraseAnimation::PhraseBuildFocus: return "short_phrase_phrase_build_focus";
            case ShortPhraseAnimation::CharacterTrackingReveal: return "short_phrase_character_tracking_reveal";
            case ShortPhraseAnimation::WordMaskSequence: return "short_phrase_word_mask_sequence";
            case ShortPhraseAnimation::CharacterCascadeShapes: return "short_phrase_character_cascade_shapes";
            case ShortPhraseAnimation::WordCascadeSentence: return "short_phrase_word_cascade_sentence";
            case ShortPhraseAnimation::SemanticChainCurve: return "short_phrase_semantic_chain_curve";
            case ShortPhraseAnimation::SimpleProgressivePhrase: return "short_phrase_simple_progressive_phrase";
            case ShortPhraseAnimation::SingleWordSwap: return "short_phrase_single_word_swap";
            case ShortPhraseAnimation::CharacterWriteOn: return "short_phrase_character_write_on";
            case ShortPhraseAnimation::EditorialBaselineRise: return "short_phrase_editorial_baseline_rise";
            case ShortPhraseAnimation::EditorialSideGlide: return "short_phrase_editorial_side_glide";
            case ShortPhraseAnimation::EditorialTrackingClose: return "short_phrase_editorial_tracking_close";
            case ShortPhraseAnimation::EditorialFocusResolve: return "short_phrase_editorial_focus_resolve";
            case ShortPhraseAnimation::EditorialUnderlineDraw: return "short_phrase_editorial_underline_draw";
            case ShortPhraseAnimation::EditorialRuleHandoff: return "short_phrase_editorial_rule_handoff";
            case ShortPhraseAnimation::EditorialGlyphCurtain: return "short_phrase_editorial_glyph_curtain";
            case ShortPhraseAnimation::EditorialContrastSweep: return "short_phrase_editorial_contrast_sweep";
            case ShortPhraseAnimation::EditorialQuietZoom: return "short_phrase_editorial_quiet_zoom";
            case ShortPhraseAnimation::EditorialLiftAndRule: return "short_phrase_editorial_lift_and_rule";
        }
        throw std::invalid_argument("chronontemplate::name: unknown short phrase animation");
    }

    std::vector<ShortPhraseAnimation> shortPhraseAnimations() {
        return {ShortPhraseAnimation::ScaleSettleWord,
                ShortPhraseAnimation::ShapePhraseWipe,
                ShortPhraseAnimation::SemanticTwoLine,
                ShortPhraseAnimation::PhraseBuildFocus,
                ShortPhraseAnimation::CharacterTrackingReveal,
                ShortPhraseAnimation::WordMaskSequence,
                ShortPhraseAnimation::CharacterCascadeShapes,
                ShortPhraseAnimation::WordCascadeSentence,
                ShortPhraseAnimation::SemanticChainCurve,
                ShortPhraseAnimation::SimpleProgressivePhrase,
                ShortPhraseAnimation::SingleWordSwap,
                ShortPhraseAnimation::CharacterWriteOn,
                ShortPhraseAnimation::EditorialBaselineRise,
                ShortPhraseAnimation::EditorialSideGlide,
                ShortPhraseAnimation::EditorialTrackingClose,
                ShortPhraseAnimation::EditorialFocusResolve,
                ShortPhraseAnimation::EditorialUnderlineDraw,
                ShortPhraseAnimation::EditorialRuleHandoff,
                ShortPhraseAnimation::EditorialGlyphCurtain,
                ShortPhraseAnimation::EditorialContrastSweep,
                ShortPhraseAnimation::EditorialQuietZoom,
                ShortPhraseAnimation::EditorialLiftAndRule};
    }

    static ShortPhraseDefinition entranceDefinition(ShortPhraseAnimation animation) {
        // Entrance keyframes in frames at the pack's 30 fps. Short phrases are
        // fast: the enter window is 300–1000 ms, never the two seconds a full
        // important-phrase showcase uses.
        switch (animation) {
            case ShortPhraseAnimation::EditorialBaselineRise:
                return {name(animation), "Word Snap", "Le idee prendono forma", 16,
                        {track("position_y", {{0, 88.f}, {11, -9.f}, {16, 0.f}}),
                         track("scale", {{0, 0.88f}, {11, 1.035f}, {16, 1.f}}), fadeIn(16, 7)},
                        {animator(PhraseSelector{"word", "forward", "band"},
                                  {track("position_y", {{0, 28.f}, {16, 0.f}}),
                                   track("opacity", {{0, 0.15f}, {16, 1.f}}, "linear")})},
                        {}, ShortPhraseExit::Reverse, ShortPhraseDecor::None, {}, 104.f};
            case ShortPhraseAnimation::EditorialSideGlide:
                return {name(animation), "Split Slide", "Il dettaglio fa la differenza", 20,
                        {fadeIn(20, 6)},
                        {animator(PhraseSelector{"word", "forward", "band"},
                                  {track("position_x", {{0, -72.f}, {14, 6.f}, {20, 0.f}}),
                                   track("position_y", {{0, 20.f}, {20, 0.f}}),
                                   track("opacity", {{0, 0.f}, {8, 1.f}, {20, 1.f}}, "linear")})},
                        {}, ShortPhraseExit::Reverse, ShortPhraseDecor::None, {}, 88.f, true};
            case ShortPhraseAnimation::EditorialTrackingClose:
                return {name(animation), "Type Bloom", "Meno rumore. Più significato.", 20,
                        {track("scale", {{0, 0.94f}, {15, 1.025f}, {20, 1.f}}), fadeIn(20, 7)},
                        {animator(PhraseSelector{"glyph", "forward", "full"},
                                  {track("tracking", {{0, 18.f}, {20, 0.f}})})},
                        {}, ShortPhraseExit::Reverse, ShortPhraseDecor::None, {}, 86.f};
            case ShortPhraseAnimation::EditorialFocusResolve:
                return {name(animation), "Focus Lock", "Un nuovo punto di vista", 18,
                        {track("scale", {{0, 1.08f}, {13, 0.985f}, {18, 1.f}}), fadeIn(18, 6)},
                        {animator(PhraseSelector{"glyph", "forward", "full"},
                                  {track("blur", {{0, 18.f}, {12, 0.f}, {18, 0.f}})})},
                        {}, ShortPhraseExit::Reverse, ShortPhraseDecor::None, {}, 96.f};
            case ShortPhraseAnimation::EditorialUnderlineDraw:
                return {name(animation), "Accent Sweep", "Semplice. Non banale.", 20,
                        {track("position_y", {{0, 44.f}, {14, -5.f}, {20, 0.f}}), fadeIn(20, 6)},
                        {animator(PhraseSelector{"word", "forward", "band"},
                                  {track("opacity", {{0, 0.2f}, {20, 1.f}}, "linear")})},
                        {}, ShortPhraseExit::Reverse, ShortPhraseDecor::None,
                        {PhraseAccent{"underline", "#6C8CFF", 760.f, 5.f, 94.f, 2.f, 1.f,
                                      {track("scale_x", {{0, 0.f}, {9, 0.f}, {20, 1.f}}),
                                       track("opacity", {{0, 0.f}, {7, 0.f}, {12, 1.f}, {20, 1.f}}, "linear")}}}, 104.f};
            case ShortPhraseAnimation::EditorialRuleHandoff:
                return {name(animation), "Color Flip", "Dalle idee ai risultati", 20,
                        {track("position_x", {{0, 110.f}, {14, -8.f}, {20, 0.f}}), fadeIn(20, 7)},
                        {animator(PhraseSelector{"word", "forward", "band"},
                                  {track("fill_blue", {{0, 1.f}, {20, 1.f}}, "linear")})},
                        {}, ShortPhraseExit::Reverse, ShortPhraseDecor::None,
                        {PhraseAccent{"rule", "#6C8CFF", 3.f, 170.f, 0.f, 1.f, 1.f,
                                      {track("position_x", {{0, -760.f}, {20, -610.f}}),
                                       track("scale_y", {{0, 0.f}, {10, 1.15f}, {20, 1.f}}),
                                       fadeIn(20, 6)}}}, 96.f};
            case ShortPhraseAnimation::EditorialGlyphCurtain:
                return {name(animation), "Mask Reveal", "Lascia parlare le immagini", 22,
                        {fadeIn(22, 5)},
                        {animator(PhraseSelector{"glyph", "forward", "reveal_soft"},
                                  {track("opacity", {{0, 0.f}, {22, 0.f}}, "linear"),
                                   track("position_y", {{0, 34.f}, {22, 0.f}})})},
                        {}, ShortPhraseExit::Wipe, ShortPhraseDecor::None, {}, 92.f};
            case ShortPhraseAnimation::EditorialContrastSweep:
                return {name(animation), "Word Highlight", "La chiarezza cambia tutto", 24,
                        {fadeIn(24, 6)},
                        {animator(PhraseSelector{"word", "forward", "band"},
                                  {track("position_y", {{0, 20.f}, {24, 0.f}}),
                                   track("opacity", {{0, 0.2f}, {24, 1.f}}, "linear"),
                                   track("fill_blue", {{0, 1.f}, {24, 1.f}}, "linear")})},
                        {2}, ShortPhraseExit::Reverse, ShortPhraseDecor::None, {}, 96.f, true};
            case ShortPhraseAnimation::EditorialQuietZoom:
                return {name(animation), "Pop Settle", "Guarda oltre", 16,
                        {track("scale", {{0, 0.78f}, {11, 1.06f}, {16, 1.f}}, "out_back"),
                         track("blur", {{0, 10.f}, {11, 0.f}, {16, 0.f}}), fadeIn(16, 5)},
                        {}, {}, ShortPhraseExit::Reverse, ShortPhraseDecor::None, {}, 132.f};
            case ShortPhraseAnimation::EditorialLiftAndRule:
                return {name(animation), "Float Stack", "Una storia da ricordare", 22,
                        {track("position_y", {{0, -72.f}, {15, 8.f}, {22, 0.f}}),
                         track("scale", {{0, 0.94f}, {15, 1.02f}, {22, 1.f}}), fadeIn(22, 6)},
                        {animator(PhraseSelector{"word", "forward", "band"},
                                  {track("position_y", {{0, -24.f}, {22, 0.f}}),
                                   track("opacity", {{0, 0.15f}, {22, 1.f}}, "linear")})},
                        {}, ShortPhraseExit::Reverse, ShortPhraseDecor::None,
                        {PhraseAccent{"top_rule", "#6C8CFF", 240.f, 3.f, -100.f, 1.f, 1.f,
                                      {track("scale_x", {{0, 0.15f}, {22, 1.f}}), fadeIn(22, 7)}}}, 100.f};

            // ── 01 · scale settle (1 strong word) ──────────────────────────
            case ShortPhraseAnimation::ScaleSettleWord:
                return {"short_phrase_scale_settle_word", "Scale Settle",
                        "Clean", 12,
                        {track("scale", {{0, 1.32f}, {8, 0.98f}, {12, 1.f}}),
                          track("blur", {{0, 7.f}, {8, 0.f}, {12, 0.f}}),
                          fadeIn(12, 8)},
                         {animator(PhraseSelector{"word", "forward", "full"},
                                   {track("fill_gray", {{0, 1.f}, {12, 0.f}}, "out_cubic")})},
                         {}, ShortPhraseExit::Reverse, ShortPhraseDecor::None};

            // ── 02 · shape-assisted wipe ────────────────────────────────────
            case ShortPhraseAnimation::ShapePhraseWipe:
                return {"short_phrase_shape_phrase_wipe", "Shape Phrase Wipe",
                        "It's really easy to manage.", 18,
                        {fadeIn(18, 10)},
                        {animator(PhraseSelector{"glyph", "forward", "reveal_soft"},
                                  {track("opacity", {{0, 0.f}, {18, 0.f}}, "linear")})},
                        {}, ShortPhraseExit::Wipe, ShortPhraseDecor::StarBumper, {}, 0.f, true};

            // ── 03 · semantic two-line highlight ────────────────────────────
            case ShortPhraseAnimation::SemanticTwoLine:
                return {"short_phrase_semantic_two_line", "Semantic Two Line",
                        "Good text design is invisible\nbad text design is unforgettable", 33,
                         {},
                         {animator(PhraseSelector{"word", "forward", "band"},
                                   {track("opacity", {{0, 0.2f}, {33, 1.f}}, "linear"),
                                    track("fill_gray", {{0, 1.f}, {33, 1.f}}, "linear")})},
                         {4, 5}, ShortPhraseExit::Forward, ShortPhraseDecor::None, {}, 76.f};

            // ── 04 · phrase build with focus words ──────────────────────────
            case ShortPhraseAnimation::PhraseBuildFocus:
                return {"short_phrase_phrase_build_focus", "Phrase Build Focus",
                        "Will make your video", 18,
                        {},
                        {animator(PhraseSelector{"word", "forward", "band"},
                                  {track("opacity", {{0, 0.15f}, {18, 1.f}}, "linear"),
                                    track("fill_blue", {{0, 1.f}, {18, 1.f}}, "linear"),
                                    track("position_x", {{0, -6.f}, {18, 0.f}})})},
                         {}, ShortPhraseExit::Reverse, ShortPhraseDecor::None};

            // ── 05 · character tracking reveal (1–3 words) ──────────────────
            case ShortPhraseAnimation::CharacterTrackingReveal:
                return {"short_phrase_character_tracking_reveal", "Character Tracking Reveal",
                        "more expensive", 20,
                        {},
                        {animator(PhraseSelector{"glyph", "forward", "reveal"},
                                  {track("opacity", {{0, 0.f}, {20, 0.f}}, "linear"),
                                   track("tracking", {{0, 20.f}, {20, 20.f}}, "linear"),
                                   track("position_x", {{0, 8.f}, {20, 8.f}}, "linear")})},
                        {}, ShortPhraseExit::Wipe, ShortPhraseDecor::None};

            // ── 06 · word mask sequence (one slot, one word at a time) ──────
            case ShortPhraseAnimation::WordMaskSequence:
                return {"short_phrase_word_mask_sequence", "Word Mask Sequence",
                        "leave your message", 24,
                        {},
                        {animator(PhraseSelector{"word", "forward", "band"},
                                  {track("opacity", {{0, 0.f}, {8, 1.f}, {24, 1.f}}, "linear"),
                                   track("position_x", {{0, 24.f}, {24, 0.f}})})},
                        {}, ShortPhraseExit::Wipe, ShortPhraseDecor::None};

            // ── 07 · character cascade with decor shapes ────────────────────
            case ShortPhraseAnimation::CharacterCascadeShapes:
                return {"short_phrase_character_cascade_shapes", "Character Cascade Shapes",
                        "Really smooth.", 21,
                        {},
                        {animator(PhraseSelector{"glyph", "forward", "reveal"},
                                  {track("opacity", {{0, 0.f}, {21, 0.f}}, "linear")})},
                         {}, ShortPhraseExit::Scatter, ShortPhraseDecor::StarBumper, {}, 0.f, true};

            // ── 08 · word cascade sentence ──────────────────────────────────
            case ShortPhraseAnimation::WordCascadeSentence:
                return {"short_phrase_word_cascade_sentence", "Word Cascade Sentence",
                        "Clean. Simple. Attractive.", 27,
                        {},
                        {animator(PhraseSelector{"word", "forward", "band"},
                                  {track("opacity", {{0, 0.2f}, {27, 1.f}}, "linear"),
                                    track("fill_blue", {{0, 1.f}, {27, 1.f}}, "linear"),
                                    track("position_x", {{0, -4.f}, {27, 0.f}})})},
                        {}, ShortPhraseExit::Reverse, ShortPhraseDecor::None};

            // ── 09 · semantic chain that folds away on an arc ───────────────
            case ShortPhraseAnimation::SemanticChainCurve:
                return {"short_phrase_semantic_chain_curve", "Semantic Chain Curve",
                        "we draw attention to something important", 30,
                        {},
                        {animator(PhraseSelector{"word", "forward", "band"},
                                  {track("opacity", {{0, 0.2f}, {30, 1.f}}, "linear"),
                                    track("fill_gray", {{0, 1.f}, {30, 1.f}}, "linear"),
                                    track("position_y", {{0, 10.f}, {30, 0.f}})})},
                        {2, 5}, ShortPhraseExit::ArcDissolve, ShortPhraseDecor::None};

            // ── 10 · simple progressive phrase ──────────────────────────────
            case ShortPhraseAnimation::SimpleProgressivePhrase:
                return {"short_phrase_simple_progressive_phrase", "Simple Progressive Phrase",
                        "Just what I needed", 24,
                        {},
                        {animator(PhraseSelector{"word", "forward", "band"},
                                  {track("opacity", {{0, 0.2f}, {24, 1.f}}, "linear"),
                                    track("fill_blue", {{0, 1.f}, {24, 1.f}}, "linear")})},
                         {}, ShortPhraseExit::Forward, ShortPhraseDecor::None};

            // ── 11 · single word swap (one slot) ────────────────────────────
            case ShortPhraseAnimation::SingleWordSwap:
                return {"short_phrase_single_word_swap", "Single Word Swap",
                        "Intro style animation", 18,
                        {},
                        {animator(PhraseSelector{"word", "forward", "full"},
                                  {track("scale", {{0, 0.8f}, {18, 1.f}}, "out_back"),
                                   track("opacity", {{0, 0.f}, {18, 1.f}}, "linear")})},
                         {1}, ShortPhraseExit::Reverse, ShortPhraseDecor::None};

            // ── 12 · elegant character write-on ─────────────────────────────
            case ShortPhraseAnimation::CharacterWriteOn:
                return {"short_phrase_character_write_on", "Character Write On",
                        "Thanks for watching!", 24,
                        {},
                        {animator(PhraseSelector{"glyph", "forward", "reveal"},
                                  {track("opacity", {{0, 0.f}, {24, 0.f}}, "linear"),
                                   track("fill_blue", {{0, 1.f}, {24, 1.f}}, "linear")})},
                         {}, ShortPhraseExit::Wipe, ShortPhraseDecor::None};
        }
        throw std::invalid_argument("chronontemplate::definition: unknown short phrase animation");
    }

    ShortPhraseDefinition definition(ShortPhraseAnimation animation) {
        auto def = entranceDefinition(animation);
        if (def.id.rfind("short_phrase_editorial_", 0) != 0) return def;

        // A five-second sequence, not a one-second entrance with four seconds
        // of dead air. Keep reading rests before/after the second editorial beat.
        const auto layerBeat = [&](const std::string& property, float from, float rest,
                                   float middle, float landing) {
            auto authored = track(property, {{0, from}, {def.enter, rest}, {42, rest},
                                            {78, middle}, {102, landing}, {120, landing}},
                                  "in_out_cubic");
            for (auto& existing : def.tracks) {
                if (existing.property == property) { existing = std::move(authored); return; }
            }
            def.tracks.push_back(std::move(authored));
        };
        for (auto& t : def.tracks) {
            if (t.property == "opacity") t = track("opacity", {{0, 0.f}, {8, 1.f}, {120, 1.f}}, "linear");
        }
        switch (animation) {
            case ShortPhraseAnimation::EditorialBaselineRise:
                layerBeat("position_y", 92.f, 0.f, -20.f, 0.f);
                break;
            case ShortPhraseAnimation::EditorialSideGlide:
                layerBeat("position_x", -84.f, 0.f, 18.f, 0.f);
                break;
            case ShortPhraseAnimation::EditorialTrackingClose:
                layerBeat("position_x", -36.f, 0.f, 8.f, 0.f);
                def.textAnimators.front().properties.front() = track(
                    "tracking", {{0, 18.f}, {20, 0.f}, {42, 0.f}, {78, 3.f}, {102, 0.f}, {120, 0.f}}, "in_out_cubic");
                break;
            case ShortPhraseAnimation::EditorialFocusResolve:
                layerBeat("position_x", 96.f, 0.f, -16.f, 0.f);
                def.textAnimators.front().properties.front() = track(
                    "blur", {{0, 18.f}, {18, 0.f}, {42, 0.f}, {78, 3.f}, {102, 0.f}, {120, 0.f}}, "in_out_cubic");
                break;
            case ShortPhraseAnimation::EditorialUnderlineDraw:
                layerBeat("position_y", 48.f, 0.f, -12.f, 0.f);
                def.accents.front().tracks.front() = track(
                    "scale_x", {{0, 0.f}, {8, 0.f}, {20, 1.f}, {42, 1.f}, {78, 0.8f}, {102, 1.f}, {120, 1.f}}, "in_out_cubic");
                def.accents.front().tracks.push_back(track(
                    "position_x", {{0, 0.f}, {42, 0.f}, {78, 36.f}, {102, 0.f}, {120, 0.f}}, "in_out_cubic"));
                break;
            case ShortPhraseAnimation::EditorialRuleHandoff:
                layerBeat("position_x", 110.f, 0.f, -24.f, 0.f);
                def.accents.front().tracks.front() = track(
                    "position_x", {{0, -760.f}, {20, -610.f}, {42, -610.f}, {78, 610.f}, {102, 520.f}, {120, 520.f}}, "in_out_cubic");
                break;
            case ShortPhraseAnimation::EditorialGlyphCurtain:
                layerBeat("position_y", 74.f, 0.f, 24.f, 0.f);
                layerBeat("scale", 0.94f, 1.f, 0.98f, 1.f);
                break;
            case ShortPhraseAnimation::EditorialContrastSweep:
                layerBeat("scale", 0.94f, 1.f, 1.025f, 1.f);
                def.textAnimators.push_back(animator(PhraseSelector{"glyph", "forward", "full"},
                    {track("fill_blue", {{0, 0.f}, {42, 0.f}, {78, 0.35f}, {102, 0.f}, {120, 0.f}}, "in_out_cubic")}));
                break;
            case ShortPhraseAnimation::EditorialQuietZoom:
                layerBeat("scale", 0.78f, 1.f, 1.04f, 1.f);
                break;
            case ShortPhraseAnimation::EditorialLiftAndRule:
                layerBeat("position_y", -78.f, 0.f, 18.f, 0.f);
                def.accents.front().tracks.front() = track(
                    "scale_x", {{0, 0.15f}, {22, 1.f}, {42, 1.f}, {78, 1.2f}, {102, 1.f}, {120, 1.f}}, "in_out_cubic");
                break;
            default: break;
        }
        return def;
    }

    ShortPhraseDecorDefinition shortPhraseDecor(ShortPhraseDecor decor) {
        switch (decor) {
            case ShortPhraseDecor::StarBumper:
                return {"short_phrase.decor.star_bumper", "four_point_star",
                        {track("rotation", {{0, 0.f}, {24, 110.f}}, "in_out_sine"),
                         track("scale", {{0, 0.8f}, {12, 1.3f}, {24, 0.7f}}, "in_out_sine"),
                         track("opacity", {{0, 0.f}, {6, 1.f}, {24, 0.f}}, "linear")}};
            case ShortPhraseDecor::None:
                break;
        }
        throw std::invalid_argument("chronontemplate::shortPhraseDecor: no decor for this id");
    }

    std::size_t shortPhraseWordCount(const std::string& phrase) {
        std::size_t count = 0;
        bool inWord = false;
        for (const char c : phrase) {
            if (std::isspace(static_cast<unsigned char>(c))) {
                inWord = false;
            } else if (!inWord) {
                inWord = true;
                ++count;
            }
        }
        return count;
    }

    ShortPhraseTiming shortPhraseTiming(int wordCount) {
        if (wordCount <= 2) return ShortPhraseTiming{wordCount, 36, 48, 9, 24, 12};
        if (wordCount <= 4) return ShortPhraseTiming{wordCount, 45, 60, 12, 30, 12};
        return ShortPhraseTiming{wordCount, 54, 75, 15, 36, 15};
    }

    std::vector<ShortPhraseAnimation> shortPhraseSuggestions(int wordCount) {
        if (wordCount <= 0 || wordCount > 7) return {};
        if (wordCount == 1) {
            return {ShortPhraseAnimation::ScaleSettleWord,
                    ShortPhraseAnimation::WordMaskSequence,
                    ShortPhraseAnimation::EditorialQuietZoom,
                    ShortPhraseAnimation::EditorialFocusResolve};
        }
        if (wordCount <= 3) {
            return {ShortPhraseAnimation::CharacterTrackingReveal,
                    ShortPhraseAnimation::WordMaskSequence,
                    ShortPhraseAnimation::SingleWordSwap,
                    ShortPhraseAnimation::EditorialTrackingClose,
                    ShortPhraseAnimation::EditorialUnderlineDraw,
                    ShortPhraseAnimation::EditorialBaselineRise};
        }
        if (wordCount <= 5) {
            return {ShortPhraseAnimation::WordCascadeSentence,
                    ShortPhraseAnimation::SemanticTwoLine,
                    ShortPhraseAnimation::PhraseBuildFocus,
                    ShortPhraseAnimation::CharacterCascadeShapes,
                    ShortPhraseAnimation::EditorialSideGlide,
                    ShortPhraseAnimation::EditorialRuleHandoff,
                    ShortPhraseAnimation::EditorialLiftAndRule};
        }
        return {ShortPhraseAnimation::SimpleProgressivePhrase,
                ShortPhraseAnimation::SemanticChainCurve,
                ShortPhraseAnimation::ShapePhraseWipe,
                ShortPhraseAnimation::EditorialGlyphCurtain,
                ShortPhraseAnimation::EditorialContrastSweep};
    }

}// namespace chronontemplate
