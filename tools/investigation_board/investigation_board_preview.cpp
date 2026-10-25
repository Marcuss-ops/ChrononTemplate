#include "chronontemplate/core/PlanLowering.hpp"
#include "chronontemplate/core/RenderPlanContentHost.hpp"
#include "chronontemplate/core/TemplateScene.hpp"
#include "chronontemplate/investigation_board/InvestigationBoardPack.hpp"

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
    chronontemplate::ContentHandle createText(const chronontemplate::TextRequest&) override { return {}; }
    chronontemplate::ContentHandle createImage(const chronontemplate::ImageRequest& request) override {
        return remember(request.path, request.targetSize, request.path);
    }
    chronontemplate::ContentHandle createVideo(const chronontemplate::VideoRequest&) override { return {}; }
    chronontemplate::ContentHandle createShape(const chronontemplate::ShapeRequest& request) override {
        return remember("shape", request.size, "");
    }
    std::string currentFingerprint(const chronontemplate::ContentId& id) const override {
        const auto found = m_fingerprints.find(id);
        return found == m_fingerprints.end() ? std::string{} : found->second;
    }

private:
    // Image content is addressed by its logical asset path, which the CLI
    // resolves under --assets-root. Shapes keep a generated id.
    chronontemplate::ContentHandle remember(const std::string& tag, chrononmotion::Vector2 size,
                                            const std::string& assetPath) {
        chronontemplate::ContentHandle handle;
        handle.id = assetPath.empty() ? "investigation/" + std::to_string(m_nextId) : assetPath;
        handle.wireId = m_nextId++;
        handle.kind = chrononmotion::motion::ContentKind::Image;
        handle.metrics.naturalSize = size;
        handle.metrics.anchor = {0.5f, 0.5f};
        handle.metrics.fingerprint = tag + ":" + std::to_string(handle.wireId);
        m_fingerprints.emplace(handle.id, handle.metrics.fingerprint);
        return handle;
    }

    std::uint64_t m_nextId{1};
    std::unordered_map<chronontemplate::ContentId, std::string> m_fingerprints;
};

} // namespace

int main(int argc, char** argv) {
    if (argc != 2) {
        std::cerr << "usage: chronontemplate_investigation_board_preview <output.plan.json>\n";
        return 2;
    }
    try {
        const std::filesystem::path output = argv[1];
        if (output.has_parent_path())
            std::filesystem::create_directories(output.parent_path());

        chronontemplate::InvestigationBoardSpec spec;
        spec.items = {
                {.path = "assets/test/square_bottle_test.png", .x = 520.f, .y = 430.f, .rotationDegrees = -4.f},
                {.path = "assets/test/square_bottle_test.png", .x = 1400.f, .y = 400.f, .rotationDegrees = 3.f},
                {.path = "assets/test/square_bottle_test.png", .x = 960.f, .y = 780.f, .rotationDegrees = -1.5f}};
        spec.connections = {{0, 1}, {1, 2}};
        spec.inFrame = 0;
        spec.duration = 240;

        BoardHost backend;
        chronontemplate::RenderPlanContentHost host({
            .createText = [&](const auto& request) { return backend.createText(request); },
            .createImage = [&](const auto& request) { return backend.createImage(request); },
            .createVideo = [&](const auto& request) { return backend.createVideo(request); },
            .createShape = [&](const auto& request) { return backend.createShape(request); },
            .currentFingerprint = [&](const auto& id) { return backend.currentFingerprint(id); }});

        chronontemplate::TemplateScene scene("investigation_board_preview", 30.f, host, 1920.f, 1080.f);
        chronontemplate::addInvestigationBoard(scene, spec);
        const auto plan = chronontemplate::lowerToRenderPlan(scene, host, "investigation_board_preview", "unused.png");

        const std::string json = chrononmotion::motion::renderPlanToJson(plan);
        std::ofstream file(output, std::ios::binary | std::ios::trunc);
        if (!file || !(file << json << '\n'))
            throw std::runtime_error("failed writing " + output.string());
        std::cout << plan.layers.size() << " layers " << output << '\n';
    } catch (const std::exception& error) {
        std::cerr << "investigation board preview: " << error.what() << '\n';
        return 1;
    }
    return 0;
}
