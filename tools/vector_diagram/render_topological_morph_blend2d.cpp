// render_topological_morph_blend2d.cpp
// 60fps Native Blend2D Renderer for Topological Morphing Showcase (Van -> Thermometer -> Sun -> Rocket)

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

// 1. Raw Vector Geometries centered at (0, 0)
std::vector<Point2D> build_van_shape() {
    // 26 vertices defining the delivery van silhouette
    return {
        { -180.0,  50.0 }, { -180.0, -40.0 }, { -170.0, -50.0 }, { -50.0, -50.0 }, // rear cargo
        {  -40.0, -50.0 }, {  10.0, -50.0 }, {   30.0, -50.0 }, {  60.0, -20.0 }, // cabin roof & windshield
        { 130.0,  -20.0 }, { 145.0,  -10.0 }, { 150.0,   10.0 }, { 150.0,  50.0 }, // hood & front bumper
        { 140.0,   55.0 }, { 115.0,   55.0 },                                      // front undercarriage
        { 105.0,   30.0 }, {  80.0,   20.0 }, {  55.0,   30.0 }, {  45.0,  55.0 }, // front wheel arch
        { -45.0,   55.0 },                                                         // center bottom
        { -55.0,   30.0 }, { -80.0,   20.0 }, { -105.0,  30.0 }, { -115.0, 55.0 }, // rear wheel arch
        { -150.0,  55.0 }, { -170.0,  55.0 }, { -180.0,  50.0 }                    // rear step
    };
}

std::vector<Point2D> build_thermometer_shape() {
    // 20 vertices defining the clinical thermometer / vial silhouette
    std::vector<Point2D> pts;
    // Top stem rounded cap
    for (int i = 0; i <= 6; ++i) {
        double a = kPi + (i / 6.0) * kPi;
        pts.push_back({ 22.0 * std::cos(a), -150.0 + 22.0 * std::sin(a) });
    }
    // Right stem down
    pts.push_back({  22.0, -150.0 });
    pts.push_back({  22.0,   60.0 });
    // Lower bulb neck transition
    pts.push_back({  32.0,   75.0 });
    // Lower bulb round reservoir (semicircle + round bottom)
    for (int i = 0; i <= 10; ++i) {
        double a = -(kPi * 0.3) + (i / 10.0) * (kPi * 1.6);
        pts.push_back({ 65.0 * std::cos(a), 115.0 + 65.0 * std::sin(a) });
    }
    // Left bulb neck transition
    pts.push_back({ -32.0,   75.0 });
    // Left stem up
    pts.push_back({ -22.0,   60.0 });
    pts.push_back({ -22.0, -150.0 });
    return pts;
}

std::vector<Point2D> build_sun_shape() {
    // 32 vertices defining radiating starburst / sun core
    std::vector<Point2D> pts;
    int num_rays = 16;
    for (int i = 0; i < num_rays * 2; ++i) {
        double a = (i / (double)(num_rays * 2)) * 2.0 * kPi;
        double r = (i % 2 == 0) ? 175.0 : 105.0;
        pts.push_back({ r * std::cos(a), r * std::sin(a) });
    }
    return pts;
}

std::vector<Point2D> build_rocket_shape() {
    // 22 vertices defining aerodynamic space rocket
    return {
        {   0.0, -180.0 }, // nose cone tip
        {  25.0, -110.0 }, {  38.0,  -40.0 }, {  42.0,   40.0 }, {  42.0,  100.0 }, // right fuselage
        {  85.0,  140.0 }, { 105.0,  160.0 }, {  75.0,  155.0 }, {  42.0,  135.0 }, // right delta fin
        {  25.0,  145.0 }, {  18.0,  165.0 }, { -18.0,  165.0 }, { -25.0,  145.0 }, // rocket engine nozzle
        { -42.0,  135.0 }, { -75.0,  155.0 }, { -105.0, 160.0 }, { -85.0,  140.0 }, // left delta fin
        { -42.0,  100.0 }, { -42.0,   40.0 }, { -38.0,  -40.0 }, { -25.0, -110.0 }  // left fuselage
    };
}

