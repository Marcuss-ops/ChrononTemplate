// ChrononTemplate: Morph Reel — Van -> Thermometer -> Sun/Mountain
//
// Rebuilt on the documentary reference look (see documentary_style.hpp):
// continuous blurred glow, strict visual hierarchy, per-primitive aesthetics.
// There is NO universal neon treatment — every primitive owns its style:
//
//   VehicleIcon      — dark natural silhouette, subtle rim light, discreet
//                      details (never glowing contours or wheel halos)
//   ThermometerIcon  — small, with a concentrated yellow light at the bulb
//   SunOrb           — the brightest point (shared SunStyle)
//   DocumentaryPath  — thin neutral stroke (shared PathStyle)
//   CheckpointMarker — translucent red spots (shared CheckpointStyle)
//
// Per-scene timing (260 frames @ 30 fps), each scene with its own entry,
// life and exit — elements never all accumulate at once:
//
//   000-060  VAN         slides in, holds briefly, fades out
//   055-115  THERMOMETER fades/scales in, the yellow column rises
//   105-118  TRANSITION  the bulb detaches, travels to the path start and
//                        becomes the SunOrb; the tube fades away
//   110-260  MOUNTAIN    trim draws the reference profile from the canonical
//                        SVG, the sun follows the path, checkpoints appear,
//                        slow camera pan + dolly (shared SceneSpec timing)
//
// The mountain section is driven by the SAME shared scene module as the
// parity renderer (SVG asset + scene preset): one geometry, one timing.
//
// Usage:
//   render_anim1_van_mountain_blend2d [framesDir] [--svg path] [--preset path]
//                                     [--atmosphere on|off]
//
// Errors: explicit "[ERROR]" and exit 1 — never a crash.

#include "documentary_style.hpp"
#include "svg_peak_scene.hpp"

#include <blend2d.h>

#include <algorithm>
#include <cmath>
#include <filesystem>
#include <iomanip>
#include <iostream>
#include <optional>
#include <random>
#include <sstream>
#include <string>
#include <vector>

namespace fs = std::filesystem;

