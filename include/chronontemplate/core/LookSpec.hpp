// The closed look vocabulary a ChrononTemplate style may request.
//
// This is deliberately not a shader language: a style selects one known
// implementation and parameterizes it. A look with no backend implementation
// declares the capability it needs instead of falling back to a different one.

#ifndef CHRONONTEMPLATE_CORE_LOOKSPEC_HPP
#define CHRONONTEMPLATE_CORE_LOOKSPEC_HPP

#include <cstdint>
#include <string>
#include <string_view>

namespace chronontemplate {

    enum class Look : std::uint8_t {
        Pbr,
        Glass,
        Halftone,
        Toon,
        Pixelated
    };

    /// What a backend must provide before it may claim support for a look.
    struct LookCapabilities {
        bool transmission{false};
        bool customFragmentShader{false};
        bool reducedFramebuffer{false};
    };

    struct LookSpec {
        Look kind{Look::Pbr};
        /// Normalized strength in [0, 1]; 1 is the recipe's authored amount.
        float intensity{1.f};

        void validate() const;
    };

    /// Stable wire id, e.g. "glass". Never localized or renamed.
    [[nodiscard]] std::string_view lookId(Look look);

    /// Parse a look id; unknown ids throw std::invalid_argument.
    [[nodiscard]] Look parseLook(std::string_view id);

    [[nodiscard]] LookCapabilities lookCapabilities(Look look);

    /// Stable, deterministic identity for caches and manifests.
    [[nodiscard]] std::string lookFingerprint(const LookSpec& spec);

}// namespace chronontemplate

#endif// CHRONONTEMPLATE_CORE_LOOKSPEC_HPP
