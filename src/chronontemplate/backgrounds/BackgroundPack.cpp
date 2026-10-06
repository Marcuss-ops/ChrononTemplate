#include "chronontemplate/backgrounds/BackgroundPack.hpp"

#include <chronon3d/render_plan/color_utils.hpp>

#include <algorithm>
#include <cmath>
#include <limits>
#include <utility>
#include <vector>
#include <stdexcept>
#include <string>
#include <utility>

namespace chronontemplate {

    namespace {

        using chrononmotion::Vector2;

        [[nodiscard]] int exitFramesFor(int duration) {
            return std::max(1, std::min(18, duration / 8));
        }

        [[nodiscard]] float unitHash(unsigned value) {
            value = (value ^ 61u) ^ (value >> 16u);
            value *= 9u;
            value ^= value >> 4u;
            value *= 0x27d4eb2du;
            value ^= value >> 15u;
            return static_cast<float>(value & 0x00ffffffu) / 16777215.f;
        }

        [[nodiscard]] std::string lightenHex(const std::string& color, float amount) {
            const auto clampChannel = [](float value) {
                return static_cast<unsigned>(std::lround(std::clamp(value, 0.f, 255.f)));
            };
            unsigned rgb = static_cast<unsigned>(std::stoul(color.substr(1), nullptr, 16));
            unsigned result = 0;
            for (unsigned channel = 0; channel < 3; ++channel) {
                const float source = static_cast<float>((rgb >> ((2u - channel) * 8u)) & 0xffu);
                const unsigned mixed = clampChannel(source + (255.f - source) * std::clamp(amount, 0.f, 1.f));
                result |= mixed << ((2u - channel) * 8u);
            }
            constexpr char digits[] = "0123456789ABCDEF";
            std::string hex{"#000000"};
            for (unsigned i = 0; i < 6; ++i)
                hex[i + 1] = digits[(result >> ((5u - i) * 4u)) & 0xfu];
            return hex;
        }

        [[nodiscard]] std::uint32_t backgroundSeed(std::uint32_t seed, std::uint32_t salt) {
            std::uint32_t value = seed ^ salt;
            value ^= value >> 16u;
            value *= 0x7feb352du;
            value ^= value >> 15u;
            value *= 0x846ca68bu;
            return value ^ (value >> 16u);
        }

        [[nodiscard]] chronon3d::graphics::Field2D makeField(
                chronon3d::graphics::Field2DGenerator generator, float frequency,
                std::uint32_t seed, float warp) {
            chronon3d::graphics::Field2D field;
            field.generator = generator;
            field.frequency = frequency;
            field.seed = seed;
            field.octaves = 5;
            field.persistence = 0.52f;
            field.lacunarity = 2.f;
            if (warp > 0.f)
                field.operators.push_back({.kind = chronon3d::graphics::Field2DOperatorKind::Warp,
                                           .amount = std::clamp(warp, 0.f, 1.f)});
            return field;
        }

        void staggerFadeInAndOut(LayerHandle& layer, int inFrame, int endFrame,
                                 int delayFrames, int enterFrames, int exitFrames,
                                 float opacity);
        [[nodiscard]] int boundedEnterFrames(int duration, int divisor);

        [[nodiscard]] LayerHandle& addShape(TemplateScene& scene, const std::string& name,
                                            const std::string& color, float width, float height,
                                            float x, float y, ShapeGeometry geometry = ShapeGeometry::Rectangle,
                                            float radius = 0.f,
                                            std::optional<ShapeRadialGradient> gradient = std::nullopt) {
            LayerHandle& layer = scene.shape(ShapeSpec{.size = Vector2(width, height),
                                                       .fillColor = color,
                                                       .name = name,
                                                       .cornerRadius = radius,
                                                       .geometry = geometry,
                                                       .radialGradient = std::move(gradient)});
            layer.position(x, y);
            return layer;
        }

        [[nodiscard]] ShapeRadialGradient radialGradient(const std::string& inner,
                                                         const std::string& outer,
                                                         float innerOpacity, float outerOpacity,
                                                         float radius = 0.5f) {
            return ShapeRadialGradient{.center = Vector2(0.5f, 0.5f),
                                       .radius = radius,
                                       .stops = {{0.f, inner, innerOpacity},
                                                 {1.f, outer, outerOpacity}}};
        }

        [[nodiscard]] chronon3d::Color srgbColor(const std::string& hex, float alpha = 1.f) {
            const auto linear = chronon3d::render_plan::parse_hex_color(hex, alpha);
            if (!linear) throw std::invalid_argument("background color must be #RRGGBB");
            return {chronon3d::render_plan::linear_to_srgb(linear->r),
                    chronon3d::render_plan::linear_to_srgb(linear->g),
                    chronon3d::render_plan::linear_to_srgb(linear->b), alpha};
        }

        [[nodiscard]] LayerHandle& addNativeField(TemplateScene& scene, const BackgroundSpec& spec,
                                                   const std::string& suffix,
                                                   chronon3d::graphics::Field2D field,
                                                   chronon3d::graphics::GradientDefinition ramp,
                                                   int inFrame, int endFrame,
                                                   std::uint32_t renderScale = 2,
                                                   chronon3d::Vec2 drift = {0.f, 0.f}) {
            ShapeSpec shape;
            shape.size = scene.canvas();
            shape.fillColor = spec.ground;
            shape.name = spec.name + suffix;
            shape.field = std::move(field);
            shape.fieldRamp = std::move(ramp);
            shape.fieldRenderScale = renderScale;
            if (drift.x != 0.f || drift.y != 0.f) shape.fieldDrift = drift;
            LayerHandle& layer = scene.shape(shape);
            layer.position(scene.canvas().x * 0.5f, scene.canvas().y * 0.5f);
            const int enter = boundedEnterFrames(spec.duration, 10);
            staggerFadeInAndOut(layer, inFrame, endFrame, 0, enter,
                                exitFramesFor(spec.duration), 1.f);
            return layer;
        }

        [[nodiscard]] bool validHexColor(const std::string& color) {
            if (color.size() != 7 || color.front() != '#') return false;
            return std::all_of(color.begin() + 1, color.end(), [](unsigned char digit) {
                return (digit >= '0' && digit <= '9') ||
                       (digit >= 'a' && digit <= 'f') ||
                       (digit >= 'A' && digit <= 'F');
            });
        }

        void animateDrift(LayerHandle& layer, float fps, int startFrame, int endFrame,
                          float fromX, float fromY, float toX, float toY) {
            const float start = static_cast<float>(startFrame) / fps;
            const float end = static_cast<float>(endFrame) / fps;
            layer.layer().tracks.position.add(start, chrononmotion::Vector3(fromX, fromY, 0.f),
                                              chrononmotion::motion::Easing::linear());
            layer.layer().tracks.position.add(end, chrononmotion::Vector3(toX, toY, 0.f),
                                              chrononmotion::motion::Easing::linear());
        }

        void fadeInAndOut(LayerHandle& layer, int inFrame, int endFrame,
                          int enterFrames, int exitFrames, float opacity) {
            const int exitStart = endFrame - exitFrames;
            layer.alive(inFrame, endFrame).opacity(0.f);
            layer.animateOpacity(inFrame, enterFrames, 0.f, opacity);
            layer.animateOpacity(exitStart, exitFrames, opacity, 0.f);
        }

        void staggerFadeInAndOut(LayerHandle& layer, int inFrame, int endFrame,
                                 int delayFrames, int enterFrames, int exitFrames,
                                 float opacity) {
            const int exitStart = endFrame - exitFrames;
            const int safeDelay = std::min(std::max(0, delayFrames),
                                           std::max(0, exitStart - inFrame - enterFrames));
            layer.alive(inFrame, endFrame).opacity(0.f);
            layer.animateOpacity(inFrame + safeDelay, enterFrames, 0.f, opacity);
            layer.animateOpacity(exitStart, exitFrames, opacity, 0.f);
        }

        void addAnimatedLookWindow(const BackgroundSpec& spec) {
            if (spec.duration < 24) {
                throw std::invalid_argument("addBackground: documentary animated looks need at least 24 frames");
            }
        }

        [[nodiscard]] int boundedEnterFrames(int duration, int divisor) {
            return std::max(1, std::min(24, duration / divisor));
        }

        [[nodiscard]] float dotSpacingForCanvas(float requested, float radius,
                                                const Vector2& canvas) {
            float spacing = std::max(requested, radius * 2.f);
            const auto countAxis = [radius](float span, float candidate) {
                const float available = std::max(0.f, span - radius * 2.f);
                return static_cast<std::uint64_t>(std::floor(available / candidate)) + 1u;
            };
            const double nx = static_cast<double>(countAxis(canvas.x, spacing));
            const double ny = static_cast<double>(countAxis(canvas.y, spacing));
            const double targetSpacing = std::max(
                static_cast<double>(canvas.x) / 63.0,
                static_cast<double>(canvas.y) / 63.0);
            if (nx * ny > 4096.0 || std::max(nx, ny) > 64.0)
                spacing = std::max(spacing, static_cast<float>(targetSpacing));
            while (spacing <= 512.f &&
                   (static_cast<double>(countAxis(canvas.x, spacing)) *
                       static_cast<double>(countAxis(canvas.y, spacing)) > 4096.0 ||
                    std::max(countAxis(canvas.x, spacing), countAxis(canvas.y, spacing)) > 64u))
                spacing *= 1.01f;
            const auto finalX = countAxis(canvas.x, spacing);
            const auto finalY = countAxis(canvas.y, spacing);
            if (spacing > 512.f || finalX > 64u || finalY > 64u || finalX * finalY > 4096u)
                throw std::invalid_argument("addBackground: native dot grid exceeds the 4096-dot render limit");
            return spacing;
        }

