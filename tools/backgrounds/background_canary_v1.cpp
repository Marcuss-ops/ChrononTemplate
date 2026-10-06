#include "chronontemplate/backgrounds/BackgroundPack.hpp"
#include "chronontemplate/core/PlanLowering.hpp"
#include "chronontemplate/core/RenderPlanContentHost.hpp"
#include "chronontemplate/core/TemplateScene.hpp"

#include <chrononmotion/motion/RenderPlanEmission.hpp>

#include <filesystem>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <string>
#include <unordered_map>

namespace {

class BackgroundHost final : public chronontemplate::ContentHost {
public:
    chronontemplate::ContentHandle createText(const chronontemplate::TextRequest&) override { return {}; }
    chronontemplate::ContentHandle createImage(const chronontemplate::ImageRequest&) override { return {}; }
    chronontemplate::ContentHandle createVideo(const chronontemplate::VideoRequest&) override { return {}; }
    chronontemplate::ContentHandle createShape(const chronontemplate::ShapeRequest& request) override {
        chronontemplate::ContentHandle handle;
        handle.id = "background/" + std::to_string(m_nextId);
        handle.wireId = m_nextId++;
        handle.kind = chrononmotion::motion::ContentKind::Image;
        handle.metrics.naturalSize = request.size;
        handle.metrics.anchor = {0.5f, 0.5f};
        handle.metrics.fingerprint = "background-canary:" + std::to_string(handle.wireId);
        m_fingerprints.emplace(handle.id, handle.metrics.fingerprint);
        return handle;
    }
    std::string currentFingerprint(const chronontemplate::ContentId& id) const override {
        const auto found = m_fingerprints.find(id);
        return found == m_fingerprints.end() ? std::string{} : found->second;
    }
private:
    std::uint64_t m_nextId{1};
    std::unordered_map<chronontemplate::ContentId, std::string> m_fingerprints;
};

} // namespace

int main(int argc, char** argv) {
    if (argc != 2) {
        std::cerr << "usage: chronontemplate_background_canary_v1 <output-directory>\n";
        return 2;
    }
    try {
        namespace fs = std::filesystem;
        const fs::path output = argv[1];
        fs::create_directories(output);
        for (const auto look : chronontemplate::backgroundLooks()) {
            BackgroundHost backend;
            chronontemplate::RenderPlanContentHost host({
                .createText = [&](const auto& request) { return backend.createText(request); },
                .createImage = [&](const auto& request) { return backend.createImage(request); },
                .createVideo = [&](const auto& request) { return backend.createVideo(request); },
                .createShape = [&](const auto& request) { return backend.createShape(request); },
                .currentFingerprint = [&](const auto& id) { return backend.currentFingerprint(id); }});
            const std::string id = chronontemplate::backgroundLookId(look);
            chronontemplate::TemplateScene scene(id, 30.f, host, 1920.f, 1080.f);
            chronontemplate::BackgroundSpec spec;
            spec.look = look;
            spec.name = id;
            const auto composition = chronontemplate::addBackground(scene, spec);
            (void)composition;
            const auto plan = chronontemplate::lowerToRenderPlan(scene, host, id, "unused.png");
            const std::string json = chrononmotion::motion::renderPlanToJson(plan);
            const fs::path path = output / (id + ".plan.json");
            std::ofstream file(path, std::ios::binary | std::ios::trunc);
            if (!file || !(file << json << '\n'))
                throw std::runtime_error("failed writing " + path.string());
            std::cout << id << " " << plan.layers.size() << " layers " << path << '\n';
        }
    } catch (const std::exception& error) {
        std::cerr << "background canary: " << error.what() << '\n';
        return 1;
    }
    return 0;
}
