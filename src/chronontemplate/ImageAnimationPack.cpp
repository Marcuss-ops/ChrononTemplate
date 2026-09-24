#include "chronontemplate/ImageAnimationPack.hpp"

#include "chrononmotion/motion/Presets.hpp"
#include "chrononmotion/math/MathUtils.hpp"

#include <stdexcept>
#include <utility>

namespace chronontemplate {

    namespace {
        using chrononmotion::Vector3;
        using chrononmotion::motion::Easing;
        using chrononmotion::motion::Layer;

        bool isImage25d(ImageAnimation animation) {
            switch (animation) {
                case ImageAnimation::DepthFloatIn:
                case ImageAnimation::YawFlipIn:
                case ImageAnimation::PitchLift:
                case ImageAnimation::PopZBounce:
                case ImageAnimation::Swipe3D:
                case ImageAnimation::CardSwing:
                case ImageAnimation::DollySettle:
                case ImageAnimation::OrbitArc:
                case ImageAnimation::CounterTilt:
                case ImageAnimation::DollyBreath:
                case ImageAnimation::ParallaxDrift:
                case ImageAnimation::HeroPullExit:
                    return true;
                default:
                    return false;
            }
        }

        float at(int frame, float fps) { return static_cast<float>(frame) / fps; }

        void image25d(Layer& layer, float fps, ImageAnimation animation) {
            auto& p = layer.tracks.position;
            auto& s = layer.tracks.scale;
            auto& r = layer.tracks.rotation;
            auto& o = layer.tracks.opacity;
            const Easing smooth = Easing::easeInOut();
            const auto pos = [&](int f, float x, float y, float z, const Easing& e = Easing::easeOut()) {
                p.add(at(f, fps), Vector3(x, y, z), e);
            };
            const auto scale = [&](int f, float v, const Easing& e = Easing::easeOut()) {
                s.add(at(f, fps), Vector3(v, v, v), e);
            };
            const auto rotate = [&](int f, float x, float y, float z, const Easing& e = Easing::easeOut()) {
                r.add(at(f, fps), Vector3(chrononmotion::math::degToRad(x),
                                          chrononmotion::math::degToRad(y),
                                          chrononmotion::math::degToRad(z)), e);
            };
            const auto opacity = [&](int f, float v, const Easing& e = Easing::easeOut()) { o.add(at(f, fps), v, e); };

            switch (animation) {
                case ImageAnimation::DepthFloatIn:
                    pos(0, 0, 0, 400); pos(55, 0, 0, 0); pos(149, 0, 0, 0);
                    opacity(0, 0); opacity(24, 1); opacity(149, 1); scale(0, 1.06f); scale(55, 1); scale(149, 1); break;
                case ImageAnimation::YawFlipIn:
                    rotate(0, 0, -18, 0); rotate(48, 0, 0, 0); rotate(149, 0, 0, 0);
                    pos(0, 0, 0, 120); pos(48, 0, 0, 0); pos(149, 0, 0, 0);
                    opacity(0, 0); opacity(18, 1); opacity(149, 1); break;
                case ImageAnimation::PitchLift:
                    rotate(0, 12, 0, 0); rotate(48, 0, 0, 0); rotate(149, 0, 0, 0);
                    pos(0, 0, 60, 0); pos(48, 0, 0, 0); pos(149, 0, 0, 0);
                    scale(0, .92f); scale(48, 1); scale(149, 1); break;
                case ImageAnimation::PopZBounce:
                    pos(0, 0, 0, -80); pos(38, 0, 0, 0); pos(149, 0, 0, 0);
                    scale(0, .70f, smooth); scale(28, 1.04f, Easing::overshoot()); scale(48, 1); scale(149, 1);
                    opacity(0, 0); opacity(10, 1); opacity(149, 1); break;
                case ImageAnimation::Swipe3D:
                    pos(0, 320, 0, 0); pos(42, 0, 0, 0); pos(149, 0, 0, 0);
                    rotate(0, 0, 14, 0); rotate(42, 0, 0, 0); rotate(149, 0, 0, 0);
                    opacity(0, 0); opacity(12, 1); opacity(149, 1); break;
                case ImageAnimation::CardSwing:
                    rotate(0, 0, -10, -2, smooth); rotate(36, 0, 6, -1, smooth); rotate(72, 0, 0, 0, smooth); rotate(149, 0, 0, 0);
                    pos(0, 0, 0, 160); pos(52, 0, 0, 0); pos(149, 0, 0, 0); break;
                case ImageAnimation::DollySettle:
                    rotate(0, 0, -4, 0); rotate(55, 0, 0, 0); rotate(149, 0, 0, 0);
                    scale(0, .94f); scale(55, 1); scale(149, 1); opacity(0, 0); opacity(20, 1); opacity(149, 1); break;
                case ImageAnimation::OrbitArc:
                    pos(0, 0, 0, 150); pos(149, 0, 0, 150); opacity(0, 0); opacity(20, 1); opacity(149, 1); break;
                case ImageAnimation::CounterTilt:
                    rotate(0, -8, 0, 0); rotate(50, 0, 0, 0); rotate(149, 0, 0, 0);
                    opacity(0, 0); opacity(18, 1); opacity(149, 1); break;
                case ImageAnimation::DollyBreath:
                    scale(0, 1, smooth); scale(55, 1.03f, smooth); scale(100, 1.03f, smooth); scale(149, 1, smooth);
                    opacity(0, 0); opacity(20, 1); opacity(149, 1); break;
                case ImageAnimation::ParallaxDrift:
                    pos(0, 0, 0, 220); pos(30, 0, 0, 0); pos(112, 0, 0, 0); pos(149, 0, 0, 70);
                    scale(0, .94f); scale(30, 1); scale(112, 1); scale(149, .96f);
                    opacity(0, 0); opacity(20, 1); opacity(124, 1); opacity(149, 0); break;
                case ImageAnimation::HeroPullExit:
                    pos(0, 0, 0, -80); pos(35, 0, 0, 0); pos(105, 0, 0, 0); pos(149, 0, 0, 90);
                    scale(0, .72f, smooth); scale(35, 1, Easing::overshoot()); scale(105, 1); scale(149, .94f);
                    opacity(0, 0); opacity(18, 1); opacity(112, 1); opacity(149, 0); break;
                default: break;
            }
        }
    }

