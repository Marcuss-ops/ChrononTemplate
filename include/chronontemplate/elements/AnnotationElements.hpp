#ifndef CHRONONTEMPLATE_ANNOTATION_ELEMENTS_HPP
#define CHRONONTEMPLATE_ANNOTATION_ELEMENTS_HPP

// Graphics objects 07-12: glow lines, brushing and annotations.

#include "chronontemplate/elements/ElementsCommon.hpp"

#include <string>

namespace chronontemplate::elements {

    /// 07 GlowBrushTrace: luminous path with sharp core, halo, moving head
    /// and optional trail. One straight segment; the renderer blooms it.
    struct GlowBrushTraceSpec {
        float length{420.f};
        float width{6.f};
        std::string color{"#FFB82E"};
        bool trail{true};
        ElementStyle style{ElementStyle::DocumentaryDark};
        ElementMotion motion{};
        std::string name{"glow_brush_trace"};
    };
    [[nodiscard]] LayerHandle& addGlowBrushTrace(TemplateScene& scene,
                                                 const GlowBrushTraceSpec& spec);

    /// 08 BrushUnderline: imperfect organic highlighter stroke under a word.
    struct BrushUnderlineSpec {
        std::string text{};
        float fontSize{64.f};
        float strokeWidth{18.f};
        std::string color{"#E8B84A"};
        ElementStyle style{ElementStyle::DocumentaryDark};
        ElementMotion motion{};
        std::string name{"brush_underline"};
    };
    [[nodiscard]] LayerHandle& addBrushUnderline(TemplateScene& scene,
                                                 const BrushUnderlineSpec& spec);

    /// 09 TextMarkerHighlight: marker stripe behind a phrase, synced to the
    /// text via the native text-background treatment.
    struct TextMarkerHighlightSpec {
        std::string text{};
        float fontSize{56.f};
        std::string markerColor{"#E8B84A"};
        std::string textColor{"#101014"};
        ElementStyle style{ElementStyle::DocumentaryDark};
        ElementMotion motion{};
        std::string name{"text_marker_highlight"};
    };
    [[nodiscard]] LayerHandle& addTextMarkerHighlight(TemplateScene& scene,
                                                      const TextMarkerHighlightSpec& spec);

    /// 10 RoughCircleAnnotation: hand-drawn ring around a face, number or
    /// key point, built from the native ellipse stroke.
    struct RoughCircleAnnotationSpec {
        float diameter{220.f};
        float strokeWidth{7.f};
        std::string color{"#E03B2F"};
        std::string label{};
        ElementStyle style{ElementStyle::DocumentaryDark};
        ElementMotion motion{};
        std::string name{"rough_circle"};
    };
    [[nodiscard]] LayerHandle& addRoughCircleAnnotation(TemplateScene& scene,
                                                        const RoughCircleAnnotationSpec& spec);

    /// 11 CurvedArrowPointer: straight shaft with angled head and precise
    /// target; curvature is renderer-side, geometry stays primitive.
    struct CurvedArrowPointerSpec {
        float length{260.f};
        float thickness{10.f};
        std::string color{"#F2EFE6"};
        std::string label{};
        ElementStyle style{ElementStyle::DocumentaryDark};
        ElementMotion motion{};
        std::string name{"curved_arrow"};
    };
    [[nodiscard]] LayerHandle& addCurvedArrowPointer(TemplateScene& scene,
                                                     const CurvedArrowPointerSpec& spec);

    /// 12 FocusBracket: four corners framing an element, optional label.
    struct FocusBracketSpec {
        float width{420.f};
        float height{260.f};
        float corner{56.f};
        float strokeWidth{8.f};
        std::string color{"#F2EFE6"};
        std::string label{};
        ElementStyle style{ElementStyle::DocumentaryDark};
        ElementMotion motion{};
        std::string name{"focus_bracket"};
    };
    [[nodiscard]] LayerHandle& addFocusBracket(TemplateScene& scene,
                                               const FocusBracketSpec& spec);

}// namespace chronontemplate::elements

#endif//CHRONONTEMPLATE_ANNOTATION_ELEMENTS_HPP
