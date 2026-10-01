#include "chronontemplate/NativePrimitives.hpp"

#include <algorithm>
#include <cmath>
#include <iostream>
#include <stdexcept>

namespace {
    int failures=0;
    void check(bool ok, const char* message) {
        if (!ok) { std::cerr << "FAIL: " << message << '\n'; ++failures; }
    }
    template<class F> void throws(F&& action, const char* message) {
        try { action(); check(false,message); } catch (const std::invalid_argument&) {}
    }
}

int main() {
    using namespace chronontemplate::native;
    const auto color=Material::rgba("#173A2B");
    check(std::abs(color[0]-23.f/255.f)<1e-6f && std::abs(color[3]-1.f)<1e-6f,"hex color converts to RGBA");
    const auto box=Geometry::box(2,4,6);
    check(Effects::noise(0.05f,7).at("seed")==7,"effect primitive preserves deterministic seed");
    check(box.at("vertices").size()==24 && box.at("indices").size()==36,"box emits six indexed flat-shaded faces");
    check(Geometry::boxLayer("box",{2,4,6},{0,0,0},"#173A2B",12).at("type")=="mesh","box layer is 3D render-plan mesh");
    const auto path=Paths::polyline({{0,0},{10,5}});
    const auto stroke=Paths::strokeLayer("stroke",path,2,8,12);
    check(stroke.at("shape").at("operators")[0].at("kind")=="trim","stroke uses native animated trim");
    check(Motion::track("opacity",{{0,0},{4,1}}).at("keyframes").size()==2,"motion track preserves keys");
    check(Camera::perspective().at("type")=="perspective","camera builder emits perspective camera");
    const auto dust=Particles::emitterLayer("dust",4,17,12,{1,1},{0,-2},{1,0},{0.1f,0.5f},{1,2},
        {{{"position",0},{"color",{1,1,1,0}}},{{"position",1},{"color",{1,1,1,1}}}});
    check(dust.at("particle_emitter").at("seed")==17,"particle emitter retains deterministic seed");
    check(Text::layer("label","Chronon",{0,0,0},{200,50},"font.ttf",32,"#FFF",12).at("text")=="Chronon","text builder carries native text request");
    const auto plan=buildBlackboardTortureV1();
    check(plan.at("layers").size()==47,"blackboard composes 47 native plan layers");
    check(plan.at("camera_animation").at("tracks").size()==2,"blackboard includes camera push and drift");
    check(plan.at("canvas").at("duration_frames")==240,"blackboard duration is ten seconds at 24 fps");
    const auto circle=std::find_if(plan.at("layers").begin(),plan.at("layers").end(),
        [](const Json& layer) { return layer.value("id","")=="chalk_circle"; });
    check(circle!=plan.at("layers").end(),"blackboard includes the chalk circle");
    if (circle!=plan.at("layers").end()) {
        const auto& tracks=circle->at("animation").at("tracks");
        check(std::count_if(tracks.begin(),tracks.end(),[](const Json& track) {
            return track.value("property","")=="opacity";
        })==1,"chalk circle composes entrance and erase into one opacity track");
        const auto& keys=tracks.front().at("keyframes");
        check(keys.back().at("frame")==239 && keys.back().at("value")==0.f,
              "chalk circle opacity closes exactly at the final frame");
    }
    throws([] { (void)Geometry::box(0,1,1); },"zero-sized mesh is rejected");
    throws([] { (void)Motion::track("opacity",{{2,0},{1,1}}); },"unordered motion keys are rejected");
    throws([] { (void)Motion::track("opacity",{{0,"not-a-number"}}); },"non-numeric motion values are rejected");
    throws([&] { (void)TemplateComposition::renderPlan("dup",320,180,24,1,{stroke,stroke}); },"duplicate composition ids are rejected");
    auto duplicateTracks=stroke;
    duplicateTracks["animation"]["tracks"].push_back(Motion::track("opacity",{{0,1},{4,0}}));
    throws([&] { (void)TemplateComposition::renderPlan("duplicate-track",320,180,24,12,{duplicateTracks}); },
           "duplicate per-layer animation properties are rejected before RenderPlan emission");
    return failures==0 ? 0 : 1;
}
