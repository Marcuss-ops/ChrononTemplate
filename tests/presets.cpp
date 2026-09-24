#include "chronontemplate/Presets.hpp"
#include "chrononmotion/motion/CompiledScene.hpp"

#include "motion_check.hpp"

#include <limits>
#include <stdexcept>
#include <string>
using namespace chrononmotion;
using namespace chrononmotion::motion;
using namespace chronontemplate;
using chrononmotion_test::check;
using chrononmotion_test::section;

namespace {

    Final3DData finalData() {
        Final3DData data;
        data.title = "GLOW 3D";
        data.subtitle = "FINAL ANIMATION";
        data.assetId = "product.asset";
        data.startFrame = 10;
        data.duration = 120;
        return data;
    }

    void finalCatalog() {
        section("final 3D preset catalog");
        check(final3DPresets().size() == 11, "final 3D catalog exposes eleven presets including the new text dolly/orbit glow recipe");
        check(std::string(name(Final3DPreset::MacBookProduct)) == "macbook_product",
              "macbook preset has a stable wire name");
        check(std::string(name(Final3DPreset::Typewriter3DGlow)) == "typewriter_3d_glow",
              "typewriter preset has a stable wire name");
        check(std::string(name(Final3DPreset::CleanRed)) == "clean_red",
              "clean red preset has a stable wire name");
        check(std::string(name(Final3DPreset::YouTubeCanary)) == "youtube_canary",
              "YouTube canary has a stable wire name");
        check(std::string(name(Final3DPreset::TextDollyOrbitGlow)) == "text_dolly_orbit_glow",
              "text dolly/orbit glow has a stable wire name");

        for (const Final3DPreset preset : final3DPresets()) {
            Composition composition = build(preset, finalData());
            check(composition.scene.validate().empty(), "final 3D preset has a valid hierarchy");
            check(composition.scene.lightCount() >= 2, "final 3D preset contains key and fill lights");
            check(composition.material.kind != MaterialKind::Unlit, "final 3D preset declares a lit/emissive material");
            check(composition.camera.hasTarget(), "final 3D preset contains a camera target");

            // Every text layer declares its real font; Glow styling itself is
            // deliberately owned by Chronon3D's single simple effect.
            for (const Layer& layer : composition.scene.layers()) {
                if (!layer.content.isText()) continue;
                const auto declared = composition.textStyles.find(layer.id);
                check(declared != composition.textStyles.end() && !declared->second.empty(),
                      "final 3D preset declares a real font on its text layers");
            }

            composition.scene.evaluate(10);
            const auto first = composition.scene.worldMatrix(2);
            composition.scene.evaluate(80);
            composition.scene.evaluate(10);
            const auto second = composition.scene.worldMatrix(2);
            bool identical = true;
            for (unsigned int i = 0; i < 16; ++i) {
                if (first[i] != second[i]) identical = false;
            }
            check(identical, "final 3D preset evaluation is deterministic");
            check(composition.scene.compile().lights.size() >= 2,
                  "final 3D preset compiles evaluated light states");
        }
    }

    void stylePresets() {
        section("style presets");
        const Final3DData data = finalData();

        const Composition macBook = build(Final3DPreset::MacBookProduct, data);
        const Layer* product = macBook.scene.findLayer("MacBookProduct");
        check(product != nullptr && product->content.isImage(),
              "macbook preset places an image product under the scene root");
        check(macBook.scene.validate().empty(), "macbook preset has a valid hierarchy");

        const Composition typewriter = build(Final3DPreset::Typewriter3DGlow, data);
        std::size_t textLayers = 0;
        for (const Layer& layer : typewriter.scene.layers()) {
            if (layer.content.isText()) ++textLayers;
        }
        check(textLayers == 1, "typewriter keeps one complete TextContentId");
        check(typewriter.scene.validate().empty(), "typewriter preset has a valid hierarchy");
        check(typewriter.textStyles.find(2) != typewriter.textStyles.end(),
              "typewriter title carries the Chronon font intent");

        Composition canary = build(Final3DPreset::YouTubeCanary, Final3DData{
                .title = "CHRONON", .subtitle = "YOUTUBE CANARY", .assetId = "product.asset",
                .titleFont = "assets/fonts/Inter-Bold.ttf", .subtitleFont = "assets/fonts/Inter-Regular.ttf",
                .fps = 30.f, .startFrame = 0, .duration = 120});
        check(canary.scene.validate().empty(), "YouTube canary has a valid hierarchy");
        Composition staticText = build(Final3DPreset::TextStatic, Final3DData{
                .title = "CHRONON", .subtitle = "STATIC TEXT", .assetId = "product.asset",
                .titleFont = "assets/fonts/Inter-Bold.ttf", .subtitleFont = "assets/fonts/Inter-Regular.ttf",
                .fps = 30.f, .startFrame = 0, .duration = 120});
        check(staticText.scene.validate().empty(), "static text canary has a valid hierarchy");
        check(staticText.material.kind == MaterialKind::Lambert,
              "static text canary has no emissive glow material");
        check(staticText.scene.findLayer(2)->tracks.empty(), "static text canary has no text animation");
        check(canary.material.kind == MaterialKind::Emissive && canary.material.emissiveColor.getHex() == 0xff1830,
              "YouTube canary declares the red emissive material");
        check(canary.textStyles.size() == 1, "YouTube canary declares one font intent for the complete TextContentId");
        canary.scene.evaluate(30);
        const auto cameraAt30 = canary.camera.sample(30.f / 30.f);
        canary.scene.evaluate(90);
        const auto cameraAt90 = canary.camera.sample(90.f / 30.f);
        check(cameraAt30.position.x != cameraAt90.position.x || cameraAt30.position.y != cameraAt90.position.y ||
                      cameraAt30.position.z != cameraAt90.position.z,
              "YouTube canary camera orbit moves during its authored window");

        Composition dollyOrbit = build(Final3DPreset::TextDollyOrbitGlow, finalData());
        std::size_t dollyOrbitTextLayers = 0;
        for (const Layer& layer : dollyOrbit.scene.layers()) {
            if (layer.content.isText()) ++dollyOrbitTextLayers;
        }
        check(dollyOrbitTextLayers == 2,
              "text dolly/orbit glow keeps title and subtitle as complete text layers");
        check(dollyOrbit.material.kind == MaterialKind::Emissive,
              "text dolly/orbit glow declares an emissive material");
        dollyOrbit.scene.evaluate(30);
        const auto dollyAt30 = dollyOrbit.camera.sample(30.f / 30.f);
        dollyOrbit.scene.evaluate(90);
        const auto dollyAt90 = dollyOrbit.camera.sample(90.f / 30.f);
        check(dollyAt30.position.x != dollyAt90.position.x || dollyAt30.position.y != dollyAt90.position.y ||
                      dollyAt30.position.z != dollyAt90.position.z,
              "text dolly/orbit glow camera moves through dolly/orbit window");

        Composition cleanRed = build(Final3DPreset::CleanRed, data);
        check(!cleanRed.scene.lights().empty(), "clean red preset declares a key light");
        Light& key = *cleanRed.scene.lights().front();
        check(key.kind() == LightKind::Directional, "clean red key light is directional");
        check(key.color[0] > key.color[1] && key.color[0] > key.color[2],
              "clean red key light is actually red");
        check(key.intensityTrack.endTime() > 0.f, "clean red key light is keyed over time");
        cleanRed.scene.evaluate(data.startFrame + 24);
        CompiledScene compiled = cleanRed.scene.compile();
        check(compiled.lights.size() >= 2, "clean red preset compiles its light states");
        check(compiled.lights.front().sample.color[0] > compiled.lights.front().sample.color[2],
              "compiled clean red key light keeps the red tint");
    }

