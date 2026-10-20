#pragma once

#include "chronontemplate/web/WebTextLayout.hpp"
#include <nlohmann/json.hpp>
#include <string>
#include <vector>

namespace chronontemplate::web {

enum class ArticleTypography { EditorialSans, ScientificSerif };

struct ArticleEvidenceSpec {
    std::string title{"DOCUMENTARY ARTICLE"};
    std::string section{"CULTURE  /  ARCHIVE"};
    std::string byline{"EDITORIAL DESK"};
    std::string bodyText;
    std::string highlightedPhrase;
    std::vector<std::string> keyPoints;
    ArticleTypography typography{ArticleTypography::EditorialSans};
    std::string output{"article_evidence_reveal.mp4"};
};

/// Builds a native 1920x1080, 30fps, 240-frame RenderPlan from an already
/// shaped page. Source layers remain individual text and shape layers.
[[nodiscard]] nlohmann::json buildArticleEvidenceRevealPlan(
    const ArticleEvidenceSpec& spec, const WebTextLayout& bodyLayout);

} // namespace chronontemplate::web
