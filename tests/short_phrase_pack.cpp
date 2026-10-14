#include "chronontemplate/short_phrases/ShortPhrasePack.hpp"

#include "motion_check.hpp"

#include <algorithm>
#include <set>
#include <stdexcept>
#include <string>
#include <unordered_map>

using namespace chronontemplate;
using chrononmotion_test::check;
using chrononmotion_test::section;

namespace {

    void everyKeyframeListIsAValidEntrance(const PhraseTrack& track, const std::string& where) {
        check(!track.property.empty(), (where + " names a property").c_str());
        check(track.keyframes.size() >= 2, (where + " has at least two keyframes").c_str());
        if (track.keyframes.empty()) return;
        check(track.keyframes.front().frame == 0, (where + " starts at frame 0").c_str());
        int previous = -1;
        bool increasing = true;
        for (const PhraseKeyframe& key : track.keyframes) {
            if (key.frame <= previous) increasing = false;
            previous = key.frame;
        }
        check(increasing, (where + " keyframe frames are strictly increasing").c_str());
    }

    void theShortPhraseArchetypesAreWellFormed() {
        section("short-phrase archetypes");
        const std::vector<ShortPhraseAnimation> animations = shortPhraseAnimations();
        check(animations.size() == 27, "the pack exposes the 27 short-phrase recipes (typewriter removed, burst kept)");

        std::set<std::string> ids;
        bool anyLayer = false;
        bool anyGlyph = false;
        bool anyWord = false;
        bool anyBand = false;
        bool anyReveal = false;
        bool anyEmphasis = false;
        bool anyDecor = false;
        std::unordered_map<std::string, ShortPhraseDefinition> definitions;
        for (const ShortPhraseAnimation animation : animations) {
            const std::string id = name(animation);
            check(ids.insert(id).second, "short-phrase ids are unique");
            check(id.rfind("short_phrase_", 0) == 0, "wire ids carry the short_phrase_ prefix");
            const ShortPhraseDefinition def = definition(animation);
            definitions.emplace(id, def);
            check(def.id == id, "the definition publishes the same id as its enumerator");
            check(!def.title.empty(), "each archetype carries a human title");
            check(!def.phrase.empty(), "each archetype carries a showcase phrase");
            if (id.rfind("short_phrase_product_", 0) == 0) {
                check(shortPhraseWordCount(def.phrase) <= 5,
                      "product short-phrase showcase text stays inside the 1..5-word range");
            }
            check(def.enter > 0 && def.enter < 210,
                  "each short-phrase entrance lands inside the showcase clip");
            bool hasMotion = !def.tracks.empty() || !def.textAnimators.empty();
            for (const auto& overlay : def.textOverlays) {
                hasMotion = hasMotion || !overlay.tracks.empty() || !overlay.textAnimators.empty();
            }
            // The perspective marquee's motion is a camera pan serialized by
            // the plan emitter, not a transform track on any individual title.
            hasMotion = hasMotion || def.id == "short_phrase_product_perspective_marquee";
            check(hasMotion, "each archetype authors motion on a layer, text unit, or native overlay");

            for (std::size_t i = 0; i < def.tracks.size(); ++i) {
                everyKeyframeListIsAValidEntrance(
                        def.tracks[i], def.id + ".tracks[" + std::to_string(i) + "]");
            }
            for (std::size_t i = 0; i < def.textAnimators.size(); ++i) {
                const PhraseTextAnimator& animator = def.textAnimators[i];
                check(!animator.properties.empty(), "each text animator authors a property");
                for (std::size_t j = 0; j < animator.properties.size(); ++j) {
                    everyKeyframeListIsAValidEntrance(
                            animator.properties[j],
                            def.id + ".textAnimators[" + std::to_string(i) + "].properties[" +
                                    std::to_string(j) + "]");
                }
                check(animator.selector.unit == "glyph" || animator.selector.unit == "word" ||
                              animator.selector.unit == "line",
                      "text animators select renderer-supported glyph, word, or line units");
                check(animator.selector.window == "full" || animator.selector.window == "reveal" ||
                              animator.selector.window == "reveal_soft" ||
                              animator.selector.window == "band" ||
                              animator.selector.window.rfind("pick:", 0) == 0,
                      "selector windows stay inside the renderer-supported set");
                anyGlyph = anyGlyph || animator.selector.unit == "glyph";
                anyWord = anyWord || animator.selector.unit == "word";
                anyBand = anyBand || animator.selector.window == "band";
                anyReveal = anyReveal || animator.selector.window == "reveal" ||
                            animator.selector.window == "reveal_soft";
            }
            if (!def.tracks.empty()) anyLayer = true;

            // A reveal window arrives visible by construction (its properties
            // hold the hidden value while the window does the ramp), so an
            // opacity that ends closed is only allowed with such a window.
            bool closesOpacity = false;
            for (const PhraseTrack& track : def.tracks) {
                if (track.property == "opacity" && track.keyframes.back().value < 1.f) closesOpacity = true;
            }
            for (const PhraseTextAnimator& animator : def.textAnimators) {
                for (const PhraseTrack& track : animator.properties) {
                    if (track.property == "opacity" && track.keyframes.back().value < 1.f) closesOpacity = true;
                }
            }
            bool hasReveal = false;
            for (const PhraseTextAnimator& animator : def.textAnimators) {
                if (animator.selector.window == "reveal" || animator.selector.window == "reveal_soft") {
                    hasReveal = true;
                }
            }
            const bool product = def.id.rfind("short_phrase_product_", 0) == 0;
            check(!closesOpacity || hasReveal || product, (def.id + " uses a valid closed-opacity reveal or product handoff").c_str());

            // The semantic emphasis must name real words of the showcase phrase.
            const std::size_t words = shortPhraseWordCount(def.phrase);
            for (const std::size_t word : def.emphasis) {
                check(word < words, (def.id + " emphasises an existing word").c_str());
            }
            if (!def.emphasis.empty()) anyEmphasis = true;
            if (def.decor != ShortPhraseDecor::None) anyDecor = true;
        }

        check(anyLayer, "the pack keeps layer-level entrances");
        check(anyGlyph && anyWord, "the pack exercises both glyph and word selectors");
        check(anyBand && anyReveal, "the pack exercises band and reveal windows");
        check(anyEmphasis, "at least one archetype carries semantic emphasis");
        check(anyDecor, "at least one archetype carries the decor star");

        const std::set<std::string> retiredIds{
                "short_phrase_editorial_claude_diff_patch",
                "short_phrase_editorial_claude_prompt_response",
                "short_phrase_editorial_lift_and_rule",
                "short_phrase_editorial_rule_handoff",
                "short_phrase_editorial_underline_draw",
                "short_phrase_phrase_build_focus",
                "short_phrase_product_decrypted_text",
                "short_phrase_product_fold_text",
                "short_phrase_product_glare_hover",
                "short_phrase_product_line_by_line_slide",
                "short_phrase_product_scramble_reveal",
                "short_phrase_product_shape_blur",
                "short_phrase_product_warp_text",
                "short_phrase_product_weight_wave",
                "short_phrase_scale_settle_word",
                "short_phrase_semantic_chain_curve",
                "short_phrase_semantic_two_line",
                "short_phrase_simple_progressive_phrase",
                "short_phrase_single_word_swap",
                "short_phrase_word_cascade_sentence",
                "short_phrase_word_mask_sequence",
                "short_phrase_character_write_on",
                "short_phrase_editorial_paper_title_card"};
        for (const auto& retiredId : retiredIds) {
            check(definitions.count(retiredId) == 0,
                  (retiredId + " is absent from the short-phrase family").c_str());
        }
    }




