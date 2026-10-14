#pragma once

#include "chronontemplate/core/NativePrimitives.hpp"
#include <cstdint>

namespace chronontemplate::native {

struct GrainBand {
    float size{1.5f};
    float weight{1.f};
};

struct ProceduralBackgroundSpec {
    std::string preset{"modern_dark_flow"};
    int width{1920};
    int height{1080};
    int fps{30};
    int frames{150};
    std::uint32_t seed{12045};
    std::vector<GrainBand> bands{{1.5f, .45f}, {5.f, .35f}, {22.f, .20f}};
    float grainOpacity{.035f};
    unsigned lineCount{65};
    std::array<float, 2> widthRange{.5f, 2.5f};
    std::array<float, 2> lengthRange{120.f, 900.f};
    float speed{.12f};
    float orientationRadians{0.f};
    float curvature{3.f};
    float distortion{1.f};
    std::string lineColor{"#72CFFF"};
    float lineOpacity{.32f};
    float glowRadius{0.f};
    float blurRadius{0.f};
    float tailFraction{1.f};
    int revealFrames{25};
};

[[nodiscard]] Json grainBands(const std::vector<GrainBand>& bands, float opacity,
                               std::uint32_t seed, bool animated = true);
[[nodiscard]] std::vector<std::string> proceduralBackgroundPresets();
[[nodiscard]] Json proceduralBackground(const ProceduralBackgroundSpec& spec);

} // namespace chronontemplate::native
