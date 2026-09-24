#include "chronontemplate/ChrononRenderAdapter.hpp"

#include "motion_check.hpp"

#include <stdexcept>

using chronontemplate::ChrononRenderAdapter;
using chrononmotion_test::check;
using chrononmotion_test::section;

int main() {
    section("Chronon3D live render adapter");

    bool rejectedMissingEngine = false;
    try {
        ChrononRenderAdapter adapter(nullptr, reinterpret_cast<const chronon_plan*>(1));
        (void)adapter;
    } catch (const std::invalid_argument&) {
        rejectedMissingEngine = true;
    }
    check(rejectedMissingEngine, "a missing engine handle fails before ABI submission");

    bool rejectedMissingPlan = false;
    try {
        ChrononRenderAdapter adapter(reinterpret_cast<chronon_engine*>(1), nullptr);
        (void)adapter;
    } catch (const std::invalid_argument&) {
        rejectedMissingPlan = true;
    }
    check(rejectedMissingPlan, "a missing plan handle fails before ABI submission");

    return chrononmotion_test::report();
}
