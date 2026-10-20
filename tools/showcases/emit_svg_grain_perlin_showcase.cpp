// Emits the 14-reference-frame SVG/Path + Perlin Field2D + Grain Specks + Glow
// showcase (Bus -> Thermometer -> Glowing Perlin Dot & Trim Line Graph) using
// ChrononTemplate's native ShapeGeometry::Path, ShapeTrimSpec, Field2D, and
// multi-pass concentric glow / FloatingDust effects.
//
// Timeline (140 frames @ 30 fps; each ref_01..ref_14 maps to a 10-frame window,
// sampled at frames 5, 15, 25, 35, 45, 55, 65, 75, 85, 95, 105, 115, 125, 135):
//   - Scene A (frames   0.. 19): ref_01 (horizontal bus + wide dashed line) ->
//                                ref_02 (tilted bus ~18 deg CW, line gone)
//   - Scene B (frames  20.. 59): ref_03 (thermometer low) ->
//                                ref_04 (mercury rising) ->
//                                ref_05 (mercury at peak + warm glow) ->
//                                ref_06 (mercury receding)
//   - Scene C (frames  60..139): ref_07..ref_14 (yellow Perlin dot +
//                                white/cyan glowing '^' line graph drawn via Trim)

#include "chronontemplate/core/PlanLowering.hpp"
#include "chronontemplate/core/RenderPlanContentHost.hpp"
#include "chronontemplate/core/TemplateScene.hpp"
#include "chronontemplate/effects/EffectsPack.hpp"
#include "chrononmotion/motion/Easing.hpp"
#include "chrononmotion/motion/RenderPlanEmission.hpp"

#include <cmath>
#include <cstdint>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <optional>
#include <stdexcept>
#include <string>
#include <unordered_map>
#include <vector>

using namespace chronontemplate;
using chrononmotion::Vector2;
using chrononmotion::Vector3;
using chrononmotion::motion::Easing;

namespace {

constexpr float kWidth = 1920.f;
constexpr float kHeight = 1080.f;
constexpr float kCenterX = kWidth * 0.5f;
constexpr float kCenterY = kHeight * 0.5f;
constexpr float kFps = 30.f;
constexpr int kTotalFrames = 140;

class ShowcaseBackend final : public ContentHost {
public:
    ContentHandle createText(const TextRequest& r) override {
        return make("text/" + r.text, chrononmotion::motion::ContentKind::Text,
                    {r.fontSize * 0.65f * static_cast<float>(r.text.size()), r.fontSize * 1.25f});
    }
    ContentHandle createImage(const ImageRequest& r) override {
        return make(r.path, chrononmotion::motion::ContentKind::Image, {kWidth, kHeight});
    }
    ContentHandle createVideo(const VideoRequest& r) override {
        return make("video/" + r.path, chrononmotion::motion::ContentKind::Video, {kWidth, kHeight});
    }
    ContentHandle createShape(const ShapeRequest& r) override {
        return make("shape/" + r.name + "_" + std::to_string(m_nextWireId),
                    chrononmotion::motion::ContentKind::Image, r.size);
    }
    std::string currentFingerprint(const ContentId& id) const override {
        const auto it = m_fingerprints.find(id);
        return it == m_fingerprints.end() ? std::string{} : it->second;
    }

private:
    std::uint64_t m_nextWireId{1};
    std::unordered_map<ContentId, std::string> m_fingerprints;

