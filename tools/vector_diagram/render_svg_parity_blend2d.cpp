// ChrononTemplate: Native C++ Blend2D Renderer for SVG Parity
// Recreates the Documentary SVG Peak & Neon Essay aesthetic in pure C++20/Blend2D.

#include <blend2d.h>

#include <algorithm>
#include <array>
#include <cmath>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <random>
#include <sstream>
#include <string>
#include <vector>

namespace fs = std::filesystem;

namespace chronon::svg_parity {

constexpr int kW = 1920;
constexpr int kH = 1080;
constexpr int kFps = 30;
constexpr int kTotalFrames = 150; // 5.0 seconds

struct Point {
    double x;
    double y;
};

// Scaling from 854x480 SVG coordinates to 1920x1080
constexpr double kScaleX = static_cast<double>(kW) / 854.0;
constexpr double kScaleY = static_cast<double>(kH) / 480.0;

const std::vector<Point> kPeakPoints = {
    {106.0 * kScaleX, 366.0 * kScaleY},
    {219.0 * kScaleX, 278.0 * kScaleY},
    {262.0 * kScaleX, 245.0 * kScaleY},
    {304.0 * kScaleX, 245.0 * kScaleY},
    {383.0 * kScaleX, 190.0 * kScaleY},
    {458.0 * kScaleX, 118.0 * kScaleY},
    {594.0 * kScaleX, 302.0 * kScaleY},
    {706.0 * kScaleX, 226.0 * kScaleY}
};

inline double easeInOutCubic(double t) {
    return t < 0.5 ? 4.0 * t * t * t : 1.0 - std::pow(-2.0 * t + 2.0, 3) / 2.0;
}

inline double easeOutCubic(double t) {
    return 1.0 - std::pow(1.0 - t, 3);
}

// Multi-pass neon glow line in Blend2D
inline void drawNeonPath(BLContext& ctx, const BLPath& path, BLRgba32 coreColor, double baseWidth) {
    // Octave 4: Wide atmospheric haze
    ctx.setStrokeStyle(BLRgba32(coreColor.r(), coreColor.g(), coreColor.b(), 22));
    ctx.setStrokeWidth(baseWidth * 6.5);
    ctx.setStrokeCaps(BL_STROKE_CAP_ROUND);
    ctx.setStrokeJoin(BL_STROKE_JOIN_ROUND);
    ctx.strokePath(path);

    // Octave 3: Soft outer bloom
    ctx.setStrokeStyle(BLRgba32(coreColor.r(), coreColor.g(), coreColor.b(), 65));
    ctx.setStrokeWidth(baseWidth * 3.5);
    ctx.strokePath(path);

    // Octave 2: Vibrant inner rim
    ctx.setStrokeStyle(BLRgba32(coreColor.r(), coreColor.g(), coreColor.b(), 180));
    ctx.setStrokeWidth(baseWidth * 1.8);
    ctx.strokePath(path);

    // Octave 1: Crisp hot center line
    ctx.setStrokeStyle(BLRgba32(255, 255, 255, 255));
    ctx.setStrokeWidth(baseWidth);
    ctx.strokePath(path);
}

// Multi-pass neon glowing circle / marker
inline void drawNeonCircle(BLContext& ctx, double cx, double cy, double radius, BLRgba32 color) {
    // Wide bloom
    ctx.setFillStyle(BLRgba32(color.r(), color.g(), color.b(), 26));
    ctx.fillCircle(BLCircle(cx, cy, radius * 3.6));

    // Mid glow
    ctx.setFillStyle(BLRgba32(color.r(), color.g(), color.b(), 85));
    ctx.fillCircle(BLCircle(cx, cy, radius * 2.0));

    // Core body
    ctx.setFillStyle(color);
    ctx.fillCircle(BLCircle(cx, cy, radius));

    // Hot specular center
    ctx.setFillStyle(BLRgba32(255, 255, 240, 220));
    ctx.fillCircle(BLCircle(cx, cy, radius * 0.45));
}

// Sample point along polyline at progress [0.0 .. 1.0]
inline Point samplePolyline(const std::vector<Point>& pts, double progress) {
    if (pts.empty()) return {0, 0};
    if (progress <= 0.0) return pts.front();
    if (progress >= 1.0) return pts.back();

    double totalLen = 0.0;
    std::vector<double> segLens;
    segLens.reserve(pts.size() - 1);
    for (std::size_t i = 0; i < pts.size() - 1; ++i) {
        double d = std::hypot(pts[i+1].x - pts[i].x, pts[i+1].y - pts[i].y);
        segLens.push_back(d);
        totalLen += d;
    }

    double target = progress * totalLen;
    for (std::size_t i = 0; i < segLens.size(); ++i) {
        if (target <= segLens[i]) {
            double frac = target / segLens[i];
            return {
                pts[i].x + (pts[i+1].x - pts[i].x) * frac,
                pts[i].y + (pts[i+1].y - pts[i].y) * frac
            };
        }
        target -= segLens[i];
    }
    return pts.back();
}

// Build partial BLPath up to given progress (Trim Path simulation)
inline BLPath buildTrimPath(const std::vector<Point>& pts, double progress) {
    BLPath path;
    if (pts.empty() || progress <= 0.0) return path;

    path.moveTo(pts[0].x, pts[0].y);
    if (progress >= 1.0) {
        for (std::size_t i = 1; i < pts.size(); ++i) {
            path.lineTo(pts[i].x, pts[i].y);
        }
        return path;
    }

    double totalLen = 0.0;
    std::vector<double> segLens;
    segLens.reserve(pts.size() - 1);
    for (std::size_t i = 0; i < pts.size() - 1; ++i) {
        double d = std::hypot(pts[i+1].x - pts[i].x, pts[i+1].y - pts[i].y);
        segLens.push_back(d);
        totalLen += d;
    }

    double rem = progress * totalLen;
    for (std::size_t i = 0; i < segLens.size(); ++i) {
        if (rem >= segLens[i]) {
            path.lineTo(pts[i+1].x, pts[i+1].y);
            rem -= segLens[i];
        } else if (rem > 0.0) {
            double frac = rem / segLens[i];
            path.lineTo(pts[i].x + (pts[i+1].x - pts[i].x) * frac,
                        pts[i].y + (pts[i+1].y - pts[i].y) * frac);
            break;
        } else {
            break;
        }
    }
    return path;
}

} // namespace chronon::svg_parity

