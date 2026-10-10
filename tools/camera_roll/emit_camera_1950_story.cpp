// ChrononTemplate — Native C++ 1950 Camera Story Generator & Renderer.
//
// 100% C++ implementation (no Python):
// 1. Procedural generation of luxury editorial backdrop & luminous wavy dashed line PNG assets via stb_image_write.
// 2. Integration of authentic historical documentary photo card.
// 3. Modern short-phrase typography using Bricolage-Grotesque.ttf and Space-Grotesk.ttf with glow.
// 4. Mathematical dead-center alignment: camera and 1950 title locked at optical center.
// 5. Compilation of exact 1920x1080 chronon.render-plan.v3 with CameraRig PushZoom & ArcCarry tracks.
// 6. Direct execution of Chronon3D CLI for hardware-accelerated Vulkan rendering.

#define STB_IMAGE_WRITE_IMPLEMENTATION
#include <stb_image_write.h>

#include <nlohmann/json.hpp>

#include "chrononmotion/math/Vector2.hpp"
#include "chrononmotion/math/Vector3.hpp"

#include <algorithm>
#include <cmath>
#include <cstdlib>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <string>
#include <vector>

namespace fs = std::filesystem;
using json = nlohmann::json;

namespace {

    constexpr int kWidth = 1920;
    constexpr int kHeight = 1080;
    constexpr int kFps = 30;
    constexpr int kTotalFrames = 210; // 7.0 seconds

    double easeInOutCubic(double t) {
        return t < 0.5 ? 4.0 * t * t * t : 1.0 - std::pow(-2.0 * t + 2.0, 3) / 2.0;
    }

    void generateBackdrop(const fs::path& outPath) {
        const int w = kWidth;
        const int h = kHeight;
        std::vector<uint8_t> pixels(w * h * 4, 255);

        const double cx = w / 2.0;
        const double cy = h / 2.0;
        const double maxRadius = std::hypot(cx, cy);

        for (int y = 0; y < h; ++y) {
            for (int x = 0; x < w; ++x) {
                double dist = std::hypot(x - cx, y - cy);
                double t = std::clamp(dist / maxRadius, 0.0, 1.0);

                // Subtle smooth cubic vignette falloff
                double vignette = t * t * (3.0 - 2.0 * t);

                // Center: deep rich navy-slate (24, 30, 42) -> Edge: deep obsidian ink (7, 9, 14)
                uint8_t r = static_cast<uint8_t>(std::clamp(24.0 * (1.0 - vignette) + 7.0 * vignette, 0.0, 255.0));
                uint8_t g = static_cast<uint8_t>(std::clamp(30.0 * (1.0 - vignette) + 9.0 * vignette, 0.0, 255.0));
                uint8_t b = static_cast<uint8_t>(std::clamp(42.0 * (1.0 - vignette) + 14.0 * vignette, 0.0, 255.0));

                // 1-bit fine dither to prevent 8-bit banding
                int dither = ((x ^ y) & 1) ? 1 : -1;
                r = static_cast<uint8_t>(std::clamp<int>(r + dither, 0, 255));
                g = static_cast<uint8_t>(std::clamp<int>(g + dither, 0, 255));
                b = static_cast<uint8_t>(std::clamp<int>(b + dither, 0, 255));

                size_t idx = (y * w + x) * 4;
                pixels[idx + 0] = r;
                pixels[idx + 1] = g;
                pixels[idx + 2] = b;
                pixels[idx + 3] = 255;
            }
        }

        fs::create_directories(outPath.parent_path());
        stbi_write_png(outPath.string().c_str(), w, h, 4, pixels.data(), w * 4);
        std::cout << "[C++] Generated luxury editorial backdrop: " << outPath << "\n";
    }

