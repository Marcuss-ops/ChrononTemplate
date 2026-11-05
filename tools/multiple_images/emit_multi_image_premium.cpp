// Emit the premium multi-image choreographies (duo/trio/quad/penta) as
// render-plan V3 JSON through the canonical TemplateScene -> RenderPlan
// lowering. The motion ids match MultiImagePack's premium choreographies.
#include "chronontemplate/core/PlanLowering.hpp"
#include "chronontemplate/core/RenderPlanContentHost.hpp"
#include "chronontemplate/core/TemplateScene.hpp"
#include "chronontemplate/multiple_images/MultiImagePack.hpp"

#include <chrononmotion/motion/RenderPlanEmission.hpp>

#include <filesystem>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <string>
#include <unordered_map>
#include <utility>
#include <vector>

namespace {

class BoardHost final : public chronontemplate::ContentHost {
public:
    chronontemplate::ContentHandle createText(const chronontemplate::TextRequest& request) override {
        return remember("text/" + request.text + "@" + std::to_string(static_cast<int>(request.fontSize)),
                        chrononmotion::motion::ContentKind::Text,
                        {request.fontSize * static_cast<float>(request.text.size()) * 0.55f,
                         request.fontSize * 1.2f}, "");
    }
    chronontemplate::ContentHandle createImage(const chronontemplate::ImageRequest& request) override {
        return remember(request.path, chrononmotion::motion::ContentKind::Image,
                        request.targetSize, request.path);
    }
    chronontemplate::ContentHandle createVideo(const chronontemplate::VideoRequest&) override { return {}; }
    chronontemplate::ContentHandle createShape(const chronontemplate::ShapeRequest& request) override {
        return remember("shape/" + request.name, chrononmotion::motion::ContentKind::Image,
                        request.size, "");
    }
    std::string currentFingerprint(const chronontemplate::ContentId& id) const override {
        const auto found = m_fingerprints.find(id);
        return found == m_fingerprints.end() ? std::string{} : found->second;
    }

private:
    chronontemplate::ContentHandle remember(const std::string& tag,
                                            chrononmotion::motion::ContentKind kind,
                                            chrononmotion::Vector2 size,
                                            const std::string& assetPath) {
        chronontemplate::ContentHandle handle;
        handle.id = assetPath.empty() ? "multi_image/" + std::to_string(m_nextId) : assetPath;
        handle.wireId = m_nextId++;
        handle.kind = kind;
        handle.metrics.naturalSize = size;
        handle.metrics.anchor = {0.5f, 0.5f};
        handle.metrics.fingerprint = tag + ":" + std::to_string(handle.wireId);
        m_fingerprints.emplace(handle.id, handle.metrics.fingerprint);
        return handle;
    }

    std::uint64_t m_nextId{1};
    std::unordered_map<chronontemplate::ContentId, std::string> m_fingerprints;
};

void emit(const std::filesystem::path& outDir, const std::string& name,
          chronontemplate::MultiImageSpec spec) {
    BoardHost backend;
    chronontemplate::RenderPlanContentHost host({
        .createText = [&](const auto& request) { return backend.createText(request); },
        .createImage = [&](const auto& request) { return backend.createImage(request); },
        .createVideo = [&](const auto& request) { return backend.createVideo(request); },
        .createShape = [&](const auto& request) { return backend.createShape(request); },
        .currentFingerprint = [&](const auto& id) { return backend.currentFingerprint(id); }});

    chronontemplate::TemplateScene scene(name, 30.f, host, 1920.f, 1080.f);
    // The board is authored in canvas-centred coordinates; aim the 2.5D
    // camera at the same origin so depth emphasis stays centred in frame.
    scene.cameraRig()
            .setPosition(chrononmotion::Vector3{0.f, 0.f, 1080.f})
            .setTarget(chrononmotion::Vector3{0.f, 0.f, 0.f});
    const chronontemplate::MultiImageBoard board = chronontemplate::addMultiImageBoard(scene, spec);
    if (!scene.validate().empty())
        throw std::runtime_error(name + ": scene does not validate");

    const auto plan = chronontemplate::lowerToRenderPlan(scene, host, name, name + ".mp4");
    const std::string json = chrononmotion::motion::renderPlanToJson(plan);
    const std::filesystem::path out = outDir / (name + ".plan.json");
    std::ofstream file(out, std::ios::binary | std::ios::trunc);
    if (!file || !(file << json << '\n'))
        throw std::runtime_error("failed writing " + out.string());
    std::cout << board.tiles.size() << " tiles, " << plan.layers.size() << " layers -> "
              << out << '\n';
}

void emitPremium(const std::filesystem::path& outDir, const char* name,
                 chronontemplate::MultiImageLayout layout, float tileWidth,
                 float tileHeight, float gap, std::vector<chronontemplate::MultiImageTile> tiles) {
    using namespace chronontemplate;

    const float captionSize = layout == MultiImageLayout::Penta ? 24.f : 30.f;
    MultiImageSpec spec;
    spec.layout = layout;
    spec.style = MultiImageStyle::SoftDream;
    spec.motionId = name;
    spec.tileWidth = tileWidth;
    spec.tileHeight = tileHeight;
    spec.gap = gap;
    spec.duration = 180;
    spec.holdFrames = 36;
    spec.captionFontSize = captionSize;
    spec.tiles = std::move(tiles);
    emit(outDir, name, spec);
}

}// namespace

