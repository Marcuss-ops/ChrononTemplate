#include "chronontemplate/core/Presets.hpp"

#include "chrononmotion/motion/Presets.hpp"
#include "chrononmotion/math/MathUtils.hpp"

#include <algorithm>
#include <cmath>
#include <limits>
#include <stdexcept>
#include <utility>

namespace chronontemplate {

    namespace {

        using namespace chrononmotion;
        using namespace chrononmotion::motion;

        constexpr Layer::Id kRoot = 1;
        constexpr Layer::Id kPrimary = 2;
        constexpr Layer::Id kSecondary = 3;
        constexpr Layer::Id kKeyLight = 50;
        constexpr Layer::Id kFillLight = 51;

        FrameRange lifetime(const Final3DData& data) {
            return FrameRange::between(data.startFrame, data.startFrame + data.duration);
        }

        int endFrame(const Final3DData& data) {
            return data.startFrame + data.duration;
        }

        /// The authored px size of the 900-unit reference title box. The glyph
        /// layers and the title box keep the proportion the recipes were built
        /// against, so one declared size travels through the same scale.
        constexpr float kTitleBoxWidth = 700.f;
        constexpr float kTitleFontSize = 130.f;
        constexpr float kSubtitleFontSize = 72.f;

        void declareTextStyle(Composition& composition, Layer::Id layer,
                              const std::string& font, float font_size) {
            if (font.empty() || !(font_size > 0.f)) {
                throw std::invalid_argument("declareTextStyle: font and a positive size are required");
            }
            composition.textStyles[layer] = TextStyleDeclaration{font, font_size};
        }

        Composition baseComposition(const Final3DData& data, const char* name,
                                     MaterialDescriptor material) {
            MotionScene scene(name, data.fps);
            Layer& root = scene.addNull(kRoot, "SceneRoot");
            root.alive(lifetime(data));

            Layer& primary = scene.addContent(
                    kPrimary, "Primary", ContentRef::text(data.title, Vector2(kTitleBoxWidth, 180.f)), kRoot);
            primary.positionedAt(Vector3(0.f, 0.f, 0.f)).alive(lifetime(data));

            DirectionalLight& key = scene.addDirectionalLight(kKeyLight, "Key", kRoot);
            key.color.setRGB(1.f, 0.9f, 0.8f, ColorSpace::Linear);
            key.intensity = 2.f;
            key.targetId = kPrimary;
            key.transform.position.set(4.f, 5.f, 8.f);

            AmbientLight& fill = scene.addAmbientLight(kFillLight, "Fill");
            fill.color.setRGB(0.2f, 0.3f, 0.5f, ColorSpace::Linear);
            fill.intensity = 0.35f;

            CameraRig camera(100, 55.f, 16.f / 9.f, 0.1f, 2000.f);
            camera.setPosition(Vector3(0.f, 0.f, 14.f)).setTarget(Vector3(0.f, 0.f, 0.f));

            Composition composition{std::move(scene), std::move(camera), std::move(material), {}};
            // The title is real text: the content side renders it with the face
            // the recipe names, not with whatever default it happens to have.
            declareTextStyle(composition, kPrimary, data.titleFont, kTitleFontSize);
            return composition;
        }

        Composition typewriter3DGlow(const Final3DData& data) {
            Composition result = baseComposition(
                    data, "final_typewriter_3d_glow",
                    MaterialDescriptor::emissive(7, Color(0xffffff), 5.f));
            // One content layer carries the complete authored run. Chronon3D
            // owns shaping, cluster positions and glyph animation; this recipe
            // only selects the typewriter behavior and never splits the string.
            Layer& title = *result.scene.findLayer(kPrimary);
            presets::fadeIn(title, data.startFrame, 18, data.fps);
            presets::scalePop(title, data.startFrame + 4, 20, 0.94f, 1.f, data.fps);
            presets::fadeOut(title, endFrame(data) - 18, 18, data.fps);
            presets::cameraPush(result.camera, data.startFrame + 20, 70, 2.5f, data.fps);
            return result;
        }

