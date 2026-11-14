// Recreates the SPOILERS reference title card in ChrononTemplate:
// 1920x1080, 24 fps, 72 frames (3.0 s), procedural film dust & curved lint
// fibers (batched into 4 Path layers for low VRAM & fast GPU execution),
// smooth crimson title with glowing vector rim, and a composite optical
// adjustment stack (pincushion lens distortion, radial edge blur, chromatic
// aberration, soft diffusion, and vignette).
//
// Usage: chronontemplate_emit_spoilers_title <output-plan-path> [output-mp4-path]
#include "chronontemplate/core/RenderPlanContentHost.hpp"
#include "chrononmotion/motion/RenderPlanEmission.hpp"

#include <algorithm>
#include <cmath>
#include <cstdint>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <string>
#include <unordered_map>
#include <vector>

using namespace chronontemplate;
using namespace chrononmotion;
using namespace chrononmotion::motion;

namespace {

constexpr float kWidth = 1920.f;
constexpr float kHeight = 1080.f;
constexpr float kFps = 24.f;
constexpr int kFrames = 72; // 3.0 s at 24 fps

float hashUnit(std::uint32_t seed, std::uint32_t index, std::uint32_t channel) {
    std::uint32_t x = seed ^ (index * 0x9E3779B9u) ^ (channel * 0x85EBCA6Bu);
    x ^= x >> 16;
    x *= 0x7FEB352Du;
    x ^= x >> 15;
    x *= 0x846CA68Bu;
    x ^= x >> 16;
    return static_cast<float>(x & 0x00FFFFFFu) / static_cast<float>(0x01000000u);
}

class SpoilersAssetBackend {
public:
    ContentHandle text(const TextRequest& request) {
        return make("text/" + request.text, ContentKind::Text, {1920.f, 700.f});
    }

    ContentHandle image(const ImageRequest& request) {
        return make(request.path, ContentKind::Image, {kWidth, kHeight});
    }

    ContentHandle video(const VideoRequest& request) {
        return make(request.path, ContentKind::Video, {kWidth, kHeight});
    }

    ContentHandle shape(const ShapeRequest& request) {
        return make("shape/" + request.name, ContentKind::Image, request.size);
    }

    std::string fingerprint(const ContentId& id) const {
        const auto found = m_fingerprints.find(id);
        return found == m_fingerprints.end() ? std::string{} : found->second;
    }

private:
    ContentHandle make(std::string id, ContentKind kind, Vector2 size) {
        ContentHandle handle;
        handle.id = std::move(id);
        handle.wireId = m_nextWireId++;
        handle.kind = kind;
        handle.metrics.naturalSize = size;
        handle.metrics.anchor = {0.5f, 0.5f};
        handle.metrics.fingerprint = "spoilers-title-v2:" + handle.id;
        m_fingerprints.emplace(handle.id, handle.metrics.fingerprint);
        return handle;
    }