    ContentHandle make(std::string id, chrononmotion::motion::ContentKind kind, Vector2 size) {
        ContentHandle c;
        c.id = std::move(id);
        c.wireId = m_nextWireId++;
        c.kind = kind;
        c.metrics.naturalSize = size;
        c.metrics.anchor = Vector2(0.5f, 0.5f);
        c.metrics.fingerprint = "svg-grain-perlin-showcase:" + c.id;
        m_fingerprints.emplace(c.id, c.metrics.fingerprint);
        return c;
    }
};

ShapePathCommand rotateCmd(const ShapePathCommand& cmd, float angleDeg, float scale = 1.f) {
    if (cmd.type == ShapePathCommandType::Close) {
        return cmd;
    }
    constexpr float kDegToRad = 0.01745329251994329577f;
    const float rad = angleDeg * kDegToRad;
    const float c = std::cos(rad) * scale;
    const float s = std::sin(rad) * scale;
    auto rot = [&](Vector2 p) -> Vector2 {
        return {p.x * c - p.y * s, p.x * s + p.y * c};
    };
    ShapePathCommand out = cmd;
    out.point = rot(cmd.point);
    out.control1 = rot(cmd.control1);
    out.control2 = rot(cmd.control2);
    return out;
}

std::vector<ShapePathCommand> transformPath(const std::vector<ShapePathCommand>& cmds,
                                            float angleDeg, float scale = 1.f) {
    std::vector<ShapePathCommand> out;
    out.reserve(cmds.size());
    for (const auto& cmd : cmds) {
        out.push_back(rotateCmd(cmd, angleDeg, scale));
    }
    return out;
}

std::vector<ShapePathCommand> makeRoundedRectPath(float x0, float y0, float x1, float y1, float r) {
    return {
        ShapePathCommand::moveTo(x0 + r, y0),
        ShapePathCommand::lineTo(x1 - r, y0),
        ShapePathCommand::quadraticTo(x1, y0, x1, y0 + r),
        ShapePathCommand::lineTo(x1, y1 - r),
        ShapePathCommand::quadraticTo(x1, y1, x1 - r, y1),
        ShapePathCommand::lineTo(x0 + r, y1),
        ShapePathCommand::quadraticTo(x0, y1, x0, y1 - r),
        ShapePathCommand::lineTo(x0, y0 + r),
        ShapePathCommand::quadraticTo(x0, y0, x0 + r, y0),
        ShapePathCommand::close()
    };
}

std::vector<ShapePathCommand> makeCirclePath(float cx, float cy, float r) {
    constexpr float kKappa = 0.5522847498f;
    const float k = r * kKappa;
    return {
        ShapePathCommand::moveTo(cx, cy - r),
        ShapePathCommand::cubicTo(cx + k, cy - r, cx + r, cy - k, cx + r, cy),
        ShapePathCommand::cubicTo(cx + r, cy + k, cx + k, cy + r, cx, cy + r),
        ShapePathCommand::cubicTo(cx - k, cy + r, cx - r, cy + k, cx - r, cy),
        ShapePathCommand::cubicTo(cx - r, cy - k, cx - k, cy - r, cx, cy - r),
        ShapePathCommand::close()
    };
}

chronon3d::graphics::Field2D makePerlinField(std::uint32_t seed, float frequency, float warpAmount = 0.18f) {
    chronon3d::graphics::Field2D field{};
    field.generator = chronon3d::graphics::Field2DGenerator::Perlin;
    field.seed = seed;
    field.frequency = frequency;
    if (warpAmount > 0.f) {
        chronon3d::graphics::Field2DOperator warpOp{};
        warpOp.kind = chronon3d::graphics::Field2DOperatorKind::Warp;
        warpOp.amount = warpAmount;
        field.operators.push_back(warpOp);
    }
    chronon3d::graphics::Field2DOperator smoothOp{};
    smoothOp.kind = chronon3d::graphics::Field2DOperatorKind::Smoothstep;
    smoothOp.edge = 0.45f;
    smoothOp.softness = 0.42f;
    field.operators.push_back(smoothOp);
    return field;
}

chronon3d::graphics::GradientDefinition makeThreeStopRamp(
        const char* c0, const char* c1, const char* c2) {
    return chronon3d::graphics::GradientDefinition::linear(
        {0.f, 0.f}, {1.f, 1.f},
        {
            {0.0f, *chronon3d::Color::try_from_hex(c0)},
            {0.55f, *chronon3d::Color::try_from_hex(c1)},
            {1.0f, *chronon3d::Color::try_from_hex(c2)}
        });
}

// Helper: Soft concentric elliptical glow ("onion" rings) with zero sub-canvas effect buffers
void addSoftEllipseGlow(TemplateScene& scene, const std::string& name,
                        float cx, float cy, float w, float h,
                        const std::string& color, float baseOpacity,
                        int inFrame, int outFrame) {
    static constexpr float kScales[] = {1.0f, 0.70f, 0.48f, 0.32f};
    static constexpr float kWeights[] = {0.16f, 0.30f, 0.52f, 0.80f};
    for (int i = 0; i < 4; ++i) {
        ShapeSpec ring;
        ring.size = {w * kScales[i], h * kScales[i]};
        ring.name = name + "_glow_ring_" + std::to_string(i);
        ring.geometry = ShapeGeometry::Ellipse;
        ring.fillColor = color;
        scene.shape(ring)
            .position(cx, cy)
            .opacity(baseOpacity * kWeights[i])
            .alive(inFrame, outFrame);
    }
}

// Helper: Multi-pass glowing vector stroke (outer wide halo + mid glow + crisp core)
void addGlowingStrokePath(TemplateScene& scene, const std::string& name,
                          Vector2 boxSize, float cx, float cy,
                          const std::vector<ShapePathCommand>& path,
                          const std::string& coreColor, const std::string& glowColor,
                          float coreWidth, int inFrame, int outFrame,
                          const std::optional<ShapeTrimSpec>& trim = std::nullopt,
                          const std::vector<float>& dashArray = {}) {
    struct Pass {
        const char* suffix;
        float widthMult;
        float opacity;
        const std::string& color;
    };
    const Pass passes[] = {
        {"_halo_outer", 3.2f, 0.08f, glowColor},
        {"_halo_mid",   1.8f, 0.20f, glowColor},
        {"_core",       1.0f, 1.00f, coreColor}
    };
    for (const auto& p : passes) {
        ShapeSpec s;
        s.size = boxSize;
        s.name = name + p.suffix;
        s.geometry = ShapeGeometry::Path;
        s.fillEnabled = false;
        s.strokeColor = p.color;
        s.strokeWidth = coreWidth * p.widthMult;
        s.strokeCap = "round";
        s.strokeJoin = "round";
        s.strokeDashArray = dashArray;
        s.path = path;
        s.trim = trim;
        scene.shape(s)
            .position(cx, cy)
            .opacity(p.opacity)
            .alive(inFrame, outFrame);
    }
}

// Builds the vector bus matching ref_01 (0 deg) and ref_02 (+18 deg CW, slightly dimmed)
void addVectorBus(TemplateScene& scene, const std::string& prefix,
                  float cx, float cy, float angleDeg, float opacityMult,
                  int inFrame, int outFrame) {
    constexpr float kBusScale = 2.15f;
    const Vector2 boxSize{520.f, 360.f};

    // 1. Soft atmospheric white/blue glow behind the bus roof and panel
    static constexpr float kPad[] = {20.f, 12.f, 6.f};
    static constexpr float kAlpha[] = {0.03f, 0.05f, 0.09f};
    for (int i = 0; i < 3; ++i) {
        const float p = kPad[i];
        ShapeSpec halo;
        halo.size = boxSize;
        halo.name = prefix + "_halo_" + std::to_string(i);
        halo.geometry = ShapeGeometry::Path;
        halo.path = transformPath(
            makeRoundedRectPath(-78.f - p, -38.f - p, 78.f + p, 28.f + p, 12.f + p * 0.4f),
            angleDeg, kBusScale);
        halo.fillColor = "#CBD5E1";
        scene.shape(halo).position(cx, cy).opacity(kAlpha[i] * opacityMult).alive(inFrame, outFrame);
    }

    // 2. Main deep navy-blue bus body with Perlin Field2D shading (matching ref_01/ref_02)
    ShapeSpec body;
    body.size = boxSize;
    body.name = prefix + "_body";
    body.geometry = ShapeGeometry::Path;
    body.path = transformPath(makeRoundedRectPath(-78.f, -30.f, 76.f, 24.f, 8.f), angleDeg, kBusScale);
    body.fillColor = "#13238E";
    body.field = makePerlinField(303, 2.8f, 0.20f);
    body.fieldRamp = makeThreeStopRamp("#09114A", "#13238E", "#1E3A8A");
    body.fieldDrift = chronon3d::Vec2{0.22f, 0.10f};
    scene.shape(body).position(cx, cy).opacity(opacityMult).alive(inFrame, outFrame);

    // 3. Glowing white upper roof cap (flat bottom, rounded top)
    ShapeSpec roofGlow;
    roofGlow.size = boxSize;
    roofGlow.name = prefix + "_roof_glow";
    roofGlow.geometry = ShapeGeometry::Path;
    roofGlow.path = transformPath(makeRoundedRectPath(-78.f, -41.f, 72.f, -26.f, 6.f), angleDeg, kBusScale);
    roofGlow.fillColor = "#FFFFFF";
    scene.shape(roofGlow).position(cx, cy).opacity(0.24f * opacityMult).alive(inFrame, outFrame);

    ShapeSpec roof;
    roof.size = boxSize;
    roof.name = prefix + "_roof";
    roof.geometry = ShapeGeometry::Path;
    roof.path = transformPath(makeRoundedRectPath(-76.f, -38.f, 70.f, -28.f, 5.f), angleDeg, kBusScale);
    roof.fillColor = "#F1F5F9";
    roof.field = makePerlinField(305, 3.5f, 0.14f);
    roof.fieldRamp = makeThreeStopRamp("#CBD5E1", "#F1F5F9", "#FFFFFF");
    roof.fieldDrift = chronon3d::Vec2{0.15f, 0.06f};
    scene.shape(roof).position(cx, cy).opacity(opacityMult).alive(inFrame, outFrame);

    // 4. Lower grey chassis trim strip along the bottom of the bus
    ShapeSpec chassis;
    chassis.size = boxSize;
    chassis.name = prefix + "_chassis_strip";
    chassis.geometry = ShapeGeometry::Path;
    chassis.path = transformPath(makeRoundedRectPath(-78.f, 16.f, 76.f, 25.f, 3.f), angleDeg, kBusScale);
    chassis.fillColor = "#646970";
    scene.shape(chassis).position(cx, cy).opacity(opacityMult).alive(inFrame, outFrame);

    // 5. Lower-left glowing white side panel (matches ref_01/ref_02)
    ShapeSpec whitePanelGlow;
    whitePanelGlow.size = boxSize;
    whitePanelGlow.name = prefix + "_white_panel_glow";
    whitePanelGlow.geometry = ShapeGeometry::Path;
    whitePanelGlow.path = transformPath(makeRoundedRectPath(-80.f, -2.f, -14.f, 19.f, 4.f), angleDeg, kBusScale);
    whitePanelGlow.fillColor = "#FFFFFF";
    scene.shape(whitePanelGlow).position(cx, cy).opacity(0.22f * opacityMult).alive(inFrame, outFrame);

    ShapeSpec whitePanel;
    whitePanel.size = boxSize;
    whitePanel.name = prefix + "_white_panel";
    whitePanel.geometry = ShapeGeometry::Path;
    whitePanel.path = transformPath(makeRoundedRectPath(-78.f, 0.f, -16.f, 17.f, 3.f), angleDeg, kBusScale);
    whitePanel.fillColor = "#F1F5F9";
    whitePanel.field = makePerlinField(309, 3.8f, 0.15f);
    whitePanel.fieldRamp = makeThreeStopRamp("#CBD5E1", "#F1F5F9", "#FFFFFF");
    whitePanel.fieldDrift = chronon3d::Vec2{0.18f, -0.10f};
    scene.shape(whitePanel).position(cx, cy).opacity(opacityMult).alive(inFrame, outFrame);

    // 6. Dark windows & central tall door cutout (matching ref_01 layout:
    //    2 windows on left, tall central black door in the middle, 1 window to its right,
    //    and tall front windshield on far right)
    struct RectDef { float x0, y0, x1, y1, r; };
    const std::vector<RectDef> windows = {
        {-68.f, -22.f, -46.f, -5.f, 3.5f}, // rear window 1
        {-40.f, -22.f, -18.f, -5.f, 3.5f}, // rear window 2
        {-13.f, -24.f,  10.f, 24.f, 3.0f}, // central tall black door
        { 18.f, -22.f,  40.f, -5.f, 3.5f}, // front-side window
        { 48.f, -24.f,  72.f, 10.f, 4.0f}  // tall front windshield
    };
    for (std::size_t i = 0; i < windows.size(); ++i) {
        const auto& w = windows[i];
        ShapeSpec win;
        win.size = boxSize;
        win.name = prefix + "_win_" + std::to_string(i);
        win.geometry = ShapeGeometry::Path;
        win.path = transformPath(makeRoundedRectPath(w.x0, w.y0, w.x1, w.y1, w.r), angleDeg, kBusScale);
        win.fillColor = "#06080E";
        scene.shape(win).position(cx, cy).opacity(opacityMult).alive(inFrame, outFrame);
    }

    // 7. Two wheels (thick metallic-grey outer tire ring + dark inner hub, matching ref_01)
    for (int w = 0; w < 2; ++w) {
        const float wx = (w == 0) ? -48.f : 48.f;
        const float wy = 24.f;

        ShapeSpec wheelOuter;
        wheelOuter.size = boxSize;
        wheelOuter.name = prefix + "_wheel_outer_" + std::to_string(w);
        wheelOuter.geometry = ShapeGeometry::Path;
        wheelOuter.path = transformPath(makeCirclePath(wx, wy, 14.5f), angleDeg, kBusScale);
        wheelOuter.fillColor = "#73787E";
        scene.shape(wheelOuter).position(cx, cy).opacity(opacityMult).alive(inFrame, outFrame);

        ShapeSpec wheelInner;
        wheelInner.size = boxSize;
        wheelInner.name = prefix + "_wheel_inner_" + std::to_string(w);
        wheelInner.geometry = ShapeGeometry::Path;
        wheelInner.path = transformPath(makeCirclePath(wx, wy, 7.2f), angleDeg, kBusScale);
        wheelInner.fillColor = "#080A0F";
        scene.shape(wheelInner).position(cx, cy).opacity(opacityMult).alive(inFrame, outFrame);
    }
}

void addLocalizedSpecks(TemplateScene& scene) {
    struct SpeckDef {
        float dx, dy;
        float radius;
        const char* color;
        int inFrame, outFrame;
        float driftX, driftY;
    };
    const std::vector<SpeckDef> specks = {
        // Scene A specks around the bus (frames 0..19)
        {-240.f,  85.f, 1.8f, "#CBD5E1",  0, 19, -5.f,  6.f},
        { 195.f,  25.f, 1.6f, "#E2E8F0",  0, 19,  6.f, -4.f},
        {-150.f, -95.f, 1.5f, "#94A3B8",  0, 19, -4.f, -5.f},
        { 280.f, -60.f, 1.7f, "#CBD5E1",  0, 19,  5.f,  6.f},
        // Scene B specks around the thermometer (frames 20..59)
        { -64.f,  38.f, 1.6f, "#E2E8F0", 20, 59, -6.f,  8.f},
        {  82.f,  46.f, 1.8f, "#FEF08A", 20, 59,  7.f,  7.f},
        { -52.f, -74.f, 1.7f, "#CBD5E1", 28, 56, -5.f, -9.f},
        {  68.f, -82.f, 1.6f, "#FEF08A", 30, 56,  6.f, -8.f},
        {  38.f, 118.f, 1.9f, "#F8FAFC", 34, 54,  4.f,  8.f},
        {  96.f,  14.f, 1.5f, "#E2E8F0", 34, 54,  8.f,  5.f},
        // Scene C specks around the yellow dot & line graph (frames 60..139)
        {-125.f, 175.f, 1.8f, "#CBD5E1", 60, 139, -8.f, 10.f},
        { -82.f, 142.f, 1.6f, "#E2E8F0", 60, 139, -6.f,  8.f},
        {-245.f, -52.f, 1.9f, "#94A3B8", 62, 139, -9.f, -8.f},
        {  78.f,  84.f, 1.6f, "#E2E8F0", 78, 139,  8.f,  9.f},
        { 148.f, -46.f, 1.7f, "#CBD5E1", 92, 139, 10.f, -6.f},
        { 220.f,  64.f, 1.6f, "#94A3B8", 105, 139, 8.f,  7.f}
    };

    for (std::size_t i = 0; i < specks.size(); ++i) {
        const auto& s = specks[i];
        ShapeSpec dot;
        dot.size = {s.radius * 2.f, s.radius * 2.f};
        dot.name = "grain_speck_" + std::to_string(i);
        dot.geometry = ShapeGeometry::Ellipse;
        dot.fillColor = s.color;
        scene.shape(dot)
            .position(kCenterX + s.dx, kCenterY + s.dy)
            .opacity(0.68f)
            .alive(s.inFrame, s.outFrame)
            .animatePosition(s.inFrame, s.outFrame - s.inFrame,
                             Vector3(-s.driftX, -s.driftY, 0.f), Easing::linear());
    }
}

} // namespace

