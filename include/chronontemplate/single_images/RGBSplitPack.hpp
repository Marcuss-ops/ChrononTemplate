#ifndef CHRONONTEMPLATE_RGB_SPLIT_PACK_HPP
#define CHRONONTEMPLATE_RGB_SPLIT_PACK_HPP

#include "chronontemplate/single_images/ImageAnimationPack.hpp"

#include <string>

namespace chronontemplate {

    /// Anaglyph-style RGB channel choreography around the centered hero
    /// image: a red ghost bar rides the left edge, a cyan ghost bar the
    /// right edge. Real channel separation is renderer-side; the C++
    /// authors the classic offsets (static, converge, pulse, glitch jitter,
    /// exit divergence) on the 150-frame timeline.
    enum class ImageRGBSplit {
        SplitStatic,
        SplitConverge,
        SplitPulse,
        SplitGlitch,
        SplitExit
    };

    /// Add the hero image with its red/cyan ghost bars.
    /// `assetPath` is resolved by the supplied Chronon ContentHost.
    [[nodiscard]] LayerHandle& addImageRGBSplit(
            TemplateScene& scene, ImageRGBSplit animation,
            const std::string& assetPath, const std::string& name = "Image",
            ImageFrameStyle frame = ImageFrameStyle{
                    .cornerRadius = 64.f, .borderColor = {}, .borderWidth = 0.f},
            ImageCameraMove cameraMove = ImageCameraMove::None);

}// namespace chronontemplate

#endif//CHRONONTEMPLATE_RGB_SPLIT_PACK_HPP
