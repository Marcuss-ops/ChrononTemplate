#include "RecipeSupport.hpp"

namespace chronontemplate::modern_short_phrase {

ShortPhraseDefinition perWordRise() {
    using namespace detail;

    // Match the supplied HyperFrames recipe: each word gets a 0.74 s rise,
    // with the three landings spread across 0.62 s. The final word lands at
    // about 1.36 s, followed by a completely still hold.
    constexpr int riseFrames = 22;
    constexpr int wordCount = 3;
    constexpr int staggerFrames = 9;
    constexpr int lastLanding = (wordCount - 1) * staggerFrames + riseFrames;

    auto phrase = make(
        "short_phrase_product_per_word_rise",
        "Per Word Rise",
        "WORDS IN MOTION",
        lastLanding,
        {t("opacity", {{0, 1.f}, {194, 1.f}, {209, 0.f}}, "linear")},
        {},
        126.f);

    for (int i = 0; i < wordCount; ++i) {
        const int start = i * staggerFrames;
        const int landing = start + riseFrames;
        const std::string window = "pick:" + std::to_string(i) + ":" + std::to_string(wordCount);
        const std::vector<PhraseKeyframe> opacity = start == 0
            ? std::vector<PhraseKeyframe>{{0, 0.f}, {landing, 1.f}, {194, 1.f}, {209, 0.f}}
            : std::vector<PhraseKeyframe>{{0, 0.f}, {start, 0.f}, {landing, 1.f}, {194, 1.f}, {209, 0.f}};
        const std::vector<PhraseKeyframe> y = start == 0
            ? std::vector<PhraseKeyframe>{{0, 86.f}, {landing, 0.f}, {194, 0.f}, {209, -48.f}}
            : std::vector<PhraseKeyframe>{{0, 86.f}, {start, 86.f}, {landing, 0.f}, {194, 0.f}, {209, -48.f}};
        const std::vector<PhraseKeyframe> blur = start == 0
            ? std::vector<PhraseKeyframe>{{0, 15.f}, {landing, 0.f}, {194, 0.f}, {209, 8.f}}
            : std::vector<PhraseKeyframe>{{0, 15.f}, {start, 15.f}, {landing, 0.f}, {194, 0.f}, {209, 8.f}};
        phrase.textAnimators.push_back(a(
            "word",
            window.c_str(),
            {t("opacity", opacity, "linear"),
             t("position_y", y, "per_word_land"),
             t("blur", blur, "per_word_land")}));
    }
    return phrase;
}

} // namespace chronontemplate::modern_short_phrase
