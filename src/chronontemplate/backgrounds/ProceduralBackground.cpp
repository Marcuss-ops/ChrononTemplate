#include "chronontemplate/backgrounds/ProceduralBackground.hpp"
#include <chronon3d/graphics/field2d.hpp>
#include <chronon3d/core/hash/hash_primitives.hpp>
#include <chrononmotion/motion/Procedural.hpp>
#include <algorithm>
#include <cmath>
#include <stdexcept>

namespace chronontemplate::native {
namespace {
float unit(std::uint32_t seed, unsigned index) {
    const auto hash = chronon3d::core::hash::splitmix64(
        (static_cast<std::uint64_t>(seed) << 32) | index);
    return static_cast<float>(hash >> 40) / 16777216.f;
}
Json ramp(const std::vector<std::string>& colors) {
    Json stops = Json::array();
    for (std::size_t i = 0; i < colors.size(); ++i)
        stops.push_back({{"position", static_cast<float>(i) / static_cast<float>(colors.size()-1)},
                         {"color", Material::rgba(colors[i])}});
    return {{"type", "linear"}, {"start", {0,0}}, {"end", {1,1}}, {"color_stops", stops}};
}
Json plate(const ProceduralBackgroundSpec& s, const std::string& id, const Json& fill) {
    return {{"id",id},{"type","shape"},{"size",{s.width,s.height}},
            {"position",{0,0}}, {"start_frame",0},
            {"duration_frames",s.frames},{"shape",{{"type","rect"},{"fill",fill}}}};
}
void cropStroke(Json& layer, const ProceduralBackgroundSpec& s) {
    auto& path=layer["shape"]["path"];
    float x0=1.e9f,y0=1.e9f,x1=-1.e9f,y1=-1.e9f;
    for (const auto& command:path) {
        const auto& p=command.at("point");
        x0=std::min(x0,p[0].get<float>());y0=std::min(y0,p[1].get<float>());
        x1=std::max(x1,p[0].get<float>());y1=std::max(y1,p[1].get<float>());
    }
    const float padding=layer["shape"]["stroke"]["width"].get<float>()*.5f+2.f;
    x0=std::floor(x0-padding);y0=std::floor(y0-padding);
    x1=std::ceil(x1+padding);y1=std::ceil(y1+padding);
    for (auto& command:path) {
        command["point"][0]=command["point"][0].get<float>()-x0;
        command["point"][1]=command["point"][1].get<float>()-y0;
    }
    layer["size"]={x1-x0,y1-y0};
    layer["position"]={x0,y0};
    layer["animation"]={{"tracks",Json::array({Motion::track("position",{
        {0,{x0,y0}},{s.frames-1,{x0+s.speed*30.f,y0-s.speed*18.f}}})})}};
}
void addLines(Json& layers, const ProceduralBackgroundSpec& s, bool grid, bool contours) {
    using chrononmotion::Vector2;
    chronon3d::graphics::Field2D field;
    field.seed = s.seed;
    field.frequency = 3.f;
    const auto treatment=[&](Json& line) {
        line["opacity"]=s.lineOpacity;
        line["shape"]["stroke"]["color"]=s.lineColor;
        if (s.tailFraction<1.f) {
            auto& keys=line["shape"]["operators"][0]["params"]["animation"]["keyframes"];
            keys=Json::array({{{"frame",0},{"value",{0.f,0.f}}},
                {{"frame",s.revealFrames},{"value",{1.f-s.tailFraction,1.f}}}});
        }
        Json effects=Json::array();
        if (s.blurRadius>0) effects.push_back({{"type","gaussian_blur"},{"radius",s.blurRadius}});
        if (s.glowRadius>0) effects.push_back({{"type","bloom"},{"radius",s.glowRadius},
            {"threshold",.2f},{"intensity",.6f}});
        if (!effects.empty()) line["effects"]=effects;
    };
    for (unsigned i=0; i<s.lineCount; ++i) {
        const float u=unit(s.seed,i*7), v=unit(s.seed,i*7+1);
        const float length=std::lerp(s.lengthRange[0],s.lengthRange[1],unit(s.seed,i*7+2));
        std::vector<Paths::Point> points;
        if (contours) {
            const float level=.28f+.44f*static_cast<float>(i+1)/static_cast<float>(s.lineCount+1);
            const auto segments=chrononmotion::motion::contourSegments(
                static_cast<float>(s.width),static_cast<float>(s.height),96,54,level,
                [&](const Vector2& p) { return field.sample({p.x/s.width,p.y/s.height}); });
            if (segments.empty()) continue;
            Json commands=Json::array();
            for (const auto& segment:segments) {
                commands.push_back({{"type","move_to"},{"point",{segment[0].x,segment[0].y}}});
                commands.push_back({{"type","line_to"},{"point",{segment[1].x,segment[1].y}}});
            }
            auto line=Paths::strokeLayer("contour_"+std::to_string(i),commands,0,s.revealFrames,s.frames,
                "#72CFFF",std::lerp(s.widthRange[0],s.widthRange[1],u),s.width,s.height);
            line["shape"]["stroke"]["cap"]="butt";
            line["opacity"]=.42f;
            line["animation"]={{"tracks",Json::array({Motion::track("position",{
                {0,{0,0}},{s.frames-1,{s.speed*30.f,-s.speed*18.f}}})})}};
            treatment(line);
            cropStroke(line,s);
            layers.push_back(std::move(line));
            continue;
        }
        if (grid) {
            const bool vertical = i%2==0;
            const float lane=static_cast<float>(i/2)/static_cast<float>((s.lineCount+1)/2);
            for (unsigned j=0;j<=64;++j) {
                const float t=static_cast<float>(j)/64.f;
                const float displacement=(field.sample({lane,t})-.5f)*90.f*s.distortion;
                points.push_back(vertical ? Paths::Point{lane*s.width+displacement,t*s.height}
                                          : Paths::Point{t*s.width,lane*s.height+displacement});
            }
        } else {
            const auto sampled=chrononmotion::motion::integrateFlow(
                Vector2(u*s.width,v*s.height),length,64,0.f,
                [&](const Vector2& p,float seconds) {
                    const auto potential=field.sample({p.x/static_cast<float>(s.width)+seconds*s.speed*.02f,
                                                        p.y/static_cast<float>(s.height)});
                    const float angle=s.orientationRadians+(potential-.5f)*s.curvature*s.distortion;
                    return Vector2(std::cos(angle),std::sin(angle));
                });
            for (const auto& p:sampled) points.push_back({p.x,p.y});
        }
        auto line=Paths::strokeLayer("flow_"+std::to_string(i),Paths::polyline(points),0,s.revealFrames,
            s.frames,"#72CFFF",std::lerp(s.widthRange[0],s.widthRange[1],unit(s.seed,i*7+3)),s.width,s.height);
        line["shape"]["stroke"]["cap"]="butt";
        line["opacity"]=contours?.45f:.32f;
        line["animation"]={{"tracks",Json::array({Motion::track("position",{
            {0,{0,0}}, {s.frames-1,{s.speed*30.f, -s.speed*18.f}}})})}};
        treatment(line);
        cropStroke(line,s);
        layers.push_back(std::move(line));
    }
}
}

Json grainBands(const std::vector<GrainBand>& bands,float opacity,std::uint32_t seed,bool animated) {
    if (bands.empty() || bands.size()>8 || !std::isfinite(opacity) || opacity<0.f || opacity>1.f)
        throw std::invalid_argument("grain requires 1..8 bands and opacity in [0,1]");
    float sum=0.f;
    for (const auto& band:bands) {
        if (!std::isfinite(band.size) || band.size<1.f || band.size>256.f ||
            !std::isfinite(band.weight) || band.weight<0.f || band.weight>1.f)
            throw std::invalid_argument("grain band size/weight outside supported bounds");
        sum+=band.weight;
    }
    if (sum<=0.f) throw std::invalid_argument("grain bands need a positive total weight");
    Json effects=Json::array();
    for (std::size_t i=0;i<bands.size();++i) {
        auto effect=Effects::noise(opacity*bands[i].weight/sum,
            seed+static_cast<std::uint32_t>(i)*0x9e3779b9U,bands[i].size);
        effect["animated"]=animated;
        effects.push_back(std::move(effect));
    }
    return effects;
}

std::vector<std::string> proceduralBackgroundPresets() {
    return {"grain_cinematic","noise_clouds","topographic_flow","liquid_warp",
            "technical_grid","light_fibers","modern_dark_flow"};
}

Json proceduralBackground(const ProceduralBackgroundSpec& s) {
    const auto presets=proceduralBackgroundPresets();
    if (std::find(presets.begin(),presets.end(),s.preset)==presets.end())
        throw std::invalid_argument("unknown procedural background preset");
    if (s.width<16 || s.width>8192 || s.height<16 || s.height>8192 ||
        s.fps<1 || s.fps>240 || s.frames<30 || s.frames>3600 || s.lineCount>256 ||
        !std::isfinite(s.speed) || s.speed<0.f || s.speed>10.f)
        throw std::invalid_argument("background dimensions, timing or density exceed bounds");
    for (const auto& range:{s.widthRange,s.lengthRange})
        if (!std::isfinite(range[0]) || !std::isfinite(range[1]) || range[0]<=0.f ||
            range[1]<range[0] || range[1]>10000.f)
            throw std::invalid_argument("background line range invalid");
    (void)Material::rgba(s.lineColor,s.lineOpacity);
    if (!std::isfinite(s.orientationRadians) || !std::isfinite(s.curvature) || s.curvature<0 || s.curvature>20 ||
        !std::isfinite(s.distortion) || s.distortion<0 || s.distortion>10 ||
        !std::isfinite(s.glowRadius) || s.glowRadius<0 || s.glowRadius>256 ||
        !std::isfinite(s.blurRadius) || s.blurRadius<0 || s.blurRadius>256 ||
        !std::isfinite(s.tailFraction) || s.tailFraction<=0 || s.tailFraction>1 ||
        s.revealFrames<1 || s.revealFrames>=s.frames)
        throw std::invalid_argument("background stroke controls outside supported ranges");
    Json layers=Json::array();
    auto gradient=plate(s,"atmosphere",ramp({"#050810","#10243B"}));
    gradient["effects"]=grainBands(s.bands,s.grainOpacity,s.seed);
    layers.push_back(std::move(gradient));
    if (s.preset=="noise_clouds" || s.preset=="liquid_warp" || s.preset=="modern_dark_flow") {
        Json field={{"generator","fractal"},{"seed",s.seed},{"frequency",4.f},
                    {"octaves",5},{"persistence",.52f},{"lacunarity",2.f}};
        if (s.preset=="liquid_warp")
            field["operators"]=Json::array({{{"kind","warp"},{"amount",.7f}}});
        const auto colors=s.preset=="liquid_warp"
            ? std::vector<std::string>{"#030810","#0A5670","#55C8CD"}
            : std::vector<std::string>{"#02040B","#172A45","#52647B"};
        auto texture=plate(s,"procedural_field",{{"type","field"},{"field",field},
            {"field_ramp",ramp(colors)},{"field_render_scale",2},
            {"field_drift",{s.speed*.04f,-s.speed*.02f}}});
        texture["opacity"]=s.preset=="modern_dark_flow"?.22f:.8f;
        layers.push_back(std::move(texture));
    }
    if (s.preset=="topographic_flow" || s.preset=="technical_grid" ||
        s.preset=="light_fibers" || s.preset=="modern_dark_flow")
        addLines(layers,s,s.preset=="technical_grid",s.preset=="topographic_flow");
    return TemplateComposition::renderPlan(s.preset,s.width,s.height,s.fps,s.frames,layers);
}
} // namespace chronontemplate::native
