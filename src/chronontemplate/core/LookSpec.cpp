#include "chronontemplate/core/LookSpec.hpp"

#include <cmath>
#include <cstdio>
#include <stdexcept>

namespace chronontemplate {

    namespace {

        void ensureFiniteIntensity(float intensity) {
            if (!std::isfinite(intensity) || intensity < 0.f || intensity > 1.f) {
                throw std::invalid_argument("LookSpec: intensity must be finite and in [0, 1]");
            }
        }

        std::string fixed(float value) {
            char buffer[32];
            std::snprintf(buffer, sizeof(buffer), "%.6f", static_cast<double>(value));
            return buffer;
        }

    }// namespace

    void LookSpec::validate() const {

        // lookId throws for an out-of-range enum value, which a reinterpret_cast
        // or a deserialization bug can produce.
        (void) lookId(kind);
        ensureFiniteIntensity(intensity);
    }

    std::string_view lookId(Look look) {

        switch (look) {
            case Look::Pbr: return "pbr";
            case Look::Glass: return "glass";
            case Look::Halftone: return "halftone";
            case Look::Toon: return "toon";
            case Look::Pixelated: return "pixelated";
        }
        throw std::invalid_argument("LookSpec: unknown look enumerator");
    }

    Look parseLook(std::string_view id) {

        if (id == "pbr") return Look::Pbr;
        if (id == "glass") return Look::Glass;
        if (id == "halftone") return Look::Halftone;
        if (id == "toon") return Look::Toon;
        if (id == "pixelated") return Look::Pixelated;
        throw std::invalid_argument("LookSpec: unknown look id '" + std::string(id) + "'");
    }

    LookCapabilities lookCapabilities(Look look) {

        LookCapabilities capabilities;
        switch (look) {
            case Look::Pbr:
                break;
            case Look::Glass:
                capabilities.transmission = true;
                break;
            case Look::Halftone:
            case Look::Toon:
                capabilities.customFragmentShader = true;
                break;
            case Look::Pixelated:
                capabilities.reducedFramebuffer = true;
                break;
        }
        return capabilities;
    }

    std::string lookFingerprint(const LookSpec& spec) {

        spec.validate();
        return "chronon.look.v1|" + std::string(lookId(spec.kind)) + "|" + fixed(spec.intensity);
    }

}// namespace chronontemplate
