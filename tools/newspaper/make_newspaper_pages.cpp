// make_newspaper_pages.cpp — C++ port of make_newspaper_pages.py (part 1).
//
// Composes the four Linux-native newspaper pages as 1920x1080 PNGs with
// stb_image / stb_truetype / stb_image_write only: no Pillow, no Python, no
// Blend2D, no browser. The Chronon text-layer quirks that motivated baking
// the editorial layout into the PNG are documented in README.md; this tool
// reproduces the same layout, copy and overlay rectangles, and writes
// assets/newspaper/pages/meta.json in the exact schema the plan emitter
// (emit_newspaper_plans.py) consumes.
//
// Layout coordinates, colors, strings and timings mirror the Python source
// 1:1. Sub-pixel raster differences vs Pillow/FreeType are expected (stb
// rasterizes differently); the marker/redaction rectangles are measured
// from this tool's own glyph boxes, so art and overlays cannot drift.

#include <algorithm>
#include <array>
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <filesystem>
#include <fstream>
#include <map>
#include <string>
#include <utility>
#include <vector>

#define STB_IMAGE_IMPLEMENTATION
#include "stb_image.h"
#define STB_TRUETYPE_IMPLEMENTATION
#include "stb_truetype.h"
#define STB_IMAGE_WRITE_IMPLEMENTATION
#include "stb_image_write.h"

namespace fs = std::filesystem;

static constexpr int W = 1920;
static constexpr int H = 1080;

struct Color { uint8_t r, g, b, a; };

static Color hexColor(const char* hex, uint8_t a = 255) {
    unsigned v = 0;
    std::sscanf(hex + 1, "%x", &v);
    return {uint8_t((v >> 16) & 0xFF), uint8_t((v >> 8) & 0xFF), uint8_t(v & 0xFF), a};
}

static constexpr Color INK         = {0x1D, 0x1B, 0x18, 255};
static constexpr Color INK_SOFT    = {0x38, 0x35, 0x30, 255};
static constexpr Color MUTED       = {0x6B, 0x66, 0x5D, 255};
static constexpr Color PAPER       = {0xF6, 0xF1, 0xE4, 255};
static constexpr Color PAPER_COOL  = {0xF7, 0xF4, 0xEA, 255};
static constexpr Color DESK        = {0xC8, 0xC5, 0xBC, 255};
static constexpr Color RULE        = {0xA9, 0xA2, 0x96, 255};
static constexpr Color RED         = {0xA2, 0x3B, 0x32, 255};
static constexpr Color BLUE        = {0x27, 0x55, 0xA8, 255};

// ── deterministic RNG (replaces numpy Generator; layout-only randomness) ─────
struct Rng {
    uint32_t s;
    explicit Rng(uint32_t seed) : s(seed ? seed : 1) {}
    uint32_t next() { s = s * 1664525u + 1013904223u; return s; }
    double uniform() { return (next() >> 8) * (1.0 / 16777216.0); }
    int randint(int lo, int hi) { // [lo, hi)
        return lo + int(next() % uint32_t(hi - lo));
    }
    double normal() { // approx N(0,1) via sum of uniforms
        return (uniform() + uniform() + uniform() + uniform() - 2.0) * 1.2247;
    }
};

// ── RGBA canvas ──────────────────────────────────────────────────────────────
struct Canvas {
    std::vector<uint8_t> px; // W*H*4
    Canvas() : px(size_t(W) * H * 4, 0) {}
    uint8_t* at(int x, int y) { return &px[(size_t(y) * W + x) * 4]; }
    const uint8_t* at(int x, int y) const { return &px[(size_t(y) * W + x) * 4]; }
};

static void blendInto(Canvas& c, int x, int y, Color col) {
    if (x < 0 || y < 0 || x >= W || y >= H) return;
    uint8_t* d = c.at(x, y);
    const double a = col.a / 255.0;
    d[0] = uint8_t(std::lround(d[0] + (col.r - d[0]) * a));
    d[1] = uint8_t(std::lround(d[1] + (col.g - d[1]) * a));
    d[2] = uint8_t(std::lround(d[2] + (col.b - d[2]) * a));
    d[3] = 255;
}

static void fillRect(Canvas& c, int x0, int y0, int x1, int y1, Color col) {
    for (int y = y0; y < y1; ++y)
        for (int x = x0; x < x1; ++x) blendInto(c, x, y, col);
}

static void hLine(Canvas& c, int x0, int x1, int y, Color col, int width = 1) {
    fillRect(c, x0, y, x1, y + width, col);
}
static void vLine(Canvas& c, int x, int y0, int y1, Color col, int width = 1) {
    fillRect(c, x, y0, x + width, y1, col);
}
static void rectOutline(Canvas& c, int x0, int y0, int x1, int y1, Color col, int width = 1) {
    hLine(c, x0, x1, y0, col, width);
    hLine(c, x0, x1, y1 - width, col, width);
    vLine(c, x0, y0, y1, col, width);
    vLine(c, x1 - width, y0, y1, col, width);
}

