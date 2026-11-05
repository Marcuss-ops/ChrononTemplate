// The WordLens contract: the underline marker is sized from the shaped advance
// of the same font the word layer renders, not from a character-count estimate.
#include "chronontemplate/camera_roll/WordLensPack.hpp"
#include "chronontemplate/web/WebFontMeasure.hpp"

#include "fake_content_host.hpp"
#include "motion_check.hpp"

#include <algorithm>
#include <cmath>

using namespace chronontemplate;
using chronontemplate_test::FakeContentHost;
using chrononmotion_test::check;
using chrononmotion_test::section;

namespace {

    void underlinesTrackTheShapedAdvance() {
        section("word-lens underlines follow the shaped advance width");
        FakeContentHost host;
        TemplateScene scene("word_lens_width", 30.f, host, 1920.f, 1080.f);
        WordLensSpec spec;
        spec.words = {{"food", {620.f, 390.f}, 0, 6, 86, 12.f, 110.f}};
        const auto board = addWordLensBoard(scene, spec);
        check(board.underlineLayers.size() == 1, "one underline per word");
        check(scene.validate().empty(), "the word board validates");

        constexpr const char* kFont = "assets/fonts/HelveticaNeue-Medium.otf";
        const float measured = web::shot::measureTextWidth(kFont, 142.f, "food");
        check(measured > 0.f, "the renderer font is measurable");

        const auto* underline = host.findShapeRequest("WordUnderline_food");
        check(underline != nullptr, "the underline reaches the content host");
        if (underline && measured > 0.f) {
            check(std::fabs(underline->size.x - (std::max(220.f, measured) + 30.f)) < 0.01f,
                  "the underline width follows the measured word, not a character count");
        }
    }

} // namespace

int main() {
    underlinesTrackTheShapedAdvance();
    return chrononmotion_test::report();
}