int main(int argc, char** argv) {
    const std::string outPath = argc > 1
        ? argv[1]
        : "ChrononTemplate/out/svg_grain_perlin_showcase/svg_grain_perlin_showcase.plan.json";
    try {
        std::filesystem::path p(outPath);
        if (p.has_parent_path()) {
            std::filesystem::create_directories(p.parent_path());
        }

        ShowcaseBackend backend;
        RenderPlanContentHost host({
            .createText = [&](const TextRequest& r) { return backend.createText(r); },
            .createImage = [&](const ImageRequest& r) { return backend.createImage(r); },
            .createVideo = [&](const VideoRequest& r) { return backend.createVideo(r); },
            .createShape = [&](const ShapeRequest& r) { return backend.createShape(r); },
            .currentFingerprint = [&](const ContentId& id) { return backend.currentFingerprint(id); }
        });

        TemplateScene scene("svg_grain_perlin_showcase", kFps, host, kWidth, kHeight);
        scene.camera().setFov(53.14f);

        // ── 0. Pitch-black base with subtle Perlin atmospheric field
        ShapeSpec bg;
        bg.size = {kWidth, kHeight};
        bg.name = "black_perlin_canvas";
        bg.geometry = ShapeGeometry::Rectangle;
        bg.fillColor = "#000000";
        scene.shape(bg).position(kCenterX, kCenterY).alive(0, kTotalFrames - 1);

        // ── 1. Scene A: Vector Bus + Wide Dashed Line (ref_01: frames 0..9, ref_02: frames 10..19)
        const std::vector<ShapePathCommand> dashedPath = {
            ShapePathCommand::moveTo(-430.f, 92.f),
            ShapePathCommand::lineTo( 430.f, 92.f)
        };
        addGlowingStrokePath(scene, "bus_ground_dashed_line", {960.f, 240.f},
                             kCenterX, kCenterY, dashedPath,
                             "#94A3B8", "#475569", 1.4f, 0, 9,
                             std::nullopt, {115.f, 88.f});

        // ref_01: Horizontal bus (frames 0..9)
        addVectorBus(scene, "bus_flat", kCenterX, kCenterY, 0.f, 1.0f, 0, 9);
        // ref_02: Clockwise-tilted bus (~18 deg CW, slightly dimmed, frames 10..19)
        addVectorBus(scene, "bus_tilted", kCenterX, kCenterY - 6.f, 18.f, 0.78f, 10, 19);

        // ── 2. Scene B: Thermometer + Rising/Receding Mercury (ref_03..ref_06: frames 20..59)
        // Note: In ChrononMotion .position(x, y), +Y is UP on screen, while in local Path
        // coordinates +Y is DOWN on screen. So local path (0, +28) inside a path centered at
        // (kCenterX, kCenterY) corresponds to screen position (kCenterX, kCenterY - 28.f)!
        const float thermoBulbScreenX = kCenterX;
        const float thermoBulbScreenY = kCenterY - 28.f;

        // Warm amber/yellow ambient glow behind the thermometer bulb (frames 20..59)
        addSoftEllipseGlow(scene, "thermo_bulb_halo",
                           thermoBulbScreenX, thermoBulbScreenY, 120.f, 120.f,
                           "#CA8A04", 0.22f, 20, 59);

        // Extra warm glow around the upper thermometer tube during peak (ref_04..ref_05: frames 30..52)
        addSoftEllipseGlow(scene, "thermometer_peak_halo",
                           kCenterX, kCenterY + 6.f, 110.f, 160.f,
                           "#FACC15", 0.16f, 32, 52);

        // Red thermometer outline (rounded vertical tube + circular bulb contour)
        // Important: We do NOT append ShapePathCommand::close() so Chronon3D renders the
        // contour purely as an unfilled red stroke without filling the interior white!
        constexpr float kBulbR = 30.f;
        constexpr float kTubeW = 14.f;
        constexpr float kTubeTopY = -66.f;
        constexpr float kBulbLocalY = 28.f;
        constexpr float kJoinY = kBulbLocalY - 26.5f; // sqrt(30^2 - 14^2) = 26.53
        const std::vector<ShapePathCommand> thermoOutlinePath = {
            ShapePathCommand::moveTo(-kTubeW, kJoinY),
            ShapePathCommand::lineTo(-kTubeW, kTubeTopY),
            ShapePathCommand::cubicTo(-kTubeW, kTubeTopY - 12.f, kTubeW, kTubeTopY - 12.f, kTubeW, kTubeTopY),
            ShapePathCommand::lineTo( kTubeW, kJoinY),
            // Right-side bulb arc down to bottom (0, 28 + 30 = 58)
            ShapePathCommand::cubicTo(kBulbR + 4.f, kBulbLocalY - 12.f, kBulbR + 4.f, kBulbLocalY + 26.f, 0.f, kBulbLocalY + kBulbR),
            // Left-side bulb arc back up to (-kTubeW, kJoinY)
            ShapePathCommand::cubicTo(-kBulbR - 4.f, kBulbLocalY + 26.f, -kBulbR - 4.f, kBulbLocalY - 12.f, -kTubeW, kJoinY)
        };
        addGlowingStrokePath(scene, "thermometer_red_outline", {220.f, 260.f},
                             kCenterX, kCenterY, thermoOutlinePath,
                             "#991B1B", "#DC2626", 4.2f, 20, 59);

        // Animated yellow mercury stem inside the thermometer tube (frames 20..59)
        // Starts inside the bulb at local (0, +28) and rises up to (0, -52) via Trim!
        const std::vector<ShapePathCommand> mercuryPath = {
            ShapePathCommand::moveTo(0.f, kBulbLocalY),
            ShapePathCommand::lineTo(0.f, -52.f)
        };
        const ShapeTrimSpec mercuryTrim{
            .start = 0.f,
            .end = 0.04f,
            .offset = 0.f,
            .easing = "in_out_cubic",
            .keyframes = {
                {20, 0.f, 0.04f, 0.f},
                {26, 0.f, 0.06f, 0.f}, // ref_03 (frame 25): low in bulb
                {35, 0.f, 0.56f, 0.f}, // ref_04 (frame 35): rising mid-way
                {45, 0.f, 0.88f, 0.f}, // ref_05 (frame 45): peak near top of tube
                {55, 0.f, 0.08f, 0.f}, // ref_06 (frame 55): receded back to bulb
                {59, 0.f, 0.02f, 0.f}
            }
        };
        addGlowingStrokePath(scene, "thermometer_mercury_stem", {220.f, 260.f},
                             kCenterX, kCenterY, mercuryPath,
                             "#EAB308", "#FEF08A", 14.f, 20, 59, mercuryTrim);

        // Inner yellow Perlin-textured bulb of the thermometer (frames 20..59)
        ShapeSpec thermoBulbDot;
        thermoBulbDot.size = {38.f, 38.f};
        thermoBulbDot.name = "thermo_yellow_perlin_bulb";
        thermoBulbDot.geometry = ShapeGeometry::Ellipse;
        thermoBulbDot.fillColor = "#FACC15";
        thermoBulbDot.field = makePerlinField(512, 3.6f, 0.24f);
        thermoBulbDot.fieldRamp = makeThreeStopRamp("#A16207", "#EAB308", "#FEF08A");
        thermoBulbDot.fieldDrift = chronon3d::Vec2{0.40f, -0.28f};
        scene.shape(thermoBulbDot).position(thermoBulbScreenX, thermoBulbScreenY).alive(20, 59);

        // ── 3. Scene C: Yellow Perlin-Textured Node + '^' Line Graph via Trim (ref_07..ref_14: frames 60..139)
        // In ref_07..ref_14, the yellow Perlin dot sits at (-88, +14) relative to center,
        // and the '^' line graph passes just tangent to its lower-right edge!
        const float graphNodeScreenX = kCenterX - 88.f;
        const float graphNodeScreenY = kCenterY + 14.f;

        addSoftEllipseGlow(scene, "graph_yellow_node_halo",
                           graphNodeScreenX, graphNodeScreenY, 130.f, 130.f,
                           "#CA8A04", 0.20f, 60, kTotalFrames - 1);

        ShapeSpec graphYellowDot;
        graphYellowDot.size = {44.f, 44.f};
        graphYellowDot.name = "graph_yellow_perlin_dot";
        graphYellowDot.geometry = ShapeGeometry::Ellipse;
        graphYellowDot.fillColor = "#FACC15";
        graphYellowDot.field = makePerlinField(512, 3.6f, 0.24f);
        graphYellowDot.fieldRamp = makeThreeStopRamp("#A16207", "#EAB308", "#FEF08A");
        graphYellowDot.fieldDrift = chronon3d::Vec2{0.42f, -0.30f};
        scene.shape(graphYellowDot).position(graphNodeScreenX, graphNodeScreenY).alive(60, kTotalFrames - 1);

        // Multi-pass glowing '^' line graph centered at (kCenterX, kCenterY):
        // Starts at (-280, +165) [bottom-left], passes tangent to the lower-right of the
        // yellow dot at (-88, -14 in local path coords) up to the peak at (+108, -155),
        // then descends to (+276, +158) [bottom-right], matching ref_07..ref_14!
        const std::vector<ShapePathCommand> graphPath = {
            ShapePathCommand::moveTo(-280.f,  165.f),
            ShapePathCommand::lineTo( 108.f, -155.f),
            ShapePathCommand::lineTo( 276.f,  158.f)
        };
        const ShapeTrimSpec graphTrim{
            .start = 0.f,
            .end = 0.04f,
            .offset = 0.f,
            .easing = "linear",
            .keyframes = {
                { 60, 0.f, 0.04f, 0.f},
                { 65, 0.f, 0.16f, 0.f}, // ref_07: short segment at bottom-left
                { 75, 0.f, 0.36f, 0.f}, // ref_08: passing lower-right edge of yellow dot
                { 85, 0.f, 0.59f, 0.f}, // ref_09: reaches top-right peak vertex
                { 95, 0.f, 0.69f, 0.f}, // ref_10: turns corner, starts descending right
                {105, 0.f, 0.80f, 0.f}, // ref_11: halfway down right slope
                {115, 0.f, 0.90f, 0.f}, // ref_12: three-quarters down right slope
                {125, 0.f, 1.00f, 0.f}, // ref_13: full '^' graph complete
                {139, 0.f, 1.00f, 0.f}  // ref_14: holds with animated Perlin + grain specks
            }
        };
        addGlowingStrokePath(scene, "line_graph", {680.f, 440.f},
                             kCenterX, kCenterY, graphPath,
                             "#CBD5E1", "#38BDF8", 5.2f, 60, kTotalFrames - 1, graphTrim);

        // ── 4. Localized animated grain/dust specks + subtle global FloatingDust
        addLocalizedSpecks(scene);

        effects::EffectSpec dustSpec{};
        dustSpec.intensity = 0.35f;
        dustSpec.opacity = 0.32f;
        dustSpec.seed = 901;
        dustSpec.color = "#94A3B8";
        dustSpec.startFrame = 0;
        dustSpec.endFrame = kTotalFrames - 1;
        (void)effects::addEffect(scene, effects::EffectKind::FloatingDust, dustSpec);

        auto plan = lowerToRenderPlan(scene, host, "svg_grain_perlin_showcase_v2",
                                      "svg_grain_perlin_showcase.mp4");
        plan.canvas.duration = chronon3d::Frame(kTotalFrames);
        plan.output.format = chronon3d::render_plan::OutputFormat::Mp4;

        std::ofstream out(outPath, std::ios::binary | std::ios::trunc);
        if (!out || !(out << chrononmotion::motion::renderPlanToJson(plan) << '\n')) {
            throw std::runtime_error("could not write plan: " + outPath);
        }
        std::cout << "Wrote " << outPath << " with " << plan.layers.size()
                  << " layers, " << kTotalFrames << " frames at " << kFps << " fps\n";
    } catch (const std::exception& e) {
        std::cerr << "svg_grain_perlin_showcase emitter error: " << e.what() << '\n';
        return 1;
    }
    return 0;
}