// Box blur (3 passes ~ Gaussian) on an alpha layer copied into `src` RGBA.
static void boxBlur(Canvas& c, int radius) {
    std::vector<uint8_t> cur = c.px, tmp = c.px;
    auto pass = [&](bool horizontal) {
        for (int y = 0; y < H; ++y)
            for (int x = 0; x < W; ++x) {
                long sr = 0, sg = 0, sb = 0, sa = 0, n = 0;
                for (int k = -radius; k <= radius; ++k) {
                    int xx = horizontal ? x + k : x, yy = horizontal ? y : y + k;
                    if (xx < 0 || yy < 0 || xx >= W || yy >= H) continue;
                    const uint8_t* p = &cur[(size_t(yy) * W + xx) * 4];
                    sr += p[0]; sg += p[1]; sb += p[2]; sa += p[3]; ++n;
                }
                uint8_t* d = &tmp[(size_t(y) * W + x) * 4];
                d[0] = uint8_t(sr / n); d[1] = uint8_t(sg / n);
                d[2] = uint8_t(sb / n); d[3] = uint8_t(sa / n);
            }
        cur.swap(tmp);
    };
    for (int i = 0; i < 3; ++i) { pass(true); pass(false); }
    c.px.swap(cur);
}

static void compositeOver(Canvas& dst, const Canvas& src) {
    for (size_t i = 0; i < dst.px.size(); ++i += 4) {
        double a = src.px[i + 3] / 255.0;
        if (a <= 0) continue;
        dst.px[i]     = uint8_t(std::lround(dst.px[i]     + (src.px[i]     - dst.px[i])     * a));
        dst.px[i + 1] = uint8_t(std::lround(dst.px[i + 1] + (src.px[i + 1] - dst.px[i + 1]) * a));
        dst.px[i + 2] = uint8_t(std::lround(dst.px[i + 2] + (src.px[i + 2] - dst.px[i + 2]) * a));
        dst.px[i + 3] = 255;
    }
}

// ── fonts (stb_truetype) ─────────────────────────────────────────────────────
static fs::path g_fontDir;

struct Font {
    std::vector<unsigned char> bytes;
    stbtt_fontinfo info;
    int ascent = 0, descent = 0, lineGap = 0;
    float scale = 0;
    int size = 0;
};

static std::map<std::pair<std::string, int>, Font> g_fonts;

static const Font& getFont(const std::string& name, int size) {
    auto key = std::make_pair(name, size);
    auto it = g_fonts.find(key);
    if (it != g_fonts.end()) return it->second;
    Font f;
    f.size = size;
    std::ifstream in(g_fontDir / name, std::ios::binary);
    if (!in) { std::fprintf(stderr, "font not found: %s\n", (g_fontDir / name).string().c_str()); std::exit(1); }
    f.bytes.assign(std::istreambuf_iterator<char>(in), std::istreambuf_iterator<char>());
    if (!stbtt_InitFont(&f.info, f.bytes.data(), 0)) {
        std::fprintf(stderr, "stbtt_InitFont failed: %s\n", name.c_str()); std::exit(1);
    }
    f.scale = stbtt_ScaleForMappingEmToPixels(&f.info, float(size));
    // stb vmetrics are in font units: scale to pixels (ascent/descent
    // baselines in drawText/textBBox are pixel-space).
    stbtt_GetFontVMetrics(&f.info, &f.ascent, &f.descent, &f.lineGap);
    f.ascent = int(std::lround(f.ascent * f.scale));
    f.descent = int(std::lround(f.descent * f.scale));
    f.lineGap = int(std::lround(f.lineGap * f.scale));
    return g_fonts.emplace(key, std::move(f)).first->second;
}

// UTF-8 decode
static std::vector<uint32_t> decodeUtf8(const std::string& s) {
    std::vector<uint32_t> out;
    for (size_t i = 0; i < s.size();) {
        auto c = (unsigned char)s[i];
        uint32_t cp = 0; size_t extra = 0;
        if (c < 0x80) { cp = c; extra = 0; }
        else if ((c & 0xE0) == 0xC0) { cp = c & 0x1F; extra = 1; }
        else if ((c & 0xF0) == 0xE0) { cp = c & 0x0F; extra = 2; }
        else if ((c & 0xF8) == 0xF0) { cp = c & 0x07; extra = 3; }
        else { ++i; continue; }
        for (size_t k = 1; k <= extra && i + k < s.size(); ++k)
            cp = (cp << 6) | ((unsigned char)s[i + k] & 0x3F);
        out.push_back(cp);
        i += 1 + extra;
    }
    return out;
}

static float textWidth(const Font& f, const std::string& text) {
    double w = 0; int prev = 0; bool first = true;
    for (uint32_t cp : decodeUtf8(text)) {
        if (!first) w += f.scale * stbtt_GetCodepointKernAdvance(&f.info, prev, int(cp));
        int adv = 0, lsb = 0;
        stbtt_GetCodepointHMetrics(&f.info, int(cp), &adv, &lsb);
        w += f.scale * adv;
        prev = int(cp); first = false;
    }
    return float(w);
}


