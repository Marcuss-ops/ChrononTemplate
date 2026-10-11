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

    }// namespace

    const char* transitionId(TransitionLook look) noexcept {
        switch (look) {
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
        return {TransitionLook::LightLeakFlashSweep, TransitionLook::LightLeakCornerBurn,
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
        (void)look;
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

        switch (spec.look) {
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
