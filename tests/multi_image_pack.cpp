#include "chronontemplate/multiple_images/MultiImagePack.hpp"

#include "fake_content_host.hpp"
#include "motion_check.hpp"

#include <array>
#include <cmath>
#include <stdexcept>
#include <string>
#include <vector>

using namespace chronontemplate;
using chronontemplate_test::FakeContentHost;
using chronontemplate_test::findLayer;
using chrononmotion_test::check;
using chrononmotion_test::section;

namespace {

    MultiImageSpec specFor(MultiImageLayout layout) {
        const std::size_t count = multiImageTileCount(layout);
        MultiImageSpec spec;
        spec.layout = layout;
        spec.entrance = MultiImageEntrance::Rise;
        for (std::size_t i = 0; i < count; ++i) {
            spec.tiles.push_back(MultiImageTile{
                    .path = "assets/images/card_trio_" + std::to_string(i + 1) + ".png"});
        }
        return spec;
    }

    void theLayoutsExposeTheirGridAndCount() {
        section("multi-image layouts expose their grid");
        constexpr std::array<MultiImageLayout, 4> layouts{
                MultiImageLayout::Duo, MultiImageLayout::Trio,
                MultiImageLayout::Quad, MultiImageLayout::Penta};
        constexpr std::array<std::size_t, 4> counts{2, 3, 4, 5};
        constexpr std::array<const char*, 4> ids{
                "multi_image_duo", "multi_image_trio", "multi_image_quad", "multi_image_penta"};

        for (std::size_t i = 0; i < layouts.size(); ++i) {
            check(multiImageTileCount(layouts[i]) == counts[i],
                  "each layout reports its tile count");
            const std::vector<chrononmotion::Vector2> cells = multiImageCells(layouts[i]);
            check(cells.size() == counts[i], "each layout reports one cell per tile");
            for (const chrononmotion::Vector2& cell : cells) {
                check(cell.x > 0.f && cell.x < 1.f && cell.y > 0.f && cell.y < 1.f,
                      "every cell stays inside the canvas");
            }
            check(std::string(multiImageLayoutId(layouts[i])) == ids[i],
                  "each layout has its stable catalog id");
        }
    }

    void theBoardsAssembleAndSubmit() {
        section("multi-image boards assemble and submit");
        constexpr std::array<MultiImageLayout, 4> layouts{
                MultiImageLayout::Duo, MultiImageLayout::Trio,
                MultiImageLayout::Quad, MultiImageLayout::Penta};
        constexpr std::array<const char*, 4> names{"duo", "trio", "quad", "penta"};

        for (std::size_t i = 0; i < layouts.size(); ++i) {
            FakeContentHost host;
            TemplateScene scene(std::string("board_") + names[i], 30.f, host, 1920.f, 1080.f);
            const MultiImageBoard board = addMultiImageBoard(scene, specFor(layouts[i]));

            check(board.tiles.size() == multiImageTileCount(layouts[i]),
                  "the board authors one layer per tile");
            check(board.captions.size() == multiImageTileCount(layouts[i]),
                  "every tile is captioned (derived from its path)");
            check(board.endFrame == 120 + 24, "the board ends after its duration and hold");

            const FrameSubmission start = scene.submit(0);
            const FrameSubmission middle = scene.submit(70);
            const FrameSubmission end = scene.submit(144);
            for (LayerHandle* tile : board.tiles) {
                check(tile != nullptr, "every tile handle is valid");
                const BoundLayer* a = findLayer(start, tile->id());
                const BoundLayer* b = findLayer(middle, tile->id());
                const BoundLayer* c = findLayer(end, tile->id());
                check(a && b && c, "each tile submits at start, middle and end");
                check(a && a->draws() && a->content.isImage(), "each tile keeps image content bound");
                if (b) {
                    check(std::isfinite(b->transform.opacity) &&
                                  b->transform.opacity >= 0.f && b->transform.opacity <= 1.f,
                          "each tile opacity stays finite and in range");
                }
                if (c) {
                    check(c->transform.opacity <= 0.05f, "each tile fades out before the end");
                }
            }
            check(scene.validate().empty(), "each board scene validates");
        }
    }

    void theBoardRejectsAMismatchedTileCount() {
        section("multi-image board rejects a mismatched tile count");
        FakeContentHost host;
        TemplateScene scene("board_bad", 30.f, host, 1920.f, 1080.f);
        MultiImageSpec spec = specFor(MultiImageLayout::Quad);
        spec.tiles.pop_back();
        bool threw = false;
        try {
            (void) addMultiImageBoard(scene, spec);
        } catch (const std::invalid_argument&) {
            threw = true;
        }
        check(threw, "a quad with three tiles is rejected");
    }

    void theTileLabelIsDerivedFromThePath() {
        section("multi-image tile labels");
        check(multiImageTileLabel("assets/card_trio_1.png") == "CARD TRIO 1",
              "the label drops the directory and extension and upper-cases");
        check(multiImageTileLabel("neil_armstrong.jpg") == "NEIL ARMSTRONG",
              "underscores become spaces");
    }

}// namespace

int main() {
    theLayoutsExposeTheirGridAndCount();
    theBoardsAssembleAndSubmit();
    theBoardRejectsAMismatchedTileCount();
    theTileLabelIsDerivedFromThePath();
    return chrononmotion_test::report();
}
