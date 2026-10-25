#include "chronontemplate/investigation_board/InvestigationBoardPack.hpp"

#include "fake_content_host.hpp"
#include "motion_check.hpp"

#include <stdexcept>

using namespace chronontemplate;
using chronontemplate_test::FakeContentHost;
using chrononmotion_test::check;
using chrononmotion_test::section;

namespace {

    InvestigationBoardSpec threeCardBoard() {
        InvestigationBoardSpec spec;
        spec.items = {
                InvestigationBoardItem{.path = "assets/test/square_bottle_test.png", .x = 500.f, .y = 400.f,
                                       .rotationDegrees = -4.f},
                InvestigationBoardItem{.path = "assets/test/square_bottle_test.png", .x = 1200.f, .y = 420.f,
                                       .rotationDegrees = 3.f},
                InvestigationBoardItem{.path = "assets/test/square_bottle_test.png", .x = 900.f, .y = 800.f,
                                       .rotationDegrees = -1.5f}};
        spec.connections = {{0, 1}, {1, 2}};
        return spec;
    }

    void theBoardBuildsOneCardPerItemAndOnePinEach() {
        section("board builds cards, pins and strings");
        FakeContentHost host;
        TemplateScene scene("investigation_board", 30.f, host, 1920.f, 1080.f);
        const InvestigationBoardLayers layers = addInvestigationBoard(scene, threeCardBoard());
        check(layers.cards.size() == 3, "one card is authored per item");
        check(layers.pins.size() == 3, "one pin is authored per item");
        check(layers.strings.size() == 2, "one red string is authored per connection");
        check(layers.endFrame == 240, "the board stays on screen for its duration");
        check(scene.validate().empty(), "the investigation board scene validates");
    }

    void theBoardRejectsInvalidSpecs() {
        section("board rejects invalid specs");
        FakeContentHost host;
        TemplateScene scene("investigation_board_invalid", 30.f, host, 1920.f, 1080.f);

        InvestigationBoardSpec empty;
        bool threw = false;
        try { addInvestigationBoard(scene, empty); } catch (const std::invalid_argument&) { threw = true; }
        check(threw, "a board with no items is rejected");

        InvestigationBoardSpec selfLink = threeCardBoard();
        selfLink.connections = {{1, 1}};
        threw = false;
        try { addInvestigationBoard(scene, selfLink); } catch (const std::invalid_argument&) { threw = true; }
        check(threw, "a connection that joins an item to itself is rejected");

        InvestigationBoardSpec outOfRange = threeCardBoard();
        outOfRange.connections = {{0, 7}};
        threw = false;
        try { addInvestigationBoard(scene, outOfRange); } catch (const std::invalid_argument&) { threw = true; }
        check(threw, "a connection that points past the item list is rejected");
    }

}// namespace

int main() {
    theBoardBuildsOneCardPerItemAndOnePinEach();
    theBoardRejectsInvalidSpecs();
    return chrononmotion_test::report();
}
