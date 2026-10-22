// Emit the four archival card recipes as Chronon3D RenderPlan JSON.
//
// The plans are authored by the real ChrononTemplate pack, lowered through the
// canonical content host, and then rendered by chronon3d_cli (see
// tools/single_images/render_archival_cards_5s.py).
#include "chronontemplate/single_images/ArchivalCardPack.hpp"

#include "chronontemplate/core/RenderPlanContentHost.hpp"

#include <chrononmotion/motion/RenderPlanEmission.hpp>

#include <algorithm>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <string>
#include <unordered_map>

namespace {

    using namespace chronontemplate;

    constexpr const char* kAlCaponePhoto =
            "ChrononTemplate/assets/archival_refs_v2/al_capone_trio_source.png";
    constexpr const char* kPucklerPhoto =
            "ChrononTemplate/assets/archival_refs_v2/von_puckler_source.png";
    constexpr const char* kChicagoBuildingPhoto =
            "ChrononTemplate/assets/archival_refs_v2/chicago_building_source.png";
    constexpr const char* kTornFrame =
            "ChrononTemplate/assets/archival_refs_v2/torn_paper_frame.png";
    constexpr const char* kFont = "Chronon3d/assets/fonts/Inter-Regular.ttf";

    class AssetBackend {
    public:
        ContentHandle text(const TextRequest& request) {
            return make("text/" + request.text + "@" + std::to_string(static_cast<int>(request.fontSize)),
                        chrononmotion::motion::ContentKind::Text,
                        {request.fontSize * static_cast<float>(request.text.size()) * 0.55f,
                         request.fontSize * 1.2f});
        }

        ContentHandle image(const ImageRequest& request) {
            return make(request.path, chrononmotion::motion::ContentKind::Image,
                        imageSize(request.path));
        }

        ContentHandle video(const VideoRequest& request) {
            return make(request.path, chrononmotion::motion::ContentKind::Video,
                        {1920.f, 1080.f});
        }

        ContentHandle shape(const ShapeRequest& request) {
            return make("shape/" + request.name, chrononmotion::motion::ContentKind::Image,
                        request.size);
        }

        std::string fingerprint(const ContentId& id) const {
            const auto found = m_fingerprints.find(id);
            return found == m_fingerprints.end() ? std::string{} : found->second;
        }

    private:
        static chrononmotion::Vector2 imageSize(const std::string& path) {
            if (path == kAlCaponePhoto) return {1153.f, 819.f};
            if (path == kPucklerPhoto) return {1448.f, 1086.f};
            if (path == kChicagoBuildingPhoto) return {1672.f, 941.f};
            if (path == kTornFrame) return {1176.f, 935.f};
            throw std::invalid_argument("archival cards: unexpected image asset " + path);
        }

        ContentHandle make(std::string id, chrononmotion::motion::ContentKind kind,
                           chrononmotion::Vector2 size) {
            ContentHandle handle;
            handle.id = std::move(id);
            handle.wireId = m_nextWireId++;
            handle.kind = kind;
            handle.metrics.naturalSize = size;
            handle.metrics.anchor = {0.5f, 0.5f};
            handle.metrics.fingerprint = "archival-card-v1:" + handle.id;
            m_fingerprints.emplace(handle.id, handle.metrics.fingerprint);
            return handle;
        }

        std::uint64_t m_nextWireId{1};
        std::unordered_map<ContentId, std::string> m_fingerprints;
    };

    ArchivalCardSpec specFor(ArchivalCardLook look, const std::string& name) {
        ArchivalCardSpec spec{};
        spec.name = name;
        spec.font = kFont;
        spec.inFrame = 0;
        spec.durationFrames = 150;
        switch (look) {
            case ArchivalCardLook::TornPaperPortrait:
                spec.primaryAsset = kPucklerPhoto;
                spec.primaryLabel = "von Pückler";
                spec.primaryWidth = 1080.f;
                spec.primaryHeight = 815.f;
                spec.centerY = 538.f;
                break;
            case ArchivalCardLook::ArchivePrint:
                spec.primaryAsset = kAlCaponePhoto;
                spec.primaryWidth = 1150.f;
                spec.primaryHeight = 819.f;
                spec.centerY = 565.f;
                break;
            case ArchivalCardLook::VintageFilmProjection:
                spec.primaryAsset = kChicagoBuildingPhoto;
                spec.primaryWidth = 1180.f;
                spec.primaryHeight = 910.f;
                spec.centerY = 540.f;
                break;
            case ArchivalCardLook::DoublePortraitArchive:
                throw std::invalid_argument("archival cards: double portrait is not part of this reference set");
                break;
            default:
                throw std::invalid_argument("archival cards: unknown look");
        }
        return spec;
    }

} // namespace

