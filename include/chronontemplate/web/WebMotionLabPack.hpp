// ChrononTemplate — Web Motion Lab.
//
// Sei ricette nuove, pensate come esperimenti di grammatica per le animazioni
// web: apertura a fessura, split-flap, dissolvenza halftone, ink bloom,
// parallasse a card e glitch a slice. Ogni ricetta produce un RenderPlan V3
// 1920x1080 a 30 fps, con durata autoriale (default 6 s, massimo 10 s).
//
// Il pack e' la source of truth C++ della famiglia; le controparti Python in
// tools/web_shots/shots_motion_lab.py sono il renderer di consegna e seguono
// la stessa coreografia, come per WebShotsNextPack.
#ifndef CHRONONTEMPLATE_WEB_MOTION_LAB_PACK_HPP
#define CHRONONTEMPLATE_WEB_MOTION_LAB_PACK_HPP

#include <array>
#include <nlohmann/json.hpp>
#include <string>

namespace chronontemplate::web {

enum class WebLabRecipe : unsigned char {
    ApertureScan,      // una fessura luminosa scorre e rivela la headline
    SplitFlap,         // quattro celle meccaniche che si assestano su 2026
    HalftoneDissolve,  // una griglia di punti si dissolve e libera la pagina
    InkBloom,          // il marker fiorisce con alone bagnato e bordo irregolare
    ParallaxDepth,     // tre card su piani diversi scorrono a velocita' diverse
    SliceGlitch        // slice orizzontali + fringe RGB che si riallineano
};

[[nodiscard]] const char* webLabName(WebLabRecipe recipe);
[[nodiscard]] const char* webCenterLabName(WebLabRecipe recipe);
[[nodiscard]] std::array<WebLabRecipe, 6> allWebLabRecipes();
[[nodiscard]] std::array<WebLabRecipe, 6> allWebCenterRecipes();

struct WebLabSpec {
    WebLabRecipe recipe{WebLabRecipe::ApertureScan};
    std::string headline{"The frame remembers what the eye forgets"};
    std::string highlight{"remembers"};
    std::string subline{"MOTION LAB / APERTURE"};
    int durationFrames{180};
    int fps{30};
    bool center{false};
    std::string outputName{};

    void validate() const;
    [[nodiscard]] std::string planName() const;
    [[nodiscard]] std::string outputStem() const;
};

[[nodiscard]] nlohmann::json buildWebLabPlan(const WebLabSpec& spec);

}  // namespace chronontemplate::web

#endif  // CHRONONTEMPLATE_WEB_MOTION_LAB_PACK_HPP
