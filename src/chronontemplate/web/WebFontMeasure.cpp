// ChrononTemplate — implementazione misura testo.
//
// Primaria: HarfBuzz (stesso shaper del renderer: advance con GPOS/kerning,
// entro ~1% dalle run renderizzate su Helvetica/Playfair/Arial). Fallback:
// stb_truetype senza shaping (sottostima del 10-30% su alcuni font), poi
// stima euristica del chiamante.
#include "chronontemplate/web/WebFontMeasure.hpp"

#include <cmath>
#include <cstdint>
#include <filesystem>
#include <fstream>
#include <vector>

namespace fs = std::filesystem;

#define STB_TRUETYPE_IMPLEMENTATION
#include "stb_truetype.h"
#ifdef CHRONONTEMPLATE_HAVE_HARFBUZZ
#include <hb-ot.h>
#include <hb.h>
#endif

namespace chronontemplate::web::shot {
namespace {

fs::path resolveFont(const std::string& ref) {
    const fs::path p(ref);
    if (fs::exists(p)) return p;
    // L'emitter gira dentro ChrononTemplate/, il ref e' relativo al workspace.
    const fs::path up = fs::path("..") / p;
    if (fs::exists(up)) return up;
    return {};
}

std::vector<unsigned char> loadBytes(const fs::path& path) {
    std::ifstream f(path, std::ios::binary | std::ios::ate);
    if (!f) return {};
    const auto bytes = static_cast<std::size_t>(f.tellg());
    f.seekg(0);
    std::vector<unsigned char> data(bytes);
    if (!f.read(reinterpret_cast<char*>(data.data()), static_cast<std::streamsize>(bytes)))
        return {};
    return data;
}

#ifdef CHRONONTEMPLATE_HAVE_HARFBUZZ

float measureHB(const std::vector<unsigned char>& data, float sizePx, const std::string& text) {
    hb_blob_t* blob = hb_blob_create(reinterpret_cast<const char*>(data.data()),
                                     static_cast<unsigned>(data.size()), HB_MEMORY_MODE_READONLY,
                                     nullptr, nullptr);
    hb_face_t* face = hb_face_create(blob, 0);
    hb_blob_destroy(blob);
    if (hb_face_get_upem(face) == 0) { hb_face_destroy(face); return -1.f; }
    hb_font_t* font = hb_font_create(face);
    hb_face_destroy(face);
    hb_ot_font_set_funcs(font);
    const int scaled = static_cast<int>(std::lround(sizePx * 64.0));
    hb_font_set_scale(font, scaled, scaled);
    hb_buffer_t* buf = hb_buffer_create();
    hb_buffer_add_utf8(buf, text.data(), static_cast<int>(text.size()), 0,
                       static_cast<int>(text.size()));
    hb_buffer_guess_segment_properties(buf);
    hb_shape(font, buf, nullptr, 0);
    unsigned count = 0;
    hb_glyph_position_t* pos = hb_buffer_get_glyph_positions(buf, &count);
    double width = 0.0;
    for (unsigned i = 0; i < count; ++i) width += pos[i].x_advance / 64.0;
    hb_buffer_destroy(buf);
    hb_font_destroy(font);
    return static_cast<float>(width);
}

#endif // CHRONONTEMPLATE_HAVE_HARFBUZZ

// Decodifica UTF-8 minima per il fallback senza shaping.
std::uint32_t nextCodepoint(const char*& p, const char* end) {
    if (p >= end) return 0;
    auto c = static_cast<unsigned char>(*p);
    if (c < 0x80) { ++p; return c; }
    std::uint32_t cp = 0; int extra = 0;
    if ((c & 0xE0) == 0xC0) { cp = c & 0x1F; extra = 1; }
    else if ((c & 0xF0) == 0xE0) { cp = c & 0x0F; extra = 2; }
    else if ((c & 0xF8) == 0xF0) { cp = c & 0x07; extra = 3; }
    else { ++p; return 0xFFFD; }
    ++p;
    for (int i = 0; i < extra && p < end; ++i, ++p) {
        auto cc = static_cast<unsigned char>(*p);
        if ((cc & 0xC0) != 0x80) return 0xFFFD;
        cp = (cp << 6) | (cc & 0x3F);
    }
    return cp;
}

float measureSTB(const std::vector<unsigned char>& data, float sizePx, const std::string& text) {
    stbtt_fontinfo font;
    if (!stbtt_InitFont(&font, data.data(), 0)) return -1.f;
    const float scale = stbtt_ScaleForMappingEmToPixels(&font, sizePx);
    double width = 0.0;
    int prev = 0;
    const char* p = text.data();
    const char* end = p + text.size();
    bool first = true;
    while (p < end) {
        const std::uint32_t cp = nextCodepoint(p, end);
        if (cp == 0 || cp == '\n') continue;
        if (!first) width += scale * stbtt_GetCodepointKernAdvance(&font, prev, static_cast<int>(cp));
        int advance = 0, lsb = 0;
        stbtt_GetCodepointHMetrics(&font, static_cast<int>(cp), &advance, &lsb);
        (void)lsb;
        width += scale * advance;
        prev = static_cast<int>(cp);
        first = false;
    }
    return static_cast<float>(width);
}

} // namespace

float measureTextWidth(const std::string& fontRef, float sizePx, const std::string& text) {
    if (text.empty() || !(sizePx > 0.f)) return -1.f;
    const fs::path fontPath = resolveFont(fontRef);
    if (fontPath.empty()) return -1.f;
    std::vector<unsigned char> data = loadBytes(fontPath);
    if (data.empty()) return -1.f;
#ifdef CHRONONTEMPLATE_HAVE_HARFBUZZ
    const float shaped = measureHB(data, sizePx, text);
    if (shaped > 0.f) return shaped;
#endif
    return measureSTB(data, sizePx, text);
}

} // namespace chronontemplate::web::shot
