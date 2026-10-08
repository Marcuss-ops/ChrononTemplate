#include "chronontemplate/core/ContentHost.hpp"
#include "chronontemplate/core/PlanLowering.hpp"
#include "chronontemplate/core/RenderPlanContentHost.hpp"
#include "chronontemplate/entities_with_text/EntityFilmstripPack.hpp"
#include "chrononmotion/motion/RenderPlanEmission.hpp"

#include <algorithm>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <string>
#include <unordered_map>

using namespace chronontemplate;
using namespace chrononmotion;
using namespace chrononmotion::motion;
using namespace chronon3d::render_plan;

namespace {
class AssetBackend {
public:
    ContentHandle text(const TextRequest& request) {
        return make("text/" + request.text + "@" + std::to_string(request.fontSize),
                    ContentKind::Text, {request.fontSize * request.text.size() * 0.62f,
                                        request.fontSize * 1.25f});
    }
    ContentHandle image(const ImageRequest& request) {
        return make(request.path, ContentKind::Image, {1187.f, 668.f});
    }
    ContentHandle video(const VideoRequest& request) {
        return make("video/" + request.path, ContentKind::Video, {1920.f, 1080.f});
    }
    ContentHandle shape(const ShapeRequest& request) {
        return make("shape/" + request.name, ContentKind::Image, request.size);
    }
    std::string fingerprint(const ContentId& id) const {
        const auto found = fingerprints.find(id);
        return found == fingerprints.end() ? std::string{} : found->second;
    }
private:
    std::uint64_t next{1};
    std::unordered_map<ContentId, std::string> fingerprints;
    ContentHandle make(std::string id, ContentKind kind, Vector2 size) {
        ContentHandle result;
        result.id = std::move(id);
        result.wireId = next++;
        result.kind = kind;
        result.metrics.naturalSize = size;
        result.metrics.anchor = Vector2(0.5f, 0.5f);
        result.metrics.fingerprint = "entity-filmstrip-canary:" + result.id;
        fingerprints.emplace(result.id, result.metrics.fingerprint);
        return result;
    }
};
} // namespace

int main(int argc, char** argv) {
    try {
        const std::string destination = argc > 1 ? argv[1] :
            "out/entity_filmstrip_jim_rohn.plan.json";
        AssetBackend backend;
        RenderPlanContentHost host({
            .createText = [&](const TextRequest& request) { return backend.text(request); },
            .createImage = [&](const ImageRequest& request) { return backend.image(request); },
            .createVideo = [&](const VideoRequest& request) { return backend.video(request); },
            .createShape = [&](const ShapeRequest& request) { return backend.shape(request); },
            .currentFingerprint = [&](const ContentId& id) { return backend.fingerprint(id); }});

        TemplateScene scene("entity_filmstrip_jim_rohn", 30.f, host, 1920.f, 1080.f);
        EntityFilmstripSpec spec;
        spec.items = {
            {"ChrononTemplate/assets/images/jim_rohn_philosophy_source.png", "FILOSOFIA"},
            {"ChrononTemplate/assets/images/jim_rohn_philosophy_source.png", "DISCIPLINA"},
            {"ChrononTemplate/assets/images/jim_rohn_philosophy_source.png", "RISULTATI"}};
        spec.inFrame = 0;
        spec.itemDuration = 28;
        spec.overlapFrames = 5;
        spec.imageWidth = 1270.f;
        spec.imageHeight = 714.f;
        spec.cornerRadius = 28.f;
        spec.titleFontSize = 112.f;
        spec.font = "ChrononTemplate/assets/fonts/Inter-Bold.ttf";
        spec.gridSpacing = 36.f;
        const auto composition = addEntityFilmstrip(scene, spec);
        auto plan = lowerToRenderPlan(scene, host, "entity_filmstrip_jim_rohn_v1",
                                      "entity_filmstrip_jim_rohn_v1.mp4");
        plan.output.format = OutputFormat::Mp4;
        std::ofstream output(destination, std::ios::binary | std::ios::trunc);
        if (!output || !(output << renderPlanToJson(plan)))
            throw std::runtime_error("failed to write plan: " + destination);
        std::cout << "Wrote " << destination << " layers=" << plan.layers.size()
                  << " frames=" << composition.endFrame << '\n';
    } catch (const std::exception& error) {
        std::cerr << "entity filmstrip canary: " << error.what() << '\n';
        return 1;
    }
    return 0;
}
