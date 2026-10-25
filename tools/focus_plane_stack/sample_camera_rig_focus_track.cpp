// Sample the real ChrononMotion CameraRig track used by focus_plane_stack_v1.
#include "chrononmotion/motion/CameraRig.hpp"

#include <iomanip>
#include <iostream>

int main() {
    using namespace chrononmotion;
    using namespace chrononmotion::motion;

    constexpr int kSamples = 10;
    constexpr float kFovDeg = 48.0f;
    constexpr float kFocalLengthMm = 22.7233697f;
    constexpr float kSensorWidthMm = 36.0f;
    constexpr float kFStop = 0.7f;
    constexpr float kMaxBlurPx = 24.0f;

    CameraRig rig{1, kFovDeg, 854.0f / 480.0f, 10.0f, 3000.0f};
    rig.setPosition(Vector3{0.0f, 0.0f, 0.0f})
        .setTarget(Vector3{0.0f, 0.0f, -1.0f})
        .setFov(kFovDeg)
        .setFocalLength(kFocalLengthMm)
        .setSensorWidth(kSensorWidthMm)
        .setFStop(kFStop)
        .setMaxBlur(kMaxBlurPx);

    auto& focus = rig.focusDistanceTrack();
    for (int frame = 0; frame < kSamples; ++frame) {
        focus.add(static_cast<float>(frame), 450.0f + 200.0f * frame,
                  Easing::linear());
    }

    std::cout << "frame,time_s,focus_distance,fov_deg,focal_length_mm,"
                 "sensor_width_mm,f_stop,max_blur_px,position_x,position_y,position_z\n";
    std::cout << std::fixed << std::setprecision(6);
    for (int frame = 0; frame < kSamples; ++frame) {
        const CameraPose pose = rig.sample(static_cast<float>(frame));
        std::cout << frame << ',' << frame << ',' << pose.focusDistance << ','
                  << pose.fov << ',' << pose.focalLength << ',' << pose.sensorWidth
                  << ',' << pose.fStop << ',' << pose.maxBlur << ','
                  << pose.position.x << ',' << pose.position.y << ','
                  << pose.position.z << '\n';
    }
}
