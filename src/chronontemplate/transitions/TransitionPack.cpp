#include "chronontemplate/transitions/TransitionPack.hpp"

#include <algorithm>
#include <cmath>
#include <stdexcept>
#include <string>

namespace chronontemplate {

    namespace {

        using Vector2 = chrononmotion::Vector2;
        using Vector3 = chrononmotion::Vector3;
        namespace pm = chrononmotion::motion::presets;
        using chrononmotion::motion::Easing;
        using chrononmotion::motion::Track;

        /// Frames -> seconds, the one conversion the motion core presets use.
        [[nodiscard]] inline float frameTime(const int frame, const float fps) {
            return chrononmotion::motion::frameToTime(frame, fps);
        }

        /// The travel direction as a unit XY vector (z flattened).
        [[nodiscard]] Vector3 slideAxis(pm::Direction direction) {
            const Vector3 unit = pm::directionOffset(direction);
            return Vector3(unit.x, unit.y, 0.f);
        }

        /// The front of the composition: the camera sits at z = +height looking at
        /// the z = 0 plane, so a plate at +z is in front of the content.
        constexpr float kPlateZ = 10.f;

        TransitionComposition rangeOf(const TransitionSpec& spec, int cover) {
            TransitionComposition out;
            out.inFrame = spec.inFrame;
            out.coverFrame = spec.inFrame + cover;
            out.endFrame = spec.inFrame + spec.duration;
            return out;
        }

        // ── Wipe / PushThrough: one or two full-span bars sweeping across ─────

        TransitionComposition addSweep(TemplateScene& scene, const TransitionSpec& spec, bool trailing) {
            const Vector2 canvas = scene.canvas();
            const float fps = scene.fps();
            const Vector3 unit = slideAxis(spec.travel);
            const bool horizontal = std::fabs(unit.x) > std::fabs(unit.y);
            const float span = horizontal ? canvas.x : canvas.y;
            const Vector2 barSize = horizontal ? Vector2(canvas.x * 2.f, canvas.y)
                                               : Vector2(canvas.x, canvas.y * 2.f);
            const Vector3 center(canvas.x * 0.5f, canvas.y * 0.5f, kPlateZ);
            const float reach = span * 2.5f;

            TransitionComposition out = rangeOf(spec, spec.duration / 2);
            const int inFrame = spec.inFrame;
            const int endFrame = out.endFrame;

            // A bar of twice the frame span covers the whole frame for the whole
            // middle of its travel: at offset 0 it spans [pos - span, pos + span]
            // across the axis, and the sweep is linear so the cover frame lands
            // exactly on the authored midpoint.
            auto bar = [&](const std::string& color, const std::string& name) -> Track<Vector3>& {
                LayerHandle& plate = scene.shape(ShapeSpec{.size = barSize,
                                                           .fillColor = color,
                                                           .name = name});
                plate.position(center.x, center.y, center.z)
                     .anchor(barSize.x * 0.5f, barSize.y * 0.5f)
                     .alive(inFrame, endFrame);
                out.plates.push_back(&plate);
                return plate.layer().tracks.position;
            };

            Track<Vector3>& leading = bar(spec.plateColor, spec.name + "_lead");
            leading.add(frameTime(inFrame, fps), center - unit * reach, Easing::linear());
            leading.add(frameTime(endFrame, fps), center + unit * reach, Easing::linear());

            if (trailing) {
                // The incoming plate follows the leader by a third of the window
                // and crosses faster, so the uncover reads as being pushed.
                const int lead = std::max(1, spec.duration / 3);
                Track<Vector3>& trailer = bar(spec.inColor, spec.name + "_trail");
                trailer.add(frameTime(inFrame, fps), center - unit * reach, Easing::linear());
                trailer.add(frameTime(inFrame + lead, fps), center - unit * reach, Easing::linear());
                trailer.add(frameTime(endFrame, fps), center + unit * reach, Easing::linear());
            }
            return out;
        }

        // ── DipToBlack / DipToColor / LightLeak: a plate that fades in place ──

        void addDip(TemplateScene& scene, const TransitionSpec& spec, const Vector2& canvas,
                    const std::string& color, const std::string& suffix, TransitionComposition& out) {
            const int cover = spec.duration / 2;
            LayerHandle& plate = scene.shape(ShapeSpec{.size = canvas,
                                                       .fillColor = color,
                                                       .name = spec.name + "_" + suffix});
            plate.position(canvas.x * 0.5f, canvas.y * 0.5f, kPlateZ)
                 .opacity(0.f)
                 .alive(spec.inFrame, out.endFrame);
            plate.animateOpacity(spec.inFrame, cover, 0.f, 1.f, Easing::easeInOut());
            plate.animateOpacity(spec.inFrame + cover, spec.duration - cover, 1.f, 0.f,
                                 Easing::easeInOut());
            out.plates.push_back(&plate);
            out.coverFrame = spec.inFrame + cover;
        }

