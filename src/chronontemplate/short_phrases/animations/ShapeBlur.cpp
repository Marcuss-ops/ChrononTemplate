#include "RecipeSupport.hpp"

namespace chronontemplate::modern_short_phrase {

ShortPhraseDefinition shapeBlur() {
    using namespace detail;
    auto d = make("short_phrase_product_shape_blur", "Shape Blur",
                  "SHAPE FINDS FOCUS", 90,
                  {t("opacity", {{0, 0.f}, {90, 1.f}, {194, 1.f}, {209, 0.f}}, "linear"),
                   t("scale", {{0, 0.94f}, {90, 1.f}, {194, 1.f}, {209, 1.02f}})},
                  {a("glyph", "reveal_soft", {
                      t("blur", {{0, 22.f}, {45, 9.f}, {90, 0.f}, {194, 0.f}, {209, 10.f}}),
                      t("opacity", {{0, 0.f}, {45, 0.45f}, {90, 1.f}, {194, 1.f}, {209, 0.f}}, "linear")})},
                  118.f);
    d.accents.push_back(PhraseAccent{
        "shape_blur_accent", "#67E8F9", 360.f, 4.f, 92.f, 2.f, 0.8f,
        {t("scale_x", {{0, 0.08f}, {48, 0.62f}, {90, 1.f}, {194, 1.f}, {209, 1.08f}}, "out_cubic"),
         t("opacity", {{0, 0.f}, {26, 0.18f}, {74, 0.3f}, {110, 0.f}, {209, 0.f}}, "linear")}});
    d.adaptation_note = "A native accent bar and soft glyph reveal stand in for the mouse-lit Three.js SDF shader; mouse following, shape variations and WebGL rendering are not represented.";
    return d;
}

} // namespace chronontemplate::modern_short_phrase
