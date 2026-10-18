#include "chronontemplate/elements/WebElements.hpp"

namespace chronontemplate::elements {

    namespace {
        // Shared card plate: paper body with a hairline top accent.
        LayerHandle& cardPlate(TemplateScene& scene, const std::string& name,
                               float w, float h, const ElementPalette& pal) {
            LayerHandle& root = scene.group(name);
            root.alive(0, 150);
            LayerHandle& body = scene.shape(ShapeSpec{
                    .size = chrononmotion::Vector2(w, h), .fillColor = pal.paper,
                    .name = name + "_body", .cornerRadius = 18.f});
            body.parent(root.id());
            body.position(0.f, 0.f);
            body.alive(0, 150);
            LayerHandle& rule = addBar(scene, root.id(), name + "_rule",
                                       w, 6.f, 0.f, -h * 0.5f + 3.f, pal.accent, 3.f);
            (void) rule;
            return root;
        }
    }

    LayerHandle& addNewsArticleCard(TemplateScene& scene, const NewsArticleCardSpec& spec) {
        require(!spec.masthead.empty(), "addNewsArticleCard: a masthead is required");
        require(!spec.headline.empty(), "addNewsArticleCard: a headline is required");
        const ElementPalette pal = paletteFor(spec.style);
        LayerHandle& root = cardPlate(scene, spec.name, 860.f, 520.f, pal);
        int slot = 0;
        const auto line = [&](const std::string& tag, const std::string& text,
                              float size, const std::string& color, float y) {
            LayerHandle& label = addText(scene, root.id(), spec.name + "_" + tag,
                                         text, size, color, -380.f, y);
            applyElementMotion(label, spec.motion, scene.fps(), slot++);
        };
        line("masthead", spec.masthead, 30.f, pal.muted, -210.f);
        if (!spec.kicker.empty()) line("kicker", spec.kicker, 30.f, pal.accent, -160.f);
        line("headline", spec.headline, 52.f, pal.ink, -80.f);
        if (!spec.excerpt.empty()) line("excerpt", spec.excerpt, 30.f, pal.muted, 30.f);
        if (!spec.byline.empty()) line("byline", spec.byline, 28.f, pal.muted, 200.f);
        if (!spec.highlight.empty()) {
            LayerHandle& mark = scene.text(TextSpec{
                    .text = spec.highlight, .fontSize = 30.f, .color = "#101014",
                    .name = spec.name + "_highlight",
                    .background = TextBackgroundStyle{.color = "#FFE45E", .opacity = 0.92f,
                                                      .radius = 6.f,
                                                      .padding = chrononmotion::Vector2(12.f, 6.f)}});
            mark.parent(root.id());
            mark.position(-380.f, 110.f);
            mark.alive(0, 150);
            applyElementMotion(mark, spec.motion, scene.fps(), slot++);
        }
        return root;
    }

    LayerHandle& addRedditCommentCard(TemplateScene& scene, const RedditCommentCardSpec& spec) {
        require(!spec.subreddit.empty(), "addRedditCommentCard: a subreddit is required");
        require(!spec.username.empty(), "addRedditCommentCard: a username is required");
        require(!spec.body.empty(), "addRedditCommentCard: a body is required");
        const ElementPalette pal = paletteFor(spec.style);
        LayerHandle& root = cardPlate(scene, spec.name, 820.f, 420.f, pal);
        LayerHandle& avatar = scene.shape(ShapeSpec{
                .size = chrononmotion::Vector2(64.f, 64.f), .fillColor = "#FF4500",
                .name = spec.name + "_avatar", .cornerRadius = 32.f,
                .geometry = ShapeGeometry::Ellipse});
        avatar.parent(root.id());
        avatar.position(-350.f, -140.f);
        avatar.alive(0, 150);
        applyElementMotion(avatar, spec.motion, scene.fps());
        int slot = 1;
        const auto line = [&](const std::string& tag, const std::string& text,
                              float size, const std::string& color, float x, float y) {
            LayerHandle& label = addText(scene, root.id(), spec.name + "_" + tag,
                                         text, size, color, x, y);
            applyElementMotion(label, spec.motion, scene.fps(), slot++);
        };
        line("subreddit", spec.subreddit, 30.f, pal.ink, -300.f, -160.f);
        line("username", spec.username, 28.f, pal.muted, -300.f, -118.f);
        line("body", spec.body, 32.f, pal.ink, -300.f, -20.f);
        if (!spec.score.empty()) line("score", spec.score, 30.f, "#FF4500", -300.f, 150.f);
        if (!spec.highlight.empty()) line("highlight", spec.highlight, 30.f, pal.accent, -300.f, 90.f);
        return root;
    }

