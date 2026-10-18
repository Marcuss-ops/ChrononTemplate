// ChrononTemplate — camera-led word highlights with real focus and point lights.

#ifndef CHRONONTEMPLATE_WORD_LENS_PACK_HPP
#define CHRONONTEMPLATE_WORD_LENS_PACK_HPP

#include "chronontemplate/core/TemplateScene.hpp"

#include "chrononmotion/math/Vector3.hpp"

#include <string>
#include <vector>

namespace chronontemplate {

    struct WordLensBeat {
        std::string text{};
        chrononmotion::Vector2 center{};
        int startFrame{0};
        int focusFrame{0};
        int endFrame{120};
        float focusBehindZ{12.f};
        float lightBehindZ{110.f};
    };

    struct WordLensSpec {
        std::string backgroundImage{"assets/screenrecording_word_lens/word_lens_kitchen_blurred.png"};
        std::string foregroundImage{"assets/screenrecording_word_lens/word_lens_presenter_cutout.png"};
        std::vector<WordLensBeat> words{
            {"food", {620.f, 390.f}, 0, 6, 86, 12.f, 110.f},
            {"houses", {1310.f, 645.f}, 34, 48, 360, 12.f, 110.f},
            {"see", {1320.f, 400.f}, 124, 138, 360, 12.f, 110.f},
        };
        // Offsets the subject plate while it follows the camera, leaving clean
        // negative space beside the centered word callout.
        chrononmotion::Vector2 backgroundCameraOffset{0.f, 0.f};
        float baseFovDegrees{48.f};
        float focusFovDegrees{38.f};
        float cameraDistance{1080.f};
        // RenderPlan's supported DOF aperture channel is normalized to [0, 1].
        float aperture{0.18f};
        float fStop{5.6f};
        float maxBlurPixels{10.f};
        float highlightGain{1.25f};
        int focusTravelFrames{24};
        int fadeFrames{10};
    };

    struct WordLensBoard {
        std::vector<MotionLayerId> wordLayers{};
        std::vector<MotionLayerId> underlineLayers{};
        std::vector<MotionLayerId> pointLightIds{};
    };

    /// Author words, underlines, behind-word point lights, and one tracked lens.
    /// Camera target/FOV/focus/aperture are keyed on ChrononMotion3D CameraRig.
    [[nodiscard]] WordLensBoard addWordLensBoard(TemplateScene& scene,
                                                  const WordLensSpec& spec = {});

} // namespace chronontemplate

#endif // CHRONONTEMPLATE_WORD_LENS_PACK_HPP