        void addMeshGradient(TemplateScene& scene, const BackgroundSpec& spec,
                            BackgroundComposition& out, const Vector2& canvas,
                            int inFrame, int endFrame) {
            struct Orb {
                const char* suffix;
                const char* color;
                float x;
                float y;
                float width;
                float height;
                float opacity;
                int delay;
            };
            const float shortSide = std::min(canvas.x, canvas.y);
            const Orb orbs[] = {
                {"_mesh_orb_0", spec.meshColors[0].c_str(), canvas.x * 0.2f, canvas.y * 0.16f,
                 shortSide * 1.05f, shortSide * 1.05f, 0.52f, 0},
                {"_mesh_orb_1", spec.meshColors[1].c_str(), canvas.x * 0.82f, canvas.y * 0.2f,
                 shortSide * 0.92f, shortSide * 0.92f, 0.46f, 4},
                {"_mesh_orb_2", spec.meshColors[2].c_str(), canvas.x * 0.54f, canvas.y * 0.88f,
                 shortSide * 1.15f, shortSide * 1.15f, 0.40f, 8},
                {"_mesh_orb_3", spec.meshColors[3].c_str(), canvas.x * 0.62f, canvas.y * 0.54f,
                 shortSide * 0.78f, shortSide * 0.78f, 0.35f, 12}};
            for (const Orb& orb : orbs) {
                LayerHandle& field = addShape(scene, spec.name + orb.suffix, orb.color,
                                              orb.width, orb.height, orb.x, orb.y,
                                              ShapeGeometry::Ellipse, 0.f,
                                              radialGradient(orb.color, orb.color, 1.f, 0.f));
                staggerFadeInAndOut(field, inFrame, endFrame, orb.delay,
                                    boundedEnterFrames(spec.duration, 10),
                                    exitFramesFor(spec.duration), orb.opacity);
                const int travelEnd = std::max(inFrame + 1, endFrame - exitFramesFor(spec.duration));
                const float phase = static_cast<float>(orb.delay) * 0.013f;
                const float driftX = std::sin(phase + 1.3f) * canvas.x * 0.08f * spec.meshSpeed;
                const float driftY = std::cos(phase + 0.7f) * canvas.y * 0.08f * spec.meshSpeed;
                animateDrift(field, scene.fps(), inFrame, travelEnd,
                             orb.x, orb.y, orb.x + driftX, orb.y + driftY);
                out.accents.push_back(&field);
            }
        }

        void addDocumentaryGrid(TemplateScene& scene, const BackgroundSpec& spec,
                                BackgroundComposition& out, const Vector2& canvas,
                                int inFrame, int endFrame) {
            const int columns = static_cast<int>(std::ceil(canvas.x / spec.gridSpacing));
            const int rows = static_cast<int>(std::ceil(canvas.y / spec.gridSpacing));
            const int enterFrames = boundedEnterFrames(spec.duration, 6);
            const int exitFrames = exitFramesFor(spec.duration);
            const float startOpacity = std::min(1.f, spec.gridOpacity);
            const float majorOpacity = std::min(1.f, spec.gridOpacity * 2.8f);
            const float lineWidth = std::max(1.f, std::min(2.f, spec.gridSpacing * 0.0125f));

            for (int column = 0; column <= columns; ++column) {
                const float x = std::min(canvas.x, static_cast<float>(column) * spec.gridSpacing);
                const bool major = column % spec.majorEvery == 0;
                LayerHandle& line = addShape(scene, spec.name + "_grid_v_" + std::to_string(column),
                                            major ? spec.seam : spec.accent,
                                            major ? lineWidth * 1.6f : lineWidth, canvas.y, x,
                                            canvas.y * 0.5f);
                staggerFadeInAndOut(line, inFrame, endFrame, std::min(column, enterFrames),
                                    std::max(1, enterFrames / 2), exitFrames,
                                    major ? majorOpacity : startOpacity);
                out.accents.push_back(&line);
            }

            for (int row = 0; row <= rows; ++row) {
                const float y = std::min(canvas.y, static_cast<float>(row) * spec.gridSpacing);
                const bool major = row % spec.majorEvery == 0;
                LayerHandle& line = addShape(scene, spec.name + "_grid_h_" + std::to_string(row),
                                            major ? spec.seam : spec.accent,
                                            canvas.x, major ? lineWidth * 1.6f : lineWidth,
                                            canvas.x * 0.5f, y);
                staggerFadeInAndOut(line, inFrame, endFrame, std::min(row, enterFrames),
                                    std::max(1, enterFrames / 2), exitFrames,
                                    major ? majorOpacity : startOpacity);
                out.accents.push_back(&line);
            }

            for (std::size_t index = 0; index < spec.gridSquares.size(); ++index) {
                const auto [column, row] = spec.gridSquares[index];
                const float x = static_cast<float>(column) * spec.gridSpacing + spec.gridSpacing * 0.5f;
                const float y = static_cast<float>(row) * spec.gridSpacing + spec.gridSpacing * 0.5f;
                if (x >= canvas.x || y >= canvas.y) continue;
                LayerHandle& square = addShape(scene, spec.name + "_grid_square_" +
                                                std::to_string(index), spec.seam,
                                                spec.gridSpacing - 1.f, spec.gridSpacing - 1.f,
                                                x, y);
                staggerFadeInAndOut(square, inFrame, endFrame,
                                    static_cast<int>(index % static_cast<std::size_t>(enterFrames)),
                                    std::max(1, enterFrames / 2), exitFrames,
                                    std::min(1.f, spec.gridOpacity * 4.f));
                out.accents.push_back(&square);
            }

            // Quiet optical reticle and four coordinate ticks keep the grid
            // documentary rather than dashboard-dense.
            const float centerX = canvas.x * 0.5f;
            const float centerY = canvas.y * 0.5f;
            const float reticleWidth = std::max(1.5f, canvas.x * 0.0015f);
            for (int arm = 0; arm < 4; ++arm) {
                const float direction = arm < 2 ? -1.f : 1.f;
                const bool horizontal = arm % 2 == 0;
                const float length = std::min(canvas.x, canvas.y) * 0.055f;
                LayerHandle& tick = addShape(scene, spec.name + "_reticle_" + std::to_string(arm),
                                             spec.seam,
                                             horizontal ? length : reticleWidth,
                                             horizontal ? reticleWidth : length,
                                             centerX + (horizontal ? direction * length * 0.75f : 0.f),
                                             centerY + (horizontal ? 0.f : direction * length * 0.75f));
                staggerFadeInAndOut(tick, inFrame, endFrame, 8 + arm * 3,
                                    std::min(12, std::max(1, spec.duration / 8)),
                                    exitFramesFor(spec.duration), 0.8f);
                out.accents.push_back(&tick);
            }
        }

        void addGridPattern(TemplateScene& scene, const BackgroundSpec& spec,
                            BackgroundComposition& out, const Vector2& canvas,
                            int inFrame, int endFrame) {
            const float spacingY = spec.gridSpacingY > 0.f ? spec.gridSpacingY : spec.gridSpacing;
            const int columns = static_cast<int>(std::ceil(canvas.x / spec.gridSpacing));
            const int rows = static_cast<int>(std::ceil(canvas.y / spacingY));
            const int exitFrames = exitFramesFor(spec.duration);
            const int enterFrames = boundedEnterFrames(spec.duration, 8);
            const float lineWidth = std::max(1.f, std::min(2.f, spec.gridSpacing * 0.025f));
            for (int column = 0; column <= columns; ++column) {
                const float x = static_cast<float>(column) * spec.gridSpacing + spec.gridOffsetX;
                if (x < 0.f || x > canvas.x) continue;
                LayerHandle& line = addShape(scene, spec.name + "_pattern_v_" +
                                              std::to_string(column), spec.accent,
                                              lineWidth, canvas.y, x, canvas.y * 0.5f);
                fadeInAndOut(line, inFrame, endFrame, enterFrames, exitFrames, spec.gridOpacity);
                out.accents.push_back(&line);
            }
            for (int row = 0; row <= rows; ++row) {
                const float y = static_cast<float>(row) * spacingY + spec.gridOffsetY;
                if (y < 0.f || y > canvas.y) continue;
                LayerHandle& line = addShape(scene, spec.name + "_pattern_h_" +
                                              std::to_string(row), spec.accent,
                                              canvas.x, lineWidth, canvas.x * 0.5f, y);
                fadeInAndOut(line, inFrame, endFrame, enterFrames, exitFrames, spec.gridOpacity);
                out.accents.push_back(&line);
            }
            for (std::size_t index = 0; index < spec.gridSquares.size(); ++index) {
                const auto [column, row] = spec.gridSquares[index];
                const float x = static_cast<float>(column) * spec.gridSpacing +
                                spec.gridOffsetX + spec.gridSpacing * 0.5f;
                const float y = static_cast<float>(row) * spacingY +
                                spec.gridOffsetY + spacingY * 0.5f;
                if (x >= canvas.x || y >= canvas.y) continue;
                LayerHandle& square = addShape(scene, spec.name + "_grid_square_" +
                                                std::to_string(index), spec.seam,
                                                spec.gridSpacing - 1.f, spacingY - 1.f, x, y);
                staggerFadeInAndOut(square, inFrame, endFrame,
                                    static_cast<int>(index % static_cast<std::size_t>(enterFrames)),
                                    enterFrames, exitFrames, std::min(1.f, spec.gridOpacity * 4.f));
                out.accents.push_back(&square);
            }
        }

