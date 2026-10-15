#include "chronontemplate/important_phrases/highlight/HighlightPhrasePack.hpp"

#include "motion_check.hpp"

#include <algorithm>
#include <set>
#include <string>

using namespace chronontemplate;
using chrononmotion_test::check;
using chrononmotion_test::section;

namespace {

    void everyTrackIsAValidEntrance(const PhraseTrack& track, const std::string& where) {
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

    void theHighlightAnimationsValidateForLongPhrases() {
        section("Documentary Highlighting 4.0 phrase family (15 presets)");
        const auto animations = highlightPhraseAnimations();
        check(animations.size() == 15, "the Highlight family publishes exactly 15 documentary animations across 3 families");

        std::set<std::string> ids;
        for (const HighlightPhraseAnimation animation : animations) {
            const std::string id = name(animation);
            check(ids.insert(id).second, "highlight animation ids are unique");
            check(id.rfind("doc_", 0) == 0, "highlight wire ids carry the doc_ prefix");

            const PhraseAnimationDefinition def = definition(animation);
            check(def.id == id, "the definition publishes the same id as its enumerator name");
            check(!def.title.empty(), "each highlight animation carries a human title");
            check(!def.phrase.empty(), "each highlight animation carries a showcase phrase");

            int lastFrame = 0;
            for (const PhraseTrack& track : def.tracks) {
                for (const PhraseKeyframe& key : track.keyframes) lastFrame = std::max(lastFrame, key.frame);
            }
            for (const PhraseAccent& accent : def.accents) {
                for (const PhraseTrack& track : accent.tracks) {
                    for (const PhraseKeyframe& key : track.keyframes) lastFrame = std::max(lastFrame, key.frame);
                }
            }
            for (const PhraseTextAnimator& anim : def.textAnimators) {
                for (const PhraseTrack& track : anim.properties) {
                    for (const PhraseKeyframe& key : track.keyframes) lastFrame = std::max(lastFrame, key.frame);
                }
            }
            check(def.enter >= lastFrame,
                  (def.id + " entrance covers every keyframe (last frame " + std::to_string(lastFrame) +
                   ", enter " + std::to_string(def.enter) + ")").c_str());
            check(def.enter == 60, "every highlight entrance is canonical two seconds (60 frames)");
            check(!def.tracks.empty() || !def.accents.empty() || !def.textAnimators.empty(),
                  "each highlight animation authors motion, accents, or animators");

            for (std::size_t i = 0; i < def.tracks.size(); ++i) {
                everyTrackIsAValidEntrance(def.tracks[i], def.id + ".tracks[" + std::to_string(i) + "]");
            }
            std::set<std::string> accentIds;
            for (const PhraseAccent& accent : def.accents) {
                check(accent.width > 0.f && accent.height > 0.f, "highlight accents have positive dimensions");
                check(!accent.id.empty(), "highlight accents carry an id");
                check(accentIds.insert(accent.id).second,
                      (def.id + " accent ids are unique: " + accent.id).c_str());
                check(!accent.color.empty() && accent.color.front() == '#' && accent.color.size() == 7,
                      (def.id + "." + accent.id + " declares a valid #RRGGBB color").c_str());
                check(accent.opacity > 0.f && accent.opacity <= 1.f,
                      (def.id + "." + accent.id + " opacity is in (0, 1]").c_str());
                for (const PhraseTrack& track : accent.tracks) {
                    everyTrackIsAValidEntrance(track, def.id + "." + accent.id);
                }
            }
            for (std::size_t i = 0; i < def.textAnimators.size(); ++i) {
                const auto& anim = def.textAnimators[i];
                check(!anim.properties.empty(), (def.id + " animator has properties").c_str());
                for (const auto& track : anim.properties) {
                    everyTrackIsAValidEntrance(track, def.id + ".textAnimators[" + std::to_string(i) + "]." + track.property);
                }
            }
        }
    }

    void testHighlightPhraseStyle() {
        section("Highlight phrase style");
        const auto style = highlightPhraseStyle();
        check(style.font_size <= 65.f && style.font_size >= 40.f, "font size is calibrated for multi-line long phrases");
        check(style.box[0] >= 1500.f && style.box[1] >= 340.f, "box accommodates multi-line long phrases");
    }

} // namespace

int main() {
    theHighlightAnimationsValidateForLongPhrases();
    testHighlightPhraseStyle();
    return chrononmotion_test::report();
}
