// ChrononTemplate: shared documentary drawing treatment.
//
// The base visual components of the documentary reference look. Every reel
// shares these components but each primitive keeps its OWN aesthetic
// parameters — there is no universal neon style:
//
//   DocumentaryPath  — thin neutral gray-white stroke, secondary to the sun
//   SunOrb           — the brightest point: flat warm-yellow core, big soft
//                      continuous halo (warm drifting to orange)
//   CheckpointMarker — translucent red spot, dimmer than the sun, no rings
//
// Glow is REAL blurred light: luminous elements deposit into an emissive
// buffer, three separable box-blur passes approximate a gaussian falloff and
// the buffer is composited additively (BL_COMP_OP_PLUS). No stacked alpha
// discs, no visible concentric rings: the halo disperses progressively into
// the black background with no detectable edge.

#pragma once

#include "svg_peak_scene.hpp"

#include <blend2d.h>

#include <algorithm>
#include <cmath>
#include <vector>

namespace chronon::svg_parity {

inline BLRgba32 toRgba32(double r, double g, double b, double a = 1.0) {
    return BLRgba32(static_cast<uint32_t>(std::clamp(r, 0.0, 1.0) * 255.0 + 0.5),
                    static_cast<uint32_t>(std::clamp(g, 0.0, 1.0) * 255.0 + 0.5),
                    static_cast<uint32_t>(std::clamp(b, 0.0, 1.0) * 255.0 + 0.5),
                    static_cast<uint32_t>(std::clamp(a, 0.0, 1.0) * 255.0 + 0.5));
}

// ── Emissive glow buffer: continuous blurred light, never visible rings ──────

struct GlowBuffer {
    int w = 0;
    int h = 0;
    std::vector<float> light; // additive RGB

    void init(int width, int height) {
        w = width;
        h = height;
        light.assign(static_cast<std::size_t>(w) * h * 3, 0.0f);
    }

    void clear() {
        std::fill(light.begin(), light.end(), 0.0f);
    }

    void addDisc(double cx, double cy, double radius, double r, double g, double b, double gain) {
        const int x0 = std::max(0, static_cast<int>(cx - radius) - 1);
        const int x1 = std::min(w - 1, static_cast<int>(cx + radius) + 1);
        const int y0 = std::max(0, static_cast<int>(cy - radius) - 1);
        const int y1 = std::min(h - 1, static_cast<int>(cy + radius) + 1);
        const double inv = 1.0 / std::max(1.0, radius * radius);
        for (int y = y0; y <= y1; ++y) {
            for (int x = x0; x <= x1; ++x) {
                const double dx = x + 0.5 - cx;
                const double dy = y + 0.5 - cy;
                const double d2 = (dx * dx + dy * dy) * inv;
                if (d2 > 1.0) continue;
                // soft emitter profile: solid core, cosine edge
                const double fall = d2 < 0.55 ? 1.0 : 0.5 * (1.0 + std::cos(3.141592653589793 *
                                                       (std::sqrt(d2) - 0.55) / 0.45));
                const std::size_t at = (static_cast<std::size_t>(y) * w + x) * 3;
                light[at + 0] += static_cast<float>(r * gain * fall);
                light[at + 1] += static_cast<float>(g * gain * fall);
                light[at + 2] += static_cast<float>(b * gain * fall);
            }
        }
    }

    void addStroke(const std::vector<Vec2>& points, double width,
                   double r, double g, double b, double gain) {
        const double radius = std::max(1.0, width * 0.5);
        for (std::size_t i = 0; i + 1 < points.size(); ++i) {
            const double length = vecDistance(points[i], points[i + 1]);
            const int steps = std::max(1, static_cast<int>(length / std::max(1.0, radius * 0.7)));
            for (int s = 0; s <= steps; ++s) {
                const double t = static_cast<double>(s) / steps;
                addDisc(points[i].x + (points[i + 1].x - points[i].x) * t,
                        points[i].y + (points[i + 1].y - points[i].y) * t,
                        radius, r, g, b, gain);
            }
        }
    }

    // Separable box blur, three passes ≈ gaussian. Radius in pixels.
    void blur(int radius) {
        if (radius <= 0) return;
        const int box = radius * 2 + 1;
        std::vector<float> tmp(light.size());
        auto pass = [&](std::vector<float>& dst, const std::vector<float>& src, bool horizontal) {
            const int outer = horizontal ? h : w;
            const int inner = horizontal ? w : h;
            const int stride = horizontal ? 3 : static_cast<std::size_t>(w) * 3;
            const int step = horizontal ? static_cast<std::size_t>(w) * 3 : 3;
            for (int o = 0; o < outer; ++o) {
                const std::size_t base = static_cast<std::size_t>(o) * step;
                for (int c = 0; c < 3; ++c) {
                    double sum = 0.0;
                    for (int i = -radius; i <= radius; ++i) {
                        const int k = std::clamp(i, 0, inner - 1);
                        sum += src[base + static_cast<std::size_t>(k) * stride + c];
                    }
                    for (int i = 0; i < inner; ++i) {
                        dst[base + static_cast<std::size_t>(i) * stride + c] =
                            static_cast<float>(sum / box);
                        const int out = std::clamp(i - radius, 0, inner - 1);
                        const int in = std::clamp(i + radius + 1, 0, inner - 1);
                        sum += src[base + static_cast<std::size_t>(in) * stride + c] -
                               src[base + static_cast<std::size_t>(out) * stride + c];
                    }
                }
            }
        };
        for (int i = 0; i < 3; ++i) {
            pass(tmp, light, true);
            pass(light, tmp, false);
        }
    }

