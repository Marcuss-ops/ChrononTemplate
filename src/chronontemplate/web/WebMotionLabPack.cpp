// ChrononTemplate web.WebMotionLabPack — sei esperimenti di grammatica web.
//
// Stessa base dei pack web (piastra 1920x1080 + layer RenderPlan V3), ma ogni
// ricetta introduce un gesto nuovo rispetto ai 28 rebuild, alle 6 recipe next,
// alle 24 varianti marker e ai 12 motion classics:
//   * apertura a fessura che rivela la headline,
//   * split-flap meccanico su quattro celle,
//   * dissolvenza halftone di una griglia di punti,
//   * ink bloom con alone bagnato e bordo irregolare,
//   * parallasse a tre card su piani diversi,
//   * glitch a slice orizzontali con fringe RGB.
//
// Tutti i piani sono deterministici e fail-closed: nessun asset esterno, nessun
// path assoluto, nessun layer fuori canvas.
#include "chronontemplate/web/WebMotionLabPack.hpp"

#include "chronontemplate/web/WebShotJson.hpp"

#include <algorithm>
#include <cmath>
#include <stdexcept>
#include <string>
#include <vector>

namespace chronontemplate::web {
namespace {

using Json = nlohmann::json;
using namespace shot;

constexpr const char* kInk = "#F4EFE7";
constexpr const char* kMuted = "#8E8A82";
constexpr const char* kPaper = "#EFEAE1";
constexpr const char* kDark = "#0B0D10";
constexpr const char* kAccent = "#E4572E";
constexpr const char* kAmber = "#E8871E";
constexpr const char* kAcid = "#E6E300";
constexpr const char* kCyan = "#67B9D4";
constexpr const char* kAnton = "ChrononTemplate/assets/fonts/Anton-Regular.ttf";

[[noreturn]] void fail(const std::string& message) {
    throw std::invalid_argument("WebLabSpec: " + message);
}

Json textAnimation(Json layer, Json tracks) {
    layer["animation"] = Json{{"tracks", std::move(tracks)}};
    return layer;
}

Json opacityKeys(std::initializer_list<std::pair<int, double>> keys) {
    Json out = Json::array();
    for (const auto& [frame, value] : keys) {
        out.push_back(Json{{"frame", frame}, {"value", value}});
    }
    return out;
}

/// Jitter orizzontale a impulsi: usato dalle slice del glitch. Ogni burst
/// decade verso zero, cosi' il frame finale e' sempre pulito.
Json jitterTrack(int start, int end, float amplitude) {
    Json keys = Json::array();
    keys.push_back(Json{{"frame", 0}, {"value", 0.0}});
    for (int frame = start; frame < end; frame += 4) {
        const float decay = 1.f - float(frame - start) / float(std::max(1, end - start));
        const float value = ((frame / 4) % 2 == 0) ? amplitude * decay : -amplitude * decay;
        keys.push_back(Json{{"frame", frame}, {"value", value}});
    }
    keys.push_back(Json{{"frame", end}, {"value", 0.0}});
    return Json{{"property", "position_x"}, {"easing", "linear"},
                {"keyframes", std::move(keys)}};
}

float prefixWidth(const std::string& text, const std::string& part, float size,
                  const char* font) {
    const auto at = text.find(part);
    if (at == std::string::npos || at == 0) return 0.f;
    return measuredTextWidth(text.substr(0, at), size, font);
}

void addGrid(Json& layers, int lines, float top, float step, float alpha, int duration) {
    for (int i = 0; i < lines; ++i) {
        layers.push_back(rect("grid_" + std::to_string(i), 90.f, top + float(i) * step,
                              1740.f, 1.f, kInk, alpha, Json::array(), duration));
    }
}

// ── Center-only cuts ────────────────────────────────────────────────────────
// The motion stays the same, the editorial chrome does not: one statement,
// optically centered, with nothing above, below or in the corners.
float centeredLeft(const std::string& text, float size, const char* font) {
    return (1920.f - measuredTextWidth(text, size, font)) * 0.5f;
}

float centeredTop(float size) {
    return (1080.f - size * 1.65f) * 0.5f;
}

Json centerCamera(int duration, double zoomTo = 1.015) {
    return cameraSamples(duration, 1.0, 0.5, 0.5, zoomTo, 0.5, 0.5);
}

Json scanSettleTrack(int duration) {
    Json keys = Json::array({Json{{"frame", 0}, {"value", -1050.0}}});
    const int settle = std::min(duration - 1, 106);
    keys.push_back(Json{{"frame", settle}, {"value", 390.0}});
    if (settle < duration - 1) {
        keys.push_back(Json{{"frame", duration - 1}, {"value", 390.0}});
    }
    return Json{{"property", "position_y"}, {"easing", "in_out_cubic"},
                {"keyframes", std::move(keys)}};
}

// ── 1. Aperture scan ────────────────────────────────────────────────────────
Json buildApertureScan(const WebLabSpec& spec, int D) {
    const float size = 76.f;
    Json layers = Json::array();

    Json bg = rect("paper", 0, 0, 1920, 1080, kDark, 1.f, Json::array(), D);
    addNoiseVignette(bg, 0.010f, 4101, 0.36f);
    layers.push_back(std::move(bg));
    addGrid(layers, 9, 150.f, 96.f, 0.035f, D);

    layers.push_back(textLayer("kicker", "MOTION LAB / APERTURE", 120, 92, 22, kOswald,
                               kAccent, D));
    layers.push_back(textLayer("meta", "SCAN 06  ·  1920 x 1080", 1800, 96, 18, kRegular,
                               kMuted, D, 0.f, -1, 1.f, "ra"));

    // La headline esiste in due copie: una spenta, sempre visibile, e una
    // luminosa che si accende mentre la fessura la attraversa.
    layers.push_back(textLayer("headline_dim", spec.headline, 150, 380, size, kHelvBold,
                               kInk, D, 0.f, -1, 0.13f));
    Json marker = rect("aperture_marker",
                       150.f + prefixWidth(spec.headline, spec.highlight, size, kHelvBold),
                       470.f, measuredTextWidth(spec.highlight, size, kHelvBold) + 26.f,
                       88.f, kAccent, 0.42f, Json::array(), D);
    marker["animation"]["tracks"] = Json::array();
    marker["animation"]["tracks"].push_back(
        Json{{"property", "opacity"}, {"easing", "in_out_cubic"},
             {"keyframes", opacityKeys({{0, 0.0}, {18, 0.0}, {36, 1.0}, {118, 1.0},
                                        {146, 0.0}, {D - 1, 0.0}})}});
    layers.push_back(std::move(marker));

    Json live = textLayer("headline_live", spec.headline, 150, 380, size, kHelvBold,
                          kInk, D);
    live["animation"]["tracks"] = Json::array();
    live["animation"]["tracks"].push_back(
        Json{{"property", "opacity"}, {"easing", "in_out_cubic"},
             {"keyframes", opacityKeys({{0, 0.0}, {16, 0.0}, {34, 1.0}, {118, 1.0},
                                        {146, 0.13}, {D - 1, 0.13}})}});
    layers.push_back(std::move(live));

    const Json scan = easedTrack("position_y", 36.f, -1050.f, 0, D - 1, "in_out_cubic");
    layers.push_back(textAnimation(rect("scan_top", 0, -2, 1920, 3, kAccent, 0.92f,
                                        Json::array(), D), Json::array({scan})));
    layers.push_back(textAnimation(rect("scan_bottom", 0, 232, 1920, 2, kInk, 0.36f,
                                        Json::array(), D), Json::array({scan})));
    layers.push_back(textAnimation(textLayer("scan_label", "APERTURE  220 px", 120, -36,
                                             17, kOswald, kAccent, D), Json::array({scan})));

    layers.push_back(textLayer("subline", spec.subline, 150, 560, 28, kRegular, kMuted, D));
    layers.push_back(rect("footer_rule", 150, 984, 1620, 2, kInk, 0.18f, Json::array(), D));
    layers.push_back(textLayer("footer", "CHRONON / MOTION LAB  ·  EXPERIMENT 01", 150, 1006,
                               16, kOswald, kMuted, D));
    return renderPlan(spec.planName(), D, layers, cameraSamples(D));
}

// ── 2. Split flap ───────────────────────────────────────────────────────────
Json buildSplitFlap(const WebLabSpec& spec, int D) {
    Json layers = Json::array();
    Json bg = rect("paper", 0, 0, 1920, 1080, "#0A0908", 1.f, Json::array(), D);
    addNoiseVignette(bg, 0.012f, 4202, 0.34f);
    layers.push_back(std::move(bg));

    layers.push_back(textLayer("kicker", "CHRONON / DEPARTURES", 120, 92, 22, kOswald,
                               kAmber, D));
    layers.push_back(textLayer("meta", "SIGNAL BOARD 06", 1800, 96, 18, kRegular, kMuted,
                               D, 0.f, -1, 1.f, "ra"));

    const char* digits[4] = {"2", "0", "2", "6"};
    const char* ghosts[4] = {"9", "4", "8", "3"};
    const char* labels[4] = {"REV", "SIG", "NOW", "06"};
    const float cellX[4] = {355.f, 665.f, 975.f, 1285.f};
    const float cellW = 280.f;
    for (int i = 0; i < 4; ++i) {
        const float x = cellX[i];
        const float cx = x + cellW * 0.5f;
        layers.push_back(rect("cell_" + std::to_string(i), x, 240.f, cellW, 430.f,
                              "#15130F", 1.f, Json::array(), D));
        layers.push_back(rect("cell_edge_" + std::to_string(i), x, 240.f, cellW, 2.f,
                              kInk, 0.14f, Json::array(), D));
        layers.push_back(rect("seam_" + std::to_string(i), x, 452.f, cellW, 2.f, kInk,
                              0.16f, Json::array(), D));
        layers.push_back(textLayer("ghost_" + std::to_string(i), ghosts[i], cx, 452.f,
                                   210, kAnton, kInk, D, 0.f, -1, 0.10f, "mm"));

        const int start = 12 + i * 16;
        Json digit = textLayer("digit_" + std::to_string(i), digits[i], cx, 452.f, 230,
                               kAnton, kInk, D, 0.f, -1, 1.f, "mm");
        digit["animation"] = Json{{"tracks", Json::array({
            easedTrack("opacity", 0.f, 1.f, start, 8, "out_cubic"),
            easedTrack("position_y", 120.f, 0.f, start, 16, "out_cubic"),
            easedTrack("scale_y", 0.35f, 1.f, start, 16, "out_back")})}};
        layers.push_back(std::move(digit));

        Json flip = rect("flip_" + std::to_string(i), x, 242.f, cellW, 3.f, kAmber, 0.85f,
                         Json::array(), D);
        const int flipEnd = start + 24;
        flip["animation"]["tracks"] = Json::array();
        flip["animation"]["tracks"].push_back(
            Json{{"property", "opacity"}, {"easing", "in_out_cubic"},
                 {"keyframes", opacityKeys({{0, 0.0}, {start, 0.0}, {start + 4, 1.0},
                                            {start + 16, 1.0}, {flipEnd, 0.0},
                                            {D - 1, 0.0}})}});
        flip["animation"]["tracks"].push_back(
            easedTrack("position_y", 0.f, -210.f, start, 16, "in_out_cubic"));
        layers.push_back(std::move(flip));

        layers.push_back(textLayer("label_" + std::to_string(i), labels[i], cx, 700.f, 18,
                                   kOswald, kMuted, D, 0.f, -1, 1.f, "ma"));
    }

    layers.push_back(textLayer("headline", spec.headline, 150, 780, 40, kOswald, kInk, D));
    layers.push_back(textLayer("subline", spec.subline, 150, 840, 24, kRegular, kMuted, D));
    layers.push_back(rect("lock_rule", 355, 724, 1210, 4, kAmber, 0.9f,
                          sweepTracks(1210.f, 70, 44), D));
    layers.push_back(textLayer("footer", "FLAP / LOCKED  ·  CHRONON MOTION LAB", 150, 1006,
                               16, kOswald, kMuted, D));
    return renderPlan(spec.planName(), D, layers, cameraSamples(D));
}

// ── 3. Halftone dissolve ────────────────────────────────────────────────────
Json buildHalftoneDissolve(const WebLabSpec& spec, int D) {
    Json layers = Json::array();
    Json bg = rect("paper", 0, 0, 1920, 1080, "#F2EFE8", 1.f, Json::array(), D);
    addNoiseVignette(bg, 0.008f, 4303, 0.16f);
    layers.push_back(std::move(bg));

    layers.push_back(textLayer("kicker", "MOTION LAB / HALFTONE", 120, 92, 22, kOswald,
                               kAccent, D));
    layers.push_back(textLayer("meta", "DOT MATRIX 16 x 9", 1800, 96, 18, kRegular,
                               "#6E6A62", D, 0.f, -1, 1.f, "ra"));
    layers.push_back(textLayer("headline", spec.headline, 120, 330, 88, kSerifBold,
                               "#121110", D));
    layers.push_back(rect("headline_rule", 120, 470, 440, 6, kAccent, 0.95f,
                          sweepTracks(440.f, 22, 40), D));
    layers.push_back(textLayer("subline", spec.subline, 120, 510, 27, kRegular,
                               "#55514A", D));

    // La griglia copre la pagina e si dissolve in onda diagonale: i punti non
    // sono un overlay decorativo, sono il velo che nasconde la composizione.
    const int cols = 16, rows = 9;
    const float left = 90.f, top = 110.f;
    const float cellW = 1740.f / float(cols), cellH = 890.f / float(rows);
    for (int row = 0; row < rows; ++row) {
        for (int col = 0; col < cols; ++col) {
            const float w = cellW * 0.84f, h = cellH * 0.82f;
            const float x = left + float(col) * cellW + (cellW - w) * 0.5f;
            const float y = top + float(row) * cellH + (cellH - h) * 0.5f;
            Json dot = ellipse("dot_" + std::to_string(row) + "_" + std::to_string(col),
                               x, y, w, h, "#14110D", 1.f, D);
            const int start = 4 + (row + col) * 4;
            dot["animation"] = Json{{"tracks", Json::array({
                easedTrack("scale_x", 1.f, 0.f, start, 26, "in_cubic"),
                easedTrack("scale_y", 1.f, 0.f, start, 26, "in_cubic"),
                easedTrack("opacity", 1.f, 0.f, start + 14, 12, "in_cubic")})}};
            layers.push_back(std::move(dot));
        }
    }

    layers.push_back(textLayer("caption", spec.highlight, 120, 930, 24, kOswald, kAccent, D));
    layers.push_back(textLayer("footer", "CHRONON / MOTION LAB  ·  EXPERIMENT 03", 150, 1006,
                               16, kOswald, "#6E6A62", D));
    return renderPlan(spec.planName(), D, layers, cameraSamples(D));
}

// ── 4. Ink bloom ────────────────────────────────────────────────────────────
Json buildInkBloom(const WebLabSpec& spec, int D) {
    const float size = 86.f;
    Json layers = Json::array();
    Json bg = rect("paper", 0, 0, 1920, 1080, kPaper, 1.f, Json::array(), D);
    addNoiseVignette(bg, 0.009f, 4404, 0.18f);
    layers.push_back(std::move(bg));

    layers.push_back(textLayer("kicker", "MOTION LAB / INK BLOOM", 120, 92, 22, kOswald,
                               kAccent, D));
    const float hx = 180.f + prefixWidth(spec.headline, spec.highlight, size, kSerifBold);
    const float hw = measuredTextWidth(spec.highlight, size, kSerifBold) + 30.f;

    const struct Bloom {
        float dx, dy, dw, dh, alpha;
        int start;
        float blur;
        const char* color;
    } blooms[4] = {
        {-18.f, 6.f, 24.f, 18.f, 0.34f, 8, 22.f, kAcid},
        {6.f, -4.f, 14.f, 12.f, 0.46f, 14, 15.f, "#E8DC4A"},
        {-6.f, 2.f, 4.f, 8.f, 0.28f, 22, 8.f, "#E4572E"},
        {2.f, 4.f, -8.f, -6.f, 0.58f, 10, 5.f, "#F2C500"},
    };
    for (int i = 0; i < 4; ++i) {
        const Bloom& b = blooms[i];
        Json stroke = rect("bloom_" + std::to_string(i), hx + b.dx, 436.f + b.dy,
                           hw + b.dw, 96.f + b.dh, b.color, b.alpha,
                           sweepTracks(hw, b.start, 46), D);
        addBlur(stroke, b.blur);
        layers.push_back(std::move(stroke));
    }

    layers.push_back(textLayer("headline", spec.headline, 180, 436, size, kSerifBold,
                               "#151310", D));
    layers.push_back(textLayer("subline", spec.subline, 180, 610, 28, kRegular, "#5E594F",
                               D));
    layers.push_back(rect("rule", 180, 680, 820, 3, "#151310", 0.7f,
                          sweepTracks(820.f, 38, 42), D));
    layers.push_back(textLayer("footer", "WET EDGE / 06  ·  CHRONON MOTION LAB", 150, 1006,
                               16, kOswald, "#6E6A62", D));
    return renderPlan(spec.planName(), D, layers, cameraSamples(D));
}

// ── 5. Parallax depth ───────────────────────────────────────────────────────
Json buildParallaxDepth(const WebLabSpec& spec, int D) {
    Json layers = Json::array();
    Json bg = rect("paper", 0, 0, 1920, 1080, "#0E1216", 1.f, Json::array(), D);
    addNoiseVignette(bg, 0.011f, 4505, 0.36f);
    layers.push_back(std::move(bg));

    Json ghost = textLayer("ghost", "DEPTH", 60, 70, 300, kOswaldBold, kInk, D, 0.f, -1,
                           0.05f);
    ghost["animation"] = Json{{"tracks", Json::array({
        easedTrack("position_x", -40.f, 24.f, 0, D - 1, "in_out_cubic")})}};
    layers.push_back(std::move(ghost));

    const char* titles[3] = {"FOREGROUND", "MIDGROUND", "BACKGROUND"};
    const char* numbers[3] = {"01", "02", "03"};
    const char* bodies[3] = {"the subject", "the context", "the field"};
    const char* panels[3] = {"#2C3A46", "#222C36", "#1A222A"};
    const char* accents[3] = {kAccent, kAcid, kCyan};
    const float baseX[3] = {1240.f, 730.f, 220.f};  // painted back to front
    for (int i = 0; i < 3; ++i) {
        const float x = baseX[i];
        const float y = 392.f + float(i) * 22.f;
        const float w = 470.f, h = 330.f;
        const float fromX = -90.f - float(i) * 46.f;
        const float toX = 26.f + float(i) * 34.f;
        const Json move = easedTrack("position_x", fromX, toX, 0, D - 1, "in_out_cubic");

        Json shadow1 = rect("shadow_a_" + std::to_string(i), x + 18.f, y + 22.f, w, h,
                            "#000000", 0.34f, Json::array(), D);
        shadow1["animation"] = Json{{"tracks", Json::array({move})}};
        layers.push_back(std::move(shadow1));
        Json shadow2 = rect("shadow_b_" + std::to_string(i), x + 36.f, y + 44.f, w, h,
                            "#000000", 0.16f, Json::array(), D);
        shadow2["animation"] = Json{{"tracks", Json::array({move})}};
        layers.push_back(std::move(shadow2));

        Json card = rect("card_" + std::to_string(i), x, y, w, h, panels[i], 1.f,
                         Json::array(), D);
        card["animation"] = Json{{"tracks", Json::array({move})}};
        layers.push_back(std::move(card));
        Json edge = rect("edge_" + std::to_string(i), x, y, w, 4.f, accents[i], 0.95f,
                         Json::array(), D);
        edge["animation"] = Json{{"tracks", Json::array({move})}};
        layers.push_back(std::move(edge));

        Json number = textLayer("number_" + std::to_string(i), numbers[i], x + 34.f,
                                y + 36.f, 46, kOswaldBold, accents[i], D);
        number["animation"] = Json{{"tracks", Json::array({move})}};
        layers.push_back(std::move(number));
        Json title = textLayer("title_" + std::to_string(i), titles[i], x + 34.f,
                               y + 100.f, 26, kOswald, kInk, D);
        title["animation"] = Json{{"tracks", Json::array({move})}};
        layers.push_back(std::move(title));
        Json body = textLayer("body_" + std::to_string(i), bodies[i], x + 34.f,
                              y + 160.f, 34, kSerifBold, "#C9C2B6", D);
        body["animation"] = Json{{"tracks", Json::array({move})}};
        layers.push_back(std::move(body));
        Json rule = rect("card_rule_" + std::to_string(i), x + 34.f, y + 250.f,
                         180.f, 3.f, accents[i], 0.72f, Json::array(), D);
        rule["animation"] = Json{{"tracks", Json::array({move})}};
        layers.push_back(std::move(rule));
    }

    layers.push_back(textLayer("kicker", "MOTION LAB / PARALLAX", 120, 92, 22, kOswald,
                               kAccent, D));
    layers.push_back(textLayer("meta", "THREE PLANES  ·  ONE FRAME", 1800, 96, 18,
                               kRegular, kMuted, D, 0.f, -1, 1.f, "ra"));
    layers.push_back(textLayer("headline", spec.headline, 120, 880, 42, kSerifBold,
                               kInk, D));
    layers.push_back(textLayer("subline", spec.subline, 120, 940, 22, kRegular, kMuted, D));
    for (int i = 0; i < 12; ++i) {
        const float x = 120.f + float((i * 317) % 1680);
        const float y = 180.f + float((i * 211) % 620);
        layers.push_back(ellipse("dust_" + std::to_string(i), x, y, 3.f, 3.f, kInk,
                                 0.18f, D));
    }
    return renderPlan(spec.planName(), D, layers, cameraSamples(D));
}

// ── 6. Slice glitch ─────────────────────────────────────────────────────────
Json buildSliceGlitch(const WebLabSpec& spec, int D) {
    Json layers = Json::array();
    Json bg = rect("paper", 0, 0, 1920, 1080, "#07090B", 1.f, Json::array(), D);
    addNoiseVignette(bg, 0.014f, 4606, 0.40f);
    layers.push_back(std::move(bg));
    addGrid(layers, 8, 120.f, 120.f, 0.045f, D);

    layers.push_back(textLayer("kicker", "TRANSMISSION / RECOVERY", 110, 82, 22, kOswald,
                               kCyan, D));
    layers.push_back(ellipse("status_dot", 1772, 88, 12, 12, kAccent, 1.f, D));
    layers.push_back(textLayer("status", "LIVE", 1798, 82, 18, kOswald, kMuted, D));

    const std::string top = spec.headline.substr(0, spec.headline.find(spec.highlight));
    const std::string bottom = spec.headline.substr(spec.headline.find(spec.highlight));
    layers.push_back(textLayer("fringe_magenta_top", top, 102, 252, 200, kOswaldBold,
                               "#FF3B30", D, 0.f, -1, 0.45f));
    layers.push_back(textLayer("fringe_cyan_top", top, 118, 258, 200, kOswaldBold,
                               kCyan, D, 0.f, -1, 0.38f));
    layers.push_back(textLayer("headline_top", top, 110, 255, 200, kOswaldBold, kInk, D));
    layers.push_back(textLayer("fringe_magenta_bottom", bottom, 108, 480, 118, kOswaldBold,
                               "#FF3B30", D, 0.f, -1, 0.40f));
    layers.push_back(textLayer("fringe_cyan_bottom", bottom, 122, 486, 118, kOswaldBold,
                               kCyan, D, 0.f, -1, 0.34f));
    layers.push_back(textLayer("headline_bottom", bottom, 115, 483, 118, kOswaldBold,
                               kInk, D));

    for (int i = 0; i < 7; ++i) {
        const int start = 18 + i * 4;
        Json slice = rect("slice_" + std::to_string(i), 110.f, 300.f + float(i) * 54.f,
                          840.f, 9.f, i % 2 == 0 ? kInk : kCyan, 0.10f,
                          Json::array(), D);
        slice["animation"] = Json{{"tracks", Json::array({
            jitterTrack(start, 150, 34.f + float(i) * 4.f),
            easedTrack("opacity", 0.0f, 0.10f, start, 6, "out_cubic")})}};
        layers.push_back(std::move(slice));
    }

    layers.push_back(rect("recover_rule", 115, 650, 920, 5, kCyan, 0.85f,
                          sweepTracks(920.f, 118, 42), D));
    layers.push_back(textLayer("subline", spec.subline, 115, 690, 28, kRegular, kMuted, D));
    layers.push_back(rect("ticker_bar", 0, 986, 1920, 44, "#101418", 1.f, Json::array(), D));
    layers.push_back(textLayer("ticker", "SIGNAL LOCKED  /  SLICE 06  /  CHRONON MOTION LAB  /  ",
                               36, 997, 17, kOswald, kCyan, D));
    return renderPlan(spec.planName(), D, layers, cameraSamples(D));
}

// ── 1c. Aperture scan, center cut ───────────────────────────────────────────
Json buildCenteredApertureScan(const WebLabSpec& spec, int D) {
    const float size = 92.f;
    Json layers = Json::array();

    Json bg = rect("paper", 0, 0, 1920, 1080, kDark, 0.998f, Json::array(), D);
    addNoiseVignette(bg, 0.010f, 5101, 0.28f);
    layers.push_back(std::move(bg));
    addGrid(layers, 9, 150.f, 96.f, 0.035f, D);

    const float left = centeredLeft(spec.headline, size, kHelvBold);
    const float top = centeredTop(size);
    layers.push_back(textLayer("headline_dim", spec.headline, left, top, size, kHelvBold,
                               kInk, D, 0.f, -1, 0.10f));

    const float hx = left + prefixWidth(spec.headline, spec.highlight, size, kHelvBold);
    const float hw = measuredTextWidth(spec.highlight, size, kHelvBold) + 28.f;
    Json marker = rect("aperture_marker", hx - 14.f, top + size * 0.30f, hw, 96.f,
                       kAccent, 0.42f, Json::array(), D);
    Json markerTracks = Json::array();
    markerTracks.push_back(Json{{"property", "opacity"},
                                {"easing", "in_out_cubic"},
                                {"keyframes", opacityKeys({{0, 0.0}, {18, 0.0}, {36, 1.0}, {D - 1, 1.0}})}});
    marker["animation"] = Json{{"tracks", std::move(markerTracks)}};
    layers.push_back(std::move(marker));

    Json live = textLayer("headline_live", spec.headline, left, top, size, kHelvBold,
                          kInk, D);
    Json liveTracks = Json::array();
    liveTracks.push_back(Json{{"property", "opacity"},
                               {"easing", "in_out_cubic"},
                               {"keyframes", opacityKeys({{0, 0.0}, {16, 0.0}, {34, 1.0}, {D - 1, 1.0}})}});
    live["animation"] = Json{{"tracks", std::move(liveTracks)}};
    layers.push_back(std::move(live));

    const Json scan = scanSettleTrack(D);
    layers.push_back(textAnimation(rect("scan_top", 0, 0, 1920, 3, kAccent, 0.92f,
                                        Json::array(), D), Json::array({scan})));
    layers.push_back(textAnimation(rect("scan_bottom", 0, 300, 1920, 2, kInk, 0.36f,
                                        Json::array(), D), Json::array({scan})));
    return renderPlan(spec.planName(), D, layers, centerCamera(D));
}

// ── 2c. Split flap, center cut ──────────────────────────────────────────────
Json buildCenteredSplitFlap(const WebLabSpec& spec, int D) {
    Json layers = Json::array();
    Json bg = rect("paper", 0, 0, 1920, 1080, "#0A0908", 0.998f, Json::array(), D);
    addNoiseVignette(bg, 0.012f, 5202, 0.30f);
    layers.push_back(std::move(bg));

    const char* digits[4] = {"2", "0", "2", "6"};
    const char* ghosts[4] = {"9", "4", "8", "3"};
    const float cellW = 280.f, cellH = 430.f, gap = 30.f;
    const float x0 = (1920.f - (4.f * cellW + 3.f * gap)) * 0.5f;
    const float y0 = (1080.f - cellH) * 0.5f;
    const float cy = y0 + cellH * 0.5f;
    for (int i = 0; i < 4; ++i) {
        const float x = x0 + float(i) * (cellW + gap);
        const float cx = x + cellW * 0.5f;
        layers.push_back(rect("cell_" + std::to_string(i), x, y0, cellW, cellH,
                              "#15130F", 1.f, Json::array(), D));
        layers.push_back(rect("cell_edge_" + std::to_string(i), x, y0, cellW, 2.f,
                              kInk, 0.14f, Json::array(), D));
        layers.push_back(rect("seam_" + std::to_string(i), x, y0 + 212.f, cellW, 2.f,
                              kInk, 0.16f, Json::array(), D));
        layers.push_back(textLayer("ghost_" + std::to_string(i), ghosts[i], cx, cy,
                                   210, kAnton, kInk, D, 0.f, -1, 0.10f, "mm"));

        const int start = 12 + i * 16;
        Json digit = textLayer("digit_" + std::to_string(i), digits[i], cx, cy, 230,
                               kAnton, kInk, D, 0.f, -1, 1.f, "mm");
        digit["animation"] = Json{{"tracks", Json::array({
            easedTrack("opacity", 0.f, 1.f, start, 8, "out_cubic"),
            easedTrack("position_y", 120.f, 0.f, start, 16, "out_cubic"),
            easedTrack("scale_y", 0.35f, 1.f, start, 16, "out_back")})}};
        layers.push_back(std::move(digit));

        Json flip = rect("flip_" + std::to_string(i), x, y0 + 2.f, cellW, 3.f,
                         kAmber, 0.85f, Json::array(), D);
        const int flipEnd = start + 24;
        flip["animation"] = Json{{"tracks", Json::array({
            Json{{"property", "opacity"}, {"easing", "in_out_cubic"},
                 {"keyframes", opacityKeys({{0, 0.0}, {start, 0.0}, {start + 4, 1.0},
                                            {start + 16, 1.0}, {flipEnd, 0.0},
                                            {D - 1, 0.0}})}},
            easedTrack("position_y", 0.f, -210.f, start, 16, "in_out_cubic")})}};
        layers.push_back(std::move(flip));
    }
    return renderPlan(spec.planName(), D, layers, centerCamera(D, 1.02));
}

// ── 3c. Halftone dissolve, center cut ───────────────────────────────────────
Json buildCenteredHalftoneDissolve(const WebLabSpec& spec, int D) {
    Json layers = Json::array();
    Json bg = rect("paper", 0, 0, 1920, 1080, "#F2EFE8", 0.998f, Json::array(), D);
    addNoiseVignette(bg, 0.008f, 5303, 0.14f);
    layers.push_back(std::move(bg));

    const int cols = 16, rows = 9;
    const float cellW = 1920.f / float(cols), cellH = 1080.f / float(rows);
    for (int row = 0; row < rows; ++row) {
        for (int col = 0; col < cols; ++col) {
            const float w = cellW * 0.84f, h = cellH * 0.82f;
            const float x = float(col) * cellW + (cellW - w) * 0.5f;
            const float y = float(row) * cellH + (cellH - h) * 0.5f;
            Json dot = ellipse("dot_" + std::to_string(row) + "_" + std::to_string(col),
                               x, y, w, h, "#14110D", 1.f, D);
            const int start = 4 + (row + col) * 4;
            dot["animation"] = Json{{"tracks", Json::array({
                easedTrack("scale_x", 1.f, 0.f, start, 26, "in_cubic"),
                easedTrack("scale_y", 1.f, 0.f, start, 26, "in_cubic"),
                easedTrack("opacity", 1.f, 0.f, start + 14, 12, "in_cubic")})}};
            layers.push_back(std::move(dot));
        }
    }

    const float size = 96.f;
    const float left = centeredLeft(spec.headline, size, kSerifBold);
    const float top = centeredTop(size);
    const float halo[4][2] = {{-4.f, 0.f}, {4.f, 0.f}, {0.f, -4.f}, {0.f, 4.f}};
    for (int i = 0; i < 4; ++i) {
        layers.push_back(textLayer("headline_halo_" + std::to_string(i), spec.headline,
                                   left + halo[i][0], top + halo[i][1], size, kSerifBold,
                                   "#F2EFE8", D, 0.f, -1, 0.92f));
    }
    layers.push_back(textLayer("headline", spec.headline, left, top, size, kSerifBold,
                               "#121110", D));
    return renderPlan(spec.planName(), D, layers, centerCamera(D));
}

// ── 4c. Ink bloom, center cut ───────────────────────────────────────────────
Json buildCenteredInkBloom(const WebLabSpec& spec, int D) {
    const float size = 92.f;
    Json layers = Json::array();
    Json bg = rect("paper", 0, 0, 1920, 1080, kPaper, 0.998f, Json::array(), D);
    addNoiseVignette(bg, 0.009f, 5404, 0.18f);
    layers.push_back(std::move(bg));

    const float left = centeredLeft(spec.headline, size, kSerifBold);
    const float top = centeredTop(size);
    const float hx = left + prefixWidth(spec.headline, spec.highlight, size, kSerifBold);
    const float hw = measuredTextWidth(spec.highlight, size, kSerifBold) + 30.f;
    const float markerTop = top + size * 0.25f;

    const struct Bloom {
        float dx, dy, dw, dh, alpha;
        int start;
        const char* color;
    } blooms[4] = {
        {-22.f, 0.f, 28.f, 18.f, 0.34f, 8, kAcid},
        {4.f, -6.f, 16.f, 12.f, 0.46f, 14, "#E8DC4A"},
        {-8.f, 4.f, 4.f, 8.f, 0.28f, 22, "#E4572E"},
        {2.f, 6.f, -8.f, -6.f, 0.58f, 10, "#F2C500"},
    };
    for (int i = 0; i < 4; ++i) {
        const Bloom& b = blooms[i];
        // The linux-video-test backends reject native blur surfaces, so the
        // wet edge is built from stacked translucent rectangles instead of a
        // gaussian_blur effect that would drop the layer.
        for (int ring = 2; ring >= 1; --ring) {
            const float pad = float(ring) * 6.f;
            Json halo = rect("bloom_halo_" + std::to_string(i) + "_" + std::to_string(ring),
                             hx + b.dx - pad, markerTop + b.dy - pad * 0.7f,
                             hw + b.dw + pad * 2.f, 96.f + b.dh + pad * 1.4f,
                             b.color, b.alpha * 0.16f,
                             sweepTracks(hw, b.start, 46), D);
            layers.push_back(std::move(halo));
        }
        Json stroke = rect("bloom_" + std::to_string(i), hx + b.dx, markerTop + b.dy,
                           hw + b.dw, 96.f + b.dh, b.color, b.alpha,
                           sweepTracks(hw, b.start, 46), D);
        layers.push_back(std::move(stroke));
    }

    layers.push_back(textLayer("headline", spec.headline, left, top, size, kSerifBold,
                               "#151310", D));
    return renderPlan(spec.planName(), D, layers, centerCamera(D));
}

// ── 5c. Parallax depth, center cut ──────────────────────────────────────────
Json buildCenteredParallaxDepth(const WebLabSpec& spec, int D) {
    Json layers = Json::array();
    Json bg = rect("paper", 0, 0, 1920, 1080, "#0E1216", 0.998f, Json::array(), D);
    addNoiseVignette(bg, 0.011f, 5505, 0.34f);
    layers.push_back(std::move(bg));
    for (int i = 0; i < 12; ++i) {
        const float x = 120.f + float((i * 317) % 1680);
        const float y = 180.f + float((i * 211) % 620);
        layers.push_back(ellipse("dust_" + std::to_string(i), x, y, 3.f, 3.f, kInk,
                                 0.18f, D));
    }

    const char* titles[3] = {"FOREGROUND", "MIDGROUND", "BACKGROUND"};
    const char* numbers[3] = {"01", "02", "03"};
    const char* bodies[3] = {"the subject", "the context", "the field"};
    const char* panels[3] = {"#2C3A46", "#222C36", "#1A222A"};
    const char* accents[3] = {kAccent, kAcid, kCyan};
    const float baseX[3] = {1185.f, 725.f, 265.f};  // front, middle, back
    const float fromX[3] = {-38.f, -22.f, 38.f};
    const float toX[3] = {38.f, 22.f, -38.f};
    const int order[3] = {2, 1, 0};  // back to front
    for (int k = 0; k < 3; ++k) {
        const int i = order[k];
        const float x = baseX[i];
        const float y = 331.f + float(i) * 22.f;
        const float w = 470.f, h = 330.f;
        const Json move = easedTrack("position_x", fromX[i], toX[i], 0, D - 1,
                                    "in_out_cubic");

        Json shadow1 = rect("shadow_a_" + std::to_string(i), x + 18.f, y + 22.f, w, h,
                            "#000000", 0.34f, Json::array(), D);
        shadow1["animation"] = Json{{"tracks", Json::array({move})}};
        layers.push_back(std::move(shadow1));
        Json shadow2 = rect("shadow_b_" + std::to_string(i), x + 36.f, y + 44.f, w, h,
                            "#000000", 0.16f, Json::array(), D);
        shadow2["animation"] = Json{{"tracks", Json::array({move})}};
        layers.push_back(std::move(shadow2));

        Json card = rect("card_" + std::to_string(i), x, y, w, h, panels[i], 1.f,
                         Json::array(), D);
        card["animation"] = Json{{"tracks", Json::array({move})}};
        layers.push_back(std::move(card));
        Json edge = rect("edge_" + std::to_string(i), x, y, w, 4.f, accents[i], 0.95f,
                         Json::array(), D);
        edge["animation"] = Json{{"tracks", Json::array({move})}};
        layers.push_back(std::move(edge));

        Json number = textLayer("number_" + std::to_string(i), numbers[i], x + 34.f,
                                y + 36.f, 46, kOswaldBold, accents[i], D);
        number["animation"] = Json{{"tracks", Json::array({move})}};
        layers.push_back(std::move(number));
        Json title = textLayer("title_" + std::to_string(i), titles[i], x + 34.f,
                               y + 100.f, 26, kOswald, kInk, D);
        title["animation"] = Json{{"tracks", Json::array({move})}};
        layers.push_back(std::move(title));
        Json body = textLayer("body_" + std::to_string(i), bodies[i], x + 34.f,
                              y + 160.f, 34, kSerifBold, "#C9C2B6", D);
        body["animation"] = Json{{"tracks", Json::array({move})}};
        layers.push_back(std::move(body));
        Json rule = rect("card_rule_" + std::to_string(i), x + 34.f, y + 250.f,
                         180.f, 3.f, accents[i], 0.72f, Json::array(), D);
        rule["animation"] = Json{{"tracks", Json::array({move})}};
        layers.push_back(std::move(rule));
    }
    return renderPlan(spec.planName(), D, layers, centerCamera(D, 1.02));
}

// ── 6c. Slice glitch, center cut ────────────────────────────────────────────
Json buildCenteredSliceGlitch(const WebLabSpec& spec, int D) {
    Json layers = Json::array();
    Json bg = rect("paper", 0, 0, 1920, 1080, "#07090B", 0.998f, Json::array(), D);
    addNoiseVignette(bg, 0.014f, 5606, 0.38f);
    layers.push_back(std::move(bg));
    addGrid(layers, 8, 120.f, 120.f, 0.045f, D);

    const char* top = "SIGNAL";
    const char* bottom = "RECOVERED";
    const float s1 = 200.f, s2 = 118.f;
    const float left1 = centeredLeft(top, s1, kOswaldBold);
    const float left2 = centeredLeft(bottom, s2, kOswaldBold);
    const float top1 = 300.f, top2 = 547.f;

    layers.push_back(textLayer("fringe_magenta_top", top, left1 - 8.f, top1 - 4.f, s1,
                               kOswaldBold, "#FF3B30", D, 0.f, -1, 0.45f));
    layers.push_back(textLayer("fringe_cyan_top", top, left1 + 8.f, top1 + 4.f, s1,
                               kOswaldBold, kCyan, D, 0.f, -1, 0.38f));
    layers.push_back(textLayer("headline_top", top, left1, top1, s1, kOswaldBold, kInk, D));
    layers.push_back(textLayer("fringe_magenta_bottom", bottom, left2 - 8.f, top2 - 4.f, s2,
                               kOswaldBold, "#FF3B30", D, 0.f, -1, 0.40f));
    layers.push_back(textLayer("fringe_cyan_bottom", bottom, left2 + 8.f, top2 + 4.f, s2,
                               kOswaldBold, kCyan, D, 0.f, -1, 0.34f));
    layers.push_back(textLayer("headline_bottom", bottom, left2, top2, s2, kOswaldBold,
                               kInk, D));

    for (int i = 0; i < 7; ++i) {
        const int start = 18 + i * 4;
        Json slice = rect("slice_" + std::to_string(i), 540.f, 300.f + float(i) * 60.f,
                          840.f, 9.f, i % 2 == 0 ? kInk : kCyan, 0.10f,
                          Json::array(), D);
        slice["animation"] = Json{{"tracks", Json::array({
            jitterTrack(start, 150, 34.f + float(i) * 4.f),
            easedTrack("opacity", 0.0f, 0.10f, start, 6, "out_cubic")})}};
        layers.push_back(std::move(slice));
    }
    return renderPlan(spec.planName(), D, layers, centerCamera(D, 1.02));
}

}  // namespace

const char* webLabName(WebLabRecipe recipe) {
    switch (recipe) {
        case WebLabRecipe::ApertureScan: return "lab_aperture_scan";
        case WebLabRecipe::SplitFlap: return "lab_split_flap";
        case WebLabRecipe::HalftoneDissolve: return "lab_halftone_dissolve";
        case WebLabRecipe::InkBloom: return "lab_ink_bloom";
        case WebLabRecipe::ParallaxDepth: return "lab_parallax_depth";
        case WebLabRecipe::SliceGlitch: return "lab_slice_glitch";
    }
    return "unknown";
}

const char* webCenterLabName(WebLabRecipe recipe) {
    switch (recipe) {
        case WebLabRecipe::ApertureScan: return "lab_aperture_scan_center";
        case WebLabRecipe::SplitFlap: return "lab_split_flap_center";
        case WebLabRecipe::HalftoneDissolve: return "lab_halftone_dissolve_center";
        case WebLabRecipe::InkBloom: return "lab_ink_bloom_center";
        case WebLabRecipe::ParallaxDepth: return "lab_parallax_depth_center";
        case WebLabRecipe::SliceGlitch: return "lab_slice_glitch_center";
    }
    return "unknown";
}

std::array<WebLabRecipe, 6> allWebLabRecipes() {
    return {WebLabRecipe::ApertureScan, WebLabRecipe::SplitFlap,
            WebLabRecipe::HalftoneDissolve, WebLabRecipe::InkBloom,
            WebLabRecipe::ParallaxDepth, WebLabRecipe::SliceGlitch};
}

std::array<WebLabRecipe, 6> allWebCenterRecipes() {
    return allWebLabRecipes();
}

void WebLabSpec::validate() const {
    if (fps != 30) fail("fps must be 30");
    if (durationFrames < 30 || durationFrames > 300)
        fail("durationFrames must be in [30,300] (max 10 s at 30 fps)");
    if (headline.empty() || headline.size() > 120) fail("headline must be 1..120 chars");
    if (subline.size() > 80) fail("subline must be at most 80 chars");
    if (headline.find('\n') != std::string::npos) fail("no newlines in headline");
    if (!highlight.empty()) {
        if (highlight.size() > 80) fail("highlight must be at most 80 chars");
        if (headline.find(highlight) == std::string::npos)
            fail("highlight must appear in headline");
    }
}

std::string WebLabSpec::planName() const {
    if (center) return std::string(webCenterLabName(recipe));
    return std::string(webLabName(recipe)) + "_v1";
}

std::string WebLabSpec::outputStem() const {
    if (!outputName.empty()) return outputName;
    return planName() + ".mp4";
}

nlohmann::json buildWebLabPlan(const WebLabSpec& spec) {
    spec.validate();
    const int D = spec.durationFrames;
    Json plan;
    if (spec.center) {
        switch (spec.recipe) {
            case WebLabRecipe::ApertureScan: plan = buildCenteredApertureScan(spec, D); break;
            case WebLabRecipe::SplitFlap: plan = buildCenteredSplitFlap(spec, D); break;
            case WebLabRecipe::HalftoneDissolve: plan = buildCenteredHalftoneDissolve(spec, D); break;
            case WebLabRecipe::InkBloom: plan = buildCenteredInkBloom(spec, D); break;
            case WebLabRecipe::ParallaxDepth: plan = buildCenteredParallaxDepth(spec, D); break;
            case WebLabRecipe::SliceGlitch: plan = buildCenteredSliceGlitch(spec, D); break;
        }
    } else {
        switch (spec.recipe) {
            case WebLabRecipe::ApertureScan: plan = buildApertureScan(spec, D); break;
            case WebLabRecipe::SplitFlap: plan = buildSplitFlap(spec, D); break;
            case WebLabRecipe::HalftoneDissolve: plan = buildHalftoneDissolve(spec, D); break;
            case WebLabRecipe::InkBloom: plan = buildInkBloom(spec, D); break;
            case WebLabRecipe::ParallaxDepth: plan = buildParallaxDepth(spec, D); break;
            case WebLabRecipe::SliceGlitch: plan = buildSliceGlitch(spec, D); break;
        }
    }
    if (spec.center) {
        // The 2D shape pass places layers relative to the canvas center,
        // while text keeps absolute plan coordinates. Convert the shape
        // origins and flatten the otherwise unused 3D transform block.
        const float canvas_width = plan["canvas"].value("width", 1920.0f);
        const float canvas_height = plan["canvas"].value("height", 1080.0f);
        for (auto& layer : plan["layers"]) {
            if (layer.value("type", std::string{}) != "shape") continue;
            layer.erase("enable_3d");
            layer.erase("rotation");
            layer.erase("scale");
            auto& position = layer["position"];
            if (position.is_array() && position.size() >= 2) {
                position[0] = position[0].get<float>() - canvas_width * 0.5f;
                position[1] = position[1].get<float>() - canvas_height * 0.5f;
            }
            if (position.is_array() && position.size() >= 3) {
                position.erase(position.begin() + 2, position.end());
            }
        }
    }
    plan["output"] = {{"path", spec.outputStem()}, {"format", "mp4"}, {"codec", "h264"}};
    return plan;
}

}  // namespace chronontemplate::web
