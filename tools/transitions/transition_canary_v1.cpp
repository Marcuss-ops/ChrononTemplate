#include "chronontemplate/core/PlanLowering.hpp"
#include "chronontemplate/core/RenderPlanContentHost.hpp"
#include "chronontemplate/core/ContentHost.hpp"
#include "chronontemplate/core/TemplateScene.hpp"
#include "chronontemplate/transitions/TransitionPack.hpp"

#include <chrononmotion/motion/RenderPlanEmission.hpp>

#include <filesystem>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <string>
#include <unordered_map>

namespace {

class CanaryHost final : public chronontemplate::ContentHost {
public:
    chronontemplate::ContentHandle createText(const chronontemplate::TextRequest&) override { return {}; }
    chronontemplate::ContentHandle createImage(const chronontemplate::ImageRequest&) override { return {}; }
    chronontemplate::ContentHandle createVideo(const chronontemplate::VideoRequest&) override { return {}; }
    chronontemplate::ContentHandle createShape(const chronontemplate::ShapeRequest& request) override {
        chronontemplate::ContentHandle handle;
        handle.id = "shape/" + std::to_string(m_nextWireId);
        handle.wireId = m_nextWireId++;
        handle.kind = chrononmotion::motion::ContentKind::Image;
        handle.metrics.naturalSize = request.size;
        handle.metrics.fingerprint = "transition-canary:" + std::to_string(handle.wireId);
        m_fingerprints[handle.id] = handle.metrics.fingerprint;
        return handle;
    }
    std::string currentFingerprint(const chronontemplate::ContentId& id) const override {
        const auto found = m_fingerprints.find(id);
        return found == m_fingerprints.end() ? std::string{} : found->second;
    }
private:
    std::uint64_t m_nextWireId{1};
    std::unordered_map<chronontemplate::ContentId, std::string> m_fingerprints;
};

chronontemplate::RenderPlanContentBackend makeRenderBackend(CanaryHost& source) {
    return {
        .createText = [&](const auto& request) { return source.createText(request); },
        .createImage = [&](const auto& request) { return source.createImage(request); },
        .createVideo = [&](const auto& request) { return source.createVideo(request); },
        .createShape = [&](const auto& request) { return source.createShape(request); },
        .currentFingerprint = [&](const auto& id) { return source.currentFingerprint(id); }};
}

void writeCanary(chronontemplate::TransitionLook look, const std::filesystem::path& outputDir) {
    using namespace chronontemplate;
    CanaryHost source;
    RenderPlanContentHost host(makeRenderBackend(source));
    TemplateScene scene(transitionId(look), 30.f, host, 640.f, 360.f);
    constexpr int startFrame = 12;
    TransitionSpec spec;
    spec.look = look;
    spec.inFrame = startFrame;
    spec.duration = recommendedTransitionDuration(look);
    spec.name = transitionId(look);
    spec.enableMotionBlur = true;
    const TransitionComposition cut = addTransition(scene, spec);
    const FrameSubmission submitted = scene.submit(cut.coverFrame);
    (void) submitted;
    const auto plan = lowerToRenderPlan(scene, host, transitionId(look), "unused.png");
    const std::string json = chrononmotion::motion::renderPlanToJson(plan);
    const std::filesystem::path path = outputDir / (std::string(transitionId(look)) + ".plan.json");
    std::ofstream file(path, std::ios::binary | std::ios::trunc);
    if (!file) throw std::runtime_error("cannot write " + path.string());
    file << json << '\n';
    if (!file) throw std::runtime_error("failed writing " + path.string());
    std::cout << transitionId(look) << " frames=" << cut.inFrame << "-" << cut.endFrame
              << " duration=" << spec.duration << " plan=" << path.string() << '\n';
}

} // namespace

int main(int argc, char** argv) {
    if (argc != 2) {
        std::cerr << "usage: chronontemplate_transition_canary_v1 <output-directory>\n";
        return 2;
    }
    try {
        const std::filesystem::path outputDir = argv[1];
        std::filesystem::create_directories(outputDir);
        for (const auto look : chronontemplate::transitionLooks()) {
            if (chronontemplate::isRapidTransition(look)) writeCanary(look, outputDir);
        }
    } catch (const std::exception& error) {
        std::cerr << "transition canary: " << error.what() << '\n';
        return 1;
    }
    return 0;
}
