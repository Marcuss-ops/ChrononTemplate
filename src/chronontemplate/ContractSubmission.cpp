#include "chronontemplate/ContractSubmission.hpp"

#if CHRONONTEMPLATE_HAS_CONTRACT_ABI

#include <algorithm>
#include <stdexcept>
#include <string>

namespace chronontemplate::contract {

    void writeRowMajor(const chrononmotion::Matrix4& matrix, float (&out)[16]) noexcept {

        // The motion side stores column-major (`elements[column * 4 + row]`,
        // three.js convention); the contract stores row-major with column
        // vectors. The transpose is the whole conversion.
        for (unsigned int row = 0; row < 4u; ++row) {
            for (unsigned int column = 0; column < 4u; ++column) {
                out[row * 4u + column] = matrix.elements[column * 4u + row];
            }
        }
    }

    chrononmotion::Matrix4 zeroToOneProjection(const chrononmotion::Matrix4& projection) {

        // Folded into a matrix and applied on the left, so the product stays one
        // matrix per layer:
        //   z_clip' = 0.5 * z_clip + 0.5 * w_clip,  w' = w_clip
        // which is NDC z' = (z + 1) / 2 for the motion camera's -1..1 range.
        chrononmotion::Matrix4 remap;                 // identity from the default
        remap.elements[2u * 4u + 2u] = 0.5f;          // column 2, row 2
        remap.elements[3u * 4u + 2u] = 0.5f;          // column 3, row 2

        chrononmotion::Matrix4 result;
        result.multiplyMatrices(remap, projection);
        return result;
    }

    ContractFrame pack(const FrameSubmission& submission,
                       const chrononmotion::Matrix4& projection,
                       const chrononmotion::Matrix4& view,
                       const ContentIdLookup& contentIds) {

        // projection · view once, then · world per layer: the ABI's
        // clip_from_local is the whole product, and the camera does not cross
        // the boundary in any other form.
        chrononmotion::Matrix4 clipFromView;
        clipFromView.multiplyMatrices(zeroToOneProjection(projection), view);

        ContractFrame frame;
        frame.frame = static_cast<std::uint64_t>(submission.frame);
        frame.layers.reserve(submission.layers.size());

        for (const BoundLayer& bound : submission.layers) {

            chronon_layer_state state{};
            state.struct_size = static_cast<std::uint32_t>(sizeof(chronon_layer_state));
            state.layer = static_cast<chronon_layer_id>(bound.transform.id);
            state.opacity = std::clamp(bound.transform.opacity, 0.f, 1.f);
            state.visible = bound.transform.visible ? 1u : 0u;
            state.content = 0u;

            if (bound.draws()) {
                const chronon_content_id content = contentIds ? contentIds(bound.content.id) : 0u;
                if (content == 0u) {
                    // 0 is the contract's "no content": an id the host cannot name
                    // would silently draw nothing, which is the failure this
                    // refuses rather than reports.
                    throw std::invalid_argument(
                            "contract::pack: layer " + std::to_string(bound.transform.id) +
                            " draws content '" + bound.content.id +
                            "' that the content host did not name (0 is reserved)");
                }
                state.content = content;
            }

            chrononmotion::Matrix4 clipFromLocal;
            clipFromLocal.multiplyMatrices(clipFromView, bound.transform.world);
            writeRowMajor(clipFromLocal, state.clip_from_local);

            // A negative depth means "not authored, recompute from the matrix".
            // The rule for recomputing it lives in exactly one place
            // (chronon3d/motion/contract_bridge.hpp), so this half does not
            // restate it — a second copy is a second thing to drift.
            state.depth = -1.f;

            frame.layers.push_back(state);
        }

        return frame;
    }

}// namespace chronontemplate::contract

#endif//CHRONONTEMPLATE_HAS_CONTRACT_ABI
