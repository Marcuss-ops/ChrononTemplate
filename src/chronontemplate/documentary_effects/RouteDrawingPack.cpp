#include "chronontemplate/documentary_effects/RouteDrawingPack.hpp"

#include <chronon3d/render_plan/color_utils.hpp>

#include <cmath>
#include <stdexcept>

namespace chronontemplate::docfx {

    namespace {

        void requireFinite(float value, const char* what) {
            if (!std::isfinite(value))
                throw std::invalid_argument(std::string("route: ") + what + " must be finite");
        }

        void validate(const RouteSpec& spec) {
            requireFinite(spec.cardWidth, "cardWidth");
            requireFinite(spec.cardHeight, "cardHeight");
            requireFinite(spec.cardCenterX, "cardCenterX");
            requireFinite(spec.cardCenterY, "cardCenterY");
            requireFinite(spec.dotRadius, "dotRadius");
            requireFinite(spec.travelerRadius, "travelerRadius");
            requireFinite(spec.labelSize, "labelSize");
            if (spec.waypoints.size() < 2 || spec.waypoints.size() > 8)
                throw std::invalid_argument("route: 2-8 waypoints are required");
            if (spec.cardWidth <= 0.f || spec.cardWidth > 1920.f ||
                spec.cardHeight <= 0.f || spec.cardHeight > 1080.f ||
                spec.dotsPerLeg < 2 || spec.dotsPerLeg > 40 ||
                spec.dotRadius <= 0.f || spec.dotRadius > 32.f ||
                spec.travelerRadius <= 0.f || spec.travelerRadius > 48.f ||
                spec.labelSize <= 0.f || spec.labelSize > 128.f ||
                spec.inFrame < 0 || spec.sceneFrames < 1 || spec.sceneFrames > 900 ||
                spec.startFrame < spec.inFrame || spec.legFrames < 5 ||
                spec.legFrames > 150 || spec.labelPopFrames < 1 || spec.labelPopFrames > 60)
                throw std::invalid_argument("route: spec is outside supported ranges");
            for (const auto& wp : spec.waypoints) {
                requireFinite(wp.x, "waypoint.x");
                requireFinite(wp.y, "waypoint.y");
                if (wp.x < 0.f || wp.x > 1920.f || wp.y < 0.f || wp.y > 1080.f ||
                    wp.label.empty() || wp.label.size() > 48)
                    throw std::invalid_argument("route: waypoints need on-canvas positions and short labels");
            }
            if (spec.startFrame + routeTravelFrames(spec) > spec.inFrame + spec.sceneFrames)
                throw std::invalid_argument("route: travel overflows the scene");
            if (!chronon3d::render_plan::parse_hex_color(spec.trailColor) ||
                !chronon3d::render_plan::parse_hex_color(spec.travelerColor))
                throw std::invalid_argument("route: colors must be #RRGGBB");
        }

        float ease(float p) {
            p = std::clamp(p, 0.f, 1.f);
            return p * p * (3.f - 2.f * p);
        }

    } // namespace

    int routeTravelFrames(const RouteSpec& spec) {
        return static_cast<int>(spec.waypoints.size() - 1) * spec.legFrames;
    }

    chrononmotion::Vector2 routePosition(const RouteSpec& spec, int frame) {
        if (spec.waypoints.empty()) return chrononmotion::Vector2(0.f, 0.f);
        if (frame <= spec.startFrame) {
            const auto& w = spec.waypoints.front();
            return chrononmotion::Vector2(w.x, w.y);
        }
        const int travel = routeTravelFrames(spec);
        if (frame >= spec.startFrame + travel) {
            const auto& w = spec.waypoints.back();
            return chrononmotion::Vector2(w.x, w.y);
        }
        const int elapsed = frame - spec.startFrame;
        const std::size_t leg = static_cast<std::size_t>(elapsed / spec.legFrames);
        const float p = ease(static_cast<float>(elapsed % spec.legFrames) /
                             static_cast<float>(spec.legFrames));
        const auto& a = spec.waypoints[leg];
        const auto& b = spec.waypoints[leg + 1];
        return chrononmotion::Vector2(a.x + (b.x - a.x) * p, a.y + (b.y - a.y) * p);
    }

