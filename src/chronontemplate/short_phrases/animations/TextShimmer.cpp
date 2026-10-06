#include "RecipeSupport.hpp"

namespace chronontemplate::modern_short_phrase {

ShortPhraseDefinition textShimmer() {
    using namespace detail;
    // Light the complete phrase together, then return to its original fill.
    // A band selector only touched a handful of glyphs on short captions.
    constexpr int sweepFrames = 42;
    return make("short_phrase_product_text_shimmer",
                "Text Shimmer",
                "Effortless",
                sweepFrames,
                {t("opacity", {{0, 1.f}, {194, 1.f}, {209, 1.f}}, "linear")},
                {a("glyph", "full", {t("fill_blue", {{0, 0.f}, {14, 0.9f}, {28, 0.35f},
                                                        {42, 0.f}, {194, 0.f}, {209, 0.f}}, "linear")})},
                144.f);
}

} // namespace chronontemplate::modern_short_phrase
