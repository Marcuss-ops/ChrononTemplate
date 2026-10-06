#include "RecipeSupport.hpp"

namespace chronontemplate::modern_short_phrase {

ShortPhraseDefinition splitFlapText() {
    using namespace detail;
    auto d = make("short_phrase_product_split_flap_text", "Split Flap Text",
                  "SIGNAL LIVE", 90,
                  {t("opacity", {{0, 0.f}, {90, 1.f}, {194, 1.f}, {209, 0.f}}, "linear")},
                  {a("glyph", "reveal_soft", {
                      t("position_y", {{0, 20.f}, {12, 5.f}, {90, 0.f}, {194, 0.f}, {209, -10.f}}),
                      t("rotation", {{0, -8.f}, {45, 0.f}, {90, 0.f}, {194, 0.f}, {209, 0.f}}),
                      t("opacity", {{0, 0.f}, {90, 1.f}, {194, 1.f}, {209, 0.f}}, "linear")})},
                  118.f);
    d.fill_color = "#F8FAFC";
    d.adaptation_note = "Deterministic glyph flip/rise proxy; live randomized character cycling, tile geometry, and phrase loops are not represented.";
    return d;
}

} // namespace chronontemplate::modern_short_phrase
