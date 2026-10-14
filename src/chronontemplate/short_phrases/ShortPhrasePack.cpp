#include "chronontemplate/short_phrases/ShortPhrasePack.hpp"
#include "ModernShortPhraseRecipes.hpp"

#include <cctype>
#include <cmath>
#include <stdexcept>
#include <utility>

namespace chronontemplate {

    namespace {

        PhraseTrack track(const std::string& property, std::vector<PhraseKeyframe> keys,
                          const std::string& easing = "out_cubic") {
            return PhraseTrack{property, easing, std::move(keys)};
        }

        PhraseTrack fadeIn(int enter, int over) {
            (void)over;
            return track("opacity", {{0, 0.f}, {enter, 1.f}}, "linear");
        }

        PhraseTextAnimator animator(PhraseSelector selector, std::vector<PhraseTrack> properties) {
            return PhraseTextAnimator{std::move(selector), std::move(properties)};
        }

    }// namespace

    const std::vector<ShortPhraseRecipeSpec>& shortPhraseRecipeSpecs() noexcept {
        static const std::vector<ShortPhraseRecipeSpec> specs{
#define SHORT_PHRASE_RECIPE(key, id, family, min_words, max_words, suggested, caption_target, runtime_enabled) \
            {ShortPhraseAnimation::key, id, family, min_words, max_words, suggested, \
             caption_target ? std::vector<const char*>{"short_phrase", "caption"} \
                            : std::vector<const char*>{"short_phrase"}, runtime_enabled},
#include "chronontemplate/short_phrases/ShortPhraseRecipes.def"
#undef SHORT_PHRASE_RECIPE
        };
        return specs;
    }

    const char* name(ShortPhraseAnimation animation) {
        for (const auto& spec : shortPhraseRecipeSpecs()) {
            if (spec.animation == animation) return spec.id;
        }
        throw std::invalid_argument("chronontemplate::name: unknown short phrase animation");
    }

    std::vector<ShortPhraseAnimation> shortPhraseAnimations() {
        std::vector<ShortPhraseAnimation> animations;
        for (const auto& spec : shortPhraseRecipeSpecs()) animations.push_back(spec.animation);
        return animations;
    }

