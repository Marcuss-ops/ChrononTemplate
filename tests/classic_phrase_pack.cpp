#include "chronontemplate/ClassicPhrasePack.hpp"

#include "motion_check.hpp"

#include <set>
#include <string>

using namespace chronontemplate;
using chrononmotion_test::check;
using chrononmotion_test::section;

namespace {

    // The shared look is exercised from the Classic file — one file per
    // family, and Classic introduced the look every family renders with.
    void sharedStyleIsWhiteOnBlackWithAVisibleGlow() {
        section("classic important-phrase style");
        const ClassicPhraseStyle style = classicPhraseStyle();
        check(style.fill == "#FFFFFF", "classic phrase face is white");
        check(style.background[0] == 0.f && style.background[1] == 0.f && style.background[2] == 0.f &&
                      style.background[3] == 1.f,
              "classic phrase canvas is solid black");
        check(style.glow == "#FFFFFF", "classic phrase glow reads on the black canvas (white halo)");
        check(style.glow_radius > 0.f && style.glow_radius <= 48.f,
              "classic phrase glow radius stays slight");
        check(style.glow_intensity > 0.f && style.glow_intensity <= 0.5f,
              "classic phrase glow intensity stays slight");
        check(style.stroke == "#000000" && style.stroke_width > 0.f && style.stroke_width <= 8.f,
              "classic phrase carries a slight black stroke that keeps the letters crisp");
        check(!style.font.empty() && style.font_size > 0.f, "classic phrase declares a real face");
        check(style.font.find("Montserrat") != std::string::npos,
              "classic phrase face is modern (Montserrat Bold)");
        check(style.box[0] > 0.f && style.box[1] > 0.f, "classic phrase declares a text box");
    }

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

    void theFourteenClassicAnimationsAreWellFormed() {
        section("fourteen classic phrase animations");
        const auto animations = classicPhraseAnimations();
        check(animations.size() == 14, "the Classic pack publishes fourteen animations");

        std::set<std::string> ids;
        bool anyLayer = false;
        bool anyUnit = false;
        bool anyWord = false;
        bool anyReveal = false;
        bool anyBand = false;
        bool anyRevealWindow = false;
        for (const ClassicPhraseAnimation animation : animations) {
            const std::string id = name(animation);
            check(ids.insert(id).second, "classic animation ids are unique");
            check(id.rfind("classic_", 0) == 0, "classic wire ids carry the family prefix");
            const PhraseAnimationDefinition def = definition(animation);
            check(def.id == id, "the definition publishes the same id as its enumerator name");
            check(!def.title.empty(), "each classic animation carries a human title");
            check(!def.phrase.empty(), "each classic animation carries a showcase phrase");
            check(def.enter == 60, "each classic animation enters over two seconds");
            check(!def.tracks.empty() || !def.textAnimators.empty(),
                  "each classic animation authors motion on the layer or on text units");

            std::set<std::string> properties;
            for (std::size_t i = 0; i < def.tracks.size(); ++i) {
                everyKeyframeListIsAValidEntrance(
                        def.tracks[i], def.id + ".tracks[" + std::to_string(i) + "]");
                properties.insert(def.tracks[i].property);
            }
            for (std::size_t i = 0; i < def.textAnimators.size(); ++i) {
                const PhraseTextAnimator& animator = def.textAnimators[i];
                check(!animator.properties.empty(), "each text animator authors at least one property");
                for (std::size_t j = 0; j < animator.properties.size(); ++j) {
                    everyKeyframeListIsAValidEntrance(
                            animator.properties[j],
                            def.id + ".textAnimators[" + std::to_string(i) + "].properties[" +
                                    std::to_string(j) + "]");
                }
                // Chronon3D's GPU text contract lowers exactly two profiles:
                // a forward glyph window and a full-run word emphasis. A pack
                // that renders on the Vulkan lane stays inside them.
                check(animator.selector.unit == "glyph" || animator.selector.unit == "word",
                      "text animators select glyph or word units (the GPU-lowerable profiles)");
                check(animator.selector.window == "full" || animator.selector.window == "reveal" ||
                              animator.selector.window == "reveal_soft" ||
                              animator.selector.window == "band",
                      "selector windows stay inside the GPU-lowerable set (full | reveal | reveal_soft | band)");
                anyUnit = true;
                anyWord = anyWord || animator.selector.unit == "word";
                anyReveal = anyReveal || animator.selector.window == "reveal";
                anyBand = anyBand || animator.selector.window == "band";
                anyRevealWindow = anyRevealWindow || animator.selector.window == "reveal";
            }
            if (!def.tracks.empty()) anyLayer = true;

            // Opacity ends open: the emitter holds the resting value and
            // synthesises the exit (and fades in any animation that authors no
            // opacity at all), so only an opacity that ends closed needs a
            // reason — a reveal-window animator arrives visible by
            // construction: its properties hold the hidden value and the
            // completed window leaves the run visible.
            bool closesOpacity = false;
            for (const PhraseTrack& track : def.tracks) {
                if (track.property == "opacity" && track.keyframes.back().value < 1.f) closesOpacity = true;
            }
            for (const PhraseTextAnimator& animator : def.textAnimators) {
                for (const PhraseTrack& track : animator.properties) {
                    if (track.property == "opacity" && track.keyframes.back().value < 1.f) closesOpacity = true;
                }
            }
            check(!closesOpacity || anyRevealWindow, (def.id + " arrives at full opacity").c_str());
            (void) properties;
            anyRevealWindow = false;
        }
        check(anyLayer, "the pack keeps the classic layer-level entrances");
        check(anyUnit, "the pack keeps the per-unit reveals");
        check(anyWord, "the pack exercises the full-run word profile");
        check(anyReveal && anyBand, "the pack exercises both staggered windows (reveal and band)");
    }

    void namesAreStableWireIds() {
        section("stable wire names");
        check(std::string(name(ClassicPhraseAnimation::Fade)) == "classic_fade", "fade has a stable wire name");
        check(std::string(name(ClassicPhraseAnimation::Typewriter)) == "classic_typewriter",
              "typewriter has a stable wire name");
    }

}// namespace

int main() {
    sharedStyleIsWhiteOnBlackWithAVisibleGlow();
    theFourteenClassicAnimationsAreWellFormed();
    namesAreStableWireIds();
    return chrononmotion_test::report();
}
