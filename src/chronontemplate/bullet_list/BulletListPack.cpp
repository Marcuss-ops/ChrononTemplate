#include "chronontemplate/bullet_list/BulletListPack.hpp"

#include "chrononmotion/math/Vector3.hpp"
#include "chrononmotion/motion/Easing.hpp"

#include <algorithm>
#include <cmath>
#include <stdexcept>
#include <string>

namespace chronontemplate {

    using chrononmotion::Vector3;
    using chrononmotion::motion::Easing;

    namespace {

        constexpr float kSlideDistance = 160.f;   ///< world units
        constexpr float kRiseDistance = 70.f;
        constexpr float kDropDistance = 90.f;
        constexpr float kDepthStart = -500.f;     ///< z units, toward the lens
        constexpr float kTiltStart = 1.1f;        ///< radians
        constexpr float kYawStart = 1.4f;         ///< radians
        constexpr float kScaleStart = 0.6f;
        constexpr float kHoldAfterCamera = 90.f;  ///< frames of hold after the last reveal

        // A small integer hash: a deterministic stand-in for a PRNG that does not
        // depend on the platform's distribution implementations.
        std::uint32_t mix(std::uint32_t x) {
            x ^= x >> 16;
            x *= 0x7feb352dU;
            x ^= x >> 15;
            x *= 0x846ca68bU;
            x ^= x >> 16;
            return x;
        }

        std::uint32_t drawIndex(std::uint32_t seed, std::uint32_t salt, std::size_t count) {
            const std::uint32_t h = mix(seed ^ mix(salt * 0x9E3779B9U + 1U));
            return h % static_cast<std::uint32_t>(count);
        }

        // Each key holds the hidden value until `t0`, then eases to `to` by `t1`.
        // Holding before the reveal keeps an un-revealed bullet at its pose.
        // A key at frame 0 keeps the start pose; the hold key is added only when
        // the reveal starts later, so keys never repeat a time.
        template <typename T>
        void ramp(chrononmotion::motion::Track<T>& track, float t0, float t1,
                  const T& from, const T& to, const Easing& easing) {
            track.add(0.f, from, Easing::linear());
            if (t0 > 0.f) {
                track.add(t0, from, Easing::linear());
            }
            track.add(t1, to, easing);
        }

        void fadeIn(LayerHandle& handle, float t0, float t1) {
            auto& tracks = handle.layer().tracks;
            tracks.opacity.add(0.f, 0.f, Easing::linear());
            if (t0 > 0.f) {
                tracks.opacity.add(t0, 0.f, Easing::linear());
            }
            tracks.opacity.add(t1, 1.f, Easing::easeOut());
        }

        void applyReveal(LayerHandle& handle, BulletReveal reveal, const Vector3& rest,
                         float t0, float t1) {
            auto& tracks = handle.layer().tracks;
            switch (reveal) {
                case BulletReveal::SlideLeft:
                    ramp(tracks.position, t0, t1, rest + Vector3(-kSlideDistance, 0.f, 0.f), rest,
                         Easing::easeOut());
                    break;
                case BulletReveal::SlideRight:
                    ramp(tracks.position, t0, t1, rest + Vector3(kSlideDistance, 0.f, 0.f), rest,
                         Easing::easeOut());
                    break;
                case BulletReveal::RiseFade:
                    ramp(tracks.position, t0, t1, rest + Vector3(0.f, kRiseDistance, 0.f), rest,
                         Easing::easeOut());
                    break;
                case BulletReveal::DropFade:
                    ramp(tracks.position, t0, t1, rest + Vector3(0.f, -kDropDistance, 0.f), rest,
                         Easing::bounceOut());
                    break;
                case BulletReveal::ScalePop:
                    ramp(tracks.scale, t0, t1, Vector3(kScaleStart, kScaleStart, 1.f),
                         Vector3(1.f, 1.f, 1.f), Easing::overshoot());
                    break;
                case BulletReveal::TiltIn:
                    ramp(tracks.rotation, t0, t1, Vector3(kTiltStart, 0.f, 0.f), Vector3(0.f, 0.f, 0.f),
                         Easing::easeOut());
                    break;
                case BulletReveal::DepthIn:
                    ramp(tracks.position, t0, t1, rest + Vector3(0.f, 0.f, kDepthStart), rest,
                         Easing::easeOut());
                    break;
                case BulletReveal::YawFlipIn:
                    ramp(tracks.rotation, t0, t1, Vector3(0.f, kYawStart, 0.f), Vector3(0.f, 0.f, 0.f),
                         Easing::easeOut());
                    break;
            }
            fadeIn(handle, t0, t1);
        }

        void validateSpec(const BulletListSpec& spec) {
            if (spec.items.empty()) {
                throw std::invalid_argument("addBulletList: at least one item is required");
            }
            if (spec.revealDuration <= 0) {
                throw std::invalid_argument("addBulletList: revealDuration must be positive");
            }
            if (spec.staggerFrames < 0 || spec.startFrame < 0) {
                throw std::invalid_argument("addBulletList: stagger and start frame must not be negative");
            }
            if (!std::isfinite(spec.centerX) || !std::isfinite(spec.centerY) ||
                !std::isfinite(spec.lineSpacing) || spec.fontSize <= 0.f) {
                throw std::invalid_argument("addBulletList: the centre, spacing and size must be finite");
            }
        }

    }// namespace

