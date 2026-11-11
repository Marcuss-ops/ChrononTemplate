// The GEL cinematic title contract covers the approved seven-layer reference
// look and the retained legacy dielectric-only mode.

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
    check(spec.look == gel::GelCinematicTitleLook::legacy_dielectric,
          "existing callers retain the legacy preset by default");
    spec.look = gel::GelCinematicTitleLook::reference_20261107;
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
          "the reference preset authors one plate, three backings and three faces");

    const auto plan = lowerToRenderPlan(scene, host, "gel-title-contract", "gel-title.mp4");
    check(plan.layers.size() == 7, "the reference plan carries seven layers");

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
          "the royal-blue backing is emitted as real extruded text");
    check(backing != nullptr && !backing->effects.empty() &&
          backing->effects[0].kind == LayerPlan::EffectKindPlan::Catalog &&
          backing->effects[0].canonical_effect_id == "generate.fill",
          "the backing keeps its blue side-light fill pass");
    check(plan.layers.size() == 7 && plan.layers[1].style &&
          plan.layers[1].style->extruded_text && plan.layers[3].style &&
          plan.layers[3].style->extruded_text && plan.layers[4].style &&
          plan.layers[4].style->gel_surface,
          "all backing layers precede all GEL faces in composite order");
    const auto gel_faces = std::count_if(plan.layers.begin(), plan.layers.end(),
        [](const LayerPlan& layer) {
            return layer.type == LayerType::Text && layer.style &&
                   layer.style->gel_surface;
        });
    check(gel_faces == 3, "all three words lower as dielectric faces");

    const LayerPlan* face = findByText(plan, "calories", true);
    check(face != nullptr && face->style && face->style->gel_surface &&
          !face->style->gel_transmission_enabled,
          "reference faces are opaque GEL surfaces that fully occlude the backing");
    check(face != nullptr && face->style && face->style->glow &&
          face->style->glow->radius == 4.5f,
          "the tight perimeter glow survives lowering");
    check(face != nullptr && face->effects.size() == 4 &&
          face->effects[0].kind == LayerPlan::EffectKindPlan::DropShadow &&
          face->effects[1].kind == LayerPlan::EffectKindPlan::ChromaticAberration &&
          face->effects[2].kind == LayerPlan::EffectKindPlan::Bloom &&
          face->effects[3].kind == LayerPlan::EffectKindPlan::Catalog &&
          face->effects[3].canonical_effect_id == "light.lens_flare",
          "the face carries contact shadow, dispersion, tight glow, bloom and horizontal flare");
    const auto flareParam = [&](const char* name) {
        const auto& params = face->effects[3].canonical_params;
        const auto found = std::find_if(params.begin(), params.end(),
            [&](const EffectPlan::ParamValue& param) { return param.param == name; });
        return found == params.end() ? -1.f : found->value;
    };
    check(face != nullptr && flareParam("threshold") == 0.88f &&
          flareParam("intensity") == 0.55f && flareParam("radius") == 0.98f &&
          flareParam("streak") == 1.f,
          "the horizontal anamorphic streak uses the reference parameters");
    check(face != nullptr && face->effects[1].chromatic_green_transform[0] == -0.75f &&
          face->effects[1].chromatic_green_transform[1] == -1.05f &&
          face->effects[1].chromatic_blue_transform[0] == 0.85f,
          "the sub-pixel spectral shifts preserve the certified values");

    check(face != nullptr && !face->transform_samples.empty(),
          "the preset authors a resolved transform calendar for the video path");

    TemplateScene legacyScene("gel-title-legacy-contract", 30.f, host, 1920.f, 1080.f);
    auto legacySpec = spec;
    legacySpec.look = gel::GelCinematicTitleLook::legacy_dielectric;
    const auto legacyLayers = gel::addGelCinematicTitle(legacyScene, legacySpec);
    const auto legacyPlan = lowerToRenderPlan(legacyScene, host,
        "gel-title-legacy-contract", "gel-title-legacy.mp4");
    check(legacyLayers.backings.empty() && legacyLayers.faces.size() == 3 &&
          legacyPlan.layers.size() == 4,
          "legacy mode preserves its plate-plus-three-faces output");
    const LayerPlan* legacyFace = findByText(legacyPlan, "calories", true);
    check(legacyFace != nullptr && legacyFace->style &&
          legacyFace->style->gel_transmission_enabled &&
          legacyFace->effects.back().kind == LayerPlan::EffectKindPlan::LightRays,
          "legacy mode retains transmitted faces and downward light rays");

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