        // ── Blinds: slats that grow closed and grow away ─────────────────────

        TransitionComposition addBlinds(TemplateScene& scene, const TransitionSpec& spec) {
            const Vector2 canvas = scene.canvas();
            const float fps = scene.fps();
            const int n = spec.slices;
            const int inFrame = spec.inFrame;
            const int cover = spec.duration / 2;
            const int uncover = spec.duration - cover;
            const int staggerIn = cover > 1 ? std::max(1, (cover - 1) / n) : 0;
            const int staggerOut = uncover > 1 ? std::max(1, (uncover - 1) / n) : 0;
            const int grow = std::max(1, cover - (n - 1) * staggerIn);
            const int shrink = std::max(1, uncover - (n - 1) * staggerOut);
            const float slatH = canvas.y / static_cast<float>(n);

            TransitionComposition out = rangeOf(spec, cover);

            // Scale never reaches an exact zero: the RenderPlan lowering fails
            // closed on singular transforms, and a 2% sliver is already invisible.
            const Vector3 open(0.02f, 1.f, 1.f);
            const Vector3 shut(1.f, 1.f, 1.f);

            for (int i = 0; i < n; ++i) {
                LayerHandle& slat = scene.shape(ShapeSpec{
                        .size = Vector2(canvas.x, slatH + 1.f),
                        .fillColor = spec.plateColor,
                        .name = spec.name + "_slat_" + std::to_string(i)});
                slat.position(0.f, (static_cast<float>(i) + 0.5f) * slatH, kPlateZ)
                    .anchor(0.f, (slatH + 1.f) * 0.5f)
                    .alive(inFrame, out.endFrame);

                // Every slat is fully closed on the cover frame: the last one
                // finishes exactly there, the earlier ones hold their shut key.
                const int tA = inFrame + i * staggerIn;
                const int tB = tA + grow;
                const int tC = inFrame + cover + i * staggerOut;
                const int tD = tC + shrink;
                Track<Vector3>& scale = slat.layer().tracks.scale;
                scale.add(frameTime(tA, fps), open, Easing::easeInOut());
                scale.add(frameTime(tB, fps), shut, Easing::easeInOut());
                scale.add(frameTime(tC, fps), shut, Easing::easeInOut());
                scale.add(frameTime(tD, fps), open, Easing::easeInOut());
                out.plates.push_back(&slat);
            }
            return out;
        }

        // ── IrisCircle: a round plate that grows over the cut and shrinks away ─

        TransitionComposition addIris(TemplateScene& scene, const TransitionSpec& spec) {
            const Vector2 canvas = scene.canvas();
            const float fps = scene.fps();
            const float d = std::max(canvas.x, canvas.y);
            const int cover = spec.duration / 2;

            TransitionComposition out = rangeOf(spec, cover);

            LayerHandle& plate = scene.shape(ShapeSpec{.size = Vector2(d, d),
                                                       .fillColor = spec.plateColor,
                                                       .name = spec.name + "_iris",
                                                       .cornerRadius = d * 0.5f});
            plate.position(canvas.x * 0.5f, canvas.y * 0.5f, kPlateZ)
                 .anchor(d * 0.5f, d * 0.5f)
                 .alive(spec.inFrame, out.endFrame);

            const Vector3 shut(1.05f, 1.05f, 1.f);
            const Vector3 open(0.02f, 0.02f, 1.f);
            Track<Vector3>& scale = plate.layer().tracks.scale;
            scale.add(frameTime(spec.inFrame, fps), open, Easing::easeInOut());
            scale.add(frameTime(spec.inFrame + cover, fps), shut, Easing::easeInOut());
            scale.add(frameTime(out.endFrame, fps), open, Easing::easeInOut());
            out.plates.push_back(&plate);
            return out;
        }

        // ── Fast light looks: shape-only approximations, no fake RGB/effects ──

