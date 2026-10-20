#include <nlohmann/json.hpp>
#include <filesystem>
#include <fstream>
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <map>
#include <string>
#include <vector>
using J=nlohmann::ordered_json;
struct Scene{J layers=J::array();int frames=1;std::string name;bool tilted=false;};
J box(std::string id,double x,double y,double w,double h,std::string hex,double alpha=1.0,double rot=0){auto c=[&](int i){return std::stoi(hex.substr(1+i*2,2),nullptr,16)/255.0;};J l={{"id",id},{"type","shape"},{"position",{x,rot?1080-y:y}},{"size",{w,h}},{"start_frame",0},{"duration_frames",1},{"shape",{{"type","rect"},{"fill",{c(0),c(1),c(2),alpha}}}}};if(rot){l["rotation"]={0,0,rot};l["enable_3d"]=true;}return l;}
std::string shell_quote(const std::string&s){std::string r="'";for(char c:s){if(c=='\'')r+="'\\''";else r+=c;}return r+="'";}
double width(std::string const&s,double fs,std::string font="assets/fonts/Inter-Regular.ttf"){
 static std::map<std::string,double> cache;const std::string key=font+"\n"+std::to_string(fs)+"\n"+s;auto hit=cache.find(key);if(hit!=cache.end())return hit->second;
 const std::string cmd="hb-shape --font-size="+std::to_string(fs)+" --output-format=json "+shell_quote(font)+" "+shell_quote(s)+" 2>/dev/null";
 FILE*p=popen(cmd.c_str(),"r");if(!p)throw std::runtime_error("cannot run HarfBuzz shaper");std::string out;char b[4096];while(std::fgets(b,sizeof(b),p))out+=b;const int status=pclose(p);if(status!=0)throw std::runtime_error("HarfBuzz failed to shape text: "+s);
 auto glyphs=J::parse(out);double result=0;for(const auto&g:glyphs)result+=g.value("ax",0.0);cache.emplace(key,result);return result;
}
void rect(Scene&s,std::string id,double x,double y,double w,double h,std::string color,double alpha=1,double rot=0){
 if(id=="brand_backdrop"){
  J grad={{"type","radial"},{"spread","pad"},{"start",{0,0}},{"end",{1,0}},
   {"center",{.5,.5}},{"radius",.5},{"angle",0},
   {"color_stops",J::array({J{{"position",0},{"color",{.67,.65,.62,1}}},J{{"position",1},{"color",{.67,.65,.62,1}}}})},
   {"opacity_stops",J::array({J{{"position",0},{"opacity",.22}},J{{"position",1},{"opacity",0}}})}};
  J l={{"id","brand_halo"},{"type","shape"},{"position",{x,y}},{"size",{w+100,h+64}},
   {"start_frame",0},{"duration_frames",1},{"shape",{{"type","ellipse"},{"fill",grad}}}};
  s.layers.push_back(std::move(l)); return;
 }
 s.layers.push_back(box(std::move(id),x,y,w,h,color,alpha,rot));
}
void paper_grain(Scene&s,std::string prefix,double x0,double y0,double w,double h,int count){
 uint32_t state=0x6d2b79f5u;
 auto next=[&](){state^=state<<13;state^=state>>17;state^=state<<5;return state;};
 for(int i=0;i<count;i++){
  double x=x0+(next()%10000)/10000.0*w, y=y0+(next()%10000)/10000.0*h;
  double d=1.0+(next()%3), a=.018+(next()%20)/1000.0;
  rect(s,prefix+"_grain_"+std::to_string(i),x,y,d,d,(i%3==0)?"#8B8174":"#5B554D",a);
 }
}
void txt(Scene&s,std::string id,std::string t,double xleft,double y,double fs,std::string color,std::string font="assets/fonts/Inter-Regular.ttf",double rot=0){const double shapedWidth=width(t,fs,font);constexpr double lineBox=1900.0;J l={{"id",id},{"type","text"},{"text",t},{"position",{xleft+shapedWidth*.5,rot?1080-y:y}},{"size",{lineBox,fs*1.8}},{"start_frame",0},{"duration_frames",1},{"style",{{"font",font},{"font_size",fs},{"fill",color},{"fit_mode","none"}}}};if(rot){l["rotation"]={0,0,rot};l["enable_3d"]=true;}s.layers.push_back(l);}
void marker(Scene&s,std::string id,double x,double y,double w,double h,bool warm=false){
 const std::string c=warm?"#E7C900":"#E7CE00";
 // One continuous path per visual line. Chronon's deterministic brush profile
 // supplies edge texture/pressure variation; glyphs remain a separate sharp pass.
 J path=J::array();
 constexpr int brush_points=12;
 for(int i=0;i<brush_points;i++){
  const double u=static_cast<double>(i)/(brush_points-1);
  const double yy=1.7*std::sin(u*19.0+0.35)+0.8*std::sin(u*43.0+1.1);
  path.push_back(J{{"type",i==0?"move_to":"line_to"},
                   {"point",{-w*.5+u*w,yy}}});
 }
 const auto rgb=[&](int i){return std::stoi(c.substr(1+i*2,2),nullptr,16)/255.0;};
 J stroke={{"color",{rgb(0),rgb(1),rgb(2),.76}},{"width",h*1.02},
        {"cap","round"},{"join","round"},{"brush",{
         {"size",h*1.02},{"hardness",.54},{"opacity",.8},{"flow",.9},
         {"spacing",.07},{"roundness",.9},{"pressure_width",.2},
         {"pressure_opacity",.14},{"width_jitter",.16},{"opacity_jitter",.12},
         {"scatter",.02},{"grain",.28},{"grain_scale",.8},
         {"edge_noise",.48},{"edge_softness",.18},{"seed",0x4d41524b}
        }}};
 J shape={{"type","path"},{"path",path},{"fill",{0,0,0,0}},{"stroke",stroke}};
 J l={{"id",id},{"type","shape"},{"position",{x+w*.5,y}},
      {"size",{w,h}},{"start_frame",0},{"duration_frames",1},{"shape",shape}};
 s.layers.push_back(std::move(l));
}
void article(Scene&s,bool highlight){s.name=highlight?"article_guardian_highlight":"article_guardian_static";rect(s,"paper",960,540,1920,1080,"#F0EFED");rect(s,"paper_inner",960,540,1790,1080,"#FCFBF9",.79);paper_grain(s,"article",86,30,1748,1020,160);rect(s,"edge_left",18,540,36,1080,"#B9B5AF",.10);rect(s,"edge_right",1902,540,36,1080,"#B9B5AF",.10);rect(s,"edge_top",960,14,1920,28,"#B9B5AF",.08);rect(s,"edge_bottom",960,1066,1920,28,"#B9B5AF",.08);rect(s,"brand_backdrop",158,86,316,112,"#AAA7A3",.25);txt(s,"brand_scienza","SCIENZA",58,73,45,"#FFFFFF","assets/fonts/Inter-ExtraBold.ttf");txt(s,"brand_tips","Tips  |  by ...",59,112,17,"#FFFFFF","assets/fonts/Inter-Bold.ttf");txt(s,"guardian_1","The",323,174,65,"#111111","assets/fonts/PlayfairDisplay-Bold.ttf");txt(s,"guardian_2","Guardian",323,226,63,"#111111","assets/fonts/PlayfairDisplay-Bold.ttf");
 double x=323,fs=39;txt(s,"p1a","La",x,325,fs,"#171717");x+=width("La ",fs);txt(s,"p1b","Monna Lisa",x,325,fs,"#171717","assets/fonts/Inter-Bold.ttf");x+=width("Monna Lisa",fs,"assets/fonts/Inter-Bold.ttf");txt(s,"p1c",", attualmente ospitata nella",x,325,fs,"#171717");x+=width(", attualmente ospitata nella ",fs);txt(s,"p1d","Salle des États",x,325,fs,"#171717","assets/fonts/Inter-Bold.ttf");x+=width("Salle des États",fs,"assets/fonts/Inter-Bold.ttf");txt(s,"p1e",", ha dovuto",x,325,fs,"#171717");
 const double x0=323, bodyfs=38.5;
 txt(s,"p2","affrontare problemi di visibilità e sovraffollamento. Le statistiche rivelano",x0,379,bodyfs,"#171717");
 const std::string line1="che circa l'80% dei visitatori del Louvre viene appositamente per vedere", line2="questo dipinto iconico";
 if(highlight)marker(s,"marker_line1",x0,433,width(line1,bodyfs),31,false);
 txt(s,"p3",line1,x0,433,bodyfs,"#171717");
 if(highlight)marker(s,"marker_line2",x0,487,width(line2,bodyfs),31,false);
 txt(s,"p4",line2+", con un numero significativo di visitatori alle prime",x0,487,bodyfs,"#171717");txt(s,"p5","armi.",x0,541,bodyfs,"#171717");
 txt(s,"p6","In genere la sala diventa così congestionata che i visitatori possono",x0,639,bodyfs,"#171717");txt(s,"p7","trascorrere in media solo 50 secondi a guardare il dipinto e non tutti",x0,693,bodyfs,"#171717");txt(s,"p8","riescono a vederlo bene, soprattutto i bambini e le persone con problemi",x0,747,bodyfs,"#171717");txt(s,"p9","di mobilità.",x0,801,bodyfs,"#171717");txt(s,"p10","Per affrontare queste sfide, l'amministrazione del Louvre, guidata da",x0,897,bodyfs,"#171717");
 const std::string bold="Laurence des Cars", rest=", sta valutando l'idea di trasferire la ", bold2="Monna Lisa", rest2=" in una"; double y=951; x=x0; txt(s,"p11a",bold,x,y,bodyfs,"#171717","assets/fonts/Inter-Bold.ttf"); x+=width(bold,bodyfs,"assets/fonts/Inter-Bold.ttf"); txt(s,"p11b",rest,x,y,bodyfs,"#171717"); x+=width(rest,bodyfs); txt(s,"p11c",bold2,x,y,bodyfs,"#171717","assets/fonts/Inter-Bold.ttf"); x+=width(bold2,bodyfs,"assets/fonts/Inter-Bold.ttf"); txt(s,"p11d",rest2,x,y,bodyfs,"#171717");
 txt(s,"p12","camera sotterranea dedicata. Questa mossa mira a creare un ambiente",x0,1005,bodyfs,"#171717");txt(s,"p13","più controllato e spazioso per i visitatori.",x0,1059,bodyfs,"#171717");}
