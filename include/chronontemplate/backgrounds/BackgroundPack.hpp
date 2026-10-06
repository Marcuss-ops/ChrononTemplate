// ChrononTemplate — the background pack: full-frame looks behind the content.
//
// A background here is composed from ordinary procedural shape layers (a ground,
// optional accent blocks, bars, a seam), each with its own entrance and exit.
// The pack authors no pixels and owns no shader: Chronon rasterizes each shape,
// exactly like every other layer in the module.
//
// The looks are editorial data; `backgroundLookId` is the stable, catalog-facing
// name and is append-only.

#ifndef CHRONONTEMPLATE_BACKGROUNDS_BACKGROUND_PACK_HPP
#define CHRONONTEMPLATE_BACKGROUNDS_BACKGROUND_PACK_HPP

#include "chronontemplate/core/TemplateScene.hpp"

#include <array>
#include <cstdint>
#include <string>
#include <vector>

namespace chronontemplate {

    /// The full-frame looks the pack can assemble.
    enum class BackgroundLook : std::uint8_t {
        SolidTint,      ///< one flat ground layer
        LetterboxBars,  ///< a tinted ground with top and bottom bars
        VerticalSplit,  ///< two tinted halves with a bright seam between them
        VignettePulse,  ///< a ground plus a soft layer that breathes over it
        CornerGlow,     ///< a ground plus a soft accent block in the top-left
        DocumentaryGrid, ///< restrained technical grid with editorial hierarchy
        RadarSweep,      ///< a coordinate grid with a traveling scan band
        ArchiveDust,     ///< dark archive plate with deterministic drifting dust
        MeshGradient,    ///< animated color fields built from native radial gradients
        GridPattern,     ///< configurable grid with optional highlighted cells
        Particles,       ///< deterministic canvas particles with gentle drift
        Aurora,           ///< simplex-driven color curtain (native Field2D approximation)
        DarkVeil,         ///< warped low-frequency veil with deterministic scan/grain controls
        DotGrid,          ///< native regular dot field
        DotField,         ///< native dot field with temporal wave and glow accents
        GradientWaves,    ///< layered native scalar-field waves
        Grainient,        ///< warped three-color field with seeded grain treatment
        RippleGrid,       ///< native grid with traveling scan/ripple accents
        ShapeGrid,        ///< moving native polygon/square/circle grid
        Silk              ///< flowing folded field with optional light treatment
    };

    struct AuroraBackgroundOptions {
        std::array<std::string, 3> colorStops{"#5227FF", "#7CFF67", "#5227FF"};
        float amplitude{1.f};
        float blend{0.5f};
        float speed{1.f};
        bool lightMode{false};
    };
    struct DarkVeilBackgroundOptions {
        float hueShift{0.f};
        float noiseIntensity{0.f};
        float scanlineIntensity{0.f};
        float speed{0.5f};
        float scanlineFrequency{0.f};
        float warpAmount{0.f};
        float resolutionScale{1.f};
        bool lightMode{false};
    };
    struct DotBackgroundOptions {
        float dotSize{16.f};
        float gap{32.f};
        float dotRadius{1.5f};
        float dotSpacing{32.f};  ///< validated against the 4096-dot native budget
        float waveAmplitude{0.f};
        float glowRadius{160.f};
        float bulgeStrength{67.f};
        std::string baseColor{"#5227FF"};
        std::string activeColor{"#7C3AED"};
        float cursorRadius{500.f};
        float cursorForce{0.1f};
        bool bulgeOnly{true};
        bool sparkle{false};
    };
    struct GradientWavesBackgroundOptions {
        std::array<std::string, 3> colors{"#5227FF", "#FF9FFC", "#FFFFFF"};
        float speed{0.4f};
        float amplitude{2.5f};
        float waveScale{0.6f};
        float waveRatio{0.9f};
        float swell{35.f};
        float turbulence{20.f};
        float tilt{1.11f};
        float zoom{1.f};
        float height{5.5f};
        float fogDepth{15.f};
        float opacity{1.f};
        float grainIntensity{0.05f};
        int detail{1}; ///< 0 low, 1 medium, 2 high native field sampling
        bool grain{true};
        bool lightMode{false};
    };
    struct GrainientBackgroundOptions {
        std::array<std::string, 3> colors{"#FF9FFC", "#5227FF", "#B497CF"};
        float timeSpeed{0.25f};
        float warpStrength{1.f};
        float warpFrequency{5.f};
        float grainAmount{0.1f};
        float contrast{1.5f};
        float gamma{1.f};
        float blendAngle{0.f};
        float blendSoftness{0.05f};
        float rotationAmount{500.f};
        float noiseScale{2.f};
        float grainScale{2.f};
        float colorBalance{0.f};
        float centerX{0.f};
        float centerY{0.f};
        float zoom{0.9f};
        bool grainAnimated{false};
        bool lightMode{false};
    };
    struct RippleGridBackgroundOptions {
        std::string gridColor{"#FFFFFF"};
        float rippleIntensity{0.05f};
        float mouseInteractionRadius{1.f};
        bool mouseInteraction{true};
        float gridSize{10.f};
        float gridThickness{1.5f};
        float fadeDistance{1.5f};
        float glowIntensity{0.1f};
        float opacity{1.f};
        float rotationDegrees{0.f};
        bool enableRainbow{false};
        bool lightMode{false};
    };
    struct ShapeGridBackgroundOptions {
        enum class Shape : std::uint8_t { Square, Hexagon, Circle, Triangle };
        Shape shape{Shape::Square};
        float squareSize{40.f};
        float speed{1.f};
        enum class Direction : std::uint8_t { Diagonal, Up, Right, Down, Left };
        Direction direction{Direction::Right};
        std::string borderColor{"#999999"};
        std::string hoverFillColor{"#222222"};
        int hoverTrailAmount{0};
    };
    struct SilkBackgroundOptions {
        float speed{5.f};
        float scale{1.f};
        std::string color{"#7B7481"};
        float noiseIntensity{1.5f};
        float rotation{0.f};
        bool lightMode{false};
    };

