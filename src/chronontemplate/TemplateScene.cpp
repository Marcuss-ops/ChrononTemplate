#include "chronontemplate/TemplateScene.hpp"

#include <stdexcept>
#include <string>
#include <utility>
#include <cmath>

namespace chronontemplate {

    using chrononmotion::Vector2;
    using chrononmotion::Vector3;
    using chrononmotion::motion::CameraRig;
    using chrononmotion::motion::ContentRef;
    using chrononmotion::motion::Layer;
    using chrononmotion::motion::MotionScene;

    namespace presets = chrononmotion::motion::presets;

    namespace {

        [[nodiscard]] float checkedFps(float fps) {

            if (!(fps > 0.f)) throw std::invalid_argument("TemplateScene: fps must be positive");
            return fps;
        }

        [[nodiscard]] float checkedSpan(float value) {

            if (!(value > 0.f)) throw std::invalid_argument("TemplateScene: the canvas must be positive");
            return value;
        }

        [[nodiscard]] std::string derivedName(std::string requested, const std::string& fallback) {

            return requested.empty() ? fallback : std::move(requested);
        }

    }// namespace

    // ── LayerHandle ─────────────────────────────────────────────────────────

    LayerHandle::LayerHandle(TemplateScene* scene, MotionLayerId id)
        : m_scene(scene), m_id(id) {}

    Layer& LayerHandle::layer() {

        Layer* found = m_scene->motion().findLayer(m_id);
        if (found == nullptr) {
            throw std::logic_error("LayerHandle: layer " + std::to_string(m_id) + " is not in the scene");
        }
        return *found;
    }

    const std::string& LayerHandle::name() const {

        return m_scene->motion().findLayer(m_id)->name;
    }

    const std::string& LayerHandle::contentId() const {

        return m_scene->bindings().contentOf(m_id);
    }

    LayerHandle& LayerHandle::position(float x, float y, float z) {

        layer().positionedAt(Vector3(x, y, z));
        return *this;
    }

    LayerHandle& LayerHandle::anchor(float x, float y, float z) {

        layer().anchoredAt(Vector3(x, y, z));
        return *this;
    }

    LayerHandle& LayerHandle::scale(float uniform) {

        layer().scaled(uniform);
        return *this;
    }

    LayerHandle& LayerHandle::opacity(float value) {

        layer().opacityAt(value);
        return *this;
    }

    LayerHandle& LayerHandle::parent(MotionLayerId parentId) {

        layer().childOf(parentId);
        return *this;
    }

    LayerHandle& LayerHandle::alive(int inFrame, int outFrame) {

        layer().alive(inFrame, outFrame);
        return *this;
    }

    LayerHandle& LayerHandle::animate(const FadeIn& motion) {

        presets::fadeIn(layer(), motion.inFrame, motion.duration, m_scene->fps());
        return *this;
    }

    LayerHandle& LayerHandle::animate(const FadeOut& motion) {

        presets::fadeOut(layer(), motion.startFrame, motion.duration, m_scene->fps());
        return *this;
    }

    LayerHandle& LayerHandle::animate(const ScalePop& motion) {

        presets::scalePop(layer(), motion.inFrame, motion.duration, motion.from, motion.to, m_scene->fps());
        return *this;
    }

    LayerHandle& LayerHandle::animate(const SlideIn& motion) {

        presets::slideIn(layer(), motion.direction, motion.inFrame, motion.duration, motion.distance,
                         m_scene->fps());
        return *this;
    }

    LayerHandle& LayerHandle::animate(const SpinXYZ& motion) {

        presets::spinXYZ(layer(), motion.inFrame, motion.duration, motion.turns, m_scene->fps());
        return *this;
    }

    // ── CameraHandle ────────────────────────────────────────────────────────

    CameraRig& CameraHandle::rig() {

        return m_scene->m_camera;
    }

    CameraHandle& CameraHandle::orbit(float yaw, float pitch) {

        m_pending = Pending::Orbit;
        m_a = yaw;
        m_b = pitch;
        return *this;
    }

    CameraHandle& CameraHandle::push(float distance) {

        m_pending = Pending::Push;
        m_a = distance;
        return *this;
    }

    CameraHandle& CameraHandle::fov(float from, float to) {

        m_pending = Pending::Fov;
        m_a = from;
        m_b = to;
        return *this;
    }

    CameraHandle& CameraHandle::framing(float x, float y, float z) {

        // A camera still looks at the canvas centre: the template states where the
        // eye is, not where the subject went.
        rig().setPosition(Vector3(x, y, z)).setTarget(Vector3(m_scene->m_width * 0.5f, m_scene->m_height * 0.5f, 0.f));
        return *this;
    }

