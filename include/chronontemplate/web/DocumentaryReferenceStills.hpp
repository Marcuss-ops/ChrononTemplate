// Native one-frame web/documentary compositions for the Web section.
#ifndef CHRONONTEMPLATE_DOCUMENTARY_REFERENCE_STILLS_HPP
#define CHRONONTEMPLATE_DOCUMENTARY_REFERENCE_STILLS_HPP

#include <nlohmann/json.hpp>
#include <vector>

namespace chronontemplate::web {

/// Four distinct, static 1920x1080 RenderPlan V3 compositions inspired by
/// archival web/news/documentary treatments. Assets resolve from the project root.
[[nodiscard]] std::vector<nlohmann::json> buildDocumentaryReferenceStillPlans();

} // namespace chronontemplate::web

#endif
