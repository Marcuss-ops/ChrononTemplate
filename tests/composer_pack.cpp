#include "chronontemplate/composers/LayoutComposer.hpp"

#include "fake_content_host.hpp"
#include "motion_check.hpp"

#include <stdexcept>
#include <string>
#include <vector>

using namespace chronontemplate;
using chronontemplate_test::FakeContentHost;
using chronontemplate_test::findLayer;
using chrononmotion_test::check;
using chrononmotion_test::section;

namespace {

    void gridMathIsPureAndPinned() {
        section("layoutCells is a pure function of (count, canvas, margin, gap)");
        const std::vector<LayoutCell> cells = layoutCells(4, 1920.f, 1080.f, 64.f, 32.f,
                                                          LayoutDirection::Grid, 0);
        check(cells.size() == 4, "four tiles produce four cells");
        // 2x2 grid: inner 1792x952, cell 880x460, origins at margin + k*(cell+gap).
        check(cells[0].x == 64.f && cells[0].y == 64.f, "the first cell starts at the margin");
        check(cells[0].w == 880.f && cells[0].h == 460.f, "cells split the inner canvas evenly");
        check(cells[1].x == 976.f && cells[1].y == 64.f, "the second cell sits right of the first");
        check(cells[2].x == 64.f && cells[2].y == 556.f, "the third cell starts the second row");
        check(cells[3].x == 976.f && cells[3].y == 556.f, "the fourth cell closes the grid");

        const std::vector<LayoutCell> row = layoutCells(3, 1920.f, 1080.f, 64.f, 32.f,
                                                        LayoutDirection::Row, 0);
        check(row.size() == 3 && row[0].y == row[1].y, "a row shares one baseline");

        bool threw = false;
        try {
            (void) layoutCells(0, 1920.f, 1080.f, 64.f, 32.f, LayoutDirection::Grid, 0);
        } catch (const std::invalid_argument&) {
            threw = true;
        }
        check(threw, "a zero tile count is rejected");
    }

    void boardAuthorsCaptionsAndValidates() {
        section("addComposerBoard authors captioned tiles that validate");
        FakeContentHost host;
        TemplateScene scene("composer", 30.f, host, 1920.f, 1080.f);
        ComposerSpec spec;
        spec.tiles = {{"a.png", "uno"}, {"b.png", "due"}, {"c.png", "tre"}};
        spec.inFrame = 5;
        spec.duration = 60;
        const ComposerBoard board = addComposerBoard(scene, spec);
        check(board.tiles.size() == 3, "one card per tile");
        check(board.captions.size() == 3, "one caption per tile");
        check(board.cells.size() == 3, "cells are stored for FLIP chaining");
        check(scene.validate().empty(), "the board scene validates");

        const FrameSubmission mid = scene.submit(40);
        check(findLayer(mid, board.tiles[0]->id()) != nullptr, "tiles are bound mid-entrance");
    }

    void flipMorphMovesTilesBetweenArrangements() {
        section("morphComposerBoard glides tiles row -> grid");
        FakeContentHost host;
        TemplateScene scene("flip", 30.f, host, 1920.f, 1080.f);
        ComposerSpec spec;
        spec.tiles = {{"a.png", "uno"}, {"b.png", "due"}, {"c.png", "tre"}};
        spec.direction = LayoutDirection::Row;
        spec.inFrame = 0;
        spec.duration = 30;
        ComposerBoard board = addComposerBoard(scene, spec);
        const std::vector<LayoutCell> grid = layoutCells(3, 1920.f, 1080.f, 64.f, 32.f,
                                                         LayoutDirection::Grid, 0);
        morphComposerBoard(scene, board, grid, 60, 24);
        check(board.cells[0].x == grid[0].x, "the board stores the new arrangement");
        check(scene.validate().empty(), "the morphed scene validates");

        // Determinism across random access: same frame, same matrices.
        const FrameSubmission a = scene.submit(72);
        const FrameSubmission b = scene.submit(72);
        bool identical = a.layers.size() == b.layers.size();
        for (std::size_t i = 0; i < a.layers.size() && identical; ++i) {
            const auto& ma = a.layers[i].transform.world.elements;
            const auto& mb = b.layers[i].transform.world.elements;
            for (std::size_t k = 0; k < ma.size(); ++k) {
                if (ma[k] != mb[k]) identical = false;
            }
        }
        check(identical, "FLIP evaluation is a pure function of (scene, frame)");

        bool threw = false;
        try {
            morphComposerBoard(scene, board, layoutCells(2, 1920.f, 1080.f, 64.f, 32.f,
                                                         LayoutDirection::Row, 0), 90, 12);
        } catch (const std::invalid_argument&) {
            threw = true;
        }
        check(threw, "a cell count mismatch fails closed");
    }

}// namespace

int main() {
    gridMathIsPureAndPinned();
    boardAuthorsCaptionsAndValidates();
    flipMorphMovesTilesBetweenArrangements();
    return chrononmotion_test::report();
}
