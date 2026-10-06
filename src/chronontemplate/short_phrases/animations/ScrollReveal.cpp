#include "RecipeSupport.hpp"

namespace chronontemplate::modern_short_phrase {

ShortPhraseDefinition scrollReveal() {
    using namespace detail;
    auto d = make("short_phrase_product_scroll_reveal", "Scroll Reveal",
                  "WORDS EMERGE WITH CLARITY", 90,
                  {t("rotation_z", {{0, 3.f}, {90, 0.f}, {194, 0.f}, {209, 0.f}}),
                   t("opacity", {{0, 0.15f}, {90, 1.f}, {194, 1.f}, {209, 0.f}}, "linear")},
                  {a("word", "band", {
                      t("blur", {{0, 5.f}, {90, 0.f}, {194, 0.f}, {209, 5.f}}),
                      t("opacity", {{0, 0.12f}, {90, 1.f}, {194, 1.f}, {209, 0.f}}, "linear"),
                      t("position_y", {{0, 12.f}, {90, 0.f}, {194, 0.f}, {209, 12.f}})})},
                  108.f);
    d.adaptation_note = "Scroll-scrub style progression baked into ordinary clip frames; a native eased entrance replaces viewport scrubbing, with no scroll container, observer, or runtime trigger (not represented).";
    return d;
}

} // namespace chronontemplate::modern_short_phrase