namespace chronon::svg_parity {

// ── Scene timing (frames @ 30 fps) ──────────────────────────────────────────
constexpr int kTotalFrames = 260;
constexpr int kVanIn = 0, kVanHold = 30, kVanOut = 48, kVanGone = 62;
constexpr int kThermoIn = 55, kThermoRise = 70, kThermoFull = 105, kThermoGone = 122;
constexpr int kBulbStart = 105, kBulbLand = 118;
constexpr int kMountainStart = 110; // mountain local frame = f - kMountainStart

inline double easeOutCubic(double t) {
    t = std::clamp(t, 0.0, 1.0);
    return 1.0 - std::pow(1.0 - t, 3.0);
}

inline double smooth(double t) {
    t = std::clamp(t, 0.0, 1.0);
    return t * t * (3.0 - 2.0 * t);
}

inline double lerp(double a, double b, double t) { return a + (b - a) * t; }

// ── VehicleIcon: dark natural silhouette, subtle rim light ──────────────────

struct VehicleIconStyle {
    double fillR = 32 / 255.0, fillG = 40 / 255.0, fillB = 50 / 255.0;
    double windowR = 46 / 255.0, windowG = 58 / 255.0, windowB = 70 / 255.0;
    double rimR = 143 / 255.0, rimG = 166 / 255.0, rimB = 188 / 255.0;
    double rimAlpha = 0.45;
    double wheelR = 16 / 255.0, wheelG = 20 / 255.0, wheelB = 26 / 255.0;
};

// Draws the van at (x, y): local box is 432 x 192, (x, y) = top-left.
inline void drawVehicleIcon(BLContext& ctx, double x, double y,
                            const VehicleIconStyle& style, double alpha) {
    ctx.save();
    ctx.setGlobalAlpha(alpha);

    // body
    BLPath body;
    body.moveTo(x + 52, y + 30);
    body.lineTo(x + 322, y + 30);
    body.quadTo(x + 352, y + 30, x + 378, y + 74);
    body.lineTo(x + 400, y + 122);
    body.lineTo(x + 404, y + 152);
    body.lineTo(x + 36, y + 152);
    body.lineTo(x + 28, y + 148);
    body.lineTo(x + 30, y + 58);
    body.quadTo(x + 32, y + 30, x + 52, y + 30);
    body.close();
    ctx.setFillStyle(toRgba32(style.fillR, style.fillG, style.fillB, 0.94));
    ctx.fillPath(body);

    // windows
    ctx.setFillStyle(toRgba32(style.windowR, style.windowG, style.windowB, 0.9));
    ctx.fillRect(BLRect(x + 95, y + 44, 178, 38));
    BLPath windshield;
    windshield.moveTo(x + 300, y + 44);
    windshield.lineTo(x + 356, y + 44);
    windshield.quadTo(x + 368, y + 48, x + 378, y + 74);
    windshield.lineTo(x + 300, y + 74);
    windshield.close();
    ctx.fillPath(windshield);

    // wheels
    ctx.setFillStyle(toRgba32(style.wheelR, style.wheelG, style.wheelB));
    ctx.fillCircle(BLCircle(x + 112, y + 152, 36));
    ctx.fillCircle(BLCircle(x + 322, y + 152, 36));
    ctx.setFillStyle(toRgba32(style.windowR, style.windowG, style.windowB, 0.8));
    ctx.fillCircle(BLCircle(x + 112, y + 152, 13));
    ctx.fillCircle(BLCircle(x + 322, y + 152, 13));

    // subtle rim light along the roof and hood — a highlight, not a contour
    BLPath rim;
    rim.moveTo(x + 52, y + 30);
    rim.lineTo(x + 322, y + 30);
    rim.quadTo(x + 352, y + 30, x + 378, y + 74);
    ctx.setStrokeStyle(toRgba32(style.rimR, style.rimG, style.rimB, style.rimAlpha));
    ctx.setStrokeWidth(2.5);
    ctx.setStrokeCaps(BL_STROKE_CAP_ROUND);
    ctx.strokePath(rim);

    // warm headlight
    ctx.setFillStyle(toRgba32(1.0, 0.88, 0.66, 0.9));
    ctx.fillCircle(BLCircle(x + 402, y + 118, 7));

    ctx.restore();
}

// ── ThermometerIcon: small, concentrated yellow light ───────────────────────

struct ThermometerIconStyle {
    double shellR = 184 / 255.0, shellG = 64 / 255.0, shellB = 47 / 255.0;
    double darkR = 26 / 255.0, darkG = 13 / 255.0, darkB = 9 / 255.0;
    double fillR = 1.0, fillG = 0.82, fillB = 0.12;
};

// Thermometer centred on (cx, cy); `level` 0..1 fills the column.
inline void drawThermometerIcon(BLContext& ctx, double cx, double cy,
                                double level, double scale, double alpha,
                                const ThermometerIconStyle& style) {
    ctx.save();
    ctx.setGlobalAlpha(alpha);
    const double s = scale;
    const double bulbY = cy + 25 * s;
    const double topY = cy - 135 * s;

    // red shell capsule
    ctx.setFillStyle(toRgba32(style.shellR, style.shellG, style.shellB, 0.9));
    ctx.fillCircle(BLCircle(cx, bulbY, 25 * s));
    ctx.fillCircle(BLCircle(cx, topY, 13 * s));
    ctx.fillRect(BLRect(cx - 13 * s, topY, 26 * s, bulbY - topY));

    // dark interior
    ctx.setFillStyle(toRgba32(style.darkR, style.darkG, style.darkB, 0.96));
    ctx.fillCircle(BLCircle(cx, bulbY, 20 * s));
    ctx.fillCircle(BLCircle(cx, topY + 3 * s, 9.5 * s));
    ctx.fillRect(BLRect(cx - 9.5 * s, topY + 3 * s, 19 * s, bulbY - topY - 3 * s));

    // yellow mercury: bulb + column up to `level`
    const double columnTop = bulbY - level * 140 * s;
    ctx.setFillStyle(toRgba32(style.fillR, style.fillG, style.fillB));
    ctx.fillCircle(BLCircle(cx, bulbY, 17 * s));
    ctx.fillRect(BLRect(cx - 7 * s, columnTop, 14 * s, bulbY - columnTop));
    ctx.fillCircle(BLCircle(cx, columnTop, 7 * s));

    ctx.restore();
}

} // namespace chronon::svg_parity