int main() {
    std::cout << "=== 2.5D Topological Morphing Blend2D Renderer (60 FPS) ===\n";

    std::string base_dir = "C:/Users/pater/Pyt/ChrononTemplate/";
    std::string frames_dir = base_dir + "out/svg_parity/topological_morph_frames/";
    std::string out_mp4 = base_dir + "out/svg_parity/topological_morph_showcase.mp4";

    fs::create_directories(frames_dir);

    // Build raw paths
    ArcLengthPath p_van, p_thermo, p_sun, p_rocket;
    p_van.build_from_points(build_van_shape(), true);
    p_thermo.build_from_points(build_thermometer_shape(), true);
    p_sun.build_from_points(build_sun_shape(), true);
    p_rocket.build_from_points(build_rocket_shape(), true);

    const size_t kNodes = 256;
    TopologicalPathMorpher morpher1; // Van -> Thermo
    morpher1.initialize(p_van, p_thermo, kNodes);

    TopologicalPathMorpher morpher2; // Thermo -> Sun
    morpher2.initialize(p_thermo, p_sun, kNodes);

    TopologicalPathMorpher morpher3; // Sun -> Rocket
    morpher3.initialize(p_sun, p_rocket, kNodes);

    std::cout << "Morpher 1 (Van->Thermo): E=" << morpher1.get_metrics().min_energy 
              << ", shift=" << morpher1.get_metrics().optimal_shift << "\n";
    std::cout << "Morpher 2 (Thermo->Sun): E=" << morpher2.get_metrics().min_energy 
              << ", shift=" << morpher2.get_metrics().optimal_shift << "\n";
    std::cout << "Morpher 3 (Sun->Rocket): E=" << morpher3.get_metrics().min_energy 
              << ", shift=" << morpher3.get_metrics().optimal_shift << "\n";

    const int kWidth = 1920;
    const int kHeight = 1080;
    const int kTotalFrames = 450; // 7.5 seconds @ 60fps
    const double kFps = 60.0;

    BLImage frame_img(kWidth, kHeight, BL_FORMAT_PRGB32);
    BLContext ctx(frame_img);

    std::cout << "Rendering 450 frames (7.5s @ 60fps)...\n";

    for (int frame = 0; frame < kTotalFrames; ++frame) {
        double t = frame / kFps; // time in seconds

        // Determine current morph stage & tau
        std::vector<Point2D> current_pts;
        std::vector<Point2D> source_pts, target_pts;
        BLRgba32 cur_color;
        std::string stage_title;
        double stage_tau = 0.0;
        double current_energy = 0.0;
        int current_shift = 0;
        double rocket_y_offset = 0.0;

        if (t < 0.5) {
            // Stage 0: Intro hold on Van
            current_pts = morpher1.get_pts_a();
            cur_color = BLRgba32(0, 240, 255); // Cyan
            stage_title = "STAGE 1: DELIVERY VAN [ORIGINAL SHAPE]";
            stage_tau = 0.0;
            current_energy = 0.0;
            current_shift = morpher1.get_metrics().optimal_shift;
        } else if (t < 2.0) {
            // Morph 1: Van -> Thermometer
            stage_tau = smoothstep(0.5, 2.0, t);
            current_pts = morpher1.evaluate_morph(stage_tau);
            source_pts = morpher1.get_pts_a();
            target_pts = morpher1.get_pts_b_aligned();
            cur_color = lerp_color(BLRgba32(0, 240, 255), BLRgba32(255, 77, 109), stage_tau);
            stage_title = "TOPOLOGICAL MORPH: VAN -> CLINICAL THERMOMETER";
            current_energy = morpher1.get_metrics().min_energy;
            current_shift = morpher1.get_metrics().optimal_shift;
        } else if (t < 2.6) {
            // Hold on Thermometer
            current_pts = morpher1.get_pts_b_aligned();
            cur_color = BLRgba32(255, 77, 109); // Coral Red
            stage_title = "STAGE 2: CLINICAL THERMOMETER [TARGET ALIGNED]";
            stage_tau = 1.0;
            current_energy = 0.0;
            current_shift = morpher2.get_metrics().optimal_shift;
        } else if (t < 4.1) {
            // Morph 2: Thermometer -> Sun
            stage_tau = smoothstep(2.6, 4.1, t);
            current_pts = morpher2.evaluate_morph(stage_tau);
            source_pts = morpher2.get_pts_a();
            target_pts = morpher2.get_pts_b_aligned();
            cur_color = lerp_color(BLRgba32(255, 77, 109), BLRgba32(255, 183, 3), stage_tau);
            stage_title = "TOPOLOGICAL MORPH: THERMOMETER -> RADIATING SUN";
            current_energy = morpher2.get_metrics().min_energy;
            current_shift = morpher2.get_metrics().optimal_shift;
        } else if (t < 4.7) {
            // Hold on Sun (pulsing breathing)
            current_pts = morpher2.get_pts_b_aligned();
            double pulse = 1.0 + 0.04 * std::sin(t * 8.0);
            for (auto& p : current_pts) { p.x *= pulse; p.y *= pulse; }
            cur_color = BLRgba32(255, 183, 3); // Golden Solar
            stage_title = "STAGE 3: RADIATING SUN [SOLAR FLUX]";
            stage_tau = 1.0;
            current_energy = 0.0;
            current_shift = morpher3.get_metrics().optimal_shift;
        } else if (t < 6.2) {
            // Morph 3: Sun -> Rocket
            stage_tau = smoothstep(4.7, 6.2, t);
            current_pts = morpher3.evaluate_morph(stage_tau);
            source_pts = morpher3.get_pts_a();
            target_pts = morpher3.get_pts_b_aligned();
            cur_color = lerp_color(BLRgba32(255, 183, 3), BLRgba32(165, 80, 255), stage_tau);
            stage_title = "TOPOLOGICAL MORPH: SUN -> SPACE ROCKET";
            current_energy = morpher3.get_metrics().min_energy;
            current_shift = morpher3.get_metrics().optimal_shift;
        } else {
            // Rocket Launch Finale
            current_pts = morpher3.get_pts_b_aligned();
            cur_color = BLRgba32(165, 80, 255); // Electric Violet
            double launch_t = (t - 6.2) / 1.3;
            rocket_y_offset = -launch_t * launch_t * 850.0;
            stage_title = "STAGE 4: SPACE ROCKET [THRUSTER ASCENT]";
            stage_tau = 1.0;
            current_energy = 0.0;
            current_shift = morpher3.get_metrics().optimal_shift;
        }

        // Clear Background (Deep Slate Cinematic Navy #020408)
        ctx.clearAll();
        ctx.setFillStyle(BLRgba32(2, 4, 8, 255));
        ctx.fillAll();

        // 1. Technical Grid & Circular Reticle
        ctx.setStrokeWidth(1.0);
        ctx.setStrokeStyle(BLRgba32(25, 45, 75, 40));
        for (double gx = 160.0; gx <= 1760.0; gx += 160.0) {
            ctx.strokeLine(gx, 80.0, gx, 1000.0);
        }
        for (double gy = 120.0; gy <= 960.0; gy += 120.0) {
            ctx.strokeLine(80.0, gy, 1840.0, gy);
        }

        // Center reticle rings
        double cx = 960.0;
        double cy = 540.0 + rocket_y_offset;

        ctx.setStrokeStyle(BLRgba32(0, 240, 255, 30));
        ctx.strokeCircle(960.0, 540.0, 280.0);
        ctx.strokeCircle(960.0, 540.0, 320.0);
        ctx.strokeLine(960.0 - 340.0, 540.0, 960.0 + 340.0, 540.0);
        ctx.strokeLine(960.0, 540.0 - 340.0, 960.0, 540.0 + 340.0);

        // 2. Draw Vector Lattice Lines during Morph Transitions
        if (!source_pts.empty() && !target_pts.empty() && stage_tau > 0.02 && stage_tau < 0.98) {
            double lattice_alpha = std::sin(stage_tau * kPi) * 85.0;
            ctx.setStrokeWidth(1.0);
            ctx.setStrokeStyle(BLRgba32(cur_color.r(), cur_color.g(), cur_color.b(), (uint32_t)lattice_alpha));
            // Draw connection rays between source and target every 4th vertex
            for (size_t i = 0; i < source_pts.size(); i += 4) {
                ctx.strokeLine(cx + source_pts[i].x, cy + source_pts[i].y,
                               cx + target_pts[i].x, cy + target_pts[i].y);
            }
        }

        // 3. Rocket Thruster Particle Trail (Finale)
        if (t > 6.2) {
            for (int k = 1; k <= 20; ++k) {
                double pk_y = cy + 170.0 + k * 18.0;
                double pk_x = cx + ((k * 17) % 21 - 10) * 1.5;
                double pk_r = (22.0 - k) * 0.9;
                uint32_t pk_a = (uint32_t)((1.0 - k / 21.0) * 220);
                ctx.setFillStyle(BLRgba32(255, 140 + k * 5, 20, pk_a));
                ctx.fillCircle(pk_x, pk_y, pk_r);
            }
        }

        // 4. Build Shape Path from Current Points
        BLPath shape_path;
        if (!current_pts.empty()) {
            shape_path.moveTo(cx + current_pts[0].x, cy + current_pts[0].y);
            for (size_t i = 1; i < current_pts.size(); ++i) {
                shape_path.lineTo(cx + current_pts[i].x, cy + current_pts[i].y);
            }
            shape_path.close();
        }

        // 5. Draw Shape: Semi-Translucent Inner Fill (SDF look)
        ctx.setFillStyle(BLRgba32(cur_color.r() / 4, cur_color.g() / 4, cur_color.b() / 4, 40));
        ctx.fillPath(shape_path);

        // 6. Multi-Pass Exponential Neon Bloom Passes
        // Pass 1: Wide Soft Outer Halo
        ctx.setStrokeWidth(30.0);
        ctx.setStrokeStyle(BLRgba32(cur_color.r(), cur_color.g(), cur_color.b(), 18));
        ctx.strokePath(shape_path);

        // Pass 2: Mid-range Glow
        ctx.setStrokeWidth(16.0);
        ctx.setStrokeStyle(BLRgba32(cur_color.r(), cur_color.g(), cur_color.b(), 45));
        ctx.strokePath(shape_path);

        // Pass 3: Tight Saturated Rim
        ctx.setStrokeWidth(7.0);
        ctx.setStrokeStyle(BLRgba32(cur_color.r(), cur_color.g(), cur_color.b(), 130));
        ctx.strokePath(shape_path);

        // Pass 4: Blazing Bright Core Line
        ctx.setStrokeWidth(2.2);
        ctx.setStrokeStyle(BLRgba32(245, 250, 255, 255));
        ctx.strokePath(shape_path);

        // 7. Vertex Nodes (Highlight every 8th vertex to showcase uniform arc-length spacing)
        for (size_t i = 0; i < current_pts.size(); i += 8) {
            double vx = cx + current_pts[i].x;
            double vy = cy + current_pts[i].y;
            ctx.setFillStyle(BLRgba32(cur_color.r(), cur_color.g(), cur_color.b(), 180));
            ctx.fillCircle(vx, vy, 4.0);
            ctx.setFillStyle(BLRgba32(255, 255, 255, 255));
            ctx.fillCircle(vx, vy, 1.8);
        }

        // 8. Technical HUD Overlay & Telemetry
        ctx.setStrokeWidth(1.5);
        ctx.setStrokeStyle(BLRgba32(0, 240, 255, 140));
        // Top Left Frame Bracket
        ctx.strokeLine(60.0, 60.0, 180.0, 60.0);
        ctx.strokeLine(60.0, 60.0, 60.0, 120.0);
        // Bottom Right Frame Bracket
        ctx.strokeLine(1860.0, 1020.0, 1740.0, 1020.0);
        ctx.strokeLine(1860.0, 1020.0, 1860.0, 960.0);

        // Progress Bar at Bottom
        double bar_w = 600.0;
        double bar_x = (kWidth - bar_w) * 0.5;
        double bar_y = 1010.0;
        ctx.setStrokeStyle(BLRgba32(40, 70, 100, 120));
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
    std::cout << "[DONE] Rendered all 450 frames to " << frames_dir << "\n";
    return 0;
}
