#include "RecipeSupport.hpp"

namespace chronontemplate::modern_short_phrase {

ShortPhraseDefinition strikethroughReplace() {
    using namespace detail;
    auto d = make("short_phrase_product_strikethrough_replace",
                  "Strikethrough Replace",
                  "Everyone promised you AI.",
                  132,
                  {t("opacity", {{0, 1.f}, {84, 1.f}, {95, 0.f}, {194, 0.f}, {209, 0.f}}, "linear")},
                  {},
                  96.f);

    // Start the new line before the old one finishes fading, so the cut never
    // exposes the black matte for a frame. The emitter draws a centered rule.
    d.textOverlays.push_back(overlay(
        "replacement",
        "Almost nobody promised control.",
        "#F7F8FA",
        0.f,
        0.f,
        1.f,
        {t("opacity", {{0, 0.f}, {88, 0.f}, {116, 1.f}, {194, 1.f}, {209, 0.f}}, "linear"),
         t("position_y", {{0, 36.f}, {88, 36.f}, {116, 0.f}, {194, 0.f}, {209, -120.f}})}));
    d.accents.push_back(PhraseAccent{
        "strike_rule", "#FF3158", 1260.f, 6.f, 0.f, 3.f, 0.95f,
        {t("scale_x", {{0, 0.f}, {55, 0.f}, {85, 1.f}, {92, 1.f}, {100, 0.f}, {209, 0.f}}, "out_cubic"),
         t("opacity", {{0, 0.f}, {55, 0.f}, {85, 0.95f}, {92, 0.95f}, {100, 0.f}, {209, 0.f}}, "linear")}});
    return d;
}

} // namespace chronontemplate::modern_short_phrase
