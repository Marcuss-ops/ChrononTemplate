#include "chronontemplate/MotionBridge.hpp"

#include <stdexcept>
#include <string>
#include <utility>

namespace chronontemplate {

    using chrononmotion::motion::MeasurementState;

    MotionBridge::MotionBridge(chrononmotion::motion::MotionScene& scene,
                               chrononmotion::motion::CameraRig& camera,
                               const BindingRegistry& bindings,
                               const ContentHost* host)
        : m_scene(scene), m_camera(camera), m_bindings(bindings), m_host(host) {}

    MeasurementState MotionBridge::measure(const chrononmotion::motion::ContentRef& content) const {

        if (m_host == nullptr) return MeasurementState::Unknown;
        return content.measurementState(m_host->currentFingerprint(content.id));
    }

    FrameSubmission MotionBridge::submit(int frame) {

        m_scene.evaluate(frame);
        const chrononmotion::motion::CompiledScene compiled = m_scene.compile();

        const float fps = compiled.fps > 0.f ? compiled.fps : m_scene.fps();

        FrameSubmission submission;
        submission.sceneName = compiled.name;
        submission.frame = compiled.frame;
        submission.fps = fps;
        submission.lights = compiled.lights;

        // `MotionScene::compile()` owns no camera: the rig is sampled for the same
        // frame, so the matrix every layer was solved against and the pose the
        // renderer uses come from one time base.
        const auto pose = m_camera.sample(static_cast<float>(frame) / fps);
        submission.camera = std::make_shared<const chrononmotion::motion::CameraPose>(pose);
        const auto camera = m_camera.makeCamera();
        m_camera.apply(pose, *camera);

        submission.layers.reserve(compiled.transforms.size());
        for (const chrononmotion::motion::CompiledTransform& transform : compiled.transforms) {
            BoundLayer bound;
            bound.transform = transform;

            const chrononmotion::motion::Layer* layer = m_scene.findLayer(transform.id);
            if (layer != nullptr) bound.content = layer->content;
            bound.clipFromLocal = camera->projectionMatrix;
            bound.clipFromLocal.multiply(camera->matrixWorldInverse);
            bound.clipFromLocal.multiply(transform.world);

            if (!bound.content.empty()) {
                if (!m_bindings.bound(transform.id)) {
                    throw std::invalid_argument(
                            "MotionBridge::submit: layer " + std::to_string(transform.id) +
                            " draws content '" + bound.content.id + "' with no binding");
                }

                bound.wireContentId = m_bindings.wireContentOf(transform.id);
                const ContentId& boundContent = m_bindings.contentOf(transform.id);
                if (boundContent != bound.content.id) {
                    throw std::invalid_argument(
                            "MotionBridge::submit: layer " + std::to_string(transform.id) + " is bound to '" +
                            boundContent + "' but carries '" + bound.content.id + "'");
                }

                bound.measurement = measure(bound.content);
                if (m_enforceMeasurements && bound.measurement == MeasurementState::Stale) {
                    throw std::invalid_argument(
                            "MotionBridge::submit: content '" + bound.content.id +
                            "' was re-measured; layer " + std::to_string(transform.id) +
                            " still carries the previous rectangle");
                }
            }

            submission.layers.push_back(std::move(bound));
        }

        return submission;
    }

}// namespace chronontemplate
