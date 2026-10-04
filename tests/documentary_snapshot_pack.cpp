#include "chronontemplate/DocumentarySnapshotPack.hpp"

#include "fake_content_host.hpp"
#include "motion_check.hpp"

#include "chrononmotion/motion/CameraScreenSpace.hpp"

#include <cmath>
#include <stdexcept>
#include <algorithm>
#include <array>
#include <vector>

using namespace chronontemplate;
using chronontemplate_test::FakeContentHost;
using chronontemplate_test::findLayer;
using chrononmotion::Vector2;
using chrononmotion::Vector3;
using chrononmotion::Quaternion;
using chrononmotion::motion::ScreenCameraIntrinsics;
using chrononmotion_test::check;
using chrononmotion_test::checkNear;
using chrononmotion_test::section;

namespace {
    constexpr float kW = 1920.f;
    constexpr float kH = 1080.f;
    constexpr float kPi = 3.14159265358979323846f;

    DocumentaryShot makeShot(DocumentaryRecipe recipe) {
        DocumentaryShot shot;
        shot.title.center = Vector3(960.f, 280.f, 0.f);
        shot.title.halfWidth = 520.f;
        shot.title.halfHeight = 100.f;
        shot.recipe = recipe;
        shot.inFrame = 7;
        shot.duration = 120;
        shot.titleHoldFrames = 48;
        shot.snapshots = {
                {"archive_a.jpg", {{960.f, 760.f, -60.f}, 300.f, 168.f}, "ROME, 1960"},
                {"archive_b.jpg", {{760.f, 760.f, -80.f}, 300.f, 168.f}, "THE FACTORY"},
                {"archive_c.jpg", {{1160.f, 760.f, -100.f}, 300.f, 168.f}, "THE ARCHIVE"},
                {"archive_d.jpg", {{1360.f, 760.f, -120.f}, 300.f, 168.f}, "THE PEOPLE"}};
        if (recipe == DocumentaryRecipe::Reveal90) {
            for (auto& snapshot : shot.snapshots)
                snapshot.anchor.center.y = shot.title.center.y;
        }
        if (recipe == DocumentaryRecipe::FilmstripHandoff) {
            for (std::size_t i = 0; i < shot.snapshots.size(); ++i) {
                shot.snapshots[i].anchor.center = Vector3(500.f + 300.f * static_cast<float>(i),
                                                          760.f, -80.f);
                shot.snapshots[i].anchor.halfWidth = 120.f;
                shot.snapshots[i].anchor.halfHeight = 68.f;
            }
        }
        return shot;
    }

    struct Bounds { float left, top, right, bottom; };

    Bounds projectedBounds(const ShotAnchor& anchor, const Vector3& center,
                           const chrononmotion::motion::CameraPose& pose,
                           const ScreenCameraIntrinsics& intrinsics) {
        Bounds result{kW, kH, 0.f, 0.f};
        for (const float sx : {-1.f, 1.f}) for (const float sy : {-1.f, 1.f}) {
            Vector3 local(sx * anchor.halfWidth, sy * anchor.halfHeight, 0.f);
            local.applyQuaternion(anchor.orientation);
            const Vector2 p = chrononmotion::motion::projectToScreen(center.clone().add(local), pose, intrinsics);
            result.left = std::min(result.left, p.x); result.top = std::min(result.top, p.y);
            result.right = std::max(result.right, p.x); result.bottom = std::max(result.bottom, p.y);
        }
        return result;
    }

    bool overlaps(const Bounds& a, const Bounds& b) {
        return a.left < b.right && a.right > b.left && a.top < b.bottom && a.bottom > b.top;
    }

    void allRecipeIdsAreStable() {
        section("documentary recipe vocabulary and catalog metadata");
        const auto ids = documentaryRecipeIds();
        check(ids.size() == 12, "the v1 family exposes all twelve documentary recipes");
        check(ids.front() == "doc_title_snap_down", "snap-down keeps its catalog id");
        check(ids.back() == "doc_archive_crane_reveal", "archive crane keeps its catalog id");
        const auto styles = snapshotStyleIds();
        const std::vector<std::string> expectedStyles = {
            "snapshot_clean", "snapshot_archive", "snapshot_polaroid", "snapshot_filmstrip",
            "snapshot_evidence", "snapshot_newspaper", "snapshot_bw_documentary"};
        check(styles == expectedStyles, "all seven snapshot style ids remain stable and ordered");
    }

