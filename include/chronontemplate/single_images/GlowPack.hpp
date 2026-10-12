#ifndef CHRONONTEMPLATE_GLOW_PACK_HPP
#define CHRONONTEMPLATE_GLOW_PACK_HPP

#include "chronontemplate/single_images/ImageAnimationPack.hpp"

#include <string>

namespace chronontemplate {

    /// Soft colored glow plates behind the centered hero image. The plate is
    /// a shape layer created before the card so it draws underneath; the
    /// renderer softens it into a halo, the C++ authors its fade and pulse
    /// on the 150-frame timeline. Plates stay subtle (peak 0.5 opacity).
    enum class ImageGlow {
        WarmGlow,
        CoolGlow,
        GoldGlow,
        RoseGlow,
        PulseGlow
    };

    /// Add the hero image with its glow plate underneath.
    /// `assetPath` is resolved by the supplied Chronon ContentHost.
    [[nodiscard]] LayerHandle& addImageGlow(
            TemplateScene& scene, ImageGlow animation,
            const std::string& assetPath, const std::string& name = "Image",
            ImageFrameStyle frame = ImageFrameStyle{
                    .cornerRadius = 64.f, .borderColor = {}, .borderWidth = 0.f},
            ImageCameraMove cameraMove = ImageCameraMove::None);

}// namespace chronontemplate

#endif//CHRONONTEMPLATE_GLOW_PACK_HPP