    struct BackgroundSpec {
        BackgroundLook look{BackgroundLook::SolidTint};
        std::string ground{"#0B0E14"};
        std::string accent{"#1B2330"};
        std::string seam{"#00E5FF"};
        float barFraction{0.08f};  ///< letterbox bar height as a fraction of the canvas
        float pulse{0.06f};        ///< opacity delta of a breathing layer
        std::string name{"background"};
        int inFrame{0};
        int duration{150};
        // Additive documentary-look tuning; appended to preserve aggregate order.
        float gridSpacing{96.f};   ///< requested minor-grid spacing in logical px
        float gridOpacity{0.14f};  ///< minor-grid opacity; major lines use seam color
        float scanOpacity{0.42f};  ///< radar scan-band opacity
        int majorEvery{4};         ///< every Nth grid line is emphasized
        int particleCount{36};     ///< ArchiveDust dots, validated in [0, 256]
        std::string particleColor{"#FFFFFF"}; ///< Particle and ArchiveDust fill color
        float particleSize{0.4f};  ///< Particles base diameter in logical pixels
        int particleQuantity{96};  ///< Particles count, validated in [0, 96]
        float particleVx{0.f};     ///< Particles horizontal velocity in px/frame
        float particleVy{0.f};     ///< Particles vertical velocity in px/frame
        float particleSpread{10.f};
        float particleSpeed{0.1f};
        float particleSizeRandomness{1.f};
        float particleHoverFactor{1.f}; ///< mapped to deterministic temporal drift offline
        float particleCameraDistance{20.f};
        bool moveParticlesOnHover{false};
        bool alphaParticles{false};
        bool disableRotation{false};
        std::vector<std::string> particleColors{}; ///< optional seeded palette for the React Particles port
        float meshSpeed{1.f};      ///< MeshGradient animation speed multiplier
        std::vector<std::array<int, 2>> gridSquares{}; ///< optional filled GridPattern cells
        float gridSpacingY{0.f};   ///< GridPattern row spacing; zero uses gridSpacing
        float gridOffsetX{0.f};    ///< GridPattern horizontal origin offset
        float gridOffsetY{0.f};    ///< GridPattern vertical origin offset
        std::array<std::string, 4> meshColors{
                "#7C3AED", "#2563EB", "#06B6D4", "#8B5CF6"};
        std::string meshBackgroundColor{"#030014"};
        // Native C++ ports of the ten supplied React background effects.
        AuroraBackgroundOptions aurora{};
        DarkVeilBackgroundOptions darkVeil{};
        DotBackgroundOptions dots{};
        GradientWavesBackgroundOptions gradientWaves{};
        GrainientBackgroundOptions grainient{};
        RippleGridBackgroundOptions rippleGrid{};
        ShapeGridBackgroundOptions shapeGrid{};
        SilkBackgroundOptions silk{};
        std::uint32_t seed{0xC0FFEEu};
    };

    /// What the pack authored. `ground` is always present; `accents` holds the
    /// look's extra layers in authoring order.
    struct BackgroundComposition {
        LayerHandle* ground{nullptr};
        std::vector<LayerHandle*> accents{};
        int inFrame{0};
        int endFrame{0};
    };

    /// Stable snake-case id of a look (the catalog/consumer-facing name).
    [[nodiscard]] const char* backgroundLookId(BackgroundLook look) noexcept;

    /// Every look in canonical order, for catalogs and contract tests.
    [[nodiscard]] std::vector<BackgroundLook> backgroundLooks();

    /// Build the look into `scene`, filling the canvas. Throws
    /// `std::invalid_argument` for invalid timing, opacity, grid density/cadence,
    /// mesh colors/speed, or particle settings. React-inspired looks are bounded,
    /// deterministic native Chronon shapes, scalar fields, meshes and gradients;
    /// pointer interactions are represented by seeded time-based motion.
    [[nodiscard]] BackgroundComposition addBackground(TemplateScene& scene,
                                                      const BackgroundSpec& spec);

}// namespace chronontemplate

#endif//CHRONONTEMPLATE_BACKGROUNDS_BACKGROUND_PACK_HPP