    // Additive composite of the blurred light over the frame.
    void composite(BLContext& ctx) {
        BLImage glow(w, h, BL_FORMAT_PRGB32);
        BLImageData data;
        if (glow.getData(&data) != BL_SUCCESS) return;
        auto* pixels = static_cast<uint8_t*>(data.pixelData);
        for (int y = 0; y < h; ++y) {
            auto* row = pixels + static_cast<std::size_t>(y) * data.stride;
            for (int x = 0; x < w; ++x) {
                const std::size_t at = (static_cast<std::size_t>(y) * w + x) * 3;
                const double rr = std::min(1.0, static_cast<double>(light[at + 0]));
                const double gg = std::min(1.0, static_cast<double>(light[at + 1]));
                const double bb = std::min(1.0, static_cast<double>(light[at + 2]));
                const double aa = std::max({rr, gg, bb});
                auto* px = reinterpret_cast<uint32_t*>(row + x * 4);
                *px = (static_cast<uint32_t>(aa * 255.0 + 0.5) << 24) |
                      (static_cast<uint32_t>(rr * 255.0 + 0.5) << 16) |
                      (static_cast<uint32_t>(gg * 255.0 + 0.5) << 8) |
                      static_cast<uint32_t>(bb * 255.0 + 0.5);
            }
        }
        ctx.setCompOp(BL_COMP_OP_PLUS);
        ctx.blitImage(BLPoint(0, 0), glow);
        ctx.setCompOp(BL_COMP_OP_SRC_OVER);
    }
};

// ── Per-primitive styles (calibrated on the documentary reference) ───────────

// DocumentaryPath: thin neutral gray-white stroke. Secondary to the sun.
struct PathStyle {
    double width = 3.0;          // px at 1080p
    double r = 222 / 255.0, g = 226 / 255.0, b = 232 / 255.0;
    double alpha = 0.78;
    double glowGain = 0.24;      // soft halo energy
};

// SunOrb: the brightest point of the scene. Small warm core, large soft
// continuous halo (warm yellow drifting to orange).
struct SunStyle {
    double coreScale = 0.34;     // core radius = markerSize * coreScale
    double coreR = 1.0, coreG = 0.82, coreB = 0.12;   // flat warm yellow
    double hotR = 1.0, hotG = 0.93, hotB = 0.55;      // subtle warmth, never white
    double glowGain = 1.15;
    double glowR = 1.0, glowG = 0.68, glowB = 0.16;   // warm halo drifting orange
};

// CheckpointMarker: translucent red spot, dimmer than the sun, no white core,
// no target-like rings.
struct CheckpointStyle {
    double coreScale = 0.62;
    double coreR = 224 / 255.0, coreG = 50 / 255.0, coreB = 40 / 255.0;
    double alpha = 0.78;
    double glowGain = 0.70;
};

inline void drawPathCore(BLContext& ctx, const std::vector<Vec2>& points,
                         const PathStyle& style, double zoom) {
    if (points.size() < 2) return;
    BLPath path;
    path.moveTo(points[0].x, points[0].y);
    for (std::size_t i = 1; i < points.size(); ++i) {
        path.lineTo(points[i].x, points[i].y);
    }
    ctx.setStrokeStyle(toRgba32(style.r, style.g, style.b, style.alpha));
    ctx.setStrokeWidth(style.width * zoom);
    ctx.setStrokeCaps(BL_STROKE_CAP_ROUND);
    ctx.setStrokeJoin(BL_STROKE_JOIN_ROUND);
    ctx.strokePath(path);
}

inline void drawSunOrb(BLContext& ctx, double cx, double cy, double markerSize,
                       double zoom, const SunStyle& style) {
    const double radius = markerSize * style.coreScale * zoom;
    ctx.setFillStyle(toRgba32(style.coreR, style.coreG, style.coreB));
    ctx.fillCircle(BLCircle(cx, cy, radius));
    ctx.setFillStyle(toRgba32(style.hotR, style.hotG, style.hotB, 0.55));
    ctx.fillCircle(BLCircle(cx, cy, radius * 0.5));
}

inline void drawCheckpointMarker(BLContext& ctx, double cx, double cy,
                                 double radius, double zoom, const CheckpointStyle& style) {
    ctx.setFillStyle(toRgba32(style.coreR, style.coreG, style.coreB, style.alpha));
    ctx.fillCircle(BLCircle(cx, cy, radius * style.coreScale * zoom));
}

} // namespace chronon::svg_parity
