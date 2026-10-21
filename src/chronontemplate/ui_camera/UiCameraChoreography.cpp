// ChrononTemplate — UI + smooth-camera choreography implementation.
//
// A composer over existing primitives: TemplateScene groups (canonical Null
// controllers), per-segment Easing keys, the CameraRig look-at rig, and the
// temporal motion-blur declaration. See the header for the contract.

#include "chronontemplate/ui_camera/UiCameraChoreography.hpp"

#include "chrononmotion/motion/CameraPanelChoreography.hpp"
#include "chrononmotion/motion/CameraValidation.hpp"
#include "chrononmotion/motion/CameraScreenSpace.hpp"
#include "chrononmotion/motion/Easing.hpp"

#include <algorithm>
#include <cmath>
#include <stdexcept>
#include <vector>

namespace chronontemplate {

    using chrononmotion::Vector2;
    using chrononmotion::Vector3;
    using chrononmotion::motion::Easing;

    namespace {

        void checkedPositive(float value, const char* what) {
            if (!std::isfinite(value) || value <= 0.f)
                throw std::invalid_argument(std::string("UiCameraChoreography: ") + what +
                                            " must be finite and positive");
        }

        void checkedFinite(float value, const char* what) {
            if (!std::isfinite(value))
                throw std::invalid_argument(std::string("UiCameraChoreography: ") + what +
                                            " must be finite");
        }

        void checkWindow(int inFrame, int duration, int totalFrames, const char* what) {
            if (duration <= 0)
                throw std::invalid_argument(std::string("UiCameraChoreography: ") + what +
                                            " duration must be positive");
            if (inFrame < 0 || inFrame + duration > totalFrames)
                throw std::invalid_argument(std::string("UiCameraChoreography: ") + what +
                                            " window must fit inside [0, totalFrames]");
        }

        [[nodiscard]] Vector3 translationOf(const chrononmotion::Matrix4& world) {
            return Vector3(world[12], world[13], world[14]);
        }

        [[nodiscard]] float lengthOf(const Vector3& v) { return std::sqrt(v.dot(v)); }

    }// namespace

    float uiFramingDistance(float subjectWidth, float fovDegrees,
                            const Vector2& viewport, float frameFill) {
        return chrononmotion::motion::camera::panelFramingDistance(
            subjectWidth, fovDegrees, viewport, frameFill);
    }

    UiPanelComposition buildUiPanel(TemplateScene& scene, const UiPanelSpec& spec) {
        if (spec.title.empty())
            throw std::invalid_argument("UiCameraChoreography: the panel title is required");
        checkedPositive(spec.fontSize, "font size");
        checkedPositive(spec.cardSize.x, "card width");
        checkedPositive(spec.cardSize.y, "card height");
        checkedFinite(spec.center.x, "panel center x");
        checkedFinite(spec.center.y, "panel center y");
        if (!std::isfinite(spec.cornerRadius) || spec.cornerRadius < 0.f ||
            spec.cornerRadius > std::min(spec.cardSize.x, spec.cardSize.y) * 0.5f)
            throw std::invalid_argument("UiCameraChoreography: corner radius is outside bounds");
        if (!std::isfinite(spec.strokeWidth) || spec.strokeWidth < 0.f)
            throw std::invalid_argument("UiCameraChoreography: stroke width must be finite");
        checkedPositive(spec.iconSize.x, "icon width");
        checkedPositive(spec.iconSize.y, "icon height");

        UiPanelComposition panel;
        LayerHandle& root = scene.group("UiRoot");
        root.position(0.f, 0.f, 0.f);
        panel.root = root.id();

        // The drop shadow is a second native rounded rect behind the card —
        // an offset dark silhouette, not a renderer effect — so the whole
        // panel stays inside the TemplateScene vocabulary.
        ShapeSpec shadowSpec;
        shadowSpec.size = spec.cardSize;
        shadowSpec.fillColor = "#000000";
        shadowSpec.name = "UiShadow";
        shadowSpec.cornerRadius = spec.cornerRadius;
        LayerHandle& shadow = scene.shape(shadowSpec);
        shadow.position(spec.center.x, spec.center.y + 18.f, -2.f);
        shadow.opacity(0.4f);
        shadow.parent(panel.root);
        panel.shadow = shadow.id();

        ShapeSpec cardSpec;
        cardSpec.size = spec.cardSize;
        cardSpec.fillColor = spec.cardFill;
        cardSpec.name = "UiCard";
        cardSpec.cornerRadius = spec.cornerRadius;
        cardSpec.strokeColor = spec.strokeColor;
        cardSpec.strokeWidth = spec.strokeWidth;
        LayerHandle& card = scene.shape(cardSpec);
        card.position(spec.center.x, spec.center.y, 0.f);
        card.parent(panel.root);
        panel.card = card.id();

        TextSpec titleSpec;
        titleSpec.text = spec.title;
        titleSpec.font = spec.font;
        titleSpec.fontSize = spec.fontSize;
        titleSpec.color = spec.titleColor;
        titleSpec.name = "UiTitle";
        LayerHandle& title = scene.text(titleSpec);
        title.position(spec.center.x, spec.center.y - spec.cardSize.y * 0.18f, 2.f);
        title.parent(panel.root);
        panel.title = title.id();

        if (!spec.iconPath.empty()) {
            ImageSpec iconSpec;
            iconSpec.path = spec.iconPath;
            iconSpec.name = "UiIcon";
            iconSpec.fit = ImageFitMode::Contain;
            iconSpec.targetSize = spec.iconSize;
            LayerHandle& icon = scene.image(iconSpec);
            icon.position(spec.center.x - spec.cardSize.x * 0.5f + spec.iconSize.x * 0.5f + 48.f,
                          spec.center.y - spec.cardSize.y * 0.5f + spec.iconSize.y * 0.5f + 48.f, 2.f);
            icon.parent(panel.root);
            panel.icon = icon.id();
        } else {
            ShapeSpec iconSpec;
            iconSpec.size = spec.iconSize;
            iconSpec.fillColor = "#62C8D6";
            iconSpec.name = "UiIcon";
            iconSpec.cornerRadius = spec.iconSize.x * 0.25f;
            LayerHandle& icon = scene.shape(iconSpec);
            icon.position(spec.center.x - spec.cardSize.x * 0.5f + spec.iconSize.x * 0.5f + 48.f,
                          spec.center.y - spec.cardSize.y * 0.5f + spec.iconSize.y * 0.5f + 48.f, 2.f);
            icon.parent(panel.root);
            panel.icon = icon.id();
        }

        // Real bounds: the card, unless the measured title or icon overflow
        // it. The framing law fits this extent, never the authored numbers.
        const Vector2 titleSize = title.layer().content.metrics.naturalSize;
        const Vector2 iconSize = scene.motion().findLayer(panel.icon)->content.metrics.naturalSize;
        panel.panelSize = spec.cardSize;
        panel.panelSize.x = std::max(panel.panelSize.x, titleSize.x);
        panel.panelSize.x = std::max(panel.panelSize.x, iconSize.x);
        panel.panelSize.y = std::max(panel.panelSize.y, titleSize.y);
        return panel;
    }

