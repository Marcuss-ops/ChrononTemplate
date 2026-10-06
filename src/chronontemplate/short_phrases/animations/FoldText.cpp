#include "RecipeSupport.hpp"

namespace chronontemplate::modern_short_phrase {

ShortPhraseDefinition foldText() {
    using namespace detail;
    auto d = make("short_phrase_product_fold_text", "Fold Text",
                  "UNFOLD", 90,
                  {t("scale", {{0, 0.94f}, {90, 1.f}, {194, 1.f}, {209, 1.f}}),
                   t("rotation_x", {{0, -88.f}, {90, 0.f}, {194, 0.f}, {209, 0.f}}),
                   t("opacity", {{0, 0.f}, {90, 1.f}, {194, 1.f}, {209, 0.f}}, "linear")},
                  {},
                  122.f);
    d.adaptation_note = "Phrase-level 3D hinge approximation; React char/word/line-specific hinge origins, crease shading, and trigger modes are not represented.";
    return d;
}

} // namespace chronontemplate::modern_short_phrase
