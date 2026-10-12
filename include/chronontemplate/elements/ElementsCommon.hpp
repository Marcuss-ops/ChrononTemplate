#ifndef CHRONONTEMPLATE_ELEMENTS_COMMON_HPP
#define CHRONONTEMPLATE_ELEMENTS_COMMON_HPP

// Chronon Graphics Object Pack — shared architecture.
//
// One registry (30 stable string IDs), one composer vocabulary (style +
// geometry + motion) and one motion path. There are no per-object renderers:
// every object is authored from the canonical primitives (Shape, Text, Image,
// Group) and every reveal runs through the canonical motion tracks. Pixel
// work (glow blur, brush texture, photo grain) stays renderer-side; the C++
// owns layout, hierarchy and choreography.
//
// Every object is usable statically first: with ElementMotionPreset::None the
// composition is complete and readable without a single keyframe.

#include "chronontemplate/core/TemplateScene.hpp"

#include <string>
#include <vector>

namespace chronontemplate::elements {

    /// Stable registry of the 30 graphics objects, in spec order.
    enum class ElementKind {
        DataTimeline = 0,
        MilestoneCard,
        DateRangeBracket,
        MetricCounterBlock,
        ComparisonDelta,
        EventSequenceRail,
        GlowBrushTrace,
        BrushUnderline,
        TextMarkerHighlight,
        RoughCircleAnnotation,
        CurvedArrowPointer,
        FocusBracket,
        NewsArticleCard,
        RedditCommentCard,
        SocialPostCard,
        SearchResultSnippet,
        BrowserWindowChrome,
        WebScreenshotFocus,
        ArchivePhotoFrame,
        EvidenceDocumentCard,
        QuoteAttributionBlock,
        IdentityLowerThird,
        ChapterDivider,
        SourceCitationTag,
        GeoLocationMarker,
        RegionBoundaryHighlight,
        RouteStrokeLegend,
        RelationConnector,
        BeforeAfterSplit,
        FlowDiagramNode
    };

    /// Stable dotted ID for an object, e.g. "annotation.glow_brush_trace".
    [[nodiscard]] const char* elementId(ElementKind kind);
    /// All 30 IDs in registry order.
    [[nodiscard]] std::vector<std::string> allElementIds();

    /// Shared visual language. The palette resolves ink/paper/accent so the
    /// 30 objects stay coherent inside one video.
    enum class ElementStyle {
        DocumentaryDark,
        PaperLight,
        Broadcast
    };

    struct ElementPalette {
        std::string paper{};
        std::string ink{};
        std::string accent{};
        std::string muted{};
        std::string line{};
    };

    [[nodiscard]] ElementPalette paletteFor(ElementStyle style);

    /// Optional reveal choreography. Motion only stages the elements or moves
    /// a cursor; it never carries the layout.
    enum class ElementMotionPreset {
        None,
        Reveal,
        Rise,
        Pop,
        DrawOn,
        Stagger,
        Pulse
    };

    struct ElementMotion {
        ElementMotionPreset preset{ElementMotionPreset::Reveal};
        int startFrame{0};
        int endFrame{24};
        int staggerStep{6};
    };

    /// Fail-closed authoring guard: empty required strings and inverted
    /// ranges throw instead of producing a broken composition.
    void require(bool condition, const char* message);

    /// Apply one motion preset to a layer. `staggerIndex` offsets the start
    /// for Stagger reveals; `fps` drives the Pulse keyframes.
    void applyElementMotion(LayerHandle& layer, const ElementMotion& motion,
                            float fps, int staggerIndex = 0);

    /// Thin helpers so the 30 objects share one spelling.
    LayerHandle& addBar(TemplateScene& scene, unsigned parentId, const std::string& name,
                        float w, float h, float x, float y, const std::string& color,
                        float cornerRadius = 0.f);
    LayerHandle& addText(TemplateScene& scene, unsigned parentId, const std::string& name,
                         const std::string& text, float fontSize, const std::string& color,
                         float x, float y);

}// namespace chronontemplate::elements

#endif//CHRONONTEMPLATE_ELEMENTS_COMMON_HPP
