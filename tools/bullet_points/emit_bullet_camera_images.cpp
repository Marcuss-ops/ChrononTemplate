// Native C++ authoring backend for the bullet -> camera -> image sequence.
// Usage: emit_bullet_camera_images MODE OUTPUT_PLAN [IMAGE ...]
#include <nlohmann/json.hpp>
#include <algorithm>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>

using J = nlohmann::json;
namespace fs = std::filesystem;
namespace {
constexpr int W=1920,H=1080,FPS=30;
struct Recipe { std::vector<std::string> items; int type=0,hold=0,travel=0,imageHold=0,font=0; };
J kf(int f,double v){return J{{"frame",f},{"value",v}};}
J uniqueFrames(J frames){J unique=J::array();for(auto& frame:frames){if(!unique.empty()&&unique.back()["frame"]==frame["frame"])unique.back()=frame;else unique.push_back(frame);}return unique;}
J track(const std::string& p,J frames,const char* easing="linear") {
 return J{{"property",p},{"easing",easing},{"keyframes",uniqueFrames(std::move(frames))}};
}
double smooth(double x){x=std::clamp(x,0.0,1.0);return x*x*(3.0-2.0*x);}
J camera(double x,double y,double z,double pitch,double yaw=0){return J{{"type","perspective"},{"position",{x,y,z}},{"rotation_deg",{pitch,yaw,0.0}},{"fov_deg",45},{"near",1},{"far",10000},{"zoom",1},{"sensor_width_mm",36},{"lens_shift",{0,0}}};}
J build(const Recipe& r,const std::vector<std::string>& images,const std::string& mode){
 if(images.size()<r.items.size()) throw std::runtime_error(mode+" requires "+std::to_string(r.items.size())+" images");
 struct Beat{int ts,te,is,ie;double yt,yi;}; std::vector<Beat> beats; int cursor=0;
 for(size_t i=0;i<r.items.size();++i){int ts=cursor,te=ts+r.type,is=te+r.hold+r.travel,ie=is+r.imageHold;double imageY=-double(i)*2250.0;beats.push_back({ts,te,is,ie,imageY+450.0,imageY});cursor=ie+r.travel;}
 int duration=cursor+12; J layers=J::array();
 layers.push_back(J{{"id","background"},{"type","shape"},{"size",{W,H}},{"position",{W/2,H/2}},{"start_frame",0},{"duration_frames",duration},{"shape",{{"type","rect"},{"fill",{0.018,0.028,0.045,1.0}}}}});
 for(size_t i=0;i<beats.size();++i){const auto& b=beats[i];const auto& phrase=r.items[i];std::string suffix=std::to_string(i+1);
   J text={{"id","bullet_"+suffix+"_underlay"},{"type","text"},{"text",phrase},{"size",{1500,180}},{"position",{W/2,H/2,0}},{"enable_3d",true},{"screen_space",true},{"start_frame",0},{"duration_frames",std::max(1,b.te+r.hold)},{"style",{{"font","ChrononTemplate/assets/fonts/Inter-ExtraBold.ttf"},{"font_size",r.font},{"fill","#ECF3FA"},{"glow",{{"radius",9},{"intensity",0.2},{"color","#FFFFFF"}}}}}};
   text["animation"]["tracks"]=J::array({track("opacity",J::array({kf(0,0),kf(duration-1,0)}))});layers.push_back(text);
   J typed=text;typed.erase("animation");typed["id"]="bullet_"+suffix+"_typewriter";
   typed["text_animators"]=J::array({J{{"selectors",J::array({J{{"unit","glyph"},{"shape","square"},{"order","forward"},{"start",{{"keyframes",uniqueFrames(J::array({kf(0,0),kf(b.ts,0),kf(b.te+1,100),kf(duration,100)}))}}},{"end",{{"keyframes",J::array({kf(0,100),kf(duration,100)})}}}}})},{"properties",J::array({track("opacity",J::array({kf(0,0),kf(duration,0)}))})}}});
   layers.push_back(typed);
   const int dropStart=b.te+r.hold;
   J leader={{"id","leader_"+suffix},{"type","shape"},{"size",{8,std::abs(b.yi-b.yt)-120}},{"position",{0,(b.yt+b.yi+120)*0.5,100.0}},{"enable_3d",true},{"start_frame",dropStart},{"duration_frames",std::max(1,b.ie-dropStart)},{"shape",{{"type","rect"},{"fill",{0.302,0.890,1.0,1.0}}}},{"style",{{"glow",{{"radius",22},{"intensity",0.8},{"color","#4DE3FF"}}}}}};layers.push_back(leader);
   J image={{"id","image_"+suffix},{"type","image"},{"asset",images[i]},{"size",{1120,630}},{"position",{0,b.yi,0}},{"enable_3d",true},{"start_frame",0},{"duration_frames",duration}};
   image["animation"]["tracks"]=J::array({track("opacity",J::array({kf(0,0),kf(dropStart,0),kf(dropStart+6,1),kf(std::max(dropStart+7,b.ie-5),1),kf(b.ie+1,0)}))});layers.push_back(image);
 }
 J samples=J::array();
 for(int f=0;f<duration;++f){double x=0,y=beats.front().yt,z=-1900,pitch=12.1,yaw=0;
   for(size_t i=0;i<beats.size();++i){const auto& b=beats[i];int dropStart=b.te+r.hold;if(f<dropStart){y=b.yt;z=-1900;pitch=std::atan2(y-b.yi,-z)*180.0/3.141592653589793;break;}if(f<b.is){double t=smooth(double(f-dropStart)/std::max(1,b.is-dropStart));y=b.yt+(b.yi-b.yt)*t;z=-1900+900*t;pitch=std::atan2(y-b.yi,-z)*180.0/3.141592653589793;break;}y=b.yi;z=-1000;pitch=0;if(i+1<beats.size()&&f<beats[i+1].ts){const auto& next=beats[i+1];double t=smooth(double(f-b.ie)/std::max(1,next.ts-b.ie));y=b.yi+(next.yt-b.yi)*t;z=-1000-900*t;pitch=std::atan2(y-next.yi,-z)*180.0/3.141592653589793;break;}}
   samples.push_back(J{{"frame",f},{"camera",camera(x,y,z,pitch,yaw)}});
 }
 return J{{"schema","chronon.render-plan.v3"},{"version",3},{"job_id","bullet_camera_"+mode},{"canvas",{{"width",W},{"height",H},{"fps_num",FPS},{"fps_den",1},{"duration_frames",duration}}},{"camera",camera(0,beats.front().yt,-1800,13.5)},{"camera_samples",std::move(samples)},{"layers",std::move(layers)},{"output",{{"path","bullet_camera_"+mode+".mp4"},{"format","mp4"},{"codec","h264"}}}};
}
}
int main(int argc,char** argv){try{
 if(argc<3)throw std::runtime_error("usage: emit_bullet_camera_images fast_intro|normal_chapter OUTPUT_PLAN [IMAGE ...]");
 std::string mode=argv[1];Recipe r;
 if(mode=="fast_intro")r={{"Ogni scelta lascia una traccia","Le immagini raccontano il resto"},40,15,30,24,62};
 else if(mode=="normal_chapter")r={{"Il contesto cambia il significato","I dettagli rendono visibile il cambiamento","Ogni immagine aggiunge una prova"},65,25,45,42,54};
 else throw std::runtime_error("unknown mode: "+mode);
 std::vector<std::string> images;for(int i=3;i<argc;++i)images.emplace_back(argv[i]);
 if(images.empty()){images={"ChrononTemplate/assets/web_archive_v1/serednyaks.png","ChrononTemplate/assets/web_archive_v1/kulaks.png","ChrononTemplate/assets/web_archive_v1/bednyaks.png"};}
 fs::path out=argv[2];if(!out.parent_path().empty())fs::create_directories(out.parent_path());std::ofstream f(out);if(!f)throw std::runtime_error("cannot open output plan: "+out.string());f<<build(r,images,mode).dump(2)<<'\n';std::cout<<"Wrote native C++ RenderPlan: "<<out<<'\n';return 0;
}catch(const std::exception& e){std::cerr<<"bullet camera emitter: "<<e.what()<<'\n';return 1;}}
