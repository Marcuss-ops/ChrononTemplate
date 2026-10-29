// ChrononTemplate: Native C++ Blend2D Renderer for SVG Parity
//
// Documentary reference renderer for the Documentary SVG Peak scene. It
// consumes the SAME shared scene module as `svg_peak_parity_emitter.cpp`
// (`svg_peak_scene.hpp`): geometry comes from the SVG asset, timing/colors/
// checkpoints/camera come from the scene preset. Nothing scene-specific is
// duplicated here — this file owns only the drawing treatment, never scene
// data (certification tests SVG-03/INT-02).
//
// Drawing treatment (calibrated on the documentary reference still):
//   - Glow is REAL blurred light: luminous elements are accumulated into an
//     emissive buffer, box-blurred into a continuous falloff and composited
//     additively (BL_COMP_OP_PLUS). No stacked alpha discs, no visible
//     concentric rings.
//   - Visual hierarchy: the SunOrb is the brightest point; DocumentaryPath is
//     a thin neutral gray-white stroke; CheckpointMarker is a translucent red
//     spot dimmer than the sun; background texture is barely visible.
//   - Per-primitive styles (SunOrb / CheckpointMarker / DocumentaryPath) share
//     the glow component but keep distinct aesthetics — no universal neon
//     look.
//   - The camera is one shared transform applied to every scene element
//     (FX-08).
//
// Usage:
//   render_svg_parity_blend2d [framesDir] [--svg path] [--preset path]
//                             [--atmosphere on|off] [--only-frame N]
//
// `--atmosphere off` renders a clean plate (no dust or vignette) for
// deterministic pixel measurements; `--only-frame N` renders a single frame
// (the static-frame look test).
//
// Errors (SVG-08): every malformed input produces an explicit "[ERROR]"
// line and exit code 1 — never a crash.

#include "documentary_style.hpp"
#include "svg_peak_scene.hpp"

#include <blend2d.h>

#include <algorithm>
#include <array>
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
// Drawing treatment (GlowBuffer + per-primitive styles) lives in
// documentary_style.hpp, shared with the morph reel renderer.
} // namespace chronon::svg_parity

