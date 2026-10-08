#ifndef CHRONONTEMPLATE_ENTITY_FILMSTRIP_PACK_HPP
#define CHRONONTEMPLATE_ENTITY_FILMSTRIP_PACK_HPP

#include "chronontemplate/core/TemplateScene.hpp"

#include <string>
#include <vector>

namespace chronontemplate {

    /// One image and its independently-rendered native text title in a filmstrip.
    struct EntityFilmstripItem {
        std::string imagePath{};
        std::string title{};
    };

    struct EntityFilmstripSpec {
        std::vector<EntityFilmstripItem> items{};
        int inFrame{0};
        int itemDuration{36};
        int overlapFrames{16};
        float imageWidth{1260.f};
        float imageHeight{700.f};
        float cornerRadius{30.f};
        float titleFontSize{112.f};
        std::string font{"assets/fonts/Inter-Bold.ttf"};
        std::string background{"#EBE7DC"};
        std::string ink{"#08090B"};
        float gridSpacing{36.f};
    };

    struct EntityFilmstripComposition {
        std::vector<MotionLayerId> imageLayers{};
        std::vector<MotionLayerId> titleLayers{};
        MotionLayerId backgroundLayer{0};
        int endFrame{0};
    };

    /// Compose an editorial horizontal carousel of images and matching native
    /// titles. Each item has a swift horizontal pass, a short readable hold,
    /// then yields to the next item entering from the right.
    [[nodiscard]] EntityFilmstripComposition addEntityFilmstrip(
        TemplateScene& scene, const EntityFilmstripSpec& spec);

} // namespace chronontemplate

#endif // CHRONONTEMPLATE_ENTITY_FILMSTRIP_PACK_HPP
