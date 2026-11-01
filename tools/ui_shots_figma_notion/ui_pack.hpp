#pragma once

// ui_pack.hpp — ChrononTemplate "figma/notion pack": native UI compositions.
//
// Fifo shots redrawn as Figma/Notion-style interface stills + short mp4 clips
// with Blend2D. Every pixel is authored vector geometry and native text; no
// reference screenshot is ever loaded. Layout space is 3840x2160 (same as the
// youtuber_style native rebuilds) rasterized to 1920x1080.

#include "../youtuber_style/common.hpp"

#include <cctype>
#include <map>
#include <utility>

#ifndef M_PI
#define M_PI 3.14159265358979323846
#endif

namespace chronon::uipack {

using chronon::youtuber::lerp;
using chronon::youtuber::easeInOutCubic;
using chronon::youtuber::easeOutCubic;
using chronon::youtuber::kW;
using chronon::youtuber::kH;

inline const std::string kFontsDir  = "C:/Users/pater/Pyt/chronons/ChrononTemplate/assets/fonts";
inline const std::string kPackRoot  = "C:/Users/pater/Pyt/chronons/ChrononTemplate/artifacts/ui_shots_figma_notion_v1";

// palette ---------------------------------------------------------------- //
inline BLRgba32 rgba(int r, int g, int b, int a = 255) { return BLRgba32(uint8_t(r), uint8_t(g), uint8_t(b), uint8_t(a)); }

// ---------------------------------------------------------------- fonts -- //

struct Fonts {
    std::map<std::string, BLFontFace> faces;
    bool valid{false};
};

inline Fonts& fonts() {
    static Fonts g = []() {
        Fonts f;
        static const std::pair<const char*, const char*> defs[] = {
            {"light",       "Inter-Light.ttf"},
            {"reg",         "Inter-Regular.ttf"},
            {"med",         "Inter-Medium.ttf"},
            {"semi",        "Inter-SemiBold.ttf"},
            {"bold",        "Inter-Bold.ttf"},
            {"xbold",       "Inter-ExtraBold.ttf"},
            {"black",       "Inter-Black.ttf"},
            {"dispbold",    "InterDisplay-Bold.ttf"},
            {"helv",        "HelveticaNeue-Regular.otf"},
            {"helvMed",     "HelveticaNeue-Medium.otf"},
            {"helvBold",    "HelveticaNeue-Bold.otf"},
            {"serif",       "PlayfairDisplay.ttf"},
            {"serifBold",   "PlayfairDisplay-Bold.ttf"},
            {"serifMedIt",  "PlayfairDisplay-MediumItalic.ttf"},
            {"serifBlackIt","PlayfairDisplay-BlackItalic.ttf"},
            {"oswald",      "Oswald.ttf"},
            {"oswaldMed",   "Oswald-Medium.ttf"},
            {"oswaldbold",  "Oswald-Bold.ttf"},
            {"impact",      "Impact.ttf"},
            {"anton",       "Anton-Regular.ttf"},
            {"abril",       "AbrilFatface-Regular.ttf"},
            {"play",        "Play-Regular.ttf"},
            {"playBold",    "Play-Bold.ttf"},
            {"dejavu",      "DejaVuSans.ttf"},
            {"georgia",     "Georgia_Bold.ttf"},
            {"freeserif",   "FreeSerif.ttf"},
        };
        for (const auto& d : defs) {
            BLFontFace face;
            if (face.createFromFile((kFontsDir + "/" + d.second).c_str()) == BL_SUCCESS) {
                f.faces[d.first] = face;
            } else {
                std::cerr << "[ui_pack] missing font: " << d.second << std::endl;
            }
        }
        f.valid = !f.faces.empty();
        return f;
    }();
    return g;
}

inline BLFont face(const std::string& name, double size) {
    static std::map<std::pair<std::string, int>, BLFont> cache;
    const auto key = std::make_pair(name, int(size * 2.0 + 0.5));
    auto it = cache.find(key);
    if (it == cache.end()) {
        BLFont f;
        f.createFromFace(fonts().faces[name], float(size));
        it = cache.emplace(key, f).first;
    }
    return it->second;
}

// ----------------------------------------------------------------- text -- //

inline double textW(const BLFont& f, const std::string& s) {
    BLGlyphBuffer b; b.setUtf8Text(s.c_str(), s.size());
    f.shape(b);
    BLTextMetrics m; f.getTextMetrics(b, m);
    return m.advance.x;
}

inline void fillText(BLContext& c, const BLFont& f, double x, double y, const std::string& s,
                     BLRgba32 col, double alpha = 1.0) {
    if (alpha <= 0.004) return;
    c.save();
    c.setGlobalAlpha(float(std::clamp(alpha, 0.0, 1.0)));
    c.setFillStyle(col);
    c.fillUtf8Text(BLPoint(x, y), f, s.c_str(), s.size());
    c.restore();
}

inline void textC(BLContext& c, const BLFont& f, double cx, double y, const std::string& s,
                  BLRgba32 col, double alpha = 1.0) {
    fillText(c, f, cx - textW(f, s) * 0.5, y, s, col, alpha);
}

// UTF-8 safe prefix for the typewriter reveals (never splits a multibyte glyph).
inline std::string typed(const std::string& s, double e) {
    if (e <= 0.0) return "";
    if (e >= 1.0) return s;
    size_t n = size_t(double(s.size()) * e + 0.5);
    if (n > s.size()) n = s.size();
    while (n < s.size() && (((unsigned char)s[n]) & 0xC0) == 0x80) --n;
    return s.substr(0, n);
}

inline double clamp01(double v) { return std::clamp(v, 0.0, 1.0); }
inline double wind(double t, double t0, double t1) { return clamp01((t - t0) / std::max(1e-6, t1 - t0)); }

// ------------------------------------------------------------ backdrops -- //

inline void dotGrid(BLContext& c, double pitch, BLRgba32 col, double r) {
    for (double y = pitch * 0.5; y < kH; y += pitch)
        for (double x = pitch * 0.5; x < kW; x += pitch) {
            c.setFillStyle(col); c.fillCircle(BLCircle(x, y, r));
        }
}

inline void lineGrid(BLContext& c, double pitch, BLRgba32 col) {
    for (double x = pitch; x < kW; x += pitch) { c.setFillStyle(col); c.fillRect(BLRect(x, 0, 3, kH)); }
    for (double y = pitch; y < kH; y += pitch) { c.setFillStyle(col); c.fillRect(BLRect(0, y, kW, 3)); }
}

inline void fillGrad(BLContext& c, double x, double y, double w, double h,
                     BLRgba32 a, BLRgba32 b, bool vertical = true) {
    BLGradientStop st[2] = {{0.0, a}, {1.0, b}};
    BLGradient g(vertical ? BLLinearGradientValues(x, y, x, y + h)
                          : BLLinearGradientValues(x, y, x + w, y),
                 BL_EXTEND_MODE_PAD, st, 2);
    c.setFillStyle(g); c.fillRect(BLRect(x, y, w, h));
}

// Layered translucent rounded rects soft enough to read as a card shadow.
inline void softShadow(BLContext& c, double x, double y, double w, double h, double radius,
                       double dy = 42.0, double spread = 64.0, int a = 34) {
    for (int i = 6; i >= 1; --i) {
        const double pad = spread * double(i) / 6.0;
        const double q = double(i) / 7.0;
        const int aa = int(a * q * q);
        if (aa <= 0) continue;
        c.setFillStyle(BLRgba32(10, 14, 24, uint8_t(aa)));
        c.fillRoundRect(BLRoundRect(x - pad, y - pad * 0.5 + dy * q, w + 2 * pad, h + 2 * pad + 22 * q,
                                    radius + pad * 0.8, radius + pad * 0.8));
    }
}

inline void card(BLContext& c, double x, double y, double w, double h, double radius, BLRgba32 fill,
                 bool shadow = false, BLRgba32 border = BLRgba32(0))
{
    if (shadow) softShadow(c, x, y, w, h, radius);
    c.setFillStyle(fill); c.fillRoundRect(BLRoundRect(x, y, w, h, radius, radius));
    if (border.value != 0) {
        c.setStrokeStyle(border); c.setStrokeWidth(5);
        c.strokeRoundRect(BLRoundRect(x, y, w, h, radius, radius));
    }
}

inline void pill(BLContext& c, double x, double y, double w, double h, BLRgba32 fill, double alpha = 1.0) {
    c.save(); c.setGlobalAlpha(float(clamp01(alpha)));
    c.setFillStyle(fill); c.fillRoundRect(BLRoundRect(x, y, w, h, h * 0.5, h * 0.5));
    c.restore();
}

// ------------------------------------------------------------- cursors -- //

static const BLPoint kPointerPts[] = {
    {0, 0}, {0, 34}, {7.8, 25.6}, {12.2, 38.2}, {16.2, 36.6}, {11.8, 24.6}, {25.2, 22.4}
};

inline void pointer(BLContext& c, double x, double y, const std::string& tag, BLRgba32 tagCol,
                    double scale = 1.0, double alpha = 1.0) {
    if (alpha <= 0.004) return;
    c.save(); c.setGlobalAlpha(float(clamp01(alpha)));

    auto polyline = [&](double dx, double dy) {
        BLPath p;
        for (const BLPoint& q : kPointerPts) p.lineTo(x + (q.x + dx) * scale, y + (q.y + dy) * scale);
        p.close(); return p;
    };
    c.setFillStyle(BLRgba32(8, 10, 16, 80));
    c.fillPath(polyline(6, 9));
    c.setFillStyle(BLRgba32(255, 255, 255, 255));
    c.fillPath(polyline(0, 0));
    c.setStrokeStyle(BLRgba32(24, 26, 32, 225)); c.setStrokeWidth(4 * scale);
    c.strokePath(polyline(0, 0));

    if (!tag.empty()) {
        const BLFont f = face("semi", 40);
        const std::string label = " " + tag + " ";
        const double w = textW(f, label) + 40.0;
        card(c, x + 28 * scale, y + 26 * scale, w, 84, 20, tagCol);
        fillText(c, f, x + 28 * scale + 22, y + 26 * scale + 58, label, BLRgba32(255, 255, 255, 255));
    }
    c.restore();
}

inline void ripple(BLContext& c, double x, double y, double e, BLRgba32 col) {
    if (e <= 0.0 || e >= 1.0) return;
    const double q = easeOutCubic(e);
    c.save();
    c.setGlobalAlpha(float((1.0 - e) * 0.75));
    c.setStrokeStyle(col); c.setStrokeWidth(14);
    c.strokeCircle(BLCircle(x, y, 30 + 150 * q));
    c.setFillStyle(col); c.setGlobalAlpha(float((1.0 - e) * 0.35));
    c.fillCircle(BLCircle(x, y, 34));
    c.restore();
}

inline void clickFlash(BLContext& c, double x, double y, double e, BLRgba32 col) {
    if (e <= 0.0 || e >= 1.0) return;
    ripple(c, x, y, e, col);
}

// ----------------------------------------------------- selection & misc -- //

inline void handles(BLContext& c, double x, double y, double w, double h, double e, BLRgba32 col) {
    if (e <= 0.004) return;
    c.save(); c.setGlobalAlpha(float(clamp01(e)));
    c.setStrokeStyle(col); c.setStrokeWidth(6);
    c.strokeRect(BLRect(x, y, w, h));
    const double s = 26.0;
    const double sw = 7.0;
    const double cs[4][2] = {{x, y}, {x + w - s, y}, {x, y + h - s}, {x + w - s, y + h - s}};
    for (const auto& corner : cs) {
        c.setFillStyle(BLRgba32(255, 255, 255, 255));
        c.fillRoundRect(BLRoundRect(corner[0] - sw * 0.5, corner[1] - sw * 0.5, s + sw, s + sw, 6, 6));
        c.setFillStyle(col);
        c.fillRoundRect(BLRoundRect(corner[0], corner[1], s, s, 4, 4));
    }
    c.restore();
}

inline void dashedRect(BLContext& c, double x, double y, double w, double h, BLRgba32 col,
                       double dash = 34.0, double gap = 26.0, double width = 5.0) {
    c.save(); c.setStrokeStyle(col); c.setStrokeWidth(width);
    for (double xx = x; xx < x + w; xx += dash + gap) {
        c.strokeLine(BLPoint(xx, y), BLPoint(std::min(xx + dash, x + w), y));
        c.strokeLine(BLPoint(xx, y + h), BLPoint(std::min(xx + dash, x + w), y + h));
    }
    for (double yy = y; yy < y + h; yy += dash + gap) {
        c.strokeLine(BLPoint(x, yy), BLPoint(x, std::min(yy + dash, y + h)));
        c.strokeLine(BLPoint(x + w, yy), BLPoint(x + w, std::min(yy + dash, y + h)));
    }
    c.restore();
}

inline void checkMark(BLContext& c, double cx, double cy, double size, double e, BLRgba32 col,
                      double width = 10.0) {
    if (e <= 0.004) return;
    const double x0 = cx - size * 0.50, y0 = cy + size * 0.05;
    const double x1 = cx - size * 0.08, y1 = cy + size * 0.40;
    const double x2 = cx + size * 0.48, y2 = cy - size * 0.28;
    if (e < 0.5) {
        const double q = e / 0.5;
        c.setStrokeStyle(col); c.setStrokeWidth(width);
        c.strokeLine(BLPoint(x0, y0), BLPoint(lerp(x0, x1, q), lerp(y0, y1, q)));
    } else {
        const double q = (e - 0.5) / 0.5;
        c.setStrokeStyle(col); c.setStrokeWidth(width);
        c.strokeLine(BLPoint(x0, y0), BLPoint(x1, y1));
        c.strokeLine(BLPoint(x1, y1), BLPoint(lerp(x1, x2, q), lerp(y1, y2, q)));
    }
}

inline void statusPill(BLContext& c, double cx, double cy, const std::string& label, double e,
                       BLRgba32 bg, BLRgba32 fg, double scale = 1.0) {
    if (e <= 0.004) return;
    const double s = scale * easeOutCubic(clamp01(e));
    const BLFont f = face("med", 40 * scale);
    const double w = textW(f, label) + 64 * scale;
    const double h = 84 * scale;
    c.save(); c.setGlobalAlpha(float(clamp01(e)));
    c.setFillStyle(bg); c.fillRoundRect(BLRoundRect(cx - w * s / 2.0, cy - h * s / 2.0, w * s, h * s, h * s / 2.0, h * s / 2.0));
    fillText(c, f, cx - textW(f, label) * s / 2.0, cy + 13 * scale * s, label, fg);
    c.restore();
}

inline void caretTriangle(BLContext& c, double cx, double cy, double size, double rotRight, BLRgba32 col) {
    BLPath p;
    const double ang = easeInOutCubic(clamp01(rotRight)) * (M_PI / 2.0);
    const BLPoint base[3] = {{-0.45, -0.55}, {0.55, 0.0}, {-0.45, 0.55}};
    for (const BLPoint& q : base) {
        const double px = q.x * size, py = q.y * size;
        const double rx = px * std::cos(ang) - py * std::sin(ang);
        const double ry = px * std::sin(ang) + py * std::cos(ang);
        p.lineTo(cx + rx, cy + ry);
    }
    p.close();
    c.setFillStyle(col); c.fillPath(p);
}

// ----------------------------------------------------------------- cam -- //
// Slow product-shot drift: zoom around a chosen center, in layout space.
struct Cam { double z0, z1, cx, cy; };
inline void cam(BLContext& c, const Cam& cc, double t) {
    const double z = lerp(cc.z0, cc.z1, easeInOutCubic(t));
    c.translate(kW * .5, kH * .5); c.scale(z, z); c.translate(-cc.cx * kW, -cc.cy * kH);
}

} // namespace chronon::uipack
