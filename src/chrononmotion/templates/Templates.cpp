#include "chrononmotion/templates/Templates.hpp"

#include "chrononmotion/math/MathUtils.hpp"
#include "chrononmotion/motion/Presets.hpp"

#include <cmath>
#include <limits>
#include <stdexcept>
#include <utility>

namespace chrononmotion::templates {

    namespace {

        using namespace motion;

        void addText(MotionScene& scene, Layer::Id id, const std::string& name,
                     const std::string& value, Layer::Id parent, const Vector3& position,
                     const Vector2& size, FrameRange lifetime) {
            Layer& layer = scene.addContent(id, name, ContentRef::text(value, size), parent);
            layer.positionedAt(position).flat().alive(lifetime);
        }

        Layer& addImage(MotionScene& scene, Layer::Id id, const std::string& name,
                        const std::string& asset, Layer::Id parent, const Vector3& position,
                        const Vector2& size, FrameRange lifetime) {
            Layer& layer = scene.addContent(id, name, ContentRef::image(asset, size), parent);
            return layer.positionedAt(position).flat().alive(lifetime);
        }

        FrameRange lifetime(const TemplateData& data) {
            return FrameRange::between(data.startFrame, data.startFrame + data.duration);
        }

        int endFrame(const TemplateData& data) {
            return data.startFrame + data.duration;
        }

        MotionScene youtubeSubscribe(const TemplateData& data) {
            const TemplateLayers ids;
            const FrameRange life = lifetime(data);
            MotionScene scene("youtube_subscribe", data.fps);
            Layer& root = scene.addNull(ids.root, "SubscribeCard");
            root.alive(life);

            Layer& avatar = addImage(scene, ids.icon, "Avatar", data.imageId, ids.root,
                                     Vector3(-360.f, 0.f, 0.f), Vector2(120.f, 120.f), life);
            addText(scene, ids.primary, "ChannelName", data.primaryText, ids.root,
                    Vector3(-190.f, 28.f, 0.f), Vector2(360.f, 48.f), life);
            addText(scene, ids.secondary, "SubscriberCount", data.secondaryText, ids.root,
                    Vector3(-190.f, -28.f, 0.f), Vector2(360.f, 36.f), life);
            Layer& button = addImage(scene, ids.accent, "SubscribeButton", data.iconId, ids.root,
                                     Vector3(300.f, 0.f, 0.f), Vector2(260.f, 76.f), life);
            addText(scene, ids.detail, "SubscribeLabel", "SUBSCRIBE", ids.accent,
                    Vector3(0.f, 0.f, 0.f), Vector2(220.f, 42.f), life);

            presets::parentGroupReveal(root, {&avatar, scene.findLayer(ids.primary), scene.findLayer(ids.secondary), &button},
                                       data.startFrame, 18, data.fps);
            presets::scalePop(button, data.startFrame + 20, 14, 0.86f, 1.f, data.fps);
            presets::flip(avatar, presets::Axis::Y, data.startFrame + 20, 12, data.fps, 8.f);
            presets::fadeOut(root, endFrame(data) - 18, 18, data.fps);
            return scene;
        }

        MotionScene instagramLike(const TemplateData& data) {
            const TemplateLayers ids;
            const FrameRange life = lifetime(data);
            MotionScene scene("instagram_like", data.fps);
            Layer& root = scene.addNull(ids.root, "LikeBurst");
            root.alive(life);

            Layer& heart = addImage(scene, ids.primary, "Heart", data.iconId, ids.root,
                                    Vector3(0.f, 0.f, 0.f), Vector2(180.f, 180.f), life);
            addText(scene, ids.secondary, "LikeText", data.primaryText, ids.root,
                    Vector3(0.f, -150.f, 0.f), Vector2(320.f, 44.f), life);
            presets::fadeIn(heart, data.startFrame, 6, data.fps);
            presets::scalePop(heart, data.startFrame + 2, 14, 0.05f, 1.f, data.fps);
            presets::spinZ(heart, data.startFrame + 2, 14, 0.12f, data.fps);
            presets::fadeIn(*scene.findLayer(ids.secondary), data.startFrame + 8, 10, data.fps);

            constexpr int particleCount = 6;
            for (int i = 0; i < particleCount; ++i) {
                const float angle = math::TWO_PI * static_cast<float>(i) / particleCount;
                const Layer::Id id = ids.particleStart + static_cast<Layer::Id>(i);
                Layer& particle = addImage(scene, id, "Particle" + std::to_string(i), data.iconId, ids.root,
                                            Vector3(0.f, 0.f, 0.f), Vector2(28.f, 28.f), life);
                const Vector3 offset(std::cos(angle) * 150.f, std::sin(angle) * 150.f, 0.f);
                presets::scalePop(particle, data.startFrame + 4, 10, 0.2f, 1.f, data.fps);
                presets::fadeIn(particle, data.startFrame + 4, 4, data.fps);
                presets::drift(particle, data.startFrame + 4, 24, offset, data.fps);
                presets::fadeOut(particle, endFrame(data) - 18, 18, data.fps);
            }
            presets::fadeOut(heart, endFrame(data) - 18, 18, data.fps);
            presets::fadeOut(*scene.findLayer(ids.secondary), endFrame(data) - 18, 18, data.fps);
            return scene;
        }

