#include "chronontemplate/important_phrases/highlight/PhraseHighlightPack.hpp"

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

    void theHighlightAnimationsShareTheCanonicalEntrance() {
        section("highlight important-phrase family");
        const auto animations = phraseHighlightAnimations();
        check(!animations.empty(), "the Highlight family publishes at least one animation");

        std::set<std::string> ids;
        for (const PhraseHighlightAnimation animation : animations) {
            const std::string id = name(animation);
            check(ids.insert(id).second, "highlight animation ids are unique");
            check(id.rfind("phrase_", 0) == 0, "highlight wire ids carry the phrase_ prefix");

            const PhraseAnimationDefinition def = definition(animation);
            check(def.id == id, "the definition publishes the same id as its enumerator name");
            check(!def.title.empty(), "each highlight animation carries a human title");
            check(!def.phrase.empty(), "each highlight animation carries a showcase phrase");
            // Highlight accents hold until frame 78, so the entrance must cover
            // every keyframe: nothing may be clipped by a shorter entrance.
            int lastFrame = 0;
            for (const PhraseTrack& track : def.tracks) {
                for (const PhraseKeyframe& key : track.keyframes) lastFrame = std::max(lastFrame, key.frame);
            }
            for (const PhraseAccent& accent : def.accents) {
                for (const PhraseTrack& track : accent.tracks) {
                    for (const PhraseKeyframe& key : track.keyframes) lastFrame = std::max(lastFrame, key.frame);
                }
            }
            check(def.enter >= lastFrame,
                  (def.id + " entrance covers every keyframe (last frame " + std::to_string(lastFrame) +
                   ", enter " + std::to_string(def.enter) + ")").c_str());
            check(def.enter >= 78, "the highlight entrance is at least the 78-frame accent hold");
            check(!def.tracks.empty() || !def.accents.empty(),
                  "each highlight animation authors layer motion or an accent");

            for (std::size_t i = 0; i < def.tracks.size(); ++i) {
                everyTrackIsAValidEntrance(def.tracks[i], def.id + ".tracks[" + std::to_string(i) + "]");
            }
            std::set<std::string> accentIds;
            for (const PhraseAccent& accent : def.accents) {
                check(accent.width > 0.f && accent.height > 0.f, "highlight accents have positive dimensions");
                check(!accent.id.empty(), "highlight accents carry an id");
                check(accentIds.insert(accent.id).second,
                      (def.id + " accent ids are unique: " + accent.id).c_str());
                check(!accent.color.empty() && accent.color.front() == '#',
                      (def.id + "." + accent.id + " declares an authored color").c_str());
                check(accent.opacity > 0.f && accent.opacity <= 1.f,
                      (def.id + "." + accent.id + " opacity is in (0, 1]").c_str());
                for (const PhraseTrack& track : accent.tracks) {
                    everyTrackIsAValidEntrance(track, def.id + "." + accent.id);
                    for (const auto& key : track.keyframes) {
                        if (track.property == "scale_x")
                            check(key.value > 0.f,
                                  (def.id + "." + accent.id + " scale_x is strictly positive for native affine shapes").c_str());
                    }
                }
            }
        }
    }

    void theSharedEntranceConstantIsTwoSecondsAtThirtyFps() {
        section("shared important-phrase entrance");
        check(kPhraseEnterFrames == 60, "the shared phrase entrance is 60 frames (two seconds at 30 fps)");
    }

} // namespace

int main() {
    theSharedEntranceConstantIsTwoSecondsAtThirtyFps();
    theHighlightAnimationsShareTheCanonicalEntrance();
    return chrononmotion_test::report();
}
