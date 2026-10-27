// ChrononTemplate: Native C++ Blend2D Animation 1
// Van -> Thermometer -> Sun & Mountain Slope Trim Path

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

namespace chronon::anim1 {

constexpr int kW = 1920;
constexpr int kH = 1080;
constexpr int kFps = 30;
constexpr int kTotalFrames = 180; // 6.0 seconds

struct Point {
    double x;
    double y;
};

// Scaled mountain profile points
const std::vector<Point> kMountainPts = {
    {320.0, 780.0},
    {580.0, 560.0},
    {720.0, 560.0},
    {860.0, 420.0},
    {980.0, 310.0},
    {1240.0, 750.0}
};

inline double easeInOutCubic(double t) {
    return t < 0.5 ? 4.0 * t * t * t : 1.0 - std::pow(-2.0 * t + 2.0, 3) / 2.0;
}

inline double easeOutCubic(double t) {
    return 1.0 - std::pow(1.0 - t, 3);
}

// Draw glowing neon stroke
inline void drawNeonStroke(BLContext& ctx, const BLPath& path, BLRgba32 coreColor, double baseWidth) {
    // Outer bloom
    ctx.setStrokeStyle(BLRgba32(coreColor.r(), coreColor.g(), coreColor.b(), 26));
    ctx.setStrokeWidth(baseWidth * 6.0);
    ctx.setStrokeCaps(BL_STROKE_CAP_ROUND);
    ctx.setStrokeJoin(BL_STROKE_JOIN_ROUND);
    ctx.strokePath(path);

    // Mid rim
    ctx.setStrokeStyle(BLRgba32(coreColor.r(), coreColor.g(), coreColor.b(), 110));
    ctx.setStrokeWidth(baseWidth * 2.8);
    ctx.strokePath(path);

    // Inner bright
    ctx.setStrokeStyle(BLRgba32(coreColor.r(), coreColor.g(), coreColor.b(), 220));
    ctx.setStrokeWidth(baseWidth * 1.5);
    ctx.strokePath(path);

    // Hot specular core
    ctx.setStrokeStyle(BLRgba32(255, 255, 255, 255));
    ctx.setStrokeWidth(baseWidth);
    ctx.strokePath(path);
}

// Draw glowing circle
inline void drawNeonCircle(BLContext& ctx, double cx, double cy, double radius, BLRgba32 color) {
    // Outer bloom
    ctx.setFillStyle(BLRgba32(color.r(), color.g(), color.b(), 28));
    ctx.fillCircle(BLCircle(cx, cy, radius * 3.4));

    // Mid glow
    ctx.setFillStyle(BLRgba32(color.r(), color.g(), color.b(), 95));
    ctx.fillCircle(BLCircle(cx, cy, radius * 2.0));

    // Core body
    ctx.setFillStyle(color);
    ctx.fillCircle(BLCircle(cx, cy, radius));

    // Hot center
    ctx.setFillStyle(BLRgba32(255, 255, 240, 230));
    ctx.fillCircle(BLCircle(cx, cy, radius * 0.42));
}

// Draw Van with inner glow
inline void drawVan(BLContext& ctx, double cx, double cy, double scale, double alpha = 1.0) {
    if (alpha <= 0.01) return;
    ctx.save();
    ctx.translate(cx, cy);
    ctx.scale(scale, scale);

    const double vw = 240.0;
    const double vh = 120.0;
    const double x1 = -vw / 2.0;
    const double y1 = -vh / 2.0;

    // Body translucent fill
    ctx.setFillStyle(BLRgba32(10, 45, 120, static_cast<uint8_t>(180 * alpha)));
    ctx.fillRoundRect(BLRoundRect(x1, y1 + 20, vw, vh - 30, 16));

    // Van glowing outline
    BLPath bodyPath;
    bodyPath.addRoundRect(BLRoundRect(x1, y1 + 20, vw, vh - 30, 16));
    drawNeonStroke(ctx, bodyPath, BLRgba32(30, 170, 255, static_cast<uint8_t>(255 * alpha)), 4.0);

    // White roof cap
    ctx.setFillStyle(BLRgba32(240, 245, 255, static_cast<uint8_t>(230 * alpha)));
    ctx.fillRoundRect(BLRoundRect(x1 + 10, y1, vw - 20, 22, 6));

    // Windows
    const double winY = y1 + 30;
    const double winH = 34;
    for (int i = 0; i < 3; ++i) {
        double wx = x1 + 20 + i * 50;
        ctx.setFillStyle(BLRgba32(5, 15, 40, static_cast<uint8_t>(220 * alpha)));
        ctx.fillRoundRect(BLRoundRect(wx, winY, 40, winH, 4));
        ctx.setStrokeStyle(BLRgba32(100, 200, 255, static_cast<uint8_t>(160 * alpha)));
        ctx.setStrokeWidth(2.0);
        ctx.strokeRoundRect(BLRoundRect(wx, winY, 40, winH, 4));
    }
    // Windshield front
    ctx.setFillStyle(BLRgba32(5, 15, 40, static_cast<uint8_t>(220 * alpha)));
    ctx.fillRoundRect(BLRoundRect(x1 + 175, winY, 45, winH, 6));
    ctx.setStrokeStyle(BLRgba32(100, 200, 255, static_cast<uint8_t>(180 * alpha)));
    ctx.setStrokeWidth(2.0);
    ctx.strokeRoundRect(BLRoundRect(x1 + 175, winY, 45, winH, 6));

    // Wheels
    const double rW = 25.0;
    drawNeonCircle(ctx, x1 + 55, y1 + vh - 10, rW, BLRgba32(80, 140, 200, static_cast<uint8_t>(255 * alpha)));
    drawNeonCircle(ctx, x1 + vw - 60, y1 + vh - 10, rW, BLRgba32(80, 140, 200, static_cast<uint8_t>(255 * alpha)));

    ctx.restore();
}

// Draw Thermometer with rising fluid
inline void drawThermometer(BLContext& ctx, double cx, double cy, double scale, double fluidLevel, double alpha = 1.0) {
    if (alpha <= 0.01) return;
    ctx.save();
    ctx.translate(cx, cy);
    ctx.scale(scale, scale);

    const double bulbR = 34.0;
    const double stemW = 26.0;
    const double stemH = 145.0;
    const double bulbY = 50.0;

    // Glass body path
    BLPath glass;
    glass.addCircle(BLCircle(0, bulbY, bulbR));
    glass.addRoundRect(BLRoundRect(-stemW / 2.0, bulbY - stemH, stemW, stemH, stemW / 2.0));

    // Outer dark translucent glass
    ctx.setFillStyle(BLRgba32(40, 10, 15, static_cast<uint8_t>(150 * alpha)));
    ctx.fillPath(glass);

    // Glowing red rim
    drawNeonStroke(ctx, glass, BLRgba32(245, 40, 60, static_cast<uint8_t>(255 * alpha)), 4.0);

    // Inner yellow mercury / rising fluid
    double curH = stemH * std::clamp(fluidLevel, 0.0, 1.0);
    drawNeonCircle(ctx, 0, bulbY, bulbR * 0.72, BLRgba32(255, 230, 40, static_cast<uint8_t>(255 * alpha)));

    if (curH > 5.0) {
        ctx.setFillStyle(BLRgba32(255, 230, 40, static_cast<uint8_t>(230 * alpha)));
        ctx.fillRoundRect(BLRoundRect(-stemW * 0.3, bulbY - curH, stemW * 0.6, curH, stemW * 0.3));
        drawNeonCircle(ctx, 0, bulbY - curH, stemW * 0.32, BLRgba32(255, 240, 70, static_cast<uint8_t>(255 * alpha)));
    }

    ctx.restore();
}

// Build partial Trim Path
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

} // namespace chronon::anim1