    void finalValidation() {
        section("final 3D validation");
        Final3DData invalid = finalData();
        invalid.duration = 30;
        bool rejected = false;
        try {
            (void)build(Final3DPreset::LogoReveal, invalid);
        } catch (const std::invalid_argument&) {
            rejected = true;
        }
        check(rejected, "short final 3D timelines are rejected");
    }

    /// The pack/preset rule, made executable. The two catalogs answer different
    /// questions, and the duplication this module exists to remove comes back
    /// through exactly two doors, so both are checked here:
    ///
    ///   1. a pack is a RECIPE (it authors its own scene graph and timing), a
    ///      preset is a PARAMETER SET over the shared recipe. A preset that
    ///      re-authored the base scene would be a second recipe.
    ///   2. the published id namespaces stay disjoint, so one overlay cannot be
    ///      described once as a pack and again as a preset, with two timings
    ///      free to drift apart.
    void packRecipeRule() {
        section("pack vs preset rule");

        const Final3DData data = finalData();
        for (const Final3DPreset preset : final3DPresets()) {
            const Composition composition = build(preset, data);
            const Layer* root = composition.scene.findLayer(1);
            const Layer* title = composition.scene.findLayer(2);
            check(root != nullptr && root->isNull() && root->name == "SceneRoot",
                  "a preset keeps the shared recipe root instead of authoring its own scene");
            check(title != nullptr && title->content.isText() && title->parentId == 1,
                  "a preset builds on the shared title layer under that root");
            // The lights live in the scene's own light storage, not among the
            // layers, so the shared rig is asserted on the light ids.
            bool keyLight = false;
            bool fillLight = false;
            for (const auto& light : composition.scene.lights()) {
                if (light->id == 50) keyLight = true;
                if (light->id == 51) fillLight = true;
            }
            check(keyLight && fillLight, "a preset keeps the shared key and fill lights");
        }

        std::vector<std::string> presetNames;
        for (const Final3DPreset preset : final3DPresets()) presetNames.push_back(name(preset));
        int duplicates = 0;
        for (std::size_t i = 0; i < presetNames.size(); ++i) {
            for (std::size_t j = i + 1; j < presetNames.size(); ++j) {
                if (presetNames[i] == presetNames[j]) ++duplicates;
            }
        }
        check(duplicates == 0, "no two presets publish the same id");

        int collisions = 0;
        for (const auto pack : chrononmotion::templates::available()) {
            const std::string packName = chrononmotion::templates::name(pack);
            for (const std::string& presetName : presetNames) {
                if (packName == presetName) ++collisions;
            }
        }
        check(collisions == 0, "no id is published as both a pack and a preset");
    }

    void webCatalog() {
        section("web-style preset catalog");
        chrononmotion::templates::TemplateData data;
        data.primaryText = "Wrestling Discovery";
        data.secondaryText = "1.2M subscribers";
        data.imageId = "avatar.asset";
        data.iconId = "social.icon";
        data.duration = 90;

        for (const auto preset : chrononmotion::templates::available()) {
            MotionScene scene = chronontemplate::build(preset, data);
            check(scene.validate().empty(), "web-style preset has a valid hierarchy");
            scene.evaluate(30);
            check(scene.compile().transforms.size() == scene.layerCount(),
                  "web-style preset compiles all generated transforms");
        }
    }

}// namespace

int main() {
    finalCatalog();
    stylePresets();
    finalValidation();
    packRecipeRule();
    webCatalog();
    return chrononmotion_test::report();
}
