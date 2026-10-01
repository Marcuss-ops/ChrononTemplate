#include "chronontemplate/TitleCameraPack.hpp"

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
    ContentHandle createText(const TextRequest& r) override {
        ContentHandle h; h.id = "text/" + r.text; h.kind = ContentKind::Text;
        h.metrics.naturalSize = Vector2(1000.f, 180.f); h.metrics.anchor = Vector2(.5f,.5f);
        h.metrics.fingerprint = "title-camera-render-v1"; return h;
    }
    ContentHandle createImage(const ImageRequest&) override { return {}; }
    ContentHandle createVideo(const VideoRequest&) override { return {}; }
    std::string currentFingerprint(const ContentId&) const override { return "title-camera-render-v1"; }
};
Vector3 euler(const Quaternion& q) {
    constexpr float radToDeg = 57.29577951308232f;
    // RenderPlan's camera looks along +Z, while CameraRig poses look along -Z.
    // Lower the inverse camera orientation before extracting XYZ Euler angles.
    Quaternion camera = q;
    camera.invert();
    const float x = std::atan2(2.f*(camera.w*camera.x-camera.y*camera.z), 1.f-2.f*(camera.x*camera.x+camera.y*camera.y));
    const float s = std::clamp(2.f*(camera.w*camera.y+camera.z*camera.x), -1.f, 1.f);
    const float y = std::asin(s);
    const float z = std::atan2(2.f*(camera.w*camera.z-camera.x*camera.y), 1.f-2.f*(camera.y*camera.y+camera.z*camera.z));
    return Vector3(x*radToDeg,y*radToDeg,z*radToDeg);
}
}

int main() {
    constexpr int duration=135, fps=30;
    Host host;
    for (int m=0; m<20; ++m) {
        const auto move=static_cast<TitleCameraMove>(m);
        TemplateScene scene("title_camera_render", static_cast<float>(fps), host, 1920.f,1080.f);
        auto& title=scene.text({.text="THE ART OF SIMPLICITY",.font="Inter-Bold.ttf",.fontSize=180.f});
        title.position(960.f,540.f);
        applyTitleCameraShot(scene,move,TitleCameraShot{.anchor={.center=Vector3(960.f,540.f,0.f),.halfWidth=900.f,.halfHeight=120.f},.framing=TitleFraming::Medium,.intensity=TitleCameraIntensity::Editorial,.inFrame=0,.duration=duration});
        std::cout << titleCameraMoveId(move) << '\n';
        for (int f=0; f<=duration; ++f) {
            const auto p=scene.camera().rig().sample(static_cast<float>(f)/fps);
            const Vector3 r=euler(p.orientation);
            std::cout << f << ' ' << p.position.x << ' ' << p.position.y << ' ' << p.position.z << ' '
                      << r.x << ' ' << r.y << ' ' << r.z << ' ' << p.fov << '\n';
        }
    }
}
