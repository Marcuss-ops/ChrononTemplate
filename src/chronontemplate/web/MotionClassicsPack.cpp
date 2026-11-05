#include "chronontemplate/web/MotionClassicsPack.hpp"

#include "chronontemplate/web/WebShotJson.hpp"

#include <algorithm>
#include <array>
#include <iomanip>
#include <sstream>
#include <string>
#include <utility>
#include <vector>

namespace chronontemplate::web {
namespace {

using Json = nlohmann::json;

constexpr int kDuration = 90;

constexpr const char* kInk = "#F4EFE7";
constexpr const char* kMuted = "#9C938A";
constexpr const char* kBody = "#D1C7BC";
constexpr const char* kRule = "#2A2825";
constexpr const char* kPanel = "#171614";
constexpr const char* kAccent = "#FF5A1F";
constexpr const char* kAmber = "#FF8A3D";

constexpr const char* kBold = "ChrononTemplate/assets/fonts/Inter-Bold.ttf";
constexpr const char* kRegular = "ChrononTemplate/assets/fonts/Inter-Regular.ttf";
constexpr const char* kSerif = "ChrononTemplate/assets/fonts/PlayfairDisplay.ttf";
constexpr const char* kSerifBold = "ChrononTemplate/assets/fonts/PlayfairDisplay-Bold.ttf";

struct PageCopy {
    const char* kicker;
    const char* lineOne;
    const char* lineTwo;
    const char* byline;
    bool centered;
    bool serif;
    bool number;
    bool grid;
};

constexpr std::array<PageCopy, 12> kPages{{
    {"THE ATTENTION ISSUE", "Less noise,", "more signal.", "WORDS / CHRONON EDITORIAL", false, false, false, false},
    {"TYPE / RHYTHM", "Make it move,", "then let it land.", "DESIGN DESK / STUDIO NOTES", false, false, false, false},
    {"A SMALL MANIFESTO", "Three ways", "to hold a reader.", "CHRONON / FIELD NOTES", true, false, false, false},
    {"A LOOP WITH A BEGINNING", "Keep it moving", "through the frame.", "MOTION / WEEKLY", false, false, false, false},
    {"THREE CARDS / ONE SYSTEM", "A page is", "a small system.", "EDITORIAL SYSTEMS / 05", false, false, false, false},
    {"ONE POINT / ONE FIELD", "One point.", "One field.", "CHRONON / VISUAL ESSAY", true, false, false, false},
    {"ORDER FROM CHAOS", "Order is", "a rhythm.", "MODULAR / TWELVE PARTS", false, false, false, true},
    {"AN EDITORIAL LINE", "Make the reveal,", "then hold.", "TYPE / PAUSE / REPEAT", false, true, false, false},
    {"A HARD EDGE", "Cut through", "the soft frame.", "DIRECTION / NINE", false, false, false, false},
    {"TWELVE BEATS / ONE SYSTEM", "Count the", "whole frame.", "MOTION / 12", false, false, true, false},
    {"WORD SLOT / ONE AT A TIME", "Type, motion,", "rhythm, impact.", "KINETIC TYPE / 11", true, false, false, false},
    {"THE CLOSING STATEMENT", "Make it move.", "That's the idea.", "CHRONON / END CARD", true, false, false, false},
}};

const std::array<const char*, 6> kBodyLines{{
    "Electricity prices are reshaping the choices",
    "manufacturers make, from the smallest shop",
    "to the largest plant. The effect is uneven:",
    "energy-intensive industries feel it first, while",
    "services absorb the change more slowly.",
    "Analysts say the next two quarters will matter.",
}};

const std::array<const char*, 3> kPicks{{
    "The new economics of power",
    "What the grid keeps hidden",
    "A field guide to attention",
}};

Json opacityTrack(int start, int span, int duration) {
    Json keys = Json::array();
    keys.push_back({{"frame", 0}, {"value", start <= 0 ? 1.0 : 0.0}});
    if (start > 0) {
        keys.push_back({{"frame", start}, {"value", 0.0}});
        keys.push_back({{"frame", std::min(start + span, duration - 1)}, {"value", 1.0}});
    }
    keys.push_back({{"frame", duration - 1}, {"value", 1.0}});
    return {{"property", "opacity"}, {"easing", "out_cubic"}, {"keyframes", std::move(keys)}};
}

void fadeIn(Json& layer, int start, int span = 12) {
    Json tracks = layer.value("animation", Json::object()).value("tracks", Json::array());
    tracks.push_back(opacityTrack(start, span, kDuration));
    layer["animation"] = {{"tracks", std::move(tracks)}};
}

Json pageText(const std::string& id, const std::string& text, float x, float y, float size,
              const char* font, const char* color, const char* anchor = "la") {
    return shot::textLayer(id, text, x, y, size, font, color, kDuration, 0.0f, -1, 1.0f, anchor);
}

/// A solid bar/panel built from the `█` glyph (DejaVu Sans), never a shape.
/// The renderer's text lane is the one path verified at full canvas on this
/// build, so the page chrome and the highlighter use the same primitive as
/// the copy. `segments` makes a marker that can be revealed left-to-right.
std::vector<Json> blockRow(const std::string& id, float left, float top, float width,
                           float height, const char* color, float alpha,
                           int segments = 1, int start = -1, int stagger = 2) {
    std::vector<Json> out;
    segments = std::max(1, segments);
    // Overlap consecutive swaths so the text-run sidebearings never leave a
    // black seam between the segments of a highlighter or a ticker bar.
    const float step = width / float(segments);
    const float segmentWidth = segments > 1 ? step * 1.80f : width;
    const float span = std::max(0.0f, width - segmentWidth);
    const float glyphSize = std::max(2.0f, height / 1.18f);
    const int blocksPerSegment = std::max(1, int(std::ceil(segmentWidth * 1.18f /
                                                           (glyphSize * 0.72f))));
    std::string blocks;
    blocks.reserve(static_cast<std::size_t>(blocksPerSegment) * 3);
    for (int i = 0; i < blocksPerSegment; ++i) blocks += "\xE2\x96\x88";  // U+2588

    for (int segment = 0; segment < segments; ++segment) {
        const float segmentLeft = left + (segments > 1
            ? span * float(segment) / float(segments - 1)
            : 0.0f);
        Json layer = shot::textLayer(id + "_" + std::to_string(segment), blocks,
                                     segmentLeft, top, glyphSize, shot::kDeja, color,
                                     kDuration, 0.0f, -1, alpha);
        // The run must stay on one line; centering keeps the segment aligned.
        layer["size"] = Json::array({segmentWidth * 1.55f, height * 1.65f});
        layer["position"] = shot::wirePos(segmentLeft + segmentWidth * 0.5f,
                                           top + height * 0.5f);
        if (start >= 0) fadeIn(layer, start + segment * stagger, 8);
        out.push_back(std::move(layer));
    }
    return out;
}

void append(Json& layers, std::vector<Json> rows) {
    for (auto& row : rows) layers.push_back(std::move(row));
}

}  // namespace

std::string MotionClassicSpec::planName() const {
    std::ostringstream name;
    name << "w" << std::setw(2) << std::setfill('0') << index << "_" << slug << "_v1";
    return name.str();
}

std::string MotionClassicSpec::videoName() const {
    std::ostringstream name;
    name << "w" << std::setw(2) << std::setfill('0') << index << "_" << slug << ".mp4";
    return name.str();
}

std::array<MotionClassicSpec, 12> motionClassicSpecs() {
    return {{
        {1, "curtain_reveal", "Curtain Reveal", "A full editorial page with a segmented highlighter on the lead.", 90, 30},
        {2, "kinetic_split", "Kinetic Split", "A dark page split by a marker and a two-column article.", 90, 30},
        {3, "staggered_manifesto", "Staggered Manifesto", "A centered manifesto whose lines land one after another.", 90, 30},
        {4, "marquee_loop", "Marquee Loop", "A page with a moving ticker and a highlighter on the second line.", 90, 30},
        {5, "card_stack", "Card Stack", "A page whose sidebar reads as a stack of editorial picks.", 90, 30},
        {6, "circle_wipe", "Circle Wipe", "A centered field with one sharp sentence and a center-out marker.", 90, 30},
        {7, "grid_rhythm", "Grid Rhythm", "A three-column page assembled in rhythm.", 90, 30},
        {8, "serif_underline", "Serif Underline", "A serif page with a segmented orange underline.", 90, 30},
        {9, "diagonal_cut", "Diagonal Cut", "A hard editorial page with offset lines and an orange edge.", 90, 30},
        {10, "count_to_twelve", "Count To Twelve", "A page built around the number twelve.", 90, 30},
        {11, "word_slot", "Word Slot", "A centered page where each headline takes its slot.", 90, 30},
        {12, "end_card", "End Card", "The full page closes on a single statement.", 90, 30},
    }};
}

Json buildMotionClassicPlan(const MotionClassicSpec& spec) {
    const PageCopy& copy = kPages[static_cast<std::size_t>(std::clamp(spec.index - 1, 0, 11))];
    const bool centered = copy.centered;
    const bool serif = copy.serif;
    const bool numberPage = copy.number;
    const bool grid = copy.grid;
    const char* accent = (spec.index % 3 == 0) ? kAmber : kAccent;

    Json layers = Json::array();

    // ── nav ─────────────────────────────────────────────────────────────────
    Json brand = pageText("brand", "CHRONON / DAILY", 90.f, 23.f, 22.f, kBold, kInk);
    fadeIn(brand, 0, 10);
    layers.push_back(std::move(brand));
    const char* links[4] = {"Business", "Design", "Culture", "Archive"};
    const float linkX[4] = {720.f, 850.f, 960.f, 1080.f};
    for (int i = 0; i < 4; ++i) {
        Json link = pageText("nav_" + std::to_string(i), links[i], linkX[i], 28.f, 15.f,
                             kRegular, kMuted);
        fadeIn(link, 2 + i, 10);
        layers.push_back(std::move(link));
    }
    append(layers, blockRow("search_pill", 1400.f, 18.f, 190.f, 38.f, kPanel, 1.f));
    Json search = pageText("search_text", "Search", 1420.f, 27.f, 15.f, kRegular, kMuted);
    fadeIn(search, 5, 10);
    layers.push_back(std::move(search));
    append(layers, blockRow("action_pill", 1620.f, 16.f, 210.f, 40.f, accent, 1.f));
    Json action = pageText("action_text", "Subscribe", 1650.f, 24.f, 16.f, kBold, "#FFFFFF");
    fadeIn(action, 6, 10);
    layers.push_back(std::move(action));

    // ── masthead ─────────────────────────────────────────────────────────────
    Json kicker = pageText("kicker", copy.kicker, centered ? 960.f : 150.f, 137.f, 17.f,
                           kBold, accent, centered ? "ma" : "la");
    fadeIn(kicker, 3, 12);
    layers.push_back(std::move(kicker));
    Json meta = pageText("meta", "NOV 2026  ·  06 MIN READ", 1770.f, 140.f, 14.f,
                         kRegular, kMuted, "ra");
    fadeIn(meta, 6, 12);
    layers.push_back(std::move(meta));

    const float headlineSize = centered ? 74.f : (serif ? 80.f : 66.f);
    const char* headlineFont = serif ? kSerifBold : kBold;
    const float baseLeft = centered ? 960.f : 150.f;
    const char* baseAnchor = centered ? "ma" : "la";
    const float lineOneY = centered ? 255.f : 210.f;
    const float lineTwoY = centered ? 355.f : 302.f;
    const float lineTwoX = (spec.index == 9) ? baseLeft + 120.f : baseLeft;

    const bool highlightOne = (spec.index % 2 == 0);
    const std::string& highlighted = highlightOne ? std::string(copy.lineOne) : std::string(copy.lineTwo);
    const float highlightedY = highlightOne ? lineOneY : lineTwoY;
    const float highlightedX = highlightOne ? baseLeft : lineTwoX;
    const float highlightedW = shot::measuredTextWidth(highlighted, headlineSize, headlineFont) + 34.f;
    const float markerLeft = centered ? 960.f - highlightedW * 0.5f : highlightedX - 14.f;
    const int markerStart = 12 + (spec.index % 3) * 2;
    const bool centerOut = centered || (spec.index == 6) || (spec.index == 11);
    if (centerOut) {
        // Two halves fill from the centre outwards, still using the text lane.
        const float halfW = highlightedW * 0.5f;
        append(layers, blockRow("marker_l", markerLeft, highlightedY - 4.f, halfW,
                                headlineSize * 1.08f, accent, 0.52f, 4, markerStart, 2));
        append(layers, blockRow("marker_r", markerLeft + halfW, highlightedY - 4.f, halfW,
                                headlineSize * 1.08f, accent, 0.52f, 4, markerStart, 2));
    } else {
        append(layers, blockRow("marker", markerLeft, highlightedY - 4.f, highlightedW,
                                headlineSize * 1.08f, accent, 0.52f, 8, markerStart, 2));
    }

    Json headlineOne = pageText("headline_one", copy.lineOne, baseLeft, lineOneY, headlineSize,
                                headlineFont, kInk, baseAnchor);
    fadeIn(headlineOne, 0, 14);
    layers.push_back(std::move(headlineOne));
    Json headlineTwo = pageText("headline_two", copy.lineTwo, lineTwoX, lineTwoY, headlineSize,
                                headlineFont, kInk, centered ? "ma" : "la");
    fadeIn(headlineTwo, 5, 16);
    layers.push_back(std::move(headlineTwo));

    if (centered) {
        Json note = pageText("quote_note", "A NOTE ON ATTENTION", 960.f, 470.f, 14.f, kBold,
                             accent, "ma");
        fadeIn(note, 18, 14);
        layers.push_back(std::move(note));
    } else {
        Json byline = pageText("byline", copy.byline, 150.f, 412.f, 17.f, kBold, kInk);
        fadeIn(byline, 10, 14);
        layers.push_back(std::move(byline));
        append(layers, blockRow("masthead_rule", 150.f, 462.f, 1620.f, 2.f, kRule, 1.f));
    }

    // ── article body ─────────────────────────────────────────────────────────
    if (centered) {
        const int rows = (spec.index == 11) ? 2 : 3;
        for (int i = 0; i < rows; ++i) {
            Json line = pageText("body_" + std::to_string(i), kBodyLines[i], 960.f,
                                 526.f + float(i) * 44.f, 19.f, kSerif, kBody, "ma");
            fadeIn(line, 20 + i * 4, 14);
            layers.push_back(std::move(line));
        }
    } else {
        const int columns = grid ? 3 : 2;
        const float columnX[3] = {150.f, 690.f, 1230.f};
        const int perColumn = grid ? 2 : 3;
        int lineIndex = 0;
        for (int col = 0; col < columns; ++col) {
            for (int row = 0; row < perColumn && lineIndex < int(kBodyLines.size()); ++row, ++lineIndex) {
                Json line = pageText("body_" + std::to_string(lineIndex), kBodyLines[lineIndex],
                                     columnX[col], 510.f + float(row) * 48.f, 20.f, kSerif, kBody);
                fadeIn(line, 14 + lineIndex * 2, 14);
                layers.push_back(std::move(line));
            }
        }
    }

    // ── sidebar / number / grid dressing ─────────────────────────────────────
    if (numberPage) {
        Json big = pageText("big_number", "12", 1770.f, 300.f, 340.f, kBold, accent, "ra");
        fadeIn(big, 8, 18);
        layers.push_back(std::move(big));
        Json caption = pageText("number_caption", "BEATS / ONE SYSTEM", 1770.f, 700.f, 15.f,
                                kBold, kInk, "ra");
        fadeIn(caption, 18, 12);
        layers.push_back(std::move(caption));
    } else if (!centered && !grid) {
        for (int i = 0; i < 3; ++i) {
            const float y = 210.f + float(i) * 138.f;
            append(layers, blockRow("pick_card_" + std::to_string(i), 1490.f, y,
                                    280.f, 112.f, kPanel, 1.f));
            Json pickTitle = pageText("pick_title_" + std::to_string(i), kPicks[i], 1608.f,
                                      y + 28.f, 14.f, kRegular, kInk);
            fadeIn(pickTitle, 16 + i * 5, 14);
            layers.push_back(std::move(pickTitle));
            Json pickNumber = pageText("pick_number_" + std::to_string(i),
                                       "0" + std::to_string(i + 1), 1516.f, y + 28.f, 13.f,
                                       kBold, accent);
            fadeIn(pickNumber, 15 + i * 5, 12);
            layers.push_back(std::move(pickNumber));
        }
    }

    if (grid) {
        Json gridLabel = pageText("grid_label", "A MODULAR MATRIX / 12 PARTS", 150.f, 940.f,
                                  15.f, kBold, kMuted);
        fadeIn(gridLabel, 22, 14);
        layers.push_back(std::move(gridLabel));
        for (int i = 0; i < 3; ++i) {
            append(layers, blockRow("grid_head_" + std::to_string(i), 150.f + float(i) * 540.f,
                                    484.f, 72.f, 3.f, accent, 1.f));
        }
    }

    if (spec.index == 4) {
        append(layers, blockRow("ticker_bar", 0.f, 994.f, 1920.f, 46.f, accent, 1.f));
        Json ticker = pageText("ticker_text",
                               "KEEP IT MOVING  /  KEEP IT MOVING  /  KEEP IT MOVING",
                               52.f, 1006.f, 16.f, kBold, "#FFFFFF");
        fadeIn(ticker, 8, 14);
        layers.push_back(std::move(ticker));
    }

    if (spec.index == 9) {
        // A diagonal reading line, expressed as a staggered stack of blocks.
        for (int i = 0; i < 5; ++i) {
            append(layers, blockRow("diag_" + std::to_string(i), 150.f + float(i) * 120.f,
                                    940.f + float(i) * 16.f, 86.f, 5.f, accent, 0.42f, 1,
                                    16 + i * 2, 1));
        }
    }

    // ── footer ───────────────────────────────────────────────────────────────
    if (spec.index != 4) {
        append(layers, blockRow("footer_rule", 150.f, 1010.f, 1620.f, 2.f, kRule, 0.9f));
    }
    Json footerLeft = pageText("footer_left", "CHRONON / DAILY  ·  ALL RIGHTS RESERVED",
                               150.f, 1028.f, 13.f, kRegular, kMuted);
    fadeIn(footerLeft, 24, 12);
    layers.push_back(std::move(footerLeft));
    Json footerRight = pageText("footer_right", "0" + std::to_string(spec.index) + " / 12",
                                1770.f, 1024.f, 14.f, kBold, accent, "ra");
    fadeIn(footerRight, 24, 12);
    layers.push_back(std::move(footerRight));

    Json plan = shot::renderPlan(spec.planName(), kDuration, layers, shot::cameraSamples(kDuration));
    plan["output"] = {{"path", spec.videoName()}, {"format", "mp4"}, {"codec", "h264"}};
    return plan;
}

}  // namespace chronontemplate::web