// Glyph extent relative to the baseline (min/max of bitmap tops/bottoms).
// Pillow's vertical anchors ('t'/'m') align to this box, not to the font
// ascender: 't' puts the top of THIS string at y, 'm' its centre at y.
static void glyphExtents(const Font& f, const std::string& text, double& minBy, double& maxBy) {
    minBy = 1e9; maxBy = -1e9; double cx = 0; int prev = 0; bool first = true;
    for (uint32_t cp : decodeUtf8(text)) {
        if (!first) cx += f.scale * stbtt_GetCodepointKernAdvance(&f.info, prev, int(cp));
        int adv = 0, lsb = 0;
        stbtt_GetCodepointHMetrics(&f.info, int(cp), &adv, &lsb);
        int bw = 0, bh = 0, bx = 0, by = 0;
        stbtt_GetCodepointBitmap(&f.info, f.scale, f.scale, int(cp), &bw, &bh, &bx, &by);
        if (bw > 0 && bh > 0) { minBy = std::min(minBy, double(by)); maxBy = std::max(maxBy, double(by + bh)); }
        cx += f.scale * adv; prev = int(cp); first = false;
    }
    if (minBy > maxBy) { minBy = -f.ascent; maxBy = -f.descent; }
}
static double baselineFor(const Font& f, const std::string& text, double y, char vAnchor) {
    double lo = 0, hi = 0; glyphExtents(f, text, lo, hi);
    if (vAnchor == 'm') return y - (lo + hi) / 2.0;
    return y - lo; // 't' (and default)
}

// Anchor: [l|m|r][t|m|a].
static void drawText(Canvas& c, double x, double y, const std::string& text,
                     const Font& f, Color col, const char* anchor = "lt") {
    double total = textWidth(f, text);
    double startX = x;
    if (anchor[0] == 'm') startX = x - total / 2;
    else if (anchor[0] == 'r') startX = x - total;
    double baseline = baselineFor(f, text, y, anchor[1]);
    double cx = startX;
    int prev = 0; bool first = true;
    for (uint32_t cp : decodeUtf8(text)) {
        if (!first) cx += f.scale * stbtt_GetCodepointKernAdvance(&f.info, prev, int(cp));
        int adv = 0, lsb = 0;
        stbtt_GetCodepointHMetrics(&f.info, int(cp), &adv, &lsb);
        int bw = 0, bh = 0, bx = 0, by = 0;
        unsigned char* bmp = stbtt_GetCodepointBitmap(&f.info, f.scale, f.scale, int(cp), &bw, &bh, &bx, &by);
        if (bmp) {
            for (int row = 0; row < bh; ++row)
                for (int colx = 0; colx < bw; ++colx) {
                    double a = bmp[row * bw + colx] / 255.0;
                    if (a <= 0) continue;
                    int px = int(std::lround(cx + bx + colx));
                    int py = int(std::lround(baseline + by + row));
                    if (px < 0 || py < 0 || px >= W || py >= H) continue;
                    uint8_t* d = c.at(px, py);
                    d[0] = uint8_t(std::lround(d[0] + (col.r - d[0]) * a));
                    d[1] = uint8_t(std::lround(d[1] + (col.g - d[1]) * a));
                    d[2] = uint8_t(std::lround(d[2] + (col.b - d[2]) * a));
                    d[3] = 255;
                }
        }
        cx += f.scale * adv;
        prev = int(cp); first = false;
    }
}

// Bounds of the rendered glyphs, for ink_rect(). Baseline computed as in drawText.
struct BBox { int x0, y0, x1, y1; };
static BBox textBBox(double x, double y, const std::string& text, const Font& f,
                     const char* anchor = "lt") {
    double total = textWidth(f, text);
    double startX = x;
    if (anchor[0] == 'm') startX = x - total / 2;
    else if (anchor[0] == 'r') startX = x - total;
    double baseline = baselineFor(f, text, y, anchor[1]);
    double minX = 1e9, minY = 1e9, maxX = -1e9, maxY = -1e9;
    double cx = startX; int prev = 0; bool first = true;
    for (uint32_t cp : decodeUtf8(text)) {
        if (!first) cx += f.scale * stbtt_GetCodepointKernAdvance(&f.info, prev, int(cp));
        int adv = 0, lsb = 0;
        stbtt_GetCodepointHMetrics(&f.info, int(cp), &adv, &lsb);
        int bw = 0, bh = 0, bx = 0, by = 0;
        stbtt_GetCodepointBitmap(&f.info, f.scale, f.scale, int(cp), &bw, &bh, &bx, &by);
        if (bw > 0 && bh > 0) {
            minX = std::min(minX, cx + bx); maxX = std::max(maxX, cx + bx + bw);
            minY = std::min(minY, baseline + by); maxY = std::max(maxY, baseline + by + bh);
        }
        cx += f.scale * adv; prev = int(cp); first = false;
    }
    if (minX > maxX) { minX = startX; maxX = startX + total; minY = baseline - f.ascent; maxY = baseline - f.descent; }
    return {int(std::floor(minX)), int(std::floor(minY)), int(std::ceil(maxX)), int(std::ceil(maxY))};
}

