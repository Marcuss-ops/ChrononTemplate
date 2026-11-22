#pragma once

// doc_pack.hpp — native C++ authoring kit for the 2026 documentary web set.
//
// This is deliberately independent of the old Python web-shot tooling. Layout
// is authored at 1920x1080 and rasterized by Blend2D; only ffmpeg is invoked
// afterwards for H.264 encoding. New primitives live here instead of changing
// the existing Figma/Notion pack.

#include <blend2d.h>

#include <algorithm>
#include <cmath>
#include <cstdint>
#include <filesystem>
#include <iostream>
#include <map>
#include <string>
#include <utility>
#include <vector>

namespace chronon::docshots {

namespace fs = std::filesystem;

constexpr int kW = 1920;
constexpr int kH = 1080;
constexpr int kFps = 30;
constexpr int kFrames = 90;
constexpr double kPi = 3.14159265358979323846;

inline BLRgba32 rgba(int r, int g, int b, int a = 255) {
    return BLRgba32(uint8_t(r), uint8_t(g), uint8_t(b), uint8_t(a));
}

inline double clamp01(double v) { return std::clamp(v, 0.0, 1.0); }
inline double lerp(double a, double b, double t) { return a + (b - a) * t; }
inline double easeInOutCubic(double t) {
    t = clamp01(t);
    return t < 0.5 ? 4.0 * t * t * t : 1.0 - std::pow(-2.0 * t + 2.0, 3.0) * 0.5;
}
inline double easeOutCubic(double t) { return 1.0 - std::pow(1.0 - clamp01(t), 3.0); }
inline double wind(double t, double a, double b) {
    return clamp01((t - a) / std::max(1e-6, b - a));
}

inline fs::path rootDir() {
    static const fs::path root = [] {
        const fs::path file = fs::path(__FILE__);
        if (file.has_parent_path()) {
            fs::path candidate = fs::absolute(file).parent_path();
            for (int i = 0; i < 3; ++i) candidate = candidate.parent_path();
            if (fs::exists(candidate / "assets" / "fonts")) return candidate;
        }
        fs::path candidate = fs::current_path();
        for (int i = 0; i < 8; ++i) {
            if (fs::exists(candidate / "assets" / "fonts")) return candidate;
            if (!candidate.has_parent_path()) break;
            candidate = candidate.parent_path();
        }
        return fs::current_path();
    }();
    return root;
}
inline fs::path fontsDir() { return rootDir() / "assets" / "fonts"; }

struct Fonts {
    std::map<std::string, BLFontFace> faces;
    bool valid{false};
};

inline Fonts& fonts() {
    static Fonts cache = [] {
        Fonts f;
        const std::pair<const char*, const char*> defs[] = {
            {"light", "Inter-Light.ttf"},       {"reg", "Inter-Regular.ttf"},
            {"med", "Inter-Medium.ttf"},        {"semi", "Inter-SemiBold.ttf"},
            {"bold", "Inter-Bold.ttf"},         {"black", "Inter-Black.ttf"},
            {"serif", "PlayfairDisplay.ttf"},   {"serifBold", "PlayfairDisplay-Bold.ttf"},
            {"serifItalic", "PlayfairDisplay-Italic.ttf"},
            {"serifBlackIt", "PlayfairDisplay-BlackItalic.ttf"},
            {"oswald", "Oswald.ttf"},           {"oswaldBold", "Oswald-Bold.ttf"},
            {"dejavu", "DejaVuSans.ttf"},       {"arialBold", "Arial-Bold.ttf"},
            {"mono", "LiberationMono-Bold.ttf"},
        };
        for (const auto& def : defs) {
            BLFontFace face;
            const std::string path = (fontsDir() / def.second).string();
            if (face.createFromFile(path.c_str()) == BL_SUCCESS) {
                f.faces[def.first] = face;
            } else {
                std::cerr << "[doc_pack] missing font: " << path << '\n';
            }
        }
        f.valid = !f.faces.empty();
        return f;
    }();
    return cache;
}

inline BLFont face(const std::string& name, double size) {
    static std::map<std::pair<std::string, int>, BLFont> cache;
    const auto key = std::make_pair(name, int(size * 2.0 + 0.5));
    auto it = cache.find(key);
    if (it == cache.end()) {
        BLFont f;
        const auto fit = fonts().faces.find(name);
        if (fit != fonts().faces.end()) f.createFromFace(fit->second, float(size));
        it = cache.emplace(key, f).first;
    }
    return it->second;
}

inline double textW(const BLFont& f, const std::string& text) {
    BLGlyphBuffer buffer;
    buffer.setUtf8Text(text.c_str(), text.size());
    f.shape(buffer);
    BLTextMetrics metrics;
    f.getTextMetrics(buffer, metrics);
    return metrics.advance.x;
}

inline void fillText(BLContext& c, const BLFont& f, double x, double y,
                     const std::string& text, BLRgba32 color, double alpha = 1.0) {
    if (alpha <= 0.004 || text.empty()) return;
    c.save();
    c.setGlobalAlpha(float(clamp01(alpha)));
    c.setFillStyle(color);
    c.fillUtf8Text(BLPoint(x, y), f, text.c_str(), text.size());
    c.restore();
}

inline void textC(BLContext& c, const BLFont& f, double cx, double baseline,
                  const std::string& text, BLRgba32 color, double alpha = 1.0) {
    fillText(c, f, cx - textW(f, text) * 0.5, baseline, text, color, alpha);
}

// Letter-spaced micro-labels. Text is ASCII by construction (URLs, kickers,
// section eyebrows); using one byte at a time keeps tracking exact.
inline void tracked(BLContext& c, const BLFont& f, double x, double y,
                    const std::string& text, BLRgba32 color, double gap = 1.5,
                    double alpha = 1.0) {
    if (alpha <= 0.004) return;
    c.save();
    c.setGlobalAlpha(float(clamp01(alpha)));
    c.setFillStyle(color);
    double cursor = x;
    for (char ch : text) {
        const std::string one(1, ch);
        c.fillUtf8Text(BLPoint(cursor, y), f, one.c_str(), 1);
        cursor += textW(f, one) + gap;
    }
    c.restore();
}

inline void trackedC(BLContext& c, const BLFont& f, double cx, double y,
                     const std::string& text, BLRgba32 color, double gap = 1.5,
                     double alpha = 1.0) {
    double total = 0.0;
    for (char ch : text) total += textW(f, std::string(1, ch)) + gap;
    tracked(c, f, cx - total * 0.5 + gap * 0.5, y, text, color, gap, alpha);
}

inline void vignette(BLContext& c, double alpha = 70.0, double inner = 0.30) {
    BLGradientStop stops[3] = {
        {0.0, rgba(0, 0, 0, 0)},
        {inner, rgba(0, 0, 0, 0)},
        {1.0, rgba(0, 0, 0, int(alpha))},
    };
    BLRadialGradientValues values(kW * 0.5, kH * 0.5, kW * 0.5, kH * 0.5,
                                  kW * 0.28, kW * 0.78);
    BLGradient grad(values, BL_EXTEND_MODE_PAD, stops, 3);
    c.setFillStyle(grad);
    c.fillRect(BLRect(0, 0, kW, kH));
}

inline void paper(BLContext& c, BLRgba32 color, double vignetteAlpha = 48.0) {
    c.setFillStyle(color);
    c.fillRect(BLRect(0, 0, kW, kH));
    vignette(c, vignetteAlpha, 0.26);
}

inline void grid(BLContext& c, double pitch, BLRgba32 color, double width = 1.0) {
    c.setStrokeStyle(color);
    c.setStrokeWidth(width);
    for (double x = pitch; x < kW; x += pitch) c.strokeLine(BLPoint(x, 0), BLPoint(x, kH));
    for (double y = pitch; y < kH; y += pitch) c.strokeLine(BLPoint(0, y), BLPoint(kW, y));
}

inline void dotGrid(BLContext& c, double pitch, BLRgba32 color, double radius = 1.6) {
    c.setFillStyle(color);
    for (double y = pitch * 0.5; y < kH; y += pitch)
        for (double x = pitch * 0.5; x < kW; x += pitch)
            c.fillCircle(BLCircle(x, y, radius));
}

inline void camera(BLContext& c, double z0, double z1, double cx, double cy, double t) {
    const double z = lerp(z0, z1, easeInOutCubic(t));
    c.translate(kW * 0.5, kH * 0.5);
    c.scale(z, z);
    c.translate(-cx * kW, -cy * kH);
}

inline void roundedCard(BLContext& c, double x, double y, double w, double h,
                        double radius, BLRgba32 fill, bool shadow = true,
                        double shadowAlpha = 34.0) {
    if (shadow) {
        for (int i = 4; i >= 1; --i) {
            const double pad = i * 4.0;
            c.setFillStyle(rgba(0, 0, 0, int(shadowAlpha / (i + 1))));
            c.fillRoundRect(BLRoundRect(x - pad, y - pad + 8, w + pad * 2,
                                       h + pad * 2, radius + pad, radius + pad));
        }
    }
    c.setFillStyle(fill);
    c.fillRoundRect(BLRoundRect(x, y, w, h, radius, radius));
}

inline void outline(BLContext& c, double x, double y, double w, double h,
                    BLRgba32 color, double width = 1.5, double radius = 0.0) {
    c.save();
    c.setStrokeStyle(color);
    c.setStrokeWidth(width);
    if (radius > 0) c.strokeRoundRect(BLRoundRect(x, y, w, h, radius, radius));
    else c.strokeRect(BLRect(x, y, w, h));
    c.restore();
}

inline void pill(BLContext& c, double x, double y, double w, double h,
                 BLRgba32 fill, const std::string& label, BLRgba32 textColor,
                 double size = 15.0, double alpha = 1.0) {
    c.save();
    c.setGlobalAlpha(float(clamp01(alpha)));
    c.setFillStyle(fill);
    c.fillRoundRect(BLRoundRect(x, y, w, h, h * 0.5, h * 0.5));
    textC(c, face("semi", size), x + w * 0.5, y + h * 0.5 + size * 0.34,
         label, textColor);
    c.restore();
}

inline void stamp(BLContext& c, double x, double y, double w, double h,
                  const std::string& text, BLRgba32 color, double angle = -7.0,
                  double alpha = 0.9, double size = 30.0) {
    if (alpha <= 0.004) return;
    c.save();
    c.setGlobalAlpha(float(clamp01(alpha)));
    c.translate(x + w * 0.5, y + h * 0.5);
    c.rotate(angle * kPi / 180.0);
    c.setStrokeStyle(color);
    c.setStrokeWidth(3.0);
    c.strokeRect(BLRect(-w * 0.5, -h * 0.5, w, h));
    c.setStrokeWidth(1.0);
    c.strokeRect(BLRect(-w * 0.5 + 5, -h * 0.5 + 5, w - 10, h - 10));
    const BLFont f = face("black", size);
    textC(c, f, 0, size * 0.34, text, color);
    c.restore();
}

inline void browserChrome(BLContext& c, const std::string& url, bool dark = false,
                          const std::string& title = "DOCUMENT") {
    // Chrome is a fixed UI surface: keep it immune to the editorial camera
    // drift so the tabs and URL never get cropped by a 1.03x push-in.
    c.save();
    c.resetTransform();
    const BLRgba32 bg = dark ? rgba(20, 22, 27) : rgba(240, 240, 238);
    const BLRgba32 fg = dark ? rgba(232, 230, 223) : rgba(58, 60, 64);
    c.setFillStyle(bg);
    c.fillRect(BLRect(0, 0, kW, 64));
    c.setFillStyle(dark ? rgba(255, 255, 255, 16) : rgba(0, 0, 0, 14));
    c.fillRect(BLRect(0, 63, kW, 1));

    c.setFillStyle(dark ? rgba(36, 38, 45) : rgba(255, 255, 255));
    c.fillRoundRect(BLRoundRect(18, 11, 188, 42, 8, 8));
    tracked(c, face("semi", 13), 32, 38, title, fg, 1.1);

    c.setFillStyle(dark ? rgba(36, 38, 45, 150) : rgba(255, 255, 255, 150));
    c.fillRoundRect(BLRoundRect(216, 11, 170, 42, 8, 8));
    tracked(c, face("reg", 12), 232, 37, "OVERVIEW", fg, 1.0);

    c.setFillStyle(dark ? rgba(13, 14, 18) : rgba(227, 228, 225));
    c.fillRoundRect(BLRoundRect(410, 16, 1100, 34, 17, 17));
    c.setFillStyle(dark ? rgba(111, 202, 139) : rgba(74, 157, 100));
    c.fillCircle(BLCircle(430, 33, 5));
    fillText(c, face("reg", 15), 448, 39, url, fg);

    tracked(c, face("med", 11), 1710, 37, "HOME", fg, 1.2);
    fillText(c, face("dejavu", 18), 1810, 39, "\u2022\u2022\u2022", fg);
    c.restore();
}

inline void searchIcon(BLContext& c, double x, double y, double r,
                       BLRgba32 color, double width = 2.2) {
    c.save();
    c.setStrokeStyle(color);
    c.setStrokeWidth(width);
    c.strokeCircle(BLCircle(x, y, r));
    c.strokeLine(BLPoint(x + r * 0.72, y + r * 0.72),
                 BLPoint(x + r * 1.45, y + r * 1.45));
    c.restore();
}

inline void avatar(BLContext& c, double x, double y, double d, BLRgba32 fill,
                   BLRgba32 inner) {
    c.setFillStyle(fill);
    c.fillCircle(BLCircle(x + d * 0.5, y + d * 0.5, d * 0.5));
    c.setFillStyle(inner);
    c.fillCircle(BLCircle(x + d * 0.5, y + d * 0.35, d * 0.18));
    c.fillEllipse(BLEllipse(x + d * 0.5, y + d * 0.84, d * 0.34, d * 0.24));
}

inline void arrowUp(BLContext& c, double cx, double cy, double s, BLRgba32 color) {
    BLPath p;
    p.moveTo(cx, cy - s * 0.6);
    p.lineTo(cx + s * 0.52, cy + s * 0.22);
    p.lineTo(cx + s * 0.18, cy + s * 0.22);
    p.lineTo(cx + s * 0.18, cy + s * 0.62);
    p.lineTo(cx - s * 0.18, cy + s * 0.62);
    p.lineTo(cx - s * 0.18, cy + s * 0.22);
    p.lineTo(cx - s * 0.52, cy + s * 0.22);
    p.close();
    c.setFillStyle(color);
    c.fillPath(p);
}

inline void rule(BLContext& c, double x, double y, double w, BLRgba32 color,
                 double alpha = 1.0, double h = 1.0) {
    c.save();
    c.setGlobalAlpha(float(clamp01(alpha)));
    c.setFillStyle(color);
    c.fillRect(BLRect(x, y, w, h));
    c.restore();
}

inline std::string padded(int n, int width = 4) {
    std::string s = std::to_string(n);
    while (int(s.size()) < width) s.insert(s.begin(), '0');
    return s;
}

struct Scene {
    std::string name;
    std::string category;
    std::string description;
    double stillT{0.80};
    void (*draw)(BLContext&, double, int){nullptr};
};

std::vector<Scene> scenesA();
std::vector<Scene> scenesB();
std::vector<Scene> scenesC();

} // namespace chronon::docshots
