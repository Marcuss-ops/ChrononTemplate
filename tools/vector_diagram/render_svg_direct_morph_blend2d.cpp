// render_svg_direct_morph_blend2d.cpp
// 100% Pure Native C++ SVG Loader, Topological Morpher & 60 FPS Blend2D Renderer
// Direct Disk SVG Ingestion: brain.svg -> cpu.svg -> atom.svg -> rocket.svg

#include <chronontemplate/vector_diagram/SvgPathParser.hpp>
#include <chronontemplate/vector_diagram/TopologicalPathMorpher.hpp>
#include <blend2d.h>
#include <iostream>
#include <vector>
#include <string>
#include <cmath>
#include <filesystem>
#include <sstream>
#include <iomanip>
#include <algorithm>

namespace fs = std::filesystem;
using namespace chronontemplate::vector_diagram;
constexpr double kPi = 3.14159265358979323846;

inline double clamp01(double v) {
    return (v < 0.0) ? 0.0 : (v > 1.0 ? 1.0 : v);
}

inline double smoothstep(double edge0, double edge1, double x) {
    double t = clamp01((x - edge0) / (edge1 - edge0));
    return t * t * (3.0 - 2.0 * t);
}

inline BLRgba32 lerp_color(BLRgba32 c1, BLRgba32 c2, double t) {
    t = clamp01(t);
    uint32_t r = (uint32_t)((1.0 - t) * c1.r() + t * c2.r());
    uint32_t g = (uint32_t)((1.0 - t) * c1.g() + t * c2.g());
    uint32_t b = (uint32_t)((1.0 - t) * c1.b() + t * c2.b());
    uint32_t a = (uint32_t)((1.0 - t) * c1.a() + t * c2.a());
    return BLRgba32(r, g, b, a);
}

// 8x8 Bayer Matrix Dithering
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