static std::array<int, 4> inkRect(double x, double y, const std::string& text,
                                  const Font& f, const char* anchor = "lt",
                                  int padX = 8, int padY = 5) {
    BBox b = textBBox(x, y, text, f, anchor);
    return {b.x0 - padX, b.y0 - padY, (b.x1 - b.x0) + 2 * padX, (b.y1 - b.y0) + 2 * padY};
}

static void drawTracked(Canvas& c, double x, double y, const std::string& text,
                        const Font& f, Color col, double tracking = 0.0,
                        const char* anchor = "lt") {
    auto cps = decodeUtf8(text);
    std::vector<double> widths;
    double total = 0;
    for (uint32_t cp : cps) {
        int adv = 0, lsb = 0;
        stbtt_GetCodepointHMetrics(&f.info, int(cp), &adv, &lsb);
        widths.push_back(f.scale * adv); total += f.scale * adv;
    }
    total += tracking * std::max<size_t>(0, cps.size() - 1);
    double cx = x;
    if (anchor[0] == 'm') cx = x - total / 2;
    else if (anchor[0] == 'r') cx = x - total;
    double baseline = baselineFor(f, text, y, 't');
    for (size_t i = 0; i < cps.size(); ++i) {
        // Draw single glyph through a 1-char string path by reusing primitives:
        // encode cp back to UTF-8.
        uint32_t cp = cps[i];
        std::string ch;
        if (cp < 0x80) ch = char(cp);
        else if (cp < 0x800) { ch = char(0xC0 | (cp >> 6)); ch += char(0x80 | (cp & 0x3F)); }
        else { ch = char(0xE0 | (cp >> 12)); ch += char(0x80 | ((cp >> 6) & 0x3F)); ch += char(0x80 | (cp & 0x3F)); }
        // drawText 'lt' aligns this glyph's top to y: pass y so its baseline
        // lands on the tracked baseline.
        double lo = 0, hi = 0; glyphExtents(f, ch, lo, hi);
        drawText(c, cx, baseline + lo, ch, f, col, "lt");
        cx += widths[i] + tracking;
    }
}

// ── page furniture ───────────────────────────────────────────────────────────
static Canvas deskBackground(Color base) {
    Canvas c;
    Rng rng(1979);
    // per-pixel noise precomputed row-wise (same offset for the 3 channels,
    // as in the numpy broadcast)
    std::vector<float> noise(size_t(W) * H);
    for (auto& n : noise) n = float(rng.normal() * 2.6);
    for (int y = 0; y < H; ++y) {
        double t = y / double(H - 1);
        double tr = std::min(255.0, base.r + 14.0) * (1 - t) + std::max(0.0, base.r - 12.0) * t;
        double tg = std::min(255.0, base.g + 14.0) * (1 - t) + std::max(0.0, base.g - 12.0) * t;
        double tb = std::min(255.0, base.b + 14.0) * (1 - t) + std::max(0.0, base.b - 12.0) * t;
        double rx = (W / 2.0), ry = (H / 2.0);
        for (int x = 0; x < W; ++x) {
            double radius = ((x - rx) * (x - rx)) / (rx * rx) + ((y - ry) * (y - ry)) / (ry * ry);
            double vig = 1.0 - 0.10 * std::max(0.0, std::min(1.0, radius - 0.35));
            float n = noise[size_t(y) * W + x];
            uint8_t* d = c.at(x, y);
            d[0] = uint8_t(std::clamp(std::lround(tr * vig + n), 0L, 255L));
            d[1] = uint8_t(std::clamp(std::lround(tg * vig + n), 0L, 255L));
            d[2] = uint8_t(std::clamp(std::lround(tb * vig + n), 0L, 255L));
            d[3] = 255;
        }
    }
    return c;
}

static void paperSheet(Canvas& im, int x0, int y0, int x1, int y1, Color fill) {
    Canvas shadow;
    fillRect(shadow, x0 + 15, y0 + 19, x1 + 15, y1 + 19, {24, 21, 17, 110});
    boxBlur(shadow, 8);
    compositeOver(im, shadow);
    fillRect(im, x0, y0, x1, y1, fill);
    rectOutline(im, x0, y0, x1, y1, hexColor("#D9D2C2"), 1);
    hLine(im, x0 + 1, x1 - 1, y0 + 1, hexColor("#FFFDF7"), 1);
    Rng rng(uint32_t(x0 * 31 + y0));
    for (int i = 0; i < 90; ++i) {
        int fx = rng.randint(x0 + 10, x1 - 10);
        int fy = rng.randint(y0 + 10, y1 - 10);
        int len = rng.randint(4, 22);
        int alpha = rng.randint(4, 11);
        int dy = rng.randint(-1, 2);
        for (int k = 0; k < len; ++k) blendInto(im, fx + k, fy + (dy * k) / std::max(1, len), {120, 108, 84, uint8_t(alpha)});
    }
}

