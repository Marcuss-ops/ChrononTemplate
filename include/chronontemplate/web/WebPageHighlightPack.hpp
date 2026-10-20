// ChrononTemplate — Web Pages Complete + Highlight 3D + Long Phrases Blurred.
//
// A native C++ web-page composition pack. Every pixel is authored as
// render-plan V3 data (text, shape, color layers with camera animation);
// no browser, no Python and no Pillow plate is involved. Chronon3D rasterizes;
// this pack owns the design vocabulary, the layout and the timing.
//
// The three recipes share one grammar: everything that is not the point of
// the shot stays blurred, the important center phrase stays sharp.
//
//   WebPageRecipe::Complete         full animated web page (nav, kicker,
//                                   headline, byline, body, sidebar, footer)
//   WebPageRecipe::Highlight3D      the complete page plus the per-glyph 3D
//                                   headline fold and an accent marker sweep
//   WebPageRecipe::LongPhraseBlurred quiet plate, the long context phrases
//                                   blurred at the edges, the important center
//                                   phrase sharp with an underline wipe
//
// The theme inversion contract: on the light page the text is ink-dark, on the
// dark page it is paper-light — the font color and page color always swap.
#ifndef CHRONONTEMPLATE_WEB_PAGE_HIGHLIGHT_PACK_HPP
#define CHRONONTEMPLATE_WEB_PAGE_HIGHLIGHT_PACK_HPP

#include <nlohmann/json.hpp>
#include <string>
#include <vector>

namespace chronontemplate::web {

    struct WebTextLayout;

    enum class WebPageTheme { Light, Dark };
    enum class WebPageRecipe { Complete, Highlight3D, LongPhraseBlurred };

    [[nodiscard]] const char* name(WebPageTheme theme);
    [[nodiscard]] const char* name(WebPageRecipe recipe);

    /// One palette per theme; ink vs paper always inverted.
    struct WebPagePalette {
        std::string paper{};      ///< the page itself
        std::string nav{};        ///< the top nav bar strip
        std::string ink{};        ///< primary text
        std::string muted{};      ///< secondary text
        std::string accent{};     ///< the site accent (markers, rules, links)
        std::string link{};       ///< visited-style link tint
        std::string rule{};       ///< hairline dividers
        std::string panel{};      ///< sidebar/pill plates
        std::string panelLine{};  ///< panel outline hairlines
        std::string highlight{};  ///< the marker sweep behind key words
        std::string body{};       ///< article copy sits between ink and muted
    };
    [[nodiscard]] WebPagePalette paletteFor(WebPageTheme theme);

    struct WebPageHighlightSpec {
        WebPageTheme theme{WebPageTheme::Light};
        WebPageRecipe recipe{WebPageRecipe::Highlight3D};

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
        std::vector<std::string> bodyLines{};
        std::vector<std::string> pickTitles{};

        // LongPhraseBlurred ingredients
        std::string importantPhrase{};
        std::vector<std::string> contextPhrases{};

        std::string outputName{};  ///< mp4 stem; empty falls back to the plan name
        int durationFrames{240};

        void validate() const;

        [[nodiscard]] std::string planName() const;
        [[nodiscard]] std::string outputStem() const;
    };

    /// All six plans (three recipes · two themes) are pure functions of the
    /// spec: the returned document is a complete `chronon.render-plan.v3`
    /// object, identical bytes for identical spec values.
    [[nodiscard]] nlohmann::json buildWebPageHighlightPlan(const WebPageHighlightSpec& spec);
    /// Exact-layout overload. Uses the shared Chronon-shaped lines and their
    /// measured baselines for the article body instead of caller-authored wraps.
    [[nodiscard]] nlohmann::json buildWebPageHighlightPlan(
        const WebPageHighlightSpec& spec, const WebTextLayout& bodyLayout);

}// namespace chronontemplate::web

#endif//CHRONONTEMPLATE_WEB_PAGE_HIGHLIGHT_PACK_HPP
