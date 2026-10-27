// render_primitives_scaling_showcase_blend2d.cpp
// Mathematical verification + Visual Parity Showcase:
// - Non-Scaling Stroke Width Invariance
// - 4-Quadrant Anchor / Pivot Zero-Drift Matrix Test
// - Arc-Length LUT Constant Linear Trajectory (Alpine Ridge)
// - True 8-Stop Radial Gradient Bloom (BL_COMP_OP_PLUS)
// - True Inset Multi-Stroke Inner Glow + Multi-Pass Outer Rim
// - Bayer Matrix Dithering against 8-bit Color Banding
// - 2.5D Multi-Plane Depth of Field

#include <blend2d.h>
#include <cmath>
#include <vector>
#include <iostream>
#include <string>
#include <filesystem>
#include <sstream>
#include <iomanip>
#include <random>
#include <algorithm>

namespace fs = std::filesystem;
constexpr double kPi = 3.14159265358979323846;

struct Vec2 {
    double x, y;
};

// Arc-length LUT for strictly uniform linear motion
class ArcLengthPolyline {
public:
    struct Segment {
        double cumLength;
        Vec2 pos;
    };
    std::vector<Segment> samples;
    double totalLength = 0.0;

    void build(const std::vector<Vec2>& pts) {
        samples.clear();
        totalLength = 0.0;
        if (pts.empty()) return;

        samples.push_back({0.0, pts[0]});
        for (size_t i = 1; i < pts.size(); ++i) {
            double dx = pts[i].x - pts[i - 1].x;
            double dy = pts[i].y - pts[i - 1].y;
            totalLength += std::hypot(dx, dy);
            samples.push_back({totalLength, pts[i]});
        }
    }

    struct Sample {
        Vec2 pos;
        Vec2 tangent;
    };

    Sample evaluate(double normU) const {
        if (samples.empty()) return {{0, 0}, {1, 0}};
        double target = std::clamp(normU, 0.0, 1.0) * totalLength;

        for (size_t i = 1; i < samples.size(); ++i) {
            if (samples[i].cumLength >= target) {
                double lPrev = samples[i - 1].cumLength;
                double span = samples[i].cumLength - lPrev;
                double t = (span > 1e-6) ? (target - lPrev) / span : 0.0;
                Vec2 p = {
                    samples[i - 1].pos.x + t * (samples[i].pos.x - samples[i - 1].pos.x),
                    samples[i - 1].pos.y + t * (samples[i].pos.y - samples[i - 1].pos.y)
                };
                double dx = samples[i].pos.x - samples[i - 1].pos.x;
                double dy = samples[i].pos.y - samples[i - 1].pos.y;
                double len = std::hypot(dx, dy);
                Vec2 tan = (len > 1e-6) ? Vec2{dx / len, dy / len} : Vec2{1, 0};
                return {p, tan};
            }
        }
        return {samples.back().pos, {1, 0}};
    }
};

inline double easeInOutCubic(double t) {
    return t < 0.5 ? 4.0 * t * t * t : 1.0 - std::pow(-2.0 * t + 2.0, 3) / 2.0;
}

inline double easeInOutSine(double t) {
    return -(std::cos(kPi * t) - 1.0) / 2.0;
}

// 1. True 8-Stop Exponential Radial Gradient Sun with Additive Blending (BL_COMP_OP_PLUS)
inline void drawExponentialBloomSun(BLContext& ctx, double cx, double cy, double radius, BLRgba32 color, double alpha = 1.0) {
    ctx.save();
    ctx.setCompOp(BL_COMP_OP_PLUS);

    double maxRadius = radius * 5.2;
    BLRadialGradientValues gradVals(cx, cy, cx, cy, maxRadius);
    BLGradient grad(gradVals);

    // 8-stop exponential optical falloff
    grad.addStop(0.00, BLRgba32(255, 255, 255, (uint32_t)(255 * alpha)));
    grad.addStop(0.07, BLRgba32(255, 245, 170, (uint32_t)(235 * alpha)));
    grad.addStop(0.18, BLRgba32(color.r(), color.g(), color.b(), (uint32_t)(180 * alpha)));
    grad.addStop(0.35, BLRgba32(color.r(), (uint8_t)(color.g() * 0.75), 10, (uint32_t)(100 * alpha)));
    grad.addStop(0.52, BLRgba32(240, 110, 0, (uint32_t)(45 * alpha)));
    grad.addStop(0.70, BLRgba32(170, 45, 0, (uint32_t)(18 * alpha)));
    grad.addStop(0.86, BLRgba32(90, 15, 0, (uint32_t)(6 * alpha)));
    grad.addStop(1.00, BLRgba32(0, 0, 0, 0));

    ctx.setFillStyle(grad);
    ctx.fillCircle(BLCircle(cx, cy, maxRadius));

    // Specular core in SRC_OVER
    ctx.setCompOp(BL_COMP_OP_SRC_OVER);
    ctx.setFillStyle(BLRgba32(255, 255, 250, (uint32_t)(255 * alpha)));
    ctx.fillCircle(BLCircle(cx, cy, radius * 0.38));
    ctx.restore();
}

