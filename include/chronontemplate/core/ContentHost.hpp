// ChrononTemplate — the Chronon-side contract.
//
// This module never owns bytes, fonts, layout or rasterization: it asks Chronon
// to create content and to measure it, and Chronon answers with an identity plus
// a neutral rectangle. The interface is abstract so the module keeps compiling
// without the renderer, and so the host can be the real Chronon engine, the C
// ABI, or a test double.

#ifndef CHRONONTEMPLATE_CONTENT_HOST_HPP
#define CHRONONTEMPLATE_CONTENT_HOST_HPP

#include "chrononmotion/motion/Content.hpp"
#include "chrononmotion/math/Vector2.hpp"

#include <chronon3d/graphics/field2d.hpp>
#include <chronon3d/graphics/gradient_mesh.hpp>
#include <chronon3d/graphics/gradient.hpp>

#include "chronontemplate/core/ContentBinding.hpp"

#include <cstdint>
#include <optional>
#include <stdexcept>
#include <string>
#include <vector>

namespace chronontemplate {

    enum class ImageFitMode : std::uint8_t { Contain, Cover, Stretch, None };

    struct ImageCrop {
        bool enabled{false};
        chrononmotion::Vector2 origin{0.f, 0.f};
        chrononmotion::Vector2 size{1.f, 1.f};
        bool flipX{false};
    };

    /// Explicit renderer-facing text treatments. ChrononTemplate keeps these
    /// values declarative; the connected RenderPlan host serializes them into
    /// Chronon's canonical text-style contract.
    struct TextStrokeStyle {
        std::string color{"#111827"};
        float width{0.f};
    };

    struct TextShadowStyle {
        std::string color{"#000000"};
        float opacity{0.68f};
        float blur{8.f};
        chrononmotion::Vector2 offset{0.f, 3.f};
    };

    struct TextGlowStyle {
        std::string color{"#FFFFFF"};
        float radius{0.f};
        float intensity{0.25f};
    };

    struct TextBackgroundStyle {
        std::string color{"#07121A"};
        float opacity{0.8f};
        float radius{12.f};
        chrononmotion::Vector2 padding{12.f, 8.f};
    };

    /// What the template wants written. The fields mirror Chronon's authoring
    /// vocabulary; the module keeps them as data and hands them over untouched.
    struct TextRequest {
        std::string text{};
        std::string font{};
        float fontSize{48.f};
        std::string color{"#FFFFFF"};
        chrononmotion::Vector2 canvas{1920.f, 1080.f};
        std::optional<TextStrokeStyle> stroke{};
        std::optional<TextShadowStyle> shadow{};
        std::optional<TextGlowStyle> glow{};
        std::optional<TextBackgroundStyle> background{};
    };

    struct ImageRequest {
        std::string path{};
        /// Chronon applies this frame mask to the content it creates. A zero
        /// radius is square; larger radii produce rounded corners. Border width
        /// is in px and zero disables the stroke.
        float cornerRadius{0.f};
        std::string borderColor{};
        float borderWidth{0.f};
        /// Existing Chronon image placement and image-effect inputs. A host
        /// should include these rendering values in its content fingerprint.
        ImageFitMode fit{ImageFitMode::Contain};
        chrononmotion::Vector2 targetSize{};
        ImageCrop crop{};
        float saturation{1.f};
        float contrast{1.f};
        float grain{0.f};
        float vignette{0.f};
        std::uint32_t grainSeed{0};
    };

    enum class ShapeGeometry : std::uint8_t { Rectangle, Ellipse, Grid, DotGrid, Polygon };

    struct ShapeGradientStop {
        float position{0.f};
        std::string color{"#FFFFFF"};
        float opacity{1.f};
    };

    /// Renderer-neutral radial fill, lowered to Chronon's native shape gradient.
    struct ShapeRadialGradient {
        chrononmotion::Vector2 center{0.5f, 0.5f};
        float radius{0.5f};
        std::vector<ShapeGradientStop> stops{};
    };

    /// Native procedural shape owned by Chronon. It is still exposed to Motion
    /// as ordinary measured content, so transform and opacity use the same path
    /// as image layers.
    struct ShapeRequest {
        chrononmotion::Vector2 size{};
        std::string fillColor{"#FFFFFF"};
        std::string name{};
        float cornerRadius{0.f};
        bool fillEnabled{true};
        ShapeGeometry geometry{ShapeGeometry::Rectangle};
        std::optional<ShapeRadialGradient> radialGradient{};
        // Additive native procedural-geometry inputs. Defaults preserve existing aggregates.
        float gridSpacing{24.f};
        float dotRadius{3.f};
        std::string strokeColor{};
        float strokeWidth{1.f};
        int polygonPoints{6};
        float polygonRotationDegrees{0.f};
        std::optional<chronon3d::graphics::Field2D> field{};
        std::optional<chronon3d::graphics::GradientDefinition> fieldRamp{};
        std::uint32_t fieldRenderScale{1};
        std::optional<chronon3d::Vec2> fieldDrift{};
        std::optional<chronon3d::graphics::GradientMesh> gradientMesh{};
        float noiseAmount{0.f};
        std::uint32_t noiseSeed{0};
        bool animatedNoise{false};
        float noiseSize{1.f};
        float contrast{1.f};
    };

    struct VideoRequest {
        std::string path{};
    };

    /// Chronon's answer: the identity it minted plus the measurement it took.
    /// `metrics.fingerprint` is the digest of the exact bytes and style the
    /// rectangle came from — the motion side carries it and never interprets it.
    struct ContentHandle {
        ContentId id{};
        /// Numeric identity minted by Chronon for the ADR-032 C boundary.
        /// Zero means that this host is not connected to the ABI adapter.
        std::uint64_t wireId{0};
        chrononmotion::motion::ContentKind kind{chrononmotion::motion::ContentKind::None};
        chrononmotion::motion::ContentMetrics metrics{};

        [[nodiscard]] bool empty() const { return id.empty(); }
    };

    /// The Chronon surface this module depends on: content creation and
    /// measurement belong to Chronon, while this module only checks whether the
    /// carried measurements are still current.
    class ContentHost {
    public:
        virtual ~ContentHost() = default;

        [[nodiscard]] virtual ContentHandle createText(const TextRequest& request) = 0;
        [[nodiscard]] virtual ContentHandle createImage(const ImageRequest& request) = 0;
        [[nodiscard]] virtual ContentHandle createVideo(const VideoRequest& request) = 0;

        /// Hosts that support native shape content override this. Keeping the
        /// default explicit lets existing image/text/video-only hosts continue
        /// to work and fail clearly when a template requests a shape.
        [[nodiscard]] virtual ContentHandle createShape(const ShapeRequest&) {
            throw std::logic_error("ContentHost: native shape content is not supported by this host");
        }

        /// Digest of the content Chronon holds under `content` right now. A digest
        /// that differs from the one carried by a `ContentRef` is the only way a
        /// re-measured asset can be detected instead of silently mis-anchored.
        [[nodiscard]] virtual std::string currentFingerprint(const ContentId& content) const = 0;
    };

}// namespace chronontemplate

#endif//CHRONONTEMPLATE_CONTENT_HOST_HPP
