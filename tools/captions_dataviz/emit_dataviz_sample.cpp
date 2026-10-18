// Emit the three Chronomotion reference charts through ChrononTemplate's
// TemplateScene and native data-viz pack.
#include "chronontemplate/captions_dataviz/CaptionsDataVizPack.hpp"
#include "chronontemplate/core/NativePrimitives.hpp"
#include "chronontemplate/core/RenderPlanContentHost.hpp"
#include "chrononmotion/motion/RenderPlanEmission.hpp"

#include <filesystem>
#include <fstream>
#include <iostream>
#include <optional>
#include <string>
#include <unordered_map>
#include <utility>

using namespace chronontemplate;
using namespace chrononmotion;
using namespace chrononmotion::motion;

namespace {

constexpr int kFrames = 180;
constexpr float kFps = 30.f;
constexpr float kCanvasHeight = 1080.f;
constexpr const char* kInk = "#202528";
constexpr const char* kMuted = "#697174";
constexpr const char* kPaper = "#F4F2EC";
constexpr const char* kRed = "#E4424D";
constexpr const char* kTeal = "#267078";

class SampleAssetBackend {
public:
    ContentHandle text(const TextRequest& request) {
        return make("text/" + request.text, ContentKind::Text,
                    {request.fontSize * static_cast<float>(request.text.size()) * 0.72f,
                     request.fontSize * 1.25f});
    }
    ContentHandle image(const ImageRequest& request) {
        return make(request.path, ContentKind::Image, {1920.f, 1080.f});
    }
    ContentHandle video(const VideoRequest& request) {
        return make(request.path, ContentKind::Video, {1920.f, 1080.f});
    }
    ContentHandle shape(const ShapeRequest& request) {
        return make("shape/" + request.name, ContentKind::Image, request.size);
    }
    std::string fingerprint(const ContentId& id) const {
        const auto found = m_fingerprints.find(id);
        return found == m_fingerprints.end() ? std::string{} : found->second;
    }
private:
    ContentHandle make(std::string id, ContentKind kind, Vector2 size) {
        ContentHandle handle;
        handle.id = std::move(id);
        handle.wireId = m_nextWireId++;
        handle.kind = kind;
        handle.metrics.naturalSize = size;
        handle.metrics.anchor = {0.5f, 0.5f};
        handle.metrics.fingerprint = "chronontemplate-reference-charts-v1:" + handle.id;
        m_fingerprints.emplace(handle.id, handle.metrics.fingerprint);
        return handle;
    }
    std::uint64_t m_nextWireId{1};
    std::unordered_map<ContentId, std::string> m_fingerprints;
};

void addBackgroundAndEditorialGrid(TemplateScene& scene, const char* accent) {
    auto& grid = scene.shape(ShapeSpec{.size = Vector2(1660.f, 565.f),
                                      .fillColor = "#D4D8D2",
                                      .name = "fine-dot-grid",
                                      .geometry = ShapeGeometry::DotGrid,
                                      .gridSpacing = 26.f,
                                      .dotRadius = 1.15f});
    grid.position(960.f, kCanvasHeight - 613.f).opacity(0.22f).alive(0, kFrames - 1);

    auto& marker = scene.shape(ShapeSpec{.size = Vector2(64.f, 5.f),
                                        .fillColor = accent,
                                        .name = "editorial-accent-rule",
                                        .cornerRadius = 2.5f});
    marker.position(150.f, kCanvasHeight - 48.f).alive(0, kFrames - 1);
}

void addHeader(TemplateScene& scene, const std::string& eyebrow,
               const std::string& title, const std::string& subtitle) {
    auto& tag = scene.text(TextSpec{.text = eyebrow,
                                    .font = "assets/fonts/Inter-Bold.ttf",
                                    .fontSize = 17.f,
                                    .color = kMuted,
                                    .name = "section-label"});
    tag.position(200.f, kCanvasHeight - 70.f).alive(0, kFrames - 1).animate(FadeIn{0, 14});
    auto& heading = scene.text(TextSpec{.text = title,
                                        .font = "assets/fonts/Inter-Bold.ttf",
                                        .fontSize = 48.f,
                                        .color = kInk,
                                        .name = "editorial-heading"});
    const float titleWidth = static_cast<float>(title.size()) * 48.f * 0.40f;
    heading.position(200.f + titleWidth * 0.5f, kCanvasHeight - 138.f)
        .alive(0, kFrames - 1).animate(FadeIn{5, 22});
    auto& deck = scene.text(TextSpec{.text = subtitle,
                                     .font = "assets/fonts/Inter-Regular.ttf",
                                     .fontSize = 24.f,
                                     .color = kMuted,
                                     .name = "editorial-deck"});
    const float deckWidth = static_cast<float>(subtitle.size()) * 24.f * 0.34f;
    deck.position(200.f + deckWidth * 0.5f, kCanvasHeight - 196.f)
        .alive(0, kFrames - 1).animate(FadeIn{12, 20});
    auto& divider = scene.shape(ShapeSpec{.size = Vector2(1620.f, 1.5f),
                                          .fillColor = "#D7DAD4",
                                          .name = "header-divider"});
    divider.position(960.f, kCanvasHeight - 240.f).alive(0, kFrames - 1);
}

void addAxisLabels(TemplateScene& scene, const std::vector<std::string>& labels,
                   float left, float right, float y) {
    for (std::size_t i = 0; i < labels.size(); ++i) {
        const float x = left + (right - left) * static_cast<float>(i) /
                                  static_cast<float>(labels.size() - 1);
        auto& label = scene.text(TextSpec{.text = labels[i],
                                          .font = "assets/fonts/Inter-Bold.ttf",
                                          .fontSize = 17.f,
                                          .color = kMuted,
                                          .name = "axis-label-" + std::to_string(i)});
        label.position(x, kCanvasHeight - y).alive(0, kFrames - 1);
    }
}

void addBarCategories(TemplateScene& scene) {
    const std::vector<std::pair<float, std::string>> items{
        {524.5f, "Stati Uniti"}, {959.5f, "Germania"}, {1394.5f, "Paesi scandinavi"}};
    for (std::size_t i = 0; i < items.size(); ++i) {
        auto& label = scene.text(TextSpec{.text = items[i].second,
            .font = "assets/fonts/Inter-Bold.ttf", .fontSize = 20.f,
            .color = kInk, .name = "category-" + std::to_string(i)});
        label.position(items[i].first, kCanvasHeight - 917.f).alive(0, kFrames - 1);
    }
}

void addChartPanel(TemplateScene& scene, float left, float top, float right, float bottom) {
    const float width = right - left;
    const float height = bottom - top;
    const float x = (left + right) * 0.5f;
    const float y = kCanvasHeight - (top + bottom) * 0.5f;
    auto& shadow = scene.shape(ShapeSpec{.size = Vector2(width, height),
        .fillColor = "#202528", .name = "chart-panel-shadow", .cornerRadius = 14.f});
    shadow.position(x, y - 8.f).opacity(0.08f).alive(0, kFrames - 1);
    auto& panel = scene.shape(ShapeSpec{.size = Vector2(width, height),
        .fillColor = "#FBFAF6", .name = "chart-panel", .cornerRadius = 14.f,
        .strokeColor = "#E5E2DA", .strokeWidth = 1.25f});
    panel.position(x, y).alive(0, kFrames - 1);
}

void addHorizontalGrid(TemplateScene& scene, float left, float top, float right,
                       float bottom, int divisions) {
    for (int i = 0; i <= divisions; ++i) {
        const float y = top + (bottom - top) * static_cast<float>(i) /
                                      static_cast<float>(divisions);
        auto& rule = scene.shape(ShapeSpec{.size = Vector2(right - left, 1.35f),
            .fillColor = "#D8DCD8", .name = "chart-grid-" + std::to_string(i)});
        rule.position((left + right) * 0.5f, kCanvasHeight - y)
            .opacity(0.42f).alive(0, kFrames - 1);
    }
}

void addFooter(TemplateScene& scene, const std::string& text) {
    auto& footer = scene.text(TextSpec{.text = text,
        .font = "assets/fonts/Inter-Regular.ttf", .fontSize = 15.f,
        .color = kMuted, .name = "source-note"});
    footer.position(960.f, kCanvasHeight - 1028.f).alive(0, kFrames - 1);
}

void addStatCell(TemplateScene& scene, const std::string& value,
                 const std::string& caption, float x, const std::string& accent,
                 int start = 104, float width = 440.f) {
    auto& marker = scene.shape(ShapeSpec{.size = Vector2(3.f, 58.f),
        .fillColor = accent, .name = "stat-accent"});
    marker.position(x - width * 0.5f + 8.f, kCanvasHeight - 895.f)
        .opacity(0.9f).alive(start, kFrames - 1).animate(FadeIn{start, 16});
    auto& number = scene.text(TextSpec{.text = value, .font = "assets/fonts/FreeSerif.ttf",
        .fontSize = 42.f, .color = kInk, .name = "editorial-stat"});
    number.position(x, kCanvasHeight - 882.f)
        .alive(start, kFrames - 1).animate(FadeIn{start, 18});
    auto& label = scene.text(TextSpec{.text = caption, .font = "assets/fonts/Inter-Bold.ttf",
        .fontSize = 15.f, .color = kMuted, .name = "editorial-stat-caption"});
    label.position(x, kCanvasHeight - 925.f)
        .alive(start + 4, kFrames - 1).animate(FadeIn{start + 4, 18});
}

void writePlan(const chronon3d::render_plan::RenderPlan& plan,
               const std::filesystem::path& output,
               const std::vector<native::Paths::Point>& path = {},
               const std::string& pathColor = kInk) {
    std::ofstream file(output, std::ios::binary | std::ios::trunc);
    auto document = nlohmann::json::parse(renderPlanToJson(plan));
    // Keep the generated plan within the deployed chronon.render-plan.v2
    // camera schema. This scene does not use aperture/iris depth-of-field.
    if (document.contains("camera") && document["camera"].is_object())
        document["camera"].erase("iris_blades");
    // The scene author's data-viz helper uses an inclusive alive end frame;
    // keep the delivery canvas at exactly six seconds while allowing layers
    // to remain alive through its final frame.
    document["canvas"]["duration_frames"] = kFrames;
    for (auto& layer : document["layers"]) {
        if (layer.contains("duration_frames") && layer["duration_frames"].is_number_integer())
            layer["duration_frames"] = std::min(layer["duration_frames"].get<int>(), kFrames);
        if (!layer.contains("animation") || !layer["animation"].contains("tracks")) continue;
        for (auto& track : layer["animation"]["tracks"]) {
            if (!track.contains("keyframes") || !track["keyframes"].is_array()) continue;
            nlohmann::json bounded = nlohmann::json::array();
            for (auto keyframe : track["keyframes"]) {
                keyframe["frame"] = std::min(keyframe.at("frame").get<int>(), kFrames - 1);
                if (!bounded.empty() && bounded.back()["frame"] == keyframe["frame"])
                    bounded.back() = std::move(keyframe);
                else
                    bounded.push_back(std::move(keyframe));
            }
            track["keyframes"] = std::move(bounded);
        }
    }
    // TemplateScene currently has no full-frame ColorSpec. Keep the editorial
    // canvas on Chronon's native color/noise layers so it covers the camera's
    // perspective overscan as well as the chart safe area.
    nlohmann::json paper{{"id", "warm-paper-canvas"}, {"type", "color"},
        {"color", native::Material::rgba(kPaper)}, {"size", {1920, 1080}},
        {"position", {0, 0}}, {"start_frame", 0}, {"duration_frames", kFrames},
        {"screen_space", true},
        {"effects", nlohmann::json::array({native::Effects::noise(0.025f, 1701, 1.2f)})}};
    document["layers"].insert(document["layers"].begin(), std::move(paper));
    if (!path.empty()) {
        // The WSL software backend paints a black bounding rectangle while a
        // long path is being trimmed. Reveal small, untrimmed native path
        // sections instead; this stays editable and renders cleanly in every
        // sampled frame. Each section contains two data intervals.
        constexpr std::size_t kIntervalsPerReveal = 2;
        const std::size_t intervalCount = path.size() - 1;
        const std::size_t revealCount =
            (intervalCount + kIntervalsPerReveal - 1) / kIntervalsPerReveal;
        for (std::size_t reveal = 0; reveal < revealCount; ++reveal) {
            const std::size_t first = reveal * kIntervalsPerReveal;
            const std::size_t last = std::min(first + kIntervalsPerReveal, intervalCount);
            std::vector<native::Paths::Point> section(path.begin() + first,
                                                       path.begin() + last + 1);
            const int start = 18 + static_cast<int>(reveal * 112 / revealCount);
            auto trace = native::Paths::strokeLayer(
                "animated-data-section-" + std::to_string(reveal),
                native::Paths::polyline(section), 0, 1, kFrames,
                pathColor, 6.0f, 1920, 1080);
            trace["shape"].erase("operators");
            trace["start_frame"] = start;
            trace["duration_frames"] = kFrames - start;
            // Keep each native path in positive local Y to avoid the known
            // software rasterizer clip, then offset it back to screen space.
            for (auto& command : trace["shape"]["path"])
                command["point"][1] = command["point"][1].get<float>() + 300.f;
            trace["position"] = {0.f, -300.f};
            document["layers"].push_back(std::move(trace));
        }
    }
    if (!file || !(file << document.dump(2) << '\n'))
        throw std::runtime_error("failed to write RenderPlan: " + output.string());
    std::cout << "Wrote " << output << " with " << document["layers"].size() << " layers\n";
}

template<class Author>
void emitScene(const std::filesystem::path& outDir, const std::string& id,
               Author&& author, const std::vector<native::Paths::Point>& path = {},
               const std::string& pathColor = kInk) {
    SampleAssetBackend backend;
    RenderPlanContentHost host({
        .createText = [&](const TextRequest& request) { return backend.text(request); },
        .createImage = [&](const ImageRequest& request) { return backend.image(request); },
        .createVideo = [&](const VideoRequest& request) { return backend.video(request); },
        .createShape = [&](const ShapeRequest& request) { return backend.shape(request); },
        .currentFingerprint = [&](const ContentId& value) { return backend.fingerprint(value); }});
    TemplateScene scene(id, kFps, host, 1920.f, 1080.f);
    author(scene);
    const auto plan = lowerToRenderPlan(scene, host, id, id + ".mp4");
    writePlan(plan, outDir / (id + ".plan.json"), path, pathColor);
}

} // namespace

