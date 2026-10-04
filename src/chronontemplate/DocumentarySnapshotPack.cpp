#include "chronontemplate/DocumentarySnapshotPack.hpp"

#include "chrononmotion/math/MathUtils.hpp"
#include "chrononmotion/motion/CameraRig.hpp"
#include "chrononmotion/motion/Easing.hpp"

#include <algorithm>
#include <cmath>
#include <stdexcept>

namespace chronontemplate {
    namespace {
        using chrononmotion::Vector2;
        using chrononmotion::Vector3;
        using chrononmotion::Quaternion;
        using chrononmotion::motion::CameraPose;
        using chrononmotion::motion::Easing;
        using chrononmotion::motion::Layer;

        constexpr float kPi = 3.14159265358979323846f;
        float at(int frame, float fps) { return static_cast<float>(frame) / fps; }

        bool valid(const ShotAnchor& a) {
            return std::isfinite(a.center.x) && std::isfinite(a.center.y) &&
                   std::isfinite(a.center.z) && std::isfinite(a.halfWidth) &&
                   std::isfinite(a.halfHeight) && a.halfWidth > 0.f && a.halfHeight > 0.f &&
                   std::isfinite(a.orientation.x) && std::isfinite(a.orientation.y) &&
                   std::isfinite(a.orientation.z) && std::isfinite(a.orientation.w) &&
                   a.orientation.lengthSq() > 1e-8f;
        }

        bool requiresMultiple(DocumentaryRecipe recipe) {
            return recipe == DocumentaryRecipe::PhotoStack ||
                   recipe == DocumentaryRecipe::FilmstripHandoff ||
                   recipe == DocumentaryRecipe::ArchiveCraneReveal;
        }

        void validateMultiImageLayout(const DocumentaryShot& shot) {
            if (shot.recipe == DocumentaryRecipe::PhotoStack) {
                for (std::size_t i = 1; i < shot.snapshots.size(); ++i) {
                    if (shot.snapshots[i - 1].anchor.center.z - shot.snapshots[i].anchor.center.z < 1.f)
                        throw std::invalid_argument("addDocumentarySnapshot: photo stack must have ordered depth gaps");
                }
            }
            if (shot.recipe == DocumentaryRecipe::FilmstripHandoff) {
                const auto& first = shot.snapshots.front().anchor;
                const auto& second = shot.snapshots[1].anchor;
                const float gap = second.center.x - first.center.x;
                if (gap <= first.halfWidth + second.halfWidth)
                    throw std::invalid_argument("addDocumentarySnapshot: filmstrip cards must have a positive gap");
                for (std::size_t i = 1; i < shot.snapshots.size(); ++i) {
                    const auto& previous = shot.snapshots[i - 1].anchor;
                    const auto& current = shot.snapshots[i].anchor;
                    if (std::fabs((current.center.x - previous.center.x) - gap) > 1.f ||
                        std::fabs(current.center.y - first.center.y) > 1.f ||
                        std::fabs(current.center.z - first.center.z) > 1.f ||
                        std::fabs(current.halfWidth - first.halfWidth) > 1.f ||
                        std::fabs(current.halfHeight - first.halfHeight) > 1.f)
                        throw std::invalid_argument("addDocumentarySnapshot: filmstrip requires evenly spaced equal cards");
                }
            }
        }

        ImageFrameStyle frameFor(SnapshotStyle style) {
            switch (style) {
                case SnapshotStyle::Clean:
                    return {.cornerRadius = 0.f, .borderColor = "#F2F0EA", .borderWidth = 3.f};
                case SnapshotStyle::Archive:
                    return {.cornerRadius = 0.f, .borderColor = "#E8E2D5", .borderWidth = 8.f,
                            .saturation = 0.78f, .contrast = 1.08f, .grain = 0.008f, .vignette = 0.12f,
                            .grainSeed = 1986};
                case SnapshotStyle::Polaroid:
                    return {.cornerRadius = 0.f, .borderColor = "#F8F4E8", .borderWidth = 18.f};
                case SnapshotStyle::Filmstrip:
                    return {.cornerRadius = 0.f, .borderColor = "#151515", .borderWidth = 14.f,
                            .contrast = 1.08f, .grain = 0.012f, .grainSeed = 35};
                case SnapshotStyle::Evidence:
                    return {.cornerRadius = 0.f, .borderColor = "#C92A32", .borderWidth = 5.f};
                case SnapshotStyle::Newspaper:
                    return {.cornerRadius = 0.f, .borderColor = "#D8D0BE", .borderWidth = 12.f,
                            .saturation = 0.f, .contrast = 1.32f, .grain = 0.01f, .vignette = 0.08f,
                            .grainSeed = 1917};
                case SnapshotStyle::BlackAndWhiteDocumentary:
                    return {.cornerRadius = 0.f, .borderColor = "#E8E2D5", .borderWidth = 6.f,
                            .saturation = 0.f, .contrast = 1.16f, .grain = 0.008f, .vignette = 0.10f,
                            .grainSeed = 1960};
            }
            throw std::invalid_argument("addDocumentarySnapshot: unknown snapshot style");
        }

        ShotAnchor resolvedSnapshotAnchor(const DocumentaryShot& shot, std::size_t index) {
            ShotAnchor anchor = shot.snapshots[index].anchor;
            if (shot.recipe == DocumentaryRecipe::Reveal90) {
                Quaternion rightWall;
                rightWall.setFromAxisAngle(Vector3(0.f, 1.f, 0.f), -kPi * 0.5f);
                anchor.orientation.multiply(rightWall).normalize();
            }
            return anchor;
        }