namespace {

struct Options {
    std::filesystem::path framesDir = "out/svg_parity/morph_frames";
    std::string svg = "tools/vector_diagram/assets/documentary_svg_peak_v1.svg";
    std::string preset = "catalog/documentary_svg_peak_v1_hd.json";
    bool atmosphere = true;
};

void printUsage() {
    std::cout << "Usage: render_anim1_van_mountain_blend2d [framesDir] [--svg path] "
                 "[--preset path] [--atmosphere on|off]\n";
}

} // namespace

int main(int argc, char** argv) {
    using namespace chronon::svg_parity;

    Options options;
    try {
        for (int i = 1; i < argc; ++i) {
            const std::string arg = argv[i];
            if (arg == "--help" || arg == "-h") {
                printUsage();
                return 0;
            }
            if (arg == "--svg" && i + 1 < argc) {
                options.svg = argv[++i];
            } else if (arg == "--preset" && i + 1 < argc) {
                options.preset = argv[++i];
            } else if (arg == "--atmosphere" && i + 1 < argc) {
                const std::string value = argv[++i];
                if (value != "on" && value != "off") {
                    throw SceneError("--atmosphere expects on or off");
                }
                options.atmosphere = value == "on";
            } else if (!arg.empty() && arg[0] != '-') {
                options.framesDir = arg;
            } else {
                throw SceneError("unknown argument: " + arg);
            }
        }

        std::cout << "========================================================\n"
                  << "ChrononTemplate: Morph Reel (Van -> Thermometer -> Mountain)\n"
                  << "Mountain source of truth: " << options.svg << " + " << options.preset << "\n"
                  << "========================================================\n";

        // The mountain scene comes from the shared module (canonical SVG +
        // preset), the very values the emitter turns into the RenderPlan.
        const SceneSpec spec = loadSceneSpec(options.svg, options.preset);
        const int width = spec.width;
        const int height = spec.height;
        const Vec2 center{width / 2.0, height / 2.0};

        fs::create_directories(options.framesDir);

        const VehicleIconStyle vehicleStyle;
        const ThermometerIconStyle thermoStyle;
        const PathStyle pathStyle;
        const SunStyle sunStyle;
        const CheckpointStyle checkpointStyle;

        // Atmosphere: near-invisible texture only (reference look).
        struct Dust { double x, y, vx, vy, b; };
        std::vector<Dust> dusts;
        std::mt19937 rng(42);
        std::uniform_real_distribution<double> distX(0, width), distY(0, height);
        std::uniform_real_distribution<double> distV(-0.25, 0.25), distB(0.2, 0.6);
        for (int i = 0; i < 55; ++i) {
            dusts.push_back({distX(rng), distY(rng), distV(rng), distV(rng), distB(rng)});
        }

        GlowBuffer glow;
        glow.init(width, height);

        BLImage img(width, height, BL_FORMAT_PRGB32);
        BLContext ctx(img);

        std::cout << "Rendering " << kTotalFrames << " frames at " << width << "x"
                  << height << "...\n";

        for (int f = 0; f < kTotalFrames; ++f) {
            ctx.setFillStyle(toRgba32(spec.background[0], spec.background[1],
                                      spec.background[2], 1.0));
            ctx.fillRect(BLRect(0, 0, width, height));

            if (options.atmosphere) {
                BLRadialGradientValues radValues{width / 2.0, height / 2.0,
                                                 width / 2.0, height / 2.0, width * 0.75};
                BLGradient radialVignette(radValues);
                radialVignette.addStop(0.0, BLRgba32(0, 0, 0, 0));
                radialVignette.addStop(1.0, BLRgba32(0, 0, 0, 60));
                ctx.setFillStyle(radialVignette);
                ctx.fillRect(BLRect(0, 0, width, height));

                for (auto& d : dusts) {
                    d.x = std::fmod(d.x + d.vx + width, width);
                    d.y = std::fmod(d.y + d.vy + height, height);
                    double flicker = 0.5 + 0.5 * std::sin(f * 0.35 + d.b * 10.0);
                    uint8_t val = static_cast<uint8_t>(30 * d.b * flicker);
                    ctx.setFillStyle(BLRgba32(200, 205, 215, val));
                    ctx.fillCircle(BLCircle(d.x, d.y, 1));
                }
            }

            glow.clear();

            // ── Scene VAN (000-060) ─────────────────────────────────────────
            if (f < kVanGone) {
                const double slide = easeOutCubic((f - kVanIn) / 30.0);
                double x = lerp(-520.0, 430.0, slide);
                double y = 420.0 + 3.0 * std::sin(f * 0.12);
                double alpha = 1.0;
                if (f > kVanHold) {
                    x += easeOutCubic((f - kVanHold) / (kVanGone - kVanHold)) * 120.0;
                    alpha = 1.0 - smooth((f - kVanOut) / (kVanGone - kVanOut));
                }
                drawVehicleIcon(ctx, x, y, vehicleStyle, alpha);
                if (alpha > 0.0) {
                    glow.addDisc(x + 402, y + 118, 26, 1.0, 0.85, 0.55, 0.45 * alpha);
                }
            }

            // ── Scene THERMOMETER (055-115) ─────────────────────────────────
            double thermoAlpha = 0.0;
            if (f >= kThermoIn && f < kThermoGone) {
                thermoAlpha = smooth((f - kThermoIn) / 15.0);
                if (f >= kThermoFull) {
                    // the tube fades during the transition; the bulb lives on
                    thermoAlpha = 1.0 - smooth((f - kThermoFull) / (kThermoGone - kThermoFull));
                }
                const double scale = lerp(0.85, 1.0, smooth((f - kThermoIn) / 15.0));
                const double level = lerp(0.25, 0.95, smooth((f - kThermoRise) / (kThermoFull - kThermoRise)));
                drawThermometerIcon(ctx, 950, 520, level, scale, thermoAlpha, thermoStyle);
                if (thermoAlpha > 0.0) {
                    glow.addDisc(950, 520 + 25 * scale, 30 * scale,
                                 1.0, 0.85, 0.35, 0.8 * thermoAlpha);
                }
            }

            // ── TRANSITION (105-118): the bulb becomes the SunOrb ───────────
            const double sunRadius = spec.markerSize * sunStyle.coreScale;
            if (f >= kBulbStart && f < kBulbLand) {
                const double t = smooth((f - kBulbStart) / (kBulbLand - kBulbStart));
                const Vec2 pathStart = spec.pathPoints.front();
                const double bx = lerp(950.0, pathStart.x, t);
                const double by = lerp(545.0, pathStart.y, t);
                const double br = lerp(17.0, sunRadius, t);
                ctx.setFillStyle(toRgba32(sunStyle.coreR, sunStyle.coreG, sunStyle.coreB));
                ctx.fillCircle(BLCircle(bx, by, br));
                ctx.setFillStyle(toRgba32(sunStyle.hotR, sunStyle.hotG, sunStyle.hotB, 0.55));
                ctx.fillCircle(BLCircle(bx, by, br * 0.5));
                glow.addDisc(bx, by, br * 2.2, sunStyle.glowR, sunStyle.glowG,
                             sunStyle.glowB, sunStyle.glowGain);
            }

            // ── Scene MOUNTAIN (110-260): canonical SVG scene module ────────
            if (f >= kMountainStart) {
                const int m = f - kMountainStart;
                const CameraState cam = cameraAt(spec, m);
                const auto toScreen = [&](const Vec2& world) {
                    return applyCamera(cam, world, center);
                };

                const double trimProgress = spec.trim.valueAt(m);
                std::vector<Vec2> visibleScreen;
                if (trimProgress > 0.0) {
                    const std::vector<Vec2> visible = trimPolyline(spec.pathPoints, trimProgress);
                    visibleScreen.reserve(visible.size());
                    for (const Vec2& point : visible) {
                        visibleScreen.push_back(toScreen(point));
                    }
                }

                std::optional<Vec2> sunScreen;
                if (m >= spec.marker.keyframes.front().first && f >= kBulbLand) {
                    sunScreen = toScreen(samplePolyline(spec.pathPoints, spec.marker.valueAt(m)));
                }

                struct CheckpointDraw { Vec2 screen; double radius; double pulse; };
                std::vector<CheckpointDraw> checkpointDraws;
                for (const CheckpointSpec& checkpoint : spec.checkpoints) {
                    if (m < checkpoint.startFrame) continue;
                    const double pulse = 1.0 + 0.06 * std::sin(m * 0.3);
                    checkpointDraws.push_back({toScreen(checkpoint.center),
                                               checkpoint.radius, pulse});
                }

                if (!visibleScreen.empty()) {
                    glow.addStroke(visibleScreen, pathStyle.width * cam.zoom * 1.6,
                                   pathStyle.r, pathStyle.g, pathStyle.b, pathStyle.glowGain);
                }
                for (const auto& checkpoint : checkpointDraws) {
                    glow.addDisc(checkpoint.screen.x, checkpoint.screen.y,
                                 checkpoint.radius * checkpointStyle.coreScale * cam.zoom * 1.3,
                                 checkpointStyle.coreR, checkpointStyle.coreG, checkpointStyle.coreB,
                                 checkpointStyle.glowGain * checkpoint.pulse);
                }
                if (sunScreen) {
                    glow.addDisc(sunScreen->x, sunScreen->y, sunRadius * cam.zoom * 2.2,
                                 sunStyle.glowR, sunStyle.glowG, sunStyle.glowB, sunStyle.glowGain);
                }

                if (!visibleScreen.empty()) {
                    drawPathCore(ctx, visibleScreen, pathStyle, cam.zoom);
                }
                for (const auto& checkpoint : checkpointDraws) {
                    drawCheckpointMarker(ctx, checkpoint.screen.x, checkpoint.screen.y,
                                         checkpoint.radius * checkpoint.pulse,
                                         cam.zoom, checkpointStyle);
                }
                if (sunScreen) {
                    drawSunOrb(ctx, sunScreen->x, sunScreen->y,
                               spec.markerSize, cam.zoom, sunStyle);
                }
            }

            // Continuous blurred halo, added last so it wraps every element.
            glow.blur(std::max(2, static_cast<int>(width / 85)));
            glow.composite(ctx);

            std::ostringstream ss;
            ss << options.framesDir.string() << "/frame_" << std::setfill('0')
               << std::setw(4) << f << ".png";
            img.writeToFile(ss.str().c_str());
            if (f % 30 == 0 || f == kTotalFrames - 1) {
                std::cout << "  Rendered sample frame: " << ss.str() << '\n';
            }
        }

        ctx.end();
        std::cout << "\n[SUCCESS] Morph reel rendering complete!\n"
                  << "Frames saved in: " << options.framesDir.string() << '\n';
        return 0;
    } catch (const SceneError& e) {
        std::cerr << "[ERROR] " << e.what() << '\n';
        return 1;
    } catch (const std::exception& e) {
        std::cerr << "[ERROR] unexpected failure: " << e.what() << '\n';
        return 1;
    }
}
