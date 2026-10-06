// ChrononTemplate — C++ composition presets built on ChrononMotion.
//
// This module owns composition recipes. ChrononMotion remains the space/time
// runtime and Chronon remains the content authority.

#ifndef CHRONONTEMPLATE_PRESETS_HPP
#define CHRONONTEMPLATE_PRESETS_HPP

#include "chrononmotion/materials/Descriptors.hpp"
#include "chrononmotion/motion/MotionScene.hpp"
#include "chrononmotion/motion/CameraRig.hpp"
#include "chrononmotion/templates/Templates.hpp"

#include <array>
#include <map>
#include <string>
#include <vector>

namespace chronontemplate {

    /// The font a text layer is rendered with, declared by the recipe and
    /// resolved by the content side through its own asset resolver. The module
    /// never touches the font file: it states which one and at what authored
    /// size, the way `material` states colour and strength.
    struct TextStyleDeclaration {
        /// Asset-relative font path (e.g. "assets/fonts/Inter-Bold.ttf"),
        /// resolved by the content side — never the process CWD.
        std::string font{};
        /// Authored font size in px for the canvas the composition declares.
        float font_size{0.f};

        [[nodiscard]] bool empty() const noexcept { return font.empty() || !(font_size > 0.f); }
    };

    /// Canonical canvas-style phrase appearance used by native Chronon3D
    /// projections.  It is the black_glow font-canary look: pure black,
    /// white face, white halo, and a centred 1700x360 text box.  Motion
    /// recipes may animate this layer, but they must not replace this style.
    /// The font remains configurable so the five approved font variants can
    /// share exactly the same visual contract.
    struct NativePhraseStyle {
        std::string font{"assets/fonts/Inter-Bold.ttf"};
        float font_size{190.f};
        std::array<float, 2> box{1700.f, 360.f};
        std::array<float, 2> position{960.f, 540.f};
        std::array<float, 4> background{0.f, 0.f, 0.f, 1.f};
        std::string fill{"#FFFFFF"};
        std::string stroke{"#FFFFFF"};
        float stroke_width{0.f};
        std::string glow{"#FFFFFF"};
        float glow_radius{42.f};
        float glow_intensity{0.25f};
    };

    [[nodiscard]] NativePhraseStyle nativePhraseStyle();

    struct Composition {
        chrononmotion::motion::MotionScene scene;
        chrononmotion::motion::CameraRig camera;
        /// How the composition should be lit, declared once. An emissive
        /// descriptor means the composition lights its own colour and its
        /// `emissiveStrength` says how much — a consumer renders the glow from
        /// the declaration, and one that ignores the material still draws a
        /// correct, if flat, composition.
        chrononmotion::MaterialDescriptor material;
        /// The font every text layer the recipe created is rendered with,
        /// keyed by layer id. A text layer without a row here is a recipe
        /// defect: the content side would have to guess a font.
        std::map<chrononmotion::motion::Layer::Id, TextStyleDeclaration> textStyles{};
    };

    struct Final3DData {
        std::string title{"CHRONON"};
        std::string subtitle{"MOTION ENGINE"};
        std::string assetId{"product.asset"};
        /// The real faces the title and subtitle are rendered with,
        /// asset-relative and resolved by the content side. The defaults are
        /// the canonical Inter assets the content engine ships.
        std::string titleFont{"assets/fonts/Inter-Bold.ttf"};
        std::string subtitleFont{"assets/fonts/Inter-Regular.ttf"};
        float fps{30.f};
        int startFrame{0};
        int duration{120};

        void validate() const;
    };

    enum class Final3DPreset {
        LogoReveal,
        ProductOrbit,
        TitleCard3D,
        CameraPush,
        LightPulse,
        MacBookProduct,
        Typewriter3DGlow,
        CleanRed,
        YouTubeCanary,
        TextStatic,
        TextDollyOrbitGlow
    };

    [[nodiscard]] const char* name(Final3DPreset preset);
    [[nodiscard]] std::vector<Final3DPreset> final3DPresets();
    [[nodiscard]] Composition build(Final3DPreset preset, const Final3DData& data = {});

    [[nodiscard]] chrononmotion::motion::MotionScene build(
            chrononmotion::templates::TemplateId preset,
            const chrononmotion::templates::TemplateData& data = {});

}// namespace chronontemplate

#endif//CHRONONTEMPLATE_PRESETS_HPP