    void titleAndCameraContracts() {
        section("title invariance, target handoff, safe final card, and deterministic sampling");
        for (const auto recipe : {DocumentaryRecipe::SnapDown, DocumentaryRecipe::PullbackReveal,
                                  DocumentaryRecipe::PushThroughSnapshot, DocumentaryRecipe::WhipToPhoto,
                                  DocumentaryRecipe::FocusDrop, DocumentaryRecipe::Reveal90,
                                  DocumentaryRecipe::CornerTurn, DocumentaryRecipe::ForegroundPhotoPass,
                                  DocumentaryRecipe::PhotoStack, DocumentaryRecipe::FilmstripHandoff,
                                  DocumentaryRecipe::SplitDepth, DocumentaryRecipe::ArchiveCraneReveal}) {
            FakeContentHost host;
            TemplateScene scene("documentary_snapshot_contract", 30.f, host, kW, kH);
            const DocumentaryShot shot = makeShot(recipe);
            addDocumentarySnapshot(scene,
                                   TextSpec{.text = "THE STORY", .font = "Inter-Bold.ttf",
                                            .fontSize = 144.f, .color = "#FFFFFF",
                                            .name = "DocumentaryTitle"}, shot);
            if (recipe == DocumentaryRecipe::Reveal90)
                check(host.lastImageRequest().crop.flipX,
                      "90-degree reveal requests a horizontal image-content flip without reflecting its world transform");
            const auto title = scene.motion().findLayer("DocumentaryTitle");
            check(title != nullptr, "documentary title layer exists");
            if (!title) continue;

            if (recipe == DocumentaryRecipe::PhotoStack) {
                std::vector<chrononmotion::motion::Layer::Id> captionIds;
                for (const auto& layer : scene.motion().layers())
                    if (layer.name == "DocumentaryCaption") captionIds.push_back(layer.id);
                check(captionIds.size() == shot.snapshots.size(),
                      "photo stack creates one native caption layer per snapshot");
                const auto imageLayers = scene.bindings().layersOf(
                    "image/" + shot.snapshots.back().path);
                const auto* finalCard = imageLayers.empty()
                    ? nullptr : scene.motion().findLayer(imageLayers.back());
                const auto* finalCaption = captionIds.empty()
                    ? nullptr : scene.motion().findLayer(captionIds.back());
                check(finalCard && finalCaption &&
                          finalCaption->transform.position.z > finalCard->transform.position.z,
                      "photo stack captions use a small positive depth bias over their image plane");
                const int handoff = shot.inFrame + shot.titleHoldFrames;
                const int fastEnd = handoff + shot.transitionFrames;
                const int travelStart = handoff + 1;
                const int secondTarget = travelStart + static_cast<int>(
                    (static_cast<std::size_t>(shot.duration - shot.titleHoldFrames - 1) * 1) /
                    shot.snapshots.size());
                const int secondSelected = std::max(fastEnd + 4, secondTarget) + 3;
                const auto selectedPose = scene.submit(secondSelected);
                for (std::size_t i = 0; i < captionIds.size(); ++i) {
                    const auto* caption = findLayer(selectedPose, captionIds[i]);
                    check(caption && std::fabs(caption->transform.opacity - (i == 1 ? 1.f : 0.f)) < 1e-4f,
                          "photo stack shows only the caption for the current camera waypoint");
                }
            }

            const auto first = scene.submit(shot.inFrame);
            const auto last = scene.submit(shot.inFrame + shot.duration);
            const auto* firstTitle = findLayer(first, title->id);
            const auto* lastTitle = findLayer(last, title->id);
            check(firstTitle && lastTitle, "title is submitted at both shot endpoints");
            if (firstTitle && lastTitle) {
                check(chronontemplate_test::sameMatrix(firstTitle->transform.world,
                                                       lastTitle->transform.world),
                      "title world transform remains unchanged across the camera handoff");
                if (recipe == DocumentaryRecipe::Reveal90) {
                    check(std::fabs(firstTitle->transform.opacity - 1.f) < 1e-4f,
                          "90-degree reveal keeps the title visible during its opening hold");
                    check(std::fabs(lastTitle->transform.opacity) < 1e-4f,
                          "90-degree reveal clears the edge-on title at the settled photo");
                    const int turnEndFrame = shot.inFrame + shot.titleHoldFrames + shot.transitionFrames;
                    const auto turnEnd = scene.submit(turnEndFrame);
                    const auto* titleAtTurnEnd = findLayer(turnEnd, title->id);
                    check(titleAtTurnEnd && std::fabs(titleAtTurnEnd->transform.opacity) < 1e-4f,
                          "90-degree reveal clears the title by the declared turn endpoint");
                    const auto captionLayer = scene.motion().findLayer("DocumentaryCaption");
                    const auto captionDuringTurn = scene.submit(turnEndFrame);
                    const auto* captionAtTurnEnd = captionLayer
                            ? findLayer(captionDuringTurn, captionLayer->id) : nullptr;
                    check(captionAtTurnEnd && std::fabs(captionAtTurnEnd->transform.opacity) < 1e-4f,
                          "90-degree reveal keeps caption hidden until the photo faces camera");
                    const auto captionAfterTurn = scene.submit(turnEndFrame + 1);
                    const auto* captionAfterTurnState = captionLayer
                            ? findLayer(captionAfterTurn, captionLayer->id) : nullptr;
                    check(captionAfterTurnState && captionAfterTurnState->transform.opacity > 0.99f,
                          "90-degree reveal restores caption readability immediately after the turn");
                    const auto turnPose = scene.camera().rig().sample(
                            static_cast<float>(turnEndFrame) / scene.fps());
                    checkNear(turnPose.target, shot.snapshots.back().anchor.center, 1e-3f,
                              "90-degree reveal reaches its photo target at the declared turn endpoint");
                }
            }

            const float startTime = static_cast<float>(shot.inFrame) / scene.fps();
            const float handoffTime = static_cast<float>(shot.inFrame + shot.titleHoldFrames) / scene.fps();
            const float endTime = static_cast<float>(shot.inFrame + shot.duration) / scene.fps();
            const auto& cameraKeys = scene.camera().rig().positionTrack().keys();
            const auto hasTime = [&](float expected) {
                for (const auto& key : cameraKeys) if (std::fabs(key.time - expected) < 1e-6f) return true;
                return false;
            };
            check(hasTime(startTime) && hasTime(handoffTime) && hasTime(endTime),
                  "camera transition keys align to the declared start, handoff, and end frames");
            const auto titleAtHandoff = scene.camera().rig().sample(handoffTime);
            const Vector3 handoffTarget = recipe == DocumentaryRecipe::FocusDrop
                ? Vector3((shot.title.center.x + shot.snapshots.front().anchor.center.x) * 0.5f,
                          (shot.title.center.y + shot.snapshots.front().anchor.center.y) * 0.5f,
                          (shot.title.center.z + shot.snapshots.front().anchor.center.z) * 0.5f)
                : shot.title.center;
            checkNear(titleAtHandoff.target, handoffTarget, 1e-3f,
                      "camera preserves the declared opening composition through the hold");
            const auto openingPose = scene.camera().rig().sample(startTime);
            ScreenCameraIntrinsics openingIntrinsics;
            openingIntrinsics.viewport = Vector2(kW, kH);
            openingIntrinsics.fovDegrees = openingPose.fov;
            const Vector2 titleTopLeft = chrononmotion::motion::projectToScreen(
                    Vector3(shot.title.center.x - shot.title.halfWidth,
                            shot.title.center.y - shot.title.halfHeight, shot.title.center.z),
                    openingPose, openingIntrinsics);
            const Vector2 titleBottomRight = chrononmotion::motion::projectToScreen(
                    Vector3(shot.title.center.x + shot.title.halfWidth,
                            shot.title.center.y + shot.title.halfHeight, shot.title.center.z),
                    openingPose, openingIntrinsics);
            check(titleTopLeft.x >= 96.f && titleTopLeft.y >= 54.f &&
                          titleBottomRight.x <= kW - 96.f && titleBottomRight.y <= kH - 54.f,
                  "opening title anchor stays inside the five-percent safe frame");
            if (recipe == DocumentaryRecipe::SnapDown || recipe == DocumentaryRecipe::WhipToPhoto) {
                const auto snapPose = scene.camera().rig().sample(
                        static_cast<float>(shot.inFrame + shot.titleHoldFrames + shot.transitionFrames) /
                        scene.fps());
                checkNear(snapPose.target, shot.snapshots.back().anchor.center, 1e-3f,
                          "snap and whip hit their photo target at the exact transition duration");
            }
            auto previousPose = titleAtHandoff;
            for (int frame = shot.inFrame + shot.titleHoldFrames + 1;
                 frame <= shot.inFrame + shot.duration; ++frame) {
                const auto pose = scene.camera().rig().sample(static_cast<float>(frame) / scene.fps());
                check(previousPose.orientation.dot(pose.orientation) >= -1e-5f,
                      "adjacent camera orientations stay in the same quaternion hemisphere");
                previousPose = pose;
            }

            const auto foregroundIds = scene.bindings().layersOf("image/" + shot.snapshots.front().path);
            const MotionLayerId foregroundId = foregroundIds.empty() ? 0 : foregroundIds.front();
            const auto* foregroundFrame = recipe == DocumentaryRecipe::ForegroundPhotoPass
                ? scene.motion().findLayer("DocumentarySnapshotFrame") : nullptr;
            const auto* foregroundCaption = recipe == DocumentaryRecipe::ForegroundPhotoPass
                ? scene.motion().findLayer("DocumentaryCaption") : nullptr;
            for (const auto& layer : scene.motion().layers()) {
                if (layer.content.kind != chrononmotion::motion::ContentKind::Image ||
                    (recipe == DocumentaryRecipe::ForegroundPhotoPass &&
                     (layer.id == foregroundId ||
                      (foregroundFrame && layer.id == foregroundFrame->id) ||
                      (foregroundCaption && layer.id == foregroundCaption->id)))) continue;
                const auto* a = findLayer(first, layer.id);
                const auto* b = findLayer(last, layer.id);
                check(a && b && chronontemplate_test::sameMatrix(a->transform.world, b->transform.world),
                      "ordinary snapshot card transforms remain invariant during camera-only recipes");
            }

            const auto finalPose = scene.camera().rig().sample(
                    static_cast<float>(shot.inFrame + shot.duration) / scene.fps());
            bool dofValuesInRange = true;
            for (int frame = shot.inFrame; frame <= shot.inFrame + shot.duration; ++frame) {
                const auto pose = scene.camera().rig().sample(static_cast<float>(frame) / scene.fps());
                dofValuesInRange = dofValuesInRange && std::isfinite(pose.aperture) &&
                    pose.aperture >= 0.f && pose.aperture <= 1.f &&
                    std::isfinite(pose.focusDistance) && pose.focusDistance >= 0.f &&
                    (pose.aperture == 0.f || pose.focusDistance > 0.f);
            }
            check(dofValuesInRange,
                  "all documentary recipes keep animated DOF values inside RenderPlan limits");
            bool focusPlaneCompatible = true;
            for (int frame = shot.inFrame; frame <= shot.inFrame + shot.duration; ++frame) {
                const auto pose = scene.camera().rig().sample(static_cast<float>(frame) / scene.fps());
                Vector3 forward(0.f, 0.f, -1.f);
                forward.applyQuaternion(pose.orientation);
                forward.normalize();
                const float motionFocusZ = pose.position.z + forward.z * pose.focusDistance;
                focusPlaneCompatible = focusPlaneCompatible && pose.focusDistance > 0.f &&
                                       std::isfinite(motionFocusZ) && motionFocusZ <= 1e-3f;
            }
            check(focusPlaneCompatible,
                  "focus plane stays in the RenderPlan-compatible half-space for every recipe frame");
            ShotAnchor finalAnchor = recipe == DocumentaryRecipe::ForegroundPhotoPass
                                             ? shot.snapshots.front().anchor
                                             : shot.snapshots.back().anchor;
            if (recipe == DocumentaryRecipe::ArchiveCraneReveal) {
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
                        const float captionSize = 144.f * 0.22f;
                        const float captionHalfWidth = captionSize * 0.65f *
                            static_cast<float>(snapshot.caption.size()) * 0.5f;
                        const float captionCenterY = anchor.center.y + anchor.halfHeight + 144.f * 0.62f;
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
            } else if (recipe == DocumentaryRecipe::PhotoStack &&
                       !shot.snapshots.back().caption.empty()) {
                const auto& snapshot = shot.snapshots.back();
                const float captionSize = 144.f * 0.22f;
                const float captionHalfWidth = captionSize * 0.65f *
                    static_cast<float>(snapshot.caption.size()) * 0.5f;
                const float captionCenterY = snapshot.anchor.center.y +
                    snapshot.anchor.halfHeight + 144.f * 0.62f;
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
            }
            if (recipe == DocumentaryRecipe::Reveal90) {
                Quaternion rightWall;
                rightWall.setFromAxisAngle(Vector3(0.f, 1.f, 0.f), -kPi * 0.5f);
                finalAnchor.orientation.multiply(rightWall).normalize();
            }
            const std::string& finalPhotoPath = recipe == DocumentaryRecipe::ForegroundPhotoPass
                                                        ? shot.snapshots.front().path
                                                        : shot.snapshots.back().path;
            checkNear(finalPose.target, finalAnchor.center, 1e-3f,
                      recipe == DocumentaryRecipe::ArchiveCraneReveal
                          ? "camera target settles on the full archive composition anchor"
                          : recipe == DocumentaryRecipe::PhotoStack
                                ? "camera target settles on the final photo and its caption"
                          : "camera target settles exactly on the final snapshot anchor");

            ScreenCameraIntrinsics intrinsics;
            intrinsics.viewport = Vector2(kW, kH);
            intrinsics.fovDegrees = finalPose.fov;
            const auto imageIds = scene.bindings().layersOf("image/" + finalPhotoPath);
            const auto* finalImage = imageIds.empty() ? nullptr : findLayer(last, imageIds.front());
            const auto& a = finalAnchor;
            std::array<Vector2, 4> projectedCorners{};
            std::size_t projectedIndex = 0;
            for (const float sx : {-1.f, 1.f}) for (const float sy : {-1.f, 1.f}) {
                Vector3 local(sx * a.halfWidth, sy * a.halfHeight, 0.f);
                local.applyQuaternion(a.orientation);
                projectedCorners[projectedIndex++] = chrononmotion::motion::projectToScreen(
                        a.center.clone().add(local), finalPose, intrinsics);
            }
            float minX = kW, minY = kH, maxX = 0.f, maxY = 0.f;
            for (const auto& corner : projectedCorners) {
                minX = std::min(minX, corner.x); minY = std::min(minY, corner.y);
                maxX = std::max(maxX, corner.x); maxY = std::max(maxY, corner.y);
            }
            check(minX >= 0.f && minY >= 0.f && maxX <= kW && maxY <= kH,
                  "final snapshot projected bounds stay inside the viewport");
            if (recipe == DocumentaryRecipe::PhotoStack) {
                const auto& snapshot = shot.snapshots.back();
                const float captionSize = 144.f * 0.22f;
                const float captionHalfWidth = captionSize * 0.65f *
                    static_cast<float>(snapshot.caption.size()) * 0.5f;
                const chrononmotion::motion::Layer* captionLayer = nullptr;
                for (const auto& layer : scene.motion().layers())
                    if (layer.name == "DocumentaryCaption") captionLayer = &layer;
                const auto captionPose = captionLayer
                    ? captionLayer->sample(static_cast<float>(shot.inFrame + shot.duration) / scene.fps())
                    : chrononmotion::motion::Transform{};
                ShotAnchor captionAnchor;
                captionAnchor.center = captionPose.position;
                captionAnchor.orientation = captionPose.orientation;
                captionAnchor.halfWidth = captionHalfWidth;
                captionAnchor.halfHeight = captionSize * 0.625f;
                const auto captionBounds = projectedBounds(captionAnchor, captionAnchor.center,
                                                           finalPose, intrinsics);
                check(captionLayer && captionBounds.left >= 0.f && captionBounds.top >= 0.f &&
                          captionBounds.right <= kW && captionBounds.bottom <= kH,
                      "photo stack's sampled final caption transform projects fully inside the viewport");
            }
            if (recipe == DocumentaryRecipe::ArchiveCraneReveal) {
                bool everyCardInside = true;
                for (const auto& snapshot : shot.snapshots) {
                    const auto bounds = projectedBounds(snapshot.anchor, snapshot.anchor.center,
                                                        finalPose, intrinsics);
                    everyCardInside = everyCardInside && bounds.left >= 0.f && bounds.top >= 0.f &&
                                      bounds.right <= kW && bounds.bottom <= kH;
                }
                check(everyCardInside,
                      "archive crane final settle keeps every snapshot card inside the viewport");
                const auto titleBounds = projectedBounds(shot.title, shot.title.center,
                                                         finalPose, intrinsics);
                check(titleBounds.left >= 0.f && titleBounds.top >= 0.f &&
                          titleBounds.right <= kW && titleBounds.bottom <= kH,
                      "archive crane final settle keeps the title inside the viewport with every card");
            }
            if (recipe == DocumentaryRecipe::Reveal90) {
                checkNear(openingPose.orientation.angleTo(finalPose.orientation), kPi * 0.5f, 0.08f,
                          "90-degree reveal lands with the declared quarter-turn camera orientation");
            }
            if (recipe == DocumentaryRecipe::PushThroughSnapshot) {
                const int coverFrame = shot.inFrame + shot.titleHoldFrames + shot.transitionFrames;
                const auto coverPose = scene.camera().rig().sample(static_cast<float>(coverFrame) / scene.fps());
                const auto& coverAnchor = shot.snapshots.back().anchor;
                std::array<Vector2, 4> coverCorners{};
                std::size_t coverIndex = 0;
                for (const float sx : {-1.f, 1.f}) for (const float sy : {-1.f, 1.f}) {
                    const Vector3 world(coverAnchor.center.x + sx * coverAnchor.halfWidth,
                                        coverAnchor.center.y + sy * coverAnchor.halfHeight,
                                        coverAnchor.center.z);
                    coverCorners[coverIndex++] = chrononmotion::motion::projectToScreen(
                            world, coverPose, intrinsics);
                }
                float coverMinX = kW, coverMinY = kH, coverMaxX = 0.f, coverMaxY = 0.f;
                for (const auto& corner : coverCorners) {
                    coverMinX = std::min(coverMinX, corner.x); coverMinY = std::min(coverMinY, corner.y);
                    coverMaxX = std::max(coverMaxX, corner.x); coverMaxY = std::max(coverMaxY, corner.y);
                }
                check(coverMinX <= 1.f && coverMinY <= 1.f && coverMaxX >= kW - 1.f &&
                              coverMaxY >= kH - 1.f,
                      "push-through snapshot covers the complete viewport at its transition peak");
                const auto* portal = scene.motion().findLayer("DocumentaryRedPortal");
                const auto coverSubmission = scene.submit(coverFrame);
                const auto* portalState = portal ? findLayer(coverSubmission, portal->id) : nullptr;
                check(portal && portalState && std::fabs(portalState->transform.opacity - 1.f) < 1e-4f,
                      "push-through red portal is opaque at the viewport-cover frame");
                const auto& portalRequest = host.lastShapeRequest();
                check(portalRequest.fillColor == "#C92A32" &&
                              std::fabs(portalRequest.size.x - coverAnchor.halfWidth * 2.f) < 1e-3f &&
                              std::fabs(portalRequest.size.y - coverAnchor.halfHeight * 2.f) < 1e-3f,
                      "push-through creates a native red shape matched to the snapshot card");
                const auto endSubmission = scene.submit(shot.inFrame + shot.duration);
                const auto* portalEnd = portal ? findLayer(endSubmission, portal->id) : nullptr;
                check(portalEnd && portalEnd->transform.opacity < 1e-4f,
                      "red portal clears at the settled snapshot frame");

            }
            if (recipe == DocumentaryRecipe::FocusDrop) {
                Vector3 openingForward(0.f, 0.f, -1.f);
                openingForward.applyQuaternion(openingPose.orientation);
                openingForward.normalize();
                Vector3 finalForward(0.f, 0.f, -1.f);
                finalForward.applyQuaternion(finalPose.orientation);
                finalForward.normalize();
                checkNear(openingPose.position.z + openingForward.z * openingPose.focusDistance,
                          shot.title.center.z, 1e-3f,
                          "focus-drop starts on the title depth plane while keeping both anchors framed");
                checkNear(finalPose.position.z + finalForward.z * finalPose.focusDistance,
                          shot.snapshots.back().anchor.center.z, 1e-3f,
                          "focus-drop ends on the snapshot depth plane");
                check(finalPose.aperture > 0.f && finalPose.aperture <= 1.f,
                      "focus-drop keeps its aperture inside the RenderPlan DOF range");
                bool apertureInRange = true;
                for (int frame = shot.inFrame; frame <= shot.inFrame + shot.duration; ++frame) {
                    const auto pose = scene.camera().rig().sample(static_cast<float>(frame) / scene.fps());
                    apertureInRange = apertureInRange && pose.aperture > 0.f && pose.aperture <= 1.f;
                }
                check(apertureInRange,
                      "focus-drop maintains a RenderPlan-compatible aperture throughout the handoff");
            }
            if (recipe == DocumentaryRecipe::SplitDepth) {
                const auto& finalAnchor = shot.snapshots.back().anchor;
                const Vector3 arc((shot.title.center.x + finalAnchor.center.x) * 0.5f -
                                      shot.cameraDistance * 0.15f,
                                  (shot.title.center.y + finalAnchor.center.y) * 0.5f,
                                  shot.title.center.z + shot.cameraDistance * 1.1f);
                const auto handoffPose = scene.camera().rig().sample(
                    static_cast<float>(shot.inFrame + shot.titleHoldFrames) / scene.fps());
                checkNear(handoffPose.focusDistance, arc.distanceTo(shot.title.center), 1e-3f,
                          "split-depth begins focused at the title target from its arc pose");
                checkNear(finalPose.focusDistance,
                          finalPose.position.distanceTo(finalAnchor.center), 1e-3f,
                          "split-depth settles focus exactly on the final snapshot anchor");
                check(finalPose.aperture > 0.f && finalPose.aperture <= 1.f,
                      "split-depth opens a valid aperture after focusing on the snapshot");
            }
            if (recipe == DocumentaryRecipe::CornerTurn) {
                float maxAngularSpeed = 0.f;
                auto previous = openingPose.orientation;
                for (int frame = shot.inFrame + shot.titleHoldFrames + 1;
                     frame <= shot.inFrame + shot.duration; ++frame) {
                    const auto pose = scene.camera().rig().sample(static_cast<float>(frame) / scene.fps());
                    const float dot = std::clamp(std::fabs(previous.dot(pose.orientation)), 0.f, 1.f);
                    maxAngularSpeed = std::max(maxAngularSpeed, 2.f * std::acos(dot) * scene.fps());
                    previous = pose.orientation;
                }
                check(maxAngularSpeed < 12.f,
                      "corner turn camera orientation stays continuous with bounded angular speed");
                const float epsilonSeconds = 1e-3f;
                for (const int frame : {shot.inFrame + shot.titleHoldFrames +
                                                 (shot.duration - shot.titleHoldFrames) / 3,
                                         shot.inFrame + shot.titleHoldFrames +
                                                 (shot.duration - shot.titleHoldFrames) * 2 / 3}) {
                    const float keyTime = static_cast<float>(frame) / scene.fps();
                    const auto before = scene.camera().rig().positionTrack().velocity(keyTime - epsilonSeconds);
                    const auto after = scene.camera().rig().positionTrack().velocity(keyTime + epsilonSeconds);
                    check((before - after).length() < 60.f,
                          "corner turn camera position has continuous velocity at each path join");
                }
            }
            if (recipe == DocumentaryRecipe::ForegroundPhotoPass) {
                const int handoffFrame = shot.inFrame + shot.titleHoldFrames;
                const auto imageIdsForPass = scene.bindings().layersOf("image/" + shot.snapshots.front().path);
                const auto* movingCard = imageIdsForPass.empty() ? nullptr : scene.motion().findLayer(imageIdsForPass.front());
                bool crossedTitle = false;
                if (movingCard) {
                    for (int frame = handoffFrame; frame <= shot.inFrame + shot.duration; ++frame) {
                        const float seconds = static_cast<float>(frame) / scene.fps();
                        const auto pose = scene.camera().rig().sample(seconds);
                        const auto transform = movingCard->sample(seconds);
                        if (overlaps(projectedBounds(shot.title, shot.title.center, pose, intrinsics),
                                     projectedBounds(shot.snapshots.front().anchor, transform.position,
                                                     pose, intrinsics)) &&
                            chrononmotion::motion::viewDepth(transform.position, pose) <
                                    chrononmotion::motion::viewDepth(shot.title.center, pose) &&
                            transform.opacity > 0.999f) {
                            crossedTitle = true;
                            break;
                        }
                    }
                }
                check(crossedTitle,
                      "foreground snapshot projection crosses and occludes the title during its pass");
                check(finalImage && finalImage->transform.opacity > 0.999f,
                      "foreground pass finishes with its moving photo fully visible");
                const auto* frame = scene.motion().findLayer("DocumentarySnapshotFrame");
                const auto* caption = scene.motion().findLayer("DocumentaryCaption");
                bool attachedLayersFollow = movingCard && frame && caption;
                for (const int frameIndex : {handoffFrame,
                        handoffFrame + (shot.duration - shot.titleHoldFrames) / 3,
                        shot.inFrame + shot.duration}) {
                    if (!movingCard || !frame || !caption) break;
                    const float seconds = static_cast<float>(frameIndex) / scene.fps();
                    const auto imagePosition = movingCard->sample(seconds).position;
                    const auto imageDelta = imagePosition.clone().sub(movingCard->transform.position);
                    for (const auto* attached : {frame, caption}) {
                        const auto attachedDelta = attached->sample(seconds).position.clone()
                                                       .sub(attached->transform.position);
                        attachedLayersFollow = attachedLayersFollow &&
                            imageDelta.distanceTo(attachedDelta) < 1e-3f;
                    }
                }
                check(attachedLayersFollow,
                      "foreground pass moves its frame and caption with the image as one snapshot card");
            }
            check(finalImage && finalImage->transform.opacity > 0.999f,
                  "the final snapshot layer is fully visible");
            const auto firstShot = scene.submit(shot.inFrame);
            const auto* openingImage = imageIds.empty() ? nullptr : findLayer(firstShot, imageIds.front());
            if (recipe == DocumentaryRecipe::FocusDrop) {
                check(openingImage && openingImage->transform.opacity > 0.999f,
                      "focus-drop keeps its blurred snapshot present during the title hold");
            } else {
                check(openingImage && openingImage->transform.opacity < 0.001f,
                      "snapshot cards stay hidden during the opening title hold");
            }
            if (!shot.snapshots.front().caption.empty()) {
                const chrononmotion::motion::Layer* captionLayer =
                    scene.motion().findLayer("DocumentaryCaption");
                if (recipe == DocumentaryRecipe::PhotoStack)
                    for (const auto& layer : scene.motion().layers())
                        if (layer.name == "DocumentaryCaption") captionLayer = &layer;
                const auto* openingCaption = captionLayer ? findLayer(firstShot, captionLayer->id) : nullptr;
                const auto* finalCaption = captionLayer ? findLayer(last, captionLayer->id) : nullptr;
                const bool captionVisibleAtOpen = openingCaption &&
                    openingCaption->transform.opacity > 0.999f;
                check(captionLayer && openingCaption && finalCaption &&
                          captionVisibleAtOpen == (recipe == DocumentaryRecipe::FocusDrop) &&
                          finalCaption->transform.opacity > 0.999f,
                      "snapshot caption shares the card's title-hold and final visibility handoff");
            }

            const int probeFrame = shot.inFrame + 79;
            const auto direct = scene.submit(probeFrame);
            for (int frame = 0; frame <= probeFrame; ++frame) (void)scene.submit(frame);
            const auto sequential = scene.submit(probeFrame);
            check(direct.layers.size() == sequential.layers.size(),
                  "direct and sequential evaluation submit the same layer count");
            for (const auto& layer : direct.layers) {
                const auto* repeated = findLayer(sequential, layer.transform.id);
                check(repeated && chronontemplate_test::sameMatrix(layer.transform.world,
                                                                   repeated->transform.world),
                      "direct frame evaluation matches sequential layer transforms");
                check(repeated && std::fabs(layer.transform.opacity - repeated->transform.opacity) < 1e-6f,
                      "direct frame evaluation matches sequential layer opacity");
            }
            check(direct.camera && sequential.camera &&
                          (direct.camera->position - sequential.camera->position).dot(
                                  direct.camera->position - sequential.camera->position) < 1e-8f &&
                          (direct.camera->target - sequential.camera->target).dot(
                                  direct.camera->target - sequential.camera->target) < 1e-8f &&
                          std::fabs(direct.camera->orientation.dot(sequential.camera->orientation)) > 0.999999f &&
                          std::fabs(direct.camera->focusDistance - sequential.camera->focusDistance) < 1e-6f &&
                          std::fabs(direct.camera->aperture - sequential.camera->aperture) < 1e-6f &&
                          std::fabs(direct.camera->fov - sequential.camera->fov) < 1e-6f,
                  "direct frame evaluation matches sequential camera pose, DOF, and lens");

            if (recipe == DocumentaryRecipe::PhotoStack) {
                const auto* a = scene.motion().findLayer(
                        scene.bindings().layersOf("image/" + shot.snapshots[0].path).front());
                const auto* b = scene.motion().findLayer(
                        scene.bindings().layersOf("image/" + shot.snapshots[1].path).front());
                const auto* c = scene.motion().findLayer(
                        scene.bindings().layersOf("image/" + shot.snapshots[2].path).front());
                check(a && b && c && a->transform.position.z > b->transform.position.z &&
                              b->transform.position.z > c->transform.position.z &&
                              a->transform.position.z - b->transform.position.z >= 1.f &&
                              b->transform.position.z - c->transform.position.z >= 1.f,
                      "photo stack card planes keep their ordered depth separation");
            }

            const auto settled = scene.camera().rig().sampleDerivative((endTime + 1.f / scene.fps()));
            check(settled.linearVelocity.dot(settled.linearVelocity) < 1e-6f,
                  "camera velocity settles to zero after the transition window");
        }
    }

