#include "chronontemplate/bullet_list/BulletListPack.hpp"

#include "fake_content_host.hpp"
#include "motion_check.hpp"

#include <cmath>
#include <set>
#include <stdexcept>
#include <string>
#include <vector>

using namespace chronontemplate;
using chronontemplate_test::FakeContentHost;
using chronontemplate_test::findLayer;
using chrononmotion_test::check;
using chrononmotion_test::section;

namespace {

    void theRevealAndCameraVocabularyIsStable() {
        section("reveal and camera vocabulary");
        check(bulletRevealIds().size() == 8, "eight bullet reveals are published");
        check(bulletRevealIds().front() == "bullet_slide_left", "the reveal ids keep their canonical order");
        check(bulletCameraChoices().size() == 23,
              "the camera pool is the title-camera vocabulary minus the whip and crash pushes");
        for (TitleCameraMove move : bulletCameraChoices()) {
            check(move != TitleCameraMove::WhipSettle && move != TitleCameraMove::CrashPush,
                  "no loud camera move is offered to a reading board");
        }
    }

    void theSeedIsDeterministicAndVaries() {
        section("seeded picks are deterministic and varied");
        check(pickBulletCameraMove(7) == pickBulletCameraMove(7), "the same seed picks the same camera");
        check(pickBulletReveal(7, 3) == pickBulletReveal(7, 3), "the same seed and index pick the same reveal");

        std::set<int> cameras;
        for (std::uint32_t seed = 0; seed < 64; ++seed) {
            cameras.insert(static_cast<int>(pickBulletCameraMove(seed)));
        }
        check(cameras.size() >= 12, "sixty-four seeds reach a wide spread of camera moves");

        std::set<int> reveals;
        for (std::size_t i = 0; i < 32; ++i) {
            reveals.insert(static_cast<int>(pickBulletReveal(42, i)));
        }
        check(reveals.size() >= 6, "thirty-two bullets of one seed use at least six distinct reveals");
    }

    void theListSubmitsHiddenThenRevealedUnderOneCamera() {
        section("list submits hidden, then revealed, under one camera");
        FakeContentHost host;
        TemplateScene scene("bullet_list", 30.f, host, 1920.f, 1080.f);

        BulletListSpec spec;
        spec.items = {"Primo punto", "Secondo punto", "Terzo punto"};
        spec.seed = 11;
        const BulletListComposition board = addBulletList(scene, spec);

        check(board.bullets.size() == 3, "one pick per bullet");
        check(scene.validate().empty(), "the bullet scene validates");

        const FrameSubmission start = scene.submit(0);
        const FrameSubmission late = scene.submit(120);
        const BoundLayer* first = findLayer(start, board.bullets[0].layerId);
        const BoundLayer* lastNow = findLayer(late, board.bullets[2].layerId);
        check(first && lastNow, "every bullet submits as a bound layer");
        if (first && lastNow) {
            check(first->transform.opacity <= 0.001f, "the first bullet is hidden before its reveal");
            check(lastNow->transform.opacity >= 0.999f, "the last bullet is fully revealed by frame 120");
            check(first->content.isText(), "each bullet keeps text content bound");
        }
        check(start.camera && late.camera, "the list submits a camera pose");
        if (start.camera && late.camera) {
            const bool moved = std::abs(start.camera->position.x - late.camera->position.x) > 0.01f ||
                               std::abs(start.camera->position.y - late.camera->position.y) > 0.01f ||
                               std::abs(start.camera->position.z - late.camera->position.z) > 0.01f;
            check(moved, "the authored camera move changes the pose over the list");
        }
    }

    void theForcedRevealIsHonoured() {
        section("a forced reveal applies to every bullet");
        FakeContentHost host;
        TemplateScene scene("forced", 30.f, host, 1920.f, 1080.f);

        BulletListSpec spec;
        spec.items = {"Alpha", "Beta"};
        spec.reveal = BulletReveal::ScalePop;
        const BulletListComposition board = addBulletList(scene, spec);
        bool allForced = true;
        for (const BulletPick& pick : board.bullets) {
            allForced = allForced && pick.reveal == BulletReveal::ScalePop;
        }
        check(allForced, "forcing a reveal overrides the seeded choice for every bullet");
    }

    void invalidSpecsFailClosed() {
        section("invalid specs fail closed");
        FakeContentHost host;
        {
            TemplateScene scene("empty", 30.f, host, 1920.f, 1080.f);
            bool threw = false;
            try {
                addBulletList(scene, BulletListSpec{});
            } catch (const std::invalid_argument&) {
                threw = true;
            }
            check(threw, "an empty list is rejected");
        }
        {
            TemplateScene scene("zero", 30.f, host, 1920.f, 1080.f);
            BulletListSpec spec;
            spec.items = {"Only"};
            spec.revealDuration = 0;
            bool threw = false;
            try {
                addBulletList(scene, spec);
            } catch (const std::invalid_argument&) {
                threw = true;
            }
            check(threw, "a non-positive reveal duration is rejected");
        }
    }

}// namespace

int main() {
    theRevealAndCameraVocabularyIsStable();
    theSeedIsDeterministicAndVaries();
    theListSubmitsHiddenThenRevealedUnderOneCamera();
    theForcedRevealIsHonoured();
    invalidSpecsFailClosed();
    return chrononmotion_test::report();
}
