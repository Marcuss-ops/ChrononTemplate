#include "RecipeSupport.hpp"

namespace chronontemplate::modern_short_phrase {

ShortPhraseDefinition perspectiveMarquee() {
    using namespace detail;
    auto d = make("short_phrase_product_perspective_marquee",
                  "Perspective Marquee",
                  "COMPONENTS PRIMITIVES TRANSITIONS AGENTS",
                  96, {}, {}, 88.f);
    d.drawMainPhrase = false;

    // A single centered strip, with enough space for a gentle camera pan.
    // Keep the camera level and close to the canvas center so the words stay
    // legible instead of flying through a steep, clipped perspective.
    const char* words[] = {"COMPONENTS", "PRIMITIVES", "TRANSITIONS", "AGENTS"};
    const float positions[] = {-1140.f, -380.f, 380.f, 1140.f};
    for (int i = 0; i < 4; ++i) {
        d.textOverlays.push_back(overlay(("marquee_" + std::to_string(i)).c_str(),
                                         words[i], "#F7F8FA", positions[i], 0.f, 1.f));
    }
    return d;
}

} // namespace chronontemplate::modern_short_phrase