        TransitionComposition addLightSweep(TemplateScene& scene, const TransitionSpec& spec,
                                            bool diagonal, bool whip) {
            const Vector2 canvas = scene.canvas();
            const float fps = scene.fps();
            const int duration = spec.duration;
            const int peak = std::max(1, duration / 2);
            const int end = spec.inFrame + duration;
            const float diagonalSpan = std::sqrt(canvas.x * canvas.x + canvas.y * canvas.y);
            const bool leftToRight = spec.travel != pm::Direction::Left && spec.travel != pm::Direction::Up;
            const float direction = leftToRight ? 1.f : -1.f;
            const Vector2 size = diagonal
                    ? Vector2(diagonalSpan * 1.6f, diagonalSpan * 0.42f)
                    : Vector2(canvas.x * 1.65f, canvas.y * (whip ? 0.28f : 0.62f));
            const float reach = diagonal ? diagonalSpan * 0.9f : canvas.x * 1.1f;
            const Vector3 center(canvas.x * 0.5f, canvas.y * 0.5f, kPlateZ);
            LayerHandle& beam = scene.shape(ShapeSpec{.size = size,
                                                       .fillColor = spec.leakColor,
                                                       .name = spec.name + "_beam",
                                                       .cornerRadius = diagonal ? size.y * 0.45f : size.y * 0.35f});
            beam.position(center.x, center.y, center.z)
                .opacity(0.f)
                .alive(spec.inFrame, end);
            const float angle = diagonal ? (leftToRight ? -0.62f : 0.62f) : 0.f;
            beam.layer().tracks.rotation.add(frameTime(spec.inFrame, fps), Vector3(0.f, 0.f, angle), Easing::linear());
            beam.layer().tracks.rotation.add(frameTime(end, fps), Vector3(0.f, 0.f, angle), Easing::linear());
            Track<Vector3>& position = beam.layer().tracks.position;
            const float startX = center.x - direction * reach;
            const float finishX = center.x + direction * reach;
            position.add(frameTime(spec.inFrame, fps), Vector3(startX, center.y, center.z), Easing::linear());
            position.add(frameTime(spec.inFrame + peak, fps), Vector3(center.x, center.y, center.z), Easing::linear());
            position.add(frameTime(end, fps), Vector3(finishX, center.y, center.z), Easing::linear());
            beam.animateOpacity(spec.inFrame, peak, 0.f, spec.leakPeakOpacity, Easing::easeInOut());
            beam.animateOpacity(spec.inFrame + peak, duration - peak, spec.leakPeakOpacity, 0.f, Easing::easeInOut());
            TransitionComposition out = rangeOf(spec, peak);
            out.plates.push_back(&beam);
            return out;
        }

        TransitionComposition addCornerBurn(TemplateScene& scene, const TransitionSpec& spec) {
            const Vector2 canvas = scene.canvas();
            const float fps = scene.fps();
            const float diameter = std::max(canvas.x, canvas.y) * 1.5f;
            const int peak = std::max(1, spec.duration / 2);
            TransitionComposition out = rangeOf(spec, peak);
            LayerHandle& burn = scene.shape(ShapeSpec{.size = Vector2(diameter, diameter),
                                                       .fillColor = spec.leakColor,
                                                       .name = spec.name + "_corner_burn",
                                                       .cornerRadius = diameter * 0.5f});
            const bool right = spec.travel == pm::Direction::Left || spec.travel == pm::Direction::Down;
            const bool bottom = spec.travel == pm::Direction::Up || spec.travel == pm::Direction::Left;
            const float x = right ? canvas.x : 0.f;
            const float y = bottom ? canvas.y : 0.f;
            burn.position(x, y, kPlateZ)
                .opacity(0.f).alive(spec.inFrame, out.endFrame);
            burn.animateOpacity(spec.inFrame, peak, 0.f, spec.leakPeakOpacity, Easing::easeOut());
            burn.animateOpacity(spec.inFrame + peak, spec.duration - peak,
                                spec.leakPeakOpacity, 0.f, Easing::easeIn());
            const float halfScale = (std::max(canvas.x, canvas.y) / diameter) * 0.8f;
            const float overscale = std::max(canvas.x, canvas.y) / diameter * 1.8f;
            burn.layer().tracks.scale.add(frameTime(spec.inFrame, fps), Vector3(halfScale, halfScale, 1.f), Easing::easeOut());
            burn.layer().tracks.scale.add(frameTime(spec.inFrame + peak, fps), Vector3(overscale, overscale, 1.f), Easing::easeOut());
            burn.layer().tracks.scale.add(frameTime(out.endFrame, fps), Vector3(halfScale, halfScale, 1.f), Easing::easeIn());
            out.plates.push_back(&burn);
            return out;
        }