        Composition youtubeCanary(const Final3DData& data) {
            Composition result = baseComposition(
                    data, "final3d_youtube_canary",
                    MaterialDescriptor::emissive(9, Color(0xff1830), 5.f));
            // The canary keeps one complete TextContentId. Chronon3D may expose
            // cluster/element animation internally, but Template never creates
            // character layers or invents advances.
            Layer& title = *result.scene.findLayer(kPrimary);
            presets::fadeIn(title, data.startFrame, 18, data.fps);
            presets::scalePop(title, data.startFrame + 18, 20, 0.94f, 1.f, data.fps);
            presets::spinXYZ(title, data.startFrame + 22, 60, 0.035f, data.fps);
            presets::fadeOut(title, endFrame(data) - 18, 18, data.fps);
            presets::cameraOrbit(result.camera, data.startFrame + 30, 60,
                                 math::PI * 0.067f, math::PI * 0.016f, data.fps);
            return result;
        }

        Composition textDollyOrbitGlow(const Final3DData& data) {
            Composition result = baseComposition(
                    data, "final_text_dolly_orbit_glow",
                    MaterialDescriptor::emissive(11, Color(0xffffff), 4.5f));
            Layer& title = *result.scene.findLayer(kPrimary);
            title.positionedAt(Vector3(0.f, 0.35f, -0.35f));

            Layer& subtitle = result.scene.addContent(
                    kSecondary, "Subtitle", ContentRef::text(data.subtitle, Vector2(700.f, 72.f)), kRoot);
            subtitle.positionedAt(Vector3(0.f, -1.15f, 0.35f)).alive(lifetime(data));
            declareTextStyle(result, kSecondary, data.subtitleFont, kSubtitleFontSize);

            // A restrained 2.5D title card: the two complete text runs sit on
            // separate depth planes, while the camera supplies the dolly and
            // orbit. Chronon3D owns shaping, pixels and the glow.
            presets::fadeIn(title, data.startFrame, 16, data.fps);
            presets::scalePop(title, data.startFrame + 6, 24, 0.86f, 1.f, data.fps);
            presets::fadeIn(subtitle, data.startFrame + 18, 18, data.fps);
            presets::fadeOut(title, endFrame(data) - 20, 20, data.fps);
            presets::fadeOut(subtitle, endFrame(data) - 20, 20, data.fps);
            presets::cameraPush(result.camera, data.startFrame + 12, 72, 3.2f, data.fps);
            presets::cameraOrbit(result.camera, data.startFrame + 18, 72,
                                 math::PI * 0.075f, math::PI * 0.018f, data.fps);
            return result;
        }

        Composition textStatic(const Final3DData& data) {
            Composition result = baseComposition(
                    data, "chronon_text_static",
                    MaterialDescriptor::lambert(10, Color(0xffffff)));
            Layer& title = *result.scene.findLayer(kPrimary);
            title.positionedAt(Vector3(0.f, 0.f, 0.f));
            result.camera.setPosition(Vector3(0.f, 0.f, 10.f))
                    .setTarget(Vector3(0.f, 0.f, 0.f));
            return result;
        }

        Composition cleanRed(const Final3DData& data) {
            Composition result = baseComposition(
                    data, "final_clean_red",
                    MaterialDescriptor::emissive(8, Color(0xff1730), 2.5f));
            Layer& title = *result.scene.findLayer(kPrimary);
            title.positionedAt(Vector3(0.f, 0.5f, 0.f));
            presets::slideIn(title, presets::Direction::Left, data.startFrame, 20, 6.f, data.fps);
            presets::fadeIn(title, data.startFrame, 20, data.fps);
            presets::scalePop(title, data.startFrame + 18, 18, 0.92f, 1.f, data.fps);
            DirectionalLight& key = static_cast<DirectionalLight&>(*result.scene.lights().front());
            key.color.setRGB(1.f, 0.05f, 0.02f, ColorSpace::Linear);
            key.intensity = 3.f;
            key.intensityTrack.add(frameToTime(data.startFrame, data.fps), 0.2f, Easing::easeOut());
            key.intensityTrack.add(frameToTime(data.startFrame + 24, data.fps), 3.5f, Easing::easeInOut());
            presets::cameraPush(result.camera, data.startFrame + 16, 80, 4.f, data.fps);
            presets::fadeOut(title, endFrame(data) - 18, 18, data.fps);
            return result;
        }

    }// namespace

