// Emits the native tactical-fill canary: one already-projected territory ring,
// the dark grid, both glows, the white outline and the late title. The sample
// points live in catalog/maps/samples/ and are canvas-space data; this tool does
// not read GeoJSON or project anything.
//
//   chronontemplate_emit_tactical_fill [out.plan.json] [sample.json]
//
// Render a proof frame with:
//   chronon3d_cli render --plan <out.plan.json>
//     --assets-root ChrononTemplate --frame 60 --output <frame.png>

#include "chronontemplate/core/PlanLowering.hpp"
#include "chronontemplate/core/RenderPlanContentHost.hpp"
#include "chronontemplate/core/TemplateScene.hpp"
#include "chronontemplate/map/TacticalFillPack.hpp"
#include "chrononmotion/motion/RenderPlanEmission.hpp"

#include <nlohmann/json.hpp>

#include <cstdint>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <string>
#include <unordered_map>
#include <vector>

using namespace chronontemplate;
using chrononmotion::Vector2;
using chrononmotion::motion::ContentKind;

namespace {

constexpr float kDefaultWidth = 1920.f;
constexpr float kDefaultHeight = 1080.f;
constexpr float kFps = 30.f;
constexpr int kTotalFrames = 120;

class PlanBackend final : public ContentHost {
public:
    PlanBackend(float width, float height) : m_width(width), m_height(height) {}

    ContentHandle createText(const TextRequest& request) override {
        return make("text/" + request.text, ContentKind::Text,
                    {request.fontSize * 0.6f * static_cast<float>(request.text.size()),
                     request.fontSize * 1.25f});
    }
    ContentHandle createImage(const ImageRequest& request) override {
        return make(request.path, ContentKind::Image, {m_width, m_height});
    }
    ContentHandle createVideo(const VideoRequest& request) override {
        return make("video/" + request.path, ContentKind::Video, {m_width, m_height});
    }
    ContentHandle createShape(const ShapeRequest& request) override {
        return make("shape/" + request.name, ContentKind::Image, request.size);
    }
    std::string currentFingerprint(const ContentId& id) const override {
        const auto found = m_fingerprints.find(id);
        return found == m_fingerprints.end() ? std::string{} : found->second;
    }

private:
    float m_width;
    float m_height;
    std::uint64_t m_nextWireId{1};
    std::unordered_map<ContentId, std::string> m_fingerprints;

    ContentHandle make(std::string id, ContentKind kind, Vector2 size) {
        ContentHandle handle;
        handle.id = std::move(id);
        handle.wireId = m_nextWireId++;
        handle.kind = kind;
        handle.metrics.naturalSize = size;
        handle.metrics.anchor = Vector2(0.5f, 0.5f);
        handle.metrics.fingerprint = "tactical-fill:" + handle.id;
        m_fingerprints.emplace(handle.id, handle.metrics.fingerprint);
        return handle;
    }
};

struct Sample {
    float width{kDefaultWidth};
    float height{kDefaultHeight};
    std::string title{};
    std::string subtitle{};
    std::vector<TacticalFillRegion> regions;
};

Sample loadSample(const std::filesystem::path& path) {
    std::ifstream in(path, std::ios::binary);
    if (!in) throw std::runtime_error("could not open sample: " + path.string());
    nlohmann::json document;
    in >> document;
    if (document.value("schema", "") != "chronontemplate.tactical-fill-sample.v1")
        throw std::runtime_error("sample schema must be chronontemplate.tactical-fill-sample.v1");
    if (!document.contains("regions") || !document["regions"].is_array() ||
        document["regions"].empty())
        throw std::runtime_error("sample must contain at least one region");
    Sample sample;
    if (document.contains("canvas")) {
        if (!document["canvas"].is_array() || document["canvas"].size() != 2 ||
            !document["canvas"][0].is_number() || !document["canvas"][1].is_number())
            throw std::runtime_error("sample canvas must be [width, height]");
        sample.width = document["canvas"][0].get<float>();
        sample.height = document["canvas"][1].get<float>();
        if (!std::isfinite(sample.width) || !std::isfinite(sample.height) ||
            sample.width < 64.f || sample.height < 64.f ||
            sample.width > 8192.f || sample.height > 8192.f)
            throw std::runtime_error("sample canvas must be 64..8192 pixels");
    }
    if (document.contains("title")) {
        if (!document["title"].is_string())
            throw std::runtime_error("sample title must be a string");
        sample.title = document["title"].get<std::string>();
    }
    if (document.contains("subtitle")) {
        if (!document["subtitle"].is_string())
            throw std::runtime_error("sample subtitle must be a string");
        sample.subtitle = document["subtitle"].get<std::string>();
    }
    for (const auto& source : document["regions"]) {
        if (!source.contains("points") || !source["points"].is_array())
            throw std::runtime_error("every sample region needs a points array");
        TacticalFillRegion region;
        for (const auto& point : source["points"]) {
            if (!point.is_array() || point.size() != 2 ||
                !point[0].is_number() || !point[1].is_number())
                throw std::runtime_error("sample points must be [x, y] numbers");
            region.points.push_back(Vector2(point[0].get<float>(), point[1].get<float>()));
        }
        sample.regions.push_back(std::move(region));
    }
    return sample;
}

} // namespace

