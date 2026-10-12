#ifndef CHRONONTEMPLATE_PIXEL_GRID_PACK_HPP
#define CHRONONTEMPLATE_PIXEL_GRID_PACK_HPP

#include "chronontemplate/single_images/ImageAnimationPack.hpp"

#include <string>

namespace chronontemplate {

    /// Central Apollo card over a dimmed oversized copy of the same asset
    /// with a thin grid lattice on top. Blur, pixelation and dimming are
    /// renderer-side; the C++ authors the choreography: backdrop plate,
    /// four lattice bars and the hero entrance on the 150-frame timeline.
    enum class ImagePixelGrid {
        GridReveal,
        PixelStepIn,
        GridZoomOut,
        GridSlideTiles,
        GridBreathe
    };

    /// Add the hero image plus its backdrop plate and grid lattice.
    /// `assetPath` is resolved by the supplied Chronon ContentHost; the same
    /// asset feeds both the hero card and the backdrop plate.
    [[nodiscard]] LayerHandle& addImagePixelGrid(
            TemplateScene& scene, ImagePixelGrid animation,
            const std::string& assetPath, const std::string& name = "Image",
            ImageFrameStyle frame = ImageFrameStyle{
                    .cornerRadius = 64.f, .borderColor = {}, .borderWidth = 0.f},
            ImageCameraMove cameraMove = ImageCameraMove::None);

}// namespace chronontemplate

#endif//CHRONONTEMPLATE_PIXEL_GRID_PACK_HPP