    static ShortPhraseDefinition entranceDefinition(ShortPhraseAnimation animation) {
        using namespace modern_short_phrase;
        switch (animation) {
            case ShortPhraseAnimation::EditorialTerminalFocus: {
                ShortPhraseDefinition def{name(animation), "Terminal Focus", "npx chronon render", 30,
                    {track("position_x", {{0, -22.f}, {22, 2.f}, {30, 0.f}}), fadeIn(30, 6)},
                    {animator(PhraseSelector{"glyph", "forward", "reveal_soft"},
                        {track("opacity", {{0, 0.f}, {30, 0.f}}, "linear"),
                         track("tracking", {{0, 5.f}, {30, 0.f}})})},
                    {}, ShortPhraseExit::Reverse, ShortPhraseDecor::None, {}, 110.f};
                def.white_background = true;
                return def;
            }
            case ShortPhraseAnimation::ProductHardMaskSlideUp: return blurOutUp();
            case ShortPhraseAnimation::ProductKineticBlurIn: return bottomUpLetters();
            case ShortPhraseAnimation::ProductWordStagger: return focusBlurResolve();
            case ShortPhraseAnimation::ProductTrackingPullIn: return kineticCenterBuild();
            case ShortPhraseAnimation::ProductSubtitleDissolve: return perWordRise();
            case ShortPhraseAnimation::ProductDualToneReveal: return perspectiveMarquee();
            case ShortPhraseAnimation::ProductRadialExpansion: return strikethroughReplace();
            case ShortPhraseAnimation::ProductDepthParallax: return textMatchCut();
            case ShortPhraseAnimation::ProductGlintPass: return textShimmer();
            case ShortPhraseAnimation::ProductDigitalAssembly: return chromaticFringeTitle();
            case ShortPhraseAnimation::ProductMaskedHeading: return maskedHeading();
            case ShortPhraseAnimation::ProductSplitFlapText: return splitFlapText();
            case ShortPhraseAnimation::ProductScrollReveal: return scrollReveal();
            case ShortPhraseAnimation::ProductScrambledText: return scrambledText();
            case ShortPhraseAnimation::ProductGradualBlur: return gradualBlur();
            default: break;
        }
        // Authored entrance shapes in frames at 30 fps. `definition()` stretches
        // the entrance window to three seconds so character builds stay legible.
        switch (animation) {
            // These definitions were fully constructed by their dedicated cases.
            case ShortPhraseAnimation::EditorialTerminalFocus:
            case ShortPhraseAnimation::ProductMaskedHeading:
            case ShortPhraseAnimation::ProductSplitFlapText:
            case ShortPhraseAnimation::ProductScrollReveal:
            case ShortPhraseAnimation::ProductScrambledText:
            case ShortPhraseAnimation::ProductGradualBlur:
                break;
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

            case ShortPhraseAnimation::ProductHardMaskSlideUp:
                return {name(animation), "Hard Mask Slide-Up", "Designed to move", 22,
                        {track("position_y", {{0, 112.f}, {8, 42.f}, {22, 0.f}}, "out_cubic"), fadeIn(22, 5)},
                        {}, {}, ShortPhraseExit::Wipe, ShortPhraseDecor::None, {}, 112.f};
            case ShortPhraseAnimation::ProductKineticBlurIn:
                return {name(animation), "Kinetic Velocity-In", "Built for what matters", 20,
                        {track("scale", {{0, 1.08f}, {20, 1.f}}, "out_cubic"),
                         track("position_y", {{0, 22.f}, {20, 0.f}}, "out_cubic"), fadeIn(20, 5)},
                        {}, {}, ShortPhraseExit::Reverse, ShortPhraseDecor::None, {}, 100.f};
            case ShortPhraseAnimation::ProductWordStagger:
                return {name(animation), "Word-by-Word Stagger", "Move with intent", 26,
                        {fadeIn(26, 6)},
                        {animator(PhraseSelector{"word", "forward", "band"},
                                  {track("position_y", {{0, 26.f}, {26, 0.f}}, "out_cubic"),
                                   track("opacity", {{0, 0.f}, {18, 1.f}}, "linear")})},
                        {}, ShortPhraseExit::Reverse, ShortPhraseDecor::None, {}, 116.f};
            case ShortPhraseAnimation::ProductTrackingPullIn:
                return {name(animation), "Tracking Pull-In", "Precision in every detail", 24,
                        {fadeIn(24, 8)},
                        {animator(PhraseSelector{"glyph", "forward", "full"},
                                  {track("tracking", {{0, 24.f}, {24, 0.f}}, "out_cubic"),
                                   track("opacity", {{0, 0.15f}, {24, 1.f}}, "linear")})},
                        {}, ShortPhraseExit::Reverse, ShortPhraseDecor::None, {}, 92.f};
            case ShortPhraseAnimation::ProductSubtitleDissolve:
                return {name(animation), "Micro-Float Dissolve", "Made for the moment", 8,
                        {track("position_y", {{0, 7.f}, {8, 0.f}}, "out_cubic"), fadeIn(8, 5)},
                        {}, {}, ShortPhraseExit::Reverse, ShortPhraseDecor::None, {}, 86.f, true};
            case ShortPhraseAnimation::ProductDualToneReveal:
                return {name(animation), "Dual-Tone Accent", "Less noise. More meaning.", 20,
                        {track("scale", {{0, 0.99f}, {16, 1.03f}, {20, 1.f}}), fadeIn(20, 6)},
                        {animator(PhraseSelector{"word", "forward", "band"},
                                  {track("fill_gray", {{0, 1.f}, {20, 1.f}}, "linear"),
                                   track("opacity", {{0, 0.45f}, {20, 1.f}}, "linear")})},
                        {2}, ShortPhraseExit::Reverse, ShortPhraseDecor::None, {}, 106.f};
            case ShortPhraseAnimation::ProductRadialExpansion:
                return {name(animation), "Soft Radial Expansion", "Focus on what matters", 22,
                        {fadeIn(22, 5)}, {}, {}, ShortPhraseExit::Wipe, ShortPhraseDecor::None, {}, 98.f};
            case ShortPhraseAnimation::ProductDepthParallax:
                return {name(animation), "Directional Depth Parallax", "Clarity\nwith purpose", 24,
                        {track("position_x", {{0, -38.f}, {12, 0.f}, {24, 0.f}}, "out_cubic"),
                         track("position_y", {{0, 24.f}, {24, 0.f}}, "out_cubic"), fadeIn(24, 6)},
                        {animator(PhraseSelector{"word", "forward", "band"},
                                  {track("opacity", {{0, 0.f}, {20, 1.f}}, "linear")})},
                        {}, ShortPhraseExit::Reverse, ShortPhraseDecor::None, {}, 110.f};
            case ShortPhraseAnimation::ProductGlintPass:
                return {name(animation), "Glint / Edge Pass", "Crafted to catch the light", 20,
                        {fadeIn(20, 6)}, {}, {}, ShortPhraseExit::Reverse, ShortPhraseDecor::None, {}, 100.f};
            case ShortPhraseAnimation::ProductDigitalAssembly:
                return {name(animation), "Digital Character Assembly", "Signal becomes meaning", 90,
                        {fadeIn(90, 8)},
                        {animator(PhraseSelector{"glyph", "forward", "reveal_soft"},
                                  {track("position_x", {{0, -28.f}, {90, 0.f}}, "out_cubic"),
                                   track("position_y", {{0, 36.f}, {90, 0.f}}, "out_cubic"),
                                   track("scale", {{0, 0.78f}, {90, 1.f}}, "out_cubic"),
                                   track("tracking", {{0, 10.f}, {90, 0.f}}, "out_cubic"),
                                   track("opacity", {{0, 0.f}, {90, 1.f}}, "linear"),
                                   track("fill_blue", {{0, 1.f}, {60, 0.45f}, {90, 0.f}}, "out_cubic")})},
                        {}, ShortPhraseExit::Reverse, ShortPhraseDecor::None, {}, 108.f};

            // ── 01 · scale settle (1 strong word) ──────────────────────────
            case ShortPhraseAnimation::ShapePhraseWipe:
                return {"short_phrase_shape_phrase_wipe", "Shape Phrase Wipe",
                        "It's really easy to manage.", 18,
                        {fadeIn(18, 10)},
                        {animator(PhraseSelector{"glyph", "forward", "reveal_soft"},
                                  {track("opacity", {{0, 0.f}, {18, 0.f}}, "linear")})},
                        {}, ShortPhraseExit::Wipe, ShortPhraseDecor::StarBumper, {}, 0.f, true};

            // ── 03 · semantic two-line highlight ────────────────────────────
            case ShortPhraseAnimation::CharacterTrackingReveal:
                return {"short_phrase_character_tracking_reveal", "Character Tracking Reveal",
                        "more expensive", 20,
                        {},
                        {animator(PhraseSelector{"glyph", "forward", "reveal"},
                                  {track("opacity", {{0, 0.f}, {20, 1.f}}, "linear"),
                                   track("tracking", {{0, 20.f}, {20, 0.f}}, "out_cubic"),
                                   track("position_x", {{0, 8.f}, {20, 0.f}}, "out_cubic")})},
                        {}, ShortPhraseExit::Wipe, ShortPhraseDecor::None};

            // ── burst · glyphs spring out of the tracking and settle ─────────
            case ShortPhraseAnimation::BurstReveal:
                return {"short_phrase_burst", "Burst Reveal",
                        "Boom. Instant impact.", 24,
                        {},
                        {animator(PhraseSelector{"glyph", "forward", "reveal"},
                                  {track("opacity", {{0, 0.f}, {8, 1.f}, {24, 1.f}}, "linear"),
                                   track("tracking", {{0, 40.f}, {24, 0.f}}, "out_cubic"),
                                   track("position_y", {{0, -30.f}, {24, 0.f}}, "out_cubic")})},
                        {}, ShortPhraseExit::Scatter, ShortPhraseDecor::None};

            // ── 06 · word mask sequence (one slot, one word at a time) ──────
            case ShortPhraseAnimation::CharacterCascadeShapes:
                return {"short_phrase_character_cascade_shapes", "Character Cascade Shapes",
                        "Really smooth.", 21,
                        {},
                        {animator(PhraseSelector{"glyph", "forward", "reveal"},
                                  {track("opacity", {{0, 0.f}, {21, 0.f}}, "linear")})},
                         {}, ShortPhraseExit::Scatter, ShortPhraseDecor::StarBumper, {}, 0.f, true};

            // ── 08 · word cascade sentence ──────────────────────────────────
}
        throw std::invalid_argument("chronontemplate::definition: unknown short phrase animation");
    }

