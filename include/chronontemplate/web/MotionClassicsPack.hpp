#pragma once

#include <array>
#include <string>

#include <nlohmann/json.hpp>

namespace chronontemplate::web {

struct MotionClassicSpec {
    int index = 0;
    const char* slug = "";
    const char* title = "";
    const char* description = "";
    int durationFrames = 90;
    int fps = 30;

    std::string planName() const;
    std::string videoName() const;
};

std::array<MotionClassicSpec, 12> motionClassicSpecs();

nlohmann::json buildMotionClassicPlan(const MotionClassicSpec& spec);

}  // namespace chronontemplate::web