    void theStarBumperIsASeparateDecorElement() {
        section("short_phrase.decor.star_bumper");
        const ShortPhraseDecorDefinition star = shortPhraseDecor(ShortPhraseDecor::StarBumper);
        check(star.id == "short_phrase.decor.star_bumper", "the decor bumper has its stable id");
        check(star.shape == "four_point_star", "the bumper is the four-point star");
        check(!star.tracks.empty(), "the bumper carries motion (rotate/scale/opacity)");
        for (std::size_t i = 0; i < star.tracks.size(); ++i) {
            everyKeyframeListIsAValidEntrance(star.tracks[i],
                                              "star.tracks[" + std::to_string(i) + "]");
        }

        bool threw = false;
        try {
            (void) shortPhraseDecor(ShortPhraseDecor::None);
        } catch (const std::invalid_argument&) {
            threw = true;
        }
        check(threw, "None has no decor definition");
    }

    void theTimingEnvelopeMatchesTheEditorialRules() {
        section("short-phrase timing envelope");
        check(shortPhraseWordCount("") == 0, "an empty phrase has zero words");
        check(shortPhraseWordCount("LEAVE   YOUR  MESSAGE") == 3, "runs of spaces stay one word");

        const ShortPhraseTiming one = shortPhraseTiming(1);
        check(one.minFrames == 180 && one.maxFrames == 210 && one.inFrames == 90, "1–2 words include a three-second reveal and six-second minimum clip");
        const ShortPhraseTiming three = shortPhraseTiming(3);
        check(three.minFrames == 195 && three.maxFrames == 210 && three.inFrames == 90, "3–4 words include a three-second reveal");
        const ShortPhraseTiming six = shortPhraseTiming(6);
        check(six.minFrames == 210 && six.maxFrames == 210 && six.inFrames == 90, "5–7 words keep a three-second reveal inside a seven-second clip");

        int previousMin = 0;
        for (int words = 1; words <= 5; ++words) {
            const ShortPhraseTiming t = shortPhraseTiming(words);
            check(t.minFrames <= t.maxFrames, "the frame bracket is ordered");
            const int total = t.inFrames + t.holdFrames + t.outFrames;
            check(total >= t.minFrames && total <= t.maxFrames,
                  "in + hold + out sits inside the bracket");
            check(t.inFrames > 0 && t.holdFrames > 0 && t.outFrames > 0,
                  "every phase is positive");
            check(t.minFrames >= previousMin, "longer phrases are never shorter");
            previousMin = t.minFrames;
        }
    }