int main(int argc, char** argv) {
    const std::string outPath = argc > 1
        ? argv[1]
        : "ChrononTemplate/out/tactical_fill/tactical_fill.plan.json";
    const std::filesystem::path samplePath = argc > 2
        ? std::filesystem::path(argv[2])
        : std::filesystem::path(
              "ChrononTemplate/catalog/maps/samples/tactical_fill_jerusalem_sample.json");
    try {
        std::filesystem::path path(outPath);
        if (path.has_parent_path()) std::filesystem::create_directories(path.parent_path());

        const Sample sample = loadSample(samplePath);
        PlanBackend backend(sample.width, sample.height);
        RenderPlanContentHost host({
            .createText = [&](const TextRequest& request) { return backend.createText(request); },
            .createImage = [&](const ImageRequest& request) { return backend.createImage(request); },
            .createVideo = [&](const VideoRequest& request) { return backend.createVideo(request); },
            .createShape = [&](const ShapeRequest& request) { return backend.createShape(request); },
            .currentFingerprint = [&](const ContentId& id) { return backend.currentFingerprint(id); },
        });

        TemplateScene scene("tactical_fill_canary", kFps, host, sample.width, sample.height);
        TacticalFillSpec spec;
        spec.regions = sample.regions;
        spec.title = sample.title;
        spec.subtitle = sample.subtitle;
        spec.duration = kTotalFrames;
        spec.titleTypography.font = "assets/fonts/Inter-Bold.ttf";
        spec.titleTypography.fontSize = 64.f;
        spec.subtitleTypography.font = "assets/fonts/Inter-Regular.ttf";
        spec.subtitleTypography.fontSize = 28.f;
        (void)addTacticalFill(scene, spec);

        auto plan = lowerToRenderPlan(scene, host, "tactical_fill_canary",
                                      "tactical_fill_canary.mp4");
        plan.canvas.duration = chronon3d::Frame(kTotalFrames);
        plan.output.format = chronon3d::render_plan::OutputFormat::Mp4;
        // The composition is a flat canvas treatment. An explicit perspective
        // camera is not part of the contract here: dropping it lets the
        // renderer's 2D canvas camera place layer coordinates directly, which
        // is what every flat showcase plan does.
        plan.camera.reset();
        plan.camera_samples.reset();
        // TemplateScene authors positions around the canvas centre, while the
        // render plan reads every layer position — static or sampled — in
        // top-left canvas coordinates. The lowering already adds the centre to
        // the static position; resolved samples need the same conversion or
        // the whole composition is culled half a canvas away.
        for (auto& layer : plan.layers) {
            // A flat editorial plate is a screen-space composition: the
            // showcase plans use screen layers so canvas coordinates reach the
            // compositor directly, without a 3D camera between them.
            layer.screen_space = true;
            for (auto& transform : layer.transform_samples) {
                transform.position[0] += sample.width * 0.5f;
                transform.position[1] += sample.height * 0.5f;
            }
        }

        std::ofstream out(outPath, std::ios::binary | std::ios::trunc);
        if (!out || !(out << chrononmotion::motion::renderPlanToJson(plan) << '\n'))
            throw std::runtime_error("could not write plan: " + outPath);
        std::cout << "Wrote " << outPath << " with " << plan.layers.size() << " layers, "
                  << kTotalFrames << " frames at " << kFps << " fps\n";
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "tactical fill emitter error: " << error.what() << '\n';
        return 1;
    }
}