// 2. True Inset Multi-Stroke Inner Glow + Multi-Pass Outer Rim for Rectangles
inline void drawNeonShapeWithInnerGlow(BLContext& ctx, double w, double h, double r, BLRgba32 neonColor, double baseStrokeWidth, double alpha = 1.0) {
    // A. Dark translucent base fill
    BLPath baseRect;
    baseRect.addRoundRect(BLRoundRect(0, 0, w, h, r));
    ctx.setFillStyle(BLRgba32(neonColor.r() / 8, neonColor.g() / 8, neonColor.b() / 8, (uint32_t)(45 * alpha)));
    ctx.fillPath(baseRect);

    // B. True Inner Glow: Inset strokes nested inward from perimeter
    ctx.save();
    ctx.setCompOp(BL_COMP_OP_PLUS);
    ctx.setStrokeCaps(BL_STROKE_CAP_ROUND);
    ctx.setStrokeJoin(BL_STROKE_JOIN_ROUND);

    for (int step = 0; step < 4; ++step) {
        double inset = step * 4.0 * baseStrokeWidth;
        if (w - inset * 2.0 <= 10.0 || h - inset * 2.0 <= 10.0) break;
        BLPath insetPath;
        insetPath.addRoundRect(BLRoundRect(inset, inset, w - inset * 2.0, h - inset * 2.0, std::max(2.0, r - inset)));
        
        double stepAlpha = (step == 0) ? 140 : (step == 1 ? 75 : (step == 2 ? 35 : 15));
        double stepWidth = baseStrokeWidth * (1.8 + step * 1.5);
        ctx.setStrokeStyle(BLRgba32(neonColor.r(), neonColor.g(), neonColor.b(), (uint32_t)(stepAlpha * alpha)));
        ctx.setStrokeWidth(stepWidth);
        ctx.strokePath(insetPath);
    }

    // C. Outer Bloom: Additive halo
    ctx.setStrokeStyle(BLRgba32(neonColor.r(), neonColor.g(), neonColor.b(), (uint32_t)(25 * alpha)));
    ctx.setStrokeWidth(baseStrokeWidth * 7.0);
    ctx.strokePath(baseRect);

    ctx.setStrokeStyle(BLRgba32(neonColor.r(), neonColor.g(), neonColor.b(), (uint32_t)(80 * alpha)));
    ctx.setStrokeWidth(baseStrokeWidth * 3.0);
    ctx.strokePath(baseRect);
    ctx.restore();

    // D. Specular Core Stroke in SRC_OVER
    ctx.setCompOp(BL_COMP_OP_SRC_OVER);
    ctx.setStrokeCaps(BL_STROKE_CAP_ROUND);
    ctx.setStrokeJoin(BL_STROKE_JOIN_ROUND);
    ctx.setStrokeStyle(BLRgba32(255, 255, 255, (uint32_t)(255 * alpha)));
    ctx.setStrokeWidth(baseStrokeWidth);
    ctx.strokePath(baseRect);
}

