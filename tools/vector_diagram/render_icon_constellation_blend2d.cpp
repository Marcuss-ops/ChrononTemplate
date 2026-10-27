// render_icon_constellation_blend2d.cpp
// Renders the 60fps 2.5D Tech & Space Icon Constellation animation:
// - Fixed transparent icons (zero white quads)
// - Additive blending (BL_COMP_OP_PLUS) for neon blooms
// - Refined satellite orbit hierarchy around the globe
// - Bayer Matrix Dithering to eliminate 8-bit banding rings

#include <blend2d.h>
#include <iostream>
#include <vector>
#include <string>
#include <cmath>
#include <filesystem>
#include <sstream>
#include <iomanip>
#include <algorithm>
#include <map>

namespace fs = std::filesystem;
constexpr double kPi = 3.14159265358979323846;

struct Vec3 {
    double x, y, z;
};

struct Vec2 {
    double x, y;
};

inline double clamp01(double v) {
    return (v < 0.0) ? 0.0 : (v > 1.0 ? 1.0 : v);
}

inline double smoothstep(double edge0, double edge1, double x) {
    double t = clamp01((x - edge0) / (edge1 - edge0));
    return t * t * (3.0 - 2.0 * t);
}

inline double spring_overshoot(double t) {
    if (t <= 0.0) return 0.0;
    if (t >= 1.0) return 1.0;
    double decay = std::exp(-5.0 * t);
    return 1.0 - decay * std::cos(7.0 * t);
}

struct Camera25D {
    Vec3 pos;
    double focal_length = 800.0;

    bool project(const Vec3& world, Vec2& screen, double& scale) const {
        double d = world.z - pos.z;
        if (d < 40.0) return false;
        scale = focal_length / d;
        screen.x = 960.0 + (world.x - pos.x) * scale;
        screen.y = 540.0 + (world.y - pos.y) * scale;
        return true;
    }
};

struct IconNode {
    std::string id;
    std::string icon_name;
    Vec3 base_pos;
    double base_scale;
    double start_time;
    BLRgba32 theme_color;
};