static fs::path g_photoPath;
static void pastePhoto(Canvas& im, int x0, int y0, int x1, int y1) {
    int tw = x1 - x0, th = y1 - y0;
    int sw = 0, sh = 0, comp = 0;
    unsigned char* data = stbi_load(g_photoPath.string().c_str(), &sw, &sh, &comp, 1);
    if (!data) { std::fprintf(stderr, "photo not found: %s\n", g_photoPath.string().c_str()); std::exit(1); }
    // autocontrast cutoff=1: clamp to [p1, p99]
    std::vector<int> hist(256, 0);
    for (int i = 0; i < sw * sh; ++i) hist[data[i]]++;
    auto percentile = [&](double p) {
        long need = long(p * sw * sh), acc = 0;
        for (int v = 0; v < 256; ++v) { acc += hist[v]; if (acc >= need) return v; }
        return 255;
    };
    int lo = percentile(0.01), hi = percentile(0.99);
    if (hi <= lo) { hi = 255; lo = 0; }
    std::vector<uint8_t> gray(size_t(sw) * sh);
    for (int i = 0; i < sw * sh; ++i) {
        int v = data[i];
        v = std::clamp((v - lo) * 255 / (hi - lo), 0, 255);
        gray[i] = uint8_t(v);
    }
    stbi_image_free(data);
    double scale = std::max(tw / double(sw), th / double(sh));
    int rw = std::max(1, int(sw * scale) + 1), rh = std::max(1, int(sh * scale) + 1);
    std::vector<uint8_t> resized(size_t(rw) * rh);
    for (int y = 0; y < rh; ++y)
        for (int x = 0; x < rw; ++x) {
            double gx = (x + 0.5) / scale - 0.5, gy = (y + 0.5) / scale - 0.5;
            int x0i = int(std::floor(gx)), y0i = int(std::floor(gy));
            double fx = gx - x0i, fy = gy - y0i;
            auto sample = [&](int xx, int yy) {
                xx = std::clamp(xx, 0, sw - 1); yy = std::clamp(yy, 0, sh - 1);
                return gray[size_t(yy) * sw + xx];
            };
            double v = sample(x0i, y0i) * (1 - fx) * (1 - fy) + sample(x0i + 1, y0i) * fx * (1 - fy)
                     + sample(x0i, y0i + 1) * (1 - fx) * fy + sample(x0i + 1, y0i + 1) * fx * fy;
            resized[size_t(y) * rw + x] = uint8_t(std::lround(v));
        }
    int left = (rw - tw) / 2, top = (rh - th) / 2;
    for (int y = 0; y < th; ++y)
        for (int x = 0; x < tw; ++x) {
            uint8_t g = resized[size_t(top + y) * rw + (left + x)];
            uint8_t* d = im.at(x0 + x, y0 + y);
            d[0] = uint8_t(std::min(255.0, g * 1.03));
            d[1] = g;
            d[2] = uint8_t(g * 0.96);
            d[3] = 255;
        }
    rectOutline(im, x0, y0, x1, y1, hexColor("#3B3833"), 2);
}

static void stamp(Canvas& im, int x0, int y0, int x1, int y1, const std::string& text, double angleDeg) {
    Canvas layer;
    rectOutline(layer, x0, y0, x1, y1, RED, 4);
    drawText(layer, (x0 + x1) / 2.0, (y0 + y1) / 2.0, text, getFont("Inter-Bold.ttf", 17), RED, "mm");
    // rotate layer around the stamp centre (bilinear)
    double cx = (x0 + x1) / 2.0, cy = (y0 + y1) / 2.0;
    double rad = angleDeg * std::acos(-1.0) / 180.0;
    double cs = std::cos(rad), sn = std::sin(rad);
    Canvas rot;
    for (int y = 0; y < H; ++y)
        for (int x = 0; x < W; ++x) {
            double dx = x - cx, dy = y - cy;
            double sx = cx + dx * cs - dy * sn, sy = cy + dx * sn + dy * cs;
            int ix = int(std::floor(sx)), iy = int(std::floor(sy));
            double fx = sx - ix, fy = sy - iy;
            // nearest is enough for a thin outline stamp at this scale
            int nx = int(std::lround(sx)), ny = int(std::lround(sy));
            (void)fx; (void)fy; (void)ix; (void)iy;
            if (nx < 0 || ny < 0 || nx >= W || ny >= H) continue;
            const uint8_t* p = layer.at(nx, ny);
            if (p[3] == 0) continue;
            uint8_t* d = rot.at(x, y);
            d[0] = p[0]; d[1] = p[1]; d[2] = p[2]; d[3] = p[3];
        }
    compositeOver(im, rot);
}

static void rule(Canvas& c, int x0, int y, int x1, Color col, int width = 1) { hLine(c, x0, x1, y, col, width); }

// ── scene metadata ───────────────────────────────────────────────────────────
struct Marker { std::string id; std::array<int, 4> rect; int delay, span; double peak; };
struct SceneMeta {
    int duration = 0;
    std::vector<Marker> markers;
    std::vector<Marker> redactions;
    std::string asset;
};

