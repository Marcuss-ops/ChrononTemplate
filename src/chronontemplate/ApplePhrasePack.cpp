#include "chronontemplate/ApplePhrasePack.hpp"

#include <algorithm>
#include <stdexcept>
#include <utility>

namespace chronontemplate {
namespace {
    PhraseTrack track(const std::string& property, std::vector<PhraseKeyframe> keys,
                      const std::string& easing = "out_cubic") {
        return {property, easing, std::move(keys)};
    }
    PhraseTextAnimator animator(const std::string& unit, const std::string& order,
                                std::vector<PhraseTrack> properties,
                                const std::string& window = "full") {
        return {{unit, order, window}, std::move(properties)};
    }
    PhraseAnimationDefinition make(const char* id, const char* title, const char* phrase,
                                   std::vector<PhraseTrack> layer,
                                   std::vector<PhraseTextAnimator> text = {}, int enter = 48) {
        return {id, title, phrase, enter, std::move(layer), std::move(text), {}};
    }
}

ClassicPhraseStyle applePhraseStyle() {
    ClassicPhraseStyle style;
    style.font = "assets/fonts/Inter-SemiBold.ttf";
    style.font_size = 84.f;
    style.box = {1640.f, 260.f};
    style.fill = "#F8F8F8";
    // A fine dark outline and restrained white halo retain a crisp silhouette
    // while giving the phrase a subtle lift from black.
    style.stroke_width = 1.5f;
    style.glow_radius = 3.f;
    style.glow_intensity = 0.045f;
    return style;
}

PhraseAnimationDefinition appleClassicStill() {
    return {"apple_classic_still", "Apple Classic Still", "watching", 1,
            {track("opacity", {{0, 1.f}, {1, 1.f}}),
             track("scale", {{0, 1.f}, {1, 1.f}})}, {}, {}};
}

const char* name(ApplePhraseAnimation a) {
    switch (a) {
        case ApplePhraseAnimation::FocusRise: return "apple_focus_rise";
        case ApplePhraseAnimation::SoftScale: return "apple_soft_scale";
        case ApplePhraseAnimation::WordCascade: return "apple_word_cascade";
        case ApplePhraseAnimation::LineCascade: return "apple_line_cascade";
        case ApplePhraseAnimation::PrecisionType: return "apple_precision_type";
        case ApplePhraseAnimation::TrackingReveal: return "apple_tracking_reveal";
        case ApplePhraseAnimation::ExpandFromCenter: return "apple_expand_from_center";
        case ApplePhraseAnimation::CompressIn: return "apple_compress_in";
        case ApplePhraseAnimation::DepthFocus: return "apple_scale_blur_focus";
        case ApplePhraseAnimation::ScaleSettle: return "apple_scale_settle";
        case ApplePhraseAnimation::BlurFocus: return "apple_blur_focus";
        case ApplePhraseAnimation::VerticalReveal: return "apple_vertical_reveal";
        case ApplePhraseAnimation::SoftOpacityReveal: return "apple_soft_opacity_reveal";
        case ApplePhraseAnimation::HeroStatement: return "apple_hero_statement";
        case ApplePhraseAnimation::CinematicExit: return "apple_cinematic_exit";
    }
    throw std::invalid_argument("chronontemplate::name: unknown Apple phrase animation");
}

std::vector<ApplePhraseAnimation> applePhraseAnimations() {
    return {ApplePhraseAnimation::FocusRise, ApplePhraseAnimation::SoftScale,
            ApplePhraseAnimation::WordCascade, ApplePhraseAnimation::LineCascade,
            ApplePhraseAnimation::PrecisionType, ApplePhraseAnimation::TrackingReveal,
            ApplePhraseAnimation::ExpandFromCenter, ApplePhraseAnimation::CompressIn,
            ApplePhraseAnimation::DepthFocus, ApplePhraseAnimation::ScaleSettle,
            ApplePhraseAnimation::BlurFocus, ApplePhraseAnimation::VerticalReveal,
            ApplePhraseAnimation::SoftOpacityReveal, ApplePhraseAnimation::HeroStatement,
            ApplePhraseAnimation::CinematicExit};
}

PhraseAnimationDefinition definition(ApplePhraseAnimation a) {
    using A = ApplePhraseAnimation;
    constexpr int n = 48;
    const auto layer = [](std::vector<PhraseTrack> tracks) {
        const bool hasOpacity = std::any_of(tracks.begin(), tracks.end(),
            [](const PhraseTrack& item) { return item.property == "opacity"; });
        if (!hasOpacity) tracks.push_back(track("opacity", {{0, 0.f}, {8, 1.f}, {48, 1.f}}));
        return tracks;
    };
    switch (a) {
        case A::FocusRise: return make(name(a), "Apple Focus Rise", "FOCUS ON WHAT MATTERS",
            layer({track("position_y", {{0, 28.f}, {n, 0.f}}), track("scale", {{0, .98f}, {n, 1.f}})}),
            {animator("glyph", "forward", {track("blur", {{0, 14.f}, {n, 0.f}})})});
        case A::SoftScale: return make(name(a), "Apple Soft Scale", "A BEAUTIFUL IDEA",
            layer({track("scale", {{0, .92f}, {n, 1.f}})}),
            {animator("glyph", "forward", {track("blur", {{0, 10.f}, {n, 0.f}})})});
        case A::WordCascade: return make(name(a), "Apple Word Cascade", "WORDS IN PERFECT FLOW",
            layer({}), {animator("word", "forward", {track("position_y", {{0, 16.f}, {n, 0.f}}), track("opacity", {{0, 0.f}, {n, 1.f}})}, "reveal_soft")});
        case A::LineCascade: return make(name(a), "Apple Line Cascade", "DESIGNED TO FEEL\nEFFORTLESS",
            layer({}),
            {animator("line", "forward", {track("position_y", {{0, 18.f}, {n, 0.f}}),
                                             track("blur", {{0, 8.f}, {n, 0.f}}),
                                             track("opacity", {{0, 0.f}, {n, 1.f}})}, "reveal_soft")});
        case A::PrecisionType: return make(name(a), "Apple Precision Type", "LESS, BUT BETTER",
            layer({}), {animator("glyph", "forward", {track("blur", {{0, 4.f}, {n, 0.f}}), track("opacity", {{0, 0.f}, {n, 1.f}})}, "reveal_soft")});
        case A::TrackingReveal: return make(name(a), "Apple Tracking Reveal", "THINK DIFFERENT",
            layer({}), {animator("glyph", "forward", {track("tracking", {{0, 35.f}, {n, 0.f}}), track("blur", {{0, 5.f}, {n, 0.f}}), track("opacity", {{0, 0.f}, {n, 1.f}})})});
        case A::ExpandFromCenter: return make(name(a), "Apple Expand From Center", "A NEW PERSPECTIVE",
            layer({}), {animator("glyph", "from_center", {track("scale", {{0, .94f}, {n, 1.f}}), track("opacity", {{0, 0.f}, {n, 1.f}})})});
        case A::CompressIn: return make(name(a), "Apple Compress In", "PRECISION IN EVERY DETAIL",
            layer({}), {animator("glyph", "forward", {track("tracking", {{0, 20.f}, {n, 0.f}}), track("scale", {{0, 1.04f}, {n, 1.f}}), track("blur", {{0, 8.f}, {n, 0.f}})})});
        case A::DepthFocus: return make(name(a), "Apple Scale Blur Focus", "CLOSER TO THE FUTURE",
            layer({track("scale", {{0, .94f}, {n, 1.f}})}),
            {animator("glyph", "forward", {track("blur", {{0, 8.f}, {n, 0.f}})})});
        case A::ScaleSettle: return make(name(a), "Apple Scale Settle", "A MORE NATURAL WAY",
            layer({track("scale", {{0, .97f}, {n, 1.f}})}));
        case A::BlurFocus: return make(name(a), "Apple Blur Focus", "FAST. POWERFUL. EFFORTLESS.",
            layer({track("scale", {{0, 1.03f}, {n, 1.f}})}),
            {animator("glyph", "forward", {track("blur", {{0, 18.f}, {n, 0.f}})})});
        case A::VerticalReveal: return make(name(a), "Apple Vertical Reveal", "MADE TO MOVE YOU",
            layer({track("position_y", {{0, 35.f}, {n, 0.f}})}));
        case A::SoftOpacityReveal: return make(name(a), "Apple Soft Opacity Reveal", "LIGHT, SHAPED BY DESIGN",
            layer({track("opacity", {{0, .82f}, {n, 1.f}})}));
        case A::HeroStatement: return make(name(a), "Apple Hero Statement", "THE FUTURE IS HERE",
            layer({track("scale", {{0, .86f}, {n - 6, 1.015f}, {n, 1.f}})}),
            {animator("glyph", "forward", {track("blur", {{0, 10.f}, {n, 0.f}})})});
        case A::CinematicExit: return make(name(a), "Apple Cinematic Exit", "BEYOND THE EXPECTED",
            layer({track("position_y", {{0, 16.f}, {n, 0.f}}), track("scale", {{0, 1.015f}, {n, 1.f}})}),
            {animator("glyph", "forward", {track("blur", {{0, 12.f}, {n, 0.f}})})});
    }
    throw std::invalid_argument("chronontemplate::definition: unknown Apple phrase animation");
}
}// namespace chronontemplate