namespace {

struct Options {
    std::filesystem::path framesDir = "out/svg_parity/frames";
    std::string svg = "tools/vector_diagram/assets/documentary_svg_peak_v1.svg";
    std::string preset = "catalog/documentary_svg_peak_v1.json";
    bool atmosphere = true;
    std::optional<int> onlyFrame;
};

void printUsage() {
    std::cout << "Usage: render_svg_parity_blend2d [framesDir] [--svg path] "
                 "[--preset path] [--atmosphere on|off] [--only-frame N]\n";
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
            } else if (arg == "--only-frame" && i + 1 < argc) {
                options.onlyFrame = std::stoi(argv[++i]);
            } else if (!arg.empty() && arg[0] != '-') {
                options.framesDir = arg;
            } else {
                throw SceneError("unknown argument: " + arg);
            }
        }

        std::cout << "========================================================\n"
                  << "ChrononTemplate: Blend2D Documentary SVG Parity Renderer\n"
                  << "Scene source of truth: " << options.svg << " + " << options.preset << "\n"
                  << "========================================================\n";

        // Single source of truth: the very values the emitter turns into the
        // RenderPlan drive every pixel here.
        const SceneSpec spec = loadSceneSpec(options.svg, options.preset);
        const int width = spec.width;
        const int height = spec.height;
        const int totalFrames = spec.frames;
        const Vec2 center{width / 2.0, height / 2.0};

        fs::create_directories(options.framesDir);

        // Atmosphere: near-invisible texture only (reference look).
        struct Dust { double x, y, vx, vy, b; int r; };
        std::vector<Dust> dusts;
        std::mt19937 rng(42);
        std::uniform_real_distribution<double> distX(0, width), distY(0, height);
        std::uniform_real_distribution<double> distV(-0.25, 0.25), distB(0.2, 0.6);
        for (int i = 0; i < 55; ++i) {
            dusts.push_back({distX(rng), distY(rng), distV(rng), distV(rng), distB(rng), 1});
        }

        const PathStyle pathStyle;
        const SunStyle sunStyle;
        const CheckpointStyle checkpointStyle;

        GlowBuffer glow;
        glow.init(width, height);

        BLImage img(width, height, BL_FORMAT_PRGB32);
        BLContext ctx(img);

        const int firstFrame = options.onlyFrame.value_or(0);
        const int lastFrame = options.onlyFrame.value_or(totalFrames - 1);

        std::cout << "Rendering frames " << firstFrame << ".." << lastFrame << " at "
                  << width << "x" << height << " (atmosphere "
                  << (options.atmosphere ? "on" : "off") << ")...\n";

        for (int f = firstFrame; f <= lastFrame; ++f) {
            // Background plate from the preset (the plan's `background` layer).
            ctx.setFillStyle(toRgba32(spec.background[0], spec.background[1],
                                      spec.background[2], 1.0));
            ctx.fillRect(BLRect(0, 0, width, height));

            if (options.atmosphere) {
                // Barely-there vignette.
                BLRadialGradientValues radValues{width / 2.0, height / 2.0,
                                                 width / 2.0, height / 2.0, width * 0.75};
                BLGradient radialVignette(radValues);
                radialVignette.addStop(0.0, BLRgba32(0, 0, 0, 0));
                radialVignette.addStop(1.0, BLRgba32(0, 0, 0, 60));
                ctx.setFillStyle(radialVignette);
                ctx.fillRect(BLRect(0, 0, width, height));

                // Micro dust: visible only as barely-perceptible texture.
                for (auto& d : dusts) {
                    d.x = std::fmod(d.x + d.vx + width, width);
                    d.y = std::fmod(d.y + d.vy + height, height);
                    double flicker = 0.5 + 0.5 * std::sin(f * 0.35 + d.b * 10.0);
                    uint8_t val = static_cast<uint8_t>(30 * d.b * flicker);
                    ctx.setFillStyle(BLRgba32(200, 205, 215, val));
                    ctx.fillCircle(BLCircle(d.x, d.y, d.r));
                }
            }

            // ── Camera: one transform shared by every scene element (FX-08) ──
            const CameraState cam = cameraAt(spec, f);
            const auto toScreen = [&](const Vec2& world) { return applyCamera(cam, world, center); };

            // Trim Path: partial polyline via the shared primitive (SVG-04/05).
            const double trimProgress = spec.trim.valueAt(f);
            std::vector<Vec2> visibleScreen;
            if (trimProgress > 0.0) {
                const std::vector<Vec2> visible = trimPolyline(spec.pathPoints, trimProgress);
                visibleScreen.reserve(visible.size());
                for (const Vec2& point : visible) {
                    visibleScreen.push_back(toScreen(point));
                }
            }

            // Sun marker following the path (SVG-06/07).
            std::optional<Vec2> sunScreen;
            if (f >= spec.marker.keyframes.front().first) {
                const Vec2 world = samplePolyline(spec.pathPoints, spec.marker.valueAt(f));
                sunScreen = toScreen(world);
            }

            // Checkpoints (SVG geometry, preset timing).
            struct CheckpointDraw { Vec2 screen; double radius; double pulse; };
            std::vector<CheckpointDraw> checkpointDraws;
            for (const CheckpointSpec& checkpoint : spec.checkpoints) {
                if (f < checkpoint.startFrame) continue;
                const double pulse = 1.0 + 0.06 * std::sin(f * 0.3);
                checkpointDraws.push_back({toScreen(checkpoint.center),
                                           checkpoint.radius, pulse});
            }

            // ── Emissive light: everything that glows deposits into the buffer,
            //    which is blurred into a continuous halo and added to the frame.
            glow.clear();
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
                const double radius = spec.markerSize * sunStyle.coreScale * cam.zoom;
                glow.addDisc(sunScreen->x, sunScreen->y, radius * 2.2,
                             sunStyle.glowR, sunStyle.glowG, sunStyle.glowB, sunStyle.glowGain);
            }
            glow.blur(std::max(2, static_cast<int>(width / 85)));

            // ── Crisp elements: dim, thin, secondary to the light. ────────────
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

            // Continuous blurred halo, added last so it wraps every element.
            glow.composite(ctx);

            // Save frame
            std::ostringstream ss;
            ss << options.framesDir.string() << "/frame_" << std::setfill('0')
               << std::setw(4) << f << ".png";
            img.writeToFile(ss.str().c_str());
            if (f % 30 == 0 || f == lastFrame) {
                std::cout << "  Rendered sample frame: " << ss.str() << '\n';
            }
        }

        ctx.end();
        std::cout << "\n[SUCCESS] Documentary SVG parity rendering complete!\n"
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
