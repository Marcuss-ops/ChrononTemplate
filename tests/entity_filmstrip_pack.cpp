#include "chronontemplate/entities_with_text/EntityFilmstripPack.hpp"

#include "fake_content_host.hpp"
#include "motion_check.hpp"

#include <cmath>
#include <stdexcept>

using namespace chronontemplate;
using chronontemplate_test::FakeContentHost;
using chronontemplate_test::findLayer;
using chrononmotion::Vector3;
using chrononmotion_test::check;
using chrononmotion_test::checkNear;
using chrononmotion_test::section;

namespace {
void itemImagesAndNativeTitlesMoveTogetherOnTheFilmstrip() {
    section("reference-driven horizontal entity filmstrip");
    FakeContentHost host;
    TemplateScene scene("entity_filmstrip", 30.f, host, 1920.f, 1080.f);
    EntityFilmstripSpec spec;
    spec.items = {{"jim-rohn.png", "FILOSOFIA"}, {"jim-rohn.png", "DISCIPLINA"}};
    spec.itemDuration = 48;
    spec.overlapFrames = 28;
    const auto result = addEntityFilmstrip(scene, spec);
    check(result.imageLayers.size() == 2 && result.titleLayers.size() == 2,
          "every filmstrip item has one Chronon image and one separate native title");
    check(result.endFrame == 68, "filmstrip duration includes both quick passes and overlap");
    check(scene.motion().layerCount() == 6,
          "composition contains background, grid, and two image/title pairs");
    const auto atStart = scene.submit(0);
    const auto atSettled = scene.submit(18);
    const auto atHandoff = scene.submit(21);
    const auto atEnd = scene.submit(result.endFrame);
    const auto* firstImageStart = findLayer(atStart, result.imageLayers[0]);
    const auto* firstImageSettled = findLayer(atSettled, result.imageLayers[0]);
    const auto* firstImageHandoff = findLayer(atHandoff, result.imageLayers[0]);
    const auto* secondImageHandoff = findLayer(atHandoff, result.imageLayers[1]);
    const auto* lastImage = findLayer(atEnd, result.imageLayers.back());
    check(firstImageStart && firstImageSettled && firstImageHandoff && secondImageHandoff && lastImage,
          "each image can be sampled at the opening, hold, overlap and exit");
    checkNear(firstImageStart->transform.opacity, 0.f, 1e-4f,
              "opening image is hidden before its fast entrance");
    checkNear(firstImageSettled->transform.opacity, 1.f, 1e-4f,
              "first image has reached its readable hold");
    if (firstImageStart && firstImageSettled) {
        const auto& openingMatrix = firstImageStart->transform.world;
        const auto& settledMatrix = firstImageSettled->transform.world;
        check(openingMatrix[12] > settledMatrix[12],
              "first image rapidly enters from the right before settling");
        check(firstImageStart->transform.opacity < 0.01f && firstImageSettled->transform.opacity > 0.99f,
              "first image fades on quickly into a readable hold");
    }

    check(firstImageHandoff && firstImageHandoff->transform.opacity > 0.01f &&
              firstImageHandoff->transform.opacity < 1.f && secondImageHandoff &&
              secondImageHandoff->transform.opacity > 0.f,
          "the next image begins entering as the prior item yields");
    check(lastImage && lastImage->transform.opacity < 1e-4f,
          "last image is fully off at the authored end frame");
    const auto* firstTitle = findLayer(atSettled, result.titleLayers.front());
    const auto* firstImage = findLayer(atSettled, result.imageLayers.front());
    check(firstTitle && firstImage &&
              std::fabs(firstTitle->transform.world[12] - firstImage->transform.world[12]) < 1e-3f,
          "the title stays horizontally registered with its image");
    check(host.lastImageRequest().path == "jim-rohn.png" &&
              host.lastImageRequest().cornerRadius == spec.cornerRadius,
          "the normal image host receives the source and rounded editorial treatment");
    const auto* grid = host.findShapeRequest("EntityFilmstripGrid");
    check(grid && grid->geometry == ShapeGeometry::Grid && grid->gridSpacing == spec.gridSpacing,
          "warm background grid is a native Chronon shape, not baked into the image");
}

void invalidFilmstripSpecsFailClosed() {
    section("invalid entity filmstrip input is rejected");
    FakeContentHost host;
    bool rejected = false;
    try {
        TemplateScene scene("empty_filmstrip", 30.f, host);
        EntityFilmstripSpec spec;
        (void)addEntityFilmstrip(scene, spec);
    } catch (const std::invalid_argument&) { rejected = true; }
    check(rejected, "empty filmstrip is refused");

    rejected = false;
    try {
        TemplateScene scene("bad_overlap_filmstrip", 30.f, host);
        EntityFilmstripSpec spec;
        spec.items = {{"portrait.png", "NAME"}};
        spec.overlapFrames = spec.itemDuration;
        (void)addEntityFilmstrip(scene, spec);
    } catch (const std::invalid_argument&) { rejected = true; }
    check(rejected, "overlap as long as an item is refused");

    rejected = false;
    try {
        TemplateScene scene("bad_title_filmstrip", 30.f, host);
        EntityFilmstripSpec spec;
        spec.items = {{"portrait.png", ""}};
        (void)addEntityFilmstrip(scene, spec);
    } catch (const std::invalid_argument&) { rejected = true; }
    check(rejected, "every image must have a paired title");
}
} // namespace

int main() {
    itemImagesAndNativeTitlesMoveTogetherOnTheFilmstrip();
    invalidFilmstripSpecsFailClosed();
    return chrononmotion_test::report();
}
