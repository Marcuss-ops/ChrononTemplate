#include "RecipeSupport.hpp"

namespace chronontemplate::modern_short_phrase {

ShortPhraseDefinition maskedHeading() {
    using namespace detail;
    auto d = make("short_phrase_product_masked_heading", "Masked Heading",
                  "DETAILS DEFINE DESIGN", 90,
                  {t("opacity", {{0, 0.f}, {90, 1.f}, {194, 1.f}, {209, 0.f}}, "linear")},
                  {a("glyph", "reveal_soft", {
                      t("position_y", {{0, 52.f}, {90, 0.f}, {194, 0.f}, {209, -32.f}}),
                      t("opacity", {{0, 0.f}, {90, 1.f}, {194, 1.f}, {209, 0.f}}, "linear")})},
                  110.f);
    d.adaptation_note = "Native soft glyph mask/rise; React image/video fill, pointer parallax, and hover/view triggers are not represented.";
    return d;
}

} // namespace chronontemplate::modern_short_phrase