int main(int argc, char** argv) {
    if (argc != 2) {
        std::cerr << "usage: chronontemplate_emit_dataviz_sample <plans-directory>\n";
        return 2;
    }
    const std::filesystem::path outDir(argv[1]);
    std::filesystem::create_directories(outDir);
    try {
        std::vector<native::Paths::Point> chinaPath;
        const std::vector<float> chinaValues{195,200,202,216,235,280,275,240,265,295,290,
            310,335,365,365,470,600,700,790,880,980};
        for (std::size_t i = 0; i < chinaValues.size(); ++i) {
            const float x = 260.f + 1510.f * static_cast<float>(i) / 20.f;
            const float y = 700.f - 370.f * chinaValues[i] / 1000.f;
            chinaPath.push_back({x - 960.f, y - 540.f});
        }
        emitScene(outDir, "china_gdp_per_capita", [](TemplateScene& scene) {
            addBackgroundAndEditorialGrid(scene, kTeal);
            addHeader(scene, "ECONOMIA  /  CINA", "La crescita del reddito cinese",
                      "PIL pro capite in valuta locale corrente  ·  1980–2000");
            addChartPanel(scene, 205.f, 276.f, 1810.f, 805.f);
            addHorizontalGrid(scene, 260.f, 330.f, 1770.f, 700.f, 4);
            addAxisLabels(scene, {"1980", "1985", "1990", "1995", "2000"}, 260.f, 1770.f, 742.f);
            for (int i = 0; i < 5; ++i) {
                const float y = 700.f - 370.f * static_cast<float>(i) / 4.f;
                auto& tick = scene.text(TextSpec{.text = std::to_string(i * 250),
                    .font = "assets/fonts/Inter-Regular.ttf", .fontSize = 16.f,
                    .color = kMuted, .name = "value-tick-" + std::to_string(i)});
                tick.position(198.f, kCanvasHeight - y).alive(0, kFrames - 1);
            }
            addStatCell(scene, "≈195", "1980  /  VALORE INIZIALE", 450.f, kTeal, 112.f);
            addStatCell(scene, "≈980", "2000  /  VALORE FINALE", 960.f, kTeal, 112.f);
            addStatCell(scene, "≈5×", "CRESCITA NEL PERIODO", 1470.f, kTeal, 112.f);
            addFooter(scene, "Fonte: Banca Mondiale  ·  valori intermedi ricostruiti visivamente dal riferimento");
        }, chinaPath, kTeal);
        std::vector<native::Paths::Point> germanyPath;
        const std::vector<float> germanyValues{730,725,750,720,701,720,740,755,775,795,810,
            822,834,833,810,785,775,780,773,732,691.5f};
        for (std::size_t i = 0; i < germanyValues.size(); ++i) {
            const float x = 245.f + 1205.f * static_cast<float>(i) / 20.f;
            const float y = 620.f - (germanyValues[i] - 650.f) * 290.f / 200.f;
            germanyPath.push_back({x - 960.f, y - 540.f});
        }
        emitScene(outDir, "german_auto_employment", [](TemplateScene& scene) {
            addBackgroundAndEditorialGrid(scene, kRed);
            addHeader(scene, "INDUSTRIA  /  GERMANIA", "Il lavoro nell’auto tedesca arretra",
                      "Addetti nell’industria automobilistica  ·  migliaia");
            addChartPanel(scene, 190.f, 276.f, 1810.f, 805.f);
            addHorizontalGrid(scene, 245.f, 330.f, 1450.f, 620.f, 4);
            addAxisLabels(scene, {"2006", "2010", "2014", "2018", "2022", "2026"}, 245.f, 1450.f, 654.f);
            for (int i = 0; i < 5; ++i) {
                const float value = 650.f + 50.f * static_cast<float>(i);
                const float y = 620.f - (value - 650.f) * 290.f / 200.f;
                auto& tick = scene.text(TextSpec{.text = std::to_string(static_cast<int>(value)),
                    .font = "assets/fonts/Inter-Regular.ttf", .fontSize = 16.f,
                    .color = kMuted, .name = "value-tick-" + std::to_string(i)});
                tick.position(185.f, kCanvasHeight - y).alive(0, kFrames - 1);
            }
            auto& peak = scene.text(TextSpec{.text = "PICCO  834", .font = "assets/fonts/Inter-Bold.ttf",
                .fontSize = 19.f, .color = kInk, .name = "peak-annotation"});
            peak.position(1025.f, kCanvasHeight - 340.f).alive(92, kFrames - 1).animate(FadeIn{92, 14});
            auto& valueCard = scene.shape(ShapeSpec{.size = Vector2(310.f, 126.f),
                .fillColor = kRed, .name = "latest-value-card", .cornerRadius = 8.f});
            valueCard.position(1580.f, kCanvasHeight - 325.f).alive(120, kFrames - 1).animate(FadeIn{120, 15});
            auto& value = scene.text(TextSpec{.text = "691.500", .font = "assets/fonts/FreeSerif.ttf",
                .fontSize = 45.f, .color = "#FFFFFF", .name = "latest-value"});
            value.position(1580.f, kCanvasHeight - 310.f).alive(120, kFrames - 1).animate(FadeIn{120, 15});
            auto& label = scene.text(TextSpec{.text = "occupati  ·  giugno 2026",
                .font = "assets/fonts/Inter-Bold.ttf", .fontSize = 17.f,
                .color = "#FFFFFF", .name = "latest-value-caption"});
            label.position(1580.f, kCanvasHeight - 355.f).alive(120, kFrames - 1).animate(FadeIn{120, 15});
            auto& lossShadow = scene.shape(ShapeSpec{.size = Vector2(310.f, 108.f),
                .fillColor = "#202528", .name = "annual-loss-shadow", .cornerRadius = 8.f});
            lossShadow.position(1580.f, kCanvasHeight - 488.f - 5.f)
                .opacity(0.09f).alive(120, kFrames - 1).animate(FadeIn{120, 15});
            auto& lossCard = scene.shape(ShapeSpec{.size = Vector2(310.f, 108.f),
                .fillColor = kInk, .name = "annual-loss-card", .cornerRadius = 8.f});
            lossCard.position(1580.f, kCanvasHeight - 488.f)
                .alive(120, kFrames - 1).animate(FadeIn{120, 15});
            auto& lossValue = scene.text(TextSpec{.text = "−144.000", .font = "assets/fonts/FreeSerif.ttf",
                .fontSize = 36.f, .color = "#FFFFFF", .name = "annual-loss-value"});
            lossValue.position(1580.f, kCanvasHeight - 471.f)
                .alive(120, kFrames - 1).animate(FadeIn{120, 15});
            auto& lossCaption = scene.text(TextSpec{.text = "posti persi in un anno",
                .font = "assets/fonts/Inter-Bold.ttf", .fontSize = 16.f,
                .color = "#FFFFFF", .name = "annual-loss-caption"});
            lossCaption.position(1580.f, kCanvasHeight - 515.f)
                .alive(120, kFrames - 1).animate(FadeIn{120, 15});
            addFooter(scene, "Fonte: Destatis  ·  valori e variazioni ripresi dal grafico di riferimento");
        }, germanyPath, kRed);
        emitScene(outDir, "percentage_comparison", [](TemplateScene& scene) {
            addBackgroundAndEditorialGrid(scene, kRed);
            addHeader(scene, "CONFRONTO  /  PERCENTUALI", "Tre valori a confronto",
                      "Categorie e percentuali riprese dal grafico di riferimento");
            addChartPanel(scene, 255.f, 284.f, 1665.f, 970.f);
            DataVizSpec spec;
            spec.values = {38.f, 48.f, 50.f};
            spec.labels = {"38%", "48%", "50%"};
            // The pack's optional highlight halo is a pulsing rectangle; omit
            // it here so it cannot leave a stray translucent strip at the base.
            spec.highlightIndex = -1;
            spec.title.clear();
            spec.barColor = kRed;
            spec.accentColor = kRed;
            spec.labelColor = kInk;
            spec.labelFont = "assets/fonts/FreeSerif.ttf";
            spec.chartHeightFraction = 0.50f;
            spec.marginX = 0.16f;
            spec.showTrendLine = false;
            spec.pingPeak = false;
            spec.name = "percentage-comparison";
            spec.inFrame = 20;
            // Keep the completed bars visible through the final video frame.
            spec.duration = 180;
            (void)addDataVizChart(scene, spec);
            addBarCategories(scene);
            addFooter(scene, "La metrica non è specificata nel riferimento originale");
        });
    } catch (const std::exception& error) {
        std::cerr << "emit_dataviz_sample: " << error.what() << '\n';
        return 1;
    }
    return 0;
}
