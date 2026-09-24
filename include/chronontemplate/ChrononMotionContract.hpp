// ChrononTemplate — adapter for the shared Chronon/Motion3D C contract.
//
// FrameSubmission is the C++ orchestration result. This adapter is the only
// conversion needed before calling chronon_render_frame_with_layers(): text,
// images and pixels remain owned by Chronon, while the final matrices and
// opacity come from Motion3D.
#ifndef CHRONONTEMPLATE_CHRONON_MOTION_CONTRACT_HPP
#define CHRONONTEMPLATE_CHRONON_MOTION_CONTRACT_HPP

#include <chronon/abi.h>
#include "chronontemplate/FrameSubmission.hpp"

#include <vector>

namespace chronontemplate {

    /// Convert a resolved frame into the ABI records consumed by Chronon.
    /// Content layers without a numeric Chronon identity are rejected rather
    /// than assigned a hash or silently rendered with the wrong asset.
    [[nodiscard]] std::vector<chronon_layer_state> makeChrononLayerStates(
            const FrameSubmission& submission);

}// namespace chronontemplate

#endif//CHRONONTEMPLATE_CHRONON_MOTION_CONTRACT_HPP
