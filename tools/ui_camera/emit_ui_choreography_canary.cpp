// ChrononTemplate — ui_camera_choreography_v1 canary emitter.
//
// Builds the 90-frame UI panel + smooth-camera test (1920x1080, 30 fps),
// validates the choreography fail-closed, and writes one
// chronon.render-plan.v3 document for `chronon3d_cli validate --plan`.
//
// Usage:
//   chronontemplate_emit_ui_choreography_canary <output-plan.json>

#include "chronontemplate/core/RenderPlanContentHost.hpp"
#include "chronontemplate/core/TemplateScene.hpp"
#include "chronontemplate/ui_camera/UiCameraChoreography.hpp"

#include <chrononmotion/motion/RenderPlanEmission.hpp>

#include <cstdint>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <string>
#include <unordered_map>

namespace {

    // Deterministic measuring backend: text and shapes measure from the
    // request alone, so the canary needs no fonts or files on disk.
    class CanaryBackend final : public chronontemplate::ContentHost {
    public:
        chronontemplate::ContentHandle createText(const chronontemplate::TextRequest& request) override {
            return measure("text/" + request.text, chrononmotion::motion::ContentKind::Text,
                           chrononmotion::Vector2(static_cast<float>(request.text.size()) *
                                                      request.fontSize * 0.55f,
                                                  request.fontSize * 1.2f));
        }
        chronontemplate::ContentHandle createImage(const chronontemplate::ImageRequest& request) override {
            return measure("image/" + request.path, chrononmotion::motion::ContentKind::Image,
                           chrononmotion::Vector2(640.f, 360.f));
        }
        chronontemplate::ContentHandle createVideo(const chronontemplate::VideoRequest& request) override {
            return measure("video/" + request.path, chrononmotion::motion::ContentKind::Video,
                           chrononmotion::Vector2(1920.f, 1080.f));
        }
        chronontemplate::ContentHandle createShape(const chronontemplate::ShapeRequest& request) override {
            return measure("shape/" + request.name, chrononmotion::motion::ContentKind::Image,
                           request.size);
        }
        std::string currentFingerprint(const chronontemplate::ContentId& id) const override {
            const auto found = m_fingerprints.find(id);
            return found == m_fingerprints.end() ? std::string{} : found->second;
        }

    private:
        chronontemplate::ContentHandle measure(const std::string& id,
                                               chrononmotion::motion::ContentKind kind,
                                               chrononmotion::Vector2 size) {
            chronontemplate::ContentHandle handle;
            handle.id = id;
            handle.wireId = m_nextId++;
            handle.kind = kind;
            handle.metrics.naturalSize = size;
            handle.metrics.anchor = chrononmotion::Vector2(0.5f, 0.5f);
            handle.metrics.fingerprint = "ui-choreography-canary:" + id;
            m_fingerprints.emplace(handle.id, handle.metrics.fingerprint);
            return handle;
        }
        std::uint64_t m_nextId{1};
        std::unordered_map<chronontemplate::ContentId, std::string> m_fingerprints{};
    };

}// namespace

int main(int argc, char** argv) {
    if (argc != 2) {
        std::cerr << "usage: chronontemplate_emit_ui_choreography_canary <output-plan.json>\n";
        return 2;
    }
    try {
        CanaryBackend backend;
        chronontemplate::RenderPlanContentHost host({
            .createText = [&](const auto& request) { return backend.createText(request); },
            .createImage = [&](const auto& request) { return backend.createImage(request); },
            .createVideo = [&](const auto& request) { return backend.createVideo(request); },
            .createShape = [&](const auto& request) { return backend.createShape(request); },
            .currentFingerprint = [&](const auto& id) { return backend.currentFingerprint(id); }});

        chronontemplate::TemplateScene scene("ui_camera_choreography_v1", 30.f, host, 1920.f, 1080.f);
        chronontemplate::UiPanelSpec panelSpec;
        panelSpec.title = "CHRONON UI";
        const chronontemplate::UiPanelComposition panel =
            chronontemplate::buildUiPanel(scene, panelSpec);
        const chronontemplate::UiCameraChoreographySpec choreo;
        chronontemplate::applyUiCameraChoreography(scene, choreo, panel);

        const chronontemplate::UiChoreographyReport report =
            chronontemplate::validateUiChoreography(scene, choreo, panel);
        if (!report.ok) {
            std::cerr << "ui choreography canary: validation failed:\n";
            for (const auto& problem : report.problems)
                std::cerr << "  - " << problem << "\n";
            return 1;
        }

        const auto plan =
            chronontemplate::lowerToRenderPlan(scene, host, "ui_camera_choreography_v1", "unused.mp4");
        const std::string json = chrononmotion::motion::renderPlanToJson(plan);
        std::ofstream file(argv[1], std::ios::binary | std::ios::trunc);
        if (!file || !(file << json << '\n'))
            throw std::runtime_error("failed writing the canary plan");
        std::cout << "ui_camera_choreography_v1: " << plan.layers.size() << " layers, "
                  << plan.canvas.duration.integral() << " frames -> " << argv[1] << "\n";
    } catch (const std::exception& error) {
        std::cerr << "ui choreography canary: " << error.what() << "\n";
        return 1;
    }
    return 0;
}
