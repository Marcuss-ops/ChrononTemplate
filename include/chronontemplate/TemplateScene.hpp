// ChrononTemplate — the orchestration API.
//
// A template says *what content*, *where*, *with which animation*. It never says
// how text is shaped, how a matrix is built, or how a frame is rasterized: the
// content calls go to Chronon, the space and time calls go to ChrononMotion, and
// the binding between the two stays here. One layer type, whatever the content.

#ifndef CHRONONTEMPLATE_TEMPLATE_SCENE_HPP
#define CHRONONTEMPLATE_TEMPLATE_SCENE_HPP

#include "chrononmotion/motion/MotionScene.hpp"
#include "chrononmotion/motion/Presets.hpp"

#include "chronontemplate/ContentBinding.hpp"
#include "chronontemplate/ContentHost.hpp"
#include "chronontemplate/FrameSubmission.hpp"
#include "chronontemplate/MotionBridge.hpp"

#include <cstdint>
#include <deque>
#include <string>
#include <vector>

namespace chronontemplate {

    // ── Animation descriptors ───────────────────────────────────────────────
    //
    // Each one is a thin spelling of a ChrononMotion preset. They are data, not
    // logic: the template states the intent and the motion core owns the keys.

    struct FadeIn {
        int inFrame{0};
        int duration{30};
    };

    struct FadeOut {
        int startFrame{0};
        int duration{30};
    };

    struct ScalePop {
        int inFrame{0};
        int duration{30};
        float from{0.6f};
        float to{1.f};
    };

    struct SlideIn {
        chrononmotion::motion::presets::Direction direction{chrononmotion::motion::presets::Direction::Left};
        int inFrame{0};
        int duration{30};
        float distance{200.f};
    };

    struct SpinXYZ {
        int inFrame{0};
        int duration{60};
        float turns{1.f};
    };

    // ── Authoring specs ────────────────────────────────────────────────────

    struct TextSpec {
        std::string text{};
        std::string font{};
        float fontSize{48.f};
        std::string color{"#FFFFFF"};
        std::string name{};  ///< layer name; derived from the text when empty
    };

    /// Per-image frame style passed to Chronon's ContentHost. Radius zero keeps
    /// square corners; borderWidth zero disables the optional outline.
    struct ImageFrameStyle {
        float cornerRadius{0.f};
        std::string borderColor{};
        float borderWidth{0.f};
    };

    struct ImageSpec {
        std::string path{};
        std::string name{};
        ImageFrameStyle frame{};
    };

    struct VideoSpec {
        std::string path{};
        std::string name{};
    };

    class TemplateScene;

    /// A handle on one layer. Everything here is fluent so a template reads as
    /// one sentence per intent.
    class LayerHandle {
    public:
        LayerHandle(TemplateScene* scene, MotionLayerId id);

        [[nodiscard]] MotionLayerId id() const { return m_id; }
        [[nodiscard]] const std::string& contentId() const;
        [[nodiscard]] const std::string& name() const;

        LayerHandle& position(float x, float y, float z = 0.f);
        LayerHandle& anchor(float x, float y, float z = 0.f);
        LayerHandle& scale(float uniform);
        LayerHandle& opacity(float value);
        LayerHandle& parent(MotionLayerId parentId);
        LayerHandle& alive(int inFrame, int outFrame);

        LayerHandle& animate(const FadeIn& motion);
        LayerHandle& animate(const FadeOut& motion);
        LayerHandle& animate(const ScalePop& motion);
        LayerHandle& animate(const SlideIn& motion);
        LayerHandle& animate(const SpinXYZ& motion);

    private:
        [[nodiscard]] chrononmotion::motion::Layer& layer();

        TemplateScene* m_scene{nullptr};
        MotionLayerId m_id{0};
    };

    /// The camera, owned by the motion side. `orbit()`/`push()` state the move and
    /// `between()` says when, so a template writes one intent per call.
    class CameraHandle {
    public:
        explicit CameraHandle(TemplateScene* scene) : m_scene(scene) {}

        CameraHandle& orbit(float yaw, float pitch);
        CameraHandle& push(float distance);
        CameraHandle& fov(float from, float to);
        CameraHandle& framing(float x, float y, float z);

        /// Apply the pending move over the frame window. Without a pending move
        /// this is a no-op, so a chained call cannot silently do nothing.
        CameraHandle& between(int startFrame, int endFrame);

        [[nodiscard]] chrononmotion::motion::CameraRig& rig();

    private:
        enum class Pending {
            None,
            Orbit,
            Push,
            Fov
        };

        TemplateScene* m_scene{nullptr};
        Pending m_pending{Pending::None};
        float m_a{0.f};
        float m_b{0.f};
    };

    /// A composition being authored: content created by Chronon, space and time by
    /// ChrononMotion, bindings by this module.
    class TemplateScene {
    public:
        TemplateScene(std::string name, float fps, ContentHost& host,
                      float width = 1920.f, float height = 1080.f);

        [[nodiscard]] LayerHandle& text(const TextSpec& spec);
        [[nodiscard]] LayerHandle& image(const ImageSpec& spec);
        [[nodiscard]] LayerHandle& video(const VideoSpec& spec);

        /// A null/controller layer: it owns no content and animates its children.
        [[nodiscard]] LayerHandle& group(const std::string& name, MotionLayerId parentId = 0);

        [[nodiscard]] CameraHandle& camera();

        /// Evaluate `frame` and resolve everything the renderer needs. Delegates to
        /// the bridge: no conversion logic lives in the template.
        [[nodiscard]] FrameSubmission submit(int frame);

        [[nodiscard]] const std::string& name() const { return m_name; }
        [[nodiscard]] float fps() const { return m_fps; }
        [[nodiscard]] chrononmotion::Vector2 canvas() const { return chrononmotion::Vector2(m_width, m_height); }

        [[nodiscard]] chrononmotion::motion::MotionScene& motion() { return m_scene; }
        [[nodiscard]] const BindingRegistry& bindings() const { return m_bindings; }
        [[nodiscard]] MotionBridge& bridge() { return m_bridge; }

        /// The last frame the composition still shows something on.
        [[nodiscard]] int contentEndFrame() const { return m_scene.contentEndFrame(); }

        /// Authoring problems reported by the motion core (unknown parents, cycles).
        [[nodiscard]] std::vector<std::string> validate() const { return m_scene.validate(); }

    private:
        friend class LayerHandle;
        friend class CameraHandle;

        [[nodiscard]] LayerHandle& adopt(ContentHandle handle, std::string name, MotionLayerId parentId);
        [[nodiscard]] LayerHandle& adoptNull(std::string name, MotionLayerId parentId);

        std::string m_name{};
        float m_fps{24.f};
        float m_width{1920.f};
        float m_height{1080.f};
        ContentHost& m_host;

        chrononmotion::motion::MotionScene m_scene;
        chrononmotion::motion::CameraRig m_camera;
        BindingRegistry m_bindings{};
        MotionBridge m_bridge;

        std::deque<LayerHandle> m_handles{};
        CameraHandle m_cameraHandle;
        MotionLayerId m_nextId{100};
    };

}// namespace chronontemplate

#endif//CHRONONTEMPLATE_TEMPLATE_SCENE_HPP
