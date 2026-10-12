#ifndef CHRONONTEMPLATE_EDGE_STROKE_PACK_HPP
#define CHRONONTEMPLATE_EDGE_STROKE_PACK_HPP

#include "chronontemplate/single_images/ImageAnimationPack.hpp"

#include <string>

namespace chronontemplate {

    /// Signature orange edge strokes on one or two card sides. The bars are
    /// shape layers parented to the centered hero image so they follow the
    /// entrance choreography; the renderer draws the color, the C++ authors
    /// the motion on the 150-frame timeline.
    enum class ImageEdgeStroke {
        StrokeLeft,
        StrokeRight,
        StrokeDuo,
        StrokeTopBottom,
        StrokeSweep
    };

    /// Add the hero image with its orange side stroke(s).
    /// `assetPath` is resolved by the supplied Chronon ContentHost.
    [[nodiscard]] LayerHandle& addImageEdgeStroke(
            TemplateScene& scene, ImageEdgeStroke animation,
            const std::string& assetPath, const std::string& name = "Image",
            ImageFrameStyle frame = ImageFrameStyle{
                    .cornerRadius = 64.f, .borderColor = {}, .borderWidth = 0.f},
            ImageCameraMove cameraMove = ImageCameraMove::None);

}// namespace chronontemplate

#endif//CHRONONTEMPLATE_EDGE_STROKE_PACK_HPP
