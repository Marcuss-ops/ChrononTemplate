#include "chronontemplate/elements/WebElements.hpp"

#include "fake_content_host.hpp"
#include "motion_check.hpp"

#include <optional>

using namespace chronontemplate;
using namespace chronontemplate::elements;
using chronontemplate_test::FakeContentHost;
using chronontemplate_test::findLayer;
using chrononmotion_test::check;
using chrononmotion_test::section;

namespace {

    SocialPostTextShaper mockSocialShaper() {
        return [](std::string_view text, const std::string&, float size)
                -> std::optional<chronon3d::GlyphRun> {
            chronon3d::GlyphRun run;
            run.ascent = size * 0.78f;
            run.descent = size * 0.22f;
            run.line_height = size * 1.2f;
            float x = 0.f;
            for (std::size_t i = 0; i < text.size();) {
                const auto lead = static_cast<unsigned char>(text[i]);
                const std::size_t bytes = lead < 0x80 ? 1 : (lead & 0xe0) == 0xc0 ? 2 :
                                          (lead & 0xf0) == 0xe0 ? 3 : 4;
                chronon3d::GlyphPosition glyph;
                glyph.glyph_id = 1;
                glyph.x = x;
                glyph.advance_x = size * 0.52f;
                glyph.cluster = static_cast<chronon3d::u32>(i);
                glyph.is_cluster_start = true;
                run.glyphs.push_back(glyph);
                x += glyph.advance_x;
                i += bytes;
            }
            run.width = x;
            return run;
        };
    }

    void submitsThrough(const char* what, TemplateScene& scene, LayerHandle& root) {
        check(findLayer(scene.submit(0), root.id()) &&
                      findLayer(scene.submit(48), root.id()) &&
                      findLayer(scene.submit(149), root.id()),
              what);
        check(scene.validate().empty(), "each web scene validates");
    }

    void newsArticleCardComposes() {
        section("13 news article card");
        FakeContentHost host;
        TemplateScene scene("el_news", 30.f, host, 1920.f, 1080.f);
        NewsArticleCardSpec spec;
        spec.masthead = "ARCHIVE / 2012";
        spec.kicker = "MAPS";
        spec.headline = "An Apple Exit Over Maps";
        spec.excerpt = "Software executive leaves the company";
        spec.byline = "Source, Publication date, Author";
        spec.highlight = "leaves the company";
        LayerHandle& root = addNewsArticleCard(scene, spec);
        root.position(960.f, 540.f);
        submitsThrough("the article root submits across the clip", scene, root);
        check(scene.submit(48).layers.size() == 9, "plate, rule and six fields compose nine layers");
        const auto* rule = host.findShapeRequest("news_article_card_rule");
        check(rule && rule->fillColor == "#C08D4E", "the paper-light accent rule is gold");
        bool threw = false;
        try {
            NewsArticleCardSpec bad;
            bad.masthead = "X";
            addNewsArticleCard(scene, bad);
        } catch (const std::invalid_argument&) { threw = true; }
        check(threw, "a headlineless article fails closed");
    }

    void redditCommentCardComposes() {
        section("14 reddit comment card");
        FakeContentHost host;
        TemplateScene scene("el_reddit", 30.f, host, 1920.f, 1080.f);
        RedditCommentCardSpec spec;
        spec.subreddit = "r/space";
        spec.username = "u/apollo_fan";
        spec.score = "12.4k";
        spec.body = "That launch footage never gets old";
        spec.highlight = "never gets old";
        LayerHandle& root = addRedditCommentCard(scene, spec);
        root.position(960.f, 540.f);
        submitsThrough("the comment root submits across the clip", scene, root);
        const auto* avatar = host.findShapeRequest("reddit_comment_card_avatar");
        check(avatar && avatar->fillColor == "#FF4500", "the avatar keeps reddit orange");
    }

    void socialPostCardComposes() {
        section("15 social post card");
        FakeContentHost host;
        TemplateScene scene("el_social", 30.f, host, 1920.f, 1080.f);
        SocialPostCardSpec spec;
        spec.author = "NASA";
        spec.handle = "@nasa";
        spec.content = "One small step";
        spec.metadata = "2.1M likes";
        LayerHandle& root = addSocialPostCard(scene, spec);
        root.position(960.f, 540.f);
        submitsThrough("the post root submits across the clip", scene, root);
        check(scene.submit(48).layers.size() == 8, "plate, rule, avatar and four fields compose eight layers");
    }