int main() {
    std::cout << "========================================================\n"
              << "ChrononTemplate: 100% Pure Native C++ SVG Direct Morpher\n"
              << "Direct Disk SVG Ingestion -> Arc-Length Resampling -> 60FPS\n"
              << "========================================================\n";

    std::string base_dir = "C:/Users/pater/Pyt/ChrononTemplate/";
    std::string svg_dir = base_dir + "assets/icons/svg/";
    std::string frames_dir = base_dir + "out/svg_parity/direct_svg_morph_frames/";
    std::string out_mp4 = base_dir + "out/svg_parity/direct_svg_morph_showcase.mp4";

    fs::create_directories(frames_dir);

    // 1. Direct Native C++ SVG Loading from Disk
    ArcLengthPath pBrain, pCpu, pAtom, pRocket;
    BLPath blBrain, blCpu, blAtom, blRocket;

    std::cout << "Loading SVG files directly from disk in C++...\n";
    if (!SvgPathParser::loadSvgFile(svg_dir + "brain.svg", pBrain, blBrain)) {
        std::cerr << "Failed to load brain.svg\n"; return 1;
    }
    if (!SvgPathParser::loadSvgFile(svg_dir + "cpu.svg", pCpu, blCpu)) {
        std::cerr << "Failed to load cpu.svg\n"; return 1;
    }
    if (!SvgPathParser::loadSvgFile(svg_dir + "atom.svg", pAtom, blAtom)) {
        std::cerr << "Failed to load atom.svg\n"; return 1;
    }
    if (!SvgPathParser::loadSvgFile(svg_dir + "rocket.svg", pRocket, blRocket)) {
        std::cerr << "Failed to load rocket.svg\n"; return 1;
    }
    std::cout << "  [SUCCESS] All 4 SVGs parsed into native ArcLengthPaths.\n";

    // 2. Initialize Pure C++ Topological Morphers
    const size_t kNodes = 256;
    TopologicalPathMorpher morpher1, morpher2, morpher3;
    morpher1.initialize(pBrain, pCpu, kNodes);     // Brain -> CPU
    morpher2.initialize(pCpu, pAtom, kNodes);       // CPU -> Atom
    morpher3.initialize(pAtom, pRocket, kNodes);   // Atom -> Rocket

    std::cout << "Morpher 1 (Brain->CPU): E=" << morpher1.get_metrics().min_energy << ", shift=" << morpher1.get_metrics().optimal_shift << "\n";
    std::cout << "Morpher 2 (CPU->Atom): E=" << morpher2.get_metrics().min_energy << ", shift=" << morpher2.get_metrics().optimal_shift << "\n";
    std::cout << "Morpher 3 (Atom->Rocket): E=" << morpher3.get_metrics().min_energy << ", shift=" << morpher3.get_metrics().optimal_shift << "\n";

    const int kWidth = 1920;
    const int kHeight = 1080;
    const int kTotalFrames = 450; // 7.5 seconds @ 60fps
    const double kFps = 60.0;

    BLImage frame_img(kWidth, kHeight, BL_FORMAT_PRGB32);
    BLContext ctx(frame_img);

    std::cout << "Rendering 450 frames (7.5s @ 60fps)...\n";

    for (int frame = 0; frame < kTotalFrames; ++frame) {
        double t = frame / kFps;

        std::vector<Point2D> current_pts;
        std::vector<Point2D> source_pts, target_pts;
        BLRgba32 cur_color;
        std::string stage_title;
        double stage_tau = 0.0;
        double rocket_y_offset = 0.0;

        if (t < 0.5) {
            current_pts = morpher1.get_pts_a();
            cur_color = BLRgba32(255, 0, 128); // Magenta Brain
            stage_title = "STAGE 1: HUMAN BRAIN (brain.svg) [NEURAL CORE]";
            stage_tau = 0.0;
        } else if (t < 2.0) {
            stage_tau = smoothstep(0.5, 2.0, t);
            current_pts = morpher1.evaluate_morph(stage_tau);
            source_pts = morpher1.get_pts_a();
            target_pts = morpher1.get_pts_b_aligned();
            cur_color = lerp_color(BLRgba32(255, 0, 128), BLRgba32(0, 240, 255), stage_tau);
            stage_title = "TOPOLOGICAL MORPH: brain.svg -> cpu.svg";
        } else if (t < 2.6) {
            current_pts = morpher1.get_pts_b_aligned();
            cur_color = BLRgba32(0, 240, 255); // Cyan CPU
            stage_title = "STAGE 2: SEMICONDUCTOR CPU (cpu.svg) [AI HARDWARE]";
            stage_tau = 1.0;
        } else if (t < 4.1) {
            stage_tau = smoothstep(2.6, 4.1, t);
            current_pts = morpher2.evaluate_morph(stage_tau);
            source_pts = morpher2.get_pts_a();
            target_pts = morpher2.get_pts_b_aligned();
            cur_color = lerp_color(BLRgba32(0, 240, 255), BLRgba32(255, 185, 10), stage_tau);
            stage_title = "TOPOLOGICAL MORPH: cpu.svg -> atom.svg";
        } else if (t < 4.7) {
            current_pts = morpher2.get_pts_b_aligned();
            double pulse = 1.0 + 0.03 * std::sin(t * 8.0);
            for (auto& p : current_pts) { p.x *= pulse; p.y *= pulse; }
            cur_color = BLRgba32(255, 185, 10); // Golden Atom
            stage_title = "STAGE 3: QUANTUM ATOM (atom.svg) [ORBITAL FLUX]";
            stage_tau = 1.0;
        } else if (t < 6.2) {
            stage_tau = smoothstep(4.7, 6.2, t);
            current_pts = morpher3.evaluate_morph(stage_tau);
            source_pts = morpher3.get_pts_a();
            target_pts = morpher3.get_pts_b_aligned();
            cur_color = lerp_color(BLRgba32(255, 185, 10), BLRgba32(165, 80, 255), stage_tau);
            stage_title = "TOPOLOGICAL MORPH: atom.svg -> rocket.svg";
        } else {
            current_pts = morpher3.get_pts_b_aligned();
            cur_color = BLRgba32(165, 80, 255); // Violet Rocket
            double launch_t = (t - 6.2) / 1.3;
            rocket_y_offset = -launch_t * launch_t * 850.0;
            stage_title = "STAGE 4: DEEP SPACE ROCKET (rocket.svg) [ORBITAL ASCENT]";
            stage_tau = 1.0;
        }

        // Clear Deep Black Background
        ctx.clearAll();
        ctx.setFillStyle(BLRgba32(2, 4, 8, 255));
        ctx.fillAll();

        // 2.5D Subtle Metric Grid
        ctx.setStrokeWidth(1.0);
        ctx.setStrokeStyle(BLRgba32(30, 50, 80, 35));
        for (double gx = 160.0; gx <= 1760.0; gx += 160.0) {
            ctx.strokeLine(gx, 80.0, gx, 1000.0);
        }
        for (double gy = 120.0; gy <= 960.0; gy += 120.0) {
            ctx.strokeLine(80.0, gy, 1840.0, gy);
        }

        double cx = 960.0;
        double cy = 540.0 + rocket_y_offset;

        // Concentric HUD Circular Reticles
        ctx.setStrokeStyle(BLRgba32(0, 240, 255, 25));
        ctx.strokeCircle(960.0, 540.0, 260.0);
        ctx.strokeCircle(960.0, 540.0, 310.0);

        // Vector Displacement Flow Lines during Morph
        if (!source_pts.empty() && !target_pts.empty() && stage_tau > 0.02 && stage_tau < 0.98) {
            double lattice_alpha = std::sin(stage_tau * kPi) * 80.0;
            ctx.save();
            ctx.setCompOp(BL_COMP_OP_PLUS);
            ctx.setStrokeWidth(1.0);
            ctx.setStrokeStyle(BLRgba32(cur_color.r(), cur_color.g(), cur_color.b(), (uint32_t)lattice_alpha));
            for (size_t i = 0; i < source_pts.size(); i += 4) {
                ctx.strokeLine(cx + source_pts[i].x, cy + source_pts[i].y,
                               cx + target_pts[i].x, cy + target_pts[i].y);
            }
            ctx.restore();
        }

        // Rocket Thruster Sparks (Finale)
        if (t > 6.2) {
            ctx.save();
            ctx.setCompOp(BL_COMP_OP_PLUS);
            for (int k = 1; k <= 20; ++k) {
                double pk_y = cy + 175.0 + k * 18.0;
                double pk_x = cx + ((k * 17) % 21 - 10) * 1.5;
                double pk_r = (22.0 - k) * 0.9;
                uint32_t pk_a = (uint32_t)((1.0 - k / 21.0) * 220);
                ctx.setFillStyle(BLRgba32(255, 130 + k * 5, 20, pk_a));
                ctx.fillCircle(pk_x, pk_y, pk_r);
            }
            ctx.restore();
        }

        // Build Shape Path
        BLPath shape_path;
        if (!current_pts.empty()) {
            shape_path.moveTo(cx + current_pts[0].x, cy + current_pts[0].y);
            for (size_t i = 1; i < current_pts.size(); ++i) {
                shape_path.lineTo(cx + current_pts[i].x, cy + current_pts[i].y);
            }
            shape_path.close();
        }

        // Semi-Translucent Inner Base Fill
        ctx.setFillStyle(BLRgba32(cur_color.r() / 8, cur_color.g() / 8, cur_color.b() / 8, 40));
        ctx.fillPath(shape_path);

        // Multi-Pass Exponential Bloom (Additive)
        ctx.save();
        ctx.setCompOp(BL_COMP_OP_PLUS);
        ctx.setStrokeCaps(BL_STROKE_CAP_ROUND);
        ctx.setStrokeJoin(BL_STROKE_JOIN_ROUND);

        // Pass 1: Wide outer halo
        ctx.setStrokeWidth(28.0);
        ctx.setStrokeStyle(BLRgba32(cur_color.r(), cur_color.g(), cur_color.b(), 18));
        ctx.strokePath(shape_path);

        // Pass 2: Mid glow
        ctx.setStrokeWidth(14.0);
        ctx.setStrokeStyle(BLRgba32(cur_color.r(), cur_color.g(), cur_color.b(), 50));
        ctx.strokePath(shape_path);

        // Pass 3: Saturated rim
        ctx.setStrokeWidth(6.5);
        ctx.setStrokeStyle(BLRgba32(cur_color.r(), cur_color.g(), cur_color.b(), 130));
        ctx.strokePath(shape_path);
        ctx.restore();

        // Pass 4: Specular Core (SRC_OVER)
        ctx.setCompOp(BL_COMP_OP_SRC_OVER);
        ctx.setStrokeCaps(BL_STROKE_CAP_ROUND);
        ctx.setStrokeJoin(BL_STROKE_JOIN_ROUND);
        ctx.setStrokeWidth(2.2);
        ctx.setStrokeStyle(BLRgba32(250, 252, 255, 255));
        ctx.strokePath(shape_path);

        // Highlight Sampled Vertices (every 8th node)
        for (size_t i = 0; i < current_pts.size(); i += 8) {
            double vx = cx + current_pts[i].x;
            double vy = cy + current_pts[i].y;
            ctx.save();
            ctx.setCompOp(BL_COMP_OP_PLUS);
            ctx.setFillStyle(BLRgba32(cur_color.r(), cur_color.g(), cur_color.b(), 190));
            ctx.fillCircle(vx, vy, 4.0);
            ctx.restore();

            ctx.setFillStyle(BLRgba32(255, 255, 255, 255));
            ctx.fillCircle(vx, vy, 1.8);
        }

        // Technical HUD Frame Brackets
        ctx.setStrokeWidth(1.5);
        ctx.setStrokeStyle(BLRgba32(0, 240, 255, 120));
        ctx.strokeLine(60.0, 60.0, 180.0, 60.0);
        ctx.strokeLine(60.0, 60.0, 60.0, 120.0);
        ctx.strokeLine(1860.0, 1020.0, 1740.0, 1020.0);
        ctx.strokeLine(1860.0, 1020.0, 1860.0, 960.0);

        // Bottom Progress Bar
        double bar_w = 600.0;
        double bar_x = (kWidth - bar_w) * 0.5;
        double bar_y = 1010.0;
        ctx.setStrokeStyle(BLRgba32(40, 70, 100, 100));
        ctx.strokeLine(bar_x, bar_y, bar_x + bar_w, bar_y);
        ctx.setStrokeWidth(3.0);
        ctx.setStrokeStyle(cur_color);
        ctx.strokeLine(bar_x, bar_y, bar_x + bar_w * (t / 7.5), bar_y);

        // Subtle Analog Film Dust
        for (int d = 0; d < 50; ++d) {
            uint32_t seed = (uint32_t)(d * 1879 + frame * 8329);
            seed = (seed ^ 61) ^ (seed >> 16);
            seed *= 9;
            seed = seed ^ (seed >> 4);
            seed *= 0x27d4eb2d;
            seed = seed ^ (seed >> 15);

            double dx = (seed % kWidth);
            double dy = ((seed / kWidth) % kHeight);
            double d_alpha = ((seed >> 8) % 35) / 255.0;

            ctx.setFillStyle(BLRgba32(220, 235, 255, (uint32_t)(d_alpha * 255)));
            ctx.fillCircle(dx, dy, 0.9);
        }

        // Apply Bayer Dithering
        applyBayerDithering(frame_img);

        // Save Frame
        std::ostringstream fn;
        fn << frames_dir << "frame_" << std::setfill('0') << std::setw(4) << frame << ".png";
        frame_img.writeToFile(fn.str().c_str());

        if (frame % 75 == 0 || frame == kTotalFrames - 1) {
            std::cout << "  Rendered frame " << frame << " / " << kTotalFrames 
                      << " (" << (int)((frame / (double)kTotalFrames) * 100) << "%)\n";
        }
    }

    ctx.end();
    std::cout << "[DONE] Successfully rendered all 450 frames to " << frames_dir << "\n";
    return 0;
}
