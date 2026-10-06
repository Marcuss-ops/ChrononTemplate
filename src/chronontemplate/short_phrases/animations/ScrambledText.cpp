#include "RecipeSupport.hpp"

namespace chronontemplate::modern_short_phrase {

ShortPhraseDefinition scrambledText() {
    using namespace detail;
    auto d = make("short_phrase_product_scrambled_text", "Scrambled Text",
                  "THE MESSAGE RESOLVES", 90,
                  {t("opacity", {{0, 0.f}, {90, 1.f}, {194, 1.f}, {209, 0.f}}, "linear")},
                  {a("glyph", "reveal_soft", {
                      t("position_y", {{0, 6.f}, {90, 0.f}, {194, 0.f}, {209, -12.f}}),
                      t("opacity", {{0, 0.f}, {90, 1.f}, {194, 1.f}, {209, 0.f}}, "linear")})},
                  108.f);
    d.adaptation_note = "Deterministic smooth glyph reveal proxy; pointer-distance scrambling and GSAP hover reversion are not represented.";
    return d;
}

} // namespace chronontemplate::modern_short_phrase
