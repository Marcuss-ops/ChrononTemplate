// Particle Lab — nine native RenderPlan V3 experiments for the Chronon3D
// particle emitter. Every motion is authored through the canonical CPU sampler
// (`chronon3d/scene/model/shape/particles.hpp`): the curl-flow displacement and
// twinkle fields here are the same values the renderer evaluates per frame, so
// these plans are deterministic and seek-safe.
//
// Usage: chronontemplate_emit_particle_lab [output-dir]
#include "chronontemplate/core/NativePrimitives.hpp"

#include <nlohmann/json.hpp>

#include <array>
#include <cmath>
#include <filesystem>
#include <fstream>
#include <initializer_list>
#include <iostream>
#include <string>
#include <utility>
#include <vector>

namespace {

using nlohmann::json;
using chronontemplate::native::Camera;
using chronontemplate::native::Material;
using chronontemplate::native::Particles;
using chronontemplate::native::TemplateComposition;

constexpr int kWidth = 1920;
constexpr int kHeight = 1080;
constexpr int kFps = 24;
constexpr int kFrames = 240;
constexpr int kYouTubeFps = 30;
constexpr int kYouTubeFrames = 180;
constexpr double kPi = 3.14159265358979323846;

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

// ---------------------------------------------------------------------------
// YouTube FX — 6 second, 30 fps bumpers with a real 3D camera, baked
// transparent typography/light plates and two depth-separated particle planes.
// The color plate stays in screen space; titles, light and particles are
// projected by the camera.
// ---------------------------------------------------------------------------

json ytKey(int frame, const json& value) {
    return json{{"frame", frame}, {"value", value}};
}

struct YouTubeRecipe {
    std::string slug;
    std::string background;
    std::array<float, 4> primary;
    std::array<float, 4> secondary;
    int motion{0}; ///< 0 push, 1 lateral orbit, 2 pull-out
    float lightX0{0.f};
    float lightX1{0.f};
    float lightY{280.f};
    float lightZ{-180.f};
    unsigned seed{0};
};

std::string youtubeAsset(const YouTubeRecipe& recipe, const std::string& suffix) {
    return "assets/youtube_fx/" + recipe.slug + suffix;
}

json youtubeImage(const std::string& id, const std::string& asset,
                  float x, float y, float z, float width, float height,
                  float opacity, const char* blend) {
    return json{
        {"id", id},
        {"type", "image"},
        {"asset", asset},
        {"enable_3d", true},
        {"position", {x, y, z}},
        {"size", {width, height}},
        {"fit", "contain"},
        {"blend_mode", blend},
        {"opacity", opacity},
        {"start_frame", 0},
        {"duration_frames", kYouTubeFrames},
    };
}

json youtubeRamp(const YouTubeRecipe& recipe) {
    return stops({
        {0.00f, recipe.secondary[0], recipe.secondary[1], recipe.secondary[2], 0.00f},
        {0.12f, recipe.primary[0], recipe.primary[1], recipe.primary[2], 0.90f},
        {0.76f, recipe.secondary[0], recipe.secondary[1], recipe.secondary[2], 0.52f},
        {1.00f, recipe.primary[0], recipe.primary[1], recipe.primary[2], 0.00f},
    });
}

json youtubeAtmosphere(const YouTubeRecipe& recipe) {
    json layer = youtubeImage("atmosphere", youtubeAsset(recipe, "_glow.png"),
                              0.f, 0.f, -700.f, 2400.f, 1600.f, 0.22f, "screen");
    layer["animation"] = json{{"tracks", json::array({
        json{{"property", "opacity"}, {"easing", "out_cubic"},
             {"keyframes", json::array({ytKey(0, 0.0), ytKey(24, 0.20),
                                        ytKey(kYouTubeFrames - 1, 0.12)})}},
    })}};
    return layer;
}

json youtubeBeam(const YouTubeRecipe& recipe) {
    json layer = youtubeImage("light_beam", youtubeAsset(recipe, "_beam.png"),
                              -650.f, -20.f, -430.f, 900.f, 2200.f, 0.28f, "screen");
    layer["animation"] = json{{"tracks", json::array({
        json{{"property", "position_x"}, {"easing", "in_out_sine"},
             {"keyframes", json::array({ytKey(0, -700.0), ytKey(kYouTubeFrames - 1, -600.0)})}},
        json{{"property", "opacity"}, {"easing", "out_cubic"},
             {"keyframes", json::array({ytKey(0, 0.0), ytKey(30, 0.30),
                                        ytKey(kYouTubeFrames - 1, 0.18)})}},
    })}};
    return layer;
}

json youtubeLightSource(const YouTubeRecipe& recipe) {
    json layer = youtubeImage("light_source", youtubeAsset(recipe, "_glow.png"),
                              recipe.lightX0, recipe.lightY, recipe.lightZ,
                              850.f, 850.f, 1.0f, "add");
    layer["animation"] = json{{"tracks", json::array({
        json{{"property", "position_x"}, {"easing", "in_out_sine"},
             {"keyframes", json::array({ytKey(0, recipe.lightX0),
                                        ytKey(92, recipe.lightX1),
                                        ytKey(kYouTubeFrames - 1, recipe.lightX1 + 36.f)})}},
        json{{"property", "position_y"}, {"easing", "in_out_sine"},
             {"keyframes", json::array({ytKey(0, recipe.lightY + 22.f),
                                        ytKey(92, recipe.lightY),
                                        ytKey(kYouTubeFrames - 1, recipe.lightY - 12.f)})}},
        json{{"property", "opacity"}, {"easing", "out_cubic"},
             {"keyframes", json::array({ytKey(0, 0.0), ytKey(18, 0.94),
                                        ytKey(kYouTubeFrames - 1, 0.80)})}},
    })}};
    return layer;
}

json youtubeTitleCard(const YouTubeRecipe& recipe) {
    json layer = youtubeImage("title_card", youtubeAsset(recipe, "_title.png"),
                              0.f, 0.f, 0.f, 1600.f, 700.f, 1.0f, "add");
    layer["animation"] = json{{"tracks", json::array({
        json{{"property", "opacity"}, {"easing", "out_cubic"},
             {"keyframes", json::array({ytKey(0, 0.0), ytKey(18, 1.0),
                                        ytKey(kYouTubeFrames - 1, 1.0)})}},
        json{{"property", "position"}, {"easing", "out_cubic"},
             {"keyframes", json::array({ytKey(0, json::array({0.0, -26.0, 0.0})),
                                        ytKey(24, json::array({0.0, 0.0, 0.0})),
                                        ytKey(kYouTubeFrames - 1, json::array({0.0, 8.0, 0.0}))})}},
    })}};
    return layer;
}

json youtubeParticles(const YouTubeRecipe& recipe, const std::string& id, int count,
                      unsigned seed, float z, float sizeMin, float sizeMax,
                      bool bokeh, float flowStrength, float twinkle, float gravity) {
    json layer = Particles::emitterLayer(
        id, count, seed, kYouTubeFrames, {2400.f, 1500.f}, {-6.f, -3.f}, {6.f, 3.f},
        {6.f, 12.f}, {sizeMin, sizeMax}, youtubeRamp(recipe),
        {0.f, 0.f, z}, 0, gravity, 0.f,
        {flowStrength, 0.006f, 0.16f}, {twinkle, 0.24f});
    json& emitter = layer["particle_emitter"];
    emitter["environment"] = true;
    emitter["depth_range"] = {0.15f, 1.0f};
    emitter["bokeh"] = bokeh;
    emitter["blend_mode"] = "screen";
    return layer;
}

json youtubeCameraSamples(const YouTubeRecipe& recipe) {
    json samples = json::array();
    for (int frame = 0; frame < kYouTubeFrames; ++frame) {
        const double t = static_cast<double>(frame) / static_cast<double>(kYouTubeFrames - 1);
        const double eased = t * t * (3.0 - 2.0 * t);
        double x = 0.0, y = 0.0, z = -2200.0, yaw = 0.0, fov = 40.0;
        if (recipe.motion == 0) {
            x = -50.0 + 100.0 * eased;
            y = 8.0 * std::sin(kPi * t);
            z = -2350.0 + 520.0 * eased;
            yaw = -2.5 + 5.0 * eased;
            fov = 39.0;
        } else if (recipe.motion == 1) {
            x = -180.0 + 360.0 * eased;
            y = 18.0 * std::sin(kPi * t);
            z = -2200.0 + 100.0 * std::sin(kPi * t);
            yaw = -4.5 + 9.0 * eased;
            fov = 42.0;
        } else {
            x = 40.0 - 80.0 * eased;
            y = 0.0;
            z = -1850.0 - 520.0 * eased;
            yaw = 2.5 - 5.0 * eased;
            fov = 39.0;
        }
        const json camera = Camera::perspective(
            {static_cast<float>(x), static_cast<float>(y), static_cast<float>(z)},
            {0.f, static_cast<float>(yaw), 0.f}, static_cast<float>(fov), 0.1f, 10000.f, 1.f);
        samples.push_back(json{{"frame", frame}, {"camera", camera}});
    }
    return samples;
}

json buildYouTubePlan(const YouTubeRecipe& recipe) {
    const json cameraSamples = youtubeCameraSamples(recipe);

    json background = json{
        {"id", "background"},
        {"type", "color"},
        {"color", Material::rgba(recipe.background)},
        {"size", {kWidth, kHeight}},
        {"screen_space", true},
        {"start_frame", 0},
        {"duration_frames", kYouTubeFrames},
        {"effects", json::array({
            json{{"type", "vignette"}, {"radius", 0.70f}, {"softness", 0.65f}, {"amount", 0.44f}},
            json{{"type", "noise"}, {"amount", 0.025f}, {"seed", recipe.seed}, {"size", 1.4f}},
        })},
    };

    json layers = json::array({
        background,
        youtubeAtmosphere(recipe),
        youtubeParticles(recipe, "dust_far", 420, recipe.seed, -650.f, 1.2f, 4.8f, true, 30.f, 0.28f, 0.f),
        youtubeBeam(recipe),
        youtubeParticles(recipe, "bokeh_mid", 36, recipe.seed + 31u, -380.f, 10.f, 36.f, true, 26.f, 0.18f, 0.f),
        youtubeLightSource(recipe),
        youtubeParticles(recipe, "bokeh_near", 72, recipe.seed + 17u, -180.f, 26.f, 88.f, true, 40.f, 0.12f, 0.f),
        youtubeTitleCard(recipe),
    });

    json plan = TemplateComposition::renderPlan(
        recipe.slug, kWidth, kHeight, kYouTubeFps, kYouTubeFrames, layers,
        cameraSamples.front().at("camera"), cameraSamples);
    plan["output"]["path"] = recipe.slug + ".mp4";
    return plan;
}

std::vector<std::pair<std::string, json>> youtubeExperiments() {
    const std::vector<YouTubeRecipe> recipes = {
        {"07_youtube_light_intro", "#05070C",
         {0.30f, 0.82f, 1.00f, 1.0f}, {1.00f, 0.48f, 0.18f, 1.0f}, 0,
         540.f, -440.f, 260.f, -180.f, 7101u},
        {"08_youtube_particle_reveal", "#0B0710",
         {1.00f, 0.25f, 0.62f, 1.0f}, {0.28f, 0.90f, 1.00f, 1.0f}, 1,
         -540.f, 520.f, 240.f, -220.f, 8207u},
        {"09_youtube_light_outro", "#0A0505",
         {1.00f, 0.58f, 0.18f, 1.0f}, {1.00f, 0.12f, 0.12f, 1.0f}, 2,
         360.f, -260.f, 280.f, -160.f, 9301u},
    };
    std::vector<std::pair<std::string, json>> out;
    for (const YouTubeRecipe& recipe : recipes) {
        out.emplace_back(recipe.slug + ".plan.json", buildYouTubePlan(recipe));
    }
    return out;
}

} // namespace

int main(int argc, char** argv) {
    const std::filesystem::path out = argc > 1 ? argv[1] : "particle_lab_plans";
    std::filesystem::create_directories(out);

    std::vector<std::pair<std::string, json>> experiments = {
        {"01_cinematic_dust.plan.json", cinematicDust()},
        {"02_embers.plan.json", embers()},
        {"03_ash_fall.plan.json", ashFall()},
        {"04_bokeh_orbs.plan.json", bokehOrbs()},
        {"05_chalk_burst.plan.json", chalkBurst()},
        {"06_light_motes.plan.json", lightMotes()},
    };
    for (auto& experiment : youtubeExperiments()) experiments.push_back(std::move(experiment));
    for (const auto& [name, plan] : experiments) {
        std::ofstream file(out / name);
        file << plan.dump(2) << "\n";
        std::error_code error;
        const auto bytes = std::filesystem::file_size(out / name, error);
        std::cout << name << " " << bytes << " bytes, "
                  << plan["layers"].size() << " layers, "
                  << plan["canvas"].at("duration_frames").get<int>() << " frames\n";
    }
    return 0;
}