    void invalidRecipeInputsFailClosed() {
        section("invalid documentary authoring is rejected");
        FakeContentHost host;
        bool rejected = false;
        try {
            TemplateScene scene("documentary_invalid", 30.f, host, kW, kH);
            DocumentaryShot shot = makeShot(DocumentaryRecipe::FilmstripHandoff);
            shot.snapshots.resize(2);
            addDocumentarySnapshot(scene, TextSpec{.text = "THE STORY"}, shot);
        } catch (const std::invalid_argument&) { rejected = true; }
        check(rejected, "filmstrip rejects fewer than three snapshots");

        rejected = false;
        try {
            TemplateScene scene("documentary_invalid_style", 30.f, host, kW, kH);
            DocumentaryShot shot = makeShot(DocumentaryRecipe::SnapDown);
            shot.style = static_cast<SnapshotStyle>(255);
            addDocumentarySnapshot(scene, TextSpec{.text = "THE STORY"}, shot);
        } catch (const std::invalid_argument&) { rejected = true; }
        check(rejected, "unknown snapshot styles fail explicitly");

        rejected = false;
        try {
            TemplateScene scene("documentary_invalid_filmstrip", 30.f, host, kW, kH);
            DocumentaryShot shot = makeShot(DocumentaryRecipe::FilmstripHandoff);
            shot.snapshots[2].anchor.center.x += 50.f;
            addDocumentarySnapshot(scene, TextSpec{.text = "THE STORY"}, shot);
        } catch (const std::invalid_argument&) { rejected = true; }
        check(rejected, "filmstrip rejects accidental inconsistent card spacing");

        rejected = false;
        try {
            TemplateScene scene("documentary_invalid_stack", 30.f, host, kW, kH);
            DocumentaryShot shot = makeShot(DocumentaryRecipe::PhotoStack);
            shot.snapshots[2].anchor.center.z = shot.snapshots[1].anchor.center.z;
            addDocumentarySnapshot(scene, TextSpec{.text = "THE STORY"}, shot);
        } catch (const std::invalid_argument&) { rejected = true; }
        check(rejected, "photo stack rejects cards without ordered depth separation");
    }

