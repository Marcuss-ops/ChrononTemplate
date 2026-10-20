// Native C++ emitter: ChrononMotion CameraRig -> Chronon3D RenderPlan.
#include <nlohmann/json.hpp>
#include <chrononmotion/motion/CameraRig.hpp>
#include <chrononmotion/motion/Easing.hpp>
#include <algorithm>
#include <cmath>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>

namespace fs = std::filesystem;
using Json = nlohmann::ordered_json;
using namespace chrononmotion::motion;
using chrononmotion::Vector3;
using chrononmotion::Quaternion;

namespace {
constexpr int W = 1920, H = 1080, FPS = 30, FRAMES = 360;
constexpr double DURATION = static_cast<double>(FRAMES - 1) / FPS;
constexpr double DEPTH_SHIFT = 1000.0;
constexpr const char* FONT = "Chronon3dGPU/assets/fonts/FreeSerif.ttf";

double round6(double x) { return std::round(x * 1e6) / 1e6; }
Json keyframes(const std::vector<double>& values) {
    Json result = Json::array();
    for (std::size_t i=0; i<values.size(); ++i)
        result.push_back({{"frame", i}, {"value", round6(values[i])}});
    return result;
}
Json cameraTrack(const std::string& prop, const std::vector<double>& values) {
    return {{"property", prop}, {"easing", "linear"}, {"keyframes", keyframes(values)}};
}
Vector3 euler(const Quaternion& orientation) {
    constexpr float toDeg = 57.29577951308232f;
    Quaternion q = orientation; q.invert();
    const float x = std::atan2(2.f*(q.w*q.x-q.y*q.z),1.f-2.f*(q.x*q.x+q.y*q.y));
    const float s = std::clamp(2.f*(q.w*q.y+q.z*q.x),-1.f,1.f);
    const float y = std::asin(s);
    const float z = std::atan2(2.f*(q.w*q.z-q.x*q.y),1.f-2.f*(q.y*q.y+q.z*q.z));
    return {x*toDeg,y*toDeg,z*toDeg};
}
Json wordLayer(const std::string& word, int index, int frameStart, int frameEnd,
               int x, int y, int finalX, int finalY, int z) {
    Json opacity = Json::array({{{"frame",0},{"value",0.0}}});
    if (frameStart > 0) opacity.push_back({{"frame",frameStart},{"value",0.0}});
    opacity.push_back({{"frame",frameStart+12},{"value",1.0}});
    if (frameEnd > frameStart+12) opacity.push_back({{"frame",frameEnd},{"value",1.0}});
    // Transform tracks are offsets from the layer's base position. Each word
    // starts settling after its speaking beat, so the phrases are separated
    // before the camera begins its final pullback.
    const int moveStart=frameStart+12;
    const int moveEnd=index==3 ? 244 : frameEnd-7;
    const Json xKeys=Json::array({{{"frame",0},{"value",0}},{{"frame",moveStart},{"value",0}},
      {{"frame",moveEnd},{"value",finalX-x}},{{"frame",359},{"value",finalX-x}}});
    const Json yKeys=Json::array({{{"frame",0},{"value",0}},{{"frame",moveStart},{"value",0}},
      {{"frame",moveEnd},{"value",finalY-y}},{{"frame",359},{"value",finalY-y}}});
    return {{"id", "word_"+std::to_string(index+1)}, {"type","text"}, {"text",word},
      {"size",{1180,210}}, {"position",{x,y,z+DEPTH_SHIFT}}, {"enable_3d",true},
      {"start_frame",0},{"duration_frames",FRAMES},
      {"style",{{"font",FONT},{"font_size",166},{"fill","#F4F0E8"},
        {"fit_mode","shrink_only"},{"min_font_size",110},{"max_font_size",210},
        {"glow",{{"radius",14},{"intensity",0.16},{"color","#F4D58A"}}}}},
      {"animation",{{"tracks",Json::array({
        {{"property","opacity"},{"easing","out_cubic"},{"keyframes",opacity}},
        {{"property","position_x"},{"easing","out_cubic"},{"keyframes",xKeys}},
        {{"property","position_y"},{"easing","out_cubic"},{"keyframes",yKeys}}
      })}}}};
}
}