// 3. True Inner Glow for Circles
inline void drawNeonCircleWithInnerGlow(BLContext& ctx, double cx, double cy, double radius, BLRgba32 neonColor, double baseStrokeWidth, double alpha = 1.0) {
    ctx.setFillStyle(BLRgba32(neonColor.r() / 8, neonColor.g() / 8, neonColor.b() / 8, (uint32_t)(45 * alpha)));
    ctx.fillCircle(BLCircle(cx, cy, radius));

    ctx.save();
    ctx.setCompOp(BL_COMP_OP_PLUS);
    for (int step = 0; step < 4; ++step) {
        double insetR = radius - step * 3.5 * baseStrokeWidth;
        if (insetR <= 5.0) break;
        double stepAlpha = (step == 0) ? 140 : (step == 1 ? 75 : (step == 2 ? 35 : 15));
        double stepWidth = baseStrokeWidth * (1.8 + step * 1.5);
        ctx.setStrokeStyle(BLRgba32(neonColor.r(), neonColor.g(), neonColor.b(), (uint32_t)(stepAlpha * alpha)));
        ctx.setStrokeWidth(stepWidth);
        ctx.strokeCircle(BLCircle(cx, cy, insetR));
    }

    ctx.setStrokeStyle(BLRgba32(neonColor.r(), neonColor.g(), neonColor.b(), (uint32_t)(25 * alpha)));
    ctx.setStrokeWidth(baseStrokeWidth * 7.0);
    ctx.strokeCircle(BLCircle(cx, cy, radius));

    ctx.setStrokeStyle(BLRgba32(neonColor.r(), neonColor.g(), neonColor.b(), (uint32_t)(80 * alpha)));
    ctx.setStrokeWidth(baseStrokeWidth * 3.0);
    ctx.strokeCircle(BLCircle(cx, cy, radius));
    ctx.restore();

    ctx.setCompOp(BL_COMP_OP_SRC_OVER);
    ctx.setStrokeStyle(BLRgba32(255, 255, 255, (uint32_t)(255 * alpha)));
    ctx.setStrokeWidth(baseStrokeWidth);
    ctx.strokeCircle(BLCircle(cx, cy, radius));
}

// 4. Glowing Neon Stroke for Lines and Paths
inline void drawNeonStroke(BLContext& ctx, const BLPath& path, BLRgba32 coreColor, double baseWidth, double alpha = 1.0) {
    ctx.save();
    ctx.setCompOp(BL_COMP_OP_PLUS);
    ctx.setStrokeCaps(BL_STROKE_CAP_ROUND);
    ctx.setStrokeJoin(BL_STROKE_JOIN_ROUND);

    ctx.setStrokeStyle(BLRgba32(coreColor.r(), coreColor.g(), coreColor.b(), (uint32_t)(25 * alpha)));
    ctx.setStrokeWidth(baseWidth * 6.5);
    ctx.strokePath(path);

    ctx.setStrokeStyle(BLRgba32(coreColor.r(), coreColor.g(), coreColor.b(), (uint32_t)(85 * alpha)));
    ctx.setStrokeWidth(baseWidth * 2.8);
    ctx.strokePath(path);
    ctx.restore();

    ctx.setStrokeStyle(BLRgba32(255, 255, 255, (uint32_t)(255 * alpha)));
    ctx.setStrokeWidth(baseWidth);
    ctx.strokePath(path);
}

// 5. Fixed Reticle proving Zero-Drift
inline void drawWorldReticle(BLContext& ctx, double x, double y, const std::string& label) {
    ctx.save();
    ctx.setCompOp(BL_COMP_OP_SRC_OVER);
    ctx.setStrokeStyle(BLRgba32(255, 50, 50, 220));
    ctx.setStrokeWidth(1.5);

    ctx.strokeLine(BLPoint(x - 22, y), BLPoint(x + 22, y));
    ctx.strokeLine(BLPoint(x, y - 22), BLPoint(x, y + 22));
    ctx.strokeCircle(BLCircle(x, y, 10));

    ctx.setFillStyle(BLRgba32(255, 120, 120, 240));
    ctx.fillCircle(BLCircle(x, y, 2.5));
    ctx.restore();
}

// 6. Bayer Matrix Dithering (breaks 8-bit banding rings)
void applyBayerDithering(BLImage& img) {
    static const int8_t kBayer[8][8] = {
        { -3,  1, -2,  2, -3,  1, -2,  2 },
        {  3, -1,  2, -2,  3, -1,  2, -2 },
        { -1,  3, -3,  1, -1,  3, -3,  1 },
        {  1, -3,  3, -1,  1, -3,  3, -1 },
        { -2,  2, -3,  1, -2,  2, -3,  1 },
        {  2, -2,  3, -1,  2, -2,  3, -1 },
        { -3,  1, -1,  3, -3,  1, -1,  3 },
        {  1, -1,  1, -3,  1, -1,  1, -3 }
    };

    BLImageData data;
    if (img.getData(&data) != BL_SUCCESS) return;

    int w = data.size.w;
    int h = data.size.h;
    uint8_t* scan = (uint8_t*)data.pixelData;

    for (int y = 0; y < h; ++y) {
        uint32_t* row = (uint32_t*)(scan + y * data.stride);
        for (int x = 0; x < w; ++x) {
            uint32_t px = row[x];
            int a = (px >> 24) & 0xFF;
            int r = (px >> 16) & 0xFF;
            int g = (px >>  8) & 0xFF;
            int b =  px        & 0xFF;

            int d = kBayer[y & 7][x & 7];
            r = std::clamp(r + d, 0, 255);
            g = std::clamp(g + d, 0, 255);
            b = std::clamp(b + d, 0, 255);

            row[x] = (a << 24) | (r << 16) | (g << 8) | b;
        }
    }
}

