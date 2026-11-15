// ChrononTemplate — Documentary parity suite.
//
// Seven native `chronon.render-plan.v3` fixtures distilled from the supplied
// documentary reference grammar. They are engineering fixtures first: every
// plan makes one renderer contract measurable (optical wrap, anchored type,
// multi-plane focus, particle depth, rounded 3D UI, CRT HUD, deterministic
// scrub) while still reading as a composed frame.
//
// The suite deliberately does not claim pixel parity against video_1/2/3:
// those reference files are not part of the repository. `PARITY_REFERENCE`
// stays NOT RUN until the decoded reference frames are supplied. The
// engine-side checks live in `tests/documentary_parity.cpp` and
// `tools/web_styles/verify_documentary_parity.py`.
#ifndef CHRONONTEMPLATE_WEB_DOCUMENTARY_PARITY_PACK_HPP
#define CHRONONTEMPLATE_WEB_DOCUMENTARY_PARITY_PACK_HPP

#include <array>
#include <nlohmann/json.hpp>
#include <string>

namespace chronontemplate::web {

enum class DocumentaryParityRecipe : unsigned char {
    MacroLcdTypewriter,       // PARITY_01
    KineticWhipBars,          // PARITY_02
    RackFocusStack,           // PARITY_03
    ParticleRainOcclusion,    // PARITY_04
    UiCardPanReveal,          // PARITY_05
    CrtHudCounter,            // PARITY_06
    DeterministicScrub        // PARITY_07
};

[[nodiscard]] const char* documentaryParityName(DocumentaryParityRecipe recipe);
[[nodiscard]] const char* documentaryParityTestId(DocumentaryParityRecipe recipe);
[[nodiscard]] std::array<DocumentaryParityRecipe, 7> allDocumentaryParityRecipes();

struct DocumentaryParitySpec {
    DocumentaryParityRecipe recipe{DocumentaryParityRecipe::MacroLcdTypewriter};
    int durationFrames{150};  // 5 s at 30 fps
    int fps{30};
    std::string outputName{};

    void validate() const;
    [[nodiscard]] std::string planName() const;
    [[nodiscard]] std::string outputStem() const;
};

/// Complete `chronon.render-plan.v3` document for one parity fixture.
[[nodiscard]] nlohmann::json buildDocumentaryParityPlan(const DocumentaryParitySpec& spec);

}  // namespace chronontemplate::web

#endif  // CHRONONTEMPLATE_WEB_DOCUMENTARY_PARITY_PACK_HPP
