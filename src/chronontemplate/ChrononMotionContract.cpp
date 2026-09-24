#include "chronontemplate/ChrononMotionContract.hpp"

#include <algorithm>
#include <cmath>
#include <stdexcept>

namespace chronontemplate {

    std::vector<chronon_layer_state> makeChrononLayerStates(
            const FrameSubmission& submission) {
        std::vector<chronon_layer_state> states;
        states.reserve(submission.layers.size());

        for (const BoundLayer& layer : submission.layers) {
            if (!layer.draws()) continue;
            if (layer.transform.id == 0 || layer.wireContentId == 0) {
                throw std::invalid_argument(
                        "makeChrononLayerStates: every content layer needs non-zero ABI identities");
            }

            chronon_layer_state state{};
            state.struct_size = sizeof(state);
            state.visible = layer.transform.visible ? 1u : 0u;
            state.layer = static_cast<chronon_layer_id>(layer.transform.id);
            state.content = static_cast<chronon_content_id>(layer.wireContentId);
            state.opacity = std::isfinite(layer.transform.opacity)
                                    ? std::clamp(layer.transform.opacity, 0.f, 1.f)
                                    : 0.f;
            // Motion3D's Matrix4 stores column-major elements; the frozen C ABI
            // contract stores row-major matrices with column vectors. Transpose
            // during packing so Chronon3D reconstructs the same clip transform.
            for (unsigned int row = 0; row < 4; ++row) {
                for (unsigned int col = 0; col < 4; ++col) {
                    const float value = layer.clipFromLocal[col * 4 + row];
                    if (!std::isfinite(value)) {
                        throw std::invalid_argument(
                                "makeChrononLayerStates: non-finite clip_from_local matrix");
                    }
                    state.clip_from_local[row * 4 + col] = value;
                }
            }
            state.depth = -1.f;
            states.push_back(state);
        }
        return states;
    }

}// namespace chronontemplate