        TransitionComposition addWhiteout(TemplateScene& scene, const TransitionSpec& spec) {
            const Vector2 canvas = scene.canvas();
            const int warmPeak = std::max(1, spec.duration / 3);
            const int whitePeak = std::max(warmPeak + 1, (spec.duration * 2) / 3);
            TransitionComposition out = rangeOf(spec, whitePeak);
            auto makeWash = [&](const std::string& color, const std::string& suffix,
                                int from, int peak, int to, float maxOpacity) {
                LayerHandle& wash = scene.shape(ShapeSpec{.size = canvas, .fillColor = color,
                                                          .name = spec.name + suffix});
                wash.position(canvas.x * 0.5f, canvas.y * 0.5f, kPlateZ + (suffix == "_white" ? 1.f : 0.f))
                    .opacity(0.f).alive(spec.inFrame, out.endFrame);
                wash.animateOpacity(spec.inFrame + from, std::max(1, peak - from), 0.f, maxOpacity, Easing::easeInOut());
                wash.animateOpacity(spec.inFrame + peak, std::max(1, to - peak), maxOpacity, 0.f, Easing::easeInOut());
                out.plates.push_back(&wash);
            };
            makeWash(spec.leakColor, "_warm", 0, warmPeak, spec.duration, spec.leakPeakOpacity);
            makeWash("#FFFFFF", "_white", warmPeak, whitePeak, spec.duration, 1.f);
            out.coverFrame = spec.inFrame + whitePeak;
            return out;
        }

        TransitionComposition addDoublePass(TemplateScene& scene, const TransitionSpec& spec) {
            const Vector2 canvas = scene.canvas();
            const float fps = scene.fps();
            const int end = spec.inFrame + spec.duration;
            const float beamHeight = canvas.y * 1.4f;
            const Vector2 size(canvas.x * 1.4f, beamHeight);
            const Vector3 center(canvas.x * 0.5f, canvas.y * 0.5f, kPlateZ);
            TransitionComposition out = rangeOf(spec, spec.duration / 2);
            for (int i = 0; i < 2; ++i) {
                const float sign = i == 0 ? -1.f : 1.f;
                LayerHandle& beam = scene.shape(ShapeSpec{.size = size, .fillColor = spec.leakColor,
                                                           .name = spec.name + "_pass_" + std::to_string(i),
                                                           .cornerRadius = beamHeight * 0.3f});
                beam.position(center.x, center.y, kPlateZ + static_cast<float>(i) * 0.1f)
                    .opacity(0.f).alive(spec.inFrame, end);
                const int start = spec.inFrame + i * std::max(1, spec.duration / 4);
                const int peak = std::min(end - 1, start + std::max(1, (end - start) / 2));
                const float z = beam.layer().transform.position.z;
                beam.layer().tracks.position.add(frameTime(spec.inFrame, fps), Vector3(center.x - sign * canvas.x, center.y, z), Easing::linear());
                beam.layer().tracks.position.add(frameTime(start, fps), Vector3(center.x - sign * canvas.x, center.y, z), Easing::linear());
                beam.layer().tracks.position.add(frameTime(peak, fps), center, Easing::linear());
                beam.layer().tracks.position.add(frameTime(end, fps), Vector3(center.x + sign * canvas.x, center.y, beam.layer().transform.position.z), Easing::linear());
                beam.animateOpacity(start, std::max(1, peak - start), 0.f, spec.leakPeakOpacity, Easing::easeInOut());
                beam.animateOpacity(peak, std::max(1, end - peak), spec.leakPeakOpacity, 0.f, Easing::easeInOut());
                out.plates.push_back(&beam);
            }
            return out;
        }

        TransitionComposition addFilmBurn(TemplateScene& scene, const TransitionSpec& spec) {
            const Vector2 canvas = scene.canvas();
            const int firstPeak = std::max(1, spec.duration / 3);
            TransitionComposition out = rangeOf(spec, firstPeak);
            // Three broad, rounded edge emitters create a deterministic, coarse
            // burn approximation. They are explicitly not turbulent/organic.
            for (int edge = 0; edge < 3; ++edge) {
                const bool vertical = edge == 2;
                const float thickness = (edge == 1 ? 0.42f : 0.28f) * (vertical ? canvas.x : canvas.y);
                const Vector2 size = vertical ? Vector2(thickness, canvas.y * 1.08f)
                                              : Vector2(canvas.x * 1.08f, thickness);
                const float x = vertical ? thickness * 0.5f : canvas.x * 0.5f;
                const float y = edge == 0 ? thickness * 0.5f
                                          : (edge == 1 ? canvas.y - thickness * 0.5f : canvas.y * 0.5f);
                LayerHandle& plate = scene.shape(ShapeSpec{.size = size,
                                                             .fillColor = edge == 2 ? "#FF5A24" : spec.leakColor,
                                                             .name = spec.name + "_edge_" + std::to_string(edge),
                                                             .cornerRadius = thickness * 0.45f});
                plate.position(x, y, kPlateZ + static_cast<float>(edge) * 0.1f)
                    .opacity(0.f).alive(spec.inFrame, out.endFrame);
                const int onset = spec.inFrame + edge * std::max(1, spec.duration / 8);
                plate.animateOpacity(onset, std::max(1, firstPeak - edge), 0.f,
                                     spec.leakPeakOpacity * (edge == 2 ? 0.55f : 1.f), Easing::easeOut());
                plate.animateOpacity(spec.inFrame + firstPeak, spec.duration - firstPeak,
                                     spec.leakPeakOpacity * (edge == 2 ? 0.55f : 1.f), 0.f, Easing::easeIn());
                out.plates.push_back(&plate);
            }
            return out;
        }

