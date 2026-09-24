// ChrononTemplate — the motion half of the contract zone.
//
// <chronon/abi.h> is the cross-repo contract: the motion side decides WHERE and
// WHEN, the content side decides WHAT, and neither sees the other's authoring
// types. Chronon3d owns the content half of this conversion
// (chronon3d/motion/contract_bridge.hpp) because it owns the content side;
// this header is the motion half, and it is the ONLY place in this module that
// mentions <chronon/abi.h>. Nothing from ChrononMotion's authoring model
// crosses here — a `FrameSubmission` becomes contract PODs and nothing else.
//
// The dependency stays one way: this module includes the engine's public
// contract header and the engine never links this module.
//
// ── The depth convention (read before changing anything here) ───────────────
// The ABI's `chronon_layer_state.clip_from_local` is the full
// projection · view · world · local product in the *content* side's NDC, which
// is GLM's `GLM_FORCE_DEPTH_ZERO_TO_ONE`: NDC z in 0..1 (Chronon3d defines it in
// chronon3d/math/glm_types.hpp, and its `depth_from_clip` clamps into [0, 1]).
//
// ChrononMotion is a three.js port and does not define that macro, so its
// `PerspectiveCamera::updateProjectionMatrix` writes NDC z in -1..1. Handing
// that matrix over unconverted is a silent defect rather than a crash: every
// layer in front of the camera gets a negative NDC z, `depth_from_clip` clamps
// it to 0, and the whole frame renders with sorting that is wrong in a way no
// assertion notices.
//
// So the remap is done here, once, on the side that produced the matrix:
// `zeroToOneProjection(projection)` returns the same projection with z in 0..1.

#ifndef CHRONONTEMPLATE_CONTRACT_SUBMISSION_HPP
#define CHRONONTEMPLATE_CONTRACT_SUBMISSION_HPP

#include "chronontemplate/FrameSubmission.hpp"

#include "chrononmotion/math/Matrix4.hpp"

#include <cstdint>
#include <functional>
#include <vector>

#if defined(__has_include)
#  if __has_include(<chronon/abi.h>)
#    include <chronon/abi.h>
#    define CHRONONTEMPLATE_HAS_CONTRACT_ABI 1
#  endif
#endif

#ifndef CHRONONTEMPLATE_HAS_CONTRACT_ABI
#  define CHRONONTEMPLATE_HAS_CONTRACT_ABI 0
#endif

#if CHRONONTEMPLATE_HAS_CONTRACT_ABI

namespace chronontemplate::contract {

    /// The contract-zone version this half is written against. The content side
    /// owns `chronon_contract_version()`; whoever links both sides checks that
    /// the two agree and fails closed on a mismatch.
    inline constexpr std::uint32_t kExpectedContractVersion = 1u;

    /// Motion content ids are opaque strings (Chronon mints them); the wire
    /// wants the numeric id Chronon minted for the same asset. Only Chronon can
    /// answer, so the caller supplies the mapping — the packer never invents an
    /// id from the string, because a digest of its own could never match the one
    /// the content side holds.
    using ContentIdLookup = std::function<chronon_content_id(const ContentId&)>;

    /// One frame, ready to hand to the content side.
    struct ContractFrame {
        std::uint64_t frame{0};
        std::vector<chronon_layer_state> layers{};
    };

    /// The ABI's row-major, column-vector storage for a column-major motion
    /// matrix: `out[r*4 + c] = m.elements[c*4 + r]`.
    void writeRowMajor(const chrononmotion::Matrix4& matrix, float (&out)[16]) noexcept;

    /// `projection` remapped from ChrononMotion's -1..1 NDC z to the ABI's 0..1.
    /// A projection already in that convention (`leftHanded` false) is returned
    /// unchanged.
    [[nodiscard]] chrononmotion::Matrix4 zeroToOneProjection(const chrononmotion::Matrix4& projection,
                                                              bool leftHanded = false);

    /// Pack one submission for the contract zone.
    ///
    /// `projection` is the motion camera's projection and `view` its
    /// world-inverse; the ABI folds them into the per-layer product, so the
    /// caller supplies both from the same evaluation the submission came from.
    ///
    /// Throws `std::invalid_argument` when a layer draws content the lookup
    /// cannot name: the motion side refuses to submit an id it cannot vouch for,
    /// exactly as `MotionBridge` refuses a layer with no binding. A null/controller
    /// layer carries no content and packs as id 0.
    [[nodiscard]] ContractFrame pack(const FrameSubmission& submission,
                                     const chrononmotion::Matrix4& projection,
                                     const chrononmotion::Matrix4& view,
                                     const ContentIdLookup& contentIds);

}// namespace chronontemplate::contract

#endif//CHRONONTEMPLATE_HAS_CONTRACT_ABI

#endif//CHRONONTEMPLATE_CONTRACT_SUBMISSION_HPP
