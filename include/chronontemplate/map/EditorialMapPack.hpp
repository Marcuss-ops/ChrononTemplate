// ChrononTemplate — vector editorial map compositions.
//
// This pack consumes the already-projected chrononplugin.editorial-map-scene.v1
// document and lowers it to Chronon3d primitives: path rings, clipped hatch
// segments, labels, glow, trim and a radar pulse. It never reads GeoJSON,
// projects coordinates or rasterizes a basemap; the map domain ends upstream.
#ifndef CHRONONTEMPLATE_EDITORIAL_MAP_PACK_HPP
#define CHRONTONTEMPLATE_EDITORIAL_MAP_PACK_HPP

#include "chronontemplate/core/TemplateScene.hpp"

#include <optional>
#include <string>
#include <vector>

namespace chronontemplate {

struct EditorialMapPoint {
    float x{0.f};
    float y{0.f};
};

struct EditorialMapRing {
    std::vector<EditorialMapPoint> points{};
};

struct EditorialMapPolygon {
    std::vector<EditorialMapRing> rings{};
};

struct EditorialMapFeature {
    std::vector<EditorialMapPolygon> polygons{};
};

struct EditorialMapPalette {
    std::string background{};
    std::string accent{};
    std::string ink{};
    std::string muted{};
    std::string paper{};
    std::string countriesFill{};
    std::string countriesStroke{};
    std::string statesFill{};
    std::string statesStroke{};
    std::string highlightFill{};
    std::string highlightStroke{};
    std::string grid{};
    std::string hatch{};
    std::string panelFill{};
    std::string panelStroke{};
    std::string shadow{};
};

struct EditorialMapLabel {
    std::string text{};
    std::string font{"sans_regular"};
    std::string color{"#FFFFFF"};
    std::string align{"left"};
    std::string stroke{};
    std::string role{"data"};
    float x{0.f};
    float y{0.f};
    float width{0.f};
    float size{16.f};
    float opacity{1.f};
    float strokeWidth{0.f};
    int tracking{0};
};

struct EditorialMapSegment {
    EditorialMapPoint from{};
    EditorialMapPoint to{};
    std::string color{"#FFFFFF"};
    float width{1.f};
};

struct EditorialMapFrame {
    float x{0.f};
    float y{0.f};
    float width{0.f};
    float height{0.f};
    std::string fill{};
    std::string stroke{};
    float strokeWidth{1.f};
};

struct EditorialMapPin {
    float x{0.f};
    float y{0.f};
    float labelX{0.f};
    float labelY{0.f};
    float radius{8.f};
    std::string label{};
    std::string fill{"#FFFFFF"};
    std::string ring{"#FFFFFF"};
    std::string style{"dot"};
};

struct EditorialMapArc {
    EditorialMapPoint from{};
    EditorialMapPoint to{};
    EditorialMapPoint control1{};
    EditorialMapPoint control2{};
    std::string distanceText{};
    float distanceX{0.f};
    float distanceY{0.f};
};

struct EditorialMapLeader {
    std::vector<EditorialMapPoint> points{};
    float anchorRadius{4.f};
};

struct EditorialMapRadar {
    float x{0.f};
    float y{0.f};
    float maxRadius{160.f};
    std::string color{"#38BDF8"};
};

struct EditorialMapShadow {
    float offsetX{0.f};
    float offsetY{0.f};
    float blur{0.f};
    float opacity{0.f};
    float scale{1.f};
    std::string color{};
};

/// Canvas-space scene produced by ChrononPlugin. All coordinates are top-left
/// canvas pixels; the pack alone converts them to TemplateScene coordinates.
struct EditorialMapScene {
    std::string style{};
    chrononmotion::Vector2 canvas{1920.f, 1080.f};
    float fps{30.f};
    int frameCount{240};
    std::string title{};
    std::string subtitle{};
    EditorialMapPalette palette{};
    std::vector<EditorialMapFeature> states{};
    std::vector<EditorialMapFeature> countries{};
    std::vector<EditorialMapPolygon> highlight{};
    std::vector<EditorialMapSegment> hatchSegments{};
    std::vector<EditorialMapSegment> graticuleSegments{};
    std::vector<EditorialMapSegment> accentSegments{};
    std::vector<EditorialMapFrame> frames{};
    std::vector<EditorialMapPin> pins{};
    std::vector<EditorialMapLabel> labels{};
    std::optional<EditorialMapArc> arc{};
    std::optional<EditorialMapLeader> leader{};
    std::optional<EditorialMapRadar> radar{};
    std::optional<EditorialMapShadow> shadow{};
};

struct EditorialMapComposition {
    LayerHandle* background{nullptr};
    LayerHandle* highlight{nullptr};
    std::vector<LayerHandle*> layers{};
    int endFrame{0};
};

[[nodiscard]] const char* editorialMapSceneSchemaId() noexcept;

/// Reads and validates a chrononplugin.editorial-map-scene.v1 document.
/// Throws std::runtime_error on malformed JSON and std::invalid_argument on a
/// scene outside the supported contract.
[[nodiscard]] EditorialMapScene loadEditorialMapScene(const std::string& path);

/// Adds the scene to `scene`. The style selects the recipe; all geometry comes
/// from the DTO. Throws std::invalid_argument on an unsupported or incomplete
/// scene.
[[nodiscard]] EditorialMapComposition addEditorialMap(TemplateScene& scene,
                                                     const EditorialMapScene& spec);

}  // namespace chronontemplate

#endif  // CHRONTONTEMPLATE_EDITORIAL_MAP_PACK_HPP
