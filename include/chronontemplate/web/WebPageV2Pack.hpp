// ChrononTemplate — Web Pages V2 (Complete + Highlight 3D + Long Phrases Blurred).
//
// Second-generation native C++ web-page composition pack. Same six-variant
// grammar as WebPageHighlightPack (three recipes · two themes) but with the
// V1 defects fixed and the design reworked:
//
//   V1-001  per-glyph headline fold authored rotation in *degrees* (82.0)
//           while the renderer reads text_animator rotation in *radians*:
//           the tight producer surface exploded to ~248k px and every video
//           export threw std::bad_alloc. V2 authors the fold in radians
//           (kFoldMaxRad) and the test below pins |rotation| <= 3.0.
//   V1-002  Complete and Highlight3D both folded the headline, so two of the
//           three recipes looked identical. V2 Complete uses a soft editorial
//           fade/rise; only Highlight3D (and the LongPhrase center) folds.
//   V1-003  flat hierarchy (kicker/meta/byline/sidebar all same voice).
//           V2 adds an accent kicker bar, a byline+dateline row with share
//           pills, a lead paragraph voice and numbered sidebar picks.
//
// Every plan is a pure function of the spec: complete `chronon.render-plan.v3`
// objects, identical bytes for identical spec values. 1920x1080 @ 30 fps,
// no browser, no Python, no Pillow plate involved.
#ifndef CHRONONTEMPLATE_WEB_PAGE_V2_PACK_HPP
#define CHRONONTEMPLATE_WEB_PAGE_V2_PACK_HPP

#include <nlohmann/json.hpp>
#include <string>
#include <vector>

namespace chronontemplate::web {

    enum class WebPageV2Theme { Light, Dark };
    enum class WebPageV2Recipe { Complete, Highlight3D, LongPhraseBlurred };

    [[nodiscard]] const char* name(WebPageV2Theme theme);
    [[nodiscard]] const char* name(WebPageV2Recipe recipe);

    /// One palette per theme; ink vs paper always inverted.
    struct WebPageV2Palette {
        std::string paper{};
        std::string nav{};
        std::string ink{};
        std::string muted{};
        std::string accent{};
        std::string link{};
        std::string rule{};
        std::string panel{};
        std::string panelLine{};
        std::string highlight{};
        std::string body{};
    };
    [[nodiscard]] WebPageV2Palette paletteFor(WebPageV2Theme theme);

    struct WebPageV2Spec {
        WebPageV2Theme theme{WebPageV2Theme::Light};
        WebPageV2Recipe recipe{WebPageV2Recipe::Highlight3D};

        // chrome
        std::string siteName{"CHRONON NEWS"};
        std::vector<std::string> navLinks{"NBA", "Football", "Business", "Culture"};
        std::string searchHint{"Search"};
        std::string actionLabel{"Subscribe"};

        // masthead
        std::string kicker{"NBA"};
        std::string headlineLineOne{};
        std::string headlineLineTwo{};
        std::string byline{};
        std::string dateline{};
        std::string meta{};

        // article fields (each vector entry is one pre-wrapped rendered line)
        std::string leadLine{};
        std::vector<std::string> bodyLines{};
        std::vector<std::string> pickTitles{};

        // LongPhraseBlurred ingredients
        std::string importantPhrase{};
        std::vector<std::string> contextPhrases{};

        std::string outputName{};
        int durationFrames{240};

        void validate() const;

        [[nodiscard]] std::string planName() const;
        [[nodiscard]] std::string outputStem() const;
    };

    /// All six plans (three recipes · two themes) are pure functions of the
    /// spec: the returned document is a complete `chronon.render-plan.v3`
    /// object, identical bytes for identical spec values.
    [[nodiscard]] nlohmann::json buildWebPageV2Plan(const WebPageV2Spec& spec);

}// namespace chronontemplate::web

#endif//CHRONONTEMPLATE_WEB_PAGE_V2_PACK_HPP
