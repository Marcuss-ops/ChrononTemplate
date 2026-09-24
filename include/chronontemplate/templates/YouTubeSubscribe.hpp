// ChrononTemplate — the YouTube subscribe card, built on `TemplateScene`.
//
// Avatar, channel name, subscriber count, button with its label, and the bell.
// Text and image are the same layer type here: the only difference is the
// `ContentRef` Chronon measured. The pack owns composition and timing; Chronon
// owns the bytes, the fonts and the rasterization.

#ifndef CHRONONTEMPLATE_TEMPLATES_YOUTUBESUBSCRIBE_HPP
#define CHRONONTEMPLATE_TEMPLATES_YOUTUBESUBSCRIBE_HPP

#include "chronontemplate/TemplateScene.hpp"
#include "chronontemplate/UiPrimitives.hpp"

#include <string>

namespace chronontemplate::templates {

    struct YouTubeSubscribeSpec {
        std::string avatarPath{"avatar.png"};
        std::string channelName{"Wrestling Discovery"};
        std::string subscriberCount{"1.2M subscribers"};
        std::string subscribeLabel{"SUBSCRIBE"};
        std::string buttonPath{"subscribe_button.png"};
        std::string bellPath{"bell.png"};
        ui::AvatarCircle avatarStyle{.diameter = 96.f};
        ui::Button buttonStyle{.shape = {.width = 260.f, .height = 76.f, .radius = 18.f},
                                .shadow = {.blur = 18.f, .offsetY = 6.f, .opacity = 0.28f}};
        float fps{30.f};
        int startFrame{0};
        int duration{90};
        /// Frame the click lands on. -1 means the middle of the composition.
        int clickFrame{-1};

        /// Rejects a composition the pack cannot fit all of its phases into.
        void validate() const;

        [[nodiscard]] int endFrame() const { return startFrame + duration; }
        [[nodiscard]] int resolvedClickFrame() const;
    };

    /// What the pack built. The handles point into the scene's own handle storage,
    /// which is stable for the scene's lifetime.
    ///
    /// Every content layer is parented to `controller`, so the controller's
    /// entrance and exit move and fade the whole card: `worldOpacity` is the
    /// product down the hierarchy, and the exit is authored once.
    struct YouTubeSubscribePack {
        LayerHandle* controller{nullptr};
        LayerHandle* avatar{nullptr};
        LayerHandle* channelName{nullptr};
        LayerHandle* subscriberCount{nullptr};
        LayerHandle* button{nullptr};
        LayerHandle* label{nullptr};
        LayerHandle* bell{nullptr};
        int startFrame{0};
        int endFrame{0};
        int clickFrame{0};
    };

    /// Build the card into `scene`. Positions are canvas coordinates: the pack
    /// places the row around the centre of the canvas the scene declares.
    [[nodiscard]] YouTubeSubscribePack buildYouTubeSubscribe(TemplateScene& scene,
                                                             const YouTubeSubscribeSpec& spec = {});

}// namespace chronontemplate::templates

#endif//CHRONONTEMPLATE_TEMPLATES_YOUTUBESUBSCRIBE_HPP
