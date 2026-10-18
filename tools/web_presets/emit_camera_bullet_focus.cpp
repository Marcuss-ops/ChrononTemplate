// ChrononTemplate web.camera_bullet_focus: CameraRig move and animated focus emphasis for title bullets.
#include <nlohmann/json.hpp>
#include <chrononmotion/motion/CameraRig.hpp>
#include <chrononmotion/motion/Easing.hpp>
#include <algorithm>
#include <array>
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
using chrononmotion::Quaternion;
using chrononmotion::Vector3;
namespace {
constexpr int W=1920, H=1080, FPS=30, FRAMES=300, BEAT=75;
constexpr int MOVE_START_OFFSET=25, MOVE_ARRIVE_OFFSET=10;
constexpr double DURATION=static_cast<double>(FRAMES-1)/FPS;
constexpr const char* FONT="tests/fixtures/Inter-Bold.ttf";
double r6(double x){return std::round(x*1e6)/1e6;}
Vector3 euler(Quaternion q){
  constexpr float d=57.29577951308232f; q.invert();
  float x=std::atan2(2.f*(q.w*q.x-q.y*q.z),1.f-2.f*(q.x*q.x+q.y*q.y));
  float sy=std::clamp(2.f*(q.w*q.y+q.z*q.x),-1.f,1.f);
  float y=std::asin(sy), z=std::atan2(2.f*(q.w*q.z-q.x*q.y),1.f-2.f*(q.y*q.y+q.z*q.z));
  return {x*d,y*d,z*d};
}
Json track(const char* prop,const std::vector<double>& values){Json k=Json::array();for(std::size_t i=0;i<values.size();++i)k.push_back({{"frame",i},{"value",r6(values[i])}});return {{"property",prop},{"easing","linear"},{"keyframes",std::move(k)}};}
Json focusTrack(int item){
  const int start=item*BEAT, next=std::min(FRAMES-1,(item+1)*BEAT);
  Json keys=Json::array();
  if(item==0) keys.push_back({{"frame",0},{"value",1.0}});
  else {keys.push_back({{"frame",0},{"value",0.0}});keys.push_back({{"frame",start-MOVE_START_OFFSET},{"value",0.0}});keys.push_back({{"frame",start+MOVE_ARRIVE_OFFSET},{"value",1.0}});}
  if(item<3){keys.push_back({{"frame",next-MOVE_START_OFFSET},{"value",1.0}});keys.push_back({{"frame",next+MOVE_ARRIVE_OFFSET},{"value",0.0}});}
  else keys.push_back({{"frame",FRAMES-1},{"value",1.0}});
  return {{"property","opacity"},{"easing","in_out_cubic"},{"keyframes",std::move(keys)}};
}
Json softTrailTrack(int item){
  Json track=focusTrack(item);
  for(auto& key:track["keyframes"]) key["value"]=(1.0-key["value"].get<double>())*0.66;
  return track;
}
Json highlightTrack(int item,const char* property){
  const int start=item*BEAT, next=std::min(FRAMES-1,(item+1)*BEAT);
  Json keys=Json::array();
  if(item==0) keys.push_back({{"frame",0},{"value",1.0}});
  else {keys.push_back({{"frame",0},{"value",0.0}});keys.push_back({{"frame",start-MOVE_START_OFFSET},{"value",0.0}});keys.push_back({{"frame",start+MOVE_ARRIVE_OFFSET},{"value",1.0}});}
  if(item<3){keys.push_back({{"frame",next-MOVE_START_OFFSET},{"value",1.0}});keys.push_back({{"frame",next+MOVE_ARRIVE_OFFSET},{"value",0.0}});}
  else keys.push_back({{"frame",FRAMES-1},{"value",1.0}});
  return {{"property",property},{"easing","in_out_cubic"},{"keyframes",std::move(keys)}};
}
Json highlightPositionTrack(int item,int width){
  Json scale=highlightTrack(item,"scale_x"), keys=Json::array();
  for(const auto& key:scale["keyframes"]){
    const double amount=key["value"].get<double>();
    // Position tracks are offsets from the layer's authored position. Move the center
    // from the left edge as scale_x grows, so the marker wipes left-to-right.
    keys.push_back({{"frame",key["frame"]},{"value",r6(-width*.5*(1.0-amount))}});
  }
  return {{"property","position_x"},{"easing","in_out_cubic"},{"keyframes",std::move(keys)}};
}
Json textLayer(std::string id,std::string text,int x,int y,int depth,int width,int size,int item,const char* color){
  return {{"id",std::move(id)},{"type","text"},{"text",std::move(text)},
    {"size",{width,126}},{"position",{x,y,depth}},{"enable_3d",true},
    {"start_frame",0},{"duration_frames",FRAMES},
    {"style",{{"font",FONT},{"font_size",size},{"fill",color},
      {"glow",{{"color","#58C8F0"},{"intensity",0.8},{"radius",18.0}}},
      {"shadow",{{"color","#45C7F3"},{"opacity",0.72},{"blur",20.0},{"offset",{0.0,0.0}}}}}},
    {"animation",{{"tracks",Json::array({focusTrack(item)})}}}};
}
Json softTrailLayer(std::string id,std::string text,int x,int y,int depth,int width,int size,int item){
  return {{"id",std::move(id)},{"type","text"},{"text",std::move(text)},
    {"size",{width,126}},{"position",{x,y,depth}},{"enable_3d",true},
    {"start_frame",0},{"duration_frames",FRAMES},
    {"style",{{"font",FONT},{"font_size",size},{"fill","#777777"}}},
    {"effects",Json::array({{{"type","mosaic"},{"block_size",40}}})},
    {"animation",{{"tracks",Json::array({softTrailTrack(item)})}}}};
}
}
int main(int argc,char**argv) try {
 if(argc!=2 && argc!=10) throw std::runtime_error("usage: emit_camera_bullet_focus <plan.json> [era1 title1 era2 title2 era3 title3 era4 title4]");
 const fs::path out=fs::absolute(argv[1]);
 // Motion and composition use pixel units, origin at upper-left, +Y down, camera forward +Z.
 // The selected line stays in the same viewport band while the actual perspective camera tracks down the list.
 constexpr float cx=W*.5f, cz=1200.f;
 const float rows[]={240.f,440.f,640.f,840.f};
 const float depths[]={0.f,0.f,0.f,0.f};
 CameraRig rig(1,55.f,static_cast<float>(W)/H,1.f,5000.f);
 rig.setPosition({cx,rows[0],cz}).setTarget({cx,rows[0],0.f}).setFov(55.f);
 const Easing glide=Easing::easeInOut();
 rig.positionTrack().add(0.f,{cx,rows[0],cz-depths[0]},glide);
 rig.targetTrack().add(0.f,{cx,rows[0],depths[0]},glide);
 for(int i=1;i<4;++i){
   const float moveStart=static_cast<float>(i*BEAT-MOVE_START_OFFSET)/FPS;
   const float arrive=static_cast<float>(i*BEAT+MOVE_ARRIVE_OFFSET)/FPS;
   rig.positionTrack().add(moveStart,{cx,rows[i-1],cz-depths[i-1]},glide).add(arrive,{cx,rows[i],cz-depths[i]},glide);
   rig.targetTrack().add(moveStart,{cx,rows[i-1],depths[i-1]},glide).add(arrive,{cx,rows[i],depths[i]},glide);
 }
 rig.positionTrack().add(static_cast<float>(DURATION),{cx,rows[3],cz-depths[3]},Easing::easeInOut());
 rig.targetTrack().add(static_cast<float>(DURATION),{cx,rows[3],depths[3]},Easing::easeInOut());
 std::vector<std::vector<double>> ch(7,std::vector<double>(FRAMES));
 for(int f=0;f<FRAMES;++f){auto p=rig.sample(static_cast<float>(f)/FPS);auto r=euler(p.orientation);ch[0][f]=p.position.x-W*.5;ch[1][f]=p.position.y-H*.5;ch[2][f]=-p.position.z;ch[3][f]=r.x;ch[4][f]=r.y;ch[5][f]=r.z;ch[6][f]=p.fov;}
 const char* props[]={"camera_position_x","camera_position_y","camera_position_z","camera_rotation_x","camera_rotation_y","camera_rotation_z","camera_fov_deg"};
 Json cameraTracks=Json::array();for(int i=0;i<7;++i)cameraTracks.push_back(track(props[i],ch[i]));
 Json layers=Json::array();
 layers.push_back({{"id","crt_paper"},{"type","color"},{"size",{W,H}},{"color",{0.78,0.78,0.77,1.0}},
  {"start_frame",0},{"duration_frames",FRAMES}});
 std::array<std::string,4> eras{"1ST ERA","2ND ERA","3RD ERA","4TH ERA"};
 std::array<std::string,4> heads{"THE RISE","THE EARLY GAME","SHOT CHUCKING ERA","MODERN BASKETBALL"};
 const int highlightWidths[]={430,700,850,850};
 if(argc==10) for(int i=0;i<4;++i){eras[i]=argv[2+i*2];heads[i]=argv[3+i*2];}
 for(int i=0;i<4;++i){int y=static_cast<int>(rows[i]);
   // A marker bar draws behind each heading and reveals as the camera settles on that row.
   layers.push_back({{"id","heading_highlight_"+std::to_string(i+1)},{"type","shape"},
     {"size",{highlightWidths[i],94}},{"position",{1220,y,static_cast<int>(depths[i])}},
     {"enable_3d",true},{"start_frame",0},{"duration_frames",FRAMES},
     {"shape",{{"type","rect"},{"fill",{0.98,0.78,0.22,0.86}}}},
     {"animation",{{"tracks",Json::array({highlightTrack(i,"opacity"),highlightTrack(i,"scale_x"),highlightPositionTrack(i,highlightWidths[i])})}}}});
   // Separate editable era and heading layers; both inherit the same per-row focus treatment.
   layers.push_back(softTrailLayer("era_soft_"+std::to_string(i+1),eras[i],500,y,static_cast<int>(depths[i]),300,60,i));
   layers.push_back(softTrailLayer("heading_soft_"+std::to_string(i+1),heads[i],1220,y,static_cast<int>(depths[i]),1100,80,i));
   layers.push_back(textLayer("era_"+std::to_string(i+1),eras[i],500,y,static_cast<int>(depths[i]),300,60,i,"#252525"));
   layers.push_back(textLayer("heading_"+std::to_string(i+1),heads[i],1220,y,static_cast<int>(depths[i]),1100,80,i,"#151515"));
 }
 // Pointer uses the camera's exact move/arrival frames and matching in-out easing.
 Json pointerKeys=Json::array({{{"frame",0},{"value",0.0}}});
 Json pointerDepthKeys=Json::array({{{"frame",0},{"value",0.0}}});
 for(int i=1;i<4;++i){
   pointerKeys.push_back({{"frame",i*BEAT-MOVE_START_OFFSET},{"value",rows[i-1]-rows[0]}});
   pointerKeys.push_back({{"frame",i*BEAT+MOVE_ARRIVE_OFFSET},{"value",rows[i]-rows[0]}});
   pointerDepthKeys.push_back({{"frame",i*BEAT-MOVE_START_OFFSET},{"value",depths[i-1]-depths[0]}});
   pointerDepthKeys.push_back({{"frame",i*BEAT+MOVE_ARRIVE_OFFSET},{"value",depths[i]-depths[0]}});
 }
 layers.push_back({{"id","active_pointer"},{"type","shape"},{"size",{56,56}},
  {"position",{320,rows[0],depths[0]}},{"enable_3d",true},{"start_frame",0},{"duration_frames",FRAMES},
  {"shape",{{"type","polygon"},{"points",3},{"rotation_degrees",90},{"fill",{0.08,0.58,0.77,1.0}}}},
  {"animation",{{"tracks",Json::array({{{"property","position_y"},{"easing","in_out_cubic"},{"keyframes",pointerKeys}},{{"property","position_z"},{"easing","in_out_cubic"},{"keyframes",pointerDepthKeys}}})}}}});
 auto p0=rig.sample(0.f);auto r0=euler(p0.orientation);
 Json plan={{"schema","chronon.render-plan.v3"},{"version",3},{"job_id","web_camera_bullet_focus_v1"},
  {"canvas",{{"width",W},{"height",H},{"fps_num",FPS},{"fps_den",1},{"duration_frames",FRAMES}}},
  {"camera",{{"type","perspective"},{"position",{p0.position.x-W*.5,p0.position.y-H*.5,-p0.position.z}},
   {"rotation_deg",{r0.x,r0.y,r0.z}},{"fov_deg",p0.fov},{"near",1},{"far",5000},{"zoom",1}}},
  {"camera_animation",{{"tracks",std::move(cameraTracks)}}},{"layers",std::move(layers)},
  {"output",{{"path","Web_Camera_Bullet_Focus.mp4"},{"format","mp4"},{"codec","h264"}}}};
 fs::create_directories(out.parent_path());std::ofstream f(out);if(!f)throw std::runtime_error("cannot write plan: "+out.string());f<<plan.dump(2)<<'\n';
 std::cout<<"Wrote "<<out<<" (4 editable title bullets, 10 s, 30 fps, ChrononMotion3D perspective CameraRig)\n";
} catch(const std::exception&e){std::cerr<<e.what()<<'\n';return 1;}
