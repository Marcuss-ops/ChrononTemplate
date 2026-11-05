// ChrononTemplate — native tactical territory fill.
//
// This is the shape-only sibling of the ChrononPlugin/OpenCV
// `territory_tactical_fill` treatment. It draws a dark tactical grid, a filled
// territory, a double glow, a crisp outline and its title with Chronon3d
// primitives and motion tracks. It does not read GeoJSON, project coordinates
// or run OpenCV: callers pass polygons already positioned in canvas space.
// Geographic projection and source provenance remain RenderingGen's concern.
#ifndef CHRONONTEMPLATE_TACTICAL_FILL_PACK_HPP
#define CHRONONTEMPLATE_TACTICAL_FILL_PACK_HPP

#include "chronontemplate/core/TemplateScene.hpp"
#include "chronontemplate/map/ModernMapPack.hpp"

#include <optional>
#include <string>
#include <vector>

namespace chronontemplate {

/// One closed territory ring in canvas coordinates (origin top-left).
/// Multiple rings are separate drawable territories; holes are not modelled.
struct TacticalFillRegion {
    std::vector<chrononmotion::Vector2> points{};
};

struct TacticalFillSpec {
    std::vector<TacticalFillRegion> regions{};
    std::string title{};
    std::string subtitle{};

    // The native plan writer does not serialize text stroke/shadow yet. Keep
    // the defaults representable; callers can still supply those declarations
    // for a consumer that supports them.
    MapTypography titleTypography{"Inter-Bold.ttf", 64.f, "#F6F9FC", {}, {}, {}, {}};
    MapTypography subtitleTypography{"Inter-Regular.ttf", 28.f, "#B8BDC3", {}, {}, {}, {}};

    /// Canvas-space centres for the two text layers. When unset the pack uses
    /// the left-hand editorial placement of the reference.
    std::optional<chrononmotion::Vector2> titlePosition{};
    std::optional<chrononmotion::Vector2> subtitlePosition{};

    int inFrame{0};
    int duration{120};

    /// The territory scales out of its centre over this fraction of the clip.
    /// This is a transform reveal, not the reference's circular mask raster.
    float revealFraction{0.72f};
    /// The title/subtitle fade in over this window, relative to the clip.
    float textRevealStart{0.42f};
    float textRevealEnd{0.62f};

    std::string background{"#07090C"};
    std::string minorGrid{"#20242B"};
    std::string majorGrid{"#30353E"};
    float gridSpacing{54.f};
    int majorGridEvery{4};

    std::string fill{"#24A62D"};
    std::string outline{"#F6F9FC"};
    std::string glow{"#FF2E1E"};
    std::string innerGlow{"#FF6A36"};
    float outlineWidth{4.f};
    float glowWidth{10.f};
    float glowRadius{34.f};
    float innerGlowWidth{6.f};
    float innerGlowRadius{12.f};
    float glowIntensity{1.4f};
};

struct TacticalFillTerritory {
    /// Per-layer reveal: scale grows from the ring centroid while the layer
    /// origin travels from centroid to bbox corner on the same curve.
    LayerHandle* outerGlow{nullptr};
    LayerHandle* innerGlow{nullptr};
    LayerHandle* fill{nullptr};
};

struct TacticalFillComposition {
    LayerHandle* background{nullptr};
    LayerHandle* minorGrid{nullptr};
    LayerHandle* majorGrid{nullptr};
    std::vector<TacticalFillTerritory> territories{};
    LayerHandle* title{nullptr};
    LayerHandle* subtitle{nullptr};
    int inFrame{0};
    /// Exclusive end of the authored window (the last drawn frame is endFrame-1).
    int endFrame{0};
};

/// The runtime vocabulary shared with the map renderer.
[[nodiscard]] const char* tacticalFillId() noexcept;

/// Adds the treatment to the scene. Throws std::invalid_argument on an empty
/// or malformed polygon, a colour outside #RRGGBB, or an impossible frame
/// window. No geographic projection is performed here.
[[nodiscard]] TacticalFillComposition addTacticalFill(
    TemplateScene& scene, const TacticalFillSpec& spec);

} // namespace chronontemplate

#endif // CHRONONTEMPLATE_TACTICAL_FILL_PACK_HPP
