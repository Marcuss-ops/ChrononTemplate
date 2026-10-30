// ChrononTemplate — helper JSON puri per i web shot (base riusabile).
//
// Solo nlohmann/json: nessuna dipendenza da ChrononMotion o dal lowering di
// Chronon3D, cosi' i pack dei web shot compilano ed emettono su ogni host
// (Linux via CMake, Windows via clang++ diretto) e Chronon3D valida/rende i
// piani con `chronon3d_cli validate|render --plan`.
//
// Convenzioni identiche ai pack web esistenti:
//  * spazio autore 1920x1080, top-left-down (le stesse coordinate dei Python);
//  * wirePos converte in coordinate pixel del renderer: x da sinistra, y dal
//    basso. È la convenzione dei pack WebHeadline già renderizzati su GPU;
//  * marker sweep = scale_x + position_x accoppiati (scale_x 0 -> 1 mentre il
//  * camera = samples per-frame, centrata, con push dolce e nessuna rotazione.
#ifndef CHRONONTEMPLATE_WEB_WEB_SHOT_JSON_HPP
#define CHRONONTEMPLATE_WEB_WEB_SHOT_JSON_HPP

#include <nlohmann/json.hpp>

#include <algorithm>
#include <cmath>
#include <stdexcept>
#include <cstdint>
#include <random>
#include <string>
#include <utility>
#include <vector>

