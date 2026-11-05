// ChrononTemplate — minimal map effects.
//
// The four treatments here are the lightweight subset of the map work in
// ChrononPlugin: rings, crosshairs, a beam and a connecting network. They draw
// only with primitives Chronon3d already renders (ellipse, rectangle, path,
// stroke, trim, glow and tracks), so a template can use them without the GPU
// map renderer, and RenderingGen can lower the same vocabulary at runtime.
//
// They are authoring recipes, not a second map renderer: the plate, the
// geographic projection and the markers remain owned by ModernMapPack.
#ifndef CHRONONTEMPLATE_MAP_FX_PACK_HPP
#define CHRONONTEMPLATE_MAP_FX_PACK_HPP

#include "chronontemplate/core/TemplateScene.hpp"

#include <cstdint>
#include <string>
#include <vector>

namespace chronontemplate {

enum class MapFxKind : std::uint8_t {
    AreaGlowPulse,
    RadarLocationReveal,
    LightBeamDrop,
    CityNetworkExpansion,
};

struct MapFxSpec {
    MapFxKind kind{MapFxKind::AreaGlowPulse};
    /// Delay from the map's inFrame. Zero starts with the map.
    int delayFrames{0};
    /// -1 uses the rest of the map's duration.
    int durationFrames{-1};
    std::string accent{"#38D9C5"};
    std::string secondary{"#F3C76A"};
    float intensity{1.f};
    float radius{110.f};
    float ringWidth{3.f};
    int ringCount{3};
};

struct MapFxComposition {
    std::vector<LayerHandle*> layers{};
    int inFrame{0};
    int endFrame{0};
};

/// The runtime id is the shared vocabulary: it matches the ChrononPlugin effect
/// name and the RenderingGen `map_fx` parameter.
[[nodiscard]] const char* mapFxId(MapFxKind kind) noexcept;
[[nodiscard]] std::vector<MapFxKind> mapFxKinds();
/// Throws std::invalid_argument for an unknown id.
[[nodiscard]] MapFxKind mapFxKindFromId(const std::string& id);
[[nodiscard]] const char* mapFxAnchorPolicy(MapFxKind kind) noexcept;

/// Adds the effect over already-positioned map anchors. Area/radar/beam take
/// exactly one anchor (the focused place); the network takes 2..8 anchors in
/// travel order. Throws std::invalid_argument on a bad spec or anchor count.
[[nodiscard]] MapFxComposition addMapFx(TemplateScene& scene, const MapFxSpec& spec,
                                        const std::vector<chrononmotion::Vector2>& anchors,
                                        int baseInFrame, int baseDuration);

} // namespace chronontemplate

#endif // CHRONONTEMPLATE_MAP_FX_PACK_HPP