    ShortPhraseDefinition definition(ShortPhraseAnimation animation) {
        auto def = entranceDefinition(animation);
        const bool editorial = def.id.rfind("short_phrase_editorial_", 0) == 0;
        const bool product = def.id.rfind("short_phrase_product_", 0) == 0;
        if (product) return def; // product timings are authored to their source beat; do not stretch them
        if (!editorial) {
            const int authoredEnter = def.enter;
            constexpr int kReadableEnterFrames = 90; // 3 s @ 30 fps
            if (authoredEnter > 0 && authoredEnter < kReadableEnterFrames) {
                const float stretch = static_cast<float>(kReadableEnterFrames) / authoredEnter;
                const auto stretchTracks = [&](std::vector<PhraseTrack>& tracks) {
                    for (auto& motion : tracks) {
                        int previous = -1;
                        for (auto& key : motion.keyframes) {
                            if (key.frame <= authoredEnter) {
                                key.frame = static_cast<int>(std::round(key.frame * stretch));
                            }
                            if (key.frame <= previous) key.frame = previous + 1;
                            previous = key.frame;
                        }
                    }
                };
                stretchTracks(def.tracks);
                for (auto& animator : def.textAnimators) stretchTracks(animator.properties);
                for (auto& accent : def.accents) stretchTracks(accent.tracks);
                def.enter = kReadableEnterFrames;
            }
            return def;
        }

        // A staged sequence with a readable entrance and secondary editorial beat.
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
            if (t.property == "opacity") t = track("opacity", {{0, 0.f}, {90, 1.f}, {120, 1.f}}, "linear");
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
            case ShortPhraseAnimation::EditorialTerminalFocus:
                layerBeat("position_x", 20.f, 0.f, -6.f, 0.f);
                break;
            // These definitions do not use the legacy editorial sequence body.
            case ShortPhraseAnimation::ProductMaskedHeading:
            case ShortPhraseAnimation::ProductSplitFlapText:
            case ShortPhraseAnimation::ProductScrollReveal:
            case ShortPhraseAnimation::ProductScrambledText:
            case ShortPhraseAnimation::ProductGradualBlur:
            case ShortPhraseAnimation::ShapePhraseWipe:
            case ShortPhraseAnimation::BurstReveal:
            case ShortPhraseAnimation::CharacterTrackingReveal:
            case ShortPhraseAnimation::CharacterCascadeShapes:
            case ShortPhraseAnimation::ProductHardMaskSlideUp:
            case ShortPhraseAnimation::ProductKineticBlurIn:
            case ShortPhraseAnimation::ProductWordStagger:
            case ShortPhraseAnimation::ProductTrackingPullIn:
            case ShortPhraseAnimation::ProductSubtitleDissolve:
            case ShortPhraseAnimation::ProductDualToneReveal:
            case ShortPhraseAnimation::ProductRadialExpansion:
            case ShortPhraseAnimation::ProductDepthParallax:
            case ShortPhraseAnimation::ProductGlintPass:
            case ShortPhraseAnimation::ProductDigitalAssembly:
                break;
            default: break;
        }
        def.enter = 90; // the editorial sequence continues its second beat through frame 120
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
        if (wordCount <= 2) return ShortPhraseTiming{wordCount, 180, 210, 90, 105, 15};
        if (wordCount <= 4) return ShortPhraseTiming{wordCount, 195, 210, 90, 105, 15};
        return ShortPhraseTiming{wordCount, 210, 210, 90, 105, 15};
    }

        std::vector<ShortPhraseAnimation> shortPhraseSuggestions(int wordCount) {
        if (wordCount <= 0 || wordCount > 5) return {};
        std::vector<ShortPhraseAnimation> suggestions;
        for (const auto& spec : shortPhraseRecipeSpecs()) {
            if (spec.runtime_enabled && spec.suggested && wordCount >= spec.min_words && wordCount <= spec.max_words) {
                suggestions.push_back(spec.animation);
            }
        }
        return suggestions;
    }

}// namespace chronontemplate
