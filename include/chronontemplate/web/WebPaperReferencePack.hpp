// ChrononTemplate — native rebuilds of five supplied web/paper reference frames.
//
// The five recipes are pure RenderPlan V3 compositions:
//   * a LA Times page tilted in 2.5D on a dark desk,
//   * a torn paper strip on charcoal with a progressive highlighter,
//   * a sharp evidence paragraph over a heavily blurred newspaper,
//   * an archival collage with a framed Golden Gate photograph,
//   * a book page whose yellow highlighter fills left-to-right.
//
// The paper artwork is a raster content asset (the same pattern as the
// existing newspaper family); every transform, marker sweep, shadow and
// camera pose is authored here as native plan data. No browser or live DOM.
#ifndef CHRONONTEMPLATE_WEB_PAPER_REFERENCE_PACK_HPP
#define CHRONONTEMPLATE_WEB_PAPER_REFERENCE_PACK_HPP

#include <array>
#include <nlohmann/json.hpp>
#include <string>

namespace chronontemplate::web {

enum class PaperReferenceRecipe : unsigned char {
    NewspaperTilt,     // LA Times page, perspective tilt, slow settle
    TornStrip,         // ragged paper strip, charcoal ground, yellow sweep
    BlurredEvidence,   // sharp paragraph over a defocused newspaper
    BridgeCollage,     // archival title + framed Golden Gate photograph
    BookHighlight      // book page, progressive multiple-blend highlighter
};

[[nodiscard]] const char* paperReferenceName(PaperReferenceRecipe recipe);
[[nodiscard]] std::array<PaperReferenceRecipe, 5> allPaperReferenceRecipes();

struct PaperReferenceSpec {
    PaperReferenceRecipe recipe{PaperReferenceRecipe::NewspaperTilt};
    int durationFrames{180};  // 6 s at 30 fps
    int fps{30};
    std::string outputName{};

    void validate() const;
    [[nodiscard]] std::string planName() const;
    [[nodiscard]] std::string outputStem() const;
};

/// Complete `chronon.render-plan.v3` document for one recipe.
[[nodiscard]] nlohmann::json buildPaperReferencePlan(const PaperReferenceSpec& spec);

}  // namespace chronontemplate::web

#endif  // CHRONONTEMPLATE_WEB_PAPER_REFERENCE_PACK_HPP
