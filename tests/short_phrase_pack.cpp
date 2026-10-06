#include "chronontemplate/short_phrases/ShortPhrasePack.hpp"

#include "motion_check.hpp"

#include <set>
#include <stdexcept>
#include <string>

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

    void theTwelveArchetypesAreWellFormed() {
        section("twelve short-phrase archetypes");
        const std::vector<ShortPhraseAnimation> animations = shortPhraseAnimations();
        check(animations.size() == 22, "the pack preserves twelve originals and adds ten editorial archetypes");

        std::set<std::string> ids;
        bool anyLayer = false;
        bool anyGlyph = false;
        bool anyWord = false;
        bool anyBand = false;
        bool anyReveal = false;
        bool anyEmphasis = false;
        bool anyDecor = false;
        for (const ShortPhraseAnimation animation : animations) {
            const std::string id = name(animation);
            check(ids.insert(id).second, "short-phrase ids are unique");
            check(id.rfind("short_phrase_", 0) == 0, "wire ids carry the short_phrase_ prefix");
            const ShortPhraseDefinition def = definition(animation);
            check(def.id == id, "the definition publishes the same id as its enumerator");
            check(!def.title.empty(), "each archetype carries a human title");
            check(!def.phrase.empty(), "each archetype carries a showcase phrase");
            check(def.enter > 0 && def.enter <= 36,
                  "each short-phrase entrance stays under ~1.2 s");
            check(!def.tracks.empty() || !def.textAnimators.empty(),
                  "each archetype authors motion on the layer or on text units");

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
                check(animator.selector.unit == "glyph" || animator.selector.unit == "word",
                      "text animators select glyph or word units (the GPU-lowerable profiles)");
                check(animator.selector.window == "full" || animator.selector.window == "reveal" ||
                              animator.selector.window == "reveal_soft" ||
                              animator.selector.window == "band",
                      "selector windows stay inside the GPU-lowerable set");
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
            check(!closesOpacity || hasReveal, (def.id + " arrives at full opacity").c_str());

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
    }

    void theCleanEditorialRecipesAreStable() {
        section("ten clean editorial recipes");
        int count = 0;
        std::set<std::string> motions;
        for (const auto animation : shortPhraseAnimations()) {
            const auto def = definition(animation);
            if (def.id.rfind("short_phrase_editorial_", 0) != 0) continue;
            ++count;
            check(def.decor == ShortPhraseDecor::None, "editorial phrases carry no bumper");
            check(shortPhraseWordCount(def.phrase) <= 7, "editorial samples stay short");
            check(def.enter <= 30, "editorial entrances land within one second");
            bool middleBeat = false;
            for (const auto& t : def.tracks) {
                for (const auto& k : t.keyframes) {
                    if (k.frame > 42 && k.frame < 120 && k.value != t.keyframes.back().value) middleBeat = true;
                }
                check(t.keyframes.back().frame >= 120, "editorial layer tracks carry the full sequence");
            }
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
        check(count == 10, "exactly ten editorial recipes");
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
        check(one.minFrames == 36 && one.maxFrames == 48, "1–2 words last 1.2–1.6 s");
        const ShortPhraseTiming three = shortPhraseTiming(3);
        check(three.minFrames == 45 && three.maxFrames == 60, "3–4 words last 1.5–2.0 s");
        const ShortPhraseTiming six = shortPhraseTiming(6);
        check(six.minFrames == 54 && six.maxFrames == 75, "5–7 words last 1.8–2.5 s");

        int previousMin = 0;
        for (int words = 1; words <= 7; ++words) {
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
        for (int words = 1; words <= 7; ++words) {
            const std::vector<ShortPhraseAnimation> picks = shortPhraseSuggestions(words);
            check(!picks.empty(), "every short phrase length has at least one recipe");
            std::set<std::string> seen;
            for (const ShortPhraseAnimation pick : picks) {
                const std::string id = name(pick);  // throws if the pick is not a real recipe
                check(seen.insert(id).second, "a suggestion list never repeats a recipe");
            }
        }
        check(shortPhraseSuggestions(0).empty(), "zero words is outside the family");
        check(shortPhraseSuggestions(8).empty(), "more than seven words is outside the family");
        const std::vector<ShortPhraseAnimation> single = shortPhraseSuggestions(1);
        check(single.front() == ShortPhraseAnimation::ScaleSettleWord,
              "a single word suggests the scale settle");
    }

}// namespace

int main() {
    theTwelveArchetypesAreWellFormed();
    theCleanEditorialRecipesAreStable();
    theEditorialExtrasAreStable();
    theStarBumperIsASeparateDecorElement();
    theTimingEnvelopeMatchesTheEditorialRules();
    theSuggestionsCoverTheShortPhraseRange();
    return chrononmotion_test::report();
}
