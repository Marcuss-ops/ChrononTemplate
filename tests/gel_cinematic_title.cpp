// The GEL cinematic title contract: one full-frame plate, three dielectric
// GEL faces, and the selective optics (including downward light shafts) on the
// face only. Backings are not emitted because they occluded the GEL surface.

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
    check(layers.plate != 0 && layers.backings.empty() && layers.faces.size() == 3,
          "the preset authors one plate and three faces");

    const auto plan = lowerToRenderPlan(scene, host, "gel-title-contract", "gel-title.mp4");
    check(plan.layers.size() == 4, "the lowered plan carries four layers");

    const auto image = std::find_if(plan.layers.begin(), plan.layers.end(),
        [](const LayerPlan& layer) { return layer.type == LayerType::Image; });
    const auto image_count = std::count_if(plan.layers.begin(), plan.layers.end(),
        [](const LayerPlan& layer) { return layer.type == LayerType::Image; });
    check(image != plan.layers.end() && image->asset == "image/plate.png" &&
          image_count == 1,
          "the reference plate lowers as one full-frame screen-space image");

    check(findByText(plan, "calories", false) == nullptr,
          "no extruded backing occludes the GEL face");
    const auto gel_faces = std::count_if(plan.layers.begin(), plan.layers.end(),
        [](const LayerPlan& layer) {
            return layer.type == LayerType::Text && layer.style &&
                   layer.style->gel_surface;
        });
    check(gel_faces == 3, "all three words lower as dielectric faces");

    const LayerPlan* face = findByText(plan, "calories", true);
    check(face != nullptr && face->style && face->style->gel_surface &&
          face->style->gel_transmission_enabled,
          "the face is a dielectric GEL surface");
    check(face != nullptr && face->style &&
          face->style->gel_material_profile == "current",
          "the legacy face keeps the current GEL material profile");
    check(face != nullptr && face->style && face->style->glow &&
          face->style->glow->radius == 4.5f,
          "the tight perimeter glow survives lowering");
    check(face != nullptr && face->effects.size() == 4 &&
          face->effects[0].kind == LayerPlan::EffectKindPlan::DropShadow &&
          face->effects[1].kind == LayerPlan::EffectKindPlan::ChromaticAberration &&
          face->effects[2].kind == LayerPlan::EffectKindPlan::Bloom &&
          face->effects[3].kind == LayerPlan::EffectKindPlan::LightRays,
          "the face carries drop shadow, dispersion, bloom and downward light rays in order");
    check(face != nullptr && face->effects[3].light_rays_origin[0] > 0.19f &&
          face->effects[3].light_rays_origin[0] < 0.21f &&
          face->effects[3].light_rays_origin[1] > 0.43f &&
          face->effects[3].light_rays_origin[1] < 0.45f &&
          face->effects[3].light_rays_length == 300.f &&
          face->effects[3].light_rays_color[3] == 0.34f,
          "the rays originate at the word top centre with the certified extent");
    check(face != nullptr && face->effects[1].chromatic_green_transform[0] == -0.75f &&
          face->effects[1].chromatic_green_transform[1] == -1.05f &&
          face->effects[1].chromatic_blue_transform[0] == 0.85f,
          "the sub-pixel spectral shifts preserve the certified values");

    check(face != nullptr && !face->transform_samples.empty(),
          "the preset authors a resolved transform calendar for the video path");

    // ── Reference closure: the seven-layer 2026-11-07 recipe ────────────────
    TemplateScene referenceScene("gel-title-reference", 30.f, host, 1920.f, 1080.f);
    gel::GelCinematicTitleSpec referenceSpec;
    referenceSpec.look = gel::GelCinematicTitleLook::Reference20261107;
    referenceSpec.name = "gel_ref";
    referenceSpec.plate = "plate.png";
    referenceSpec.font = "LiberationMono-Bold.ttf";
    referenceSpec.fontSize = 125.f;
    referenceSpec.words = {
        {.text = "calories", .x = 382.f, .y = 540.f, .scale = 1.f},
        {.text = "or", .x = 813.f, .y = 540.f, .scale = 1.f},
        {.text = "ingredients", .x = 1408.f, .y = 540.f, .scale = 1.f}};

    const auto referenceLayers = gel::addGelCinematicTitle(referenceScene, referenceSpec);
    check(referenceLayers.plate != 0 && referenceLayers.backings.size() == 3 &&
          referenceLayers.faces.size() == 3,
          "the reference mode authors one plate, three backings and three faces");

    const auto referencePlan =
        lowerToRenderPlan(referenceScene, host, "gel-title-reference", "gel-title-reference.mp4");
    check(referencePlan.layers.size() == 7, "the reference plan carries seven layers");

    int backingCount = 0;
    std::size_t lastBacking = 0;
    std::size_t firstFace = referencePlan.layers.size();
    for (std::size_t i = 0; i < referencePlan.layers.size(); ++i) {
        const auto& layer = referencePlan.layers[i];
        if (layer.type != LayerType::Text || !layer.style) continue;
        if (layer.style->extruded_text && !layer.style->gel_surface) {
            ++backingCount;
            lastBacking = i;
        }
        if (layer.style->gel_surface) firstFace = std::min(firstFace, i);
    }
    check(backingCount == 3 && lastBacking < firstFace,
          "all three extruded backings precede the GEL faces in draw order");

    const LayerPlan* backing = findByText(referencePlan, "calories", false);
    check(backing != nullptr && backing->style && backing->style->extruded_text &&
          backing->style->extrusion_depth == 8.f && backing->style->fill == "#1454FF",
          "the reference backing is an extruded royal-blue mesh at the certified depth");
    check(backing != nullptr && backing->effects.size() == 1 &&
          backing->effects[0].kind == LayerPlan::EffectKindPlan::Catalog &&
          backing->effects[0].canonical_effect_id == "generate.fill",
          "the reference backing keeps the native generate.fill pass");

    const LayerPlan* referenceFace = findByText(referencePlan, "calories", true);
    check(referenceFace != nullptr && referenceFace->style &&
          !referenceFace->style->gel_transmission_enabled,
          "the reference face is opaque");
    check(referenceFace != nullptr && referenceFace->style &&
          referenceFace->style->gel_material_profile == "reference_20261107",
          "the reference face selects the certified GEL material profile");
    check(referenceFace != nullptr && referenceFace->effects.size() == 4 &&
          referenceFace->effects[0].kind == LayerPlan::EffectKindPlan::DropShadow &&
          referenceFace->effects[1].kind == LayerPlan::EffectKindPlan::ChromaticAberration &&
          referenceFace->effects[2].kind == LayerPlan::EffectKindPlan::Bloom &&
          referenceFace->effects[3].kind == LayerPlan::EffectKindPlan::Catalog &&
          referenceFace->effects[3].canonical_effect_id == "light.lens_flare",
          "the reference face carries the pinned streak and no downward shafts");
    check(referenceFace != nullptr && referenceFace->effects[3].canonical_params.size() == 6 &&
          referenceFace->effects[3].canonical_params[0].param == "threshold" &&
          referenceFace->effects[3].canonical_params[0].value == 0.88f &&
          referenceFace->effects[3].canonical_params[5].param == "streak" &&
          referenceFace->effects[3].canonical_params[5].value == 1.f,
          "the reference streak uses the certified threshold and full wing");

    const LayerPlan* referenceOr = findByText(referencePlan, "or", true);
    check(referenceOr != nullptr && referenceOr->style &&
          referenceOr->style->fill == "#00E8FF",
          "the reference keeps the same opaque fill on the centre word");

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
