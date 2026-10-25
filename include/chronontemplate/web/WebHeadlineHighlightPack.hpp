// ChrononTemplate — Web Headline Highlight pack.
//
// Native C++ recreations of three editorial highlighter looks seen in the
// supplied reference frames: a statement page whose headline phrase sits under
// a coral marker, a marker sweep over an italic serif phrase on lined paper,
// and a stepped yellow highlight over a serif headline. Every pixel is
// authored as render-plan V3 data (text and shape layers with camera
// animation); no browser, no Python and no Pillow plate is involved. Chronon3D
// rasterizes; this pack owns the design vocabulary, the layout and the timing.
//
// The three recipes share one grammar: the highlighter is the point of the
// shot and the supporting copy is quieter around it.
//
//   HeadlineHighlightRecipe::StatementPage   full statement page (nav, kicker,
//                                            highlighted headline phrase,
//                                            dateline, serif body)
//   HeadlineHighlightRecipe::MarkerSweep     lined paper, italic serif phrase,
//                                            yellow marker band sweeping in
//   HeadlineHighlightRecipe::SteppedHighlight serif headline with stepped
//                                            yellow blocks behind the lead
//                                            lines and a red-bullet kicker
//
// The highlight geometry is estimated from the authored copy with the pack's
// deterministic width table: blocks are composition intent, not glyph-exact
// coverage. Where a reference band is hand-drawn (the marker sweep's slanted
// ends) the pack approximates it with stacked rectangles rather than claiming
// optical-identical ink.
#ifndef CHRONONTEMPLATE_WEB_HEADLINE_HIGHLIGHT_PACK_HPP
#define CHRONONTEMPLATE_WEB_HEADLINE_HIGHLIGHT_PACK_HPP

#include <nlohmann/json.hpp>
#include <string>
#include <vector>

namespace chronontemplate::web {

    enum class HeadlineHighlightRecipe : unsigned char {
        StatementPage,
        MarkerSweep,
        SteppedHighlight
    };

    [[nodiscard]] const char* name(HeadlineHighlightRecipe recipe);

    struct WebHeadlineHighlightSpec {
        HeadlineHighlightRecipe recipe{HeadlineHighlightRecipe::StatementPage};

        // shared copy
        std::string kicker{};                    ///< "Announcements", "AI • META", ...
        std::vector<std::string> headlineLines{};///< rendered headline lines (1..4)
        std::string highlightText{};             ///< phrase covered by the highlighter
        std::string dateline{};                  ///< centered date under the headline
        std::vector<std::string> bodyLines{};    ///< serif body copy (1..8 lines)

        // statement-page chrome
        std::string siteName{"CHRONON NEWS"};
        std::vector<std::string> navLinks{"Research", "Policy", "Pronouncements"};

        // marker-sweep phrase (recipe two); italic serif on lined paper
        std::string phrase{};                    ///< the marked phrase, e.g. "one company"

        // palette overrides; empty keeps the recipe's authored colors
        std::string paperColor{};
        std::string inkColor{};
        std::string highlightColor{};

        std::string outputName{};  ///< mp4 stem; empty falls back to the plan name
        int durationFrames{180};

        void validate() const;

        [[nodiscard]] std::string planName() const;
        [[nodiscard]] std::string outputStem() const;
    };

    /// Pure function of the spec: the returned document is a complete
    /// `chronon.render-plan.v3` object, identical bytes for identical values.
    [[nodiscard]] nlohmann::json buildWebHeadlineHighlightPlan(const WebHeadlineHighlightSpec& spec);

}// namespace chronontemplate::web

#endif//CHRONONTEMPLATE_WEB_HEADLINE_HIGHLIGHT_PACK_HPP
