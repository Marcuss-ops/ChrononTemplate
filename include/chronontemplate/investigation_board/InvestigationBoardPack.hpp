// ChrononTemplate — the investigation board pack.
//
// A corkboard plate with photos and documents pinned to it at slight
// rotations, a soft drop shadow under each card, red strings between pins and
// one slow camera pan. Everything is authored as ordinary image/shape/camera
// data on the TemplateScene; Chronon owns the pixels.
//
// Strings are thin rotated rectangles between two pin centres, so they need no
// path geometry and stay deterministic.

#ifndef CHRONONTEMPLATE_INVESTIGATION_BOARD_PACK_HPP
#define CHRONONTEMPLATE_INVESTIGATION_BOARD_PACK_HPP

#include "chronontemplate/core/TemplateScene.hpp"

#include <cstddef>
#include <string>
#include <vector>

namespace chronontemplate {

    struct InvestigationBoardItem {
        std::string path{};                ///< photo or document asset
        float x{0.f};                      ///< card centre, canvas pixels
        float y{0.f};
        float width{480.f};
        float height{320.f};
        float rotationDegrees{0.f};        ///< slight tilt, e.g. -4 .. 4
        std::string borderColor{"#F4F1EA"};///< paper edge
        float borderWidth{8.f};
    };

    /// A red string from the pin of item `from` to the pin of item `to`.
    struct InvestigationBoardConnection {
        std::size_t from{0};
        std::size_t to{0};
    };

    struct InvestigationBoardSpec {
        std::string corkPath{"assets/nba_rivalry/web/corkboard_bg.png"};
        std::string pinPath{"assets/nba_rivalry/web/red_pushpin.png"};
        std::vector<InvestigationBoardItem> items{};
        std::vector<InvestigationBoardConnection> connections{};
        int inFrame{0};
        int duration{240};        ///< frames the whole board is on screen
        int staggerFrames{12};    ///< delay between consecutive cards
        float pinSize{28.f};
        float stringWidth{4.f};
        float shadowOffset{10.f}; ///< drop shadow offset, px down and right
        float shadowOpacity{0.35f};
        float panYaw{-0.06f};     ///< camera pan across the board, radians
    };

    struct InvestigationBoardLayers {
        std::vector<LayerHandle*> cards{};
        std::vector<LayerHandle*> pins{};
        std::vector<LayerHandle*> strings{};
        int endFrame{0};
    };

    /// Build the board into `scene`. Throws `std::invalid_argument` when the
    /// spec has no items, a connection points outside the item list or joins an
    /// item to itself, or a size, duration or pan is not finite and positive.
    [[nodiscard]] InvestigationBoardLayers addInvestigationBoard(TemplateScene& scene,
                                                                 const InvestigationBoardSpec& spec);

}// namespace chronontemplate

#endif//CHRONONTEMPLATE_INVESTIGATION_BOARD_PACK_HPP
