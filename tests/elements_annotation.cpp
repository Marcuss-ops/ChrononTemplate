#include "chronontemplate/elements/AnnotationElements.hpp"

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
        check(scene.validate().empty(), "each annotation scene validates");
    }

    void glowBrushTraceComposes() {
        section("07 glow brush trace");
        FakeContentHost host;
        TemplateScene scene("el_brush", 30.f, host, 1920.f, 1080.f);
        GlowBrushTraceSpec spec;
        spec.length = 420.f;
        LayerHandle& root = addGlowBrushTrace(scene, spec);
        root.position(960.f, 540.f);
        submitsThrough("the brush root submits across the clip", scene, root);
        check(scene.submit(48).layers.size() == 5, "halo, core, head and trail compose five layers");
        const auto* core = host.findShapeRequest("glow_brush_trace_core");
        check(core && core->fillColor == "#FFFFFF", "the brush core stays hot white");
        const auto* halo = host.findShapeRequest("glow_brush_trace_halo");
        check(halo && halo->fillColor == "#FFB82E", "the halo keeps its default amber");
        bool threw = false;
        try {
            GlowBrushTraceSpec bad;
            bad.length = 0.f;
            addGlowBrushTrace(scene, bad);
        } catch (const std::invalid_argument&) { threw = true; }
        check(threw, "a zero-length trace fails closed");
    }

    void brushUnderlineComposes() {
        section("08 brush underline");
        FakeContentHost host;
        TemplateScene scene("el_underline", 30.f, host, 1920.f, 1080.f);
        BrushUnderlineSpec spec;
        spec.text = "STEVE JOBS";
        LayerHandle& root = addBrushUnderline(scene, spec);
        root.position(960.f, 600.f);
        submitsThrough("the underline root submits across the clip", scene, root);
        check(scene.submit(48).layers.size() == 4, "word plus two stroke bars compose four layers");
        const auto* stroke = host.findShapeRequest("brush_underline_stroke");
        check(stroke && stroke->fillColor == "#E8B84A", "the underline keeps its gold");
    }

    void textMarkerHighlightComposes() {
        section("09 text marker highlight");
        FakeContentHost host;
        TemplateScene scene("el_marker", 30.f, host, 1920.f, 1080.f);
        TextMarkerHighlightSpec spec;
        spec.text = "THE FIRST iPHONE";
        LayerHandle& root = addTextMarkerHighlight(scene, spec);
        root.position(960.f, 540.f);
        submitsThrough("the marker root submits across the clip", scene, root);
        check(scene.submit(48).layers.size() == 2, "root plus synced phrase compose two layers");
    }

    void roughCircleComposes() {
        section("10 rough circle annotation");
        FakeContentHost host;
        TemplateScene scene("el_circle", 30.f, host, 1920.f, 1080.f);
        RoughCircleAnnotationSpec spec;
        spec.diameter = 220.f;
        spec.label = "SUBJECT";
        LayerHandle& root = addRoughCircleAnnotation(scene, spec);
        root.position(960.f, 540.f);
        submitsThrough("the circle root submits across the clip", scene, root);
        check(scene.submit(48).layers.size() == 4, "ring, wobble and label compose four layers");
        const auto* ring = host.findShapeRequest("rough_circle_ring");
        check(ring && ring->strokeColor == "#E03B2F", "the ring keeps its signal red");
    }

    void curvedArrowComposes() {
        section("11 curved arrow pointer");
        FakeContentHost host;
        TemplateScene scene("el_arrow", 30.f, host, 1920.f, 1080.f);
        CurvedArrowPointerSpec spec;
        spec.length = 260.f;
        spec.label = "SEE HERE";
        LayerHandle& root = addCurvedArrowPointer(scene, spec);
        root.position(800.f, 540.f);
        submitsThrough("the arrow root submits across the clip", scene, root);
        check(scene.submit(48).layers.size() == 5, "shaft, head pair and label compose five layers");
    }

    void focusBracketComposes() {
        section("12 focus bracket");
        FakeContentHost host;
        TemplateScene scene("el_bracket", 30.f, host, 1920.f, 1080.f);
        FocusBracketSpec spec;
        spec.width = 420.f;
        spec.height = 260.f;
        spec.label = "EVIDENCE A";
        LayerHandle& root = addFocusBracket(scene, spec);
        root.position(960.f, 540.f);
        submitsThrough("the bracket root submits across the clip", scene, root);
        check(scene.submit(48).layers.size() == 10, "eight corner bars plus label compose ten layers");
        const auto* corner = host.findShapeRequest("focus_bracket_corner_tl_h");
        check(corner != nullptr, "corner bars use stable names");
    }

    void glowLineComposes() {
        section("13 docus glow line");
        FakeContentHost host;
        TemplateScene scene("el_glow_line", 30.f, host, 1920.f, 1080.f);
        GlowLineSpec spec;
        spec.length = 640.f;
        LayerHandle& root = addGlowLine(scene, spec);
        root.position(960.f, 540.f);
        submitsThrough("the glow line root submits across the clip", scene, root);
        // root, wide halo, tight halo, core, head halo, head core -> 6 layers
        check(scene.submit(48).layers.size() == 6, "wide halo, halo, core and light head compose six layers");
        const auto* core = host.findShapeRequest("glow_line_core");
        check(core && core->fillColor == "#FFFFFF", "the glow line core is razor sharp white");
        const auto* halo = host.findShapeRequest("glow_line_halo");
        check(halo && halo->fillColor == "#00E5FF", "the tight halo keeps vibrant cyan");
        const auto* wide = host.findShapeRequest("glow_line_wide_halo");
        check(wide && wide->fillColor == "#0072FF", "the wide halo keeps deep blue aura");
    }

}// namespace

int main() {
    glowBrushTraceComposes();
    brushUnderlineComposes();
    textMarkerHighlightComposes();
    roughCircleComposes();
    curvedArrowComposes();
    focusBracketComposes();
    glowLineComposes();
    return chrononmotion_test::report();
}