    void prepareVintagePhoto(const fs::path& workspaceRoot, const fs::path& outPath) {
        fs::create_directories(outPath.parent_path());

        fs::path srcPhoto = workspaceRoot / "ChrononTemplate/catalog/vintage_documentary_map_italy/assets/photo_card_torrazzo.png";
        if (fs::exists(srcPhoto)) {
            std::error_code ec;
            fs::copy_file(srcPhoto, outPath, fs::copy_options::overwrite_existing, ec);
            if (!ec) {
                std::cout << "[C++] Installed authentic archival vintage photo card: " << outPath << "\n";
                return;
            }
        }

        // High-contrast archival fallback card
        const int w = 680;
        const int h = 880;
        const int border = 32;
        std::vector<uint8_t> pixels(w * h * 4, 0);

        auto setPixel = [&](int x, int y, uint8_t r, uint8_t g, uint8_t b, uint8_t a = 255) {
            if (x < 0 || x >= w || y < 0 || y >= h) return;
            size_t idx = (y * w + x) * 4;
            pixels[idx + 0] = r;
            pixels[idx + 1] = g;
            pixels[idx + 2] = b;
            pixels[idx + 3] = a;
        };

        // 1. Warm archival cardboard frame
        for (int y = 0; y < h; ++y) {
            for (int x = 0; x < w; ++x) {
                int dx = std::min(x, w - 1 - x);
                int dy = std::min(y, h - 1 - y);
                if (dx < 12 && dy < 12 && (12 - dx) * (12 - dx) + (12 - dy) * (12 - dy) > 144) continue;
                setPixel(x, y, 246, 243, 236, 255);
            }
        }

        // Inner photo frame
        const int px0 = border;
        const int py0 = border;
        const int px1 = w - border;
        const int py1 = h - border - 36;

        for (int y = py0; y < py1; ++y) {
            double ratio = static_cast<double>(y - py0) / (py1 - py0);
            uint8_t r = static_cast<uint8_t>(32 + ratio * 58);
            uint8_t g = static_cast<uint8_t>(28 + ratio * 48);
            uint8_t b = static_cast<uint8_t>(24 + ratio * 38);
            for (int x = px0; x < px1; ++x) {
                setPixel(x, y, r, g, b, 255);
            }
        }

        stbi_write_png(outPath.string().c_str(), w, h, 4, pixels.data(), w * 4);
        std::cout << "[C++] Generated procedural vintage photo card: " << outPath << "\n";
    }

