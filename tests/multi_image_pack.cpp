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

    /// Opacity of every tile sampled every 10 frames: the choreography's signature.
    std::vector<float> tileOpacityTimeline(const MultiImageSpec& spec, std::size_t tileIndex) {
        FakeContentHost host;
        TemplateScene scene("timeline", 30.f, host, 1920.f, 1080.f);
        const MultiImageBoard board = addMultiImageBoard(scene, spec);
        std::vector<float> out;
        for (int frame = 0; frame <= 140; frame += 10) {
            const FrameSubmission sub = scene.submit(frame);
            const BoundLayer* layer = findLayer(sub, board.tiles[tileIndex]->id());
            out.push_back(layer ? layer->transform.opacity : -1.f);
        }
        return out;
    }

    void theGroupMotionsAreCertifiedPerLayout() {
        section("group motions are certified per layout");
        constexpr std::array<MultiImageLayout, 4> layouts{
                MultiImageLayout::Duo, MultiImageLayout::Trio,
                MultiImageLayout::Quad, MultiImageLayout::Penta};
        for (const MultiImageLayout layout : layouts) {
            const std::vector<std::string> ids = multiImageMotionIds(layout);
            check(ids.size() >= 2, "each layout certifies at least two group motions");
            for (const std::string& id : ids) {
                check(isMultiImageMotion(layout, id), "a certified motion is accepted by its layout");
                MultiImageSpec spec = specFor(layout);
                spec.motionId = id;
                FakeContentHost host;
                TemplateScene scene("motion_" + id, 30.f, host, 1920.f, 1080.f);
                const MultiImageBoard board = addMultiImageBoard(scene, spec);
                check(board.tiles.size() == multiImageTileCount(layout),
                      "a certified motion authors one layer per tile");
                check(scene.validate().empty(), "a certified motion builds a valid scene");

                const FrameSubmission settled = scene.submit(100);
                for (LayerHandle* tile : board.tiles) {
                    const BoundLayer* layer = findLayer(settled, tile->id());
                    check(layer && layer->transform.opacity >= 0.95f,
                          "every tile is fully visible by mid-board");
                }
            }
            bool threw = false;
            MultiImageSpec bad = specFor(layout);
            bad.motionId = "not_a_real_motion";
            try {
                FakeContentHost host;
                TemplateScene scene("bad_motion", 30.f, host, 1920.f, 1080.f);
                (void) addMultiImageBoard(scene, bad);
            } catch (const std::invalid_argument&) {
                threw = true;
            }
            check(threw, "an uncertified motion id is rejected");
        }
    }

    void randomGroupMotionsAreStableAndApplied() {
        section("random group motions are stable and applied");
        constexpr std::array<MultiImageLayout, 4> layouts{
                MultiImageLayout::Duo, MultiImageLayout::Trio,
                MultiImageLayout::Quad, MultiImageLayout::Penta};
        for (const MultiImageLayout layout : layouts) {
            const std::vector<std::string> ids = multiImageMotionIds(layout);
            const std::string first = selectMultiImageMotion(layout, "story-a");
            check(isMultiImageMotion(layout, first), "random selection returns a certified motion");
            check(selectMultiImageMotion(layout, "story-a") == first,
                  "the same seed selects the same motion");
            check(selectMultiImageMotion(layout, "story-a", first) != first,
                  "a prior motion is avoided when another candidate exists");

            bool sawAlternative = false;
            for (int seed = 0; seed < 32 && !sawAlternative; ++seed) {
                sawAlternative = selectMultiImageMotion(layout, "story-" + std::to_string(seed)) != first;
            }
            check(sawAlternative && ids.size() > 1, "different seeds can choose different motions");

            MultiImageSpec spec = specFor(layout);
            spec.motionSeed = "story-a";
            FakeContentHost host;
            TemplateScene scene("random_motion", 30.f, host, 1920.f, 1080.f);
            const MultiImageBoard board = addMultiImageBoard(scene, spec);
            check(board.motionId == first, "board exposes its resolved random motion");
        }
    }

    void theTwoMotionsOfALayoutDiffer() {
        section("the two motions of a layout produce different choreographies");
        constexpr std::array<MultiImageLayout, 4> layouts{
                MultiImageLayout::Duo, MultiImageLayout::Trio,
                MultiImageLayout::Quad, MultiImageLayout::Penta};
        for (const MultiImageLayout layout : layouts) {
            const std::vector<std::string> ids = multiImageMotionIds(layout);
            MultiImageSpec first = specFor(layout);
            first.motionId = ids[0];
            MultiImageSpec second = specFor(layout);
            second.motionId = ids[1];
            bool differs = false;
            for (std::size_t tile = 0; tile < multiImageTileCount(layout); ++tile) {
                if (tileOpacityTimeline(first, tile) != tileOpacityTimeline(second, tile)) {
                    differs = true;
                }
            }
            check(differs, "the two certified motions stagger the tiles differently");
        }
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
    theGroupMotionsAreCertifiedPerLayout();
    randomGroupMotionsAreStableAndApplied();
    theTwoMotionsOfALayoutDiffer();
    return chrononmotion_test::report();
}
