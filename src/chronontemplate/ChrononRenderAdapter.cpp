#include "chronontemplate/ChrononRenderAdapter.hpp"

#include "chronontemplate/ChrononMotionContract.hpp"

#include <stdexcept>

namespace chronontemplate {

    ChrononRenderAdapter::ChrononRenderAdapter(chronon_engine* engine,
                                               const chronon_plan* plan)
            : m_engine(engine), m_plan(plan) {
        if (m_engine == nullptr || m_plan == nullptr) {
            throw std::invalid_argument(
                    "ChrononRenderAdapter: engine and plan handles are required");
        }
    }

    chronon_status ChrononRenderAdapter::renderFrame(
            const FrameSubmission& submission,
            chronon_frame_buffer* outBuffer) const {
        if (outBuffer == nullptr) {
            return CHRONON_ERROR_INVALID_ARGUMENT;
        }
        *outBuffer = chronon_frame_buffer{};

        const std::vector<chronon_layer_state> states =
                makeChrononLayerStates(submission);
        return chronon_render_frame_with_layers(
                m_engine, m_plan, static_cast<uint64_t>(submission.frame),
                states.empty() ? nullptr : states.data(), states.size(), outBuffer);
    }

    void ChrononRenderAdapter::releaseFrame(chronon_frame_buffer* buffer) const noexcept {
        if (buffer == nullptr) return;
        chronon_buffer_free(m_engine, buffer);
    }

}// namespace chronontemplate
