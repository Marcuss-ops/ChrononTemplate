// ChrononTemplate — misura reale delle larghezze testo (stb_truetype).
//
// textLayer dimensionava i box con una stima euristica: il renderer centra
// la run nel box, quindi un box sovrastimato sposta il testo a destra e
// scolla marker/highlight dalla frase. Qui misuriamo gli advance reali dal
// font indicato nello style (stessi file OTF/TTF usati dal renderer), con
// fallback alla stima se il font non si carica.
#ifndef CHRONONTEMPLATE_WEB_FONT_MEASURE_HPP
#define CHRONONTEMPLATE_WEB_FONT_MEASURE_HPP

#include <string>

namespace chronontemplate::web::shot {

// Larghezza in px di `text` a `sizePx`, misurata con gli advance del font.
// `fontRef` e' il riferimento usato nei plan (es.
// "ChrononTemplate/assets/fonts/HelveticaNeue-Bold.otf", relativo alla root
// del workspace). Ritorna un valore <= 0 se la misura fallisce (il chiamante
// usa estimateWidth come fallback).
[[nodiscard]] float measureTextWidth(const std::string& fontRef, float sizePx,
                                     const std::string& text);

} // namespace chronontemplate::web::shot

#endif