    void theSuggestionsCoverTheShortPhraseRange() {
        section("short-phrase suggestions by word count");
        for (int words = 1; words <= 5; ++words) {
            const std::vector<ShortPhraseAnimation> picks = shortPhraseSuggestions(words);
            check(!picks.empty(), "every short phrase length has at least one recipe");
            std::set<std::string> seen;
            for (const ShortPhraseAnimation pick : picks) {
                const std::string id = name(pick);  // throws if the pick is not a real recipe
                check(seen.insert(id).second, "a suggestion list never repeats a recipe");
            }
        }
        check(shortPhraseSuggestions(0).empty(), "zero words is outside the family");
        check(shortPhraseSuggestions(6).empty(), "six or more words route to Important Phrases");
        const std::set<std::string> retired{
                "short_phrase_editorial_claude_diff_patch",
                "short_phrase_editorial_claude_prompt_response",
                "short_phrase_editorial_lift_and_rule",
                "short_phrase_editorial_rule_handoff",
                "short_phrase_editorial_underline_draw",
                "short_phrase_phrase_build_focus",
                "short_phrase_product_decrypted_text",
                "short_phrase_product_fold_text",
                "short_phrase_product_glare_hover",
                "short_phrase_product_line_by_line_slide",
                "short_phrase_product_scramble_reveal",
                "short_phrase_product_shape_blur",
                "short_phrase_product_warp_text",
                "short_phrase_product_weight_wave",
                "short_phrase_scale_settle_word",
                "short_phrase_semantic_chain_curve",
                "short_phrase_semantic_two_line",
                "short_phrase_simple_progressive_phrase",
                "short_phrase_single_word_swap",
                "short_phrase_word_cascade_sentence",
                "short_phrase_word_mask_sequence",
                "short_phrase_character_write_on",
                "short_phrase_editorial_paper_title_card"};
        for (int words = 1; words <= 5; ++words) {
            for (const auto pick : shortPhraseSuggestions(words)) {
                check(!retired.count(name(pick)), "removed motions are never suggested");
            }
        }
        const std::vector<ShortPhraseAnimation> single = shortPhraseSuggestions(1);
        check(std::find(single.begin(), single.end(), ShortPhraseAnimation::EditorialTerminalFocus) != single.end(),
              "one-word terminal phrases suggest the terminal-focus recipe");
    }


}// namespace

int main() {
    theShortPhraseArchetypesAreWellFormed();
    theStarBumperIsASeparateDecorElement();
    theTimingEnvelopeMatchesTheEditorialRules();
    theSuggestionsCoverTheShortPhraseRange();
    return chrononmotion_test::report();
}
