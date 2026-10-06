#include "RecipeSupport.hpp"

namespace chronontemplate::modern_short_phrase {

ShortPhraseDefinition scanBand() {
    using namespace detail;
    // Keep the wordmark pristine and sweep one narrow cyan glyph across it.
    // A native text layer avoids the black rectangles caused by animated GPU
    // shape opacity in this composition path.
    auto d = make("short_phrase_product_scan_band",
                  "Scan Band",
                  "HYPERFRAMES",
                  106,
                  {t("opacity", {{0, 1.f}, {194, 1.f}, {209, 0.f}}, "linear")},
                  {},
                  128.f);
    d.textOverlays.push_back(overlay(
        "scan_cursor", "┃", "#35C8D9", 0.f, 0.f, 1.f,
        {t("position_x", {{0, -820.f}, {16, -820.f}, {106, 820.f}, {124, 820.f}, {209, 820.f}}, "in_out_cubic"),
         t("opacity", {{0, 0.f}, {16, 0.9f}, {106, 0.9f}, {124, 0.f}, {209, 0.f}}, "linear")}));
    return d;
}

} // namespace chronontemplate::modern_short_phrase