        void addRadarSweep(TemplateScene& scene, const BackgroundSpec& spec,
                           BackgroundComposition& out, const Vector2& canvas,
                           int inFrame, int endFrame) {
            const int enterFrames = boundedEnterFrames(spec.duration, 8);
            const int exitFrames = exitFramesFor(spec.duration);
            const float lineWidth = std::max(1.f, std::min(2.f, spec.gridSpacing * 0.01f));

            // Retain the orthogonal coordinate system but push the minor field
            // back so the scan plate reads cleanly behind documentary titles.
            const int columns = static_cast<int>(std::ceil(canvas.x / spec.gridSpacing));
            for (int column = 1; column < columns; ++column) {
                const float x = std::min(canvas.x, static_cast<float>(column) * spec.gridSpacing);
                LayerHandle& line = addShape(scene, spec.name + "_coord_v_" + std::to_string(column),
                                            spec.accent, lineWidth, canvas.y, x, canvas.y * 0.5f);
                fadeInAndOut(line, inFrame, endFrame, enterFrames, exitFrames,
                             spec.gridOpacity * 0.65f);
                out.accents.push_back(&line);
            }

            const int rows = static_cast<int>(std::ceil(canvas.y / spec.gridSpacing));
            for (int row = 1; row < rows; ++row) {
                const float y = std::min(canvas.y, static_cast<float>(row) * spec.gridSpacing);
                LayerHandle& line = addShape(scene, spec.name + "_coord_h_" + std::to_string(row),
                                            spec.accent, canvas.x, lineWidth, canvas.x * 0.5f, y);
                fadeInAndOut(line, inFrame, endFrame, enterFrames, exitFrames,
                             spec.gridOpacity * 0.65f);
                out.accents.push_back(&line);
            }

            const float bandWidth = std::max(canvas.x * 0.045f, spec.gridSpacing * 0.6f);
            LayerHandle& band = addShape(scene, spec.name + "_scan_band", spec.seam,
                                        bandWidth, canvas.y, -bandWidth * 0.5f, canvas.y * 0.5f);
            fadeInAndOut(band, inFrame, endFrame, enterFrames, exitFrames, spec.scanOpacity);
            animateDrift(band, scene.fps(), inFrame, endFrame - exitFrames,
                         -bandWidth * 0.5f, canvas.y * 0.5f,
                         canvas.x + bandWidth * 0.5f, canvas.y * 0.5f);
            out.accents.push_back(&band);

            const float sweepWidth = std::max(2.f, canvas.x * 0.002f);
            LayerHandle& sweep = addShape(scene, spec.name + "_scan_line", spec.seam,
                                         sweepWidth, canvas.y, 0.f, canvas.y * 0.5f);
            staggerFadeInAndOut(sweep, inFrame, endFrame, enterFrames / 2,
                                enterFrames, exitFrames, 0.9f);
            animateDrift(sweep, scene.fps(), inFrame, endFrame - exitFrames,
                         0.f, canvas.y * 0.5f, canvas.x, canvas.y * 0.5f);
            out.accents.push_back(&sweep);

            const float centerX = canvas.x * 0.5f;
            const float centerY = canvas.y * 0.5f;
            const float ring = std::min(canvas.x, canvas.y) * 0.32f;
            for (int arm = 0; arm < 4; ++arm) {
                const float dx = arm % 2 == 0 ? -1.f : 1.f;
                const float dy = arm < 2 ? -1.f : 1.f;
                LayerHandle& marker = addShape(scene, spec.name + "_radar_marker_" + std::to_string(arm),
                                               spec.seam, 8.f, 8.f,
                                               centerX + dx * ring, centerY + dy * ring,
                                               ShapeGeometry::Ellipse);
                staggerFadeInAndOut(marker, inFrame, endFrame,
                                    std::min(12 + arm * 8, endFrame - inFrame - exitFrames - 1),
                                    12, exitFrames, 0.9f);
                out.accents.push_back(&marker);
            }
        }

        [[nodiscard]] std::string hexBlend(const std::string& first, const std::string& second,
                                           float amount) {
            const auto a = static_cast<unsigned>(std::stoul(first.substr(1), nullptr, 16));
            const auto b = static_cast<unsigned>(std::stoul(second.substr(1), nullptr, 16));
            const float t = std::clamp(amount, 0.f, 1.f);
            unsigned result = 0;
            for (unsigned channel = 0; channel < 3; ++channel) {
                const unsigned shift = (2u - channel) * 8u;
                const float av = static_cast<float>((a >> shift) & 255u);
                const float bv = static_cast<float>((b >> shift) & 255u);
                result |= static_cast<unsigned>(std::lround(av + (bv - av) * t)) << shift;
            }
            constexpr char digits[] = "0123456789ABCDEF";
            std::string output{"#000000"};
            for (unsigned i = 0; i < 6; ++i)
                output[i + 1] = digits[(result >> ((5u - i) * 4u)) & 0xfu];
            return output;
        }

        [[nodiscard]] chronon3d::graphics::GradientDefinition fieldRamp(
                const std::vector<std::pair<float, std::pair<std::string, float>>>& stops,
                float angle = 0.f);

        [[nodiscard]] chronon3d::graphics::GradientDefinition fieldRamp(
                const std::vector<std::pair<float, std::pair<std::string, float>>>& stops,
                float angle) {
            std::vector<chronon3d::graphics::GradientStop> output;
            output.reserve(stops.size());
            for (const auto& [position, colorAndAlpha] : stops)
                output.push_back({position, srgbColor(colorAndAlpha.first, colorAndAlpha.second)});
            const float dx = 0.5f * std::cos(angle);
            const float dy = 0.5f * std::sin(angle);
            return chronon3d::graphics::GradientDefinition::linear(
                {0.5f - dx, 0.5f - dy}, {0.5f + dx, 0.5f + dy}, std::move(output));
        }

        [[nodiscard]] LayerHandle& addMeshFill(TemplateScene& scene, const BackgroundSpec& spec,
                                               const std::string& suffix,
                                               chronon3d::graphics::GradientMesh mesh,
                                               int inFrame, int endFrame) {
            ShapeSpec request;
            request.size = scene.canvas();
            request.fillColor = spec.ground;
            request.name = spec.name + suffix;
            request.gradientMesh = std::move(mesh);
            LayerHandle& layer = scene.shape(request);
            layer.position(scene.canvas().x * 0.5f, scene.canvas().y * 0.5f);
            staggerFadeInAndOut(layer, inFrame, endFrame, 0,
                                boundedEnterFrames(spec.duration, 10),
                                exitFramesFor(spec.duration), 1.f);
            return layer;
        }

        void addReactParticles(TemplateScene& scene, const BackgroundSpec& spec,
                               BackgroundComposition& out, const Vector2& canvas,
                               int inFrame, int endFrame) {
            const int count = std::min(spec.particleQuantity, 96);
            const float cameraScale = 20.f / spec.particleCameraDistance;
            const int enter = boundedEnterFrames(spec.duration, 10);
            const int exit = exitFramesFor(spec.duration);
            for (int index = 0; index < count; ++index) {
                const auto item = static_cast<std::uint32_t>(index);
                const float u = unitHash(item * 3u + spec.seed + 0x51ed270bU);
                const float v = unitHash(item * 7u + spec.seed + 0x68bc21ebU);
                const float phase = unitHash(item * 11u + spec.seed + 0x02e5be93U) * 6.2831853f;
                const float sizeNoise = 1.f + spec.particleSizeRandomness *
                    (unitHash(item * 13u + spec.seed + 0xa511e9b3U) - 0.5f);
                const float diameter = std::clamp(spec.particleSize * cameraScale * sizeNoise,
                                                  0.5f, 48.f);
                const auto& palette = spec.particleColors;
                const std::string& particleColor = palette.empty()
                    ? spec.particleColor
                    : palette[static_cast<std::size_t>(index) % palette.size()];
                const float x = std::clamp(canvas.x * (0.5f + (u - 0.5f) * spec.particleSpread * 0.12f),
                                           -canvas.x * 0.25f, canvas.x * 1.25f);
                const float y = std::clamp(canvas.y * (0.5f + (v - 0.5f) * spec.particleSpread * 0.12f),
                                           -canvas.y * 0.25f, canvas.y * 1.25f);
                const float temporalOrbit = std::max(canvas.x, canvas.y) * spec.particleSpeed * 0.012f;
                const float hoverDrift = spec.moveParticlesOnHover ? spec.particleHoverFactor * 3.f : 0.f;
                auto& particle = addShape(scene, spec.name + "_particle_" + std::to_string(index),
                    particleColor, diameter, diameter, x, y, ShapeGeometry::Ellipse);
                const float alpha = spec.alphaParticles
                    ? 0.46f + unitHash(item * 17u + spec.seed) * 0.42f : 1.f;
                staggerFadeInAndOut(particle, inFrame, endFrame, index % std::max(1, enter),
                                    enter, exit, alpha);
                animateDrift(particle, scene.fps(), inFrame, endFrame - exit,
                    x, y, x + std::cos(phase) * temporalOrbit + hoverDrift,
                    y + std::sin(phase) * temporalOrbit - hoverDrift * 0.35f);
                out.accents.push_back(&particle);
            }
        }

