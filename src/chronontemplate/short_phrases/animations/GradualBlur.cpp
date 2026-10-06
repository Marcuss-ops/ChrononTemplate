#include "RecipeSupport.hpp"

namespace chronontemplate::modern_short_phrase {

ShortPhraseDefinition gradualBlur() {
    using namespace detail;
    auto d = make("short_phrase_product_gradual_blur", "Gradual Blur",
                  "A SOFTER ARRIVAL", 90,
                  {t("opacity", {{0, 0.f}, {90, 1.f}, {194, 1.f}, {209, 0.f}}, "linear"),
                   t("position_y", {{0, 32.f}, {90, 0.f}, {194, 0.f}, {209, -18.f}}, "out_cubic")},
                  {a("glyph", "reveal_soft", {
                      t("blur", {{0, 30.f}, {18, 22.f}, {42, 12.f}, {66, 4.f}, {90, 0.f}, {194, 0.f}, {209, 14.f}}),
                      t("opacity", {{0, 0.f}, {18, 0.18f}, {42, 0.48f}, {66, 0.82f}, {90, 1.f}, {194, 1.f}, {209, 0.f}}, "linear")})},
                  112.f);
    d.adaptation_note = "Progressive native glyph blur/opacity approximates the bottom-edge backdrop blur; the CSS layer stack, responsive presets and scroll/hover triggers are not represented.";
    return d;
}

} // namespace chronontemplate::modern_short_phrase