    void snapshotStylesUseTheNormalImageHost() {
        section("snapshot frame style uses the native shape and image paths");
        struct ExpectedStyle { SnapshotStyle style; float width; float saturation; float grain; std::uint32_t seed; };
        const ExpectedStyle styles[] = {
            {SnapshotStyle::Clean, 3.f, 1.f, 0.f, 0},
            {SnapshotStyle::Archive, 8.f, 0.78f, 0.008f, 1986},
            {SnapshotStyle::Polaroid, 18.f, 1.f, 0.f, 0},
            {SnapshotStyle::Filmstrip, 14.f, 1.f, 0.012f, 35},
            {SnapshotStyle::Evidence, 5.f, 1.f, 0.f, 0},
            {SnapshotStyle::Newspaper, 12.f, 0.f, 0.01f, 1917},
            {SnapshotStyle::BlackAndWhiteDocumentary, 6.f, 0.f, 0.008f, 1960}};
        for (const auto& expected : styles) {
            FakeContentHost host;
            TemplateScene scene("documentary_snapshot_style", 30.f, host, kW, kH);
            DocumentaryShot shot = makeShot(DocumentaryRecipe::SnapDown);
            shot.snapshots.resize(1);
            shot.style = expected.style;
            addDocumentarySnapshot(scene, TextSpec{.text = "THE STORY"}, shot);
            check(host.lastImageRequest().path == "archive_a.jpg",
                  "snapshot style creates content through the existing image host");
            checkNear(host.lastImageRequest().borderWidth, 0.f, 1e-6f,
                      "snapshot border is authored as a separate native frame layer");
            check(host.lastShapeRequest().name == "DocumentarySnapshotFrame" &&
                      host.lastShapeRequest().fillColor ==
                          (expected.style == SnapshotStyle::Evidence ? "#C92A32" :
                           expected.style == SnapshotStyle::Clean ? "#F2F0EA" :
                           expected.style == SnapshotStyle::Polaroid ? "#F8F4E8" :
                           expected.style == SnapshotStyle::Filmstrip ? "#151515" :
                           expected.style == SnapshotStyle::Newspaper ? "#D8D0BE" : "#E8E2D5"),
                  "snapshot frame style is a native shape behind the image");
            checkNear(host.lastShapeRequest().cornerRadius, expected.width, 1e-6f,
                      "snapshot frame radius includes the visible frame width");
            checkNear(host.lastImageRequest().saturation, expected.saturation, 1e-6f,
                      "snapshot color grade is passed through the normal image request");
            checkNear(host.lastImageRequest().grain, expected.grain, 1e-6f,
                      "snapshot grain is passed through the normal image request");
            checkNear(host.lastImageRequest().contrast,
                      expected.style == SnapshotStyle::Newspaper ? 1.32f :
                      expected.style == SnapshotStyle::BlackAndWhiteDocumentary ? 1.16f :
                      expected.style == SnapshotStyle::Archive || expected.style == SnapshotStyle::Filmstrip ? 1.08f : 1.f,
                      1e-6f, "snapshot contrast is passed through the normal image request");
            check(host.lastImageRequest().grainSeed == expected.seed,
                  "snapshot grain uses a stable style seed");
        }
    }