        void addReactField(TemplateScene& scene, const BackgroundSpec& spec,
                           BackgroundComposition& out, const Vector2& canvas,
                           int inFrame, int endFrame) {
            using namespace chronon3d::graphics;
            const auto addField = [&](const char* suffix, Field2DGenerator generator,
                                      float frequency, std::uint32_t seed, float driftX,
                                      float driftY, GradientDefinition ramp, float opacity,
                                      std::uint32_t scale, float noiseAmount = 0.f,
                                      bool animatedNoise = false, float noiseSize = 1.f,
                                      float contrast = 1.f) {
                Field2D field = makeField(generator, frequency, seed, 0.18f);
                ShapeSpec request;
                request.size = canvas;
                request.fillColor = spec.ground;
                request.name = spec.name + suffix;
                request.field = std::move(field);
                request.fieldRamp = std::move(ramp);
                request.fieldRenderScale = scale;
                request.fieldDrift = chronon3d::Vec2{driftX, driftY};
                request.noiseAmount = noiseAmount;
                request.noiseSeed = seed;
                request.animatedNoise = animatedNoise;
                request.noiseSize = noiseSize;
                request.contrast = contrast;
                LayerHandle& layer = scene.shape(request);
                layer.position(canvas.x * 0.5f, canvas.y * 0.5f);
                staggerFadeInAndOut(layer, inFrame, endFrame, 0,
                                    boundedEnterFrames(spec.duration, 10),
                                    exitFramesFor(spec.duration), opacity);
                out.accents.push_back(&layer);
            };

            switch (spec.look) {
                case BackgroundLook::Aurora: {
                    const auto color = [&](const std::string& input) {
                        return spec.aurora.lightMode ? lightenHex(input, 0.50f) : input;
                    };
                    GradientMesh mesh;
                    mesh.nodes = {
                        {{0.02f, 0.05f}, srgbColor("#09111F"), 1.f},
                        {{0.98f, 0.05f}, srgbColor("#100D27"), 1.f},
                        {{0.02f, 0.95f}, srgbColor("#102035"), 1.f},
                        {{0.98f, 0.95f}, srgbColor("#160D2A"), 1.f},
                        {{0.20f, 0.58f}, srgbColor(color(spec.aurora.colorStops[0]), 0.52f), 1.8f},
                        {{0.51f, 0.45f}, srgbColor(color(spec.aurora.colorStops[1]), 0.58f), 2.f},
                        {{0.82f, 0.62f}, srgbColor(color(spec.aurora.colorStops[2]), 0.48f), 1.7f}};
                    auto& atmosphere = addMeshFill(scene, spec, "_aurora_mesh", std::move(mesh), inFrame, endFrame);
                    out.accents.push_back(&atmosphere);
                    auto field = makeField(Field2DGenerator::Simplex, 2.5f + spec.aurora.amplitude,
                                           spec.seed, 0.12f + spec.aurora.blend * 0.35f);
                    auto& curtain = addNativeField(scene, spec, "_aurora_curtain", std::move(field),
                        fieldRamp({{0.f, {color(spec.aurora.colorStops[0]), 0.f}},
                                   {0.48f, {color(spec.aurora.colorStops[1]), 0.50f}},
                                   {1.f, {color(spec.aurora.colorStops[2]), 0.f}}}),                                   inFrame, endFrame, 2,
                                   {spec.aurora.speed * 0.018f, spec.aurora.speed * 0.008f});
                    out.accents.push_back(&curtain);
                    break;
                }
                case BackgroundLook::DarkVeil: {
                    const auto color = [&](const char* input) {
                        const std::string hex{input};
                        return spec.darkVeil.lightMode ? lightenHex(hex, 0.72f) : hex;
                    };
                    const auto hueSeed = spec.seed + static_cast<std::uint32_t>(
                        std::lround((spec.darkVeil.hueShift + 360.f) * 17.f));
                    addField("_dark_veil", Field2DGenerator::Fractal,
                             3.2f + spec.darkVeil.warpAmount * 3.f, hueSeed,
                             spec.darkVeil.speed * 0.025f, -spec.darkVeil.speed * 0.01f,
                             fieldRamp({{0.f, {color("#10102A"), 0.12f}},
                                        {0.48f, {color("#35284D"), 0.42f}},
                                        {1.f, {color("#8B4C86"), 0.68f}}}), 1.f,
                             spec.darkVeil.resolutionScale < 0.5f ? 4u :
                                 spec.darkVeil.resolutionScale < 1.f ? 2u : 1u,
                             spec.darkVeil.noiseIntensity * 0.08f, true,
                             std::clamp(spec.darkVeil.resolutionScale * 4.f, 0.1f, 256.f));
                    const int scanCount = spec.darkVeil.scanlineIntensity > 0.f
                        ? std::clamp(static_cast<int>(std::ceil(spec.darkVeil.scanlineFrequency / 12.f)), 1, 8) : 0;
                    for (int i = 0; i < scanCount; ++i) {
                        auto& line = addShape(scene, spec.name + "_dark_scan_" + std::to_string(i),
                            spec.darkVeil.lightMode ? "#6B547E" : "#D8C9FF",
                            canvas.x, std::max(1.f, spec.darkVeil.scanlineIntensity * 2.f),
                            canvas.x * 0.5f, canvas.y * static_cast<float>(i + 1) /
                                static_cast<float>(scanCount + 1));
                        fadeInAndOut(line, inFrame, endFrame, boundedEnterFrames(spec.duration, 10),
                                     exitFramesFor(spec.duration),
                                     std::clamp(spec.darkVeil.noiseIntensity + 0.16f, 0.f, 0.65f));
                        out.accents.push_back(&line);
                    }
                    break;
                }
                case BackgroundLook::DotGrid:
                case BackgroundLook::DotField: {
                    ShapeSpec dots;
                    dots.size = canvas;
                    dots.fillColor = spec.look == BackgroundLook::DotGrid
                        ? spec.dots.baseColor : spec.dots.activeColor;
                    dots.name = spec.name + (spec.look == BackgroundLook::DotGrid ? "_dots" : "_dot_field");
                    dots.geometry = ShapeGeometry::DotGrid;
                    dots.dotRadius = spec.look == BackgroundLook::DotGrid
                        ? std::max(0.5f, spec.dots.dotSize * 0.5f) : spec.dots.dotRadius;
                    const float requestedSpacing = spec.look == BackgroundLook::DotGrid
                        ? spec.dots.dotSize + spec.dots.gap : spec.dots.dotSpacing;
                    dots.gridSpacing = dotSpacingForCanvas(requestedSpacing, dots.dotRadius, canvas);
                    auto& grid = scene.shape(dots);
                    grid.position(canvas.x * 0.5f, canvas.y * 0.5f);
                    fadeInAndOut(grid, inFrame, endFrame, boundedEnterFrames(spec.duration, 10),
                                 exitFramesFor(spec.duration), 0.72f);
                    out.accents.push_back(&grid);
                    if (spec.look == BackgroundLook::DotField &&
                        (spec.dots.waveAmplitude > 0.f || spec.dots.cursorForce != 0.f)) {
                        const float fieldStrength = spec.dots.bulgeOnly
                            ? spec.dots.bulgeStrength / 100.f : spec.dots.cursorForce * 10.f;
                        const float radiusScale = std::max(0.15f, spec.dots.cursorRadius / 500.f);
                        addField("_dot_field_wave", Field2DGenerator::Rings,
                                 5.f / radiusScale, spec.seed,
                                 0.03f * fieldStrength, 0.02f * fieldStrength,
                                 fieldRamp({{0.f, {spec.dots.activeColor, 0.f}},
                                            {1.f, {spec.dots.activeColor, 0.22f}}}), 0.72f, 4);
                    }
                    if (spec.look == BackgroundLook::DotField && spec.dots.sparkle) {
                        const int sparkleCount = std::min(24, static_cast<int>(std::ceil(spec.dots.glowRadius / 24.f)));
                        for (int i = 0; i < sparkleCount; ++i) {
                            const auto item = static_cast<std::uint32_t>(i);
                            const float x = unitHash(item * 31u + spec.seed + 0x93a4U) * canvas.x;
                            const float y = unitHash(item * 47u + spec.seed + 0x175dU) * canvas.y;
                            const float size = 1.f + unitHash(item * 59u + spec.seed) * 2.5f;
                            auto& sparkle = addShape(scene, spec.name + "_dot_sparkle_" + std::to_string(i),
                                spec.dots.activeColor, size, size, x, y, ShapeGeometry::Ellipse);
                            fadeInAndOut(sparkle, inFrame, endFrame, boundedEnterFrames(spec.duration, 10),
                                         exitFramesFor(spec.duration), 0.35f + unitHash(item + spec.seed) * 0.4f);
                            out.accents.push_back(&sparkle);
                        }
                    }
                    if (spec.look == BackgroundLook::DotField && spec.dots.glowRadius > 0.f) {
                        auto& glow = addShape(scene, spec.name + "_dot_field_glow",
                            spec.dots.activeColor, spec.dots.glowRadius * 2.f, spec.dots.glowRadius * 2.f,
                            canvas.x * 0.5f, canvas.y * 0.5f, ShapeGeometry::Ellipse, 0.f,
                            radialGradient(spec.dots.activeColor, spec.dots.activeColor, 0.20f, 0.f));
                        fadeInAndOut(glow, inFrame, endFrame, boundedEnterFrames(spec.duration, 10),
                                     exitFramesFor(spec.duration), 0.55f);
                        out.accents.push_back(&glow);
                    }
                    break;
                }
                case BackgroundLook::GradientWaves: {
                    const auto waves = [&](const std::string& input) {
                        return spec.gradientWaves.lightMode ? lightenHex(input, 0.55f) : input;
                    };
                    addField("_gradient_waves", Field2DGenerator::Fractal,
                             std::max(0.5f, spec.gradientWaves.waveScale * 8.f /
                                 std::max(0.1f, spec.gradientWaves.zoom) +
                                 spec.gradientWaves.turbulence * 0.05f + spec.gradientWaves.amplitude * 0.08f),
                             backgroundSeed(spec.seed, static_cast<std::uint32_t>(
                                 std::lround(spec.gradientWaves.tilt * 100.f + spec.gradientWaves.swell +
                                             spec.gradientWaves.height * 7.f + spec.gradientWaves.fogDepth * 3.f +
                                             spec.gradientWaves.waveRatio * 19.f))),
                             spec.gradientWaves.speed * 0.04f * std::cos(spec.gradientWaves.tilt * 0.01745329252f),
                             spec.gradientWaves.speed * 0.015f + spec.gradientWaves.swell * 0.0004f,
                             fieldRamp({{0.f, {waves(spec.gradientWaves.colors[0]), 0.24f}},
                                        {0.55f, {waves(spec.gradientWaves.colors[1]), 0.78f}},
                                        {1.f, {waves(spec.gradientWaves.colors[2]), 0.96f}}}),
                             std::clamp(spec.gradientWaves.opacity, 0.f, 1.f),
                             spec.gradientWaves.detail == 0 ? 4u : spec.gradientWaves.detail == 2 ? 1u : 2u,
                             spec.gradientWaves.grain ? spec.gradientWaves.grainIntensity : 0.f,
                             true, 1.f);
                    break;
                }
                case BackgroundLook::Grainient:
                    {
                        const auto grainColor = [&](const std::string& input) {
                            return spec.grainient.lightMode ? lightenHex(input, 0.45f) : input;
                        };
                        const std::string balancedMid = hexBlend(
                            grainColor(spec.grainient.colors[1]),
                            grainColor(spec.grainient.colors[0]),
                            std::clamp(0.5f + spec.grainient.colorBalance * 0.5f, 0.f, 1.f));
                        addField("_grainient", Field2DGenerator::Fractal,
                                 std::clamp(spec.grainient.warpFrequency * spec.grainient.noiseScale *
                                     std::max(0.1f, spec.grainient.warpStrength), 0.5f, 40.f),
                                 backgroundSeed(spec.seed, static_cast<std::uint32_t>(
                                     std::lround(spec.grainient.rotationAmount + spec.grainient.blendAngle * 11.f))),
                                 spec.grainient.timeSpeed * spec.grainient.warpStrength * 0.035f,
                                 spec.grainient.timeSpeed * 0.018f,
                                 fieldRamp({{0.f, {grainColor(spec.grainient.colors[2]), 0.92f}},
                                            {0.5f, {balancedMid, std::clamp(0.98f - spec.grainient.blendSoftness * 0.2f, 0.75f, 1.f)}},
                                            {1.f, {grainColor(spec.grainient.colors[0]), 1.f}}},
                                           spec.grainient.blendAngle * 0.01745329252f), 1.f, 2,
                                 spec.grainient.grainAmount, spec.grainient.grainAnimated,
                                 std::clamp(spec.grainient.grainScale * spec.grainient.noiseScale, 0.1f, 256.f),
                                 std::clamp(spec.grainient.contrast * spec.grainient.gamma, 0.f, 4.f));
                    }
                    break;
                case BackgroundLook::RippleGrid: {
                    ShapeSpec grid;
                    grid.size = canvas;
                    grid.fillColor = spec.rippleGrid.gridColor;
                    grid.name = spec.name + "_ripple_grid";
                    grid.geometry = ShapeGeometry::Grid;
                    grid.gridSpacing = std::clamp(spec.rippleGrid.gridSize, 4.f, 512.f);
                    grid.strokeColor = spec.rippleGrid.gridColor;
                    grid.strokeWidth = std::clamp(spec.rippleGrid.gridThickness * 0.08f, 0.25f, 8.f);
                    auto& lines = scene.shape(grid);
                    lines.position(canvas.x * 0.5f, canvas.y * 0.5f);
                    lines.layer().rotated(chrononmotion::Vector3(0.f, 0.f,
                        spec.rippleGrid.rotationDegrees * 0.01745329252f));
                    lines.layer().tracks.position.add(static_cast<float>(inFrame) / scene.fps(),
                        chrononmotion::Vector3(canvas.x * 0.5f, canvas.y * 0.5f, 0.f));
                    fadeInAndOut(lines, inFrame, endFrame, boundedEnterFrames(spec.duration, 10),
                                 exitFramesFor(spec.duration), std::clamp(spec.rippleGrid.opacity, 0.f, 1.f));
                    out.accents.push_back(&lines);
                    const float radius = std::min(canvas.x, canvas.y) *
                        std::clamp(0.18f + spec.rippleGrid.rippleIntensity * 0.8f +
                                   (spec.rippleGrid.mouseInteraction ? spec.rippleGrid.mouseInteractionRadius * 0.02f : 0.f),
                                   0.12f, 0.4f);
                    const std::string ringColor = spec.rippleGrid.lightMode
                        ? lightenHex(spec.rippleGrid.gridColor, 0.35f) : spec.rippleGrid.gridColor;
                    ShapeSpec ringSpec;
                    ringSpec.size = {radius * 2.f, radius * 2.f};
                    ringSpec.fillColor = ringColor;
                    ringSpec.fillEnabled = false;
                    ringSpec.name = spec.name + "_ripple_ring";
                    ringSpec.geometry = ShapeGeometry::Ellipse;
                    ringSpec.strokeColor = ringColor;
                    ringSpec.strokeWidth = std::clamp(spec.rippleGrid.glowIntensity * 8.f, 1.f, 8.f);
                    auto& ring = scene.shape(ringSpec);
                    ring.position(canvas.x * 0.5f, canvas.y * 0.5f);
                    fadeInAndOut(ring, inFrame, endFrame, boundedEnterFrames(spec.duration, 10),
                                 exitFramesFor(spec.duration), std::clamp(spec.rippleGrid.glowIntensity, 0.f, 0.8f));
                    const int ringEnd = std::max(inFrame + 1, endFrame - exitFramesFor(spec.duration));
                    ring.layer().tracks.scale.add(static_cast<float>(inFrame) / scene.fps(),
                        chrononmotion::Vector3(0.15f, 0.15f, 1.f));
                    ring.layer().tracks.scale.add(static_cast<float>(ringEnd) / scene.fps(),
                        chrononmotion::Vector3(1.5f, 1.5f, 1.f));
                    out.accents.push_back(&ring);
                    break;
                }
                case BackgroundLook::ShapeGrid: {
                    const float size = spec.shapeGrid.squareSize;
                    const float step = size * 1.5f;
                    const int columns = static_cast<int>(std::ceil(canvas.x / step)) + 1;
                    const int rows = static_cast<int>(std::ceil(canvas.y / step)) + 1;
                    for (int row = 0; row < rows && out.accents.size() < 190; ++row)
                        for (int col = 0; col < columns && out.accents.size() < 190; ++col) {
                        const std::size_t index = static_cast<std::size_t>(row * columns + col);
                        ShapeSpec cell;
                        cell.size = {size, size};
                        cell.fillEnabled = false;
                        cell.fillColor = spec.ground;
                        cell.name = spec.name + "_shape_cell_" + std::to_string(index);
                        const bool highlight = spec.shapeGrid.hoverTrailAmount > 0 &&
                            index % static_cast<std::size_t>(std::max(2, 12 -
                                std::min(spec.shapeGrid.hoverTrailAmount, 10))) == 0;
                        if (highlight) {
                            cell.fillEnabled = true;
                            cell.fillColor = spec.shapeGrid.hoverFillColor;
                        }
                        cell.strokeColor = spec.shapeGrid.borderColor;
                        cell.strokeWidth = 1.f;
                        switch (spec.shapeGrid.shape) {
                            case ShapeGridBackgroundOptions::Shape::Square:
                                cell.geometry = ShapeGeometry::Rectangle;
                                break;
                            case ShapeGridBackgroundOptions::Shape::Hexagon:
                                cell.geometry = ShapeGeometry::Polygon; cell.polygonPoints = 6;
                                cell.polygonRotationDegrees = 30.f;
                                break;
                            case ShapeGridBackgroundOptions::Shape::Circle:
                                cell.geometry = ShapeGeometry::Ellipse;
                                break;
                            case ShapeGridBackgroundOptions::Shape::Triangle:
                                cell.geometry = ShapeGeometry::Polygon; cell.polygonPoints = 3;
                                cell.polygonRotationDegrees = (row + col) % 2 == 0 ? 0.f : 180.f;
                                break;
                        }
                        auto& shape = scene.shape(cell);
                        const float baseX = static_cast<float>(col) * step + size * 0.5f;
                        const float baseY = static_cast<float>(row) * step + size * 0.5f;
                        shape.position(baseX, baseY);
                        staggerFadeInAndOut(shape, inFrame, endFrame,
                                            static_cast<int>(index % 24),
                                            boundedEnterFrames(spec.duration, 12),
                                            exitFramesFor(spec.duration), 0.75f);
                        if (spec.shapeGrid.speed > 0.f) {
                            const float distance = spec.shapeGrid.speed * static_cast<float>(spec.duration);
                            const auto [dx, dy] = [&]() {
                                using Direction = ShapeGridBackgroundOptions::Direction;
                                switch (spec.shapeGrid.direction) {
                                    case Direction::Up: return std::pair{0.f, distance};
                                    case Direction::Right: return std::pair{-distance, 0.f};
                                    case Direction::Down: return std::pair{0.f, -distance};
                                    case Direction::Left: return std::pair{distance, 0.f};
                                    case Direction::Diagonal: return std::pair{-distance, -distance};
                                }
                                return std::pair{-distance, 0.f};
                            }();
                            shape.layer().tracks.position.add(static_cast<float>(inFrame) / scene.fps(),
                                chrononmotion::Vector3(baseX, baseY, 0.f));
                            shape.layer().tracks.position.add(static_cast<float>(endFrame - exitFramesFor(spec.duration)) / scene.fps(),
                                chrononmotion::Vector3(baseX + dx, baseY + dy, 0.f));
                        }
                        out.accents.push_back(&shape);
                    }
                    break;
                }
                case BackgroundLook::Silk: {
                    const std::string silkColor = spec.silk.lightMode
                        ? lightenHex(spec.silk.color, 0.5f) : spec.silk.color;
                    addField("_silk", Field2DGenerator::Fractal,
                             std::max(0.5f, spec.silk.scale * 7.f),
                             backgroundSeed(spec.seed, static_cast<std::uint32_t>(
                                 std::lround(spec.silk.rotation * 100.f + spec.silk.noiseIntensity * 31.f))),
                             spec.silk.speed * 0.016f * std::cos(spec.silk.rotation * 0.01745329252f),
                             spec.silk.speed * 0.008f + spec.silk.noiseIntensity * 0.001f,
                             fieldRamp({{0.f, {silkColor, 0.38f}},
                                        {0.48f, {silkColor, 0.82f}},
                                        {1.f, {"#FFFFFF", 0.96f}}}), 1.f, 2,
                             std::clamp(spec.silk.noiseIntensity * 0.05f, 0.f, 0.4f),
                             true, std::clamp(spec.silk.scale * 2.f, 0.1f, 256.f));
                    break;
                }
                case BackgroundLook::Particles:
                    addReactParticles(scene, spec, out, canvas, inFrame, endFrame);
                    break;

                default:
                    break;
            }
        }

