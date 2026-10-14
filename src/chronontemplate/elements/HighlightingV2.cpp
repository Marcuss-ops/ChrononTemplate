#include "chronontemplate/elements/HighlightingV2.hpp"
#include <algorithm>
#include <cmath>
#include <stdexcept>

namespace chronontemplate::native {
namespace {
void validateRegion(const HighlightRegion& r) {
    if (!std::isfinite(r.x) || !std::isfinite(r.y) || !std::isfinite(r.width) ||
        !std::isfinite(r.height) || r.width<=0 || r.height<=0)
        throw std::invalid_argument("highlight region must be finite with positive dimensions");
}
void validateStyle(const HighlightStyle& s) {
    (void)Material::rgba(s.color,s.opacity);
    if (!std::isfinite(s.width) || s.width<=0 || s.width>256 ||
        !std::isfinite(s.widthEm) || s.widthEm<0 || s.widthEm>4)
        throw std::invalid_argument("highlight width outside supported range");
}
}
HighlightRegion HighlightRegion::mapped(const HighlightRegion& display,float sw,float sh) const {
    validateRegion(*this); validateRegion(display);
    if (!std::isfinite(sw) || !std::isfinite(sh) || sw<=0 || sh<=0 ||
        x<0 || y<0 || x+width>sw || y+height>sh)
        throw std::invalid_argument("source highlight exceeds source image");
    return {display.x+x*display.width/sw,display.y+y*display.height/sh,
            width*display.width/sw,height*display.height/sh};
}
std::vector<std::string> highlightingPresets() {
    return {"marker_soft","marker_rough","marker_double","marker_ink",
        "underline_clean","underline_wave","underline_glow","underline_scribble",
        "box_outline","box_scan","box_corner","box_pulse",
        "focus_dim","focus_zoom","focus_tracking","focus_vignette",
        "evidence_red","archive_yellow","document_scan","investigation_circle",
        "word_emphasis","phrase_highlight","typewriter_focus","data_emphasis",
        "callout_elbow","callout_curve","callout_arrow","callout_trace"};
}
HighlightStyle highlightingStyle(const std::string& preset) {
    const auto presets=highlightingPresets();
    if (std::find(presets.begin(),presets.end(),preset)==presets.end())
        throw std::invalid_argument("unknown highlighting preset");
    HighlightStyle s;
    s.rough=preset=="marker_rough" || preset=="underline_scribble" || preset=="marker_ink";
    s.glow=preset=="underline_glow";
    s.dashed=preset=="box_scan" || preset=="document_scan";
    if (preset.rfind("underline",0)==0) {s.opacity=1.f;s.widthEm=.06f;}
    if (preset=="evidence_red" || preset=="investigation_circle") {s.color="#E03B2F";s.opacity=.9f;}
    if (preset.rfind("callout",0)==0 || preset.rfind("box",0)==0) {s.color="#72CFFF";s.opacity=.9f;}
    return s;
}
Json highlightSpan(const std::string& text,std::size_t start,std::size_t end,
                    const std::string& semanticId,const HighlightStyle& s) {
    validateStyle(s);
    const auto boundary=[&](std::size_t offset) {
        return offset==text.size() || (static_cast<unsigned char>(text[offset])&0xc0U)!=0x80U;
    };
    if (start>=end || end>text.size() || !boundary(start) || !boundary(end) ||
        semanticId.empty() || semanticId.size()>256)
        throw std::invalid_argument("highlight span requires valid UTF-8 byte boundaries and semantic identity");
    // Native shaping is the sole authority for glyph positions and wrapping.
    constexpr char digits[]="0123456789ABCDEF";
    const auto alpha=static_cast<unsigned>(std::lround(s.opacity*255.f));
    std::string background=s.color;
    background.push_back(digits[alpha>>4]);
    background.push_back(digits[alpha&15]);
    return {{"start",start},{"end",end},{"semantic_id",semanticId},
        {"style",{{"highlight",{{"background",background},{"padding_em",.08f},{"radius_em",.04f}}}}}};
}
Json highlightStroke(const std::string& id,const std::vector<Paths::Point>& points,
                      const HighlightStyle& s,int start,int end,int frames,float fontSize,unsigned seed) {
    validateStyle(s);
    if (!std::isfinite(fontSize) || fontSize<=0 || start<0 || end>=frames)
        throw std::invalid_argument("highlight timing or font size invalid");
    const float width=s.widthEm>0?s.widthEm*fontSize:s.width;
    auto layer=Paths::strokeLayer(id,Paths::polyline(points),start,end,frames,s.color,width);
    layer["opacity"]=s.opacity;
    auto& stroke=layer["shape"]["stroke"];
    stroke["cap"]="butt";
    if (s.dashed) stroke["dash_array"]={8,5};
    if (s.rough) stroke["brush"]={{"size",width},{"width_jitter",.12f},
        {"edge_noise",.12f},{"grain",.1f},{"seed",seed},
        {"texture",{{"generator","perlin"},{"seed",seed},{"frequency",4.f}}}};
    if (s.glow) layer["effects"]=Json::array({{{"type","bloom"},{"threshold",.2f},
        {"radius",12.f},{"intensity",.8f}}});
    return layer;
}
namespace {
float easeInOut(float p) {
    p=std::clamp(p,0.f,1.f);
    return p*p*(3.f-2.f*p);
}
Json rgbaArray(const std::string& hex,float alpha=1.f) {
    const auto c=Material::rgba(hex,alpha);
    return Json::array({c[0],c[1],c[2],c[3]});
}
Paths::Point samplePolyline(const std::vector<Paths::Point>& pts,float u) {
    if (pts.size()<2) throw std::invalid_argument("polyline needs 2+ points");
    u=std::clamp(u,0.f,1.f);
    std::vector<double> cum{0.0};
    double total=0.0;
    for (std::size_t i=1;i<pts.size();++i) {
        const double dx=pts[i][0]-pts[i-1][0], dy=pts[i][1]-pts[i-1][1];
        total+=std::hypot(dx,dy);
        cum.push_back(total);
    }
    if (total<=1.e-9) return pts.front();
    const double target=static_cast<double>(u)*total;
    for (std::size_t i=1;i<pts.size();++i) {
        if (target<=cum[i]) {
            const double seg=cum[i]-cum[i-1];
            const double f=seg>1.e-12?(target-cum[i-1])/seg:0.0;
            return {static_cast<float>(pts[i-1][0]+(pts[i][0]-pts[i-1][0])*f),
                    static_cast<float>(pts[i-1][1]+(pts[i][1]-pts[i-1][1])*f)};
        }
    }
    return pts.back();
}
void applyTail(Json& layer,float tailFraction,int start,int revealEnd) {
    if (tailFraction>=1.f) return;
    auto& keys=layer["shape"]["operators"][0]["params"]["animation"]["keyframes"];
    keys=Json::array({{{"frame",start},{"value",{0.f,0.f}}},
        {{"frame",revealEnd},{"value",{1.f-tailFraction,1.f}}}});
}
} // namespace
Json highlightStrokeGradient(const std::string& id,const std::vector<Paths::Point>& points,
                              const std::string& fromColor,const std::string& toColor,
                              const HighlightStyle& s,int start,int end,int frames,
                              float fontSize,unsigned seed) {
    validateStyle(s);
    (void)Material::rgba(fromColor,s.opacity);
    (void)Material::rgba(toColor,s.opacity);
    if (points.size()<2) throw std::invalid_argument("gradient stroke needs 2+ points");
    auto layer=highlightStroke(id,points,s,start,end,frames,fontSize,seed);
    auto& stroke=layer["shape"]["stroke"];
    stroke["color"]={{"type","linear"},{"start",{0,0}},{"end",{1,0}},
        {"color_stops",Json::array({{{"position",0.f},{"color",rgbaArray(fromColor,s.opacity)}},
            {{"position",1.f},{"color",rgbaArray(toColor,s.opacity)}}})}};
    // Taper slightly at both ends so sub-pixel lines stay antialiased.
    stroke["taper_start"]=.85f;
    stroke["taper_end"]=.85f;
    return layer;
}
Json highlightGroupLayers(const std::string& id,const HighlightGroup& group,
                           const std::string& preset,const HighlightTiming& base) {
    if (group.targets.empty() || group.targets.size()>64)
        throw std::invalid_argument("highlight group needs 1..64 targets");
    if (group.staggerFrames<1 || group.staggerFrames>120)
        throw std::invalid_argument("stagger must be in [1,120] frames");
    if (base.start<0 || base.revealEnd<=base.start || base.revealEnd>=base.frames)
        throw std::invalid_argument("invalid base reveal interval");
    (void)highlightingStyle(preset);
    Json layers=Json::array();
    for (std::size_t i=0;i<group.targets.size();++i) {
        const auto& target=group.targets[i];
        validateRegion(target.region);
        const int start=base.start+static_cast<int>(i)*group.staggerFrames;
        const int revealEnd=base.revealEnd+static_cast<int>(i)*group.staggerFrames;
        if (revealEnd>=base.frames)
            throw std::invalid_argument("staggered reveal overflows frame budget");
        HighlightTiming t{start,revealEnd,base.frames,base.seed+static_cast<unsigned>(i)};
        auto stack=highlightRegionLayers(id+"_g"+std::to_string(i),target.region,preset,t);
        for (auto& layer:stack) layers.push_back(std::move(layer));
    }
    return layers;
}
Json cinematicPathStroke(const std::string& id,const std::vector<Paths::Point>& points,
                          const CinematicGlowSpec& spec,const HighlightTiming& t) {
    if (points.size()<2 || points.size()>4096)
        throw std::invalid_argument("cinematic path needs 2..4096 points");
    for (const auto& p:points)
        if (!std::isfinite(p[0]) || !std::isfinite(p[1]))
            throw std::invalid_argument("cinematic path points must be finite");
    (void)Material::rgba(spec.coreColor);
    (void)Material::rgba(spec.haloColor);
    (void)Material::rgba(spec.wideColor);
    if (!std::isfinite(spec.coreWidth) || spec.coreWidth<.5f || spec.coreWidth>8.f ||
        !std::isfinite(spec.haloWidth) || spec.haloWidth<2.f || spec.haloWidth>64.f ||
        !std::isfinite(spec.wideWidth) || spec.wideWidth<8.f || spec.wideWidth>128.f ||
        !std::isfinite(spec.headRadius) || spec.headRadius<1.f || spec.headRadius>32.f ||
        !std::isfinite(spec.tailFraction) || spec.tailFraction<=0.f || spec.tailFraction>1.f ||
        !std::isfinite(spec.glowIntensity) || spec.glowIntensity<0.f || spec.glowIntensity>2.f ||
        !std::isfinite(spec.bloomThreshold) || spec.bloomThreshold<0.f || spec.bloomThreshold>1.f)
        throw std::invalid_argument("cinematic glow parameters outside supported ranges");
    if (t.start<0 || t.revealEnd<=t.start || t.revealEnd>=t.frames)
        throw std::invalid_argument("invalid reveal interval");
    if (id.empty()) throw std::invalid_argument("layer id must not be empty");
    auto commands=Paths::polyline(points);
    Json layers=Json::array();
    // Wide diffuse halo (ambient dispersion).
    auto wide=Paths::strokeLayer(id+"_wide",commands,t.start,t.revealEnd,t.frames,
        spec.wideColor,spec.wideWidth);
    wide["shape"]["stroke"]["cap"]="round";
    wide["shape"]["stroke"]["join"]="round";
    wide["opacity"]=.24f;
    wide["effects"]=Json::array({{{"type","bloom"},{"threshold",spec.bloomThreshold},
        {"radius",spec.wideWidth},{"intensity",spec.glowIntensity*.6f}}});
    applyTail(wide,spec.tailFraction,t.start,t.revealEnd);
    layers.push_back(std::move(wide));
    // Tight saturated halo.
    auto halo=Paths::strokeLayer(id+"_halo",commands,t.start,t.revealEnd,t.frames,
        spec.haloColor,spec.haloWidth);
    halo["shape"]["stroke"]["cap"]="round";
    halo["shape"]["stroke"]["join"]="round";
    halo["opacity"]=.68f;
    halo["effects"]=Json::array({{{"type","bloom"},{"threshold",spec.bloomThreshold},
        {"radius",spec.haloWidth},{"intensity",spec.glowIntensity}}});
    applyTail(halo,spec.tailFraction,t.start,t.revealEnd);
    layers.push_back(std::move(halo));
    // Razor-sharp white core (precision geometry, no blur).
    auto core=Paths::strokeLayer(id+"_core",commands,t.start,t.revealEnd,t.frames,
        spec.coreColor,spec.coreWidth);
    core["shape"]["stroke"]["cap"]="round";
    core["shape"]["stroke"]["join"]="round";
    core["opacity"]=1.f;
    applyTail(core,spec.tailFraction,t.start,t.revealEnd);
    layers.push_back(std::move(core));
    if (spec.headEnabled) {
        // Deterministic head: arc-length position + ease_in_out acceleration.
        // Pure function of frame; no dependency on previous frames.
        std::vector<Keyframe> posKeys, opaKeys;
        const int span=t.revealEnd-t.start;
        for (int f=t.start;f<t.revealEnd;f+=3) {
            const float p=easeInOut(static_cast<float>(f-t.start)/static_cast<float>(span));
            const auto pos=samplePolyline(points,p);
            posKeys.push_back({f,{pos[0],pos[1]}});
        }
        posKeys.push_back({t.revealEnd,{points.back()[0],points.back()[1]}});
        // Hold head at the node after arrival, then fade with the scene.
        if (spec.pulseEnabled) {
            opaKeys.push_back({t.start,.0f});
            opaKeys.push_back({t.start+std::max(1,span/4),1.f});
            opaKeys.push_back({t.revealEnd,1.f});
            opaKeys.push_back({t.frames-1,.9f});
        }
        const float d=spec.headRadius*2.f;
        Json headCore={{"id",id+"_head_core"},{"type","shape"},
            {"shape",{{"type","ellipse"},{"fill",rgbaArray(spec.coreColor,1.f)}}},
            {"size",{d,d}},{"position",{points.front()[0],points.front()[1]}},
            {"start_frame",t.start},{"duration_frames",t.frames-t.start}};
        Json headHalo={{"id",id+"_head_halo"},{"type","shape"},
            {"shape",{{"type","ellipse"},{"fill",rgbaArray(spec.haloColor,.75f)}}},
            {"size",{d*2.f,d*2.f}},{"position",{points.front()[0],points.front()[1]}},
            {"start_frame",t.start},{"duration_frames",t.frames-t.start}};
        headHalo["effects"]=Json::array({{{"type","bloom"},{"threshold",spec.bloomThreshold},
            {"radius",spec.haloWidth},{"intensity",spec.glowIntensity}}});
        Json tracks=Json::array({Motion::track("position",posKeys,"linear")});
        if (!opaKeys.empty()) tracks.push_back(Motion::track("opacity",opaKeys,"in_out_sine"));
        headCore["animation"]={{"tracks",tracks}};
        headHalo["animation"]={{"tracks",tracks}};
        layers.push_back(std::move(headHalo));
        layers.push_back(std::move(headCore));
    }
    return layers;
}
Json revealAnimation(RevealMode mode,const HighlightTiming& t,const Json& targetPath) {
    if (t.start<0 || t.revealEnd<=t.start || t.revealEnd>=t.frames)
        throw std::invalid_argument("invalid reveal interval");
    if (mode==RevealMode::Morph) {
        if (!targetPath.is_array() || targetPath.empty()) throw std::invalid_argument("morph needs target path");
        return {{"kind","morph"},{"params",{{"target",targetPath},{"animation",{
            {"easing","in_out_sine"},{"keyframes",Json::array({{{"frame",t.start},{"value",0.f}},
                {{"frame",t.revealEnd},{"value",1.f}}})}}}}}};
    }
    auto trim=Paths::trim(t.start,t.revealEnd);
    auto& params=trim["params"];
    auto& anim=params["animation"];
    auto& keys=anim["keyframes"];
    if (mode==RevealMode::Draw) {
        anim["easing"]="in_out_sine";
    } else if (mode==RevealMode::Wipe) {
        anim["easing"]="linear";
    } else if (mode==RevealMode::Scribble) {
        // Hand-drawn wobble lives in the layer brush (highlightStroke rough);
        // the trim operator stays decoder-safe and deterministic.
        anim["easing"]="linear";
    } else if (mode==RevealMode::Expand) {
        params["start"]=.5f;params["end"]=.5f;
        anim["easing"]="in_out_sine";
        keys=Json::array({{{"frame",t.start},{"value",{.5f,.5f}}},
                         {{"frame",t.revealEnd},{"value",{0.f,1.f}}}});
    } else if (mode==RevealMode::Sweep) {
        anim["easing"]="out_sine";
        keys=Json::array({{{"frame",t.start},{"value",{0.f,0.f}}},
                         {{"frame",t.revealEnd},{"value",{.85f,1.f}}}});
    } else if (mode==RevealMode::Trace) {
        anim["easing"]="in_out_sine";
        keys=Json::array({{{"frame",t.start},{"value",{0.f,0.f}}},
                         {{"frame",t.revealEnd},{"value",{.85f,1.f}}}});
    } else if (mode==RevealMode::Pulse || mode==RevealMode::FocusFollow || mode==RevealMode::Stagger) {
        throw std::invalid_argument("pulse/follow/stagger are layer or group animations, not path operators");
    }
    return trim;
}

Json calloutConnector(const std::string& id,const Paths::Point& from,const Paths::Point& to,
                       const std::string& preset,const HighlightTiming& t) {
    if (preset.rfind("callout_",0)!=0) throw std::invalid_argument("connector preset required");
    auto style=highlightingStyle(preset);
    std::vector<Paths::Point> points{from};
    if (preset=="callout_elbow") points.push_back({to[0],from[1]});
    else if (preset=="callout_curve") {
        for (unsigned i=1;i<32;++i) {
            const float u=i/32.f, v=1-u;
            points.push_back({v*v*from[0]+2*v*u*to[0]+u*u*to[0],
                              v*v*from[1]+2*v*u*from[1]+u*u*to[1]});
        }
    }
    points.push_back(to);
    if (preset=="callout_arrow") {
        const float angle=std::atan2(to[1]-from[1],to[0]-from[0]);
        points.push_back({to[0]-18*std::cos(angle-.45f),to[1]-18*std::sin(angle-.45f)});
        points.push_back(to);
        points.push_back({to[0]-18*std::cos(angle+.45f),to[1]-18*std::sin(angle+.45f)});
    }
    return highlightStroke(id,points,style,t.start,t.revealEnd,t.frames,56,t.seed);
}

Json highlightRegionLayers(const std::string& id,const HighlightRegion& r,
                            const std::string& preset,const HighlightTiming& t) {
    validateRegion(r);
    auto style=highlightingStyle(preset);
    Json layers=Json::array();
    std::vector<Paths::Point> points;
    const bool marker=preset.rfind("marker",0)==0 || preset=="archive_yellow" || preset=="phrase_highlight";
    const bool underline=preset.rfind("underline",0)==0;
    if (marker || underline) {
        style.widthEm=0;
        style.width=marker?r.height*.8f:std::max(1.f,r.height*.06f);
        for (unsigned i=0;i<=64;++i) {
            const float u=i/64.f;
            const float wave=preset=="underline_wave"?std::sin(u*18.849556f)*r.height*.08f:0.f;
            points.push_back({r.x+r.width*u,r.y+(marker?r.height*.5f:r.height+style.width)+wave});
        }
    } else if (preset=="investigation_circle") {
        for (unsigned i=0;i<=96;++i) {
            const float a=i*6.2831853f/96.f;
            points.push_back({r.x+r.width*.5f+r.width*.55f*std::cos(a),
                              r.y+r.height*.5f+r.height*.65f*std::sin(a)});
        }
    } else {
        points={{r.x,r.y},{r.x+r.width,r.y},{r.x+r.width,r.y+r.height},
                {r.x,r.y+r.height},{r.x,r.y}};
    }
    auto stroke=highlightStroke(id,points,style,t.start,t.revealEnd,t.frames,56,t.seed);
    if (preset=="box_pulse" || preset=="data_emphasis")
        stroke["animation"]={{"tracks",Json::array({Motion::track("opacity",{
            {0,.25f},{t.frames/3,1.f},{2*t.frames/3,.45f},{t.frames-1,1.f}},"in_out_sine")})}};
    if (preset=="focus_dim" || preset=="focus_vignette") {
        layers=focusDim(r,preset=="focus_dim"?.65f:.4f,t.frames);
    }
    if (preset=="focus_zoom")
        stroke["animation"]={{"tracks",Json::array({Motion::track("scale",{
            {0,1.f},{t.frames-1,1.08f}},"in_out_sine")})}};
    layers.push_back(stroke);
    if (preset=="marker_double") {
        for (auto& point:points) point[1]+=style.width*.25f;
        style.width*=.6f;style.opacity*=.6f;
        layers.push_back(highlightStroke(id+"_second",points,style,t.start,t.revealEnd,t.frames,56,t.seed+1));
    }
    return layers;
}

Json focusPolygon(const std::vector<Paths::Point>& polygon,float opacity,int frames,
                   float feather,int width,int height) {
    if (polygon.size()<3 || polygon.size()>4096 || frames<=0 || width<=0 || height<=0 ||
        !std::isfinite(opacity) || opacity<0 || opacity>1 || !std::isfinite(feather) || feather<0 || feather>256)
        throw std::invalid_argument("invalid polygon focus");
    auto path=Paths::polyline(polygon);
    path.push_back({{"type","close"}});
    return {{"id","focus_polygon_dim"},{"type","color"},{"color",{0,0,0,opacity}},
        {"size",{width,height}},{"position",{0,0}},{"start_frame",0},{"duration_frames",frames},
        {"masks",Json::array({{{"type","path"},{"mode","subtract"},{"path",path},{"feather",feather}}})}};
}

Json focusDim(const HighlightRegion& r,float opacity,int frames,int width,int height) {
    validateRegion(r);
    if (!std::isfinite(opacity) || opacity<0 || opacity>1 || frames<=0 || width<=0 || height<=0 ||
        r.x<0 || r.y<0 || r.x+r.width>width || r.y+r.height>height)
        throw std::invalid_argument("focus region or canvas invalid");
    Json layers=Json::array();
    const HighlightRegion pieces[]={{0,0,static_cast<float>(width),r.y},
        {0,r.y+r.height,static_cast<float>(width),height-r.y-r.height},
        {0,r.y,r.x,r.height},{r.x+r.width,r.y,width-r.x-r.width,r.height}};
    for (unsigned i=0;i<4;++i) {
        const auto& p=pieces[i];if (p.width<=0 || p.height<=0) continue;
        layers.push_back({{"id","focus_dim_"+std::to_string(i)},{"type","color"},
            {"color",{0,0,0,opacity}},{"size",{p.width,p.height}},
            {"position",{p.x,p.y}}, {"start_frame",0},{"duration_frames",frames}});
    }
    return layers;
}
} // namespace chronontemplate::native
