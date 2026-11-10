// Particle Lab — six native RenderPlan V3 experiments for the Chronon3D
// particle emitter. Every motion is authored through the canonical CPU sampler
// (`chronon3d/scene/model/shape/particles.hpp`): the curl-flow displacement and
// twinkle fields here are the same values the renderer evaluates per frame, so
// these plans are deterministic and seek-safe.
//
// Usage: chronontemplate_emit_particle_lab [output-dir]
#include "chronontemplate/core/NativePrimitives.hpp"

#include <nlohmann/json.hpp>

#include <array>
#include <filesystem>
#include <fstream>
#include <initializer_list>
#include <iostream>
#include <string>
#include <utility>
#include <vector>

namespace {

using nlohmann::json;
using chronontemplate::native::Material;
using chronontemplate::native::Particles;
using chronontemplate::native::TemplateComposition;

constexpr int kWidth = 1920;
constexpr int kHeight = 1080;
constexpr int kFps = 24;
constexpr int kFrames = 240;

json stops(std::initializer_list<std::array<float, 5>> rows) {
    json out = json::array();
    for (const auto& row : rows) {
        out.push_back({{"position", row[0]},
                       {"color", {row[1], row[2], row[3], row[4]}}});
    }
    return out;
}

struct Emitter {
    std::string id;
    int count{0};
    unsigned seed{0};
    float emitterWidth{0.f};
    float emitterHeight{0.f};
    float velocityMinX{0.f};
    float velocityMinY{0.f};
    float velocityMaxX{0.f};
    float velocityMaxY{0.f};
    float lifetimeMin{1.f};
    float lifetimeMax{1.f};
    float sizeMin{1.f};
    float sizeMax{1.f};
    json ramp{};
    float positionX{0.f}; ///< centre-relative, like the screen-space shape packs
    float positionY{0.f};
    float gravity{0.f};
    float turbulence{0.f};
    Particles::Flow flow{};
    Particles::Twinkle twinkle{};
    bool environment{false};
    float depthMin{0.f};
    float depthMax{1.f};
    bool bokeh{false};
    const char* blend{"normal"};
};

json emitterLayer(const Emitter& spec, int frames) {
    json layer = Particles::emitterLayer(
        spec.id, spec.count, spec.seed, frames,
        {spec.emitterWidth, spec.emitterHeight},
        {spec.velocityMinX, spec.velocityMinY},
        {spec.velocityMaxX, spec.velocityMaxY},
        {spec.lifetimeMin, spec.lifetimeMax},
        {spec.sizeMin, spec.sizeMax},
        spec.ramp,
        {spec.positionX, spec.positionY, 0.f},
        0, spec.gravity, spec.turbulence,
        spec.flow, spec.twinkle);
    // The lab uses the canvas pixel grid directly: screen-space layers take
    // centre-relative positions, so no camera is required and the samples are
    // not rescaled by the fallback 2.5D camera.
    layer["screen_space"] = true;
    layer["enable_3d"] = false;
    // Screen-space layers must not carry a 3-component transform: the decoder
    // treats an explicit z as 3D data and rejects it when enable_3d is false.
    layer["position"] = {spec.positionX, spec.positionY};
    json& emitter = layer["particle_emitter"];
    emitter["environment"] = spec.environment;
    emitter["depth_range"] = {spec.depthMin, spec.depthMax};
    emitter["bokeh"] = spec.bokeh;
    emitter["blend_mode"] = spec.blend;
    return layer;
}

json background(const std::string& hex) {
    return {{"id", "bg"},
            {"type", "color"},
            {"color", Material::rgba(hex)},
            {"size", {kWidth, kHeight}},
            // The legacy particle composition places screen-space color
            // plates in absolute canvas coordinates; centre the plate on the
            // canvas explicitly (particle samples remain centre-relative).
            {"position", {kWidth / 2, kHeight / 2}},
            {"screen_space", true},
            {"start_frame", 0},
            {"duration_frames", kFrames}};
}

json assemble(const std::string& id, const std::string& backgroundHex,
              const json& particles, int frames = kFrames) {
    json plan = TemplateComposition::renderPlan(
        id, kWidth, kHeight, kFps, frames,
        json::array({background(backgroundHex), particles}));
    plan["output"]["path"] = id + ".mp4";
    return plan;
}

// 01 — cinematic dust: three depth bands, cool far motes, warm near motes.
json cinematicDust() {
    Emitter spec;
    spec.id = "cinematic_dust";
    spec.count = 320;
    spec.seed = 9137;
    spec.emitterWidth = 2200.f;
    spec.emitterHeight = 1380.f;
    spec.velocityMinX = -7.f;
    spec.velocityMinY = -10.f;
    spec.velocityMaxX = 7.f;
    spec.velocityMaxY = 2.f;
    spec.lifetimeMin = 6.f;
    spec.lifetimeMax = 14.f;
    spec.sizeMin = 1.2f;
    spec.sizeMax = 7.5f;
    spec.ramp = stops({
        {0.00f, 0.74f, 0.82f, 0.96f, 0.00f},
        {0.18f, 0.74f, 0.82f, 0.96f, 0.48f},
        {0.70f, 0.94f, 0.84f, 0.65f, 0.55f},
        {1.00f, 0.94f, 0.84f, 0.65f, 0.00f},
    });
    spec.flow = {26.f, 0.006f, 0.18f};
    spec.twinkle = {0.35f, 0.22f};
    spec.environment = true;
    spec.depthMin = 0.20f;
    spec.depthMax = 1.00f;
    spec.bokeh = true;
    spec.blend = "screen";
    return assemble("01_cinematic_dust", "#07090D", emitterLayer(spec, kFrames));
}

// 02 — embers: negative gravity lifts hot motes, fast twinkle sells the burn.
json embers() {
    Emitter spec;
    spec.id = "embers";
    spec.count = 180;
    spec.seed = 2219;
    spec.emitterWidth = 900.f;
    spec.emitterHeight = 140.f;
    spec.positionY = 390.f;
    spec.velocityMinX = -12.f;
    spec.velocityMinY = -46.f;
    spec.velocityMaxX = 12.f;
    spec.velocityMaxY = -14.f;
    spec.lifetimeMin = 1.6f;
    spec.lifetimeMax = 4.2f;
    spec.sizeMin = 0.7f;
    spec.sizeMax = 3.2f;
    spec.ramp = stops({
        {0.00f, 1.00f, 0.78f, 0.36f, 0.00f},
        {0.10f, 1.00f, 0.62f, 0.18f, 0.95f},
        {0.75f, 1.00f, 0.30f, 0.05f, 0.70f},
        {1.00f, 0.70f, 0.10f, 0.02f, 0.00f},
    });
    spec.gravity = -6.f;
    spec.flow = {16.f, 0.008f, 0.50f};
    spec.twinkle = {0.70f, 1.40f};
    spec.environment = true;
    spec.depthMin = 0.25f;
    spec.depthMax = 1.00f;
    spec.bokeh = true;
    spec.blend = "add";
    return assemble("02_embers", "#0A0604", emitterLayer(spec, kFrames));
}

// 03 — ash fall: slow, cool, low-contrast; the flow makes it drift sideways.
json ashFall() {
    Emitter spec;
    spec.id = "ash_fall";
    spec.count = 240;
    spec.seed = 4073;
    spec.emitterWidth = 2200.f;
    spec.emitterHeight = 180.f;
    spec.positionY = -470.f;
    spec.velocityMinX = -14.f;
    spec.velocityMinY = 18.f;
    spec.velocityMaxX = 14.f;
    spec.velocityMaxY = 55.f;
    spec.lifetimeMin = 5.f;
    spec.lifetimeMax = 11.f;
    spec.sizeMin = 1.f;
    spec.sizeMax = 5.f;
    spec.ramp = stops({
        {0.00f, 0.70f, 0.72f, 0.76f, 0.00f},
        {0.15f, 0.70f, 0.72f, 0.76f, 0.32f},
        {0.85f, 0.82f, 0.83f, 0.86f, 0.26f},
        {1.00f, 0.82f, 0.83f, 0.86f, 0.00f},
    });
    spec.gravity = 2.f;
    spec.flow = {22.f, 0.005f, 0.12f};
    spec.twinkle = {0.25f, 0.30f};
    spec.environment = true;
    spec.depthMin = 0.30f;
    spec.depthMax = 1.00f;
    spec.bokeh = true;
    spec.blend = "screen";
    return assemble("03_ash_fall", "#0B0C0F", emitterLayer(spec, kFrames));
}

// 04 — bokeh orbs: large defocused discs with a slow curl drift.
json bokehOrbs() {
    Emitter spec;
    spec.id = "bokeh_orbs";
    spec.count = 48;
    spec.seed = 6113;
    spec.emitterWidth = 2000.f;
    spec.emitterHeight = 1200.f;
    spec.velocityMinX = -4.f;
    spec.velocityMinY = -3.f;
    spec.velocityMaxX = 4.f;
    spec.velocityMaxY = 3.f;
    spec.lifetimeMin = 8.f;
    spec.lifetimeMax = 16.f;
    spec.sizeMin = 30.f;
    spec.sizeMax = 110.f;
    spec.ramp = stops({
        {0.00f, 0.95f, 0.72f, 0.40f, 0.00f},
        {0.20f, 0.95f, 0.72f, 0.40f, 0.20f},
        {0.70f, 0.52f, 0.70f, 0.98f, 0.16f},
        {1.00f, 0.52f, 0.70f, 0.98f, 0.00f},
    });
    spec.flow = {48.f, 0.003f, 0.08f};
    spec.twinkle = {0.20f, 0.15f};
    spec.environment = true;
    spec.depthMin = 0.15f;
    spec.depthMax = 1.00f;
    spec.bokeh = true;
    spec.blend = "screen";
    return assemble("04_bokeh_orbs", "#05070C", emitterLayer(spec, kFrames));
}

// 05 — chalk burst: a classroom puff that expands, falls and settles.
json chalkBurst() {
    Emitter spec;
    spec.id = "chalk_burst";
    spec.count = 160;
    spec.seed = 7319;
    spec.emitterWidth = 260.f;
    spec.emitterHeight = 80.f;
    spec.positionX = -200.f;
    spec.positionY = 20.f;
    spec.velocityMinX = -160.f;
    spec.velocityMinY = -130.f;
    spec.velocityMaxX = 160.f;
    spec.velocityMaxY = 120.f;
    spec.lifetimeMin = 0.7f;
    spec.lifetimeMax = 1.8f;
    spec.sizeMin = 0.7f;
    spec.sizeMax = 3.4f;
    spec.ramp = stops({
        {0.00f, 0.92f, 0.90f, 0.84f, 0.00f},
        {0.08f, 0.92f, 0.90f, 0.84f, 0.80f},
        {0.80f, 0.82f, 0.80f, 0.74f, 0.35f},
        {1.00f, 0.82f, 0.80f, 0.74f, 0.00f},
    });
    spec.gravity = 28.f;
    spec.flow = {6.f, 0.010f, 0.60f};
    spec.twinkle = {0.10f, 0.50f};
    spec.bokeh = false;
    spec.blend = "normal";
    return assemble("05_chalk_burst", "#0C1512", emitterLayer(spec, kFrames));
}

// 06 — light motes: tiny additive sparks with a strong shimmer.
json lightMotes() {
    Emitter spec;
    spec.id = "light_motes";
    spec.count = 90;
    spec.seed = 8429;
    spec.emitterWidth = 1600.f;
    spec.emitterHeight = 900.f;
    spec.velocityMinX = -2.f;
    spec.velocityMinY = -3.f;
    spec.velocityMaxX = 2.f;
    spec.velocityMaxY = 1.f;
    spec.lifetimeMin = 4.f;
    spec.lifetimeMax = 9.f;
    spec.sizeMin = 0.6f;
    spec.sizeMax = 2.2f;
    spec.ramp = stops({
        {0.00f, 1.00f, 0.88f, 0.58f, 0.00f},
        {0.12f, 1.00f, 0.88f, 0.58f, 0.95f},
        {0.85f, 1.00f, 0.72f, 0.30f, 0.75f},
        {1.00f, 1.00f, 0.72f, 0.30f, 0.00f},
    });
    spec.gravity = -0.4f;
    spec.flow = {34.f, 0.007f, 0.35f};
    spec.twinkle = {0.85f, 0.90f};
    spec.environment = true;
    spec.depthMin = 0.10f;
    spec.depthMax = 1.00f;
    spec.bokeh = false;
    spec.blend = "add";
    return assemble("06_light_motes", "#04050A", emitterLayer(spec, kFrames));
}

} // namespace

int main(int argc, char** argv) {
    const std::filesystem::path out = argc > 1 ? argv[1] : "particle_lab_plans";
    std::filesystem::create_directories(out);

    const std::vector<std::pair<std::string, json>> experiments = {
        {"01_cinematic_dust.plan.json", cinematicDust()},
        {"02_embers.plan.json", embers()},
        {"03_ash_fall.plan.json", ashFall()},
        {"04_bokeh_orbs.plan.json", bokehOrbs()},
        {"05_chalk_burst.plan.json", chalkBurst()},
        {"06_light_motes.plan.json", lightMotes()},
    };
    for (const auto& [name, plan] : experiments) {
        std::ofstream file(out / name);
        file << plan.dump(2) << "\n";
        std::error_code error;
        const auto bytes = std::filesystem::file_size(out / name, error);
        std::cout << name << " " << bytes << " bytes, "
                  << plan["layers"].size() << " layers, " << kFrames
                  << " frames\n";
    }
    return 0;
}
