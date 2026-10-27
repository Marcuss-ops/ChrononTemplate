// ChrononTemplate: Native C++ Blend2D Animation 2
// 2.5D Neon Essay Scene: Thinking Figure -> Scientist -> Foreground Laughing Giants Dolly Out with DoF

#include <blend2d.h>

#include <algorithm>
#include <array>
#define _USE_MATH_DEFINES
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

namespace chronon::anim2 {

constexpr double kPi = 3.14159265358979323846;
constexpr int kW = 1920;
constexpr int kH = 1080;
constexpr int kFps = 30;
constexpr int kTotalFrames = 210; // 7.0 seconds

inline double easeInOutCubic(double t) {
    return t < 0.5 ? 4.0 * t * t * t : 1.0 - std::pow(-2.0 * t + 2.0, 3) / 2.0;
}

inline double easeOutCubic(double t) {
    return 1.0 - std::pow(1.0 - t, 3);
}

// Multi-pass glowing stroke
inline void drawNeonStroke(BLContext& ctx, const BLPath& path, BLRgba32 coreColor, double baseWidth, double alpha = 1.0) {
    uint8_t a = static_cast<uint8_t>(255 * std::clamp(alpha, 0.0, 1.0));
    // Outer bloom
    ctx.setStrokeStyle(BLRgba32(coreColor.r(), coreColor.g(), coreColor.b(), static_cast<uint8_t>(25 * alpha)));
    ctx.setStrokeWidth(baseWidth * 6.5);
    ctx.setStrokeCaps(BL_STROKE_CAP_ROUND);
    ctx.setStrokeJoin(BL_STROKE_JOIN_ROUND);
    ctx.strokePath(path);

    // Mid rim
    ctx.setStrokeStyle(BLRgba32(coreColor.r(), coreColor.g(), coreColor.b(), static_cast<uint8_t>(110 * alpha)));
    ctx.setStrokeWidth(baseWidth * 3.0);
    ctx.strokePath(path);

    // Inner rim
    ctx.setStrokeStyle(BLRgba32(coreColor.r(), coreColor.g(), coreColor.b(), static_cast<uint8_t>(210 * alpha)));
    ctx.setStrokeWidth(baseWidth * 1.5);
    ctx.strokePath(path);

    // Hot specular core
    ctx.setStrokeStyle(BLRgba32(255, 255, 255, a));
    ctx.setStrokeWidth(baseWidth);
    ctx.strokePath(path);
}

// Multi-pass glowing circle
inline void drawNeonCircle(BLContext& ctx, double cx, double cy, double radius, BLRgba32 color, double alpha = 1.0) {
    uint8_t a = static_cast<uint8_t>(255 * std::clamp(alpha, 0.0, 1.0));
    ctx.setFillStyle(BLRgba32(color.r(), color.g(), color.b(), static_cast<uint8_t>(26 * alpha)));
    ctx.fillCircle(BLCircle(cx, cy, radius * 3.2));

    ctx.setFillStyle(BLRgba32(color.r(), color.g(), color.b(), static_cast<uint8_t>(90 * alpha)));
    ctx.fillCircle(BLCircle(cx, cy, radius * 1.8));

    ctx.setFillStyle(BLRgba32(color.r(), color.g(), color.b(), a));
    ctx.fillCircle(BLCircle(cx, cy, radius));

    ctx.setFillStyle(BLRgba32(255, 255, 245, static_cast<uint8_t>(220 * alpha)));
    ctx.fillCircle(BLCircle(cx, cy, radius * 0.4));
}

// Draw Standing Stick Figure with neon inner glow aesthetic
inline void drawFigure(BLContext& ctx, double cx, double cy, double scale, BLRgba32 rimColor, BLRgba32 fillColor, int pose = 0, double alpha = 1.0) {
    ctx.save();
    ctx.translate(cx, cy);
    ctx.scale(scale, scale);

    const double headR = 48.0;
    const double headY = -220.0;

    // Head
    ctx.setFillStyle(BLRgba32(fillColor.r(), fillColor.g(), fillColor.b(), static_cast<uint8_t>(fillColor.a() * alpha)));
    ctx.fillCircle(BLCircle(0, headY, headR));
    BLPath headPath;
    headPath.addCircle(BLCircle(0, headY, headR));
    drawNeonStroke(ctx, headPath, rimColor, 3.5, alpha);

    // Torso & Limbs Path
    BLPath bodyPath;
    const double bodyTop = headY + headR + 12.0;
    const double bodyBot = 60.0;
    bodyPath.moveTo(0, bodyTop);
    bodyPath.lineTo(0, bodyBot);

    // Legs
    const double legLen = 170.0;
    bodyPath.moveTo(-18.0, bodyBot);
    bodyPath.lineTo(-24.0, bodyBot + legLen);
    bodyPath.moveTo(18.0, bodyBot);
    bodyPath.lineTo(24.0, bodyBot + legLen);

    // Arms
    const double armY = bodyTop + 30.0;
    if (pose == 1) { // Thinking (hand to head)
        bodyPath.moveTo(-25.0, armY);
        bodyPath.lineTo(-75.0, armY + 80.0);
        bodyPath.moveTo(25.0, armY);
        bodyPath.lineTo(70.0, armY - 20.0);
        bodyPath.lineTo(45.0, headY);
    } else { // Idle
        bodyPath.moveTo(-25.0, armY);
        bodyPath.lineTo(-65.0, armY + 125.0);
        bodyPath.moveTo(25.0, armY);
        bodyPath.lineTo(65.0, armY + 125.0);
    }

    drawNeonStroke(ctx, bodyPath, rimColor, 12.0, alpha);
    ctx.restore();
}

// Draw Scientist in Lab Coat & Chemistry Workbench
inline void drawScientistScene(BLContext& ctx, double cx, double cy, double scale, double bubbleT, double alpha = 1.0) {
    ctx.save();
    ctx.translate(cx, cy);
    ctx.scale(scale, scale);

    BLRgba32 amberRim(255, 150, 20, 255);
    BLRgba32 amberFill(80, 35, 5, 200);

    // Scientist Head
    const double headY = -230.0;
    const double headR = 52.0;
    ctx.setFillStyle(BLRgba32(amberFill.r(), amberFill.g(), amberFill.b(), static_cast<uint8_t>(amberFill.a() * alpha)));
    ctx.fillCircle(BLCircle(0, headY, headR));
    BLPath headPath;
    headPath.addCircle(BLCircle(0, headY, headR));
    drawNeonStroke(ctx, headPath, amberRim, 3.5, alpha);

    // Lab coat body
    BLPath coatPath;
    const double bodyTop = headY + headR + 12.0;
    const double bodyBot = 110.0;
    coatPath.moveTo(-32.0, bodyTop);
    coatPath.lineTo(32.0, bodyTop);
    coatPath.lineTo(70.0, bodyBot);
    coatPath.lineTo(-70.0, bodyBot);
    coatPath.close();

    ctx.setFillStyle(BLRgba32(amberFill.r(), amberFill.g(), amberFill.b(), static_cast<uint8_t>(amberFill.a() * alpha)));
    ctx.fillPath(coatPath);
    drawNeonStroke(ctx, coatPath, amberRim, 3.5, alpha);

    // Legs
    BLPath legPath;
    legPath.moveTo(-30.0, bodyBot);
    legPath.lineTo(-30.0, bodyBot + 60.0);
    legPath.moveTo(30.0, bodyBot);
    legPath.lineTo(30.0, bodyBot + 60.0);
    // Arm reaching forward
    legPath.moveTo(30.0, bodyTop + 40.0);
    legPath.lineTo(135.0, bodyTop + 90.0);
    drawNeonStroke(ctx, legPath, amberRim, 12.0, alpha);

    // Workbench & Apparatus
    const double tableTop = 40.0;
    const double tableW = 400.0;
    const double tableTh = 24.0;
    const double labX = 140.0;

    // Table
    BLPath tablePath;
    tablePath.addRect(BLRect(labX - tableW / 2.0, tableTop, tableW, tableTh));
    tablePath.addRect(BLRect(labX - tableW / 2.0 + 30.0, tableTop + tableTh, 20.0, 160.0));
    tablePath.addRect(BLRect(labX + tableW / 2.0 - 50.0, tableTop + tableTh, 20.0, 160.0));
    ctx.setFillStyle(BLRgba32(50, 20, 5, static_cast<uint8_t>(200 * alpha)));
    ctx.fillPath(tablePath);
    drawNeonStroke(ctx, tablePath, amberRim, 3.0, alpha);

    // Bottles on left
    BLPath bottles;
    bottles.addRoundRect(BLRoundRect(labX - 160.0, tableTop - 80.0, 32.0, 80.0, 4.0));
    bottles.addRoundRect(BLRoundRect(labX - 118.0, tableTop - 95.0, 34.0, 95.0, 4.0));
    ctx.setFillStyle(BLRgba32(60, 25, 5, static_cast<uint8_t>(180 * alpha)));
    ctx.fillPath(bottles);
    drawNeonStroke(ctx, bottles, amberRim, 2.5, alpha);

    // Conical boiling flask
    const double flaskX = labX;
    const double flaskY = tableTop - 55.0;
    const double flaskR = 36.0;

    BLPath flaskPath;
    flaskPath.addCircle(BLCircle(flaskX, flaskY, flaskR));
    flaskPath.addRect(BLRect(flaskX - 10.0, flaskY - 60.0, 20.0, 40.0));
    ctx.setFillStyle(BLRgba32(70, 30, 5, static_cast<uint8_t>(200 * alpha)));
    ctx.fillPath(flaskPath);
    drawNeonStroke(ctx, flaskPath, amberRim, 3.0, alpha);

    // Stand legs & flame
    BLPath stand;
    stand.moveTo(flaskX, flaskY + 15.0);
    stand.lineTo(flaskX - 32.0, tableTop);
    stand.moveTo(flaskX, flaskY + 15.0);
    stand.lineTo(flaskX + 32.0, tableTop);
    drawNeonStroke(ctx, stand, amberRim, 2.0, alpha);
    drawNeonCircle(ctx, flaskX, tableTop - 10.0, 8.0, BLRgba32(255, 220, 40, 255), alpha);

    // Rising bubbles
    for (int i = 0; i < 3; ++i) {
        double by = flaskY - 65.0 - std::fmod(bubbleT * 60.0 + i * 25.0, 80.0);
        double bx = flaskX + std::sin(by * 0.1) * 8.0;
        drawNeonCircle(ctx, bx, by, 4.0 + i, BLRgba32(255, 230, 80, 255), alpha);
    }

    // Test tubes on right
    BLPath rack;
    for (int i = 0; i < 3; ++i) {
        double tx = labX + 90.0 + i * 30.0;
        rack.moveTo(tx, tableTop - 75.0);
        rack.lineTo(tx, tableTop);
    }
    drawNeonStroke(ctx, rack, amberRim, 8.0, alpha);

    // Skull Danger Bubble above flask
    const double skullX = flaskX + 25.0;
    const double skullY = flaskY - 145.0;
    drawNeonCircle(ctx, skullX, skullY, 32.0, BLRgba32(245, 45, 65, 255), alpha * (0.85 + 0.15 * std::sin(bubbleT * 4.0)));

    ctx.restore();
}

// Draw Foreground Giant Laughing Figures
inline void drawForegroundGiants(BLContext& ctx, double leftX, double rightX, double yOffset, double alpha = 1.0) {
    if (alpha <= 0.01) return;

    BLRgba32 coralRim(250, 60, 95, 255);
    BLRgba32 coralFill(70, 15, 30, 220);

    // --- LEFT GIANT (Hands on hips, laughing mouth, radiating lines) ---
    ctx.save();
    ctx.translate(leftX, 1080.0 + yOffset);
    ctx.scale(1.45, 1.45);

    const double hY = -480.0;
    const double hR = 115.0;

    // Head
    ctx.setFillStyle(BLRgba32(coralFill.r(), coralFill.g(), coralFill.b(), static_cast<uint8_t>(coralFill.a() * alpha)));
    ctx.fillCircle(BLCircle(0, hY, hR));
    BLPath hPath;
    hPath.addCircle(BLCircle(0, hY, hR));
    drawNeonStroke(ctx, hPath, coralRim, 6.0, alpha);

    // Open laughing mouth (half-crescent cutout)
    BLPath mouth;
    mouth.addCircle(BLCircle(0, hY + 25.0, 50.0));
    ctx.setFillStyle(BLRgba32(10, 4, 8, static_cast<uint8_t>(255 * alpha)));
    ctx.fillPath(mouth);

    // Body
    BLPath body;
    body.moveTo(0, hY + hR + 20.0);
    body.lineTo(0, 220.0);
    drawNeonStroke(ctx, body, coralRim, 45.0, alpha);

    // Arms akimbo (on hips)
    BLPath arms;
    arms.moveTo(-60.0, hY + hR + 80.0);
    arms.lineTo(-240.0, hY + hR + 210.0);
    arms.lineTo(-75.0, 180.0);
    arms.moveTo(60.0, hY + hR + 80.0);
    arms.lineTo(240.0, hY + hR + 210.0);
    arms.lineTo(75.0, 180.0);
    drawNeonStroke(ctx, arms, coralRim, 26.0, alpha);

    // Radiating laugh lines above head
    BLPath rays;
    const std::vector<double> angles = {-45.0, -20.0, 5.0, 30.0};
    for (double aDeg : angles) {
        double rad = aDeg * kPi / 180.0;
        double x1 = std::cos(rad) * (hR + 35.0);
        double y1 = hY - std::sin(rad) * (hR + 35.0);
        double x2 = std::cos(rad) * (hR + 115.0);
        double y2 = hY - std::sin(rad) * (hR + 115.0);
        rays.moveTo(x1, y1);
        rays.lineTo(x2, y2);
    }
    drawNeonStroke(ctx, rays, coralRim, 8.0, alpha);
    ctx.restore();

    // --- RIGHT GIANT (Bending forward laughing, pointing left) ---
    ctx.save();
    ctx.translate(rightX, 1080.0 + yOffset);
    ctx.scale(1.45, 1.45);

    const double rhY = -460.0;
    const double rhR = 115.0;

    // Head
    ctx.setFillStyle(BLRgba32(coralFill.r(), coralFill.g(), coralFill.b(), static_cast<uint8_t>(coralFill.a() * alpha)));
    ctx.fillCircle(BLCircle(0, rhY, rhR));
    BLPath rhPath;
    rhPath.addCircle(BLCircle(0, rhY, rhR));
    drawNeonStroke(ctx, rhPath, coralRim, 6.0, alpha);

    // Open laughing mouth
    BLPath rmouth;
    rmouth.addCircle(BLCircle(-20.0, rhY + 25.0, 50.0));
    ctx.setFillStyle(BLRgba32(10, 4, 8, static_cast<uint8_t>(255 * alpha)));
    ctx.fillPath(rmouth);

    // Body leaning forward to left
    BLPath rbody;
    rbody.moveTo(0, rhY + rhR + 20.0);
    rbody.lineTo(-60.0, 220.0);
    drawNeonStroke(ctx, rbody, coralRim, 45.0, alpha);

    // Long arm pointing left at scientist
    BLPath rarm;
    rarm.moveTo(-40.0, rhY + rhR + 80.0);
    rarm.lineTo(-440.0, rhY + rhR + 120.0);
    drawNeonStroke(ctx, rarm, coralRim, 26.0, alpha);

    // Exclamation lines
    BLPath rrays;
    for (double aDeg : {150.0, 175.0, 200.0}) {
        double rad = aDeg * kPi / 180.0;
        double x1 = std::cos(rad) * (rhR + 40.0);
        double y1 = rhY - std::sin(rad) * (rhR + 40.0);
        double x2 = std::cos(rad) * (rhR + 130.0);
        double y2 = rhY - std::sin(rad) * (rhR + 130.0);
        rrays.moveTo(x1, y1);
        rrays.lineTo(x2, y2);
    }
    drawNeonStroke(ctx, rrays, coralRim, 8.0, alpha);
    ctx.restore();
}

} // namespace chronon::anim2

