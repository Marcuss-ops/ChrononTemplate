// Graphic documentary effects: redaction retractions + stamp, film
// leader beats, route drawing math, and flip-book counters.
#include "chronontemplate/documentary_effects/RedactedPack.hpp"
#include "chronontemplate/documentary_effects/FilmLeaderPack.hpp"
#include "chronontemplate/documentary_effects/RouteDrawingPack.hpp"
#include "chronontemplate/documentary_effects/AnimatedCountersPack.hpp"

#include "fake_content_host.hpp"
#include "motion_check.hpp"

#include <stdexcept>

using namespace chronontemplate;
using namespace chronontemplate::docfx;
using chronontemplate_test::FakeContentHost;
using chronontemplate_test::findLayer;
using chrononmotion_test::check;
using chrononmotion_test::checkNear;
using chrononmotion_test::section;

namespace {

    void redactedRetractsAndStamps() {
        section("redacted document");
        RedactedSpec spec;
        spec.bars = {{0.1f, 0.15f, 0.8f, 0.06f, 0}, {0.1f, 0.35f, 0.6f, 0.06f, 10}};
        checkNear(barRetract(spec, 0, 0), 0.f, 1e-6f, "bar 0 starts covered");
        checkNear(barRetract(spec, 0, 10), 0.f, 1e-6f, "bar 0 holds before onset");
        checkNear(barRetract(spec, 0, 28), 1.f, 1e-6f, "bar 0 clears after its window");
        check(barRetract(spec, 1, 28) < 1.f, "bar 1 lags behind bar 0");
        FakeContentHost host;
        TemplateScene scene("redacted", 30.f, host, 1920.f, 1080.f);
        const auto layers = addRedactedDocument(scene, spec);
        check(layers.paper != 0 && layers.stamp != 0, "paper and stamp are authored");
        check(host.findShapeRequest("redacted_bar_0") != nullptr, "bar shapes exist");
        check(host.findShapeRequest("redacted_bar_1") != nullptr, "both bars exist");
        const FrameSubmission stamped = scene.submit(100);
        const BoundLayer* stamp = findLayer(stamped, layers.stamp);
        check(stamp && stamp->transform.visible, "the stamp draws after its slam");
        check(scene.validate().empty(), "the redacted scene validates");
        bool threw = false;
        {
            FakeContentHost h2;
            TemplateScene s2("v", 30.f, h2, 1920.f, 1080.f);
            RedactedSpec bad = spec;
            bad.bars[0].x = 0.9f; // 0.9 + 0.8 overflows the card
            try { (void) addRedactedDocument(s2, bad); } catch (const std::invalid_argument&) { threw = true; }
        }
        check(threw, "an overflowing bar rect throws");
        check(std::string(redactedId()) == "docfx_redacted_v1", "redacted id is stable");
    }

    void leaderBeatsDown() {
        section("film leader");
        FilmLeaderSpec spec;
        check(filmLeaderFrames(spec) == 5 * 15 + 30, "leader length is beats plus start card");
        FakeContentHost host;
        TemplateScene scene("leader", 30.f, host, 1920.f, 1080.f);
        const auto layers = addFilmLeader(scene, spec);
        check(layers.field != 0 && layers.startCard != 0, "field and start card are authored");
        const FrameSubmission first = scene.submit(2);
        const FrameSubmission third = scene.submit(2 * 15 + 2);
        const FrameSubmission start = scene.submit(5 * 15 + 5);
        bool five = false, three = false;
        for (const auto& layer : first.layers)
            if (layer.content.id == "text/5@420") five = true;
        for (const auto& layer : third.layers)
            if (layer.content.id == "text/3@420") three = true;
        check(five && three, "numerals 5 and 3 draw on their beats");
        const BoundLayer* card = findLayer(start, layers.startCard);
        check(card && card->transform.visible, "the start card draws after the beats");
        check(scene.validate().empty(), "the leader scene validates");
        bool threw = false;
        {
            FakeContentHost h2;
            TemplateScene s2("v", 30.f, h2, 1920.f, 1080.f);
            FilmLeaderSpec bad = spec;
            bad.startNumber = 0;
            try { (void) addFilmLeader(s2, bad); } catch (const std::invalid_argument&) { threw = true; }
        }
        check(threw, "a zero start number throws");
        check(std::string(filmLeaderId()) == "docfx_film_leader_v1", "leader id is stable");
    }