static void writeMeta(const fs::path& path, const std::map<std::string, SceneMeta>& meta) {
    std::ofstream out(path);
    out << "{\n";
    size_t idx = 0;
    for (auto& [name, m] : meta) {
        out << "  \"" << name << "\": {\n";
        out << "    \"duration\": " << m.duration << ",\n";
        out << "    \"markers\": [";
        for (size_t i = 0; i < m.markers.size(); ++i) {
            auto& k = m.markers[i];
            if (i) out << ", ";
            out << "{\"id\": \"" << k.id << "\", \"rect\": [" << k.rect[0] << ", " << k.rect[1] << ", " << k.rect[2] << ", " << k.rect[3]
                << "], \"delay\": " << k.delay << ", \"span\": " << k.span << ", \"peak\": " << k.peak << "}";
        }
        out << "],\n";
        out << "    \"redactions\": [";
        for (size_t i = 0; i < m.redactions.size(); ++i) {
            auto& k = m.redactions[i];
            if (i) out << ", ";
            out << "{\"id\": \"" << k.id << "\", \"rect\": [" << k.rect[0] << ", " << k.rect[1] << ", " << k.rect[2] << ", " << k.rect[3]
                << "], \"delay\": " << k.delay << ", \"span\": " << k.span << "}";
        }
        out << "],\n";
        out << "    \"asset\": \"" << m.asset << "\"\n";
        out << "  }" << (++idx < meta.size() ? "," : "") << "\n";
    }
    out << "}\n";
}

// ── 01. Front page ───────────────────────────────────────────────────────────
static std::pair<Canvas, SceneMeta> frontPage() {
    Canvas im = deskBackground(DESK);
    paperSheet(im, 150, 86, 1770, 1000, PAPER);
    drawTracked(im, 210, 120, "THE CHRONON JOURNAL  \xC2\xB7  SECTION D  \xC2\xB7  SUNDAY EDITION",
                getFont("Inter-Bold.ttf", 15), MUTED, 2.6);
    drawText(im, 960, 146, "Science Times", getFont("PlayfairDisplay-Bold.ttf", 106), INK, "mt");
    rule(im, 210, 274, 1710, RULE, 2);
    drawText(im, 960, 284, "TUESDAY, OCTOBER 19, 2026  \xC2\xB7  SCIENCE DESK  \xC2\xB7  WASHINGTON, D.C.",
             getFont("Inter-Medium.ttf", 15), hexColor("#4A4741"), "mt");
    rule(im, 210, 316, 1710, hexColor("#2A2824"), 4);
    drawText(im, 210, 350, "THE MEN WHO", getFont("PlayfairDisplay-Bold.ttf", 92), INK);
    drawText(im, 210, 442, "STARED AT GOATS", getFont("PlayfairDisplay-Bold.ttf", 92), INK);
    drawText(im, 210, 572, "Inside the Pentagon's psychic-spy program \xE2\x80\x94 and the",
             getFont("PlayfairDisplay-Italic.ttf", 31), INK_SOFT);
    drawText(im, 210, 610, "paper trail that refused to disappear.",
             getFont("PlayfairDisplay-Italic.ttf", 31), INK_SOFT);
    drawText(im, 210, 660, "BY ELENA MARSH  \xC2\xB7  WASHINGTON, D.C.", getFont("Inter-Bold.ttf", 14), hexColor("#5A554E"));
    rule(im, 210, 692, 1050, hexColor("#8E897F"), 1);
    pastePhoto(im, 1110, 350, 1710, 690);
    drawText(im, 1110, 700, "A declassified training room, photographed for the archive in 1983.",
             getFont("PlayfairDisplay-Italic.ttf", 16), hexColor("#504C45"));
    drawText(im, 1110, 724, "PHOTO: CHRONON VISUAL LAB / ARCHIVE", getFont("Inter-Medium.ttf", 11), hexColor("#7A746B"));
    const std::vector<std::vector<std::string>> columns = {
        {"For nearly two decades, a small group of","intelligence officers argued that the human",
         "mind could be trained to see across oceans.","The program began with a simple question:",
         "if attention can be focused, can it also be","projected? Files released this month show",
         "that the answer was never settled. What","survived was the paperwork."},
        {"Reviewers described a revolving door of","contractors, retired officers and self-taught",
         "psychics. Each brought a different vocabulary","for the same claim: that distance was a detail,",
         "not a limit. Funding continued through the","1980s, even as internal reports warned that",
         "results could not be repeated outside the lab.","The archive kept growing anyway."},
        {"Historians say the file is valuable less for","what it proves than for what it records: the",
         "confidence of institutions, the fragility of","evidence, and the long afterlife of a secret.",
         "The final memo is dated 1987. Its last line is","a request for more time. The request was",
         "denied, but the pages were never destroyed.","They were simply moved to another box."},
    };
    for (size_t i = 0; i < columns.size(); ++i) {
        int x = 210 + int(i) * 480;
        for (size_t j = 0; j < columns[i].size(); ++j)
            drawText(im, x, 760 + int(j) * 23, columns[i][j], getFont("PlayfairDisplay.ttf", 17), INK_SOFT);
    }
    vLine(im, 675, 750, 940, hexColor("#B9B1A2"), 1);
    vLine(im, 1155, 750, 940, hexColor("#B9B1A2"), 1);
    rule(im, 210, 958, 1710, hexColor("#8E897F"), 1);
    drawText(im, 210, 968, "D1  \xC2\xB7  CHRONON JOURNAL  \xC2\xB7  ALL RIGHTS RESERVED", getFont("Inter-Medium.ttf", 11), MUTED);
    drawText(im, 1710, 968, "PAGE 01", getFont("Inter-Bold.ttf", 11), MUTED, "rt");
    return {std::move(im), {180, {}, {}, ""}};
}