namespace chronontemplate::web::shot {

using Json = nlohmann::json;

inline constexpr int kW = 1920;
inline constexpr int kH = 1080;
inline constexpr int kFps = 30;

// Font canonici: stesso vocabolario dei pack web.
inline constexpr const char* kBold = "ChrononTemplate/assets/fonts/Inter-Bold.ttf";
inline constexpr const char* kBlack = "ChrononTemplate/assets/fonts/Inter-Black.ttf";
inline constexpr const char* kPlayfair = "ChrononTemplate/assets/fonts/PlayfairDisplay.ttf";
inline constexpr const char* kRegular = "ChrononTemplate/assets/fonts/Inter-Regular.ttf";
inline constexpr const char* kMed = "ChrononTemplate/assets/fonts/Inter-Medium.ttf";
inline constexpr const char* kSemi = "ChrononTemplate/assets/fonts/Inter-SemiBold.ttf";
inline constexpr const char* kSerif = "Chronon3d/assets/fonts/FreeSerif.ttf";
inline constexpr const char* kSerifBold = "Chronon3d/assets/fonts/Georgia_Bold.ttf";
inline constexpr const char* kSerifIt = "ChrononTemplate/assets/fonts/PlayfairDisplay-Italic.ttf";
inline constexpr const char* kSerifBlkIt = "ChrononTemplate/assets/fonts/PlayfairDisplay-BlackItalic.ttf";
inline constexpr const char* kPlayfairBold = "ChrononTemplate/assets/fonts/PlayfairDisplay-Bold.ttf";
inline constexpr const char* kOswald = "ChrononTemplate/assets/fonts/Oswald.ttf";
inline constexpr const char* kOswaldBold = "ChrononTemplate/assets/fonts/Oswald-Bold.ttf";
inline constexpr const char* kOswaldMed = "ChrononTemplate/assets/fonts/Oswald-Medium.ttf";
inline constexpr const char* kDeja = "ChrononTemplate/assets/fonts/DejaVuSans.ttf";
inline constexpr const char* kHelv = "ChrononTemplate/assets/fonts/HelveticaNeue-Regular.otf";
inline constexpr const char* kHelvMed = "ChrononTemplate/assets/fonts/HelveticaNeue-Medium.otf";
inline constexpr const char* kHelvBold = "ChrononTemplate/assets/fonts/HelveticaNeue-Bold.otf";
inline constexpr const char* kArialBold = "ChrononTemplate/assets/fonts/Arial-Bold.ttf";

/// #RRGGBB -> [r,g,b,a] in 0..1 (stessa codifica di Material::rgba).
inline Json rgba(const std::string& hex, float alpha = 1.f) {
    const auto value = std::stoul(hex.substr(1), nullptr, 16);
    return Json::array({((value >> 16) & 255) / 255.0, ((value >> 8) & 255) / 255.0,
                        (value & 255) / 255.0, static_cast<double>(alpha)});
}

/// Coordinate autore (1920x1080, top-left-down) -> coordinate wire del renderer.
/// Origine al centro canvas, X a destra, Y verso l'ALTO (verificato sul lane
/// pixel-truth raw: wire [-760,-340] centra un box su (200,880) px).
/// `position` e' il centro del layer. Lo z e' assegnato da renderPlan.
inline Json wirePos(float topDownCenterX, float topDownCenterY, float z = 0.f) {
    return Json::array({topDownCenterX - float(kW) * 0.5f, float(kH) * 0.5f - topDownCenterY, z});
}

/// Depth separation between consecutive layers, in wire units. The camera
/// sits at ~1158 units, so a full stack of 40 layers moves by 2 units: the
/// perspective scale drift stays under 0.2% while the depth test still
/// resolves every layer deterministically (coplanar layers z-fight).
inline constexpr float kLayerDepthStep = 0.05f;

/// Tabella di larghezza deterministica: la geometria dei blocchi segue il
/// copy autore, non i glifi misurati (stessa scelta dei pack web).
inline float estimateWidth(const std::string& text, float size) {
    double units = 0.0;
    for (unsigned char c : text) {
        if (c == ' ') units += 0.28;
        else if (c == 'i' || c == 'l' || c == 'I' || c == '!' || c == '.' || c == ',' || c == ':') units += 0.29;
        else if (c == 'm' || c == 'w' || c == 'M' || c == 'W') units += 0.78;
        else if (c >= 'A' && c <= 'Z') units += 0.64;
        else units += 0.52;
    }
    return float(units * size);
}

inline Json rect(const std::string& id, float left, float top, float w, float h,
                 const std::string& hex, float alpha, const Json& tracks = Json::array(),
                 int duration = 90) {
    // Opaque full-frame plates: plain 3D rect centered on the canvas origin.
    // Verified white on software+Vulkan (il tipo `color` senza position resta
    // fuori canvas su questi backend).
    if (left == 0.f && top == 0.f && w == float(kW) && h == float(kH) &&
        alpha >= 0.999f && tracks.empty()) {
        Json layer = {{"id", id}, {"type", "shape"}, {"enable_3d", true},
                      {"size", Json::array({kW, kH})},
                      {"position", wirePos(float(kW) * 0.5f, float(kH) * 0.5f)},
                      {"start_frame", 0}, {"duration_frames", duration},
                      {"shape", {{"type", "rect"}, {"fill", rgba(hex, alpha)}}}};
        return layer;
    }
    const bool isMarkerColor = (hex == "#F7F7F5" && id == "cap") ||
        hex == "#C9DC28" || hex == "#E6E300" || hex == "#8F7313" ||
        hex == "#E9E600" || hex == "#F2E933" || hex == "#B3121B" || hex == "#7E1417" ||
        hex == "#8A6A08" || hex == "#E8DC4A" || hex == "#E6E32E" || hex == "#E8C84A" ||
        hex == "#E4572E" || hex == "#E8E300" || hex == "#B9A916" || hex == "#F2C500";
    const bool markerSweep = isMarkerColor && !tracks.empty() && tracks.is_array() && tracks.size() == 3 &&
        tracks[0].value("property", std::string{}) == "opacity" &&
        tracks[1].value("property", std::string{}) == "scale_x" &&
        tracks[2].value("property", std::string{}) == "position_x";
    Json geometry;
    Json layer = {{"id", id}, {"type", "shape"}, {"enable_3d", true},
                  {"size", Json::array({w, h})},
                  {"position", wirePos(left + w * 0.5f, top + h * 0.5f)},
                  {"start_frame", 0}, {"duration_frames", duration}};
    if (markerSweep) {
        // The Python Canvas.marker is a seeded rough swipe, not a hard-edged
        // rectangle. Match its top/bottom contour and its smoothstep reveal.
        // Il fill nativo Vulkan accetta contorni di 3..8 vertici: n resta
        // piccolo (7 comandi per n=2), la banda core gemella aggiunge il
        // corpo piu' denso del pennarello.
        std::uint32_t seed = 2166136261u;
        for (unsigned char c : id) seed = (seed ^ c) * 16777619u;
        std::mt19937 rng(seed);
        std::uniform_real_distribution<float> jitter(-0.9f, 0.9f);
        const int n = std::min(2, std::max(1, int(w / 26.f)));
        Json commands = Json::array();
        for (int i = 0; i <= n; ++i) {
            const float x = -w * 0.5f + w * float(i) / float(n);
            const float y = -h * 0.5f + jitter(rng) * (h * 0.045f);
            commands.push_back(Json{{"type", i == 0 ? "move_to" : "line_to"},
                                    {"point", Json::array({x, y})}});
        }
        for (int i = n; i >= 0; --i) {
            const float x = -w * 0.5f + w * float(i) / float(n);
            const float y = h * 0.5f + jitter(rng) * (h * 0.045f);
            commands.push_back(Json{{"type", "line_to"},
                                    {"point", Json::array({x, y})}});
        }
        commands.push_back(Json{{"type", "close"}});
        geometry = {{"type", "path"}, {"path", std::move(commands)},
                    {"fill", rgba(hex, alpha)}};

        const auto& keys = tracks[1]["keyframes"];
        const int begin = keys.size() >= 3 ? keys[1]["frame"].get<int>() : 0;
        const int end = keys.size() >= 3 ? keys.back()["frame"].get<int>() : begin + 1;
        Json opacityKeys = Json::array(), scaleKeys = Json::array(), xKeys = Json::array();
        for (int frame = 0; frame < duration; ++frame) {
            const float t = std::clamp(float(frame - begin) / float(std::max(1, end - begin)), 0.f, 1.f);
            const float s = t * t * (3.f - 2.f * t); // Python _ease / smoothstep
            opacityKeys.push_back(Json{{"frame", frame}, {"value", frame <= begin ? 0.0 : 1.0}});
            scaleKeys.push_back(Json{{"frame", frame}, {"value", s}});
            xKeys.push_back(Json{{"frame", frame}, {"value", -w * 0.5f * (1.f - s)}});
        }
        layer["animation"] = {{"tracks", Json::array({
            Json{{"property", "opacity"}, {"easing", "linear"}, {"keyframes", std::move(opacityKeys)}},
            Json{{"property", "scale_x"}, {"easing", "linear"}, {"keyframes", std::move(scaleKeys)}},
            Json{{"property", "position_x"}, {"easing", "linear"}, {"keyframes", std::move(xKeys)}}})}};
        layer["_native_marker_core_alpha"] = std::min(1.f, alpha < 1.f ? alpha * 1.05f : 1.f);
    } else {
        geometry = {{"type", "rect"}, {"fill", rgba(hex, alpha)}};
        if (!tracks.empty()) layer["animation"] = {{"tracks", tracks}};
    }
    layer["shape"] = std::move(geometry);
    return layer;
}

inline Json ellipse(const std::string& id, float left, float top, float w, float h,
                    const std::string& hex, float alpha, int duration = 90) {
    return {{"id", id}, {"type", "shape"}, {"enable_3d", true},
            {"size", Json::array({w, h})},
            {"position", wirePos(left + w * 0.5f, top + h * 0.5f)},
            {"start_frame", 0}, {"duration_frames", duration},
            {"shape", {{"type", "ellipse"}, {"fill", rgba(hex, alpha)}}}};
}

/// Poligono arbitrario in coordinate autore (top-left-down). Il bbox diventa
/// `size`, i punti passano relativi al centro, e `blur` aggiunge l'effetto
/// gaussiano del decoder: e' cosi' che i Python disegnano i fogli/ritagli
/// (`Canvas.poly`) prima del blur di placca.
inline Json poly(const std::string& id, const std::vector<std::pair<float, float>>& pts,
                 const std::string& hex, float alpha, int duration = 90, float blur = 0.f) {
    if (pts.size() < 3) throw std::invalid_argument("poly needs at least 3 points");
    float minx = pts[0].first, maxx = minx, miny = pts[0].second, maxy = miny;
    for (const auto& p : pts) {
        minx = std::min(minx, p.first);  maxx = std::max(maxx, p.first);
        miny = std::min(miny, p.second); maxy = std::max(maxy, p.second);
    }
    const float cx = (minx + maxx) * 0.5f, cy = (miny + maxy) * 0.5f;
    Json commands = Json::array();
    for (std::size_t i = 0; i < pts.size(); ++i)
        commands.push_back(Json{{"type", i == 0 ? "move_to" : "line_to"},
                                {"point", Json::array({pts[i].first - cx, cy - pts[i].second})}});
    commands.push_back(Json{{"type", "close"}});
    Json layer = {{"id", id}, {"type", "shape"}, {"enable_3d", true},
                  {"size", Json::array({maxx - minx, maxy - miny})},
                  {"position", wirePos(cx, cy)},
                  {"start_frame", 0}, {"duration_frames", duration},
                  {"shape", {{"type", "path"}, {"path", std::move(commands)},
                             {"fill", rgba(hex, alpha)}}}};
    if (blur > 0.f) layer["effects"] = Json::array({Json{{"type", "gaussian_blur"}, {"radius", blur}}});
    return layer;
}

/// Segmento con estremita' piatte (`Canvas.line`): poligono di 4 punti largo
/// `width`, cosi' i tratti di penna dei reference restano nitidi/angolati.
inline Json line(const std::string& id, float x1, float y1, float x2, float y2,
                 float width, const std::string& hex, float alpha, int duration = 90) {
    const float dx = x2 - x1, dy = y2 - y1;
    const float len = std::sqrt(dx * dx + dy * dy);
    if (len <= 0.0001f) throw std::invalid_argument("line needs two distinct points");
    const float nx = -dy / len * width * 0.5f, ny = dx / len * width * 0.5f;
    return poly(id, {{x1 + nx, y1 + ny}, {x2 + nx, y2 + ny},
                     {x2 - nx, y2 - ny}, {x1 - nx, y1 - ny}}, hex, alpha, duration, 0.f);
}

namespace modules {
struct EvidenceTimeline {
    static Json rail(const std::string& id, float left, float top, float width, float height,
                     const std::string& color, float alpha, int duration) {
        return rect(id,left,top,width,height,color,alpha,Json::array(),duration);
    }
    static Json point(const std::string& id, float left, float top, float width, float height,
                      const std::string& color, float alpha, int duration) {
        return ellipse(id,left,top,width,height,color,alpha,duration);
    }
};
} // namespace modules

/// Blur gaussiano di placca (Python `GaussianBlur(9)`): effetto sul layer.
inline void addBlur(Json& layer, float radius) {
    if (radius <= 0.f) return;
    Json effects = layer.contains("effects") ? layer["effects"] : Json::array();
    effects.push_back(Json{{"type", "gaussian_blur"}, {"radius", radius}});
    layer["effects"] = std::move(effects);
}

inline Json image(const std::string& id, const std::string& asset, float left, float top,
                  float w, float h, int duration = 90) {
    return {{"id", id}, {"type", "image"}, {"enable_3d", true}, {"asset", asset},
            {"position", wirePos(left + w * 0.5f, top + h * 0.5f)},
            {"size", Json::array({w, h})}, {"fit", "cover"},
            {"start_frame", 0}, {"duration_frames", duration}};
}

inline Json easedTrack(const std::string& property, float from, float to,
                       int start, int span, const std::string& easing) {
    return {{"property", property}, {"easing", easing},
            {"keyframes", Json::array({
                Json{{"frame", 0}, {"value", from}},
                Json{{"frame", std::max(1, start)}, {"value", from}},
                Json{{"frame", start + span}, {"value", to}}})}};
}

template <typename Push>
Json sortedKeys(Push push) {
    Json keys = Json::array();
    push(keys);
    std::sort(keys.begin(), keys.end(), [](const Json& a, const Json& b) {
        return a["frame"].get<int>() < b["frame"].get<int>();
    });
    return keys;
}

/// Marker/highlighter: opacity + scale_x crescono mentre il centro scorre,
/// cosi il blocco si svela da sinistra come nei Python.
inline Json legacySweepTracks(float width, int begin, int span) {
    auto reveal = [&](Json& keys) {
        keys.push_back(Json{{"frame", std::max(0, begin - 8)}, {"value", 0.0}});
        keys.push_back(Json{{"frame", begin}, {"value", 0.0}});
        keys.push_back(Json{{"frame", begin + span}, {"value", 1.0}});
    };
    auto slide = [&](Json& keys) {
        keys.push_back(Json{{"frame", begin}, {"value", -width * 0.5}});
        keys.push_back(Json{{"frame", begin + span}, {"value", 0.0}});
    };
    return Json::array({
        Json{{"property", "opacity"}, {"easing", "in_out_cubic"}, {"keyframes", sortedKeys(reveal)}},
        Json{{"property", "scale_x"}, {"easing", "in_out_cubic"}, {"keyframes", sortedKeys(reveal)}},
        Json{{"property", "position_x"}, {"easing", "in_out_cubic"}, {"keyframes", sortedKeys(slide)}}});
}

// Reusable animation primitive consumed by every editorial marker scene.
namespace modules {
struct TextHighlight {
    static Json tracks(float width, int begin, int span) {
        auto reveal = [&](Json& keys) {
            keys.push_back(Json{{"frame", std::max(0, begin - 8)}, {"value", 0.0}});
            keys.push_back(Json{{"frame", begin}, {"value", 0.0}});
            keys.push_back(Json{{"frame", begin + span}, {"value", 1.0}});
        };
        auto slide = [&](Json& keys) {
            keys.push_back(Json{{"frame", begin}, {"value", -width * 0.5}});
            keys.push_back(Json{{"frame", begin + span}, {"value", 0.0}});
        };
        return Json::array({
            Json{{"property", "opacity"}, {"easing", "in_out_cubic"}, {"keyframes", sortedKeys(reveal)}},
            Json{{"property", "scale_x"}, {"easing", "in_out_cubic"}, {"keyframes", sortedKeys(reveal)}},
            Json{{"property", "position_x"}, {"easing", "in_out_cubic"}, {"keyframes", sortedKeys(slide)}}});
    }
    static Json layer(const std::string& id, float left, float top, float width,
                      float height, const std::string& color, float alpha,
                      int begin, int span, int duration) {
        return rect(id,left,top,width,height,color,alpha * 0.62f,
                    tracks(width,begin,span),duration);
    }
};
} // namespace modules

inline Json sweepTracks(float width, int begin, int span) {
    return modules::TextHighlight::tracks(width,begin,span);
}

/// Baked linear blur animator (il decoder richiede keyframe campionati).
inline Json blurAnimator(const std::string& id, float blur, int duration) {
    Json selector = Json::object();
    selector["id"] = id + "_sel";
    selector["unit"] = "character";
    selector["shape"] = "square";
    selector["order"] = "forward";
    selector["combine"] = "replace";
    selector["exclude_spaces"] = false;
    selector["start"] = Json{{"keyframes", Json::array({Json{{"frame", 0}, {"value", 0.0}}})},
                             {"easing", "linear"}};
    selector["end"] = Json{{"keyframes", Json::array({Json{{"frame", 0}, {"value", 100.0}}})},
                           {"easing", "linear"}};
    Json property = Json::object();
    property["property"] = "blur";
    property["easing"] = "linear";
    property["keyframes"] = Json::array({Json{{"frame", 0}, {"value", blur}},
                                         Json{{"frame", duration - 1}, {"value", blur}}});
    Json animator = Json::object();
    animator["id"] = id + "_blur";
    animator["selectors"] = Json::array({selector});
    animator["properties"] = Json::array({property});
    return animator;
}

namespace modules {
struct FocusMask {
    static Json textBlur(const std::string& id, float amount, int duration) {
        return blurAnimator(id,amount,duration);
    }
};
} // namespace modules

/// Letter-spacing (PIL `spacing=` nei call Python): animator statico su `tracking`.
inline Json trackingAnimator(const std::string& id, float px, int duration) {
    Json selector = Json::object();
    selector["id"] = id + "_trk_sel";
    selector["unit"] = "character";
    selector["shape"] = "square";
    selector["order"] = "forward";
    selector["combine"] = "replace";
    selector["exclude_spaces"] = false;
    selector["start"] = Json{{"keyframes", Json::array({Json{{"frame", 0}, {"value", 0.0}}})},
                             {"easing", "linear"}};
    selector["end"] = Json{{"keyframes", Json::array({Json{{"frame", 0}, {"value", 100.0}}})},
                           {"easing", "linear"}};
    Json property = Json::object();
    property["property"] = "tracking";
    property["easing"] = "linear";
    property["keyframes"] = Json::array({Json{{"frame", 0}, {"value", px}},
                                         Json{{"frame", duration - 1}, {"value", px}}});
    Json animator = Json::object();
    animator["id"] = id + "_trk";
    animator["selectors"] = Json::array({selector});
    animator["properties"] = Json::array({property});
    return animator;
}

/// Un layer di testo. `blur > 0` aggiunge l'animatore di blur, `slot >= 0`
/// sfalsa fade+rise come i pannelli secondari dei reference.
/// `anchor` replica la convenzione PIL del kit Python:
///   primo char  = orizzontale: 'l' (left), 'm' (middle), 'r' (right)
///   secondo char = verticale:  'a' (ascender top), 'm' (middle)
/// In modalità 'l' la run esce dal bordo sinistro di `left`; in 'm'/'r' la
/// run è centrata/ancorata a destra su `left` (il call site passa la x PIL).
inline Json textLayer(const std::string& id, const std::string& text, float left, float top,
                      float size, const char* font, const std::string& fill, int duration,
                      float blur = 0.f, int slot = -1, float opacity = 1.f,
                      const char* anchor = "la", float tracking = 0.f) {
    const bool hCenter = anchor[0] == 'm';
    const bool hRight  = anchor[0] == 'r';
    const bool vMiddle = anchor[1] == 'm';
    const bool edgeLeft = !hCenter && !hRight;
    // The RenderPlan text renderer wraps at `size[0]`. The heuristic advance
    // is only for aligning the authored left edge; using it as the wrap box
    // clipped real-font runs (notably long headlines and small source labels).
    // Builders author each line explicitly, so grant the full remaining canvas
    // width and preserve that left edge as the box origin. Centered/right
    // runs get a canvas-wide box so overlong Python single-line runs (e.g.
    // the CNBC deck) stay on one line and overflow like PIL does.
    const float advance = estimateWidth(text, size) * 1.07f;
    const float w = edgeLeft
        ? std::max(60.f, left >= 0.f ? float(kW) - left
                                     : float(kW) + std::min(0.f, left))
        : float(kW) * 2.f;
    // Large display fonts have taller ascender/line metrics in Chronon3D than
    // the CSS-like 1.65 estimate; leave room so exact-size headlines do not
    // get clipped by the text frame.
    const float h = size * (size >= 70.f ? 2.15f : 1.65f);
    // Coordinate contract matches the Python kit's anchors:
    //   - `text_align: left` hangs the run from the box's left edge, so the
    //     run starts exactly at `left` regardless of advance estimation.
    //   - The renderer vertically centers the 1.2em line box inside `h`;
    //     measured mapping: cap_top = position.y - 0.407*size. PIL's "la"
    //     anchor puts the ascender line at `top`, i.e. cap_top = top +
    //     (ascent - capHeight) ~= top + 0.242*size, so position.y = top +
    //     0.65*size reproduces the Python render (verified on shot 03).
    //   - 'm' horizontal centers the run on `left` (box center == position.x);
    //     'r' right-aligns it; 'm' vertical centers the line box on `top`.
    // The native text renderer centers the glyph run inside the box (it does
    // not honour text_align), so the box center is what lands on screen. Place
    // it at the run's own center: left edge + half the measured advance.
    const float px = hCenter ? left : (hRight ? left - advance * 0.5f : left + advance * 0.5f);
    const float py = vMiddle ? top : top + size * 0.65f;
    Json position = wirePos(px, py);
    const char* align = hCenter ? "center" : (hRight ? "right" : "left");
    Json layer = {{"id", id}, {"type", "text"}, {"text", text},
                  {"size", Json::array({w, h})},
                  {"position", std::move(position)},
                  {"enable_3d", true},
                  {"style", {{"font", font}, {"font_size", size}, {"fill", fill},
                             {"text_align", align}, {"fit_mode", "none"}}},
                  {"start_frame", 0}, {"duration_frames", duration}};
    if (opacity != 1.f) layer["opacity"] = opacity;
    Json animators = Json::array();
    if (blur > 0.f) animators.push_back(modules::FocusMask::textBlur(id, blur, duration));
    if (tracking != 0.f) animators.push_back(trackingAnimator(id, tracking, duration));
    if (!animators.empty()) layer["text_animators"] = std::move(animators);
    // `slot` is kept in the helper signature for source compatibility, but
    // static text stays at its authored position. The old generic fade/rise
    // track wrote absolute position_y values and pushed unrelated headlines
    // off canvas. Python shots animate the camera/marker per shot instead.
    (void)slot;
    return layer;
}

namespace modules {
struct HeadlineComposition {
    static Json line(const std::string& id, const std::string& copy, float left, float top,
                     float size, const char* font, const std::string& color,
                     int duration, const char* anchor = "la") {
        return textLayer(id,copy,left,top,size,font,color,duration,0.f,-1,1.f,anchor);
    }
};
} // namespace modules

/// Grain + vignette sulla piastra di fondo (gli stessi effetti dei reference).
inline void addNoiseVignette(Json& background, float grain, int seed, float vignette) {
    Json effects = Json::array();
    if (grain > 0.f) effects.push_back(Json{{"type", "noise"}, {"amount", grain}, {"seed", seed}});
    if (vignette > 0.f) {
        effects.push_back(Json{{"type", "vignette"}, {"radius", 0.72},
                               {"softness", 0.62}, {"amount", vignette}});
    }
    if (!effects.empty()) background["effects"] = std::move(effects);
}

namespace modules {
struct DocumentLayer {
    static void finish(Json& layer, float grain, int seed, float vignette) {
        addNoiseVignette(layer,grain,seed,vignette);
    }
};
} // namespace modules

/// Chrome del player YouTube (le reference sono player in pausa).
inline void addPlayerChrome(Json& layers, const std::string& timestamp, double progress,
                            int duration = 90) {
    layers.push_back(rect("player_fade", 0, 936, 1920, 144, "#050607", 0.55, Json::array(), duration));
    layers.push_back(rect("player_track", 18, 1004, 1884, 3, "#B8B8B8", 0.56, Json::array(), duration));
    layers.push_back(rect("player_played", 18, 1003, float(1884 * progress), 5, "#F00032", 1.f,
                          Json::array(), duration));
    layers.push_back(ellipse("player_scrubber", float(18 + 1884 * progress - 6), 999, 13, 13,
                             "#F00032", 1.f, duration));
    layers.push_back(textLayer("player_play", "▶", 31, 1011, 31, kDeja, "#F5F5F5", duration));
    layers.push_back(textLayer("player_timestamp", timestamp, 155, 1017, 20, kRegular, "#E8E8E8", duration));
    layers.push_back(textLayer("player_icons", "▣   ⚙   CC", 1673, 1014, 22, kDeja, "#E9E9E9", duration));
}

/// Distanza camera che mappa 1 unita' = 1 px: il piano a z=0 riempie il canvas.
/// Con fov verticale 50deg: (1080/2) / tan(25deg) = 1158.06.
inline constexpr float kCameraBaseDistance = 1158.06f;

/// Camera samples per-frame: asse centrale e push molto leggero, senza yaw,
/// roll, tilt o oscillazioni. Il push e' uno zoom ottico minimo, quindi non
/// sposta gli elementi rispetto al centro del frame.
inline Json cameraSamples(int duration) {
    Json samples = Json::array();
    for (int frame = 0; frame < duration; ++frame) {
        const float progress = duration > 1 ? float(frame) / float(duration - 1) : 1.f;
        const float zoom = 1.f + 0.035f * progress;
        Json camera = {
            {"type", "perspective"},
            {"position", Json::array({0.f, 0.f, -kCameraBaseDistance})},
            {"rotation_deg", Json::array({0.f, 0.f, 0.f})},
            {"fov_deg", 50.f}, {"near", 100.f}, {"far", 10000.f}, {"zoom", zoom},
            {"sensor_width_mm", 36.f},
            {"lens_shift", Json::array({0.f, 0.f})},
            {"dof", Json{{"enabled", false}, {"focus_distance", kCameraBaseDistance},
                         {"aperture", 0.f}, {"max_blur", 0.f}}}};
        samples.push_back(Json{{"frame", frame}, {"camera", std::move(camera)}});
    }
    return samples;
}

/// Port of Shot.camera()/apply_camera() camera inputs. The Python authoring
/// data is a linear (zoom, center-x, center-y) move; keep the camera axis
/// aligned to the pixel-authored layer plane instead of applying a shared
/// dolly and yaw to every shot.
inline Json cameraSamples(int duration, double zoomFrom, double cxFrom, double cyFrom,
                          double zoomTo, double cxTo, double cyTo) {
    Json samples = Json::array();
    for (int frame = 0; frame < duration; ++frame) {
        const double t = duration > 1 ? double(frame) / double(duration - 1) : 1.0;
        const double zoom = zoomFrom + (zoomTo - zoomFrom) * t;
        const double cx = cxFrom + (cxTo - cxFrom) * t;
        const double cy = cyFrom + (cyTo - cyFrom) * t;
        Json camera = {
            {"type", "perspective"},
            {"position", Json::array({(cx - 0.5) * kW, (0.5 - cy) * kH,
                                      -kCameraBaseDistance})},
            {"rotation_deg", Json::array({0.f, 0.f, 0.f})},
            {"fov_deg", 50.f}, {"near", 100.f}, {"far", 10000.f}, {"zoom", zoom},
            {"sensor_width_mm", 36.f}, {"lens_shift", Json::array({0.f, 0.f})},
            {"dof", Json{{"enabled", false}, {"focus_distance", kCameraBaseDistance},
                         {"aperture", 0.f}, {"max_blur", 0.f}}}};
        samples.push_back(Json{{"frame", frame}, {"camera", std::move(camera)}});
    }
    return samples;
}

namespace modules {
struct DocumentCamera {
    static Json samples(int duration, double zoomFrom, double cxFrom, double cyFrom,
                        double zoomTo, double cxTo, double cyTo) {
        return cameraSamples(duration,zoomFrom,cxFrom,cyFrom,zoomTo,cxTo,cyTo);
    }
};
} // namespace modules

/// Affine per-frame del riferimento Python apply_camera(): crop attorno a
/// (cx, cy) con zoom e resize su 1920x1080, vincolato ai bordi della piastra.
/// Espressa come offset wire (origine centro, Y up) sommato alla base del
/// layer: off = base*(z-1) + (tx, ty), con tx = (960-x0)*z - 960 e
/// ty = y0*z - 540*(z-1)  [x0,y0 = crop top-left in px]. Il renderer somma le
/// track position_* alla base, quindi questi offset bucati nelle track
/// riproducono il crop 1:1 (verificato: carta ferma a frame 0, crop a 89).
struct CamAffine { double z{1.0}, tx{0.0}, ty{0.0}; };

inline std::vector<CamAffine> cameraAffines(const Json& samples, int duration) {
    std::vector<CamAffine> out(static_cast<std::size_t>(std::max(1, duration)));
    if (!samples.is_array()) return out;
    for (const Json& sample : samples) {
        if (!sample.is_object() || !sample.contains("camera") || !sample.contains("frame"))
            continue;
        const int frame = int(std::lround(sample.at("frame").get<double>()));
        if (frame < 0 || frame >= int(out.size())) continue;
        const Json& cam = sample.at("camera");
        const double zoom = std::max(1e-6, cam.value("zoom", 1.0));
        double cx = 0.5, cy = 0.5;
        if (cam.contains("position") && cam["position"].is_array() && cam["position"].size() >= 2) {
            cx = cam["position"][0].get<double>() / double(kW) + 0.5;
            cy = 0.5 - cam["position"][1].get<double>() / double(kH);
        }
        const double cw = double(kW) / zoom;
        const double ch = double(kH) / zoom;
        const double x0 = std::clamp(cx * double(kW) - cw * 0.5, 0.0, std::max(0.0, double(kW) - cw));
        const double y0 = std::clamp(cy * double(kH) - ch * 0.5, 0.0, std::max(0.0, double(kH) - ch));
        out[static_cast<std::size_t>(frame)] =
            CamAffine{zoom, (double(kW) * 0.5 - x0) * zoom - double(kW) * 0.5,
                       y0 * zoom - double(kH) * 0.5 * (zoom - 1.0)};
    }
    return out;
}

/// Stesse curve di easing del renderer (glm: cubicEase*/backEaseOut).
inline double easingEval(const std::string& name, double u) {
    u = std::clamp(u, 0.0, 1.0);
    if (name == "in_out_cubic") return u < 0.5 ? 4.0 * u * u * u
                                               : 1.0 - std::pow(-2.0 * u + 2.0, 3.0) / 2.0;
    if (name == "out_cubic") { const double f = u - 1.0; return f * f * f + 1.0; }
    if (name == "in_cubic") return u * u * u;
    if (name == "out_back") { const double c1 = 1.70158, n = u - 1.0;
                               return 1.0 + n * n * ((c1 + 1.0) * n + c1); }
    return u; // linear
}

/// Valore di una track a un frame intero (clamp fuori intervallo).
inline double trackValueAt(const Json& track, int frame) {
    if (!track.contains("keyframes")) return 0.0;
    const Json& keys = track.at("keyframes");
    if (keys.empty()) return 0.0;
    const std::string ease = track.value("easing", std::string{"linear"});
    const double f = double(frame);
    if (f <= keys.front().at("frame").get<double>()) return keys.front().at("value").get<double>();
    if (f >= keys.back().at("frame").get<double>()) return keys.back().at("value").get<double>();
    for (std::size_t i = 1; i < keys.size(); ++i) {
        const double f0 = keys[i - 1].at("frame").get<double>();
        const double f1 = keys[i].at("frame").get<double>();
        if (f <= f1) {
            const double v0 = keys[i - 1].at("value").get<double>();
            const double v1 = keys[i].at("value").get<double>();
            const double u = f1 > f0 ? (f - f0) / (f1 - f0) : 1.0;
            return v0 + (v1 - v0) * easingEval(ease, u);
        }
    }
    return keys.back().at("value").get<double>();
}

/// Baking dell'affine camera su un layer non-marker. Il moto autore (se c'e')
/// resta intatto: la posizione finale autore e' (base + track) con scala
/// attorno al centro del layer, quindi la composizione con p -> p*z + t e':
///   position = base*(z-1) + z*track + t     scale = track_scale * z
/// I layer senza position (le lastre color di piena pagina) restano fermi:
/// il crop della camera non esce mai dalla piastra.
inline void bakeCameraTracks(Json& layer, const std::vector<CamAffine>& cam) {
    if (!layer.contains("position") || !layer["position"].is_array() ||
        layer["position"].size() < 2)
        return;
    // Keep text in the authored screen composition and full-frame plates
    // pinned to the canvas. Baking camera transforms into these two layer
    // classes makes Vulkan clip glyph runs and expose black beyond backgrounds.
    if (layer.value("type", std::string{}) == "text") return;
    if (layer.value("type", std::string{}) == "shape" && layer.contains("size") &&
        layer["size"].is_array() && layer["size"].size() >= 2 &&
        std::abs(layer["size"][0].get<double>() - kW) < 0.5 &&
        std::abs(layer["size"][1].get<double>() - kH) < 0.5) return;
    bool identity = true;
    for (const auto& a : cam)
        if (a.z != 1.0 || a.tx != 0.0 || a.ty != 0.0) { identity = false; break; }
    if (identity) return;
    const double px = layer["position"][0].get<double>();
    const double py = layer["position"][1].get<double>();
    static constexpr const char* kCamProps[4] = {"position_x", "position_y", "scale_x", "scale_y"};
    Json existing[4]; // null = nessuna track autore per quella proprieta'
    Json kept = Json::array();
    if (layer.contains("animation") && layer["animation"].contains("tracks")) {
        for (const Json& track : layer["animation"]["tracks"]) {
            const std::string prop = track.value("property", std::string{});
            int hit = -1;
            for (int i = 0; i < 4; ++i)
                if (prop == kCamProps[i]) hit = i;
            if (hit >= 0) existing[hit] = track;
            else kept.push_back(track);
        }
    }
    Json pxK = Json::array(), pyK = Json::array(), sxK = Json::array(), syK = Json::array();
    for (std::size_t f = 0; f < cam.size(); ++f) {
        const auto& a = cam[f];
        const double exX  = existing[0].is_null() ? 0.0 : trackValueAt(existing[0], int(f));
        const double exY  = existing[1].is_null() ? 0.0 : trackValueAt(existing[1], int(f));
        const double exSx = existing[2].is_null() ? 1.0 : trackValueAt(existing[2], int(f));
        const double exSy = existing[3].is_null() ? 1.0 : trackValueAt(existing[3], int(f));
        pxK.push_back(Json{{"frame", int(f)}, {"value", px * (a.z - 1.0) + a.z * exX + a.tx}});
        pyK.push_back(Json{{"frame", int(f)}, {"value", py * (a.z - 1.0) + a.z * exY + a.ty}});
        sxK.push_back(Json{{"frame", int(f)}, {"value", exSx * a.z}});
        syK.push_back(Json{{"frame", int(f)}, {"value", exSy * a.z}});
    }
    kept.push_back(Json{{"property", "position_x"}, {"easing", "linear"}, {"keyframes", std::move(pxK)}});
    kept.push_back(Json{{"property", "position_y"}, {"easing", "linear"}, {"keyframes", std::move(pyK)}});
    kept.push_back(Json{{"property", "scale_x"}, {"easing", "linear"}, {"keyframes", std::move(sxK)}});
    kept.push_back(Json{{"property", "scale_y"}, {"easing", "linear"}, {"keyframes", std::move(syK)}});
    layer["animation"] = Json{{"tracks", std::move(kept)}};
}

/// Envelope `chronon.render-plan.v3` completa della composizione.
///
/// Con una camera prospettica il renderer fa depth test: layer complanari
/// si contengono a vicenda. Ogni layer riceve uno z leggermente piu'
/// vicino alla camera del precedente (vedi kLayerDepthStep), cosi' il
/// renderer conserva l'ordine autoriale del builder.
inline Json renderPlan(const std::string& jobId, int duration, const Json& layers,
                       const Json& cameraSamplesJson) {
    Json stack = Json::array();
    const std::vector<CamAffine> camA = cameraAffines(cameraSamplesJson, duration);
    for (const Json& authored : layers) {
        Json layer = authored;
        const bool hasMarkerCore = layer.contains("_native_marker_core_alpha");
        const double coreAlpha = hasMarkerCore ? layer["_native_marker_core_alpha"].get<double>() : 1.0;
        layer.erase("_native_marker_core_alpha");
        // Painter order: i layer successivi siedono piu' vicini alla camera
        // (camera a z=-1158: z piu' negativo = piu' vicino). Il core del
        // marker segue subito il bordo grezzo cosi' resta sopra di esso e
        // sotto i glifi del testo.
        auto pushWithDepth = [&](Json l) {
            if (l.contains("position") && l["position"].is_array() &&
                l["position"].size() >= 3)
                l["position"][2] = -kLayerDepthStep * float(stack.size());
            stack.push_back(std::move(l));
        };
        pushWithDepth(layer);
        if (hasMarkerCore) {
            // Banda core del pennarello (Python: rect denso al 56% altezza):
            // stesso centro, stesse track di sweep del bordo, un layer solo.
            Json core = authored;
            core.erase("_native_marker_core_alpha");
            const std::string id = authored.value("id", std::string{});
            const float w = authored["size"][0].get<float>();
            const float h = authored["size"][1].get<float>();
            core["id"] = id + "_core";
            core["size"] = Json::array({w, h * 0.56f});
            core["shape"] = {{"type", "rect"}, {"fill", authored["shape"]["fill"]}};
            if (core["shape"]["fill"].is_array()) core["shape"]["fill"][3] = coreAlpha;
            pushWithDepth(std::move(core));
        }
    }
    // La camera del renderer resta inerte su questi layer: il push autore e'
    // bucato nelle track (bakeCameraTracks) cosi' la composizione coincide
    // con apply_camera() del kit Python. I campioni restano nel piano per
    // ispezione ma non vengono applicati due volte.
    for (Json& l : stack) bakeCameraTracks(l, camA); // single transform
    // I layer sono 3D con origine al centro canvas (Y verso il basso):
    // lo z di pila qui sopra conserva l'ordine autoriale nel depth test.
    return {{"schema", "chronon.render-plan.v3"}, {"version", 3}, {"job_id", jobId},
            {"canvas", {{"width", kW}, {"height", kH}, {"fps_num", kFps}, {"fps_den", 1},
                        {"duration_frames", duration}}},
            {"layers", std::move(stack)},
            {"camera", cameraSamples(1, 1.0, 0.5, 0.5, 1.0, 0.5, 0.5)[0]["camera"]},
            {"camera_samples", cameraSamples(duration, 1.0, 0.5, 0.5, 1.0, 0.5, 0.5)}};
}

} // namespace chronontemplate::web::shot

#endif
