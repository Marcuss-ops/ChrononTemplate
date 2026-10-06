#ifndef CHRONONTEMPLATE_RENDER_PLAN_CONTENT_HOST_HPP
#define CHRONONTEMPLATE_RENDER_PLAN_CONTENT_HOST_HPP

#include "chronontemplate/core/ContentHost.hpp"
#include "chronontemplate/core/PlanLowering.hpp"

#include <functional>
#include <unordered_map>

namespace chronontemplate {

/// Backend callbacks keep asset creation and measurement in the host that owns
/// Chronon's fonts and media. This adapter records the matching native plan
/// payload so a TemplateScene can lower directly to Chronon3D.
struct RenderPlanContentBackend {
    std::function<ContentHandle(const TextRequest&)> createText;
    std::function<ContentHandle(const ImageRequest&)> createImage;
    std::function<ContentHandle(const VideoRequest&)> createVideo;
    std::function<ContentHandle(const ShapeRequest&)> createShape;
    std::function<std::string(const ContentId&)> currentFingerprint;
};

class RenderPlanContentHost final : public ContentHost {
public:
    explicit RenderPlanContentHost(RenderPlanContentBackend backend);

    [[nodiscard]] ContentHandle createText(const TextRequest& request) override;
    [[nodiscard]] ContentHandle createImage(const ImageRequest& request) override;
    [[nodiscard]] ContentHandle createVideo(const VideoRequest& request) override;
    [[nodiscard]] ContentHandle createShape(const ShapeRequest& request) override;
    [[nodiscard]] std::string currentFingerprint(const ContentId& content) const override;

    [[nodiscard]] std::unordered_map<MotionLayerId, chronon3d::render_plan::LayerPlan>
    layerPlans(const BindingRegistry& bindings) const;

private:
    [[nodiscard]] ContentHandle remember(ContentHandle handle, chronon3d::render_plan::LayerPlan plan);

    RenderPlanContentBackend m_backend;
    std::unordered_map<std::uint64_t, chronon3d::render_plan::LayerPlan> m_plansByWireId;
};

[[nodiscard]] chronon3d::render_plan::RenderPlan lowerToRenderPlan(
        TemplateScene& scene, const RenderPlanContentHost& host,
        std::string jobId = "chronontemplate", std::string outputPath = "output.png");

} // namespace chronontemplate

#endif
