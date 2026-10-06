#include "chronontemplate/core/NativePrimitives.hpp"

#include <algorithm>
#include <cmath>
#include <set>
#include <stdexcept>

namespace chronontemplate::native {
namespace {
    void requireId(const std::string& id) {
        if (id.empty()) throw std::invalid_argument("layer id must not be empty");
    }
    void requireFinite(float value, const char* name) {
        if (!std::isfinite(value)) throw std::invalid_argument(std::string(name) + " must be finite");
    }
    void requirePositive(float value, const char* name) {
        requireFinite(value, name);
        if (value <= 0.f) throw std::invalid_argument(std::string(name) + " must be positive");
    }
    Json vec(const std::array<float, 2>& value) { return Json::array({value[0], value[1]}); }
    Json vec(const std::array<float, 3>& value) { return Json::array({value[0], value[1], value[2]}); }
    Json rgba(const std::array<float, 4>& value) {
        return Json::array({value[0], value[1], value[2], value[3]});
    }
    void validateTrackValue(const Json& value) {
        if (value.is_number()) {
            if (!std::isfinite(value.get<double>())) throw std::invalid_argument("track values must be finite");
            return;
        }
        if (value.is_array() && !value.empty()) {
            for (const Json& component : value) validateTrackValue(component);
            return;
        }
        throw std::invalid_argument("track values must be numbers or non-empty numeric arrays");
    }
}

std::array<float, 4> Material::rgba(const std::string& hex, float alpha) {
    if (hex.size() != 7 || hex[0] != '#') throw std::invalid_argument("color must use #RRGGBB");
    requireFinite(alpha, "alpha");
    if (alpha < 0.f || alpha > 1.f) throw std::invalid_argument("alpha must be in [0,1]");
    std::array<float, 4> result{};
    for (std::size_t i=0; i<3; ++i) {
        std::size_t consumed=0;
        try { result[i] = static_cast<float>(std::stoul(hex.substr(1+i*2,2), &consumed, 16))/255.f; }
        catch (...) { throw std::invalid_argument("color must use #RRGGBB"); }
        if (consumed != 2) throw std::invalid_argument("color must use #RRGGBB");
    }
    result[3]=alpha;
    return result;
}

Json Material::inlineMesh(float diffuse, float specular, float shininess, float rimIntensity) {
    for (float value : {diffuse,specular,shininess,rimIntensity}) requireFinite(value,"mesh material value");
    if (diffuse<0.f || diffuse>1.f || specular<0.f || specular>1.f || shininess<0.f || rimIntensity<0.f)
        throw std::invalid_argument("mesh material values are outside supported ranges");
    return {{"diffuse",diffuse},{"specular",specular},{"shininess",shininess},{"rim_intensity",rimIntensity}};
}

Json Effects::noise(float amount, unsigned seed, float size) {
    requireFinite(amount,"noise amount"); requirePositive(size,"noise size");
    if (amount<0.f || amount>1.f || size>256.f) throw std::invalid_argument("noise effect is outside supported ranges");
    return {{"type","noise"},{"amount",amount},{"seed",seed},{"size",size}};
}

Json Geometry::box(float width, float height, float depth) {
    requirePositive(width,"box width"); requirePositive(height,"box height"); requirePositive(depth,"box depth");
    struct Face { std::array<float,3> normal; std::array<std::array<float,3>,4> corners; };
    const std::array<Face,6> faces{{
        {{0,0,1},{{{-1,-1,1},{1,-1,1},{1,1,1},{-1,1,1}}}},
        {{0,0,-1},{{{1,-1,-1},{-1,-1,-1},{-1,1,-1},{1,1,-1}}}},
        {{1,0,0},{{{1,-1,1},{1,-1,-1},{1,1,-1},{1,1,1}}}},
        {{-1,0,0},{{{-1,-1,-1},{-1,-1,1},{-1,1,1},{-1,1,-1}}}},
        {{0,1,0},{{{-1,1,1},{1,1,1},{1,1,-1},{-1,1,-1}}}},
        {{0,-1,0},{{{-1,-1,-1},{1,-1,-1},{1,-1,1},{-1,-1,1}}}},
    }};
    Json vertices=Json::array(), indices=Json::array();
    for (const Face& face : faces) {
        const auto base=static_cast<unsigned>(vertices.size());
        for (const auto& p : face.corners) {
            vertices.push_back({{"position",{p[0]*width/2.f,p[1]*height/2.f,p[2]*depth/2.f}},
                                {"normal",face.normal},{"uv",{(p[0]+1.f)/2.f,(p[1]+1.f)/2.f}}});
        }
        for (unsigned index : {base,base+1,base+2,base,base+2,base+3}) indices.push_back(index);
    }
    return {{"vertices",std::move(vertices)},{"indices",std::move(indices)},
            {"material",Material::inlineMesh()}};
}

Json Geometry::boxLayer(const std::string& id, const std::array<float,3>& dimensions,
                        const std::array<float,3>& position, const std::string& color,
                        int durationFrames, const std::array<float,3>& rotation) {
    requireId(id); requirePositive(static_cast<float>(durationFrames),"duration_frames");
    for (float value : position) requireFinite(value,"position");
    for (float value : rotation) requireFinite(value,"rotation");
    return {{"id",id},{"type","mesh"},{"enable_3d",true},
            {"inline_mesh",box(dimensions[0],dimensions[1],dimensions[2])},
            {"color",rgba(Material::rgba(color))},{"position",vec(position)},
            {"rotation",vec(rotation)},{"start_frame",0},{"duration_frames",durationFrames}};
}

Json Motion::track(const std::string& property, const std::vector<Keyframe>& keys, const std::string& easing) {
    if (property.empty() || keys.empty()) throw std::invalid_argument("motion track needs a property and keyframes");
    Json frames=Json::array(); int previous=-1;
    for (const Keyframe& key : keys) {
        if (key.frame<0 || key.frame<=previous) throw std::invalid_argument("keyframes must be strictly increasing");
        validateTrackValue(key.value);
        previous=key.frame;
        frames.push_back({{"frame",key.frame},{"value",key.value}});
    }
    return {{"property",property},{"easing",easing},{"keyframes",std::move(frames)}};
}

Json Paths::polyline(const std::vector<Point>& points) {
    if (points.size()<2) throw std::invalid_argument("polyline requires at least two points");
    Json path=Json::array();
    for (std::size_t i=0;i<points.size();++i) {
        requireFinite(points[i][0],"path x"); requireFinite(points[i][1],"path y");
        path.push_back({{"type",i==0?"move_to":"line_to"},{"point",vec(points[i])}});
    }
    return path;
}

Json Paths::trim(int startFrame, int endFrame) {
    if (startFrame<0 || endFrame<=startFrame) throw std::invalid_argument("trim interval requires 0 <= start < end");
    return {{"kind","trim"},{"params",{{"start",0.f},{"end",0.f},
        {"animation",{{"easing","linear"},{"keyframes",Json::array({
            {{"frame",startFrame},{"value",0.f}},{{"frame",endFrame},{"value",1.f}}})}}}}}};
}

Json Paths::strokeLayer(const std::string& id, const Json& commands, int startFrame, int endFrame,
                        int durationFrames, const std::string& color, float width,
                        int canvasWidth, int canvasHeight, const Json& opacityKeys) {
    requireId(id); requirePositive(width,"stroke width"); requirePositive(static_cast<float>(durationFrames),"duration_frames");
    requirePositive(static_cast<float>(canvasWidth),"canvas width"); requirePositive(static_cast<float>(canvasHeight),"canvas height");
    if (!commands.is_array() || commands.empty()) throw std::invalid_argument("path commands must be a non-empty array");
    Json layer={{"id",id},{"type","shape"},{"shape",{{"type","path"},{"path",commands},
        {"stroke",{{"color",color},{"width",width},{"cap","round"},{"join","round"}}},
        {"operators",Json::array({trim(startFrame,endFrame)})}}},
        {"size",{canvasWidth,canvasHeight}},{"position",{0,0}},
        {"start_frame",0},{"duration_frames",durationFrames}};
    if (!opacityKeys.empty()) {
        std::vector<Keyframe> keys;
        for (const auto& key : opacityKeys) keys.push_back({key.at(0).get<int>(),key.at(1)});
        layer["animation"]={{"tracks",Json::array({Motion::track("opacity",keys)})}};
    }
    return layer;
}

Json Camera::perspective(const std::array<float,3>& position, const std::array<float,3>& rotationDeg,
                         float fovDeg, float nearPlane, float farPlane, float zoom) {
    for (float value : position) requireFinite(value,"camera position");
    for (float value : rotationDeg) requireFinite(value,"camera rotation");
    requireFinite(fovDeg,"camera fov"); requirePositive(nearPlane,"camera near");
    requirePositive(farPlane,"camera far"); requirePositive(zoom,"camera zoom");
    if (fovDeg<=0.f || fovDeg>=180.f || farPlane<=nearPlane) throw std::invalid_argument("camera lens is invalid");
    return {{"type","perspective"},{"position",vec(position)},{"rotation_deg",vec(rotationDeg)},
            {"fov_deg",fovDeg},{"near",nearPlane},{"far",farPlane},{"zoom",zoom}};
}

Json Camera::animation(const Json& tracks) {
    if (!tracks.is_array() || tracks.empty()) throw std::invalid_argument("camera animation needs tracks");
    return {{"tracks",tracks}};
}

Json Particles::emitterLayer(const std::string& id, int count, unsigned seed, int durationFrames,
                             const std::array<float,2>& emitterSize, const std::array<float,2>& velocityMin,
                             const std::array<float,2>& velocityMax, const std::array<float,2>& lifetime,
                             const std::array<float,2>& size, const Json& colorRamp,
                             const std::array<float,3>& position, int startFrame, float gravity, float turbulence) {
    requireId(id); requirePositive(static_cast<float>(durationFrames),"duration_frames");
    if (count<0 || count>1000000 || startFrame<0) throw std::invalid_argument("particle count or start frame is out of range");
    for (float value : emitterSize) { requireFinite(value,"emitter size"); if (value<0) throw std::invalid_argument("emitter size must be non-negative"); }
    for (unsigned i=0;i<2;++i) {
        requireFinite(velocityMin[i],"minimum velocity"); requireFinite(velocityMax[i],"maximum velocity");
        if (velocityMin[i]>velocityMax[i]) throw std::invalid_argument("particle velocity range is reversed");
        requireFinite(lifetime[i],"lifetime"); requireFinite(size[i],"particle size");
    }
    if (lifetime[0]<=0 || lifetime[1]<lifetime[0] || size[0]<0 || size[1]<size[0])
        throw std::invalid_argument("particle lifetime or size range is invalid");
    requireFinite(gravity,"gravity"); requireFinite(turbulence,"turbulence");
    if (turbulence<0 || !colorRamp.is_array() || colorRamp.size()<2) throw std::invalid_argument("particle ramp/turbulence is invalid");
    return {{"id",id},{"type","particles"},{"enable_3d",true},{"position",vec(position)},
        {"particle_emitter",{{"count",count},{"seed",seed},{"emitter_size",vec(emitterSize)},
            {"velocity_min",vec(velocityMin)},{"velocity_max",vec(velocityMax)},
            {"lifetime",vec(lifetime)},{"size",vec(size)},{"gravity",gravity},
            {"turbulence",turbulence},{"color_ramp",colorRamp}}},
        {"start_frame",startFrame},{"duration_frames",durationFrames}};
}

Json Text::layer(const std::string& id, const std::string& content, const std::array<float,3>& position,
                 const std::array<float,2>& size, const std::string& font, float fontSize,
                 const std::string& fill, int durationFrames, int startFrame) {
    requireId(id); requirePositive(fontSize,"font size"); requirePositive(size[0],"text width");
    requirePositive(size[1],"text height"); requirePositive(static_cast<float>(durationFrames),"duration_frames");
    if (font.empty() || fill.empty() || startFrame<0) throw std::invalid_argument("text font/fill/start frame is invalid");
    for (float value : position) requireFinite(value,"text position");
    return {{"id",id},{"type","text"},{"text",content},{"position",vec(position)},
        {"size",vec(size)},{"enable_3d",true},{"style",{{"font",font},{"font_size",fontSize},{"fill",fill}}},
        {"start_frame",startFrame},{"duration_frames",durationFrames}};
}

Json TemplateComposition::renderPlan(const std::string& jobId, int width, int height, int fps,
                                     int durationFrames, const Json& layers, const Json& camera,
                                     const Json& cameraAnimation, const Json& output) {
    requireId(jobId);
    if (width<=0 || height<=0 || fps<=0 || durationFrames<=0 || !layers.is_array())
        throw std::invalid_argument("composition canvas/layers are invalid");
    std::set<std::string> ids;
    for (const Json& layer : layers) {
        if (!layer.is_object() || !layer.contains("id")) throw std::invalid_argument("each layer needs an id");
        if (!ids.insert(layer.at("id").get<std::string>()).second) throw std::invalid_argument("layer ids must be unique");
        if (layer.contains("animation")) {
            const Json& animation = layer.at("animation");
            if (!animation.is_object() || !animation.contains("tracks") ||
                !animation.at("tracks").is_array())
                throw std::invalid_argument("layer animation must contain a tracks array");
            std::set<std::string> properties;
            for (const Json& track : animation.at("tracks")) {
                if (!track.is_object() || !track.contains("property") ||
                    !track.at("property").is_string())
                    throw std::invalid_argument("animation tracks need a property name");
                if (!properties.insert(track.at("property").get<std::string>()).second)
                    throw std::invalid_argument("layer animation properties must be unique");
            }
        }
    }
    Json plan={{"schema","chronon.render-plan.v3"},{"version",3},{"job_id",jobId},
        {"canvas",{{"width",width},{"height",height},{"fps_num",fps},{"fps_den",1},{"duration_frames",durationFrames}}},
        {"layers",layers},{"output",output.is_null()?Json{{"path",jobId+".mp4"},{"format","mp4"},{"codec","h264"}}:output}};
    if (!camera.is_null()) plan["camera"]=camera;
    if (!cameraAnimation.is_null()) plan["camera_animation"]=cameraAnimation;
    return plan;
}

Json buildBlackboardTortureV1() {
    constexpr int width=1920,height=1080,fps=24,duration=240;
    Json layers=Json::array({{{"id","background"},{"type","color"},{"color",rgba(Material::rgba("#101815"))},
        {"size",{width,height}},{"screen_space",true},{"start_frame",0},{"duration_frames",duration}}});
    layers.push_back(Geometry::boxLayer("board_surface",{1420,770,30},{960,500,0},"#173A2B",duration));
    layers.push_back(Geometry::boxLayer("frame_top",{1480,36,70},{960,903,-8},"#68452C",duration));
    layers.push_back(Geometry::boxLayer("frame_bottom",{1480,36,70},{960,97,-8},"#68452C",duration));
    layers.push_back(Geometry::boxLayer("frame_left",{36,770,70},{222,500,-8},"#68452C",duration));
    layers.push_back(Geometry::boxLayer("frame_right",{36,770,70},{1698,500,-8},"#68452C",duration));
    layers.push_back(Geometry::boxLayer("chalk_tray",{1480,34,110},{960,52,-56},"#543923",duration));

    const Json camera=Camera::perspective();
    Json cameraTracks=Json::array({
        Motion::track("camera_position_z",{{0,-2300},{24,-2050},{96,-2010},{120,-1980},{216,-1940},{239,-1940}},"in_out_cubic"),
        Motion::track("camera_rotation_y",{{0,-3},{24,-1},{96,0},{216,1.5f},{239,1.5f}},"in_out_cubic")});
    const Json cameraMotion=Camera::animation(cameraTracks);
    using P=Paths::Point;
    const std::vector<std::vector<P>> strokes={
        {{520,610},{520,450},{620,450}},{{520,530},{600,530}},{{520,610},{620,610}},
        {{650,610},{650,450}},{{750,610},{750,450}},{{650,530},{750,530}},
        {{780,610},{780,450},{870,450},{900,480},{870,530},{780,530}},{{835,530},{900,610}},
        {{930,610},{930,480},{960,450},{1030,450},{1060,480},{1060,580},{1030,610},{960,610},{930,580},{930,480}},
        {{1090,610},{1090,450}},{{1090,450},{1190,610}},{{1190,610},{1190,450}},
        {{1220,610},{1220,480},{1250,450},{1320,450},{1350,480},{1350,580},{1320,610},{1250,610},{1220,580},{1220,480}},
        {{1380,610},{1380,450}},{{1380,450},{1480,610}},{{1480,610},{1480,450}}};
    for (std::size_t i=0;i<strokes.size();++i) {
        const int start=24+static_cast<int>(i)*4;
        const int end=std::min(94,start+72/static_cast<int>(strokes.size())+2);
        const Json commands=Paths::polyline(strokes[i]);
        layers.push_back(Paths::strokeLayer("chalk_stroke_"+std::to_string(i/10)+std::to_string(i%10),commands,start,end,duration));
        layers.push_back(Paths::strokeLayer("chalk_residue_"+std::to_string(i/10)+std::to_string(i%10),commands,start,end,duration,
            "#D8D3C3",4.f,width,height,Json::array({{0,0},{151,0},{180,0.13f},{239,0.13f}})));
    }
    layers.push_back(Paths::strokeLayer("underline",Paths::polyline({{520,665},{1400,665}}),96,118,duration,"#F7F2DE",8.f));
    layers.push_back(Paths::strokeLayer("chalk_arrow",Paths::polyline({{1410,570},{1510,570},{1480,540},{1510,570},{1480,600}}),120,138,duration,"#F7F2DE",7.f));
    Json circle=Json::array({
        {{"type","move_to"},{"point",{480,420}}},
        {{"type","cubic_to"},{"point",{480,420}},{"control1",{690,330}},{"control2",{1270,330}}},
        {{"type","cubic_to"},{"point",{1450,500}},{"control1",{1480,390}},{"control2",{1480,610}}},
        {{"type","cubic_to"},{"point",{480,680}},{"control1",{1300,740}},{"control2",{650,750}}},
        {{"type","cubic_to"},{"point",{480,420}},{"control1",{360,560}},{"control2",{370,440}}}});
    layers.push_back(Paths::strokeLayer("chalk_circle",circle,144,164,duration,"#F7F2DE",6.f,width,height,
        Json::array({{0,0},{144,1},{163,1},{180,0.12f},{204,0.f},{239,0.f}})));
    layers.push_back(Particles::emitterLayer("chalk_dust",84,7319,114,{10,8},{-8,-18},{8,-3},{0.25f,0.8f},{1,4},
        Json::array({{{"position",0},{"color",{0.9f,0.88f,0.8f,0.f}}},{{"position",1},{"color",{0.9f,0.88f,0.8f,0.45f}}}}),
        {960,540,20},24,24.f,0.2f));
    for (Json& layer : layers) {
        const std::string id=layer.value("id","");
        const bool erasedStroke=id.rfind("chalk_stroke_",0)==0 && id>="chalk_stroke_10" && id<="chalk_stroke_16";
        if (erasedStroke || id=="underline") {
            layer["animation"]["tracks"].push_back(Motion::track("opacity",{{0,1},{168,1},{204,0},{239,0}},"in_out_cubic"));
        }
    }
    const std::array<std::vector<P>,4> next={
        std::vector<P>{{620,610},{620,450},{760,610},{760,450}},
        std::vector<P>{{830,610},{830,450},{960,450},{990,480},{960,530},{830,530}},
        std::vector<P>{{1040,450},{1180,450}},std::vector<P>{{1110,450},{1110,610}}};
    const std::array<int,4> starts{208,220,232,236}, ends{220,232,236,239};
    for (std::size_t i=0;i<next.size();++i)
        layers.push_back(Paths::strokeLayer("chalk_next_"+std::to_string(i),Paths::polyline(next[i]),starts[i],ends[i],duration));
    return TemplateComposition::renderPlan("blackboard_torture_v1",width,height,fps,duration,layers,camera,cameraMotion,
        {{"path","blackboard_torture_v1.mp4"},{"format","mp4"},{"codec","h264"}});
}

} // namespace chronontemplate::native
