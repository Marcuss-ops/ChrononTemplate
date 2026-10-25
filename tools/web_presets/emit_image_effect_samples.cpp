// Eleven native still plans that demonstrate the existing image-effect stack.
#include <nlohmann/json.hpp>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>

namespace fs=std::filesystem;using J=nlohmann::json;constexpr int W=1920,H=1080;
J rgba(const std::string&s,double a=1){auto n=std::stoul(s.substr(1),nullptr,16);return J::array({((n>>16)&255)/255.0,((n>>8)&255)/255.0,(n&255)/255.0,a});}
J rect(std::string id,int x,int y,int w,int h,std::string c,double a=1){return {{"id",id},{"type","shape"},{"enable_3d",true},{"position",{x+w/2,H-y-h/2,0}},{"size",{w,h}},{"start_frame",0},{"duration_frames",1},{"shape",{{"type","rect"},{"fill",rgba(c,a)}}}};}
J text(std::string id,std::string s,int y,int h,int size,std::string font,std::string c){return {{"id",id},{"type","text"},{"enable_3d",true},{"text",s},{"position",{W/2,H-y-h/2,0}},{"size",{W-160,h}},{"start_frame",0},{"duration_frames",1},{"style",{{"font",font},{"font_size",size},{"fill",c},{"fit_mode","none"},{"text_align","center"}}}};}
J chromatic(double red,double blue){return {{"type","chromatic_aberration"},{"red_offset",red},{"blue_offset",blue}};}
J buildPlan(std::string id,std::string title,std::string sub,J effects,bool lines=false){J l=J::array();J im={{"id","effect_photo"},{"type","image"},{"enable_3d",true},{"screen_space",true},{"asset","assets/images/investigative_journalist_hero.png"},{"position",{W/2,H/2,0}},{"size",{W,H}},{"fit","cover"},{"start_frame",0},{"duration_frames",1}};if(!effects.empty())im["effects"]=std::move(effects);l.push_back(std::move(im));
 if(lines){for(int y=36,i=0;y<880;y+=26,++i)l.push_back(rect("crt_line_"+std::to_string(i),0,y,W,2,i%4==0?"#D9F3F4":"#050709",i%4==0?.045:.13));l.push_back(rect("crt_tint",0,0,W,890,"#132B3E",.10));}
 l.push_back(rect("caption_bar",0,884,W,196,"#071117",.91));l.push_back(rect("caption_accent",150,920,6,94,"#D0A84C"));l.push_back(text("effect_title",std::move(title),902,63,44,"assets/fonts/Oswald-Bold.ttf","#F7F3EA"));l.push_back(text("effect_subtitle",std::move(sub),972,40,19,"assets/fonts/Inter-Medium.ttf","#D5CEC1"));
 return {{"schema","chronon.render-plan.v3"},{"version",3},{"job_id","image_effect_"+id+"_v1"},{"canvas",{{"width",W},{"height",H},{"fps_num",30},{"fps_den",1},{"duration_frames",1}}},{"layers",std::move(l)},{"output",{{"path","image_effect_"+id+".mp4"},{"format","mp4"},{"codec","h264"}}}};}
struct Look{const char* id;const char* title;const char* sub;J fx;bool lines=false;};
std::vector<Look> looks(){return {
 {"chromatic_aberration","CHROMATIC ABERRATION","Red and cyan channels pulled apart at the image edges",J::array({chromatic(12,-12)})},
 {"rgb_prism","RGB PRISM SPLIT","A stronger red / blue ghost creates the classic anaglyph fringe",J::array({chromatic(25,-25)})},
 {"eighties_scanlines","80s CRT SCANLINES","Square-wave interference, phosphor tint and horizontal raster lines",J::array({J{{"type","wave_warp"},{"direction",{0.0,1.0}},{"amplitude",0.0035},{"wavelength",0.018},{"speed",0.0},{"phase",0.0},{"wave_type","square"}},J{{"type","vignette"},{"radius",0.79},{"softness",0.45},{"amount",0.24}}}),true},
 {"vhs_glitch","VHS GLITCH","Torn horizontal slices, RGB separation and coarse tape noise",J::array({J{{"type","mesh_warp"},{"cols",2},{"rows",4},{"smoothness",0.0},{"offsets",{0.0,0.0,0.0,0.0,0.018,0.0,-0.018,0.0,0.0,0.0,0.0,0.0,0.014,0.0,-0.014,0.0}}},chromatic(8,-8),J{{"type","noise"},{"amount",0.12},{"seed",8104}}})},
 {"vintage_crt_lens","VINTAGE CRT LENS","Barrel curvature, gentle chroma fringe and aged film grain",J::array({J{{"type","lens_distortion"},{"curvature",0.17},{"scale",1.10},{"center",{0.5,0.5}}},chromatic(2,-2),J{{"type","noise"},{"amount",0.045},{"seed",1985}},J{{"type","vignette"},{"radius",0.72},{"softness",0.50},{"amount",0.32}}})},
 {"film_grain","ARCHIVAL FILM GRAIN","Fine, deterministic grain over a restrained documentary grade",J::array({J{{"type","noise"},{"amount",0.19},{"seed",1950}},J{{"type","vignette"},{"radius",0.82},{"softness",0.55},{"amount",0.18}}})},
 {"cinematic_vignette","CINEMATIC VIGNETTE","Focus falls toward the center while the photograph stays sharp",J::array({J{{"type","vignette"},{"radius",0.61},{"softness",0.66},{"amount",0.57}}})},
 {"warm_light_leak","WARM LIGHT LEAK","Amber light rays bloom into the frame like a damaged film gate",J::array({J{{"type","light_rays"},{"origin",{0.02,0.50}},{"length",1180},{"density",0.55},{"color",{1.0,0.43,0.12,0.78}},{"decay",0.89}},J{{"type","glow"},{"radius",55},{"intensity",0.32},{"color",{1.0,0.35,0.10,0.62}}}})},
 {"film_halation","FILM HALATION","Soft highlight bloom with a warm edge around bright details",J::array({J{{"type","glow"},{"radius",32},{"intensity",0.48},{"color",{1.0,0.55,0.26,0.7}}},J{{"type","gaussian_blur"},{"radius",0.8}}})},
 {"pixel_mosaic","PIXEL MOSAIC","A digital block treatment for a deliberate archival glitch",J::array({J{{"type","mosaic"},{"block_size",14}},chromatic(3,-3)})},
 {"soft_diffusion","OPTICAL DIFFUSION","A gentle lens softening that keeps the documentary frame readable",J::array({J{{"type","gaussian_blur"},{"radius",2.2}},J{{"type","glow"},{"radius",24},{"intensity",0.14},{"color",{0.82,0.88,0.92,0.25}}}})}
 };}
int main(int argc,char**argv)try{if(argc!=2)throw std::runtime_error("usage: emit_image_effect_samples <output-directory>");fs::path out=fs::absolute(argv[1]);fs::create_directories(out);for(const auto&k:looks()){fs::path file=out/(std::string(k.id)+".plan.json");std::ofstream f(file);f<<buildPlan(k.id,k.title,k.sub,k.fx,k.lines).dump(2)<<'\n';if(!f)throw std::runtime_error("write failed: "+file.string());std::cout<<file<<'\n';}return 0;}catch(const std::exception&e){std::cerr<<e.what()<<'\n';return 1;}