// ── 02. Dossier ──────────────────────────────────────────────────────────────
static std::pair<Canvas, SceneMeta> dossier() {
    Canvas im = deskBackground(hexColor("#C6C3BA"));
    paperSheet(im, 250, 70, 1670, 1010, hexColor("#F3EFE3"));
    drawTracked(im, 330, 122, "ARCHIVE  /  RESEARCH NOTE 1979", getFont("Inter-Bold.ttf", 16), hexColor("#6B6862"), 2.2);
    rule(im, 330, 158, 1450, hexColor("#8B877F"), 2);
    drawText(im, 330, 196, "... Project.", getFont("PlayfairDisplay.ttf", 58), hexColor("#5D5B57"));
    drawText(im, 330, 280, "primarily involved", getFont("PlayfairDisplay.ttf", 58), hexColor("#5D5B57"));
    const Font& focus = getFont("PlayfairDisplay-Bold.ttf", 74);
    drawText(im, 330, 378, "remote viewing", focus, BLUE);
    auto marker = inkRect(330, 378, "remote viewing", focus, "lt", 14, 9);
    drawText(im, 330, 504, "Project was overseen until 1987", getFont("PlayfairDisplay.ttf", 46), hexColor("#5D5B57"));
    drawText(im, 330, 588, "Albert Stubblebine", getFont("PlayfairDisplay-Bold.ttf", 56), hexColor("#6D6861"));
    drawText(im, 330, 664, "former head of the Defense", getFont("PlayfairDisplay.ttf", 42), hexColor("#5D5B57"));
    drawText(im, 330, 718, "Intelligence Agency", getFont("PlayfairDisplay.ttf", 42), hexColor("#5D5B57"));
    const std::vector<std::string> leftNotes = {
        "Records released under the","declassification review show","a long-running program that",
        "trained viewers to describe","distant locations from a","controlled room. The file",
        "contains interviews, session","notes and administrative","memos spanning more than","a decade of work."};
    const std::vector<std::string> rightNotes = {
        "Funding was renewed each","year despite mixed results.","Reviewers noted that the",
        "program produced few","reliable leads and that","independent replication",
        "remained difficult. The","archive copy is incomplete;","several pages are marked","as withheld."};
    for (auto [x, notes] : std::vector<std::pair<int, const std::vector<std::string>*>>{{330, &leftNotes}, {940, &rightNotes}})
        for (size_t i = 0; i < notes->size(); ++i)
            drawText(im, x, 790 + int(i) * 18, (*notes)[i], getFont("PlayfairDisplay.ttf", 15), hexColor("#77736C"));
    rule(im, 330, 972, 1450, hexColor("#8B877F"), 1);
    drawText(im, 330, 982, "DECLASSIFIED  /  ARCHIVE COPY  /  PAGE 12 OF 29", getFont("Inter-Medium.ttf", 11), hexColor("#6B6862"));
    drawText(im, 1450, 982, "PAGE 12", getFont("Inter-Bold.ttf", 11), hexColor("#6B6862"), "rt");
    stamp(im, 1352, 116, 1592, 174, "DECLASSIFIED", -4.5);
    SceneMeta m; m.duration = 150;
    m.markers.push_back({"dossier_marker", marker, 34, 40, 0.30});
    return {std::move(im), m};
}

// ── 03. Highlighter ──────────────────────────────────────────────────────────
static std::pair<Canvas, SceneMeta> highlighter() {
    Canvas im = deskBackground(hexColor("#C7C4BB"));
    paperSheet(im, 220, 200, 1700, 880, PAPER_COOL);
    drawTracked(im, 960, 250, "CONTEMPORARY PRESS  /  ARCHIVE CLIPPING", getFont("Inter-Bold.ttf", 15), MUTED, 2.6, "mt");
    rule(im, 310, 286, 1610, hexColor("#A7A199"), 1);
    const Font& big = getFont("PlayfairDisplay.ttf", 54);
    drawText(im, 960, 338, "Over the years more than 20", big, hexColor("#2C2A27"), "mt");
    drawText(im, 960, 402, "psychics were employed.", big, hexColor("#2C2A27"), "mt");
    const Font& mid = getFont("PlayfairDisplay.ttf", 36);
    drawText(im, 960, 492, "some ended up in psychiatric hospitals,", mid, hexColor("#5E5B56"), "mt");
    drawText(im, 960, 540, "others lost the plot ...", mid, hexColor("#5E5B56"), "mt");
    drawText(im, 960, 620, "obsessed with crop circles and aliens.", getFont("PlayfairDisplay-Italic.ttf", 36), hexColor("#5E5B56"), "mt");
    drawText(im, 960, 700, "\xE2\x80\x94 filed by the science desk, undated", getFont("PlayfairDisplay-Italic.ttf", 18), hexColor("#77736C"), "mt");
    rule(im, 310, 790, 1610, hexColor("#A7A199"), 1);
    drawText(im, 310, 806, "FIG. 04  \xC2\xB7  PRESS CLIPPING, UNDATED", getFont("Inter-Medium.ttf", 11), MUTED);
    drawText(im, 1610, 806, "SOURCE: CHRONON ARCHIVE", getFont("Inter-Medium.ttf", 11), MUTED, "rt");
    auto m1 = inkRect(960, 402, "psychics were employed.", big, "mt", 14, 8);
    auto m2 = inkRect(960, 620, "crop circles and aliens.", getFont("PlayfairDisplay-Italic.ttf", 36), "mt", 12, 7);
    SceneMeta m; m.duration = 150;
    m.markers.push_back({"sweep_marker_1", m1, 34, 42, 0.62});
    m.markers.push_back({"sweep_marker_2", m2, 82, 34, 0.52});
    return {std::move(im), m};
}

