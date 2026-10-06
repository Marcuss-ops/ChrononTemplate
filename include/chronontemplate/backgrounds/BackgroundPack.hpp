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
        CornerGlow      ///< a ground plus a soft accent block in the top-left
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
    /// `std::invalid_argument` on a non-positive duration, a bar fraction
    /// outside [0, 0.5), or a pulse outside [0, 1].
    [[nodiscard]] BackgroundComposition addBackground(TemplateScene& scene,
                                                      const BackgroundSpec& spec);

}// namespace chronontemplate

#endif//CHRONONTEMPLATE_BACKGROUNDS_BACKGROUND_PACK_HPP
