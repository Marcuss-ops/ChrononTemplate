#include "chronontemplate/gel/GelCinematicTitlePack.hpp"

#include <chronon3d/render_plan/color_utils.hpp>

#include <cmath>
#include <stdexcept>
#include <string>

namespace chronontemplate::gel {

    namespace {

        void requireFinite(float value, const char* what) {
            if (!std::isfinite(value))
                throw std::invalid_argument(std::string("GelCinematicTitle: ") + what + " must be finite");
        }

        void requireHex(const std::string& color, const char* what) {
            if (!chronon3d::render_plan::parse_hex_color(color))
                throw std::invalid_argument(std::string("GelCinematicTitle: ") + what + " must be #RRGGBB");
        }

        void applyPush(TemplateScene& scene, LayerHandle& layer, float baseScale,
                       int inFrame, int durationFrames, float pushScale) {
            if (pushScale == 1.f) return;
            const float fps = scene.fps();
            const float t0 = static_cast<float>(inFrame) / fps;
            const float t1 = static_cast<float>(inFrame + durationFrames) / fps;
            using chrononmotion::motion::Easing;
            layer.layer().tracks.scale.add(
                t0, chrononmotion::Vector3(baseScale, baseScale, 1.f), Easing::linear());
            layer.layer().tracks.scale.add(
                t1, chrononmotion::Vector3(baseScale * pushScale, baseScale * pushScale, 1.f),
                Easing::linear());
        }

    }// namespace

