#ifndef CHRONONTEMPLATE_DIAGRAM_ELEMENTS_HPP
#define CHRONONTEMPLATE_DIAGRAM_ELEMENTS_HPP

// Graphics objects 25-30: maps, diagrams and comparisons. They plug into
// the map tooling: markers anchor to coordinates, routes reuse the stroke
// language, splits reuse the wipe contract.

#include "chronontemplate/elements/ElementsCommon.hpp"

#include <string>

namespace chronontemplate::elements {

    /// 25 GeoLocationMarker: target ring, core dot, optional label.
    struct GeoLocationMarkerSpec {
        std::string label{};
        float radius{46.f};
        std::string color{"#E03B2F"};
        ElementStyle style{ElementStyle::DocumentaryDark};
        ElementMotion motion{};
        std::string name{"geo_location_marker"};
    };
    [[nodiscard]] LayerHandle& addGeoLocationMarker(TemplateScene& scene,
                                                    const GeoLocationMarkerSpec& spec);

    /// 26 RegionBoundaryHighlight: dashed-looking boundary from the native
    /// polygon stroke with fill, glow-side bar and label.
    struct RegionBoundaryHighlightSpec {
        float width{520.f};
        float height{360.f};
        std::string label{};
        std::string color{"#E8B84A"};
        ElementStyle style{ElementStyle::DocumentaryDark};
        ElementMotion motion{};
        std::string name{"region_boundary_highlight"};
    };
    [[nodiscard]] LayerHandle& addRegionBoundaryHighlight(TemplateScene& scene,
                                                          const RegionBoundaryHighlightSpec& spec);

    /// 27 RouteStrokeLegend: glowing line sample, direction head, route
    /// name and chromatic legend swatches.
    struct RouteStrokeLegendSpec {
        std::string routeName{};
        std::string color{"#E8B84A"};
        std::string altColor{"#38BDF8"};
        ElementStyle style{ElementStyle::DocumentaryDark};
        ElementMotion motion{};
        std::string name{"route_stroke_legend"};
    };
    [[nodiscard]] LayerHandle& addRouteStrokeLegend(TemplateScene& scene,
                                                    const RouteStrokeLegendSpec& spec);

    /// 28 RelationConnector: two endpoint dots, link line, relation text.
    struct RelationConnectorSpec {
        std::string leftLabel{};
        std::string rightLabel{};
        std::string relation{};
        float span{560.f};
        ElementStyle style{ElementStyle::DocumentaryDark};
        ElementMotion motion{};
        std::string name{"relation_connector"};
    };
    [[nodiscard]] LayerHandle& addRelationConnector(TemplateScene& scene,
                                                    const RelationConnectorSpec& spec);

    /// 29 BeforeAfterSplit: two image plates, divider, BEFORE/AFTER tags.
    /// The pixel wipe stays renderer-side; C++ owns plates and geometry.
    struct BeforeAfterSplitSpec {
        std::string beforePath{};
        std::string afterPath{};
        float split{0.5f};
        float width{960.f};
        float height{540.f};
        ElementStyle style{ElementStyle::DocumentaryDark};
        ElementMotion motion{};
        std::string name{"before_after_split"};
    };
    [[nodiscard]] LayerHandle& addBeforeAfterSplit(TemplateScene& scene,
                                                   const BeforeAfterSplitSpec& spec);

    /// 30 FlowDiagramNode: reusable process/org-chart block with title,
    /// subtitle and connector stubs.
    struct FlowDiagramNodeSpec {
        std::string title{};
        std::string subtitle{};
        std::string accent{"#E8B84A"};
        float width{420.f};
        float height{220.f};
        ElementStyle style{ElementStyle::DocumentaryDark};
        ElementMotion motion{};
        std::string name{"flow_diagram_node"};
    };
    [[nodiscard]] LayerHandle& addFlowDiagramNode(TemplateScene& scene,
                                                  const FlowDiagramNodeSpec& spec);

}// namespace chronontemplate::elements

#endif//CHRONONTEMPLATE_DIAGRAM_ELEMENTS_HPP