// ── 04. Memo ─────────────────────────────────────────────────────────────────
static std::pair<Canvas, SceneMeta> memo() {
    Canvas im = deskBackground(hexColor("#C4C1B8"));
    paperSheet(im, 230, 80, 1690, 1000, hexColor("#F5F1E5"));
    drawTracked(im, 960, 126, "DEPARTMENT OF DEFENSE", getFont("Inter-Bold.ttf", 26), hexColor("#2E2B27"), 2.2, "mt");
    drawText(im, 960, 168, "DECLASSIFIED  \xC2\xB7  ARCHIVE COPY", getFont("Inter-Medium.ttf", 15), MUTED, "mt");
    stamp(im, 1390, 126, 1640, 184, "DECLASSIFIED", -4.0);
    rule(im, 330, 208, 1590, hexColor("#8B877F"), 2);
    const Font& mono = getFont("LiberationMono-Bold.ttf", 34);
    const std::vector<std::string> body = {
        "The program was reviewed in","years 1983 and 1984 by the",
        "former head of the Defense","Intelligence Agency."};
    for (size_t i = 0; i < body.size(); ++i)
        drawText(im, 330, 258 + int(i) * 52, body[i], mono, INK_SOFT);
    auto dateRect = inkRect(330, 310, "years 1983 and 1984", mono, "lt", 8, 5);
    drawText(im, 330, 560, "Selected phrases remain", getFont("PlayfairDisplay.ttf", 44), INK_SOFT);
    drawText(im, 330, 614, "redacted in this copy.", getFont("PlayfairDisplay.ttf", 44), INK_SOFT);
    drawText(im, 1120, 754, "REDACTED", getFont("Inter-Bold.ttf", 13), hexColor("#8B2F28"));
    drawText(im, 1120, 866, "SOURCE AND METHOD WITHHELD", getFont("Inter-Medium.ttf", 12), MUTED);
    rule(im, 330, 954, 1590, hexColor("#8B877F"), 1);
    drawText(im, 330, 966, "ARCHIVE  /  BOX 14  /  FOLDER 03  /  PAGE 07", getFont("Inter-Medium.ttf", 11), MUTED);
    drawText(im, 1590, 966, "PAGE 07", getFont("Inter-Bold.ttf", 11), MUTED, "rt");
    SceneMeta m; m.duration = 150;
    m.markers.push_back({"memo_date_marker", dateRect, 38, 40, 0.52});
    m.redactions.push_back({"memo_redaction_1", {1120, 788, 330, 26}, 22, 8, 1.0});
    m.redactions.push_back({"memo_redaction_2", {1120, 824, 240, 26}, 28, 8, 1.0});
    return {std::move(im), m};
}

int main(int argc, char** argv) {
    fs::path root = argc > 1 ? fs::path(argv[1]) : fs::path(".");
    g_fontDir = root / "assets" / "fonts";
    g_photoPath = root / "assets" / "newspaper" / "front_page_photo.jpg";
    fs::path outDir = root / "assets" / "newspaper" / "pages";
    fs::create_directories(outDir);
    std::map<std::string, SceneMeta> meta;
    struct Builder { const char* name; std::pair<Canvas, SceneMeta> (*fn)(); };
    for (auto b : std::vector<Builder>{{"front_page", frontPage}, {"dossier", dossier}, {"highlighter", highlighter}, {"memo", memo}}) {
        auto [canvas, sceneMeta] = b.fn();
        fs::path path = outDir / (std::string(b.name) + ".png");
        if (!stbi_write_png(path.string().c_str(), W, H, 4, canvas.px.data(), W * 4)) {
            std::fprintf(stderr, "failed to write %s\n", path.string().c_str());
            return 1;
        }
        sceneMeta.asset = std::string("assets/newspaper/pages/") + b.name + ".png";
        meta[b.name] = sceneMeta;
        std::printf("wrote %s (%dx%d)\n", path.string().c_str(), W, H);
    }
    writeMeta(outDir / "meta.json", meta);
    std::printf("wrote %s\n", (outDir / "meta.json").string().c_str());
    return 0;
}
