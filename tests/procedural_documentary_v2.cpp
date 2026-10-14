#include "chronontemplate/backgrounds/ProceduralBackground.hpp"
#include "chronontemplate/elements/HighlightingV2.hpp"
#include <chronon3d/graphics/field2d.hpp>
#include <chrononmotion/motion/Procedural.hpp>
#include <cmath>
#include <iostream>
#include <limits>
#include <stdexcept>

namespace {
int failures=0;
void check(bool ok,const char* message) {
    if (!ok) { std::cerr<<"FAIL: "<<message<<'\n'; ++failures; }
}
template<class F> void rejects(F f) {
    try { f(); check(false,"invalid input accepted"); }
    catch (const std::invalid_argument&) {}
}
}
int main() {
    using namespace chronontemplate::native;
    using namespace chronon3d::graphics;
    Field2D field;
    field.seed=12045;
    for (auto generator:{Field2DGenerator::Perlin,Field2DGenerator::Simplex,
                         Field2DGenerator::Value,Field2DGenerator::Ridged,Field2DGenerator::Fractal}) {
        field.generator=generator;
        for (unsigned i=0;i<100;++i) {
            const float x=i*.031f;
            const float value=field.sample({x,.371f});
            check(std::isfinite(value) && value>=0.f && value<=1.f,"bounded deterministic samples");
            check(value==field.sample({x,.371f}),"repeat sample parity");
        }
    }
    field.generator=Field2DGenerator::Linear;
    field.operators={{.kind=Field2DOperatorKind::Quantize,.scalar=4.f}};
    check(std::abs(field.sample({.4f,.5f})-1.f/3.f)<1e-6f,"quantize levels");
    const auto fingerprint=field2d_fingerprint(field);
    field.transform.pivot.x=.7f;
    check(fingerprint!=field2d_fingerprint(field),"pivot participates in content fingerprint");
    using chrononmotion::Vector2;
    const auto line=chrononmotion::motion::integrateFlow(Vector2(0,0),100,10,0,
        [](const Vector2&,float) {return Vector2(1,0);});
    check(line.size()==11 && std::abs(line.back().x-100.f)<1e-6f,"midpoint straight-line integration");
    Field2D shared;
    const auto consumer=[&](const Vector2& p,float t) {
        const auto drifted=shared.drifted(t,{.02f,0.f});
        const float v=drifted.sample({p.x,p.y});
        auto rasterField=shared;
        rasterField.transform.translation.x=static_cast<float>(static_cast<double>(.02f)*t);
        check(v==rasterField.sample({p.x,p.y}),"Motion callback and raster share samples");
        return Vector2(std::cos(v),std::sin(v));
    };
    const auto flow=chrononmotion::motion::integrateFlow(Vector2(.1f,.2f),1.f,32,2.f,consumer);
    const auto again=chrononmotion::motion::integrateFlow(Vector2(.1f,.2f),1.f,32,2.f,consumer);
    check(flow.back().x==again.back().x && flow.back().y==again.back().y,"random-access flow determinism");
    rejects([]{(void)chrononmotion::motion::integrateFlow(Vector2(),1,0,0,{});});
    rejects([]{(void)chrononmotion::motion::integrateFlow(Vector2(),1,1,0,
        [](const Vector2&,float){return Vector2(std::numeric_limits<float>::quiet_NaN(),0.f);});});
    const auto contours=chrononmotion::motion::contourSegments(100,100,10,10,.5f,
        [](const Vector2& p){return p.x/100.f;});
    check(contours.size()==10,"linear scalar field yields ten aligned contour segments");
    for (const auto& segment:contours)
        check(std::abs(segment[0].x-50.f)<1e-6f && std::abs(segment[1].x-50.f)<1e-6f,
              "contours follow iso-values, not arbitrary flow paths");
    rejects([]{(void)chrononmotion::motion::contourSegments(100,100,0,10,.5f,{});});
    const auto grain=grainBands({{1.5f,.45f},{5.f,.35f},{22.f,.2f}},.16f,12045);
    check(grain.size()==3 && grain[0]["seed"]!=grain[1]["seed"],"independent band seeds");
    check(grain[0]["size"]==1.5f && grain[2]["size"]==22.f,"characteristic pixel sizes preserved");
    rejects([]{(void)grainBands({},.1f,1);});
    rejects([]{(void)grainBands({{2,0}},.1f,1);});
    rejects([]{(void)grainBands({{0,1}},.1f,1);});
    for (const auto& preset:proceduralBackgroundPresets()) {
        ProceduralBackgroundSpec s; s.preset=preset;
        const auto plan=proceduralBackground(s);
        check(plan==proceduralBackground(s),"repeat plan byte-equivalent");
        check(plan["canvas"]["width"]==1920 && plan["canvas"]["height"]==1080 &&
              plan["canvas"]["duration_frames"]==150,"1080p 5-second delivery contract");
        s.seed++;
        check(plan!=proceduralBackground(s),"seed changes authored output");
    }
    rejects([]{ProceduralBackgroundSpec s;s.preset="typo";(void)proceduralBackground(s);});
    ProceduralBackgroundSpec configured;configured.preset="light_fibers";configured.lineCount=2;
    configured.lineColor="#FF0000";configured.lineOpacity=.7f;configured.tailFraction=.4f;
    configured.glowRadius=8.f;configured.blurRadius=2.f;configured.orientationRadians=1.f;
    const auto tuned=proceduralBackground(configured);
    const auto& tunedLine=tuned["layers"][1];
    check(tunedLine["shape"]["stroke"]["color"]=="#FF0000" && tunedLine["opacity"]==.7f,
          "line color and opacity controls reach native stroke");
    check(tunedLine["effects"].size()==2,"glow and blur are independent native effects");
    check(tunedLine["shape"]["operators"][0]["params"]["animation"]["keyframes"][1]["value"][0]==.6f,
          "tail and reveal share canonical trim animation");
    rejects([]{ProceduralBackgroundSpec s;s.tailFraction=0;(void)proceduralBackground(s);});
    check(highlightingPresets().size()==28,"28 documentary style configurations");
    const HighlightRegion source{100,50,300,100};
    const auto mapped=source.mapped({200,100,1000,500},2000,1000);
    check(mapped.x==250 && mapped.y==125 && mapped.width==150 && mapped.height==50,
          "source-image region maps to display coordinates");
    rejects([&]{(void)source.mapped({0,0,10,10},10,10);});
    const auto span=highlightSpan("Caffè evidence",0,6,"accent",highlightingStyle("marker_soft"));
    check(span["start"]==0 && span["end"]==6,"text targets retain UTF-8 byte ranges");
    check(span["style"]["highlight"]["background"]=="#E8B84A59","marker alpha is retained in native span");
    check(focusDim({100,100,300,200},.5f,150)[0]["position"]==Json::array({0.f,0.f}),
          "native color regions use top-left origin");
    rejects([]{(void)highlightSpan("Caffè",0,5,"accent",HighlightStyle{});});
    rejects([]{(void)highlightingStyle("unknown");});
    const auto underline=highlightStroke("u",{{0,0},{100,0}},highlightingStyle("underline_clean"),0,15,150,100);
    check(std::abs(underline["shape"]["stroke"]["width"].get<float>()-6.f)<1e-5f,"font-relative stroke width");
    check(focusDim({100,100,300,200},.5f,150).size()==4,"focus dims only outside region");
    rejects([]{(void)focusDim({-1,0,300,200},.5f,150);});
    check(highlightRegionLayers("double",{100,100,300,40},"marker_double").size()==2,
          "double marker layers share primitive implementation");
    check(calloutConnector("arrow",{100,100},{300,200},"callout_arrow")["shape"]["path"].size()==5,
          "connector adds directional arrowhead");
    check(focusPolygon({{100,100},{400,100},{300,300}},.5f,150)["masks"][0]["mode"]=="subtract",
          "arbitrary spotlight uses canonical subtract mask");
    // ── Highlighting 2.0 gaps: reveal easings, gradient stroke, groups ──
    const HighlightTiming base{0,30,150,12045};
    const auto drawOp=revealAnimation(RevealMode::Draw,base);
    const auto wipeOp=revealAnimation(RevealMode::Wipe,base);
    const auto scribbleOp=revealAnimation(RevealMode::Scribble,base);
    const auto sweepOp=revealAnimation(RevealMode::Sweep,base);
    const auto traceOp=revealAnimation(RevealMode::Trace,base);
    check(drawOp["params"]["animation"]["easing"]=="ease_in_out","draw uses eased reveal");
    check(wipeOp["params"]["animation"]["easing"]=="linear","wipe uses linear reveal");
    check(sweepOp["params"]["animation"]["easing"]=="ease_out","sweep uses ease-out");
    check(traceOp["params"]["animation"]["easing"]=="ease_in_out","trace uses ease-in-out");
    check(scribbleOp==wipeOp || scribbleOp["params"]["animation"]["easing"]=="linear",
          "scribble trim stays decoder-safe");
    rejects([&]{(void)revealAnimation(RevealMode::Pulse,base);});
    rejects([&]{(void)revealAnimation(RevealMode::Stagger,base);});
    const auto grad=highlightStrokeGradient("g",{{0,0},{100,0}},"#FFFFFF","#72CFFF",
        highlightingStyle("underline_clean"),0,15,150,100);
    check(grad["shape"]["stroke"]["color"]["type"]=="linear","gradient stroke carries linear ramp");
    check(grad["shape"]["stroke"]["color"]["color_stops"].size()==2,"two gradient stops");
    check(grad["shape"]["stroke"].contains("taper_start"),"variable-width taper present");
    rejects([]{(void)highlightStrokeGradient("g",{{0,0}},"#FFFFFF","#72CFFF",HighlightStyle{},0,15,150);});
    rejects([]{(void)highlightStrokeGradient("g",{{0,0},{1,1}},"#ZZZZZZ","#72CFFF",HighlightStyle{},0,15,150);});
    HighlightGroup grp; grp.staggerFrames=8;
    grp.targets.push_back({"a","s0",0,1,{100,100,300,40}});
    grp.targets.push_back({"b","s1",0,1,{100,200,300,40}});
    const auto grouped=highlightGroupLayers("grp",grp,"marker_soft",base);
    check(grouped.size()==2,"staggered group emits one stack per target");
    check(grouped[0]["id"]=="grp_g0" && grouped[1]["id"]=="grp_g1","group ids stay unique");
    rejects([]{(void)highlightGroupLayers("e",HighlightGroup{},"marker_soft",HighlightTiming{});});
    rejects([&]{HighlightGroup big; big.staggerFrames=140;
        big.targets.push_back({"a","s",0,1,{0,0,10,10}}); big.targets.push_back({"b","s",0,1,{0,0,10,10}});
        (void)highlightGroupLayers("e",big,"marker_soft",base);});
    // ── Cinematic premium PathStroke: multi-layer glow + deterministic head ──
    CinematicGlowSpec glow; glow.tailFraction=.75f;
    const std::vector<Paths::Point> path{{100,500},{600,500},{900,300}};
    const auto cine=cinematicPathStroke("glow",path,glow,base);
    check(cine.size()==5,"core + two halos + head halo + head core");
    check(cine[0]["shape"]["stroke"]["width"]==36.f,"wide halo carries ambient dispersion");
    check(cine[1]["shape"]["stroke"]["width"]==12.f,"tight halo carries saturated color");
    check(cine[2]["shape"]["stroke"]["width"]==2.f,"white core stays razor-sharp");
    check(cine[2]["shape"]["stroke"]["cap"]=="round","round caps for smooth path");
    check(cine[1].contains("effects") && cine[0].contains("effects"),"halos bloom in linear space");
    check(!cine[2].contains("effects"),"core has no blur (precision vs light)");
    check(cine[4]["shape"]["type"]=="ellipse","light head is an ellipse node");
    check(cine[4]["animation"]["tracks"][0]["property"]=="position","head follows arc-length");
    check(cine==cinematicPathStroke("glow",path,glow,base),"repeat premium stroke byte-equivalent");
    CinematicGlowSpec noHead; noHead.headEnabled=false;
    check(cinematicPathStroke("g2",path,noHead,base).size()==3,"head toggle removes two layers");
    CinematicGlowSpec other=glow; other.haloColor="#FF0000";
    check(cine!=cinematicPathStroke("glow",path,other,base),"halo color changes output");
    rejects([&]{CinematicGlowSpec bad; bad.coreWidth=0;(void)cinematicPathStroke("x",path,bad,base);});
    rejects([&]{(void)cinematicPathStroke("",path,glow,base);});
    rejects([&]{(void)cinematicPathStroke("x",{{0,0}},glow,base);});
    return failures?1:0;
}