        TransitionComposition addCenterBurst(TemplateScene& scene, const TransitionSpec& spec) {
            const Vector2 canvas = scene.canvas();
            const float fps = scene.fps();
            const float diameter = std::max(canvas.x, canvas.y) * 1.2f;
            const int peak = std::max(1, spec.duration / 2);
            TransitionComposition out = rangeOf(spec, peak);
            LayerHandle& burst = scene.shape(ShapeSpec{.size = Vector2(diameter, diameter),
                                                        .fillColor = spec.leakColor,
                                                        .name = spec.name + "_burst",
                                                        .cornerRadius = diameter * 0.5f});
            burst.position(canvas.x * 0.5f, canvas.y * 0.5f, kPlateZ)
                .opacity(0.f).alive(spec.inFrame, out.endFrame);
            const float small = std::min(canvas.x, canvas.y) / diameter * 0.02f;
            const float large = std::max(canvas.x, canvas.y) / diameter * 1.8f;
            burst.layer().tracks.scale.add(frameTime(spec.inFrame, fps), Vector3(small, small, 1.f), Easing::easeOut());
            burst.layer().tracks.scale.add(frameTime(spec.inFrame + peak, fps), Vector3(large, large, 1.f), Easing::easeOut());
            burst.layer().tracks.scale.add(frameTime(out.endFrame, fps), Vector3(small, small, 1.f), Easing::easeIn());
            burst.animateOpacity(spec.inFrame, peak, 0.f, spec.leakPeakOpacity, Easing::easeOut());
            burst.animateOpacity(spec.inFrame + peak, spec.duration - peak, spec.leakPeakOpacity, 0.f, Easing::easeIn());
            out.plates.push_back(&burst);
            return out;
        }

        // ── BarnDoors / CurtainLift: paired plates meeting at the cover ────

        TransitionComposition addPairedDoors(TemplateScene& scene, const TransitionSpec& spec,
                                             bool vertical) {
            const Vector2 canvas = scene.canvas();
            const float fps = scene.fps();
            const int cover = spec.duration / 2;
            TransitionComposition out = rangeOf(spec, cover);
            const float half = vertical ? canvas.x * 0.5f : canvas.y * 0.5f;
            const Vector2 size = vertical ? Vector2(half + 1.f, canvas.y)
                                          : Vector2(canvas.x, half + 1.f);
            const float span = vertical ? canvas.x : canvas.y;
            const float fixed = vertical ? canvas.y * 0.5f : canvas.x * 0.5f;
            for (int i = 0; i < 2; ++i) {
                const float sign = i == 0 ? -1.f : 1.f;
                LayerHandle& door = scene.shape(ShapeSpec{.size = size,
                                                           .fillColor = spec.plateColor,
                                                           .name = spec.name + "_door_" + std::to_string(i)});
                // Closed: the pair tiles the frame (centres at 1/4 and 3/4).
                // Open: parked fully off-screen on its own side.
                const float closedAlong = span * 0.5f + sign * span * 0.25f;
                const float openAlong = sign < 0.f ? -(half + 1.f) * 0.5f
                                                   : span + (half + 1.f) * 0.5f;
                auto at = [&](float along) -> Vector3 {
                    return vertical ? Vector3(along, fixed, kPlateZ)
                                    : Vector3(fixed, along, kPlateZ);
                };
                door.position(at(openAlong).x, at(openAlong).y, kPlateZ)
                    .anchor(size.x * 0.5f, size.y * 0.5f)
                    .alive(spec.inFrame, out.endFrame);
                Track<Vector3>& pos = door.layer().tracks.position;
                pos.add(frameTime(spec.inFrame, fps), at(openAlong), Easing::easeInOut());
                pos.add(frameTime(spec.inFrame + cover, fps), at(closedAlong), Easing::easeInOut());
                pos.add(frameTime(out.endFrame, fps), at(openAlong), Easing::easeInOut());
                out.plates.push_back(&door);
            }
            return out;
        }

        // ── DiamondIris: a diamond plate growing over the cut, like IrisCircle

