#include "chronontemplate/camera_roll/ResolvedCameraSamples.hpp"

#include <iostream>
#include <nlohmann/json.hpp>
#include <stdexcept>

int main() {
    try {
        const auto request = nlohmann::json::parse(std::cin);
        const auto samples = chronontemplate::camera_roll::bakeResolvedCameraSamples(
            request.at("camera"), request.at("channels"), request.at("fps").get<float>(),
            request.at("frame_count").get<std::size_t>());
        std::cout << samples.dump() << '\n';
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "resolve_camera_samples: " << error.what() << '\n';
        return 1;
    }
}
