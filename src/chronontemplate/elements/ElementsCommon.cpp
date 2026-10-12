#include "chronontemplate/elements/ElementsCommon.hpp"

#include "chrononmotion/motion/Easing.hpp"

#include <stdexcept>

namespace chronontemplate::elements {

    namespace {
        using chrononmotion::Vector2;
        using chrononmotion::motion::Easing;
    }

    const char* elementId(ElementKind kind) {
        switch (kind) {
            case ElementKind::DataTimeline: return "timeline.data_timeline";
            case ElementKind::MilestoneCard: return "timeline.milestone_card";
            case ElementKind::DateRangeBracket: return "timeline.date_range_bracket";
            case ElementKind::MetricCounterBlock: return "timeline.metric_counter_block";
            case ElementKind::ComparisonDelta: return "timeline.comparison_delta";
            case ElementKind::EventSequenceRail: return "timeline.event_sequence_rail";
            case ElementKind::GlowBrushTrace: return "annotation.glow_brush_trace";
            case ElementKind::BrushUnderline: return "annotation.brush_underline";
            case ElementKind::TextMarkerHighlight: return "annotation.text_marker_highlight";
            case ElementKind::RoughCircleAnnotation: return "annotation.rough_circle";
            case ElementKind::CurvedArrowPointer: return "annotation.curved_arrow";
            case ElementKind::FocusBracket: return "annotation.focus_bracket";
            case ElementKind::NewsArticleCard: return "web.news_article_card";
            case ElementKind::RedditCommentCard: return "web.reddit_comment_card";
            case ElementKind::SocialPostCard: return "web.social_post_card";
            case ElementKind::SearchResultSnippet: return "web.search_result_snippet";
            case ElementKind::BrowserWindowChrome: return "web.browser_chrome";
            case ElementKind::WebScreenshotFocus: return "web.screenshot_focus";
            case ElementKind::ArchivePhotoFrame: return "doc.archive_photo_frame";
            case ElementKind::EvidenceDocumentCard: return "doc.evidence_document_card";
            case ElementKind::QuoteAttributionBlock: return "doc.quote_attribution_block";
            case ElementKind::IdentityLowerThird: return "doc.identity_lower_third";
            case ElementKind::ChapterDivider: return "doc.chapter_divider";
            case ElementKind::SourceCitationTag: return "doc.source_citation_tag";
            case ElementKind::GeoLocationMarker: return "diagram.geo_location_marker";
            case ElementKind::RegionBoundaryHighlight: return "diagram.region_boundary_highlight";
            case ElementKind::RouteStrokeLegend: return "diagram.route_stroke_legend";
            case ElementKind::RelationConnector: return "diagram.relation_connector";
            case ElementKind::BeforeAfterSplit: return "diagram.before_after_split";
            case ElementKind::FlowDiagramNode: return "diagram.flow_diagram_node";
            default: return "unknown.unknown";
        }
    }

    std::vector<std::string> allElementIds() {
        std::vector<std::string> ids;
        for (int i = 0; i <= static_cast<int>(ElementKind::FlowDiagramNode); ++i) {
            ids.emplace_back(elementId(static_cast<ElementKind>(i)));
        }
        return ids;
    }

    ElementPalette paletteFor(ElementStyle style) {
        switch (style) {
            case ElementStyle::PaperLight:
                return {.paper = "#F4F0E7", .ink = "#242627", .accent = "#C08D4E",
                        .muted = "#8A8F98", .line = "#D8D2C2"};
            case ElementStyle::Broadcast:
                return {.paper = "#F7F8FA", .ink = "#222832", .accent = "#E03B2F",
                        .muted = "#697586", .line = "#D5DAE2"};
            case ElementStyle::DocumentaryDark:
            default:
                return {.paper = "#101014", .ink = "#F2EFE6", .accent = "#E8B84A",
                        .muted = "#8A8F98", .line = "#3A3A40"};
        }
    }

    void require(bool condition, const char* message) {
        if (!condition) throw std::invalid_argument(message);
    }

    void applyElementMotion(LayerHandle& layer, const ElementMotion& motion,
                            float fps, int staggerIndex) {
        const int start = motion.startFrame + staggerIndex * motion.staggerStep;
        const int clampedStart = start < motion.endFrame ? start : motion.endFrame;
        const int duration = motion.endFrame - clampedStart >= 8
                ? motion.endFrame - clampedStart : 8;
        switch (motion.preset) {
            case ElementMotionPreset::None:
                break;
            case ElementMotionPreset::Reveal:
                layer.animate(FadeIn{.inFrame = clampedStart, .duration = duration});
                break;
            case ElementMotionPreset::Rise:
                layer.animate(SlideIn{.direction = chrononmotion::motion::presets::Direction::Up,
                                      .inFrame = clampedStart, .duration = duration, .distance = 90.f})
                     .animate(FadeIn{.inFrame = clampedStart, .duration = duration / 2 + 4});
                break;
            case ElementMotionPreset::Pop:
                layer.animate(ScalePop{.inFrame = clampedStart, .duration = duration,
                                       .from = 0.85f, .to = 1.f})
                     .animate(FadeIn{.inFrame = clampedStart, .duration = duration / 2 + 4});
                break;
            case ElementMotionPreset::DrawOn:
                // Trim emulation with canonical tracks: the stroke slides in
                // along its axis while fading, no separate path engine.
                layer.animate(SlideIn{.direction = chrononmotion::motion::presets::Direction::Left,
                                      .inFrame = clampedStart, .duration = duration, .distance = 160.f})
                     .animate(FadeIn{.inFrame = clampedStart, .duration = duration / 2 + 4});
                break;
            case ElementMotionPreset::Stagger:
                layer.animate(FadeIn{.inFrame = clampedStart, .duration = duration});
                break;
            case ElementMotionPreset::Pulse: {
                layer.animate(FadeIn{.inFrame = clampedStart, .duration = duration});
                auto& track = layer.layer().tracks.opacity;
                const auto at = [&](int f) { return static_cast<float>(f) / fps; };
                track.add(at(clampedStart + duration), 1.f, Easing::easeInOut());
                track.add(at(clampedStart + duration + 24), 0.45f, Easing::easeInOut());
                track.add(at(clampedStart + duration + 48), 1.f, Easing::easeInOut());
                break;
            }
            default:
                throw std::invalid_argument("applyElementMotion: unknown motion preset");
        }
    }

    LayerHandle& addBar(TemplateScene& scene, unsigned parentId, const std::string& name,
                        float w, float h, float x, float y, const std::string& color,
                        float cornerRadius) {
        LayerHandle& bar = scene.shape(ShapeSpec{
                .size = Vector2(w, h), .fillColor = color,
                .name = name, .cornerRadius = cornerRadius});
        bar.parent(parentId);
        bar.position(x, y);
        bar.alive(0, 150);
        return bar;
    }

    LayerHandle& addText(TemplateScene& scene, unsigned parentId, const std::string& name,
                         const std::string& text, float fontSize, const std::string& color,
                         float x, float y) {
        LayerHandle& label = scene.text(TextSpec{
                .text = text, .fontSize = fontSize, .color = color, .name = name});
        label.parent(parentId);
        label.position(x, y);
        label.alive(0, 150);
        return label;
    }

}// namespace chronontemplate::elements
