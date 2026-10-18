// Ten centered editorial bullet cards, each animated by a ChrononMotion3D CameraRig.
#include <chrononmotion/motion/CameraRig.hpp>
#include <chrononmotion/motion/Easing.hpp>
#include <algorithm>
#include <array>
#include <cmath>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>

namespace fs = std::filesystem;
using namespace chrononmotion::motion;
using chrononmotion::Quaternion;
using chrononmotion::Vector3;
namespace {
constexpr int W=1920, H=1080, FPS=30, FRAMES=150;
constexpr float CX=W*.5f, CY=H*.5f, BASE_Z=1800.f;
constexpr double DURATION=static_cast<double>(FRAMES-1)/FPS;
constexpr const char* FONT="assets/fonts/Inter-Bold.ttf";
struct Shot { const char* id; const char* label; const char* title; const char* subtitle; float sx,sy,sz,mx,my,mz,ex,ey,ez,sf,ef; };
const std::array<Shot,10> SHOTS{{
 {"01_push_in","PUSH IN","IL FATTO","Ogni dettaglio comincia da una domanda.",0,0,2050,0,0,1900,0,0,1650,52,48},
 {"02_pull_out","PULL OUT","IL CONTESTO","Allargare lo sguardo cambia la prospettiva.",0,0,1550,0,0,1800,0,0,2150,48,55},
 {"03_orbit_left","ORBITA SINISTRA","LE PROVE","Le fonti si leggono una accanto all'altra.",-360,0,1750,-100,0,1750,220,0,1750,50,50},
 {"04_orbit_right","ORBITA DESTRA","LA CRONOLOGIA","Mettere in ordine i fatti fa emergere i legami.",360,0,1750,100,0,1750,-220,0,1750,50,50},
 {"05_lateral_track","CARRELLATA LATERALE","IL LUOGO","La posizione racconta ciò che le parole non dicono.",-300,0,1700,0,0,1700,300,0,1700,50,50},
 {"06_crane_down","CRANE DOWN","IL DATO","Un punto fermo aiuta a distinguere i segnali.",0,-280,1750,0,-80,1750,0,0,1750,50,50},
 {"07_crane_up","CRANE UP","IL DETTAGLIO","Guardare da vicino, poi tornare all'insieme.",0,260,1800,0,80,1800,0,0,1800,52,50},
 {"08_dolly_arc","DOLLY ARC","IL CAMBIAMENTO","Una sequenza chiara rende visibile la trasformazione.",-220,0,2100,0,0,1850,220,0,1650,54,48},
 {"09_roll_reveal","ROLL REVEAL","IL RISCONTRO","Ogni affermazione deve trovare conferma.",0,0,1850,0,0,1750,0,0,1700,52,49},
 {"10_slow_drift","SLOW DRIFT","LA SINTESI","I punti essenziali, senza perdere il quadro completo.",-90,0,1800,0,0,1780,90,0,1760,50,50}
}};
Vector3 euler(Quaternion q){constexpr float d=57.29577951308232f;q.invert();float x=std::atan2(2.f*(q.w*q.x-q.y*q.z),1.f-2.f*(q.x*q.x+q.y*q.y));float sy=std::clamp(2.f*(q.w*q.y+q.z*q.x),-1.f,1.f);float y=std::asin(sy),z=std::atan2(2.f*(q.w*q.z-q.x*q.y),1.f-2.f*(q.y*q.y+q.z*q.z));return{x*d,y*d,z*d};}
void quoted(std::ostream& o,const std::string& s){o<<'"';for(unsigned char c:s){if(c=='"'||c=='\\')o<<'\\'<<c;else if(c<0x20)o<<"\\u00"<<std::hex<<std::setw(2)<<std::setfill('0')<<static_cast<int>(c)<<std::dec;else o<<c;}o<<'"';}
void track(std::ostream& o,const char* p,const std::vector<double>& vals){o<<"{\"property\":";quoted(o,p);o<<",\"easing\":\"linear\",\"keyframes\":[";for(int i=0;i<FRAMES;++i){if(i)o<<',';o<<"{\"frame\":"<<i<<",\"value\":"<<std::fixed<<std::setprecision(6)<<vals[i]<<'}';}o<<"]}";}
void text(std::ostream& o,const char* id,const char* value,int y,int size,const char* fill,bool comma){if(comma)o<<',';o<<"{\"id\":";quoted(o,id);o<<",\"type\":\"text\",\"text\":";quoted(o,value);o<<",\"size\":[1600,180],\"position\":[960,"<<y<<",0],\"enable_3d\":true,\"start_frame\":0,\"duration_frames\":150,\"style\":{\"font\":\""<<FONT<<"\",\"font_size\":"<<size<<",\"min_font_size\":"<<size<<",\"max_font_size\":"<<size<<",\"fit_mode\":\"shrink_only\",\"fill\":\""<<fill<<"\"}}";}
void emit(const Shot& s,const fs::path& path){
 CameraRig rig(1,s.sf,static_cast<float>(W)/H,1.f,5000.f);rig.setPosition({CX+s.sx,CY+s.sy,s.sz}).setTarget({CX,CY,0}).setFov(s.sf);
 const Easing ease=Easing::easeInOut();
 rig.positionTrack().add(0.f,{CX+s.sx,CY+s.sy,s.sz},ease).add(DURATION*.5f,{CX+s.mx,CY+s.my,s.mz},ease).add(static_cast<float>(DURATION),{CX+s.ex,CY+s.ey,s.ez},ease);
 rig.targetTrack().add(0.f,{CX,CY,0},ease).add(DURATION*.5f,{CX,CY,0},ease).add(static_cast<float>(DURATION),{CX,CY,0},ease);
 rig.fovTrack().add(0.f,s.sf,ease).add(DURATION*.5f,(s.sf+s.ef)*.5f,ease).add(static_cast<float>(DURATION),s.ef,ease);
 if(std::string(s.id)=="09_roll_reveal")rig.rollTrack().add(0.f,-0.12f,ease).add(DURATION*.5f,0.10f,ease).add(static_cast<float>(DURATION),0.f,ease);
 std::array<std::vector<double>,7> c;for(auto& v:c)v.resize(FRAMES);
 for(int f=0;f<FRAMES;++f){auto p=rig.sample(static_cast<float>(f)/FPS);auto r=euler(p.orientation);c[0][f]=p.position.x-CX;c[1][f]=p.position.y-CY;c[2][f]=-p.position.z;c[3][f]=r.x;c[4][f]=r.y;c[5][f]=r.z;c[6][f]=p.fov;}
 auto p=rig.sample(0);auto r=euler(p.orientation);
 fs::create_directories(path.parent_path());std::ofstream f(path);if(!f)throw std::runtime_error("cannot write "+path.string());
 f<<std::setprecision(6)<<"{\n\"schema\":\"chronon.render-plan.v3\",\"version\":3,\"job_id\":\"bullet_camera_"<<s.id<<"\",\n"
  <<"\"canvas\":{\"width\":1920,\"height\":1080,\"fps_num\":30,\"fps_den\":1,\"duration_frames\":150},\n"
  <<"\"camera\":{\"type\":\"perspective\",\"position\":["<<p.position.x-CX<<','<<p.position.y-CY<<','<<-p.position.z<<"],\"rotation_deg\":["<<r.x<<','<<r.y<<','<<r.z<<"],\"fov_deg\":"<<p.fov<<",\"near\":1,\"far\":5000,\"zoom\":1},\n\"camera_animation\":{\"tracks\":[";
 const char* props[]={"camera_position_x","camera_position_y","camera_position_z","camera_rotation_x","camera_rotation_y","camera_rotation_z","camera_fov_deg"};for(int i=0;i<7;++i){if(i)f<<',';track(f,props[i],c[i]);}
 f<<"]},\"layers\":[{\"id\":\"background\",\"type\":\"color\",\"size\":[1920,1080],\"color\":[0.035,0.055,0.075,1.0],\"start_frame\":0,\"duration_frames\":150}";
 text(f,"bullet_text",s.title,CY-18,82,"#F6F3EC",true);text(f,"supporting_text",s.subtitle,CY-130,34,"#C9D2D8",true);
 f<<"],\"output\":{\"path\":\""<<s.id<<".mp4\",\"format\":\"mp4\",\"codec\":\"h264\"}}\n";
}
}
int main(int argc,char**argv)try{if(argc!=2)throw std::runtime_error("usage: chronontemplate_emit_bullet_camera_10 <plans-dir>");fs::path dir=fs::absolute(argv[1]);for(const auto&s:SHOTS){auto p=dir/(std::string(s.id)+".plan.json");emit(s,p);std::cout<<p<<'\n';}return 0;}catch(const std::exception&e){std::cerr<<e.what()<<'\n';return 1;}
