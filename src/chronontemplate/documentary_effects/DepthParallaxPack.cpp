#include "chronontemplate/documentary_effects/DepthParallaxPack.hpp"

#include <cmath>
#include <stdexcept>

namespace chronontemplate::docfx {

    namespace {

        void requireFinite(float value, const char* what) {
            if (!std::isfinite(value))
                throw std::invalid_argument(std::string("parallax: ") + what + " must be finite");
        }

        void validate(const DepthParallaxSpec& spec) {
            requireFinite(spec.cardWidth, "cardWidth");
            requireFinite(spec.cardHeight, "cardHeight");
            requireFinite(spec.cardCenterX, "cardCenterX");
            requireFinite(spec.cardCenterY, "cardCenterY");
            requireFinite(spec.fgOriginX, "fgOriginX");
            requireFinite(spec.fgOriginY, "fgOriginY");
            requireFinite(spec.fgSizeW, "fgSizeW");
            requireFinite(spec.fgSizeH, "fgSizeH");
            requireFinite(spec.bgDriftX, "bgDriftX");
            requireFinite(spec.bgDriftY, "bgDriftY");
            requireFinite(spec.fgDriftX, "fgDriftX");
            requireFinite(spec.fgDriftY, "fgDriftY");
            requireFinite(spec.cameraPush, "cameraPush");
            if (spec.photoAsset.empty())
                throw std::invalid_argument("parallax: photo asset is required");
            if (spec.cardWidth <= 0.f || spec.cardWidth > 1920.f ||
                spec.cardHeight <= 0.f || spec.cardHeight > 1080.f ||
                spec.fgOriginX < 0.f || spec.fgOriginY < 0.f ||
                spec.fgSizeW <= 0.f || spec.fgSizeH <= 0.f ||
                spec.fgOriginX + spec.fgSizeW > 1.f ||
                spec.fgOriginY + spec.fgSizeH > 1.f ||
                std::abs(spec.bgDriftX) > 400.f || std::abs(spec.bgDriftY) > 400.f ||
                std::abs(spec.fgDriftX) > 600.f || std::abs(spec.fgDriftY) > 600.f ||
                spec.cameraPush < 0.f || spec.cameraPush > 1200.f ||
                spec.inFrame < 0 || spec.sceneFrames < 1 || spec.sceneFrames > 900)
                throw std::invalid_argument("parallax: spec is outside supported ranges");
        }

    } // namespace

    float parallaxProgress(const DepthParallaxSpec& spec, int frame) {
        if (frame <= spec.inFrame) return 0.f;
        if (frame >= spec.inFrame + spec.sceneFrames) return 1.f;
        float p = static_cast<float>(frame - spec.inFrame) /
            static_cast<float>(spec.sceneFrames);
        return p * p * (3.f - 2.f * p);
    }

    DepthParallaxLayers addDepthParallax(TemplateScene& scene,
                                         const DepthParallaxSpec& spec) {
        validate(spec);
        const int endFrame = spec.inFrame + spec.sceneFrames;
        DepthParallaxLayers out{};
        const chrononmotion::Vector2 card(spec.cardWidth, spec.cardHeight);

        LayerHandle& bg = scene.image(ImageSpec{
                .path = spec.photoAsset, .name = "parallax_bg",
                .fit = ImageFitMode::Cover, .targetSize = card});
        bg.position(spec.cardCenterX, spec.cardCenterY);
        bg.alive(spec.inFrame, endFrame);
        bg.animate(FadeIn{.inFrame = spec.inFrame, .duration = 16});
        bg.animatePosition(spec.inFrame, spec.sceneFrames,
                           chrononmotion::Vector3(spec.bgDriftX, spec.bgDriftY, 0.f),
                           chrononmotion::motion::Easing::easeInOut());
        bg.animate(FadeOut{.startFrame = endFrame - 16, .duration = 16});
        out.background = bg.id();

        ImageCrop fgCrop;
        fgCrop.enabled = true;
        fgCrop.origin = chrononmotion::Vector2(spec.fgOriginX, spec.fgOriginY);
        fgCrop.size = chrononmotion::Vector2(spec.fgSizeW, spec.fgSizeH);
        LayerHandle& fg = scene.image(ImageSpec{
                .path = spec.photoAsset, .name = "parallax_fg",
                .fit = ImageFitMode::Cover, .targetSize = card, .crop = fgCrop});
        fg.position(spec.cardCenterX, spec.cardCenterY);
        fg.alive(spec.inFrame, endFrame);
        fg.animate(FadeIn{.inFrame = spec.inFrame + 8, .duration = 16});
        fg.animatePosition(spec.inFrame, spec.sceneFrames,
                           chrononmotion::Vector3(spec.fgDriftX, spec.fgDriftY, 0.f),
                           chrononmotion::motion::Easing::easeInOut());
        fg.animate(FadeOut{.startFrame = endFrame - 16, .duration = 16});
        out.foreground = fg.id();

        if (spec.cameraPush > 0.f)
            scene.camera().push(spec.cameraPush).between(spec.inFrame, endFrame);
        return out;
    }

    const char* depthParallaxId() noexcept {
        return "docfx_depth_parallax_v1";
    }

} // namespace chronontemplate::docfx