        TransitionComposition addDiamondIris(TemplateScene& scene, const TransitionSpec& spec) {
            const Vector2 canvas = scene.canvas();
            const float fps = scene.fps();
            const float d = std::max(canvas.x, canvas.y);
            const int cover = spec.duration / 2;
            TransitionComposition out = rangeOf(spec, cover);
            ShapeSpec diamond{.size = Vector2(d, d),
                              .fillColor = spec.plateColor,
                              .name = spec.name + "_diamond"};
            diamond.geometry = ShapeGeometry::Polygon;
            diamond.polygonPoints = 4;
            diamond.polygonRotationDegrees = 45.f;
            LayerHandle& plate = scene.shape(diamond);
            plate.position(canvas.x * 0.5f, canvas.y * 0.5f, kPlateZ)
                 .anchor(d * 0.5f, d * 0.5f)
                 .alive(spec.inFrame, out.endFrame);
            const Vector3 shut(1.05f, 1.05f, 1.f);
            const Vector3 open(0.02f, 0.02f, 1.f);
            Track<Vector3>& scale = plate.layer().tracks.scale;
            scale.add(frameTime(spec.inFrame, fps), open, Easing::easeInOut());
            scale.add(frameTime(spec.inFrame + cover, fps), shut, Easing::easeInOut());
            scale.add(frameTime(out.endFrame, fps), open, Easing::easeInOut());
            out.plates.push_back(&plate);
            return out;
        }

        // ── FourWayDoors: four plates converging on the centre at the cover ──

        TransitionComposition addFourWayDoors(TemplateScene& scene, const TransitionSpec& spec) {
            const Vector2 canvas = scene.canvas();
            const float fps = scene.fps();
            const int cover = spec.duration / 2;
            TransitionComposition out = rangeOf(spec, cover);
            const Vector2 hSize(canvas.x * 0.5f + 1.f, canvas.y * 0.5f + 1.f);
            const float cx = canvas.x * 0.5f;
            const float cy = canvas.y * 0.5f;
            for (int i = 0; i < 4; ++i) {
                LayerHandle& door = scene.shape(ShapeSpec{.size = hSize,
                                                           .fillColor = spec.plateColor,
                                                           .name = spec.name + "_four_" + std::to_string(i)});
                const float qx = (i % 2 == 0) ? -1.f : 1.f;
                const float qy = (i < 2) ? -1.f : 1.f;
                const Vector3 closed(cx + qx * hSize.x * 0.5f, cy + qy * hSize.y * 0.5f, kPlateZ);
                const Vector3 open(cx + qx * (hSize.x * 0.5f + canvas.x * 0.5f),
                                   cy + qy * (hSize.y * 0.5f + canvas.y * 0.5f), kPlateZ);
                door.position(open.x, open.y, open.z)
                    .anchor(hSize.x * 0.5f, hSize.y * 0.5f)
                    .alive(spec.inFrame, out.endFrame);
                Track<Vector3>& pos = door.layer().tracks.position;
                pos.add(frameTime(spec.inFrame, fps), open, Easing::easeInOut());
                pos.add(frameTime(spec.inFrame + cover, fps), closed, Easing::easeInOut());
                pos.add(frameTime(out.endFrame, fps), open, Easing::easeInOut());
                out.plates.push_back(&door);
            }
            return out;
        }

        // ── GlitchSlices: bands that flash and shift, deterministically ──────


        TransitionComposition addGlitch(TemplateScene& scene, const TransitionSpec& spec) {
            const Vector2 canvas = scene.canvas();
            const float fps = scene.fps();
            const Vector3 unit = slideAxis(spec.travel);
            const int n = spec.slices;
            const int inFrame = spec.inFrame;
            const int cover = spec.duration / 2;
            const int endFrame = spec.inFrame + spec.duration;
            const int step = std::max(1, cover / n);
            const float bandH = canvas.y / static_cast<float>(n);

            TransitionComposition out = rangeOf(spec, cover);

            for (int i = 0; i < n; ++i) {
                const std::string color = (i % 2 == 0) ? spec.plateColor : spec.inColor;
                LayerHandle& slice = scene.shape(ShapeSpec{
                        .size = Vector2(canvas.x, bandH + 1.f),
                        .fillColor = color,
                        .name = spec.name + "_slice_" + std::to_string(i)});
                const Vector3 base(canvas.x * 0.5f, (static_cast<float>(i) + 0.5f) * bandH, kPlateZ);
                slice.position(base.x, base.y, base.z)
                     .anchor(canvas.x * 0.5f, (bandH + 1.f) * 0.5f)
                     .opacity(0.f)
                     .alive(inFrame, endFrame);

                Track<Vector3>& pos = slice.layer().tracks.position;
                Track<float>& op = slice.layer().tracks.opacity;
                const float shift = canvas.x * 0.06f * (1.f + static_cast<float>(i % 3));

                // Two flashes per slice, mirrored in phase: one on the way in,
                // one on the way out, every key a deterministic function of the
                // slice index. Steps easing holds each flash flat between frames.
                auto flash = [&](int t0, float magnitude) {
                    t0 = std::clamp(t0, inFrame, endFrame - 2);
                    const float s0 = frameTime(t0, fps);
                    const float s1 = frameTime(t0 + 1, fps);
                    const float s2 = frameTime(t0 + 2, fps);
                    pos.add(s0, base, Easing::steps(1));
                    pos.add(s1, base + unit * magnitude, Easing::steps(1));
                    pos.add(s2, base, Easing::linear());
                    op.add(s0, 0.f, Easing::steps(1));
                    op.add(s1, 1.f, Easing::steps(1));
                    op.add(s2, 0.f, Easing::linear());
                };
                flash(inFrame + i * step, shift);
                flash(inFrame + cover + (n - 1 - i) * step, -shift);
                out.plates.push_back(&slice);
            }
            return out;
        }

    }// namespace