int main(int argc, char** argv) {
    if (argc != 2) {
        std::cerr << "usage: chronontemplate_emit_archival_cards <output-directory>\n";
        return 2;
    }
    try {
        namespace fs = std::filesystem;
        const fs::path output = argv[1];
        fs::create_directories(output);
        for (const ArchivalCardLook look : {ArchivalCardLook::ArchivePrint,
                                            ArchivalCardLook::TornPaperPortrait,
                                            ArchivalCardLook::VintageFilmProjection}) {
            AssetBackend backend;
            RenderPlanContentHost host({
                    .createText = [&](const auto& request) { return backend.text(request); },
                    .createImage = [&](const auto& request) { return backend.image(request); },
                    .createVideo = [&](const auto& request) { return backend.video(request); },
                    .createShape = [&](const auto& request) { return backend.shape(request); },
                    .currentFingerprint = [&](const auto& id) { return backend.fingerprint(id); }});
            const std::string id = archivalCardLookId(look);
            TemplateScene scene(id, 30.f, host, 1920.f, 1080.f);
            (void)addArchivalCard(scene, look, specFor(look, id));
            if (!scene.validate().empty()) {
                std::string problems;
                for (const auto& problem : scene.validate())
                    problems += "\n  " + problem;
                throw std::runtime_error("archival cards: " + id + " does not validate:" + problems);
            }
            const fs::path videoPath = output / (id + ".mp4");
            auto plan = lowerToRenderPlan(scene, host, id, videoPath.string());
            // The lowerer always stamps a PNG still format; these plans are
            // authored for video delivery, so stamp the MP4 lane before
            // emission: without it the CLI plan route skips the video
            // compatibility view and video renders fail closed.
            plan.output.format = chronon3d::render_plan::OutputFormat::Mp4;
            // Keep authored opacity entrances while removing identity transform
            // tracks emitted for otherwise-static layers. Those transforms can
            // override their composed placement in the CLI plan.
            std::size_t stripped = 0;
            for (auto& layer : plan.layers) {
                if (layer.animation) {
                    auto& tracks = layer.animation->tracks;
                    tracks.erase(std::remove_if(tracks.begin(), tracks.end(),
                            [](const auto& track) { return track.property != "opacity"; }),
                            tracks.end());
                    if (tracks.empty()) layer.animation.reset();
                }
                const auto before = layer.effects.size();
                layer.effects.erase(std::remove_if(layer.effects.begin(), layer.effects.end(),
                        [](const auto& effect) {
                            using Kind = chronon3d::render_plan::LayerPlan::EffectKindPlan;
                            switch (effect.kind) {
                                case Kind::Catalog:
                                    return effect.canonical_effect_id != "color.saturation" &&
                                           effect.canonical_effect_id != "color.contrast";
                                case Kind::Noise:
                                case Kind::Vignette:
                                case Kind::Glow:
                                case Kind::Bloom:
                                    return false;
                                default:
                                    return true;
                            }
                        }), layer.effects.end());
                stripped += before - layer.effects.size();
            }
            const std::string json = chrononmotion::motion::renderPlanToJson(plan);
            const fs::path path = output / (id + ".plan.json");
            std::ofstream file(path, std::ios::binary | std::ios::trunc);
            if (!file || !(file << json << '\n'))
                throw std::runtime_error("failed writing " + path.string());
            std::cout << id << " " << plan.layers.size() << " layers, "
                      << stripped << " unsupported preview effects dropped " << path << '\n';
        }
    } catch (const std::exception& error) {
        std::cerr << "archival cards: " << error.what() << '\n';
        return 1;
    }
    return 0;
}
