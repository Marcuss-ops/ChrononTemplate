#include "chronontemplate/elements/WebElements.hpp"

#include <algorithm>
#include <cmath>
#include <optional>
#include <sstream>
#include <utility>

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

    namespace {
        struct SocialPalette {
            const char* canvas;
            const char* card;
            const char* ink;
            const char* muted;
            const char* line;
            const char* accent;
        };

        SocialPalette socialPalette(const SocialPostSpec& spec) {
            if (spec.platform == SocialPlatform::X && spec.theme == SocialPostTheme::Dark) {
                return {"#000000", "#000000", "#E7E9EA", "#71767B",
                        "#2F3336", "#1D9BF0"};
            }
            if (spec.platform == SocialPlatform::X) {
                return {"#FFFFFF", "#FFFFFF", "#0F1419", "#536471",
                        "#EFF3F4", "#1D9BF0"};
            }
            if (spec.theme == SocialPostTheme::Dark) {
                return {"#0F0F0F", "#212121", "#F1F1F1", "#AAAAAA",
                        "#3F3F3F", "#3EA6FF"};
            }
            return {"#F2F2F2", "#FFFFFF", "#0F0F0F", "#606060",
                    "#E5E5E5", "#065FD4"};
        }

        std::string metricText(const SocialPostSpec& spec) {
            std::ostringstream out;
            bool first = true;
            auto add = [&](const std::string& value, const char* label) {
                if (value.empty()) return;
                if (!first) out << "   ·   ";
                out << value << ' ' << label;
                first = false;
            };
            if (spec.platform == SocialPlatform::X) {
                add(spec.metrics.replies, "replies");
                add(spec.metrics.reposts, "reposts");
                add(spec.metrics.likes, "likes");
            } else {
                add(spec.metrics.likes, "likes");
                add(spec.metrics.replies, "comments");
            }
            return out.str();
        }

        float shapedWidth(const SocialPostTextShaper& shape, const std::string& value,
                          const std::string& font, float size) {
            if (value.empty()) return 0.f;
            const auto run = shape(value, font, size);
            if (!run || !std::isfinite(run->width) || run->width < 0.f)
                throw std::runtime_error("social post text shaper returned invalid metrics");
            return run->width;
        }

        LayerHandle& socialText(TemplateScene& scene, unsigned parent,
                                const std::string& name, const std::string& text,
                                const std::string& font, float size,
                                const std::string& color, float x, float y,
                                int durationFrames, const ElementMotion& motion,
                                float fps, int stagger = 0) {
            LayerHandle& layer = scene.text(TextSpec{
                    .text = text, .font = font, .fontSize = size, .color = color,
                    .name = name});
            layer.parent(parent).position(x, y).alive(0, durationFrames - 1);
            applyElementMotion(layer, motion, fps, stagger);
            return layer;
        }

        LayerHandle& socialShape(TemplateScene& scene, unsigned parent,
                                 const std::string& name, float width, float height,
                                 const std::string& fill, float x, float y,
                                 int durationFrames, const ElementMotion& motion,
                                 float fps, float radius = 0.f,
                                 const std::string& stroke = {}, float strokeWidth = 0.f) {
            LayerHandle& layer = scene.shape(ShapeSpec{
                    .size = chrononmotion::Vector2(width, height),
                    .fillColor = fill, .name = name, .cornerRadius = radius,
                    .fillEnabled = !fill.empty(), .strokeColor = stroke,
                    .strokeWidth = strokeWidth});
            layer.parent(parent).position(x, y).alive(0, durationFrames - 1);
            applyElementMotion(layer, motion, fps);
            return layer;
        }

        void validateSocialPost(const SocialPostSpec& spec,
                                const SocialPostTextShaper& shape) {
            require(!spec.author.empty(), "addSocialPostV1: an author is required");
            require(!spec.body.empty(), "addSocialPostV1: body text is required");
            require(static_cast<bool>(shape), "addSocialPostV1: a Chronon text shaper is required");
            require(!spec.bodyFont.empty(), "addSocialPostV1: body font is required");
            require(std::isfinite(spec.cardWidth) && spec.cardWidth >= 700.f,
                    "addSocialPostV1: card width must be at least 700 pixels");
            require(std::isfinite(spec.bodyFontSize) && spec.bodyFontSize > 0.f &&
                    std::isfinite(spec.bodyLineSpacing) && spec.bodyLineSpacing > 0.f,
                    "addSocialPostV1: body font metrics must be positive");
            require(std::isfinite(spec.mediaAspectRatio) && spec.mediaAspectRatio > 0.f,
                    "addSocialPostV1: media aspect ratio must be positive");
            require(spec.durationFrames > 0, "addSocialPostV1: duration must be positive");
            require(!spec.name.empty(), "addSocialPostV1: layer name is required");
            require(spec.platform == SocialPlatform::X
                            ? spec.variant == SocialPostVariant::Post
                            : spec.variant == SocialPostVariant::CommunityPost,
                    "addSocialPostV1: platform and variant do not match");
        }
    }

    SocialPostLayout resolveSocialPostLayout(const SocialPostSpec& spec,
                                             const SocialPostTextShaper& shape) {
        validateSocialPost(spec, shape);
        constexpr float kPadding = 46.f;
        constexpr float kAvatarSize = 82.f;
        constexpr float kHeaderToBody = 30.f;
        constexpr float kBodyToMedia = 24.f;
        constexpr float kMediaToFooter = 30.f;
        constexpr float kFooterHeight = 82.f;
        constexpr float kBottomPadding = 40.f;
        const float bodyWidth = spec.cardWidth - 2.f * kPadding;
        const float bodyTop = kPadding + kAvatarSize + kHeaderToBody;
        const auto bodyShape = [&](std::string_view text) {
            return shape(text, spec.bodyFont, spec.bodyFontSize);
        };

        SocialPostLayout layout;
        layout.cardWidth = spec.cardWidth;
        layout.padding = kPadding;
        layout.bodyTop = bodyTop;
        layout.bodyWidth = bodyWidth;
        layout.body = web::layoutWebText(spec.body, 0.f, 0.f, bodyWidth,
                spec.bodyLineSpacing, spec.bodyFont, spec.bodyFontSize, bodyShape);
        layout.authorWidth = shapedWidth(shape, spec.author,
                "assets/fonts/Inter-Bold.ttf", 31.f);
        const std::string identity = (spec.handle.empty() ? "" : spec.handle) +
                (spec.timestamp.empty() || spec.handle.empty() ? "" : "  ·  ") + spec.timestamp;
        layout.handleWidth = shapedWidth(shape, identity,
                "assets/fonts/Inter-Regular.ttf", 24.f);
        const std::string interactions = metricText(spec);
        layout.metricsWidth = shapedWidth(shape, interactions,
                "assets/fonts/Inter-Regular.ttf", 22.f);
        layout.mediaWidth = bodyWidth;
        layout.mediaHeight = spec.mediaPath.empty() ? 0.f : bodyWidth / spec.mediaAspectRatio;
        layout.mediaTop = bodyTop + layout.body.height +
                (spec.mediaPath.empty() ? 0.f : kBodyToMedia);
        layout.footerTop = layout.mediaTop + layout.mediaHeight +
                (spec.mediaPath.empty() ? 26.f : kMediaToFooter);
        layout.cardHeight = layout.footerTop + kFooterHeight + kBottomPadding;
        for (const auto& phrase : spec.highlights) {
            require(!phrase.empty(), "addSocialPostV1: highlight phrases must be non-empty");
            const auto begin = spec.body.find(phrase);
            require(begin != std::string::npos,
                    "addSocialPostV1: every highlight must occur in the body text");
            layout.highlightSegments.push_back(web::resolveWebTextSpan(
                    layout.body, begin, begin + phrase.size()));
        }
        return layout;
    }

    LayerHandle& addSocialPostV1(TemplateScene& scene, const SocialPostSpec& spec,
                                 const SocialPostTextShaper& shape) {
        const SocialPostLayout layout = resolveSocialPostLayout(spec, shape);
        const SocialPalette colors = socialPalette(spec);
        const auto canvas = scene.canvas();
        LayerHandle& root = scene.group(spec.name);
        root.position(canvas.x * 0.5f, canvas.y * 0.5f)
            .alive(0, spec.durationFrames - 1);
        applyElementMotion(root, spec.motion, scene.fps());

        const unsigned parent = root.id();
        const float left = -layout.cardWidth * 0.5f;
        const float top = -layout.cardHeight * 0.5f;
        const float cardCenterY = 0.f;
        socialShape(scene, parent, spec.name + "_canvas",
                canvas.x, canvas.y, colors.canvas, 0.f, cardCenterY,
                spec.durationFrames, spec.motion, scene.fps());
        socialShape(scene, parent, spec.name + "_card",
                layout.cardWidth, layout.cardHeight, colors.card, 0.f, 0.f,
                spec.durationFrames, spec.motion, scene.fps(), 22.f,
                colors.line, 1.f);

        const float avatarLeft = left + layout.padding;
        const float avatarTop = top + layout.padding;
        if (!spec.avatarPath.empty()) {
            LayerHandle& avatar = scene.image(ImageSpec{
                    .path = spec.avatarPath, .name = spec.name + "_avatar",
                    .frame = ImageFrameStyle{.cornerRadius = 41.f},
                    .fit = ImageFitMode::Cover,
                    .targetSize = chrononmotion::Vector2(82.f, 82.f)});
            avatar.parent(parent).position(avatarLeft + 41.f, avatarTop + 41.f)
                  .alive(0, spec.durationFrames - 1);
            applyElementMotion(avatar, spec.motion, scene.fps());
        } else {
            const std::string avatarFill = spec.platform == SocialPlatform::X
                    ? "#1D9BF0" : "#065FD4";
            socialShape(scene, parent, spec.name + "_avatar_fallback",
                    82.f, 82.f, avatarFill, avatarLeft + 41.f, avatarTop + 41.f,
                    spec.durationFrames, spec.motion, scene.fps(), 41.f);
            const std::string initial(1, spec.author.front());
            socialText(scene, parent, spec.name + "_avatar_initial", initial,
                    "assets/fonts/Inter-Bold.ttf", 34.f, "#FFFFFF",
                    avatarLeft + 41.f, avatarTop + 41.f,
                    spec.durationFrames, spec.motion, scene.fps());
        }

        const float identityLeft = avatarLeft + 104.f;
        const float authorCenter = identityLeft + layout.authorWidth * 0.5f;
        const float authorY = avatarTop + 24.f;
        socialText(scene, parent, spec.name + "_author", spec.author,
                "assets/fonts/Inter-Bold.ttf", 31.f, colors.ink, authorCenter,
                authorY, spec.durationFrames, spec.motion, scene.fps());
        if (spec.verified) {
            const float badgeX = identityLeft + layout.authorWidth + 19.f;
            socialShape(scene, parent, spec.name + "_verified_badge",
                    22.f, 22.f, colors.accent, badgeX, authorY,
                    spec.durationFrames, spec.motion, scene.fps(), 11.f);
            socialText(scene, parent, spec.name + "_verified_check", "✓",
                    "assets/fonts/DejaVuSans.ttf", 16.f, "#FFFFFF", badgeX,
                    authorY + 1.f, spec.durationFrames, spec.motion, scene.fps());
        }
        const std::string identityMeta = (spec.handle.empty() ? "" : spec.handle) +
                (spec.timestamp.empty() || spec.handle.empty() ? "" : "  ·  ") + spec.timestamp;
        if (!identityMeta.empty()) {
            socialText(scene, parent, spec.name + "_identity_meta", identityMeta,
                    "assets/fonts/Inter-Regular.ttf", 24.f, colors.muted,
                    identityLeft + layout.handleWidth * 0.5f, avatarTop + 60.f,
                    spec.durationFrames, spec.motion, scene.fps());
        }

        const float bodyLeft = left + layout.padding;
        for (std::size_t phraseIndex = 0;
             phraseIndex < layout.highlightSegments.size(); ++phraseIndex) {
            for (std::size_t segmentIndex = 0;
                 segmentIndex < layout.highlightSegments[phraseIndex].size(); ++segmentIndex) {
                const auto& segment = layout.highlightSegments[phraseIndex][segmentIndex];
                socialShape(scene, parent, spec.name + "_highlight_" +
                        std::to_string(phraseIndex) + "_" + std::to_string(segmentIndex),
                        segment.width + 10.f, segment.height + 5.f,
                        spec.highlightColor,
                        bodyLeft + segment.x + segment.width * 0.5f,
                        top + layout.bodyTop + segment.y + segment.height * 0.5f,
                        spec.durationFrames, spec.motion, scene.fps(), 5.f);
            }
        }
        for (std::size_t i = 0; i < layout.body.lines.size(); ++i) {
            const auto& line = layout.body.lines[i];
            socialText(scene, parent, spec.name + "_body_line_" + std::to_string(i),
                    line.text, spec.bodyFont, spec.bodyFontSize, colors.ink,
                    bodyLeft + line.x + line.width * 0.5f,
                    top + layout.bodyTop + line.top + line.lineHeight * 0.5f,
                    spec.durationFrames, spec.motion, scene.fps());
        }

        if (!spec.mediaPath.empty()) {
            LayerHandle& media = scene.image(ImageSpec{
                    .path = spec.mediaPath, .name = spec.name + "_media",
                    .frame = ImageFrameStyle{.cornerRadius = 14.f,
                            .borderColor = colors.line, .borderWidth = 1.f},
                    .fit = ImageFitMode::Cover,
                    .targetSize = chrononmotion::Vector2(layout.mediaWidth,
                                                        layout.mediaHeight)});
            media.parent(parent).position(0.f,
                    top + layout.mediaTop + layout.mediaHeight * 0.5f)
                 .alive(0, spec.durationFrames - 1);
            applyElementMotion(media, spec.motion, scene.fps());
        }

        const std::string interactions = metricText(spec);
        if (!spec.timestamp.empty() && spec.platform == SocialPlatform::X) {
            std::string timing = spec.timestamp;
            if (!spec.metrics.views.empty()) timing += "  ·  " + spec.metrics.views + " views";
            socialText(scene, parent, spec.name + "_timestamp", timing,
                    "assets/fonts/Inter-Regular.ttf", 22.f, colors.muted,
                    left + layout.padding + 310.f, top + layout.footerTop + 17.f,
                    spec.durationFrames, spec.motion, scene.fps());
        }
        if (!interactions.empty()) {
            socialText(scene, parent, spec.name + "_metrics", interactions,
                    "assets/fonts/Inter-Regular.ttf", 22.f, colors.muted,
                    left + layout.padding + layout.metricsWidth * 0.5f,
                    top + layout.footerTop + (spec.platform == SocialPlatform::X ? 52.f : 26.f),
                    spec.durationFrames, spec.motion, scene.fps());
        }
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