    const char* transitionId(TransitionLook look) noexcept {
        switch (look) {
            case TransitionLook::Wipe: return "transition_wipe";
            case TransitionLook::PushThrough: return "transition_push_through";
            case TransitionLook::DipToBlack: return "transition_dip_to_black";
            case TransitionLook::DipToColor: return "transition_dip_to_color";
            case TransitionLook::Blinds: return "transition_blinds";
            case TransitionLook::IrisCircle: return "transition_iris_circle";
            case TransitionLook::GlitchSlices: return "transition_glitch_slices";
            case TransitionLook::LightLeak: return "transition_light_leak";
            case TransitionLook::BarnDoors: return "transition_barn_doors";
            case TransitionLook::CurtainLift: return "transition_curtain_lift";
            case TransitionLook::DiamondIris: return "transition_diamond_iris";
            case TransitionLook::FourWayDoors: return "transition_four_way_doors";
            case TransitionLook::LightLeakFlashSweep: return "lightleak_flash_sweep";
            case TransitionLook::LightLeakCornerBurn: return "lightleak_corner_burn";
            case TransitionLook::LightLeakWhiteout: return "lightleak_whiteout";
            case TransitionLook::LightLeakDiagonalCut: return "lightleak_diagonal_cut";
            case TransitionLook::LightLeakDoublePass: return "lightleak_double_pass";
            case TransitionLook::LightLeakFilmBurn: return "lightleak_film_burn";
            case TransitionLook::LightLeakCenterBurst: return "lightleak_center_burst";
            case TransitionLook::LightLeakHorizontalWhip: return "lightleak_horizontal_whip";
        }
        return "unknown";
    }

    std::vector<TransitionLook> transitionLooks() {
        return {TransitionLook::Wipe, TransitionLook::PushThrough, TransitionLook::DipToBlack,
                TransitionLook::DipToColor, TransitionLook::Blinds, TransitionLook::IrisCircle,
                TransitionLook::GlitchSlices, TransitionLook::LightLeak,
                TransitionLook::BarnDoors, TransitionLook::CurtainLift,
                TransitionLook::DiamondIris, TransitionLook::FourWayDoors,
                TransitionLook::LightLeakFlashSweep, TransitionLook::LightLeakCornerBurn,
                TransitionLook::LightLeakWhiteout, TransitionLook::LightLeakDiagonalCut,
                TransitionLook::LightLeakDoublePass, TransitionLook::LightLeakFilmBurn,
                TransitionLook::LightLeakCenterBurst, TransitionLook::LightLeakHorizontalWhip};
    }

    TransitionDurationBounds transitionDurationBounds(TransitionLook look) noexcept {
        switch (look) {
            case TransitionLook::LightLeakFlashSweep: return {6, 10};
            case TransitionLook::LightLeakCornerBurn: return {8, 12};
            case TransitionLook::LightLeakWhiteout: return {5, 8};
            case TransitionLook::LightLeakDiagonalCut: return {6, 9};
            case TransitionLook::LightLeakDoublePass: return {10, 14};
            case TransitionLook::LightLeakFilmBurn: return {8, 12};
            case TransitionLook::LightLeakCenterBurst: return {5, 8};
            case TransitionLook::LightLeakHorizontalWhip: return {4, 7};
            default: return {2, 0};
        }
    }

    int recommendedTransitionDuration(TransitionLook look) noexcept {
        const auto bounds = transitionDurationBounds(look);
        if (bounds.maximumFrames == 0) return 24;
        return (bounds.minimumFrames + bounds.maximumFrames) / 2;
    }

    bool isRapidTransition(TransitionLook look) noexcept {
        return transitionDurationBounds(look).maximumFrames != 0;
    }

    TransitionTimingClass transitionTimingClass(TransitionLook look) noexcept {
        if (!isRapidTransition(look)) return TransitionTimingClass::Legacy;
        const int frames = recommendedTransitionDuration(look);
        if (frames <= 6) return TransitionTimingClass::Micro;
        if (frames >= 11) return TransitionTimingClass::Hero;
        return TransitionTimingClass::Normal;
    }

