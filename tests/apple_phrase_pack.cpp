#include "chronontemplate/ApplePhrasePack.hpp"

#include "motion_check.hpp"

#include <set>
#include <string>

using namespace chronontemplate;
using chrononmotion_test::check;
using chrononmotion_test::section;

namespace {

    void testAllAppleEntrancesLastTwoSeconds() {
        section("Modern Apple entrance timing and variety");
        const auto animations = applePhraseAnimations();
        check(animations.size() == 15, "Apple pack publishes fifteen animations");

        std::set<std::string> ids;
        std::set<std::string> signatures;
        std::string showcasePhrase;
        for (const ApplePhraseAnimation animation : animations) {
            const std::string id = name(animation);
            check(ids.insert(id).second, "Apple animation ids are unique");
            const PhraseAnimationDefinition def = definition(animation);
            check(def.id == id, "definition id matches its registry id");
            check(def.enter == 60, "every entrance lasts two seconds at 30 fps");
            check(!def.title.empty() && !def.phrase.empty(), "preset has a title and sample phrase");
            if (showcasePhrase.empty()) showcasePhrase = def.phrase;
            check(def.phrase == showcasePhrase,
                  "all Apple presets use the same phrase for motion-by-motion comparison");
            check(!def.tracks.empty() || !def.textAnimators.empty(), "preset contains animation tracks");

            std::string signature;
            for (const auto& item : def.tracks) {
                signature += "L:" + item.property + ";";
                for (const auto& key : item.keyframes) signature += std::to_string(key.value) + ",";
            }
            for (const auto& animator : def.textAnimators) {
                signature += "U:" + animator.selector.unit + ":" + animator.selector.order +
                            ":" + animator.selector.window + ";";
                for (const auto& item : animator.properties) {
                    signature += item.property + ";";
                    for (const auto& key : item.keyframes) signature += std::to_string(key.value) + ",";
                }
            }
            signatures.insert(signature);

            for (const auto& item : def.tracks) {
                check(item.keyframes.size() >= 2 && item.keyframes.front().frame == 0,
                      "layer tracks start at frame zero and have an entrance");
                check(item.keyframes.back().frame <= 60, "layer track completes within two seconds");
                check(item.property != "blur", "Apple text stays crisp without per-glyph blur");
            }
            for (const auto& animator : def.textAnimators) {
                check(!animator.properties.empty(), "text-unit animation has visible properties");
                for (const auto& item : animator.properties) {
                    check(item.keyframes.size() >= 2 && item.keyframes.front().frame == 0,
                          "unit tracks start at frame zero and have an entrance");
                    check(item.keyframes.back().frame <= 60, "unit track completes within two seconds");
                    check(item.property != "blur", "Apple glyph animation does not use the noisy blur path");
                }
            }
        }
        check(signatures.size() >= 12, "the Apple pack exposes distinct motion signatures");
    }

}

int main() {
    testAllAppleEntrancesLastTwoSeconds();
    return chrononmotion_test::report();
}