    LayerHandle& addSocialPostCard(TemplateScene& scene, const SocialPostCardSpec& spec) {
        require(!spec.author.empty(), "addSocialPostCard: an author is required");
        require(!spec.content.empty(), "addSocialPostCard: content is required");
        const ElementPalette pal = paletteFor(spec.style);
        LayerHandle& root = cardPlate(scene, spec.name, 820.f, 440.f, pal);
        LayerHandle& avatar = scene.shape(ShapeSpec{
                .size = chrononmotion::Vector2(72.f, 72.f), .fillColor = pal.accent,
                .name = spec.name + "_avatar", .cornerRadius = 36.f,
                .geometry = ShapeGeometry::Ellipse});
        avatar.parent(root.id());
        avatar.position(-340.f, -140.f);
        avatar.alive(0, 150);
        applyElementMotion(avatar, spec.motion, scene.fps());
        int slot = 1;
        const auto line = [&](const std::string& tag, const std::string& text,
                              float size, const std::string& color, float x, float y) {
            LayerHandle& label = addText(scene, root.id(), spec.name + "_" + tag,
                                         text, size, color, x, y);
            applyElementMotion(label, spec.motion, scene.fps(), slot++);
        };
        line("author", spec.author, 34.f, pal.ink, -285.f, -160.f);
        if (!spec.handle.empty()) line("handle", spec.handle, 28.f, pal.muted, -285.f, -115.f);
        line("content", spec.content, 34.f, pal.ink, -285.f, -10.f);
        if (!spec.metadata.empty()) line("metadata", spec.metadata, 28.f, pal.muted, -285.f, 150.f);
        return root;
    }

    LayerHandle& addSearchResultSnippet(TemplateScene& scene, const SearchResultSnippetSpec& spec) {
        require(!spec.url.empty(), "addSearchResultSnippet: a URL is required");
        require(!spec.title.empty(), "addSearchResultSnippet: a title is required");
        const ElementPalette pal = paletteFor(spec.style);
        LayerHandle& root = scene.group(spec.name);
        root.alive(0, 150);
        LayerHandle& favicon = scene.shape(ShapeSpec{
                .size = chrononmotion::Vector2(40.f, 40.f), .fillColor = pal.accent,
                .name = spec.name + "_favicon", .cornerRadius = 20.f,
                .geometry = ShapeGeometry::Ellipse});
        favicon.parent(root.id());
        favicon.position(-400.f, -60.f);
        favicon.alive(0, 150);
        applyElementMotion(favicon, spec.motion, scene.fps());
        int slot = 1;
        const auto line = [&](const std::string& tag, const std::string& text,
                              float size, const std::string& color, float y) {
            LayerHandle& label = addText(scene, root.id(), spec.name + "_" + tag,
                                         text, size, color, -350.f, y);
            applyElementMotion(label, spec.motion, scene.fps(), slot++);
        };
        line("url", spec.url, 28.f, pal.muted, -70.f);
        line("title", spec.title, 46.f, "#1A56DB", -10.f);
        if (!spec.description.empty()) line("description", spec.description, 30.f, pal.muted, 60.f);
        return root;
    }

    LayerHandle& addBrowserWindowChrome(TemplateScene& scene, const BrowserWindowChromeSpec& spec) {
        require(!spec.url.empty(), "addBrowserWindowChrome: a URL is required");
        require(spec.width > 0.f && spec.height > 0.f,
                "addBrowserWindowChrome: positive dimensions are required");
        const ElementPalette pal = paletteFor(spec.style);
        LayerHandle& root = scene.group(spec.name);
        root.alive(0, 150);
        LayerHandle& frame = scene.shape(ShapeSpec{
                .size = chrononmotion::Vector2(spec.width, spec.height),
                .fillColor = pal.paper, .name = spec.name + "_frame", .cornerRadius = 18.f});
        frame.parent(root.id());
        frame.position(0.f, 0.f);
        frame.alive(0, 150);
        applyElementMotion(frame, spec.motion, scene.fps());
        const char* dots[] = {"#E03B2F", "#E8B84A", "#3FB950"};
        for (int i = 0; i < 3; ++i) {
            LayerHandle& dot = scene.shape(ShapeSpec{
                    .size = chrononmotion::Vector2(22.f, 22.f), .fillColor = dots[i],
                    .name = spec.name + "_dot_" + std::to_string(i), .cornerRadius = 11.f,
                    .geometry = ShapeGeometry::Ellipse});
            dot.parent(root.id());
            dot.position(-spec.width * 0.5f + 40.f + i * 36.f, -spec.height * 0.5f + 34.f);
            dot.alive(0, 150);
            applyElementMotion(dot, spec.motion, scene.fps(), i + 1);
        }
        LayerHandle& address = scene.shape(ShapeSpec{
                .size = chrononmotion::Vector2(spec.width * 0.62f, 44.f),
                .fillColor = pal.line, .name = spec.name + "_address", .cornerRadius = 22.f});
        address.parent(root.id());
        address.position(40.f, -spec.height * 0.5f + 34.f);
        address.alive(0, 150);
        applyElementMotion(address, spec.motion, scene.fps(), 2);
        LayerHandle& url = addText(scene, root.id(), spec.name + "_url",
                                   spec.url, 26.f, pal.muted, -spec.width * 0.5f + 90.f,
                                   -spec.height * 0.5f + 26.f);
        applyElementMotion(url, spec.motion, scene.fps(), 3);
        if (!spec.tab.empty()) {
            LayerHandle& tab = addText(scene, root.id(), spec.name + "_tab",
                                       spec.tab, 28.f, pal.ink, -spec.width * 0.5f + 170.f,
                                       -spec.height * 0.5f + 80.f);
            applyElementMotion(tab, spec.motion, scene.fps(), 4);
        }
        LayerHandle& viewport = addBar(scene, root.id(), spec.name + "_viewport",
                                       spec.width - 40.f, spec.height - 150.f, 0.f, 45.f,
                                       pal.line, 12.f);
        applyElementMotion(viewport, spec.motion, scene.fps(), 3);
        return root;
    }