    std::vector<TransitionWeight> recommendedTransitionWeights() {
        return {{TransitionLook::LightLeakFlashSweep, 35},
                {TransitionLook::LightLeakHorizontalWhip, 20},
                {TransitionLook::LightLeakFilmBurn, 15},
                {TransitionLook::LightLeakWhiteout, 10},
                {TransitionLook::LightLeakDiagonalCut, 8},
                {TransitionLook::LightLeakDoublePass, 5},
                {TransitionLook::LightLeakCornerBurn, 4},
                {TransitionLook::LightLeakCenterBurst, 3}};
    }

    TransitionComposition addTransition(TemplateScene& scene, const TransitionSpec& spec) {
        if (spec.duration < 2) {
            throw std::invalid_argument("addTransition: the duration must be at least 2 frames");
        }
        const auto durationBounds = transitionDurationBounds(spec.look);
        if (durationBounds.maximumFrames != 0 &&
            (spec.duration < durationBounds.minimumFrames || spec.duration > durationBounds.maximumFrames)) {
            throw std::invalid_argument("addTransition: rapid look duration is outside its declared frame range");
        }
        if (spec.slices < 1 || spec.slices > 16) {
            throw std::invalid_argument("addTransition: the slice count must be in [1, 16]");
        }
        if (!(spec.leakPeakOpacity > 0.f) || spec.leakPeakOpacity > 1.f) {
            throw std::invalid_argument("addTransition: the leak peak opacity must be in (0, 1]");
        }
        if (spec.enableMotionBlur) {
            scene.setTemporalMotionBlur(180.f, 8);
        }

        const Vector2 canvas = scene.canvas();
        switch (spec.look) {
            case TransitionLook::Wipe:
                return addSweep(scene, spec, false);

            case TransitionLook::PushThrough:
                return addSweep(scene, spec, true);

            case TransitionLook::DipToBlack: {
                TransitionComposition out = rangeOf(spec, spec.duration / 2);
                addDip(scene, spec, canvas, "#000000", "dip", out);
                return out;
            }

            case TransitionLook::DipToColor: {
                TransitionComposition out = rangeOf(spec, spec.duration / 2);
                addDip(scene, spec, canvas, spec.plateColor, "dip", out);
                return out;
            }

            case TransitionLook::Blinds:
                return addBlinds(scene, spec);

            case TransitionLook::IrisCircle:
                return addIris(scene, spec);

            case TransitionLook::GlitchSlices:
                return addGlitch(scene, spec);

            case TransitionLook::BarnDoors:
                return addPairedDoors(scene, spec, true);

            case TransitionLook::CurtainLift:
                return addPairedDoors(scene, spec, false);

            case TransitionLook::DiamondIris:
                return addDiamondIris(scene, spec);

            case TransitionLook::FourWayDoors:
                return addFourWayDoors(scene, spec);

            case TransitionLook::LightLeak: {
                TransitionComposition out = rangeOf(spec, spec.duration / 2);
                const int cover = spec.duration / 2;
                LayerHandle& wash = scene.shape(ShapeSpec{.size = canvas,
                                                          .fillColor = spec.leakColor,
                                                          .name = spec.name + "_leak"});
                wash.position(canvas.x * 0.5f, canvas.y * 0.5f, kPlateZ)
                    .opacity(0.f)
                    .alive(spec.inFrame, out.endFrame);
                wash.animateOpacity(spec.inFrame, cover, 0.f, spec.leakPeakOpacity, Easing::easeInOut());
                wash.animateOpacity(spec.inFrame + cover, spec.duration - cover,
                                    spec.leakPeakOpacity, 0.f, Easing::easeInOut());
                out.plates.push_back(&wash);
                return out;
            }
            case TransitionLook::LightLeakFlashSweep:
                return addLightSweep(scene, spec, false, false);
            case TransitionLook::LightLeakCornerBurn:
                return addCornerBurn(scene, spec);
            case TransitionLook::LightLeakWhiteout:
                return addWhiteout(scene, spec);
            case TransitionLook::LightLeakDiagonalCut:
                return addLightSweep(scene, spec, true, false);
            case TransitionLook::LightLeakDoublePass:
                return addDoublePass(scene, spec);
            case TransitionLook::LightLeakFilmBurn:
                return addFilmBurn(scene, spec);
            case TransitionLook::LightLeakCenterBurst:
                return addCenterBurst(scene, spec);
            case TransitionLook::LightLeakHorizontalWhip:
                return addLightSweep(scene, spec, false, true);
        }
        throw std::invalid_argument("addTransition: unknown transition look");
    }

}// namespace chronontemplate
