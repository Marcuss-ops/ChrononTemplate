#ifndef CHRONONTEMPLATE_WEB_ELEMENTS_HPP
#define CHRONONTEMPLATE_WEB_ELEMENTS_HPP

// Graphics objects 13-18: web preset library (sites, articles, social).
// Data-driven reconstructions, never raw screenshots: every card is laid
// out from fields, and mockups must be labeled as such downstream.

#include "chronontemplate/elements/ElementsCommon.hpp"
#include "chronontemplate/web/WebTextLayout.hpp"

#include <cstdint>
#include <string>
#include <vector>

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

    enum class SocialPlatform : std::uint8_t { X, YouTube };
    enum class SocialPostVariant : std::uint8_t { Post, CommunityPost };
    enum class SocialPostTheme : std::uint8_t { Light, Dark };

    struct SocialPostMetrics {
        std::string replies{};
        std::string reposts{};
        std::string likes{};
        std::string views{};
    };

    using SocialPostTextShaper = std::function<std::optional<chronon3d::GlyphRun>(
            std::string_view, const std::string&, float)>;

    /// One shared, content-first contract for platform post presets. Asset
    /// paths remain separate native image layers; body text is shaped and
    /// wrapped through WebTextLayout before any scene layers are authored.
    struct SocialPostSpec {
        SocialPlatform platform{SocialPlatform::X};
        SocialPostVariant variant{SocialPostVariant::Post};
        SocialPostTheme theme{SocialPostTheme::Dark};
        std::string author{};
        std::string handle{};
        std::string avatarPath{};
        bool verified{false};
        std::string timestamp{};
        std::string body{};
        std::vector<std::string> highlights{};
        std::string highlightColor{"#F7D85B"};
        std::string mediaPath{};
        float mediaAspectRatio{16.f / 9.f};
        SocialPostMetrics metrics{};
        std::string bodyFont{"assets/fonts/Inter-Regular.ttf"};
        float bodyFontSize{34.f};
        float bodyLineSpacing{46.f};
        float cardWidth{1180.f};
        int durationFrames{150};
        ElementMotion motion{ElementMotionPreset::None, 0, 24, 6};
        std::string name{"social_post_v1"};
    };

    struct SocialPostLayout {
        float cardWidth{0.f};
        float cardHeight{0.f};
        float padding{0.f};
        float bodyTop{0.f};
        float bodyWidth{0.f};
        float mediaTop{0.f};
        float mediaWidth{0.f};
        float mediaHeight{0.f};
        float footerTop{0.f};
        float authorWidth{0.f};
        float handleWidth{0.f};
        float metricsWidth{0.f};
        web::WebTextLayout body{};
        std::vector<std::vector<web::WebTextSegment>> highlightSegments{};
    };

    /// Resolve the platform card dimensions and semantic highlight spans.
    /// The caller binds `shape` to Chronon3D FontEngine::shape_text.
    [[nodiscard]] SocialPostLayout resolveSocialPostLayout(
            const SocialPostSpec& spec, const SocialPostTextShaper& shape);

    /// Compose an X post or YouTube Community post using editable native
    /// text, shape and image layers. The matching platform/variant pair is
    /// validated; no camera or reveal is added by this static-first preset.
    [[nodiscard]] LayerHandle& addSocialPostV1(
            TemplateScene& scene, const SocialPostSpec& spec,
            const SocialPostTextShaper& shape);

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

    /// BoundedBox: a plain square-corner rectangle with centered editable text.
    struct BoundedBoxSpec {
        std::string text{};
        float width{920.f};
        float height{300.f};
        float fontSize{62.f};
        std::string font{"assets/fonts/Inter-Bold.ttf"};
        std::string fill{"#FFFFFF"};
        std::string textColor{"#17191F"};
        int durationFrames{300};
        ElementMotion motion{};
        std::string name{"bounded_box"};
    };
    [[nodiscard]] LayerHandle& addBoundedBox(TemplateScene& scene,
                                             const BoundedBoxSpec& spec);

}// namespace chronontemplate::elements

#endif//CHRONONTEMPLATE_WEB_ELEMENTS_HPP