// Bayer Matrix Dithering to prevent color banding
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
    std::cout << "=== 2.5D Icon Constellation Blend2D Renderer (Visual Parity) ===\n";

    std::string base_dir = "C:/Users/pater/Pyt/ChrononTemplate/";
    std::string neon_png_dir = base_dir + "assets/icons/png_neon/";
    std::string white_png_dir = base_dir + "assets/icons/png_white/";
    std::string frames_dir = base_dir + "out/svg_parity/icon_constellation_frames/";
    std::string out_mp4 = base_dir + "out/svg_parity/icon_constellation_25d.mp4";

    fs::create_directories(frames_dir);

    std::vector<std::string> icon_names = {
        "cpu", "brain", "vulkan", "cplusplus", "database", 
        "shield", "globe", "satellite", "rocket", "atom", 
        "dna", "zap", "radar", "sparkles", "telescope"
    };

    std::map<std::string, BLImage> neon_images;
    std::map<std::string, BLImage> white_images;

    for (const auto& name : icon_names) {
        std::string n_path = neon_png_dir + name + "_neon.png";
        std::string w_path = white_png_dir + name + ".png";

        BLImage img_neon, img_white;
        if (img_neon.readFromFile(n_path.c_str()) == BL_SUCCESS) {
            neon_images[name] = std::move(img_neon);
        }
        if (img_white.readFromFile(w_path.c_str()) == BL_SUCCESS) {
            white_images[name] = std::move(img_white);
        }
    }
    std::cout << "Loaded " << neon_images.size() << " neon icon textures.\n";

    const int kWidth = 1920;
    const int kHeight = 1080;
    const int kTotalFrames = 360; // 6 seconds @ 60fps
    const double kFps = 60.0;

    BLImage frame_img(kWidth, kHeight, BL_FORMAT_PRGB32);
    BLContext ctx(frame_img);

    // Nodes Layout in 2.5D Space
    std::vector<IconNode> nodes = {
        { "cpu",       "cpu",       {  960.0, 540.0,   0.0 }, 0.38, 0.0, BLRgba32(0, 240, 255) },
        { "vulkan",    "vulkan",    {  680.0, 360.0,  90.0 }, 0.28, 0.4, BLRgba32(230, 30, 30) },
        { "cpp",       "cplusplus", { 1240.0, 360.0,  90.0 }, 0.28, 0.5, BLRgba32(0, 120, 240) },
        { "db",        "database",  {  680.0, 720.0,  70.0 }, 0.28, 0.6, BLRgba32(180, 40, 210) },
        { "shield",    "shield",    { 1240.0, 720.0,  70.0 }, 0.28, 0.7, BLRgba32(0, 255, 140) },
        { "globe",     "globe",     { 1520.0, 500.0, 240.0 }, 0.34, 1.2, BLRgba32(255, 185, 10) },
        { "atom",      "atom",      {  420.0, 780.0, 180.0 }, 0.26, 1.4, BLRgba32(0, 240, 255) },
        { "dna",       "dna",       { 1500.0, 800.0, 160.0 }, 0.26, 1.6, BLRgba32(255, 0, 130) },
        { "zap",       "zap",       {  960.0, 230.0, 120.0 }, 0.28, 0.9, BLRgba32(255, 230, 0) },
        { "telescope", "telescope", {  400.0, 300.0, 280.0 }, 0.26, 1.8, BLRgba32(255, 180, 20) },
        { "sparkles",  "sparkles",  {  960.0, 840.0, 140.0 }, 0.25, 1.5, BLRgba32(255, 215, 0) }
    };

    std::cout << "Rendering 360 frames (6.0s @ 60fps)...\n";

    for (int frame = 0; frame < kTotalFrames; ++frame) {
        double t = frame / kFps;

        // 1. Camera Animation: Dolly Out
        Camera25D camera;
        double dolly_t = smoothstep(1.8, 4.6, t);
        camera.pos.x = 960.0 + dolly_t * 60.0;
        camera.pos.y = 540.0 - dolly_t * 30.0;
        camera.pos.z = -420.0 - dolly_t * 540.0;
        camera.focal_length = 800.0;

        // Clear Background (Deep Space Navy #03050B)
        ctx.clearAll();
        ctx.setFillStyle(BLRgba32(3, 5, 11, 255));
        ctx.fillAll();

        // 2. 2.5D Background Grid Planes
        ctx.setStrokeWidth(1.0);
        ctx.setStrokeStyle(BLRgba32(35, 65, 105, 40));
        for (double gz : { 100.0, 300.0 }) {
            for (double gx = 200.0; gx <= 1800.0; gx += 200.0) {
                Vec2 p1, p2; double s1, s2;
                if (camera.project({ gx, 100.0, gz }, p1, s1) && camera.project({ gx, 980.0, gz }, p2, s2)) {
                    ctx.strokeLine(p1.x, p1.y, p2.x, p2.y);
                }
            }
            for (double gy = 200.0; gy <= 900.0; gy += 150.0) {
                Vec2 p1, p2; double s1, s2;
                if (camera.project({ 200.0, gy, gz }, p1, s1) && camera.project({ 1800.0, gy, gz }, p2, s2)) {
                    ctx.strokeLine(p1.x, p1.y, p2.x, p2.y);
                }
            }
        }

        // 3. Dynamic Node Positions
        Vec3 core_world = nodes[0].base_pos;
        core_world.y += std::sin(t * 3.0) * 8.0;

        // Orbiting Satellite: Hugs the globe closely (horizontal radius: 110, vertical: 50)
        Vec3 globe_world = nodes[5].base_pos;
        double orb_angle = t * 1.5;
        Vec3 sat_world = {
            globe_world.x + 110.0 * std::cos(orb_angle),
            globe_world.y +  50.0 * std::sin(orb_angle),
            globe_world.z -  65.0 * std::sin(orb_angle)
        };

        // Rocket Trajectory (Launching from pad to deep space)
        double rkt_t = smoothstep(1.5, 5.8, t);
        Vec3 p0 = { 520.0, 740.0, 80.0 };
        Vec3 p1 = { 460.0, 480.0, 160.0 };
        Vec3 p2 = { 380.0, 300.0, 280.0 };
        Vec3 p3 = { 260.0, 120.0, 420.0 };

        double u = rkt_t; double u2 = u * u; double u3 = u2 * u;
        double om = 1.0 - u; double om2 = om * om; double om3 = om2 * om;

        Vec3 rocket_world = {
            om3 * p0.x + 3.0 * om2 * u * p1.x + 3.0 * om * u2 * p2.x + u3 * p3.x,
            om3 * p0.y + 3.0 * om2 * u * p1.y + 3.0 * om * u2 * p2.y + u3 * p3.y,
            om3 * p0.z + 3.0 * om2 * u * p1.z + 3.0 * om * u2 * p2.z + u3 * p3.z
        };

        Vec3 rocket_tangent = {
            3.0 * om2 * (p1.x - p0.x) + 6.0 * om * u * (p2.x - p1.x) + 3.0 * u2 * (p3.x - p2.x),
            3.0 * om2 * (p1.y - p0.y) + 6.0 * om * u * (p2.y - p1.y) + 3.0 * u2 * (p3.y - p2.y),
            3.0 * om2 * (p1.z - p0.z) + 6.0 * om * u * (p2.z - p1.z) + 3.0 * u2 * (p3.z - p2.z)
        };
        double rocket_angle = std::atan2(rocket_tangent.y, rocket_tangent.x) + kPi * 0.5;

        // 4. Draw Connecting Laser Axons
        Vec2 core_scr; double core_s;
        if (camera.project(core_world, core_scr, core_s)) {
            for (size_t i = 1; i <= 4; ++i) {
                Vec2 node_scr; double node_s;
                if (camera.project(nodes[i].base_pos, node_scr, node_s)) {
                    double trim_progress = smoothstep(nodes[i].start_time, nodes[i].start_time + 0.6, t);
                    if (trim_progress > 0.01) {
                        double ex = core_scr.x + (node_scr.x - core_scr.x) * trim_progress;
                        double ey = core_scr.y + (node_scr.y - core_scr.y) * trim_progress;

                        ctx.save();
                        ctx.setCompOp(BL_COMP_OP_PLUS);
                        ctx.setStrokeWidth(3.5 * core_s);
                        ctx.setStrokeStyle(BLRgba32(0, 200, 255, (uint32_t)(85 * trim_progress)));
                        ctx.strokeLine(core_scr.x, core_scr.y, ex, ey);
                        ctx.restore();

                        ctx.setStrokeWidth(1.2 * core_s);
                        ctx.setStrokeStyle(BLRgba32(230, 250, 255, (uint32_t)(220 * trim_progress)));
                        ctx.strokeLine(core_scr.x, core_scr.y, ex, ey);

                        double pulse_u = std::fmod(t * 1.8 + i * 0.25, 1.0);
                        double px = core_scr.x + (node_scr.x - core_scr.x) * pulse_u;
                        double py = core_scr.y + (node_scr.y - core_scr.y) * pulse_u;

                        ctx.save();
                        ctx.setCompOp(BL_COMP_OP_PLUS);
                        ctx.setFillStyle(BLRgba32(0, 255, 255, 180));
                        ctx.fillCircle(px, py, 6.0 * core_s);
                        ctx.restore();

                        ctx.setFillStyle(BLRgba32(255, 255, 255, 255));
                        ctx.fillCircle(px, py, 2.2 * core_s);
                    }
                }
            }

            // Draw Clean Satellite Orbit Track around Globe
            Vec2 globe_scr; double globe_s;
            if (camera.project(globe_world, globe_scr, globe_s)) {
                BLPath orbit_path;
                for (int a = 0; a <= 60; ++a) {
                    double ang = (a / 60.0) * 2.0 * kPi;
                    Vec3 pt = {
                        globe_world.x + 110.0 * std::cos(ang),
                        globe_world.y +  50.0 * std::sin(ang),
                        globe_world.z -  65.0 * std::sin(ang)
                    };
                    Vec2 scr; double sc;
                    if (camera.project(pt, scr, sc)) {
                        if (a == 0) orbit_path.moveTo(scr.x, scr.y);
                        else orbit_path.lineTo(scr.x, scr.y);
                    }
                }
                ctx.setStrokeWidth(1.5 * globe_s);
                ctx.setStrokeStyle(BLRgba32(255, 185, 10, 85));
                ctx.strokePath(orbit_path);
            }

            // Radar waves from satellite
            Vec2 sat_scr; double sat_s;
            if (camera.project(sat_world, sat_scr, sat_s)) {
                for (int w = 0; w < 3; ++w) {
                    double wave_t = std::fmod(t * 1.6 + w * 0.33, 1.0);
                    double radius = wave_t * 55.0 * sat_s;
                    uint32_t alpha = (uint32_t)((1.0 - wave_t) * 150);
                    ctx.save();
                    ctx.setCompOp(BL_COMP_OP_PLUS);
                    ctx.setStrokeWidth(1.4 * sat_s);
                    ctx.setStrokeStyle(BLRgba32(0, 240, 255, alpha));
                    ctx.strokeCircle(sat_scr.x, sat_scr.y, radius);
                    ctx.restore();
                }
            }

            // Rocket Exhaust Particle Trail
            if (t > 1.5) {
                for (int k = 1; k <= 12; ++k) {
                    double past_t = std::max(1.5, t - k * 0.04);
                    double past_u = smoothstep(1.5, 5.8, past_t);
                    double past_om = 1.0 - past_u;
                    Vec3 trail_pt = {
                        past_om*past_om*past_om*p0.x + 3.0*past_om*past_om*past_u*p1.x + 3.0*past_om*past_u*past_u*p2.x + past_u*past_u*past_u*p3.x,
                        past_om*past_om*past_om*p0.y + 3.0*past_om*past_om*past_u*p1.y + 3.0*past_om*past_u*past_u*p2.y + past_u*past_u*past_u*p3.y,
                        past_om*past_om*past_om*p0.z + 3.0*past_om*past_om*past_u*p1.z + 3.0*past_om*past_u*past_u*p2.z + past_u*past_u*past_u*p3.z
                    };
                    Vec2 scr; double sc;
                    if (camera.project(trail_pt, scr, sc)) {
                        double trail_alpha = (1.0 - k / 13.0) * 200;
                        double trail_r = (1.0 + k * 0.5) * sc * 3.0;
                        ctx.save();
                        ctx.setCompOp(BL_COMP_OP_PLUS);
                        ctx.setFillStyle(BLRgba32(255, 120 + k * 8, 20, (uint32_t)trail_alpha));
                        ctx.fillCircle(scr.x, scr.y, trail_r);
                        ctx.restore();
                    }
                }
            }

            // Concentric Rotating HUD Rings around Central CPU
            ctx.setStrokeWidth(1.8 * core_s);
            ctx.setStrokeStyle(BLRgba32(0, 240, 255, 130));
            BLPath hud_arc1;
            hud_arc1.addArc(BLArc(core_scr.x, core_scr.y, 110.0 * core_s, 110.0 * core_s, t * 1.2, kPi * 1.1));
            ctx.strokePath(hud_arc1);

            BLPath hud_arc2;
            hud_arc2.addArc(BLArc(core_scr.x, core_scr.y, 130.0 * core_s, 130.0 * core_s, -t * 0.8, kPi * 0.9));
            ctx.setStrokeStyle(BLRgba32(0, 180, 255, 100));
            ctx.strokePath(hud_arc2);
        }

        // 5. Render Icons in Depth-Sorted Order (Back to Front)
        struct RenderItem {
            std::string name;
            Vec3 world;
            double scale_mult;
            double rotation;
            double start_t;
        };

        std::vector<RenderItem> items;
        for (const auto& n : nodes) {
            Vec3 w = n.base_pos;
            if (n.id == "cpu") w = core_world;
            items.push_back({ n.icon_name, w, n.base_scale, 0.0, n.start_time });
        }
        items.push_back({ "satellite", sat_world, 0.28, orb_angle, 1.2 });
        if (t > 1.2) {
            items.push_back({ "rocket", rocket_world, 0.32, rocket_angle, 1.5 });
        }

        std::sort(items.begin(), items.end(), [](const RenderItem& a, const RenderItem& b) {
            return a.world.z > b.world.z;
        });

        for (const auto& item : items) {
            Vec2 scr; double sc;
            if (!camera.project(item.world, scr, sc)) continue;

            double intro_t = clamp01((t - item.start_t) / 0.6);
            if (intro_t <= 0.0) continue;

            double spring_s = spring_overshoot(intro_t);
            double total_s = item.scale_mult * sc * spring_s;

            BLMatrix2D m = BLMatrix2D::makeTranslation(scr.x, scr.y);
            m.rotate(item.rotation);
            m.scale(total_s, total_s);
            m.translate(-256.0, -256.0); // 512x512 texture center

            // A. Blit Neon Bloom Texture with ADDITIVE BLENDING (BL_COMP_OP_PLUS)
            if (neon_images.count(item.name)) {
                ctx.save();
                ctx.setTransform(m);
                ctx.setCompOp(BL_COMP_OP_PLUS);
                ctx.setGlobalAlpha(intro_t);
                ctx.blitImage(BLPoint(0, 0), neon_images[item.name]);
                ctx.restore();
            }

            // B. Blit Crisp Core Texture in SRC_OVER
            if (white_images.count(item.name)) {
                ctx.save();
                ctx.setTransform(m);
                ctx.setCompOp(BL_COMP_OP_SRC_OVER);
                ctx.setGlobalAlpha(intro_t * 0.95);
                ctx.blitImage(BLPoint(0, 0), white_images[item.name]);
                ctx.restore();
            }
        }

        // 6. Subtle Analog Film Dust
        for (int d = 0; d < 60; ++d) {
            uint32_t seed = (uint32_t)(d * 1973 + frame * 9271);
            seed = (seed ^ 61) ^ (seed >> 16);
            seed *= 9;
            seed = seed ^ (seed >> 4);
            seed *= 0x27d4eb2d;
            seed = seed ^ (seed >> 15);

            double dx = (seed % kWidth);
            double dy = ((seed / kWidth) % kHeight);
            double d_alpha = ((seed >> 8) % 40) / 255.0;

            ctx.setFillStyle(BLRgba32(230, 240, 255, (uint32_t)(d_alpha * 255)));
            ctx.fillCircle(dx, dy, (seed % 3 == 0) ? 1.2 : 0.8);
        }

        // 7. Apply Bayer Dithering to eliminate 8-bit color banding
        applyBayerDithering(frame_img);

        // Save Frame
        std::ostringstream fn;
        fn << frames_dir << "frame_" << std::setfill('0') << std::setw(4) << frame << ".png";
        frame_img.writeToFile(fn.str().c_str());

        if (frame % 60 == 0 || frame == kTotalFrames - 1) {
            std::cout << "  Rendered frame " << frame << " / " << kTotalFrames 
                      << " (" << (int)((frame / (double)kTotalFrames) * 100) << "%)\n";
        }
    }

    ctx.end();
    std::cout << "[DONE] Rendered all 360 frames to " << frames_dir << "\n";
    return 0;
}
