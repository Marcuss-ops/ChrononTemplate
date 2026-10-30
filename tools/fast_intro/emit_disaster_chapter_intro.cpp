#include <nlohmann/json.hpp>
#include <fstream>
#include <filesystem>
#include <cmath>
using J=nlohmann::json; using namespace std;
J key(int f,double v){return J{{"frame",f},{"value",v}};}
J tr(string p,J k){return J{{"property",p},{"easing","in_out_cubic"},{"keyframes",k}};}
J shape(string id,double x,double y,double z,double w,double h,J fill,string typ="rect") {J q; q["id"]=id;q["type"]="shape";q["enable_3d"]=true;q["screen_space"]=true;q["position"]={x,y,z};q["size"]={w,h};q["shape"]={{"type",typ},{"fill",fill}};q["start_frame"]=0;q["duration_frames"]=150;return q;}
J text(string id,string s,double y,int sz,string font,string fill="#FFF8F5") {J q;q["id"]=id;q["type"]="text";q["text"]=s;q["position"]={960,y,-8};q["size"]={1840,112};q["enable_3d"]=true;q["screen_space"]=true;q["start_frame"]=0;q["duration_frames"]=150;q["style"]={{"font",font},{"font_size",sz},{"min_font_size",sz-10},{"max_font_size",sz},{"fit_mode","shrink_only"},{"fill",fill}};q["animation"]["tracks"]=J::array({tr("opacity",J::array({key(0,0),key(22,1),key(130,1),key(149,0)})),tr("scale_x",J::array({key(0,.94),key(26,1.0),key(120,1.075),key(149,1.11)})),tr("scale_y",J::array({key(0,.94),key(26,1.0),key(120,1.075),key(149,1.11)}))});return q;}
int main(int c,char**v){filesystem::path out=c>1?v[1]:"ChrononTemplate/out/disaster_chapter_v1/disaster_chapter_v1.plan.json";filesystem::create_directories(out.parent_path());J L=J::array();J bg;bg["id"]="black_ground";bg["type"]="color";bg["screen_space"]=true;bg["size"]={1920,1080};bg["color"]={.003,.002,.004,1};bg["start_frame"]=0;bg["duration_frames"]=150;L.push_back(bg);
for(int i=0;i<24;i++){unsigned n=static_cast<unsigned>(i*747796405u+2891336453u);n=(n>>((n>>28)+4))^n;n*=277803737u;n=(n>>22)^n;double x=80+(n%1760),y=55+((n/7)%970),s=2+(n%11),drift=35+(n%70),phase=(n%53)/53.;J d=shape("particle_"+to_string(i),x,y,-20-i,s,s,J{.88,.73,.69,.28+(n%35)/100.},"ellipse");d["animation"]["tracks"]=J::array({tr("position_x",J::array({key(0,x-drift*.3),key(75,x+drift*.2),key(149,x+drift)})),tr("position_y",J::array({key(0,y+drift),key(75,y-drift*.25),key(149,y-drift)})),tr("opacity",J::array({key(0,.04),key(static_cast<int>(25+phase*28),.72),key(95,.24),key(149,.03)}))});L.push_back(d);if(i%4==0){J halo=shape("particle_halo_"+to_string(i),x,y,-19-i,s*4,s*4,J{.62,.12,.11,.12},"ellipse");halo["animation"]["tracks"]=J::array({tr("opacity",J::array({key(0,.02),key(60,.24),key(149,.01)}))});L.push_back(halo);}}
L.push_back(shape("red_atmosphere",960,500,-5,1100,560,J{.24,.012,.018,.30},"ellipse"));J band=shape("band_outer",960,657,0,1920,112,J{.35,.008,.018,1});band["animation"]["tracks"]=J::array({tr("scale_x",J::array({key(0,.01),key(20,1),key(122,1),key(149,.01)})),tr("scale_y",J::array({key(0,.92),key(20,1),key(122,1.08),key(149,.92)}))});L.push_back(band);L.push_back(shape("band_red",960,657,-1,1920,94,J{.78,.012,.025,1}));
// A pair of blurred text passes supplies an actual soft halo behind the crisp title.
J glow=text("title_glow_wide","THE HITMAN HIDDEN IN A FAMILY PHOTO",660,66,"Chronon3d/assets/fonts/Inter-Bold.ttf","#FF2638");glow["style"]["fill"]="#FF2638";J anim;anim["id"]="wide_red_glow";anim["properties"]=J::array({J{{"property","blur"},{"easing","linear"},{"keyframes",J::array({key(0,22),key(149,22)})}}});J sel;sel["id"]="glow_all";sel["unit"]="character";sel["shape"]="square";sel["start"]["keyframes"]=J::array({key(0,0)});sel["end"]["keyframes"]=J::array({key(0,100)});anim["selectors"]=J::array({sel});glow["text_animators"]=J::array({anim});L.push_back(glow);
J tight=text("title_glow_core","THE HITMAN HIDDEN IN A FAMILY PHOTO",660,66,"Chronon3d/assets/fonts/Inter-Bold.ttf","#FF6670");tight["position"][2]=-9;L.push_back(tight);L.push_back(text("chapter_title","THE HITMAN HIDDEN IN A FAMILY PHOTO",660,66,"Chronon3d/assets/fonts/Inter-Bold.ttf"));L.push_back(text("chapter_label_glow","CHAPTER 1",550,54,"Chronon3d/assets/fonts/Inter-Bold.ttf","#FF5968"));L.push_back(text("chapter_label","CHAPTER 1",550,54,"Chronon3d/assets/fonts/Inter-Bold.ttf"));
J cams=J::array();for(int f=0;f<150;f++){double t=f/149.,z=-1350+300*t,x=10*sin(t*3.14159);J cam;cam["type"]="perspective";cam["position"]={x,0,z};cam["rotation_deg"]={0,0,0};cam["fov_deg"]=48.;cam["near"]=1;cam["far"]=10000;cam["zoom"]=1.;cams.push_back(J{{"frame",double(f)},{"camera",cam}});}
J plan;plan["schema"]="chronon.render-plan.v3";plan["version"]=3;plan["job_id"]="disaster_chapter_fast_intro";plan["canvas"]={{"width",1920},{"height",1080},{"fps_num",30},{"fps_den",1},{"duration_frames",150}};plan["camera"]=cams[0]["camera"];plan["camera_samples"]=cams;plan["layers"]=L;plan["output"]={{"path","disaster_chapter_fast_intro.mp4"},{"format","mp4"},{"codec","h264"}};ofstream f(out);f<<plan.dump(2)<<'\n';}








