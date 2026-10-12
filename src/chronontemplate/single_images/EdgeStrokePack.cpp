#include "chronontemplate/single_images/EdgeStrokePack.hpp"

#include "chronontemplate/single_images/ImageAnimationPack.hpp"

#include "chrononmotion/motion/Presets.hpp"

#include <stdexcept>

namespace chronontemplate {

    namespace {
        using chrononmotion::Vector2;
        using chrononmotion::Vector3;

        constexpr const char* kStrokeColor = "#FF7A1A";

        void orangeBar(TemplateScene& scene, unsigned parentId, const std::string& name,
                       float barW, float barH, float relX, float relY,
                       const Vector3& slideFrom) {
            LayerHandle& edge = scene.shape(ShapeSpec{
                    .size = Vector2(barW, barH), .fillColor = kStrokeColor,
                    .name = name, .cornerRadius = 5.f});
            edge.parent(parentId);
            edge.position(relX, relY);
            edge.alive(0, 150);
            edge.animateOpacity(0, 24, 0.f, 1.f);
            if (slideFrom.x != 0.f || slideFrom.y != 0.f || slideFrom.z != 0.f) {
                edge.animatePosition(0, 36, slideFrom);
            }
            edge.animateOpacity(132, 18, 1.f, 0.f);
        }
    }

    LayerHandle& addImageEdgeStroke(TemplateScene& scene, ImageEdgeStroke animation,
                                    const std::string& assetPath, const std::string& name,
                                    ImageFrameStyle frame, ImageCameraMove cameraMove) {
        switch (animation) {
            case ImageEdgeStroke::StrokeLeft:
            case ImageEdgeStroke::StrokeRight:
            case ImageEdgeStroke::StrokeDuo:
            case ImageEdgeStroke::StrokeTopBottom:
            case ImageEdgeStroke::StrokeSweep:
                break;
            default:
                throw std::invalid_argument("addImageEdgeStroke: unknown animation");
        }

        LayerHandle& image = scene.image(ImageSpec{
                .path = assetPath, .name = name, .frame = std::move(frame)});
        image.animate(ScalePop{.inFrame = 0, .duration = 88, .from = 0.92f, .to = 1.0f})
             .animate(FadeIn{.inFrame = 0, .duration = 20});

        // Geometry targets the 480px preset card (half-size 240); bars sit
        // just outside the card with a slight offset gap.
        switch (animation) {
            case ImageEdgeStroke::StrokeLeft:
                orangeBar(scene, image.id(), name + "_stroke_left",
                          10.f, 440.f, -258.f, 0.f, Vector3(-70.f, 0.f, 0.f));
                break;
            case ImageEdgeStroke::StrokeRight:
                orangeBar(scene, image.id(), name + "_stroke_right",
                          10.f, 440.f, 258.f, 0.f, Vector3(70.f, 0.f, 0.f));
                break;
            case ImageEdgeStroke::StrokeDuo:
                orangeBar(scene, image.id(), name + "_stroke_duo_left",
                          10.f, 440.f, -258.f, 0.f, Vector3(-70.f, 0.f, 0.f));
                orangeBar(scene, image.id(), name + "_stroke_duo_right",
                          10.f, 440.f, 258.f, 0.f, Vector3(70.f, 0.f, 0.f));
                break;
            case ImageEdgeStroke::StrokeTopBottom:
                orangeBar(scene, image.id(), name + "_stroke_top",
                          440.f, 10.f, 0.f, -258.f, Vector3(0.f, -70.f, 0.f));
                orangeBar(scene, image.id(), name + "_stroke_bottom",
                          440.f, 10.f, 0.f, 258.f, Vector3(0.f, 70.f, 0.f));
                break;
            case ImageEdgeStroke::StrokeSweep:
                // The orange bar travels from the left edge to the right
                // edge during the entrance, then rests on the right side.
                orangeBar(scene, image.id(), name + "_stroke_sweep",
                          10.f, 440.f, 258.f, 0.f, Vector3(-516.f, 0.f, 0.f));
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
                throw std::invalid_argument("addImageEdgeStroke: unknown camera move");
        }
        image.animate(FadeOut{.startFrame = 132, .duration = 18});
        return image;
    }

}// namespace chronontemplate
