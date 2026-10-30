// ChrononTemplate — Web Shots Next (nuove animazioni nello stile dei 28).
//
// Sei recipe riusabili costruite sulla stessa grammatica dei 28 rebuild:
// piastra + marker sweep + camera lenta. Ognuna estende un gesto visto nei
// 28 senza copiare un singolo shot: doppia evidenziazione incrociata,
// glow pulsante, tilt che si raddrizza, timeline che si disegna, caption
// che poppa, fringe CRT con flash.
//
// Pensate come base per i prossimi render: basta riempire headline/
// highlight/body, il resto (marker, camera, timing) e' gia' coreografato.
#ifndef CHRONONTEMPLATE_WEB_SHOTS_NEXT_PACK_HPP
#define CHRONONTEMPLATE_WEB_SHOTS_NEXT_PACK_HPP

#include <nlohmann/json.hpp>
#include <string>
#include <vector>

namespace chronontemplate::web {

enum class WebNextRecipe : unsigned char {
    DualMarkerCross, // due marker gialli incrociati (da 16/17/23) che si incontrano
    GlowLinePulse,   // riga glow gialla pulsante + underline draw (da 12 sabotage)
    TiltSnapReveal,  // pagina tiltata che scatta in piano (da 15/16/20)
    TimelineDash,    // linea timeline che si disegna + dot ping (da 21 seoul)
    CaptionPopCard,  // card bianca che poppa su fondo blur scuro (da 25 pizza)
    CrtFringeFlash   // headline serif con fringe RGB + flash reveal (da 07/13)
};

[[nodiscard]] const char* webNextName(WebNextRecipe r);
[[nodiscard]] std::vector<WebNextRecipe> allWebNextRecipes();

struct WebNextSpec {
    WebNextRecipe recipe{WebNextRecipe::DualMarkerCross};
    std::string headline{"New evidence changes the timeline"};
    std::string highlight{"changes the timeline"};
    std::string subline{"Editorial desk — archive rebuild"};
    std::string body{"Second line of context goes here."};
    std::string paperColor{};     // vuoto -> default della recipe
    std::string highlightColor{}; // vuoto -> default della recipe
    int durationFrames{90};
    int fps{30};
    std::string outputName{};

    void validate() const;
    [[nodiscard]] std::string planName() const;
    [[nodiscard]] std::string outputStem() const;
};

[[nodiscard]] nlohmann::json buildWebNextPlan(const WebNextSpec& spec);

} // namespace chronontemplate::web

#endif
