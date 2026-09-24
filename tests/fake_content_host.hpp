// ChrononTemplate test doubles.
//
// A stand-in for Chronon: deterministic ids, a box it can measure without a font
// engine, and the ability to re-measure an asset so the staleness check can be
// proven to fire. Shared by the scene tests, which is why it is not inside one
// of them.

#ifndef CHRONONTEMPLATE_TEST_FAKE_CONTENT_HOST_HPP
#define CHRONONTEMPLATE_TEST_FAKE_CONTENT_HOST_HPP

#include "chronontemplate/ContentHost.hpp"
#include "chronontemplate/FrameSubmission.hpp"

#include "chrononmotion/math/Matrix4.hpp"

#include <string>
#include <unordered_map>

namespace chronontemplate_test {

    namespace ct = chronontemplate;

    /// Chronon, faked: ids and rectangles are deterministic functions of the
    /// request, and the digest of each asset is remembered so a test can replace
    /// it.
    class FakeContentHost final : public ct::ContentHost {
    public:
        ct::ContentHandle createText(const ct::TextRequest& request) override {

            return measure("text/" + request.text + "@" + std::to_string(static_cast<int>(request.fontSize)),
                           chrononmotion::motion::ContentKind::Text,
                           chrononmotion::Vector2(static_cast<float>(request.text.size()) * request.fontSize * 0.55f,
                                                  request.fontSize * 1.2f));
        }

        ct::ContentHandle createImage(const ct::ImageRequest& request) override {

            m_lastImageRequest = request;
            return measure("image/" + request.path, chrononmotion::motion::ContentKind::Image,
                           chrononmotion::Vector2(640.f, 360.f));
        }

        [[nodiscard]] const ct::ImageRequest& lastImageRequest() const { return m_lastImageRequest; }

        ct::ContentHandle createVideo(const ct::VideoRequest& request) override {

            return measure("video/" + request.path, chrononmotion::motion::ContentKind::Video,
                           chrononmotion::Vector2(1920.f, 1080.f));
        }

        std::string currentFingerprint(const ct::ContentId& content) const override {

            const auto it = m_fingerprints.find(content);
            return it == m_fingerprints.end() ? std::string{} : it->second;
        }

        /// Re-measure an asset: same id, different digest.
        void remeasure(const ct::ContentId& content) { m_fingerprints[content] = "digest:v2:" + content; }

    private:
        ct::ImageRequest m_lastImageRequest{};
        ct::ContentHandle measure(const std::string& id, chrononmotion::motion::ContentKind kind,
                                  const chrononmotion::Vector2& size) {

            ct::ContentHandle handle;
            handle.id = id;
            handle.kind = kind;
            handle.metrics.naturalSize = size;
            handle.metrics.anchor = chrononmotion::Vector2(0.5f, 0.5f);
            handle.metrics.fingerprint = "digest:v1:" + id;
            m_fingerprints[id] = handle.metrics.fingerprint;
            return handle;
        }

        std::unordered_map<std::string, std::string> m_fingerprints{};
    };

    /// A host that forgets to measure: the template must refuse its content.
    class UnmeasuredHost final : public ct::ContentHost {
    public:
        ct::ContentHandle createText(const ct::TextRequest& request) override {

            ct::ContentHandle handle;
            handle.id = "text/" + request.text;
            handle.kind = chrononmotion::motion::ContentKind::Text;
            return handle;
        }

        ct::ContentHandle createImage(const ct::ImageRequest&) override { return ct::ContentHandle{}; }
        ct::ContentHandle createVideo(const ct::VideoRequest&) override { return ct::ContentHandle{}; }
        std::string currentFingerprint(const ct::ContentId&) const override { return {}; }
    };

    [[nodiscard]] inline const ct::BoundLayer* findLayer(const ct::FrameSubmission& frame, ct::MotionLayerId id) {

        for (const ct::BoundLayer& layer : frame.layers) {
            if (layer.transform.id == id) return &layer;
        }
        return nullptr;
    }

    [[nodiscard]] inline bool sameMatrix(const chrononmotion::Matrix4& lhs, const chrononmotion::Matrix4& rhs) {

        for (unsigned int i = 0; i < 16; ++i) {
            if (lhs[i] != rhs[i]) return false;
        }
        return true;
    }

}// namespace chronontemplate_test

#endif//CHRONONTEMPLATE_TEST_FAKE_CONTENT_HOST_HPP
