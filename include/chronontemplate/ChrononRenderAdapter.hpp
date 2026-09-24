// ChrononTemplate — thin live handoff to the Chronon3D C ABI.
//
// The adapter borrows engine/plan handles owned by the Chronon host. It owns no
// renderer state, content bytes or output buffer; Chronon3D owns the returned
// frame buffer until releaseFrame() is called.
#ifndef CHRONONTEMPLATE_CHRONON_RENDER_ADAPTER_HPP
#define CHRONONTEMPLATE_CHRONON_RENDER_ADAPTER_HPP

#include <chronon/abi.h>
#include "chronontemplate/FrameSubmission.hpp"

namespace chronontemplate {

    class ChrononRenderAdapter final {
    public:
        /// The handles remain owned by the caller and must outlive this adapter.
        ChrononRenderAdapter(chronon_engine* engine, const chronon_plan* plan);

        /// Submit one already-resolved frame through the ADR-032 layer contract.
        /// `outBuffer` is filled by Chronon3D and must be released with
        /// releaseFrame() before the engine is destroyed.
        [[nodiscard]] chronon_status renderFrame(
                const FrameSubmission& submission,
                chronon_frame_buffer* outBuffer) const;

        /// Release a buffer returned by renderFrame(). Null is accepted.
        void releaseFrame(chronon_frame_buffer* buffer) const noexcept;

    private:
        chronon_engine* m_engine;
        const chronon_plan* m_plan;
    };

}// namespace chronontemplate

#endif//CHRONONTEMPLATE_CHRONON_RENDER_ADAPTER_HPP