int main(int argc, char** argv) {
    using namespace chronon::anim2;

    std::cout << "========================================================\n"
              << "ChrononTemplate: Animation 2 (2.5D Neon Essay Dolly Out)\n"
              << "========================================================\n";

    fs::path outDir = "out/svg_parity/anim2_frames";
    if (argc >= 2) {
        outDir = fs::path(argv[1]);
    }
    fs::create_directories(outDir);

    struct Dust { double x, y, vx, vy, b; int r; };
    std::vector<Dust> dusts;
    std::mt19937 rng(1337);
    std::uniform_real_distribution<double> distX(0, kW), distY(0, kH);
    std::uniform_real_distribution<double> distV(-0.35, 0.35), distB(0.3, 0.85);

    for (int i = 0; i < 110; ++i) {
        dusts.push_back({distX(rng), distY(rng), distV(rng), distV(rng), distB(rng), (i % 3 == 0 ? 2 : 1)});
    }

    BLImage img(kW, kH, BL_FORMAT_PRGB32);
    BLContext ctx(img);

    std::cout << "Rendering " << kTotalFrames << " frames at 1920x1080...\n";

    for (int f = 0; f < kTotalFrames; ++f) {
        double t = static_cast<double>(f) / kFps;

        // Clear background
        ctx.setFillStyle(BLRgba32(3, 3, 5, 255));
        ctx.fillRect(BLRect(0, 0, kW, kH));

        // Soft optical vignette
        BLRadialGradientValues radValues{kW / 2.0, kH / 2.0, kW / 2.0, kH / 2.0, kW * 0.72};
        BLGradient radialVignette(radValues);
        radialVignette.addStop(0.0, BLRgba32(6, 6, 12, 0));
        radialVignette.addStop(1.0, BLRgba32(0, 0, 0, 125));
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

        // --- CAMERA CHOREOGRAPHY ---
        double camPan = 0.0;
        double dolly = 0.0;

        if (f < 60) {
            camPan = 0.0;
            dolly = 0.0;
        } else if (f < 120) {
            double p = (f - 60.0) / 60.0;
            camPan = easeInOutCubic(p);
            dolly = 0.0;
        } else {
            camPan = 1.0;
            double p = (f - 120.0) / 90.0;
            dolly = easeInOutCubic(p);
        }

        // Camera Pan & Dolly scaling
        double panShiftX = camPan * 550.0 * (1.0 - dolly * 0.35);
        double bgScale = (1.0 - dolly * 0.35);
        double bgAlpha = 1.0 - dolly * 0.25;

        // --- LAYER 1: Purple Couple on Left ---
        double l1X1 = (540.0 - panShiftX) * bgScale + (1.0 - bgScale) * (kW / 2.0);
        double l1Y1 = 680.0 * bgScale + (1.0 - bgScale) * (kH / 2.0);
        double l1Scale = 1.25 * bgScale;

        BLRgba32 purpleRim(245, 40, 180, 255);
        BLRgba32 purpleFill(70, 10, 50, 190);

        drawFigure(ctx, l1X1, l1Y1, l1Scale, purpleRim, purpleFill, 1, bgAlpha);
        drawFigure(ctx, l1X1 + 220.0 * l1Scale, l1Y1, l1Scale, purpleRim, purpleFill, 0, bgAlpha);

        // Thought bubble above left figure
        const double tbX = l1X1 + 90.0 * l1Scale;
        const double tbY = l1Y1 - 320.0 * l1Scale;
        drawNeonCircle(ctx, tbX, tbY, 65.0 * l1Scale, purpleRim, bgAlpha);
        drawNeonCircle(ctx, tbX - 45.0 * l1Scale, tbY - 10.0 * l1Scale, 40.0 * l1Scale, purpleRim, bgAlpha);
        drawNeonCircle(ctx, tbX + 45.0 * l1Scale, tbY - 10.0 * l1Scale, 40.0 * l1Scale, purpleRim, bgAlpha);
        // Tangle scribble inside
        BLPath tangle;
        tangle.addCircle(BLCircle(tbX, tbY, 28.0 * l1Scale));
        drawNeonStroke(ctx, tangle, BLRgba32(255, 230, 250, 255), 2.5 * l1Scale, bgAlpha);

        // Electric pulse arrow
        double arrowPulse = 0.7 + 0.3 * std::sin(f * 0.5);
        BLPath arrow;
        arrow.moveTo(tbX + 50.0 * l1Scale, tbY);
        arrow.lineTo(l1X1 + 220.0 * l1Scale, tbY + 30.0 * l1Scale);
        drawNeonStroke(ctx, arrow, BLRgba32(255, 120, 220, 255), 3.0 * l1Scale, bgAlpha * arrowPulse);

        // --- LAYER 2: Amber Scientist in Center/Right ---
        double l2X = (1300.0 - panShiftX) * bgScale + (1.0 - bgScale) * (kW / 2.0);
        double l2Y = 680.0 * bgScale + (1.0 - bgScale) * (kH / 2.0);
        double l2Scale = 1.35 * bgScale;

        drawScientistScene(ctx, l2X, l2Y, l2Scale, t, bgAlpha);

        // --- LAYER 3: Foreground Laughing Giants (Enter upon Dolly Out, f >= 115) ---
        if (f >= 115) {
            double pSlide = easeOutCubic(std::clamp((f - 115.0) / 45.0, 0.0, 1.0));
            double fgAlpha = std::clamp((f - 115.0) / 20.0, 0.0, 1.0);

            double leftGiantX = -220.0 + pSlide * 400.0;
            double rightGiantX = kW + 240.0 - pSlide * 420.0;
            double yOffset = 180.0 - pSlide * 180.0;

            drawForegroundGiants(ctx, leftGiantX, rightGiantX, yOffset, fgAlpha);
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
    std::cout << "[SUCCESS] Animation 2 rendered successfully to: " << outDir.string() << '\n';
    return 0;
}
