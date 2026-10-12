#include "chronontemplate/elements/DiagramElements.hpp"

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
        check(scene.validate().empty(), "each diagram scene validates");
    }

    void geoLocationMarkerComposes() {
        section("25 geo location marker");
        FakeContentHost host;
        TemplateScene scene("el_geo", 30.f, host, 1920.f, 1080.f);
        GeoLocationMarkerSpec spec;
        spec.label = "CUPERTINO";
        LayerHandle& root = addGeoLocationMarker(scene, spec);
        root.position(960.f, 540.f);
        submitsThrough("the marker root submits across the clip", scene, root);
        check(scene.submit(48).layers.size() == 4, "ring, core and label compose four layers");
        const auto* ring = host.findShapeRequest("geo_location_marker_ring");
        check(ring && ring->strokeColor == "#E03B2F", "the target ring keeps signal red");
    }

    void regionBoundaryHighlightComposes() {
        section("26 region boundary highlight");
        FakeContentHost host;
        TemplateScene scene("el_region", 30.f, host, 1920.f, 1080.f);
        RegionBoundaryHighlightSpec spec;
        spec.label = "SECTOR 7";
        LayerHandle& root = addRegionBoundaryHighlight(scene, spec);
        root.position(960.f, 540.f);
        submitsThrough("the region root submits across the clip", scene, root);
        check(scene.submit(48).layers.size() == 5, "fill, boundary, glow side and label compose five layers");
        const auto* boundary = host.findShapeRequest("region_boundary_highlight_boundary");
        check(boundary && boundary->polygonPoints == 6, "the boundary is a hexagonal stroke");
    }

    void routeStrokeLegendComposes() {
        section("27 route stroke legend");
        FakeContentHost host;
        TemplateScene scene("el_route", 30.f, host, 1920.f, 1080.f);
        RouteStrokeLegendSpec spec;
        spec.routeName = "EARTH TO MOON";
        LayerHandle& root = addRouteStrokeLegend(scene, spec);
        root.position(960.f, 540.f);
        submitsThrough("the legend root submits across the clip", scene, root);
        check(scene.submit(48).layers.size() == 7, "halo, line, head, name and swatches compose seven layers");
        const auto* swatch = host.findShapeRequest("route_stroke_legend_swatch_b");
        check(swatch && swatch->fillColor == "#38BDF8", "the alternate swatch stays sky blue");
    }

    void relationConnectorComposes() {
        section("28 relation connector");
        FakeContentHost host;
        TemplateScene scene("el_relation", 30.f, host, 1920.f, 1080.f);
        RelationConnectorSpec spec;
        spec.leftLabel = "APPLE";
        spec.rightLabel = "NOKIA";
        spec.relation = "DISRUPTED";
        LayerHandle& root = addRelationConnector(scene, spec);
        root.position(960.f, 540.f);
        submitsThrough("the connector root submits across the clip", scene, root);
        check(scene.submit(48).layers.size() == 7, "dots, labels, link and relation compose seven layers");
    }

    void beforeAfterSplitComposes() {
        section("29 before after split");
        FakeContentHost host;
        TemplateScene scene("el_split", 30.f, host, 1920.f, 1080.f);
        BeforeAfterSplitSpec spec;
        spec.beforePath = "assets/test/square_bottle_test.png";
        spec.afterPath = "assets/test/square_bottle_test.png";
        LayerHandle& root = addBeforeAfterSplit(scene, spec);
        root.position(960.f, 540.f);
        submitsThrough("the split root submits across the clip", scene, root);
        check(scene.submit(48).layers.size() == 6, "plates, divider and tags compose six layers");
        const auto* divider = host.findShapeRequest("before_after_split_divider");
        check(divider != nullptr, "the divider exists");
        bool threw = false;
        try {
            BeforeAfterSplitSpec bad;
            bad.beforePath = "a.png";
            bad.afterPath = "b.png";
            bad.split = 1.0f;
            addBeforeAfterSplit(scene, bad);
        } catch (const std::invalid_argument&) { threw = true; }
        check(threw, "a full-width split fails closed");
    }

    void flowDiagramNodeComposes() {
        section("30 flow diagram node");
        FakeContentHost host;
        TemplateScene scene("el_flow", 30.f, host, 1920.f, 1080.f);
        FlowDiagramNodeSpec spec;
        spec.title = "LAUNCH";
        spec.subtitle = "Cause";
        LayerHandle& root = addFlowDiagramNode(scene, spec);
        root.position(960.f, 540.f);
        submitsThrough("the node root submits across the clip", scene, root);
        check(scene.submit(48).layers.size() == 7, "body, accent, texts and stubs compose seven layers");
    }

}// namespace

int main() {
    geoLocationMarkerComposes();
    regionBoundaryHighlightComposes();
    routeStrokeLegendComposes();
    relationConnectorComposes();
    beforeAfterSplitComposes();
    flowDiagramNodeComposes();
    return chrononmotion_test::report();
}