int main(int argc, char** argv) {
    using namespace chronon::svg_parity;

    std::cout << "========================================================\n"
              << "ChrononTemplate: Blend2D Native C++ SVG Parity Renderer\n"
              << "Rendering Documentary SVG Peak to PNG Sequence / Video\n"
              << "========================================================\n";

    fs::path outDir = "out/svg_parity/frames";
    if (argc >= 2) {
        outDir = fs::path(argv[1]);
    }
    fs::create_directories(outDir);

    // Dust particles
    struct Dust { double x, y, vx, vy, b; int r; };
    std::vector<Dust> dusts;
    std::mt19937 rng(42);
    std::uniform_real_distribution<double> distX(0, kW), distY(0, kH);
    std::uniform_real_distribution<double> distV(-0.35, 0.35), distB(0.3, 0.85);

    for (int i = 0; i < 90; ++i) {
        dusts.push_back({distX(rng), distY(rng), distV(rng), distV(rng), distB(rng), (i % 3 == 0 ? 2 : 1)});
    }

    BLImage img(kW, kH, BL_FORMAT_PRGB32);
    BLContext ctx(img);

    std::cout << "Rendering " << kTotalFrames << " frames at " << kW << "x" << kH << "...\n";

    for (int f = 0; f < kTotalFrames; ++f) {
        // Clear background
        ctx.setFillStyle(BLRgba32(3, 4, 6, 255));
        ctx.fillRect(BLRect(0, 0, kW, kH));

        // Subtle vignette simulation (gradient)
        BLRadialGradientValues radValues{kW / 2.0, kH / 2.0, kW / 2.0, kH / 2.0, kW * 0.72};
        BLGradient radialVignette(radValues);
        radialVignette.addStop(0.0, BLRgba32(6, 8, 12, 0));
        radialVignette.addStop(1.0, BLRgba32(0, 0, 0, 110));
        ctx.setFillStyle(radialVignette);
        ctx.fillRect(BLRect(0, 0, kW, kH));

        // Floating dust particles
        for (auto& d : dusts) {
            d.x = std::fmod(d.x + d.vx + kW, kW);
            d.y = std::fmod(d.y + d.vy + kH, kH);
            double flicker = 0.5 + 0.5 * std::sin(f * 0.45 + d.b * 10.0);
            if (flicker > 0.3) {
                uint8_t val = static_cast<uint8_t>(255 * d.b * flicker);
                ctx.setFillStyle(BLRgba32(val, val, val, val));
                ctx.fillCircle(BLCircle(d.x, d.y, d.r));
            }
        }

        // Horizontal altitude guide / wind lines
        double drift1 = std::fmod(f * 4.5, kW + 400.0) - 200.0;
        ctx.setStrokeStyle(BLRgba32(180, 200, 230, 45));
        ctx.setStrokeWidth(1.5);
        ctx.strokeLine(BLPoint(drift1, 245.0 * kScaleY), BLPoint(drift1 + 380.0, 245.0 * kScaleY));

        double drift2 = std::fmod(f * 3.2 + 500.0, kW + 400.0) - 200.0;
        ctx.setStrokeStyle(BLRgba32(180, 200, 230, 40));
        ctx.strokeLine(BLPoint(drift2, 118.0 * kScaleY), BLPoint(drift2 + 320.0, 118.0 * kScaleY));

        // Trim Path progress [frames 10 .. 80]
        double trimProgress = 0.0;
        if (f >= 10) {
            double p = std::clamp((f - 10.0) / 70.0, 0.0, 1.0);
            trimProgress = easeOutCubic(p);
        }

        if (trimProgress > 0.0) {
            BLPath path = buildTrimPath(kPeakPoints, trimProgress);
            drawNeonPath(ctx, path, BLRgba32(232, 235, 240, 255), 5.5);
        }

        // Yellow Sun Marker following path [frames 10 .. 90]
        if (f >= 10) {
            double sunProgress = easeOutCubic(std::clamp((f - 10.0) / 80.0, 0.0, 1.0)) * 0.72;
            Point sunPos = samplePolyline(kPeakPoints, sunProgress);
            drawNeonCircle(ctx, sunPos.x, sunPos.y, 22.0 * kScaleX, BLRgba32(255, 220, 30, 255));
        }

        // Rising checkpoint marker (Red) appears around frame 32
        if (f >= 32) {
            double pulse = 1.0 + 0.12 * std::sin(f * 0.35);
            drawNeonCircle(ctx, kPeakPoints[2].x, kPeakPoints[2].y, 14.0 * kScaleX * pulse, BLRgba32(240, 43, 60, 255));
        }

        // Summit peak checkpoint marker (Red) appears when path arrives around frame 65
        if (f >= 65) {
            double pulse = 1.0 + 0.15 * std::sin(f * 0.38 + 1.2);
            drawNeonCircle(ctx, kPeakPoints[5].x, kPeakPoints[5].y, 17.0 * kScaleX * pulse, BLRgba32(240, 43, 60, 255));
        }

        // Save all frames for 30fps animation sequence
        std::ostringstream ss;
        ss << outDir.string() << "/frame_" << std::setfill('0') << std::setw(4) << f << ".png";
        img.writeToFile(ss.str().c_str());
        if (f % 30 == 0 || f == kTotalFrames - 1) {
            std::cout << "  Rendered sample frame: " << ss.str() << '\n';
        }
    }

    ctx.end();
    std::cout << "\n[SUCCESS] Blend2D native SVG parity rendering complete!\n"
              << "Keyframes saved in: " << outDir.string() << '\n';

    return 0;
}