    std::uint64_t m_nextWireId{1};
    std::unordered_map<ContentId, std::string> m_fingerprints;
};

std::uint32_t crc32Update(std::uint32_t crc, const std::uint8_t* data, std::size_t len) {
    crc = ~crc;
    for (std::size_t i = 0; i < len; ++i) {
        crc ^= data[i];
        for (int b = 0; b < 8; ++b) {
            crc = (crc >> 1) ^ (0xEDB88320u & (0u - (crc & 1u)));
        }
    }
    return ~crc;
}

void appendBe32(std::vector<std::uint8_t>& out, std::uint32_t v) {
    out.push_back(static_cast<std::uint8_t>((v >> 24) & 0xFF));
    out.push_back(static_cast<std::uint8_t>((v >> 16) & 0xFF));
    out.push_back(static_cast<std::uint8_t>((v >> 8) & 0xFF));
    out.push_back(static_cast<std::uint8_t>(v & 0xFF));
}

void appendPngChunk(std::vector<std::uint8_t>& out, const char type[4],
                    const std::vector<std::uint8_t>& data) {
    appendBe32(out, static_cast<std::uint32_t>(data.size()));
    const std::size_t typePos = out.size();
    out.insert(out.end(), type, type + 4);
    out.insert(out.end(), data.begin(), data.end());
    const std::uint32_t crc = crc32Update(0u, out.data() + typePos, 4 + data.size());
    appendBe32(out, crc);
}

/// Write a standard RGBA8 PNG using stored (uncompressed) deflate blocks.
void writeRgbaPng(const std::filesystem::path& path, int w, int h,
                  const std::vector<std::uint8_t>& rgba) {
    std::vector<std::uint8_t> raw;
    raw.reserve(static_cast<std::size_t>(h) * (1 + static_cast<std::size_t>(w) * 4));
    for (int y = 0; y < h; ++y) {
        raw.push_back(0); // filter type 0 (None)
        const std::uint8_t* row = rgba.data() + static_cast<std::size_t>(y) * w * 4;
        raw.insert(raw.end(), row, row + static_cast<std::size_t>(w) * 4);
    }

    // Zlib stream: CMF=0x78, FLG=0x01 + stored deflate blocks + Adler32.
    std::vector<std::uint8_t> zlib;
    zlib.push_back(0x78);
    zlib.push_back(0x01);
    std::size_t offset = 0;
    while (offset < raw.size()) {
        const std::size_t chunk = std::min<std::size_t>(65535u, raw.size() - offset);
        const bool last = (offset + chunk == raw.size());
        zlib.push_back(last ? 0x01 : 0x00);
        const std::uint16_t len = static_cast<std::uint16_t>(chunk);
        const std::uint16_t nlen = static_cast<std::uint16_t>(~len);
        zlib.push_back(static_cast<std::uint8_t>(len & 0xFF));
        zlib.push_back(static_cast<std::uint8_t>((len >> 8) & 0xFF));
        zlib.push_back(static_cast<std::uint8_t>(nlen & 0xFF));
        zlib.push_back(static_cast<std::uint8_t>((nlen >> 8) & 0xFF));
        zlib.insert(zlib.end(), raw.data() + offset, raw.data() + offset + chunk);
        offset += chunk;
    }
    std::uint32_t s1 = 1u, s2 = 0u;
    for (std::uint8_t b : raw) {
        s1 = (s1 + b) % 65521u;
        s2 = (s2 + s1) % 65521u;
    }
    appendBe32(zlib, (s2 << 16) | s1);

    std::vector<std::uint8_t> png = {0x89, 'P', 'N', 'G', 0x0D, 0x0A, 0x1A, 0x0A};
    std::vector<std::uint8_t> ihdr;
    appendBe32(ihdr, static_cast<std::uint32_t>(w));
    appendBe32(ihdr, static_cast<std::uint32_t>(h));
    ihdr.push_back(8); // bit depth
    ihdr.push_back(6); // RGBA
    ihdr.push_back(0);
    ihdr.push_back(0);
    ihdr.push_back(0);
    appendPngChunk(png, "IHDR", ihdr);
    appendPngChunk(png, "IDAT", zlib);
    appendPngChunk(png, "IEND", {});

    std::ofstream out(path, std::ios::binary | std::ios::trunc);
    if (!out || !out.write(reinterpret_cast<const char*>(png.data()),
                           static_cast<std::streamsize>(png.size()))) {
        throw std::runtime_error("failed to write PNG: " + path.string());
    }
}

void splatSoftDot(std::vector<float>& buf, int w, int h, float cx, float cy,
                  float rx, float ry, float angle, float intensity,
                  float rTint, float gTint, float bTint) {
    const float ca = std::cos(angle);
    const float sa = std::sin(angle);
    const int margin = static_cast<int>(std::ceil(std::max(rx, ry) * 2.5f)) + 2;
    const int x0 = std::max(0, static_cast<int>(std::floor(cx)) - margin);
    const int x1 = std::min(w - 1, static_cast<int>(std::ceil(cx)) + margin);
    const int y0 = std::max(0, static_cast<int>(std::floor(cy)) - margin);
    const int y1 = std::min(h - 1, static_cast<int>(std::ceil(cy)) + margin);

    for (int y = y0; y <= y1; ++y) {
        for (int x = x0; x <= x1; ++x) {
            const float dx = static_cast<float>(x) - cx;
            const float dy = static_cast<float>(y) - cy;
            const float lx = (dx * ca + dy * sa) / std::max(0.4f, rx);
            const float ly = (-dx * sa + dy * ca) / std::max(0.4f, ry);
            const float d2 = lx * lx + ly * ly;
            if (d2 > 4.0f) continue;
            const float wgt = std::exp(-d2 * 1.45f) * intensity;
            const std::size_t idx = (static_cast<std::size_t>(y) * w + x) * 3;
            buf[idx + 0] += wgt * rTint;
            buf[idx + 1] += wgt * gTint;
            buf[idx + 2] += wgt * bTint;
        }
    }
}

void generateDustPlatePng(const std::filesystem::path& path, std::uint32_t seed,
                          int dustCount, int fiberCount, float brightness) {
    constexpr int W = static_cast<int>(kWidth);
    constexpr int H = static_cast<int>(kHeight);
    std::vector<float> sharp(static_cast<std::size_t>(W) * H * 3, 0.f);

    // Dust specks: mix of tiny pinpoints and soft optical flecks.
    for (int i = 0; i < dustCount; ++i) {
        const auto idx = static_cast<std::uint32_t>(i);
        const float cx = hashUnit(seed, idx, 1) * W;
        const float cy = hashUnit(seed, idx, 2) * H;
        const float baseR = 0.7f + std::pow(hashUnit(seed, idx, 3), 2.2f) * 2.8f;
        const float aspect = 0.75f + hashUnit(seed, idx, 4) * 1.15f;
        const float angle = hashUnit(seed, idx, 5) * 6.2831853f;
        const float inten = brightness * (0.18f + std::pow(hashUnit(seed, idx, 6), 1.4f) * 0.85f);
        const float warm = hashUnit(seed, idx, 7);
        const float rT = 0.90f + 0.10f * warm;
        const float gT = 0.88f + 0.08f * warm;
        const float bT = 0.94f - 0.10f * warm;
        splatSoftDot(sharp, W, H, cx, cy, baseR, baseR * aspect, angle, inten, rT, gT, bT);
    }

    // Curved hair / lint fibers (cubic Bezier sampled finely).
    for (int i = 0; i < fiberCount; ++i) {
        const auto idx = static_cast<std::uint32_t>(i + 1000);
        const float cx = hashUnit(seed, idx, 10) * W;
        const float cy = hashUnit(seed, idx, 11) * H;
        const float len = 24.f + hashUnit(seed, idx, 12) * 78.f;
        const float ang = hashUnit(seed, idx, 13) * 6.2831853f;
        const float c1 = (hashUnit(seed, idx, 14) - 0.5f) * 34.f;
        const float c2 = (hashUnit(seed, idx, 15) - 0.5f) * 34.f;
        const float inten = brightness * (0.14f + hashUnit(seed, idx, 16) * 0.34f);
        const float radius = 0.65f + hashUnit(seed, idx, 17) * 0.55f;

        const float ca = std::cos(ang), sa = std::sin(ang);
        const float nx = -sa, ny = ca;
        const float p0x = cx - ca * (len * 0.5f), p0y = cy - sa * (len * 0.5f);
        const float p3x = cx + ca * (len * 0.5f), p3y = cy + sa * (len * 0.5f);
        const float p1x = cx - ca * (len * 0.16f) + nx * c1, p1y = cy - sa * (len * 0.16f) + ny * c1;
        const float p2x = cx + ca * (len * 0.16f) + nx * c2, p2y = cy + sa * (len * 0.16f) + ny * c2;

        const int steps = std::max(20, static_cast<int>(len * 1.6f));
        for (int s = 0; s <= steps; ++s) {
            const float t = static_cast<float>(s) / static_cast<float>(steps);
            const float u = 1.f - t;
            const float bx = u*u*u*p0x + 3*u*u*t*p1x + 3*u*t*t*p2x + t*t*t*p3x;
            const float by = u*u*u*p0y + 3*u*u*t*p1y + 3*u*t*t*p2y + t*t*t*p3y;
            const float taper = std::sin(t * 3.14159265f);
            splatSoftDot(sharp, W, H, bx, by, radius, radius, 0.f,
                         inten * (0.35f + 0.65f * taper) * 0.32f, 0.92f, 0.91f, 0.89f);
        }
    }

    // Apply radial optical edge smear toward frame corners (matches reference lens falloff).
    std::vector<std::uint8_t> rgba(static_cast<std::size_t>(W) * H * 4, 0);
    const float halfW = W * 0.5f;
    const float halfH = H * 0.5f;
    for (int y = 0; y < H; ++y) {
        for (int x = 0; x < W; ++x) {
            const float dx = static_cast<float>(x) - halfW;
            const float dy = static_cast<float>(y) - halfH;
            const float rn = std::sqrt((dx / halfW) * (dx / halfW) + (dy / halfH) * (dy / halfH));
            const float smear = std::max(0.f, rn - 0.38f);
            const float streakLen = smear * smear * 28.f;
            float rAcc = 0.f, gAcc = 0.f, bAcc = 0.f;
            if (streakLen < 0.6f) {
                const std::size_t idx = (static_cast<std::size_t>(y) * W + x) * 3;
                rAcc = sharp[idx + 0];
                gAcc = sharp[idx + 1];
                bAcc = sharp[idx + 2];
            } else {
                const float invR = 1.f / std::max(1.f, std::sqrt(dx * dx + dy * dy));
                const float ux = dx * invR;
                const float uy = dy * invR;
                constexpr int kTaps = 9;
                for (int k = 0; k < kTaps; ++k) {
                    const float f = (static_cast<float>(k) / static_cast<float>(kTaps - 1) - 0.5f) * streakLen;
                    const int sx = std::clamp(static_cast<int>(std::lround(x - ux * f)), 0, W - 1);
                    const int sy = std::clamp(static_cast<int>(std::lround(y - uy * f)), 0, H - 1);
                    const std::size_t sidx = (static_cast<std::size_t>(sy) * W + sx) * 3;
                    rAcc += sharp[sidx + 0];
                    gAcc += sharp[sidx + 1];
                    bAcc += sharp[sidx + 2];
                }
                rAcc /= static_cast<float>(kTaps);
                gAcc /= static_cast<float>(kTaps);
                bAcc /= static_cast<float>(kTaps);
            }
            const std::size_t oidx = (static_cast<std::size_t>(y) * W + x) * 4;
            const float alpha = std::clamp(std::max({rAcc, gAcc, bAcc}), 0.f, 1.f);
            if (alpha > 1e-4f) {
                rgba[oidx + 0] = static_cast<std::uint8_t>(std::clamp(rAcc / alpha, 0.f, 1.f) * 255.f);
                rgba[oidx + 1] = static_cast<std::uint8_t>(std::clamp(gAcc / alpha, 0.f, 1.f) * 255.f);
                rgba[oidx + 2] = static_cast<std::uint8_t>(std::clamp(bAcc / alpha, 0.f, 1.f) * 255.f);
                rgba[oidx + 3] = static_cast<std::uint8_t>(alpha * 255.f);
            }
        }
    }
    writeRgbaPng(path, W, H, rgba);
}

} // namespace

