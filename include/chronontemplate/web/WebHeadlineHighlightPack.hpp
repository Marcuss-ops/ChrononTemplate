// ChrononTemplate — Web Headline Highlight pack.
//
// Native C++ recreations of six editorial highlighter looks seen in the
// supplied reference frames: a statement page whose headline phrase sits under
// a coral marker, a marker sweep over an italic serif phrase on lined paper,
// a stepped yellow highlight over a serif headline, a breaking-news page with
// a red kicker bar and a ticker tape, a live-blog feed whose latest entry is
// marked, and a centered quote card with a coral key-phrase highlight. Every
// pixel is authored as render-plan V3 data (text and shape layers with camera
// animation); no browser, no Python and no Pillow plate is involved. Chronon3D
// rasterizes; this pack owns the design vocabulary, the layout and the timing.
//
// The six recipes share one grammar: the highlighter is the point of the
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
//   HeadlineHighlightRecipe::BreakingTicker  dark breaking-news page (red
//                                            kicker bar, stepped headline
//                                            highlight, sliding ticker tape)
//   HeadlineHighlightRecipe::LiveBlogFeed    live-blog feed (LIVE dot,
//                                            timestamped entries, marker band
//                                            on the latest entry)
//   HeadlineHighlightRecipe::QuoteCard       centered quote card (serif
//                                            italic quote, coral key-phrase
//                                            highlight, attribution)
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
        SteppedHighlight,
        BreakingTicker,
        LiveBlogFeed,
        QuoteCard
    };

    [[nodiscard]] const char* name(HeadlineHighlightRecipe recipe);

    struct WebHeadlineHighlightSpec {
        HeadlineHighlightRecipe recipe{HeadlineHighlightRecipe::StatementPage};

        // shared copy
        std::string kicker{};                    ///< "Announcements", "AI • META", ...
        std::vector<std::string> headlineLines{};///< rendered headline lines (1..4)
        std::string highlightText{};             ///< phrase covered by the highlighter
        std::string dateline{};                  ///< centered date under the headline
        std::vector<std::string> bodyLines{};    ///< serif body copy (1..8 lines),
                                                 ///< or live-blog entries (2..4)

        // statement-page chrome
        std::string siteName{"CHRONON NEWS"};
        std::vector<std::string> navLinks{"Research", "Policy", "Pronouncements"};

        // marker-sweep phrase (recipe two); italic serif on lined paper
        std::string phrase{};                    ///< the marked phrase, e.g. "one company"

        // breaking-ticker tape (recipe four); one muted line sliding in
        std::string tickerText{};                ///< e.g. "Markets rally as ..."

        // live-blog feed (recipe five); bodyLines are the entry texts and
        // entryTimes carries one short timestamp per entry, in order
        std::vector<std::string> entryTimes{};

        // quote card (recipe six); centered serif italic lines plus credit
        std::vector<std::string> quoteLines{};   ///< the quote, 1..3 lines
        std::string attribution{};               ///< e.g. "Ada Lovelace"
        std::string source{};                    ///< e.g. "The Interview, Jun 2026"

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