    LayerHandle& addWebScreenshotFocus(TemplateScene& scene, const WebScreenshotFocusSpec& spec) {
        require(spec.width > 0.f && spec.height > 0.f,
                "addWebScreenshotFocus: positive dimensions are required");
        require(spec.focusW > 0.f && spec.focusH > 0.f,
                "addWebScreenshotFocus: a positive focus region is required");
        const ElementPalette pal = paletteFor(spec.style);
        LayerHandle& root = scene.group(spec.name);
        root.alive(0, 150);
        LayerHandle& plate = scene.shape(ShapeSpec{
                .size = chrononmotion::Vector2(spec.width, spec.height),
                .fillColor = "#1A1A20", .name = spec.name + "_plate", .cornerRadius = 14.f});
        plate.parent(root.id());
        plate.position(0.f, 0.f);
        plate.alive(0, 150);
        applyElementMotion(plate, spec.motion, scene.fps());
        // Bright region + four focus corners + optional lens ring.
        LayerHandle& region = scene.shape(ShapeSpec{
                .size = chrononmotion::Vector2(spec.focusW, spec.focusH),
                .fillColor = "#2E2E38", .name = spec.name + "_region", .cornerRadius = 10.f});
        region.parent(root.id());
        region.position(spec.focusX, spec.focusY);
        region.alive(0, 150);
        applyElementMotion(region, spec.motion, scene.fps(), 1);
        const float hx = spec.focusW * 0.5f;
        const float hy = spec.focusH * 0.5f;
        const char* tags[] = {"tl", "tr", "bl", "br"};
        for (int i = 0; i < 4; ++i) {
            const float cx = spec.focusX + (i % 2 == 0 ? -hx : hx);
            const float cy = spec.focusY + (i < 2 ? -hy : hy);
            LayerHandle& corner = addBar(scene, root.id(),
                                         spec.name + "_focus_" + tags[i],
                                         44.f, 6.f, cx, cy, pal.accent, 3.f);
            applyElementMotion(corner, spec.motion, scene.fps(), i + 2);
        }
        if (!spec.label.empty()) {
            LayerHandle& label = addText(scene, root.id(), spec.name + "_label",
                                         spec.label, 30.f, pal.accent,
                                         spec.focusX, spec.focusY + hy + 40.f);
            applyElementMotion(label, spec.motion, scene.fps(), 6);
        }
        return root;
    }

    LayerHandle& addBoundedBox(TemplateScene& scene, const BoundedBoxSpec& spec) {
        require(!spec.text.empty(), "addBoundedBox: text is required");
        require(spec.width > 0.f && spec.height > 0.f && spec.fontSize > 0.f,
                "addBoundedBox: width, height and font size must be positive");
        require(!spec.fill.empty() && !spec.textColor.empty(),
                "addBoundedBox: fill and text color are required");
        require(!spec.font.empty(), "addBoundedBox: font is required");
        require(spec.durationFrames > 0, "addBoundedBox: duration must be positive");

        LayerHandle& root = scene.group(spec.name);
        root.alive(0, spec.durationFrames - 1);

        LayerHandle& plate = scene.shape(ShapeSpec{
                .size = chrononmotion::Vector2(spec.width, spec.height),
                .fillColor = spec.fill,
                .name = spec.name + "_plate"});
        plate.parent(root.id());
        plate.position(0.f, 0.f);
        plate.alive(0, spec.durationFrames - 1);
        applyElementMotion(plate, spec.motion, scene.fps());

        LayerHandle& label = scene.text(TextSpec{
                .text = spec.text, .font = spec.font, .fontSize = spec.fontSize,
                .color = spec.textColor, .name = spec.name + "_text"});
        label.parent(root.id());
        label.position(0.f, 0.f);
        label.alive(0, spec.durationFrames - 1);
        applyElementMotion(label, spec.motion, scene.fps(), 1);
        return root;
    }

}// namespace chronontemplate::elements