        void addArchiveDust(TemplateScene& scene, const BackgroundSpec& spec,
                            BackgroundComposition& out, const Vector2& canvas,
                            int inFrame, int endFrame) {
            const int count = spec.particleCount;
            const int exitFrames = exitFramesFor(spec.duration);
            const int enterFrames = std::min(10, std::max(1, spec.duration / 8));
            for (int index = 0; index < count; ++index) {
                const float seedX = unitHash(static_cast<unsigned>(index) * 17u + 11u);
                const float seedY = unitHash(static_cast<unsigned>(index) * 43u + 29u);
                const float driftX = (unitHash(static_cast<unsigned>(index) * 71u + 5u) - 0.5f) * 42.f;
                const float driftY = -(7.f + unitHash(static_cast<unsigned>(index) * 97u + 31u) * 28.f);
                const float size = 1.2f + unitHash(static_cast<unsigned>(index) * 131u + 19u) * 2.5f;
                const float x = seedX * canvas.x;
                const float y = seedY * canvas.y;
                const int delay = (index * 13) % std::max(1, std::min(44, spec.duration / 3));
                const int lifeIn = std::min(endFrame, inFrame + delay);
                const int lifeOut = std::max(lifeIn + enterFrames + 1, endFrame - exitFrames);
                const std::string& dotColor = spec.particleColors.empty()
                    ? spec.particleColor
                    : spec.particleColors[static_cast<std::size_t>(index) % spec.particleColors.size()];
                const float opacity = index % 5 == 0 ? 0.55f : 0.26f;
                LayerHandle& dot = addShape(scene, spec.name + "_dust_" + std::to_string(index),
                                           dotColor, size, size, x, y, ShapeGeometry::Ellipse,
                                           0.f, radialGradient(dotColor, dotColor, 1.f, 0.f));
                dot.alive(inFrame, endFrame).opacity(0.f);
                dot.animateOpacity(lifeIn, enterFrames, 0.f, opacity);
                dot.animateOpacity(lifeOut, std::max(1, endFrame - lifeOut), opacity, 0.f);
                animateDrift(dot, scene.fps(), lifeIn, lifeOut, x, y,
                             x + driftX, y + driftY);
                out.accents.push_back(&dot);
            }
        }

    }// namespace