void evidence(Scene&s){s.name="evidence_zoom";auto layer=[](std::string id,std::string asset){return J{{"id",id},{"type","image"},{"asset",asset},{"position",{0,0}},{"size",{1920,1080}},{"fit","stretch"},{"screen_space",true},{"start_frame",0},{"duration_frames",1}};};s.layers.push_back(layer("same_page_context_blur","assets/reference_article/evidence_blur.png"));s.layers.push_back(layer("same_page_sharp_focus","assets/reference_article/evidence_focus.png"));}
void tilted(Scene&s){s.name="tilted_news_card";s.tilted=true;rect(s,"black",960,540,1920,1080,"#050607");rect(s,"photo_blue",960,165,1850,420,"#102956",.96,-2.4);rect(s,"photo_skin",1450,130,270,400,"#A87865",.85,-2.4);rect(s,"photo_cyan",620,205,240,300,"#147A80",.8,-2.4);
 // Soft-looking stacked shadow and a restrained hairline separate the card from its dark backdrop.
 for(int i=0;i<3;i++)rect(s,"card_shadow_"+std::to_string(i),960,625+i*8,1860+i*12,870+i*12,"#000000",.045,-2.4);
 rect(s,"card",960,615,1840,850,"#1B1B1B",1,-2.4);
 rect(s,"stroke_top",960,191,1840,2,"#E5E5E5",.13,-2.4);rect(s,"stroke_bottom",960,1039,1840,2,"#E5E5E5",.13,-2.4);rect(s,"stroke_left",40,615,2,850,"#E5E5E5",.13,-2.4);rect(s,"stroke_right",1880,615,2,850,"#E5E5E5",.13,-2.4);
 rect(s,"card_high",960,220,1840,72,"#151515",.9,-2.4);txt(s,"caption","Mark Cuban yells during the game against the San Antonio Spurs — NBA playoffs",150,243,24,"#AAAAAA","assets/fonts/Inter-Regular.ttf",-2.4);txt(s,"nba","NBA",135,420,28,"#AAAAAA","assets/fonts/Inter-Bold.ttf",-2.4);txt(s,"headline1","Report: Mark Cuban Hired Former FBI Agent",125,502,65,"#F1F1F1","assets/fonts/Inter-ExtraBold.ttf",-2.4);txt(s,"headline2","to Investigate NBA After 2006 Finals",125,578,65,"#F1F1F1","assets/fonts/Inter-ExtraBold.ttf",-2.4);txt(s,"byline","Grant Hughes  ·  May 19, 2014",130,668,31,"#969696","assets/fonts/Inter-Regular.ttf",-2.4);txt(s,"social","X       f       ↗",132,765,33,"#B5B5B5","assets/fonts/Inter-Bold.ttf",-2.4);}
int main(int argc,char**argv){if(argc!=3)return 2;std::string mode=argv[1];Scene s;if(mode=="article")article(s,false);else if(mode=="article-highlight")article(s,true);else if(mode=="evidence")evidence(s);else tilted(s);J p={{"schema","chronon.render-plan.v3"},{"version",3},{"job_id",s.name},{"canvas",{{"width",1920},{"height",1080},{"fps_num",30},{"fps_den",1},{"duration_frames",1}}},{"layers",s.layers},{"output",{{"path","unused.mp4"},{"format","mp4"},{"codec","h264"}}}};std::ofstream o(argv[2]);o<<p.dump(2)<<"\n";return o?0:3;}
