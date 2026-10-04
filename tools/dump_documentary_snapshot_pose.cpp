#include "chronontemplate/DocumentarySnapshotPack.hpp"

#include <algorithm>
#include <cmath>
#include <iostream>
#include <string>

using namespace chronontemplate;
using namespace chrononmotion;
using namespace chrononmotion::motion;

namespace {
    class Host final : public ContentHost {
    public:
        ContentHandle createText(const TextRequest& request) override {
            return make("text/" + request.text, ContentKind::Text,
                        Vector2(request.fontSize * request.text.size() * 0.5f, request.fontSize * 1.2f));
        }
        ContentHandle createImage(const ImageRequest& request) override {
            return make("image/" + request.path, ContentKind::Image, Vector2(640.f, 360.f));
        }
        ContentHandle createShape(const ShapeRequest& request) override {
            return make("shape/" + request.name, ContentKind::Image, request.size);
        }
        ContentHandle createVideo(const VideoRequest&) override { return {}; }
        std::string currentFingerprint(const ContentId&) const override { return "documentary-snapshot-v1"; }

    private:
        ContentHandle make(std::string id, ContentKind kind, Vector2 size) {
            ContentHandle handle;
            handle.id = std::move(id);
            handle.kind = kind;
            handle.metrics.naturalSize = size;
            handle.metrics.anchor = Vector2(0.5f, 0.5f);
            handle.metrics.fingerprint = "documentary-snapshot-v1";
            return handle;
        }
    };

    Vector3 renderEuler(const Quaternion& source) {
        constexpr float radToDeg = 57.29577951308232f;
        Quaternion q = source;
        q.invert();
        const float x = std::atan2(2.f * (q.w*q.x - q.y*q.z), 1.f - 2.f * (q.x*q.x + q.y*q.y));
        const float s = std::clamp(2.f * (q.w*q.y + q.z*q.x), -1.f, 1.f);
        const float y = std::asin(s);
        const float z = std::atan2(2.f * (q.w*q.z - q.x*q.y), 1.f - 2.f * (q.y*q.y + q.z*q.z));
        return Vector3(x * radToDeg, y * radToDeg, z * radToDeg);
    }
}

int main(int argc, char** argv) {
    constexpr int fps = 30;
    constexpr int endFrame = 120;
    Host host;
    TemplateScene scene("documentary_snapshot_canary", static_cast<float>(fps), host, 1920.f, 1080.f);
    DocumentaryShot shot;
    shot.title.center = Vector3(960.f, 300.f, 0.f);
    shot.title.halfWidth = 820.f;
    shot.title.halfHeight = 120.f;
    shot.snapshots = {{"RenderingGen/testdata/golden/gerard_butler.jpg",
                       {Vector3(960.f, 960.f, -80.f), 620.f, 350.f}, {}}};
    const std::string recipe = argc > 1 ? argv[1] : "doc_title_snap_down";
    if (recipe == "doc_title_push_through_snapshot")
        shot.recipe = DocumentaryRecipe::PushThroughSnapshot;
    else if (recipe == "doc_title_focus_drop")
        shot.recipe = DocumentaryRecipe::FocusDrop;
    else
        shot.recipe = DocumentaryRecipe::SnapDown;
    shot.style = SnapshotStyle::Archive;
    shot.inFrame = 0;
    shot.duration = endFrame;
    shot.titleHoldFrames = 45;
    shot.transitionFrames = 8;
    addDocumentarySnapshot(scene,
                           TextSpec{.text = "THE STORY OF ROME", .font = "Playfair Display Italic",
                                    .fontSize = 138.f, .color = "#F1EBDD", .name = "DocumentaryTitle"},
                           shot);

    for (int frame = 0; frame <= endFrame; ++frame) {
        const CameraPose pose = scene.camera().rig().sample(static_cast<float>(frame) / fps);
        const Vector3 angles = renderEuler(pose.orientation);
        std::cout << frame << ' ' << pose.position.x << ' ' << pose.position.y << ' ' << pose.position.z
                  << ' ' << angles.x << ' ' << angles.y << ' ' << angles.z << ' ' << pose.fov
                  << ' ' << pose.focusDistance << ' ' << std::max(0.001f, -pose.target.z)
                  << ' ' << pose.aperture << '\n';
    }
}
