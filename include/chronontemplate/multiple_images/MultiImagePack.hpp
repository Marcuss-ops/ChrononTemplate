// ChrononTemplate — the multi-image pack: one scene, several images.
//
// The recipes place a fixed number of images in a layout (duo, trio, quad,
// penta), caption each one, and stage a single entrance across the grid so the
// board assembles as one move instead of N independent clips. The pack authors
// ordinary image/text layers; Chronon owns the bytes and the rasterization.
//
// The pack is data, not rendering: `multiImageCells` exposes the grid so a test
// can pin it without owning a scene.

#ifndef CHRONONTEMPLATE_MULTIPLE_IMAGES_MULTI_IMAGE_PACK_HPP
#define CHRONONTEMPLATE_MULTIPLE_IMAGES_MULTI_IMAGE_PACK_HPP

#include "chronontemplate/core/TemplateScene.hpp"

#include "chrononmotion/math/Vector2.hpp"

#include <cstddef>
#include <cstdint>
#include <string>
#include <vector>

namespace chronontemplate {

    /// How the images are arranged in the frame.
    enum class MultiImageLayout : std::uint8_t {
        Duo,    ///< two images side by side
        Trio,   ///< three images in a row
        Quad,   ///< two by two
        Penta   ///< two on top, three below
    };

    /// The entrance the whole board shares. The grid staggers one recipe across
    /// the images so the board reads as a single move.
    enum class MultiImageEntrance : std::uint8_t {
        Fade,       ///< opacity only
        Rise,       ///< each card rises into its cell
        ScalePop    ///< each card pops from below then settles
    };

    /// How the board is dressed. Classic is the original bare grid; the other
    /// looks add the plate, the archival header and the styled frames seen in
    /// the editorial reference boards. The look owns the frame and caption
    /// typography; `MultiImageTile::frame` keeps authoring the Classic tiles.
    enum class MultiImageStyle : std::uint8_t {
        Classic,       ///< plain tiles and captions on the scene's own ground
        ArchiveBoard,  ///< light board, archival header + rule, rounded shadowed cards
        SepiaTorn,     ///< aged paper plate, torn-edge prints, serif captions
        PolaroidFan    ///< dark board, white polaroid borders, fanned tilts
    };

    /// Stable snake-case id of a style (the catalog/consumer-facing name).
    [[nodiscard]] const char* multiImageStyleId(MultiImageStyle style) noexcept;

    /// Stable ids of the group choreographies a layout certifies. Each id is a
    /// real choreography of the layout's tiles, not just a catalog name.
    [[nodiscard]] std::vector<std::string> multiImageMotionIds(MultiImageLayout layout);

    /// True when `motionId` is one of the layout's certified choreographies.
    [[nodiscard]] bool isMultiImageMotion(MultiImageLayout layout, const std::string& motionId);

    /// Select one certified choreography with a stable pseudo-random draw.
    /// The same seed/layout returns the same id; a previous id is avoided when
    /// the layout has another candidate.
    [[nodiscard]] std::string selectMultiImageMotion(MultiImageLayout layout,
                                                     const std::string& seed,
                                                     const std::string& previous = {});

    struct MultiImageTile {
        std::string path{};
        std::string caption{};  ///< optional caption under the tile; empty derives it from the path
        ImageFrameStyle frame{.cornerRadius = 24.f};
    };

    struct MultiImageSpec {
        std::vector<MultiImageTile> tiles{};
        MultiImageLayout layout{MultiImageLayout::Duo};
        MultiImageEntrance entrance{MultiImageEntrance::Rise};
        MultiImageStyle style{MultiImageStyle::Classic};
        /// Archival header drawn top-left by ArchiveBoard and SepiaTorn.
        std::string headerLabel{"Archive image"};
        /// The subjects line under the header rule, e.g. the captioned names.
        std::string headerSubtitle{};
        /// Certified group choreography, or `random` to select one from the
        /// layout's catalog. Random selection is stable for motionSeed; when
        /// motionSeed is empty the scene and tile paths provide the seed.
        /// Empty explicitly keeps the shared `entrance` stagger.
        std::string motionId{"random"};
        std::string motionSeed{};
        float tileWidth{560.f};
        float tileHeight{315.f};
        float gap{48.f};
        int inFrame{0};
        int duration{120};    ///< frames the assembly takes
        int holdFrames{24};   ///< frames the board rests before its exit
        float captionOffset{26.f};
        std::string captionFont{"Inter-Bold.ttf"};
        float captionFontSize{36.f};
        std::string captionColor{"#FFFFFF"};
    };

    /// What the pack authored. The handles point into the scene's own handle
    /// storage, which is stable for the scene's lifetime.
    struct MultiImageBoard {
        std::vector<LayerHandle*> tiles{};
        std::vector<LayerHandle*> captions{};
        std::string motionId{}; ///< resolved choreography; empty for legacy entrance
        int inFrame{0};
        int endFrame{0};
    };

    /// How many tiles a layout holds.
    [[nodiscard]] std::size_t multiImageTileCount(MultiImageLayout layout);

    /// The cells of a layout in reading order, as canvas fractions with the
    /// origin at the top-left. Exposed so a test can pin the grid.
    [[nodiscard]] std::vector<chrononmotion::Vector2> multiImageCells(MultiImageLayout layout);

    /// Stable snake-case id of a layout (the catalog/consumer-facing name).
    [[nodiscard]] const char* multiImageLayoutId(MultiImageLayout layout) noexcept;

    /// A short label for a tile derived from its asset path
    /// (`assets/card_trio_1.png` -> `CARD TRIO 1`).
    [[nodiscard]] std::string multiImageTileLabel(const std::string& assetPath);

    /// Build the board into `scene`: place the tiles, caption each one and
    /// stagger the shared entrance across the grid. Throws
    /// `std::invalid_argument` when the tile count does not match the layout,
    /// when a tile has no path, or when a dimension is not positive.
    [[nodiscard]] MultiImageBoard addMultiImageBoard(TemplateScene& scene,
                                                     const MultiImageSpec& spec);

}// namespace chronontemplate

#endif//CHRONONTEMPLATE_MULTIPLE_IMAGES_MULTI_IMAGE_PACK_HPP