    const char* backgroundLookId(BackgroundLook look) noexcept {
        switch (look) {
            case BackgroundLook::SolidTint: return "bg_solid_tint";
            case BackgroundLook::LetterboxBars: return "bg_letterbox_bars";
            case BackgroundLook::VerticalSplit: return "bg_vertical_split";
            case BackgroundLook::VignettePulse: return "bg_vignette_pulse";
            case BackgroundLook::CornerGlow: return "bg_corner_glow";
            case BackgroundLook::DocumentaryGrid: return "bg_documentary_grid";
            case BackgroundLook::RadarSweep: return "bg_radar_sweep";
            case BackgroundLook::ArchiveDust: return "bg_archive_dust";
            case BackgroundLook::MeshGradient: return "bg_mesh_gradient";
            case BackgroundLook::GridPattern: return "bg_grid_pattern";
            case BackgroundLook::Particles: return "bg_particles";
            case BackgroundLook::Aurora: return "bg_aurora";
            case BackgroundLook::DarkVeil: return "bg_dark_veil";
            case BackgroundLook::DotGrid: return "bg_dot_grid";
            case BackgroundLook::DotField: return "bg_dot_field";
            case BackgroundLook::GradientWaves: return "bg_gradient_waves";
            case BackgroundLook::Grainient: return "bg_grainient";
            case BackgroundLook::RippleGrid: return "bg_ripple_grid";
            case BackgroundLook::ShapeGrid: return "bg_shape_grid";
            case BackgroundLook::Silk: return "bg_silk";
        }
        return "unknown";
    }

    std::vector<BackgroundLook> backgroundLooks() {
        return {BackgroundLook::SolidTint, BackgroundLook::LetterboxBars,
                BackgroundLook::VerticalSplit, BackgroundLook::VignettePulse,
                BackgroundLook::CornerGlow, BackgroundLook::DocumentaryGrid,
                BackgroundLook::RadarSweep, BackgroundLook::ArchiveDust,
                BackgroundLook::MeshGradient, BackgroundLook::GridPattern,
                BackgroundLook::Particles, BackgroundLook::Aurora, BackgroundLook::DarkVeil,
                BackgroundLook::DotGrid, BackgroundLook::DotField, BackgroundLook::GradientWaves,
                BackgroundLook::Grainient, BackgroundLook::RippleGrid, BackgroundLook::ShapeGrid,
                BackgroundLook::Silk};
    }

