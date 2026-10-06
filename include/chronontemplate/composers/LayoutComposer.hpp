// ChrononTemplate — the native layout composers: flex rows, columns and
// grids plus FLIP moves between arrangements.
//
// Remotion authors these with flexbox and CSS; here they are deterministic
// recipes over `TemplateScene`. `layoutCells` is a pure function of
// (count, canvas, margin, gap, columns) so a test can pin the grid without a
// scene, and `morphComposerBoard` animates an existing board from its current
// cells to a new arrangement — the shared-element move, as ordinary position
// tracks, hence a pure function of (scene, frame) like everything else.

#ifndef CHRONONTEMPLATE_COMPOSERS_LAYOUT_COMPOSER_HPP
#define CHRONONTEMPLATE_COMPOSERS_LAYOUT_COMPOSER_HPP

#include "chronontemplate/core/TemplateScene.hpp"

#include "chrononmotion/math/Vector2.hpp"

#include <cstddef>
#include <cstdint>
#include <string>
#include <vector>

namespace chronontemplate {

    /// How cells flow across the canvas.
    enum class LayoutDirection : std::uint8_t {
        Row,     ///< one row, N columns
        Column,  ///< one column, N rows
        Grid     ///< rows × columns, row-major
    };

    /// One cell in canvas pixels: top-left corner plus size.
    struct LayoutCell {
        float x{0.f};
        float y{0.f};
        float w{0.f};
        float h{0.f};
    };

    struct ComposerTile {
        std::string path{};
        std::string caption{};
    };

    struct ComposerSpec {
        std::vector<ComposerTile> tiles{};  ///< 1..9 tiles
        LayoutDirection direction{LayoutDirection::Grid};
        int columns{0};                     ///< Grid only; 0 selects ceil(sqrt(n))
        float margin{64.f};                 ///< outer margin, canvas px
        float gap{32.f};                    ///< inter-cell gap, canvas px
        float tileCornerRadius{24.f};
        std::string captionFont{};
        float captionFontSize{36.f};
        std::string captionColor{"#FFFFFF"};
        std::string name{"composer"};
        int inFrame{0};
        int duration{60};                   ///< frames the staggered entrance takes
        int holdFrames{24};
    };

    struct ComposerBoard {
        std::vector<LayerHandle*> tiles{};
        std::vector<LayerHandle*> captions{};
        std::vector<LayoutCell> cells{};
        float captionOffset{21.6f};
        int inFrame{0};
        int endFrame{0};
    };

    /// Pure grid math: cell rects in canvas pixels for `count` tiles.
    /// Throws `std::invalid_argument` on a zero count, more than 9 tiles, or
    /// degenerate margin/gap/geometry.
    [[nodiscard]] std::vector<LayoutCell> layoutCells(std::size_t count, float canvasW,
                                                      float canvasH, float margin, float gap,
                                                      LayoutDirection direction, int columns = 0);

    /// Stable snake-case id of a direction (catalog-facing, append-only).
    [[nodiscard]] const char* layoutDirectionId(LayoutDirection direction) noexcept;

    /// Author the board into `scene`: one image card per cell with a staggered
    /// rise entrance plus a shared fade exit, each card captioned underneath.
    /// Throws `std::invalid_argument` on the same bad geometry `layoutCells`
    /// rejects, an empty tile path, or a non-positive duration.
    [[nodiscard]] ComposerBoard addComposerBoard(TemplateScene& scene, const ComposerSpec& spec);

    /// FLIP the board to `newCells`: every tile and caption glides from its
    /// current centre to the new centre over `duration` frames starting at
    /// `inFrame`, then holds. Cell counts must match; the board's stored cells
    /// are updated in place so a second morph chains from the new arrangement.
    /// Throws `std::invalid_argument` on a count mismatch or bad timing.
    void morphComposerBoard(TemplateScene& scene, ComposerBoard& board,
                            const std::vector<LayoutCell>& newCells,
                            int inFrame, int duration);

}// namespace chronontemplate

#endif//CHRONONTEMPLATE_COMPOSERS_LAYOUT_COMPOSER_HPP
