// ChrononTemplate — four archival documentary card recipes.
//
// The looks are compositions of primitives that already exist: ImageFrameStyle
// grading/grain/torn edges, native shape layers (paper, grid, borders, stains,
// vignettes) and the EffectsPack overlays (grain, scratches, dust, RGB split).
// Nothing here adds a renderer or a new effect kind.
//
// Layer order is part of the recipe, bottom to top:
//   01 TornPaperPortrait   graph paper -> stains -> shadow -> torn mat -> photo
//                          -> name -> grain/RGB split
//   02 ArchivePrint        worn grey -> dust -> black border -> white paper
//                          -> B/W photo -> grain/scratches
//   03 VintageFilm         black -> diffuse halo -> rounded window -> B/W photo
//                          -> vignette -> dust/scratches
//   04 DoublePortrait      parchment -> stains -> two torn mats -> sepia photos
//                          -> two names -> archival label

#ifndef CHRONONTEMPLATE_ARCHIVAL_CARD_PACK_HPP
#define CHRONONTEMPLATE_ARCHIVAL_CARD_PACK_HPP

#include "chronontemplate/core/TemplateScene.hpp"

#include <cstdint>
#include <string>
#include <vector>
#include <vector>

namespace chronontemplate {

    /// The four reference compositions from the archive brief.
    enum class ArchivalCardLook : std::uint8_t {
        TornPaperPortrait,   ///< aged graph paper, torn white mat, RGB split
        ArchivePrint,        ///< B/W print, double black border, dust and scratches
        VintageFilmProjection, ///< rounded projection window, halo, heavy vignette
        DoublePortraitArchive  ///< parchment, two sepia cuts, two names + label
    };

    /// A parametric archive card. The default geometry is authored for a
    /// 1920x1080 canvas; centres below zero mean "canvas centre".
    struct ArchivalCardSpec {
        std::string primaryAsset{};
        std::string secondaryAsset{}; ///< DoublePortraitArchive only
        std::string primaryLabel{};
        std::string secondaryLabel{};
        std::string archiveLabel{};   ///< small editorial line under the card
        std::string font{};
        std::string name{"archival_card"};
        float primaryWidth{760.f};
        float primaryHeight{540.f};
        float secondaryWidth{520.f};
        float secondaryHeight{420.f};
        float centerX{-1.f};
        float centerY{-1.f};
        int inFrame{0};
        int durationFrames{150};      ///< 5 s at 30 fps
    };

    /// Handles to the authored layers, for caller-side timing tweaks.
    struct ArchivalCardLayers {
        MotionLayerId background{0};
        MotionLayerId mat{0};
        MotionLayerId primary{0};
        MotionLayerId secondary{0};
        MotionLayerId caption{0};
        std::vector<MotionLayerId> animatedDust;
    };

    /// The image treatment of a look. TornPaper and DoublePortrait carry a torn
    /// alpha edge; ArchivePrint and VintageFilm are neutral (saturation 0).
    [[nodiscard]] ImageFrameStyle archivalCardFrameStyle(ArchivalCardLook look);

    /// Stable snake_case id, used in catalogs and layer names.
    [[nodiscard]] const char* archivalCardLookId(ArchivalCardLook look) noexcept;

    /// All four ids in declaration order.
    [[nodiscard]] std::vector<std::string> archivalCardLookIds();

    /// Author the card. Throws std::invalid_argument for empty assets, unknown
    /// looks, a missing second portrait, or a window/geometry outside the
    /// supported range.
    [[nodiscard]] ArchivalCardLayers addArchivalCard(TemplateScene& scene,
                                                     ArchivalCardLook look,
                                                     const ArchivalCardSpec& spec);

    [[nodiscard]] const char* archivalCardPackId() noexcept;

} // namespace chronontemplate

#endif // CHRONONTEMPLATE_ARCHIVAL_CARD_PACK_HPP
