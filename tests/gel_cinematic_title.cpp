// The GEL cinematic title contract: one full-frame plate, three extruded
// backings with the native fill pass, three opaque GEL faces, and the selective
// optics on the face only.

#include "chronontemplate/core/RenderPlanContentHost.hpp"
#include "chronontemplate/gel/GelCinematicTitlePack.hpp"

#include "fake_content_host.hpp"
#include "motion_check.hpp"

#include <algorithm>
#include <stdexcept>

using namespace chronontemplate;
using namespace chronon3d::render_plan;
using chronontemplate_test::FakeContentHost;
using chrononmotion_test::check;

namespace {

    const LayerPlan* findByText(const RenderPlan& plan, const std::string& text, bool gel) {
        const auto found = std::find_if(plan.layers.begin(), plan.layers.end(),
            [&](const LayerPlan& layer) {
                return layer.type == LayerType::Text && layer.text == text &&
                       layer.style && layer.style->gel_surface == gel;
            });
        return found == plan.layers.end() ? nullptr : &*found;
    }

}// namespace

int main() {
    FakeContentHost backend;
    RenderPlanContentHost host(RenderPlanContentBackend{
        .createText = [&](const TextRequest& request) { return backend.createText(request); },
        .createImage = [&](const ImageRequest& request) { return backend.createImage(request); },
        .createVideo = [&](const VideoRequest& request) { return backend.createVideo(request); },
        .createShape = [&](const ShapeRequest& request) { return backend.createShape(request); },
        .currentFingerprint = [&](const ContentId& id) { return backend.currentFingerprint(id); }});

    TemplateScene scene("gel-title-contract", 30.f, host, 1920.f, 1080.f);
    gel::GelCinematicTitleSpec spec;
    spec.name = "gel_title";
    spec.plate = "plate.png";
    spec.font = "LiberationMono-Bold.ttf";
    spec.fontSize = 125.f;
    spec.words = {
        {.text = "calories", .x = 382.f, .y = 540.f, .scale = 1.f},
        {.text = "or", .x = 813.f, .y = 540.f, .scale = 1.f},
        {.text = "ingredients", .x = 1408.f, .y = 540.f, .scale = 1.f}};

    const auto layers = gel::addGelCinematicTitle(scene, spec);
    check(layers.plate != 0 && layers.backings.size() == 3 && layers.faces.size() == 3,
          "the preset authors one plate, three backings and three faces");

    const auto plan = lowerToRenderPlan(scene, host, "gel-title-contract", "gel-title.mp4");
    check(plan.layers.size() == 7, "the lowered plan carries seven layers");

    const auto image = std::find_if(plan.layers.begin(), plan.layers.end(),
        [](const LayerPlan& layer) { return layer.type == LayerType::Image; });
    const auto image_count = std::count_if(plan.layers.begin(), plan.layers.end(),
        [](const LayerPlan& layer) { return layer.type == LayerType::Image; });
    check(image != plan.layers.end() && image->asset == "image/plate.png" &&
          image_count == 1,
          "the reference plate lowers as one full-frame screen-space image");

    const LayerPlan* backing = findByText(plan, "calories", false);
    check(backing != nullptr && backing->style && backing->style->extruded_text &&
          backing->style->extrusion_depth == 8.f,
          "the backing word requests real extruded geometry at the certified depth");
    check(backing != nullptr && backing->effects.size() == 1 &&
          backing->effects.front().kind == LayerPlan::EffectKindPlan::Catalog &&
          backing->effects.front().canonical_effect_id == "generate.fill",
          "the backing keeps the native generate.fill pass");

    const LayerPlan* face = findByText(plan, "calories", true);
    check(face != nullptr && face->style && face->style->gel_surface &&
          !face->style->gel_transmission_enabled,
          "the face is an opaque GEL surface");
    check(face != nullptr && face->style && face->style->glow &&
          face->style->glow->radius == 4.5f,
          "the tight perimeter glow survives lowering");
    check(face != nullptr && face->effects.size() == 4 &&
          face->effects[0].kind == LayerPlan::EffectKindPlan::DropShadow &&
          face->effects[1].kind == LayerPlan::EffectKindPlan::ChromaticAberration &&
          face->effects[2].kind == LayerPlan::EffectKindPlan::Bloom &&
          face->effects[3].kind == LayerPlan::EffectKindPlan::Catalog &&
          face->effects[3].canonical_effect_id == "light.lens_flare",
          "the face carries drop shadow, dispersion, bloom and the highlight-only streak in order");
    check(face != nullptr && face->effects[3].canonical_params.size() == 6 &&
          face->effects[3].canonical_params[5].param == "streak" &&
          face->effects[3].canonical_params[5].value == 1.f,
          "the anamorphic streak keeps the certified horizontal contract");
    check(face != nullptr && face->effects[1].chromatic_green_transform[0] == -0.75f &&
          face->effects[1].chromatic_green_transform[1] == -1.05f &&
          face->effects[1].chromatic_blue_transform[0] == 0.85f,
          "the sub-pixel spectral shifts preserve the certified values");

    check(face != nullptr && !face->transform_samples.empty(),
          "the preset authors a resolved transform calendar for the video path");

    bool emptyWordsRejected = false;
    try {
        gel::GelCinematicTitleSpec bad;
        bad.font = "font.ttf";
        (void)gel::addGelCinematicTitle(scene, bad);
    } catch (const std::invalid_argument&) {
        emptyWordsRejected = true;
    }
    check(emptyWordsRejected, "an empty title fails closed");

    bool missingFontRejected = false;
    try {
        gel::GelCinematicTitleSpec bad;
        bad.words = {{.text = "x", .x = 0.f, .y = 0.f, .scale = 1.f}};
        (void)gel::addGelCinematicTitle(scene, bad);
    } catch (const std::invalid_argument&) {
        missingFontRejected = true;
    }
    check(missingFontRejected, "a missing font fails closed");

    bool deepExtrusionRejected = false;
    try {
        gel::GelCinematicTitleSpec bad;
        bad.font = "font.ttf";
        bad.extrusionDepth = 300.f;
        bad.words = {{.text = "x", .x = 0.f, .y = 0.f, .scale = 1.f}};
        (void)gel::addGelCinematicTitle(scene, bad);
    } catch (const std::invalid_argument&) {
        deepExtrusionRejected = true;
    }
    check(deepExtrusionRejected, "out-of-contract extrusion fails closed");

    return chrononmotion_test::report();
}
