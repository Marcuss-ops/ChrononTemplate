#include "chronontemplate/Typewriter3DPhrasePack.hpp"

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

    void theTypewriterAnimationsAreWellFormed() {
        section("typewriter phrase animations");
        const auto animations = typewriter3DPhraseAnimations();
        check(animations.size() == 15, "the Typewriter pack publishes fifteen animations");

        std::set<std::string> ids;
        for (const Typewriter3DPhraseAnimation animation : animations) {
            const std::string id = name(animation);
            check(ids.insert(id).second, "typewriter animation ids are unique");
            check(id.rfind("typewriter_", 0) == 0, "wire ids carry the family prefix");
            const PhraseAnimationDefinition def = definition(animation);
            check(def.id == id, "definition publishes the same id as its enumerator name");
            check(!def.title.empty() && !def.phrase.empty(),
                  "each animation carries a title and a showcase phrase");
            check(def.enter == 60, "entrance duration is calibrated at 2s");
            check(!def.textAnimators.empty(), "every animation types through a text animator");
            for (std::size_t i = 0; i < def.tracks.size(); ++i) {
                everyKeyframeListIsAValidEntrance(
                        def.tracks[i], def.id + ".tracks[" + std::to_string(i) + "]");
            }
            if (!def.cursor.tracks.empty()) {
                for (std::size_t i = 0; i < def.cursor.tracks.size(); ++i) {
                    everyKeyframeListIsAValidEntrance(
                            def.cursor.tracks[i], def.id + ".cursor[" + std::to_string(i) + "]");
                }
            }
        }

        const auto style3d = typewriter3DStyle();
        check(style3d.has_card, "3D style includes card container");
        check(style3d.card_stroke_width > 0.0f, "card container has non-zero rect stroke");
        check(!style3d.glow.empty(), "glow color is defined");

        const auto paperStyle = paperCardWebStyle();
        check(paperStyle.has_card, "paper card style has card");
        check(paperStyle.fill == "#111111", "paper card style uses almost black font");
        check(paperStyle.glow == "#000000", "paper card style uses subtle black halo");

        const auto docStyle = docCleanWhiteStyle();
        check(!docStyle.has_card, "clean white doc style has no card");
        check(docStyle.fill == "#FFFFFF", "clean white doc style uses white font");

        const auto searchStyle = docSearchBarWebStyle();
        check(searchStyle.has_card, "search bar style has card");
        check(searchStyle.card_radius == 50.f, "search bar style has pill radius");

        const auto quoteStyle = docQuoteSerifStyle();
        check(quoteStyle.has_card, "quote serif style has card");
        check(quoteStyle.font.find("Georgia") != std::string::npos, "quote serif uses Georgia font");

        const auto lowerStyle = docLowerThirdStyle();
        check(!lowerStyle.has_card, "lower third style has no card");
        check(lowerStyle.fill == "#FFFFFF", "lower third style uses white font");

        const auto statStyle = docStatCardStyle();
        check(statStyle.has_card, "stat card style has card");
        check(statStyle.font_size == 64.f, "stat card uses prominent number");

        const auto underlineStyle = docUnderlineDrawStyle();
        check(!underlineStyle.has_card, "underline style has no card");
        check(underlineStyle.font.find("Poppins") != std::string::npos, "underline style uses Poppins font");

        const auto wordStyle = docWordStageStyle();
        check(wordStyle.font_size == 96.f, "word stage uses large 96px display font");

        const auto trailerStyle = docTrailerScaleStyle();
        check(trailerStyle.font.find("Montserrat") != std::string::npos, "trailer style uses Montserrat-Bold");

        const auto countStyle = docCountUpStatStyle();
        check(countStyle.has_card, "count-up stat has card");
        check(countStyle.font.find("Sora") != std::string::npos, "count-up stat uses Sora font");
    }

} // namespace

int main() {
    theTypewriterAnimationsAreWellFormed();
    return 0;
}