    void generateWavyDashedLine(const fs::path& outPath) {
        const int w = kWidth;
        const int h = kHeight;
        std::vector<uint8_t> pixels(w * h * 4, 0);

        auto blendPixel = [&](int x, int y, uint8_t r, uint8_t g, uint8_t b, uint8_t a) {
            if (x < 0 || x >= w || y < 0 || y >= h || a == 0) return;
            size_t idx = (y * w + x) * 4;
            float srcA = a / 255.0f;
            float dstA = pixels[idx + 3] / 255.0f;
            float outA = srcA + dstA * (1.0f - srcA);
            if (outA > 0.0001f) {
                pixels[idx + 0] = static_cast<uint8_t>((r * srcA + pixels[idx + 0] * dstA * (1.0f - srcA)) / outA);
                pixels[idx + 1] = static_cast<uint8_t>((g * srcA + pixels[idx + 1] * dstA * (1.0f - srcA)) / outA);
                pixels[idx + 2] = static_cast<uint8_t>((b * srcA + pixels[idx + 2] * dstA * (1.0f - srcA)) / outA);
                pixels[idx + 3] = static_cast<uint8_t>(outA * 255.0f);
            }
        };

        auto stampGlowingPoint = [&](double cx, double cy) {
            const int rad = 15;
            for (int dy = -rad; dy <= rad; ++dy) {
                for (int dx = -rad; dx <= rad; ++dx) {
                    double d = std::hypot(dx, dy);
                    if (d > rad) continue;

                    int px = static_cast<int>(std::round(cx + dx));
                    int py = static_cast<int>(std::round(cy + dy));

                    if (d <= 5.0) {
                        // Luminous ivory core (thickness 10-12px)
                        blendPixel(px, py, 255, 250, 220, 255);
                    } else if (d <= 9.5) {
                        // Radiant warm gold rim
                        float t = static_cast<float>((d - 5.0) / 4.5);
                        uint8_t alpha = static_cast<uint8_t>(255.0f * (1.0f - 0.25f * t));
                        blendPixel(px, py, 250, 196, 54, alpha);
                    } else {
                        // Amber halo aura
                        float t = static_cast<float>((d - 9.5) / 5.5);
                        uint8_t alpha = static_cast<uint8_t>(180.0f * (1.0f - t));
                        blendPixel(px, py, 238, 150, 32, alpha);
                    }
                }
            }
        };

        auto drawMarkerNode = [&](int cx, int cy, int outerRad, int ringRad, int innerRad) {
            // Soft halo
            for (int dy = -outerRad; dy <= outerRad; ++dy) {
                for (int dx = -outerRad; dx <= outerRad; ++dx) {
                    double d = std::hypot(dx, dy);
                    if (d <= outerRad) {
                        float a = std::clamp(1.0f - static_cast<float>(d / outerRad), 0.0f, 1.0f);
                        blendPixel(cx + dx, cy + dy, 250, 196, 54, static_cast<uint8_t>(150 * a * a));
                    }
                }
            }
            // Gold outer ring
            for (int dy = -ringRad; dy <= ringRad; ++dy) {
                for (int dx = -ringRad; dx <= ringRad; ++dx) {
                    double d = std::hypot(dx, dy);
                    if (d <= ringRad && d >= ringRad - 4.5) {
                        blendPixel(cx + dx, cy + dy, 252, 210, 80, 255);
                    }
                }
            }
            // Inner white bullseye
            for (int dy = -innerRad; dy <= innerRad; ++dy) {
                for (int dx = -innerRad; dx <= innerRad; ++dx) {
                    double d = std::hypot(dx, dy);
                    if (d <= innerRad) {
                        blendPixel(cx + dx, cy + dy, 255, 255, 255, 255);
                    }
                }
            }
        };

        // Generate serpentine wave coordinates
        const int steps = 2400;
        std::vector<std::pair<double, double>> points;
        points.reserve(steps);

        const double xStart = 280.0;
        const double xEnd = 1640.0;
        const double yBase = 540.0;
        const double amplitude = 150.0;

        for (int i = 0; i < steps; ++i) {
            double t = static_cast<double>(i) / (steps - 1);
            double x = xStart + t * (xEnd - xStart);
            double y = yBase + std::sin(t * M_PI * 2.0) * amplitude;
            points.push_back({x, y});
        }

        // Draw bold dashed segments (Dash: 48px, Gap: 24px)
        const double dashLen = 48.0;
        const double gapLen = 24.0;
        const double cycle = dashLen + gapLen;
        double accumulatedDist = 0.0;

        for (size_t i = 0; i + 1 < points.size(); ++i) {
            double x1 = points[i].first, y1 = points[i].second;
            double x2 = points[i + 1].first, y2 = points[i + 1].second;
            double segLen = std::hypot(x2 - x1, y2 - y1);
            accumulatedDist += segLen;

            double inCycle = std::fmod(accumulatedDist, cycle);
            if (inCycle < dashLen) {
                int numStamps = std::max(2, static_cast<int>(segLen * 2.0));
                for (int s = 0; s <= numStamps; ++s) {
                    double st = static_cast<double>(s) / numStamps;
                    double sx = x1 + st * (x2 - x1);
                    double sy = y1 + st * (y2 - y1);
                    stampGlowingPoint(sx, sy);
                }
            }
        }

        // Start anchor ring (xStart, yBase)
        drawMarkerNode(static_cast<int>(points.front().first), static_cast<int>(points.front().second), 32, 20, 8);

        // End target ring (xEnd, yBase)
        drawMarkerNode(static_cast<int>(points.back().first), static_cast<int>(points.back().second), 36, 24, 9);

        fs::create_directories(outPath.parent_path());
        stbi_write_png(outPath.string().c_str(), w, h, 4, pixels.data(), w * 4);
        std::cout << "[C++] Generated bold luminous wavy dashed line: " << outPath << "\n";
    }