int main(int argc, char** argv) try {
    if (argc != 2) throw std::runtime_error("usage: emit_multi_image_premium <out-dir>");
    const std::filesystem::path outDir = std::filesystem::absolute(argv[1]);
    std::filesystem::create_directories(outDir);

    using namespace chronontemplate;
    using Tile = MultiImageTile;

    constexpr const char* glenn = "ChrononTemplate/assets/famous_people_trio_v1/john_glenn.png";
    constexpr const char* armstrong = "ChrononTemplate/assets/famous_people_trio_v1/neil_armstrong.png";
    constexpr const char* ride = "ChrononTemplate/assets/famous_people_trio_v1/sally_ride.png";
    constexpr const char* woman = "ChrononTemplate/assets/drive_trio_replica_v1/online/portrait_woman.jpg";
    constexpr const char* man = "ChrononTemplate/assets/drive_trio_replica_v1/online/portrait_man1.jpg";

    emitPremium(outDir, "duo_cinematic_parallax", MultiImageLayout::Duo, 600.f, 900.f, 64.f,
                {Tile{.path = glenn, .caption = "John Glenn"},
                 Tile{.path = ride, .caption = "Sally Ride"}});
    emitPremium(outDir, "duo_depth_handoff", MultiImageLayout::Duo, 600.f, 900.f, 64.f,
                {Tile{.path = armstrong, .caption = "Neil Armstrong"},
                 Tile{.path = woman, .caption = "Portrait woman"}});

    emitPremium(outDir, "trio_orbit_focus", MultiImageLayout::Trio, 500.f, 740.f, 44.f,
                {Tile{.path = glenn, .caption = "John Glenn"},
                 Tile{.path = armstrong, .caption = "Neil Armstrong"},
                 Tile{.path = ride, .caption = "Sally Ride"}});
    emitPremium(outDir, "trio_prism_cascade", MultiImageLayout::Trio, 500.f, 740.f, 44.f,
                {Tile{.path = ride, .caption = "Sally Ride"},
                 Tile{.path = woman, .caption = "Portrait woman"},
                 Tile{.path = man, .caption = "Portrait man"}});

    emitPremium(outDir, "quad_mosaic_wave", MultiImageLayout::Quad, 420.f, 570.f, 36.f,
                {Tile{.path = glenn, .caption = "John Glenn"},
                 Tile{.path = armstrong, .caption = "Neil Armstrong"},
                 Tile{.path = ride, .caption = "Sally Ride"},
                 Tile{.path = woman, .caption = "Portrait woman"}});
    emitPremium(outDir, "quad_parallax_grid", MultiImageLayout::Quad, 420.f, 570.f, 36.f,
                {Tile{.path = man, .caption = "Portrait man"},
                 Tile{.path = glenn, .caption = "John Glenn"},
                 Tile{.path = woman, .caption = "Portrait woman"},
                 Tile{.path = armstrong, .caption = "Neil Armstrong"}});

    emitPremium(outDir, "penta_carousel_orbit", MultiImageLayout::Penta, 300.f, 430.f, 28.f,
                {Tile{.path = glenn, .caption = "Glenn"},
                 Tile{.path = armstrong, .caption = "Armstrong"},
                 Tile{.path = ride, .caption = "Ride"},
                 Tile{.path = woman, .caption = "Woman"},
                 Tile{.path = man, .caption = "Man"}});
    emitPremium(outDir, "penta_hero_cascade", MultiImageLayout::Penta, 300.f, 430.f, 28.f,
                {Tile{.path = ride, .caption = "Ride"},
                 Tile{.path = woman, .caption = "Woman"},
                 Tile{.path = glenn, .caption = "Glenn"},
                 Tile{.path = man, .caption = "Man"},
                 Tile{.path = armstrong, .caption = "Armstrong"}});

    std::cout << "8 premium boards emitted\n";
    return 0;
} catch (const std::exception& error) {
    std::cerr << "emit_multi_image_premium: " << error.what() << '\n';
    return 1;
}
