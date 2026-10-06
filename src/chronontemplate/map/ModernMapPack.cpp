#include "chronontemplate/map/ModernMapPack.hpp"

#include "chrononmotion/math/MathUtils.hpp"
#include "chrononmotion/motion/Presets.hpp"

#include <algorithm>
#include <cmath>
#include <limits>
#include <stdexcept>
#include <string>

namespace chronontemplate {
namespace {
using chrononmotion::Vector2;

float cameraTravelFraction(MapCameraMove move) {
    switch (move) {
        case MapCameraMove::Hold: return 0.f;
        case MapCameraMove::PushIn: return 0.60f;
        case MapCameraMove::OrbitSettle: return 0.70f;
        case MapCameraMove::LateralDrift: return 0.50f;
        case MapCameraMove::PullBack: return 0.50f;
    }
    return 0.f;
}

void validateTypography(const MapTypography& type) {
    if (type.font.empty() || type.color.empty() || !std::isfinite(type.fontSize) ||
        type.fontSize <= 0.f || type.fontSize > 256.f)
        throw std::invalid_argument("composeModernMap: typography requires a font, color, and size in (0,256]");
    if (type.stroke && (type.stroke->color.empty() || !std::isfinite(type.stroke->width) ||
                        type.stroke->width < 0.f || type.stroke->width > 16.f))
        throw std::invalid_argument("composeModernMap: invalid text stroke");
    if (type.shadow && (type.shadow->color.empty() || !std::isfinite(type.shadow->opacity) ||
                        type.shadow->opacity < 0.f || type.shadow->opacity > 1.f ||
                        !std::isfinite(type.shadow->blur) || type.shadow->blur < 0.f || type.shadow->blur > 64.f ||
                        !std::isfinite(type.shadow->offset.x) || !std::isfinite(type.shadow->offset.y)))
        throw std::invalid_argument("composeModernMap: invalid text shadow");
    if (type.glow && (type.glow->color.empty() || !std::isfinite(type.glow->radius) ||
                      type.glow->radius < 0.f || type.glow->radius > 128.f ||
                      !std::isfinite(type.glow->intensity) || type.glow->intensity < 0.f || type.glow->intensity > 1.f))
        throw std::invalid_argument("composeModernMap: invalid text glow");
    if (type.background && (type.background->color.empty() ||
                            !std::isfinite(type.background->opacity) || type.background->opacity < 0.f ||
                            type.background->opacity > 1.f || !std::isfinite(type.background->radius) ||
                            type.background->radius < 0.f || type.background->radius > 128.f ||
                            !std::isfinite(type.background->padding.x) || type.background->padding.x < 0.f ||
                            !std::isfinite(type.background->padding.y) || type.background->padding.y < 0.f))
        throw std::invalid_argument("composeModernMap: invalid text background");
}

TextSpec textSpec(const std::string& text, const MapTypography& typography, const std::string& name) {
    validateTypography(typography);
    return TextSpec{.text = text, .font = typography.font, .fontSize = typography.fontSize,
                    .color = typography.color, .name = name, .stroke = typography.stroke,
                    .shadow = typography.shadow, .glow = typography.glow,
                    .background = typography.background};
}
}

MapTypography mapTypographyPreset(MapTextRole role) {
    const MapTypographyRoles presets{};
    switch (role) {
        case MapTextRole::Title: return presets.title;
        case MapTextRole::PrimaryLocation: return presets.primaryLocation;
        case MapTextRole::SecondaryLocation: return presets.secondaryLocation;
        case MapTextRole::DataValue: return presets.dataValue;
        case MapTextRole::Legend: return presets.legend;
        case MapTextRole::Attribution: return presets.attribution;
    }
    return presets.primaryLocation;
}

const char* mapCameraMoveId(MapCameraMove move) noexcept {
    switch (move) {
        case MapCameraMove::Hold: return "map_hold";
        case MapCameraMove::PushIn: return "map_push_in";
        case MapCameraMove::OrbitSettle: return "map_orbit_settle";
        case MapCameraMove::LateralDrift: return "map_lateral_drift";
        case MapCameraMove::PullBack: return "map_pull_back";
    }
    return "unknown";
}

std::vector<MapCameraMove> mapCameraMoves() {
    return {MapCameraMove::Hold, MapCameraMove::PushIn, MapCameraMove::OrbitSettle,
            MapCameraMove::LateralDrift, MapCameraMove::PullBack};
}

ModernMapComposition composeModernMap(TemplateScene& scene, const ModernMapSpec& spec) {
    if (spec.platePath.empty()) throw std::invalid_argument("composeModernMap: plate path is required");
    if (spec.duration <= 0 || spec.inFrame < 0 || spec.inFrame > std::numeric_limits<int>::max() - spec.duration)
        throw std::invalid_argument("composeModernMap: frame window must be positive and non-negative");
    if (!std::isfinite(spec.titleOffset) || !std::isfinite(spec.subtitleOffset))
        throw std::invalid_argument("composeModernMap: title and subtitle offsets must be finite");
    if (!std::isfinite(spec.plateSize.x) || !std::isfinite(spec.plateSize.y) ||
        spec.plateSize.x <= 0.f || spec.plateSize.y <= 0.f)
        throw std::invalid_argument("composeModernMap: plate dimensions must be positive and finite");
    validateTypography(spec.titleTypography);
    validateTypography(spec.subtitleTypography);
    validateTypography(spec.attributionTypography);

    const auto canvas = scene.canvas();
    const int endFrame = spec.inFrame + spec.duration;
    const int enterFrames = std::max(1, spec.duration / 10);
    const int exitFrames = std::max(1, std::min(18, spec.duration / 8));
    const int travelFrames = static_cast<int>(static_cast<float>(spec.duration) * cameraTravelFraction(spec.cameraMove));
    ModernMapComposition result;
    result.inFrame = spec.inFrame;
    result.endFrame = endFrame;

    LayerHandle& plate = scene.image(ImageSpec{.path = spec.platePath, .name = "modern_map_plate",
                                                .targetSize = spec.plateSize});
    plate.position(canvas.x * 0.5f, canvas.y * 0.5f).alive(spec.inFrame, endFrame)
            .animate(FadeIn{.inFrame = spec.inFrame, .duration = enterFrames})
            .animate(FadeOut{.startFrame = endFrame - exitFrames, .duration = exitFrames});
    result.plate = &plate;

    std::vector<std::size_t> order(spec.markers.size());
    for (std::size_t i = 0; i < order.size(); ++i) order[i] = i;
    std::stable_sort(order.begin(), order.end(), [&](std::size_t a, std::size_t b) {
        if (spec.markers[a].priority != spec.markers[b].priority)
            return spec.markers[a].priority > spec.markers[b].priority;
        return a < b;
    });
    const int stagger = std::max(1, spec.duration / (static_cast<int>(spec.markers.size()) + 2));
    for (std::size_t rank = 0; rank < order.size(); ++rank) {
        const auto& marker = spec.markers[order[rank]];
        if (!std::isfinite(marker.position.x) || !std::isfinite(marker.position.y) ||
            !std::isfinite(marker.labelOffset.x) || !std::isfinite(marker.labelOffset.y) ||
            !std::isfinite(marker.size) || marker.size <= 0.f || marker.size > 256.f || marker.color.empty())
            throw std::invalid_argument("composeModernMap: marker requires finite positions and a positive size");
        const MapTypography typography = marker.typography.value_or(mapTypographyPreset(marker.role));
        validateTypography(typography);

        LayerHandle& dot = scene.shape(ShapeSpec{.size = Vector2(marker.size, marker.size),
                                                  .fillColor = marker.color,
                                                  .name = "modern_map_marker_" + std::to_string(order[rank]),
                                                  .cornerRadius = marker.size * 0.5f});
        dot.position(marker.position.x, marker.position.y).alive(spec.inFrame, endFrame)
                .animate(ScalePop{.inFrame = spec.inFrame + enterFrames + static_cast<int>(rank) * stagger,
                                 .duration = std::max(2, stagger), .from = 0.35f, .to = 1.f})
                .animate(FadeIn{.inFrame = spec.inFrame + enterFrames, .duration = enterFrames})
                .animate(FadeOut{.startFrame = endFrame - exitFrames, .duration = exitFrames});
        result.markers.push_back(&dot);

        if (!marker.label.empty()) {
            LayerHandle& label = scene.text(textSpec(marker.label, typography,
                                                       "modern_map_label_" + std::to_string(order[rank])));
            label.position(marker.position.x + marker.labelOffset.x,
                           marker.position.y + marker.labelOffset.y).alive(spec.inFrame, endFrame)
                    .animate(SlideIn{.direction = chrononmotion::motion::presets::Direction::Up,
                                     .inFrame = spec.inFrame + enterFrames + static_cast<int>(rank) * stagger,
                                     .duration = std::max(2, stagger), .distance = 16.f})
                    .animate(FadeIn{.inFrame = spec.inFrame + enterFrames + static_cast<int>(rank) * stagger,
                                   .duration = std::max(2, stagger)})
                    .animate(FadeOut{.startFrame = endFrame - exitFrames, .duration = exitFrames});
            result.labels.push_back(&label);
        }
    }

    const auto addEditorialText = [&](const std::string& text, const MapTypography& typography,
                                      const std::string& name, Vector2 position, int revealFrame,
                                      int revealDuration) -> LayerHandle* {
        if (text.empty()) return nullptr;
        LayerHandle& layer = scene.text(textSpec(text, typography, name));
        layer.position(position.x, position.y).alive(spec.inFrame, endFrame)
                .animate(FadeIn{.inFrame = revealFrame, .duration = revealDuration})
                .animate(FadeOut{.startFrame = endFrame - exitFrames, .duration = exitFrames});
        return &layer;
    };

    result.title = addEditorialText(spec.title, spec.titleTypography, "modern_map_title",
                                    Vector2(canvas.x * 0.5f, canvas.y - spec.titleOffset),
                                    spec.inFrame, enterFrames);
    result.subtitle = addEditorialText(spec.subtitle, spec.subtitleTypography, "modern_map_subtitle",
                                       Vector2(canvas.x * 0.5f, canvas.y - spec.subtitleOffset),
                                       spec.inFrame + enterFrames, enterFrames);
    result.attribution = addEditorialText(spec.attribution, spec.attributionTypography, "modern_map_attribution",
                                          Vector2(canvas.x - 24.f, 28.f), spec.inFrame + enterFrames,
                                          enterFrames);

    for (std::size_t i = 0; i < spec.dataCards.size(); ++i) {
        const auto& card = spec.dataCards[i];
        if (!std::isfinite(card.position.x) || !std::isfinite(card.position.y) ||
            !std::isfinite(card.size.x) || !std::isfinite(card.size.y) ||
            card.size.x <= 0.f || card.size.y <= 24.f || card.accent.empty())
            throw std::invalid_argument("composeModernMap: data card requires finite position and positive size");
        LayerHandle& plateCard = scene.shape(ShapeSpec{.size = card.size, .fillColor = "#101C24",
                                                        .name = "modern_map_data_card_" + std::to_string(i),
                                                        .cornerRadius = 12.f});
        plateCard.position(card.position.x, card.position.y).alive(spec.inFrame, endFrame)
                .animate(FadeIn{.inFrame = spec.inFrame + enterFrames, .duration = enterFrames})
                .animate(FadeOut{.startFrame = endFrame - exitFrames, .duration = exitFrames});
        result.editorial.push_back(&plateCard);
        LayerHandle& accentRail = scene.shape(ShapeSpec{.size = Vector2(4.f, card.size.y - 24.f),
                                                         .fillColor = card.accent,
                                                         .name = "modern_map_data_card_accent_" + std::to_string(i),
                                                         .cornerRadius = 2.f});
        accentRail.position(card.position.x - card.size.x * 0.5f + 10.f, card.position.y)
                .alive(spec.inFrame, endFrame)
                .animate(FadeIn{.inFrame = spec.inFrame + enterFrames, .duration = enterFrames})
                .animate(FadeOut{.startFrame = endFrame - exitFrames, .duration = exitFrames});
        result.editorial.push_back(&accentRail);
        const float left = card.position.x - card.size.x * 0.5f + 20.f;
        const float top = card.position.y - card.size.y * 0.5f;
        if (auto* heading = addEditorialText(card.heading, spec.subtitleTypography,
                "modern_map_data_card_heading_" + std::to_string(i), Vector2(left, top + 34.f),
                spec.inFrame + enterFrames * 2, enterFrames)) result.editorial.push_back(heading);
        if (auto* value = addEditorialText(card.value, mapTypographyPreset(MapTextRole::DataValue),
                "modern_map_data_card_value_" + std::to_string(i), Vector2(left, top + 86.f),
                spec.inFrame + enterFrames * 3, enterFrames)) result.editorial.push_back(value);
    }

    const float legendRow = 30.f;
    for (std::size_t i = 0; i < spec.legend.size(); ++i) {
        const auto& item = spec.legend[i];
        if (item.label.empty() || item.color.empty())
            throw std::invalid_argument("composeModernMap: legend items require label and color");
        const float y = canvas.y * 0.5f - 24.f - legendRow * static_cast<float>(i);
        LayerHandle& swatch = scene.shape(ShapeSpec{.size = Vector2(14.f, 14.f), .fillColor = item.color,
                                                     .name = "modern_map_legend_swatch_" + std::to_string(i),
                                                     .cornerRadius = 7.f});
        swatch.position(28.f, y).alive(spec.inFrame, endFrame)
                .animate(ScalePop{.inFrame = spec.inFrame + enterFrames + static_cast<int>(i) * 2,
                                 .duration = std::max(2, enterFrames / 2), .from = 0.5f, .to = 1.f})
                .animate(FadeOut{.startFrame = endFrame - exitFrames, .duration = exitFrames});
        result.editorial.push_back(&swatch);
        if (auto* label = addEditorialText(item.label, mapTypographyPreset(MapTextRole::Legend),
                "modern_map_legend_label_" + std::to_string(i), Vector2(48.f, y),
                spec.inFrame + enterFrames + static_cast<int>(i) * 2, enterFrames))
            result.editorial.push_back(label);
    }

    for (std::size_t i = 0; i < spec.callouts.size(); ++i) {
        const auto& callout = spec.callouts[i];
        if (callout.label.empty() || callout.color.empty() ||
            !std::isfinite(callout.markerPosition.x) || !std::isfinite(callout.markerPosition.y) ||
            !std::isfinite(callout.elbowPosition.x) || !std::isfinite(callout.elbowPosition.y) ||
            !std::isfinite(callout.textPosition.x) || !std::isfinite(callout.textPosition.y))
            throw std::invalid_argument("composeModernMap: callout coordinates and label must be valid");
        const auto addRule = [&](Vector2 from, Vector2 to, const std::string& suffix, int reveal) {
            const bool horizontal = std::abs(to.x - from.x) >= std::abs(to.y - from.y);
            const Vector2 size = horizontal
                ? Vector2(std::max(2.f, std::abs(to.x - from.x)), 2.f)
                : Vector2(2.f, std::max(2.f, std::abs(to.y - from.y)));
            LayerHandle& rule = scene.shape(ShapeSpec{.size = size, .fillColor = callout.color,
                                                       .name = "modern_map_callout_" + suffix + "_" + std::to_string(i)});
            rule.position((from.x + to.x) * 0.5f, (from.y + to.y) * 0.5f).alive(spec.inFrame, endFrame)
                    .animate(FadeIn{.inFrame = reveal, .duration = enterFrames})
                    .animate(FadeOut{.startFrame = endFrame - exitFrames, .duration = exitFrames});
            result.editorial.push_back(&rule);
        };
        const Vector2 firstBend(callout.elbowPosition.x, callout.markerPosition.y);
        const Vector2 secondBend(callout.textPosition.x, callout.elbowPosition.y);
        addRule(callout.markerPosition, firstBend, "line_a", spec.inFrame + enterFrames);
        addRule(firstBend, callout.elbowPosition, "line_b", spec.inFrame + enterFrames * 2);
        addRule(callout.elbowPosition, secondBend, "line_c", spec.inFrame + enterFrames * 2);
        addRule(secondBend, callout.textPosition, "line_d", spec.inFrame + enterFrames * 3);
        if (auto* label = addEditorialText(callout.label, mapTypographyPreset(MapTextRole::PrimaryLocation),
                "modern_map_callout_label_" + std::to_string(i), callout.textPosition,
                spec.inFrame + enterFrames * 4, enterFrames)) result.editorial.push_back(label);
    }

    switch (spec.cameraMove) {
        case MapCameraMove::Hold: break;
        case MapCameraMove::PushIn: scene.camera().push(320.f).between(spec.inFrame, spec.inFrame + travelFrames); break;
        case MapCameraMove::OrbitSettle: scene.camera().orbit(0.05f, 0.02f).between(spec.inFrame, spec.inFrame + travelFrames); break;
        case MapCameraMove::LateralDrift:
            chrononmotion::motion::presets::cameraPan(scene.cameraRig(), spec.inFrame, travelFrames,
                                                       Vector2(180.f, 0.f), scene.fps());
            break;
        case MapCameraMove::PullBack: scene.camera().push(-420.f).between(spec.inFrame, spec.inFrame + travelFrames); break;
    }
    return result;
}

} // namespace chronontemplate
