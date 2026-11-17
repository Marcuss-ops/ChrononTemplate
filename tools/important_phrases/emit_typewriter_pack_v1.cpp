// ChrononTemplate — typewriter motion pack v1 (C++ emitter).
//
// Eight new typewriter recipes authored as `chronon.render-plan.v3` documents:
// per-glyph (or per-word) reveal through a percentage selector, the unrevealed
// tail hidden by an opacity-0 animator property, and a caret shape layer whose
// position_x/position_y tracks chase the typing frontier frame by frame.
//
// Long phrases are wrapped automatically: the font size is fitted so every line
// fits the safe width and the block stays inside the safe height, which is what
// makes the same recipe usable for two words or for three lines of copy.
//
// Usage: emit_typewriter_pack_v1 <repo-root> <plan-output-dir> [motion-id ...]
//   fonts are resolved from <repo-root>/Chronon3d/assets/fonts
#include <ft2build.h>
#include FT_FREETYPE_H

#include <nlohmann/json.hpp>

#include <algorithm>
#include <cmath>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <string>
#include <utility>
#include <vector>

namespace {
using json = nlohmann::ordered_json;
namespace fs = std::filesystem;

constexpr int W = 1920, H = 1080, FPS = 24, DUR = 192;  // 8 s at 24 fps
constexpr double MAX_BLOCK_H = 800.0;

struct Preset {
    std::string id;
    std::string fit;  // short | long
    std::string phrase;
    std::string font;        // file name inside Chronon3d/assets/fonts
    int size_hint;
    double max_width;
    int max_lines;
    double line_height;      // multiplier of font size
    std::string ink;
    std::string glow_color;
    double glow_radius;
    double glow_intensity;
    std::string bg;
    std::string bar;         // accent rule under the block ("" = none)
    std::string caret_color; // "" = no caret
    double caret_w_em;
    double caret_h_em;
    double caret_y_em;       // vertical offset from the line centre
    std::string unit;        // glyph | word
    std::string shape;       // square | ramp_up | smooth
    double frames_per_char;  // typing speed
    double start_sec;
    double type_budget;      // fraction of the clip the typing may use
    bool erase;
    bool enter;
    bool blink;
    double soft_band;  // percent of the run that trails the frontier with blur (0 = crisp)
};

const std::vector<Preset> kPresets = {
    // 1. monospaced block caret, short phrase, crisp per-glyph typing.
    {"tw01_mono_caret_short", "short", "OGNI DETTAGLIO CONTA", "DejaVuSansMono-Bold.ttf", 132, 1500, 1, 1.16,
     "#F2F5F8", "#FFFFFF", 8.0, 0.18, "#05070D", "#FFB454", "#FFB454", 0.62, 0.10, 0.50,
     "glyph", "square", 1.6, 0.42, 0.55, false, false, true},

    // 2. the same mono voice on a long sentence wrapped over up to three lines.
    {"tw02_mono_long_wrap", "long", "NON È IL COLPO A DECIDERE LA PARTITA, MA IL MODO IN CUI SCEGLI DI RACCONTARLO.",
     "DejaVuSansMono-Bold.ttf", 88, 1560, 3, 1.24,
     "#E8EEF4", "#AFC8FF", 6.0, 0.16, "#05070D", "#FFB454", "#FFB454", 0.10, 0.92, 0.02,
     "glyph", "square", 1.35, 0.42, 0.60, false, false, true},

    // 3. soft frontier (ramp_up) on a long editorial sentence, no caret.
    {"tw03_soft_frontier_long", "long", "Il silenzio, prima della verità, è la parte più difficile da montare.",
     "Inter-Medium.ttf", 96, 1520, 3, 1.28,
     "#F4F6FA", "#8FB6FF", 10.0, 0.22, "#06080F", "#8FB6FF", "", 0.0, 0.0, 0.0,
     "glyph", "square", 1.5, 0.40, 0.62, false, false, false, 14.0},

    // 4. short impact card: heavy black weight, oversized, entrance push.
    {"tw04_impact_short", "short", "TUTTO CAMBIA IN UN FRAME", "Inter-Black.ttf", 196, 1640, 1, 1.10,
     "#FFFFFF", "#FF7A3D", 22.0, 0.55, "#08060A", "#FF7A3D", "#FF7A3D", 0.14, 0.86, 0.02,
     "glyph", "square", 1.9, 0.30, 0.50, false, true, true},

    // 5. type forward, hold, erase right-to-left, caret follows both passes.
    {"tw05_type_erase_short", "short", "ORA LO VEDI.", "Space-Grotesk.ttf", 168, 1360, 1, 1.12,
     "#F7F8FA", "#9BE7FF", 16.0, 0.40, "#05070C", "#9BE7FF", "#9BE7FF", 0.12, 0.88, 0.02,
     "glyph", "square", 3.4, 0.14, 0.34, true, false, false},

    // 6. terminal readout: green mono, block cursor, long multi-line payload.
    {"tw06_terminal_long", "long", "SIGNAL LOCKED // ARCHIVIO 1987 // LA TRASMISSIONE È IN CORSO",
     "DejaVuSansMono-Bold.ttf", 84, 1560, 3, 1.26,
     "#7CF0C9", "#7CF0C9", 14.0, 0.35, "#03070A", "#7CF0C9", "#7CF0C9", 0.52, 0.92, 0.02,
     "glyph", "square", 1.25, 0.46, 0.58, false, false, true},

    // 7. editorial serif with an amber underscore caret on a long quote.
    {"tw07_editorial_caret_long", "long", "La verità è un dettaglio che nessuno aveva notato.",
     "PlayfairDisplay-Bold.ttf", 104, 1500, 3, 1.22,
     "#F5EFE3", "#FFD9A0", 8.0, 0.20, "#0A0807", "#C9A227", "#FFB454", 0.60, 0.08, 0.50,
     "glyph", "square", 1.3, 0.42, 0.58, false, false, true},

    // 8. word-at-a-time burst for very short cards.
    {"tw08_word_burst_short", "short", "NESSUN DETTAGLIO È CASUALE", "Inter-ExtraBold.ttf", 150, 1580, 1, 1.14,
     "#FFFFFF", "#FFB454", 18.0, 0.48, "#07070B", "#FFB454", "#FFB454", 0.18, 0.80, 0.02,
     "word", "square", 0.85, 0.36, 0.52, false, false, true},
};

// ── text measurement ────────────────────────────────────────────────────────

struct Metrics {
    double width = 0.0;
    std::vector<double> starts;  // left edge of each codepoint, plus the end
};

Metrics measureText(FT_Library lib, const fs::path& font, int size, const std::u32string& text) {
    FT_Face face = nullptr;
    if (FT_New_Face(lib, font.c_str(), 0, &face))
        throw std::runtime_error("cannot open font " + font.string());
    FT_Set_Pixel_Sizes(face, 0, static_cast<FT_UInt>(size));
    Metrics m;
    m.starts.reserve(text.size() + 1);
    double x = 0.0;
    FT_UInt prev = 0;
    for (char32_t cp : text) {
        const FT_UInt glyph = FT_Get_Char_Index(face, static_cast<FT_ULong>(cp));
        if (prev != 0 && glyph != 0 && FT_HAS_KERNING(face)) {
            FT_Vector kern{};
            if (!FT_Get_Kerning(face, prev, glyph, FT_KERNING_DEFAULT, &kern))
                x += static_cast<double>(kern.x) / 64.0;
        }
        m.starts.push_back(x);
        if (!FT_Load_Glyph(face, glyph, FT_LOAD_DEFAULT))
            x += static_cast<double>(face->glyph->advance.x) / 64.0;
        prev = glyph;
    }
    m.starts.push_back(x);
    m.width = x;
    FT_Done_Face(face);
    return m;
}

std::u32string utf8ToU32(const std::string& s) {
    std::u32string out;
    for (std::size_t i = 0; i < s.size();) {
        const unsigned char c = static_cast<unsigned char>(s[i]);
        char32_t cp = 0;
        int extra = 0;
        if (c < 0x80) { cp = c; extra = 0; }
        else if ((c & 0xE0) == 0xC0) { cp = c & 0x1F; extra = 1; }
        else if ((c & 0xF0) == 0xE0) { cp = c & 0x0F; extra = 2; }
        else if ((c & 0xF8) == 0xF0) { cp = c & 0x07; extra = 3; }
        else { ++i; continue; }
        if (i + extra >= s.size()) break;
        for (int k = 1; k <= extra; ++k)
            cp = (cp << 6) | (static_cast<unsigned char>(s[i + k]) & 0x3F);
        out.push_back(cp);
        i += static_cast<std::size_t>(extra) + 1;
    }
    return out;
}

std::vector<std::u32string> splitWords(const std::u32string& text) {
    std::vector<std::u32string> words;
    std::u32string current;
    for (char32_t cp : text) {
        if (cp == U' ') {
            if (!current.empty()) words.push_back(current);
            current.clear();
        } else {
            current.push_back(cp);
        }
    }
    if (!current.empty()) words.push_back(current);
    return words;
}

struct WrappedLine {
    std::u32string text;
    int phrase_start = 0;  // codepoint offset of text[0] inside the full phrase
};

std::vector<WrappedLine> wrapLines(FT_Library lib, const fs::path& font, int size,
                                   const std::vector<std::u32string>& words, double max_width) {
    const double space = measureText(lib, font, size, U" ").width;
    std::vector<WrappedLine> lines;
    std::vector<int> offsets(words.size(), 0);
    int cursor = 0;
    for (std::size_t i = 0; i < words.size(); ++i) {
        offsets[i] = cursor;
        cursor += static_cast<int>(words[i].size()) + 1;  // word plus the space that follows it
    }

    WrappedLine line;
    double line_width = 0.0;
    for (std::size_t i = 0; i < words.size(); ++i) {
        const auto& word = words[i];
        const double word_width = measureText(lib, font, size, word).width;
        if (line.text.empty()) {
            line.text = word;
            line.phrase_start = offsets[i];
            line_width = word_width;
            continue;
        }
        if (line_width + space + word_width <= max_width) {
            line.text.push_back(U' ');
            line.text += word;
            line_width += space + word_width;
        } else {
            lines.push_back(line);
            line = WrappedLine{word, offsets[i]};
            line_width = word_width;
        }
    }
    if (!line.text.empty()) lines.push_back(line);
    return lines;
}

int fitFontSize(FT_Library lib, const fs::path& font, const std::vector<std::u32string>& words,
                const Preset& preset) {
    for (int size = preset.size_hint; size >= 40; size -= 2) {
        const auto lines = wrapLines(lib, font, size, words, preset.max_width);
        if (static_cast<int>(lines.size()) > preset.max_lines) continue;
        if (static_cast<double>(lines.size()) * size * preset.line_height <= MAX_BLOCK_H)
            return size;
    }
    return 40;
}

// ── keyframe helpers ────────────────────────────────────────────────────────

using Keys = std::vector<std::pair<int, double>>;

Keys normalise(Keys keys) {
    for (auto& key : keys) key.first = std::clamp(key.first, 0, DUR);
    std::stable_sort(keys.begin(), keys.end(),
                     [](const auto& a, const auto& b) { return a.first < b.first; });
    Keys out;
    for (const auto& key : keys) {
        if (!out.empty() && out.back().first == key.first) out.back().second = key.second;
        else out.push_back(key);
    }
    return out;
}

json bareTrack(Keys keys, const std::string& easing = "linear") {
    keys = normalise(std::move(keys));
    json frames = json::array();
    for (const auto& [frame, value] : keys) frames.push_back({{"frame", frame}, {"value", value}});
    return {{"easing", easing}, {"keyframes", frames}};
}

json track(const std::string& property, Keys keys, const std::string& easing = "linear") {
    keys = normalise(std::move(keys));
    json frames = json::array();
    for (const auto& [frame, value] : keys) frames.push_back({{"frame", frame}, {"value", value}});
    return {{"property", property}, {"easing", easing}, {"keyframes", frames}};
}

std::size_t utf8OffsetOf(const std::string& text, int codepoints) {
    std::size_t byte = 0;
    int seen = 0;
    while (byte < text.size() && seen < codepoints) {
        const unsigned char c = static_cast<unsigned char>(text[byte]);
        const int extra = c < 0x80 ? 0 : ((c & 0xE0) == 0xC0 ? 1 : ((c & 0xF0) == 0xE0 ? 2 : 3));
        byte += static_cast<std::size_t>(extra) + 1;
        ++seen;
    }
    return byte;
}

json revealAnimator(const Preset& preset, Keys start_keys) {
    start_keys = normalise(std::move(start_keys));
    json start_frames = json::array();
    for (const auto& [frame, value] : start_keys)
        start_frames.push_back({{"frame", frame}, {"value", value}});

    json selector = {
        {"unit", preset.unit},
        {"shape", preset.shape},
        {"order", "forward"},
        {"combine", "replace"},
        {"exclude_spaces", false},
        {"start", {{"easing", "linear"}, {"keyframes", start_frames}}},
        {"end", {{"easing", "linear"}, {"keyframes", json::array({{{"frame", 0}, {"value", 100.0}},
                                                                  {{"frame", DUR}, {"value", 100.0}}})}}},
    };
    // The selector window covers the *unrevealed* tail: hiding it is the typing.
    return {
        {"id", "typewriter_window"},
        {"selectors", json::array({selector})},
        {"properties", json::array({track("opacity", {{0, 0.0}, {DUR, 0.0}})})},
    };
}

// Shape layers express `position` as an offset from the canvas centre (text
// layers use absolute canvas coordinates), so every authored absolute point is
// rebased here. `size` is the exact rect size.
// Soft frontier: the tail is still hidden with a crisp square window, while a
// narrow band trailing the frontier carries a constant blur. Revealed glyphs
// leave the band already sharp, which reads as a soft typing edge instead of a
// whole-run opacity ramp.
json blurFrontierAnimator(const Preset& preset, int ts, int te, double band) {
    const double low = std::max(0.0, 100.0 - band);
    const int fs = std::clamp(ts, 0, DUR);
    const int fe = std::clamp(te, 0, DUR);
    json selector = {
        {"unit", preset.unit},
        {"shape", "smooth"},
        {"order", "forward"},
        {"combine", "replace"},
        {"exclude_spaces", false},
        {"start", bareTrack({{0, 0.0}, {fs, 0.0}, {fe, low}, {DUR, low}})},
        {"end", bareTrack({{0, 0.0}, {fs, 0.0}, {fe, 100.0}, {DUR, 100.0}})},
    };
    return {
        {"id", "frontier_blur"},
        {"selectors", json::array({selector})},
        {"properties", json::array({track("blur", {{0, 12.0}, {DUR, 12.0}})})},
    };
}

json shapeLayer(const std::string& id, double x, double y, double width, double height,
                const std::string& fill_hex, const std::string& glow_hex, double glow_radius,
                double glow_intensity) {
    (void)glow_hex; (void)glow_radius; (void)glow_intensity;  // shape style.glow is a no-op today
    auto rgba = [](const std::string& hex) {
        json out = json::array();
        for (int i = 1; i < 7; i += 2)
            out.push_back(static_cast<double>(std::stoi(hex.substr(static_cast<std::size_t>(i), 2), nullptr, 16)) / 255.0);
        out.push_back(1.0);
        return out;
    };
    return json{
        {"id", id},
        {"type", "shape"},
        {"size", {width, height}},
        {"position", {x - W / 2.0, y - H / 2.0}},
        {"start_frame", 0},
        {"duration_frames", DUR},
        {"shape", {{"type", "rect"}, {"fill", rgba(fill_hex)}}},
    };
}

std::string hexToJsonColor(const std::string& hex) { return hex; }

// ── plan construction ───────────────────────────────────────────────────────

struct LineMetrics {
    std::u32string text;
    Metrics metrics;
    double left = 0.0;
    double y = 0.0;
    int phrase_start = 0;
    int start_char = 0;
    int end_char = 0;
};

json buildPlan(FT_Library lib, const fs::path& fonts, const Preset& preset) {
    const fs::path font_path = fonts / preset.font;
    const std::u32string phrase = utf8ToU32(preset.phrase);
    const auto words = splitWords(phrase);
    const int size = fitFontSize(lib, font_path, words, preset);
    const auto lines = wrapLines(lib, font_path, size, words, preset.max_width);

    const double line_height = size * preset.line_height;
    const double block_h = static_cast<double>(lines.size()) * line_height;
    const double top = (static_cast<double>(H) - block_h) / 2.0 + line_height / 2.0;

    std::vector<LineMetrics> laid;
    int cursor = 0;
    for (std::size_t i = 0; i < lines.size(); ++i) {
        LineMetrics lm;
        lm.text = lines[i].text;
        lm.phrase_start = lines[i].phrase_start;
        lm.metrics = measureText(lib, font_path, size, lm.text);
        lm.left = (static_cast<double>(W) - lm.metrics.width) / 2.0;
        lm.y = top + static_cast<double>(i) * line_height;
        lm.start_char = cursor;
        lm.end_char = cursor + static_cast<int>(lm.text.size());
        cursor = lm.end_char;
        laid.push_back(std::move(lm));
    }
    const int total_chars = std::max(cursor, 1);

    // Typing schedule: the configured speed, capped by the per-clip budget.
    const int type_start = static_cast<int>(std::lround(preset.start_sec * FPS));
    const int budget = static_cast<int>(std::lround(preset.type_budget * DUR));
    const int natural = static_cast<int>(std::lround(static_cast<double>(total_chars) * preset.frames_per_char));
    const int typed_span = std::clamp(natural, 8, std::max(8, budget));
    const int type_end = std::min(DUR - 6, type_start + typed_span);

    const int erase_start = preset.erase ? std::min(DUR - 24, type_end + 22) : type_end;
    const int erase_end = preset.erase ? DUR - 10 : type_end;

    json layers = json::array();
    layers.push_back(shapeLayer("bg", W / 2.0, H / 2.0, W, H, preset.bg, "", 0.0, 0.0));

    // Accent rule: grows under the block when the typing completes.
    double bar_y = 0.0;
    if (!preset.bar.empty()) {
        bar_y = laid.back().y + size * 0.72;
        json bar = shapeLayer("rule", W / 2.0, bar_y, 420.0, 3.0, preset.bar, preset.bar, 12.0, 0.45);
        bar["animation"] = {{"tracks", json::array({
            track("scale_x", {{0, 0.0}, {type_end, 1.0}}, "out_cubic"),
            track("opacity", {{0, 0.0}, {type_end - 6, 1.0}}, "linear"),
        })}};
        layers.push_back(bar);
    }

    for (std::size_t i = 0; i < laid.size(); ++i) {
        const auto& lm = laid[i];
        const double share_before = static_cast<double>(lm.start_char) / static_cast<double>(total_chars);
        const double share_after = static_cast<double>(lm.end_char) / static_cast<double>(total_chars);
        const int ts = type_start + static_cast<int>(std::lround((type_end - type_start) * share_before));
        int te = type_start + static_cast<int>(std::lround((type_end - type_start) * share_after));
        te = std::max(te, ts + 2);

        Keys start_keys;
        if (preset.erase && i + 1 == laid.size()) {
            // Type forward, hold, then erase right-to-left from the same frontier.
            start_keys = {{0, 0.0},          {ts, 0.0},   {te, 100.0},
                          {erase_start, 100.0}, {erase_end, 0.0}, {DUR, 0.0}};
        } else {
            start_keys = {{0, 0.0}, {ts, 0.0}, {te, 100.0}, {DUR, 100.0}};
        }

        json layer = {
            {"id", "line" + std::to_string(i)},
            {"type", "text"},
            {"text", ""},  // filled with the source slice below
            {"size", {preset.max_width, size * 1.45}},
            {"position", {W / 2.0, lm.y}},
            {"start_frame", 0},
            {"duration_frames", DUR},
            {"style", {{"font", "assets/fonts/" + preset.font},
                       {"font_size", size},
                       {"fill", hexToJsonColor(preset.ink)},
                       {"glow", {{"radius", preset.glow_radius},
                                 {"intensity", preset.glow_intensity},
                                 {"color", preset.glow_color}}}}},
            {"text_animators", json::array({revealAnimator(preset, start_keys)})},
        };
        if (preset.soft_band > 0.0 && !preset.erase)
            layer["text_animators"].push_back(
                blurFrontierAnimator(preset, ts, te, preset.soft_band));
        // slice the UTF-8 source phrase for this line (keeps accents intact)
        const std::size_t byte_start = utf8OffsetOf(preset.phrase, lm.phrase_start);
        const std::size_t byte_end = utf8OffsetOf(preset.phrase, lm.phrase_start + static_cast<int>(lm.text.size()));
        layer["text"] = preset.phrase.substr(byte_start, byte_end - byte_start);

        if (preset.enter && i == 0) {
            layer["animation"] = {{"tracks", json::array({
                track("position_y", {{0, 26.0}, {10, 0.0}}, "out_cubic"),
                track("opacity", {{0, 0.0}, {8, 1.0}}, "linear"),
                track("scale", {{0, 0.94}, {12, 1.0}}, "out_cubic"),
            })}};
        }
        layers.push_back(layer);
    }

    json plan = {
        {"schema", "chronon.render-plan.v3"},
        {"version", 3},
        {"job_id", preset.id},
        {"canvas", {{"width", W}, {"height", H}, {"fps_num", FPS}, {"fps_den", 1}, {"duration_frames", DUR}}},
        {"layers", layers},
        {"output", {{"path", preset.id + ".mp4"}, {"format", "mp4"}, {"codec", "h264"}}},
    };

    // Caret: sampled per frame on the frontier of the line currently being typed.
    if (!preset.caret_color.empty()) {
        const double caret_w = size * preset.caret_w_em;
        const double caret_h = size * preset.caret_h_em;
        Keys xs, ys, ops;
        for (int frame = 0; frame <= DUR; ++frame) {
            std::size_t line_idx = 0;
            const int clipped = std::clamp(frame, type_start, type_end);
            const double global = (type_end > type_start)
                ? static_cast<double>(clipped - type_start) / static_cast<double>(type_end - type_start)
                : 1.0;
            double in_line = global;
            if (preset.erase && frame > erase_start) {
                const double e = static_cast<double>(std::min(frame, erase_end) - erase_start) /
                                 std::max(1, erase_end - erase_start);
                in_line = 1.0 - e;
            } else {
                const double target = global * static_cast<double>(total_chars);
                for (std::size_t i = 0; i < laid.size(); ++i) {
                    if (target <= static_cast<double>(laid[i].end_char) || i + 1 == laid.size()) {
                        line_idx = i;
                        const double span = static_cast<double>(laid[i].end_char - laid[i].start_char);
                        in_line = span > 0.0 ? (target - static_cast<double>(laid[i].start_char)) / span : 1.0;
                        break;
                    }
                }
            }
            in_line = std::clamp(in_line, 0.0, 1.0);
            const auto& lm = laid[std::min(line_idx, laid.size() - 1)];
            const int len = static_cast<int>(lm.text.size());
            const int k = std::clamp(static_cast<int>(std::floor(in_line * static_cast<double>(len))), 0, len);
            const double x = lm.left + lm.metrics.starts[static_cast<std::size_t>(k)];
            const double caret_y = lm.y + size * preset.caret_y_em;
            xs.push_back({frame, x + caret_w * 0.5 - W / 2.0});
            if (frame == 0 || std::abs(ys.back().second - (caret_y - H / 2.0)) > 0.5)
                ys.push_back({frame, caret_y - H / 2.0});
            ops.push_back({frame, 1.0});
        }

        // Blink after the typing (and after the erase) completes.
        const int still_from = preset.erase ? erase_end : type_end;
        bool on = true;
        for (int frame = still_from; frame <= DUR; frame += 8) {
            for (auto& key : ops)
                if (key.first >= frame) key.second = on ? 1.0 : 0.0;
            on = !on;
        }

        json caret = shapeLayer("caret",
                                laid.front().left + caret_w * 0.5,
                                laid.front().y + size * preset.caret_y_em,
                                caret_w, caret_h, preset.caret_color, preset.caret_color, 10.0, 0.40);
        // Shape position tracks are ADDITIVE to the layer position, so carry
        // the travel as a delta from the first sampled point.
        const double x0 = xs.front().second;
        const double y0 = ys.front().second;
        for (auto& key : xs) key.second -= x0;
        for (auto& key : ys) key.second -= y0;
        caret["animation"] = {{"tracks", json::array({
            track("position_x", xs),
            track("position_y", ys),
            track("opacity", ops),
        })}};
        layers.push_back(caret);
        plan["layers"] = layers;
    }

    return plan;
}

json motionMetadata(const Preset& preset, int size, int lines) {
    return {
        {"id", preset.id},
        {"phrase", preset.phrase},
        {"fit", preset.fit},
        {"font", preset.font},
        {"font_size", size},
        {"lines", lines},
        {"unit", preset.unit},
        {"reveal_shape", preset.shape},
        {"caret", preset.caret_color.empty() ? json(nullptr) : json(preset.caret_color)},
        {"caret_block_em", {{"width", preset.caret_w_em}, {"height", preset.caret_h_em}, {"y", preset.caret_y_em}}},
        {"erase", preset.erase},
        {"entrance", preset.enter},
        {"blink", preset.blink},
        {"frames_per_char", preset.frames_per_char},
    };
}
}  // namespace