    RouteLayers addRouteDrawing(TemplateScene& scene, const RouteSpec& spec) {
        validate(spec);
        const int endFrame = spec.inFrame + spec.sceneFrames;
        RouteLayers out{};

        if (!spec.mapAsset.empty()) {
            LayerHandle& card = scene.image(ImageSpec{
                    .path = spec.mapAsset, .name = "route_map",
                    .fit = ImageFitMode::Cover,
                    .targetSize = chrononmotion::Vector2(spec.cardWidth, spec.cardHeight)});
            card.position(spec.cardCenterX, spec.cardCenterY);
            card.alive(spec.inFrame, endFrame);
            card.animate(FadeIn{.inFrame = spec.inFrame, .duration = 16});
            card.animate(FadeOut{.startFrame = endFrame - 16, .duration = 16});
            out.card = card.id();
        } else {
            LayerHandle& plate = scene.shape(ShapeSpec{
                    .size = chrononmotion::Vector2(spec.cardWidth, spec.cardHeight),
                    .fillColor = "#10151F", .name = "route_plate", .cornerRadius = 24.f});
            plate.position(spec.cardCenterX, spec.cardCenterY);
            plate.alive(spec.inFrame, endFrame);
            plate.animateOpacity(spec.inFrame, 16, 0.f, 1.f);
            plate.animateOpacity(endFrame - 16, 16, 1.f, 0.f);
            out.card = plate.id();
        }

        // Trail dots draw the route leg by leg, each popping as passed.
        const std::size_t legs = spec.waypoints.size() - 1;
        for (std::size_t leg = 0; leg < legs; ++leg) {
            const auto& a = spec.waypoints[leg];
            const auto& b = spec.waypoints[leg + 1];
            for (int d = 0; d <= spec.dotsPerLeg; ++d) {
                const float t = static_cast<float>(d) / static_cast<float>(spec.dotsPerLeg);
                const int onset = spec.startFrame + static_cast<int>(leg) * spec.legFrames +
                    static_cast<int>(t * spec.legFrames);
                LayerHandle& dot = scene.shape(ShapeSpec{
                        .size = chrononmotion::Vector2(spec.dotRadius * 2.f,
                                                       spec.dotRadius * 2.f),
                        .fillColor = spec.trailColor,
                        .name = "route_dot_" + std::to_string(leg) + "_" + std::to_string(d),
                        .geometry = ShapeGeometry::Ellipse});
                dot.position(a.x + (b.x - a.x) * t, a.y + (b.y - a.y) * t);
                dot.alive(onset, endFrame);
                dot.animate(ScalePop{.inFrame = onset, .duration = 10, .from = 0.2f, .to = 1.f});
            }
        }

        // Traveler rides the whole route with keyed position tracks.
        {
            const auto& w0 = spec.waypoints.front();
            LayerHandle& traveler = scene.shape(ShapeSpec{
                    .size = chrononmotion::Vector2(spec.travelerRadius * 2.f,
                                                   spec.travelerRadius * 2.f),
                    .fillColor = spec.travelerColor,
                    .name = "route_traveler", .geometry = ShapeGeometry::Ellipse});
            traveler.position(w0.x, w0.y);
            traveler.alive(spec.startFrame, spec.startFrame + routeTravelFrames(spec) + 20);
            auto& track = traveler.layer().tracks.position;
            const float fps = scene.fps();
            for (int f = 0; f <= routeTravelFrames(spec); f += 5) {
                const auto pos = routePosition(spec, spec.startFrame + f);
                track.add(static_cast<float>(spec.startFrame + f) / fps,
                          chrononmotion::Vector3(pos.x, pos.y, 0.f),
                          f == 0 ? chrononmotion::motion::Easing::linear()
                                 : chrononmotion::motion::Easing::easeInOut());
            }
            out.traveler = traveler.id();
        }

        // Place labels pop as the traveler arrives.
        for (std::size_t i = 0; i < spec.waypoints.size(); ++i) {
            const auto& wp = spec.waypoints[i];
            const int onset = spec.startFrame + static_cast<int>(i) * spec.legFrames;
            LayerHandle& label = scene.text(TextSpec{
                    .text = wp.label, .fontSize = spec.labelSize,
                    .color = "#F5F2EA", .name = "route_label_" + std::to_string(i)});
            label.position(wp.x, wp.y - spec.travelerRadius * 3.f);
            label.alive(onset, endFrame);
            label.animate(ScalePop{.inFrame = onset, .duration = spec.labelPopFrames,
                                   .from = 0.5f, .to = 1.f});
            label.animate(FadeIn{.inFrame = onset, .duration = 8});
        }
        return out;
    }

    const char* routeDrawingId() noexcept {
        return "docfx_route_drawing_v1";
    }

} // namespace chronontemplate::docfx
