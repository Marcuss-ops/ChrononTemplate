#include "chronontemplate/core/TemplateScene.hpp"

#include <stdexcept>
#include <string>
#include <utility>
#include <cmath>
#include <algorithm>

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

    const Layer& LayerHandle::layer() const {

        const Layer* found = m_scene->motion().findLayer(m_id);
        if (found == nullptr) {
            throw std::logic_error("LayerHandle: layer " + std::to_string(m_id) + " is not in the scene");
        }
        return *found;
    }

    LayerHandle& LayerHandle::animatePosition(int inFrame, int duration,
                                             const Vector3& startOffset,
                                             const chrononmotion::motion::Easing& easing) {
        const float fps = m_scene->fps();
        const float t0 = static_cast<float>(inFrame) / fps;
        const float t1 = static_cast<float>(inFrame + duration) / fps;
        const Vector3 rest = layer().transform.position;
        layer().tracks.position.add(t0, rest + startOffset, easing);
        layer().tracks.position.add(t1, rest, easing);
        return *this;
    }

    LayerHandle& LayerHandle::animateOpacity(int inFrame, int duration,
                                            float from, float to,
                                            const chrononmotion::motion::Easing& easing) {
        const float fps = m_scene->fps();
        const float t0 = static_cast<float>(inFrame) / fps;
        const float t1 = static_cast<float>(inFrame + duration) / fps;
        layer().tracks.opacity.add(t0, from, easing);
        layer().tracks.opacity.add(t1, to, easing);
        return *this;
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

    CameraHandle& CameraHandle::setFov(float degrees) {
        if (!std::isfinite(degrees) || degrees <= 0.f || degrees >= 180.f) {
            throw std::invalid_argument("CameraHandle::setFov: degrees must be finite and in (0, 180)");
        }
        rig().setFov(degrees);
        return *this;
    }

    CameraHandle& CameraHandle::horizon(float rollDegrees) {
        if (!std::isfinite(rollDegrees)) {
            throw std::invalid_argument("CameraHandle::horizon: roll must be finite");
        }
        constexpr float kDegreesToRadians = 0.01745329251994329577f;
        rig().setRoll(rollDegrees * kDegreesToRadians);
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
        request.stroke = spec.stroke;
        request.shadow = spec.shadow;
        request.glow = spec.glow;
        request.background = spec.background;

        // Chronon creates and measures; the rectangle and its fingerprint come
        // back neutral, so the motion side can anchor without knowing a font.
        ContentHandle handle = m_host.createText(request);
        return adopt(std::move(handle), derivedName(spec.name, spec.text), Layer::kRoot);
    }

    LayerHandle& TemplateScene::image(const ImageSpec& spec) {

        if (spec.path.empty()) throw std::invalid_argument("TemplateScene::image: the path is required");
        if (!std::isfinite(spec.frame.cornerRadius) || spec.frame.cornerRadius < 0.f ||
            !std::isfinite(spec.frame.borderWidth) || spec.frame.borderWidth < 0.f ||
            (spec.frame.borderWidth > 0.f && spec.frame.borderColor.empty()) ||
            !std::isfinite(spec.frame.saturation) || spec.frame.saturation < 0.f || spec.frame.saturation > 4.f ||
            !std::isfinite(spec.frame.contrast) || spec.frame.contrast < 0.f || spec.frame.contrast > 16.f ||
            !std::isfinite(spec.frame.grain) || spec.frame.grain < 0.f || spec.frame.grain > 1.f ||
            !std::isfinite(spec.frame.vignette) || spec.frame.vignette < 0.f || spec.frame.vignette > 1.f) {
            throw std::invalid_argument("TemplateScene::image: invalid image frame or look style");
        }
        const bool noTargetSize = spec.targetSize.x == 0.f && spec.targetSize.y == 0.f;
        if (!std::isfinite(spec.targetSize.x) || !std::isfinite(spec.targetSize.y) ||
            (noTargetSize ? false : (spec.targetSize.x <= 0.f || spec.targetSize.y <= 0.f))) {
            throw std::invalid_argument("TemplateScene::image: target size must be positive or unset");
        }
        switch (spec.fit) {
            case ImageFitMode::Contain:
            case ImageFitMode::Cover:
            case ImageFitMode::Stretch:
            case ImageFitMode::None:
                break;
            default:
                throw std::invalid_argument("TemplateScene::image: unsupported fit mode");
        }
        if (spec.crop.enabled && (!std::isfinite(spec.crop.origin.x) || !std::isfinite(spec.crop.origin.y) ||
                                  !std::isfinite(spec.crop.size.x) || !std::isfinite(spec.crop.size.y) ||
                                  spec.crop.origin.x < 0.f || spec.crop.origin.y < 0.f ||
                                  spec.crop.size.x <= 0.f || spec.crop.size.y <= 0.f ||
                                  spec.crop.origin.x + spec.crop.size.x > 1.f ||
                                  spec.crop.origin.y + spec.crop.size.y > 1.f)) {
            throw std::invalid_argument("TemplateScene::image: crop must be a normalized positive rectangle");
        }

        ImageRequest request;
        request.path = spec.path;
        request.cornerRadius = spec.frame.cornerRadius;
        request.borderColor = spec.frame.borderColor;
        request.borderWidth = spec.frame.borderWidth;
        request.fit = spec.fit;
        request.targetSize = spec.targetSize;
        request.crop = spec.crop;
        request.saturation = spec.frame.saturation;
        request.contrast = spec.frame.contrast;
        request.grain = spec.frame.grain;
        request.vignette = spec.frame.vignette;
        request.grainSeed = spec.frame.grainSeed;
        request.lightLeak = spec.frame.lightLeak;
        request.channelSplit = spec.frame.channelSplit;
        request.channelTrail = spec.frame.channelTrail;
        request.sliceDisplace = spec.frame.sliceDisplace;

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

    LayerHandle& TemplateScene::shape(const ShapeSpec& spec) {

        if (!std::isfinite(spec.size.x) || !std::isfinite(spec.size.y) ||
            spec.size.x <= 0.f || spec.size.y <= 0.f ||
            (spec.fillEnabled && spec.fillColor.empty()) ||
            !std::isfinite(spec.cornerRadius) || spec.cornerRadius < 0.f ||
            spec.cornerRadius > std::min(spec.size.x, spec.size.y) * 0.5f ||
            (spec.geometry != ShapeGeometry::Rectangle && spec.geometry != ShapeGeometry::Ellipse &&
             spec.geometry != ShapeGeometry::Grid && spec.geometry != ShapeGeometry::DotGrid &&
             spec.geometry != ShapeGeometry::Polygon))
            throw std::invalid_argument("TemplateScene::shape: positive finite size and supported geometry are required");
        const bool gridGeometry = spec.geometry == ShapeGeometry::Grid;
        const bool dotGridGeometry = spec.geometry == ShapeGeometry::DotGrid;
        const bool polygonGeometry = spec.geometry == ShapeGeometry::Polygon;
        if (gridGeometry || dotGridGeometry) {
            if (!std::isfinite(spec.gridSpacing) || spec.gridSpacing < 4.f || spec.gridSpacing > 512.f ||
                (dotGridGeometry && (!std::isfinite(spec.dotRadius) || spec.dotRadius < 0.5f || spec.dotRadius > 64.f)) ||
                (gridGeometry && (spec.strokeColor.empty() || !std::isfinite(spec.strokeWidth) ||
                                  spec.strokeWidth < 0.25f || spec.strokeWidth > 32.f)))
                throw std::invalid_argument("TemplateScene::shape: grid spacing, radius or stroke is outside supported bounds");
        }
        if (!spec.strokeColor.empty() &&
            (spec.strokeColor.size() != 7 || spec.strokeColor.front() != '#' ||
             !std::all_of(spec.strokeColor.begin() + 1, spec.strokeColor.end(), [](unsigned char c) {
                 return (c >= '0' && c <= '9') || (c >= 'a' && c <= 'f') ||
                        (c >= 'A' && c <= 'F');
             }) || !std::isfinite(spec.strokeWidth) || spec.strokeWidth < 0.25f ||
             spec.strokeWidth > 10000.f))
            throw std::invalid_argument("TemplateScene::shape: stroke color and width are outside supported bounds");
        if (polygonGeometry && (spec.polygonPoints < 3 || spec.polygonPoints > 64 ||
                                !std::isfinite(spec.polygonRotationDegrees) ||
                                !std::isfinite(spec.strokeWidth) || spec.strokeWidth < 0.25f ||
                                spec.strokeWidth > 10000.f ||
                                (!spec.strokeColor.empty() && !std::all_of(
                                    spec.strokeColor.begin(), spec.strokeColor.end(), [](unsigned char c) {
                                        return (c >= '0' && c <= '9') || (c >= 'a' && c <= 'f') ||
                                               (c >= 'A' && c <= 'F') || c == '#';
                                    }))))
            throw std::invalid_argument("TemplateScene::shape: polygon points or rotation is outside supported bounds");
        if (!std::isfinite(spec.noiseAmount) || spec.noiseAmount < 0.f || spec.noiseAmount > 1.f ||
            !std::isfinite(spec.noiseSize) || spec.noiseSize <= 0.f || spec.noiseSize > 256.f ||
            !std::isfinite(spec.contrast) || spec.contrast < 0.f || spec.contrast > 4.f)
            throw std::invalid_argument("TemplateScene::shape: noise, size and contrast are outside supported bounds");
        if (spec.field) {
            const auto& field = *spec.field;
            if (gridGeometry || dotGridGeometry || polygonGeometry ||
                !std::isfinite(field.frequency) || field.frequency <= 0.f || field.frequency > 4096.f ||
                field.octaves < 1 || field.octaves > 16 ||
                !std::isfinite(field.persistence) || field.persistence < 0.f || field.persistence > 1.f ||
                !std::isfinite(field.lacunarity) || field.lacunarity <= 0.f || field.lacunarity > 8.f ||
                field.operators.size() > 8)
                throw std::invalid_argument("TemplateScene::shape: native field is invalid for this geometry");
        }
        if (spec.fieldRamp && !spec.field)
            throw std::invalid_argument("TemplateScene::shape: a field ramp requires a native field");
        if (spec.gradientMesh && (spec.field || spec.radialGradient || spec.gradientMesh->nodes.empty() ||
                                  spec.gradientMesh->nodes.size() > 256))
            throw std::invalid_argument("TemplateScene::shape: mesh fill conflicts with another fill or exceeds node budget");
        if (spec.fieldRenderScale != 1 && spec.fieldRenderScale != 2 && spec.fieldRenderScale != 4)
            throw std::invalid_argument("TemplateScene::shape: field render scale must be 1, 2 or 4");
        if (spec.radialGradient) {
            const auto& gradient = *spec.radialGradient;
            if (spec.geometry != ShapeGeometry::Ellipse ||
                !std::isfinite(gradient.center.x) || !std::isfinite(gradient.center.y) ||
                gradient.center.x < 0.f || gradient.center.x > 1.f ||
                gradient.center.y < 0.f || gradient.center.y > 1.f ||
                !std::isfinite(gradient.radius) || gradient.radius <= 0.f ||
                gradient.radius > 2.f || gradient.stops.size() < 2 || gradient.stops.size() > 16)
                throw std::invalid_argument("TemplateScene::shape: radial gradients require an ellipse and bounded geometry/stops");
            float previousPosition = -1.f;
            for (const auto& stop : gradient.stops) {
                const bool validHex = stop.color.size() == 7 && stop.color.front() == '#' &&
                    std::all_of(stop.color.begin() + 1, stop.color.end(), [](unsigned char digit) {
                        return (digit >= '0' && digit <= '9') ||
                               (digit >= 'a' && digit <= 'f') ||
                               (digit >= 'A' && digit <= 'F');
                    });
                if (!std::isfinite(stop.position) || stop.position < previousPosition ||
                    stop.position < 0.f || stop.position > 1.f || !validHex || !std::isfinite(stop.opacity) ||
                    stop.opacity < 0.f || stop.opacity > 1.f)
                    throw std::invalid_argument("TemplateScene::shape: radial gradient stops must be ordered, colored and bounded");
                previousPosition = stop.position;
            }
        }

        ShapeRequest request;
        request.size = spec.size;
        request.fillColor = spec.fillColor;
        request.name = spec.name;
        request.cornerRadius = spec.cornerRadius;
        request.fillEnabled = spec.fillEnabled;
        request.geometry = spec.geometry;
        request.radialGradient = spec.radialGradient;
        request.gridSpacing = spec.gridSpacing;
        request.dotRadius = spec.dotRadius;
        request.strokeColor = spec.strokeColor;
        request.strokeWidth = spec.strokeWidth;
        request.polygonPoints = spec.polygonPoints;
        request.polygonRotationDegrees = spec.polygonRotationDegrees;
        request.field = spec.field;
        request.fieldRamp = spec.fieldRamp;
        request.fieldRenderScale = spec.fieldRenderScale;
        request.fieldDrift = spec.fieldDrift;
        request.gradientMesh = spec.gradientMesh;
        request.noiseAmount = spec.noiseAmount;
        request.noiseSeed = spec.noiseSeed;
        request.animatedNoise = spec.animatedNoise;
        request.noiseSize = spec.noiseSize;
        request.contrast = spec.contrast;
        ContentHandle handle = m_host.createShape(request);
        return adopt(std::move(handle), derivedName(spec.name, "Shape"), Layer::kRoot);
    }

    LayerHandle& TemplateScene::group(const std::string& name, MotionLayerId parentId) {

        if (name.empty()) throw std::invalid_argument("TemplateScene::group: the name is required");
        return adoptNull(name, parentId);
    }

    CameraHandle& TemplateScene::camera() {

        return m_cameraHandle;
    }

    TemplateScene& TemplateScene::setTemporalMotionBlur(float shutterAngle,
                                                        std::uint32_t samples) {
        if (!std::isfinite(shutterAngle) || shutterAngle <= 0.f || shutterAngle > 360.f)
            throw std::invalid_argument("TemplateScene::setTemporalMotionBlur: shutter angle must be in (0, 360]");
        if (samples < 2 || samples > 64)
            throw std::invalid_argument("TemplateScene::setTemporalMotionBlur: samples must be in [2, 64]");
        m_temporalMotionBlur = TemporalMotionBlurSettings{shutterAngle, samples};
        return *this;
    }

    FrameSubmission TemplateScene::submit(int frame) {

        return m_bridge.submit(frame);
    }

}// namespace chronontemplate