int main(int argc, char** argv) {
    if (argc < 3) {
        std::cerr << "usage: emit_typewriter_pack_v1 <repo-root> <plan-output-dir> [motion-id ...]\n";
        return 2;
    }
    const fs::path repo = argv[1];
    const fs::path out = argv[2];
    const fs::path fonts = repo / "Chronon3d/assets/fonts";
    fs::create_directories(out);

    std::vector<std::string> wanted;
    for (int i = 3; i < argc; ++i) wanted.emplace_back(argv[i]);

    FT_Library lib = nullptr;
    if (FT_Init_FreeType(&lib)) {
        std::cerr << "FreeType init failed\n";
        return 1;
    }

    json motions = json::array();
    for (const auto& preset : kPresets) {
        if (!wanted.empty() && std::find(wanted.begin(), wanted.end(), preset.id) == wanted.end()) continue;
        const std::u32string phrase = utf8ToU32(preset.phrase);
        const auto words = splitWords(phrase);
        const int size = fitFontSize(lib, fonts / preset.font, words, preset);
        const auto lines = wrapLines(lib, fonts / preset.font, size, words, preset.max_width);
        const json plan = buildPlan(lib, fonts, preset);
        std::ofstream(out / (preset.id + ".plan.json")) << plan.dump(1) << "\n";
        motions.push_back(motionMetadata(preset, size, static_cast<int>(lines.size())));
        std::cout << "emitted " << preset.id << " (size " << size << ", " << lines.size() << " line(s))\n";
    }

    if (wanted.empty()) {
        std::ofstream(out / "typewriter_motions.v1.json")
            << json{{"schema", "chronontemplate.typewriter-motions.v1"},
                    {"canvas", {{"width", W}, {"height", H}, {"fps_num", FPS}, {"fps_den", 1}, {"duration_frames", DUR}}},
                    {"motions", motions}}.dump(1)
            << "\n";
    }

    FT_Done_FreeType(lib);
    return 0;
}