    void snapshotFitModesUseChrononImagePlacement() {
        section("snapshot fit, fill, and crop use the existing Chronon image placement contract");
        for (const auto fit : {SnapshotFit::Fit, SnapshotFit::Fill, SnapshotFit::Crop}) {
            FakeContentHost host;
            host.imageNaturalSize = Vector2(640.f, 480.f);
            TemplateScene scene("documentary_snapshot_fit", 30.f, host, kW, kH);
            DocumentaryShot shot = makeShot(DocumentaryRecipe::SnapDown);
            shot.snapshots.resize(1);
            shot.snapshots.front().fit = fit;
            if (fit == SnapshotFit::Crop) {
                shot.snapshots.front().crop = {true, Vector2(0.1f, 0.2f), Vector2(0.8f, 0.7f)};
            }
            addDocumentarySnapshot(scene, TextSpec{.text = "THE STORY"}, shot);
            const auto& request = host.lastImageRequest();
            check(request.fit == (fit == SnapshotFit::Fit ? ImageFitMode::Contain : ImageFitMode::Cover),
                  "snapshot fit mode maps to Chronon's existing contain or cover path");
            checkNear(request.targetSize.x, 600.f, 1e-6f, "snapshot target width is forwarded");
            checkNear(request.targetSize.y, 336.f, 1e-6f, "snapshot target height is forwarded");
            check(request.crop.enabled == (fit == SnapshotFit::Crop),
                  "explicit crop is sent only for the crop recipe");
            if (fit == SnapshotFit::Crop) {
                checkNear(request.crop.origin.x, 0.1f, 1e-6f, "crop origin X is preserved");
                checkNear(request.crop.origin.y, 0.2f, 1e-6f, "crop origin Y is preserved");
                checkNear(request.crop.size.x, 0.8f, 1e-6f, "crop width is preserved");
                checkNear(request.crop.size.y, 0.7f, 1e-6f, "crop height is preserved");
            }
            const auto ids = scene.bindings().layersOf("image/archive_a.jpg");
            const auto* card = ids.empty() ? nullptr : scene.motion().findLayer(ids.front());
            const float sourceAspect = 640.f / 480.f;
            const float expectedProjectionCorrection = fit == SnapshotFit::Fit
                ? (kW / kH) / sourceAspect : 1.f;
            check(card && std::fabs(card->transform.scale.y / card->transform.scale.x -
                                    expectedProjectionCorrection) < 1e-5f,
                  "snapshot Fit compensates camera projection so source pixels stay undistorted");
            const auto* frame = scene.motion().findLayer("DocumentarySnapshotFrame");
            const float fittedWidth = fit == SnapshotFit::Fit
                ? 640.f * std::min(600.f / 640.f, 336.f / 480.f)
                : 600.f;
            check(frame && std::fabs(frame->content.metrics.naturalSize.x -
                                      (fittedWidth + 16.f)) < 1e-3f,
                  "archive frame follows fitted image bounds plus its border padding");
            if (frame && card) {
                const int titleHoldFrame = shot.inFrame + shot.titleHoldFrames - 1;
                const int revealFrame = shot.inFrame + shot.titleHoldFrames + shot.transitionFrames;
                const auto titleHold = scene.submit(titleHoldFrame);
                const auto reveal = scene.submit(revealFrame);
                const auto* frameHold = findLayer(titleHold, frame->id);
                const auto* frameReveal = findLayer(reveal, frame->id);
                check(frameHold && frameHold->transform.opacity < 1e-4f,
                      "snapshot frame stays hidden during the title hold");
                check(frameReveal && frameReveal->transform.opacity > 0.99f,
                      "snapshot frame is visible when the photo reveal settles");
            }
        }
    }
}

int main() {
    allRecipeIdsAreStable();
    titleAndCameraContracts();
    invalidRecipeInputsFailClosed();
    snapshotStylesUseTheNormalImageHost();
    snapshotFitModesUseChrononImagePlacement();
    return chrononmotion_test::report();
}
