#ifndef CHRONONTEMPLATE_IMAGE_ANIMATION_PACK_HPP
#define CHRONONTEMPLATE_IMAGE_ANIMATION_PACK_HPP

#include "chronontemplate/TemplateScene.hpp"

#include <string>

namespace chronontemplate {

    /// Image motion recipes. The original five 2D entrances remain available;
    /// the image_25d_* entries add the clean 2.5D pack.
    enum class ImageAnimation {
        Fade,
        Rise,
        ScalePop,
        Slide,
        Spin,
        DepthFloatIn,
        YawFlipIn,
        PitchLift,
        PopZBounce,
        Swipe3D,
        CardSwing,
        DollySettle,
        OrbitArc,
        CounterTilt,
        DollyBreath,
        ParallaxDrift,
        HeroPullExit
    };

    /// Optional camera move for 2.5D image scenes. The camera implementation
    /// and interpolation are delegated to ChrononMotion3D through CameraHandle.
    enum class ImageCameraMove {
        None,
        Dolly,
        Orbit,
        DollyOrbit
    };

    /// Add one image and author the selected entrance and optional camera move.
    /// `assetPath` is resolved by the supplied Chronon ContentHost.
    [[nodiscard]] LayerHandle& addImageAnimation(
            TemplateScene& scene, ImageAnimation animation,
            const std::string& assetPath, const std::string& name = "Image",
            ImageFrameStyle frame = ImageFrameStyle{
                    .cornerRadius = 64.f, .borderColor = {}, .borderWidth = 0.f},
            ImageCameraMove cameraMove = ImageCameraMove::DollyOrbit);

}// namespace chronontemplate

#endif//CHRONONTEMPLATE_IMAGE_ANIMATION_PACK_HPP
