#include "chronontemplate/templates/YouTubeSubscribe.hpp"

#include <cmath>
#include <limits>
#include <stdexcept>

namespace chronontemplate::templates {

    namespace {

        // The phases every spec must have room for: the entrance, the click, the
        // exit. Shortening one silently would leave keys outside the lifetime.
        constexpr int kMinimumDuration = 48;
        constexpr int kEntranceFrames = 18;
        constexpr int kExitFrames = 12;
        constexpr int kClickFrames = 10;

        // How far the card overshoots as it settles: 0.7 -> 1 with the motion
        // core's overshoot easing peaks around 1.08.
        constexpr float kEntranceFrom = 0.7f;
        constexpr float kClickFrom = 1.12f;

        constexpr float kRowOffset = 300.f;
        constexpr float kAvatarOffset = -360.f;
        constexpr float kBellOffset = 520.f;
        constexpr float kTextOffset = -190.f;
        constexpr float kTextSpread = 28.f;

    }// namespace

    int YouTubeSubscribeSpec::resolvedClickFrame() const {

        return clickFrame >= 0 ? clickFrame : startFrame + duration / 2;
    }

    void YouTubeSubscribeSpec::validate() const {

        if (!std::isfinite(fps) || fps <= 0.f) {
            throw std::invalid_argument("YouTubeSubscribeSpec: fps must be positive and finite");
        }
        if (startFrame < 0 || duration < kMinimumDuration ||
            startFrame > std::numeric_limits<int>::max() - duration) {
            throw std::invalid_argument("YouTubeSubscribeSpec: duration must be at least 48 frames");
        }
        if (avatarPath.empty() || buttonPath.empty() || bellPath.empty()) {
            throw std::invalid_argument("YouTubeSubscribeSpec: avatar, button and bell assets are required");
        }
        ui::AvatarCircle avatar = avatarStyle;
        avatar.assetPath = avatarPath;
        avatar.validate();
        ui::Button button = buttonStyle;
        button.assetPath = buttonPath;
        button.label = subscribeLabel;
        button.validate();
        if (channelName.empty() || subscriberCount.empty() || subscribeLabel.empty()) {
            throw std::invalid_argument("YouTubeSubscribeSpec: channel name, subscriber count and label are required");
        }

        const int click = resolvedClickFrame();
        if (click < startFrame || click > endFrame() - kExitFrames - kClickFrames) {
            throw std::invalid_argument(
                    "YouTubeSubscribeSpec: clickFrame must leave room for the click pulse and the exit");
        }
    }

    YouTubeSubscribePack buildYouTubeSubscribe(TemplateScene& scene, const YouTubeSubscribeSpec& spec) {

        spec.validate();

        // Two time bases in one template is a defect, not a preference: every
        // timing below is authored through the scene's fps.
        if (spec.fps != scene.fps()) {
            throw std::invalid_argument(
                    "buildYouTubeSubscribe: the spec fps must match the scene's time base");
        }

        const int start = spec.startFrame;
        const int end = spec.endFrame();
        const int click = spec.resolvedClickFrame();
        const chrononmotion::Vector2 canvas = scene.canvas();
        const float centreX = canvas.x * 0.5f;
        const float centreY = canvas.y * 0.5f;

        YouTubeSubscribePack pack;
        pack.startFrame = start;
        pack.endFrame = end;
        pack.clickFrame = click;

        // The controller: the card enters as one object and leaves as one object.
        // Its children inherit both through `worldOpacity` and the hierarchy.
        LayerHandle& controller = scene.group("Null_Subscribe");
        controller.alive(start, end)
                .animate(FadeIn{.inFrame = start, .duration = 10})
                .animate(ScalePop{.inFrame = start, .duration = kEntranceFrames, .from = kEntranceFrom, .to = 1.f})
                .animate(FadeOut{.startFrame = end - kExitFrames, .duration = kExitFrames});

        LayerHandle& avatar = scene.image(ImageSpec{.path = spec.avatarPath, .name = "Avatar"});
        avatar.parent(controller.id())
                .position(centreX + kAvatarOffset, centreY, 0.f)
                .alive(start, end)
                .animate(FadeIn{.inFrame = start + 4, .duration = 8})
                .animate(SpinXYZ{.inFrame = start + 4, .duration = 12, .turns = 0.25f});

        LayerHandle& channelName = scene.text(
                TextSpec{.text = spec.channelName, .font = "Inter-Bold.ttf", .fontSize = 48.f, .name = "ChannelName"});
        channelName.parent(controller.id())
                .position(centreX + kTextOffset, centreY + kTextSpread, 0.f)
                .alive(start, end)
                .animate(SlideIn{.direction = chrononmotion::motion::presets::Direction::Up,
                                 .inFrame = start + 6, .duration = 12, .distance = 40.f})
                .animate(FadeIn{.inFrame = start + 6, .duration = 10});

        LayerHandle& subscriberCount = scene.text(
                TextSpec{.text = spec.subscriberCount, .font = "Inter-Regular.ttf", .fontSize = 36.f,
                         .color = "#B0B0B0", .name = "SubscriberCount"});
        subscriberCount.parent(controller.id())
                .position(centreX + kTextOffset, centreY - kTextSpread, 0.f)
                .alive(start, end)
                .animate(SlideIn{.direction = chrononmotion::motion::presets::Direction::Up,
                                 .inFrame = start + 9, .duration = 12, .distance = 40.f})
                .animate(FadeIn{.inFrame = start + 9, .duration = 10});

        LayerHandle& button = scene.image(ImageSpec{.path = spec.buttonPath, .name = "SubscribeButton"});
        button.parent(controller.id())
                .position(centreX + kRowOffset, centreY, 0.f)
                .alive(start, end)
                .animate(SlideIn{.direction = chrononmotion::motion::presets::Direction::Right,
                                 .inFrame = start + 20, .duration = 12, .distance = 60.f});

        // The click pulse. A preset appends keys, so a second `ScalePop` alone
        // would ramp from the entrance's last key up to the punch; the hold writes
        // a key just before the click so the segment between them stays flat.
        button.animate(ScalePop{.inFrame = click - 1, .duration = 1, .from = 1.f, .to = 1.f})
                .animate(ScalePop{.inFrame = click, .duration = kClickFrames, .from = kClickFrom, .to = 1.f});

        LayerHandle& label = scene.text(
                TextSpec{.text = spec.subscribeLabel, .font = "Inter-Bold.ttf", .fontSize = 36.f,
                         .name = "SubscribeLabel"});
        label.parent(button.id())
                .position(0.f, 0.f, 0.f)
                .alive(start, end)
                .animate(FadeIn{.inFrame = start + 22, .duration = 8});

        LayerHandle& bell = scene.image(ImageSpec{.path = spec.bellPath, .name = "Bell"});
        bell.parent(controller.id())
                .position(centreX + kBellOffset, centreY, 0.f)
                .alive(start, end)
                .animate(ScalePop{.inFrame = start + 28, .duration = 12, .from = 0.5f, .to = 1.f})
                .animate(FadeIn{.inFrame = start + 28, .duration = 8});

        pack.controller = &controller;
        pack.avatar = &avatar;
        pack.channelName = &channelName;
        pack.subscriberCount = &subscriberCount;
        pack.button = &button;
        pack.label = &label;
        pack.bell = &bell;
        return pack;
    }

}// namespace chronontemplate::templates
