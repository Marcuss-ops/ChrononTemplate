// ChrononTemplate — animated route drawing.
//
// A dotted path draws itself across a map card point by point, a traveler
// dot rides the full route, and place labels pop as it arrives. Dots need
// no rotation, so the whole look authors with existing primitives
// (shapes, text, motion): no renderer-side gap.

#ifndef CHRONONTEMPLATE_ROUTE_DRAWING_PACK_HPP
#define CHRONONTEMPLATE_ROUTE_DRAWING_PACK_HPP

#include "chronontemplate/core/TemplateScene.hpp"

#include <cstdint>
#include <string>
#include <vector>

namespace chronontemplate::docfx {

    struct RouteWaypoint {
        float x{0.f}; ///< canvas px
        float y{0.f};
        std::string label{};
    };

    struct RouteSpec {
        std::string mapAsset{}; ///< backdrop card; empty keeps a dark plate
        float cardWidth{1240.f};
        float cardHeight{700.f};
        float cardCenterX{960.f};
        float cardCenterY{540.f};
        std::vector<RouteWaypoint> waypoints{{400.f, 800.f, "ROME"},
                                             {960.f, 540.f, "NAPLES"},
                                             {1500.f, 300.f, "PALERMO"}};
        int dotsPerLeg{10};       ///< trail dots per waypoint leg
        float dotRadius{7.f};
        float travelerRadius{13.f};
        std::string trailColor{"#E8B84A"};
        std::string travelerColor{"#FFFFFF"};
        float labelSize{40.f};
        int startFrame{10};
        int legFrames{30};        ///< frames to travel each leg
        int labelPopFrames{12};
        int inFrame{0};
        int sceneFrames{150};
    };

    struct RouteLayers {
        MotionLayerId card{0};
        MotionLayerId traveler{0};
    };

    /// Author the card, the drawing dots, the traveler and the labels.
    /// Throws std::invalid_argument on any out-of-range spec value.
    [[nodiscard]] RouteLayers addRouteDrawing(TemplateScene& scene,
                                              const RouteSpec& spec);

    /// Interpolated route position at `frame` (polyline, eased per leg).
    /// Pure function of the spec; the traveler keys mirror it.
    [[nodiscard]] chrononmotion::Vector2 routePosition(const RouteSpec& spec, int frame);

    /// Frames needed to travel the whole route.
    [[nodiscard]] int routeTravelFrames(const RouteSpec& spec);

    [[nodiscard]] const char* routeDrawingId() noexcept;

} // namespace chronontemplate::docfx

#endif // CHRONONTEMPLATE_ROUTE_DRAWING_PACK_HPP