    void routeDrawsAndTravels() {
        section("route drawing");
        RouteSpec spec;
        spec.waypoints = {{400.f, 800.f, "ROME"}, {960.f, 540.f, "NAPLES"}, {1500.f, 300.f, "PALERMO"}};
        check(routeTravelFrames(spec) == 60, "two legs take 60 frames");
        const auto p0 = routePosition(spec, 0);
        checkNear(p0.x, 400.f, 1e-4f, "route starts at ROME");
        const auto p1 = routePosition(spec, 55);
        check(p1.x > 960.f && p1.x < 1500.f, "the traveler rides the second leg");
        const auto pEnd = routePosition(spec, 500);
        checkNear(pEnd.x, 1500.f, 1e-4f, "route ends at PALERMO");
        FakeContentHost host;
        TemplateScene scene("route", 30.f, host, 1920.f, 1080.f);
        const auto layers = addRouteDrawing(scene, spec);
        check(layers.card != 0 && layers.traveler != 0, "plate and traveler are authored");
        check(host.findShapeRequest("route_dot_0_0") != nullptr, "trail dots exist");
        const FrameSubmission mid = scene.submit(40);
        const BoundLayer* traveler = findLayer(mid, layers.traveler);
        check(traveler && traveler->transform.visible, "the traveler draws mid-route");
        check(scene.validate().empty(), "the route scene validates");
        bool threw = false;
        {
            FakeContentHost h2;
            TemplateScene s2("v", 30.f, h2, 1920.f, 1080.f);
            RouteSpec bad = spec;
            bad.waypoints.clear();
            try { (void) addRouteDrawing(s2, bad); } catch (const std::invalid_argument&) { threw = true; }
        }
        check(threw, "an empty waypoint list throws");
        check(std::string(routeDrawingId()) == "docfx_route_drawing_v1", "route id is stable");
    }

    void countersFlipAndScrub() {
        section("animated counters");
        CounterSpec spec;
        spec.startValue = 0;
        spec.endValue = 100;
        spec.steps = 10;
        spec.suffix = "%";
        spec.years = {"1960", "1970", "1980"};
        check(counterValue(spec, 0) == 0, "counter starts at 0");
        check(counterValue(spec, 10 + 5 * 9) == 50, "counter reads 50 halfway");
        check(counterValue(spec, 500) == 100, "counter lands on 100");
        check(counterText(spec, 500) == "100%", "counter text carries the suffix");
        checkNear(rulerProgress(spec, 10), 0.f, 1e-6f, "ruler starts at 0");
        checkNear(rulerProgress(spec, 10 + 90), 1.f, 1e-6f, "ruler ends at 1");
        FakeContentHost host;
        TemplateScene scene("counters", 30.f, host, 1920.f, 1080.f);
        const auto layers = addAnimatedCounters(scene, spec);
        check(layers.ruler != 0 && layers.cursor != 0, "rail and cursor are authored");
        const FrameSubmission mid = scene.submit(55);
        bool fifty = false;
        for (const auto& layer : mid.layers)
            if (layer.content.id == "text/50%@120") fifty = true;
        check(fifty, "the 50% step draws mid-window");
        check(scene.validate().empty(), "the counters scene validates");
        bool threw = false;
        {
            FakeContentHost h2;
            TemplateScene s2("v", 30.f, h2, 1920.f, 1080.f);
            CounterSpec bad = spec;
            bad.steps = 0;
            try { (void) addAnimatedCounters(s2, bad); } catch (const std::invalid_argument&) { threw = true; }
        }
        check(threw, "zero steps throw");
        check(std::string(animatedCountersId()) == "docfx_animated_counters_v1",
              "counters id is stable");
    }

} // namespace

int main() {
    redactedRetractsAndStamps();
    leaderBeatsDown();
    routeDrawsAndTravels();
    countersFlipAndScrub();
    return chrononmotion_test::report();
}
