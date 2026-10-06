// ChrononTemplate — modern editorial map compositions.
//
// This is the successor to MapPack: it composes an authored map plate, grounded
// marker shapes, independently styled marker labels and a title while keeping
// all camera movement on ChrononMotion's shared rig. Geographic projection and
// basemap provenance remain owned by RenderingGen's georeferenced map contract.
#ifndef CHRONONTEMPLATE_MODERN_MAP_PACK_HPP
#define CHRONONTEMPLATE_MODERN_MAP_PACK_HPP

#include "chronontemplate/core/TemplateScene.hpp"

#include <cstdint>
#include <optional>
#include <string>
#include <vector>

namespace chronontemplate {

enum class MapCameraMove : std::uint8_t {
    Hold, PushIn, OrbitSettle, LateralDrift, PullBack
};

struct MapTypography {
    std::string font{"Inter-Bold.ttf"};
    float fontSize{32.f};
    std::string color{"#FFFFFF"};
    std::optional<TextStrokeStyle> stroke{};
    std::optional<TextShadowStyle> shadow{TextShadowStyle{}};
    std::optional<TextGlowStyle> glow{};
    std::optional<TextBackgroundStyle> background{};
};

enum class MapTextRole : std::uint8_t {
    Title, PrimaryLocation, SecondaryLocation, DataValue, Legend, Attribution
};

struct MapTypographyRoles {
    MapTypography title{"Inter-Bold.ttf", 72.f, "#F8F5EA", {}, TextShadowStyle{}, {}, {}};
    MapTypography primaryLocation{"Inter-Bold.ttf", 30.f, "#F3C76A", TextStrokeStyle{"#07121A", 1.5f}, TextShadowStyle{}, {}, {}};
    MapTypography secondaryLocation{"Inter-Regular.ttf", 22.f, "#E8EEE9", {}, TextShadowStyle{}, {}, {}};
    MapTypography dataValue{"Inter-Bold.ttf", 40.f, "#FFFFFF", TextStrokeStyle{"#07121A", 1.f}, TextShadowStyle{}, {}, {}};
    MapTypography legend{"Inter-Regular.ttf", 20.f, "#E8EEE9", {}, TextShadowStyle{}, {}, {}};
    MapTypography attribution{"Inter-Regular.ttf", 14.f, "#C4D0CC", {}, TextShadowStyle{}, {}, {}};
};

struct MapDataCard {
    std::string heading{};
    std::string value{};
    chrononmotion::Vector2 position{};
    chrononmotion::Vector2 size{300.f, 132.f};
    std::string accent{"#69D7C6"};
};

struct MapLegendItem {
    std::string label{};
    std::string color{"#69D7C6"};
};

struct MapEditorialCallout {
    std::string label{};
    chrononmotion::Vector2 markerPosition{};
    chrononmotion::Vector2 elbowPosition{};
    chrononmotion::Vector2 textPosition{};
    std::string color{"#69D7C6"};
};

[[nodiscard]] MapTypography mapTypographyPreset(MapTextRole role);

struct MapPlaceMarker {
    std::string label{};
    chrononmotion::Vector2 position{};
    chrononmotion::Vector2 labelOffset{0.f, -34.f};
    float size{18.f};
    std::string color{"#38D9C5"};
    int priority{0};
    MapTextRole role{MapTextRole::PrimaryLocation};
    std::optional<MapTypography> typography{};
};

struct ModernMapSpec {
    std::string platePath{};
    std::string title{};
    std::vector<MapPlaceMarker> markers{};
    MapCameraMove cameraMove{MapCameraMove::PushIn};
    chrononmotion::Vector2 plateSize{1920.f, 1080.f};
    int inFrame{0};
    int duration{150};
    MapTypography titleTypography{MapTypographyRoles{}.title};
    MapTypography subtitleTypography{MapTypographyRoles{}.secondaryLocation};
    MapTypography attributionTypography{MapTypographyRoles{}.attribution};
    std::string subtitle{};
    std::string attribution{};
    std::vector<MapDataCard> dataCards{};
    std::vector<MapLegendItem> legend{};
    std::vector<MapEditorialCallout> callouts{};
    float titleOffset{112.f};
    float subtitleOffset{150.f};
};

struct ModernMapComposition {
    LayerHandle* plate{nullptr};
    std::vector<LayerHandle*> markers{};
    std::vector<LayerHandle*> labels{};
    std::vector<LayerHandle*> editorial{};
    LayerHandle* title{nullptr};
    LayerHandle* subtitle{nullptr};
    LayerHandle* attribution{nullptr};
    int inFrame{0};
    int endFrame{0};
};

[[nodiscard]] const char* mapCameraMoveId(MapCameraMove move) noexcept;
[[nodiscard]] std::vector<MapCameraMove> mapCameraMoves();
[[nodiscard]] ModernMapComposition composeModernMap(TemplateScene& scene, const ModernMapSpec& spec);

} // namespace chronontemplate

#endif // CHRONONTEMPLATE_MODERN_MAP_PACK_HPP