int main(int argc,char**argv) try {
    if(argc!=4) throw std::runtime_error("usage: emit_editorial_words <asset-dir> <plan.json> <assets-root>");
    const fs::path a=fs::absolute(argv[1]), out=fs::absolute(argv[2]), root=fs::absolute(argv[3]);
    const auto ref=[&](const fs::path& p){
      const auto relative=p.lexically_normal().lexically_relative(root.lexically_normal());
      if(relative.empty() || relative.native().starts_with(".."))
        throw std::runtime_error("asset is outside render assets-root: "+p.string());
      return relative.generic_string();
    };
    for(const auto& p:{a/"mrbeast_clean_plate.png"})
      if(!fs::is_regular_file(p)) throw std::runtime_error("missing scene asset: "+p.string());

    // World units: pixels on the 1920x1080 canvas; camera forward is -Z.
    // Four 3D title planes sit at individually keyed depths; camera lives at Z=1080.
    CameraRig rig(1,55.f,static_cast<float>(W)/H,1.f,10000.f);
    rig.setPosition({600.f,540.f,1080.f}).setTarget({600.f,300.f,0.f})
       .setFov(55.f).setLegacyDefocusStrength(0.045f).setFocusDistance(975.f).setMaxBlur(12.f);
    const Easing glide=Easing::cubicBezier(.22f,.72f,.20f,1.f);
    rig.positionTrack().add(0.f,{600.f,300.f,1080.f},glide)
      .add(2.05f,{590.f,460.f,1080.f},glide).add(4.10f,{610.f,620.f,1080.f},glide)
      .add(6.15f,{600.f,780.f,1080.f},glide).add(8.15f,{960.f,540.f,1530.f},Easing::circOut())
      .add(static_cast<float>(DURATION),{960.f,540.f,1530.f},Easing::easeInOut());
    rig.targetTrack().add(0.f,{600.f,300.f,25.f},glide)
      .add(2.05f,{590.f,460.f,45.f},glide).add(4.10f,{610.f,620.f,65.f},glide)
      .add(6.15f,{600.f,780.f,85.f},glide).add(8.15f,{960.f,540.f,0.f},Easing::circOut())
      .add(static_cast<float>(DURATION),{960.f,540.f,0.f},Easing::easeInOut());
    rig.focusDistanceTrack().add(0.f,975.f,glide).add(2.05f,955.f,glide)
      .add(4.10f,935.f,glide).add(6.15f,915.f,glide).add(8.15f,1000.f,Easing::circOut())
      .add(static_cast<float>(DURATION),1000.f,Easing::easeInOut());
    rig.legacyDefocusStrengthTrack().add(0.f,.045f).add(8.15f,.035f).add(static_cast<float>(DURATION),.035f);
    rig.maxBlurTrack().add(0.f,12.f).add(8.15f,10.f).add(static_cast<float>(DURATION),10.f);

    std::vector<std::vector<double>> ch(10,std::vector<double>(FRAMES));
    // position xyz, rotation xyz, fov, focus distance, aperture, max blur
    for(int f=0;f<FRAMES;++f){
      const auto p=rig.sample(static_cast<float>(f)/FPS); const auto r=euler(p.orientation);
      ch[0][f]=p.position.x-W*.5; ch[1][f]=p.position.y-H*.5; ch[2][f]=-p.position.z+DEPTH_SHIFT;
      ch[3][f]=r.x; ch[4][f]=r.y; ch[5][f]=r.z; ch[6][f]=p.fov;
      ch[7][f]=p.focusDistance; ch[8][f]=p.legacyDefocusStrength; ch[9][f]=p.maxBlur;
      // Continuous, restrained hand-held drift without introducing jitter.
      ch[0][f]+=0.9*std::sin(static_cast<double>(f)/FPS*.42);
      ch[1][f]+=0.55*std::sin(static_cast<double>(f)/FPS*.31+1.2);
    }
    const char* props[]={"camera_position_x","camera_position_y","camera_position_z",
      "camera_rotation_x","camera_rotation_y","camera_rotation_z","camera_fov_deg",
      "camera_focus_distance","camera_aperture","camera_max_blur"};
    Json tracks=Json::array(); for(int i=0;i<10;++i) tracks.push_back(cameraTrack(props[i],ch[i]));
    const auto p0=rig.sample(0.f); const auto r0=euler(p0.orientation);
    Json layers=Json::array();
    // The clean plate spans the complete camera gate and remains edge-to-edge
    // during the final pullback, avoiding a second image plane or visible seam.
    Json plateScale=Json::array({{{"frame",0},{"value",1.55}},
      {{"frame",244},{"value",1.55}},{{"frame",300},{"value",2.25}},
      {{"frame",359},{"value",2.25}}});
    layers.push_back({{"id","presenter_room_plate"},{"type","image"},
      {"asset",ref(a/"mrbeast_clean_plate.png")},{"size",{2800,1575}},
      {"position",{-160,-40,1150}},{"scale",{1.55,1.55,1.0}},
      {"fit","cover"},{"enable_3d",true},
      {"start_frame",0},{"duration_frames",FRAMES},
      {"animation",{{"tracks",Json::array({
        {{"property","scale"},{"easing","out_cubic"},{"keyframes",plateScale}},
        {{"property","position_y"},{"easing","linear"},{"keyframes",[&](){
          Json keys=Json::array();
          for(int f=0;f<FRAMES;++f)
            keys.push_back({{"frame",f},{"value",round6(ch[1][f]-ch[1][0])}});
          return keys;
        }()}}
      })}}}});
    const char* words[]={"HOMES","CAN","CHANGE","LIVES"};
    const int xs[]={600,590,610,600}, ys[]={300,460,620,780};
    const int finalXs[]={180,680,1180,1680}, finalYs[]={540,540,540,540}, zs[]={-25,-45,-65,-85};
    const int starts[]={0,62,124,186}, ends[]={61,123,185,245};
    for(int i=0;i<4;++i) layers.push_back(wordLayer(words[i],i,starts[i],ends[i],
      xs[i],ys[i],finalXs[i],finalYs[i],zs[i]));
    // A measured, restrained archival texture pass and edge falloff.
    layers.push_back({{"id","film_texture"},{"type","adjustment"},
      {"effects",Json::array({
        {{"type","noise"},{"amount",0.022},{"size",1.0},{"color_mode","monochrome"}},
        {{"type","vignette"},{"amount",0.08},{"radius",0.9},{"softness",0.8}},
        {{"type","chromatic_aberration"},{"red_offset",0.32},{"blue_offset",-0.32}}
      })}});
    Json plan={{"schema","chronon.render-plan.v3"},{"version",3},{"job_id","editorial_words_chrononmotion_v1"},
      {"canvas",{{"width",W},{"height",H},{"fps_num",FPS},{"fps_den",1},{"duration_frames",FRAMES}}},
      {"camera",{{"type","perspective"},{"position",{p0.position.x-W*.5,p0.position.y-H*.5,-p0.position.z+DEPTH_SHIFT}},
        {"rotation_deg",{r0.x,r0.y,r0.z}},{"fov_deg",p0.fov},{"near",1},{"far",10000},{"zoom",1},
        {"dof",{{"enabled",true},{"focus_distance",p0.focusDistance},{"aperture",p0.legacyDefocusStrength},{"max_blur",p0.maxBlur}}}}},
      {"camera_animation",{{"tracks",std::move(tracks)}}},{"layers",std::move(layers)},
      {"output",{{"path","editorial_words.mp4"},{"format","mp4"},{"codec","h264"}}}};
    fs::create_directories(out.parent_path()); std::ofstream f(out); f<<plan.dump(2)<<'\n';
    if(!f) throw std::runtime_error("failed writing plan: "+out.string());
    std::cout<<"Wrote "<<out<<" ("<<FRAMES<<" frames, 30 fps); 4 native text planes, one photographic plane, ChrononMotion camera samples\n";
  }catch(const std::exception&e){std::cerr<<e.what()<<'\n';return 1;}
