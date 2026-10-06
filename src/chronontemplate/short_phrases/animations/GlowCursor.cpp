#include "RecipeSupport.hpp"

namespace chronontemplate::modern_short_phrase {

ShortPhraseDefinition glowCursor() {
    using namespace detail;
    auto d = make("short_phrase_product_glow_cursor", "Glow Cursor",
                  "FOLLOW THE LIGHT", 90,
                  {t("opacity", {{0, 0.f}, {8, 1.f}, {194, 1.f}, {209, 0.f}}, "linear")},
                  {a("glyph", "full", {
                      t("blur", {{0, 18.f}, {90, 1.f}, {194, 1.f}, {209, 12.f}}),
                      t("scale", {{0, 0.96f}, {90, 1.f}, {194, 1.f}, {209, 0.98f}})})},
                  116.f);
    d.fill_color = "#67E8F9";
    d.accents.push_back(PhraseAccent{
        "glow_trail", "#A78BFA", 520.f, 5.f, 76.f, 2.f, 0.8f,
        {t("position_x", {{0, -720.f}, {22, -720.f}, {95, 720.f}, {112, 720.f}, {195, 720.f}, {209, 860.f}}, "in_out_cubic"),
         t("position_y", {{0, 70.f}, {22, 70.f}, {95, 45.f}, {112, -24.f}, {195, 0.f}, {209, -140.f}}, "in_out_cubic"),
         t("scale_x", {{0, 0.08f}, {22, 0.08f}, {95, 1.f}, {112, 0.08f}, {195, 0.08f}, {209, 0.08f}}, "in_out_cubic"),
         t("opacity", {{0, 0.f}, {22, 0.f}, {95, 0.85f}, {112, 0.f}, {195, 0.f}, {209, 0.f}}, "in_out_cubic")}});
    d.adaptation_note = "A single deterministic cyan-violet trail animates across the title; live pointer tracking, GPU noise, pulse and idle fading are not represented.";
    return d;
}

} // namespace chronontemplate::modern_short_phrase
