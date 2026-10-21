#pragma once

#include <chrononmotion/math/Vector3.hpp>
#include <chrononmotion/motion/RenderPlanLowering.hpp>

#include <nlohmann/json.hpp>

#include <algorithm>
#include <array>
#include <cmath>
#include <stdexcept>
#include <string>
#include <string_view>
#include <vector>

namespace chronontemplate::camera_roll {

inline chrononmotion::motion::Easing cameraEasing(std::string_view name) {
    using chrononmotion::motion::Easing;
    if (name == "linear") return Easing::linear();
    if (name == "in_cubic") return Easing::cubicBezier(1.f / 3.f, 0.f, 2.f / 3.f, 0.f);
    if (name == "out_cubic") return Easing::cubicBezier(1.f / 3.f, 1.f, 2.f / 3.f, 1.f);
    if (name == "in_out_cubic") return Easing::inOutCubic();
    throw std::invalid_argument("unsupported CM3D camera easing: " + std::string(name));
}

template <class Json>
inline nlohmann::json bakeResolvedCameraSamples(
    const Json& baseCamera, const Json& channels, float fps, std::size_t frameCount) {
    using namespace chrononmotion;
    using namespace chrononmotion::motion;
    if (!baseCamera.is_object() || !channels.is_array() || channels.size() > 16 ||
        !std::isfinite(fps) || fps <= 0.f || frameCount == 0 || frameCount > 65536)
        throw std::invalid_argument("invalid resolved camera sample request");

    const auto vector3 = [&](std::string_view key) {
        const auto& value = baseCamera.at(std::string(key));
        if (!value.is_array() || value.size() != 3)
            throw std::invalid_argument("camera " + std::string(key) + " must have three components");
        for (const auto& component : value)
            if (!component.is_number() || !std::isfinite(component.template get<float>()))
                throw std::invalid_argument("camera vector components must be finite numbers");
        return Vector3(value[0].template get<float>(), value[1].template get<float>(), value[2].template get<float>());
    };
    const auto number = [&](std::string_view key, float fallback) {
        const auto it = baseCamera.find(std::string(key));
        if (it == baseCamera.end()) return fallback;
        if (!it->is_number() || !std::isfinite(it->template get<float>()))
            throw std::invalid_argument("camera " + std::string(key) + " must be finite");
        return it->template get<float>();
    };

    const Vector3 planPosition = vector3("position");
    const Vector3 planRotation = vector3("rotation_deg");
    const float nearPlane = number("near", 0.1f);
    const float farPlane = number("far", 10000.f);
    const float fov = number("fov_deg", 50.f);
    const float zoom = number("zoom", 1.f);
    if (zoom != 1.f)
        throw std::invalid_argument("camera zoom must be resolved into FOV before CM3D sampling");

    // RenderPlan mirrors Motion's Z axis. Conjugating the camera rotation at
    // this bridge negates the X/Y Euler components and preserves Z.
    constexpr float kDegToRad = 0.01745329251994329577f;
    const Vector3 baseRotation(-planRotation.x * kDegToRad,
                               -planRotation.y * kDegToRad,
                                planRotation.z * kDegToRad);
    chrononmotion::motion::CameraPose basePose;
    basePose.position = Vector3(planPosition.x, planPosition.y, -planPosition.z);
    basePose.fov = fov;
    basePose.sensorWidth = number("sensor_width_mm", 36.f);
    if (const auto shift = baseCamera.find("lens_shift"); shift != baseCamera.end()) {
        if (!shift->is_array() || shift->size() != 2)
            throw std::invalid_argument("camera lens_shift must have two components");
        basePose.lensShift.set(shift->at(0).template get<float>(), shift->at(1).template get<float>());
    }
    if (const auto focalLength = baseCamera.find("focal_length_mm"); focalLength != baseCamera.end())
        basePose.focalLength = focalLength->template get<float>();
    if (const auto dof = baseCamera.find("dof"); dof != baseCamera.end() && dof->is_object()) {
        if (dof->value("enabled", false))
            basePose.legacyDefocusStrength = dof->value("aperture", 0.f);
        if (dof->contains("focus_distance"))
            basePose.focusDistance = dof->at("focus_distance").template get<float>();
        if (dof->contains("max_blur")) basePose.maxBlur = dof->at("max_blur").template get<float>();
        if (dof->contains("f_stop")) basePose.fStop = dof->at("f_stop").template get<float>();
        if (dof->contains("iris_blades")) basePose.irisBlades = dof->at("iris_blades").template get<int>();
        if (dof->contains("highlight_gain"))
            basePose.highlightGain = dof->at("highlight_gain").template get<float>();
    }

    std::array<Track<float>, 7> scalarTracks;
    std::array<bool, 7> hasTrack{};
    constexpr std::array<std::string_view, 7> names{
        "position_x", "position_y", "position_z", "rotation_x", "rotation_y", "rotation_z", "fov"};
    for (const auto& channel : channels) {
        if (!channel.is_object() || !channel.contains("channel") || !channel.contains("keyframes") ||
            !channel.at("keyframes").is_array() || channel.at("keyframes").empty())
            throw std::invalid_argument("camera channel requires a name and non-empty keyframes");
        const auto name = channel.at("channel").template get<std::string>();
        const auto found = std::find(names.begin(), names.end(), name);
        if (found == names.end()) throw std::invalid_argument("unsupported camera channel: " + name);
        const std::size_t index = static_cast<std::size_t>(found - names.begin());
        if (hasTrack[index]) throw std::invalid_argument("duplicate camera channel: " + name);
        hasTrack[index] = true;
        const Easing easing = cameraEasing(channel.value("easing", "linear"));
        float previousFrame = -1.f;
        for (const auto& key : channel.at("keyframes")) {
            if (!key.is_object() || !key.contains("frame") || !key.contains("value") ||
                !key.at("frame").is_number() || !key.at("value").is_number())
                throw std::invalid_argument("camera keyframe requires numeric frame and value");
            const float frame = key.at("frame").template get<float>();
            const float value = key.at("value").template get<float>();
            if (!std::isfinite(frame) || !std::isfinite(value) || frame < 0.f || frame <= previousFrame)
                throw std::invalid_argument("camera keyframes must be finite and strictly increasing");
            previousFrame = frame;
            float resolved = value;
            if (index == 2) resolved = -resolved;
            else if (index == 3 || index == 4) resolved = -resolved * kDegToRad;
            else if (index == 5) resolved *= kDegToRad;
            scalarTracks[index].add(frame / fps, resolved, easing);
        }
    }

    const Vector3 basePosition(planPosition.x, planPosition.y, -planPosition.z);
    std::vector<chronon3d::render_plan::CameraSamplePlan> samples;
    samples.reserve(frameCount);
    for (std::size_t frame = 0; frame < frameCount; ++frame) {
        const float seconds = static_cast<float>(frame) / fps;
        Vector3 position = basePosition;
        Vector3 rotation = baseRotation;
        float sampleFov = fov;
        if (hasTrack[0]) position.x = scalarTracks[0].sample(seconds);
        if (hasTrack[1]) position.y = scalarTracks[1].sample(seconds);
        if (hasTrack[2]) position.z = scalarTracks[2].sample(seconds);
        if (hasTrack[3]) rotation.x = scalarTracks[3].sample(seconds);
        if (hasTrack[4]) rotation.y = scalarTracks[4].sample(seconds);
        if (hasTrack[5]) rotation.z = scalarTracks[5].sample(seconds);
        if (hasTrack[6]) sampleFov = scalarTracks[6].sample(seconds);
        auto pose = basePose;
        pose.position = position;
        pose.orientation.setFromEuler(chrononmotion::Euler(rotation.x, rotation.y, rotation.z));
        pose.fov = sampleFov;
        samples.push_back({static_cast<double>(frame), lowerCameraPose(pose, nearPlane, farPlane)});
    }

    return cameraSamplesToJson(samples);
}

template <class Json>
inline void attachResolvedCameraSamples(Json& plan, const Json& baseCamera,
                                        const Json& channels, float fps,
                                        std::size_t frameCount) {
    const auto samples = bakeResolvedCameraSamples(baseCamera, channels, fps, frameCount);
    if (samples.empty()) throw std::logic_error("CM3D camera baker returned no samples");
    plan["camera"] = samples.front().at("camera");
    plan["camera_samples"] = samples;
}

} // namespace chronontemplate::camera_roll