    void Final3DData::validate() const {
        if (!std::isfinite(fps) || fps <= 0.f) {
            throw std::invalid_argument("Final3DData: fps must be positive and finite");
        }
        constexpr int minimumDuration = 60;
        if (startFrame < 0 || duration < minimumDuration ||
            startFrame > std::numeric_limits<int>::max() - duration) {
            throw std::invalid_argument("Final3DData: duration must be at least 60 frames");
        }
        if (title.empty() || subtitle.empty() || assetId.empty()) {
            throw std::invalid_argument("Final3DData: title, subtitle and assetId are required");
        }
        if (titleFont.empty() || subtitleFont.empty()) {
            throw std::invalid_argument("Final3DData: titleFont and subtitleFont are required");
        }
    }

    NativePhraseStyle nativePhraseStyle() {
        // This is the single canvas projection contract for the modern phrase
        // pack.  Consumers may lower motion, but they must not restate these
        // appearance/layout values in a second authority.
        return NativePhraseStyle{};
    }

    const char* name(Final3DPreset preset) {
        switch (preset) {
            case Final3DPreset::Typewriter3DGlow: return "typewriter_3d_glow";
            case Final3DPreset::CleanRed: return "clean_red";
            case Final3DPreset::YouTubeCanary: return "youtube_canary";
            case Final3DPreset::TextStatic: return "text_static";
            case Final3DPreset::TextDollyOrbitGlow: return "text_dolly_orbit_glow";
        }
        throw std::invalid_argument("chronontemplate::name: unknown final 3D preset");
    }

    std::vector<Final3DPreset> final3DPresets() {
        return {Final3DPreset::Typewriter3DGlow, Final3DPreset::CleanRed,
                Final3DPreset::YouTubeCanary, Final3DPreset::TextStatic,
                Final3DPreset::TextDollyOrbitGlow};
    }

    namespace {

        /// The catalog's shared post-build contract: every text layer names
        /// its real face. A recipe that adds text content without a declaration
        /// would render with the consumer's default font and silently break the
        /// pack's look, so the gate covers every text layer rather than the ones
        /// that happen to start opaque:
        /// a layer whose opacity is animated up from zero still draws.
        void verifyCatalogContract(const Composition& composition) {
            for (const Layer& layer : composition.scene.layers()) {
                if (!layer.content.isText()) continue;
                if (composition.textStyles.find(layer.id) == composition.textStyles.end()) {
                    throw std::logic_error("chronontemplate::build: text layer '" + layer.name +
                                           "' has no TextStyleDeclaration");
                }
            }
        }

    }// namespace

    Composition build(Final3DPreset preset, const Final3DData& data) {

        data.validate();
        switch (preset) {
            case Final3DPreset::Typewriter3DGlow: {
                Composition composition = typewriter3DGlow(data);
                verifyCatalogContract(composition);
                return composition;
            }
            case Final3DPreset::CleanRed: {
                Composition composition = cleanRed(data);
                verifyCatalogContract(composition);
                return composition;
            }
            case Final3DPreset::YouTubeCanary: {
                Composition composition = youtubeCanary(data);
                verifyCatalogContract(composition);
                return composition;
            }
            case Final3DPreset::TextStatic: {
                Composition composition = textStatic(data);
                verifyCatalogContract(composition);
                return composition;
            }
            case Final3DPreset::TextDollyOrbitGlow: {
                Composition composition = textDollyOrbitGlow(data);
                verifyCatalogContract(composition);
                return composition;
            }
        }
        throw std::invalid_argument("chronontemplate::build: unknown final 3D preset");
    }

    chrononmotion::motion::MotionScene build(
            chrononmotion::templates::TemplateId preset,
            const chrononmotion::templates::TemplateData& data) {
        return chrononmotion::templates::build(preset, data);
    }

}// namespace chronontemplate
