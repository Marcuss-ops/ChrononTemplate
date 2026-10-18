#include "chronontemplate/camera_roll/WordLensPack.hpp"

#include "chrononmotion/math/Color.hpp"
#include "chrononmotion/motion/Lighting.hpp"
#include "chrononmotion/motion/Easing.hpp"

#include <algorithm>
#include <cmath>
#include <stdexcept>

namespace chronontemplate {

    namespace {

        using chrononmotion::Vector2;
        using chrononmotion::Vector3;
        using chrononmotion::motion::CameraRig;
        using chrononmotion::motion::Easing;
        using chrononmotion::motion::PointLight;

        constexpr float kCanvasWidth = 1920.f;
        constexpr float kCanvasHeight = 1080.f;
        constexpr float kBackgroundDepth = 300.f;
        constexpr float kTextFontSize = 142.f;
        constexpr float kUnderlineHeight = 34.f;
        // Keep the callout in the open upper-right area beside the presenter.
        constexpr float kCameraAimOffsetX = -110.f;
        constexpr float kCameraAimOffsetY = -120.f;
        constexpr float kPresenterOffsetX = -330.f;

        float secondsAt(int frame, float fps) {
            return static_cast<float>(frame) / fps;
        }

        Vector3 cameraAnchor(const WordLensBeat& beat, float z) {
            return Vector3(beat.center.x + kCameraAimOffsetX,
                           beat.center.y + kCameraAimOffsetY, z);
        }

        float focusDistance(const WordLensBeat& beat, float cameraDistance) {
            const float z = cameraDistance + beat.focusBehindZ;
            return std::sqrt(z * z + kCameraAimOffsetX * kCameraAimOffsetX +
                             kCameraAimOffsetY * kCameraAimOffsetY);
        }

        void validate(const WordLensSpec& spec) {
            if (spec.backgroundImage.empty() || spec.foregroundImage.empty() || spec.words.empty() ||
                !(spec.baseFovDegrees > 0.f && spec.baseFovDegrees < 180.f) ||
                !(spec.focusFovDegrees > 0.f && spec.focusFovDegrees <= spec.baseFovDegrees) ||
                !(spec.cameraDistance > 0.f) || !(spec.aperture > 0.f && spec.aperture <= 1.f) ||
                !(spec.fStop > 0.f) || !(spec.maxBlurPixels >= 0.f) ||
                !(spec.highlightGain >= 0.f) || spec.focusTravelFrames < 2 || spec.fadeFrames < 1) {
                throw std::invalid_argument("addWordLensBoard: invalid camera, lens, background, or timing spec");
            }
            int priorFocus = -1;
            for (const auto& word : spec.words) {
                if (word.text.empty() || word.startFrame < 0 || word.focusFrame < word.startFrame ||
                    word.endFrame <= word.focusFrame || word.focusFrame <= priorFocus ||
                    word.focusBehindZ < 0.f || word.lightBehindZ <= word.focusBehindZ ||
                    !std::isfinite(word.center.x) || !std::isfinite(word.center.y)) {
                    throw std::invalid_argument("addWordLensBoard: words need ordered frames and finite anchors");
                }
                priorFocus = word.focusFrame;
            }
        }

        void authorCamera(TemplateScene& scene, const WordLensSpec& spec) {
            CameraRig& camera = scene.cameraRig();
            const auto& first = spec.words.front();
            const Vector3 firstTarget = cameraAnchor(first, -first.focusBehindZ);
            const Vector3 firstPosition = cameraAnchor(first, spec.cameraDistance);
            camera.setPosition(firstPosition)
                  .setTarget(firstTarget)
                  .setFov(spec.baseFovDegrees)
                  .setAperture(spec.aperture)
                  .setFocusDistance(focusDistance(first, spec.cameraDistance))
                  .setFStop(spec.fStop)
                  .setIrisBlades(8)
                  .setMaxBlur(spec.maxBlurPixels)
                  .setHighlightGain(spec.highlightGain);

            auto& positions = camera.positionTrack();
            auto& targets = camera.targetTrack();
            auto& fov = camera.fovTrack();
            auto& focus = camera.focusDistanceTrack();
            auto& aperture = camera.apertureTrack();
            const float fps = scene.fps();
            const Easing ease = Easing::easeInOut();

            const Vector3 initialPosition = cameraAnchor(first, spec.cameraDistance);
            const Vector3 initialTarget = cameraAnchor(first, -first.focusBehindZ);
            positions.add(secondsAt(first.focusFrame, fps), initialPosition, ease);
            targets.add(secondsAt(first.focusFrame, fps), initialTarget, ease);
            fov.add(secondsAt(first.focusFrame, fps), spec.focusFovDegrees, ease);
            focus.add(secondsAt(first.focusFrame, fps), focusDistance(first, spec.cameraDistance), ease);
            aperture.add(secondsAt(first.focusFrame, fps), spec.aperture, ease);

            for (std::size_t index = 1; index < spec.words.size(); ++index) {
                const auto& previous = spec.words[index - 1];
                const auto& current = spec.words[index];
                const int halfTravel = std::max(1, spec.focusTravelFrames / 2);
                const int travelStart = std::max(previous.focusFrame, current.focusFrame - halfTravel);
                const int travelEnd = current.focusFrame + halfTravel;
                const float t0 = secondsAt(travelStart, fps);
                const float t1 = secondsAt(travelEnd, fps);
                const Vector3 position0 = cameraAnchor(previous, spec.cameraDistance);
                const Vector3 position1 = cameraAnchor(current, spec.cameraDistance);
                const Vector3 target0 = cameraAnchor(previous, -previous.focusBehindZ);
                const Vector3 target1 = cameraAnchor(current, -current.focusBehindZ);

                positions.add(t0, position0, ease).add(t1, position1, ease);
                targets.add(t0, target0, ease).add(t1, target1, ease);
                fov.add(t0, spec.baseFovDegrees, ease).add(t1, spec.focusFovDegrees, ease);
                focus.add(t0, focusDistance(previous, spec.cameraDistance), ease)
                      .add(t1, focusDistance(current, spec.cameraDistance), ease);
                aperture.add(t0, spec.aperture * 0.78f, ease)
                         .add(t1, spec.aperture, ease);
            }
        }