    void applyUiCameraChoreography(TemplateScene& scene,
                                   const UiCameraChoreographySpec& spec,
                                   const UiPanelComposition& panel) {
        if (spec.totalFrames <= 0)
            throw std::invalid_argument("UiCameraChoreography: totalFrames must be positive");
        checkWindow(spec.panelInFrame, spec.panelDuration, spec.totalFrames, "panel entrance");
        checkedFinite(spec.panelEnterDistance, "panel enter distance");
        if (panel.root == 0 || panel.card == 0 || panel.title == 0 || panel.icon == 0)
            throw std::invalid_argument("UiCameraChoreography: the panel composition is empty");
        if (!std::isfinite(panel.panelSize.x) || panel.panelSize.x <= 0.f ||
            !std::isfinite(panel.panelSize.y) || panel.panelSize.y <= 0.f)
            throw std::invalid_argument("UiCameraChoreography: the measured panel size is invalid");

        const float fps = scene.fps();

        // ── Panel entrance on the Null root, staggered reveals on children ──
        LayerHandle rootHandle(&scene, panel.root);
        rootHandle.animatePosition(spec.panelInFrame, spec.panelDuration,
                                   Vector3(0.f, spec.panelEnterDistance, 0.f), Easing::easeOut());

        LayerHandle cardHandle(&scene, panel.card);
        cardHandle.animateOpacity(spec.panelInFrame, spec.panelDuration, 0.f, 1.f, Easing::easeOut());
        LayerHandle shadowHandle(&scene, panel.shadow);
        shadowHandle.animateOpacity(spec.panelInFrame, spec.panelDuration, 0.f, 0.4f, Easing::easeOut());
        LayerHandle titleHandle(&scene, panel.title);
        titleHandle.animatePosition(spec.panelInFrame + 2, spec.panelDuration,
                                    Vector3(0.f, 26.f, 0.f), Easing::easeOut());
        titleHandle.animateOpacity(spec.panelInFrame + 2, spec.panelDuration,
                                   0.f, 1.f, Easing::easeOut());
        LayerHandle iconHandle(&scene, panel.icon);
        iconHandle.animate(ScalePop{.inFrame = spec.panelInFrame + 4, .duration = 12, .from = 0.6f});
        iconHandle.animate(FadeIn{.inFrame = spec.panelInFrame + 4, .duration = 12});

        // Camera framing and all CameraRig track evaluation belong to CM3D.
        chrononmotion::motion::camera::CameraPanelChoreography cameraMove;
        cameraMove.subjectWidth = panel.panelSize.x;
        cameraMove.fov = spec.fov;
        cameraMove.frameFill = spec.frameFill;
        cameraMove.safeMargin = spec.safeMargin;
        cameraMove.totalFrames = spec.totalFrames;
        cameraMove.zoomInFrame = spec.zoomInFrame;
        cameraMove.zoomDuration = spec.zoomDuration;
        cameraMove.zoomDolly = spec.zoomDolly;
        cameraMove.panInFrame = spec.panInFrame;
        cameraMove.panDuration = spec.panDuration;
        cameraMove.panOffset = spec.panOffset;
        chrononmotion::motion::camera::applyPanelChoreography(
            scene.cameraRig(), cameraMove, fps, scene.canvas());

        if (spec.motionBlur)
            scene.setTemporalMotionBlur(spec.shutterAngle, spec.motionBlurSamples);
    }

