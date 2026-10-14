#pragma once
#include "chronontemplate/core/NativePrimitives.hpp"

namespace chronontemplate::native {
struct HighlightRegion {
    float x{0}, y{0}, width{1}, height{1};
    [[nodiscard]] HighlightRegion mapped(const HighlightRegion& display,
                                         float sourceWidth, float sourceHeight) const;
};
struct HighlightTarget {
    std::string layerId;
    std::string semanticId;
    std::size_t byteStart{0}, byteEnd{0};
    HighlightRegion region{};
};
struct HighlightGroup {
    std::vector<HighlightTarget> targets;
    int staggerFrames{8};
};
struct HighlightStyle {
    std::string color{"#E8B84A"};
    float opacity{.35f};
    float width{3.f};
    float widthEm{0.f};
    bool rough{false};
    bool glow{false};
    bool dashed{false};
};
enum class RevealMode { Draw, Wipe, Sweep, Pulse, Trace, Scribble, Expand, FocusFollow, Stagger, Morph };
struct HighlightTiming {
    int start{0};
    int revealEnd{30};
    int frames{150};
    unsigned seed{12045};
};
/// Docus/Reacts premium multi-layer glow line (RenderPlan-native mirror of
/// elements::addGlowLine). Core is razor-sharp white; halos are wide, soft
/// and restrained. All motion is a deterministic function of frame.
struct CinematicGlowSpec {
    std::string coreColor{"#FFFFFF"};
    float coreWidth{2.f};
    std::string haloColor{"#72CFFF"};
    float haloWidth{12.f};
    std::string wideColor{"#1E90FF"};
    float wideWidth{36.f};
    bool headEnabled{true};
    float headRadius{4.5f};
    bool pulseEnabled{true};
    /// Fraction of the path visible at the reveal head (1 = full draw).
    float tailFraction{1.f};
    float glowIntensity{.7f};
    float bloomThreshold{.2f};
};
[[nodiscard]] Json cinematicPathStroke(const std::string& id,
                                        const std::vector<Paths::Point>& points,
                                        const CinematicGlowSpec& spec,
                                        const HighlightTiming& timing);
[[nodiscard]] std::vector<std::string> highlightingPresets();
[[nodiscard]] HighlightStyle highlightingStyle(const std::string& preset);
[[nodiscard]] Json highlightSpan(const std::string& text, std::size_t start, std::size_t end,
                                  const std::string& semanticId, const HighlightStyle& style);
[[nodiscard]] Json highlightStroke(const std::string& id, const std::vector<Paths::Point>& points,
                                    const HighlightStyle& style, int start, int end, int frames,
                                    float fontSize = 56.f, unsigned seed = 12045);
/// Gradient stroke: linear along-path gradient (sRGB authoring, linear-space
/// compositing stays renderer-side). Validates both endpoint colors.
[[nodiscard]] Json highlightStrokeGradient(const std::string& id,
                                            const std::vector<Paths::Point>& points,
                                            const std::string& fromColor,
                                            const std::string& toColor,
                                            const HighlightStyle& style,
                                            int start, int end, int frames,
                                            float fontSize = 56.f, unsigned seed = 12045);
/// Staggered group: one region-layer stack per target, offset by
/// staggerFrames. All motion stays a pure function of frame (no chaining).
[[nodiscard]] Json highlightGroupLayers(const std::string& id,
                                         const HighlightGroup& group,
                                         const std::string& preset,
                                         const HighlightTiming& base);
[[nodiscard]] Json revealAnimation(RevealMode mode, const HighlightTiming& timing,
                                    const Json& targetPath = nullptr);
/// Returns ordinary RenderPlan layers; polygons use canonical native masks.
[[nodiscard]] Json highlightRegionLayers(const std::string& id, const HighlightRegion& region,
                                          const std::string& preset, const HighlightTiming& timing = {});
[[nodiscard]] Json calloutConnector(const std::string& id, const Paths::Point& from,
                                     const Paths::Point& to, const std::string& preset,
                                     const HighlightTiming& timing = {});
[[nodiscard]] Json focusPolygon(const std::vector<Paths::Point>& polygon, float opacity,
                                 int frames, float feather = 8.f, int width = 1920, int height = 1080);
[[nodiscard]] Json focusDim(const HighlightRegion& region, float opacity, int frames,
                            int width = 1920, int height = 1080);
} // namespace chronontemplate::native