        void authorPointLight(TemplateScene& scene, const WordLensBeat& beat,
                              std::size_t index, int fadeFrames, WordLensBoard& board) {
            constexpr chrononmotion::motion::Layer::Id kPointLightBase = 8000;
            const auto lightId = kPointLightBase + static_cast<chrononmotion::motion::Layer::Id>(index);
            PointLight& light = scene.motion().addPointLight(lightId, "WordPointLight_" + beat.text);
            // The RenderPlan light color channel is linear sRGB. Assign these
            // components directly so its RGB-to-hex round-trip stays exact.
            light.color.r = 1.f;
            light.color.g = 0.4072402f;
            light.color.b = 0.05126946f;
            light.transform.position.set(beat.center.x, beat.center.y, -beat.lightBehindZ);
            light.intensity = 0.f;
            light.range = 680.f;
            light.decay = 2.f;

            const float fps = scene.fps();
            const int peakStart = std::min(beat.endFrame - 1, beat.startFrame + fadeFrames);
            const int peakEnd = std::max(peakStart, beat.endFrame - fadeFrames);
            light.intensityTrack.add(secondsAt(beat.startFrame, fps), 0.f, Easing::easeOut())
                .add(secondsAt(peakStart, fps), 12.f, Easing::easeInOut())
                .add(secondsAt(peakEnd, fps), 12.f, Easing::easeInOut())
                .add(secondsAt(beat.endFrame, fps), 0.f, Easing::easeIn());
            board.pointLightIds.push_back(lightId);
        }

    } // namespace