int main(int argc, char** argv) {
    using namespace chronon::anim1;

    std::cout << "========================================================\n"
              << "ChrononTemplate: Animation 1 (Van -> Thermo -> Mountain)\n"
              << "========================================================\n";

    fs::path outDir = "out/svg_parity/anim1_frames";
    if (argc >= 2) {
        outDir = fs::path(argv[1]);
    }
    fs::create_directories(outDir);

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

    std::cout << "Rendering " << kTotalFrames << " frames at 1920x1080...\n";

    for (int f = 0; f < kTotalFrames; ++f) {
        // Deep black background
        ctx.setFillStyle(BLRgba32(3, 4, 6, 255));
        ctx.fillRect(BLRect(0, 0, kW, kH));

        // Soft optical vignette
        BLRadialGradientValues radValues{kW / 2.0, kH / 2.0, kW / 2.0, kH / 2.0, kW * 0.72};
        BLGradient radialVignette(radValues);
        radialVignette.addStop(0.0, BLRgba32(6, 8, 12, 0));
        radialVignette.addStop(1.0, BLRgba32(0, 0, 0, 115));
        ctx.setFillStyle(radialVignette);
        ctx.fillRect(BLRect(0, 0, kW, kH));

        // Analog floating dust
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

        // --- STAGE 1: Van Driving (Frames 0..45) ---
        if (f < 45) {
            double p = std::clamp(f / 35.0, 0.0, 1.0);
            double e = easeOutCubic(p);
            double vanX = -200.0 + e * (kW / 2.0 + 200.0);
            double bounce = (f < 35) ? std::sin(f * 0.45) * 3.5 : 0.0;
            double vanY = 560.0 + bounce;

            // Road line
            ctx.setStrokeStyle(BLRgba32(120, 160, 220, 75));
            ctx.setStrokeWidth(2.0);
            ctx.strokeLine(BLPoint(100, 622), BLPoint(kW - 100, 622));

            drawVan(ctx, vanX, vanY, 1.35, 1.0);
        }
        // --- STAGE 2: Morph Van -> Thermometer (Frames 45..85) ---
        else if (f < 85) {
            double p = (f - 45.0) / 40.0;
            double e = easeInOutCubic(p);
            double cx = kW / 2.0;
            double cy = 560.0 - e * 50.0;

            if (p < 0.4) {
                double vanShrink = 1.35 * (1.0 - p * 2.0);
                drawVan(ctx, cx, cy, std::max(vanShrink, 0.1), 1.0 - p * 2.2);
            }

            double thermoAlpha = std::clamp((p - 0.2) / 0.4, 0.0, 1.0);
            double fluidLevel = easeOutCubic(std::clamp((p - 0.3) / 0.7, 0.0, 1.0));
            drawThermometer(ctx, cx, cy, 1.4, fluidLevel, thermoAlpha);
        }
        // --- STAGE 3: Thermometer morphs to Sun & Slope (Frames 85..120) ---
        else if (f < 120) {
            double p = (f - 85.0) / 35.0;
            double e = easeInOutCubic(p);

            // Sun detaches from bulb and moves to slope
            Point startSun{kW / 2.0, 560.0 - 50.0 + 50.0 * 1.4};
            Point targetSun{520.0, 615.0};
            double sx = startSun.x + (targetSun.x - startSun.x) * e;
            double sy = startSun.y + (targetSun.y - startSun.y) * e;
            double sR = 32.0 + e * 14.0;
            drawNeonCircle(ctx, sx, sy, sR, BLRgba32(255, 220, 30, 255));

            // Stem tilts and expands to first slope segment
            Point stemA{kW / 2.0, 560.0 - 50.0 + 30.0};
            Point stemB{kW / 2.0, 560.0 - 50.0 - 145.0 * 1.4};
            Point curA{stemA.x + (kMountainPts[0].x - stemA.x) * e, stemA.y + (kMountainPts[0].y - stemA.y) * e};
            Point curB{stemB.x + (kMountainPts[1].x - stemB.x) * e, stemB.y + (kMountainPts[1].y - stemB.y) * e};

            BLPath slopeLine;
            slopeLine.moveTo(curA.x, curA.y);
            slopeLine.lineTo(curB.x, curB.y);
            drawNeonStroke(ctx, slopeLine, BLRgba32(235, 240, 248, 255), 5.5);
        }
        // --- STAGE 4: Full Mountain Trim Path & Checkpoints (Frames 120..180) ---
        else {
            double p = (f - 120.0) / 55.0;
            double trimProgress = easeOutCubic(std::clamp(p, 0.0, 1.0));

            // Draw Mountain line
            BLPath mPath = buildTrimPath(kMountainPts, trimProgress);
            drawNeonStroke(ctx, mPath, BLRgba32(235, 240, 248, 255), 5.5);

            // Sun rests on slope
            drawNeonCircle(ctx, 520.0, 615.0, 46.0, BLRgba32(255, 220, 30, 255));

            // Red checkpoint marker 1 on slope
            double pulse1 = 1.0 + 0.12 * std::sin(f * 0.35);
            drawNeonCircle(ctx, 580.0, 560.0, 18.0 * pulse1, BLRgba32(240, 40, 60, 255));

            // Red checkpoint marker 2 on summit peak
            if (p > 0.6) {
                double pulse2 = 1.0 + 0.15 * std::sin(f * 0.38 + 1.0);
                drawNeonCircle(ctx, 980.0, 310.0, 24.0 * pulse2, BLRgba32(240, 40, 60, 255));
            }

            // Drifting altitude guide lines
            double drift = std::fmod(f * 4.0, kW + 400.0) - 200.0;
            ctx.setStrokeStyle(BLRgba32(180, 200, 230, 40));
            ctx.setStrokeWidth(1.5);
            ctx.strokeLine(BLPoint(drift, 560), BLPoint(drift + 350, 560));
            ctx.strokeLine(BLPoint(drift + 400, 310), BLPoint(drift + 720, 310));
        }

        // Save frame
        std::ostringstream ss;
        ss << outDir.string() << "/frame_" << std::setfill('0') << std::setw(4) << f << ".png";
        img.writeToFile(ss.str().c_str());

        if (f % 45 == 0 || f == kTotalFrames - 1) {
            std::cout << "  Rendered frame " << f << "/" << kTotalFrames << '\n';
        }
    }

    ctx.end();
    std::cout << "[SUCCESS] Animation 1 rendered successfully to: " << outDir.string() << '\n';
    return 0;
}
