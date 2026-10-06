#include "chronontemplate/map/ModernMapPack.hpp"

#include "fake_content_host.hpp"
#include "motion_check.hpp"

#include <cmath>
#include <stdexcept>
#include <string>

using namespace chronontemplate;
using chronontemplate_test::FakeContentHost;
using chronontemplate_test::findLayer;
using chrononmotion_test::check;
using chrononmotion_test::section;

namespace {
void everyMapMoveHasStableIdAndProducesModernComposition() {
    section("modern map moves author styled labels and camera recipes");
    check(mapCameraMoves().size() == 5, "modern map pack publishes five camera recipes");
    for (const auto move : mapCameraMoves()) {
        FakeContentHost host;
        TemplateScene scene(std::string("modern_") + mapCameraMoveId(move), 30.f, host, 1920.f, 1080.f);
        ModernMapSpec spec;
        spec.platePath = "catalog/maps/nasa_blue_marble_august.jpg";
        spec.title = "NORTH ATLANTIC ROUTE";
        spec.cameraMove = move;
        spec.markers = {
            MapPlaceMarker{.label = "ROME", .position = {1180.f, 470.f}, .labelOffset = {34.f, -22.f},
                           .priority = 2, .typography = MapTypography{"Inter-Bold.ttf", 30.f, "#F3C76A",
                               TextStrokeStyle{"#07121A", 2.f}, TextShadowStyle{},
                               TextGlowStyle{"#F3C76A", 18.f, 0.2f}}},
            MapPlaceMarker{.label = "PARIS", .position = {760.f, 380.f}, .labelOffset = {-80.f, 0.f}}
        };
        const auto built = composeModernMap(scene, spec);
        check(built.plate && built.markers.size() == 2 && built.labels.size() == 2 && built.title,
              "composition includes plate, marker shapes, marker labels and title");
        check(built.endFrame == spec.duration, "modern map preserves the authored frame window");
        const auto mid = scene.submit(75);
        const BoundLayer* label = findLayer(mid, built.labels.front()->id());
        check(label && label->draws(), "marker text is bound into the submitted frame");
        check(scene.validate().empty(), "modern map scene validates");
    }
}

void mapTypographyRolesAndEditorialElementsComposeIndependently() {
    section("map typography roles and editorial layers reveal independently");
    const auto title = mapTypographyPreset(MapTextRole::Title);
    const auto primary = mapTypographyPreset(MapTextRole::PrimaryLocation);
    const auto secondary = mapTypographyPreset(MapTextRole::SecondaryLocation);
    const auto value = mapTypographyPreset(MapTextRole::DataValue);
    const auto legend = mapTypographyPreset(MapTextRole::Legend);
    const auto attribution = mapTypographyPreset(MapTextRole::Attribution);
    check(title.fontSize > primary.fontSize && primary.fontSize > secondary.fontSize &&
              value.fontSize > secondary.fontSize && legend.fontSize > attribution.fontSize,
          "title, location, value, legend, and attribution roles have distinct size hierarchy");
    check(primary.stroke.has_value() && !secondary.stroke.has_value() && !legend.stroke.has_value(),
          "stroke is reserved for emphasized text, not applied indiscriminately");

    FakeContentHost host;
    TemplateScene scene("modern_editorial", 30.f, host, 1920.f, 1080.f);
    ModernMapSpec spec;
    spec.platePath = "catalog/maps/nasa_blue_marble_august.jpg";
    spec.title = "EUROPE CONNECTED";
    spec.subtitle = "A regional overview";
    spec.attribution = "Source: illustrative basemap";
    spec.markers = {MapPlaceMarker{.label = "ROME", .position = {1180.f, 470.f},
                                    .role = MapTextRole::PrimaryLocation}};
    spec.dataCards = {MapDataCard{"NETWORK", "12.4M", {1540.f, 690.f}, {300.f, 132.f}, "#69D7C6"}};
    spec.legend = {MapLegendItem{"Primary route", "#69D7C6"}};
    spec.callouts = {MapEditorialCallout{"Rome hub", {1180.f, 470.f}, {1330.f, 430.f},
                                         {1440.f, 380.f}, "#69D7C6"}};
    const auto built = composeModernMap(scene, spec);
    check(built.title && built.subtitle && built.attribution,
          "title, subtitle, and attribution have separately addressable layers");
    check(built.editorial.size() == 11,
          "data card, graduated legend row, and callout line/text are independently addressable");
    const auto frame = scene.submit(75);
    for (const auto* layer : built.editorial) {
        const auto* bound = findLayer(frame, layer->id());
        check(bound && bound->draws(), "editorial element reaches the submitted frame");
    }
    check(scene.validate().empty(), "editorial map composition validates");
}

void mapPackRejectsInvalidTypographyAndMarkerGeometry() {
    section("modern map pack rejects invalid authoring input");
    FakeContentHost host;
    TemplateScene scene("modern_invalid", 30.f, host, 1920.f, 1080.f);
    ModernMapSpec spec;
    spec.platePath = "catalog/maps/nasa_blue_marble_august.jpg";
    spec.markers = {MapPlaceMarker{.label = "BAD", .position = {std::nanf(""), 0.f}}};
    bool threw = false;
    try { (void)composeModernMap(scene, spec); }
    catch (const std::invalid_argument&) { threw = true; }
    check(threw, "non-finite marker coordinates are rejected");

    spec.markers.clear();
    spec.titleTypography.glow = TextGlowStyle{"#FFFFFF", 12.f, 9.f};
    threw = false;
    try { (void)composeModernMap(scene, spec); }
    catch (const std::invalid_argument&) { threw = true; }
    check(threw, "glow intensity outside the supported range is rejected");

    spec.titleTypography.glow.reset();
    spec.titleTypography.background = TextBackgroundStyle{"#07121A", 1.f, -1.f, {8.f, 4.f}};
    threw = false;
    try { (void)composeModernMap(scene, spec); }
    catch (const std::invalid_argument&) { threw = true; }
    check(threw, "invalid typography chip radius is rejected");
}
}

int main() {
    everyMapMoveHasStableIdAndProducesModernComposition();
    mapTypographyRolesAndEditorialElementsComposeIndependently();
    mapPackRejectsInvalidTypographyAndMarkerGeometry();
    return chrononmotion_test::report();
}