    const char* bulletRevealId(BulletReveal reveal) noexcept {
        switch (reveal) {
            case BulletReveal::SlideLeft: return "bullet_slide_left";
            case BulletReveal::SlideRight: return "bullet_slide_right";
            case BulletReveal::RiseFade: return "bullet_rise_fade";
            case BulletReveal::DropFade: return "bullet_drop_bounce";
            case BulletReveal::ScalePop: return "bullet_scale_pop";
            case BulletReveal::TiltIn: return "bullet_tilt_in";
            case BulletReveal::DepthIn: return "bullet_depth_in";
            case BulletReveal::YawFlipIn: return "bullet_yaw_flip";
        }
        return "bullet_unknown";
    }

    const std::vector<BulletReveal>& bulletRevealChoices() {
        static const std::vector<BulletReveal> choices{
                BulletReveal::SlideLeft, BulletReveal::SlideRight, BulletReveal::RiseFade,
                BulletReveal::DropFade, BulletReveal::ScalePop, BulletReveal::TiltIn,
                BulletReveal::DepthIn, BulletReveal::YawFlipIn};
        return choices;
    }

    std::vector<std::string> bulletRevealIds() {
        std::vector<std::string> ids;
        for (BulletReveal reveal : bulletRevealChoices()) {
            ids.emplace_back(bulletRevealId(reveal));
        }
        return ids;
    }

    const std::vector<TitleCameraMove>& bulletCameraChoices() {
        // Every title-camera move except the two that are too loud for reading
        // text: the whip acquisition and the crash push.
        static const std::vector<TitleCameraMove> choices{
                TitleCameraMove::SlowPush, TitleCameraMove::SlowPullOut,
                TitleCameraMove::LeftDrift, TitleCameraMove::RightDrift,
                TitleCameraMove::VerticalRise, TitleCameraMove::VerticalDescend,
                TitleCameraMove::MicroOrbitLeft, TitleCameraMove::MicroOrbitRight,
                TitleCameraMove::ArcPush, TitleCameraMove::ArcPull,
                TitleCameraMove::LowAnglePush, TitleCameraMove::HighAngleSettle,
                TitleCameraMove::RollSettle, TitleCameraMove::RollPass,
                TitleCameraMove::DollyZoomSubtle, TitleCameraMove::FocusPush,
                TitleCameraMove::ParallaxSide, TitleCameraMove::ParallaxPush,
                TitleCameraMove::CornerReveal, TitleCameraMove::TopDownSettle,
                TitleCameraMove::HandheldMicro, TitleCameraMove::OrbitWide,
                TitleCameraMove::FloorRise};
        return choices;
    }

    BulletReveal pickBulletReveal(std::uint32_t seed, std::size_t index) {
        const auto& choices = bulletRevealChoices();
        return choices[drawIndex(seed, static_cast<std::uint32_t>(index) + 1U, choices.size())];
    }

    TitleCameraMove pickBulletCameraMove(std::uint32_t seed) {
        const auto& choices = bulletCameraChoices();
        return choices[drawIndex(seed, 0xC0FFEEU, choices.size())];
    }

    BulletListComposition addBulletList(TemplateScene& scene, const BulletListSpec& spec) {
        validateSpec(spec);

        const float fps = scene.fps();
        const std::size_t count = spec.items.size();
        const float centreOffset = static_cast<float>(count - 1) * 0.5f;

        BulletListComposition out;
        out.bullets.reserve(count);

        float longest = 0.f;
        int lastRevealEnd = spec.startFrame;

        for (std::size_t i = 0; i < count; ++i) {
            const float y = spec.centerY + (static_cast<float>(i) - centreOffset) * spec.lineSpacing;
            const std::string text = spec.marker + "  " + spec.items[i];
            longest = std::max(longest, static_cast<float>(text.size()));

            LayerHandle& bullet = scene.text(TextSpec{
                    .text = text,
                    .font = spec.font,
                    .fontSize = spec.fontSize,
                    .color = spec.color,
                    .name = "bullet_" + std::to_string(i)});
            bullet.position(spec.centerX, y, 0.f);

            const BulletReveal reveal = spec.reveal.value_or(pickBulletReveal(spec.seed, i));
            const int inFrame = spec.startFrame + static_cast<int>(i) * spec.staggerFrames;
            const int outFrame = inFrame + spec.revealDuration;
            lastRevealEnd = std::max(lastRevealEnd, outFrame);

            applyReveal(bullet, reveal, Vector3(spec.centerX, y, 0.f),
                        static_cast<float>(inFrame) / fps, static_cast<float>(outFrame) / fps);

            if (spec.outFrame >= 0) {
                bullet.animate(FadeOut{.startFrame = spec.outFrame, .duration = spec.fadeOutDuration});
            }
            out.bullets.push_back(BulletPick{.layerId = bullet.id(), .reveal = reveal});
        }

        // One camera move frames the whole board. The anchor is the list centre,
        // and the bound is the widest line by the full stack height.
        out.camera = spec.camera.value_or(pickBulletCameraMove(spec.seed));

        TitleCameraShot shot{};
        shot.anchor.center = Vector3(spec.centerX, spec.centerY, 0.f);
        shot.anchor.halfWidth = longest * spec.fontSize * 0.3f;
        shot.anchor.halfHeight = centreOffset * spec.lineSpacing + spec.fontSize * 0.5f;
        shot.framing = spec.framing;
        shot.intensity = spec.intensity;
        shot.inFrame = spec.startFrame;
        shot.duration = spec.outFrame > spec.startFrame
                                ? spec.outFrame - spec.startFrame
                                : (lastRevealEnd - spec.startFrame) + static_cast<int>(kHoldAfterCamera);
        applyTitleCameraShot(scene, out.camera, shot);

        return out;
    }

}// namespace chronontemplate