        MotionScene followPrompt(const TemplateData& data) {
            const TemplateLayers ids;
            const FrameRange life = lifetime(data);
            MotionScene scene("follow_prompt", data.fps);
            Layer& root = scene.addNull(ids.root, "FollowPrompt");
            root.alive(life);

            Layer& avatar = addImage(scene, ids.icon, "Avatar", data.imageId, ids.root,
                                     Vector3(-330.f, 0.f, 0.f), Vector2(108.f, 108.f), life);
            addText(scene, ids.primary, "Handle", data.primaryText, ids.root,
                    Vector3(-170.f, 24.f, 0.f), Vector2(340.f, 44.f), life);
            addText(scene, ids.secondary, "Message", data.secondaryText, ids.root,
                    Vector3(-170.f, -24.f, 0.f), Vector2(340.f, 34.f), life);
            Layer& button = addImage(scene, ids.accent, "FollowButton", data.iconId, ids.root,
                                     Vector3(280.f, 0.f, 0.f), Vector2(220.f, 72.f), life);
            addText(scene, ids.detail, "FollowLabel", "FOLLOW", ids.accent,
                    Vector3(0.f, 0.f, 0.f), Vector2(180.f, 38.f), life);

            presets::slideIn(root, presets::Direction::Up, data.startFrame, 20, 80.f, data.fps);
            presets::fadeIn(root, data.startFrame, 20, data.fps);
            presets::scalePop(button, data.startFrame + 24, 12, 0.9f, 1.f, data.fps);
            presets::flip(avatar, presets::Axis::Z, data.startFrame + 20, 10, data.fps, 12.f);
            presets::fadeOut(root, endFrame(data) - 18, 18, data.fps);
            return scene;
        }

        MotionScene lowerThird(const TemplateData& data) {
            const TemplateLayers ids;
            const FrameRange life = lifetime(data);
            MotionScene scene("lower_third", data.fps);
            Layer& root = scene.addNull(ids.root, "LowerThird");
            root.alive(life);

            Layer& accent = addImage(scene, ids.accent, "AccentBar", data.iconId, ids.root,
                                     Vector3(-700.f, -360.f, 0.f), Vector2(18.f, 150.f), life);
            addText(scene, ids.primary, "Name", data.primaryText, ids.root,
                    Vector3(-560.f, -320.f, 0.f), Vector2(520.f, 64.f), life);
            addText(scene, ids.secondary, "Role", data.secondaryText, ids.root,
                    Vector3(-560.f, -390.f, 0.f), Vector2(520.f, 40.f), life);

            presets::slideIn(root, presets::Direction::Left, data.startFrame, 18, 420.f, data.fps);
            presets::fadeIn(root, data.startFrame, 18, data.fps);
            presets::scalePop(accent, data.startFrame + 6, 12, 0.75f, 1.f, data.fps);
            presets::fadeOut(root, endFrame(data) - 18, 18, data.fps);
            return scene;
        }

        MotionScene breakingNews(const TemplateData& data) {
            const TemplateLayers ids;
            const FrameRange life = lifetime(data);
            MotionScene scene("breaking_news", data.fps);
            Layer& root = scene.addNull(ids.root, "BreakingNews");
            root.alive(life);
            Layer& banner = addImage(scene, ids.accent, "BreakingBanner", data.iconId, ids.root,
                                     Vector3(0.f, 280.f, 0.f), Vector2(1500.f, 180.f), life);
            addText(scene, ids.primary, "Headline", data.primaryText, ids.root,
                    Vector3(0.f, 300.f, 0.f), Vector2(1200.f, 62.f), life);
            addText(scene, ids.secondary, "Details", data.secondaryText, ids.root,
                    Vector3(0.f, 220.f, 0.f), Vector2(1000.f, 38.f), life);
            presets::slideIn(root, presets::Direction::Left, data.startFrame, 16, 600.f, data.fps);
            presets::fadeIn(root, data.startFrame, 16, data.fps);
            presets::scalePop(banner, data.startFrame + 10, 12, 0.85f, 1.f, data.fps);
            presets::fadeOut(root, endFrame(data) - 18, 18, data.fps);
            return scene;
        }