int main(int argc, char** argv) {
    if (argc < 2) {
        std::cerr << "usage: chronontemplate_emit_spoilers_title <output-plan-path> [output-mp4-path]\n";
        return 2;
    }
    const std::filesystem::path planPath = argv[1];
    const std::string mp4Path = (argc >= 3)
        ? std::string(argv[2])
        : (planPath.parent_path() / "spoilers_chronontemplate.mp4").string();

    try {
        if (planPath.has_parent_path()) {
            std::filesystem::create_directories(planPath.parent_path());
        }

        SpoilersAssetBackend backend;
        RenderPlanContentHost host({
            .createText = [&](const TextRequest& request) { return backend.text(request); },
            .createImage = [&](const ImageRequest& request) { return backend.image(request); },
            .createVideo = [&](const VideoRequest& request) { return backend.video(request); },
            .createShape = [&](const ShapeRequest& request) { return backend.shape(request); },
            .currentFingerprint = [&](const ContentId& id) { return backend.fingerprint(id); }});

        TemplateScene scene("spoilers_reference_recreation", kFps, host, kWidth, kHeight);
        scene.camera().setFov(53.14f);

        // 1. Deep black backdrop.
        ShapeSpec background{};
        background.name = "black_backdrop";
        background.size = Vector2(kWidth, kHeight);
        background.fillColor = "#000000";
        scene.shape(background)
             .position(kWidth * 0.5f, kHeight * 0.5f)
             .alive(0, kFrames - 1);

        // 2. Procedural film dust & curved lint fiber plates with radial edge smear.
        const auto outDir = planPath.has_parent_path() ? planPath.parent_path() : std::filesystem::path(".");
        const auto bgDustPath = outDir / "dust_plate_bg.png";
        const auto fgDustPath = outDir / "dust_plate_fg.png";
        generateDustPlatePng(bgDustPath, 1997u, 185, 22, 0.72f);
        generateDustPlatePng(fgDustPath, 4242u, 115, 16, 0.90f);

        ImageSpec dustBg{};
        dustBg.path = bgDustPath.string();
        dustBg.name = "dust_plate_bg";
        dustBg.fit = ImageFitMode::Cover;
        dustBg.targetSize = Vector2(kWidth, kHeight);
        dustBg.screenSpace = true;
        scene.image(dustBg)
             .position(-28.f, -16.f)
             .scale(1.03f)
             .opacity(0.88f)
             .alive(0, kFrames - 1);

        // 3. SPOILERS title: smooth deep crimson fill, bright glowing rim,
        //    soft optical diffusion, and chromatic split.
        TextSpec title{};
        title.name = "spoilers_title";
        title.text = "SPOILERS";
        title.font = "Chronon3d/assets/fonts/SF-Pro-Display-Black.otf";
        title.fontSize = 285.f;
        title.color = "#7E0F03";
        title.stroke = TextStrokeStyle{
            .color = "#C91E0B",
            .width = 4.4f,
            .mode = "vector"
        };
        title.glow = TextGlowStyle{
            .color = "#E0200C",
            .radius = 12.f,
            .intensity = 0.75f
        };
        title.effectGlow = TextGlowStyle{
            .color = "#D61B09",
            .radius = 28.f,
            .intensity = 0.75f
        };
        title.halation = TextHalationStyle{
            .threshold = 0.10f,
            .softness = 0.25f,
            .radiusPx = 22.f,
            .intensity = 0.90f,
            .tint = {1.0f, 0.14f, 0.04f, 1.0f}
        };
        title.chromaticAberration = TextChromaticAberrationStyle{
            .redOffset = 1.0f,
            .blueOffset = -1.0f
        };
        title.gaussianBlurRadius = 1.4f;
        title.lensDistortion = TextLensDistortionStyle{
            .curvature = -0.42f,
            .scale = 0.89f,
            .center = {0.5f, 0.5f}
        };

        scene.text(title)
             .position(kWidth * 0.5f, kHeight * 0.5f + 12.f)
             .alive(0, kFrames - 1);

        // 4. Foreground dust & lint plate (subtly overlaps title and edges).
        ImageSpec dustFg{};
        dustFg.path = fgDustPath.string();
        dustFg.name = "dust_plate_fg";
        dustFg.fit = ImageFitMode::Cover;
        dustFg.targetSize = Vector2(kWidth, kHeight);
        dustFg.screenSpace = true;
        scene.image(dustFg)
             .position(-28.f, -16.f)
             .scale(1.03f)
             .opacity(0.90f)
             .alive(0, kFrames - 1);

        auto plan = lowerToRenderPlan(scene, host, "spoilers_chronontemplate_v1", mp4Path);
        plan.output.format = chronon3d::render_plan::OutputFormat::Mp4;

        std::ofstream file(planPath, std::ios::binary | std::ios::trunc);
        if (!file || !(file << renderPlanToJson(plan))) {
            throw std::runtime_error("failed to write RenderPlan: " + planPath.string());
        }
        std::cout << "Wrote " << planPath << " (" << plan.layers.size() << " layers)\n";
    } catch (const std::exception& e) {
        std::cerr << "emit_spoilers_title: " << e.what() << '\n';
        return 1;
    }
    return 0;
}
