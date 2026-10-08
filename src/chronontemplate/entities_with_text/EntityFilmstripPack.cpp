#include "chronontemplate/entities_with_text/EntityFilmstripPack.hpp"

#include "chrononmotion/motion/Easing.hpp"

#include <algorithm>
#include <cmath>
#include <stdexcept>

namespace chronontemplate {
namespace {
using chrononmotion::Vector3;
using chrononmotion::motion::Easing;

float seconds(int frame, float fps) {
    return static_cast<float>(frame) / fps;
}

} // namespace

EntityFilmstripComposition addEntityFilmstrip(
    TemplateScene& scene, const EntityFilmstripSpec& spec) {
    if (spec.items.empty())
        throw std::invalid_argument("addEntityFilmstrip: at least one item is required");
    if (spec.inFrame < 0 || spec.itemDuration < 18 || spec.overlapFrames < 1 ||
        spec.overlapFrames >= spec.itemDuration ||
        !std::isfinite(spec.imageWidth) || spec.imageWidth <= 0.f ||
        !std::isfinite(spec.imageHeight) || spec.imageHeight <= 0.f ||
        !std::isfinite(spec.cornerRadius) || spec.cornerRadius < 0.f ||
        spec.cornerRadius > std::min(spec.imageWidth, spec.imageHeight) * 0.5f ||
        !std::isfinite(spec.titleFontSize) || spec.titleFontSize <= 0.f ||
        spec.font.empty() || spec.background.empty() || spec.ink.empty() ||
        !std::isfinite(spec.gridSpacing) || spec.gridSpacing < 12.f || spec.gridSpacing > 512.f)
        throw std::invalid_argument("addEntityFilmstrip: invalid timing or visual settings");
    for (const auto& item : spec.items) {
        if (item.imagePath.empty() || item.title.empty())
            throw std::invalid_argument("addEntityFilmstrip: each item needs an image and title");
    }

    const auto canvas = scene.canvas();
    const float centerX = canvas.x * 0.5f;
    const float imageY = canvas.y * 0.5f + spec.imageHeight * 0.18f;
    const float titleY = imageY - spec.imageHeight * 0.5f - spec.titleFontSize * 0.9f;
    const float canvasScale = 1.12f;
    const chrononmotion::Vector2 backgroundSize(canvas.x * canvasScale, canvas.y * canvasScale);
    const int step = spec.itemDuration - spec.overlapFrames;
    const int endFrame = spec.inFrame + step * static_cast<int>(spec.items.size()) + spec.overlapFrames;
    EntityFilmstripComposition result;
    result.endFrame = endFrame;

    auto& background = scene.shape(ShapeSpec{
        .size = backgroundSize,
        .fillColor = spec.background,
        .name = "EntityFilmstripBackground"});
    background.position(centerX, canvas.y * 0.5f, -20.f).alive(spec.inFrame, endFrame);
    auto& grid = scene.shape(ShapeSpec{
        .size = backgroundSize,
        .fillColor = spec.background,
        .name = "EntityFilmstripGrid",
        .fillEnabled = false,
        .geometry = ShapeGeometry::Grid,
        .gridSpacing = spec.gridSpacing,
        .strokeColor = "#171719",
        .strokeWidth = 0.7f});
    grid.position(centerX, canvas.y * 0.5f, -18.f).opacity(0.12f).alive(spec.inFrame, endFrame);
    result.backgroundLayer = background.id();

    const float enterX = canvas.x + spec.imageWidth * 0.5f;
    const float exitX = -spec.imageWidth * 0.5f;
    const float settleNudge = 18.f;
    const int settleIn = std::max(3, spec.overlapFrames / 3);
    const int leaveStart = spec.itemDuration - spec.overlapFrames;

    for (std::size_t index = 0; index < spec.items.size(); ++index) {
        const int start = spec.inFrame + static_cast<int>(index) * step;
        const int finish = start + spec.itemDuration;
        const int holdStart = start + settleIn;
        const int fadeInEnd = start + std::max(2, spec.overlapFrames / 2);
        const int fadeOutStart = start + leaveStart;
        const auto& item = spec.items[index];

        auto& image = scene.image(ImageSpec{
            .path = item.imagePath,
            .name = "EntityFilmstripImage",
            .frame = ImageFrameStyle{.cornerRadius = spec.cornerRadius},
            .fit = ImageFitMode::Cover,
            .targetSize = chrononmotion::Vector2(spec.imageWidth, spec.imageHeight)});
        image.position(centerX, imageY, 2.f).alive(start, finish);
        auto& imagePosition = image.layer().tracks.position;
        imagePosition.add(seconds(start, scene.fps()), Vector3(enterX, imageY - settleNudge, 0.f), Easing::easeIn());
        imagePosition.add(seconds(holdStart, scene.fps()), Vector3(centerX, imageY, 0.f), Easing::expoOut());
        imagePosition.add(seconds(fadeOutStart, scene.fps()), Vector3(centerX, imageY, 0.f), Easing::linear());
        imagePosition.add(seconds(finish, scene.fps()), Vector3(exitX, imageY + settleNudge, 0.f), Easing::easeIn());
        auto& imageOpacity = image.layer().tracks.opacity;
        imageOpacity.add(seconds(start, scene.fps()), 0.f, Easing::linear());
        imageOpacity.add(seconds(fadeInEnd, scene.fps()), 1.f, Easing::easeOut());
        imageOpacity.add(seconds(fadeOutStart, scene.fps()), 1.f, Easing::linear());
        imageOpacity.add(seconds(finish, scene.fps()), 0.f, Easing::easeIn());
        auto& imageScale = image.layer().tracks.scale;
        imageScale.add(seconds(start, scene.fps()), Vector3(0.985f, 0.985f, 1.f), Easing::easeOut());
        imageScale.add(seconds(holdStart, scene.fps()), Vector3(1.f, 1.f, 1.f), Easing::easeOut());
        imageScale.add(seconds(fadeOutStart, scene.fps()), Vector3(1.018f, 1.018f, 1.f), Easing::linear());
        imageScale.add(seconds(finish, scene.fps()), Vector3(1.025f, 1.025f, 1.f), Easing::easeIn());

        auto& title = scene.text(TextSpec{
            .text = item.title,
            .font = spec.font,
            .fontSize = spec.titleFontSize,
            .color = spec.ink,
            .name = "EntityFilmstripTitle"});
        const float titleCenterX = centerX;
        title.position(titleCenterX, titleY, 4.f).alive(start, finish);
        auto& titlePosition = title.layer().tracks.position;
        titlePosition.add(seconds(start, scene.fps()), Vector3(enterX + 48.f, titleY, 0.f), Easing::easeIn());
        titlePosition.add(seconds(holdStart, scene.fps()), Vector3(titleCenterX, titleY, 0.f), Easing::expoOut());
        titlePosition.add(seconds(fadeOutStart, scene.fps()), Vector3(titleCenterX, titleY, 0.f), Easing::linear());
        titlePosition.add(seconds(finish, scene.fps()), Vector3(exitX - 48.f, titleY, 0.f), Easing::easeIn());
        auto& titleOpacity = title.layer().tracks.opacity;
        titleOpacity.add(seconds(start, scene.fps()), 0.f, Easing::linear());
        titleOpacity.add(seconds(fadeInEnd + 2, scene.fps()), 1.f, Easing::easeOut());
        titleOpacity.add(seconds(fadeOutStart, scene.fps()), 1.f, Easing::linear());
        titleOpacity.add(seconds(finish, scene.fps()), 0.f, Easing::easeIn());
        auto& titleScale = title.layer().tracks.scale;
        titleScale.add(seconds(start, scene.fps()), Vector3(0.97f, 0.97f, 1.f), Easing::easeOut());
        titleScale.add(seconds(holdStart, scene.fps()), Vector3(1.f, 1.f, 1.f), Easing::easeOut());
        titleScale.add(seconds(fadeOutStart, scene.fps()), Vector3(1.f, 1.f, 1.f), Easing::linear());
        titleScale.add(seconds(finish, scene.fps()), Vector3(0.985f, 0.985f, 1.f), Easing::easeIn());

        result.imageLayers.push_back(image.id());
        result.titleLayers.push_back(title.id());
    }
    return result;
}

} // namespace chronontemplate
