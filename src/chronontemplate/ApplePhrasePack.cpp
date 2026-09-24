#include "chronontemplate/ApplePhrasePack.hpp"

#include <algorithm>
#include <stdexcept>
#include <utility>

namespace chronontemplate {
namespace {
    constexpr const char* kShowcasePhrase = "Words appear at the\nright time";
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
                                   std::vector<PhraseTextAnimator> text = {}, int enter = 60) {
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
        case ApplePhraseAnimation::DepthFocus: return "apple_scale_push";
        case ApplePhraseAnimation::ScaleSettle: return "apple_scale_settle";
        case ApplePhraseAnimation::BlurFocus: return "apple_word_pulse";
        case ApplePhraseAnimation::VerticalReveal: return "apple_vertical_glyph_lift";
        case ApplePhraseAnimation::SoftOpacityReveal: return "apple_line_sweep";
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
    constexpr int n = 60;
    const auto layer = [](std::vector<PhraseTrack> tracks) {
        const bool hasOpacity = std::any_of(tracks.begin(), tracks.end(),
            [](const PhraseTrack& item) { return item.property == "opacity"; });
        if (!hasOpacity) tracks.push_back(track("opacity", {{0, 0.f}, {n, 1.f}}));
        return tracks;
    };
    switch (a) {
        case A::FocusRise: return make(name(a), "Apple Focus Rise", kShowcasePhrase,
            layer({track("position_y", {{0, 210.f}, {44, -8.f}, {n, 0.f}}), track("scale", {{0, .86f}, {44, 1.015f}, {n, 1.f}})}));
        case A::SoftScale: return make(name(a), "Apple Soft Scale", kShowcasePhrase,
            layer({track("scale", {{0, .54f}, {45, 1.045f}, {n, 1.f}}), track("position_y", {{0, 38.f}, {n, 0.f}})}));
        case A::WordCascade: return make(name(a), "Apple Word Cascade", kShowcasePhrase,
            layer({}), {animator("word", "forward", {track("position_y", {{0, 155.f}, {n, 0.f}}), track("opacity", {{0, 0.f}, {n, 1.f}})}, "reveal")});
        case A::LineCascade: return make(name(a), "Apple Line Cascade", kShowcasePhrase,
            layer({}),
            {animator("line", "forward", {track("position_y", {{0, 18.f}, {n, 0.f}}),
                                             track("position_x", {{0, 110.f}, {n, 0.f}}),
                                             track("opacity", {{0, 0.f}, {n, 1.f}})}, "reveal_soft")});
        case A::PrecisionType: return make(name(a), "Apple Precision Type", kShowcasePhrase,
            layer({}), {animator("glyph", "forward", {track("opacity", {{0, 0.f}, {n, 1.f}})}, "reveal")});
        case A::TrackingReveal: return make(name(a), "Apple Tracking Reveal", kShowcasePhrase,
            layer({}), {animator("glyph", "forward", {track("tracking", {{0, 28.f}, {n, 0.f}}), track("opacity", {{0, 0.f}, {n, 1.f}})}, "reveal")});
        case A::ExpandFromCenter: return make(name(a), "Apple Expand From Center", kShowcasePhrase,
            layer({}), {animator("glyph", "from_center", {track("scale", {{0, .12f}, {n, 1.f}}), track("position_y", {{0, 42.f}, {n, 0.f}}), track("opacity", {{0, 0.f}, {n, 1.f}})}, "reveal")});
        case A::CompressIn: return make(name(a), "Apple Compress In", kShowcasePhrase,
            layer({track("scale_x", {{0, .56f}, {n, 1.f}}), track("position_x", {{0, -145.f}, {n, 0.f}})}));
        case A::DepthFocus: return make(name(a), "Apple Scale Push", kShowcasePhrase,
            layer({track("scale", {{0, .28f}, {n, 1.f}}), track("position_y", {{0, -100.f}, {n, 0.f}})}));
        case A::ScaleSettle: return make(name(a), "Apple Scale Settle", kShowcasePhrase,
            layer({track("scale", {{0, .68f}, {44, 1.08f}, {n, 1.f}}), track("rotation_z", {{0, -.12f}, {44, .015f}, {n, 0.f}})}));
        case A::BlurFocus: return make(name(a), "Apple Word Pulse", kShowcasePhrase,
            layer({}), {animator("word", "forward", {track("scale", {{0, .72f}, {24, 1.14f}, {n, 1.f}})}, "band")});
        case A::VerticalReveal: return make(name(a), "Apple Vertical Reveal", kShowcasePhrase,
            layer({}), {animator("glyph", "reverse", {track("position_y", {{0, 145.f}, {n, 0.f}}), track("opacity", {{0, 0.f}, {n, 1.f}})}, "reveal")});
        case A::SoftOpacityReveal: return make(name(a), "Apple Line Sweep", kShowcasePhrase,
            layer({}), {animator("line", "reverse", {track("position_x", {{0, 190.f}, {n, 0.f}}), track("opacity", {{0, 0.f}, {n, 1.f}})}, "reveal")});
        case A::HeroStatement: return make(name(a), "Apple Hero Statement", kShowcasePhrase,
            layer({track("scale", {{0, .68f}, {48, 1.055f}, {n, 1.f}})}));
        case A::CinematicExit: return make(name(a), "Apple Cinematic Exit", kShowcasePhrase,
            layer({track("position_x", {{0, 440.f}, {42, -14.f}, {n, 0.f}}), track("rotation_z", {{0, -.12f}, {42, .02f}, {n, 0.f}}), track("scale", {{0, .9f}, {n, 1.f}})}));
    }
    throw std::invalid_argument("chronontemplate::definition: unknown Apple phrase animation");
}
}// namespace chronontemplate