    json buildRenderPlan(const std::string& backdropRel, const std::string& photoRel, const std::string& lineRel) {
        std::vector<double> camX(kTotalFrames), camY(kTotalFrames), camZ(kTotalFrames), camRy(kTotalFrames), camFov(kTotalFrames);

        for (int f = 0; f < kTotalFrames; ++f) {
            if (f <= 42) {
                // Phase 1: Photo enters from bottom and settles center; camera framed at rest
                camX[f] = 0.0;
                camY[f] = 0.0;
                camZ[f] = -880.0;
                camRy[f] = 0.0;
                camFov[f] = 50.0;
            } else if (f <= 78) {
                // Phase 2: Dramatic Push-Zoom into the photograph
                double t = (f - 42.0) / 36.0;
                double e = easeInOutCubic(t);
                camX[f] = 0.0;
                camY[f] = 0.0;
                camZ[f] = -880.0 + e * 360.0; // -880 -> -520
                camRy[f] = 0.0;
                camFov[f] = 50.0 - e * 8.0;    // 50 -> 42
            } else if (f <= 135) {
                // Phase 3: ArcCarry motion along the wavy dashed line (subtle parallax, perfectly framed)
                double t = (f - 78.0) / 57.0;
                double e = easeInOutCubic(t);
                double bow = std::sin(e * M_PI);
                camX[f] = -bow * 110.0;        // Gentle lateral curve following the wave
                camY[f] = -bow * 25.0;         // Gentle vertical lift
                camZ[f] = -520.0 - e * 180.0;  // -520 -> -700
                camRy[f] = bow * 3.5;          // Gentle banking counter-yaw to preserve framing
                camFov[f] = 42.0 + e * 8.0;    // 42 -> 50
            } else {
                // Phase 4: Rock-solid dead-center lock on 1950
                camX[f] = 0.0;
                camY[f] = 0.0;
                camZ[f] = -700.0;
                camRy[f] = 0.0;
                camFov[f] = 50.0;
            }
        }

        auto makeTrack = [](const std::string& prop, const std::vector<double>& vals) {
            json kfs = json::array();
            for (size_t i = 0; i < vals.size(); ++i) {
                kfs.push_back({{"frame", static_cast<int>(i)}, {"value", std::round(vals[i] * 10000.0) / 10000.0}});
            }
            return json{{"property", prop}, {"easing", "linear"}, {"keyframes", kfs}};
        };

        json cameraAnimation = {
            {"tracks", json::array({
                makeTrack("camera_position_x", camX),
                makeTrack("camera_position_y", camY),
                makeTrack("camera_position_z", camZ),
                makeTrack("camera_rotation_y", camRy),
                makeTrack("camera_fov_deg", camFov)
            })}
        };

        // 1. Luxury Editorial Backdrop (rich dark slate vignette)
        json bgLayer = {
            {"id", "bg_backdrop"},
            {"type", "image"},
            {"asset", backdropRel},
            {"size", {kWidth, kHeight}},
            {"screen_space", true},
            {"start_frame", 0},
            {"duration_frames", kTotalFrames}
        };

        // 2. Vintage Historical Photograph Card (starts below framing, settles at 3D center [0, 0, 0])
        json photoLayer = {
            {"id", "vintage_photo"},
            {"type", "image"},
            {"asset", photoRel},
            {"size", {580, 760}},
            {"position", {0, 0, 0}},
            {"fit", "contain"},
            {"start_frame", 0},
            {"duration_frames", 95},
            {"enable_3d", true},
            {"animation", {
                {"tracks", json::array({
                    {
                        {"property", "position_y"},
                        {"easing", "out_cubic"},
                        {"keyframes", json::array({
                            {{"frame", 0}, {"value", 650.0}},
                            {{"frame", 38}, {"value", 0.0}}
                        })}
                    },
                    {
                        {"property", "opacity"},
                        {"easing", "linear"},
                        {"keyframes", json::array({
                            {{"frame", 0}, {"value", 0.0}},
                            {{"frame", 12}, {"value", 1.0}},
                            {{"frame", 76}, {"value", 1.0}},
                            {{"frame", 92}, {"value", 0.0}}
                        })}
                    }
                })}
            }}
        };

        // 3. Bold Luminous Wavy Dashed Line (centered at [0, 0, 0])
        json lineLayer = {
            {"id", "wavy_connector"},
            {"type", "image"},
            {"asset", lineRel},
            {"size", {kWidth, kHeight}},
            {"position", {0, 0, 0}},
            {"fit", "contain"},
            {"start_frame", 76},
            {"duration_frames", 64},
            {"enable_3d", true},
            {"animation", {
                {"tracks", json::array({
                    {
                        {"property", "opacity"},
                        {"easing", "out_cubic"},
                        {"keyframes", json::array({
                            {{"frame", 0}, {"value", 0.0}},
                            {{"frame", 12}, {"value", 1.0}},
                            {{"frame", 48}, {"value", 1.0}},
                            {{"frame", 60}, {"value", 0.0}}
                        })}
                    }
                })}
            }}
        };

        // 4. Hero Title "1950" — Canonical Modern Font (Bricolage Grotesque) & Dead-Center
        json dateLayer = {
            {"id", "date_1950"},
            {"type", "text"},
            {"text", "1950"},
            {"size", {1400, 360}},
            {"position", {960, 540, 0}}, // Exact optical and mathematical center
            {"start_frame", 126},
            {"duration_frames", kTotalFrames - 126},
            {"enable_3d", true},
            {"style", {
                {"font", "Chronon3d/assets/fonts/Bricolage-Grotesque.ttf"},
                {"font_size", 260},
                {"fill", "#FFFFFF"},
                {"fit_mode", "shrink_only"},
                {"min_font_size", 180},
                {"max_font_size", 260},
                {"glow", {
                    {"radius", 36.0},
                    {"intensity", 0.70},
                    {"color", "#FFFFFF"}
                }}
            }},
            {"animation", {
                {"tracks", json::array({
                    {
                        {"property", "opacity"},
                        {"easing", "out_cubic"},
                        {"keyframes", json::array({
                            {{"frame", 0}, {"value", 0.0}},
                            {{"frame", 18}, {"value", 1.0}}
                        })}
                    },
                    {
                        {"property", "scale"},
                        {"easing", "out_cubic"},
                        {"keyframes", json::array({
                            {{"frame", 0}, {"value", 0.84}},
                            {{"frame", 22}, {"value", 1.0}}
                        })}
                    }
                })}
            }}
        };

        // 5. Space-Grotesk Editorial Subtitle Badge
        json subtitleLayer = {
            {"id", "date_subtitle"},
            {"type", "text"},
            {"text", "ARCHIVIO STORICO"},
            {"size", {900, 50}},
            {"position", {960, 680, 0}},
            {"start_frame", 136},
            {"duration_frames", kTotalFrames - 136},
            {"enable_3d", true},
            {"style", {
                {"font", "Chronon3d/assets/fonts/Space-Grotesk.ttf"},
                {"font_size", 28},
                {"fill", "#E5C378"},
                {"fit_mode", "shrink_only"},
                {"min_font_size", 18},
                {"max_font_size", 28}
            }},
            {"animation", {
                {"tracks", json::array({
                    {
                        {"property", "opacity"},
                        {"easing", "out_cubic"},
                        {"keyframes", json::array({
                            {{"frame", 0}, {"value", 0.0}},
                            {{"frame", 18}, {"value", 1.0}}
                        })}
                    }
                })}
            }}
        };

        // 6. Warm Gold Accent Rule
        json ruleLayer = {
            {"id", "accent_rule"},
            {"type", "shape"},
            {"size", {160, 4}},
            {"position", {960, 715, 0}},
            {"start_frame", 140},
            {"duration_frames", kTotalFrames - 140},
            {"enable_3d", true},
            {"shape", {
                {"type", "rounded_rect"},
                {"radius", 1},
                {"fill", {0.898, 0.765, 0.471, 0.85}}
            }},
            {"animation", {
                {"tracks", json::array({
                    {
                        {"property", "scale_x"},
                        {"easing", "out_cubic"},
                        {"keyframes", json::array({
                            {{"frame", 0}, {"value", 0.0}},
                            {{"frame", 20}, {"value", 1.0}}
                        })}
                    }
                })}
            }}
        };

        return json{
            {"schema", "chronon.render-plan.v3"},
            {"version", 3},
            {"job_id", "chronon_1950_camera_story_cpp_v2"},
            {"canvas", {
                {"width", kWidth},
                {"height", kHeight},
                {"fps_num", kFps},
                {"fps_den", 1},
                {"duration_frames", kTotalFrames}
            }},
            {"camera", {
                {"type", "perspective"},
                {"position", {camX[0], camY[0], camZ[0]}},
                {"rotation_deg", {0, camRy[0], 0}},
                {"fov_deg", camFov[0]},
                {"near", 1},
                {"far", 10000},
                {"zoom", 1}
            }},
            {"camera_animation", cameraAnimation},
            {"layers", json::array({
                bgLayer,
                photoLayer,
                lineLayer,
                dateLayer,
                subtitleLayer,
                ruleLayer
            })},
            {"output", {
                {"path", "camera_1950_story_cpp.mp4"},
                {"format", "mp4"},
                {"codec", "h264"}
            }}
        };
    }

} // namespace