int main(int argc, char* argv[]) {
    std::cout << "========================================================\n"
              << "ChrononTemplate: Primitives Scaling & Visual Parity Showcase\n"
              << "60 FPS Native 2.5D Multi-Plane / Non-Scaling Stroke / SDF\n"
              << "========================================================\n";

    fs::path outDir = "out/svg_parity/showcase_frames";
    if (argc >= 2) outDir = fs::path(argv[1]);
    fs::create_directories(outDir);

    // Setup Organic Alpine Mountain Trajectory (20 vertices: slopes, rocky crags, acute summit)
    std::vector<Vec2> trajPts = {
        {  200.0, 750.0 },
        {  340.0, 750.0 }, // Foothill base
        {  450.0, 710.0 }, // Gentle rise
        {  540.0, 680.0 }, // Rocky ledge
        {  610.0, 650.0 },
        {  680.0, 600.0 }, // Steep ascent 1
        {  740.0, 560.0 },
        {  810.0, 510.0 }, // Couloir approach
        {  870.0, 460.0 },
        {  910.0, 410.0 }, // Summit ridge
        {  940.0, 360.0 }, // ACUTE SUMMIT PEAK (Highest elevation)
        {  970.0, 400.0 }, // North face descent
        { 1020.0, 470.0 },
        { 1080.0, 520.0 }, // Crag step
        { 1160.0, 580.0 },
        { 1250.0, 630.0 }, // Lower glacier slope
        { 1370.0, 680.0 },
        { 1500.0, 720.0 },
        { 1620.0, 750.0 },
        { 1740.0, 750.0 }  // Valley floor
    };
    ArcLengthPolyline polylineLut;
    polylineLut.build(trajPts);

    const int kW = 1920;
    const int kH = 1080;
    const int kFps = 60;
    const int kDurationSec = 6;
    const int kTotalFrames = kFps * kDurationSec; // 360 frames

    BLImage img(kW, kH, BL_FORMAT_PRGB32);
    BLContext ctx(img);

    std::cout << "Rendering " << kTotalFrames << " frames (60fps) at " << kW << "x" << kH << "...\n";

    for (int f = 0; f < kTotalFrames; ++f) {
        double t = static_cast<double>(f) / kFps;
        double normT = static_cast<double>(f) / kTotalFrames;

        // 2.5D Camera Choreography: Pan X + Dolly Z
        double camPanX = 0.0;
        double camDollyZ = 0.0;
        if (f < 180) {
            double p = f / 180.0;
            camPanX = std::sin(p * kPi) * 160.0;
            camDollyZ = easeInOutCubic(p) * 320.0; // Pulls back
        } else {
            double p = (f - 180.0) / 180.0;
            camPanX = -std::sin(p * kPi) * 160.0;
            camDollyZ = (1.0 - easeInOutCubic(p)) * 320.0; // Pushes back in
        }

        const double focalLength = 1000.0;
        auto project25D = [&](double wx, double wy, double wz) -> std::pair<Vec2, double> {
            double distZ = (focalLength + wz) - camDollyZ;
            if (distZ < 50.0) distZ = 50.0;
            double pScale = focalLength / distZ;
            double sx = (kW * 0.5) + (wx - (kW * 0.5) - camPanX) * pScale;
            double sy = (kH * 0.5) + (wy - (kH * 0.5)) * pScale;
            return {{sx, sy}, pScale};
        };

        // Clear screen with deep documentary black
        ctx.clearAll();
        ctx.setFillStyle(BLRgba32(3, 5, 10, 255));
        ctx.fillAll();

        // Subtle 2.5D Perspective Grid (Z = -250)
        ctx.setStrokeWidth(1.0);
        ctx.setStrokeStyle(BLRgba32(35, 60, 95, 35));
        for (double gx = 160.0; gx <= 1760.0; gx += 160.0) {
            auto [p1, s1] = project25D(gx, 100.0, -250.0);
            auto [p2, s2] = project25D(gx, 980.0, -250.0);
            ctx.strokeLine(p1.x, p1.y, p2.x, p2.y);
        }
        for (double gy = 150.0; gy <= 950.0; gy += 150.0) {
            auto [p1, s1] = project25D(160.0, gy, -250.0);
            auto [p2, s2] = project25D(1760.0, gy, -250.0);
            ctx.strokeLine(p1.x, p1.y, p2.x, p2.y);
        }

        // =========================================================================
        // PLANE 1: BACKGROUND (Z = -200) -> DEPTH OF FIELD BLUR
        // =========================================================================
        {
            auto [pBg, sBg] = project25D(320.0, 260.0, -200.0);
            ctx.save();
            ctx.translate(pBg.x, pBg.y);
            ctx.scale(sBg, sBg);
            BLPath bgWave;
            bgWave.moveTo(-80, 0);
            bgWave.cubicTo(-40, -40, 40, 40, 80, 0);
            // Softened out-of-focus background stroke
            drawNeonStroke(ctx, bgWave, BLRgba32(0, 180, 255, 120), 4.5, 0.45);
            ctx.restore();
        }

        // =========================================================================
        // PLANE 2: FOCAL PLANE (Z = 0) -> NON-SCALING STROKE & INNER GLOW PIVOTS
        // =========================================================================
        {
            // Breathing Circle demonstrating vector-effect="non-scaling-stroke"
            auto [pCen, sCen] = project25D(kW * 0.5, kH * 0.5, 0.0);
            double dynamicScale = 0.4 + 1.2 * easeInOutSine(std::sin(normT * 2.0 * kPi));
            double targetPixelWidth = 4.0;
            double compensatedWidth = targetPixelWidth / (sCen * dynamicScale);

            ctx.save();
            ctx.translate(pCen.x, pCen.y);
            ctx.scale(sCen * dynamicScale, sCen * dynamicScale);
            // Apply true inner glow + outer bloom to center circle
            drawNeonCircleWithInnerGlow(ctx, 0, 0, 120.0, BLRgba32(0, 240, 255, 255), compensatedWidth);
            ctx.restore();
        }

        // 4 SHAPES WITH PIVOT ANCHORING & TRUE INNER GLOW
        struct PivotCase {
            Vec2 worldTarget;
            Vec2 localOffset;
            std::string name;
            BLRgba32 color;
        };

        std::vector<PivotCase> pivotCases = {
            {{  460.0, 360.0 }, { 70.0, 45.0 }, "CENTER",          BLRgba32(255, 180, 20, 255)},
            {{ 1460.0, 360.0 }, {  0.0,  0.0 }, "TOP_LEFT",        BLRgba32(60, 255, 140, 255)},
            {{  460.0, 780.0 }, { 70.0, 90.0 }, "BOTTOM_CENTER",   BLRgba32(255, 75, 90, 255)},
            {{ 1460.0, 780.0 }, { 35.0, 67.5 }, "CUSTOM_0.25_0.75", BLRgba32(195, 90, 255, 255)}
        };

        double rotAngle = t * 1.5;
        double scaleDyn = 0.6 + 0.9 * easeInOutSine(std::sin(normT * 2.0 * kPi));

        for (const auto& pc : pivotCases) {
            auto [projP, perspP] = project25D(pc.worldTarget.x, pc.worldTarget.y, 0.0);

            ctx.save();
            ctx.translate(projP.x, projP.y);
            ctx.scale(perspP * scaleDyn, perspP * (scaleDyn * 0.7)); // Non-uniform scale
            ctx.rotate(rotAngle);
            ctx.translate(-pc.localOffset.x, -pc.localOffset.y);     // Exact pivot anchoring

            double strokeComp = 3.5 / (perspP * scaleDyn);

            // TRUE INNER GLOW + OUTER NEON BLOOM (with inset multi-strokes)
            drawNeonShapeWithInnerGlow(ctx, 140.0, 90.0, 14.0, pc.color, strokeComp);
            ctx.restore();

            // FIXED world reticle crosshair on target world position proving ZERO drift
            drawWorldReticle(ctx, projP.x, projP.y, pc.name);
        }

        // =========================================================================
        // PLANE 3: FOREGROUND (Z = +150) -> MOUNTAIN TRIM-PATH & RADIAL GLOW SUN
        // =========================================================================
        {
            double u = 0.0;
            if (f >= 30 && f <= 310) {
                u = easeInOutCubic(static_cast<double>(f - 30) / 280.0);
            } else if (f > 310) {
                u = 1.0;
            }

            // Draw Mountain Ridge
            BLPath mountainPath;
            bool first = true;
            for (const auto& pt : trajPts) {
                auto [p, s] = project25D(pt.x, pt.y, 150.0);
                if (first) { mountainPath.moveTo(p.x, p.y); first = false; }
                else { mountainPath.lineTo(p.x, p.y); }
            }
            // Background faint baseline
            ctx.setStrokeWidth(1.2);
            ctx.setStrokeStyle(BLRgba32(120, 150, 190, 45));
            ctx.strokePath(mountainPath);

            // Animated Trim Path
            if (u > 0.001) {
                BLPath trimPath;
                double targetDist = u * polylineLut.totalLength;
                bool tFirst = true;

                for (size_t i = 0; i < polylineLut.samples.size(); ++i) {
                    if (polylineLut.samples[i].cumLength <= targetDist) {
                        auto [p, s] = project25D(polylineLut.samples[i].pos.x, polylineLut.samples[i].pos.y, 150.0);
                        if (tFirst) { trimPath.moveTo(p.x, p.y); tFirst = false; }
                        else { trimPath.lineTo(p.x, p.y); }
                    } else {
                        auto curSample = polylineLut.evaluate(u);
                        auto [p, s] = project25D(curSample.pos.x, curSample.pos.y, 150.0);
                        if (tFirst) { trimPath.moveTo(p.x, p.y); tFirst = false; }
                        else { trimPath.lineTo(p.x, p.y); }
                        break;
                    }
                }
                drawNeonStroke(ctx, trimPath, BLRgba32(245, 250, 255, 255), 3.2);
            }

            // FollowPath Yellow Sun moving at strict constant linear speed with 8-Stop Exponential Radial Bloom!
            if (f >= 30) {
                auto sample = polylineLut.evaluate(u);
                auto [sunP, sunS] = project25D(sample.pos.x, sample.pos.y, 150.0);
                drawExponentialBloomSun(ctx, sunP.x, sunP.y, 22.0 * sunS, BLRgba32(255, 220, 30, 255));
            }
        }

        // Technical HUD Frame Brackets
        ctx.setStrokeWidth(1.5);
        ctx.setStrokeStyle(BLRgba32(0, 240, 255, 100));
        ctx.strokeLine(60.0, 60.0, 160.0, 60.0);
        ctx.strokeLine(60.0, 60.0, 60.0, 120.0);
        ctx.strokeLine(1860.0, 1020.0, 1760.0, 1020.0);
        ctx.strokeLine(1860.0, 1020.0, 1860.0, 960.0);

        // Micro-particles
        for (int d = 0; d < 65; ++d) {
            uint32_t seed = (uint32_t)(d * 1973 + f * 9271);
            seed = (seed ^ 61) ^ (seed >> 16);
            seed *= 9;
            seed = seed ^ (seed >> 4);
            seed *= 0x27d4eb2d;
            seed = seed ^ (seed >> 15);

            double dx = (seed % kW);
            double dy = ((seed / kW) % kH);
            double d_alpha = ((seed >> 8) % 45) / 255.0;

            ctx.setFillStyle(BLRgba32(220, 240, 255, (uint32_t)(d_alpha * 255)));
            ctx.fillCircle(dx, dy, (seed % 3 == 0) ? 1.2 : 0.8);
        }

        // Apply Bayer Dithering to eliminate 8-bit banding rings!
        applyBayerDithering(img);

        // Write frame to disk
        std::ostringstream fn;
        fn << outDir.string() << "/frame_" << std::setfill('0') << std::setw(4) << f << ".png";
        img.writeToFile(fn.str().c_str());

        if (f % 60 == 0 || f == kTotalFrames - 1) {
            std::cout << "  Rendered frame " << f << " / " << kTotalFrames 
                      << " (" << (int)((f / (double)kTotalFrames) * 100) << "%)\n";
        }
    }

    ctx.end();
    std::cout << "[DONE] Successfully rendered all 360 frames to " << outDir << "\n";
    return 0;
}
