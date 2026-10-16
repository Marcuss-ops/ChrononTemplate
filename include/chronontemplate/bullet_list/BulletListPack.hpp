// ChrononTemplate — the bullet-list documentary pack.
//
// A vertical list of points where every bullet enters with its own reveal
// (slide, rise, drop, scale pop, tilt, depth, yaw flip) and the whole board is
// framed by one camera move drawn from the title-camera vocabulary. Both
// choices are deterministic: the same seed always yields the same reveals and
// the same camera, so a render is reproducible and a preview is trustworthy.
//
// Boundary: the pack owns composition and timing only. Text shaping is the
// ContentHost's job, the camera is lowered by `applyTitleCameraShot`, and every
// key lands on ChrononMotion's tracks through the regular LayerHandle API.

#ifndef CHRONONTEMPLATE_BULLET_LIST_PACK_HPP
#define CHRONONTEMPLATE_BULLET_LIST_PACK_HPP

#include "chronontemplate/camera_roll/TitleCameraPack.hpp"
#include "chronontemplate/core/TemplateScene.hpp"

#include <cstddef>
#include <cstdint>
#include <optional>
#include <string>
#include <vector>

namespace chronontemplate {

    /// How one bullet enters. Stable ids, append-only.
    enum class BulletReveal : std::uint8_t {
        SlideLeft,   ///< bullet_slide_left: travels in from the left
        SlideRight,  ///< bullet_slide_right: travels in from the right
        RiseFade,    ///< bullet_rise_fade: rises a short way while fading in
        DropFade,    ///< bullet_drop_bounce: drops from above with a bounce
        ScalePop,    ///< bullet_scale_pop: grows from 60% with overshoot
        TiltIn,      ///< bullet_tilt_in: swings up from a pitched plane
        DepthIn,     ///< bullet_depth_in: comes toward the lens from depth
        YawFlipIn    ///< bullet_yaw_flip: turns in on the vertical axis
    };

    /// Stable snake-case id of a reveal.
    [[nodiscard]] const char* bulletRevealId(BulletReveal reveal) noexcept;

    /// Every reveal id in canonical order, for catalogs and contract tests.
    [[nodiscard]] std::vector<std::string> bulletRevealIds();

    /// Every reveal, in canonical order.
    [[nodiscard]] const std::vector<BulletReveal>& bulletRevealChoices();

    /// Camera moves the bullet board may draw from. A list is read, not
    /// watched, so loud moves (whip settle, crash push) are not offered.
    [[nodiscard]] const std::vector<TitleCameraMove>& bulletCameraChoices();

    /// Deterministic pick: a function of (seed, index) only.
    [[nodiscard]] BulletReveal pickBulletReveal(std::uint32_t seed, std::size_t index);
    [[nodiscard]] TitleCameraMove pickBulletCameraMove(std::uint32_t seed);

    struct BulletListSpec {
        std::vector<std::string> items{};
        std::string font{};                 ///< empty = the host's default face
        float fontSize{56.f};
        std::string color{"#FFFFFF"};
        std::string marker{"\xE2\x80\xA2"}; ///< bullet glyph (UTF-8 U+2022)
        float centerX{960.f};
        float centerY{540.f};
        float lineSpacing{110.f};
        int startFrame{0};
        int staggerFrames{12};              ///< frames between consecutive bullets
        int revealDuration{24};             ///< frames each bullet takes to enter
        int outFrame{-1};                   ///< when the list fades out; -1 = stays
        int fadeOutDuration{12};
        std::uint32_t seed{0};
        /// Forces one reveal for every bullet. Unset = each bullet draws its own.
        std::optional<BulletReveal> reveal{};
        /// Unset = the camera move is drawn from `seed`.
        std::optional<TitleCameraMove> camera{};
        TitleFraming framing{TitleFraming::Medium};
        TitleCameraIntensity intensity{TitleCameraIntensity::Editorial};
    };

    struct BulletPick {
        MotionLayerId layerId{0};
        BulletReveal reveal{BulletReveal::RiseFade};
    };

    struct BulletListComposition {
        std::vector<BulletPick> bullets{};
        TitleCameraMove camera{TitleCameraMove::SlowPush};
    };

    /// Author the list: one text layer per item, each with its own reveal, and
    /// one camera move over the whole board. Throws `std::invalid_argument` on
    /// an empty list, a non-positive reveal duration or a non-finite centre.
    [[nodiscard]] BulletListComposition addBulletList(TemplateScene& scene, const BulletListSpec& spec);

}// namespace chronontemplate

#endif//CHRONONTEMPLATE_BULLET_LIST_PACK_HPP
