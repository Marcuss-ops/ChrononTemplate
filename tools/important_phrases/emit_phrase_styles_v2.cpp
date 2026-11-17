// ChrononTemplate — modern phrase styles v2 (C++ emitter).
// Ten coloured-group phrase styles ("Kind of. But also, not really." look): modern serif/sans fonts,
// simple radial plates, coloured glow, soft reflection shadow, staggered rise-in.
// Text widths come from FreeType so the groups are centred exactly like the layout expects.
//
// Usage: chronontemplate_emit_phrase_styles_v2 <repo-root> <output-dir> [style_idx ...]
//   expects the static fonts in <repo>/Chronon3d/assets/fonts and plates in <repo>/Chronon3d/assets/images
#include <nlohmann/json.hpp>
#include <ft2build.h>
#include FT_FREETYPE_H

#include <filesystem>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>

namespace {
using json = nlohmann::ordered_json;
namespace fs = std::filesystem;

constexpr int W = 1920, H = 1080, FPS = 30, FR = 120;
const char *Y = "#FFD83A", *WH = "#FFFFFF", *R = "#FF2A1F";
const std::vector<std::string> kGroups = {"Kind of.", "But also,", "not really."};

struct Style {
    std::string id, font;
    int size;
    std::string bg1, bg2;
    std::string colors[3];
    bool light;
};

const std::vector<Style> kStyles = {
    {"01_newsreader_graphite", "Newsreader-Medium.ttf", 128, "#4a4a4a", "#121212", {Y, WH, R}, false},
    {"02_sourceserif_charcoal", "SourceSerif4-Semibold.ttf", 120, "#3c3c40", "#0e0e10", {WH, WH, WH}, false},
    {"03_fraunces_cream", "Fraunces-Semibold.ttf", 124, "#f4eee2", "#d8cfba", {"#1a1a1a", "#1a1a1a", "#C2261B"}, true},
    {"04_instrumentserif_navy", "InstrumentSerif-Regular.ttf", 150, "#223049", "#0a0f1a", {"#FFE08A", WH, "#FF7A6B"}, false},
    {"05_youngserif_forest", "YoungSerif-Regular.ttf", 118, "#24402f", "#0a1510", {"#F6E7B0", WH, "#F28C5B"}, false},
    {"06_gloock_wine", "Gloock-Regular.ttf", 118, "#4b1f2a", "#140509", {"#F5D9A8", WH, "#FF8F8F"}, false},
    {"07_literata_slate", "Literata-Semibold.ttf", 118, "#e9edf1", "#c3ccd6", {"#0F2A47", "#0F2A47", "#D8322A"}, true},
    {"08_geist_black", "Geist-Bold.ttf", 112, "#262626", "#000000", {WH, WH, "#4DA3FF"}, false},
    {"09_figtree_sand", "Figtree-ExtraBold.ttf", 118, "#efe3cf", "#cdb998", {"#2B2118", "#2B2118", "#E0541D"}, true},
    {"10_onest_ink", "Onest-Bold.ttf", 114, "#1c2540", "#05070f", {"#7CF0C9", WH, "#FFB454"}, false},
};

double textWidth(FT_Library lib, const fs::path& font, int size, const std::string& text) {
    FT_Face face;
    if (FT_New_Face(lib, font.c_str(), 0, &face)) throw std::runtime_error("cannot open font " + font.string());
    FT_Set_Pixel_Sizes(face, 0, size);
    double w = 0;
    FT_UInt prev = 0;
    for (unsigned char ch : text) {
        const FT_UInt g = FT_Get_Char_Index(face, ch);
        if (prev && FT_HAS_KERNING(face)) {
            FT_Vector k;
            FT_Get_Kerning(face, prev, g, FT_KERNING_DEFAULT, &k);
            w += k.x / 64.0;
        }
        FT_Load_Glyph(face, g, FT_LOAD_DEFAULT);
        w += face->glyph->advance.x / 64.0;
        prev = g;
    }
    FT_Done_Face(face);
    return w;
}

json track(const std::string& prop, std::vector<std::pair<int, double>> keys, const std::string& easing) {
    json k = json::array();
    for (auto& [f, v] : keys) k.push_back({{"frame", f}, {"value", v}});
    return {{"property", prop}, {"keyframes", k}, {"easing", easing}};
}

json animation(int s0, int s1, double peak, double blur) {
    json t = json::array();
    if (blur > 0) t.push_back(track("blur", {{0, blur}, {FR, blur}}, "linear"));
    t.push_back(track("position_y", {{0, 28}, {s0, 28}, {s1, 0}}, "out_cubic"));
    t.push_back(track("opacity", {{0, 0}, {s0, 0}, {s1, peak}}, "linear"));
    return {{"tracks", t}};
}

json buildPlan(FT_Library lib, const fs::path& fonts, const Style& s) {
    const std::string font = "assets/fonts/" + s.font;
    std::vector<double> ws;
    double total = 0;
    const int gap = static_cast<int>(s.size * .28);
    for (auto& g : kGroups) { ws.push_back(textWidth(lib, fonts / s.font, s.size, g)); total += ws.back(); }
    total += gap * 2;
    double x = (W - total) / 2;

    json layers = json::array();
    layers.push_back({{"id", "bg"}, {"type", "image"}, {"asset", "assets/images/" + s.id + "_plate.png"},
                      {"size", {W, H}}, {"position", {0, 0}}, {"start_frame", 0}, {"duration_frames", FR}});
    for (size_t k = 0; k < kGroups.size(); ++k) {
        const double cx = x + ws[k] / 2;
        x += ws[k] + gap;
        const int s0 = 9 + static_cast<int>(k) * 14, s1 = s0 + 16;
        layers.push_back({{"id", "shadow" + std::to_string(k)}, {"type", "text"}, {"text", kGroups[k]},
                          {"size", {W, H}}, {"position", {cx, 540 + s.size * 0.95}},
                          {"style", {{"font", font}, {"font_size", s.size}, {"fill", "#000000"}}},
                          {"start_frame", 0}, {"duration_frames", FR}, {"animation", animation(s0, s1, 0.18, 14)}});
        layers.push_back({{"id", "word" + std::to_string(k)}, {"type", "text"}, {"text", kGroups[k]},
                          {"size", {W, H}}, {"position", {cx, 540}},
                          {"style", {{"font", font}, {"font_size", s.size}, {"fill", s.colors[k]},
                                     {"glow", {{"radius", s.light ? 10 : 18}, {"intensity", s.light ? 0.2 : 0.55},
                                               {"color", s.colors[k]}}}}},
                          {"start_frame", 0}, {"duration_frames", FR}, {"animation", animation(s0, s1, 1.0, 0)}});
    }
    return {{"schema", "chronon.render-plan.v2"}, {"version", 2}, {"job_id", s.id},
            {"canvas", {{"width", W}, {"height", H}, {"fps_num", FPS}, {"fps_den", 1}, {"duration_frames", FR}}},
            {"layers", layers}, {"output", {{"path", s.id + ".mp4"}, {"format", "mp4"}, {"codec", "h264"}}}};
}
}  // namespace

int main(int argc, char** argv) {
    if (argc < 3) { std::cerr << "usage: emit_phrase_styles_v2 <repo-root> <out-dir> [idx...]\n"; return 2; }
    const fs::path repo = argv[1], out = argv[2];
    fs::create_directories(out);
    FT_Library lib;
    FT_Init_FreeType(&lib);
    std::vector<size_t> idx;
    for (int i = 3; i < argc; ++i) idx.push_back(std::stoul(argv[i]));
    if (idx.empty()) for (size_t i = 0; i < kStyles.size(); ++i) idx.push_back(i);
    for (size_t i : idx) {
        const Style& s = kStyles.at(i);
        std::ofstream(out / (s.id + ".plan.json")) << buildPlan(lib, repo / "Chronon3d/assets/fonts", s).dump(1);
        std::cout << "emitted " << s.id << "\n";
    }
    FT_Done_FreeType(lib);
}
