#include "chronontemplate/elements/WebElements.hpp"

#include "fake_content_host.hpp"
#include "motion_check.hpp"

using namespace chronontemplate;
using namespace chronontemplate::elements;
using chronontemplate_test::FakeContentHost;
using chronontemplate_test::findLayer;
using chrononmotion_test::check;
using chrononmotion_test::section;

namespace {

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
    searchResultSnippetComposes();
    browserChromeComposes();
    screenshotFocusComposes();
    return chrononmotion_test::report();
}
