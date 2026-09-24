// ChrononTemplate — the bridge.
//
// No creative logic lives here. The bridge evaluates the motion scene, resolves
// every layer to the content it draws, checks that the measurement is still the
// current one, samples the camera rig, and hands the result over. It is the only
// place where the two engines meet, and it converts in one direction only:
// ChrononMotion's evaluated state becomes what Chronon has to draw.

#ifndef CHRONONTEMPLATE_MOTION_BRIDGE_HPP
#define CHRONONTEMPLATE_MOTION_BRIDGE_HPP

#include "chrononmotion/motion/CameraRig.hpp"
#include "chrononmotion/motion/MotionScene.hpp"

#include "chronontemplate/ContentBinding.hpp"
#include "chronontemplate/ContentHost.hpp"
#include "chronontemplate/FrameSubmission.hpp"

#include <string>

namespace chronontemplate {

    class MotionBridge {
    public:
        /// `camera` is sampled per frame; `host` is optional and only used to
        /// answer the staleness question (a template can be built and inspected
        /// without a content host attached).
        MotionBridge(chrononmotion::motion::MotionScene& scene,
                     chrononmotion::motion::CameraRig& camera,
                     const BindingRegistry& bindings,
                     const ContentHost* host = nullptr);

        /// Evaluate `frame` and resolve the whole scene for the renderer.
        ///
        /// Throws `std::invalid_argument` when a layer carries content with no
        /// binding (the frame would draw the wrong asset) and, when measurements
        /// are enforced, when a binding's measurement is no longer the digest the
        /// host currently holds.
        [[nodiscard]] FrameSubmission submit(int frame);

        /// Reject a stale measurement instead of reporting it. On by default: the
        /// anchor of a re-measured asset silently keeps the old rectangle, which is
        /// the failure this check exists for.
        MotionBridge& enforceMeasurements(bool value) {
            m_enforceMeasurements = value;
            return *this;
        }

        [[nodiscard]] bool enforcesMeasurements() const { return m_enforceMeasurements; }

    private:
        [[nodiscard]] chrononmotion::motion::MeasurementState measure(
                const chrononmotion::motion::ContentRef& content) const;

        chrononmotion::motion::MotionScene& m_scene;
        chrononmotion::motion::CameraRig& m_camera;
        const BindingRegistry& m_bindings;
        const ContentHost* m_host{nullptr};
        bool m_enforceMeasurements{true};
    };

}// namespace chronontemplate

#endif//CHRONONTEMPLATE_MOTION_BRIDGE_HPP
