#include <nlohmann/json.hpp>
#include "chronontemplate/camera_roll/ResolvedCameraSamples.hpp"

#include <algorithm>
#include <cmath>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <map>
#include <stdexcept>
#include <string>
#include <vector>

namespace {
using json = nlohmann::ordered_json;
constexpr int W=1920,H=1080,F=150;
const std::vector<std::string> presets={"text_focus_word_static","text_focus_word_travel","text_focus_near_to_far","text_focus_far_to_near","text_focus_center_out","text_focus_edges_in","text_focus_rack_duo","text_focus_depth_cascade"};
json keys(const std::vector<std::pair<int,float>>& v){json a=json::array();for(auto [f,x]:v)a.push_back({{"frame",f},{"value",x}});return a;}
std::vector<std::pair<int,float>> focus(std::vector<int> o){std::vector<std::pair<int,float>> r;for(int f=0;f<F;++f){float t=static_cast<float>(f)*(o.size()-1)/(F-1);auto i=std::min(static_cast<int>(t),static_cast<int>(o.size())-2);float u=t-i;u=u*u*(3-2*u);r.emplace_back(f,o[i]+(o[i+1]-o[i])*u);}return r;}
json color(const std::string&s){auto h=s.substr(1);return json::array({std::stoi(h.substr(0,2),nullptr,16)/255.0,std::stoi(h.substr(2,2),nullptr,16)/255.0,std::stoi(h.substr(4,2),nullptr,16)/255.0,1.0});}
json make(const std::string&id){
 if(std::find(presets.begin(),presets.end(),id)==presets.end())throw std::runtime_error("unknown preset: "+id);
 const std::vector<std::string> words={"MAKE","BETTER","VIDEOS","FASTER"};const std::vector<int>x={-625,-205,260,690};
 const bool depth=id==presets[2]||id==presets[3]||id==presets[7];
 std::vector<std::pair<int,float>> timeline;
 if(id==presets[0]||id==presets[6])timeline={{0,2},{149,2}};
 else if(id==presets[4])timeline={{0,1.5},{40,1.5},{75,0},{149,3}};
 else if(id==presets[5])timeline={{0,0},{38,3},{76,1},{112,2},{149,2.5}};
 else if(id==presets[6])timeline={{0,0},{54,2},{96,2},{149,3}};
 else if(id==presets[7])timeline={{0,2},{149,2}};
 else if(id==presets[1])timeline={{0,0},{42,1},{78,2},{114,3},{149,3}};
 else timeline=focus(id==presets[3]?std::vector<int>{3,2,1,0}:std::vector<int>{0,1,2,3});
 json layers=json::array({{{"id","background"},{"type","color"},{"color",{0.018,0.022,0.035,1}},{"size",{W,H}},{"screen_space",true},{"start_frame",0},{"duration_frames",F}}});
 for(int i=0;i<4;++i){
  float z=depth?500+60*i:0; float target=(id==presets[0]||id==presets[6])?2.0f:0;
  auto focusKeys=timeline;
  if(id==presets[7])focusKeys={{0,2},{149,2}};
  json blur=json::array(),scale=json::array(),opacity=json::array();
  if((id==presets[0]||id==presets[6])||id==presets[7]){
   float b=id==presets[7]?0.0f:(i==2?0.0f:std::min(7.0f,std::abs(i-target)*2.6f));
   blur=(id==presets[0])?keys({{0,std::max(5.0f,b)},{16,b},{149,b}}):keys({{0,b},{149,b}});
   scale=(id==presets[0])?keys({{0,.965f},{16,1},{149,1}}):keys({{0,1},{149,1}});
   opacity=(id==presets[0])?keys({{0,.72f},{16,1},{149,1}}):keys({{0,1},{149,1}});
  } else {
   for(auto [f,q]:focusKeys){float d=std::abs(i-q);blur.push_back({{"frame",f},{"value",std::min(7.0f,d*2.6f)}});scale.push_back({{"frame",f},{"value",{1.0f-std::min(d,2.0f)*.012f}}});opacity.push_back({{"frame",f},{"value",1.0f-std::min(d,3.0f)*.055f}});}
  }
  json anim={{"id","word-focus-"+std::to_string(i)},{"selectors",json::array({{{"id","word-selector-"+std::to_string(i)},{"unit","glyph"},{"order","forward"},{"shape","square"},{"combine","replace"},{"exclude_spaces",true},{"semantic_id","word-"+std::to_string(i)}}})},{"properties",json::array({{{"property","blur"},{"easing","linear"},{"keyframes",blur}},{{"property","scale"},{"easing","linear"},{"keyframes",scale}},{{"property","opacity"},{"easing","linear"},{"keyframes",opacity}},{{"property","fill_color"},{"easing","linear"},{"keyframes",json::array({{{"frame",0},{"value",color(i==2?"#F5F3F7":"#C9C4D0")}},{{"frame",149},{"value",color(i==2?"#F5F3F7":"#C9C4D0")}}})}}})}};
  json layer={{"id","word-"+std::to_string(i)},{"type","text"},{"text",words[i]},{"size",{i==1||i==2?390:310,180}},{"position",depth?json::array({W/2+x[i],H/2,z}):json::array({W/2+x[i],H/2})},{"enable_3d",depth},{"spans",json::array({{{"start",0},{"end",words[i].size()},{"semantic_id","word-"+std::to_string(i)},{"style",{{"color",i==2?"#F5F3F7":"#C9C4D0"}}}}})},{"style",{{"font","Chronon3d/assets/fonts/Inter-Bold.ttf"},{"font_size",112},{"min_font_size",86},{"max_font_size",112},{"fit_mode","shrink_only"},{"fill","#F5F3F7"}}},{"start_frame",0},{"duration_frames",F},{"text_animators",json::array({anim})}};
  if(id==presets[0])layer["animation"]={{"tracks",json::array({{{"property","scale"},{"easing","in_out_cubic"},{"keyframes",json::array({{{"frame",0},{"value",.98}},{{"frame",16},{"value",1}},{{"frame",149},{"value",1}}})}}})}};
  if(id==presets[7])layer["animation"]={{"tracks",json::array({{{"property","position_z"},{"easing","in_out_cubic"},{"keyframes",json::array({{{"frame",0},{"value",20}},{{"frame",24},{"value",0}},{{"frame",149},{"value",0}}})}}})}};
  layers.push_back(std::move(layer));
 }
 layers.push_back({{"id","editorial-kicker"},{"type","text"},{"text","CHRONON  /  DEPTH STUDY"},{"size",{600,44}},{"position",{W/2,145}},{"screen_space",true},{"style",{{"font","Chronon3d/assets/fonts/Inter-Regular.ttf"},{"font_size",20},{"min_font_size",18},{"max_font_size",20},{"fit_mode","shrink_only"},{"fill","#8D8A96"}}},{"start_frame",0},{"duration_frames",F}});
 json p={{"schema","chronon.render-plan.v3"},{"version",3},{"job_id",id},{"canvas",{{"width",W},{"height",H},{"fps_num",30},{"fps_den",1},{"duration_frames",F}}},{"layers",layers},{"output",{{"path",id+".mp4"},{"format","mp4"},{"codec","h264"}}}};
 if(depth){
  json camera={{"type","perspective"},{"position",{0,0,-1000}},{"rotation_deg",{0,0,0}},{"fov_deg",45},{"near",1},{"far",10000},{"zoom",1},{"dof",{{"enabled",id==presets[7]},{"focus_distance",620},{"aperture",.035},{"max_blur",12}}}};
  json channels=json::array();
  if(id!=presets[7])channels.push_back({{"channel","position_z"},{"easing","in_out_cubic"},{"keyframes",json::array({{{"frame",0},{"value",-1000}},{{"frame",75},{"value",-970}},{{"frame",149},{"value",-940}}})}});
  chronontemplate::camera_roll::attachResolvedCameraSamples(p,camera,channels,30.f,F);
 }
 return p;
}
}
int main(int argc,char**argv){try{std::filesystem::path out="out/text_depth_focus_v1";if(argc>1)out=argv[1];std::filesystem::create_directories(out);json names=json::array(),files=json::array();for(auto&id:presets){auto p=make(id);std::string fn=id+".plan.json";std::ofstream f(out/fn);f<<p.dump(2)<<'\n';names.push_back(id);files.push_back(fn);}std::ofstream m(out/"manifest.json");m<<json{{"schema","chronontemplate.text-depth-focus.v1"},{"family","text_depth_focus_v1"},{"renderer_contract","RenderPlan V3; semantic word TextAnimator blur/scale/opacity, 3D layer position_z, camera DOF"},{"canvas",{{"width",W},{"height",H},{"fps",30},{"frames",F}}},{"phrase","MAKE BETTER VIDEOS FASTER"},{"presets",names},{"plans",files}}.dump(2)<<'\n';std::cout<<"Emitted and validated "<<presets.size()<<" text depth-focus plans at "<<out<<'\n';return 0;}catch(const std::exception&e){std::cerr<<e.what()<<'\n';return 1;}}
