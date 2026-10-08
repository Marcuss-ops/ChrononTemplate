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
        check(animations.size() == 50, "the pack preserves twelve original recipes, adds thirteen editorial recipes, and registers twenty-five product recipes");

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
            if (id.rfind("short_phrase_product_", 0) == 0 &&
                id != "short_phrase_product_line_by_line_slide") {
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
                    if (animator.properties[j].property == "character_offset") {
                        const auto& keys = animator.properties[j].keyframes;
                        check(keys.size() >= 2 && keys.front().value == 8.f && keys.back().value == 0.f,
                              "decrypted-text offset moves from an encoded state to the source text");
                    }
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

        const std::vector<std::string> reactIds{
                "short_phrase_product_masked_heading",
                "short_phrase_product_split_flap_text",
                "short_phrase_product_warp_text",
                "short_phrase_product_fold_text",
                "short_phrase_product_decrypted_text",
                "short_phrase_product_scroll_reveal",
                "short_phrase_product_scrambled_text"};
        for (const std::string& reactId : reactIds) {
            const auto found = definitions.find(reactId);
            check(found != definitions.end(), (reactId + " is registered").c_str());
            if (found == definitions.end()) continue;
            const auto& note = found->second.adaptation_note;
            check(note.find("not represented") != std::string::npos ||
                          note.find("native eased entrance") != std::string::npos,
                  (reactId + " documents effects/interaction that cannot be carried over").c_str());
            check(found->second.enter == 90,
                  (reactId + " reaches its native frame-based reveal at frame 90").c_str());
            if (reactId == "short_phrase_product_decrypted_text") {
                check(found->second.textOverlays.size() == 10,
                      "decrypted text includes nine encoded snapshots and one resolved overlay");
                if (!found->second.textOverlays.empty())
                    check(found->second.textOverlays.back().text == "DECODE THE SIGNAL",
                          "the decrypted text ends with its exact target string");
            }
        }
    }

    void theCleanEditorialRecipesAreStable() {
        section("clean editorial recipes");
        int count = 0;
        std::set<std::string> motions;
        for (const auto animation : shortPhraseAnimations()) {
            const auto def = definition(animation);
            if (def.id.rfind("short_phrase_editorial_", 0) != 0) continue;
            ++count;
            check(def.decor == ShortPhraseDecor::None, "editorial phrases carry no bumper");
            check(shortPhraseWordCount(def.phrase) <= 7, "editorial samples stay short");
            check(def.enter == 90, "editorial entrance lands at the documented three-second reveal");
            bool middleBeat = false;
            bool sequenceTrack = false;
            for (const auto& t : def.tracks) {
                everyKeyframeListIsAValidEntrance(t, def.id + "." + t.property);
                sequenceTrack = sequenceTrack || t.keyframes.back().frame >= 120;
                for (const auto& k : t.keyframes) {
                    if (k.frame > 42 && k.frame < 120 && k.value != t.keyframes.back().value) middleBeat = true;
                }
            }
            check(sequenceTrack, "every editorial recipe includes a track continuing into the second beat");
            check(middleBeat, "every editorial recipe has a visible second motion beat");
            std::string fingerprint;
            for (const auto& t : def.tracks) {
                fingerprint += t.property + std::to_string(t.keyframes.front().value);
            }
            for (const auto& a : def.textAnimators) {
                fingerprint += a.selector.window;
                for (const auto& t : a.properties) fingerprint += t.property;
            }
            for (const auto& a : def.accents) {
                fingerprint += a.id;
                check(a.width > 0.f && a.height > 0.f, "editorial accents have positive dimensions");
                for (const auto& t : a.tracks) everyKeyframeListIsAValidEntrance(t, def.id + "." + a.id);
            }
            check(motions.insert(fingerprint).second, "each editorial recipe has distinct motion");
        }
        check(count == 13, "exactly thirteen editorial recipes, including the three Claude-inspired looks");

        std::size_t productCount = 0;
        for (const auto animation : shortPhraseAnimations()) {
            if (std::string(name(animation)).rfind("short_phrase_product_", 0) == 0) ++productCount;
        }
        check(productCount == 25, "the product family contains fourteen existing recipes, seven text adaptations, and four native visual adaptations");
    }

    void claudeInspiredShortPhrasesUseTheWhiteEditorialPalette() {
        section("Claude-inspired white editorial short phrases");
        const std::vector<ShortPhraseAnimation> animations{
                ShortPhraseAnimation::EditorialPromptResponse,
                ShortPhraseAnimation::EditorialDiffPatch,
                ShortPhraseAnimation::EditorialTerminalFocus};
        for (const auto animation : animations) {
            const auto def = definition(animation);
            check(def.white_background, "Claude-inspired recipes declare the pure-white palette");
            check(def.id.rfind("short_phrase_editorial_claude_", 0) == 0,
                  "Claude-inspired recipe ids are stable and editorial");
            check(!def.textAnimators.empty(), "each new recipe uses native text animation");
        }
        const auto patch = definition(ShortPhraseAnimation::EditorialDiffPatch);
        check(patch.textAnimators.size() >= 2 &&
                  patch.textAnimators.back().properties.front().property == "fill_orange",
              "Diff / Patch accents a selected word in orange");
        check(patch.textAnimators.back().selector.window == "pick:2:3" &&
                  shortPhraseWordCount(patch.phrase) == 3,
              "Diff / Patch accent selector targets a valid word");
        const auto terminal = definition(ShortPhraseAnimation::EditorialTerminalFocus);
        check(terminal.phrase == "npx chronon render" && terminal.white_background,
              "Terminal Focus uses a CLI phrase on the white-paper palette");
    }

    void theEditorialExtrasAreStable() {
        section("short-phrase editorial extras");
        check(definition(ShortPhraseAnimation::SemanticChainCurve).exit == ShortPhraseExit::ArcDissolve,
              "the semantic chain folds away on an arc");
        check(definition(ShortPhraseAnimation::ShapePhraseWipe).decor == ShortPhraseDecor::StarBumper,
              "the shape wipe carries the star bumper");
        check(definition(ShortPhraseAnimation::CharacterCascadeShapes).decor == ShortPhraseDecor::StarBumper,
              "the character cascade carries the star bumper");
        check(std::string(name(ShortPhraseAnimation::WordCascadeSentence)) ==
                      "short_phrase_word_cascade_sentence",
              "word cascade has a stable wire name");
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
        const std::vector<ShortPhraseAnimation> adapted{
                ShortPhraseAnimation::ProductMaskedHeading,
                ShortPhraseAnimation::ProductSplitFlapText,
                ShortPhraseAnimation::ProductWarpText,
                ShortPhraseAnimation::ProductFoldText,
                ShortPhraseAnimation::ProductDecryptedText,
                ShortPhraseAnimation::ProductScrollReveal,
                ShortPhraseAnimation::ProductScrambledText};
        for (const auto animation : adapted) {
            const auto def = definition(animation);
            check(def.adaptation_note.find("not represented") != std::string::npos ||
                          def.adaptation_note.find("no scroll container") != std::string::npos ||
                          def.adaptation_note.find("replaces viewport scrubbing") != std::string::npos ||
                          def.adaptation_note.find("no runtime trigger") != std::string::npos ||
                          def.adaptation_note.find("native eased entrance") != std::string::npos,
                  "React interactivity/effects are explicitly documented as adaptations");
            check(def.enter == 90, "adapted phrase effects use the three-second showcase reveal");
            check(definition(animation).id == name(animation), "each React effect has a stable catalog id");
            if (animation == ShortPhraseAnimation::ProductDecryptedText) {
                check(def.textOverlays.size() == 10,
                      "decrypted text contains nine fixed scramble stages followed by its resolved phrase");
                check(def.textOverlays.back().text == "DECODE THE SIGNAL",
                      "decrypted text ends on the exact resolved phrase");
            }
        }
        const std::vector<ShortPhraseAnimation> single = shortPhraseSuggestions(1);
        check(single.front() == ShortPhraseAnimation::ScaleSettleWord,
              "the default single-word suggestion remains scale settle");
        check(std::find(single.begin(), single.end(), ShortPhraseAnimation::EditorialTerminalFocus) != single.end(),
              "one-word terminal phrases suggest the terminal-focus recipe");
    }

    void theFourNativeVisualAdaptationsAreRegistered() {
        section("four native visual adaptations");
        const std::vector<ShortPhraseAnimation> animations{
                ShortPhraseAnimation::ProductGlareHover,
                ShortPhraseAnimation::ProductGlowCursor,
                ShortPhraseAnimation::ProductGradualBlur,
                ShortPhraseAnimation::ProductShapeBlur};
        for (const ShortPhraseAnimation animation : animations) {
            const auto def = definition(animation);
            check(def.enter == 90, "each adapted visual recipe uses the authored three-second reveal");
            check(def.adaptation_note.find("not represented") != std::string::npos,
                  "each recipe documents browser-only behavior");
            bool hasNativeMotion = !def.tracks.empty() || !def.textAnimators.empty() || !def.accents.empty();
            for (const auto& overlay : def.textOverlays)
                hasNativeMotion = hasNativeMotion || !overlay.tracks.empty() || !overlay.textAnimators.empty();
            check(hasNativeMotion, "each adapted effect has native motion");
            for (const auto& track : def.tracks)
                everyKeyframeListIsAValidEntrance(track, def.id + ".track");
            for (const auto& animator : def.textAnimators)
                for (const auto& track : animator.properties)
                    everyKeyframeListIsAValidEntrance(track, def.id + ".text");
            for (const auto& accent : def.accents) {
                check(accent.width > 0.f && accent.height > 0.f,
                      "native accents have positive dimensions");
                for (const auto& track : accent.tracks)
                    everyKeyframeListIsAValidEntrance(track, def.id + ".accent");
            }
        }
    }

}// namespace

int main() {
    theShortPhraseArchetypesAreWellFormed();
    theCleanEditorialRecipesAreStable();
    theEditorialExtrasAreStable();
    theStarBumperIsASeparateDecorElement();
    theTimingEnvelopeMatchesTheEditorialRules();
    theSuggestionsCoverTheShortPhraseRange();
    theFourNativeVisualAdaptationsAreRegistered();
    claudeInspiredShortPhrasesUseTheWhiteEditorialPalette();
    return chrononmotion_test::report();
}
