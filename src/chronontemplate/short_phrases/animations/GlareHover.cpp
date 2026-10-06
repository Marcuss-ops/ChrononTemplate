#include "RecipeSupport.hpp"

namespace chronontemplate::modern_short_phrase {

ShortPhraseDefinition glareHover() {
    using namespace detail;
    auto d = make("short_phrase_product_glare_hover", "Glare Hover",
                  "LIGHT IN MOTION", 90,
                  {t("opacity", {{0, 0.f}, {12, 1.f}, {194, 1.f}, {209, 0.f}}, "linear")},
                  {a("glyph", "full", {
                      t("blur", {{0, 5.f}, {90, 0.f}, {194, 0.f}, {209, 4.f}})})},
                  120.f);
    d.accents.push_back(PhraseAccent{
        "glare_sweep", "#FFFFFF", 360.f, 150.f, 0.f, 0.f, 0.28f,
        {t("position_x", {{0, -900.f}, {22, -900.f}, {94, 900.f}, {112, 900.f}, {209, 900.f}}, "in_out_cubic"),
         t("opacity", {{0, 0.f}, {18, 0.f}, {30, 1.f}, {94, 1.f}, {108, 0.f}, {209, 0.f}}, "linear")}});
    d.adaptation_note = "Deterministic highlight-bar sweep approximates the CSS glare pass; hover re-entry, playOnce and card layout styles are not represented.";
    return d;
}

} // namespace chronontemplate::modern_short_phrase
