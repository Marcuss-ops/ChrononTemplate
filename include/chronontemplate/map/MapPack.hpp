// ChrononTemplate — the map pack: a map plate the camera moves over.
//
// A map animation is one image (the plate), optional markers and a title, plus
// a camera move that carries the audience across the plate. The subjects never
// animate: every key lands on the shared CameraRig, exactly like the title- and
// scene-camera packs do.
//
// The pack owns no camera math. Every move is lowered onto the ChrononMotion3D
// CameraRig channels; the named `map_*` ids are editorial vocabulary and
// deliberately live here, not in the motion core.

#ifndef CHRONONTEMPLATE_MAP_MAP_PACK_HPP
#define CHRONONTEMPLATE_MAP_MAP_PACK_HPP

#include "chronontemplate/core/TemplateScene.hpp"

#include "chrononmotion/math/Vector2.hpp"

#include <cstdint>
#include <string>
#include <vector>

namespace chronontemplate {

    /// The camera grammar of a map beat.
    enum class MapMotion : std::uint8_t {
        HoldStatic,      ///< map_hold_static — the plate just appears, the lens stays put
        DivePush,        ///< map_dive_push — push the lens toward the plate
        OrbitSettle,     ///< map_orbit_settle — a small orbit that settles on the plate
        LateralDrift,    ///< map_lateral_drift — pan across the plate, aimed ahead
        PullBackReveal   ///< map_pull_back_reveal — start tight, pull back to the whole plate
    };

    /// A labelled point on the plate, in canvas pixels.
    struct MapMarker {
        std::string label{};
        chrononmotion::Vector2 position{};
        float size{18.f};
        std::string color{"#FF3B30"};
    };

    struct MapSpec {
        std::string platePath{};
        std::string title{};
        std::vector<MapMarker> markers{};
        MapMotion motion{MapMotion::DivePush};
        chrononmotion::Vector2 plateSize{1920.f, 1080.f};
        int inFrame{0};
        int duration{150};
        std::string titleFont{"Inter-Bold.ttf"};
        float titleFontSize{96.f};
        std::string titleColor{"#FFFFFF"};
        float titleOffset{120.f};  ///< title baseline lift from the bottom edge
    };

    /// What the pack authored. The handles point into the scene's own handle
    /// storage, which is stable for the scene's lifetime.
    struct MapComposition {
        LayerHandle* plate{nullptr};
        std::vector<LayerHandle*> markers{};
        LayerHandle* title{nullptr};
        int inFrame{0};
        int endFrame{0};
    };

    /// Stable snake-case id of a motion (the catalog/consumer-facing name).
    [[nodiscard]] const char* mapMotionId(MapMotion motion) noexcept;

    /// Every motion in canonical order, for catalogs and contract tests.
    [[nodiscard]] std::vector<MapMotion> mapMotions();

    /// Author the plate, its markers, its title and the camera move onto
    /// `scene`. Throws `std::invalid_argument` on an empty plate path, a
    /// non-positive duration, a non-positive plate size, or a non-finite marker.
    [[nodiscard]] MapComposition addMapMotion(TemplateScene& scene, const MapSpec& spec);

}// namespace chronontemplate

#endif//CHRONONTEMPLATE_MAP_MAP_PACK_HPP