        MotionScene episodeTag(const TemplateData& data) {
            const TemplateLayers ids;
            const FrameRange life = lifetime(data);
            MotionScene scene("episode_tag", data.fps);
            Layer& root = scene.addNull(ids.root, "EpisodeTag");
            root.alive(life);
            addText(scene, ids.primary, "Episode", data.primaryText, ids.root,
                    Vector3(700.f, -380.f, 0.f), Vector2(300.f, 54.f), life);
            addText(scene, ids.secondary, "Tagline", data.secondaryText, ids.root,
                    Vector3(700.f, -320.f, 0.f), Vector2(600.f, 42.f), life);
            presets::slideIn(root, presets::Direction::Right, data.startFrame, 14, 360.f, data.fps);
            presets::fadeIn(root, data.startFrame, 14, data.fps);
            presets::fadeOut(root, endFrame(data) - 18, 18, data.fps);
            return scene;
        }

        MotionScene quoteCard(const TemplateData& data) {
            const TemplateLayers ids;
            const FrameRange life = lifetime(data);
            MotionScene scene("quote_card", data.fps);
            Layer& root = scene.addNull(ids.root, "QuoteCard");
            root.alive(life);

            Layer& background = addImage(scene, ids.icon, "Background", data.imageId, ids.root,
                                         Vector3(0.f, 0.f, -1.f), data.canvas, life);
            addText(scene, ids.primary, "Quote", data.primaryText, ids.root,
                    Vector3(0.f, 35.f, 0.f), Vector2(920.f, 180.f), life);
            addText(scene, ids.secondary, "Author", data.authorText, ids.root,
                    Vector3(0.f, -170.f, 0.f), Vector2(480.f, 48.f), life);

            presets::fadeScale(root, data.startFrame, 22, 0.92f, data.fps);
            presets::drift(background, data.startFrame, data.duration, Vector3(30.f, 0.f, 0.f), data.fps);
            presets::fadeIn(*scene.findLayer(ids.primary), data.startFrame + 12, 18, data.fps);
            presets::fadeIn(*scene.findLayer(ids.secondary), data.startFrame + 24, 18, data.fps);
            presets::fadeOut(root, endFrame(data) - 18, 18, data.fps);
            return scene;
        }

    }// namespace

    void TemplateData::validate() const {
        if (!std::isfinite(fps) || fps <= 0.f) {
            throw std::invalid_argument("TemplateData: fps must be positive and finite");
        }
        if (canvas.x <= 0.f || canvas.y <= 0.f || !std::isfinite(canvas.x) || !std::isfinite(canvas.y)) {
            throw std::invalid_argument("TemplateData: canvas must be finite and positive");
        }
        constexpr int minimumDuration = 48;
        if (startFrame < 0 || duration < minimumDuration ||
            startFrame > std::numeric_limits<int>::max() - duration) {
            throw std::invalid_argument("TemplateData: startFrame must be non-negative and duration must be at least 48 frames");
        }
        if (primaryText.empty()) {
            throw std::invalid_argument("TemplateData: primaryText must not be empty");
        }
        if (imageId.empty() || iconId.empty()) {
            throw std::invalid_argument("TemplateData: imageId and iconId must not be empty");
        }
    }

    const char* name(TemplateId id) {
        switch (id) {
            case TemplateId::YouTubeSubscribe: return "youtube_subscribe";
            case TemplateId::InstagramLike: return "instagram_like";
            case TemplateId::FollowPrompt: return "follow_prompt";
            case TemplateId::LowerThird: return "lower_third";
            case TemplateId::QuoteCard: return "quote_card";
            case TemplateId::BreakingNews: return "breaking_news";
            case TemplateId::EpisodeTag: return "episode_tag";
        }
        throw std::invalid_argument("templates::name: unknown template id");
    }

    std::vector<TemplateId> available() {
        return {TemplateId::YouTubeSubscribe, TemplateId::InstagramLike,
                TemplateId::FollowPrompt, TemplateId::LowerThird, TemplateId::QuoteCard,
                TemplateId::BreakingNews, TemplateId::EpisodeTag};
    }

    MotionScene build(TemplateId id, const TemplateData& data) {
        data.validate();
        switch (id) {
            case TemplateId::YouTubeSubscribe: return youtubeSubscribe(data);
            case TemplateId::InstagramLike: return instagramLike(data);
            case TemplateId::FollowPrompt: return followPrompt(data);
            case TemplateId::LowerThird: return lowerThird(data);
            case TemplateId::QuoteCard: return quoteCard(data);
            case TemplateId::BreakingNews: return breakingNews(data);
            case TemplateId::EpisodeTag: return episodeTag(data);
        }
        throw std::invalid_argument("templates::build: unknown template id");
    }

}// namespace chrononmotion::templates