    UiChoreographyReport validateUiChoreography(TemplateScene& scene,
                                                const UiCameraChoreographySpec& spec,
                                                const UiPanelComposition& panel) {
        UiChoreographyReport report;
        auto fail = [&](const std::string& problem) { report.problems.push_back(problem); };

        if (!scene.validate().empty())
            fail("motion core validation: " + scene.validate().front());

        const float fps = scene.fps();
        const Vector2 viewport = scene.canvas();
        auto& rig = scene.cameraRig();

        // CM3D owns camera-track temporal validation. Template keeps the
        // composition-specific parenting and safe-area checks below.
        const auto cameraTrack = chrononmotion::motion::validateCameraTrack(
            rig, {.totalFrames = spec.totalFrames, .settleWindowFrames = 12,
                  .framesPerSecond = fps, .maxPositionStep = 240.f,
                  .minimumMidTrackSpeed = 1.f});
        report.maxJump = cameraTrack.maxPositionStep;
        report.midRate = cameraTrack.maxMidTrackSpeed;
        report.endRate = cameraTrack.maxSettleSpeed;
        for (const auto& problem : cameraTrack.failures) fail(problem);

        // 3. Animated parenting end-to-end: children follow the Null root.
        // Remove the child's authored local stagger delta before comparing
        // with root translation: the title has its own entrance position keys.
        const std::vector<int> stamps = {spec.panelInFrame, spec.panelInFrame + spec.panelDuration,
                                         spec.zoomInFrame + spec.zoomDuration,
                                         spec.panInFrame + spec.panDuration, spec.totalFrames};
        bool parentingChecked = false;
        for (std::size_t i = 1; i < stamps.size(); ++i) {
            scene.motion().evaluate(stamps[i - 1]);
            const Vector3 rootA = translationOf(scene.motion().worldMatrix(panel.root));
            const Vector3 titleA = translationOf(scene.motion().worldMatrix(panel.title));
            scene.motion().evaluate(stamps[i]);
            const Vector3 rootB = translationOf(scene.motion().worldMatrix(panel.root));
            const Vector3 titleB = translationOf(scene.motion().worldMatrix(panel.title));
            const Vector3 rootDelta = rootB - rootA;
            const auto* title = scene.motion().findLayer(panel.title);
            const Vector3 localDelta = title->sample(static_cast<float>(stamps[i]) / fps).position -
                title->sample(static_cast<float>(stamps[i - 1]) / fps).position;
            const Vector3 titleDelta = titleB - titleA - localDelta;
            if (lengthOf(rootDelta) < 1e-3f)
                continue;
            parentingChecked = true;
            const float mismatch = lengthOf(titleDelta - rootDelta);
            if (mismatch > 0.01f * lengthOf(rootDelta) + 0.5f) {
                fail("parenting drift between frames " + std::to_string(stamps[i - 1]) + " and " +
                     std::to_string(stamps[i]));
                break;
            }
        }
        if (!parentingChecked)
            fail("parenting unproven: the Null root never moves across the stamps");

        // 4. Safe-area framing of the measured panel across the whole window.
        chrononmotion::motion::ScreenCameraIntrinsics intrinsics;
        intrinsics.viewport = viewport;
        for (int frame = 0; frame <= spec.totalFrames; ++frame) {
            const float seconds = static_cast<float>(frame) / fps;
            scene.motion().evaluate(frame);
            const Vector3 titleWorld = translationOf(scene.motion().worldMatrix(panel.title));
            const auto pose = rig.sample(seconds);
            intrinsics.fovDegrees = pose.fov;
            const Vector2 screen =
                chrononmotion::motion::projectToScreen(titleWorld, pose, intrinsics);
            if (!(screen.x >= 0.05f * viewport.x && screen.x <= 0.95f * viewport.x &&
                  screen.y >= 0.08f * viewport.y && screen.y <= 0.92f * viewport.y)) {
                fail("title leaves the safe area at frame " + std::to_string(frame));
                break;
            }
        }
        report.ok = report.problems.empty();
        return report;
    }

}// namespace chronontemplate