int main(int argc, char** argv) {
    fs::path workspaceRoot = fs::current_path();
    while (!fs::exists(workspaceRoot / "Chronon3d") && workspaceRoot.has_parent_path()) {
        workspaceRoot = workspaceRoot.parent_path();
    }

    fs::path outDir = workspaceRoot / "ChrononTemplate/out/camera_1950_story";
    fs::path assetsDir = outDir / "assets";
    fs::path planPath = outDir / "camera_1950_story_cpp.plan.json";
    fs::path outMp4 = outDir / "camera_1950_story_cpp.mp4";
    fs::path cliPath = workspaceRoot / "Chronon3d/build/chronon/linux-video-fast-dev/apps/chronon3d_cli/chronon3d_cli";
    bool doRender = true;

    for (int i = 1; i < argc; ++i) {
        std::string arg = argv[i];
        if (arg == "--no-render") doRender = false;
        else if (arg == "--output" && i + 1 < argc) planPath = argv[++i];
        else if (arg == "--cli" && i + 1 < argc) cliPath = argv[++i];
        else if (arg == "--video" && i + 1 < argc) outMp4 = argv[++i];
    }

    std::cout << "====================================================\n";
    std::cout << " Chronon C++ 1950 Camera Story Generator (1920x1080)\n";
    std::cout << "====================================================\n";
    std::cout << "Workspace: " << workspaceRoot << "\n";
    std::cout << "Output Plan: " << planPath << "\n";

    fs::path backdropPath = assetsDir / "backdrop_editorial.png";
    fs::path photoPath = assetsDir / "vintage_photo_1950.png";
    fs::path linePath = assetsDir / "wavy_dashed_line.png";

    generateBackdrop(backdropPath);
    prepareVintagePhoto(workspaceRoot, photoPath);
    generateWavyDashedLine(linePath);

    std::string backdropRel = fs::relative(backdropPath, workspaceRoot).string();
    std::string photoRel = fs::relative(photoPath, workspaceRoot).string();
    std::string lineRel = fs::relative(linePath, workspaceRoot).string();

    json plan = buildRenderPlan(backdropRel, photoRel, lineRel);

    fs::create_directories(planPath.parent_path());
    std::ofstream ofs(planPath);
    ofs << plan.dump(2) << "\n";
    ofs.close();
    std::cout << "[C++] Written render plan to: " << planPath << "\n";

    if (doRender) {
        if (!fs::exists(cliPath)) {
            std::cerr << "[C++] Error: Chronon3D CLI not found at " << cliPath << "\n";
            return 1;
        }

        std::string renderCmd = cliPath.string() + " render --plan " + planPath.string() +
                                " --assets-root " + workspaceRoot.string() + " -o " + outMp4.string();

        std::cout << "[C++] Launching Chronon3D Vulkan renderer:\n" << renderCmd << "\n";
        int ret = std::system(renderCmd.c_str());
        if (ret != 0) {
            std::cerr << "[C++] Renderer exited with code " << ret << "\n";
            return ret;
        }
        std::cout << "\n[C++] SUCCESS! Rendered 1920x1080 video saved to: " << outMp4 << "\n";
    }

    return 0;
}
