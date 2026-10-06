#include "RecipeSupport.hpp"

namespace chronontemplate::modern_short_phrase {

ShortPhraseDefinition warpText() {
    using namespace detail;
    auto d = make("short_phrase_product_warp_text", "Warp Text",
                  "BEND THE MOMENT", 90,
                  {t("scale", {{0, 0.96f}, {45, 1.015f}, {90, 1.f}, {194, 1.f}, {209, 1.f}}),
                   t("opacity", {{0, 0.f}, {90, 1.f}, {194, 1.f}, {209, 0.f}}, "linear")},
                  {a("glyph", "band", {
                      t("position_y", {{0, 10.f}, {45, -8.f}, {90, 0.f}, {194, 0.f}, {209, 0.f}}),
                      t("rotation", {{0, -4.f}, {45, 4.f}, {90, 0.f}, {194, 0.f}, {209, 0.f}})})},
                  114.f);
    d.adaptation_note = "Native deterministic glyph-wave proxy; WebGL noise/refraction shader and pointer-reactive bulge/ripple are not represented.";
    return d;
}

} // namespace chronontemplate::modern_short_phrase