        Vector3 cameraAt(const ShotAnchor& anchor, float distance) {
            Vector3 normal(0.f, 0.f, 1.f);
            normal.applyQuaternion(anchor.orientation);
            normal.normalize();
            return Vector3(anchor.center.x + normal.x * distance,
                           anchor.center.y + normal.y * distance,
                           anchor.center.z + normal.z * distance);
        }

        void addKey(Layer& layer, float time, const Vector3& value, const Easing& easing) {
            layer.tracks.position.add(time, value, easing);
        }
    }

    const char* documentaryRecipeId(DocumentaryRecipe recipe) noexcept {
        switch (recipe) {
            case DocumentaryRecipe::SnapDown: return "doc_title_snap_down";
            case DocumentaryRecipe::PullbackReveal: return "doc_title_pullback_photo_reveal";
            case DocumentaryRecipe::PushThroughSnapshot: return "doc_title_push_through_snapshot";
            case DocumentaryRecipe::WhipToPhoto: return "doc_title_whip_to_photo";
            case DocumentaryRecipe::FocusDrop: return "doc_title_focus_drop";
            case DocumentaryRecipe::Reveal90: return "doc_title_90_reveal";
            case DocumentaryRecipe::CornerTurn: return "doc_title_corner_turn";
            case DocumentaryRecipe::ForegroundPhotoPass: return "doc_title_foreground_photo_pass";
            case DocumentaryRecipe::PhotoStack: return "doc_title_photo_stack";
            case DocumentaryRecipe::FilmstripHandoff: return "doc_title_filmstrip_handoff";
            case DocumentaryRecipe::SplitDepth: return "doc_title_split_depth";
            case DocumentaryRecipe::ArchiveCraneReveal: return "doc_archive_crane_reveal";
        }
        return "doc_title_unknown";
    }

    const char* snapshotStyleId(SnapshotStyle style) noexcept {
        switch (style) {
            case SnapshotStyle::Clean: return "snapshot_clean";
            case SnapshotStyle::Archive: return "snapshot_archive";
            case SnapshotStyle::Polaroid: return "snapshot_polaroid";
            case SnapshotStyle::Filmstrip: return "snapshot_filmstrip";
            case SnapshotStyle::Evidence: return "snapshot_evidence";
            case SnapshotStyle::Newspaper: return "snapshot_newspaper";
            case SnapshotStyle::BlackAndWhiteDocumentary: return "snapshot_bw_documentary";
        }
        return "snapshot_unknown";
    }

    std::vector<std::string> documentaryRecipeIds() {
        std::vector<std::string> ids;
        for (const auto recipe : {DocumentaryRecipe::SnapDown, DocumentaryRecipe::PullbackReveal,
                                  DocumentaryRecipe::PushThroughSnapshot, DocumentaryRecipe::WhipToPhoto,
                                  DocumentaryRecipe::FocusDrop, DocumentaryRecipe::Reveal90,
                                  DocumentaryRecipe::CornerTurn, DocumentaryRecipe::ForegroundPhotoPass,
                                  DocumentaryRecipe::PhotoStack, DocumentaryRecipe::FilmstripHandoff,
                                  DocumentaryRecipe::SplitDepth, DocumentaryRecipe::ArchiveCraneReveal}) {
            ids.emplace_back(documentaryRecipeId(recipe));
        }
        return ids;
    }

    std::vector<std::string> snapshotStyleIds() {
        return {snapshotStyleId(SnapshotStyle::Clean), snapshotStyleId(SnapshotStyle::Archive),
                snapshotStyleId(SnapshotStyle::Polaroid), snapshotStyleId(SnapshotStyle::Filmstrip),
                snapshotStyleId(SnapshotStyle::Evidence), snapshotStyleId(SnapshotStyle::Newspaper),
                snapshotStyleId(SnapshotStyle::BlackAndWhiteDocumentary)};
    }

