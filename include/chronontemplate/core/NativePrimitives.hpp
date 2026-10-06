// C++ authoring helpers for values consumed by Chronon3D's RenderPlan V3.
// These are composition builders: sampling, validation and rasterization stay
// with the canonical Chronon3D render-plan pipeline.
#pragma once

#include <nlohmann/json.hpp>

#include <array>
#include <string>
#include <vector>

namespace chronontemplate::native {

    using Json = nlohmann::json;

    struct Keyframe {
        int frame{0};
        Json value{};
    };

    class Material {
    public:
        [[nodiscard]] static std::array<float, 4> rgba(const std::string& hex, float alpha = 1.f);
        [[nodiscard]] static Json inlineMesh(float diffuse = 0.92f, float specular = 0.12f,
                                             float shininess = 10.f, float rimIntensity = 0.08f);
    };

    class Effects {
    public:
        [[nodiscard]] static Json noise(float amount, unsigned seed, float size = 1.f);
    };

    class Geometry {
    public:
        [[nodiscard]] static Json box(float width, float height, float depth);
        [[nodiscard]] static Json boxLayer(const std::string& id,
                                           const std::array<float, 3>& dimensions,
                                           const std::array<float, 3>& position,
                                           const std::string& color,
                                           int durationFrames,
                                           const std::array<float, 3>& rotation = {0.f, 0.f, 0.f});
    };

    class Motion {
    public:
        [[nodiscard]] static Json track(const std::string& property,
                                        const std::vector<Keyframe>& keys,
                                        const std::string& easing = "linear");
    };

    class Paths {
    public:
        using Point = std::array<float, 2>;
        [[nodiscard]] static Json polyline(const std::vector<Point>& points);
        [[nodiscard]] static Json trim(int startFrame, int endFrame);
        [[nodiscard]] static Json strokeLayer(const std::string& id, const Json& commands,
                                              int startFrame, int endFrame, int durationFrames,
                                              const std::string& color = "#F7F2DE", float width = 9.f,
                                              int canvasWidth = 1920, int canvasHeight = 1080,
                                              const Json& opacityKeys = Json::array());
    };

    class Camera {
    public:
        [[nodiscard]] static Json perspective(const std::array<float, 3>& position = {0.f, 0.f, -2300.f},
                                             const std::array<float, 3>& rotationDeg = {0.f, 0.f, 0.f},
                                             float fovDeg = 43.f, float nearPlane = 1.f,
                                             float farPlane = 10000.f, float zoom = 1.f);
        [[nodiscard]] static Json animation(const Json& tracks);
    };

    class Particles {
    public:
        [[nodiscard]] static Json emitterLayer(const std::string& id, int count, unsigned seed,
                                                int durationFrames, const std::array<float, 2>& emitterSize,
                                                const std::array<float, 2>& velocityMin,
                                                const std::array<float, 2>& velocityMax,
                                                const std::array<float, 2>& lifetime,
                                                const std::array<float, 2>& size,
                                                const Json& colorRamp,
                                                const std::array<float, 3>& position = {0.f, 0.f, 0.f},
                                                int startFrame = 0, float gravity = 0.f,
                                                float turbulence = 0.f);
    };

    class Text {
    public:
        [[nodiscard]] static Json layer(const std::string& id, const std::string& content,
                                        const std::array<float, 3>& position,
                                        const std::array<float, 2>& size,
                                        const std::string& font, float fontSize,
                                        const std::string& fill, int durationFrames,
                                        int startFrame = 0);
    };

    class TemplateComposition {
    public:
        [[nodiscard]] static Json renderPlan(const std::string& jobId, int width, int height,
                                            int fps, int durationFrames, const Json& layers,
                                            const Json& camera = nullptr,
                                            const Json& cameraAnimation = nullptr,
                                            const Json& output = nullptr);
    };

    /// Full renderer-native canary composed from the public primitives above.
    [[nodiscard]] Json buildBlackboardTortureV1();

} // namespace chronontemplate::native