    WordLensBoard addWordLensBoard(TemplateScene& scene, const WordLensSpec& spec) {
        validate(spec);
        WordLensBoard board;

        const float backgroundHeight = 2.f * (spec.cameraDistance + kBackgroundDepth) *
                                       std::tan(spec.baseFovDegrees * 0.5f * 3.14159265358979323846f / 180.f);
        const float backgroundWidth = backgroundHeight * (kCanvasWidth / kCanvasHeight);
        auto& background = scene.image({
            .path = spec.backgroundImage,
            .name = "WordLensBackground",
            .fit = ImageFitMode::Cover,
            .targetSize = Vector2(backgroundWidth, backgroundHeight),
        });
        const auto& firstBeat = spec.words.front();
        background.position(firstBeat.center.x + kCameraAimOffsetX + spec.backgroundCameraOffset.x,
                            firstBeat.center.y + kCameraAimOffsetY + spec.backgroundCameraOffset.y, -kBackgroundDepth);
        background.layer().alive(0, spec.words.back().endFrame);
        auto& backgroundPosition = background.layer().tracks.position;
        const float fps = scene.fps();
        const Easing cameraEase = Easing::easeInOut();
        backgroundPosition.add(0.f, Vector3(firstBeat.center.x + kCameraAimOffsetX + spec.backgroundCameraOffset.x,
                                            firstBeat.center.y + kCameraAimOffsetY + spec.backgroundCameraOffset.y,
                                            -kBackgroundDepth), cameraEase);
        for (std::size_t index = 1; index < spec.words.size(); ++index) {
            const auto& previous = spec.words[index - 1];
            const auto& current = spec.words[index];
            const int halfTravel = std::max(1, spec.focusTravelFrames / 2);
            const int travelStart = std::max(previous.focusFrame, current.focusFrame - halfTravel);
            const int travelEnd = current.focusFrame + halfTravel;
            backgroundPosition
                .add(secondsAt(travelStart, fps),
                     Vector3(previous.center.x + kCameraAimOffsetX + spec.backgroundCameraOffset.x,
                             previous.center.y + kCameraAimOffsetY + spec.backgroundCameraOffset.y,
                             -kBackgroundDepth), cameraEase)
                .add(secondsAt(travelEnd, fps),
                     Vector3(current.center.x + kCameraAimOffsetX + spec.backgroundCameraOffset.x,
                             current.center.y + kCameraAimOffsetY + spec.backgroundCameraOffset.y,
                             -kBackgroundDepth), cameraEase);
        }

        // Keep the presenter on a separate, nearer depth plane. The camera
        // DOF pass can then soften the kitchen while preserving the face.
        auto& presenter = scene.image({
            .path = spec.foregroundImage,
            .name = "WordLensPresenter",
            .fit = ImageFitMode::Cover,
            .targetSize = Vector2(backgroundWidth, backgroundHeight),
        });
        presenter.position(firstBeat.center.x + kCameraAimOffsetX + kPresenterOffsetX + spec.backgroundCameraOffset.x,
                           firstBeat.center.y + kCameraAimOffsetY + spec.backgroundCameraOffset.y, 24.f);
        presenter.layer().alive(0, spec.words.back().endFrame);
        presenter.layer().tracks.scale.add(0.f, Vector3(0.9f, 0.9f, 1.f), cameraEase);
        auto& presenterPosition = presenter.layer().tracks.position;
        presenterPosition.add(0.f, Vector3(firstBeat.center.x + kCameraAimOffsetX + kPresenterOffsetX + spec.backgroundCameraOffset.x,
                                           firstBeat.center.y + kCameraAimOffsetY + spec.backgroundCameraOffset.y,
                                           24.f), cameraEase);
        for (std::size_t index = 1; index < spec.words.size(); ++index) {
            const auto& previous = spec.words[index - 1];
            const auto& current = spec.words[index];
            const int halfTravel = std::max(1, spec.focusTravelFrames / 2);
            const int travelStart = std::max(previous.focusFrame, current.focusFrame - halfTravel);
            const int travelEnd = current.focusFrame + halfTravel;
            presenterPosition
                .add(secondsAt(travelStart, fps),
                     Vector3(previous.center.x + kCameraAimOffsetX + kPresenterOffsetX + spec.backgroundCameraOffset.x,
                             previous.center.y + kCameraAimOffsetY + spec.backgroundCameraOffset.y, 24.f), cameraEase)
                .add(secondsAt(travelEnd, fps),
                     Vector3(current.center.x + kCameraAimOffsetX + kPresenterOffsetX + spec.backgroundCameraOffset.x,
                             current.center.y + kCameraAimOffsetY + spec.backgroundCameraOffset.y, 24.f), cameraEase);
        }

        for (std::size_t index = 0; index < spec.words.size(); ++index) {
            const auto& beat = spec.words[index];
            const float estimatedWidth = std::max(220.f, static_cast<float>(beat.text.size()) * kTextFontSize * 0.61f);
            auto& underline = scene.shape({
                .size = Vector2(estimatedWidth + 30.f, kUnderlineHeight),
                .fillColor = "#F2C52B",
                .name = "WordUnderline_" + beat.text,
                .cornerRadius = 4.f,
            });
            // Match the reference's solid yellow marker passing through the
            // lower portion of the glyphs, rather than a thin underline.
            underline.position(beat.center.x, beat.center.y - 49.f, -12.f)
                     .alive(beat.startFrame, beat.endFrame)
                     .animateOpacity(beat.startFrame, spec.fadeFrames, 0.f, 1.f)
                     .animateOpacity(beat.endFrame - spec.fadeFrames, spec.fadeFrames, 1.f, 0.f);
            underline.layer().tracks.scale
                .add(secondsAt(beat.startFrame, fps), Vector3(0.04f, 1.f, 1.f), Easing::easeOut())
                .add(secondsAt(beat.startFrame + spec.fadeFrames, fps), Vector3(1.f, 1.f, 1.f), Easing::easeOut());

            auto& word = scene.text({
                .text = beat.text,
                .font = "assets/fonts/HelveticaNeue-Medium.otf",
                .fontSize = kTextFontSize,
                .color = "#FFF9EC",
                .name = "WordLens_" + beat.text,
                .glow = TextGlowStyle{.color = "#FFD35A", .radius = 9.f, .intensity = 0.12f},
            });
            word.position(beat.center.x, beat.center.y, 0.f)
                .alive(beat.startFrame, beat.endFrame)
                .animateOpacity(beat.startFrame, spec.fadeFrames, 0.f, 1.f)
                .animateOpacity(beat.endFrame - spec.fadeFrames, spec.fadeFrames, 1.f, 0.f);
            word.layer().tracks.scale
                .add(secondsAt(beat.startFrame, fps), Vector3(0.92f, 0.92f, 1.f), Easing::easeOut())
                .add(secondsAt(beat.startFrame + spec.fadeFrames, fps), Vector3(1.f, 1.f, 1.f), Easing::easeOut());

            board.wordLayers.push_back(word.id());
            board.underlineLayers.push_back(underline.id());
            authorPointLight(scene, beat, index, spec.fadeFrames, board);
        }

        authorCamera(scene, spec);
        return board;
    }

} // namespace chronontemplate