    void addDocumentarySnapshot(TemplateScene& scene, const TextSpec& title,
                                const DocumentaryShot& shot) {
        switch (shot.recipe) {
            case DocumentaryRecipe::SnapDown:
            case DocumentaryRecipe::PullbackReveal:
            case DocumentaryRecipe::PushThroughSnapshot:
            case DocumentaryRecipe::WhipToPhoto:
            case DocumentaryRecipe::FocusDrop:
            case DocumentaryRecipe::Reveal90:
            case DocumentaryRecipe::CornerTurn:
            case DocumentaryRecipe::ForegroundPhotoPass:
            case DocumentaryRecipe::PhotoStack:
            case DocumentaryRecipe::FilmstripHandoff:
            case DocumentaryRecipe::SplitDepth:
            case DocumentaryRecipe::ArchiveCraneReveal:
                break;
            default:
                throw std::invalid_argument("addDocumentarySnapshot: unknown documentary recipe");
        }
        if (shot.snapshots.empty())
            throw std::invalid_argument("addDocumentarySnapshot: at least one snapshot asset is required");
        if (requiresMultiple(shot.recipe) && shot.snapshots.size() < 3)
            throw std::invalid_argument("addDocumentarySnapshot: this recipe requires at least three snapshots");
        if (!valid(shot.title))
            throw std::invalid_argument("addDocumentarySnapshot: title anchor must be finite and positive");
        for (std::size_t snapshotIndex = 0; snapshotIndex < shot.snapshots.size(); ++snapshotIndex) {
            const auto& snapshot = shot.snapshots[snapshotIndex];
            if (snapshot.path.empty() || !valid(snapshot.anchor))
                throw std::invalid_argument("addDocumentarySnapshot: every snapshot needs a path and valid anchor");
            if (snapshot.fit != SnapshotFit::Fit && snapshot.fit != SnapshotFit::Fill &&
                snapshot.fit != SnapshotFit::Crop)
                throw std::invalid_argument("addDocumentarySnapshot: unsupported snapshot fit mode");
            if (snapshot.fit == SnapshotFit::Crop && !snapshot.crop.enabled)
                throw std::invalid_argument("addDocumentarySnapshot: crop fit requires an explicit crop rectangle");
            if (snapshot.crop.enabled &&
                (!std::isfinite(snapshot.crop.origin.x) || !std::isfinite(snapshot.crop.origin.y) ||
                 !std::isfinite(snapshot.crop.size.x) || !std::isfinite(snapshot.crop.size.y) ||
                 snapshot.crop.origin.x < 0.f || snapshot.crop.origin.y < 0.f ||
                 snapshot.crop.size.x <= 0.f || snapshot.crop.size.y <= 0.f ||
                 snapshot.crop.origin.x + snapshot.crop.size.x > 1.f ||
                 snapshot.crop.origin.y + snapshot.crop.size.y > 1.f))
                throw std::invalid_argument("addDocumentarySnapshot: crop must be a normalized positive rectangle");
        }
        validateMultiImageLayout(shot);
        if (shot.duration < 12 || shot.titleHoldFrames < 0 ||
            shot.titleHoldFrames >= shot.duration || !std::isfinite(shot.cameraDistance) ||
            shot.cameraDistance <= 1.f || shot.inFrame < 0 || shot.transitionFrames < 2 ||
            shot.transitionFrames > shot.duration - shot.titleHoldFrames)
            throw std::invalid_argument("addDocumentarySnapshot: invalid timing or camera distance");
        if (requiresMultiple(shot.recipe) &&
            shot.duration - shot.titleHoldFrames <= static_cast<int>(shot.snapshots.size()))
            throw std::invalid_argument("addDocumentarySnapshot: transition window is too short for all snapshots");
        // A global temporal shutter follows the authored camera path, so it
        // softens rapid documentary handoffs without baking blur into content.
        scene.setTemporalMotionBlur(90.f, 8);
        const ImageFrameStyle frameStyle = frameFor(shot.style);

        auto& titleLayer = scene.text(title);
        titleLayer.position(shot.title.center.x, shot.title.center.y, shot.title.center.z);
        titleLayer.layer().oriented(shot.title.orientation);
        titleLayer.alive(shot.inFrame, shot.inFrame + shot.duration);
        std::vector<Layer*> cardLayers;
        std::vector<Layer*> revealCaptions;
        std::vector<Layer*> photoStackCaptions(shot.snapshots.size(), nullptr);
        cardLayers.reserve(shot.snapshots.size() * 3);
        std::vector<Layer*> foregroundCardLayers;
        foregroundCardLayers.reserve(3);
        for (std::size_t snapshotIndex = 0; snapshotIndex < shot.snapshots.size(); ++snapshotIndex) {
            const auto& snapshot = shot.snapshots[snapshotIndex];
            const ShotAnchor cardAnchor = resolvedSnapshotAnchor(shot, snapshotIndex);
            const ImageFitMode fit = snapshot.fit == SnapshotFit::Fit
                                             ? ImageFitMode::Contain : ImageFitMode::Cover;
            const Vector2 targetSize(snapshot.anchor.halfWidth * 2.f,
                                     snapshot.anchor.halfHeight * 2.f);
            const ImageFrameStyle frameStyle = frameFor(shot.style);
            ImageFrameStyle imageStyle = frameStyle;
            imageStyle.borderColor.clear();
            imageStyle.borderWidth = 0.f;
            ImageCrop imageCrop = snapshot.crop;
            if (shot.recipe == DocumentaryRecipe::Reveal90)
                imageCrop.flipX = !imageCrop.flipX;
            auto& card = scene.image(ImageSpec{.path = snapshot.path,
                                               .name = "DocumentarySnapshot",
                                               .frame = imageStyle,
                                               .fit = fit,
                                               .targetSize = targetSize,
                                               .crop = imageCrop});
            card.position(cardAnchor.center.x, cardAnchor.center.y, cardAnchor.center.z);
            card.layer().oriented(cardAnchor.orientation);
            const auto& measuredSize = card.layer().content.metrics.naturalSize;
            if (measuredSize.x <= 0.f || measuredSize.y <= 0.f ||
                !std::isfinite(measuredSize.x) || !std::isfinite(measuredSize.y))
                throw std::invalid_argument("addDocumentarySnapshot: image measurement must have positive finite dimensions");
            const float contentWidth = measuredSize.x *
                (snapshot.crop.enabled ? snapshot.crop.size.x : 1.f);
            const float contentHeight = measuredSize.y *
                (snapshot.crop.enabled ? snapshot.crop.size.y : 1.f);
            const float scaleX = targetSize.x / contentWidth;
            const float scaleY = targetSize.y / contentHeight;
            const float imageScale = snapshot.fit == SnapshotFit::Fit
                                             ? std::min(scaleX, scaleY)
                                             : std::max(scaleX, scaleY);
            card.scale(imageScale);
            if (snapshot.fit == SnapshotFit::Fit) {
                // RenderPlan image quads inherit the viewport's pixel aspect
                // in camera projection. Counter-scale Y against the source
                // aspect so portrait and landscape cards both keep source
                // pixels undistorted in the projected image plane.
                const Vector2 canvas = scene.canvas();
                const float sourceAspect = contentWidth / contentHeight;
                const float viewportAspect = canvas.x / canvas.y;
                card.layer().transform.scale.y *= viewportAspect / sourceAspect;
            }
            card.alive(shot.inFrame, shot.inFrame + shot.duration);
            cardLayers.push_back(&card.layer());
            if (shot.recipe == DocumentaryRecipe::ForegroundPhotoPass && snapshotIndex == 0)
                foregroundCardLayers.push_back(&card.layer());
            if (frameStyle.borderWidth > 0.f) {
                const float displayWidth = snapshot.fit == SnapshotFit::Fit
                    ? contentWidth * imageScale : targetSize.x;
                const float displayHeight = snapshot.fit == SnapshotFit::Fit
                    ? contentHeight * imageScale : targetSize.y;
                const Vector2 plateSize(displayWidth + frameStyle.borderWidth * 2.f,
                                        displayHeight + frameStyle.borderWidth * 2.f);
                Vector3 plateOffset(0.f, 0.f, -2.f);
                plateOffset.applyQuaternion(cardAnchor.orientation);
                auto& plate = scene.shape(ShapeSpec{
                    .size = plateSize,
                    .fillColor = frameStyle.borderColor,
                    .name = "DocumentarySnapshotFrame",
                    .cornerRadius = frameStyle.cornerRadius + frameStyle.borderWidth});
                plate.position(cardAnchor.center.x + plateOffset.x,
                               cardAnchor.center.y + plateOffset.y,
                               cardAnchor.center.z + plateOffset.z);
                plate.layer().oriented(cardAnchor.orientation);
                plate.alive(shot.inFrame, shot.inFrame + shot.duration);
                cardLayers.push_back(&plate.layer());
                if (shot.recipe == DocumentaryRecipe::ForegroundPhotoPass && snapshotIndex == 0)
                    foregroundCardLayers.push_back(&plate.layer());
            }
            if (!snapshot.caption.empty()) {
                auto& caption = scene.text(TextSpec{.text = snapshot.caption,
                                                     .font = title.font,
                                                     .fontSize = title.fontSize * 0.22f,
                                                     .color = "#E8E2D5",
                                                     .name = "DocumentaryCaption"});
                // Keep the caption's glyph box clear of the frame edge. The
                // Text layer is centered on its anchor, so half a font-size
                // above the card was not enough to avoid visual contact.
                // Keep text in front of the image plane. Equal-depth native
                // text and image quads can z-fight or let the image cover the
                // caption when perspective makes their projections overlap.
                Vector3 captionOffset(0.f, snapshot.anchor.halfHeight + title.fontSize * 0.62f,
                                      4.f);
                captionOffset.applyQuaternion(cardAnchor.orientation);
                caption.position(cardAnchor.center.x + captionOffset.x,
                                 cardAnchor.center.y + captionOffset.y,
                                 cardAnchor.center.z + captionOffset.z);
                Quaternion captionOrientation = cardAnchor.orientation;
                if (shot.recipe == DocumentaryRecipe::Reveal90) {
                    Quaternion readableSide;
                    readableSide.setFromAxisAngle(Vector3(0.f, 1.f, 0.f), kPi);
                    captionOrientation.multiply(readableSide).normalize();
                }
                caption.layer().oriented(captionOrientation);
                caption.alive(shot.inFrame, shot.inFrame + shot.duration);
                if (shot.recipe == DocumentaryRecipe::Reveal90)
                    revealCaptions.push_back(&caption.layer());
                else if (shot.recipe == DocumentaryRecipe::PhotoStack)
                    photoStackCaptions[snapshotIndex] = &caption.layer();
                else
                    cardLayers.push_back(&caption.layer());
                if (shot.recipe == DocumentaryRecipe::ForegroundPhotoPass && snapshotIndex == 0)
                    foregroundCardLayers.push_back(&caption.layer());
            }
        }

        Layer* redPortal = nullptr;
        if (shot.recipe == DocumentaryRecipe::PushThroughSnapshot) {
            const ShotAnchor portalAnchor = resolvedSnapshotAnchor(shot, shot.snapshots.size() - 1);
            Vector3 portalOffset(0.f, 0.f, 2.f);
            portalOffset.applyQuaternion(portalAnchor.orientation);
            auto& portal = scene.shape(ShapeSpec{
                .size = Vector2(portalAnchor.halfWidth * 2.f, portalAnchor.halfHeight * 2.f),
                .fillColor = "#C92A32",
                .name = "DocumentaryRedPortal"});
            portal.position(portalAnchor.center.x + portalOffset.x,
                            portalAnchor.center.y + portalOffset.y,
                            portalAnchor.center.z + portalOffset.z);
            portal.layer().oriented(portalAnchor.orientation);
            portal.alive(shot.inFrame, shot.inFrame + shot.duration);
            redPortal = &portal.layer();
        }

        auto& rig = scene.camera().rig();
        const float fps = scene.fps();
        const int start = shot.inFrame;
        const int handoff = start + shot.titleHoldFrames;
        const int end = start + shot.duration;
        const int transitionLength = end - handoff;
        const int mid = handoff + transitionLength / 2;
        const int fastTransitionEnd = handoff + shot.transitionFrames;
        const int revealTurnMid = handoff + shot.transitionFrames / 2;
        if (shot.recipe == DocumentaryRecipe::Reveal90) {
            titleLayer.layer().tracks.opacity.add(at(start, fps), 1.f, Easing::linear());
            titleLayer.layer().tracks.opacity.add(at(handoff, fps), 1.f, Easing::linear());
            titleLayer.layer().tracks.opacity.add(at(handoff + 1, fps), 0.f, Easing::easeIn());
            titleLayer.layer().tracks.opacity.add(at(end, fps), 0.f, Easing::linear());
            for (Layer* caption : revealCaptions) {
                caption->tracks.opacity.add(at(start, fps), 0.f, Easing::linear());
                caption->tracks.opacity.add(at(fastTransitionEnd, fps), 0.f, Easing::linear());
                caption->tracks.opacity.add(at(fastTransitionEnd + 1, fps), 1.f, Easing::easeOut());
                caption->tracks.opacity.add(at(end, fps), 1.f, Easing::linear());
            }
        }
        for (Layer* card : cardLayers) {
            const float openingOpacity = shot.recipe == DocumentaryRecipe::FocusDrop ? 1.f : 0.f;
            card->tracks.opacity.add(at(start, fps), openingOpacity, Easing::linear());
            card->tracks.opacity.add(at(handoff, fps), openingOpacity, Easing::linear());
            card->tracks.opacity.add(at(fastTransitionEnd, fps), 1.f, Easing::easeOut());
            card->tracks.opacity.add(at(end, fps), 1.f, Easing::linear());
        }
        if (shot.recipe == DocumentaryRecipe::PhotoStack) {
            const int travelStart = handoff + 1;
            const auto switchFrame = [&](std::size_t index) {
                return travelStart + static_cast<int>(
                    (static_cast<std::size_t>(transitionLength - 1) * index) /
                    shot.snapshots.size());
            };
            const auto selectionFrame = [&](std::size_t index) {
                return std::max(fastTransitionEnd + 4, switchFrame(index));
            };
            for (Layer* caption : photoStackCaptions) {
                if (!caption) continue;
                caption->tracks.opacity.add(at(start, fps), 0.f, Easing::linear());
                caption->tracks.opacity.add(at(handoff, fps), 0.f, Easing::linear());
                caption->tracks.opacity.add(at(fastTransitionEnd, fps), 0.f, Easing::linear());
            }
            if (!photoStackCaptions.empty() && photoStackCaptions.front()) {
                auto* firstCaption = photoStackCaptions.front();
                firstCaption->tracks.opacity.add(at(fastTransitionEnd, fps), 1.f, Easing::easeOut());
                firstCaption->tracks.opacity.add(
                    at(std::max(fastTransitionEnd, selectionFrame(1) - 2), fps),
                    1.f, Easing::linear());
                firstCaption->tracks.opacity.add(at(selectionFrame(1) + 2, fps), 0.f, Easing::easeIn());
            }
            for (std::size_t i = 1; i < photoStackCaptions.size(); ++i) {
                const int change = selectionFrame(i);
                if (photoStackCaptions[i]) {
                    photoStackCaptions[i]->tracks.opacity.add(at(change - 2, fps), 0.f, Easing::linear());
                    photoStackCaptions[i]->tracks.opacity.add(at(change + 2, fps), 1.f, Easing::easeOut());
                    if (i + 1 < photoStackCaptions.size()) {
                        photoStackCaptions[i]->tracks.opacity.add(
                            at(std::max(change + 2, selectionFrame(i + 1) - 2), fps),
                            1.f, Easing::linear());
                        photoStackCaptions[i]->tracks.opacity.add(
                            at(selectionFrame(i + 1) + 2, fps), 0.f, Easing::easeIn());
                    }
                }
            }
            if (photoStackCaptions.size() > 1 && photoStackCaptions.back()) {
                const int finalSwitch = selectionFrame(photoStackCaptions.size() - 1);
                photoStackCaptions.back()->tracks.opacity.add(at(finalSwitch - 2, fps), 0.f, Easing::linear());
                photoStackCaptions.back()->tracks.opacity.add(at(finalSwitch + 2, fps), 1.f, Easing::easeOut());
                photoStackCaptions.back()->tracks.opacity.add(at(end, fps), 1.f, Easing::linear());
            }
        }
        const ShotAnchor first = resolvedSnapshotAnchor(shot, 0);
        const ShotAnchor last = resolvedSnapshotAnchor(shot, shot.snapshots.size() - 1);
        ShotAnchor finalAnchor = shot.recipe == DocumentaryRecipe::ForegroundPhotoPass ? first : last;
        float finalDistance = shot.cameraDistance;
        if (shot.recipe == DocumentaryRecipe::ArchiveCraneReveal) {
            float left = shot.title.center.x - shot.title.halfWidth;
            float right = shot.title.center.x + shot.title.halfWidth;
            float top = shot.title.center.y - shot.title.halfHeight;
            float bottom = shot.title.center.y + shot.title.halfHeight;
            for (const auto& snapshot : shot.snapshots) {
                const auto& anchor = snapshot.anchor;
                left = std::min(left, anchor.center.x - anchor.halfWidth);
                right = std::max(right, anchor.center.x + anchor.halfWidth);
                top = std::min(top, anchor.center.y - anchor.halfHeight);
                bottom = std::max(bottom, anchor.center.y + anchor.halfHeight);
                if (!snapshot.caption.empty()) {
                    const float captionSize = title.fontSize * 0.22f;
                    const float captionHalfWidth = captionSize * 0.65f *
                        static_cast<float>(snapshot.caption.size()) * 0.5f;
                    const float captionCenterY = anchor.center.y + anchor.halfHeight +
                                                 title.fontSize * 0.62f;
                    left = std::min(left, anchor.center.x - captionHalfWidth);
                    right = std::max(right, anchor.center.x + captionHalfWidth);
                    top = std::min(top, captionCenterY - captionSize * 0.625f);
                    bottom = std::max(bottom, captionCenterY + captionSize * 0.625f);
                }
            }
            finalAnchor.center = Vector3((left + right) * 0.5f,
                                         (top + bottom) * 0.5f, 0.f);
            finalAnchor.halfWidth = (right - left) * 0.5f;
            finalAnchor.halfHeight = (bottom - top) * 0.5f;
            const float tanHalfFov = std::tan(rig.fov() * 0.5f * kPi / 180.f);
            const Vector2 canvas = scene.canvas();
            const float verticalDistance = finalAnchor.halfHeight / tanHalfFov;
            const float horizontalDistance = finalAnchor.halfWidth /
                (tanHalfFov * canvas.x / canvas.y);
            finalDistance = std::max(shot.cameraDistance,
                                     std::max(verticalDistance, horizontalDistance) * 1.10f);
        } else if (shot.recipe == DocumentaryRecipe::PhotoStack &&
                   !shot.snapshots.back().caption.empty()) {
            const auto& snapshot = shot.snapshots.back();
            const float captionSize = title.fontSize * 0.22f;
            const float captionHalfWidth = captionSize * 0.65f *
                static_cast<float>(snapshot.caption.size()) * 0.5f;
            const float captionCenterY = snapshot.anchor.center.y +
                snapshot.anchor.halfHeight + title.fontSize * 0.62f;
            const float left = std::min(snapshot.anchor.center.x - snapshot.anchor.halfWidth,
                                        snapshot.anchor.center.x - captionHalfWidth);
            const float right = std::max(snapshot.anchor.center.x + snapshot.anchor.halfWidth,
                                         snapshot.anchor.center.x + captionHalfWidth);
            const float top = std::min(snapshot.anchor.center.y - snapshot.anchor.halfHeight,
                                       captionCenterY - captionSize * 0.625f);
            const float bottom = std::max(snapshot.anchor.center.y + snapshot.anchor.halfHeight,
                                          captionCenterY + captionSize * 0.625f);
            finalAnchor.center = Vector3((left + right) * 0.5f,
                                         (top + bottom) * 0.5f, snapshot.anchor.center.z);
            finalAnchor.halfWidth = (right - left) * 0.5f;
            finalAnchor.halfHeight = (bottom - top) * 0.5f;
            const float tanHalfFov = std::tan(rig.fov() * 0.5f * kPi / 180.f);
            const Vector2 canvas = scene.canvas();
            const float verticalDistance = finalAnchor.halfHeight / tanHalfFov;
            const float horizontalDistance = finalAnchor.halfWidth /
                (tanHalfFov * canvas.x / canvas.y);
            finalDistance = std::max(shot.cameraDistance,
                                     std::max(verticalDistance, horizontalDistance) * 1.10f);
        }
        const Vector3 titleCam = cameraAt(shot.title, shot.cameraDistance);
        const Vector3 photoCam = cameraAt(finalAnchor, finalDistance);
        const float closeDistance = shot.cameraDistance * 0.58f;
        auto& position = rig.positionTrack();
        auto& target = rig.targetTrack();
        auto& focus = rig.focusDistanceTrack();
        const auto point = [&](int frame, const Vector3& p, const Vector3& aim,
                               const Easing& easing = Easing::easeInOut()) {
            position.add(at(frame, fps), p, easing);
            target.add(at(frame, fps), aim, easing);
        };

        // Initial static pose agrees with the opening title shot for arbitrary
        // nonzero inFrame. The authored final keys similarly land on the final card.
        rig.setPosition(titleCam).setTarget(shot.title.center);
        Vector3 openingTarget = shot.title.center;
        float openingCameraDistance = shot.cameraDistance;
        if (shot.recipe == DocumentaryRecipe::FocusDrop) {
            const ShotAnchor openingPhoto = resolvedSnapshotAnchor(shot, 0);
            openingTarget = Vector3((shot.title.center.x + openingPhoto.center.x) * 0.5f,
                                    (shot.title.center.y + openingPhoto.center.y) * 0.5f,
                                    (shot.title.center.z + openingPhoto.center.z) * 0.5f);
            const float verticalExtent = std::fabs(shot.title.center.y - openingPhoto.center.y) * 0.5f +
                                         std::max(shot.title.halfHeight, openingPhoto.halfHeight);
            const float tanHalfFov = std::tan(rig.fov() * 0.5f * kPi / 180.f);
            openingCameraDistance = std::max(shot.cameraDistance,
                                             verticalExtent / tanHalfFov * 1.06f);
        }
        const Vector3 openingCamera = shot.recipe == DocumentaryRecipe::PullbackReveal
                                              ? cameraAt(shot.title, closeDistance)
                                              : shot.recipe == DocumentaryRecipe::FocusDrop
                                                    ? cameraAt(ShotAnchor{.center = openingTarget},
                                                               openingCameraDistance)
                                                    : titleCam;
        point(start, openingCamera, openingTarget, Easing::linear());
        switch (shot.recipe) {
            case DocumentaryRecipe::SnapDown: {
                const Vector3 preload = cameraAt(shot.title, shot.cameraDistance * 0.94f);
                point(handoff, preload, shot.title.center);
                point(fastTransitionEnd, photoCam, last.center, Easing::expoOut());
                point(end, photoCam, last.center, Easing::linear());
                break;
            }
            case DocumentaryRecipe::PullbackReveal: {
                const Vector3 close = openingCamera;
                const Vector3 wide = cameraAt(shot.title, shot.cameraDistance * 1.8f);
                point(handoff, close, shot.title.center);
                point(mid, wide, shot.title.center, Easing::easeOut());
                point(end, photoCam, last.center, Easing::easeInOut());
                break;
            }
            case DocumentaryRecipe::PushThroughSnapshot: {
                const float tanHalfFov = std::tan(rig.fov() * 0.5f * kPi / 180.f);
                const float coverDistance = std::max(1.f, 0.96f * std::min(
                        last.halfWidth / (tanHalfFov * rig.aspect()),
                        last.halfHeight / tanHalfFov));
                const Vector3 through = cameraAt(last, coverDistance);
                point(handoff, titleCam, shot.title.center);
                point(fastTransitionEnd, through, last.center, Easing::easeIn());
                point(end, photoCam, last.center, Easing::easeOut());
                // The native rectangle takes over the whole viewport at the
                // closest push frame, then clears to reveal the snapshot below.
                redPortal->tracks.opacity.add(at(start, fps), 0.f, Easing::linear());
                redPortal->tracks.opacity.add(at(handoff, fps), 0.f, Easing::linear());
                redPortal->tracks.opacity.add(at(fastTransitionEnd, fps), 1.f, Easing::easeIn());
                redPortal->tracks.opacity.add(at(end, fps), 0.f, Easing::easeOut());
                break;
            }
            case DocumentaryRecipe::WhipToPhoto: {
                const Vector3 acquisition(shot.title.center.x - shot.cameraDistance * 0.16f,
                                          shot.title.center.y, shot.title.center.z + shot.cameraDistance);
                point(handoff, titleCam, shot.title.center);
                point(handoff + 1, acquisition, shot.title.center, Easing::expoOut());
                point(fastTransitionEnd, photoCam, last.center, Easing::easeOut());
                point(end, photoCam, last.center, Easing::linear());
                break;
            }
            case DocumentaryRecipe::FocusDrop: {
                point(handoff, openingCamera, openingTarget);
                point(end, photoCam, last.center);
                // RenderPlan's native DOF aperture channel is normalized to
                // [0, 1]. Keep it open throughout the handoff so the two depth
                // planes exchange sharpness instead of briefly snapping sharp.
                rig.apertureTrack().add(at(start, fps), 0.18f, Easing::linear());
                rig.apertureTrack().add(at(end, fps), 0.18f, Easing::linear());
                break;
            }
            case DocumentaryRecipe::Reveal90: {
                const Vector3 side(shot.title.center.x + shot.cameraDistance,
                                   shot.title.center.y,
                                   shot.title.center.z + shot.cameraDistance * 0.12f);
                point(handoff, titleCam, shot.title.center);
                point(revealTurnMid, side, shot.title.center, Easing::easeInOut());
                point(fastTransitionEnd, photoCam, last.center, Easing::easeOut());
                point(end, photoCam, last.center);
                break;
            }
            case DocumentaryRecipe::CornerTurn: {
                const Vector3 corner(shot.title.center.x + shot.cameraDistance * 0.70f,
                                     shot.title.center.y, shot.title.center.z + shot.cameraDistance * 0.72f);
                const Vector3 around( last.center.x + shot.cameraDistance * 0.72f,
                                      last.center.y, last.center.z + shot.cameraDistance * 0.70f);
                point(handoff, titleCam, shot.title.center);
                const int turn = handoff + transitionLength / 3;
                const int exit = handoff + (transitionLength * 2) / 3;
                point(turn, corner, shot.title.center, Easing::easeInOut());
                point(exit, around, last.center, Easing::easeInOut());
                point(end, photoCam, last.center);
                break;
            }
            case DocumentaryRecipe::ForegroundPhotoPass: {
                const auto& a = shot.snapshots.front().anchor;
                const int passCenter = handoff + transitionLength / 3;
                const int passExit = handoff + (transitionLength * 2) / 3;
                const Vector3 offscreen(a.center.x - a.halfWidth * 3.f,
                                        shot.title.center.y, a.center.z + 180.f);
                const auto offsetFromAnchor = [&](const Vector3& point) {
                    return Vector3(point.x - a.center.x, point.y - a.center.y,
                                   point.z - a.center.z);
                };
                const Vector3 offscreenOffset = offsetFromAnchor(offscreen);
                const Vector3 passCenterOffset = offsetFromAnchor(
                    Vector3(shot.title.center.x, shot.title.center.y, a.center.z + 180.f));
                const Vector3 passExitOffset = offsetFromAnchor(
                    Vector3(shot.title.center.x + a.halfWidth * 3.f,
                            shot.title.center.y, a.center.z + 180.f));
                for (Layer* foregroundLayer : foregroundCardLayers) {
                    const Vector3 base = foregroundLayer->transform.position;
                    addKey(*foregroundLayer, at(start, fps), base.clone().add(offscreenOffset), Easing::easeIn());
                    addKey(*foregroundLayer, at(handoff, fps), base.clone().add(offscreenOffset), Easing::easeIn());
                    addKey(*foregroundLayer, at(passCenter, fps), base.clone().add(passCenterOffset), Easing::easeInOut());
                    addKey(*foregroundLayer, at(passExit, fps), base.clone().add(passExitOffset), Easing::easeInOut());
                    addKey(*foregroundLayer, at(end, fps), base, Easing::easeOut());
                }
                point(handoff, titleCam, shot.title.center, Easing::linear());
                point(passCenter, titleCam, shot.title.center, Easing::linear());
                point(passExit, cameraAt(a, shot.cameraDistance), a.center, Easing::easeInOut());
                point(end, cameraAt(a, shot.cameraDistance), a.center);
                break;
            }
            case DocumentaryRecipe::PhotoStack: {
                point(handoff, titleCam, shot.title.center);
                const int travelStart = handoff + 1;
                point(travelStart, cameraAt(first, shot.cameraDistance), first.center);
                for (std::size_t i = 1; i < shot.snapshots.size(); ++i) {
                    const int frame = travelStart + static_cast<int>((static_cast<std::size_t>(transitionLength - 1) * i) /
                                                                      shot.snapshots.size());
                    point(frame, cameraAt(shot.snapshots[i].anchor, shot.cameraDistance),
                          shot.snapshots[i].anchor.center, Easing::easeInOut());
                }
                point(end, photoCam, finalAnchor.center);
                break;
            }
            case DocumentaryRecipe::FilmstripHandoff: {
                point(handoff, titleCam, shot.title.center);
                const int travelStart = handoff + 1;
                point(travelStart, cameraAt(first, shot.cameraDistance), first.center);
                for (std::size_t i = 1; i < shot.snapshots.size(); ++i) {
                    const int frame = travelStart + static_cast<int>((static_cast<std::size_t>(transitionLength - 1) * i) /
                                                                      shot.snapshots.size());
                    point(frame, cameraAt(shot.snapshots[i].anchor, shot.cameraDistance),
                          shot.snapshots[i].anchor.center, Easing::linear());
                }
                point(end, photoCam, last.center, Easing::easeOut());
                break;
            }
            case DocumentaryRecipe::SplitDepth: {
                const Vector3 arc((shot.title.center.x + last.center.x) * 0.5f - shot.cameraDistance * 0.15f,
                                  (shot.title.center.y + last.center.y) * 0.5f,
                                  shot.title.center.z + shot.cameraDistance * 1.1f);
                point(handoff, arc, shot.title.center, Easing::easeIn());
                point(mid, arc, last.center, Easing::easeOut());
                point(end, photoCam, last.center);
                rig.apertureTrack().add(at(handoff, fps), 0.f, Easing::linear());
                rig.apertureTrack().add(at(end, fps), 0.06f, Easing::easeInOut());
                break;
            }
            case DocumentaryRecipe::ArchiveCraneReveal: {
                const Vector3 crane(shot.title.center.x, shot.title.center.y - shot.cameraDistance * 0.25f,
                                    shot.title.center.z + shot.cameraDistance * 1.65f);
                point(handoff, crane, shot.title.center, Easing::easeInOut());
                point(mid, Vector3((shot.title.center.x + last.center.x) * 0.5f,
                                   (shot.title.center.y + last.center.y) * 0.5f - shot.cameraDistance * 0.10f,
                                   shot.title.center.z + shot.cameraDistance * 1.30f),
                      last.center, Easing::easeOut());
                point(end, photoCam, finalAnchor.center);
                break;
            }
        }
        if (shot.recipe == DocumentaryRecipe::FocusDrop) {
            // The RenderPlan DOF bridge represents a world-Z focus plane. As
            // this recipe moves the camera, sample the optical-axis distance
            // that intersects an eased title-Z → snapshot-Z rack-focus plane.
            for (int frame = start; frame <= end; ++frame) {
                const float progress = frame <= handoff ? 0.f :
                    static_cast<float>(frame - handoff) / static_cast<float>(end - handoff);
                const float eased = progress * progress * (3.f - 2.f * progress);
                const float focusPlaneZ = shot.title.center.z +
                    (last.center.z - shot.title.center.z) * eased;
                const CameraPose pose = rig.sample(at(frame, fps));
                Vector3 forward(0.f, 0.f, -1.f);
                forward.applyQuaternion(pose.orientation);
                forward.normalize();
                if (std::fabs(forward.z) <= 1e-4f)
                    throw std::invalid_argument(
                        "addDocumentarySnapshot: focus-drop optical axis cannot reach its focus plane");
                const float distance = (focusPlaneZ - pose.position.z) / forward.z;
                if (!std::isfinite(distance) || distance <= 0.f)
                    throw std::invalid_argument(
                        "addDocumentarySnapshot: focus-drop focus plane must stay in front of the camera");
                focus.add(at(frame, fps), distance, Easing::linear());
            }
        } else {
            // Keep focus locked to the authored camera target at every frame.
            // Interpolating only endpoint distances can place the legacy
            // RenderPlan Z focus plane behind its camera during pans and turns.
            for (int frame = start; frame <= end; ++frame) {
                const CameraPose pose = rig.sample(at(frame, fps));
                const float distance = pose.position.distanceTo(pose.target);
                if (!std::isfinite(distance) || distance <= 0.f)
                    throw std::invalid_argument(
                        "addDocumentarySnapshot: camera target must stay in front of the focal plane");
                focus.add(at(frame, fps), distance, Easing::linear());
            }
        }
        rig.setPosition(photoCam).setTarget(finalAnchor.center);
    }
} // namespace chronontemplate
