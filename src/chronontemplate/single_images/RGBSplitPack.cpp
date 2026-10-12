#include "chronontemplate/single_images/RGBSplitPack.hpp"

#include "chronontemplate/single_images/ImageAnimationPack.hpp"

#include "chrononmotion/motion/Presets.hpp"

#include <stdexcept>

namespace chronontemplate {

    namespace {
        using chrononmotion::Vector2;
        using chrononmotion::Vector3;
        using chrononmotion::motion::Easing;
        using chrononmotion::motion::Layer;

        constexpr const char* kRedChannel = "#FF3B30";
        constexpr const char* kCyanChannel = "#22D3EE";

        float at(int frame, float fps) { return static_cast<float>(frame) / fps; }

        LayerHandle& ghostBar(TemplateScene& scene, unsigned parentId,
                              const std::string& name, const char* color,
                              float relX) {
            LayerHandle& bar = scene.shape(ShapeSpec{
                    .size = Vector2(14.f, 440.f), .fillColor = color,
                    .name = name, .cornerRadius = 7.f});
            bar.parent(parentId);
            bar.position(relX, 0.f);
            bar.alive(0, 150);
            bar.animateOpacity(0, 24, 0.f, 0.85f);
            bar.animateOpacity(132, 18, 0.85f, 0.f);
            return bar;
        }
    }

    LayerHandle& addImageRGBSplit(TemplateScene& scene, ImageRGBSplit animation,
                                  const std::string& assetPath, const std::string& name,
                                  ImageFrameStyle frame, ImageCameraMove cameraMove) {
        switch (animation) {
            case ImageRGBSplit::SplitStatic:
            case ImageRGBSplit::SplitConverge:
            case ImageRGBSplit::SplitPulse:
            case ImageRGBSplit::SplitGlitch:
            case ImageRGBSplit::SplitExit:
                break;
            default:
                throw std::invalid_argument("addImageRGBSplit: unknown animation");
        }

        LayerHandle& image = scene.image(ImageSpec{
                .path = assetPath, .name = name, .frame = std::move(frame)});
        image.animate(ScalePop{.inFrame = 0, .duration = 88, .from = 0.92f, .to = 1.0f})
             .animate(FadeIn{.inFrame = 0, .duration = 20});

        const float fps = scene.fps();
        LayerHandle& red = ghostBar(scene, image.id(), name + "_rgb_red", kRedChannel, -258.f);
        LayerHandle& cyan = ghostBar(scene, image.id(), name + "_rgb_cyan", kCyanChannel, 258.f);
        Layer& redLayer = *scene.motion().findLayer(red.id());
        Layer& cyanLayer = *scene.motion().findLayer(cyan.id());

        switch (animation) {
            case ImageRGBSplit::SplitStatic:
                red.animatePosition(0, 36, Vector3(-70.f, 0.f, 0.f));
                cyan.animatePosition(0, 36, Vector3(70.f, 0.f, 0.f));
                break;
            case ImageRGBSplit::SplitConverge:
                // Wide offsets slam into the card edges during the entrance.
                redLayer.tracks.position.add(at(0, fps), Vector3(-398.f, 0.f, 0.f), Easing::easeOut());
                redLayer.tracks.position.add(at(48, fps), Vector3(-258.f, 0.f, 0.f), Easing::easeOut());
                cyanLayer.tracks.position.add(at(0, fps), Vector3(398.f, 0.f, 0.f), Easing::easeOut());
                cyanLayer.tracks.position.add(at(48, fps), Vector3(258.f, 0.f, 0.f), Easing::easeOut());
                break;
            case ImageRGBSplit::SplitPulse:
                // Channels breathe in and out twice after settling.
                redLayer.tracks.opacity.add(at(48, fps), 0.85f, Easing::easeInOut());
                redLayer.tracks.opacity.add(at(72, fps), 0.30f, Easing::easeInOut());
                redLayer.tracks.opacity.add(at(96, fps), 0.85f, Easing::easeInOut());
                cyanLayer.tracks.opacity.add(at(48, fps), 0.85f, Easing::easeInOut());
                cyanLayer.tracks.opacity.add(at(72, fps), 0.30f, Easing::easeInOut());
                cyanLayer.tracks.opacity.add(at(96, fps), 0.85f, Easing::easeInOut());
                red.animatePosition(0, 36, Vector3(-70.f, 0.f, 0.f));
                cyan.animatePosition(0, 36, Vector3(70.f, 0.f, 0.f));
                break;
            case ImageRGBSplit::SplitGlitch: {
                // Primitive jitter: channels stutter around their edges.
                red.animatePosition(0, 24, Vector3(-70.f, 0.f, 0.f));
                cyan.animatePosition(0, 24, Vector3(70.f, 0.f, 0.f));
                for (int f = 30; f <= 78; f += 6) {
                    const float jitter = (f / 6) % 2 == 0 ? 10.f : -10.f;
                    redLayer.tracks.position.add(at(f, fps), Vector3(-258.f + jitter, 0.f, 0.f),
                                                 Easing::linear());
                    cyanLayer.tracks.position.add(at(f, fps), Vector3(258.f - jitter, 0.f, 0.f),
                                                  Easing::linear());
                }
                redLayer.tracks.position.add(at(90, fps), Vector3(-258.f, 0.f, 0.f), Easing::easeOut());
                cyanLayer.tracks.position.add(at(90, fps), Vector3(258.f, 0.f, 0.f), Easing::easeOut());
                break;
            }
            case ImageRGBSplit::SplitExit:
                red.animatePosition(0, 36, Vector3(-70.f, 0.f, 0.f));
                cyan.animatePosition(0, 36, Vector3(70.f, 0.f, 0.f));
                // Channels tear outward while the card fades out.
                redLayer.tracks.position.add(at(110, fps), Vector3(-258.f, 0.f, 0.f),
                                             Easing::easeInOut());
                redLayer.tracks.position.add(at(132, fps), Vector3(-420.f, 0.f, 0.f),
                                             Easing::easeInOut());
                cyanLayer.tracks.position.add(at(110, fps), Vector3(258.f, 0.f, 0.f),
                                              Easing::easeInOut());
                cyanLayer.tracks.position.add(at(132, fps), Vector3(420.f, 0.f, 0.f),
                                              Easing::easeInOut());
                break;
        }

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
                throw std::invalid_argument("addImageRGBSplit: unknown camera move");
        }
        image.animate(FadeOut{.startFrame = 132, .duration = 18});
        return image;
    }

}// namespace chronontemplate