    void socialPostV1UsesShapedNativeLayout() {
        section("social post v1 uses shaped native layout");
        const auto shaper = mockSocialShaper();
        SocialPostSpec x;
        x.platform = SocialPlatform::X;
        x.variant = SocialPostVariant::Post;
        x.theme = SocialPostTheme::Dark;
        x.author = "Example Research";
        x.handle = "@example";
        x.timestamp = "2h";
        x.verified = true;
        x.body = "A careful comparison shows how the new evidence changes the early timeline for this story.";
        x.highlights = {"new evidence changes the early timeline"};
        x.avatarPath = "assets/images/people_sample_portrait_b.png";
        x.mediaPath = "assets/images/investigative_journalist_hero.jpg";
        x.metrics = {.replies = "128", .reposts = "430", .likes = "2.7K", .views = "83K"};
        const auto layout = resolveSocialPostLayout(x, shaper);
        check(layout.body.lines.size() > 1, "long post body wraps into shaped lines");
        check(!layout.highlightSegments.empty() &&
                      layout.highlightSegments.front().size() >= 2,
              "multiline semantic phrase resolves to shaped highlight geometry");
        check(layout.mediaHeight > 0.f && layout.cardHeight > layout.mediaHeight,
              "attached media contributes to the adaptive card height");

        FakeContentHost host;
        TemplateScene scene("el_social_x_v1", 30.f, host, 1920.f, 1080.f);
        LayerHandle& root = addSocialPostV1(scene, x, shaper);
        root.position(960.f, 540.f);
        submitsThrough("native X post submits across its duration", scene, root);
        check(findLayer(scene.submit(0), root.id()) != nullptr,
              "X post is a native scene group");
        const auto* card = host.findShapeRequest("social_post_v1_card");
        check(card && card->fillColor == "#000000" && card->strokeColor == "#2F3336",
              "X dark theme uses its near-black surface and subtle border");
        check(host.lastImageRequest().path == x.mediaPath,
              "attached image remains an independent native image layer");

        SocialPostSpec youtube;
        youtube.platform = SocialPlatform::YouTube;
        youtube.variant = SocialPostVariant::CommunityPost;
        youtube.theme = SocialPostTheme::Light;
        youtube.author = "Chronon Lab";
        youtube.handle = "@chrononlab";
        youtube.timestamp = "5 hours ago";
        youtube.body = "The complete report is now available, with the source links and a short behind-the-scenes note.";
        youtube.metrics = {.replies = "86", .likes = "1.2K"};
        FakeContentHost ytHost;
        TemplateScene ytScene("el_social_youtube_v1", 30.f, ytHost, 1920.f, 1080.f);
        LayerHandle& ytRoot = addSocialPostV1(ytScene, youtube, shaper);
        ytRoot.position(960.f, 540.f);
        submitsThrough("YouTube Community post submits across its duration", ytScene, ytRoot);
        const auto* ytCard = ytHost.findShapeRequest("social_post_v1_card");
        check(ytCard && ytCard->fillColor == "#FFFFFF",
              "YouTube light theme uses a white platform card");

        std::string longBody;
        for (int i = 0; i < 200; ++i) {
            if (!longBody.empty()) longBody.push_back(' ');
            longBody += (i % 2 == 0) ? "evidence" : "timeline";
        }
        SocialPostSpec longPost;
        longPost.author = "Example";
        longPost.body = longBody;
        longPost.cardWidth = 700.f;
        const auto longLayout = resolveSocialPostLayout(longPost, shaper);
        std::string reconstructed;
        for (const auto& line : longLayout.body.lines) {
            if (!reconstructed.empty()) reconstructed.push_back(' ');
            reconstructed += line.text;
            check(line.width <= longLayout.bodyWidth,
                  "every long-post line fits its measured column");
        }
        check(reconstructed == longBody && longLayout.body.lines.size() > 15,
              "a 200-word post wraps without losing text and expands its card");

        bool badVariantRejected = false;
        try {
            SocialPostSpec invalid = youtube;
            invalid.variant = SocialPostVariant::Post;
            (void)resolveSocialPostLayout(invalid, shaper);
        } catch (const std::invalid_argument&) { badVariantRejected = true; }
        check(badVariantRejected, "platform and post variant mismatch fails closed");

        bool missingHighlightRejected = false;
        try {
            SocialPostSpec invalid = x;
            invalid.highlights = {"phrase not present"};
            (void)resolveSocialPostLayout(invalid, shaper);
        } catch (const std::invalid_argument&) { missingHighlightRejected = true; }
        check(missingHighlightRejected, "highlight phrase must refer to actual body text");
    }

    void searchResultSnippetComposes() {
        section("16 search result snippet");
        FakeContentHost host;
        TemplateScene scene("el_search", 30.f, host, 1920.f, 1080.f);
        SearchResultSnippetSpec spec;
        spec.url = "nasa.gov/apollo";
        spec.title = "Apollo 11 Mission Overview";
        spec.description = "The first crewed Moon landing";
        LayerHandle& root = addSearchResultSnippet(scene, spec);
        root.position(960.f, 540.f);
        submitsThrough("the snippet root submits across the clip", scene, root);
        check(scene.submit(48).layers.size() == 5, "favicon plus three lines compose five layers");
    }

    void browserChromeComposes() {
        section("17 browser window chrome");
        FakeContentHost host;
        TemplateScene scene("el_browser", 30.f, host, 1920.f, 1080.f);
        BrowserWindowChromeSpec spec;
        spec.tab = "Apollo 11";
        spec.url = "nasa.gov/apollo";
        LayerHandle& root = addBrowserWindowChrome(scene, spec);
        root.position(960.f, 540.f);
        submitsThrough("the chrome root submits across the clip", scene, root);
        const auto* dot = host.findShapeRequest("browser_chrome_dot_0");
        check(dot && dot->fillColor == "#E03B2F", "traffic dots start signal red");
        const auto* viewport = host.findShapeRequest("browser_chrome_viewport");
        check(viewport != nullptr, "the viewport plate exists");
    }

    void screenshotFocusComposes() {
        section("18 screenshot focus");
        FakeContentHost host;
        TemplateScene scene("el_focus", 30.f, host, 1920.f, 1080.f);
        WebScreenshotFocusSpec spec;
        spec.label = "FIGURE 1";
        LayerHandle& root = addWebScreenshotFocus(scene, spec);
        root.position(960.f, 540.f);
        submitsThrough("the focus root submits across the clip", scene, root);
        check(scene.submit(48).layers.size() == 8, "plate, region, corners and label compose eight layers");
        const auto* corner = host.findShapeRequest("screenshot_focus_focus_tl");
        check(corner && corner->fillColor == "#E8B84A", "focus corners carry the accent");
    }

}// namespace

int main() {
    newsArticleCardComposes();
    redditCommentCardComposes();
    socialPostCardComposes();
    socialPostV1UsesShapedNativeLayout();
    searchResultSnippetComposes();
    browserChromeComposes();
    screenshotFocusComposes();
    return chrononmotion_test::report();
}
