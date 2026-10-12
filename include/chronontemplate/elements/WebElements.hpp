#ifndef CHRONONTEMPLATE_WEB_ELEMENTS_HPP
#define CHRONONTEMPLATE_WEB_ELEMENTS_HPP

// Graphics objects 13-18: web preset library (sites, articles, social).
// Data-driven reconstructions, never raw screenshots: every card is laid
// out from fields, and mockups must be labeled as such downstream.

#include "chronontemplate/elements/ElementsCommon.hpp"

#include <string>

namespace chronontemplate::elements {

    /// 13 NewsArticleCard: masthead, kicker, headline, excerpt, byline.
    struct NewsArticleCardSpec {
        std::string masthead{};
        std::string kicker{};
        std::string headline{};
        std::string excerpt{};
        std::string byline{};
        std::string highlight{};
        ElementStyle style{ElementStyle::PaperLight};
        ElementMotion motion{};
        std::string name{"news_article_card"};
    };
    [[nodiscard]] LayerHandle& addNewsArticleCard(TemplateScene& scene,
                                                  const NewsArticleCardSpec& spec);

    /// 14 RedditCommentCard: avatar dot, subreddit, user, score, body.
    struct RedditCommentCardSpec {
        std::string subreddit{};
        std::string username{};
        std::string score{};
        std::string body{};
        std::string highlight{};
        ElementStyle style{ElementStyle::PaperLight};
        ElementMotion motion{};
        std::string name{"reddit_comment_card"};
    };
    [[nodiscard]] LayerHandle& addRedditCommentCard(TemplateScene& scene,
                                                    const RedditCommentCardSpec& spec);

    /// 15 SocialPostCard: author, handle, content, metadata row.
    struct SocialPostCardSpec {
        std::string author{};
        std::string handle{};
        std::string content{};
        std::string metadata{};
        ElementStyle style{ElementStyle::PaperLight};
        ElementMotion motion{};
        std::string name{"social_post_card"};
    };
    [[nodiscard]] LayerHandle& addSocialPostCard(TemplateScene& scene,
                                                 const SocialPostCardSpec& spec);

    /// 16 SearchResultSnippet: favicon dot, URL, title, description.
    struct SearchResultSnippetSpec {
        std::string url{};
        std::string title{};
        std::string description{};
        ElementStyle style{ElementStyle::PaperLight};
        ElementMotion motion{};
        std::string name{"search_result_snippet"};
    };
    [[nodiscard]] LayerHandle& addSearchResultSnippet(TemplateScene& scene,
                                                      const SearchResultSnippetSpec& spec);

    /// 17 BrowserWindowChrome: traffic dots, tab, address bar, viewport.
    struct BrowserWindowChromeSpec {
        std::string tab{};
        std::string url{};
        float width{900.f};
        float height{560.f};
        ElementStyle style{ElementStyle::PaperLight};
        ElementMotion motion{};
        std::string name{"browser_chrome"};
    };
    [[nodiscard]] LayerHandle& addBrowserWindowChrome(TemplateScene& scene,
                                                      const BrowserWindowChromeSpec& spec);

    /// 18 WebScreenshotFocus: dimmed plate, bright region, focus corners.
    struct WebScreenshotFocusSpec {
        float width{900.f};
        float height{560.f};
        float focusX{0.f};
        float focusY{0.f};
        float focusW{320.f};
        float focusH{200.f};
        std::string label{};
        ElementStyle style{ElementStyle::DocumentaryDark};
        ElementMotion motion{};
        std::string name{"screenshot_focus"};
    };
    [[nodiscard]] LayerHandle& addWebScreenshotFocus(TemplateScene& scene,
                                                     const WebScreenshotFocusSpec& spec);

}// namespace chronontemplate::elements

#endif//CHRONONTEMPLATE_WEB_ELEMENTS_HPP