    CameraHandle& CameraHandle::between(int startFrame, int endFrame) {

        if (endFrame < startFrame) {
            throw std::invalid_argument("CameraHandle::between: expected startFrame <= endFrame");
        }
        if (m_pending == Pending::None) return *this;

        const int duration = endFrame - startFrame;
        const float fps = m_scene->fps();

        switch (m_pending) {
            case Pending::Orbit:
                presets::cameraOrbit(rig(), startFrame, duration, m_a, m_b, fps);
                break;
            case Pending::Push:
                presets::cameraPush(rig(), startFrame, duration, m_a, fps);
                break;
            case Pending::Fov:
                presets::cameraFov(rig(), startFrame, duration, m_a, m_b, fps);
                break;
            case Pending::None:
                break;
        }

        m_pending = Pending::None;
        return *this;
    }

    // ── TemplateScene ───────────────────────────────────────────────────────

    TemplateScene::TemplateScene(std::string name, float fps, ContentHost& host, float width, float height)
        : m_name(std::move(name)),
          m_fps(checkedFps(fps)),
          m_width(checkedSpan(width)),
          m_height(checkedSpan(height)),
          m_host(host),
          m_scene(m_name, m_fps),
          m_camera(1, 55.f, m_width / m_height, 0.1f, 2000.f),
          m_bridge(m_scene, m_camera, m_bindings, &m_host),
          m_cameraHandle(this) {

        if (m_name.empty()) throw std::invalid_argument("TemplateScene: the composition name is required");

        // The 2.5D convention the motion core is authored for: the eye sits one
        // canvas height away from the plane it looks at.
        m_camera.setPosition(Vector3(m_width * 0.5f, m_height * 0.5f, m_height))
                .setTarget(Vector3(m_width * 0.5f, m_height * 0.5f, 0.f));
    }

    LayerHandle& TemplateScene::adopt(ContentHandle handle, std::string name, MotionLayerId parentId) {

        if (handle.empty()) {
            throw std::invalid_argument("TemplateScene: the content host returned an empty handle");
        }
        if (handle.metrics.fingerprint.empty()) {
            throw std::invalid_argument("TemplateScene: content '" + handle.id +
                                        "' was handed over without a measurement");
        }

        // Chronon measured it, the motion side carries it: this is the form a
        // Chronon-produced ref takes.
        const ContentRef ref = ContentRef::measured(handle.id, handle.kind, handle.metrics.fingerprint,
                                                    handle.metrics.naturalSize, handle.metrics.anchor);

        Layer& layer = m_scene.addContent(m_nextId++, std::move(name), ref, parentId);
        m_bindings.bind(layer.id, handle.id, handle.wireId);

        m_handles.emplace_back(this, layer.id);
        return m_handles.back();
    }

    LayerHandle& TemplateScene::adoptNull(std::string name, MotionLayerId parentId) {

        Layer& layer = m_scene.addNull(m_nextId++, std::move(name), parentId);
        m_handles.emplace_back(this, layer.id);
        return m_handles.back();
    }

    LayerHandle& TemplateScene::text(const TextSpec& spec) {

        if (spec.text.empty()) throw std::invalid_argument("TemplateScene::text: the text is required");

        TextRequest request;
        request.text = spec.text;
        request.font = spec.font;
        request.fontSize = spec.fontSize;
        request.color = spec.color;
        request.canvas = canvas();

        // Chronon creates and measures; the rectangle and its fingerprint come
        // back neutral, so the motion side can anchor without knowing a font.
        ContentHandle handle = m_host.createText(request);
        return adopt(std::move(handle), derivedName(spec.name, spec.text), Layer::kRoot);
    }

    LayerHandle& TemplateScene::image(const ImageSpec& spec) {

        if (spec.path.empty()) throw std::invalid_argument("TemplateScene::image: the path is required");
        if (!std::isfinite(spec.frame.cornerRadius) || spec.frame.cornerRadius < 0.f ||
            !std::isfinite(spec.frame.borderWidth) || spec.frame.borderWidth < 0.f ||
            (spec.frame.borderWidth > 0.f && spec.frame.borderColor.empty())) {
            throw std::invalid_argument("TemplateScene::image: invalid image frame style");
        }

        ImageRequest request;
        request.path = spec.path;
        request.cornerRadius = spec.frame.cornerRadius;
        request.borderColor = spec.frame.borderColor;
        request.borderWidth = spec.frame.borderWidth;

        ContentHandle handle = m_host.createImage(request);
        return adopt(std::move(handle), derivedName(spec.name, spec.path), Layer::kRoot);
    }

    LayerHandle& TemplateScene::video(const VideoSpec& spec) {

        if (spec.path.empty()) throw std::invalid_argument("TemplateScene::video: the path is required");

        VideoRequest request;
        request.path = spec.path;

        ContentHandle handle = m_host.createVideo(request);
        return adopt(std::move(handle), derivedName(spec.name, spec.path), Layer::kRoot);
    }

    LayerHandle& TemplateScene::group(const std::string& name, MotionLayerId parentId) {

        if (name.empty()) throw std::invalid_argument("TemplateScene::group: the name is required");
        return adoptNull(name, parentId);
    }

    CameraHandle& TemplateScene::camera() {

        return m_cameraHandle;
    }

    FrameSubmission TemplateScene::submit(int frame) {

        return m_bridge.submit(frame);
    }

}// namespace chronontemplate