    BackgroundComposition addBackground(TemplateScene& scene, const BackgroundSpec& spec) {
        if (spec.duration <= 0 || spec.inFrame < 0 ||
            spec.duration > std::numeric_limits<int>::max() - spec.inFrame) {
            throw std::invalid_argument(
                    "addBackground: frame window must be positive and representable");
        }
        if (spec.look == BackgroundLook::DocumentaryGrid ||
            spec.look == BackgroundLook::RadarSweep ||
            spec.look == BackgroundLook::ArchiveDust ||
            spec.look == BackgroundLook::MeshGradient ||
            spec.look == BackgroundLook::GridPattern ||
            spec.look == BackgroundLook::Particles ||
            spec.look == BackgroundLook::Aurora || spec.look == BackgroundLook::DarkVeil ||
            spec.look == BackgroundLook::DotGrid || spec.look == BackgroundLook::DotField ||
            spec.look == BackgroundLook::GradientWaves || spec.look == BackgroundLook::Grainient ||
            spec.look == BackgroundLook::RippleGrid || spec.look == BackgroundLook::ShapeGrid ||
            spec.look == BackgroundLook::Silk) {
            addAnimatedLookWindow(spec);
        }
        if (!(spec.barFraction >= 0.f) || spec.barFraction >= 0.5f) {
            throw std::invalid_argument("addBackground: the bar fraction must be in [0, 0.5)");
        }
        if (!(spec.pulse >= 0.f) || spec.pulse > 1.f) {
            throw std::invalid_argument("addBackground: the pulse must be in [0, 1]");
        }
        if (!(spec.gridSpacing >= 12.f) || !std::isfinite(spec.gridSpacing) || spec.gridSpacing > 2048.f ||
            !std::isfinite(spec.gridSpacingY) || spec.gridSpacingY < 0.f ||
            (spec.gridSpacingY > 0.f && spec.gridSpacingY < 12.f) || spec.gridSpacingY > 2048.f ||
            !std::isfinite(spec.gridOffsetX) || !std::isfinite(spec.gridOffsetY) ||
            std::abs(spec.gridOffsetX) > 16384.f || std::abs(spec.gridOffsetY) > 16384.f) {
            throw std::invalid_argument("addBackground: grid spacing and offsets are outside supported ranges");
        }
        if (!(spec.gridOpacity >= 0.f) || spec.gridOpacity > 1.f ||
            !(spec.scanOpacity >= 0.f) || spec.scanOpacity > 1.f) {
            throw std::invalid_argument("addBackground: grid and scan opacities must be in [0, 1]");
        }
        if (spec.majorEvery < 1 || spec.majorEvery > 32) {
            throw std::invalid_argument("addBackground: majorEvery must be in [1, 32]");
        }
        if (spec.particleCount < 0 || spec.particleCount > 256 ||
            spec.particleQuantity < 0 || spec.particleQuantity > 96) {
            throw std::invalid_argument("addBackground: archive count must be in [0, 256] and React particle quantity in [0, 96]");
        }
        if (!std::isfinite(spec.particleSize) || spec.particleSize <= 0.f || spec.particleSize > 32.f ||
            !std::isfinite(spec.particleVx) || !std::isfinite(spec.particleVy) ||
            std::abs(spec.particleVx) > 32.f || std::abs(spec.particleVy) > 32.f) {
            throw std::invalid_argument("addBackground: particle motion and size are outside supported ranges");
        }
        if (!std::isfinite(spec.meshSpeed) || spec.meshSpeed < 0.f || spec.meshSpeed > 8.f) {
            throw std::invalid_argument("addBackground: meshSpeed must be finite and in [0, 8]");
        }
        if (!validHexColor(spec.particleColor) || !std::isfinite(spec.particleSpread) ||
            spec.particleSpread <= 0.f || spec.particleSpread > 100.f ||
            !std::isfinite(spec.particleSpeed) || spec.particleSpeed < 0.f || spec.particleSpeed > 8.f ||
            !std::isfinite(spec.particleSizeRandomness) || spec.particleSizeRandomness < 0.f ||
            spec.particleSizeRandomness > 2.f || !std::isfinite(spec.particleCameraDistance) ||
            spec.particleCameraDistance < 1.f || spec.particleCameraDistance > 1000.f ||
            !std::isfinite(spec.particleHoverFactor) ||
            std::abs(spec.particleHoverFactor) > 8.f) {
            throw std::invalid_argument("addBackground: particle color, spread, speed, or size controls are invalid");
        }
        for (const auto& color : spec.particleColors) {
            if (!validHexColor(color)) throw std::invalid_argument("addBackground: particle palette colors must use #RRGGBB");
        }
        if (spec.particleColors.size() > 32)
            throw std::invalid_argument("addBackground: particle palette is limited to 32 colors");
        for (const auto& color : spec.aurora.colorStops) {
            if (!validHexColor(color)) throw std::invalid_argument("addBackground: Aurora colors must use #RRGGBB");
        }
        for (const auto& color : spec.gradientWaves.colors) {
            if (!validHexColor(color)) throw std::invalid_argument("addBackground: GradientWaves colors must use #RRGGBB");
        }
        for (const auto& color : spec.grainient.colors) {
            if (!validHexColor(color)) throw std::invalid_argument("addBackground: Grainient colors must use #RRGGBB");
        }
        for (const auto& color : {spec.dots.baseColor, spec.dots.activeColor, spec.rippleGrid.gridColor,
                                  spec.shapeGrid.borderColor, spec.shapeGrid.hoverFillColor,
                                  spec.silk.color}) {
            if (!validHexColor(color)) throw std::invalid_argument("addBackground: React background colors must use #RRGGBB");
        }
        for (const std::string& color : spec.meshColors) {
            if (!validHexColor(color)) {
                throw std::invalid_argument("addBackground: meshColors must use #RRGGBB hex colors");
            }
        }
        if (!validHexColor(spec.meshBackgroundColor)) {
            throw std::invalid_argument("addBackground: meshBackgroundColor must use #RRGGBB hex color");
        }
        for (const auto& square : spec.gridSquares) {
            if (square[0] < 0 || square[1] < 0) {
                throw std::invalid_argument("addBackground: grid square coordinates must be non-negative");
            }
        }
        if (spec.gridSquares.size() > 128) {
            throw std::invalid_argument("addBackground: gridSquares is limited to 128 cells");
        }
        const Vector2 canvas = scene.canvas();
        if (!std::isfinite(canvas.x) || !std::isfinite(canvas.y) ||
            canvas.x > 16384.f || canvas.y > 16384.f) {
            throw std::invalid_argument("addBackground: canvas dimensions must be finite and at most 16384 px");
        }
        if (spec.look == BackgroundLook::DotGrid || spec.look == BackgroundLook::DotField) {
            const float radius = spec.look == BackgroundLook::DotGrid
                ? std::max(0.5f, spec.dots.dotSize * 0.5f) : spec.dots.dotRadius;
            const float requested = spec.look == BackgroundLook::DotGrid
                ? spec.dots.dotSize + spec.dots.gap : spec.dots.dotSpacing;
            if (dotSpacingForCanvas(requested, radius, canvas) > requested)
                throw std::invalid_argument("addBackground: configured dot spacing would exceed the native dot-grid budget");
        }
        if (spec.look == BackgroundLook::DocumentaryGrid || spec.look == BackgroundLook::RadarSweep ||
            spec.look == BackgroundLook::GridPattern) {
            const float spacingY = spec.look == BackgroundLook::GridPattern && spec.gridSpacingY > 0.f
                                       ? spec.gridSpacingY : spec.gridSpacing;
            double estimatedAccents = std::ceil(static_cast<double>(canvas.x) / spec.gridSpacing) +
                                      std::ceil(static_cast<double>(canvas.y) / spacingY) + 2.0;
            if (spec.look == BackgroundLook::DocumentaryGrid) {
                estimatedAccents += 4.0 + static_cast<double>(spec.gridSquares.size());
            } else if (spec.look == BackgroundLook::RadarSweep) {
                // Two scan layers plus four marker ellipses accompany its grid.
                estimatedAccents += 6.0;
            } else {
                estimatedAccents += static_cast<double>(spec.gridSquares.size());
            }
            // Include the always-present ground so the actual composition is bounded.
            if (estimatedAccents + 1.0 > 192.0) {
                throw std::invalid_argument("addBackground: grid would exceed the 192-layer composition budget");
            }
        }
        const int inFrame = spec.inFrame;
        if (!std::isfinite(spec.aurora.amplitude) || spec.aurora.amplitude < 0.f || spec.aurora.amplitude > 4.f ||
            !std::isfinite(spec.aurora.blend) || spec.aurora.blend <= 0.f || spec.aurora.blend > 1.f ||
            !std::isfinite(spec.aurora.speed) || spec.aurora.speed < 0.f || spec.aurora.speed > 8.f ||
            !std::isfinite(spec.darkVeil.hueShift) || std::abs(spec.darkVeil.hueShift) > 360.f ||
            !std::isfinite(spec.darkVeil.noiseIntensity) || spec.darkVeil.noiseIntensity < 0.f || spec.darkVeil.noiseIntensity > 1.f ||
            !std::isfinite(spec.darkVeil.scanlineIntensity) || spec.darkVeil.scanlineIntensity < 0.f || spec.darkVeil.scanlineIntensity > 1.f ||
            !std::isfinite(spec.darkVeil.speed) || spec.darkVeil.speed < 0.f || spec.darkVeil.speed > 8.f ||
            !std::isfinite(spec.darkVeil.scanlineFrequency) || spec.darkVeil.scanlineFrequency < 0.f || spec.darkVeil.scanlineFrequency > 100.f ||
            !std::isfinite(spec.darkVeil.warpAmount) || spec.darkVeil.warpAmount < 0.f || spec.darkVeil.warpAmount > 1.f ||
            !std::isfinite(spec.darkVeil.resolutionScale) || spec.darkVeil.resolutionScale <= 0.f || spec.darkVeil.resolutionScale > 2.f ||
            !std::isfinite(spec.dots.dotSize) || spec.dots.dotSize <= 0.f || spec.dots.dotSize > 64.f ||
            !std::isfinite(spec.dots.gap) || spec.dots.gap < 0.f || spec.dots.gap > 256.f ||
            !std::isfinite(spec.dots.dotRadius) || spec.dots.dotRadius < 0.5f || spec.dots.dotRadius > 64.f ||
            !std::isfinite(spec.dots.dotSpacing) || spec.dots.dotSpacing < 0.f || spec.dots.dotSpacing > 256.f ||
            !std::isfinite(spec.dots.glowRadius) || spec.dots.glowRadius < 0.f || spec.dots.glowRadius > 8192.f ||
            !std::isfinite(spec.dots.cursorRadius) || spec.dots.cursorRadius <= 0.f || spec.dots.cursorRadius > 4096.f ||
            !std::isfinite(spec.dots.cursorForce) || std::abs(spec.dots.cursorForce) > 8.f ||
            !std::isfinite(spec.dots.bulgeStrength) || spec.dots.bulgeStrength < 0.f || spec.dots.bulgeStrength > 512.f ||
            !std::isfinite(spec.dots.waveAmplitude) || spec.dots.waveAmplitude < 0.f || spec.dots.waveAmplitude > 128.f ||
            !std::isfinite(spec.gradientWaves.speed) || spec.gradientWaves.speed < 0.f || spec.gradientWaves.speed > 8.f ||
            !std::isfinite(spec.gradientWaves.waveScale) || spec.gradientWaves.waveScale <= 0.f || spec.gradientWaves.waveScale > 8.f ||
            !std::isfinite(spec.gradientWaves.opacity) || spec.gradientWaves.opacity < 0.f || spec.gradientWaves.opacity > 1.f ||
            !std::isfinite(spec.gradientWaves.amplitude) || spec.gradientWaves.amplitude < 0.f || spec.gradientWaves.amplitude > 8.f ||
            !std::isfinite(spec.gradientWaves.waveRatio) || spec.gradientWaves.waveRatio < 0.1f || spec.gradientWaves.waveRatio > 4.f ||
            !std::isfinite(spec.gradientWaves.swell) || std::abs(spec.gradientWaves.swell) > 1000.f ||
            !std::isfinite(spec.gradientWaves.turbulence) || spec.gradientWaves.turbulence < 0.f || spec.gradientWaves.turbulence > 100.f ||
            !std::isfinite(spec.gradientWaves.tilt) || std::abs(spec.gradientWaves.tilt) > 360.f ||
            !std::isfinite(spec.gradientWaves.zoom) || spec.gradientWaves.zoom <= 0.f || spec.gradientWaves.zoom > 16.f ||
            !std::isfinite(spec.gradientWaves.height) || spec.gradientWaves.height <= 0.f || spec.gradientWaves.height > 100.f ||
            !std::isfinite(spec.gradientWaves.fogDepth) || spec.gradientWaves.fogDepth < 0.f || spec.gradientWaves.fogDepth > 100.f ||
            !std::isfinite(spec.gradientWaves.grainIntensity) || spec.gradientWaves.grainIntensity < 0.f || spec.gradientWaves.grainIntensity > 1.f ||
            spec.gradientWaves.detail < 0 || spec.gradientWaves.detail > 2 ||
            !std::isfinite(spec.grainient.warpFrequency) || spec.grainient.warpFrequency <= 0.f || spec.grainient.warpFrequency > 40.f ||
            !std::isfinite(spec.grainient.warpStrength) || spec.grainient.warpStrength < 0.f || spec.grainient.warpStrength > 4.f ||
            !std::isfinite(spec.grainient.timeSpeed) || spec.grainient.timeSpeed < 0.f || spec.grainient.timeSpeed > 8.f ||
            !std::isfinite(spec.grainient.grainAmount) || spec.grainient.grainAmount < 0.f || spec.grainient.grainAmount > 1.f ||
            !std::isfinite(spec.grainient.contrast) || spec.grainient.contrast < 0.f || spec.grainient.contrast > 4.f ||
            !std::isfinite(spec.grainient.gamma) || spec.grainient.gamma < 0.f || spec.grainient.gamma > 4.f ||
            !std::isfinite(spec.grainient.blendAngle) || std::abs(spec.grainient.blendAngle) > 360.f ||
            !std::isfinite(spec.grainient.blendSoftness) || spec.grainient.blendSoftness < 0.f || spec.grainient.blendSoftness > 1.f ||
            !std::isfinite(spec.grainient.rotationAmount) || std::abs(spec.grainient.rotationAmount) > 36000.f ||
            !std::isfinite(spec.grainient.noiseScale) || spec.grainient.noiseScale <= 0.f || spec.grainient.noiseScale > 64.f ||
            !std::isfinite(spec.grainient.grainScale) || spec.grainient.grainScale <= 0.f || spec.grainient.grainScale > 256.f ||
            !std::isfinite(spec.grainient.colorBalance) || std::abs(spec.grainient.colorBalance) > 1.f ||
            !std::isfinite(spec.grainient.centerX) || std::abs(spec.grainient.centerX) > 1.f ||
            !std::isfinite(spec.grainient.centerY) || std::abs(spec.grainient.centerY) > 1.f ||
            !std::isfinite(spec.grainient.zoom) || spec.grainient.zoom <= 0.f || spec.grainient.zoom > 16.f ||
            !std::isfinite(spec.rippleGrid.mouseInteractionRadius) || spec.rippleGrid.mouseInteractionRadius < 0.f || spec.rippleGrid.mouseInteractionRadius > 100.f ||
            !std::isfinite(spec.rippleGrid.rotationDegrees) || std::abs(spec.rippleGrid.rotationDegrees) > 360.f ||
            !std::isfinite(spec.rippleGrid.fadeDistance) || spec.rippleGrid.fadeDistance < 0.f || spec.rippleGrid.fadeDistance > 10.f ||
            !std::isfinite(spec.rippleGrid.glowIntensity) || spec.rippleGrid.glowIntensity < 0.f || spec.rippleGrid.glowIntensity > 1.f ||
            !std::isfinite(spec.rippleGrid.opacity) || spec.rippleGrid.opacity < 0.f || spec.rippleGrid.opacity > 1.f ||
            !std::isfinite(spec.grainient.timeSpeed) || spec.grainient.timeSpeed < 0.f || spec.grainient.timeSpeed > 8.f ||
            !std::isfinite(spec.rippleGrid.gridSize) || spec.rippleGrid.gridSize < 4.f || spec.rippleGrid.gridSize > 512.f ||
            !std::isfinite(spec.rippleGrid.gridThickness) || spec.rippleGrid.gridThickness <= 0.f || spec.rippleGrid.gridThickness > 100.f ||
            !std::isfinite(spec.rippleGrid.rippleIntensity) || spec.rippleGrid.rippleIntensity < 0.f || spec.rippleGrid.rippleIntensity > 1.f ||
            !std::isfinite(spec.shapeGrid.squareSize) || spec.shapeGrid.squareSize < 8.f || spec.shapeGrid.squareSize > 512.f ||
            !std::isfinite(spec.shapeGrid.speed) || spec.shapeGrid.speed < 0.f || spec.shapeGrid.speed > 16.f ||
            spec.shapeGrid.hoverTrailAmount < 0 || spec.shapeGrid.hoverTrailAmount > 128 ||
            !std::isfinite(spec.silk.speed) || spec.silk.speed < 0.f || spec.silk.speed > 20.f ||
            !std::isfinite(spec.silk.scale) || spec.silk.scale <= 0.f || spec.silk.scale > 16.f ||
            !std::isfinite(spec.silk.noiseIntensity) || spec.silk.noiseIntensity < 0.f || spec.silk.noiseIntensity > 8.f ||
            !std::isfinite(spec.silk.rotation) || std::abs(spec.silk.rotation) > 360.f) {
            throw std::invalid_argument("addBackground: React-inspired background controls are outside supported ranges");
        }
        const int endFrame = spec.inFrame + spec.duration;
        const int exitFrames = exitFramesFor(spec.duration);
        const int exitStart = endFrame - exitFrames;
        const int enterFrames = std::max(1, spec.duration / 10);

        const auto dress = [&](LayerHandle& layer, const char* suffix) {
            layer.alive(inFrame, endFrame);
            layer.animate(FadeIn{.inFrame = inFrame, .duration = enterFrames});
            layer.animate(FadeOut{.startFrame = exitStart, .duration = exitFrames});
            (void) suffix;
            return &layer;
        };

        BackgroundComposition out;
        out.inFrame = inFrame;
        out.endFrame = endFrame;

        LayerHandle& ground = scene.shape(ShapeSpec{.size = canvas,
                                                    .fillColor = spec.look == BackgroundLook::MeshGradient
                                                                    ? spec.meshBackgroundColor
                                                                    : spec.ground,
                                                    .name = spec.name + "_ground"});
        ground.position(canvas.x * 0.5f, canvas.y * 0.5f);
        out.ground = dress(ground, "ground");

        switch (spec.look) {
            case BackgroundLook::SolidTint:
                break;

            case BackgroundLook::LetterboxBars: {
                const float barHeight = canvas.y * spec.barFraction;
                if (barHeight > 0.f) {
                    LayerHandle& top = scene.shape(ShapeSpec{
                            .size = Vector2(canvas.x, barHeight),
                            .fillColor = spec.accent,
                            .name = spec.name + "_bar_top"});
                    top.position(canvas.x * 0.5f, barHeight * 0.5f);
                    out.accents.push_back(dress(top, "bar_top"));

                    LayerHandle& bottom = scene.shape(ShapeSpec{
                            .size = Vector2(canvas.x, barHeight),
                            .fillColor = spec.accent,
                            .name = spec.name + "_bar_bottom"});
                    bottom.position(canvas.x * 0.5f, canvas.y - barHeight * 0.5f);
                    out.accents.push_back(dress(bottom, "bar_bottom"));
                }
                break;
            }

            case BackgroundLook::VerticalSplit: {
                const float halfWidth = canvas.x * 0.5f;
                LayerHandle& left = scene.shape(ShapeSpec{
                        .size = Vector2(halfWidth, canvas.y),
                        .fillColor = spec.accent,
                        .name = spec.name + "_left"});
                left.position(halfWidth * 0.5f, canvas.y * 0.5f);
                out.accents.push_back(dress(left, "left"));

                const float seamWidth = std::max(2.f, canvas.x * 0.004f);
                LayerHandle& seam = scene.shape(ShapeSpec{
                        .size = Vector2(seamWidth, canvas.y),
                        .fillColor = spec.seam,
                        .name = spec.name + "_seam"});
                seam.position(canvas.x * 0.5f, canvas.y * 0.5f);
                out.accents.push_back(dress(seam, "seam"));
                break;
            }

            case BackgroundLook::VignettePulse: {
                LayerHandle& veil = scene.shape(ShapeSpec{
                        .size = canvas,
                        .fillColor = spec.accent,
                        .name = spec.name + "_veil"});
                veil.position(canvas.x * 0.5f, canvas.y * 0.5f);
                veil.alive(inFrame, endFrame);
                const float low = std::max(0.f, 0.5f - spec.pulse);
                const float high = std::min(1.f, 0.5f + spec.pulse);
                const int half = std::max(1, spec.duration / 2);
                veil.animateOpacity(inFrame, half, low, high);
                veil.animateOpacity(inFrame + half, half, high, low);
                out.accents.push_back(&veil);
                break;
            }

            case BackgroundLook::CornerGlow: {
                const float block = std::min(canvas.x, canvas.y) * 0.45f;
                LayerHandle& glow = scene.shape(ShapeSpec{
                        .size = Vector2(block, block),
                        .fillColor = spec.accent,
                        .name = spec.name + "_glow",
                        .cornerRadius = block * 0.5f});
                glow.position(block * 0.5f, block * 0.5f);
                glow.alive(inFrame, endFrame);
                const float low = std::max(0.f, 0.35f - spec.pulse);
                const float high = std::min(1.f, 0.35f + spec.pulse);
                const int half = std::max(1, spec.duration / 2);
                glow.animateOpacity(inFrame, half, low, high);
                glow.animateOpacity(inFrame + half, half, high, low);
                out.accents.push_back(&glow);
                break;
            }

            case BackgroundLook::DocumentaryGrid:
                addDocumentaryGrid(scene, spec, out, canvas, inFrame, endFrame);
                break;

            case BackgroundLook::RadarSweep:
                addRadarSweep(scene, spec, out, canvas, inFrame, endFrame);
                break;

            case BackgroundLook::ArchiveDust:
                addArchiveDust(scene, spec, out, canvas, inFrame, endFrame);
                break;

            case BackgroundLook::MeshGradient:
                addMeshGradient(scene, spec, out, canvas, inFrame, endFrame);
                break;

            case BackgroundLook::GridPattern:
                addGridPattern(scene, spec, out, canvas, inFrame, endFrame);
                break;

            case BackgroundLook::Particles:
                addReactParticles(scene, spec, out, canvas, inFrame, endFrame);
                break;
            case BackgroundLook::Aurora:
            case BackgroundLook::DarkVeil:
            case BackgroundLook::DotGrid:
            case BackgroundLook::DotField:
            case BackgroundLook::GradientWaves:
            case BackgroundLook::Grainient:
            case BackgroundLook::RippleGrid:
            case BackgroundLook::ShapeGrid:
            case BackgroundLook::Silk:
                addReactField(scene, spec, out, canvas, inFrame, endFrame);
                break;
        }

        return out;
    }

}// namespace chronontemplate
