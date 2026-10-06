// ChrononTemplate — the neutral frame the renderer consumes.
//
// The bridge's whole output: per layer, the matrix the motion side produced and
// the content it draws, already resolved. No engine type from the content side
// and no authoring type from the motion side survives into this struct, so a
// renderer can read it without knowing either engine's authoring model.

#ifndef CHRONONTEMPLATE_FRAME_SUBMISSION_HPP
#define CHRONONTEMPLATE_FRAME_SUBMISSION_HPP

#include "chrononmotion/motion/CompiledScene.hpp"
#include "chrononmotion/motion/Content.hpp"
#include "chrononmotion/motion/Lighting.hpp"

#include <cstdint>
#include <memory>
#include <string>
#include <vector>

namespace chronontemplate {

    /// One layer ready to draw: where the motion side put it, what the content
    /// side holds for it, and whether those two still agree.
    struct BoundLayer {
        chrononmotion::motion::CompiledTransform transform{};
        /// Empty for a null/controller layer: it moves children and draws nothing.
        chrononmotion::motion::ContentRef content{};
        /// Numeric Chronon identity when the host is ABI-connected.
        std::uint64_t wireContentId{0};
        /// Final projection * view * world transform for the ABI consumer.
        chrononmotion::Matrix4 clipFromLocal{};
        /// Verdict on the carried measurement against the host's current digest.
        /// `Unknown` when the ref was hand-authored or no host was supplied.
        chrononmotion::motion::MeasurementState measurement{
                chrononmotion::motion::MeasurementState::Unknown};

        [[nodiscard]] bool draws() const { return !content.empty(); }
    };

    struct FrameSubmission {
        std::string sceneName{};
        int frame{0};
        float fps{24.f};
        std::vector<BoundLayer> layers{};
        std::vector<chrononmotion::motion::LightState> lights{};
        /// Sampled from the camera rig: `MotionScene::compile()` deliberately does
        /// not own a camera, so the bridge samples the rig for the same frame.
        std::shared_ptr<const chrononmotion::motion::CameraPose> camera{};

        [[nodiscard]] std::size_t layerCount() const { return layers.size(); }
    };

}// namespace chronontemplate

#endif//CHRONONTEMPLATE_FRAME_SUBMISSION_HPP
