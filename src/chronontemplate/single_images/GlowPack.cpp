#include "chronontemplate/single_images/GlowPack.hpp"

#include "chronontemplate/single_images/ImageAnimationPack.hpp"

#include "chrononmotion/motion/Presets.hpp"

#include <stdexcept>

namespace chronontemplate {

    namespace {
        using chrononmotion::Vector2;
        using chrononmotion::motion::Easing;
        using chrononmotion::motion::Layer;

        float at(int frame, float fps) { return static_cast<float>(frame) / fps; }

        const char* glowColor(ImageGlow animation) {
            switch (animation) {
                case ImageGlow::WarmGlow: return "#FF8A3D";
                case ImageGlow::CoolGlow: return "#38BDF8";
                case ImageGlow::GoldGlow: return "#E8B84A";
                case ImageGlow::RoseGlow: return "#F472B6";
                case ImageGlow::PulseGlow: return "#A78BFA";
                default: return "#FF8A3D";
            }
        }
    }

    LayerHandle& addImageGlow(TemplateScene& scene, ImageGlow animation,
                              const std::string& assetPath, const std::string& name,
                              ImageFrameStyle frame, ImageCameraMove cameraMove) {
        switch (animation) {
            case ImageGlow::WarmGlow:
            case ImageGlow::CoolGlow:
            case ImageGlow::GoldGlow:
            case ImageGlow::RoseGlow:
            case ImageGlow::PulseGlow:
                break;
            default:
                throw std::invalid_argument("addImageGlow: unknown animation");
        }

        // Halo plate first so it draws underneath the hero card. Slightly
        // larger than the 480px preset card; the renderer blurs it into a
        // soft halo while the C++ keeps the choreography subtle.
        LayerHandle& plate = scene.shape(ShapeSpec{
                .size = Vector2(560.f, 560.f), .fillColor = glowColor(animation),
                .name = name + "_glow", .cornerRadius = 90.f});
        plate.alive(0, 150);
        plate.animateOpacity(0, 30, 0.f, 0.5f);

        LayerHandle& image = scene.image(ImageSpec{
                .path = assetPath, .name = name, .frame = std::move(frame)});
        plate.parent(image.id());
        plate.position(0.f, 0.f);

        const float fps = scene.fps();
        if (animation == ImageGlow::PulseGlow) {
            // Gentle halo breathing after the entrance settles.
            Layer& plateLayer = *scene.motion().findLayer(plate.id());
            plateLayer.tracks.opacity.add(at(48, fps), 0.5f, Easing::easeInOut());
            plateLayer.tracks.opacity.add(at(84, fps), 0.28f, Easing::easeInOut());
            plateLayer.tracks.opacity.add(at(120, fps), 0.5f, Easing::easeInOut());
            image.animate(ScalePop{.inFrame = 0, .duration = 88, .from = 0.90f, .to = 1.04f})
                 .animate(FadeIn{.inFrame = 0, .duration = 20});
            chrononmotion::motion::presets::floatHover(
                    *scene.motion().findLayer(image.id()), 40, 90, 26.f, fps);
        } else if (animation == ImageGlow::GoldGlow) {
            image.animate(ScalePop{.inFrame = 0, .duration = 96, .from = 0.94f, .to = 1.02f})
                 .animate(FadeIn{.inFrame = 0, .duration = 24});
            chrononmotion::motion::presets::floatHover(
                    *scene.motion().findLayer(image.id()), 32, 100, 18.f, fps);
        } else {
            image.animate(ScalePop{.inFrame = 0, .duration = 88, .from = 0.92f, .to = 1.0f})
                 .animate(FadeIn{.inFrame = 0, .duration = 20});
        }
        plate.animateOpacity(132, 18, 0.5f, 0.f);

        switch (cameraMove) {
            case ImageCameraMove::None:
                break;
            case ImageCameraMove::Dolly:
                scene.camera().push(3.f).between(8, 126);
                break;
            case ImageCameraMove::Orbit:
                scene.camera().orbit(0.22f, 0.045f).between(8, 126);
                break;
            case ImageCameraMove::DollyOrbit:
                scene.camera().push(3.f).between(8, 66);
                scene.camera().orbit(0.22f, 0.045f).between(66, 126);
                break;
            default:
                throw std::invalid_argument("addImageGlow: unknown camera move");
        }
        image.animate(FadeOut{.startFrame = 132, .duration = 18});
        return image;
    }

}// namespace chronontemplate
