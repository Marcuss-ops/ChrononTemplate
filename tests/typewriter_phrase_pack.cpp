#include "chronontemplate/TypewriterPhrasePack.hpp"

#include "motion_check.hpp"

#include <set>
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

    void theFifteenTypewriterAnimationsAreWellFormed() {
        section("fifteen typewriter phrase animations");
        const auto animations = typewriterPhraseAnimations();
        check(animations.size() == 15, "the Typewriter pack publishes fifteen animations");

        std::set<std::string> ids;
        bool anyCursor = false;
        for (const TypewriterPhraseAnimation animation : animations) {
            const std::string id = name(animation);
            check(ids.insert(id).second, "typewriter animation ids are unique");
            check(id.rfind("typewriter_", 0) == 0, "typewriter wire ids carry the family prefix");
            const PhraseAnimationDefinition def = definition(animation);
            check(def.id == id, "the typewriter definition publishes the same id as its enumerator name");
            check(!def.title.empty() && !def.phrase.empty(),
                  "each typewriter animation carries a title and a showcase phrase");
            check(def.enter == 30 || def.enter == 60 || def.enter == 90,
                  "typewriter entrances keep their one, two or three-second pace");
            check(!def.textAnimators.empty(), "every typewriter animation types through a text animator");
            for (const PhraseTextAnimator& animator : def.textAnimators) {
                check(animator.selector.window == "reveal" ||
                              animator.selector.window == "reveal_soft",
                      "typing is always the reveal window");
            }
            for (std::size_t i = 0; i < def.tracks.size(); ++i) {
                everyKeyframeListIsAValidEntrance(
                        def.tracks[i], def.id + ".tracks[" + std::to_string(i) + "]");
            }
            for (std::size_t i = 0; i < def.cursor.tracks.size(); ++i) {
                everyKeyframeListIsAValidEntrance(
                        def.cursor.tracks[i], def.id + ".cursor[" + std::to_string(i) + "]");
            }
            anyCursor = anyCursor || !def.cursor.tracks.empty();
        }
        check(anyCursor, "the typewriter family types with the underscore cursor");
    }

    void namesAreStableWireIds() {
        section("stable wire names");
        check(std::string(name(TypewriterPhraseAnimation::Cursor)) == "typewriter_cursor",
              "the underscore cursor has a stable wire name");
    }

}// namespace

int main() {
    theFifteenTypewriterAnimationsAreWellFormed();
    namesAreStableWireIds();
    return chrononmotion_test::report();
}
