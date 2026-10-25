// Emit the styled multi-image boards (archive, sepia torn, polaroid fan) as
// render-plan V3 JSON through the canonical TemplateScene -> RenderPlan
// lowering. Pattern follows tools/investigation_board/investigation_board_preview.cpp.
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

}// namespace

int main(int argc, char** argv) try {
    if (argc != 2) throw std::runtime_error("usage: emit_multi_image_styles <out-dir>");
    const std::filesystem::path outDir = std::filesystem::absolute(argv[1]);
    std::filesystem::create_directories(outDir);

    using namespace chronontemplate;

    {
        MultiImageSpec spec;
        spec.layout = MultiImageLayout::Trio;
        spec.style = MultiImageStyle::ArchiveBoard;
        spec.motionId = "trio_fan_reveal";
        spec.headerLabel = "Archive image";
        spec.headerSubtitle = "Glenn, Armstrong, and Ride";
        for (const char* path : {"ChrononTemplate/assets/famous_people_trio_v1/john_glenn.png",
                                 "ChrononTemplate/assets/famous_people_trio_v1/neil_armstrong.png",
                                 "ChrononTemplate/assets/famous_people_trio_v1/sally_ride.png"}) {
            spec.tiles.push_back(MultiImageTile{.path = path});
        }
        emit(outDir, "multi_image_archive_board_trio_v1", spec);
    }
    {
        MultiImageSpec spec;
        spec.layout = MultiImageLayout::Duo;
        spec.style = MultiImageStyle::SepiaTorn;
        spec.motionId = "duo_soft_bloom_rise";
        spec.headerLabel = "Archive image";
        spec.headerSubtitle = "John Glenn and Neil Armstrong";
        for (const char* path : {"ChrononTemplate/assets/famous_people_trio_v1/john_glenn.png",
                                 "ChrononTemplate/assets/famous_people_trio_v1/neil_armstrong.png"}) {
            spec.tiles.push_back(MultiImageTile{.path = path});
        }
        emit(outDir, "multi_image_sepia_torn_duo_v1", spec);
    }
    {
        MultiImageSpec spec;
        spec.layout = MultiImageLayout::Trio;
        spec.style = MultiImageStyle::PolaroidFan;
        spec.motionId = "trio_center_priority";
        for (const char* path : {"ChrononTemplate/assets/famous_people_trio_v1/john_glenn.png",
                                 "ChrononTemplate/assets/famous_people_trio_v1/sally_ride.png",
                                 "ChrononTemplate/assets/famous_people_trio_v1/neil_armstrong.png"}) {
            spec.tiles.push_back(MultiImageTile{.path = path});
        }
        emit(outDir, "multi_image_polaroid_fan_trio_v1", spec);
    }

    std::cout << "3 styled boards emitted\n";
    return 0;
} catch (const std::exception& error) {
    std::cerr << "emit_multi_image_styles: " << error.what() << '\n';
    return 1;
}