    LayerHandle& addImageAnimation(TemplateScene& scene, ImageAnimation animation,
                                   const std::string& assetPath, const std::string& name,
                                   ImageFrameStyle frame, ImageCameraMove cameraMove) {
        LayerHandle& image = scene.image(ImageSpec{
                .path = assetPath, .name = name, .frame = std::move(frame)});

        if (isImage25d(animation)) {
            Layer& layer = *scene.motion().findLayer(image.id());
            image25d(layer, scene.fps(), animation);
            // Camera motions are authored by the existing ChrononMotion3D rig.
            // Image-only recipes deliberately leave that rig untouched.
            const float fps = scene.fps();
            switch (animation) {
                case ImageAnimation::DollySettle:
                    scene.camera().push(350.f).between(0, 55);
                    break;
                case ImageAnimation::OrbitArc:
                    chrononmotion::motion::presets::cameraOrbit(
                            scene.camera().rig(), 0, 75,
                            chrononmotion::math::degToRad(-3.2f), 0.f, fps);
                    chrononmotion::motion::presets::cameraOrbit(
                            scene.camera().rig(), 75, 74,
                            chrononmotion::math::degToRad(6.4f), 0.f, fps);
                    break;
                case ImageAnimation::CounterTilt:
                    scene.camera().orbit(0.f, chrononmotion::math::degToRad(1.5f)).between(0, 50);
                    break;
                case ImageAnimation::DollyBreath:
                    scene.camera().push(240.f).between(0, 55);
                    scene.camera().push(-240.f).between(100, 149);
                    scene.camera().fov(55.f, 52.f).between(0, 55);
                    scene.camera().fov(52.f, 55.f).between(100, 149);
                    break;
                case ImageAnimation::ParallaxDrift:
                    scene.camera().push(280.f).between(0, 30);
                    chrononmotion::motion::presets::cameraPan(
                            scene.camera().rig(), 30, 78,
                            chrononmotion::Vector2(120.f, 0.f), fps);
                    chrononmotion::motion::presets::cameraPan(
                            scene.camera().rig(), 108, 41,
                            chrononmotion::Vector2(-120.f, 0.f), fps);
                    break;
                case ImageAnimation::HeroPullExit:
                    scene.camera().push(350.f).between(0, 35);
                    scene.camera().push(-150.f).between(105, 149);
                    break;
                default: break;
            }
            (void) cameraMove; // The 2.5D preset owns its camera, if it uses one.
            return image;
        } else if (animation != ImageAnimation::Fade && animation != ImageAnimation::Rise &&
                   animation != ImageAnimation::ScalePop && animation != ImageAnimation::Slide &&
                   animation != ImageAnimation::Spin) {
            throw std::invalid_argument("addImageAnimation: unknown animation");
        }

        using chrononmotion::motion::presets::Direction;
        switch (animation) {
            case ImageAnimation::Fade:
                image.animate(FadeIn{.inFrame = 0, .duration = 70});
                break;
            case ImageAnimation::Rise:
                image.animate(SlideIn{.direction = Direction::Up, .inFrame = 0,
                                      .duration = 30, .distance = 180.f})
                     .animate(FadeIn{.inFrame = 0, .duration = 16});
                chrononmotion::motion::presets::floatHover(
                        *scene.motion().findLayer(image.id()), 30, 100, 30.f, scene.fps());
                break;
            case ImageAnimation::ScalePop:
                image.animate(ScalePop{.inFrame = 0, .duration = 96,
                                       .from = 0.82f, .to = 1.08f})
                     .animate(FadeIn{.inFrame = 0, .duration = 16});
                break;
            case ImageAnimation::Slide:
                image.animate(SlideIn{.direction = Direction::Left, .inFrame = 0,
                                      .duration = 90, .distance = 320.f})
                     .animate(FadeIn{.inFrame = 0, .duration = 18});
                break;
            case ImageAnimation::Spin:
                image.animate(SpinXYZ{.inFrame = 0, .duration = 126, .turns = 0.5f})
                     .animate(FadeIn{.inFrame = 0, .duration = 18});
                break;
            default:
                throw std::invalid_argument("addImageAnimation: unknown animation");
        }

        // All camera evaluation stays in ChrononMotion3D. Splitting the combined
        // move into adjacent windows lets each preset start from the previous pose.
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
                throw std::invalid_argument("addImageAnimation: unknown camera move");
        }
        image.animate(FadeOut{.startFrame = 132, .duration = 18});
        return image;
    }

}// namespace chronontemplate