    GelCinematicTitleLayers addGelCinematicTitle(
            TemplateScene& scene, const GelCinematicTitleSpec& spec) {
        if (spec.words.empty())
            throw std::invalid_argument("GelCinematicTitle: at least one word is required");
        if (spec.font.empty())
            throw std::invalid_argument("GelCinematicTitle: a font is required");
        requireFinite(spec.fontSize, "fontSize");
        if (spec.fontSize <= 0.f || spec.fontSize > 512.f)
            throw std::invalid_argument("GelCinematicTitle: fontSize must be in (0, 512]");
        requireFinite(spec.extrusionDepth, "extrusionDepth");
        if (spec.extrusionDepth < 0.f || spec.extrusionDepth > 256.f)
            throw std::invalid_argument("GelCinematicTitle: extrusionDepth must be in [0, 256]");
        requireFinite(spec.backingScale, "backingScale");
        if (spec.backingScale <= 0.f || spec.backingScale > 2.f)
            throw std::invalid_argument("GelCinematicTitle: backingScale must be in (0, 2]");
        requireFinite(spec.backingOffset.x, "backingOffset.x");
        requireFinite(spec.backingOffset.y, "backingOffset.y");
        requireFinite(spec.pushScale, "pushScale");
        if (spec.pushScale < 1.f || spec.pushScale > 1.5f)
            throw std::invalid_argument("GelCinematicTitle: pushScale must be in [1, 1.5]");
        if (spec.inFrame < 0 || spec.durationFrames < 1 || spec.durationFrames > 3000)
            throw std::invalid_argument("GelCinematicTitle: the frame window is outside supported ranges");
        requireHex(spec.faceColor, "faceColor");
        requireHex(spec.backingColor, "backingColor");
        requireHex(spec.dropShadow.color, "dropShadow.color");
        requireHex(spec.glow.color, "glow.color");
        if (!std::isfinite(spec.dropShadow.opacity) || spec.dropShadow.opacity < 0.f ||
            spec.dropShadow.opacity > 1.f)
            throw std::invalid_argument("GelCinematicTitle: dropShadow.opacity must be in [0, 1]");

        const auto canvas = scene.canvas();
        const int endFrame = spec.inFrame + spec.durationFrames;
        const float backingX = spec.backingOffset.x;
        const float backingY = spec.backingOffset.y;
        // RenderPlan text/shape positions are absolute canvas centres, while
        // the Template/Motion authoring space is canvas-centred. Convert once
        // here so callers keep writing the reference pixel coordinates.
        const float originX = canvas.x * 0.5f;
        const float originY = canvas.y * 0.5f;

        // The extruded backing is real 3D geometry, so it needs the camera.
        // Put the optical axis on the canvas centre and choose the focal
        // length that maps one world unit to one output pixel at z=0. The
        // flat GEL face and the plate remain canvas-space layers and therefore
        // stay pixel-aligned with this projection.
        constexpr float kCameraDistance = 1080.f;
        constexpr float kCanvasHeight = 1080.f;
        constexpr float kPixelFov = 53.130102f;
        static_assert(kCanvasHeight == 1080.f);
        scene.camera().setFov(kPixelFov);
        // 3D primitives and their resolved samples are centred on the canvas;
        // the camera therefore sits on the projection origin, not at the
        // canvas-centre pixel coordinate. The +5px Y offset matches the
        // backing's authored down-offset in the Y-up 3D projection.
        scene.cameraRig().positionTrack().add(
            0.f, chrononmotion::Vector3(0.f, 5.f, kCameraDistance));
        scene.cameraRig().setTarget(chrononmotion::Vector3(0.f, 5.f, 0.f));

        GelCinematicTitleLayers out{};
        out.backings.reserve(spec.words.size());
        out.faces.reserve(spec.words.size());

        if (!spec.plate.empty()) {
            if (spec.plateSize.x < 0.f || spec.plateSize.y < 0.f)
                throw std::invalid_argument("GelCinematicTitle: plateSize must be non-negative");

            const chrononmotion::Vector2 fullSize =
                (spec.plateSize.x > 0.f && spec.plateSize.y > 0.f) ? spec.plateSize : canvas;
            // One full-frame plate, never a sharp strip over a blurred copy.
            // The asset owns its depth-of-field extension so the composer has
            // no internal edge to seam at y=415/666.
            ImageSpec plate;
            plate.path = spec.plate;
            plate.name = spec.name + "_plate";
            plate.fit = spec.plateFit;
            plate.targetSize = fullSize;
            plate.screenSpace = true;
            LayerHandle& layer = scene.image(plate);
            layer.layer().flat();
            layer.position(0.f, 0.f).alive(spec.inFrame, endFrame);
            out.plate = layer.id();
        }

        // The extruded backing is real geometry; the native generate.fill pass
        // keeps its side normals royal blue instead of dark navy.
        for (std::size_t i = 0; i < spec.words.size(); ++i) {
            const GelCinematicWord& word = spec.words[i];
            if (word.text.empty())
                throw std::invalid_argument("GelCinematicTitle: word text is required");
            requireFinite(word.x, "word.x");
            requireFinite(word.y, "word.y");
            requireFinite(word.scale, "word.scale");
            if (word.scale <= 0.f || word.scale > 8.f)
                throw std::invalid_argument("GelCinematicTitle: word.scale must be in (0, 8]");

            TextSpec backing;
            backing.text = word.text;
            backing.font = spec.font;
            backing.fontSize = spec.fontSize;
            backing.color = spec.backingColor;
            backing.name = spec.name + "_backing_" + std::to_string(i);
            backing.screenSpace = false;
            backing.material = TextMaterialStyle{
                .gelSurface = false,
                .gelTransmission = true,
                .gelSoftFusion = false,
                .extrusionDepth = spec.extrusionDepth};
            backing.catalogEffects.push_back(TextCatalogEffectStyle{
                .effectId = "generate.fill",
                .params = {{"amount", 0.78f},
                           {"color.r", 0.08f},
                           {"color.g", 0.52f},
                           {"color.b", 1.00f}}});

            LayerHandle& backingLayer = scene.text(backing);
            const float backingWordScale = word.scale * spec.backingScale;
            backingLayer.position(word.x + backingX - originX, word.y + backingY - originY)
                .layer()
                .scaled(chrononmotion::Vector3(backingWordScale, backingWordScale, 1.f));
            backingLayer.alive(spec.inFrame, endFrame);
            applyPush(scene, backingLayer, backingWordScale, spec.inFrame,
                      spec.durationFrames, spec.pushScale);
            out.backings.push_back(backingLayer.id());
        }

        for (std::size_t i = 0; i < spec.words.size(); ++i) {
            const GelCinematicWord& word = spec.words[i];
            TextSpec face;
            face.text = word.text;
            face.font = spec.font;
            face.fontSize = spec.fontSize;
            face.color = spec.faceColor;
            face.name = spec.name + "_face_" + std::to_string(i);
            face.screenSpace = false;
            face.material = TextMaterialStyle{
                .gelSurface = true,
                .gelTransmission = false,
                .gelSoftFusion = false,
                .extrusionDepth = 0.f};
            face.dropShadow = spec.dropShadow;
            face.chromaticAberration = spec.chromaticAberration;
            face.glow = spec.glow;
            face.bloom = spec.bloom;
            if (spec.enableLensFlare)
                face.lensFlare = spec.lensFlare;

            LayerHandle& faceLayer = scene.text(face);
            faceLayer.position(word.x - originX, word.y - originY)
                .layer()
                .scaled(chrononmotion::Vector3(word.scale, word.scale, 1.f));
            faceLayer.alive(spec.inFrame, endFrame);
            applyPush(scene, faceLayer, word.scale, spec.inFrame,
                      spec.durationFrames, spec.pushScale);
            out.faces.push_back(faceLayer.id());
        }

        return out;
    }

}// namespace chronontemplate::gel
